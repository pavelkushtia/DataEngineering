#!/usr/bin/env python3
"""
Kafka Producer Example in Python

This script demonstrates how to produce messages to a Kafka topic using the kafka-python library.
It includes error handling, delivery confirmation, and performance monitoring.

Usage:
    python producer.py [--topic TOPIC] [--count COUNT] [--rate RATE]

Example:
    python producer.py --topic my-topic --count 1000 --rate 10

Requirements:
    pip install kafka-python
"""

import argparse
import signal
import sys
import time
from typing import Optional

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
except ImportError:
    print("❌ Error: kafka-python library not found!")
    print("📦 Install with: pip install kafka-python")
    sys.exit(1)

from kafka_common import (
    get_producer_config, create_sample_message, serialize_message,
    get_default_topic, MessageStats
)


class EnhancedKafkaProducer:
    """Enhanced Kafka producer with monitoring and error handling."""
    
    def __init__(self, topic: str):
        self.topic = topic
        self.producer: Optional[KafkaProducer] = None
        self.stats = MessageStats()
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def connect(self) -> bool:
        """
        Connect to Kafka cluster.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            config = get_producer_config()
            print(f"🔌 Connecting to Kafka brokers: {config['bootstrap_servers']}")
            
            # Create producer with string serialization
            self.producer = KafkaProducer(
                bootstrap_servers=config['bootstrap_servers'],
                acks=config['acks'],
                retries=config['retries'],
                retry_backoff_ms=config['retry_backoff_ms'],
                request_timeout_ms=config['request_timeout_ms'],
                delivery_timeout_ms=config['delivery_timeout_ms'],
                enable_idempotence=config['enable_idempotence'],
                max_in_flight_requests_per_connection=config['max_in_flight_requests_per_connection'],
                compression_type=config['compression_type'],
                batch_size=config['batch_size'],
                linger_ms=config['linger_ms'],
                buffer_memory=config['buffer_memory'],
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                value_serializer=lambda v: v.encode('utf-8'),
            )
            
            print(f"✅ Connected to Kafka successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def send_message(self, key: Optional[str], message: str) -> bool:
        """
        Send a message to the Kafka topic.
        
        Args:
            key: Message key (for partitioning)
            message: Message content
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            future = self.producer.send(self.topic, key=key, value=message)
            
            # Add callback for delivery confirmation
            future.add_callback(self._on_send_success)
            future.add_errback(self._on_send_error)
            
            return True
            
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            self.stats.record_error()
            return False
    
    def _on_send_success(self, record_metadata):
        """Callback for successful message delivery."""
        self.stats.record_sent()
        print(f"✅ Message sent to {record_metadata.topic}[{record_metadata.partition}] "
              f"at offset {record_metadata.offset}")
    
    def _on_send_error(self, exception):
        """Callback for message delivery failure."""
        self.stats.record_error()
        print(f"❌ Message delivery failed: {exception}")
    
    def produce_messages(self, count: int, rate: float = 1.0):
        """
        Produce a specified number of messages.
        
        Args:
            count: Number of messages to produce
            rate: Messages per second (0 = no limit)
        """
        print(f"🚀 Starting to produce {count} messages to topic '{self.topic}'")
        print(f"📊 Rate limit: {rate} messages/second" if rate > 0 else "📊 Rate limit: unlimited")
        
        sleep_time = 1.0 / rate if rate > 0 else 0
        
        for i in range(count):
            if not self.running:
                print("🛑 Stopping due to shutdown signal")
                break
            
            # Create sample message
            message_data = create_sample_message(i, "producer_demo")
            message_json = serialize_message(message_data)
            message_key = f"key_{i}"
            
            # Send message
            success = self.send_message(message_key, message_json)
            
            if success:
                print(f"📤 Sent message {i+1}/{count}: {message_key}")
            
            # Rate limiting
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Print stats every 100 messages
            if (i + 1) % 100 == 0:
                self.stats.print_stats()
        
        # Flush remaining messages
        print("🔄 Flushing remaining messages...")
        if self.producer:
            self.producer.flush(timeout=30)
        
        print(f"✅ Finished producing messages!")
        self.stats.print_stats()
    
    def close(self):
        """Close the producer connection."""
        if self.producer:
            print("🔌 Closing producer connection...")
            self.producer.close(timeout=30)
            print("✅ Producer closed successfully")


def main():
    """Main function to run the Kafka producer."""
    parser = argparse.ArgumentParser(description="Kafka Producer Example")
    parser.add_argument(
        "--topic", 
        default=get_default_topic(),
        help=f"Kafka topic to produce to (default: {get_default_topic()})"
    )
    parser.add_argument(
        "--count", 
        type=int, 
        default=10,
        help="Number of messages to produce (default: 10)"
    )
    parser.add_argument(
        "--rate", 
        type=float, 
        default=1.0,
        help="Messages per second (0 for unlimited, default: 1.0)"
    )
    
    args = parser.parse_args()
    
    print("🎯 Kafka Producer Example")
    print("=" * 50)
    print(f"📌 Topic: {args.topic}")
    print(f"📊 Message count: {args.count}")
    print(f"⚡ Rate: {args.rate} messages/second")
    print("=" * 50)
    
    producer = EnhancedKafkaProducer(args.topic)
    
    try:
        # Connect to Kafka
        if not producer.connect():
            sys.exit(1)
        
        # Produce messages
        producer.produce_messages(args.count, args.rate)
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        producer.close()


if __name__ == "__main__":
    main()
