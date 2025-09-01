#!/usr/bin/env python3
"""
Spark SQL Examples - Building Block Application

This module demonstrates advanced SQL capabilities with Apache Spark:
- Complex analytical queries with window functions
- Data transformation and ETL operations
- Performance optimization techniques
- Integration with different data sources
- Advanced SQL features (CTEs, UDFs, etc.)

Usage:
    bazel run //spark/python:sql_queries -- --records 100000

Examples:
    # Basic SQL analytics
    bazel run //spark/python:sql_queries
    
    # Large dataset analysis
    bazel run //spark/python:sql_queries -- --records 1000000
    
    # Custom queries with output
    bazel run //spark/python:sql_queries -- --output-path /tmp/sql-results
"""

import sys
import time
from datetime import datetime, timedelta
from spark_common import (
    SparkConfig, create_spark_session, generate_sample_data,
    monitor_job_progress, cleanup_session, print_dataframe_summary,
    parse_common_args, handle_errors
)

try:
    from pyspark.sql import DataFrame, Row
    from pyspark.sql.functions import (
        col, when, lit, concat, concat_ws, split, 
        regexp_replace, regexp_extract, length, substring,
        upper, lower, trim, ltrim, rtrim,
        year, month, dayofmonth, hour, minute, second,
        date_format, date_add, date_sub, datediff,
        current_date, current_timestamp, unix_timestamp,
        count, sum as spark_sum, avg, max as spark_max, min as spark_min,
        stddev, variance, collect_list, collect_set,
        rank, dense_rank, row_number, lag, lead,
        first, last, ntile, percent_rank,
        round as spark_round, ceil, floor, abs as spark_abs,
        coalesce, greatest, least, isnan, isnull,
        array, explode, posexplode, map_keys, map_values,
        struct, get_json_object, from_json, to_json,
        udf
    )
    from pyspark.sql.types import (
        StringType, IntegerType, DoubleType, BooleanType, ArrayType
    )
    from pyspark.sql.window import Window
except ImportError:
    print("ERROR: PySpark not found. Install with: pip install pyspark")
    sys.exit(1)


@handle_errors
def setup_sample_tables(spark, num_records: int):
    """
    Create sample tables for SQL demonstrations.
    
    Args:
        spark: SparkSession
        num_records: Number of records to generate
    """
    print(f"\n🔄 Setting up sample tables with {num_records:,} records...")
    
    # Generate main dataset
    df = generate_sample_data(spark, num_records)
    
    # Create temporary views for SQL queries
    df.createOrReplaceTempView("sales")
    print("   ✅ Created 'sales' table")
    
    # Create users table
    users_data = []
    for i in range(1, 1001):  # 1000 users
        user = Row(
            user_id=f"user_{i}",
            name=f"User {i}",
            email=f"user{i}@example.com",
            registration_date=datetime.now() - timedelta(days=i % 365),
            age=20 + (i % 60),
            city=["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"][i % 5],
            is_premium=i % 10 == 0  # 10% premium users
        )
        users_data.append(user)
    
    users_df = spark.createDataFrame(users_data)
    users_df.createOrReplaceTempView("users")
    print("   ✅ Created 'users' table")
    
    # Create products table
    products_data = []
    categories = ["ELECTRONICS", "CLOTHING", "BOOKS", "HOME", "SPORTS"]
    for i in range(1, 10001):  # 10000 products
        product = Row(
            product_id=f"prod_{i}",
            name=f"Product {i}",
            category=categories[i % 5],
            base_price=10.0 + (i % 1000),
            supplier=f"Supplier {(i % 100) + 1}",
            in_stock=i % 20 != 0,  # 95% in stock
            launch_date=datetime.now() - timedelta(days=(i % 1000))
        )
        products_data.append(product)
    
    products_df = spark.createDataFrame(products_data)
    products_df.createOrReplaceTempView("products")
    print("   ✅ Created 'products' table")
    
    # Show table schemas
    print("\n📋 Table Schemas:")
    print("   Sales table:")
    spark.sql("DESCRIBE sales").show()
    print("   Users table:")
    spark.sql("DESCRIBE users").show()
    print("   Products table:")
    spark.sql("DESCRIBE products").show()


