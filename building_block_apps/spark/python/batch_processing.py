#!/usr/bin/env python3
"""
Spark Batch Processing Examples - Building Block Application

This module demonstrates common batch processing patterns with Apache Spark:
- Data loading and transformation
- Aggregations and analytics
- Data quality checks  
- Performance optimization techniques
- Multiple output formats

Usage:
    bazel run //spark/python:batch_processing -- --records 50000 --output-path /tmp/batch-results

Examples:
    # Basic batch processing
    bazel run //spark/python:batch_processing
    
    # Large dataset processing  
    bazel run //spark/python:batch_processing -- --records 1000000
    
    # Custom output location
    bazel run //spark/python:batch_processing -- --output-path /tmp/my-results
"""

import sys
import time
from datetime import datetime
from spark_common import (
    SparkConfig,
    create_spark_session,
    generate_sample_data,
    monitor_job_progress,
    cleanup_session,
    print_dataframe_summary,
    parse_common_args,
    handle_errors,
)

try:
    from pyspark.sql import DataFrame
    from pyspark.sql.functions import (
        col,
        count,
        sum as spark_sum,
        avg,
        max as spark_max,
        min as spark_min,
        when,
        desc,
        asc,
        round as spark_round,
        date_format,
        year,
        month,
        dayofmonth,
        hour,
        regexp_replace,
        upper,
        lower,
        trim,
        rank,
        dense_rank,
        row_number,
        lag,
        lead,
        collect_list,
        concat_ws,
        split,
        size,
    )
    from pyspark.sql.window import Window
    from pyspark.sql.types import StringType
except ImportError:
    print("ERROR: PySpark not found. Install with: pip install pyspark")
    sys.exit(1)


@handle_errors
def load_and_clean_data(spark, num_records: int) -> DataFrame:
    """
    Load sample data and perform basic cleaning operations.

    Args:
        spark: SparkSession
        num_records: Number of records to generate

    Returns:
        Cleaned DataFrame
    """
    print("\n🔄 Step 1: Loading and cleaning data...")

    # Generate sample data
    df = generate_sample_data(spark, num_records)

    # Data cleaning operations
    cleaned_df = (
        df.filter(col("price") > 0)
        .filter(col("quantity") > 0)
        .withColumn("category", upper(trim(col("category"))))
        .withColumn("action", lower(trim(col("action"))))
        .withColumn("total_amount", col("price") * col("quantity"))
        .withColumn("date", date_format(col("timestamp"), "yyyy-MM-dd"))
        .withColumn("hour", hour(col("timestamp")))
        .dropDuplicates()
    )

    print(f"   Original records: {df.count():,}")
    print(f"   After cleaning: {cleaned_df.count():,}")
    print(f"   Records removed: {df.count() - cleaned_df.count():,}")

    return cleaned_df


