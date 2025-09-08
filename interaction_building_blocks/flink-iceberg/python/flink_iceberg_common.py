#!/usr/bin/env python3
"""
Common utilities for Flink-Iceberg integration
"""

import os
import logging
from typing import Dict, List, Optional
from pyflink.table import EnvironmentSettings, TableEnvironment
from pyflink.table.expressions import col

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FlinkIcebergConfig:
    """Configuration for Flink-Iceberg integration"""

    def __init__(self):
        # Default cluster configuration
        self.hive_metastore_uri = "thrift://192.168.1.184:9083"
        self.hdfs_warehouse = "hdfs://192.168.1.184:9000/lakehouse/iceberg"
        self.kafka_bootstrap_servers = (
            "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092"
        )

        # JAR paths
        self.flink_home = "/home/flink/flink"
        self.iceberg_jar_path = (
            f"{self.flink_home}/lib/iceberg-flink-runtime-1.19-1.9.2.jar"
        )
        self.hadoop_jar_path = f"{self.flink_home}/lib/hadoop-client-3.3.6.jar"

    def validate_environment(self) -> bool:
        """Validate that required JARs and services are available"""
        required_jars = [self.iceberg_jar_path, self.hadoop_jar_path]

        for jar_path in required_jars:
            if not os.path.exists(jar_path):
                logger.error(f"Required JAR not found: {jar_path}")
                return False

        logger.info("✅ Environment validation passed")
        return True