@handle_errors
def basic_sql_queries(spark) -> dict:
    """
    Execute basic SQL queries for analytics.
    
    Args:
        spark: SparkSession
        
    Returns:
        Dictionary of query results
    """
    print("\n🔄 Executing basic SQL queries...")
    
    results = {}
    
    # 1. Sales summary
    print("   1. Sales summary by category...")
    sales_summary = spark.sql("""
        SELECT 
            category,
            COUNT(*) as order_count,
            SUM(price * quantity) as total_revenue,
            AVG(price * quantity) as avg_order_value,
            MIN(price * quantity) as min_order_value,
            MAX(price * quantity) as max_order_value
        FROM sales
        WHERE price > 0 AND quantity > 0
        GROUP BY category
        ORDER BY total_revenue DESC
    """)
    results["sales_summary"] = sales_summary
    
    # 2. Top customers
    print("   2. Top customers by revenue...")
    top_customers = spark.sql("""
        SELECT 
            s.user_id,
            u.name,
            u.city,
            u.is_premium,
            COUNT(*) as total_orders,
            SUM(s.price * s.quantity) as total_spent,
            AVG(s.price * s.quantity) as avg_order_value
        FROM sales s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.user_id, u.name, u.city, u.is_premium
        ORDER BY total_spent DESC
        LIMIT 20
    """)
    results["top_customers"] = top_customers
    
    # 3. Daily trends
    print("   3. Daily sales trends...")
    daily_trends = spark.sql("""
        SELECT 
            DATE(timestamp) as sale_date,
            COUNT(*) as daily_orders,
            SUM(price * quantity) as daily_revenue,
            COUNT(DISTINCT user_id) as unique_customers,
            AVG(price * quantity) as avg_order_value
        FROM sales
        GROUP BY DATE(timestamp)
        ORDER BY sale_date DESC
        LIMIT 30
    """)
    results["daily_trends"] = daily_trends
    
    # 4. Product performance
    print("   4. Product performance analysis...")
    product_performance = spark.sql("""
        SELECT 
            p.product_id,
            p.name,
            p.category,
            p.base_price,
            COUNT(s.product_id) as times_sold,
            SUM(s.quantity) as total_quantity_sold,
            SUM(s.price * s.quantity) as total_revenue,
            AVG(s.price) as avg_selling_price,
            (AVG(s.price) - p.base_price) / p.base_price * 100 as price_markup_pct
        FROM products p
        LEFT JOIN sales s ON p.product_id = s.product_id
        GROUP BY p.product_id, p.name, p.category, p.base_price
        HAVING COUNT(s.product_id) > 0
        ORDER BY total_revenue DESC
        LIMIT 50
    """)
    results["product_performance"] = product_performance
    
    return results