@handle_errors
def perform_aggregations(df: DataFrame) -> dict:
    """
    Perform various aggregation operations on the data.

    Args:
        df: Input DataFrame

    Returns:
        Dictionary containing aggregation results
    """
    print("\n🔄 Step 2: Performing aggregations...")

    results = {}

    # Basic statistics
    print("   Computing basic statistics...")
    stats_df = df.agg(
        count("*").alias("total_records"),
        spark_sum("total_amount").alias("total_revenue"),
        avg("total_amount").alias("avg_order_value"),
        spark_max("total_amount").alias("max_order_value"),
        spark_min("total_amount").alias("min_order_value"),
        count("user_id").alias("total_users"),
    ).collect()[0]

    results["basic_stats"] = stats_df.asDict()

    # Revenue by category
    print("   Computing revenue by category...")
    category_revenue = (
        df.groupBy("category")
        .agg(
            spark_sum("total_amount").alias("revenue"),
            count("*").alias("order_count"),
            avg("total_amount").alias("avg_order_value"),
        )
        .orderBy(desc("revenue"))
    )

    results["category_revenue"] = category_revenue

    # Daily trends
    print("   Computing daily trends...")
    daily_trends = (
        df.groupBy("date")
        .agg(
            spark_sum("total_amount").alias("daily_revenue"),
            count("*").alias("daily_orders"),
            count("user_id").alias("daily_users"),
        )
        .orderBy("date")
    )

    results["daily_trends"] = daily_trends

    # Hourly patterns
    print("   Computing hourly patterns...")
    hourly_patterns = (
        df.groupBy("hour")
        .agg(count("*").alias("orders"), spark_sum("total_amount").alias("revenue"))
        .orderBy("hour")
    )

    results["hourly_patterns"] = hourly_patterns

    # User behavior analysis
    print("   Analyzing user behavior...")
    user_behavior = (
        df.groupBy("user_id")
        .agg(
            count("*").alias("total_orders"),
            spark_sum("total_amount").alias("total_spent"),
            count("session_id").alias("total_sessions"),
            collect_list("action").alias("actions"),
        )
        .withColumn("actions_count", size("actions"))
        .withColumn(
            "avg_order_value", spark_round(col("total_spent") / col("total_orders"), 2)
        )
    )

    # Top customers
    top_customers = user_behavior.orderBy(desc("total_spent")).limit(10)
    results["top_customers"] = top_customers

    # Customer segmentation
    customer_segments = (
        user_behavior.withColumn(
            "segment",
            when(col("total_spent") > 1000, "Premium")
            .when(col("total_spent") > 500, "Gold")
            .when(col("total_spent") > 100, "Silver")
            .otherwise("Bronze"),
        )
        .groupBy("segment")
        .agg(
            count("*").alias("customer_count"),
            avg("total_spent").alias("avg_spent"),
            avg("total_orders").alias("avg_orders"),
        )
        .orderBy(desc("avg_spent"))
    )

    results["customer_segments"] = customer_segments

    return results


@handle_errors
def perform_window_operations(df: DataFrame) -> DataFrame:
    """
    Demonstrate window functions for advanced analytics.

    Args:
        df: Input DataFrame

    Returns:
        DataFrame with window function results
    """
    print("\n🔄 Step 3: Performing window operations...")

    # Define window specifications
    user_window = Window.partitionBy("user_id").orderBy("timestamp")
    category_window = Window.partitionBy("category").orderBy(desc("total_amount"))
    daily_window = Window.partitionBy("date").orderBy(desc("total_amount"))

    # Add window function columns
    windowed_df = (
        df.withColumn("user_order_number", row_number().over(user_window))
        .withColumn("previous_purchase", lag("total_amount", 1).over(user_window))
        .withColumn("next_purchase", lead("total_amount", 1).over(user_window))
        .withColumn("category_rank", rank().over(category_window))
        .withColumn("daily_rank", dense_rank().over(daily_window))
        .withColumn(
            "is_first_purchase",
            when(col("user_order_number") == 1, True).otherwise(False),
        )
        .withColumn(
            "purchase_growth",
            when(
                col("previous_purchase").isNotNull(),
                spark_round(
                    (col("total_amount") - col("previous_purchase"))
                    / col("previous_purchase")
                    * 100,
                    2,
                ),
            ).otherwise(0),
        )
    )

    print("   Added window function columns:")
    print("     - user_order_number: Sequential order number per user")
    print("     - previous_purchase, next_purchase: Lag/lead values")
    print("     - category_rank: Rank within category by order value")
    print("     - daily_rank: Dense rank within day")
    print("     - is_first_purchase: Boolean flag for first-time customers")
    print("     - purchase_growth: Growth rate compared to previous purchase")

    return windowed_df


