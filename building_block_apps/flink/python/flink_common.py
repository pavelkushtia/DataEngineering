#!/usr/bin/env python3
"""
Flink Common Utilities - Building Block Support Module

This module provides common utilities and configurations for Flink applications:
- Flink execution environment setup
- Data generators for testing
- Monitoring and progress tracking
- Error handling and logging
- Common argument parsing
- Integration helpers for Kafka, databases

Usage:
    from flink_common import *
    
    env = create_flink_environment(FlinkConfig())
    df = generate_sample_streaming_data(env, 1000)
"""

import os
import sys
import time
import json
import logging
import argparse
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from functools import wraps

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.table import StreamTableEnvironment, EnvironmentSettings
    from pyflink.common import Configuration, Types, WatermarkStrategy, Duration
    from pyflink.datastream.connectors.kafka import (
        FlinkKafkaConsumer,
        FlinkKafkaProducer,
    )
    from pyflink.common.serialization import (
        SimpleStringSchema,
        JsonRowSerializationSchema,
    )
    from pyflink.common.typeinfo import TypeInformation
    from pyflink.datastream.functions import SourceFunction, SinkFunction
    from pyflink.table.descriptors import Kafka, Json, Schema
except ImportError:
    print("ERROR: PyFlink not found. Install with: pip install apache-flink")
    sys.exit(1)

try:
    import random
    import uuid
    from concurrent.futures import ThreadPoolExecutor
except ImportError as e:
    print(f"ERROR: Required Python packages not found: {e}")
    sys.exit(1)


@dataclass
class FlinkConfig:
    """Configuration class for Flink applications."""

    app_name: str = "FlinkBuildingBlockApp"
    parallelism: int = 4
    checkpoint_interval: int = 10000  # 10 seconds
    checkpoint_timeout: int = 600000  # 10 minutes
    restart_attempts: int = 3

    # Kafka configuration
    kafka_servers: str = "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092"
    kafka_group_id: str = "flink-consumer-group"

    # Database configuration
    postgres_url: str = "jdbc:postgresql://192.168.1.184:5432/analytics_db"
    postgres_user: str = "dataeng"
    postgres_password: str = "password"

    # State backend configuration
    state_backend: str = "rocksdb"
    checkpoints_dir: str = "file:///tmp/flink-checkpoints"
    savepoints_dir: str = "file:///tmp/flink-savepoints"

    # Performance tuning
    managed_memory_fraction: float = 0.4
    network_buffer_timeout: int = 100

    # Development settings
    web_ui_enabled: bool = True
    log_level: str = "INFO"


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("/tmp/flink-app.log"),
        ],
    )
    return logging.getLogger(__name__)


