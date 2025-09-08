#!/usr/bin/env python3
"""
Kafka to Iceberg Streaming with Apache Flink

This script demonstrates streaming data from Kafka to Apache Iceberg tables using Flink.
It includes data transformation, partitioning, and real-time processing capabilities.

Prerequisites:
- Flink cluster running (JobManager on cpu-node1, TaskManagers on all nodes)
- Kafka cluster running with topic 'user-events'
- Hive Metastore running on cpu-node1:9083
- HDFS cluster running with warehouse at hdfs://192.168.1.184:9000/lakehouse/iceberg
- Required JAR files in Flink lib directory
"""

import sys
import time
import logging
from typing import Optional
from flink_iceberg_common import (
    FlinkIcebergManager,
    FlinkIcebergConfig,
    validate_dependencies,
    print_job_status,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/flink_iceberg_streaming.log"),
    ],
)
logger = logging.getLogger(__name__)


class KafkaIcebergStreamingJob:
    """Streaming job from Kafka to Iceberg"""

    def __init__(self, config: Optional[FlinkIcebergConfig] = None):
        self.config = config or FlinkIcebergConfig()
        self.manager = FlinkIcebergManager(self.config)
        self.job_result = None

    def setup_streaming_pipeline(
        self,
        topic: str = "user-events",
        catalog_name: str = "iceberg_catalog",
        namespace: str = "lakehouse",
        sink_table: str = "streaming_events",
    ) -> None:
        """Setup the complete streaming pipeline"""

        logger.info("🚀 Setting up Kafka to Iceberg streaming pipeline...")

        try:
            # 1. Create table environment
            logger.info("1️⃣ Creating Flink table environment...")
            table_env = self.manager.create_table_environment()

            # 2. Create Iceberg catalog
            logger.info("2️⃣ Setting up Iceberg catalog...")
            self.manager.create_iceberg_catalog(catalog_name)

            # 3. Create Kafka source table
            logger.info("3️⃣ Creating Kafka source table...")
            self.manager.create_kafka_source_table(
                topic=topic,
                table_name="kafka_events",
                consumer_group="iceberg-flink-consumer",
            )

            # 4. Create Iceberg sink table
            logger.info("4️⃣ Creating Iceberg sink table...")
            self.manager.create_iceberg_sink_table(
                namespace=namespace, table_name=sink_table, catalog_name=catalog_name
            )

            logger.info("✅ Pipeline setup completed successfully!")

        except Exception as e:
            logger.error(f"❌ Pipeline setup failed: {e}")
            raise

    def start_streaming(self, sink_table: str = "streaming_events") -> None:
        """Start the streaming job"""

        logger.info("🔄 Starting Kafka to Iceberg streaming...")

        try:
            # Define the streaming SQL with transformations
            streaming_sql = f"""
                INSERT INTO {sink_table}
                SELECT 
                    event_id,
                    user_id,
                    event_type,
                    event_time,
                    properties,
                    region,
                    EXTRACT(YEAR FROM event_time) as year,
                    EXTRACT(MONTH FROM event_time) as month,
                    EXTRACT(DAY FROM event_time) as day,
                    EXTRACT(HOUR FROM event_time) as hour
                FROM kafka_events
            """

            logger.info("📝 Executing streaming SQL:")
            logger.info(streaming_sql)

            # Execute the streaming job
            table_result = self.manager.table_env.execute_sql(streaming_sql)
            self.job_result = table_result

            print_job_status(table_result)

            return table_result

        except Exception as e:
            logger.error(f"❌ Streaming job failed: {e}")
            raise

    def monitor_job(self, duration_minutes: int = 5) -> None:
        """Monitor the streaming job for specified duration"""

        logger.info(f"👀 Monitoring streaming job for {duration_minutes} minutes...")

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        while time.time() < end_time:
            try:
                # Check job status
                if self.job_result:
                    logger.info(
                        "📊 Job is running... Check Flink Web UI for detailed metrics"
                    )
                    logger.info("🌐 Web UI: http://192.168.1.184:8081")

                # Sleep before next check
                time.sleep(30)  # Check every 30 seconds

            except KeyboardInterrupt:
                logger.info("⚠️ Monitoring interrupted by user")
                break
            except Exception as e:
                logger.error(f"❌ Monitoring error: {e}")
                break

        logger.info("✅ Monitoring completed")

    def stop_job(self) -> None:
        """Stop the streaming job gracefully"""
        try:
            if self.job_result:
                logger.info("🛑 Stopping streaming job...")
                # Note: Flink jobs typically run continuously until manually stopped
                logger.info(
                    "ℹ️ Use Flink Web UI or CLI to stop the job: http://192.168.1.184:8081"
                )

        except Exception as e:
            logger.error(f"❌ Error stopping job: {e}")


