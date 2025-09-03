#!/usr/bin/env python3
"""
Kafka-Cassandra Interaction Common Utilities

This module provides common utilities for Kafka-Cassandra stream processing integration:
- Real-time event streaming from Kafka to Cassandra
- Time-series data ingestion patterns
- Event sourcing and CQRS patterns
- High-throughput data ingestion optimization
- Connection pooling for both Kafka and Cassandra
- Error handling and replay mechanisms

Requirements:
    pip install kafka-python cassandra-driver
"""

import sys
import time
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

try:
    from kafka import KafkaConsumer, KafkaProducer
    from kafka.errors import KafkaError
except ImportError:
    print("❌ Error: kafka-python library not found!")
    print("📦 Install with: pip install kafka-python")
    sys.exit(1)

try:
    from cassandra.cluster import Cluster, Session
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.policies import DCAwareRoundRobinPolicy
    from cassandra.query import PreparedStatement, BatchStatement, BatchType
    from cassandra import InvalidRequest, WriteTimeout
except ImportError:
    print("❌ Error: cassandra-driver library not found!")
    print("📦 Install with: pip install cassandra-driver")
    sys.exit(1)


class KafkaCassandraConfig:
    """Configuration for Kafka-Cassandra stream processing integration."""

    # Kafka configuration
    KAFKA_BROKERS = ["192.168.1.184:9092", "192.168.1.187:9092", "192.168.1.190:9092"]
    KAFKA_CONSUMER_GROUP = "cassandra-stream-processor"
    KAFKA_AUTO_OFFSET_RESET = "latest"
    KAFKA_ENABLE_AUTO_COMMIT = False
    KAFKA_MAX_POLL_RECORDS = 500

    # Cassandra configuration
    CASSANDRA_HOSTS = ["192.168.1.184", "192.168.1.187", "192.168.1.190"]
    CASSANDRA_PORT = 9042
    CASSANDRA_KEYSPACE = "streaming_analytics"
    CASSANDRA_USERNAME = None
    CASSANDRA_PASSWORD = None

    # Stream processing configuration
    BATCH_SIZE = 100
    BATCH_TIMEOUT_MS = 5000
    MAX_CONCURRENT_BATCHES = 10
    RETRY_ATTEMPTS = 3
    RETRY_BACKOFF_MS = 1000

    # Performance settings
    CONSUMER_TIMEOUT_MS = 30000
    PRODUCER_RETRIES = 3
    PRODUCER_BATCH_SIZE = 16384


