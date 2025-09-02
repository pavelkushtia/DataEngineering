#!/usr/bin/env python3
"""
Flink SQL Streaming Examples - Building Block Application

This module demonstrates declarative stream processing with Flink SQL:
- Stream processing using SQL syntax
- Complex windowing and aggregations in SQL
- Temporal joins and pattern matching
- CDC (Change Data Capture) processing
- Multi-sink streaming pipelines
- Real-time analytics dashboards

Usage:
    bazel run //flink/python:sql_streaming -- --duration 180

Examples:
    # Basic SQL streaming
    bazel run //flink/python:sql_streaming
    
    # Extended duration with custom output
    bazel run //flink/python:sql_streaming -- --duration 300 --output-path /tmp/sql-results
    
    # CDC processing pipeline
    bazel run //flink/python:sql_streaming -- --enable-cdc --duration 600
"""

import sys
import time
import json
import signal
from datetime import datetime, timedelta
from flink_common import (
    FlinkConfig,
    create_flink_environment,
    create_table_environment,
    generate_sample_streaming_data,
    setup_postgres_table,
    monitor_job_progress,
    parse_common_args,
    handle_errors,
    cleanup_environment,
    metrics_tracker,
)

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.table import StreamTableEnvironment, DataTypes, Schema
    from pyflink.table.expressions import lit, col, call
    from pyflink.table.window import Tumble, Slide, Session
    from pyflink.common import Configuration
except ImportError:
    print("ERROR: PyFlink not found. Install with: pip install apache-flink")
    sys.exit(1)


@handle_errors
def setup_kafka_tables(table_env: StreamTableEnvironment, kafka_servers: str):
    """
    Setup Kafka source and sink tables for SQL streaming.

    Args:
        table_env: StreamTableEnvironment
        kafka_servers: Kafka bootstrap servers
    """
    print("\n🔄 Setting up Kafka tables for SQL streaming...")

    # 1. Source table for incoming events
    print("   Creating events source table...")
    events_source_ddl = f"""
    CREATE TABLE events_source (
        event_id STRING,
        user_id STRING,
        session_id STRING,
        product_id STRING,
        category STRING,
        action STRING,
        price DECIMAL(10,2),
        quantity INT,
        timestamp_str STRING,
        metadata ROW<
            source STRING,
            user_agent STRING,
            ip_address STRING
        >,
        event_time AS TO_TIMESTAMP(timestamp_str, 'yyyy-MM-dd''T''HH:mm:ss'),
        WATERMARK FOR event_time AS event_time - INTERVAL '30' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'flink-events',
        'properties.bootstrap.servers' = '{kafka_servers}',
        'properties.group.id' = 'flink-sql-consumer',
        'scan.startup.mode' = 'latest-offset',
        'format' = 'json',
        'json.fail-on-missing-field' = 'false',
        'json.ignore-parse-errors' = 'true'
    )
    """
    table_env.execute_sql(events_source_ddl)

    # 2. Sink table for real-time analytics results
    print("   Creating analytics sink table...")
    analytics_sink_ddl = f"""
    CREATE TABLE analytics_sink (
        window_start TIMESTAMP(3),
        window_end TIMESTAMP(3),
        category STRING,
        total_revenue DECIMAL(12,2),
        order_count BIGINT,
        unique_users BIGINT,
        avg_order_value DECIMAL(10,2),
        max_order_value DECIMAL(10,2)
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'analytics-results',
        'properties.bootstrap.servers' = '{kafka_servers}',
        'format' = 'json'
    )
    """
    table_env.execute_sql(analytics_sink_ddl)

    # 3. Fraud alerts sink table
    print("   Creating fraud alerts sink table...")
    fraud_sink_ddl = f"""
    CREATE TABLE fraud_alerts_sink (
        alert_id STRING,
        user_id STRING,
        event_id STRING,
        fraud_score INT,
        alert_type STRING,
        event_amount DECIMAL(10,2),
        alert_timestamp TIMESTAMP(3)
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'fraud-alerts',
        'properties.bootstrap.servers' = '{kafka_servers}',
        'format' = 'json'
    )
    """
    table_env.execute_sql(fraud_sink_ddl)

    # 4. User sessions sink table
    print("   Creating user sessions sink table...")
    sessions_sink_ddl = f"""
    CREATE TABLE user_sessions_sink (
        session_id STRING,
        user_id STRING,
        session_start TIMESTAMP(3),
        session_end TIMESTAMP(3),
        session_duration_minutes DOUBLE,
        event_count BIGINT,
        total_spent DECIMAL(12,2),
        unique_products BIGINT
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'user-sessions',
        'properties.bootstrap.servers' = '{kafka_servers}',
        'format' = 'json'
    )
    """
    table_env.execute_sql(sessions_sink_ddl)

    print("✅ Kafka tables configured")


