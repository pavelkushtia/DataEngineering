#!/usr/bin/env python3
"""
Common utilities and configuration for Spark building block applications.

This module provides:
- Spark session creation with optimized settings
- Common data schemas and sample data generation
- Utility functions for performance monitoring
- Error handling patterns
"""

import sys
import time
import json
import random
import argparse
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.types import (
        StructType, StructField, StringType, IntegerType, 
        DoubleType, TimestampType, BooleanType
    )
    from pyspark.sql.functions import col, current_timestamp, lit
except ImportError:
    print("ERROR: PySpark not found. Install with: pip install pyspark")
    sys.exit(1)


@dataclass
class SparkConfig:
    """Configuration for Spark applications."""
    app_name: str = "SparkBuildingBlock"
    master: str = "spark://192.168.1.184:7077"
    executor_memory: str = "2g"
    executor_cores: str = "2"
    driver_memory: str = "1g"
    kafka_servers: str = "192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092"
    checkpoint_dir: str = "/tmp/spark-checkpoints"
    warehouse_dir: str = "/home/spark/spark/warehouse"


def create_spark_session(config: SparkConfig) -> SparkSession:
    """
    Create a Spark session with optimized configuration.
    
    Args:
        config: SparkConfig object with application settings
        
    Returns:
        Configured SparkSession
    """
    builder = SparkSession.builder \
        .appName(config.app_name) \
        .master(config.master) \
        .config("spark.executor.memory", config.executor_memory) \
        .config("spark.executor.cores", config.executor_cores) \
        .config("spark.driver.memory", config.driver_memory) \
        .config("spark.sql.warehouse.dir", config.warehouse_dir) \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.sql.adaptive.skewJoin.enabled", "true") \
        .config("spark.dynamicAllocation.enabled", "false")
    
    # Add Kafka dependencies if available
    try:
        builder = builder.config(
            "spark.jars.packages", 
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.6"
        )
    except Exception:
        print("WARNING: Kafka package not available, streaming examples may fail")
    
    session = builder.getOrCreate()
    session.sparkContext.setLogLevel("WARN")
    
    print(f"✅ Spark session created: {config.app_name}")
    print(f"   Master: {config.master}")
    print(f"   Executor Memory: {config.executor_memory}")
    print(f"   Executor Cores: {config.executor_cores}")
    
    return session


def get_sample_data_schema() -> StructType:
    """
    Define a common schema for sample data used across examples.
    
    Returns:
        StructType schema for sample e-commerce data
    """
    return StructType([
        StructField("user_id", StringType(), True),
        StructField("product_id", StringType(), True),
        StructField("category", StringType(), True),
        StructField("action", StringType(), True),
        StructField("timestamp", TimestampType(), True),
        StructField("price", DoubleType(), True),
        StructField("quantity", IntegerType(), True),
        StructField("session_id", StringType(), True),
        StructField("is_premium", BooleanType(), True),
        StructField("region", StringType(), True),
    ])


def generate_sample_data(spark: SparkSession, num_records: int = 10000) -> DataFrame:
    """
    Generate sample e-commerce data for testing and examples.
    
    Args:
        spark: SparkSession 
        num_records: Number of records to generate
        
    Returns:
        DataFrame with sample data
    """
    print(f"🔄 Generating {num_records:,} sample records...")
    
    categories = ["electronics", "clothing", "books", "home", "sports"]
    actions = ["view", "add_to_cart", "purchase", "remove_from_cart"]
    regions = ["US-East", "US-West", "EU", "Asia"]
    
    # Generate data in batches for better performance
    batch_size = 1000
    data = []
    
    for i in range(num_records):
        record = {
            "user_id": f"user_{random.randint(1, 50000)}",
            "product_id": f"prod_{random.randint(1, 10000)}",
            "category": random.choice(categories),
            "action": random.choice(actions),
            "timestamp": datetime.now() - timedelta(
                seconds=random.randint(0, 7*24*3600)  # Last 7 days
            ),
            "price": round(random.uniform(10, 1000), 2),
            "quantity": random.randint(1, 5),
            "session_id": f"session_{random.randint(1, 100000)}",
            "is_premium": random.choice([True, False]),
            "region": random.choice(regions),
        }
        data.append(record)
        
        if len(data) >= batch_size:
            # Process batch
            if i % 5000 == 0 and i > 0:
                print(f"   Generated {i:,} records...")
    
    df = spark.createDataFrame(data, schema=get_sample_data_schema())
    print(f"✅ Generated {df.count():,} records")
    return df


