#!/usr/bin/env python3
"""
Trino Federated Queries - Building Block Application

This script demonstrates Trino's federated query capabilities:
- Cross-system joins (PostgreSQL + Kafka + Iceberg + Delta Lake)
- Query optimization across different data sources
- Performance comparison between federated vs single-source queries
- Real-world analytics scenarios using multiple catalogs

Usage:
    bazel run //trino/python:federated_queries
    bazel run //trino/python:federated_queries -- --include-kafka --include-iceberg

Examples:
    # Basic federated queries
    bazel run //trino/python:federated_queries
    
    # Include all data sources
    bazel run //trino/python:federated_queries -- --include-all
    
    # Performance benchmarking
    bazel run //trino/python:federated_queries -- --benchmark

Requirements:
    pip install trino requests
"""

import sys
import argparse
from typing import Dict, List, Any
from trino_common import (
    get_trino_connection,
    execute_query,
    display_results,
    QueryStats,
    get_available_catalogs,
    get_catalog_schemas,
    get_schema_tables,
    parse_common_args,
    setup_logging,
    handle_errors,
)


class FederatedQueryEngine:
    """Engine for executing and analyzing federated queries."""

    def __init__(self, conn):
        self.conn = conn
        self.stats = QueryStats()
        self.available_catalogs = get_available_catalogs(conn)

    def check_catalog_availability(self) -> Dict[str, bool]:
        """Check which catalogs are available in the cluster."""
        catalog_status = {
            "postgresql": "postgresql" in self.available_catalogs,
            "kafka": "kafka" in self.available_catalogs,
            "iceberg": "iceberg" in self.available_catalogs,
            "delta": "delta" in self.available_catalogs,
            "memory": "memory" in self.available_catalogs,
            "tpch": "tpch" in self.available_catalogs,
        }

        print("🔍 Catalog Availability Check:")
        for catalog, available in catalog_status.items():
            status = "✅" if available else "❌"
            print(f"  {status} {catalog}")

        return catalog_status

    def create_sample_data(self):
        """Create sample data in the memory catalog for demonstration."""
        print("\n📝 Creating sample data in memory catalog...")

        # Create sample customers table
        create_customers = """
            CREATE TABLE IF NOT EXISTS memory.default.customers AS
            SELECT * FROM (VALUES
                (1, 'Alice Johnson', 'alice@example.com', 'Premium', 'USA'),
                (2, 'Bob Smith', 'bob@example.com', 'Standard', 'Canada'), 
                (3, 'Charlie Brown', 'charlie@example.com', 'Premium', 'USA'),
                (4, 'Diana Prince', 'diana@example.com', 'Standard', 'UK'),
                (5, 'Eve Wilson', 'eve@example.com', 'Premium', 'Australia')
            ) AS t(id, name, email, tier, country)
        """

        # Create sample orders table
        create_orders = """
            CREATE TABLE IF NOT EXISTS memory.default.orders AS
            SELECT * FROM (VALUES
                (101, 1, 250.00, DATE '2024-01-15', 'completed'),
                (102, 2, 150.00, DATE '2024-01-16', 'completed'),
                (103, 1, 320.00, DATE '2024-01-17', 'completed'),
                (104, 3, 450.00, DATE '2024-01-18', 'pending'),
                (105, 4, 180.00, DATE '2024-01-19', 'completed'),
                (106, 5, 720.00, DATE '2024-01-20', 'completed'),
                (107, 2, 95.00, DATE '2024-01-21', 'cancelled'),
                (108, 3, 380.00, DATE '2024-01-22', 'completed')
            ) AS t(order_id, customer_id, amount, order_date, status)
        """

        # Create sample products table
        create_products = """
            CREATE TABLE IF NOT EXISTS memory.default.products AS
            SELECT * FROM (VALUES
                ('PROD-001', 'Laptop Pro', 'Electronics', 1299.99, 50),
                ('PROD-002', 'Wireless Mouse', 'Electronics', 29.99, 200),
                ('PROD-003', 'Coffee Maker', 'Appliances', 89.99, 75),
                ('PROD-004', 'Office Chair', 'Furniture', 199.99, 25),
                ('PROD-005', 'Monitor 27"', 'Electronics', 349.99, 40)
            ) AS t(product_id, name, category, price, inventory)
        """

        try:
            execute_query(self.conn, create_customers, "Creating customers table")
            execute_query(self.conn, create_orders, "Creating orders table")
            execute_query(self.conn, create_products, "Creating products table")
            print("✅ Sample data created successfully!")
        except Exception as e:
            print(f"⚠️ Could not create sample data: {e}")

    def basic_federated_queries(self):
        """Execute basic federated query examples."""
        print("\n🌐 STEP 1: Basic Federated Queries")
        print("-" * 40)

        # Cross-catalog information query
        query = """
            SELECT 
                'postgresql' as catalog_name,
                COUNT(*) as table_count,
                'OLTP Database' as description
            FROM postgresql.information_schema.tables
            WHERE table_schema = 'public'
            
            UNION ALL
            
            SELECT 
                'memory' as catalog_name,
                COUNT(*) as table_count,
                'In-Memory Data' as description
            FROM memory.information_schema.tables
            WHERE table_schema = 'default'
        """

        try:
            results, exec_time = execute_query(
                self.conn, query, "Cross-catalog information"
            )
            display_results(results, ["Catalog", "Tables", "Description"])
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Basic federated query failed: {e}")

    def customer_analytics_federation(self):
        """Demonstrate customer analytics using federated queries."""
        print("\n👥 STEP 2: Customer Analytics Federation")
        print("-" * 40)

        # Customer analysis across different data sources
        query = """
            WITH customer_summary AS (
                SELECT 
                    c.id,
                    c.name,
                    c.country,
                    c.tier,
                    COUNT(o.order_id) as total_orders,
                    COALESCE(SUM(o.amount), 0) as total_spent,
                    COALESCE(AVG(o.amount), 0) as avg_order_value,
                    MAX(o.order_date) as last_order_date
                FROM memory.default.customers c
                LEFT JOIN memory.default.orders o ON c.id = o.customer_id
                WHERE o.status = 'completed'
                GROUP BY c.id, c.name, c.country, c.tier
            )
            SELECT 
                name,
                country,
                tier,
                total_orders,
                ROUND(total_spent, 2) as total_spent,
                ROUND(avg_order_value, 2) as avg_order_value,
                last_order_date,
                CASE 
                    WHEN total_spent > 500 THEN 'High Value'
                    WHEN total_spent > 200 THEN 'Medium Value'
                    ELSE 'Low Value'
                END as customer_segment
            FROM customer_summary
            ORDER BY total_spent DESC
        """

        try:
            results, exec_time = execute_query(self.conn, query, "Customer analytics")
            headers = [
                "Name",
                "Country",
                "Tier",
                "Orders",
                "Total Spent",
                "Avg Order",
                "Last Order",
                "Segment",
            ]
            display_results(results, headers)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Customer analytics query failed: {e}")

    def cross_system_joins(self):
        """Demonstrate complex joins across different systems."""
        print("\n🔗 STEP 3: Cross-System Joins")
        print("-" * 40)

        # Example of joining data from different catalogs
        query = """
            WITH order_details AS (
                SELECT 
                    o.order_id,
                    o.customer_id,
                    o.amount,
                    o.order_date,
                    c.name as customer_name,
                    c.country,
                    c.tier
                FROM memory.default.orders o
                JOIN memory.default.customers c ON o.customer_id = c.id
                WHERE o.status = 'completed'
            ),
            country_stats AS (
                SELECT 
                    country,
                    COUNT(*) as orders_count,
                    SUM(amount) as total_revenue,
                    AVG(amount) as avg_order_amount,
                    COUNT(DISTINCT customer_id) as unique_customers
                FROM order_details
                GROUP BY country
            )
            SELECT 
                cs.country,
                cs.orders_count,
                ROUND(cs.total_revenue, 2) as total_revenue,
                ROUND(cs.avg_order_amount, 2) as avg_order_amount,
                cs.unique_customers,
                ROUND(cs.total_revenue / cs.unique_customers, 2) as revenue_per_customer
            FROM country_stats cs
            ORDER BY total_revenue DESC
        """

        try:
            results, exec_time = execute_query(
                self.conn, query, "Cross-system country analysis"
            )
            headers = [
                "Country",
                "Orders",
                "Total Revenue",
                "Avg Order",
                "Customers",
                "Revenue/Customer",
            ]
            display_results(results, headers)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Cross-system joins query failed: {e}")

    def time_series_analysis(self):
        """Demonstrate time-series analysis using federated data."""
        print("\n📈 STEP 4: Time-Series Analysis")
        print("-" * 40)

        query = """
            WITH daily_metrics AS (
                SELECT 
                    o.order_date,
                    COUNT(*) as daily_orders,
                    SUM(o.amount) as daily_revenue,
                    AVG(o.amount) as avg_daily_order_value,
                    COUNT(DISTINCT o.customer_id) as unique_customers
                FROM memory.default.orders o
                WHERE o.status = 'completed'
                GROUP BY o.order_date
            ),
            metrics_with_trends AS (
                SELECT 
                    order_date,
                    daily_orders,
                    ROUND(daily_revenue, 2) as daily_revenue,
                    ROUND(avg_daily_order_value, 2) as avg_order_value,
                    unique_customers,
                    LAG(daily_revenue) OVER (ORDER BY order_date) as prev_day_revenue,
                    AVG(daily_revenue) OVER (
                        ORDER BY order_date 
                        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                    ) as three_day_avg_revenue
                FROM daily_metrics
            )
            SELECT 
                order_date,
                daily_orders,
                daily_revenue,
                avg_order_value,
                unique_customers,
                CASE 
                    WHEN prev_day_revenue IS NULL THEN 'N/A'
                    WHEN daily_revenue > prev_day_revenue THEN 'Up'
                    WHEN daily_revenue < prev_day_revenue THEN 'Down'
                    ELSE 'Same'
                END as revenue_trend,
                ROUND(COALESCE(three_day_avg_revenue, daily_revenue), 2) as three_day_avg
            FROM metrics_with_trends
            ORDER BY order_date
        """

        try:
            results, exec_time = execute_query(self.conn, query, "Time-series analysis")
            headers = [
                "Date",
                "Orders",
                "Revenue",
                "Avg Order",
                "Customers",
                "Trend",
                "3-Day Avg",
            ]
            display_results(results, headers)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Time-series analysis query failed: {e}")

    def advanced_analytics_queries(self):
        """Execute advanced analytics queries using window functions and CTEs."""
        print("\n🧠 STEP 5: Advanced Analytics")
        print("-" * 40)

        query = """
            WITH customer_behavior AS (
                SELECT 
                    c.id,
                    c.name,
                    c.tier,
                    COUNT(o.order_id) as total_orders,
                    SUM(o.amount) as total_spent,
                    AVG(o.amount) as avg_order_value,
                    MIN(o.order_date) as first_order,
                    MAX(o.order_date) as last_order,
                    DATE_DIFF('day', MIN(o.order_date), MAX(o.order_date)) as customer_lifetime_days
                FROM memory.default.customers c
                LEFT JOIN memory.default.orders o ON c.id = o.customer_id AND o.status = 'completed'
                GROUP BY c.id, c.name, c.tier
            ),
            customer_segments AS (
                SELECT 
                    *,
                    NTILE(3) OVER (ORDER BY total_spent DESC) as spending_tercile,
                    NTILE(3) OVER (ORDER BY total_orders DESC) as frequency_tercile,
                    CASE 
                        WHEN customer_lifetime_days = 0 THEN 'Single Purchase'
                        WHEN customer_lifetime_days <= 7 THEN 'New Customer'
                        WHEN customer_lifetime_days <= 30 THEN 'Regular Customer'
                        ELSE 'Loyal Customer'
                    END as lifecycle_stage
                FROM customer_behavior
            )
            SELECT 
                name,
                tier,
                total_orders,
                ROUND(total_spent, 2) as total_spent,
                ROUND(avg_order_value, 2) as avg_order_value,
                customer_lifetime_days,
                lifecycle_stage,
                CASE spending_tercile
                    WHEN 1 THEN 'High Spender'
                    WHEN 2 THEN 'Medium Spender'
                    ELSE 'Low Spender'
                END as spending_segment,
                CASE frequency_tercile
                    WHEN 1 THEN 'High Frequency'
                    WHEN 2 THEN 'Medium Frequency'  
                    ELSE 'Low Frequency'
                END as frequency_segment
            FROM customer_segments
            ORDER BY total_spent DESC
        """

        try:
            results, exec_time = execute_query(
                self.conn, query, "Advanced customer segmentation"
            )
            headers = [
                "Name",
                "Tier",
                "Orders",
                "Total Spent",
                "Avg Order",
                "Days",
                "Lifecycle",
                "Spending",
                "Frequency",
            ]
            display_results(results, headers, max_rows=15)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Advanced analytics query failed: {e}")

    def performance_comparison(self):
        """Compare performance of federated vs single-catalog queries."""
        print("\n⚡ STEP 6: Performance Comparison")
        print("-" * 40)

        # Single-catalog query
        single_catalog_query = """
            SELECT 
                tier,
                COUNT(*) as customer_count,
                AVG(id) as avg_id
            FROM memory.default.customers
            GROUP BY tier
            ORDER BY customer_count DESC
        """

        # Multi-catalog simulation (using memory twice)
        multi_catalog_query = """
            SELECT 
                'memory_customers' as source,
                tier,
                COUNT(*) as customer_count
            FROM memory.default.customers
            GROUP BY tier
            
            UNION ALL
            
            SELECT 
                'memory_backup' as source,
                tier, 
                COUNT(*) as customer_count
            FROM memory.default.customers
            GROUP BY tier
        """

        try:
            # Execute single-catalog query
            print("🔍 Testing single-catalog query performance...")
            results1, exec_time1 = execute_query(
                self.conn, single_catalog_query, "Single-catalog query"
            )
            display_results(results1, ["Tier", "Count", "Avg ID"])

            # Execute multi-catalog query
            print("🔍 Testing multi-catalog query performance...")
            results2, exec_time2 = execute_query(
                self.conn, multi_catalog_query, "Multi-catalog query"
            )
            display_results(results2, ["Source", "Tier", "Count"])

            # Performance comparison
            print(f"\n📊 Performance Comparison:")
            print(f"  Single-catalog: {exec_time1:.3f}s")
            print(f"  Multi-catalog:  {exec_time2:.3f}s")
            print(f"  Overhead:       {((exec_time2/exec_time1-1)*100):.1f}%")

            self.stats.record_query(exec_time1, len(results1))
            self.stats.record_query(exec_time2, len(results2))

        except Exception as e:
            print(f"⚠️ Performance comparison failed: {e}")