@handle_errors
def setup_database_tables(table_env: StreamTableEnvironment, postgres_config: dict):
    """
    Setup PostgreSQL tables for persistent storage.

    Args:
        table_env: StreamTableEnvironment
        postgres_config: Database configuration
    """
    print("\n🔄 Setting up PostgreSQL tables...")

    # 1. Hourly analytics table
    print("   Creating hourly analytics table...")
    hourly_analytics_ddl = f"""
    CREATE TABLE hourly_analytics (
        hour_timestamp TIMESTAMP(3),
        category STRING,
        total_revenue DECIMAL(12,2),
        order_count BIGINT,
        unique_users BIGINT,
        avg_order_value DECIMAL(10,2),
        PRIMARY KEY (hour_timestamp, category) NOT ENFORCED
    ) WITH (
        'connector' = 'jdbc',
        'url' = '{postgres_config["url"]}',
        'table-name' = 'hourly_analytics',
        'username' = '{postgres_config["user"]}',
        'password' = '{postgres_config["password"]}',
        'sink.buffer-flush.max-rows' = '1000',
        'sink.buffer-flush.interval' = '30s',
        'sink.max-retries' = '3'
    )
    """
    table_env.execute_sql(hourly_analytics_ddl)

    # 2. Product performance table
    print("   Creating product performance table...")
    product_performance_ddl = f"""
    CREATE TABLE product_performance (
        window_time TIMESTAMP(3),
        product_id STRING,
        category STRING,
        total_revenue DECIMAL(12,2),
        order_count BIGINT,
        popularity_rank INT,
        PRIMARY KEY (window_time, product_id) NOT ENFORCED
    ) WITH (
        'connector' = 'jdbc',
        'url' = '{postgres_config["url"]}',
        'table-name' = 'product_performance',
        'username' = '{postgres_config["user"]}',
        'password' = '{postgres_config["password"]}',
        'sink.buffer-flush.max-rows' = '500',
        'sink.buffer-flush.interval' = '60s'
    )
    """
    table_env.execute_sql(product_performance_ddl)

    print("✅ PostgreSQL tables configured")


@handle_errors
def setup_cdc_tables(table_env: StreamTableEnvironment, postgres_config: dict):
    """
    Setup CDC (Change Data Capture) tables for real-time data synchronization.

    Args:
        table_env: StreamTableEnvironment
        postgres_config: Database configuration
    """
    print("\n🔄 Setting up CDC tables...")

    # 1. User profiles CDC source
    print("   Creating user profiles CDC source...")
    user_profiles_cdc_ddl = f"""
    CREATE TABLE user_profiles_cdc (
        user_id STRING,
        username STRING,
        email STRING,
        registration_date DATE,
        user_tier STRING,
        total_spent DECIMAL(12,2),
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3),
        PRIMARY KEY (user_id) NOT ENFORCED
    ) WITH (
        'connector' = 'postgres-cdc',
        'hostname' = '192.168.1.184',
        'port' = '5432',
        'username' = 'cdc_user',
        'password' = 'cdc_password123',
        'database-name' = 'analytics_db',
        'schema-name' = 'public',
        'table-name' = 'user_profiles',
        'slot.name' = 'flink_sql_cdc_slot'
    )
    """
    table_env.execute_sql(user_profiles_cdc_ddl)

    # 2. Product catalog CDC source
    print("   Creating product catalog CDC source...")
    product_catalog_cdc_ddl = f"""
    CREATE TABLE product_catalog_cdc (
        product_id STRING,
        product_name STRING,
        category STRING,
        price DECIMAL(10,2),
        in_stock BOOLEAN,
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3),
        PRIMARY KEY (product_id) NOT ENFORCED
    ) WITH (
        'connector' = 'postgres-cdc',
        'hostname' = '192.168.1.184',
        'port' = '5432',
        'username' = 'cdc_user',
        'password' = 'cdc_password123',
        'database-name' = 'analytics_db',
        'schema-name' = 'public',
        'table-name' = 'product_catalog',
        'slot.name' = 'flink_sql_product_cdc_slot'
    )
    """
    table_env.execute_sql(product_catalog_cdc_ddl)

    print("✅ CDC tables configured")


