#!/usr/bin/env python3
"""
Flink Advanced Windowing and Aggregations - Building Block Application

This module demonstrates sophisticated windowing patterns with Apache Flink:
- Multiple window types (tumbling, sliding, session, global)
- Custom window triggers and evictors
- Complex aggregations with custom functions
- Window joins and temporal patterns
- Late data handling strategies
- Multi-level windowing hierarchies

Usage:
    bazel run //flink/python:windowing_aggregations -- --window-types tumbling,sliding,session

Examples:
    # Basic windowing patterns
    bazel run //flink/python:windowing_aggregations
    
    # All window types with extended duration
    bazel run //flink/python:windowing_aggregations -- --window-types all --duration 300
    
    # Custom window sizes
    bazel run //flink/python:windowing_aggregations -- --tumbling-minutes 5 --sliding-minutes 10
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
    monitor_job_progress,
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
        GlobalWindows,
        TimeWindow,
    )
    from pyflink.datastream.functions import (
        ProcessWindowFunction,
        AggregateFunction,
        ReduceFunction,
        ProcessFunction,
        WindowFunction,
        AllWindowFunction,
        Trigger,
        TriggerResult,
    )
    from pyflink.common.state import ValueStateDescriptor, ListStateDescriptor
    from pyflink.common.time import Time as FlinkTime
    from pyflink.datastream.state import RuntimeContext
except ImportError:
    print("ERROR: PyFlink not found. Install with: pip install apache-flink")
    sys.exit(1)


class EventData:
    """Enhanced event data class for windowing examples."""

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

            # Parse event time
            try:
                self.event_time = datetime.fromisoformat(
                    self.timestamp.replace("Z", "+00:00")
                )
            except:
                self.event_time = datetime.now()

        except Exception:
            # Fallback for malformed data
            self._set_defaults()

    def _set_defaults(self):
        """Set default values for malformed data."""
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
        self.event_time = datetime.now()

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
            "event_time_ms": int(self.event_time.timestamp() * 1000),
            "metadata": self.metadata,
        }


class RevenueAggregator(AggregateFunction):
    """Advanced revenue aggregator with detailed metrics."""

    def create_accumulator(self):
        return {
            "total_revenue": 0.0,
            "order_count": 0,
            "unique_users": set(),
            "unique_products": set(),
            "unique_sessions": set(),
            "categories": {},
            "actions": {},
            "hourly_distribution": {},
            "price_ranges": {
                "0-50": 0,
                "50-100": 0,
                "100-200": 0,
                "200-500": 0,
                "500+": 0,
            },
            "max_order": {"amount": 0, "user_id": "", "product_id": ""},
            "min_order": {"amount": float("inf"), "user_id": "", "product_id": ""},
            "first_event_time": None,
            "last_event_time": None,
        }

    def add(self, value, accumulator):
        event = value
        amount = event["total_amount"]

        # Basic metrics
        accumulator["total_revenue"] += amount
        accumulator["order_count"] += 1
        accumulator["unique_users"].add(event["user_id"])
        accumulator["unique_products"].add(event["product_id"])
        accumulator["unique_sessions"].add(event["session_id"])

        # Category distribution
        category = event["category"]
        accumulator["categories"][category] = (
            accumulator["categories"].get(category, 0) + amount
        )

        # Action distribution
        action = event["action"]
        accumulator["actions"][action] = accumulator["actions"].get(action, 0) + 1

        # Hourly distribution
        try:
            hour = datetime.fromisoformat(
                event["timestamp"].replace("Z", "+00:00")
            ).hour
            accumulator["hourly_distribution"][hour] = (
                accumulator["hourly_distribution"].get(hour, 0) + amount
            )
        except:
            pass

        # Price range distribution
        if amount <= 50:
            accumulator["price_ranges"]["0-50"] += 1
        elif amount <= 100:
            accumulator["price_ranges"]["50-100"] += 1
        elif amount <= 200:
            accumulator["price_ranges"]["100-200"] += 1
        elif amount <= 500:
            accumulator["price_ranges"]["200-500"] += 1
        else:
            accumulator["price_ranges"]["500+"] += 1

        # Max/min orders
        if amount > accumulator["max_order"]["amount"]:
            accumulator["max_order"] = {
                "amount": amount,
                "user_id": event["user_id"],
                "product_id": event["product_id"],
            }

        if amount < accumulator["min_order"]["amount"]:
            accumulator["min_order"] = {
                "amount": amount,
                "user_id": event["user_id"],
                "product_id": event["product_id"],
            }

        # Time tracking
        event_time = event.get("event_time_ms", int(datetime.now().timestamp() * 1000))
        if (
            accumulator["first_event_time"] is None
            or event_time < accumulator["first_event_time"]
        ):
            accumulator["first_event_time"] = event_time
        if (
            accumulator["last_event_time"] is None
            or event_time > accumulator["last_event_time"]
        ):
            accumulator["last_event_time"] = event_time

        return accumulator

    def get_result(self, accumulator):
        return {
            "total_revenue": accumulator["total_revenue"],
            "order_count": accumulator["order_count"],
            "unique_users": len(accumulator["unique_users"]),
            "unique_products": len(accumulator["unique_products"]),
            "unique_sessions": len(accumulator["unique_sessions"]),
            "avg_order_value": accumulator["total_revenue"]
            / max(accumulator["order_count"], 1),
            "revenue_per_user": accumulator["total_revenue"]
            / max(len(accumulator["unique_users"]), 1),
            "orders_per_user": accumulator["order_count"]
            / max(len(accumulator["unique_users"]), 1),
            "categories": dict(accumulator["categories"]),
            "actions": dict(accumulator["actions"]),
            "hourly_distribution": dict(accumulator["hourly_distribution"]),
            "price_ranges": dict(accumulator["price_ranges"]),
            "max_order": (
                dict(accumulator["max_order"])
                if accumulator["max_order"]["amount"] > 0
                else None
            ),
            "min_order": (
                dict(accumulator["min_order"])
                if accumulator["min_order"]["amount"] != float("inf")
                else None
            ),
            "window_duration_ms": (accumulator["last_event_time"] or 0)
            - (accumulator["first_event_time"] or 0),
            "events_per_second": accumulator["order_count"]
            / max(
                (accumulator["last_event_time"] or 0)
                - (accumulator["first_event_time"] or 0),
                1,
            )
            * 1000,
        }

    def merge(self, acc1, acc2):
        merged = {
            "total_revenue": acc1["total_revenue"] + acc2["total_revenue"],
            "order_count": acc1["order_count"] + acc2["order_count"],
            "unique_users": acc1["unique_users"].union(acc2["unique_users"]),
            "unique_products": acc1["unique_products"].union(acc2["unique_products"]),
            "unique_sessions": acc1["unique_sessions"].union(acc2["unique_sessions"]),
            "categories": {},
            "actions": {},
            "hourly_distribution": {},
            "price_ranges": {},
            "max_order": (
                acc1["max_order"]
                if acc1["max_order"]["amount"] >= acc2["max_order"]["amount"]
                else acc2["max_order"]
            ),
            "min_order": (
                acc1["min_order"]
                if acc1["min_order"]["amount"] <= acc2["min_order"]["amount"]
                else acc2["min_order"]
            ),
            "first_event_time": min(
                acc1["first_event_time"] or float("inf"),
                acc2["first_event_time"] or float("inf"),
            ),
            "last_event_time": max(
                acc1["last_event_time"] or 0, acc2["last_event_time"] or 0
            ),
        }

        # Merge category distributions
        for cat, amount in acc1["categories"].items():
            merged["categories"][cat] = merged["categories"].get(cat, 0) + amount
        for cat, amount in acc2["categories"].items():
            merged["categories"][cat] = merged["categories"].get(cat, 0) + amount

        # Merge action distributions
        for action, count in acc1["actions"].items():
            merged["actions"][action] = merged["actions"].get(action, 0) + count
        for action, count in acc2["actions"].items():
            merged["actions"][action] = merged["actions"].get(action, 0) + count

        # Merge hourly distributions
        for hour, amount in acc1["hourly_distribution"].items():
            merged["hourly_distribution"][hour] = (
                merged["hourly_distribution"].get(hour, 0) + amount
            )
        for hour, amount in acc2["hourly_distribution"].items():
            merged["hourly_distribution"][hour] = (
                merged["hourly_distribution"].get(hour, 0) + amount
            )

        # Merge price ranges
        for range_key in acc1["price_ranges"]:
            merged["price_ranges"][range_key] = (
                acc1["price_ranges"][range_key] + acc2["price_ranges"][range_key]
            )

        return merged


class DetailedWindowProcessFunction(ProcessWindowFunction):
    """Process function that adds window metadata to aggregated results."""

    def process(self, key, context, elements, out):
        """
        Process window results and add metadata.

        Args:
            key: Window key
            context: Window context
            elements: Aggregated elements (should be single result)
            out: Output collector
        """
        window = context.window()
        aggregated_result = list(elements)[0]  # Get the aggregated result

        # Add window metadata
        result = {
            "window_key": key,
            "window_start": window.start,
            "window_end": window.end,
            "window_duration_ms": window.end - window.start,
            "processing_time": context.current_processing_time(),
            "watermark": context.current_watermark(),
            "aggregated_data": aggregated_result,
            "window_type": "tumbling",  # This would be set based on window type
        }

        out.collect(result)
        metrics_tracker.increment("windows_processed")


class SessionAnalysisFunction(ProcessWindowFunction):
    """Specialized function for session window analysis."""

    def process(self, key, context, elements, out):
        """
        Process session window and calculate session-specific metrics.

        Args:
            key: Session key (user_id)
            context: Window context
            elements: All events in the session
            out: Output collector
        """
        window = context.window()
        events = list(elements)

        if not events:
            return

        # Calculate session metrics
        total_amount = sum(event["total_amount"] for event in events)
        event_count = len(events)
        unique_products = len(set(event["product_id"] for event in events))
        unique_categories = len(set(event["category"] for event in events))

        # Action sequence analysis
        actions = [event["action"] for event in events]
        action_sequence = " -> ".join(actions)

        # Time-based analysis
        event_times = [event.get("event_time_ms", 0) for event in events]
        session_duration = max(event_times) - min(event_times) if event_times else 0
        avg_time_between_events = (
            session_duration / max(event_count - 1, 1) if event_count > 1 else 0
        )

        # Purchase pattern analysis
        purchase_events = [e for e in events if e["action"] == "purchase"]
        conversion_rate = len(purchase_events) / event_count if event_count > 0 else 0

        # Session categorization
        if total_amount > 500:
            session_type = "HIGH_VALUE"
        elif event_count > 10:
            session_type = "HIGH_ENGAGEMENT"
        elif unique_categories > 2:
            session_type = "CROSS_CATEGORY"
        elif conversion_rate > 0.5:
            session_type = "HIGH_CONVERSION"
        else:
            session_type = "REGULAR"

        session_result = {
            "user_id": key,
            "session_start": window.start,
            "session_end": window.end,
            "session_duration_ms": session_duration,
            "event_count": event_count,
            "total_amount": total_amount,
            "avg_order_value": total_amount / max(len(purchase_events), 1),
            "unique_products": unique_products,
            "unique_categories": unique_categories,
            "action_sequence": action_sequence,
            "conversion_rate": conversion_rate,
            "avg_time_between_events_ms": avg_time_between_events,
            "session_type": session_type,
            "purchase_count": len(purchase_events),
            "window_type": "session",
        }

        out.collect(session_result)
        metrics_tracker.increment("sessions_analyzed")


class CustomCountTrigger(Trigger):
    """Custom trigger that fires when count threshold is reached or on time."""

    def __init__(self, count_threshold: int = 100):
        self.count_threshold = count_threshold
        self.count_descriptor = ValueStateDescriptor("count", Types.LONG())

    def on_element(self, element, timestamp, window, trigger_context):
        """Called for each element added to window."""
        count_state = trigger_context.get_partitioned_state(self.count_descriptor)
        current_count = count_state.value() or 0
        current_count += 1
        count_state.update(current_count)

        if current_count >= self.count_threshold:
            return TriggerResult.FIRE_AND_PURGE

        # Also register timer for window end
        trigger_context.register_event_time_timer(window.max_timestamp())
        return TriggerResult.CONTINUE

    def on_processing_time(self, time, window, trigger_context):
        """Called when processing time timer fires."""
        return TriggerResult.FIRE_AND_PURGE

    def on_event_time(self, time, window, trigger_context):
        """Called when event time timer fires."""
        return TriggerResult.FIRE_AND_PURGE

    def clear(self, window, trigger_context):
        """Clean up trigger state."""
        count_state = trigger_context.get_partitioned_state(self.count_descriptor)
        count_state.clear()


@handle_errors
def create_tumbling_windows(stream, window_minutes: int = 2):
    """
    Create tumbling window aggregations.

    Args:
        stream: Input data stream
        window_minutes: Window size in minutes

    Returns:
        Tumbling window stream
    """
    print(f"\n🔄 Creating tumbling windows ({window_minutes} minutes)...")

    # Basic tumbling windows by category
    tumbling_stream = (
        stream.key_by(lambda event: event["category"])
        .window(TumblingEventTimeWindows.of(FlinkTime.minutes(window_minutes)))
        .aggregate(RevenueAggregator(), DetailedWindowProcessFunction())
    )

    print(f"✅ Tumbling windows created ({window_minutes}min intervals)")
    return tumbling_stream


@handle_errors
def create_sliding_windows(stream, window_minutes: int = 10, slide_minutes: int = 2):
    """
    Create sliding window aggregations.

    Args:
        stream: Input data stream
        window_minutes: Window size in minutes
        slide_minutes: Slide interval in minutes

    Returns:
        Sliding window stream
    """
    print(
        f"\n🔄 Creating sliding windows ({window_minutes}min window, {slide_minutes}min slide)..."
    )

    # Sliding windows for trend analysis
    sliding_stream = (
        stream.key_by(lambda event: event["category"])
        .window(
            SlidingEventTimeWindows.of(
                FlinkTime.minutes(window_minutes), FlinkTime.minutes(slide_minutes)
            )
        )
        .aggregate(RevenueAggregator(), DetailedWindowProcessFunction())
    )

    print(f"✅ Sliding windows created ({window_minutes}min/{slide_minutes}min)")
    return sliding_stream


@handle_errors
def create_session_windows(stream, session_timeout_minutes: int = 30):
    """
    Create session window aggregations.

    Args:
        stream: Input data stream
        session_timeout_minutes: Session timeout in minutes

    Returns:
        Session window stream
    """
    print(f"\n🔄 Creating session windows ({session_timeout_minutes}min timeout)...")

    # Session windows by user
    session_stream = (
        stream.key_by(lambda event: event["user_id"])
        .window(SessionWindows.with_gap(FlinkTime.minutes(session_timeout_minutes)))
        .process(SessionAnalysisFunction())
    )

    print(f"✅ Session windows created ({session_timeout_minutes}min timeout)")
    return session_stream


@handle_errors
def create_global_windows_with_custom_trigger(stream, count_threshold: int = 50):
    """
    Create global windows with custom trigger.

    Args:
        stream: Input data stream
        count_threshold: Number of events to trigger window

    Returns:
        Global window stream with custom trigger
    """
    print(f"\n🔄 Creating global windows (trigger at {count_threshold} events)...")

    # Global windows with count-based trigger
    global_stream = (
        stream.key_by(lambda event: event["category"])
        .window(GlobalWindows.create())
        .trigger(CustomCountTrigger(count_threshold))
        .aggregate(RevenueAggregator(), DetailedWindowProcessFunction())
    )

    print(f"✅ Global windows created (trigger: {count_threshold} events)")
    return global_stream


@handle_errors
def create_multi_level_windows(stream):
    """
    Create multi-level windowing hierarchy.

    Args:
        stream: Input data stream

    Returns:
        Dictionary of multi-level window streams
    """
    print("\n🔄 Creating multi-level windowing hierarchy...")

    window_streams = {}

    # Level 1: Fine-grained (1-minute tumbling)
    minute_stream = (
        stream.key_by(lambda event: event["category"])
        .window(TumblingEventTimeWindows.of(FlinkTime.minutes(1)))
        .aggregate(RevenueAggregator())
    )

    window_streams["minute"] = minute_stream

    # Level 2: Medium-grained (5-minute tumbling)
    five_minute_stream = (
        stream.key_by(lambda event: event["category"])
        .window(TumblingEventTimeWindows.of(FlinkTime.minutes(5)))
        .aggregate(RevenueAggregator())
    )

    window_streams["five_minute"] = five_minute_stream

    # Level 3: Coarse-grained (15-minute tumbling)
    fifteen_minute_stream = (
        stream.key_by(lambda event: event["category"])
        .window(TumblingEventTimeWindows.of(FlinkTime.minutes(15)))
        .aggregate(RevenueAggregator())
    )

    window_streams["fifteen_minute"] = fifteen_minute_stream

    # Level 4: Hourly tumbling
    hourly_stream = (
        stream.key_by(lambda event: event["category"])
        .window(TumblingEventTimeWindows.of(FlinkTime.hours(1)))
        .aggregate(RevenueAggregator())
    )

    window_streams["hourly"] = hourly_stream

    print("✅ Multi-level windowing hierarchy created")
    return window_streams


@handle_errors
def create_pattern_detection_windows(stream):
    """
    Create windows for pattern detection and anomaly detection.

    Args:
        stream: Input data stream

    Returns:
        Pattern detection stream
    """
    print("\n🔄 Creating pattern detection windows...")

    # Pattern detection with sliding windows
    pattern_stream = (
        stream.key_by(lambda event: event["user_id"])
        .window(SlidingEventTimeWindows.of(FlinkTime.minutes(10), FlinkTime.minutes(2)))
        .process(PatternDetectionFunction())
    )

    print("✅ Pattern detection windows created")
    return pattern_stream


class PatternDetectionFunction(ProcessWindowFunction):
    """Detect interesting patterns in user behavior."""

    def process(self, key, context, elements, out):
        """
        Detect patterns in windowed events.

        Args:
            key: User ID
            context: Window context
            elements: Events in window
            out: Output collector
        """
        events = list(elements)
        if len(events) < 2:
            return

        window = context.window()
        user_id = key

        # Calculate various patterns
        patterns = []

        # 1. Rapid purchasing pattern
        purchase_events = [e for e in events if e["action"] == "purchase"]
        if len(purchase_events) >= 3:
            patterns.append(
                {
                    "type": "RAPID_PURCHASING",
                    "description": f"{len(purchase_events)} purchases in window",
                    "severity": "HIGH" if len(purchase_events) > 5 else "MEDIUM",
                }
            )

        # 2. High-value purchasing pattern
        total_spent = sum(e["total_amount"] for e in purchase_events)
        if total_spent > 1000:
            patterns.append(
                {
                    "type": "HIGH_VALUE_PURCHASING",
                    "description": f"${total_spent:.2f} spent in window",
                    "severity": "HIGH",
                }
            )

        # 3. Category switching pattern
        categories = [e["category"] for e in events]
        unique_categories = len(set(categories))
        if unique_categories >= 4:
            patterns.append(
                {
                    "type": "CATEGORY_SWITCHING",
                    "description": f"{unique_categories} different categories",
                    "severity": "MEDIUM",
                }
            )

        # 4. Abandoned cart pattern
        cart_adds = [e for e in events if e["action"] == "add_to_cart"]
        cart_removes = [e for e in events if e["action"] == "remove"]
        if len(cart_adds) > len(purchase_events) + len(cart_removes):
            patterns.append(
                {
                    "type": "ABANDONED_CART",
                    "description": f"{len(cart_adds) - len(purchase_events) - len(cart_removes)} items left in cart",
                    "severity": "LOW",
                }
            )

        # 5. Price sensitivity pattern
        view_events = [e for e in events if e["action"] == "view"]
        if len(view_events) > 10 and len(purchase_events) == 0:
            patterns.append(
                {
                    "type": "PRICE_SENSITIVE_BROWSING",
                    "description": f"{len(view_events)} views but no purchases",
                    "severity": "MEDIUM",
                }
            )

        # Emit patterns if any detected
        if patterns:
            pattern_result = {
                "user_id": user_id,
                "window_start": window.start,
                "window_end": window.end,
                "event_count": len(events),
                "patterns": patterns,
                "total_spent": total_spent,
                "unique_categories": unique_categories,
                "detected_at": context.current_processing_time(),
            }

            out.collect(pattern_result)
            metrics_tracker.increment("patterns_detected")


@handle_errors
def setup_window_outputs(window_streams: dict, kafka_servers: str, output_path: str):
    """
    Setup outputs for all window streams.

    Args:
        window_streams: Dictionary of window streams
        kafka_servers: Kafka bootstrap servers
        output_path: Base output path
    """
    print(f"\n🔄 Setting up window outputs to Kafka and {output_path}...")

    for window_type, stream in window_streams.items():
        # Console output for monitoring
        stream.print(f"{window_type.upper()}_WINDOW")

        # Kafka output
        kafka_topic = f"windowing-{window_type}"
        kafka_sink = create_kafka_sink(kafka_topic, kafka_servers)

        # Convert to JSON and send to Kafka
        stream.map(lambda result: json.dumps(result, default=str)).add_sink(kafka_sink)

        print(f"   {window_type} windows -> topic: {kafka_topic}")

    print("✅ Window outputs configured")


@handle_errors
def monitor_windowing_job(env: StreamExecutionEnvironment, duration: int):
    """
    Monitor windowing job execution.

    Args:
        env: StreamExecutionEnvironment
        duration: How long to monitor
    """
    print(f"\n📊 Monitoring windowing job for {duration} seconds...")

    start_time = time.time()
    end_time = start_time + duration

    # Start job
    job_result = env.execute_async("FlinkWindowingAggregations")

    # Setup signal handler
    def signal_handler(signum, frame):
        print("\n⚠️  Received interrupt signal, stopping job...")
        try:
            job_result.cancel()
        except:
            pass
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while time.time() < end_time and not job_result.is_done():
            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            print(f"\n⏱️  Elapsed: {elapsed:.0f}s | Remaining: {remaining:.0f}s")

            # Print metrics
            metrics = metrics_tracker.get_metrics()
            print(f"   Windows processed: {metrics.get('windows_processed', 0)}")
            print(f"   Sessions analyzed: {metrics.get('sessions_analyzed', 0)}")
            print(f"   Patterns detected: {metrics.get('patterns_detected', 0)}")

            if job_result.is_done():
                print("   Job Status: COMPLETED")
                break
            else:
                print("   Job Status: RUNNING")

            time.sleep(15)

    except KeyboardInterrupt:
        print("\n⚠️  Job monitoring interrupted")
        try:
            job_result.cancel()
        except:
            pass

    finally:
        if not job_result.is_done():
            print("\n🔄 Cancelling job...")
            try:
                job_result.cancel()
            except:
                pass

    print("✅ Windowing job monitoring completed")


@handle_errors
def main():
    """Main windowing aggregations workflow."""
    # Parse arguments
    parser = parse_common_args()
    parser.add_argument(
        "--window-types",
        default="tumbling,sliding,session",
        help="Comma-separated window types to create",
    )
    parser.add_argument(
        "--tumbling-minutes",
        type=int,
        default=2,
        help="Tumbling window size in minutes",
    )
    parser.add_argument(
        "--sliding-minutes", type=int, default=10, help="Sliding window size in minutes"
    )
    parser.add_argument(
        "--slide-minutes",
        type=int,
        default=2,
        help="Sliding window slide interval in minutes",
    )
    parser.add_argument(
        "--session-timeout", type=int, default=30, help="Session timeout in minutes"
    )
    parser.add_argument(
        "--custom-trigger-count",
        type=int,
        default=50,
        help="Event count for custom trigger",
    )
    args = parser.parse_args()

    print("🚀 Starting Flink Advanced Windowing and Aggregations")
    print(f"   Application: {args.app_name}")
    print(f"   Duration: {args.duration} seconds")
    print(f"   Window types: {args.window_types}")
    print(f"   Tumbling window: {args.tumbling_minutes} minutes")
    print(f"   Sliding window: {args.sliding_minutes}/{args.slide_minutes} minutes")
    print(f"   Session timeout: {args.session_timeout} minutes")

    # Create configuration
    config = FlinkConfig(
        app_name=f"{args.app_name}_WindowingAggregations",
        parallelism=args.parallelism,
        kafka_servers=args.kafka_servers,
    )

    # Create environment
    env = create_flink_environment(config)

    try:
        # Setup data source
        print("\n🔄 Setting up data source...")

        # Use sample data generator for consistent windowing examples
        sample_stream = generate_sample_streaming_data(
            env,
            rate_per_second=20,  # 20 events per second
            total_records=args.duration * 20,
        )

        # Parse events
        from streaming_analytics import EventParsingFunction

        parsed_stream = sample_stream.map(EventParsingFunction())

        # Set watermark strategy
        watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(
            Duration.of_seconds(30)
        ).with_timestamp_assigner(
            lambda event, ts: event.get(
                "event_time_ms", int(datetime.now().timestamp() * 1000)
            )
        )

        event_stream = parsed_stream.assign_timestamps_and_watermarks(
            watermark_strategy
        )

        # Create window streams based on requested types
        window_streams = {}
        window_types = args.window_types.split(",")

        if "tumbling" in window_types or "all" in window_types:
            tumbling_stream = create_tumbling_windows(
                event_stream, args.tumbling_minutes
            )
            window_streams["tumbling"] = tumbling_stream

        if "sliding" in window_types or "all" in window_types:
            sliding_stream = create_sliding_windows(
                event_stream, args.sliding_minutes, args.slide_minutes
            )
            window_streams["sliding"] = sliding_stream

        if "session" in window_types or "all" in window_types:
            session_stream = create_session_windows(event_stream, args.session_timeout)
            window_streams["session"] = session_stream

        if "global" in window_types or "all" in window_types:
            global_stream = create_global_windows_with_custom_trigger(
                event_stream, args.custom_trigger_count
            )
            window_streams["global"] = global_stream

        if "multi_level" in window_types or "all" in window_types:
            multi_level_streams = create_multi_level_windows(event_stream)
            window_streams.update(multi_level_streams)

        if "pattern" in window_types or "all" in window_types:
            pattern_stream = create_pattern_detection_windows(event_stream)
            window_streams["pattern"] = pattern_stream

        # Setup outputs
        setup_window_outputs(window_streams, config.kafka_servers, args.output_path)

        # Monitor job progress
        monitor_job_progress(env, "Advanced Windowing")

        print(f"\n📊 Created {len(window_streams)} window types:")
        for window_type in window_streams.keys():
            print(f"   - {window_type}")

        # Monitor job
        monitor_windowing_job(env, args.duration)

        # Print final metrics
        metrics_tracker.print_summary()

        print(f"\n✅ Windowing aggregations completed!")
        print(
            f"   Processed {len(window_streams)} window types for {args.duration} seconds"
        )
        print(f"   Results available in Kafka topics and console output")
        print(f"   Flink Web UI: http://192.168.1.184:8081")

    except KeyboardInterrupt:
        print("\n⚠️  Windowing aggregations interrupted by user")
    except Exception as e:
        print(f"\n❌ Windowing aggregations error: {e}")
        raise
    finally:
        cleanup_environment(env)


if __name__ == "__main__":
    main()
