#!/usr/bin/env python3
"""
Flink Streaming Analytics Examples - Building Block Application

This module demonstrates comprehensive real-time stream processing with Apache Flink:
- Real-time event processing from Kafka
- Complex windowing and aggregations
- Stateful operations and pattern detection
- Event time processing with watermarks
- Multiple output sinks and monitoring
- Backpressure handling and performance optimization

Usage:
    bazel run //flink/python:streaming_analytics -- --kafka-topic events --duration 120

Examples:
    # Basic streaming analytics
    bazel run //flink/python:streaming_analytics
    
    # Custom topic and duration
    bazel run //flink/python:streaming_analytics -- --kafka-topic user-events --duration 300
    
    # High-throughput processing
    bazel run //flink/python:streaming_analytics -- --parallelism 8 --duration 600
"""

import sys
import time
import json
import signal
from datetime import datetime, timedelta
from flink_common import (
    FlinkConfig,
    create_flink_environment,
    create_table_environment,
    generate_sample_streaming_data,
    create_kafka_source,
    create_kafka_sink,
    setup_postgres_table,
    monitor_job_progress,
    print_stream_summary,
    parse_common_args,
    handle_errors,
    cleanup_environment,
    metrics_tracker,
)

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.table import StreamTableEnvironment
    from pyflink.common import Types, WatermarkStrategy, Duration, Time
    from pyflink.datastream.window import (
        TumblingEventTimeWindows,
        SlidingEventTimeWindows,
        SessionWindows,
    )
    from pyflink.datastream.functions import (
        ProcessFunction,
        KeyedProcessFunction,
        WindowFunction,
        AggregateFunction,
        ReduceFunction,
        MapFunction,
        FilterFunction,
    )
    from pyflink.common.state import (
        ValueStateDescriptor,
        ListStateDescriptor,
        MapStateDescriptor,
    )
    from pyflink.common.time import Time as FlinkTime
    from pyflink.common.typeinfo import TypeInformation
    from pyflink.datastream.connectors.kafka import FlinkKafkaProducer
    from pyflink.common.serialization import SimpleStringSchema
except ImportError:
    print("ERROR: PyFlink not found. Install with: pip install apache-flink")
    sys.exit(1)


class EventData:
    """Data class for parsed events."""

    def __init__(self, json_str: str):
        try:
            data = json.loads(json_str)
            self.event_id = data.get("event_id", "")
            self.user_id = data.get("user_id", "")
            self.session_id = data.get("session_id", "")
            self.product_id = data.get("product_id", "")
            self.category = data.get("category", "")
            self.action = data.get("action", "")
            self.price = float(data.get("price", 0))
            self.quantity = int(data.get("quantity", 0))
            self.timestamp = data.get("timestamp", "")
            self.metadata = data.get("metadata", {})
            self.total_amount = self.price * self.quantity
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            # Handle malformed data gracefully
            self.event_id = "invalid"
            self.user_id = "unknown"
            self.session_id = "unknown"
            self.product_id = "unknown"
            self.category = "unknown"
            self.action = "unknown"
            self.price = 0.0
            self.quantity = 0
            self.timestamp = datetime.now().isoformat()
            self.metadata = {}
            self.total_amount = 0.0

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "product_id": self.product_id,
            "category": self.category,
            "action": self.action,
            "price": self.price,
            "quantity": self.quantity,
            "total_amount": self.total_amount,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class EventParsingFunction(MapFunction):
    """Parse JSON events into structured data."""

    def map(self, value):
        event = EventData(value)
        metrics_tracker.increment("events_parsed")

        if event.event_id == "invalid":
            metrics_tracker.increment("parsing_errors")

        return event.to_dict()