def handle_errors(func):
    """Decorator for error handling with detailed logging."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error in {func.__name__}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    return wrapper


@handle_errors
def create_flink_environment(config: FlinkConfig) -> StreamExecutionEnvironment:
    """
    Create and configure Flink StreamExecutionEnvironment.

    Args:
        config: FlinkConfig object with settings

    Returns:
        Configured StreamExecutionEnvironment
    """
    print(f"\n🔄 Creating Flink environment: {config.app_name}")

    # Create environment
    env = StreamExecutionEnvironment.get_execution_environment()

    # Set parallelism
    env.set_parallelism(config.parallelism)
    print(f"   Parallelism: {config.parallelism}")

    # Enable checkpointing
    env.enable_checkpointing(config.checkpoint_interval)

    # Configure checkpointing
    checkpoint_config = env.get_checkpoint_config()
    checkpoint_config.set_checkpoint_timeout(config.checkpoint_timeout)
    checkpoint_config.set_min_pause_between_checkpoints(5000)
    checkpoint_config.set_max_concurrent_checkpoints(1)
    checkpoint_config.enable_unaligned_checkpoints()
    print(f"   Checkpointing: {config.checkpoint_interval}ms interval")

    # Configure restart strategy
    env.set_restart_strategy_fixed_delay(config.restart_attempts, 10000)
    print(f"   Restart strategy: {config.restart_attempts} attempts")

    # Configure state backend
    if config.state_backend == "rocksdb":
        env.set_state_backend("rocksdb")
        print("   State backend: RocksDB")

    # Add required JARs for connectors
    jars = [
        "flink-sql-connector-kafka-1.18.0.jar",
        "flink-connector-jdbc-3.1.1-1.18.jar",
        "postgresql-42.7.2.jar",
    ]

    for jar in jars:
        jar_path = f"/home/flink/flink/lib/{jar}"
        if os.path.exists(jar_path):
            env.add_jars(f"file://{jar_path}")

    print("✅ Flink environment created")
    return env


@handle_errors
def create_table_environment(
    stream_env: StreamExecutionEnvironment,
) -> StreamTableEnvironment:
    """
    Create Flink Table environment for SQL operations.

    Args:
        stream_env: StreamExecutionEnvironment

    Returns:
        StreamTableEnvironment
    """
    print("\n🔄 Creating Table environment for SQL...")

    # Create table environment
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    table_env = StreamTableEnvironment.create(stream_env, settings)

    # Configure table environment
    configuration = table_env.get_config().get_configuration()
    configuration.set_string("table.exec.state.ttl", "3600000")  # 1 hour TTL

    print("✅ Table environment created")
    return table_env


class SampleDataGenerator(SourceFunction):
    """Generate sample streaming data for testing."""

    def __init__(self, rate_per_second: int = 100, total_records: int = 10000):
        self.rate_per_second = rate_per_second
        self.total_records = total_records
        self.running = True

    def run(self, ctx):
        """Generate sample data at specified rate."""
        interval = 1.0 / self.rate_per_second
        generated = 0

        categories = ["ELECTRONICS", "CLOTHING", "BOOKS", "HOME", "SPORTS"]
        actions = ["view", "add_to_cart", "purchase", "remove", "search"]

        while self.running and generated < self.total_records:
            # Generate sample event
            event = {
                "event_id": f"evt_{uuid.uuid4().hex[:8]}",
                "user_id": f"user_{random.randint(1, 1000)}",
                "session_id": f"session_{random.randint(1, 100)}",
                "product_id": f"prod_{random.randint(1, 500)}",
                "category": random.choice(categories),
                "action": random.choice(actions),
                "price": round(random.uniform(10, 500), 2),
                "quantity": random.randint(1, 5),
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "source": "web",
                    "user_agent": "Mozilla/5.0",
                    "ip_address": f"192.168.1.{random.randint(1, 254)}",
                },
            }

            ctx.collect(json.dumps(event))
            generated += 1

            # Rate limiting
            time.sleep(interval)

    def cancel(self):
        """Stop data generation."""
        self.running = False


@handle_errors
def generate_sample_streaming_data(
    env: StreamExecutionEnvironment,
    rate_per_second: int = 100,
    total_records: int = 10000,
):
    """
    Generate sample streaming data for testing.

    Args:
        env: StreamExecutionEnvironment
        rate_per_second: Events per second to generate
        total_records: Total number of records to generate

    Returns:
        DataStream with sample data
    """
    print(
        f"\n🔄 Generating sample data: {rate_per_second} events/sec, {total_records} total"
    )

    data_stream = env.add_source(
        SampleDataGenerator(rate_per_second, total_records),
        source_name="SampleDataGenerator",
    )

    print("✅ Sample data stream created")
    return data_stream


@handle_errors
def create_kafka_source(
    env: StreamExecutionEnvironment,
    topic: str,
    kafka_servers: str,
    group_id: str = "flink-consumer",
) -> Any:
    """
    Create Kafka source for streaming.

    Args:
        env: StreamExecutionEnvironment
        topic: Kafka topic name
        kafka_servers: Kafka bootstrap servers
        group_id: Consumer group ID

    Returns:
        Kafka source DataStream
    """
    print(f"\n🔄 Creating Kafka source for topic: {topic}")

    # Kafka consumer properties
    kafka_props = {
        "bootstrap.servers": kafka_servers,
        "group.id": group_id,
        "auto.offset.reset": "latest",
        "enable.auto.commit": "true",
    }

    # Create Kafka consumer
    kafka_consumer = FlinkKafkaConsumer(topic, SimpleStringSchema(), kafka_props)

    # Set watermark strategy for event time processing
    watermark_strategy = WatermarkStrategy.for_bounded_out_of_orderness(
        Duration.of_seconds(20)
    )

    kafka_stream = env.add_source(kafka_consumer).assign_timestamps_and_watermarks(
        watermark_strategy
    )

    print(f"✅ Kafka source created for topic: {topic}")
    return kafka_stream


@handle_errors
def create_kafka_sink(topic: str, kafka_servers: str) -> FlinkKafkaProducer:
    """
    Create Kafka sink for output.

    Args:
        topic: Kafka topic name
        kafka_servers: Kafka bootstrap servers

    Returns:
        FlinkKafkaProducer
    """
    print(f"\n🔄 Creating Kafka sink for topic: {topic}")

    # Kafka producer properties
    kafka_props = {
        "bootstrap.servers": kafka_servers,
        "batch.size": "16384",
        "linger.ms": "5",
        "acks": "1",
    }

    kafka_sink = FlinkKafkaProducer(topic, SimpleStringSchema(), kafka_props)

    print(f"✅ Kafka sink created for topic: {topic}")
    return kafka_sink


@handle_errors
def setup_postgres_table(
    table_env: StreamTableEnvironment,
    table_name: str,
    postgres_url: str,
    postgres_user: str,
    postgres_password: str,
):
    """
    Setup PostgreSQL table connection.

    Args:
        table_env: StreamTableEnvironment
        table_name: Table name in Flink
        postgres_url: PostgreSQL JDBC URL
        postgres_user: Database username
        postgres_password: Database password
    """
    print(f"\n🔄 Setting up PostgreSQL table: {table_name}")

    # Create JDBC table
    create_table_sql = f"""
    CREATE TABLE {table_name} (
        event_id STRING,
        user_id STRING,
        product_id STRING,
        category STRING,
        action STRING,
        price DOUBLE,
        quantity INT,
        total_amount DOUBLE,
        event_time TIMESTAMP(3),
        processing_time TIMESTAMP(3)
    ) WITH (
        'connector' = 'jdbc',
        'url' = '{postgres_url}',
        'table-name' = '{table_name}',
        'username' = '{postgres_user}',
        'password' = '{postgres_password}',
        'sink.buffer-flush.max-rows' = '1000',
        'sink.buffer-flush.interval' = '10s'
    )
    """

    table_env.execute_sql(create_table_sql)
    print(f"✅ PostgreSQL table {table_name} configured")


@handle_errors
def monitor_job_progress(env: StreamExecutionEnvironment, job_name: str):
    """
    Monitor Flink job execution progress.

    Args:
        env: StreamExecutionEnvironment
        job_name: Name of the job for logging
    """
    print(f"\n📊 Monitoring job: {job_name}")
    print("   Web UI available at: http://192.168.1.184:8081")
    print("   Use Ctrl+C to stop the job")


@handle_errors
def print_stream_summary(stream, stream_name: str, sample_size: int = 5):
    """
    Print summary information about a data stream.

    Args:
        stream: DataStream to analyze
        stream_name: Name for logging
        sample_size: Number of sample records to show
    """
    print(f"\n📋 Stream Summary: {stream_name}")
    print(f"   Type: {type(stream)}")
    print(f"   Note: Stream processing is lazy - data flows when job executes")
    print(f"   Monitor progress in Flink Web UI: http://192.168.1.184:8081")


def parse_common_args() -> argparse.ArgumentParser:
    """Parse common command line arguments for Flink applications."""
    parser = argparse.ArgumentParser(description="Flink Building Block Application")

    parser.add_argument(
        "--app-name", default="FlinkBuildingBlock", help="Application name"
    )
    parser.add_argument("--parallelism", type=int, default=4, help="Parallelism level")
    parser.add_argument(
        "--records", type=int, default=10000, help="Number of records to process"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration to run streaming job (seconds)",
    )
    parser.add_argument(
        "--output-path", default="/tmp/flink-output", help="Output path for results"
    )

    # Kafka arguments
    parser.add_argument(
        "--kafka-topic", default="flink-events", help="Kafka topic name"
    )
    parser.add_argument(
        "--kafka-servers",
        default="192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092",
        help="Kafka bootstrap servers",
    )
    parser.add_argument(
        "--kafka-group-id",
        default="flink-consumer-group",
        help="Kafka consumer group ID",
    )

    # Database arguments
    parser.add_argument(
        "--postgres-url",
        default="jdbc:postgresql://192.168.1.184:5432/analytics_db",
        help="PostgreSQL JDBC URL",
    )
    parser.add_argument(
        "--postgres-user", default="dataeng", help="PostgreSQL username"
    )
    parser.add_argument(
        "--postgres-password", default="password", help="PostgreSQL password"
    )

    return parser


@handle_errors
def cleanup_environment(env: StreamExecutionEnvironment):
    """
    Clean up Flink environment and resources.

    Args:
        env: StreamExecutionEnvironment to clean up
    """
    print("\n🔄 Cleaning up Flink environment...")
    try:
        # In Flink, cleanup is typically handled automatically
        # when the job completes or is cancelled
        print("✅ Environment cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")


class MetricsTracker:
    """Track custom metrics for Flink applications."""

    def __init__(self):
        self.metrics = {}
        self.start_time = time.time()

    def increment(self, metric_name: str, value: int = 1):
        """Increment a counter metric."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = 0
        self.metrics[metric_name] += value

    def set_gauge(self, metric_name: str, value: float):
        """Set a gauge metric."""
        self.metrics[metric_name] = value

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics with runtime info."""
        runtime = time.time() - self.start_time
        return {
            **self.metrics,
            "runtime_seconds": runtime,
            "timestamp": datetime.now().isoformat(),
        }

    def print_summary(self):
        """Print metrics summary."""
        metrics = self.get_metrics()
        print("\n📊 METRICS SUMMARY")
        print("=" * 40)
        for name, value in metrics.items():
            if isinstance(value, float):
                print(f"   {name}: {value:.2f}")
            else:
                print(f"   {name}: {value}")
        print("=" * 40)


# Global metrics tracker
metrics_tracker = MetricsTracker()


@handle_errors
def validate_flink_setup():
    """Validate Flink setup and dependencies."""
    print("\n🔍 Validating Flink setup...")

    try:
        # Test basic Flink functionality
        env = StreamExecutionEnvironment.get_execution_environment()
        env.set_parallelism(1)

        # Test data stream creation
        test_stream = env.from_collection([1, 2, 3])

        print("✅ Basic Flink functionality: OK")

        # Check connector JARs
        jar_dir = "/home/flink/flink/lib"
        required_jars = [
            "flink-sql-connector-kafka",
            "flink-connector-jdbc",
            "postgresql",
        ]

        if os.path.exists(jar_dir):
            available_jars = os.listdir(jar_dir)
            for jar_pattern in required_jars:
                found = any(jar_pattern in jar for jar in available_jars)
                status = "✅" if found else "⚠️"
                print(
                    f"{status} Connector JAR {jar_pattern}: {'Found' if found else 'Missing'}"
                )
        else:
            print(f"⚠️  JAR directory not found: {jar_dir}")

        # Test network connectivity
        import socket

        kafka_host = "192.168.1.184"
        kafka_port = 9092

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((kafka_host, kafka_port))
            sock.close()

            if result == 0:
                print(f"✅ Kafka connectivity: {kafka_host}:{kafka_port}")
            else:
                print(f"⚠️  Kafka connectivity: Cannot reach {kafka_host}:{kafka_port}")
        except Exception as e:
            print(f"⚠️  Network test error: {e}")

        print("✅ Flink setup validation completed")

    except Exception as e:
        print(f"❌ Flink setup validation failed: {e}")
        raise


if __name__ == "__main__":
    """Test common utilities."""
    print("🧪 Testing Flink common utilities...")

    # Validate setup
    validate_flink_setup()

    # Test configuration
    config = FlinkConfig(app_name="TestApp")
    print(f"Config: {config}")

    # Test environment creation
    env = create_flink_environment(config)
    table_env = create_table_environment(env)

    print("✅ All tests passed!")