@handle_errors
def data_quality_checks(df: DataFrame) -> dict:
    """
    Perform comprehensive data quality checks.

    Args:
        df: DataFrame to check

    Returns:
        Dictionary with data quality metrics
    """
    print("\n🔄 Step 4: Performing data quality checks...")

    quality_metrics = {}
    total_records = df.count()

    # Null value checks
    print("   Checking for null values...")
    null_counts = {}
    for column in df.columns:
        null_count = df.filter(col(column).isNull()).count()
        null_counts[column] = {
            "null_count": null_count,
            "null_percentage": (
                round(null_count / total_records * 100, 2) if total_records > 0 else 0
            ),
        }

    quality_metrics["null_analysis"] = null_counts

    # Duplicate analysis
    print("   Checking for duplicates...")
    unique_records = df.dropDuplicates().count()
    duplicate_count = total_records - unique_records
    quality_metrics["duplicates"] = {
        "total_records": total_records,
        "unique_records": unique_records,
        "duplicate_count": duplicate_count,
        "duplicate_percentage": (
            round(duplicate_count / total_records * 100, 2) if total_records > 0 else 0
        ),
    }

    # Business rule validations
    print("   Validating business rules...")
    validations = {
        "positive_prices": df.filter(col("price") <= 0).count(),
        "positive_quantities": df.filter(col("quantity") <= 0).count(),
        "valid_categories": df.filter(
            ~col("category").isin(
                ["ELECTRONICS", "CLOTHING", "BOOKS", "HOME", "SPORTS"]
            )
        ).count(),
        "future_dates": df.filter(col("timestamp") > datetime.now()).count(),
        "reasonable_prices": df.filter(
            (col("price") < 1) | (col("price") > 10000)
        ).count(),
    }

    quality_metrics["business_rules"] = validations

    # Data distribution analysis
    print("   Analyzing data distributions...")
    distributions = {}

    # Category distribution
    category_dist = df.groupBy("category").count().orderBy(desc("count")).collect()
    distributions["categories"] = [
        {"category": row["category"], "count": row["count"]} for row in category_dist
    ]

    # Action distribution
    action_dist = df.groupBy("action").count().orderBy(desc("count")).collect()
    distributions["actions"] = [
        {"action": row["action"], "count": row["count"]} for row in action_dist
    ]

    quality_metrics["distributions"] = distributions

    return quality_metrics


@handle_errors
def save_results(
    results: dict, windowed_df: DataFrame, quality_metrics: dict, output_path: str
):
    """
    Save results in multiple formats.

    Args:
        results: Aggregation results
        windowed_df: DataFrame with window operations
        quality_metrics: Data quality metrics
        output_path: Base output path
    """
    print(f"\n🔄 Step 5: Saving results to {output_path}...")

    try:
        # Save aggregation results
        print("   Saving aggregation results...")
        results["category_revenue"].coalesce(1).write.mode("overwrite").csv(
            f"{output_path}/category_revenue", header=True
        )
        results["daily_trends"].coalesce(1).write.mode("overwrite").csv(
            f"{output_path}/daily_trends", header=True
        )
        results["hourly_patterns"].coalesce(1).write.mode("overwrite").csv(
            f"{output_path}/hourly_patterns", header=True
        )
        results["top_customers"].coalesce(1).write.mode("overwrite").csv(
            f"{output_path}/top_customers", header=True
        )
        results["customer_segments"].coalesce(1).write.mode("overwrite").csv(
            f"{output_path}/customer_segments", header=True
        )

        # Save windowed data (sample)
        print("   Saving windowed data sample...")
        windowed_df.sample(0.1).coalesce(1).write.mode("overwrite").parquet(
            f"{output_path}/windowed_sample"
        )

        # Save full dataset in Parquet format (partitioned for better performance)
        print("   Saving full dataset...")
        windowed_df.write.mode("overwrite").partitionBy("category", "date").parquet(
            f"{output_path}/full_dataset"
        )

        # Save data quality report as JSON
        print("   Saving data quality report...")
        import json

        with open(f"{output_path}/quality_report.json", "w") as f:
            json.dump(quality_metrics, f, indent=2, default=str)

        print(f"✅ Results saved to: {output_path}")
        print(
            f"   - CSV files: category_revenue, daily_trends, hourly_patterns, top_customers, customer_segments"
        )
        print(f"   - Parquet files: windowed_sample, full_dataset (partitioned)")
        print(f"   - JSON report: quality_report.json")

    except Exception as e:
        print(f"⚠️  Error saving results: {e}")
        print("   Results computed successfully but not saved to disk")


