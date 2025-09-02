#!/usr/bin/env python3
"""
Flink CDC Processing Examples - Building Block Application

This module demonstrates Change Data Capture (CDC) processing with Apache Flink:
- Real-time database synchronization
- Multi-table CDC with data enrichment
- Event-driven data transformations
- Real-time analytics on changing data
- Data quality monitoring and validation
- Conflict resolution and data consistency

Usage:
    bazel run //flink/python:cdc_processing -- --source-tables users,orders,products

Examples:
    # Basic CDC processing
    bazel run //flink/python:cdc_processing
    
    # Multi-table CDC with custom duration
    bazel run //flink/python:cdc_processing -- --source-tables users,orders,products --duration 300
    
    # CDC with data validation
    bazel run //flink/python:cdc_processing -- --enable-validation --duration 600
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
    monitor_job_progress,
    parse_common_args,
    handle_errors,
    cleanup_environment,
    metrics_tracker,
)

try:
    from pyflink.datastream import StreamExecutionEnvironment
    from pyflink.table import StreamTableEnvironment, DataTypes
    from pyflink.common import Configuration
except ImportError:
    print("ERROR: PyFlink not found. Install with: pip install apache-flink")
    sys.exit(1)


@handle_errors
def setup_cdc_source_tables(table_env: StreamTableEnvironment):
    """
    Setup CDC source tables for various database tables.

    Args:
        table_env: StreamTableEnvironment
    """
    print("\n🔄 Setting up CDC source tables...")

    # 1. Users table CDC
    print("   Creating users CDC source...")
    users_cdc_ddl = """
    CREATE TABLE users_cdc (
        user_id STRING,
        username STRING,
        email STRING,
        first_name STRING,
        last_name STRING,
        date_of_birth DATE,
        registration_date TIMESTAMP(3),
        user_status STRING,
        user_tier STRING,
        total_spent DECIMAL(12,2),
        last_login TIMESTAMP(3),
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3),
        is_deleted BOOLEAN,
        PRIMARY KEY (user_id) NOT ENFORCED
    ) WITH (
        'connector' = 'postgres-cdc',
        'hostname' = '192.168.1.184',
        'port' = '5432',
        'username' = 'cdc_user',
        'password' = 'cdc_password123',
        'database-name' = 'analytics_db',
        'schema-name' = 'public',
        'table-name' = 'users',
        'slot.name' = 'flink_users_cdc_slot',
        'debezium.snapshot.mode' = 'initial'
    )
    """
    table_env.execute_sql(users_cdc_ddl)

    # 2. Orders table CDC
    print("   Creating orders CDC source...")
    orders_cdc_ddl = """
    CREATE TABLE orders_cdc (
        order_id STRING,
        user_id STRING,
        order_status STRING,
        order_total DECIMAL(12,2),
        order_date TIMESTAMP(3),
        shipping_address ROW<
            street STRING,
            city STRING,
            state STRING,
            zip_code STRING,
            country STRING
        >,
        payment_method STRING,
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3),
        is_deleted BOOLEAN,
        PRIMARY KEY (order_id) NOT ENFORCED
    ) WITH (
        'connector' = 'postgres-cdc',
        'hostname' = '192.168.1.184',
        'port' = '5432',
        'username' = 'cdc_user',
        'password' = 'cdc_password123',
        'database-name' = 'analytics_db',
        'schema-name' = 'public',
        'table-name' = 'orders',
        'slot.name' = 'flink_orders_cdc_slot',
        'debezium.snapshot.mode' = 'initial'
    )
    """
    table_env.execute_sql(orders_cdc_ddl)

    # 3. Products table CDC
    print("   Creating products CDC source...")
    products_cdc_ddl = """
    CREATE TABLE products_cdc (
        product_id STRING,
        product_name STRING,
        category STRING,
        subcategory STRING,
        price DECIMAL(10,2),
        cost DECIMAL(10,2),
        inventory_count INT,
        reorder_level INT,
        supplier_id STRING,
        product_status STRING,
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3),
        is_deleted BOOLEAN,
        PRIMARY KEY (product_id) NOT ENFORCED
    ) WITH (
        'connector' = 'postgres-cdc',
        'hostname' = '192.168.1.184',
        'port' = '5432',
        'username' = 'cdc_user',
        'password' = 'cdc_password123',
        'database-name' = 'analytics_db',
        'schema-name' = 'public',
        'table-name' = 'products',
        'slot.name' = 'flink_products_cdc_slot',
        'debezium.snapshot.mode' = 'initial'
    )
    """
    table_env.execute_sql(products_cdc_ddl)

    # 4. Order items table CDC
    print("   Creating order_items CDC source...")
    order_items_cdc_ddl = """
    CREATE TABLE order_items_cdc (
        order_item_id STRING,
        order_id STRING,
        product_id STRING,
        quantity INT,
        unit_price DECIMAL(10,2),
        total_price DECIMAL(12,2),
        discount_amount DECIMAL(10,2),
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3),
        is_deleted BOOLEAN,
        PRIMARY KEY (order_item_id) NOT ENFORCED
    ) WITH (
        'connector' = 'postgres-cdc',
        'hostname' = '192.168.1.184',
        'port' = '5432',
        'username' = 'cdc_user',
        'password' = 'cdc_password123',
        'database-name' = 'analytics_db',
        'schema-name' = 'public',
        'table-name' = 'order_items',
        'slot.name' = 'flink_order_items_cdc_slot',
        'debezium.snapshot.mode' = 'initial'
    )
    """
    table_env.execute_sql(order_items_cdc_ddl)

    print("✅ CDC source tables configured")


@handle_errors
def setup_output_tables(
    table_env: StreamTableEnvironment, kafka_servers: str, postgres_config: dict
):
    """
    Setup output tables for CDC processing results.

    Args:
        table_env: StreamTableEnvironment
        kafka_servers: Kafka bootstrap servers
        postgres_config: PostgreSQL configuration
    """
    print("\n🔄 Setting up output tables...")

    # 1. Real-time analytics warehouse (PostgreSQL)
    print("   Creating analytics warehouse tables...")

    # Customer analytics table
    customer_analytics_ddl = f"""
    CREATE TABLE customer_analytics (
        user_id STRING,
        username STRING,
        email STRING,
        full_name STRING,
        user_tier STRING,
        total_orders BIGINT,
        total_spent DECIMAL(12,2),
        avg_order_value DECIMAL(10,2),
        last_order_date TIMESTAMP(3),
        days_since_last_order INT,
        customer_lifetime_days INT,
        is_active BOOLEAN,
        updated_at TIMESTAMP(3),
        PRIMARY KEY (user_id) NOT ENFORCED
    ) WITH (
        'connector' = 'jdbc',
        'url' = '{postgres_config["url"]}',
        'table-name' = 'customer_analytics',
        'username' = '{postgres_config["user"]}',
        'password' = '{postgres_config["password"]}',
        'sink.buffer-flush.max-rows' = '1000',
        'sink.buffer-flush.interval' = '30s'
    )
    """
    table_env.execute_sql(customer_analytics_ddl)

    # Product analytics table
    product_analytics_ddl = f"""
    CREATE TABLE product_analytics (
        product_id STRING,
        product_name STRING,
        category STRING,
        current_price DECIMAL(10,2),
        current_inventory INT,
        total_sold BIGINT,
        total_revenue DECIMAL(12,2),
        avg_sale_price DECIMAL(10,2),
        inventory_turnover_rate DOUBLE,
        profit_margin DECIMAL(5,2),
        last_sale_date TIMESTAMP(3),
        reorder_needed BOOLEAN,
        updated_at TIMESTAMP(3),
        PRIMARY KEY (product_id) NOT ENFORCED
    ) WITH (
        'connector' = 'jdbc',
        'url' = '{postgres_config["url"]}',
        'table-name' = 'product_analytics',
        'username' = '{postgres_config["user"]}',
        'password' = '{postgres_config["password"]}',
        'sink.buffer-flush.max-rows' = '1000',
        'sink.buffer-flush.interval' = '30s'
    )
    """
    table_env.execute_sql(product_analytics_ddl)

    # 2. Real-time event streams (Kafka)
    print("   Creating event stream tables...")

    # User lifecycle events
    user_lifecycle_events_ddl = f"""
    CREATE TABLE user_lifecycle_events (
        event_id STRING,
        user_id STRING,
        event_type STRING,
        event_timestamp TIMESTAMP(3),
        previous_state ROW<
            user_status STRING,
            user_tier STRING,
            total_spent DECIMAL(12,2)
        >,
        current_state ROW<
            user_status STRING,
            user_tier STRING,
            total_spent DECIMAL(12,2)
        >,
        change_reason STRING
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'user-lifecycle-events',
        'properties.bootstrap.servers' = '{kafka_servers}',
        'format' = 'json'
    )
    """
    table_env.execute_sql(user_lifecycle_events_ddl)

    # Inventory alerts
    inventory_alerts_ddl = f"""
    CREATE TABLE inventory_alerts (
        alert_id STRING,
        product_id STRING,
        product_name STRING,
        category STRING,
        alert_type STRING,
        current_inventory INT,
        reorder_level INT,
        recommended_order_quantity INT,
        alert_timestamp TIMESTAMP(3)
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'inventory-alerts',
        'properties.bootstrap.servers' = '{kafka_servers}',
        'format' = 'json'
    )
    """
    table_env.execute_sql(inventory_alerts_ddl)

    # Data quality alerts
    data_quality_alerts_ddl = f"""
    CREATE TABLE data_quality_alerts (
        alert_id STRING,
        table_name STRING,
        record_id STRING,
        quality_issue STRING,
        severity STRING,
        field_name STRING,
        invalid_value STRING,
        expected_format STRING,
        alert_timestamp TIMESTAMP(3)
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'data-quality-alerts',
        'properties.bootstrap.servers' = '{kafka_servers}',
        'format' = 'json'
    )
    """
    table_env.execute_sql(data_quality_alerts_ddl)

    print("✅ Output tables configured")


@handle_errors
def create_real_time_analytics_views(table_env: StreamTableEnvironment):
    """
    Create real-time analytics views that combine CDC data.

    Args:
        table_env: StreamTableEnvironment
    """
    print("\n🔄 Creating real-time analytics views...")

    # 1. Enhanced order view with customer and product details
    print("   Creating enhanced order view...")
    enhanced_orders_view = """
    CREATE VIEW enhanced_orders AS
    SELECT 
        o.order_id,
        o.user_id,
        u.username,
        u.email,
        CONCAT(u.first_name, ' ', u.last_name) as customer_name,
        u.user_tier,
        o.order_status,
        o.order_total,
        o.order_date,
        o.payment_method,
        o.shipping_address,
        DATEDIFF(DAY, u.registration_date, o.order_date) as days_since_registration,
        CASE 
            WHEN DATEDIFF(DAY, u.registration_date, o.order_date) <= 30 THEN 'NEW_CUSTOMER'
            WHEN DATEDIFF(DAY, u.registration_date, o.order_date) <= 365 THEN 'EXISTING_CUSTOMER'
            ELSE 'LOYAL_CUSTOMER'
        END as customer_segment,
        o.created_at,
        o.updated_at,
        o.is_deleted
    FROM orders_cdc o
    LEFT JOIN users_cdc FOR SYSTEM_TIME AS OF o.updated_at AS u
        ON o.user_id = u.user_id
    WHERE o.is_deleted = false AND u.is_deleted = false
    """
    table_env.execute_sql(enhanced_orders_view)

    # 2. Order details view with product information
    print("   Creating order details view...")
    order_details_view = """
    CREATE VIEW order_details AS
    SELECT 
        oi.order_item_id,
        oi.order_id,
        o.user_id,
        o.order_date,
        o.order_status,
        oi.product_id,
        p.product_name,
        p.category,
        p.subcategory,
        oi.quantity,
        oi.unit_price,
        p.price as current_price,
        p.cost as product_cost,
        oi.total_price,
        oi.discount_amount,
        (oi.total_price - (p.cost * oi.quantity)) as profit_amount,
        ((oi.total_price - (p.cost * oi.quantity)) / NULLIF(oi.total_price, 0)) * 100 as profit_margin_percent,
        CASE 
            WHEN oi.unit_price < p.price * 0.8 THEN 'HIGH_DISCOUNT'
            WHEN oi.unit_price < p.price * 0.9 THEN 'MEDIUM_DISCOUNT'
            WHEN oi.unit_price < p.price THEN 'LOW_DISCOUNT'
            ELSE 'NO_DISCOUNT'
        END as discount_category,
        oi.created_at,
        oi.updated_at
    FROM order_items_cdc oi
    LEFT JOIN orders_cdc FOR SYSTEM_TIME AS OF oi.updated_at AS o
        ON oi.order_id = o.order_id
    LEFT JOIN products_cdc FOR SYSTEM_TIME AS OF oi.updated_at AS p
        ON oi.product_id = p.product_id
    WHERE oi.is_deleted = false AND o.is_deleted = false AND p.is_deleted = false
    """
    table_env.execute_sql(order_details_view)

    print("✅ Analytics views created")


@handle_errors
def create_customer_analytics_pipeline(table_env: StreamTableEnvironment):
    """
    Create customer analytics pipeline with real-time updates.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        Query execution result
    """
    print("\n🔄 Creating customer analytics pipeline...")

    # Customer analytics aggregation
    customer_analytics_sql = """
    INSERT INTO customer_analytics
    SELECT 
        user_id,
        username,
        email,
        CONCAT(first_name, ' ', last_name) as full_name,
        user_tier,
        COALESCE(order_count, 0) as total_orders,
        COALESCE(total_spent, 0.0) as total_spent,
        COALESCE(total_spent / NULLIF(order_count, 0), 0.0) as avg_order_value,
        last_order_date,
        COALESCE(DATEDIFF(DAY, last_order_date, CURRENT_TIMESTAMP), 999) as days_since_last_order,
        DATEDIFF(DAY, registration_date, CURRENT_TIMESTAMP) as customer_lifetime_days,
        CASE 
            WHEN last_order_date >= CURRENT_TIMESTAMP - INTERVAL '30' DAY THEN true
            ELSE false
        END as is_active,
        CURRENT_TIMESTAMP as updated_at
    FROM (
        SELECT 
            u.user_id,
            u.username,
            u.email,
            u.first_name,
            u.last_name,
            u.user_tier,
            u.registration_date,
            COUNT(o.order_id) as order_count,
            SUM(o.order_total) as total_spent,
            MAX(o.order_date) as last_order_date
        FROM users_cdc u
        LEFT JOIN orders_cdc o ON u.user_id = o.user_id 
            AND o.is_deleted = false 
            AND o.order_status IN ('completed', 'shipped', 'delivered')
        WHERE u.is_deleted = false
        GROUP BY u.user_id, u.username, u.email, u.first_name, u.last_name, u.user_tier, u.registration_date
    )
    """

    result = table_env.execute_sql(customer_analytics_sql)
    print("✅ Customer analytics pipeline started")
    return result


@handle_errors
def create_product_analytics_pipeline(table_env: StreamTableEnvironment):
    """
    Create product analytics pipeline with real-time updates.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        Query execution result
    """
    print("\n🔄 Creating product analytics pipeline...")

    # Product analytics aggregation
    product_analytics_sql = """
    INSERT INTO product_analytics
    SELECT 
        p.product_id,
        p.product_name,
        p.category,
        p.price as current_price,
        p.inventory_count as current_inventory,
        COALESCE(sales_data.total_sold, 0) as total_sold,
        COALESCE(sales_data.total_revenue, 0.0) as total_revenue,
        COALESCE(sales_data.avg_sale_price, p.price) as avg_sale_price,
        CASE 
            WHEN p.inventory_count > 0 THEN COALESCE(sales_data.total_sold, 0) * 1.0 / p.inventory_count
            ELSE 0.0
        END as inventory_turnover_rate,
        CASE 
            WHEN p.price > 0 THEN ((p.price - p.cost) / p.price) * 100
            ELSE 0.0
        END as profit_margin,
        sales_data.last_sale_date,
        CASE 
            WHEN p.inventory_count <= p.reorder_level THEN true
            ELSE false
        END as reorder_needed,
        CURRENT_TIMESTAMP as updated_at
    FROM products_cdc p
    LEFT JOIN (
        SELECT 
            product_id,
            SUM(quantity) as total_sold,
            SUM(total_price) as total_revenue,
            AVG(unit_price) as avg_sale_price,
            MAX(order_date) as last_sale_date
        FROM order_details
        WHERE order_status IN ('completed', 'shipped', 'delivered')
        GROUP BY product_id
    ) sales_data ON p.product_id = sales_data.product_id
    WHERE p.is_deleted = false
    """

    result = table_env.execute_sql(product_analytics_sql)
    print("✅ Product analytics pipeline started")
    return result


@handle_errors
def create_lifecycle_event_pipeline(table_env: StreamTableEnvironment):
    """
    Create user lifecycle event detection pipeline.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        Query execution result
    """
    print("\n🔄 Creating lifecycle event pipeline...")

    # Detect user tier changes and status changes
    lifecycle_events_sql = """
    INSERT INTO user_lifecycle_events
    SELECT 
        CONCAT('lifecycle_', user_id, '_', UNIX_TIMESTAMP(updated_at)) as event_id,
        user_id,
        CASE 
            WHEN user_status <> LAG(user_status) OVER (PARTITION BY user_id ORDER BY updated_at) 
                THEN 'STATUS_CHANGE'
            WHEN user_tier <> LAG(user_tier) OVER (PARTITION BY user_id ORDER BY updated_at) 
                THEN 'TIER_CHANGE'
            WHEN total_spent - LAG(total_spent, 1, 0) OVER (PARTITION BY user_id ORDER BY updated_at) > 1000 
                THEN 'HIGH_VALUE_PURCHASE'
            ELSE 'UPDATE'
        END as event_type,
        updated_at as event_timestamp,
        ROW(
            LAG(user_status) OVER (PARTITION BY user_id ORDER BY updated_at),
            LAG(user_tier) OVER (PARTITION BY user_id ORDER BY updated_at),
            LAG(total_spent, 1, 0) OVER (PARTITION BY user_id ORDER BY updated_at)
        ) as previous_state,
        ROW(user_status, user_tier, total_spent) as current_state,
        CASE 
            WHEN user_status <> LAG(user_status) OVER (PARTITION BY user_id ORDER BY updated_at) 
                THEN CONCAT('Status changed from ', LAG(user_status) OVER (PARTITION BY user_id ORDER BY updated_at), ' to ', user_status)
            WHEN user_tier <> LAG(user_tier) OVER (PARTITION BY user_id ORDER BY updated_at) 
                THEN CONCAT('Tier changed from ', LAG(user_tier) OVER (PARTITION BY user_id ORDER BY updated_at), ' to ', user_tier)
            WHEN total_spent - LAG(total_spent, 1, 0) OVER (PARTITION BY user_id ORDER BY updated_at) > 1000 
                THEN 'High value purchase detected'
            ELSE 'Regular update'
        END as change_reason
    FROM users_cdc
    WHERE updated_at > created_at  -- Only capture actual updates, not initial inserts
    """

    result = table_env.execute_sql(lifecycle_events_sql)
    print("✅ Lifecycle event pipeline started")
    return result


@handle_errors
def create_inventory_monitoring_pipeline(table_env: StreamTableEnvironment):
    """
    Create inventory monitoring and alerting pipeline.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        Query execution result
    """
    print("\n🔄 Creating inventory monitoring pipeline...")

    # Monitor inventory levels and generate alerts
    inventory_monitoring_sql = """
    INSERT INTO inventory_alerts
    SELECT 
        CONCAT('inv_alert_', product_id, '_', UNIX_TIMESTAMP(updated_at)) as alert_id,
        product_id,
        product_name,
        category,
        CASE 
            WHEN inventory_count <= 0 THEN 'OUT_OF_STOCK'
            WHEN inventory_count <= reorder_level THEN 'LOW_STOCK'
            WHEN inventory_count <= reorder_level * 1.5 THEN 'APPROACHING_REORDER'
            ELSE 'STOCK_OK'
        END as alert_type,
        inventory_count as current_inventory,
        reorder_level,
        CASE 
            WHEN inventory_count <= 0 THEN reorder_level * 3
            WHEN inventory_count <= reorder_level THEN reorder_level * 2
            ELSE reorder_level
        END as recommended_order_quantity,
        updated_at as alert_timestamp
    FROM products_cdc
    WHERE inventory_count <= reorder_level * 1.5
      AND product_status = 'ACTIVE'
      AND is_deleted = false
    """

    result = table_env.execute_sql(inventory_monitoring_sql)
    print("✅ Inventory monitoring pipeline started")
    return result


@handle_errors
def create_data_quality_monitoring(table_env: StreamTableEnvironment):
    """
    Create data quality monitoring for CDC streams.

    Args:
        table_env: StreamTableEnvironment

    Returns:
        List of data quality query results
    """
    print("\n🔄 Creating data quality monitoring...")

    results = []

    # 1. User data quality checks
    user_quality_sql = """
    INSERT INTO data_quality_alerts
    SELECT 
        CONCAT('dq_user_', user_id, '_', UNIX_TIMESTAMP(updated_at)) as alert_id,
        'users' as table_name,
        user_id as record_id,
        CASE 
            WHEN email IS NULL OR email = '' THEN 'MISSING_EMAIL'
            WHEN email NOT LIKE '%@%.%' THEN 'INVALID_EMAIL_FORMAT'
            WHEN username IS NULL OR username = '' THEN 'MISSING_USERNAME'
            WHEN first_name IS NULL OR first_name = '' THEN 'MISSING_FIRST_NAME'
            WHEN user_tier NOT IN ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM') THEN 'INVALID_USER_TIER'
            WHEN total_spent < 0 THEN 'NEGATIVE_TOTAL_SPENT'
        END as quality_issue,
        CASE 
            WHEN email IS NULL OR email = '' OR email NOT LIKE '%@%.%' THEN 'HIGH'
            WHEN username IS NULL OR username = '' THEN 'MEDIUM'
            ELSE 'LOW'
        END as severity,
        CASE 
            WHEN email IS NULL OR email = '' OR email NOT LIKE '%@%.%' THEN 'email'
            WHEN username IS NULL OR username = '' THEN 'username'
            WHEN first_name IS NULL OR first_name = '' THEN 'first_name'
            WHEN user_tier NOT IN ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM') THEN 'user_tier'
            WHEN total_spent < 0 THEN 'total_spent'
        END as field_name,
        CASE 
            WHEN email IS NULL OR email = '' OR email NOT LIKE '%@%.%' THEN COALESCE(email, 'NULL')
            WHEN username IS NULL OR username = '' THEN COALESCE(username, 'NULL')
            WHEN first_name IS NULL OR first_name = '' THEN COALESCE(first_name, 'NULL')
            WHEN user_tier NOT IN ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM') THEN COALESCE(user_tier, 'NULL')
            WHEN total_spent < 0 THEN CAST(total_spent AS STRING)
        END as invalid_value,
        CASE 
            WHEN email IS NULL OR email = '' OR email NOT LIKE '%@%.%' THEN 'valid email format (user@domain.com)'
            WHEN username IS NULL OR username = '' THEN 'non-empty username'
            WHEN first_name IS NULL OR first_name = '' THEN 'non-empty first name'
            WHEN user_tier NOT IN ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM') THEN 'BRONZE, SILVER, GOLD, or PLATINUM'
            WHEN total_spent < 0 THEN 'non-negative value'
        END as expected_format,
        updated_at as alert_timestamp
    FROM users_cdc
    WHERE (email IS NULL OR email = '' OR email NOT LIKE '%@%.%')
       OR (username IS NULL OR username = '')
       OR (first_name IS NULL OR first_name = '')
       OR (user_tier NOT IN ('BRONZE', 'SILVER', 'GOLD', 'PLATINUM'))
       OR (total_spent < 0)
    """

    user_quality_result = table_env.execute_sql(user_quality_sql)
    results.append(("User Data Quality", user_quality_result))

    # 2. Product data quality checks
    product_quality_sql = """
    INSERT INTO data_quality_alerts
    SELECT 
        CONCAT('dq_product_', product_id, '_', UNIX_TIMESTAMP(updated_at)) as alert_id,
        'products' as table_name,
        product_id as record_id,
        CASE 
            WHEN product_name IS NULL OR product_name = '' THEN 'MISSING_PRODUCT_NAME'
            WHEN price <= 0 THEN 'INVALID_PRICE'
            WHEN cost < 0 THEN 'INVALID_COST'
            WHEN cost >= price THEN 'COST_EXCEEDS_PRICE'
            WHEN inventory_count < 0 THEN 'NEGATIVE_INVENTORY'
            WHEN reorder_level < 0 THEN 'NEGATIVE_REORDER_LEVEL'
            WHEN category IS NULL OR category = '' THEN 'MISSING_CATEGORY'
        END as quality_issue,
        CASE 
            WHEN product_name IS NULL OR product_name = '' THEN 'HIGH'
            WHEN price <= 0 OR cost >= price THEN 'HIGH'
            WHEN inventory_count < 0 THEN 'MEDIUM'
            ELSE 'LOW'
        END as severity,
        CASE 
            WHEN product_name IS NULL OR product_name = '' THEN 'product_name'
            WHEN price <= 0 THEN 'price'
            WHEN cost < 0 OR cost >= price THEN 'cost'
            WHEN inventory_count < 0 THEN 'inventory_count'
            WHEN reorder_level < 0 THEN 'reorder_level'
            WHEN category IS NULL OR category = '' THEN 'category'
        END as field_name,
        CASE 
            WHEN product_name IS NULL OR product_name = '' THEN COALESCE(product_name, 'NULL')
            WHEN price <= 0 THEN CAST(price AS STRING)
            WHEN cost < 0 OR cost >= price THEN CAST(cost AS STRING)
            WHEN inventory_count < 0 THEN CAST(inventory_count AS STRING)
            WHEN reorder_level < 0 THEN CAST(reorder_level AS STRING)
            WHEN category IS NULL OR category = '' THEN COALESCE(category, 'NULL')
        END as invalid_value,
        CASE 
            WHEN product_name IS NULL OR product_name = '' THEN 'non-empty product name'
            WHEN price <= 0 THEN 'positive price value'
            WHEN cost < 0 THEN 'non-negative cost value'
            WHEN cost >= price THEN 'cost less than price'
            WHEN inventory_count < 0 THEN 'non-negative inventory count'
            WHEN reorder_level < 0 THEN 'non-negative reorder level'
            WHEN category IS NULL OR category = '' THEN 'non-empty category'
        END as expected_format,
        updated_at as alert_timestamp
    FROM products_cdc
    WHERE (product_name IS NULL OR product_name = '')
       OR (price <= 0)
       OR (cost < 0)
       OR (cost >= price)
       OR (inventory_count < 0)
       OR (reorder_level < 0)
       OR (category IS NULL OR category = '')
    """

    product_quality_result = table_env.execute_sql(product_quality_sql)
    results.append(("Product Data Quality", product_quality_result))

    print("✅ Data quality monitoring started")
    return results


@handle_errors
def monitor_cdc_pipelines(
    table_env: StreamTableEnvironment, pipeline_results: list, duration: int
):
    """
    Monitor CDC pipeline execution and health.

    Args:
        table_env: StreamTableEnvironment
        pipeline_results: List of pipeline results to monitor
        duration: How long to monitor
    """
    print(f"\n📊 Monitoring CDC pipelines for {duration} seconds...")

    start_time = time.time()
    end_time = start_time + duration

    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\n⚠️  Received interrupt signal, stopping CDC pipelines...")
        for name, result in pipeline_results:
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

            # Check pipeline status
            active_pipelines = 0
            for name, result in pipeline_results:
                try:
                    job_client = result.get_job_client()
                    if job_client:
                        job_status = job_client.get_job_status()
                        print(f"   {name}: {job_status}")
                        if not job_status.is_globally_terminal_state():
                            active_pipelines += 1
                    else:
                        print(f"   {name}: No job client")
                except Exception as e:
                    print(f"   {name}: Status check error - {e}")

            print(f"   Active Pipelines: {active_pipelines}/{len(pipeline_results)}")

            # Show CDC lag and processing metrics
            try:
                # This would be customized based on your CDC monitoring needs
                print(
                    f"   CDC Events Processed: {metrics_tracker.get_metrics().get('cdc_events_processed', 0)}"
                )
                print(
                    f"   Data Quality Issues: {metrics_tracker.get_metrics().get('quality_issues', 0)}"
                )
                print(
                    f"   Inventory Alerts: {metrics_tracker.get_metrics().get('inventory_alerts', 0)}"
                )
            except Exception as e:
                print(f"   Metrics error: {e}")

            time.sleep(20)  # Check every 20 seconds

    except KeyboardInterrupt:
        print("\n⚠️  CDC monitoring interrupted by user")

    # Stop all pipelines
    print("\n🔄 Stopping CDC pipelines...")
    for name, result in pipeline_results:
        try:
            print(f"   Stopping {name}...")
            job_client = result.get_job_client()
            if job_client:
                job_client.cancel()
        except Exception as e:
            print(f"   Warning stopping {name}: {e}")

    print("✅ All CDC pipelines stopped")


@handle_errors
def main():
    """Main CDC processing workflow."""
    # Parse arguments
    parser = parse_common_args()
    parser.add_argument(
        "--source-tables",
        default="users,orders,products,order_items",
        help="Comma-separated list of tables to process",
    )
    parser.add_argument(
        "--enable-validation",
        action="store_true",
        help="Enable data quality validation",
    )
    args = parser.parse_args()

    print("🚀 Starting Flink CDC Processing")
    print(f"   Application: {args.app_name}")
    print(f"   Duration: {args.duration} seconds")
    print(f"   Source tables: {args.source_tables}")
    print(f"   Enable validation: {args.enable_validation}")

    # Create Flink configuration
    config = FlinkConfig(
        app_name=f"{args.app_name}_CDCProcessing",
        parallelism=args.parallelism,
        kafka_servers=args.kafka_servers,
        postgres_url=args.postgres_url,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
    )

    # Create environments
    env = create_flink_environment(config)
    table_env = create_table_environment(env)

    # Configure for CDC processing
    table_config = table_env.get_config()
    table_config.set("table.exec.state.ttl", "86400000")  # 24 hours state TTL
    table_config.set("table.optimizer.join-reorder-enabled", "true")

    try:
        # Setup source tables
        setup_cdc_source_tables(table_env)

        # Setup output tables
        postgres_config = {
            "url": config.postgres_url,
            "user": config.postgres_user,
            "password": config.postgres_password,
        }
        setup_output_tables(table_env, config.kafka_servers, postgres_config)

        # Create analytics views
        create_real_time_analytics_views(table_env)

        # Start CDC processing pipelines
        pipeline_results = []

        print("\n🔄 Starting CDC processing pipelines...")

        # Customer analytics
        customer_result = create_customer_analytics_pipeline(table_env)
        pipeline_results.append(("Customer Analytics", customer_result))

        # Product analytics
        product_result = create_product_analytics_pipeline(table_env)
        pipeline_results.append(("Product Analytics", product_result))

        # Lifecycle events
        lifecycle_result = create_lifecycle_event_pipeline(table_env)
        pipeline_results.append(("Lifecycle Events", lifecycle_result))

        # Inventory monitoring
        inventory_result = create_inventory_monitoring_pipeline(table_env)
        pipeline_results.append(("Inventory Monitoring", inventory_result))

        # Data quality monitoring (if enabled)
        if args.enable_validation:
            quality_results = create_data_quality_monitoring(table_env)
            pipeline_results.extend(quality_results)

        # Monitor job progress
        monitor_job_progress(env, "CDC Processing")

        print(f"\n📊 Started {len(pipeline_results)} CDC processing pipelines:")
        for name, _ in pipeline_results:
            print(f"   - {name}")

        print("\n💡 CDC Processing Features:")
        print("   - Real-time customer analytics updates")
        print("   - Product performance tracking")
        print("   - User lifecycle event detection")
        print("   - Inventory level monitoring")
        if args.enable_validation:
            print("   - Data quality validation and alerting")
        print(f"   - Results in Kafka topics and PostgreSQL tables")

        # Monitor pipelines
        monitor_cdc_pipelines(table_env, pipeline_results, args.duration)

        # Print final metrics
        metrics_tracker.print_summary()

        print(f"\n✅ CDC processing completed!")
        print(f"   Ran {len(pipeline_results)} pipelines for {args.duration} seconds")
        print(f"   Real-time analytics available in PostgreSQL")
        print(f"   Event streams available in Kafka")
        print(f"   Flink Web UI: http://192.168.1.184:8081")

    except KeyboardInterrupt:
        print("\n⚠️  CDC processing interrupted by user")
    except Exception as e:
        print(f"\n❌ CDC processing error: {e}")
        raise
    finally:
        cleanup_environment(env)


if __name__ == "__main__":
    main()
