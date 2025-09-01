#!/usr/bin/env python3
"""
Spark Structured Streaming Examples - Building Block Application

This module demonstrates real-time data processing with Spark Structured Streaming:
- Kafka stream processing
- Real-time aggregations with windowing
- Watermarks for late data handling
- Multiple output sinks (console, files, Kafka)
- Stateful operations and complex event processing

Usage:
    bazel run //spark/python:streaming -- --kafka-topic events --duration 120

Examples:
    # Basic streaming from Kafka
    bazel run //spark/python:streaming
    
    # Custom topic and duration
    bazel run //spark/python:streaming -- --kafka-topic user-events --duration 300
    
    # Stream to multiple outputs
    bazel run //spark/python:streaming -- --output-path /tmp/streaming-output
"""

import sys
import time
import signal
from datetime import datetime, timedelta
from spark_common import (
    SparkConfig, create_spark_session, monitor_job_progress,
    cleanup_session, parse_common_args, handle_errors,
    setup_kafka_checkpoint
)

try:
    from pyspark.sql import DataFrame
    from pyspark.sql.functions import (
        col, count, sum as spark_sum, avg, max as spark_max,
        min as spark_min, when, desc, asc, round as spark_round,
        window, current_timestamp, to_timestamp, from_json,
        to_json, struct, lit, concat, date_format,
        split, regexp_extract, length, coalesce,
        collect_list, size, array_contains
    )
    from pyspark.sql.types import (
        StructType, StructField, StringType, IntegerType,
        DoubleType, TimestampType, BooleanType
    )
    from pyspark.sql.streaming import StreamingQuery
except ImportError:
    print("ERROR: PySpark not found. Install with: pip install pyspark")
    sys.exit(1)


def get_kafka_stream_schema() -> StructType:
    """
    Define schema for incoming Kafka messages.
    
    Returns:
        StructType schema for JSON messages
    """
    return StructType([
        StructField("event_id", StringType(), True),
        StructField("user_id", StringType(), True),
        StructField("event_type", StringType(), True),
        StructField("product_id", StringType(), True),
        StructField("category", StringType(), True),
        StructField("price", DoubleType(), True),
        StructField("quantity", IntegerType(), True),
        StructField("session_id", StringType(), True),
        StructField("timestamp", StringType(), True),  # Will convert to TimestampType
        StructField("metadata", StructType([
            StructField("source", StringType(), True),
            StructField("version", StringType(), True),
            StructField("user_agent", StringType(), True),
            StructField("ip_address", StringType(), True)
        ]), True)
    ])