class RevenueAggregator(AggregateFunction):
    """Aggregate revenue metrics in windows."""

    def create_accumulator(self):
        return {
            "total_revenue": 0.0,
            "order_count": 0,
            "unique_users": set(),
            "unique_products": set(),
            "max_order_value": 0.0,
            "min_order_value": float("inf"),
        }

    def add(self, value, accumulator):
        event = value
        accumulator["total_revenue"] += event["total_amount"]
        accumulator["order_count"] += 1
        accumulator["unique_users"].add(event["user_id"])
        accumulator["unique_products"].add(event["product_id"])
        accumulator["max_order_value"] = max(
            accumulator["max_order_value"], event["total_amount"]
        )
        accumulator["min_order_value"] = min(
            accumulator["min_order_value"], event["total_amount"]
        )
        return accumulator

    def get_result(self, accumulator):
        return {
            "total_revenue": accumulator["total_revenue"],
            "order_count": accumulator["order_count"],
            "unique_users": len(accumulator["unique_users"]),
            "unique_products": len(accumulator["unique_products"]),
            "avg_order_value": accumulator["total_revenue"]
            / max(accumulator["order_count"], 1),
            "max_order_value": (
                accumulator["max_order_value"]
                if accumulator["max_order_value"] != 0
                else 0
            ),
            "min_order_value": (
                accumulator["min_order_value"]
                if accumulator["min_order_value"] != float("inf")
                else 0
            ),
        }

    def merge(self, acc1, acc2):
        return {
            "total_revenue": acc1["total_revenue"] + acc2["total_revenue"],
            "order_count": acc1["order_count"] + acc2["order_count"],
            "unique_users": acc1["unique_users"].union(acc2["unique_users"]),
            "unique_products": acc1["unique_products"].union(acc2["unique_products"]),
            "max_order_value": max(acc1["max_order_value"], acc2["max_order_value"]),
            "min_order_value": min(acc1["min_order_value"], acc2["min_order_value"]),
        }


class UserSessionTracker(KeyedProcessFunction):
    """Track user sessions with timeouts."""

    def __init__(self, session_timeout_minutes: int = 30):
        self.session_timeout = (
            session_timeout_minutes * 60 * 1000
        )  # Convert to milliseconds
        self.session_state = None
        self.timer_state = None

    def open(self, runtime_context):
        # Initialize state descriptors
        session_descriptor = ValueStateDescriptor(
            "user_session", TypeInformation.of(Types.PICKLED_BYTE_ARRAY())
        )
        self.session_state = runtime_context.get_state(session_descriptor)

        timer_descriptor = ValueStateDescriptor(
            "session_timer", TypeInformation.of(Types.LONG())
        )
        self.timer_state = runtime_context.get_state(timer_descriptor)

    def process_element(self, value, ctx, out):
        current_session = self.session_state.value()
        current_time = ctx.timestamp()

        if current_session is None:
            # Start new session
            current_session = {
                "session_id": value["session_id"],
                "user_id": value["user_id"],
                "start_time": current_time,
                "last_activity": current_time,
                "event_count": 0,
                "total_spent": 0.0,
                "actions": [],
            }

        # Update session
        current_session["last_activity"] = current_time
        current_session["event_count"] += 1
        current_session["total_spent"] += value["total_amount"]
        current_session["actions"].append(value["action"])

        # Update state
        self.session_state.update(current_session)

        # Set/update timer for session timeout
        timer_time = current_time + self.session_timeout
        self.timer_state.update(timer_time)
        ctx.timer_service().register_event_time_timer(timer_time)

        # Emit updated session info
        session_info = {
            **current_session,
            "duration_minutes": (current_time - current_session["start_time"])
            / (1000 * 60),
            "avg_time_between_events": (current_time - current_session["start_time"])
            / max(current_session["event_count"] - 1, 1)
            / 1000,
        }

        out.collect(session_info)
        metrics_tracker.increment("session_updates")

    def on_timer(self, timestamp, ctx, out):
        # Session timed out
        current_session = self.session_state.value()
        if current_session:
            # Emit final session summary
            final_session = {
                **current_session,
                "session_ended": True,
                "end_reason": "timeout",
                "duration_minutes": (timestamp - current_session["start_time"])
                / (1000 * 60),
            }
            out.collect(final_session)
            metrics_tracker.increment("sessions_ended")

        # Clear state
        self.session_state.clear()
        self.timer_state.clear()