@handle_errors
def advanced_sql_queries(spark) -> dict:
    """
    Execute advanced SQL queries with window functions and CTEs.
    
    Args:
        spark: SparkSession
        
    Returns:
        Dictionary of advanced query results
    """
    print("\n🔄 Executing advanced SQL queries...")
    
    results = {}
    
    # 1. Customer cohort analysis with CTEs
    print("   1. Customer cohort analysis...")
    cohort_analysis = spark.sql("""
        WITH first_purchase AS (
            SELECT 
                user_id,
                DATE(MIN(timestamp)) as first_purchase_date,
                DATE_TRUNC('month', MIN(timestamp)) as cohort_month
            FROM sales
            GROUP BY user_id
        ),
        user_activities AS (
            SELECT 
                s.user_id,
                fp.cohort_month,
                fp.first_purchase_date,
                DATE_TRUNC('month', s.timestamp) as activity_month,
                SUM(s.price * s.quantity) as monthly_revenue
            FROM sales s
            JOIN first_purchase fp ON s.user_id = fp.user_id
            GROUP BY s.user_id, fp.cohort_month, fp.first_purchase_date, DATE_TRUNC('month', s.timestamp)
        )
        SELECT 
            cohort_month,
            activity_month,
            COUNT(DISTINCT user_id) as active_users,
            SUM(monthly_revenue) as cohort_revenue,
            AVG(monthly_revenue) as avg_revenue_per_user
        FROM user_activities
        GROUP BY cohort_month, activity_month
        ORDER BY cohort_month, activity_month
    """)
    results["cohort_analysis"] = cohort_analysis
    
    # 2. Running totals and window functions
    print("   2. Running totals and rankings...")
    running_analytics = spark.sql("""
        SELECT 
            user_id,
            timestamp,
            price * quantity as order_value,
            SUM(price * quantity) OVER (
                PARTITION BY user_id 
                ORDER BY timestamp 
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) as running_total,
            ROW_NUMBER() OVER (
                PARTITION BY user_id 
                ORDER BY timestamp
            ) as order_sequence,
            LAG(price * quantity, 1) OVER (
                PARTITION BY user_id 
                ORDER BY timestamp
            ) as previous_order_value,
            LEAD(price * quantity, 1) OVER (
                PARTITION BY user_id 
                ORDER BY timestamp
            ) as next_order_value,
            RANK() OVER (
                PARTITION BY DATE(timestamp) 
                ORDER BY price * quantity DESC
            ) as daily_rank
        FROM sales
        WHERE user_id IN (
            SELECT user_id 
            FROM sales 
            GROUP BY user_id 
            HAVING COUNT(*) >= 5
        )
        ORDER BY user_id, timestamp
    """)
    results["running_analytics"] = running_analytics
    
    # 3. Advanced aggregations with CUBE and ROLLUP
    print("   3. Multi-dimensional aggregations...")
    cube_analysis = spark.sql("""
        SELECT 
            category,
            action,
            is_premium,
            COUNT(*) as transaction_count,
            SUM(price * quantity) as total_revenue,
            AVG(price * quantity) as avg_transaction_value
        FROM sales s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY CUBE(category, action, is_premium)
        ORDER BY 
            CASE WHEN category IS NULL THEN 1 ELSE 0 END,
            category,
            CASE WHEN action IS NULL THEN 1 ELSE 0 END,
            action,
            CASE WHEN is_premium IS NULL THEN 1 ELSE 0 END,
            is_premium
    """)
    results["cube_analysis"] = cube_analysis
    
    # 4. Percentiles and statistical functions
    print("   4. Statistical analysis with percentiles...")
    statistical_analysis = spark.sql("""
        SELECT 
            category,
            COUNT(*) as sample_size,
            AVG(price * quantity) as mean_value,
            STDDEV(price * quantity) as std_deviation,
            PERCENTILE_APPROX(price * quantity, 0.25) as q1,
            PERCENTILE_APPROX(price * quantity, 0.5) as median,
            PERCENTILE_APPROX(price * quantity, 0.75) as q3,
            PERCENTILE_APPROX(price * quantity, 0.9) as p90,
            PERCENTILE_APPROX(price * quantity, 0.95) as p95,
            PERCENTILE_APPROX(price * quantity, 0.99) as p99
        FROM sales
        GROUP BY category
        ORDER BY mean_value DESC
    """)
    results["statistical_analysis"] = statistical_analysis
    
    # 5. Complex string operations and pattern matching
    print("   5. Text analytics with regex...")
    text_analytics = spark.sql("""
        SELECT 
            category,
            COUNT(*) as total_records,
            COUNT(CASE WHEN user_id REGEXP '^user_[0-9]+$' THEN 1 END) as valid_user_ids,
            COUNT(CASE WHEN LENGTH(session_id) > 10 THEN 1 END) as long_sessions,
            COLLECT_SET(SUBSTRING(user_id, 1, 8)) as user_id_prefixes,
            AVG(LENGTH(CAST(price * quantity AS STRING))) as avg_amount_digits
        FROM sales
        GROUP BY category
        ORDER BY category
    """)
    results["text_analytics"] = text_analytics
    
    return results


@handle_errors
def create_custom_udfs(spark):
    """
    Create and register custom User Defined Functions.
    
    Args:
        spark: SparkSession
    """
    print("\n🔄 Creating custom UDFs...")
    
    # 1. Customer tier classification UDF
    def classify_customer_tier(total_spent: float) -> str:
        if total_spent is None:
            return "Unknown"
        elif total_spent >= 5000:
            return "Platinum"
        elif total_spent >= 2000:
            return "Gold"
        elif total_spent >= 500:
            return "Silver"
        else:
            return "Bronze"
    
    tier_udf = udf(classify_customer_tier, StringType())
    spark.udf.register("classify_tier", tier_udf)
    
    # 2. Price category UDF
    def categorize_price(price: float) -> str:
        if price is None:
            return "Unknown"
        elif price >= 500:
            return "Premium"
        elif price >= 100:
            return "Standard"
        else:
            return "Budget"
    
    price_category_udf = udf(categorize_price, StringType())
    spark.udf.register("categorize_price", price_category_udf)
    
    # 3. Order complexity score UDF
    def calculate_complexity_score(quantity: int, price: float, category: str) -> int:
        if any(x is None for x in [quantity, price, category]):
            return 0
        
        base_score = quantity * (price / 100)
        
        # Category multipliers
        multipliers = {
            "ELECTRONICS": 1.5,
            "CLOTHING": 1.0,
            "BOOKS": 0.8,
            "HOME": 1.2,
            "SPORTS": 1.1
        }
        
        multiplier = multipliers.get(category, 1.0)
        return int(base_score * multiplier)
    
    complexity_udf = udf(calculate_complexity_score, IntegerType())
    spark.udf.register("complexity_score", complexity_udf)
    
    print("   ✅ Registered UDFs: classify_tier, categorize_price, complexity_score")