def monitor_job_progress(spark: SparkSession, job_name: str = "Spark Job"):
    """
    Print job progress and performance metrics.
    
    Args:
        spark: SparkSession
        job_name: Name of the job for logging
    """
    print(f"\n📊 {job_name} Metrics:")
    print(f"   Spark UI: http://192.168.1.184:4040")
    
    # Get basic stats from Spark context
    sc = spark.sparkContext
    print(f"   Application ID: {sc.applicationId}")
    print(f"   Default Parallelism: {sc.defaultParallelism}")
    
    # Additional metrics if available
    try:
        status = sc.statusTracker()
        executor_infos = status.getExecutorInfos()
        print(f"   Active Executors: {len(executor_infos)}")
        
        total_cores = sum(exec.totalCores for exec in executor_infos)
        print(f"   Total Cores: {total_cores}")
        
    except Exception as e:
        print(f"   Metrics unavailable: {e}")


def setup_kafka_checkpoint(spark: SparkSession, config: SparkConfig, app_name: str):
    """
    Setup checkpoint directory for streaming applications.
    
    Args:
        spark: SparkSession
        config: SparkConfig
        app_name: Application name for unique checkpoint directory
    """
    import os
    checkpoint_path = f"{config.checkpoint_dir}/{app_name}"
    
    # Create checkpoint directory if it doesn't exist
    try:
        os.makedirs(checkpoint_path, exist_ok=True)
        print(f"✅ Checkpoint directory: {checkpoint_path}")
    except Exception as e:
        print(f"⚠️  Could not create checkpoint directory: {e}")
        print(f"   Using default: /tmp/spark-checkpoints/{app_name}")


def parse_common_args() -> argparse.ArgumentParser:
    """
    Create argument parser with common Spark application options.
    
    Returns:
        ArgumentParser with common options
    """
    parser = argparse.ArgumentParser(description="Spark Building Block Application")
    
    parser.add_argument(
        "--master", 
        default="spark://192.168.1.184:7077",
        help="Spark master URL (default: spark://192.168.1.184:7077)"
    )
    
    parser.add_argument(
        "--app-name",
        default="SparkBuildingBlock", 
        help="Spark application name"
    )
    
    parser.add_argument(
        "--executor-memory",
        default="2g",
        help="Executor memory (default: 2g)"
    )
    
    parser.add_argument(
        "--executor-cores", 
        default="2",
        help="Executor cores (default: 2)"
    )
    
    parser.add_argument(
        "--records",
        type=int,
        default=10000,
        help="Number of records to generate/process (default: 10000)"
    )
    
    parser.add_argument(
        "--output-path",
        default="/tmp/spark-output",
        help="Output path for results (default: /tmp/spark-output)"
    )
    
    parser.add_argument(
        "--kafka-topic",
        default="spark-demo",
        help="Kafka topic for streaming examples (default: spark-demo)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration to run streaming jobs in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    return parser


def cleanup_session(spark: SparkSession):
    """
    Properly clean up Spark session.
    
    Args:
        spark: SparkSession to clean up
    """
    try:
        print("\n🔄 Cleaning up Spark session...")
        spark.stop()
        print("✅ Spark session stopped")
    except Exception as e:
        print(f"⚠️  Error during cleanup: {e}")


def print_dataframe_summary(df: DataFrame, name: str = "DataFrame", show_data: bool = True):
    """
    Print a comprehensive summary of a DataFrame.
    
    Args:
        df: DataFrame to summarize
        name: Name for the DataFrame in output
        show_data: Whether to show sample data
    """
    print(f"\n📊 {name} Summary:")
    print(f"   Rows: {df.count():,}")
    print(f"   Columns: {len(df.columns)}")
    print(f"   Schema:")
    
    for field in df.schema.fields:
        print(f"     {field.name}: {field.dataType}")
    
    if show_data and df.count() > 0:
        print(f"\n   Sample Data:")
        df.show(5, truncate=False)
        
        # Show basic statistics for numeric columns
        numeric_cols = [f.name for f in df.schema.fields 
                       if isinstance(f.dataType, (IntegerType, DoubleType))]
        if numeric_cols:
            print(f"\n   Numeric Statistics:")
            df.select(*numeric_cols).describe().show()


def handle_errors(func):
    """
    Decorator for consistent error handling across Spark applications.
    
    Args:
        func: Function to wrap with error handling
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n⚠️  Application interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error in {func.__name__}: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    return wrapper


if __name__ == "__main__":
    # Test the common utilities
    print("🧪 Testing Spark common utilities...")
    
    config = SparkConfig(app_name="SparkCommonTest")
    spark = create_spark_session(config)
    
    # Generate and show sample data
    df = generate_sample_data(spark, 100)
    print_dataframe_summary(df, "Sample Data")
    
    monitor_job_progress(spark, "Common Utilities Test")
    cleanup_session(spark)
    
    print("✅ Spark common utilities test completed")