class FlinkIcebergManager:
    """Manager for Flink-Iceberg streaming operations"""

    def __init__(self, config: Optional[FlinkIcebergConfig] = None):
        self.config = config or FlinkIcebergConfig()
        self.table_env = None

    def create_table_environment(self) -> TableEnvironment:
        """Create and configure Flink table environment for Iceberg"""
        try:
            # Create streaming environment
            env_settings = (
                EnvironmentSettings.new_instance().in_streaming_mode().build()
            )
            table_env = TableEnvironment.create(env_settings)

            # Add required JARs
            jars = f"file://{self.config.iceberg_jar_path};file://{self.config.hadoop_jar_path}"
            table_env.get_config().get_configuration().set_string("pipeline.jars", jars)

            # Set checkpoint configuration
            table_env.get_config().get_configuration().set_string(
                "execution.checkpointing.interval", "10s"
            )
            table_env.get_config().get_configuration().set_string(
                "execution.checkpointing.mode", "EXACTLY_ONCE"
            )

            logger.info("✅ Flink table environment created successfully")
            self.table_env = table_env
            return table_env

        except Exception as e:
            logger.error(f"❌ Failed to create table environment: {e}")
            raise

    def create_iceberg_catalog(self, catalog_name: str = "iceberg_catalog") -> None:
        """Create Iceberg catalog in Flink"""
        if not self.table_env:
            raise RuntimeError(
                "Table environment not initialized. Call create_table_environment() first."
            )

        try:
            catalog_ddl = f"""
                CREATE CATALOG {catalog_name} WITH (
                    'type' = 'iceberg',
                    'catalog-type' = 'hive',
                    'uri' = '{self.config.hive_metastore_uri}',
                    'warehouse' = '{self.config.hdfs_warehouse}',
                    'hive-conf-dir' = '/opt/hadoop/current/etc/hadoop'
                )
            """

            self.table_env.execute_sql(catalog_ddl)
            self.table_env.execute_sql(f"USE CATALOG {catalog_name}")
            logger.info(f"✅ Iceberg catalog '{catalog_name}' created and activated")

        except Exception as e:
            logger.error(f"❌ Failed to create Iceberg catalog: {e}")
            raise

    def create_kafka_source_table(
        self,
        topic: str,
        table_name: str = "kafka_events",
        consumer_group: str = "flink-iceberg-consumer",
    ) -> None:
        """Create Kafka source table definition"""
        if not self.table_env:
            raise RuntimeError("Table environment not initialized")

        try:
            kafka_ddl = f"""
                CREATE TABLE {table_name} (
                    event_id BIGINT,
                    user_id BIGINT,
                    event_type STRING,
                    event_time TIMESTAMP(3),
                    properties MAP<STRING, STRING>,
                    region STRING,
                    processing_time AS PROCTIME(),
                    event_time_attr AS event_time,
                    WATERMARK FOR event_time_attr AS event_time_attr - INTERVAL '5' SECOND
                ) WITH (
                    'connector' = 'kafka',
                    'topic' = '{topic}',
                    'properties.bootstrap.servers' = '{self.config.kafka_bootstrap_servers}',
                    'properties.group.id' = '{consumer_group}',
                    'format' = 'json',
                    'scan.startup.mode' = 'latest-offset',
                    'properties.auto.offset.reset' = 'latest'
                )
            """

            self.table_env.execute_sql(kafka_ddl)
            logger.info(
                f"✅ Kafka source table '{table_name}' created for topic '{topic}'"
            )

        except Exception as e:
            logger.error(f"❌ Failed to create Kafka source table: {e}")
            raise

    def create_iceberg_sink_table(
        self,
        namespace: str = "lakehouse",
        table_name: str = "streaming_events",
        catalog_name: str = "iceberg_catalog",
    ) -> None:
        """Create Iceberg sink table with partitioning"""
        if not self.table_env:
            raise RuntimeError("Table environment not initialized")

        try:
            # Ensure namespace exists
            self.table_env.execute_sql(f"CREATE DATABASE IF NOT EXISTS {namespace}")
            self.table_env.execute_sql(f"USE {namespace}")

            iceberg_ddl = f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    event_id BIGINT,
                    user_id BIGINT,
                    event_type STRING,
                    event_time TIMESTAMP(3),
                    properties MAP<STRING, STRING>,
                    region STRING,
                    year INT,
                    month INT,
                    day INT,
                    hour INT
                ) PARTITIONED BY (region, year, month, day, hour)
                WITH (
                    'connector' = 'iceberg',
                    'catalog-name' = '{catalog_name}',
                    'database-name' = '{namespace}',
                    'table-name' = '{table_name}',
                    'write.format.default' = 'parquet',
                    'write.parquet.compression-codec' = 'zstd'
                )
            """

            self.table_env.execute_sql(iceberg_ddl)
            logger.info(f"✅ Iceberg sink table '{namespace}.{table_name}' created")

        except Exception as e:
            logger.error(f"❌ Failed to create Iceberg sink table: {e}")
            raise

    def get_table_info(self, table_name: str) -> Dict:
        """Get information about a table"""
        if not self.table_env:
            raise RuntimeError("Table environment not initialized")

        try:
            # Get table schema
            result = self.table_env.execute_sql(f"DESCRIBE {table_name}")
            schema_info = []

            with result.collect() as results:
                for row in results:
                    schema_info.append(
                        {"column": row[0], "type": row[1], "nullable": row[2]}
                    )

            return {"table_name": table_name, "schema": schema_info, "status": "active"}

        except Exception as e:
            logger.error(f"❌ Failed to get table info for '{table_name}': {e}")
            return {"table_name": table_name, "status": "error", "error": str(e)}


def print_job_status(job_result):
    """Print Flink job execution status"""
    try:
        logger.info("🚀 Flink streaming job started successfully!")
        logger.info(f"📊 Job ID: {job_result.get_job_id()}")
        logger.info("🔄 Streaming data from Kafka to Iceberg...")
        logger.info("📈 Monitor progress in Flink Web UI: http://192.168.1.184:8081")

    except Exception as e:
        logger.error(f"❌ Job status error: {e}")


def validate_dependencies():
    """Validate that all required dependencies are available"""
    dependencies = ["pyflink", "apache-flink", "py4j"]

    missing_deps = []
    for dep in dependencies:
        try:
            __import__(dep.replace("-", "_"))
        except ImportError:
            missing_deps.append(dep)

    if missing_deps:
        logger.error(f"❌ Missing dependencies: {missing_deps}")
        logger.error("Install with: pip install apache-flink")
        return False

    logger.info("✅ All Python dependencies available")
    return True