def create_test_data_producer():
    """Create a simple test data producer for demonstration"""

    test_producer_script = """
#!/usr/bin/env python3
# Simple test data producer for Kafka topic 'user-events'

import json
import time
import random
from datetime import datetime
from kafka import KafkaProducer

def create_test_event():
    regions = ['us-east', 'us-west', 'eu-central', 'asia-pacific']
    event_types = ['page_view', 'click', 'purchase', 'signup', 'logout']
    
    return {
        'event_id': random.randint(1000, 9999),
        'user_id': random.randint(1, 100),
        'event_type': random.choice(event_types),
        'event_time': datetime.now().isoformat(),
        'properties': {
            'source': 'web',
            'device': random.choice(['mobile', 'desktop', 'tablet'])
        },
        'region': random.choice(regions)
    }

def main():
    producer = KafkaProducer(
        bootstrap_servers=['192.168.1.184:9092', '192.168.1.187:9092', '192.168.1.190:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    print("🚀 Starting test data producer...")
    
    try:
        for i in range(100):  # Send 100 test events
            event = create_test_event()
            producer.send('user-events', event)
            print(f"📤 Sent event {i+1}: {event['event_type']} from {event['region']}")
            time.sleep(2)  # Send event every 2 seconds
            
    except KeyboardInterrupt:
        print("⚠️ Producer stopped by user")
    finally:
        producer.close()

if __name__ == "__main__":
    main()
"""

    with open("/tmp/test_data_producer.py", "w") as f:
        f.write(test_producer_script)

    logger.info("📝 Test data producer script created at /tmp/test_data_producer.py")


def main():
    """Main function to run the streaming job"""

    print("🎯 Kafka to Iceberg Streaming Job Starting...")
    print("=" * 60)

    # Validate environment
    logger.info("🔍 Validating environment...")

    if not validate_dependencies():
        logger.error("❌ Dependency validation failed")
        sys.exit(1)

    config = FlinkIcebergConfig()
    if not config.validate_environment():
        logger.error("❌ Environment validation failed")
        sys.exit(1)

    # Create streaming job
    streaming_job = KafkaIcebergStreamingJob(config)

    try:
        # Setup pipeline
        streaming_job.setup_streaming_pipeline(
            topic="user-events",
            catalog_name="iceberg_catalog",
            namespace="lakehouse",
            sink_table="streaming_events",
        )

        # Create test data producer
        create_test_data_producer()

        logger.info("🎉 Setup completed! Ready to start streaming...")
        logger.info("📋 Next steps:")
        logger.info("  1. Run test data producer: python3 /tmp/test_data_producer.py")
        logger.info("  2. This script will start consuming and streaming to Iceberg")
        logger.info("  3. Monitor in Flink Web UI: http://192.168.1.184:8081")

        # Ask user if they want to start streaming
        start_streaming = input("\n▶️  Start streaming now? (y/N): ").lower().strip()

        if start_streaming == "y":
            # Start streaming
            streaming_job.start_streaming("streaming_events")

            # Monitor for a few minutes
            streaming_job.monitor_job(duration_minutes=5)

        else:
            logger.info("ℹ️ Streaming setup completed but not started")
            logger.info(
                "💡 To start later, run: streaming_job.start_streaming('streaming_events')"
            )

    except KeyboardInterrupt:
        logger.info("⚠️ Process interrupted by user")
    except Exception as e:
        logger.error(f"❌ Job execution failed: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        streaming_job.stop_job()


if __name__ == "__main__":
    main()