@handle_errors
def create_kafka_stream(spark, kafka_topic: str, kafka_servers: str) -> DataFrame:
    """
    Create a streaming DataFrame from Kafka topic.
    
    Args:
        spark: SparkSession
        kafka_topic: Kafka topic to consume from
        kafka_servers: Kafka bootstrap servers
        
    Returns:
        Streaming DataFrame
    """
    print(f"\n🔄 Creating Kafka stream from topic: {kafka_topic}")
    print(f"   Kafka servers: {kafka_servers}")
    
    # Read from Kafka
    kafka_df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_servers) \
        .option("subscribe", kafka_topic) \
        .option("startingOffsets", "latest") \
        .option("failOnDataLoss", "false") \
        .load()
    
    # Parse JSON messages
    schema = get_kafka_stream_schema()
    
    parsed_df = kafka_df \
        .select(
            col("key").cast("string"),
            from_json(col("value").cast("string"), schema).alias("data"),
            col("topic"),
            col("partition"),
            col("offset"),
            col("timestamp").alias("kafka_timestamp")
        ) \
        .select(
            col("key"),
            col("data.*"),
            col("topic"),
            col("partition"), 
            col("offset"),
            col("kafka_timestamp")
        ) \
        .withColumn("processed_timestamp", current_timestamp()) \
        .withColumn("event_timestamp", to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss")) \
        .withColumn("total_amount", col("price") * col("quantity")) \
        .filter(col("event_timestamp").isNotNull())
    
    print("✅ Kafka stream created and parsed")
    return parsed_df


@handle_errors
def real_time_analytics(stream_df: DataFrame) -> dict:
    """
    Create multiple real-time analytics queries.
    
    Args:
        stream_df: Input streaming DataFrame
        
    Returns:
        Dictionary of streaming queries
    """
    print("\n🔄 Setting up real-time analytics...")
    
    queries = {}
    
    # 1. Basic event counts per minute
    print("   Creating minute-by-minute event counts...")
    minute_counts = stream_df \
        .withWatermark("event_timestamp", "2 minutes") \
        .groupBy(
            window(col("event_timestamp"), "1 minute"),
            col("event_type")
        ) \
        .agg(
            count("*").alias("event_count"),
            spark_sum("total_amount").alias("total_revenue")
        )
    
    queries["minute_counts"] = minute_counts
    
    # 2. Real-time revenue by category (5-minute windows)
    print("   Creating revenue tracking by category...")
    category_revenue = stream_df \
        .withWatermark("event_timestamp", "5 minutes") \
        .groupBy(
            window(col("event_timestamp"), "5 minutes", "1 minute"),
            col("category")
        ) \
        .agg(
            spark_sum("total_amount").alias("revenue"),
            count("*").alias("order_count"),
            avg("total_amount").alias("avg_order_value")
        )
    
    queries["category_revenue"] = category_revenue
    
    # 3. Top active users (10-minute sliding window)
    print("   Creating top active users tracking...")
    active_users = stream_df \
        .withWatermark("event_timestamp", "10 minutes") \
        .groupBy(
            window(col("event_timestamp"), "10 minutes", "2 minutes"),
            col("user_id")
        ) \
        .agg(
            count("*").alias("activity_count"),
            spark_sum("total_amount").alias("total_spent"),
            collect_list("event_type").alias("events")
        ) \
        .withColumn("unique_events", size(col("events")))
    
    queries["active_users"] = active_users
    
    # 4. High-value transaction alerts (real-time)
    print("   Creating high-value transaction alerts...")
    high_value_alerts = stream_df \
        .filter(col("total_amount") > 500) \
        .select(
            col("event_id"),
            col("user_id"),
            col("total_amount"),
            col("category"),
            col("event_timestamp"),
            lit("HIGH_VALUE_TRANSACTION").alias("alert_type")
        )
    
    queries["high_value_alerts"] = high_value_alerts
    
    # 5. Session analysis (30-minute windows)
    print("   Creating session analysis...")
    session_analysis = stream_df \
        .withWatermark("event_timestamp", "30 minutes") \
        .groupBy(
            window(col("event_timestamp"), "30 minutes", "5 minutes"),
            col("session_id")
        ) \
        .agg(
            count("*").alias("events_in_session"),
            spark_sum("total_amount").alias("session_value"),
            collect_list("event_type").alias("session_events"),
            spark_min("event_timestamp").alias("session_start"),
            spark_max("event_timestamp").alias("session_end")
        ) \
        .withColumn("session_duration_minutes", 
                   (col("session_end").cast("long") - col("session_start").cast("long")) / 60)
    
    queries["session_analysis"] = session_analysis
    
    return queries


@handle_errors
def fraud_detection_stream(stream_df: DataFrame) -> DataFrame:
    """
    Create a fraud detection stream with complex event processing.
    
    Args:
        stream_df: Input streaming DataFrame
        
    Returns:
        Streaming DataFrame with fraud alerts
    """
    print("\n🔄 Setting up fraud detection...")
    
    # Define fraud patterns
    fraud_alerts = stream_df \
        .withWatermark("event_timestamp", "5 minutes") \
        .groupBy(
            window(col("event_timestamp"), "5 minutes"),
            col("user_id")
        ) \
        .agg(
            count("*").alias("transaction_count"),
            spark_sum("total_amount").alias("total_amount_5min"),
            collect_list("metadata.ip_address").alias("ip_addresses")
        ) \
        .withColumn("unique_ips", size(col("ip_addresses"))) \
        .filter(
            (col("transaction_count") > 10) |  # Too many transactions
            (col("total_amount_5min") > 2000) |  # High spending
            (col("unique_ips") > 3)  # Multiple IP addresses
        ) \
        .select(
            col("window"),
            col("user_id"),
            col("transaction_count"),
            col("total_amount_5min"),
            col("unique_ips"),
            when(col("transaction_count") > 10, "HIGH_FREQUENCY")
            .when(col("total_amount_5min") > 2000, "HIGH_VALUE")
            .when(col("unique_ips") > 3, "MULTIPLE_IPS")
            .otherwise("UNKNOWN").alias("fraud_type"),
            current_timestamp().alias("alert_timestamp")
        )
    
    print("✅ Fraud detection stream configured")
    return fraud_alerts


@handle_errors
def setup_output_sinks(queries: dict, output_path: str, kafka_servers: str, duration: int) -> list:
    """
    Setup multiple output sinks for streaming queries.
    
    Args:
        queries: Dictionary of streaming DataFrames
        output_path: Base output path for file sinks
        kafka_servers: Kafka servers for Kafka sink
        duration: How long to run streams
        
    Returns:
        List of active streaming queries
    """
    print(f"\n🔄 Setting up output sinks (duration: {duration}s)...")
    
    active_queries = []
    
    # Console outputs for monitoring
    print("   Setting up console outputs...")
    
    # 1. Minute counts to console
    console_query1 = queries["minute_counts"] \
        .writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", "false") \
        .option("numRows", 20) \
        .trigger(processingTime="30 seconds") \
        .start()
    
    active_queries.append(console_query1)
    
    # 2. High-value alerts to console
    console_query2 = queries["high_value_alerts"] \
        .writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime="10 seconds") \
        .start()
    
    active_queries.append(console_query2)
    
    # File outputs for persistence
    print("   Setting up file outputs...")
    
    # 3. Category revenue to Parquet files
    file_query1 = queries["category_revenue"] \
        .writeStream \
        .outputMode("update") \
        .format("parquet") \
        .option("path", f"{output_path}/category_revenue") \
        .option("checkpointLocation", f"{output_path}/checkpoints/category_revenue") \
        .trigger(processingTime="1 minute") \
        .start()
    
    active_queries.append(file_query1)
    
    # 4. Session analysis to Delta/Parquet
    file_query2 = queries["session_analysis"] \
        .writeStream \
        .outputMode("update") \
        .format("parquet") \
        .option("path", f"{output_path}/session_analysis") \
        .option("checkpointLocation", f"{output_path}/checkpoints/session_analysis") \
        .trigger(processingTime="2 minutes") \
        .start()
    
    active_queries.append(file_query2)
    
    # Memory sink for testing
    print("   Setting up memory sink for testing...")
    memory_query = queries["active_users"] \
        .writeStream \
        .outputMode("update") \
        .format("memory") \
        .queryName("active_users_table") \
        .trigger(processingTime="30 seconds") \
        .start()
    
    active_queries.append(memory_query)
    
    print(f"✅ {len(active_queries)} streaming queries started")
    
    return active_queries