@handle_errors
def create_real_time_analytics_queries(table_env: StreamTableEnvironment):
    """
    Create and start real-time analytics SQL queries.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        List of query results for monitoring
    """
    print("\n🔄 Creating real-time analytics SQL queries...")

    query_results = []

    # 1. Real-time revenue analytics (1-minute tumbling windows)
    print("   Creating revenue analytics query...")
    revenue_analytics_sql = """
    INSERT INTO analytics_sink
    SELECT 
        TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
        TUMBLE_END(event_time, INTERVAL '1' MINUTE) as window_end,
        category,
        SUM(price * quantity) as total_revenue,
        COUNT(*) as order_count,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(price * quantity) as avg_order_value,
        MAX(price * quantity) as max_order_value
    FROM events_source
    WHERE price > 0 AND quantity > 0
    GROUP BY 
        TUMBLE(event_time, INTERVAL '1' MINUTE),
        category
    """

    revenue_result = table_env.execute_sql(revenue_analytics_sql)
    query_results.append(("Revenue Analytics", revenue_result))

    # 2. Fraud detection query
    print("   Creating fraud detection query...")
    fraud_detection_sql = """
    INSERT INTO fraud_alerts_sink
    SELECT 
        CONCAT('fraud_', event_id) as alert_id,
        user_id,
        event_id,
        CASE 
            WHEN price * quantity > 1000 THEN 80
            WHEN price * quantity > 500 THEN 60
            WHEN category = 'ELECTRONICS' AND price * quantity > 200 THEN 50
            ELSE 30
        END as fraud_score,
        CASE 
            WHEN price * quantity > 1000 THEN 'HIGH_VALUE_TRANSACTION'
            WHEN price * quantity > 500 THEN 'MEDIUM_VALUE_TRANSACTION'
            ELSE 'SUSPICIOUS_PATTERN'
        END as alert_type,
        price * quantity as event_amount,
        CURRENT_TIMESTAMP as alert_timestamp
    FROM events_source
    WHERE (price * quantity > 500) 
       OR (category = 'ELECTRONICS' AND price * quantity > 200)
       OR (action = 'purchase' AND EXTRACT(HOUR FROM event_time) BETWEEN 0 AND 6)
    """

    fraud_result = table_env.execute_sql(fraud_detection_sql)
    query_results.append(("Fraud Detection", fraud_result))

    # 3. User session analytics (session windows with 30-minute timeout)
    print("   Creating user session analytics query...")
    session_analytics_sql = """
    INSERT INTO user_sessions_sink
    SELECT 
        session_id,
        user_id,
        SESSION_START(event_time, INTERVAL '30' MINUTE) as session_start,
        SESSION_END(event_time, INTERVAL '30' MINUTE) as session_end,
        (CAST(SESSION_END(event_time, INTERVAL '30' MINUTE) AS BIGINT) - 
         CAST(SESSION_START(event_time, INTERVAL '30' MINUTE) AS BIGINT)) / 60000.0 as session_duration_minutes,
        COUNT(*) as event_count,
        SUM(price * quantity) as total_spent,
        COUNT(DISTINCT product_id) as unique_products
    FROM events_source
    WHERE action IN ('view', 'add_to_cart', 'purchase')
    GROUP BY 
        session_id,
        user_id,
        SESSION(event_time, INTERVAL '30' MINUTE)
    HAVING COUNT(*) > 1
    """

    session_result = table_env.execute_sql(session_analytics_sql)
    query_results.append(("User Sessions", session_result))

    # 4. Hourly aggregations for reporting
    print("   Creating hourly aggregations query...")
    hourly_analytics_sql = """
    INSERT INTO hourly_analytics
    SELECT 
        TUMBLE_START(event_time, INTERVAL '1' HOUR) as hour_timestamp,
        category,
        SUM(price * quantity) as total_revenue,
        COUNT(*) as order_count,
        COUNT(DISTINCT user_id) as unique_users,
        AVG(price * quantity) as avg_order_value
    FROM events_source
    WHERE price > 0 AND quantity > 0
    GROUP BY 
        TUMBLE(event_time, INTERVAL '1' HOUR),
        category
    """

    hourly_result = table_env.execute_sql(hourly_analytics_sql)
    query_results.append(("Hourly Analytics", hourly_result))

    # 5. Product performance with ranking (5-minute sliding windows)
    print("   Creating product performance query...")
    product_performance_sql = """
    INSERT INTO product_performance
    SELECT 
        window_start,
        product_id,
        category,
        total_revenue,
        order_count,
        ROW_NUMBER() OVER (PARTITION BY window_start, category ORDER BY total_revenue DESC) as popularity_rank
    FROM (
        SELECT 
            TUMBLE_START(event_time, INTERVAL '5' MINUTE) as window_start,
            product_id,
            category,
            SUM(price * quantity) as total_revenue,
            COUNT(*) as order_count
        FROM events_source
        WHERE action = 'purchase'
        GROUP BY 
            TUMBLE(event_time, INTERVAL '5' MINUTE),
            product_id,
            category
        HAVING SUM(price * quantity) > 0
    )
    WHERE popularity_rank <= 10
    """

    product_result = table_env.execute_sql(product_performance_sql)
    query_results.append(("Product Performance", product_result))

    print("✅ Real-time analytics queries started")
    return query_results


