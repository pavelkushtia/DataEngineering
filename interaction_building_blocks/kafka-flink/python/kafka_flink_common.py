#!/usr/bin/env python3
"""
Kafka-Flink Interaction Common Utilities

This module provides common utilities for Kafka-Flink integration examples:
- Flink environment setup with Kafka connectors
- Kafka source and sink configuration
- Stream processing utilities and monitoring
- Error handling and performance tracking
- Data serialization helpers for Kafka-Flink pipelines

Requirements:
    pip install apache-flink kafka-python
"""

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import argparse
import logging

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.table import StreamTableEnvironment
    from pyflink.common import WatermarkStrategy, Types, Duration
    from pyflink.datastream.connectors.kafka import (
        FlinkKafkaConsumer,
        FlinkKafkaProducer,
    )
    from pyflink.common.serialization import (
        SimpleStringSchema,
        JsonRowSerializationSchema,
        JsonRowDeserializationSchema,
    )
    from pyflink.datastream.window import (
        TumblingEventTimeWindows,
        SlidingEventTimeWindows,
        SessionWindows,
    )
    from pyflink.common.time import Time as FlinkTime
    from pyflink.datastream.functions import (
        MapFunction,
        FilterFunction,
        KeyedProcessFunction,
        ProcessWindowFunction,
    )
    from pyflink.common.state import ValueStateDescriptor, ListStateDescriptor
    from pyflink.common.typeinfo import TypeInformation
except ImportError:
    print("❌ Error: PyFlink library not found!")
    print("📦 Install with: pip install apache-flink")
    sys.exit(1)

try:
    from kafka import KafkaProducer, KafkaConsumer
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError
except ImportError:
    print("❌ Error: kafka-python library not found!")
    print("📦 Install with: pip install kafka-python")
    sys.exit(1)


class KafkaFlinkConfig:
    """Configuration for Kafka-Flink integration."""

    # Kafka cluster configuration
    KAFKA_BROKERS = ["192.168.1.184:9092", "192.168.1.187:9092", "192.168.1.190:9092"]
    KAFKA_BOOTSTRAP_SERVERS = ",".join(KAFKA_BROKERS)

    # Flink cluster configuration
    FLINK_JOBMANAGER_HOST = "192.168.1.184"
    FLINK_JOBMANAGER_PORT = 6123
    FLINK_WEB_UI_PORT = 8081

    # Default processing settings
    DEFAULT_PARALLELISM = 2
    CHECKPOINT_INTERVAL = 10000  # 10 seconds

    # Kafka connector settings
    KAFKA_GROUP_ID_PREFIX = "flink-consumer"
    KAFKA_AUTO_OFFSET_RESET = "latest"

    # Common topics
    DEFAULT_INPUT_TOPIC = "events"
    DEFAULT_OUTPUT_TOPIC = "processed-events"


class FlinkKafkaJobManager:
    """Manager for Flink jobs that process Kafka streams."""

    def __init__(self, config: KafkaFlinkConfig = None):
        self.config = config or KafkaFlinkConfig()
        self.env = None
        self.table_env = None
        self.job_stats = {"started_at": None, "processed_records": 0, "errors": 0}

    def create_stream_environment(
        self, parallelism: int = None
    ) -> StreamExecutionEnvironment:
        """Create and configure Flink streaming environment."""
        parallelism = parallelism or self.config.DEFAULT_PARALLELISM

        # Create stream environment
        self.env = StreamExecutionEnvironment.get_execution_environment()
        self.env.set_parallelism(parallelism)

        # Configure checkpointing for fault tolerance
        self.env.enable_checkpointing(self.config.CHECKPOINT_INTERVAL)

        # Add Kafka connector JAR (this would need to be properly configured in production)
        print(f"🚀 Created Flink stream environment with parallelism: {parallelism}")
        print(
            f"✅ Checkpointing enabled with interval: {self.config.CHECKPOINT_INTERVAL}ms"
        )

        return self.env

    def create_table_environment(self) -> StreamTableEnvironment:
        """Create Flink table environment for SQL operations."""
        if not self.env:
            self.create_stream_environment()

        self.table_env = StreamTableEnvironment.create(self.env)

        print("🗃️ Created Flink table environment")
        return self.table_env

    def create_kafka_source(
        self, topic: str, group_id: str = None, value_schema=None
    ) -> FlinkKafkaConsumer:
        """Create Kafka source for Flink streaming."""
        group_id = group_id or f"{self.config.KAFKA_GROUP_ID_PREFIX}-{int(time.time())}"
        value_schema = value_schema or SimpleStringSchema()

        properties = {
            "bootstrap.servers": self.config.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": group_id,
            "auto.offset.reset": self.config.KAFKA_AUTO_OFFSET_RESET,
        }

        kafka_source = FlinkKafkaConsumer(
            topics=topic, deserialization_schema=value_schema, properties=properties
        )

        # Configure watermark strategy for event time processing
        watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(
            Duration.of_seconds(5)
        )
        kafka_source.assign_timestamps_and_watermarks(watermark_strategy)

        print(f"📥 Created Kafka source: topic={topic}, group_id={group_id}")
        return kafka_source

    def create_kafka_sink(self, topic: str, value_schema=None) -> FlinkKafkaProducer:
        """Create Kafka sink for Flink streaming."""
        value_schema = value_schema or SimpleStringSchema()

        properties = {
            "bootstrap.servers": self.config.KAFKA_BOOTSTRAP_SERVERS,
            "transaction.timeout.ms": "900000",  # 15 minutes
        }

        kafka_sink = FlinkKafkaProducer(
            topic=topic, serialization_schema=value_schema, producer_config=properties
        )

        print(f"📤 Created Kafka sink: topic={topic}")
        return kafka_sink

    def execute_job(self, job_name: str):
        """Execute the Flink job."""
        if not self.env:
            raise ValueError(
                "Stream environment not created. Call create_stream_environment() first."
            )

        self.job_stats["started_at"] = datetime.now()
        print(f"🎯 Executing Flink job: {job_name}")

        try:
            # Execute the job (this will block until job completes or is cancelled)
            self.env.execute(job_name)
            print(f"✅ Flink job '{job_name}' completed successfully")

        except Exception as e:
            print(f"❌ Flink job '{job_name}' failed: {e}")
            self.job_stats["errors"] += 1
            raise