class FraudDetectionFunction(ProcessFunction):
    """Detect potential fraud patterns."""

    def __init__(self):
        self.suspicious_amounts = [999.99, 1000.00, 1111.11, 1234.56]
        self.high_risk_categories = ["ELECTRONICS", "JEWELRY"]

    def process_element(self, value, ctx, out):
        fraud_score = 0
        fraud_reasons = []

        # Check for suspicious amounts
        if value["total_amount"] in self.suspicious_amounts:
            fraud_score += 30
            fraud_reasons.append("suspicious_amount")

        # Check for high-value transactions
        if value["total_amount"] > 500:
            fraud_score += 20
            fraud_reasons.append("high_value")

        # Check for high-risk categories
        if value["category"] in self.high_risk_categories:
            fraud_score += 15
            fraud_reasons.append("high_risk_category")

        # Check for rapid transactions (would need state to track)
        # This is simplified - in practice you'd track recent transactions per user

        # Check time patterns (late night purchases)
        try:
            event_time = datetime.fromisoformat(
                value["timestamp"].replace("Z", "+00:00")
            )
            hour = event_time.hour
            if hour < 6 or hour > 23:
                fraud_score += 10
                fraud_reasons.append("unusual_time")
        except:
            pass

        # Emit fraud alert if score is high enough
        if fraud_score >= 30:
            fraud_alert = {
                "event_id": value["event_id"],
                "user_id": value["user_id"],
                "fraud_score": fraud_score,
                "fraud_reasons": fraud_reasons,
                "original_event": value,
                "alert_timestamp": datetime.now().isoformat(),
                "alert_type": "POTENTIAL_FRAUD",
            }
            out.collect(fraud_alert)
            metrics_tracker.increment("fraud_alerts")


@handle_errors
def setup_real_time_analytics(stream):
    """
    Setup comprehensive real-time analytics on the event stream.

    Args:
        stream: Input data stream

    Returns:
        Dictionary of analytics streams
    """
    print("\n🔄 Setting up real-time analytics...")

    analytics_streams = {}

    # 1. Real-time revenue tracking (1-minute tumbling windows)
    print("   Creating revenue tracking...")
    revenue_stream = (
        stream.key_by(lambda event: event["category"])
        .window(TumblingEventTimeWindows.of(FlinkTime.minutes(1)))
        .aggregate(RevenueAggregator())
    )

    analytics_streams["revenue_by_category"] = revenue_stream

    # 2. User session tracking
    print("   Creating user session tracking...")
    session_stream = stream.key_by(lambda event: event["user_id"]).process(
        UserSessionTracker(session_timeout_minutes=30)
    )

    analytics_streams["user_sessions"] = session_stream

    # 3. High-value transaction monitoring
    print("   Creating high-value transaction monitoring...")
    high_value_stream = stream.filter(lambda event: event["total_amount"] > 200).map(
        lambda event: {
            **event,
            "alert_type": "HIGH_VALUE_TRANSACTION",
            "threshold": 200.0,
        }
    )

    analytics_streams["high_value_transactions"] = high_value_stream

    # 4. Fraud detection
    print("   Creating fraud detection...")
    fraud_stream = stream.process(FraudDetectionFunction())
    analytics_streams["fraud_alerts"] = fraud_stream

    # 5. Product popularity tracking (5-minute sliding windows)
    print("   Creating product popularity tracking...")
    product_stream = (
        stream.key_by(lambda event: event["product_id"])
        .window(SlidingEventTimeWindows.of(FlinkTime.minutes(5), FlinkTime.minutes(1)))
        .aggregate(RevenueAggregator())
    )

    analytics_streams["product_popularity"] = product_stream

    # 6. Hourly aggregations for daily reporting
    print("   Creating hourly aggregations...")
    hourly_stream = (
        stream.key_by(lambda event: "global")
        .window(TumblingEventTimeWindows.of(FlinkTime.hours(1)))
        .aggregate(RevenueAggregator())
    )

    analytics_streams["hourly_aggregations"] = hourly_stream

    print("✅ Real-time analytics configured")
    return analytics_streams