@handle_errors
def udf_based_queries(spark) -> dict:
    """
    Execute queries using custom UDFs.
    
    Args:
        spark: SparkSession
        
    Returns:
        Dictionary of UDF-based query results
    """
    print("\n🔄 Executing UDF-based queries...")
    
    results = {}
    
    # 1. Customer tier analysis
    print("   1. Customer tier analysis with UDFs...")
    customer_tiers = spark.sql("""
        SELECT 
            classify_tier(SUM(price * quantity)) as customer_tier,
            COUNT(DISTINCT user_id) as customer_count,
            AVG(SUM(price * quantity)) as avg_spending,
            MIN(SUM(price * quantity)) as min_spending,
            MAX(SUM(price * quantity)) as max_spending
        FROM sales
        GROUP BY user_id
        GROUP BY classify_tier(SUM(price * quantity))
        ORDER BY avg_spending DESC
    """)
    results["customer_tiers"] = customer_tiers
    
    # 2. Price category analysis
    print("   2. Price category performance...")
    price_categories = spark.sql("""
        SELECT 
            category as product_category,
            categorize_price(price) as price_tier,
            COUNT(*) as transaction_count,
            SUM(price * quantity) as total_revenue,
            AVG(quantity) as avg_quantity
        FROM sales
        GROUP BY category, categorize_price(price)
        ORDER BY product_category, total_revenue DESC
    """)
    results["price_categories"] = price_categories
    
    # 3. Order complexity analysis
    print("   3. Order complexity scoring...")
    complexity_analysis = spark.sql("""
        SELECT 
            category,
            complexity_score(quantity, price, category) as complexity,
            COUNT(*) as order_count,
            AVG(price * quantity) as avg_order_value,
            SUM(price * quantity) as total_revenue
        FROM sales
        GROUP BY category, complexity_score(quantity, price, category)
        HAVING complexity > 0
        ORDER BY category, complexity DESC
    """)
    results["complexity_analysis"] = complexity_analysis
    
    return results


@handle_errors
def performance_optimization_queries(spark) -> dict:
    """
    Demonstrate performance optimization techniques.
    
    Args:
        spark: SparkSession
        
    Returns:
        Dictionary of optimization examples
    """
    print("\n🔄 Demonstrating performance optimizations...")
    
    results = {}
    
    # 1. Broadcast join example
    print("   1. Broadcast join optimization...")
    broadcast_query = spark.sql("""
        SELECT /*+ BROADCAST(u) */
            s.category,
            u.city,
            COUNT(*) as order_count,
            SUM(s.price * s.quantity) as total_revenue
        FROM sales s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.category, u.city
        ORDER BY total_revenue DESC
        LIMIT 20
    """)
    results["broadcast_join"] = broadcast_query
    
    # 2. Partition pruning example
    print("   2. Partition-aware query...")
    # Note: This would be more effective with actual partitioned data
    partition_query = spark.sql("""
        SELECT 
            category,
            DATE(timestamp) as date,
            COUNT(*) as daily_orders,
            SUM(price * quantity) as daily_revenue
        FROM sales
        WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), 7)
        GROUP BY category, DATE(timestamp)
        ORDER BY date DESC, daily_revenue DESC
    """)
    results["partition_query"] = partition_query
    
    # 3. Columnar analytics (aggregation pushdown)
    print("   3. Columnar analytics optimization...")
    columnar_query = spark.sql("""
        SELECT 
            category,
            action,
            COUNT(*) as event_count,
            COUNT(DISTINCT user_id) as unique_users,
            MIN(price * quantity) as min_value,
            MAX(price * quantity) as max_value,
            AVG(price * quantity) as avg_value,
            STDDEV(price * quantity) as std_value
        FROM sales
        GROUP BY category, action
        ORDER BY event_count DESC
    """)
    results["columnar_query"] = columnar_query
    
    return results


