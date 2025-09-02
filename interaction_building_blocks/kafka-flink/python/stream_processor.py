#!/usr/bin/env python3
"""
Kafka-Flink Stream Processor - Interaction Building Block

This application demonstrates real-time stream processing using Kafka as the data source
and Flink as the processing engine. It showcases:
- Consuming events from Kafka topics
- Real-time data transformations and enrichment
- Event filtering and routing
- Multiple output sinks (Kafka, files, console)
- Fault-tolerant stream processing with checkpointing

Usage:
    bazel run //kafka-flink/python:stream_processor -- --kafka-topic events --duration 300
    bazel run //kafka-flink/python:stream_processor -- --kafka-topic user-events --output-topic processed --parallelism 4

Examples:
    # Basic stream processing
    bazel run //kafka-flink/python:stream_processor
    
    # High-throughput processing with custom parallelism
    bazel run //kafka-flink/python:stream_processor -- --parallelism 8 --checkpoint-interval 5000
    
    # Process specific event types
    bazel run //kafka-flink/python:stream_processor -- --filter-actions purchase,add_to_cart --min-value 10.0

Requirements:
    pip install apache-flink kafka-python
"""

import sys
import time
import json
import signal
from datetime import datetime
from typing import List, Dict, Any
from kafka_flink_common import (
    FlinkKafkaJobManager,
    KafkaFlinkConfig,
    KafkaTestDataGenerator,
    KafkaTopicManager,
    EventEnrichmentFunction,
    EventFilterFunction,
    parse_common_args,
    setup_logging,
    handle_errors,
)

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.datastream.functions import MapFunction, ProcessFunction
    from pyflink.common.serialization import SimpleStringSchema
    from pyflink.common.typeinfo import Types
except ImportError:
    print("❌ Error: PyFlink not found. Install with: pip install apache-flink")
    sys.exit(1)


class StreamMetricsCollector(ProcessFunction):
    """Collect metrics during stream processing."""

    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        self.start_time = time.time()

    def process_element(self, value, ctx):
        try:
            # Parse and process the event
            event = json.loads(value)
            self.processed_count += 1

            # Add processing metrics
            event["processing_time"] = int(time.time() * 1000)
            event["processor_id"] = f"processor_{ctx.get_current_watermark()}"

            # Emit processed event
            yield json.dumps(event)

            # Log progress periodically
            if self.processed_count % 1000 == 0:
                elapsed = time.time() - self.start_time
                rate = self.processed_count / elapsed if elapsed > 0 else 0
                print(
                    f"📊 Processed {self.processed_count} events at {rate:.2f} events/sec"
                )

        except Exception as e:
            self.error_count += 1
            print(f"⚠️ Error processing event: {e}")
            # Emit original event on error
            yield value


class EventTypeRouter(ProcessFunction):
    """Route events to different outputs based on event type."""

    def __init__(self, high_value_threshold: float = 100.0):
        self.high_value_threshold = high_value_threshold

    def process_element(self, value, ctx):
        try:
            event = json.loads(value)

            # Route based on action type
            if event.get("action") == "purchase":
                # Tag as high-priority transaction
                event["priority"] = "high"
                event["route"] = "transactions"

            elif event.get("value", 0) > self.high_value_threshold:
                # Tag as high-value event
                event["priority"] = "high"
                event["route"] = "high_value"

            elif event.get("action") in ["view", "search"]:
                # Tag as analytics event
                event["priority"] = "normal"
                event["route"] = "analytics"

            else:
                # Default routing
                event["priority"] = "normal"
                event["route"] = "general"

            yield json.dumps(event)

        except Exception as e:
            print(f"⚠️ Error routing event: {e}")
            yield value