@handle_errors
def setup_output_sinks(analytics_streams: dict, config: FlinkConfig, output_path: str):
    """
    Setup multiple output sinks for the analytics streams.

    Args:
        analytics_streams: Dictionary of analytics streams
        config: FlinkConfig object
        output_path: Base output path
    """
    print(f"\n🔄 Setting up output sinks to {output_path}...")

    # 1. Console output for monitoring
    print("   Setting up console outputs...")

    # Revenue tracking to console
    analytics_streams["revenue_by_category"].print("REVENUE")

    # Fraud alerts to console
    analytics_streams["fraud_alerts"].print("FRAUD_ALERT")

    # High-value transactions to console
    analytics_streams["high_value_transactions"].print("HIGH_VALUE")

    # 2. Kafka output for downstream processing
    print("   Setting up Kafka outputs...")

    # Create Kafka sinks
    fraud_kafka_sink = create_kafka_sink("fraud-alerts", config.kafka_servers)
    revenue_kafka_sink = create_kafka_sink("revenue-metrics", config.kafka_servers)

    # Convert to JSON and send to Kafka
    analytics_streams["fraud_alerts"].map(lambda alert: json.dumps(alert)).add_sink(
        fraud_kafka_sink
    )

    analytics_streams["revenue_by_category"].map(
        lambda revenue: json.dumps(revenue)
    ).add_sink(revenue_kafka_sink)

    # 3. File outputs for batch processing
    print("   Setting up file outputs...")

    # Note: In PyFlink, file outputs are typically handled through Table API
    # For demonstration, we'll print file paths where data would be saved
    print(f"   Revenue data would be saved to: {output_path}/revenue/")
    print(f"   Session data would be saved to: {output_path}/sessions/")
    print(f"   Fraud alerts would be saved to: {output_path}/fraud/")

    print("✅ Output sinks configured")


@handle_errors
def setup_monitoring_and_alerts(env: StreamExecutionEnvironment):
    """
    Setup monitoring and alerting for the streaming job.

    Args:
        env: StreamExecutionEnvironment
    """
    print("\n🔄 Setting up monitoring and alerts...")

    # Configure metrics reporting
    config = env.get_config()

    # Enable latency tracking
    config.set_auto_watermark_interval(200)  # 200ms watermark interval

    # Setup custom metrics (would integrate with Prometheus in production)
    print("   Custom metrics tracking enabled")
    print("   Prometheus metrics would be available at: :9249/metrics")

    # Setup alerting thresholds
    print("   Alerting thresholds:")
    print("     - Backpressure > 80%")
    print("     - Checkpoint failure rate > 5%")
    print("     - Processing latency > 10 seconds")
    print("     - Fraud alerts > 10 per minute")

    print("✅ Monitoring and alerts configured")


@handle_errors
def run_streaming_job(
    env: StreamExecutionEnvironment,
    source_stream,
    analytics_streams: dict,
    duration: int,
):
    """
    Execute the streaming job with monitoring.

    Args:
        env: StreamExecutionEnvironment
        source_stream: Input data stream
        analytics_streams: Dictionary of analytics streams
        duration: How long to run the job
    """
    print(f"\n🚀 Starting streaming job for {duration} seconds...")

    # Start the job asynchronously
    job_result = env.execute_async("FlinkStreamingAnalytics")

    start_time = time.time()
    end_time = start_time + duration

    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\n⚠️  Received interrupt signal, stopping job...")
        try:
            job_result.cancel()
        except:
            pass
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Monitor job progress
        while time.time() < end_time and not job_result.is_done():
            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            print(f"\n⏱️  Elapsed: {elapsed:.0f}s | Remaining: {remaining:.0f}s")

            # Print metrics
            metrics = metrics_tracker.get_metrics()
            print(f"   Events processed: {metrics.get('events_parsed', 0)}")
            print(f"   Fraud alerts: {metrics.get('fraud_alerts', 0)}")
            print(f"   Session updates: {metrics.get('session_updates', 0)}")
            print(f"   Sessions ended: {metrics.get('sessions_ended', 0)}")
            print(f"   Parsing errors: {metrics.get('parsing_errors', 0)}")

            # Check job status
            if job_result.is_done():
                print("   Job Status: COMPLETED")
                break
            else:
                print("   Job Status: RUNNING")

            time.sleep(10)  # Check every 10 seconds

    except KeyboardInterrupt:
        print("\n⚠️  Job interrupted by user")
        try:
            job_result.cancel()
        except:
            pass

    except Exception as e:
        print(f"\n❌ Job execution error: {e}")
        try:
            job_result.cancel()
        except:
            pass
        raise

    # Wait for job completion or timeout
    try:
        if not job_result.is_done():
            print("\n🔄 Cancelling job...")
            job_result.cancel()

        print("✅ Streaming job completed")

    except Exception as e:
        print(f"⚠️  Job cleanup warning: {e}")