@handle_errors
def save_sql_results(all_results: dict, output_path: str):
    """
    Save all SQL query results to files.
    
    Args:
        all_results: Dictionary containing all query results
        output_path: Base output path
    """
    print(f"\n🔄 Saving SQL results to {output_path}...")
    
    try:
        for category, results in all_results.items():
            category_path = f"{output_path}/{category}"
            print(f"   Saving {category} results...")
            
            for query_name, df in results.items():
                query_path = f"{category_path}/{query_name}"
                df.coalesce(1).write.mode("overwrite").csv(query_path, header=True)
                print(f"     ✅ {query_name}")
        
        print(f"✅ All SQL results saved to: {output_path}")
        
    except Exception as e:
        print(f"⚠️  Error saving results: {e}")


@handle_errors
def print_sql_summary(all_results: dict):
    """
    Print a summary of all SQL query results.
    
    Args:
        all_results: Dictionary containing all query results
    """
    print("\n" + "="*60)
    print("📊 SQL QUERIES RESULTS SUMMARY")
    print("="*60)
    
    total_queries = sum(len(results) for results in all_results.values())
    print(f"\n📈 Total Queries Executed: {total_queries}")
    
    for category, results in all_results.items():
        print(f"\n🔍 {category.upper().replace('_', ' ')} ({len(results)} queries):")
        
        for query_name, df in results.items():
            try:
                count = df.count()
                print(f"   {query_name}: {count:,} rows")
                
                # Show sample for key results
                if query_name in ["sales_summary", "top_customers", "customer_tiers"] and count > 0:
                    print(f"     Sample data:")
                    sample_data = df.take(3)
                    for row in sample_data:
                        row_dict = row.asDict()
                        key_value = list(row_dict.items())[0]
                        print(f"       {key_value[0]}: {key_value[1]}")
                        
            except Exception as e:
                print(f"   {query_name}: Error getting count - {e}")
    
    print("\n" + "="*60)


@handle_errors
def main():
    """Main SQL workflow."""
    # Parse arguments
    parser = parse_common_args()
    args = parser.parse_args()
    
    print("🚀 Starting Spark SQL Examples")
    print(f"   Records to process: {args.records:,}")
    print(f"   Output path: {args.output_path}")
    print(f"   Master: {args.master}")
    
    # Create Spark session
    config = SparkConfig(
        app_name=f"{args.app_name}_SQL",
        master=args.master,
        executor_memory=args.executor_memory,
        executor_cores=args.executor_cores
    )
    
    spark = create_spark_session(config)
    
    # Enable Spark SQL optimizations
    spark.conf.set("spark.sql.adaptive.enabled", "true")
    spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
    spark.conf.set("spark.sql.cbo.enabled", "true")
    
    try:
        start_time = time.time()
        
        # Setup sample tables
        setup_sample_tables(spark, args.records)
        
        # Create custom UDFs
        create_custom_udfs(spark)
        
        # Execute query categories
        all_results = {}
        
        print("\n🔄 Executing SQL query categories...")
        
        # Basic queries
        all_results["basic_queries"] = basic_sql_queries(spark)
        
        # Advanced queries
        all_results["advanced_queries"] = advanced_sql_queries(spark)
        
        # UDF-based queries
        all_results["udf_queries"] = udf_based_queries(spark)
        
        # Performance optimization examples
        all_results["optimization_queries"] = performance_optimization_queries(spark)
        
        # Save results
        save_sql_results(all_results, args.output_path)
        
        # Monitor performance
        monitor_job_progress(spark, "SQL Queries")
        
        # Print summary
        print_sql_summary(all_results)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n⏱️  Total Processing Time: {processing_time:.2f} seconds")
        print(f"   Records processed: {args.records:,}")
        print(f"   Queries per second: {sum(len(r) for r in all_results.values())/processing_time:.1f}")
        
        print(f"\n✅ SQL examples completed successfully!")
        print(f"   Executed {sum(len(r) for r in all_results.values())} queries")
        print(f"   Results saved to: {args.output_path}")
        print(f"   Spark SQL UI: http://192.168.1.184:4040")
        
    finally:
        cleanup_session(spark)


if __name__ == "__main__":
    main()
