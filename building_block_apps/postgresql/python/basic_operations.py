#!/usr/bin/env python3
"""
PostgreSQL Basic Operations - Building Block Application

This script demonstrates basic PostgreSQL database operations:
- CRUD operations (Create, Read, Update, Delete)
- Table management and schema operations
- Data insertion and bulk operations
- Basic queries with filtering and sorting
- Transaction handling

Usage:
    bazel run //postgresql/python:basic_operations
    bazel run //postgresql/python:basic_operations -- --create-tables --insert-data

Examples:
    # Basic operations demo
    bazel run //postgresql/python:basic_operations
    
    # Setup fresh tables and data
    bazel run //postgresql/python:basic_operations -- --create-tables --insert-data
    
    # Run specific operations
    bazel run //postgresql/python:basic_operations -- --operations crud

Requirements:
    pip install psycopg2-binary
"""

import sys
import argparse
from typing import List, Dict, Any
from postgresql_common import (
    PostgreSQLConnection,
    PostgreSQLConfig,
    display_results,
    QueryStats,
    get_database_info,
    create_sample_tables,
    insert_sample_data,
    parse_common_args,
    setup_logging,
    handle_errors,
)


class BasicOperations:
    """Demonstrate basic PostgreSQL operations."""

    def __init__(self, pg_conn: PostgreSQLConnection):
        self.pg_conn = pg_conn
        self.stats = QueryStats()

    def demonstrate_create_operations(self):
        """Demonstrate CREATE operations (INSERT)."""
        print("\n📝 CREATE Operations (INSERT)")
        print("-" * 35)

        # Insert single customer
        insert_query = """
            INSERT INTO customers (name, email, phone, address, tier, country)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, email, tier
        """

        customer_data = (
            "John Doe",
            "john.doe@example.com",
            "+1-555-9999",
            "999 Example St, Test City, TC",
            "Premium",
            "USA",
        )

        try:
            results, exec_time = self.pg_conn.execute_query(
                insert_query, customer_data, "Inserting new customer"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Insert operation failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Bulk insert products
        bulk_products = [
            (
                "WIDGET-001",
                "Smart Widget",
                "IoT smart widget",
                "Electronics",
                99.99,
                150,
            ),
            (
                "GADGET-001",
                "Multi-Gadget",
                "Versatile gadget",
                "Electronics",
                149.99,
                75,
            ),
            ("TOOL-001", "Power Tool", "Professional power tool", "Tools", 199.99, 50),
        ]

        bulk_insert_query = """
            INSERT INTO products (product_code, name, description, category, price, inventory)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        print(f"\n📦 Bulk inserting {len(bulk_products)} products...")
        try:
            for product in bulk_products:
                self.pg_conn.execute_query(
                    bulk_insert_query,
                    product,
                    f"Inserting {product[1]}",
                    fetch_results=False,
                )

            # Verify bulk insert
            verify_query = "SELECT product_code, name, price FROM products WHERE product_code LIKE 'WIDGET%' OR product_code LIKE 'GADGET%' OR product_code LIKE 'TOOL%'"
            results, exec_time = self.pg_conn.execute_query(
                verify_query, description="Verifying bulk insert"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))

        except Exception as e:
            print(f"⚠️ Bulk insert failed: {e}")
            self.stats.record_query(0, 0, error=True)

    def demonstrate_read_operations(self):
        """Demonstrate READ operations (SELECT)."""
        print("\n📖 READ Operations (SELECT)")
        print("-" * 30)

        # Simple SELECT with filtering
        print("🔍 1. Simple SELECT with WHERE clause:")
        query1 = """
            SELECT id, name, email, tier, country
            FROM customers
            WHERE tier = 'Premium'
            ORDER BY name
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                query1, description="Selecting Premium customers"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ SELECT query failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # SELECT with JOIN
        print("\n🔗 2. SELECT with JOIN:")
        query2 = """
            SELECT 
                c.name as customer_name,
                c.country,
                o.id as order_id,
                o.order_date,
                o.total_amount,
                o.status
            FROM customers c
            JOIN orders o ON c.id = o.customer_id
            WHERE o.total_amount > 100
            ORDER BY o.total_amount DESC
            LIMIT 10
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                query2, description="Customers with large orders"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ JOIN query failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Aggregation query
        print("\n📊 3. Aggregation query:")
        query3 = """
            SELECT 
                country,
                COUNT(*) as customer_count,
                COUNT(DISTINCT tier) as tier_count,
                STRING_AGG(DISTINCT tier, ', ') as tiers
            FROM customers
            GROUP BY country
            ORDER BY customer_count DESC
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                query3, description="Customer statistics by country"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Aggregation query failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Complex query with subquery
        print("\n🧮 4. Complex query with subquery:")
        query4 = """
            SELECT 
                p.name as product_name,
                p.category,
                p.price,
                p.inventory,
                COALESCE(order_stats.total_ordered, 0) as total_ordered,
                (p.inventory - COALESCE(order_stats.total_ordered, 0)) as remaining_inventory
            FROM products p
            LEFT JOIN (
                SELECT 
                    CAST(metadata->>'items'->0->>'product' AS VARCHAR) as product_code,
                    COUNT(*) as total_ordered
                FROM orders
                WHERE status IN ('completed', 'shipped')
                GROUP BY CAST(metadata->>'items'->0->>'product' AS VARCHAR)
            ) order_stats ON p.product_code = order_stats.product_code
            ORDER BY total_ordered DESC NULLS LAST
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                query4, description="Product inventory analysis"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Complex query failed: {e}")
            self.stats.record_query(0, 0, error=True)

    def demonstrate_update_operations(self):
        """Demonstrate UPDATE operations."""
        print("\n✏️ UPDATE Operations")
        print("-" * 20)

        # Single record update
        print("🔧 1. Single record update:")
        update_query1 = """
            UPDATE customers 
            SET tier = 'VIP', updated_at = CURRENT_TIMESTAMP
            WHERE email = 'john.doe@example.com'
            RETURNING id, name, tier, updated_at
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                update_query1, description="Updating customer tier"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Update operation failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Bulk update with conditions
        print("\n📦 2. Bulk update with conditions:")
        update_query2 = """
            UPDATE products 
            SET price = price * 0.9,
                updated_at = CURRENT_TIMESTAMP
            WHERE category = 'Electronics' 
                AND price > 100
            RETURNING product_code, name, price
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                update_query2,
                description="Applying 10% discount to expensive electronics",
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Bulk update failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Update with JOIN
        print("\n🔗 3. Update with JOIN (PostgreSQL specific):")
        update_query3 = """
            UPDATE orders
            SET status = 'priority',
                updated_at = CURRENT_TIMESTAMP
            FROM customers c
            WHERE orders.customer_id = c.id 
                AND c.tier IN ('Premium', 'VIP')
                AND orders.status = 'pending'
            RETURNING orders.id, orders.status, c.name, c.tier
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                update_query3, description="Prioritizing orders for premium customers"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Update with JOIN failed: {e}")
            self.stats.record_query(0, 0, error=True)

    def demonstrate_delete_operations(self):
        """Demonstrate DELETE operations."""
        print("\n🗑️ DELETE Operations")
        print("-" * 20)

        # Create some test data for deletion
        print("📝 Creating test data for deletion...")
        test_insert = """
            INSERT INTO customers (name, email, tier, country)
            VALUES 
                ('Test User 1', 'test1@delete.com', 'Standard', 'Test'),
                ('Test User 2', 'test2@delete.com', 'Standard', 'Test'),
                ('Test User 3', 'test3@delete.com', 'Standard', 'Test')
            RETURNING id, name, email
        """

        try:
            results, _ = self.pg_conn.execute_query(
                test_insert, description="Creating test users for deletion"
            )
            display_results(results)
        except Exception as e:
            print(f"⚠️ Could not create test data: {e}")
            return

        # Simple DELETE
        print("\n🗑️ 1. Simple DELETE with WHERE clause:")
        delete_query1 = """
            DELETE FROM customers 
            WHERE email = 'test1@delete.com'
            RETURNING id, name, email
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                delete_query1, description="Deleting single test user"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Delete operation failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Conditional DELETE
        print("\n📋 2. Conditional DELETE:")
        delete_query2 = """
            DELETE FROM customers 
            WHERE country = 'Test' 
                AND tier = 'Standard'
                AND created_at > CURRENT_DATE - INTERVAL '1 day'
            RETURNING id, name, email
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                delete_query2, description="Deleting test users by criteria"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Conditional delete failed: {e}")
            self.stats.record_query(0, 0, error=True)

    def demonstrate_transactions(self):
        """Demonstrate transaction handling."""
        print("\n🔄 Transaction Operations")
        print("-" * 25)

        print("💳 Simulating order processing with transactions...")

        try:
            with self.pg_conn.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Start transaction (automatic)
                    print("🔄 Starting transaction...")

                    # Check customer exists
                    cursor.execute(
                        "SELECT id, name, tier FROM customers WHERE id = %s", (1,)
                    )
                    customer = cursor.fetchone()

                    if not customer:
                        print("❌ Customer not found!")
                        return

                    print(
                        f"✅ Processing order for customer: {customer['name']} ({customer['tier']})"
                    )

                    # Insert new order
                    cursor.execute(
                        """
                        INSERT INTO orders (customer_id, total_amount, payment_method, status, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, total_amount
                    """,
                        (
                            customer["id"],
                            299.99,
                            "credit_card",
                            "processing",
                            '{"items": [{"product": "CHAIR-001", "quantity": 1}], "transaction_id": "txn_12345"}',
                        ),
                    )

                    order = cursor.fetchone()
                    print(
                        f"📝 Created order {order['id']} for ${order['total_amount']}"
                    )

                    # Update product inventory
                    cursor.execute(
                        """
                        UPDATE products 
                        SET inventory = inventory - 1,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE product_code = %s AND inventory > 0
                        RETURNING product_code, inventory
                    """,
                        ("CHAIR-001",),
                    )

                    product = cursor.fetchone()
                    if product:
                        print(
                            f"📦 Updated inventory for {product['product_code']}: {product['inventory']} remaining"
                        )
                    else:
                        print("❌ Insufficient inventory!")
                        conn.rollback()
                        return

                    # Update order status
                    cursor.execute(
                        """
                        UPDATE orders 
                        SET status = 'confirmed',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING id, status
                    """,
                        (order["id"],),
                    )

                    final_order = cursor.fetchone()
                    print(
                        f"✅ Order {final_order['id']} status: {final_order['status']}"
                    )

                    # Commit transaction
                    conn.commit()
                    print("✅ Transaction committed successfully!")

                    self.stats.record_query(0.1, 3)  # Approximate stats for transaction

        except Exception as e:
            print(f"❌ Transaction failed and rolled back: {e}")
            self.stats.record_query(0, 0, error=True)

    def demonstrate_data_types(self):
        """Demonstrate working with different PostgreSQL data types."""
        print("\n🔢 Data Types Demonstration")
        print("-" * 30)

        # JSON operations
        print("📄 1. JSON operations:")
        json_query = """
            SELECT 
                o.id,
                o.metadata->>'transaction_id' as transaction_id,
                o.metadata->'items'->0->>'product' as first_product,
                jsonb_array_length(o.metadata->'items') as item_count,
                o.metadata->'items' as items_json
            FROM orders o
            WHERE o.metadata IS NOT NULL
            LIMIT 5
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                json_query, description="JSON data extraction"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ JSON query failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Array operations
        print("\n🔢 2. Array operations:")
        array_query = """
            SELECT 
                'Sample Array' as description,
                ARRAY[1, 2, 3, 4, 5] as number_array,
                ARRAY['apple', 'banana', 'orange'] as fruit_array,
                array_length(ARRAY[1, 2, 3, 4, 5], 1) as array_length,
                3 = ANY(ARRAY[1, 2, 3, 4, 5]) as contains_three
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                array_query, description="Array operations"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Array query failed: {e}")
            self.stats.record_query(0, 0, error=True)

        # Date/Time operations
        print("\n📅 3. Date/Time operations:")
        datetime_query = """
            SELECT 
                CURRENT_TIMESTAMP as now,
                CURRENT_DATE as today,
                CURRENT_TIME as current_time,
                NOW() - INTERVAL '7 days' as week_ago,
                EXTRACT(YEAR FROM CURRENT_TIMESTAMP) as current_year,
                EXTRACT(MONTH FROM CURRENT_TIMESTAMP) as current_month,
                TO_CHAR(CURRENT_TIMESTAMP, 'YYYY-MM-DD HH24:MI:SS') as formatted_time,
                AGE(CURRENT_TIMESTAMP, '2024-01-01'::timestamp) as age_from_2024
        """

        try:
            results, exec_time = self.pg_conn.execute_query(
                datetime_query, description="Date/Time operations"
            )
            display_results(results)
            self.stats.record_query(exec_time, len(results))
        except Exception as e:
            print(f"⚠️ Date/Time query failed: {e}")
            self.stats.record_query(0, 0, error=True)


@handle_errors
def demonstrate_basic_operations(args):
    """
    Main demonstration of basic PostgreSQL operations.

    Args:
        args: Command line arguments
    """
    print("🐘 Starting PostgreSQL Basic Operations Demo")
    print("=" * 50)

    # Initialize PostgreSQL connection
    config = PostgreSQLConfig()
    if args.host != config.HOST:
        config.HOST = args.host
    if args.port != config.PORT:
        config.PORT = args.port
    if args.database != config.DATABASE:
        config.DATABASE = args.database
    if args.user != config.USER:
        config.USER = args.user
    if args.password != config.PASSWORD:
        config.PASSWORD = args.password

    pg_conn = PostgreSQLConnection(config)

    try:
        # Get database information
        db_info = get_database_info(pg_conn)
        if db_info.get("version"):
            print(f"🖥️ Connected to: {db_info['version']['version']}")

        # Create tables and sample data if requested
        if args.create_tables:
            create_sample_tables(pg_conn)

        if args.insert_data:
            insert_sample_data(pg_conn)

        # Initialize operations demo
        ops_demo = BasicOperations(pg_conn)

        # Run operations based on arguments
        if args.operations == "all" or "create" in args.operations:
            ops_demo.demonstrate_create_operations()

        if args.operations == "all" or "read" in args.operations:
            ops_demo.demonstrate_read_operations()

        if args.operations == "all" or "update" in args.operations:
            ops_demo.demonstrate_update_operations()

        if args.operations == "all" or "delete" in args.operations:
            ops_demo.demonstrate_delete_operations()

        if args.operations == "all" or "transactions" in args.operations:
            ops_demo.demonstrate_transactions()

        if args.operations == "all" or "datatypes" in args.operations:
            ops_demo.demonstrate_data_types()

        # Display final statistics
        ops_demo.stats.print_summary()

        # Display connection statistics
        conn_stats = pg_conn.get_stats()
        print("\n🔌 Connection Statistics:")
        for key, value in conn_stats.items():
            formatted_key = key.replace("_", " ").title()
            print(f"{formatted_key:.<25} {value}")

    finally:
        pg_conn.close_pool()
        print("\n🔌 Connection pool closed")

    print("\n✅ Basic operations demonstration completed!")


def main():
    """Main function for basic operations demo."""
    parser = parse_common_args()

    # Add basic operations specific arguments
    parser.add_argument(
        "--create-tables", action="store_true", help="Create sample tables"
    )
    parser.add_argument("--insert-data", action="store_true", help="Insert sample data")
    parser.add_argument(
        "--operations",
        nargs="*",
        choices=[
            "all",
            "create",
            "read",
            "update",
            "delete",
            "transactions",
            "datatypes",
        ],
        default=["all"],
        help="Operations to demonstrate",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # Convert operations list to set for easy checking
    if (
        isinstance(args.operations, list)
        and len(args.operations) == 1
        and args.operations[0] == "all"
    ):
        args.operations = "all"

    demonstrate_basic_operations(args)


if __name__ == "__main__":
    main()