class KafkaTestDataGenerator:
    """Generate test data for Kafka topics."""

    def __init__(self, config: KafkaFlinkConfig = None):
        self.config = config or KafkaFlinkConfig()
        self.producer = None

    def create_producer(self) -> KafkaProducer:
        """Create Kafka producer for sending test data."""
        self.producer = KafkaProducer(
            bootstrap_servers=self.config.KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda v: str(v).encode("utf-8") if v else None,
        )

        print(f"📤 Created Kafka producer for test data generation")
        return self.producer

    def generate_user_events(self, count: int = 100, topic: str = None) -> List[Dict]:
        """Generate sample user event data."""
        topic = topic or self.config.DEFAULT_INPUT_TOPIC
        events = []

        import random

        actions = [
            "view",
            "click",
            "purchase",
            "add_to_cart",
            "remove_from_cart",
            "search",
        ]
        products = ["laptop", "phone", "tablet", "headphones", "mouse", "keyboard"]

        for i in range(count):
            event = {
                "event_id": f"evt_{i:06d}",
                "user_id": f"user_{random.randint(1, 1000):04d}",
                "action": random.choice(actions),
                "product": random.choice(products),
                "timestamp": int(time.time() * 1000)
                + i * 100,  # Spread events over time
                "value": round(random.uniform(10.0, 500.0), 2),
                "session_id": f"sess_{random.randint(1, 100):03d}",
                "metadata": {"source": "kafka_flink_test", "version": "1.0"},
            }
            events.append(event)

        return events

    def send_test_events(
        self, topic: str, events: List[Dict], rate_limit: float = 10.0
    ):
        """Send test events to Kafka topic."""
        if not self.producer:
            self.create_producer()

        print(
            f"📨 Sending {len(events)} events to topic '{topic}' at {rate_limit} msgs/sec"
        )

        delay = 1.0 / rate_limit if rate_limit > 0 else 0
        sent_count = 0

        try:
            for event in events:
                # Use user_id as partition key for consistent partitioning
                key = event.get("user_id")

                future = self.producer.send(topic, key=key, value=event)

                # Optional: wait for confirmation
                try:
                    record_metadata = future.get(timeout=1)
                    sent_count += 1
                except Exception as e:
                    print(f"⚠️ Failed to send event {event['event_id']}: {e}")

                if delay > 0:
                    time.sleep(delay)

        finally:
            self.producer.flush()
            print(f"✅ Sent {sent_count}/{len(events)} events successfully")

    def close(self):
        """Close the Kafka producer."""
        if self.producer:
            self.producer.close()


class KafkaTopicManager:
    """Manage Kafka topics for integration tests."""

    def __init__(self, config: KafkaFlinkConfig = None):
        self.config = config or KafkaFlinkConfig()
        self.admin_client = None

    def create_admin_client(self) -> KafkaAdminClient:
        """Create Kafka admin client."""
        self.admin_client = KafkaAdminClient(
            bootstrap_servers=self.config.KAFKA_BROKERS, client_id="flink-kafka-admin"
        )
        return self.admin_client

    def create_topic(
        self, topic_name: str, num_partitions: int = 3, replication_factor: int = 2
    ):
        """Create a Kafka topic."""
        if not self.admin_client:
            self.create_admin_client()

        topic = NewTopic(
            name=topic_name,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
        )

        try:
            self.admin_client.create_topics([topic])
            print(f"✅ Created topic '{topic_name}' with {num_partitions} partitions")
        except TopicAlreadyExistsError:
            print(f"📋 Topic '{topic_name}' already exists")
        except Exception as e:
            print(f"❌ Failed to create topic '{topic_name}': {e}")