@handle_errors
def create_enrichment_queries(table_env: StreamTableEnvironment):
    """
    Create queries that enrich events with reference data using temporal joins.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        List of enrichment query results
    """
    print("\n🔄 Creating data enrichment queries...")

    query_results = []

    # 1. Create enriched events view with user profiles
    print("   Creating user profile enrichment...")
    enriched_events_sql = """
    CREATE VIEW enriched_events AS
    SELECT 
        e.event_id,
        e.user_id,
        e.product_id,
        e.category,
        e.action,
        e.price,
        e.quantity,
        e.price * e.quantity as total_amount,
        e.event_time,
        u.username,
        u.email,
        u.user_tier,
        u.total_spent as user_lifetime_value,
        p.product_name,
        p.in_stock
    FROM events_source e
    LEFT JOIN user_profiles_cdc FOR SYSTEM_TIME AS OF e.event_time AS u
        ON e.user_id = u.user_id
    LEFT JOIN product_catalog_cdc FOR SYSTEM_TIME AS OF e.event_time AS p
        ON e.product_id = p.product_id
    """

    table_env.execute_sql(enriched_events_sql)

    # 2. Premium user analytics
    print("   Creating premium user analytics...")
    premium_analytics_sql = """
    CREATE TABLE premium_user_analytics (
        window_start TIMESTAMP(3),
        window_end TIMESTAMP(3),
        user_tier STRING,
        total_revenue DECIMAL(12,2),
        avg_order_value DECIMAL(10,2),
        user_count BIGINT
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'premium-analytics',
        'properties.bootstrap.servers' = '192.168.1.184:9092',
        'format' = 'json'
    )
    """
    table_env.execute_sql(premium_analytics_sql)

    premium_insert_sql = """
    INSERT INTO premium_user_analytics
    SELECT 
        TUMBLE_START(event_time, INTERVAL '5' MINUTE) as window_start,
        TUMBLE_END(event_time, INTERVAL '5' MINUTE) as window_end,
        COALESCE(user_tier, 'UNKNOWN') as user_tier,
        SUM(total_amount) as total_revenue,
        AVG(total_amount) as avg_order_value,
        COUNT(DISTINCT user_id) as user_count
    FROM enriched_events
    WHERE action = 'purchase'
    GROUP BY 
        TUMBLE(event_time, INTERVAL '5' MINUTE),
        user_tier
    """

    premium_result = table_env.execute_sql(premium_insert_sql)
    query_results.append(("Premium User Analytics", premium_result))

    # 3. Inventory impact tracking
    print("   Creating inventory impact tracking...")
    inventory_tracking_sql = """
    CREATE TABLE inventory_alerts (
        product_id STRING,
        product_name STRING,
        category STRING,
        purchase_count BIGINT,
        estimated_remaining_stock BIGINT,
        alert_level STRING,
        last_purchase_time TIMESTAMP(3)
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'inventory-alerts',
        'properties.bootstrap.servers' = '192.168.1.184:9092',
        'format' = 'json'
    )
    """
    table_env.execute_sql(inventory_tracking_sql)

    inventory_insert_sql = """
    INSERT INTO inventory_alerts
    SELECT 
        product_id,
        COALESCE(product_name, 'Unknown Product') as product_name,
        category,
        COUNT(*) as purchase_count,
        GREATEST(0, 100 - COUNT(*)) as estimated_remaining_stock,
        CASE 
            WHEN COUNT(*) > 80 THEN 'CRITICAL'
            WHEN COUNT(*) > 60 THEN 'LOW'
            WHEN COUNT(*) > 40 THEN 'MEDIUM'
            ELSE 'OK'
        END as alert_level,
        MAX(event_time) as last_purchase_time
    FROM enriched_events
    WHERE action = 'purchase' AND in_stock = true
    GROUP BY 
        TUMBLE(event_time, INTERVAL '10' MINUTE),
        product_id, product_name, category
    HAVING COUNT(*) > 5
    """

    inventory_result = table_env.execute_sql(inventory_insert_sql)
    query_results.append(("Inventory Tracking", inventory_result))

    print("✅ Data enrichment queries started")
    return query_results