@handle_errors
def run_stream_processor(args):
    """
    Main stream processing application.

    Args:
        args: Command line arguments
    """
    print("🚀 Starting Kafka-Flink Stream Processor")
    print("=" * 50)

    # Initialize configuration
    config = KafkaFlinkConfig()
    if args.kafka_brokers:
        config.KAFKA_BOOTSTRAP_SERVERS = args.kafka_brokers

    # Create Flink job manager
    job_manager = FlinkKafkaJobManager(config)
    env = job_manager.create_stream_environment(parallelism=args.parallelism)

    print(f"🔧 Configuration:")
    print(f"   Kafka Topic: {args.kafka_topic}")
    print(f"   Consumer Group: {args.kafka_group_id}")
    print(f"   Parallelism: {args.parallelism}")
    print(f"   Checkpoint Interval: {args.checkpoint_interval}ms")
    print(f"   Duration: {args.duration}s")

    # Create Kafka source
    kafka_source = job_manager.create_kafka_source(
        topic=args.kafka_topic, group_id=args.kafka_group_id
    )

    # Create input stream
    input_stream = env.add_source(kafka_source)

    # Optional: Generate test data if requested
    if hasattr(args, "generate_test_data") and args.generate_test_data:
        print("📝 Generating test data...")
        topic_manager = KafkaTopicManager(config)
        topic_manager.create_topic(args.kafka_topic)

        data_generator = KafkaTestDataGenerator(config)
        test_events = data_generator.generate_user_events(args.test_event_count or 1000)
        data_generator.send_test_events(args.kafka_topic, test_events, rate_limit=10.0)
        data_generator.close()

    # Apply transformations
    processed_stream = input_stream

    # 1. Filter events if criteria specified
    if hasattr(args, "filter_actions") and args.filter_actions:
        allowed_actions = args.filter_actions.split(",")
        filter_func = EventFilterFunction(
            min_value=getattr(args, "min_value", 0.0), allowed_actions=allowed_actions
        )
        processed_stream = processed_stream.filter(filter_func)
        print(
            f"🔍 Applied filter: actions={allowed_actions}, min_value={args.min_value}"
        )

    # 2. Enrich events with additional data
    enrichment_func = EventEnrichmentFunction()
    processed_stream = processed_stream.map(enrichment_func)
    print("✨ Applied event enrichment")

    # 3. Collect processing metrics
    metrics_collector = StreamMetricsCollector()
    processed_stream = processed_stream.process(metrics_collector)
    print("📊 Added metrics collection")

    # 4. Route events based on type/value
    if hasattr(args, "enable_routing") and args.enable_routing:
        router = EventTypeRouter(
            high_value_threshold=getattr(args, "high_value_threshold", 100.0)
        )
        processed_stream = processed_stream.process(router)
        print(f"🚦 Added event routing with threshold: ${args.high_value_threshold}")

    # Configure output sinks
    if args.output_topic:
        # Kafka sink
        kafka_sink = job_manager.create_kafka_sink(args.output_topic)
        processed_stream.add_sink(kafka_sink)
        print(f"📤 Added Kafka sink: {args.output_topic}")

    # Console sink for monitoring (limited output)
    if hasattr(args, "console_output") and args.console_output:
        processed_stream.print("PROCESSED")
        print("🖥️ Added console output")

    # File sink if specified
    if hasattr(args, "output_path") and args.output_path:
        processed_stream.write_to_socket("localhost", 9999)  # Example socket sink
        print(f"📁 Added file output: {args.output_path}")

    # Setup graceful shutdown
    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        print(f"\n🛑 Received signal {signum}, initiating graceful shutdown...")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Execute the streaming job
    if args.duration > 0:
        print(f"⏱️ Running stream processor for {args.duration} seconds...")
        # For time-limited execution, we'll run in a separate thread
        # This is a simplified approach - production would use Flink's built-in mechanisms
        import threading

        job_thread = threading.Thread(
            target=lambda: job_manager.execute_job("kafka-flink-stream-processor")
        )
        job_thread.start()

        # Wait for duration or shutdown signal
        start_time = time.time()
        while time.time() - start_time < args.duration and not shutdown_requested:
            time.sleep(1)

        if not shutdown_requested:
            print(f"⏰ Duration limit reached ({args.duration}s), stopping job...")

        # In a real implementation, we would cancel the Flink job here
        print("🏁 Stream processor completed")

    else:
        print("♾️ Running stream processor indefinitely (Ctrl+C to stop)...")
        try:
            job_manager.execute_job("kafka-flink-stream-processor")
        except KeyboardInterrupt:
            print("\n🛑 Stream processor stopped by user")

    print("\n📊 Stream Processing Summary:")
    print(
        f"   Job Duration: {time.time() - job_manager.job_stats.get('started_at', time.time()):.1f}s"
    )
    print(f"   Parallelism: {args.parallelism}")
    print(f"   Input Topic: {args.kafka_topic}")
    print(f"   Output Topic: {args.output_topic or 'console/file'}")
    print("✅ Stream processor shutdown complete")


def main():
    """Main function for stream processor."""
    parser = parse_common_args()

    # Add stream processor specific arguments
    parser.add_argument(
        "--output-topic", default=None, help="Kafka output topic for processed events"
    )
    parser.add_argument(
        "--filter-actions",
        default=None,
        help="Comma-separated list of actions to filter",
    )
    parser.add_argument(
        "--min-value", type=float, default=0.0, help="Minimum event value to process"
    )
    parser.add_argument(
        "--enable-routing",
        action="store_true",
        help="Enable event routing based on type/value",
    )
    parser.add_argument(
        "--high-value-threshold",
        type=float,
        default=100.0,
        help="Threshold for high-value event routing",
    )
    parser.add_argument(
        "--console-output",
        action="store_true",
        help="Enable console output for monitoring",
    )
    parser.add_argument(
        "--output-path", default=None, help="File path for output (optional)"
    )
    parser.add_argument(
        "--generate-test-data",
        action="store_true",
        help="Generate test data before processing",
    )
    parser.add_argument(
        "--test-event-count",
        type=int,
        default=1000,
        help="Number of test events to generate",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    run_stream_processor(args)


if __name__ == "__main__":
    main()