def create_sample_event_data(count: int = 100) -> List[Dict]:
    """Create sample event data for testing."""
    generator = KafkaTestDataGenerator()
    return generator.generate_user_events(count)


def parse_common_args() -> argparse.ArgumentParser:
    """Create argument parser with common Kafka-Flink options."""
    parser = argparse.ArgumentParser(description="Kafka-Flink Interaction Application")

    parser.add_argument(
        "--kafka-brokers",
        default=KafkaFlinkConfig.KAFKA_BOOTSTRAP_SERVERS,
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--kafka-topic",
        default=KafkaFlinkConfig.DEFAULT_INPUT_TOPIC,
        help="Kafka input topic",
    )
    parser.add_argument(
        "--kafka-group-id",
        default=f"{KafkaFlinkConfig.KAFKA_GROUP_ID_PREFIX}-{int(time.time())}",
        help="Kafka consumer group ID",
    )
    parser.add_argument(
        "--output-topic",
        default=KafkaFlinkConfig.DEFAULT_OUTPUT_TOPIC,
        help="Kafka output topic",
    )

    parser.add_argument(
        "--parallelism",
        type=int,
        default=KafkaFlinkConfig.DEFAULT_PARALLELISM,
        help="Flink job parallelism",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=KafkaFlinkConfig.CHECKPOINT_INTERVAL,
        help="Checkpoint interval in milliseconds",
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Job duration in seconds (0 for infinite)",
    )
    parser.add_argument(
        "--window-size", type=int, default=60, help="Window size in seconds"
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    return parser


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def handle_errors(func):
    """Decorator for handling common errors."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n🛑 Operation interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if hasattr(e, "__traceback__"):
                import traceback

                traceback.print_exc()
            sys.exit(1)

    return wrapper


# Sample transformation functions for Flink processing


class EventEnrichmentFunction(MapFunction):
    """Enrich incoming events with additional metadata."""

    def map(self, value):
        try:
            event = json.loads(value)

            # Add enrichment data
            event["processed_at"] = int(time.time() * 1000)
            event["enriched"] = True

            # Add derived fields
            if "action" in event:
                event["category"] = self.get_action_category(event["action"])

            if "value" in event:
                event["value_tier"] = self.get_value_tier(event["value"])

            return json.dumps(event)

        except Exception as e:
            print(f"⚠️ Error enriching event: {e}")
            return value

    def get_action_category(self, action: str) -> str:
        """Categorize user actions."""
        if action in ["view", "search"]:
            return "browse"
        elif action in ["add_to_cart", "remove_from_cart"]:
            return "cart"
        elif action in ["purchase"]:
            return "transaction"
        else:
            return "other"

    def get_value_tier(self, value: float) -> str:
        """Categorize event values into tiers."""
        if value < 50:
            return "low"
        elif value < 200:
            return "medium"
        else:
            return "high"


class EventFilterFunction(FilterFunction):
    """Filter events based on criteria."""

    def __init__(self, min_value: float = 0.0, allowed_actions: List[str] = None):
        self.min_value = min_value
        self.allowed_actions = allowed_actions or []

    def filter(self, value):
        try:
            event = json.loads(value)

            # Filter by value
            if "value" in event and event["value"] < self.min_value:
                return False

            # Filter by action
            if (
                self.allowed_actions
                and "action" in event
                and event["action"] not in self.allowed_actions
            ):
                return False

            return True

        except Exception as e:
            print(f"⚠️ Error filtering event: {e}")
            return True  # Pass through on error


if __name__ == "__main__":
    # Test the common utilities
    print("🧪 Testing Kafka-Flink common utilities...")

    try:
        # Test configuration
        config = KafkaFlinkConfig()
        print(f"✅ Kafka brokers: {config.KAFKA_BOOTSTRAP_SERVERS}")
        print(
            f"✅ Flink JobManager: {config.FLINK_JOBMANAGER_HOST}:{config.FLINK_JOBMANAGER_PORT}"
        )

        # Test data generation
        generator = KafkaTestDataGenerator(config)
        sample_events = generator.generate_user_events(5)
        print(f"✅ Generated {len(sample_events)} sample events")
        for event in sample_events:
            print(
                f"   Event: {event['event_id']} - {event['action']} - ${event['value']}"
            )

        # Test Flink environment creation
        job_manager = FlinkKafkaJobManager(config)
        env = job_manager.create_stream_environment()
        print(f"✅ Created Flink environment with parallelism: {env.get_parallelism()}")

        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