class KafkaStreamConsumer:
    """Kafka consumer optimized for streaming to Cassandra."""

    def __init__(self, config: KafkaCassandraConfig = None):
        self.config = config or KafkaCassandraConfig()
        self.consumer = None
        self.stats = {
            "messages_consumed": 0,
            "messages_processed": 0,
            "batches_processed": 0,
            "errors": 0,
            "processing_time": 0.0
        }

    def create_consumer(self, topics: List[str]) -> KafkaConsumer:
        """Create Kafka consumer for streaming data."""
        try:
            self.consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.config.KAFKA_BROKERS,
                group_id=self.config.KAFKA_CONSUMER_GROUP,
                auto_offset_reset=self.config.KAFKA_AUTO_OFFSET_RESET,
                enable_auto_commit=self.config.KAFKA_ENABLE_AUTO_COMMIT,
                max_poll_records=self.config.KAFKA_MAX_POLL_RECORDS,
                consumer_timeout_ms=self.config.CONSUMER_TIMEOUT_MS,
                value_deserializer=lambda x: json.loads(x.decode('utf-8')),
                key_deserializer=lambda x: x.decode('utf-8') if x else None
            )

            print(f"🔌 Connected to Kafka: {', '.join(self.config.KAFKA_BROKERS)}")
            print(f"📡 Subscribed to topics: {topics}")
            print(f"👥 Consumer group: {self.config.KAFKA_CONSUMER_GROUP}")

            return self.consumer

        except Exception as e:
            print(f"❌ Failed to create Kafka consumer: {e}")
            raise

    def consume_messages(self, batch_processor: Callable, max_messages: int = None):
        """
        Consume messages in batches and process them.

        Args:
            batch_processor: Function to process message batches
            max_messages: Maximum messages to consume (None for unlimited)
        """
        if not self.consumer:
            raise ValueError("Consumer not initialized. Call create_consumer() first.")

        messages_processed = 0
        current_batch = []
        batch_start_time = time.time()

        print(f"🚀 Starting message consumption...")
        print(f"📦 Batch size: {self.config.BATCH_SIZE}")

        try:
            for message in self.consumer:
                self.stats["messages_consumed"] += 1
                
                # Add message to current batch
                current_batch.append({
                    'topic': message.topic,
                    'partition': message.partition,
                    'offset': message.offset,
                    'key': message.key,
                    'value': message.value,
                    'timestamp': message.timestamp,
                    'timestamp_type': message.timestamp_type
                })

                # Process batch when it reaches target size or timeout
                should_process_batch = (
                    len(current_batch) >= self.config.BATCH_SIZE or
                    (time.time() - batch_start_time) * 1000 >= self.config.BATCH_TIMEOUT_MS
                )

                if should_process_batch and current_batch:
                    success = self._process_batch_with_retry(current_batch, batch_processor)
                    
                    if success:
                        # Commit offsets after successful processing
                        self.consumer.commit()
                        self.stats["batches_processed"] += 1
                        messages_processed += len(current_batch)
                        
                        print(f"✅ Processed batch: {len(current_batch)} messages (Total: {messages_processed})")
                    
                    # Reset batch
                    current_batch = []
                    batch_start_time = time.time()

                # Check if we've reached the message limit
                if max_messages and messages_processed >= max_messages:
                    break

            # Process remaining messages in final batch
            if current_batch:
                success = self._process_batch_with_retry(current_batch, batch_processor)
                if success:
                    self.consumer.commit()
                    messages_processed += len(current_batch)

        except KeyboardInterrupt:
            print("\n🛑 Consumption interrupted by user")
        except Exception as e:
            print(f"❌ Error during message consumption: {e}")
            self.stats["errors"] += 1
            raise
        finally:
            print(f"📊 Final stats: {messages_processed} messages processed")

    def _process_batch_with_retry(self, batch: List[Dict], processor: Callable) -> bool:
        """Process batch with retry logic."""
        for attempt in range(self.config.RETRY_ATTEMPTS):
            try:
                start_time = time.time()
                processor(batch)
                
                processing_time = time.time() - start_time
                self.stats["processing_time"] += processing_time
                self.stats["messages_processed"] += len(batch)
                
                return True

            except Exception as e:
                self.stats["errors"] += 1
                print(f"⚠️ Batch processing failed (attempt {attempt + 1}/{self.config.RETRY_ATTEMPTS}): {e}")
                
                if attempt < self.config.RETRY_ATTEMPTS - 1:
                    time.sleep(self.config.RETRY_BACKOFF_MS / 1000.0)
                else:
                    print(f"❌ Failed to process batch after {self.config.RETRY_ATTEMPTS} attempts")

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        avg_processing_time = (
            self.stats["processing_time"] / max(self.stats["batches_processed"], 1)
        )
        
        return {
            **self.stats,
            "avg_batch_processing_time": f"{avg_processing_time:.3f}s",
            "throughput_msg_per_sec": self.stats["messages_processed"] / max(self.stats["processing_time"], 1)
        }

    def close(self):
        """Close Kafka consumer."""
        if self.consumer:
            self.consumer.close()
            print("🔌 Kafka consumer closed")