@handle_errors
def monitor_streaming_progress(spark, queries: list, duration: int):
    """
    Monitor streaming query progress and metrics.
    
    Args:
        spark: SparkSession
        queries: List of active streaming queries
        duration: How long to monitor
    """
    print(f"\n📊 Monitoring streaming queries for {duration} seconds...")
    
    start_time = time.time()
    end_time = start_time + duration
    
    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\n⚠️  Received interrupt signal, stopping streams...")
        for query in queries:
            if query.isActive:
                query.stop()
        raise KeyboardInterrupt()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while time.time() < end_time:
            current_time = time.time()
            elapsed = current_time - start_time
            remaining = end_time - current_time
            
            print(f"\n⏱️  Elapsed: {elapsed:.0f}s | Remaining: {remaining:.0f}s")
            
            # Check query status
            active_count = 0
            for i, query in enumerate(queries):
                if query.isActive:
                    active_count += 1
                    progress = query.lastProgress
                    if progress:
                        batch_id = progress.get("batchId", "N/A")
                        input_rows = progress.get("inputRowsPerSecond", 0)
                        processed_rows = progress.get("processedRowsPerSecond", 0)
                        print(f"   Query {i+1}: Batch {batch_id}, Input: {input_rows:.1f} rows/s, Processed: {processed_rows:.1f} rows/s")
                else:
                    print(f"   Query {i+1}: ❌ Stopped")
            
            print(f"   Active Queries: {active_count}/{len(queries)}")
            
            # Show memory table contents (if available)
            try:
                memory_data = spark.sql("SELECT * FROM active_users_table").collect()
                if memory_data:
                    print(f"   Memory Table Records: {len(memory_data)}")
            except Exception:
                pass
            
            # Wait before next check
            time.sleep(15)
            
    except KeyboardInterrupt:
        print("\n⚠️  Monitoring interrupted by user")
    
    # Stop all queries
    print("\n🔄 Stopping streaming queries...")
    for i, query in enumerate(queries):
        if query.isActive:
            print(f"   Stopping query {i+1}...")
            query.stop()
    
    # Wait for graceful shutdown
    print("   Waiting for graceful shutdown...")
    time.sleep(5)
    
    print("✅ All streaming queries stopped")