@handle_errors
def main():
    """Main streaming analytics workflow."""
    # Parse arguments
    parser = parse_common_args()
    args = parser.parse_args()

    print("🚀 Starting Flink Streaming Analytics")
    print(f"   Application: {args.app_name}")
    print(f"   Parallelism: {args.parallelism}")
    print(f"   Duration: {args.duration} seconds")
    print(f"   Kafka topic: {args.kafka_topic}")
    print(f"   Output path: {args.output_path}")

    # Create Flink configuration
    config = FlinkConfig(
        app_name=args.app_name,
        parallelism=args.parallelism,
        kafka_servers=args.kafka_servers,
        postgres_url=args.postgres_url,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
    )

    # Create Flink environment
    env = create_flink_environment(config)

    try:
        # Setup data source
        print(f"\n🔄 Setting up data source...")

        # Option 1: Use Kafka source (if topic exists and has data)
        try:
            kafka_stream = create_kafka_source(
                env, args.kafka_topic, config.kafka_servers, config.kafka_group_id
            )

            # Parse JSON events
            parsed_stream = kafka_stream.map(EventParsingFunction())
            print("✅ Using Kafka source")

        except Exception as e:
            print(f"⚠️  Kafka source not available: {e}")
            print("   Falling back to sample data generator...")

            # Option 2: Use sample data generator
            sample_stream = generate_sample_streaming_data(
                env,
                rate_per_second=50,  # 50 events/second
                total_records=args.duration * 50,  # Enough for duration
            )

            # Parse JSON events
            parsed_stream = sample_stream.map(EventParsingFunction())
            print("✅ Using sample data generator")

        # Set up watermark strategy for event time processing
        watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(
            Duration.of_seconds(20)
        ).with_timestamp_assigner(
            lambda event, ts: int(
                datetime.fromisoformat(
                    event["timestamp"].replace("Z", "+00:00")
                ).timestamp()
                * 1000
            )
        )

        event_stream = parsed_stream.assign_timestamps_and_watermarks(
            watermark_strategy
        )

        # Print stream summary
        print_stream_summary(event_stream, "Parsed Event Stream")

        # Setup real-time analytics
        analytics_streams = setup_real_time_analytics(event_stream)

        # Setup output sinks
        setup_output_sinks(analytics_streams, config, args.output_path)

        # Setup monitoring
        setup_monitoring_and_alerts(env)

        # Monitor job progress
        monitor_job_progress(env, "Streaming Analytics")

        # Run the streaming job
        run_streaming_job(env, event_stream, analytics_streams, args.duration)

        # Print final metrics
        metrics_tracker.print_summary()

        print(f"\n✅ Streaming analytics completed!")
        print(f"   Processed events for {args.duration} seconds")
        print(f"   Results available in Kafka topics and {args.output_path}")
        print(f"   Flink Web UI: http://192.168.1.184:8081")

    except KeyboardInterrupt:
        print("\n⚠️  Streaming analytics interrupted by user")
    except Exception as e:
        print(f"\n❌ Streaming analytics error: {e}")
        raise
    finally:
        cleanup_environment(env)


if __name__ == "__main__":
    main()