@handle_errors
def create_advanced_analytics_queries(table_env: StreamTableEnvironment):
    """
    Create advanced analytics queries with complex patterns.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        List of advanced query results
    """
    print("\n🔄 Creating advanced analytics queries...")

    query_results = []

    # 1. Customer lifetime value tracking
    print("   Creating CLV tracking...")
    clv_tracking_sql = """
    CREATE VIEW customer_clv AS
    SELECT 
        user_id,
        username,
        user_tier,
        window_start,
        SUM(total_amount) OVER (
            PARTITION BY user_id 
            ORDER BY window_start 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as cumulative_clv,
        COUNT(*) OVER (
            PARTITION BY user_id 
            ORDER BY window_start 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) as total_transactions,
        AVG(total_amount) OVER (
            PARTITION BY user_id 
            ORDER BY window_start 
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) as recent_avg_order_value
    FROM (
        SELECT 
            user_id,
            username,
            user_tier,
            TUMBLE_START(event_time, INTERVAL '1' HOUR) as window_start,
            SUM(total_amount) as total_amount
        FROM enriched_events
        WHERE action = 'purchase'
        GROUP BY 
            user_id, username, user_tier,
            TUMBLE(event_time, INTERVAL '1' HOUR)
    )
    """
    table_env.execute_sql(clv_tracking_sql)

    # 2. Cross-category purchase patterns
    print("   Creating cross-category analytics...")
    cross_category_sql = """
    CREATE TABLE cross_category_patterns (
        window_start TIMESTAMP(3),
        user_id STRING,
        categories_purchased ARRAY<STRING>,
        category_count INT,
        total_spent DECIMAL(12,2),
        cross_category_score DOUBLE
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'cross-category-patterns',
        'properties.bootstrap.servers' = '192.168.1.184:9092',
        'format' = 'json'
    )
    """
    table_env.execute_sql(cross_category_sql)

    cross_category_insert_sql = """
    INSERT INTO cross_category_patterns
    SELECT 
        TUMBLE_START(event_time, INTERVAL '1' HOUR) as window_start,
        user_id,
        COLLECT(DISTINCT category) as categories_purchased,
        COUNT(DISTINCT category) as category_count,
        SUM(total_amount) as total_spent,
        COUNT(DISTINCT category) * SUM(total_amount) / 1000.0 as cross_category_score
    FROM enriched_events
    WHERE action = 'purchase'
    GROUP BY 
        user_id,
        TUMBLE(event_time, INTERVAL '1' HOUR)
    HAVING COUNT(DISTINCT category) > 1
    """

    cross_category_result = table_env.execute_sql(cross_category_insert_sql)
    query_results.append(("Cross-Category Patterns", cross_category_result))

    # 3. Real-time churn prediction signals
    print("   Creating churn prediction signals...")
    churn_signals_sql = """
    CREATE TABLE churn_prediction_signals (
        user_id STRING,
        signal_timestamp TIMESTAMP(3),
        days_since_last_purchase INT,
        avg_session_gap_hours DOUBLE,
        recent_engagement_score DOUBLE,
        churn_risk_level STRING
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'churn-signals',
        'properties.bootstrap.servers' = '192.168.1.184:9092',
        'format' = 'json'
    )
    """
    table_env.execute_sql(churn_signals_sql)

    # Note: This is a simplified churn prediction - in practice would use more sophisticated ML
    churn_insert_sql = """
    INSERT INTO churn_prediction_signals
    SELECT 
        user_id,
        MAX(event_time) as signal_timestamp,
        CAST((UNIX_TIMESTAMP(MAX(event_time)) - UNIX_TIMESTAMP(MIN(event_time))) / 86400 AS INT) as days_since_last_purchase,
        CAST((UNIX_TIMESTAMP(MAX(event_time)) - UNIX_TIMESTAMP(MIN(event_time))) / 3600.0 AS DOUBLE) / GREATEST(COUNT(DISTINCT session_id), 1) as avg_session_gap_hours,
        COUNT(*) * 1.0 / GREATEST(COUNT(DISTINCT session_id), 1) as recent_engagement_score,
        CASE 
            WHEN COUNT(*) < 3 THEN 'HIGH_RISK'
            WHEN COUNT(*) < 7 THEN 'MEDIUM_RISK'
            ELSE 'LOW_RISK'
        END as churn_risk_level
    FROM enriched_events
    WHERE event_time > CURRENT_TIMESTAMP - INTERVAL '7' DAY
    GROUP BY 
        user_id,
        TUMBLE(event_time, INTERVAL '1' DAY)
    HAVING COUNT(*) > 0
    """

    churn_result = table_env.execute_sql(churn_insert_sql)
    query_results.append(("Churn Prediction", churn_result))

    print("✅ Advanced analytics queries started")
    return query_results