@handle_errors
def demonstrate_federated_queries(args):
    """
    Main demonstration of federated query capabilities.

    Args:
        args: Command line arguments
    """
    print("🌐 Starting Trino Federated Queries Demo")
    print("=" * 50)

    # Connect to Trino
    conn = get_trino_connection(user=args.user)

    try:
        # Initialize federated query engine
        fed_engine = FederatedQueryEngine(conn)

        # Check catalog availability
        catalog_status = fed_engine.check_catalog_availability()

        # Create sample data for demonstration
        if catalog_status.get("memory", False):
            fed_engine.create_sample_data()
        else:
            print("⚠️ Memory catalog not available - some examples may not work")

        # Run federated query examples
        if args.include_basic or args.include_all:
            fed_engine.basic_federated_queries()

        if args.include_analytics or args.include_all:
            fed_engine.customer_analytics_federation()

        if args.include_joins or args.include_all:
            fed_engine.cross_system_joins()

        if args.include_timeseries or args.include_all:
            fed_engine.time_series_analysis()

        if args.include_advanced or args.include_all:
            fed_engine.advanced_analytics_queries()

        if args.benchmark or args.include_all:
            fed_engine.performance_comparison()

        # Display final statistics
        fed_engine.stats.print_summary()

    finally:
        conn.close()
        print("\n🔌 Connection closed")

    print("\n✅ Federated queries demonstration completed!")


def main():
    """Main function for federated queries demo."""
    parser = parse_common_args()

    # Add federated query specific arguments
    parser.add_argument(
        "--include-all",
        action="store_true",
        default=True,
        help="Run all examples (default)",
    )
    parser.add_argument(
        "--include-basic", action="store_true", help="Include basic federated queries"
    )
    parser.add_argument(
        "--include-analytics", action="store_true", help="Include customer analytics"
    )
    parser.add_argument(
        "--include-joins", action="store_true", help="Include cross-system joins"
    )
    parser.add_argument(
        "--include-timeseries", action="store_true", help="Include time-series analysis"
    )
    parser.add_argument(
        "--include-advanced", action="store_true", help="Include advanced analytics"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run performance benchmarks"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # If specific includes are set, disable include_all
    if any(
        [
            args.include_basic,
            args.include_analytics,
            args.include_joins,
            args.include_timeseries,
            args.include_advanced,
            args.benchmark,
        ]
    ):
        args.include_all = False

    demonstrate_federated_queries(args)


if __name__ == "__main__":
    main()
