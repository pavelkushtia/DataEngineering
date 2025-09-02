#!/usr/bin/env python3
"""
Spark ETL Pipeline Examples - Building Block Application

This module demonstrates comprehensive ETL (Extract, Transform, Load) pipelines:
- Multi-source data extraction (files, databases, APIs)
- Complex data transformations and validation
- Multiple output formats and destinations
- Error handling and data quality checks
- Performance optimization and monitoring

Usage:
    bazel run //spark/python:etl_pipeline -- --records 50000 --output-path /tmp/etl-results

Examples:
    # Basic ETL pipeline
    bazel run //spark/python:etl_pipeline
    
    # Large-scale ETL with custom output
    bazel run //spark/python:etl_pipeline -- --records 1000000 --output-path /tmp/warehouse
"""

import sys
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
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
    from pyspark.sql import DataFrame, Row
    from pyspark.sql.functions import (
        col,
        when,
        lit,
        concat,
        concat_ws,
        split,
        regexp_replace,
        regexp_extract,
        length,
        substring,
        upper,
        lower,
        trim,
        ltrim,
        rtrim,
        year,
        month,
        dayofmonth,
        hour,
        minute,
        second,
        date_format,
        date_add,
        date_sub,
        datediff,
        current_date,
        current_timestamp,
        unix_timestamp,
        count,
        sum as spark_sum,
        avg,
        max as spark_max,
        min as spark_min,
        stddev,
        variance,
        collect_list,
        collect_set,
        rank,
        dense_rank,
        row_number,
        lag,
        lead,
        coalesce,
        greatest,
        least,
        isnan,
        isnull,
        hash,
        md5,
        sha1,
        crc32,
        round as spark_round,
        ceil,
        floor,
        abs as spark_abs,
        array,
        explode,
        posexplode,
        map_keys,
        map_values,
        struct,
        get_json_object,
        from_json,
        to_json,
        broadcast,
    )
    from pyspark.sql.types import (
        StructType,
        StructField,
        StringType,
        IntegerType,
        DoubleType,
        TimestampType,
        BooleanType,
        DateType,
    )
    from pyspark.sql.window import Window
except ImportError:
    print("ERROR: PySpark not found. Install with: pip install pyspark")
    sys.exit(1)