@handle_errors
def monitor_sql_queries(
    table_env: StreamTableEnvironment, query_results: list, duration: int
):
    """
    Monitor the execution of SQL streaming queries.

    Args:
        table_env: StreamTableEnvironment
        query_results: List of query results to monitor
        duration: How long to monitor
    """
    print(f"\n📊 Monitoring SQL queries for {duration} seconds...")

    start_time = time.time()
    end_time = start_time + duration

    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\n⚠️  Received interrupt signal, stopping queries...")
        for name, result in query_results:
            try:
                result.get_job_client().cancel()
            except:
                pass
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while time.time() < end_time:
            current_time = time.time()
            elapsed = current_time - start_time
            remaining = end_time - current_time

            print(f"\n⏱️  Elapsed: {elapsed:.0f}s | Remaining: {remaining:.0f}s")

            # Check query status
            active_queries = 0
            for name, result in query_results:
                try:
                    job_client = result.get_job_client()
                    if job_client:
                        job_status = job_client.get_job_status()
                        print(f"   {name}: {job_status}")
                        if job_status.is_globally_terminal_state():
                            print(f"   ❌ {name}: Terminal state reached")
                        else:
                            active_queries += 1
                    else:
                        print(f"   {name}: No job client available")
                except Exception as e:
                    print(f"   {name}: Status check failed - {e}")

            print(f"   Active Queries: {active_queries}/{len(query_results)}")

            # Sample some results (this would be customized based on your needs)
            try:
                # Query some sample data from memory tables if available
                sample_result = table_env.execute_sql("SHOW TABLES")
                tables = [row[0] for row in sample_result.collect()]
                print(f"   Available tables: {len(tables)}")
            except Exception as e:
                print(f"   Table query error: {e}")

            time.sleep(15)  # Check every 15 seconds

    except KeyboardInterrupt:
        print("\n⚠️  Monitoring interrupted by user")

    # Stop all queries
    print("\n🔄 Stopping SQL queries...")
    for name, result in query_results:
        try:
            print(f"   Stopping {name}...")
            job_client = result.get_job_client()
            if job_client:
                job_client.cancel()
        except Exception as e:
            print(f"   Warning stopping {name}: {e}")

    print("✅ All SQL queries stopped")