@handle_errors
def print_results_summary(results: dict, quality_metrics: dict):
    """
    Print a comprehensive summary of results.

    Args:
        results: Aggregation results
        quality_metrics: Data quality metrics
    """
    print("\n" + "=" * 60)
    print("📊 BATCH PROCESSING RESULTS SUMMARY")
    print("=" * 60)

    # Basic statistics
    stats = results["basic_stats"]
    print(f"\n💰 REVENUE SUMMARY:")
    print(f"   Total Records: {stats['total_records']:,}")
    print(f"   Total Revenue: ${stats['total_revenue']:,.2f}")
    print(f"   Average Order Value: ${stats['avg_order_value']:.2f}")
    print(f"   Max Order Value: ${stats['max_order_value']:.2f}")
    print(f"   Min Order Value: ${stats['min_order_value']:.2f}")

    # Top categories
    print(f"\n🏆 TOP CATEGORIES BY REVENUE:")
    for i, row in enumerate(results["category_revenue"].take(3), 1):
        print(
            f"   {i}. {row['category']}: ${row['revenue']:,.2f} ({row['order_count']:,} orders)"
        )

    # Customer segments
    print(f"\n👥 CUSTOMER SEGMENTS:")
    for row in results["customer_segments"].collect():
        print(
            f"   {row['segment']}: {row['customer_count']:,} customers, Avg: ${row['avg_spent']:.2f}"
        )

    # Data quality summary
    print(f"\n✅ DATA QUALITY SUMMARY:")
    duplicates = quality_metrics["duplicates"]
    print(f"   Duplicate Rate: {duplicates['duplicate_percentage']:.1f}%")

    business_issues = sum(quality_metrics["business_rules"].values())
    total_records = duplicates["total_records"]
    print(
        f"   Business Rule Violations: {business_issues:,} ({business_issues/total_records*100:.1f}%)"
    )

    # Top null columns
    null_cols = [
        (col, data["null_percentage"])
        for col, data in quality_metrics["null_analysis"].items()
        if data["null_percentage"] > 0
    ]
    if null_cols:
        null_cols.sort(key=lambda x: x[1], reverse=True)
        print(f"   Columns with Nulls: {len(null_cols)}")
        for col, pct in null_cols[:3]:
            print(f"     {col}: {pct:.1f}%")

    print("\n" + "=" * 60)


@handle_errors
def main():
    """Main batch processing workflow."""
    # Parse arguments
    parser = parse_common_args()
    args = parser.parse_args()

    print("🚀 Starting Spark Batch Processing Example")
    print(f"   Records to process: {args.records:,}")
    print(f"   Output path: {args.output_path}")
    print(f"   Master: {args.master}")

    # Create Spark session
    config = SparkConfig(
        app_name=f"{args.app_name}_BatchProcessing",
        master=args.master,
        executor_memory=args.executor_memory,
        executor_cores=args.executor_cores,
    )

    spark = create_spark_session(config)

    try:
        start_time = time.time()

        # Step 1: Load and clean data
        cleaned_df = load_and_clean_data(spark, args.records)
        print_dataframe_summary(
            cleaned_df, "Cleaned Dataset", show_data=not args.records > 10000
        )

        # Step 2: Perform aggregations
        results = perform_aggregations(cleaned_df)

        # Step 3: Window operations
        windowed_df = perform_window_operations(cleaned_df)

        # Step 4: Data quality checks
        quality_metrics = data_quality_checks(windowed_df)

        # Step 5: Save results
        save_results(results, windowed_df, quality_metrics, args.output_path)

        # Monitor performance
        monitor_job_progress(spark, "Batch Processing")

        # Print summary
        print_results_summary(results, quality_metrics)

        end_time = time.time()
        processing_time = end_time - start_time

        print(f"\n⏱️  Total Processing Time: {processing_time:.2f} seconds")
        print(f"   Records per second: {args.records/processing_time:,.0f}")

        print(f"\n✅ Batch processing completed successfully!")
        print(f"   Processed {args.records:,} records in {processing_time:.2f} seconds")
        print(f"   Results saved to: {args.output_path}")

    finally:
        cleanup_session(spark)


if __name__ == "__main__":
    main()