class CassandraStreamSink:
    """Cassandra sink optimized for high-throughput streaming data."""

    def __init__(self, config: KafkaCassandraConfig = None):
        self.config = config or KafkaCassandraConfig()
        self.cluster = None
        self.session = None
        self.prepared_statements = {}
        self.stats = {
            "inserts": 0,
            "batches": 0,
            "errors": 0,
            "insert_time": 0.0
        }

    def create_session(self) -> Session:
        """Create Cassandra session for streaming data."""
        try:
            # Configure authentication if needed
            auth_provider = None
            if self.config.CASSANDRA_USERNAME and self.config.CASSANDRA_PASSWORD:
                auth_provider = PlainTextAuthProvider(
                    username=self.config.CASSANDRA_USERNAME,
                    password=self.config.CASSANDRA_PASSWORD
                )

            # Create cluster
            self.cluster = Cluster(
                contact_points=self.config.CASSANDRA_HOSTS,
                port=self.config.CASSANDRA_PORT,
                auth_provider=auth_provider,
                load_balancing_policy=DCAwareRoundRobinPolicy(local_dc='datacenter1')
            )

            self.session = self.cluster.connect()
            
            # Set keyspace
            try:
                self.session.set_keyspace(self.config.CASSANDRA_KEYSPACE)
                print(f"📁 Using keyspace: {self.config.CASSANDRA_KEYSPACE}")
            except InvalidRequest:
                print(f"⚠️ Keyspace '{self.config.CASSANDRA_KEYSPACE}' not found")
                raise

            print(f"🔌 Connected to Cassandra: {', '.join(self.config.CASSANDRA_HOSTS)}")

            return self.session

        except Exception as e:
            print(f"❌ Failed to connect to Cassandra: {e}")
            raise

    def get_session(self) -> Session:
        """Get Cassandra session, creating if needed."""
        if not self.session:
            self.create_session()
        return self.session

    def prepare_statement(self, query: str, cache_key: str = None) -> PreparedStatement:
        """Prepare CQL statement for efficient batch inserts."""
        cache_key = cache_key or query
        
        if cache_key in self.prepared_statements:
            return self.prepared_statements[cache_key]

        session = self.get_session()
        prepared = session.prepare(query)
        self.prepared_statements[cache_key] = prepared
        
        print(f"⚡ Prepared statement: {cache_key[:50]}...")
        return prepared

    def insert_batch(self, statements_and_params: List[Tuple[PreparedStatement, List]]):
        """Insert batch of data with optimized performance."""
        start_time = time.time()
        session = self.get_session()

        try:
            # Use unlogged batch for performance (eventual consistency)
            batch = BatchStatement(batch_type=BatchType.UNLOGGED)
            
            for statement, params in statements_and_params:
                batch.add(statement, params)

            session.execute(batch)
            
            insert_time = time.time() - start_time
            self.stats["batches"] += 1
            self.stats["inserts"] += len(statements_and_params)
            self.stats["insert_time"] += insert_time

            print(f"💾 Inserted batch: {len(statements_and_params)} records in {insert_time:.3f}s")

        except WriteTimeout as e:
            self.stats["errors"] += 1
            print(f"⚠️ Write timeout during batch insert: {e}")
            raise
        except Exception as e:
            self.stats["errors"] += 1
            print(f"❌ Error during batch insert: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get sink statistics."""
        avg_insert_time = self.stats["insert_time"] / max(self.stats["batches"], 1)
        throughput = self.stats["inserts"] / max(self.stats["insert_time"], 1)
        
        return {
            **self.stats,
            "avg_batch_insert_time": f"{avg_insert_time:.3f}s",
            "throughput_inserts_per_sec": f"{throughput:.1f}"
        }

    def close(self):
        """Close Cassandra connection."""
        if self.cluster:
            self.cluster.shutdown()
            print("🔌 Cassandra connection closed")


class EventStreamProcessor:
    """Complete stream processor for Kafka to Cassandra pipeline."""

    def __init__(self, config: KafkaCassandraConfig = None):
        self.config = config or KafkaCassandraConfig()
        self.consumer = KafkaStreamConsumer(config)
        self.sink = CassandraStreamSink(config)
        self.event_transformers = {}

    def register_event_transformer(self, event_type: str, transformer: Callable):
        """Register a transformer function for specific event types."""
        self.event_transformers[event_type] = transformer
        print(f"📝 Registered transformer for event type: {event_type}")

    def create_tables_if_not_exists(self):
        """Create required tables for stream processing."""
        session = self.sink.get_session()

        # Create keyspace if it doesn't exist
        create_keyspace = f"""
            CREATE KEYSPACE IF NOT EXISTS {self.config.CASSANDRA_KEYSPACE}
            WITH replication = {{
                'class': 'NetworkTopologyStrategy',
                'datacenter1': 3
            }}
        """
        session.execute(create_keyspace)
        session.set_keyspace(self.config.CASSANDRA_KEYSPACE)

        # Create events table for general event streaming
        create_events_table = """
            CREATE TABLE IF NOT EXISTS stream_events (
                event_id timeuuid,
                event_type text,
                user_id uuid,
                timestamp timestamp,
                data map<text, text>,
                source_topic text,
                source_partition int,
                source_offset bigint,
                PRIMARY KEY (event_type, timestamp, event_id)
            ) WITH CLUSTERING ORDER BY (timestamp DESC, event_id DESC)
              AND compaction = {
                'class': 'TimeWindowCompactionStrategy',
                'compaction_window_unit': 'HOURS',
                'compaction_window_size': 24
              }
        """

        # Create user activity table for time-series analysis
        create_activity_table = """
            CREATE TABLE IF NOT EXISTS user_activity (
                user_id uuid,
                activity_date date,
                activity_time timestamp,
                activity_id timeuuid,
                activity_type text,
                properties map<text, text>,
                session_id uuid,
                PRIMARY KEY ((user_id, activity_date), activity_time, activity_id)
            ) WITH CLUSTERING ORDER BY (activity_time DESC, activity_id DESC)
              AND default_time_to_live = 2592000
        """

        session.execute(create_events_table)
        session.execute(create_activity_table)
        print("✅ Created stream processing tables")

    def process_events_batch(self, messages: List[Dict]):
        """Process a batch of Kafka messages and insert into Cassandra."""
        # Prepare statements
        insert_event = self.sink.prepare_statement("""
            INSERT INTO stream_events (
                event_id, event_type, user_id, timestamp, data, 
                source_topic, source_partition, source_offset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, "insert_event")

        insert_activity = self.sink.prepare_statement("""
            INSERT INTO user_activity (
                user_id, activity_date, activity_time, activity_id, 
                activity_type, properties, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, "insert_activity")

        batch_statements = []

        for message in messages:
            try:
                # Extract message data
                event_data = message['value']
                timestamp = datetime.fromtimestamp(message['timestamp'] / 1000.0)
                
                # Apply transformation if registered
                event_type = event_data.get('event_type', 'unknown')
                if event_type in self.event_transformers:
                    event_data = self.event_transformers[event_type](event_data)

                # Prepare event record
                event_id = uuid.uuid1()
                user_id = uuid.UUID(event_data.get('user_id')) if event_data.get('user_id') else None
                
                # Convert all data values to strings for map storage
                data_map = {k: str(v) for k, v in event_data.items() if k not in ['event_type', 'user_id']}

                event_params = [
                    event_id,
                    event_type,
                    user_id,
                    timestamp,
                    data_map,
                    message['topic'],
                    message['partition'],
                    message['offset']
                ]

                batch_statements.append((insert_event, event_params))

                # Also insert into user activity table if we have user_id
                if user_id:
                    activity_params = [
                        user_id,
                        timestamp.date(),
                        timestamp,
                        event_id,
                        event_type,
                        data_map,
                        uuid.UUID(event_data.get('session_id')) if event_data.get('session_id') else None
                    ]
                    batch_statements.append((insert_activity, activity_params))

            except Exception as e:
                print(f"⚠️ Error processing message: {e}")
                continue

        # Insert batch
        if batch_statements:
            self.sink.insert_batch(batch_statements)

    def start_streaming(self, topics: List[str], max_messages: int = None):
        """Start the complete streaming pipeline."""
        print(f"🚀 Starting Kafka → Cassandra stream processing")
        print(f"📡 Topics: {topics}")
        
        # Setup
        self.create_tables_if_not_exists()
        self.consumer.create_consumer(topics)
        
        # Start processing
        self.consumer.consume_messages(
            batch_processor=self.process_events_batch,
            max_messages=max_messages
        )

    def get_complete_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from the entire pipeline."""
        return {
            "consumer": self.consumer.get_stats(),
            "sink": self.sink.get_stats()
        }

    def close(self):
        """Close all connections."""
        self.consumer.close()
        self.sink.close()


def create_sample_event_data(count: int = 100) -> List[Dict]:
    """Create sample event data for testing."""
    events = []
    event_types = ['page_view', 'click', 'purchase', 'login', 'logout']
    
    for i in range(count):
        event = {
            'event_type': event_types[i % len(event_types)],
            'user_id': str(uuid.uuid4()),
            'session_id': str(uuid.uuid4()),
            'timestamp': int(time.time() * 1000),
            'page_url': f'/page/{i % 10}',
            'user_agent': 'Mozilla/5.0',
            'ip_address': f'192.168.1.{i % 255}',
            'duration': str(30 + (i % 120))
        }
        events.append(event)
    
    return events


def parse_common_args() -> argparse.ArgumentParser:
    """Create argument parser with common Kafka-Cassandra options."""
    parser = argparse.ArgumentParser(description="Kafka-Cassandra Stream Processing Application")

    # Kafka options
    parser.add_argument(
        "--kafka-brokers", 
        nargs='+',
        default=KafkaCassandraConfig.KAFKA_BROKERS, 
        help="Kafka broker addresses"
    )
    parser.add_argument(
        "--kafka-topics", 
        nargs='+',
        required=True, 
        help="Kafka topics to consume"
    )
    parser.add_argument(
        "--consumer-group", 
        default=KafkaCassandraConfig.KAFKA_CONSUMER_GROUP, 
        help="Kafka consumer group"
    )

    # Cassandra options
    parser.add_argument(
        "--cassandra-hosts", 
        nargs='+',
        default=KafkaCassandraConfig.CASSANDRA_HOSTS, 
        help="Cassandra host addresses"
    )
    parser.add_argument(
        "--keyspace", 
        default=KafkaCassandraConfig.CASSANDRA_KEYSPACE, 
        help="Cassandra keyspace"
    )

    # Processing options
    parser.add_argument(
        "--batch-size", 
        type=int,
        default=KafkaCassandraConfig.BATCH_SIZE, 
        help="Batch size for processing"
    )
    parser.add_argument(
        "--max-messages", 
        type=int,
        help="Maximum messages to process"
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


if __name__ == "__main__":
    # Test the common utilities
    print("🧪 Testing Kafka-Cassandra common utilities...")

    try:
        # Test configuration
        config = KafkaCassandraConfig()
        print(f"✅ Kafka brokers: {config.KAFKA_BROKERS}")
        print(f"✅ Cassandra hosts: {config.CASSANDRA_HOSTS}")

        # Test Cassandra connection
        sink = CassandraStreamSink(config)
        session = sink.get_session()
        print("✅ Cassandra connection successful")

        # Test prepared statement
        test_stmt = sink.prepare_statement(
            "SELECT cluster_name FROM system.local",
            "test_query"
        )
        print("✅ Prepared statement test successful")

        # Cleanup
        sink.close()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