class ETLPipeline:
    """
    Comprehensive ETL Pipeline with multi-stage processing.
    """

    def __init__(self, spark, config: SparkConfig):
        self.spark = spark
        self.config = config
        self.metrics = {
            "extraction": {},
            "transformation": {},
            "loading": {},
            "data_quality": {},
        }
        self.start_time = time.time()

    @handle_errors
    def extract_data_sources(self, num_records: int) -> Dict[str, DataFrame]:
        """
        Extract data from multiple sources (simulated).

        Args:
            num_records: Number of records to generate for each source

        Returns:
            Dictionary of source DataFrames
        """
        print("\n🔄 EXTRACT: Loading data from multiple sources...")

        sources = {}

        # 1. Transactional data (sales)
        print("   Loading sales transactions...")
        sales_df = generate_sample_data(self.spark, num_records)
        sources["sales"] = sales_df
        self.metrics["extraction"]["sales"] = sales_df.count()

        # 2. Customer data (simulated)
        print("   Loading customer data...")
        customers_data = []
        for i in range(1, min(10001, num_records // 10)):
            customer = Row(
                customer_id=f"cust_{i}",
                user_id=f"user_{i}",
                full_name=f"Customer {i}",
                email=f"customer{i}@example.com",
                phone=f"+1-555-{1000+i:04d}",
                address=f"{i*10} Main St",
                city=["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"][
                    i % 5
                ],
                state=["NY", "CA", "IL", "TX", "AZ"][i % 5],
                zip_code=f"{10000 + (i % 90000):05d}",
                country="USA",
                registration_date=datetime.now() - timedelta(days=i % 1000),
                last_login=datetime.now() - timedelta(hours=i % 720),
                is_active=i % 20 != 0,
                customer_segment=["Premium", "Standard", "Basic"][i % 3],
                lifetime_value=round(100 + (i * 5.5), 2),
            )
            customers_data.append(customer)

        customers_df = self.spark.createDataFrame(customers_data)
        sources["customers"] = customers_df
        self.metrics["extraction"]["customers"] = customers_df.count()

        # 3. Product catalog (simulated)
        print("   Loading product catalog...")
        products_data = []
        categories = ["ELECTRONICS", "CLOTHING", "BOOKS", "HOME", "SPORTS"]
        suppliers = [f"Supplier_{i}" for i in range(1, 51)]

        for i in range(1, min(50001, num_records // 20)):
            product = Row(
                product_id=f"prod_{i}",
                sku=f"SKU-{i:06d}",
                name=f"Product {i}",
                description=f"High-quality product {i} with advanced features",
                category=categories[i % 5],
                subcategory=f"Sub_{categories[i % 5]}_{(i % 10) + 1}",
                brand=f"Brand_{(i % 100) + 1}",
                supplier=suppliers[i % 50],
                cost_price=round(10 + (i % 500), 2),
                retail_price=round(15 + (i % 750), 2),
                weight_kg=round(0.1 + (i % 50), 2),
                dimensions=f"{i%50}x{i%30}x{i%20} cm",
                color=["Red", "Blue", "Green", "Black", "White"][i % 5],
                size=["XS", "S", "M", "L", "XL", "XXL"][i % 6],
                is_available=i % 25 != 0,
                stock_quantity=i % 1000,
                created_date=datetime.now() - timedelta(days=i % 2000),
                last_updated=datetime.now() - timedelta(hours=i % 168),
            )
            products_data.append(product)

        products_df = self.spark.createDataFrame(products_data)
        sources["products"] = products_df
        self.metrics["extraction"]["products"] = products_df.count()

        # 4. Web analytics (simulated)
        print("   Loading web analytics data...")
        web_analytics_data = []
        for i in range(num_records // 5):
            analytics = Row(
                session_id=f"session_{i}",
                user_id=f"user_{(i % 50000) + 1}",
                page_url=f"/page/{(i % 100) + 1}",
                referrer=["google.com", "facebook.com", "direct", "email", "other"][
                    i % 5
                ],
                device_type=["desktop", "mobile", "tablet"][i % 3],
                browser=["Chrome", "Firefox", "Safari", "Edge"][i % 4],
                os=["Windows", "macOS", "Linux", "iOS", "Android"][i % 5],
                country=["USA", "Canada", "UK", "Germany", "France"][i % 5],
                timestamp=datetime.now() - timedelta(seconds=i % 604800),  # Last week
                duration_seconds=30 + (i % 600),
                bounce_rate=i % 10 == 0,
                conversion=i % 50 == 0,
            )
            web_analytics_data.append(analytics)

        web_analytics_df = self.spark.createDataFrame(web_analytics_data)
        sources["web_analytics"] = web_analytics_df
        self.metrics["extraction"]["web_analytics"] = web_analytics_df.count()

        print(f"   ✅ Extracted {len(sources)} data sources:")
        for source, df in sources.items():
            print(f"      {source}: {df.count():,} records")

        return sources

    @handle_errors
    def transform_data(self, sources: Dict[str, DataFrame]) -> Dict[str, DataFrame]:
        """
        Apply comprehensive data transformations.

        Args:
            sources: Dictionary of source DataFrames

        Returns:
            Dictionary of transformed DataFrames
        """
        print("\n🔄 TRANSFORM: Applying data transformations...")

        transformed = {}

        # 1. Sales data transformations
        print("   Transforming sales data...")
        sales_transformed = (
            sources["sales"]
            .withColumn("sale_date", date_format(col("timestamp"), "yyyy-MM-dd"))
            .withColumn("sale_hour", hour(col("timestamp")))
            .withColumn("total_amount", col("price") * col("quantity"))
            .withColumn(
                "discount_amount",
                when(col("total_amount") > 1000, col("total_amount") * 0.1)
                .when(col("total_amount") > 500, col("total_amount") * 0.05)
                .otherwise(0),
            )
            .withColumn("final_amount", col("total_amount") - col("discount_amount"))
            .withColumn(
                "profit_margin",
                when(col("category") == "ELECTRONICS", 0.15)
                .when(col("category") == "CLOTHING", 0.40)
                .when(col("category") == "BOOKS", 0.20)
                .when(col("category") == "HOME", 0.25)
                .otherwise(0.30),
            )
            .withColumn("estimated_profit", col("final_amount") * col("profit_margin"))
            .withColumn("customer_id", regexp_replace(col("user_id"), "user_", "cust_"))
            .withColumn(
                "order_id",
                concat(
                    lit("ORD-"),
                    date_format(col("timestamp"), "yyyyMMdd"),
                    lit("-"),
                    hash(col("user_id"), col("timestamp")).cast("string"),
                ),
            )
            .filter(col("price") > 0)
            .filter(col("quantity") > 0)
        )

        transformed["sales_fact"] = sales_transformed
        self.metrics["transformation"]["sales_fact"] = sales_transformed.count()

        # 2. Customer dimension transformations
        print("   Transforming customer data...")
        customers_transformed = (
            sources["customers"]
            .withColumn(
                "full_name_clean",
                concat(
                    upper(substring(col("full_name"), 1, 1)),
                    lower(substring(col("full_name"), 2, 100)),
                ),
            )
            .withColumn("email_domain", regexp_extract(col("email"), "@(.+)", 1))
            .withColumn("phone_clean", regexp_replace(col("phone"), "[^0-9]", ""))
            .withColumn(
                "days_since_registration",
                datediff(current_date(), col("registration_date")),
            )
            .withColumn(
                "days_since_last_login", datediff(current_date(), col("last_login"))
            )
            .withColumn(
                "customer_age_category",
                when(col("days_since_registration") < 30, "New")
                .when(col("days_since_registration") < 365, "Regular")
                .otherwise("Veteran"),
            )
            .withColumn(
                "activity_status",
                when(col("days_since_last_login") <= 7, "Highly Active")
                .when(col("days_since_last_login") <= 30, "Active")
                .when(col("days_since_last_login") <= 90, "Inactive")
                .otherwise("Dormant"),
            )
            .withColumn(
                "lifetime_value_tier",
                when(col("lifetime_value") >= 1000, "High Value")
                .when(col("lifetime_value") >= 500, "Medium Value")
                .otherwise("Low Value"),
            )
        )

        transformed["customer_dim"] = customers_transformed
        self.metrics["transformation"]["customer_dim"] = customers_transformed.count()

        # 3. Product dimension transformations
        print("   Transforming product data...")
        products_transformed = (
            sources["products"]
            .withColumn(
                "markup_percentage",
                round(
                    (col("retail_price") - col("cost_price")) / col("cost_price") * 100,
                    2,
                ),
            )
            .withColumn(
                "price_tier",
                when(col("retail_price") >= 500, "Premium")
                .when(col("retail_price") >= 100, "Standard")
                .otherwise("Budget"),
            )
            .withColumn(
                "availability_status",
                when(col("stock_quantity") == 0, "Out of Stock")
                .when(col("stock_quantity") < 10, "Low Stock")
                .when(col("stock_quantity") < 50, "Medium Stock")
                .otherwise("High Stock"),
            )
            .withColumn(
                "product_age_days", datediff(current_date(), col("created_date"))
            )
            .withColumn(
                "product_lifecycle",
                when(col("product_age_days") < 30, "New Launch")
                .when(col("product_age_days") < 365, "Current")
                .when(col("product_age_days") < 1095, "Mature")
                .otherwise("Legacy"),
            )
            .withColumn("sku_category", substring(col("sku"), 1, 3))
            .withColumn(
                "weight_category",
                when(col("weight_kg") < 1, "Light")
                .when(col("weight_kg") < 5, "Medium")
                .otherwise("Heavy"),
            )
        )

        transformed["product_dim"] = products_transformed
        self.metrics["transformation"]["product_dim"] = products_transformed.count()

        # 4. Web analytics transformations
        print("   Transforming web analytics data...")
        web_transformed = (
            sources["web_analytics"]
            .withColumn("session_date", date_format(col("timestamp"), "yyyy-MM-dd"))
            .withColumn("session_hour", hour(col("timestamp")))
            .withColumn(
                "duration_category",
                when(col("duration_seconds") < 30, "Quick View")
                .when(col("duration_seconds") < 120, "Browse")
                .when(col("duration_seconds") < 300, "Engaged")
                .otherwise("Deep Dive"),
            )
            .withColumn(
                "traffic_source",
                when(col("referrer").contains("google"), "Search")
                .when(col("referrer").contains("facebook"), "Social")
                .when(col("referrer") == "direct", "Direct")
                .when(col("referrer") == "email", "Email")
                .otherwise("Other"),
            )
            .withColumn(
                "device_category",
                when(col("device_type") == "mobile", "Mobile")
                .when(col("device_type") == "tablet", "Tablet")
                .otherwise("Desktop"),
            )
            .withColumn(
                "page_category", regexp_extract(col("page_url"), "/([^/]+)/", 1)
            )
            .withColumn("is_weekend", dayofmonth(col("timestamp")) % 7 < 2)
        )

        transformed["web_analytics_fact"] = web_transformed
        self.metrics["transformation"]["web_analytics_fact"] = web_transformed.count()

        # 5. Create aggregated tables
        print("   Creating aggregated dimensions...")

        # Daily sales summary
        daily_sales = sales_transformed.groupBy("sale_date", "category").agg(
            count("*").alias("transaction_count"),
            spark_sum("final_amount").alias("total_revenue"),
            spark_sum("estimated_profit").alias("total_profit"),
            avg("final_amount").alias("avg_transaction_value"),
            count("customer_id").alias("unique_customers"),
        )

        transformed["daily_sales_agg"] = daily_sales
        self.metrics["transformation"]["daily_sales_agg"] = daily_sales.count()

        # Customer summary
        customer_summary = (
            sales_transformed.groupBy("customer_id")
            .agg(
                count("*").alias("total_orders"),
                spark_sum("final_amount").alias("total_spent"),
                spark_sum("estimated_profit").alias("total_profit_generated"),
                avg("final_amount").alias("avg_order_value"),
                max("timestamp").alias("last_order_date"),
                min("timestamp").alias("first_order_date"),
                collect_set("category").alias("purchased_categories"),
            )
            .withColumn(
                "customer_tenure_days",
                datediff(col("last_order_date"), col("first_order_date")),
            )
            .withColumn(
                "order_frequency",
                when(
                    col("customer_tenure_days") > 0,
                    col("total_orders") / (col("customer_tenure_days") / 30),
                ).otherwise(col("total_orders")),
            )
        )

        transformed["customer_summary"] = customer_summary
        self.metrics["transformation"]["customer_summary"] = customer_summary.count()

        print(f"   ✅ Transformed {len(transformed)} datasets:")
        for name, df in transformed.items():
            print(f"      {name}: {df.count():,} records")

        return transformed

    @handle_errors
    def data_quality_checks(self, transformed: Dict[str, DataFrame]) -> Dict[str, Any]:
        """
        Perform comprehensive data quality validation.

        Args:
            transformed: Dictionary of transformed DataFrames

        Returns:
            Dictionary containing data quality metrics
        """
        print("\n🔄 VALIDATE: Performing data quality checks...")

        quality_results = {}

        for table_name, df in transformed.items():
            print(f"   Checking {table_name}...")

            table_quality = {
                "total_records": df.count(),
                "column_count": len(df.columns),
                "null_checks": {},
                "business_rules": {},
                "data_types": {},
                "duplicates": {},
            }

            # Null value analysis
            for column in df.columns:
                null_count = df.filter(col(column).isNull()).count()
                table_quality["null_checks"][column] = {
                    "null_count": null_count,
                    "null_percentage": (
                        round(null_count / table_quality["total_records"] * 100, 2)
                        if table_quality["total_records"] > 0
                        else 0
                    ),
                }

            # Duplicate analysis
            if table_quality["total_records"] > 0:
                unique_count = df.dropDuplicates().count()
                duplicate_count = table_quality["total_records"] - unique_count
                table_quality["duplicates"] = {
                    "unique_records": unique_count,
                    "duplicate_count": duplicate_count,
                    "duplicate_percentage": round(
                        duplicate_count / table_quality["total_records"] * 100, 2
                    ),
                }

            # Table-specific business rules
            if table_name == "sales_fact":
                # Sales fact table validations
                table_quality["business_rules"]["negative_amounts"] = df.filter(
                    col("final_amount") < 0
                ).count()
                table_quality["business_rules"]["zero_quantities"] = df.filter(
                    col("quantity") <= 0
                ).count()
                table_quality["business_rules"]["future_dates"] = df.filter(
                    col("timestamp") > current_timestamp()
                ).count()
                table_quality["business_rules"]["invalid_discounts"] = df.filter(
                    col("discount_amount") < 0
                ).count()

            elif table_name == "customer_dim":
                # Customer dimension validations
                table_quality["business_rules"]["invalid_emails"] = df.filter(
                    ~col("email").contains("@")
                ).count()
                table_quality["business_rules"]["future_registrations"] = df.filter(
                    col("registration_date") > current_date()
                ).count()
                table_quality["business_rules"]["negative_lifetime_value"] = df.filter(
                    col("lifetime_value") < 0
                ).count()

            elif table_name == "product_dim":
                # Product dimension validations
                table_quality["business_rules"]["negative_prices"] = df.filter(
                    col("retail_price") <= 0
                ).count()
                table_quality["business_rules"]["negative_stock"] = df.filter(
                    col("stock_quantity") < 0
                ).count()
                table_quality["business_rules"]["cost_higher_than_retail"] = df.filter(
                    col("cost_price") > col("retail_price")
                ).count()

            quality_results[table_name] = table_quality

        # Calculate overall quality score
        total_issues = 0
        total_records = 0

        for table_quality in quality_results.values():
            total_records += table_quality["total_records"]
            total_issues += table_quality["duplicates"].get("duplicate_count", 0)
            total_issues += sum(table_quality["business_rules"].values())

            # Count significant null issues (>5% null rate)
            for null_info in table_quality["null_checks"].values():
                if null_info["null_percentage"] > 5:
                    total_issues += null_info["null_count"]

        overall_quality_score = (
            max(0, 100 - (total_issues / total_records * 100))
            if total_records > 0
            else 100
        )
        quality_results["overall_quality_score"] = round(overall_quality_score, 2)

        self.metrics["data_quality"] = quality_results

        print(f"   ✅ Data quality checks completed")
        print(f"      Overall Quality Score: {overall_quality_score:.1f}%")
        print(f"      Total Issues Found: {total_issues:,}")

        return quality_results

    @handle_errors
    def load_data(self, transformed: Dict[str, DataFrame], output_path: str):
        """
        Load transformed data to multiple destinations.

        Args:
            transformed: Dictionary of transformed DataFrames
            output_path: Base output path
        """
        print(f"\n🔄 LOAD: Saving transformed data to {output_path}...")

        try:
            # 1. Save fact tables (partitioned for performance)
            print("   Saving fact tables...")

            # Sales fact table - partitioned by date and category
            sales_fact = transformed["sales_fact"]
            sales_fact.write.mode("overwrite").partitionBy(
                "sale_date", "category"
            ).parquet(f"{output_path}/fact/sales")

            self.metrics["loading"]["sales_fact"] = sales_fact.count()
            print(f"      ✅ sales_fact: {sales_fact.count():,} records")

            # Web analytics fact table - partitioned by date
            web_fact = transformed["web_analytics_fact"]
            web_fact.write.mode("overwrite").partitionBy("session_date").parquet(
                f"{output_path}/fact/web_analytics"
            )

            self.metrics["loading"]["web_analytics_fact"] = web_fact.count()
            print(f"      ✅ web_analytics_fact: {web_fact.count():,} records")

            # 2. Save dimension tables
            print("   Saving dimension tables...")

            # Customer dimension
            customer_dim = transformed["customer_dim"]
            customer_dim.write.mode("overwrite").parquet(f"{output_path}/dim/customers")

            self.metrics["loading"]["customer_dim"] = customer_dim.count()
            print(f"      ✅ customer_dim: {customer_dim.count():,} records")

            # Product dimension
            product_dim = transformed["product_dim"]
            product_dim.write.mode("overwrite").parquet(f"{output_path}/dim/products")

            self.metrics["loading"]["product_dim"] = product_dim.count()
            print(f"      ✅ product_dim: {product_dim.count():,} records")

            # 3. Save aggregated tables
            print("   Saving aggregated tables...")

            # Daily sales aggregates
            daily_sales = transformed["daily_sales_agg"]
            daily_sales.write.mode("overwrite").parquet(
                f"{output_path}/agg/daily_sales"
            )

            self.metrics["loading"]["daily_sales_agg"] = daily_sales.count()
            print(f"      ✅ daily_sales_agg: {daily_sales.count():,} records")

            # Customer summary
            customer_summary = transformed["customer_summary"]
            customer_summary.write.mode("overwrite").parquet(
                f"{output_path}/agg/customer_summary"
            )

            self.metrics["loading"]["customer_summary"] = customer_summary.count()
            print(f"      ✅ customer_summary: {customer_summary.count():,} records")

            # 4. Save as CSV for external consumption
            print("   Saving CSV exports...")

            # Top-level summary for business users
            business_summary = daily_sales.groupBy("category").agg(
                spark_sum("total_revenue").alias("category_revenue"),
                spark_sum("transaction_count").alias("category_transactions"),
                avg("avg_transaction_value").alias("avg_transaction_value"),
            )

            business_summary.coalesce(1).write.mode("overwrite").csv(
                f"{output_path}/export/business_summary", header=True
            )

            # Top customers export
            top_customers = customer_summary.orderBy(col("total_spent").desc()).limit(
                100
            )
            top_customers.coalesce(1).write.mode("overwrite").csv(
                f"{output_path}/export/top_customers", header=True
            )

            print(f"   ✅ All data loaded successfully to: {output_path}")

        except Exception as e:
            print(f"   ❌ Error loading data: {e}")
            raise

    @handle_errors
    def generate_pipeline_report(
        self, quality_results: Dict[str, Any], output_path: str
    ):
        """
        Generate a comprehensive ETL pipeline report.

        Args:
            quality_results: Data quality validation results
            output_path: Output path for the report
        """
        print("\n🔄 Generating ETL pipeline report...")

        end_time = time.time()
        total_duration = end_time - self.start_time

        report = {
            "pipeline_execution": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "end_time": datetime.fromtimestamp(end_time).isoformat(),
                "total_duration_seconds": round(total_duration, 2),
                "status": "COMPLETED",
            },
            "stage_metrics": self.metrics,
            "data_quality": quality_results,
            "performance_metrics": {
                "total_records_processed": sum(self.metrics["extraction"].values()),
                "records_per_second": sum(self.metrics["extraction"].values())
                / total_duration,
                "total_output_records": sum(self.metrics["loading"].values()),
            },
        }

        # Save report as JSON
        report_path = f"{output_path}/pipeline_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        print(f"   ✅ Pipeline report saved: {report_path}")

        # Print summary
        self.print_pipeline_summary(report)

    def print_pipeline_summary(self, report: Dict[str, Any]):
        """Print a comprehensive pipeline summary."""

        print("\n" + "=" * 70)
        print("📊 ETL PIPELINE EXECUTION SUMMARY")
        print("=" * 70)

        # Execution summary
        exec_info = report["pipeline_execution"]
        print(f"\n⏱️  EXECUTION TIME:")
        print(f"   Duration: {exec_info['total_duration_seconds']:.2f} seconds")
        print(f"   Status: {exec_info['status']}")

        # Processing metrics
        perf = report["performance_metrics"]
        print(f"\n📈 PERFORMANCE METRICS:")
        print(f"   Total Records Processed: {perf['total_records_processed']:,}")
        print(f"   Processing Rate: {perf['records_per_second']:,.0f} records/second")
        print(f"   Output Records: {perf['total_output_records']:,}")

        # Stage breakdown
        print(f"\n🔄 STAGE BREAKDOWN:")
        for stage, metrics in report["stage_metrics"].items():
            if stage != "data_quality" and isinstance(metrics, dict):
                total = sum(metrics.values()) if metrics else 0
                print(f"   {stage.title()}: {total:,} records")
                for source, count in metrics.items():
                    print(f"     - {source}: {count:,}")

        # Data quality summary
        quality_score = report["data_quality"].get("overall_quality_score", 0)
        print(f"\n✅ DATA QUALITY:")
        print(f"   Overall Quality Score: {quality_score:.1f}%")

        if quality_score >= 95:
            print(f"   Status: 🟢 EXCELLENT")
        elif quality_score >= 85:
            print(f"   Status: 🟡 GOOD")
        elif quality_score >= 70:
            print(f"   Status: 🟠 FAIR")
        else:
            print(f"   Status: 🔴 POOR")

        print("\n" + "=" * 70)


@handle_errors
def main():
    """Main ETL pipeline workflow."""
    # Parse arguments
    parser = parse_common_args()
    args = parser.parse_args()

    print("🚀 Starting Comprehensive ETL Pipeline")
    print(f"   Records to process: {args.records:,}")
    print(f"   Output path: {args.output_path}")
    print(f"   Master: {args.master}")

    # Create Spark session with ETL optimizations
    config = SparkConfig(
        app_name=f"{args.app_name}_ETL_Pipeline",
        master=args.master,
        executor_memory=args.executor_memory,
        executor_cores=args.executor_cores,
    )

    spark = create_spark_session(config)

    # Enable ETL-specific optimizations
    spark.conf.set("spark.sql.adaptive.enabled", "true")
    spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
    spark.conf.set("spark.serializer", "org.apache.spark.serializer.KryoSerializer")

    try:
        # Initialize ETL pipeline
        pipeline = ETLPipeline(spark, config)

        # Execute ETL stages
        print("\n🔄 Executing ETL Pipeline...")

        # EXTRACT
        sources = pipeline.extract_data_sources(args.records)

        # TRANSFORM
        transformed = pipeline.transform_data(sources)

        # VALIDATE
        quality_results = pipeline.data_quality_checks(transformed)

        # LOAD
        pipeline.load_data(transformed, args.output_path)

        # REPORT
        pipeline.generate_pipeline_report(quality_results, args.output_path)

        # Monitor performance
        monitor_job_progress(spark, "ETL Pipeline")

        print(f"\n✅ ETL Pipeline completed successfully!")
        print(f"   Processed {args.records:,} source records")
        print(
            f"   Generated {sum(pipeline.metrics['loading'].values()):,} output records"
        )
        print(f"   Data quality score: {quality_results['overall_quality_score']:.1f}%")
        print(f"   Results saved to: {args.output_path}")
        print(f"   Pipeline report: {args.output_path}/pipeline_report.json")

    finally:
        cleanup_session(spark)


if __name__ == "__main__":
    main()