@handle_errors
def generate_sample_kafka_data(spark, kafka_topic: str, kafka_servers: str, duration: int):
    """
    Generate sample data to Kafka for testing (optional).
    
    Args:
        spark: SparkSession
        kafka_topic: Kafka topic to write to
        kafka_servers: Kafka bootstrap servers
        duration: How long to generate data
    """
    print(f"\n🔄 Generating sample data to Kafka topic: {kafka_topic}")
    
    # This is a placeholder - in real scenarios, data would come from external sources
    # For testing, you could implement a data generator here
    
    print("   📝 Note: To test streaming, send JSON messages to Kafka topic:")
    print(f"      Topic: {kafka_topic}")
    print(f"      Format: {get_kafka_stream_schema()}")
    print("   Example message:")
    
    example_message = {
        "event_id": "evt_12345",
        "user_id": "user_123",
        "event_type": "purchase",
        "product_id": "prod_456",
        "category": "electronics",
        "price": 299.99,
        "quantity": 1,
        "session_id": "session_789",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": {
            "source": "web",
            "version": "1.0",
            "user_agent": "Mozilla/5.0",
            "ip_address": "192.168.1.100"
        }
    }
    
    print(f"      {example_message}")


@handle_errors
def main():
    """Main streaming workflow."""
    # Parse arguments
    parser = parse_common_args()
    args = parser.parse_args()
    
    print("🚀 Starting Spark Structured Streaming Example")
    print(f"   Kafka topic: {args.kafka_topic}")
    print(f"   Duration: {args.duration} seconds")
    print(f"   Output path: {args.output_path}")
    print(f"   Master: {args.master}")
    
    # Create Spark session with streaming configuration
    config = SparkConfig(
        app_name=f"{args.app_name}_Streaming",
        master=args.master,
        executor_memory=args.executor_memory,
        executor_cores=args.executor_cores,
        kafka_servers=config.kafka_servers
    )
    
    spark = create_spark_session(config)
    
    # Configure streaming settings
    spark.conf.set("spark.sql.streaming.metricsEnabled", "true")
    spark.conf.set("spark.sql.streaming.ui.enabled", "true")
    
    # Setup checkpoint directory
    setup_kafka_checkpoint(spark, config, "streaming_example")
    
    try:
        # Create Kafka stream
        stream_df = create_kafka_stream(spark, args.kafka_topic, config.kafka_servers)
        
        # Setup analytics queries
        analytics_queries = real_time_analytics(stream_df)
        
        # Setup fraud detection
        fraud_stream = fraud_detection_stream(stream_df)
        analytics_queries["fraud_alerts"] = fraud_stream
        
        # Setup output sinks
        active_queries = setup_output_sinks(
            analytics_queries, 
            args.output_path, 
            config.kafka_servers,
            args.duration
        )
        
        # Generate sample data instruction
        generate_sample_kafka_data(spark, args.kafka_topic, config.kafka_servers, args.duration)
        
        # Monitor streaming progress
        monitor_streaming_progress(spark, active_queries, args.duration)
        
        print(f"\n✅ Streaming example completed!")
        print(f"   Processed streams for {args.duration} seconds")
        print(f"   Results available in: {args.output_path}")
        print(f"   Spark Streaming UI: http://192.168.1.184:4040")
        
    except KeyboardInterrupt:
        print("\n⚠️  Streaming interrupted by user")
    except Exception as e:
        print(f"\n❌ Streaming error: {e}")
        raise
    finally:
        cleanup_session(spark)


if __name__ == "__main__":
    main()
