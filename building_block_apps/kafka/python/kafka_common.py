"""
Common utilities for Kafka Python examples.

This module provides shared configuration and utilities for Kafka producers and consumers.
"""

import json
import logging
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def get_kafka_config() -> Dict[str, Any]:
    """
    Get common Kafka configuration.

    Returns:
        Dictionary containing Kafka configuration parameters
    """
    return {
        "bootstrap_servers": [
            "192.168.1.184:9092",
            "192.168.1.187:9092",
            "192.168.1.190:9092",
        ],
        "security_protocol": "PLAINTEXT",
        "acks": "all",  # Wait for all replicas to acknowledge
        "retries": 3,
        "retry_backoff_ms": 100,
        "request_timeout_ms": 30000,
        "delivery_timeout_ms": 120000,
    }


def get_producer_config() -> Dict[str, Any]:
    """
    Get Kafka producer specific configuration.

    Returns:
        Dictionary containing producer configuration
    """
    config = get_kafka_config()
    config.update(
        {
            "enable_idempotence": True,
            "max_in_flight_requests_per_connection": 5,
            "compression_type": "snappy",
            "batch_size": 16384,
            "linger_ms": 10,
            "buffer_memory": 33554432,
            "key_serializer": "org.apache.kafka.common.serialization.StringSerializer",
            "value_serializer": "org.apache.kafka.common.serialization.StringSerializer",
        }
    )
    return config


def get_consumer_config(group_id: str) -> Dict[str, Any]:
    """
    Get Kafka consumer specific configuration.

    Args:
        group_id: Consumer group identifier

    Returns:
        Dictionary containing consumer configuration
    """
    config = get_kafka_config()
    config.update(
        {
            "group_id": group_id,
            "auto_offset_reset": "earliest",
            "enable_auto_commit": True,
            "auto_commit_interval_ms": 1000,
            "session_timeout_ms": 30000,
            "heartbeat_interval_ms": 3000,
            "max_poll_records": 500,
            "max_poll_interval_ms": 300000,
            "key_deserializer": "org.apache.kafka.common.serialization.StringDeserializer",
            "value_deserializer": "org.apache.kafka.common.serialization.StringDeserializer",
        }
    )
    return config


def create_sample_message(
    message_id: int, message_type: str = "sample"
) -> Dict[str, Any]:
    """
    Create a sample message for testing.

    Args:
        message_id: Unique identifier for the message
        message_type: Type of message being created

    Returns:
        Dictionary containing sample message data
    """
    return {
        "id": message_id,
        "type": message_type,
        "timestamp": int(time.time() * 1000),
        "data": {
            "user_id": f"user_{message_id % 1000}",
            "action": "view_product" if message_id % 2 == 0 else "add_to_cart",
            "product_id": f"product_{message_id % 100}",
            "session_id": f"session_{message_id // 10}",
            "value": round((message_id * 1.23) % 1000, 2),
        },
        "metadata": {
            "source": "python_producer",
            "version": "1.0",
            "environment": "development",
        },
    }


def serialize_message(message: Dict[str, Any]) -> str:
    """
    Serialize message to JSON string.

    Args:
        message: Message dictionary to serialize

    Returns:
        JSON string representation of the message
    """
    return json.dumps(message, separators=(",", ":"))


def deserialize_message(message_str: str) -> Optional[Dict[str, Any]]:
    """
    Deserialize JSON string to message dictionary.

    Args:
        message_str: JSON string to deserialize

    Returns:
        Deserialized message dictionary or None if parsing fails
    """
    try:
        return json.loads(message_str)
    except json.JSONDecodeError as e:
        logging.error(f"Failed to deserialize message: {e}")
        return None


def get_default_topic() -> str:
    """
    Get the default topic name for examples.

    Returns:
        Default topic name
    """
    return "building-blocks-demo"


class MessageStats:
    """Simple statistics tracker for messages."""

    def __init__(self):
        self.sent_count = 0
        self.received_count = 0
        self.error_count = 0
        self.start_time = time.time()

    def record_sent(self):
        """Record a message sent."""
        self.sent_count += 1

    def record_received(self):
        """Record a message received."""
        self.received_count += 1

    def record_error(self):
        """Record an error."""
        self.error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        elapsed = time.time() - self.start_time
        return {
            "sent_count": self.sent_count,
            "received_count": self.received_count,
            "error_count": self.error_count,
            "elapsed_seconds": round(elapsed, 2),
            "send_rate": round(self.sent_count / elapsed, 2) if elapsed > 0 else 0,
            "receive_rate": (
                round(self.received_count / elapsed, 2) if elapsed > 0 else 0
            ),
        }

    def print_stats(self):
        """Print current statistics."""
        stats = self.get_stats()
        print(
            f"📊 Stats: Sent={stats['sent_count']}, "
            f"Received={stats['received_count']}, "
            f"Errors={stats['error_count']}, "
            f"Elapsed={stats['elapsed_seconds']}s, "
            f"Send Rate={stats['send_rate']}/s, "
            f"Receive Rate={stats['receive_rate']}/s"
        )