@handle_errors
def main():
    """Main SQL streaming workflow."""
    # Parse arguments
    parser = parse_common_args()
    parser.add_argument(
        "--enable-cdc", action="store_true", help="Enable CDC processing"
    )
    args = parser.parse_args()

    print("🚀 Starting Flink SQL Streaming Analytics")
    print(f"   Application: {args.app_name}")
    print(f"   Duration: {args.duration} seconds")
    print(f"   Enable CDC: {args.enable_cdc}")
    print(f"   Output path: {args.output_path}")

    # Create Flink configuration
    config = FlinkConfig(
        app_name=f"{args.app_name}_SQLStreaming",
        parallelism=args.parallelism,
        kafka_servers=args.kafka_servers,
        postgres_url=args.postgres_url,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
    )

    # Create environments
    env = create_flink_environment(config)
    table_env = create_table_environment(env)

    # Configure table environment for SQL streaming
    table_config = table_env.get_config()
    table_config.set("table.exec.emit.early-fire.enabled", "true")
    table_config.set("table.exec.emit.early-fire.delay", "5s")
    table_config.set("table.optimizer.join-reorder-enabled", "true")

    try:
        # Setup tables
        setup_kafka_tables(table_env, config.kafka_servers)

        postgres_config = {
            "url": config.postgres_url,
            "user": config.postgres_user,
            "password": config.postgres_password,
        }
        setup_database_tables(table_env, postgres_config)

        # Setup CDC if enabled
        if args.enable_cdc:
            try:
                setup_cdc_tables(table_env, postgres_config)
                print("✅ CDC enabled")
            except Exception as e:
                print(f"⚠️  CDC setup failed: {e}")
                print("   Continuing without CDC...")

        all_query_results = []

        # Create and start analytics queries
        analytics_results = create_real_time_analytics_queries(table_env)
        all_query_results.extend(analytics_results)

        # Create enrichment queries if CDC is available
        if args.enable_cdc:
            try:
                enrichment_results = create_enrichment_queries(table_env)
                all_query_results.extend(enrichment_results)

                advanced_results = create_advanced_analytics_queries(table_env)
                all_query_results.extend(advanced_results)
            except Exception as e:
                print(f"⚠️  Advanced queries failed: {e}")

        # Monitor job progress
        monitor_job_progress(env, "SQL Streaming Analytics")

        print(f"\n📊 Started {len(all_query_results)} SQL streaming queries:")
        for name, _ in all_query_results:
            print(f"   - {name}")

        print(
            "\n💡 To send test data, publish JSON events to Kafka topic 'flink-events'"
        )
        print("   Example event:")
        example_event = {
            "event_id": "evt_123",
            "user_id": "user_456",
            "session_id": "session_789",
            "product_id": "prod_101",
            "category": "ELECTRONICS",
            "action": "purchase",
            "price": 299.99,
            "quantity": 1,
            "timestamp_str": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "metadata": {
                "source": "web",
                "user_agent": "Mozilla/5.0",
                "ip_address": "192.168.1.100",
            },
        }
        print(f"   {json.dumps(example_event, indent=2)}")

        # Monitor queries
        monitor_sql_queries(table_env, all_query_results, args.duration)

        # Print final metrics
        metrics_tracker.print_summary()

        print(f"\n✅ SQL streaming analytics completed!")
        print(f"   Ran {len(all_query_results)} queries for {args.duration} seconds")
        print(f"   Results available in Kafka topics and PostgreSQL tables")
        print(f"   Flink Web UI: http://192.168.1.184:8081")

    except KeyboardInterrupt:
        print("\n⚠️  SQL streaming interrupted by user")
    except Exception as e:
        print(f"\n❌ SQL streaming error: {e}")
        raise
    finally:
        cleanup_environment(env)


if __name__ == "__main__":
    main()
