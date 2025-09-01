#!/usr/bin/env python3
"""
Kafka Consumer Example in Python

This script demonstrates how to consume messages from a Kafka topic using the kafka-python library.
It includes error handling, offset management, and performance monitoring.

Usage:
    python consumer.py [--topic TOPIC] [--group GROUP] [--timeout TIMEOUT]

Example:
    python consumer.py --topic my-topic --group my-consumer-group --timeout 60

Requirements:
    pip install kafka-python
"""

import argparse
import signal
import sys
import time
from typing import Optional

try:
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
except ImportError:
    print("❌ Error: kafka-python library not found!")
    print("📦 Install with: pip install kafka-python")
    sys.exit(1)

from kafka_common import (
    get_consumer_config, deserialize_message, get_default_topic, MessageStats
)


class EnhancedKafkaConsumer:
    """Enhanced Kafka consumer with monitoring and error handling."""
    
    def __init__(self, topic: str, group_id: str):
        self.topic = topic
        self.group_id = group_id
        self.consumer: Optional[KafkaConsumer] = None
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
        Connect to Kafka cluster and subscribe to topic.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            config = get_consumer_config(self.group_id)
            print(f"🔌 Connecting to Kafka brokers: {config['bootstrap_servers']}")
            print(f"👥 Consumer group: {self.group_id}")
            
            # Create consumer with string deserialization
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=config['bootstrap_servers'],
                group_id=config['group_id'],
                auto_offset_reset=config['auto_offset_reset'],
                enable_auto_commit=config['enable_auto_commit'],
                auto_commit_interval_ms=config['auto_commit_interval_ms'],
                session_timeout_ms=config['session_timeout_ms'],
                heartbeat_interval_ms=config['heartbeat_interval_ms'],
                max_poll_records=config['max_poll_records'],
                max_poll_interval_ms=config['max_poll_interval_ms'],
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                value_deserializer=lambda v: v.decode('utf-8'),
                consumer_timeout_ms=1000,  # 1 second timeout for polling
            )
            
            print(f"✅ Connected to Kafka and subscribed to topic '{self.topic}'!")
            
            # Print partition assignment
            partitions = self.consumer.assignment()
            if partitions:
                print(f"📋 Assigned partitions: {[p.partition for p in partitions]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            return False
    
    def process_message(self, message) -> bool:
        """
        Process a received message.
        
        Args:
            message: Kafka message object
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            # Extract message details
            topic = message.topic
            partition = message.partition
            offset = message.offset
            key = message.key
            value = message.value
            timestamp = message.timestamp
            
            # Deserialize JSON message
            message_data = deserialize_message(value)
            
            if message_data:
                self.stats.record_received()
                
                # Print message details
                print(f"📨 Received message:")
                print(f"   🔑 Key: {key}")
                print(f"   📋 Topic: {topic}[{partition}] @ offset {offset}")
                print(f"   ⏰ Timestamp: {timestamp}")
                print(f"   📦 Message ID: {message_data.get('id', 'N/A')}")
                print(f"   📊 Message Type: {message_data.get('type', 'N/A')}")
                
                # Process specific message types
                self._process_by_type(message_data)
                
                return True
            else:
                print(f"❌ Failed to deserialize message: {value}")
                self.stats.record_error()
                return False
                
        except Exception as e:
            print(f"❌ Error processing message: {e}")
            self.stats.record_error()
            return False
    
    def _process_by_type(self, message_data: dict):
        """Process message based on its type."""
        message_type = message_data.get('type', 'unknown')
        data = message_data.get('data', {})
        
        if message_type == "producer_demo":
            user_id = data.get('user_id')
            action = data.get('action')
            product_id = data.get('product_id')
            value = data.get('value')
            
            print(f"   👤 User: {user_id}")
            print(f"   🎯 Action: {action}")
            print(f"   📦 Product: {product_id}")
            print(f"   💰 Value: {value}")
            
        elif message_type == "order":
            order_id = data.get('order_id')
            total = data.get('total_amount')
            print(f"   🛒 Order ID: {order_id}")
            print(f"   💵 Total: ${total}")
            
        elif message_type == "user_event":
            event_name = data.get('event_name')
            session_id = data.get('session_id')
            print(f"   📊 Event: {event_name}")
            print(f"   🔗 Session: {session_id}")
        
        print()  # Empty line for readability
    
    def consume_messages(self, timeout_seconds: Optional[int] = None):
        """
        Consume messages from the Kafka topic.
        
        Args:
            timeout_seconds: Maximum time to consume (None = infinite)
        """
        print(f"🚀 Starting to consume from topic '{self.topic}'")
        if timeout_seconds:
            print(f"⏰ Timeout: {timeout_seconds} seconds")
        else:
            print(f"⏰ Timeout: infinite (Ctrl+C to stop)")
        print("=" * 50)
        
        start_time = time.time()
        last_stats_time = start_time
        
        try:
            while self.running:
                # Check timeout
                if timeout_seconds and (time.time() - start_time) > timeout_seconds:
                    print(f"⏰ Timeout reached ({timeout_seconds}s)")
                    break
                
                # Poll for messages
                message_batch = self.consumer.poll(timeout_ms=1000)
                
                if message_batch:
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            if not self.running:
                                break
                            self.process_message(message)
                
                # Print stats every 10 seconds
                current_time = time.time()
                if current_time - last_stats_time >= 10:
                    self.stats.print_stats()
                    last_stats_time = current_time
                
        except Exception as e:
            print(f"❌ Error during consumption: {e}")
            self.stats.record_error()
        
        print(f"✅ Finished consuming messages!")
        self.stats.print_stats()
    
    def close(self):
        """Close the consumer connection."""
        if self.consumer:
            print("🔌 Closing consumer connection...")
            self.consumer.close()
            print("✅ Consumer closed successfully")


def main():
    """Main function to run the Kafka consumer."""
    parser = argparse.ArgumentParser(description="Kafka Consumer Example")
    parser.add_argument(
        "--topic", 
        default=get_default_topic(),
        help=f"Kafka topic to consume from (default: {get_default_topic()})"
    )
    parser.add_argument(
        "--group", 
        default="building-blocks-consumer-group",
        help="Consumer group ID (default: building-blocks-consumer-group)"
    )
    parser.add_argument(
        "--timeout", 
        type=int,
        help="Consumption timeout in seconds (default: infinite)"
    )
    
    args = parser.parse_args()
    
    print("🎯 Kafka Consumer Example")
    print("=" * 50)
    print(f"📌 Topic: {args.topic}")
    print(f"👥 Group: {args.group}")
    print(f"⏰ Timeout: {args.timeout}s" if args.timeout else "⏰ Timeout: infinite")
    print("=" * 50)
    
    consumer = EnhancedKafkaConsumer(args.topic, args.group)
    
    try:
        # Connect to Kafka
        if not consumer.connect():
            sys.exit(1)
        
        # Consume messages
        consumer.consume_messages(args.timeout)
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
