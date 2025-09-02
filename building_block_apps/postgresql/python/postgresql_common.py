#!/usr/bin/env python3
"""
PostgreSQL Common Utilities for Building Block Applications

This module provides common utilities for PostgreSQL building block examples:
- Connection management with pooling
- Query execution helpers
- Transaction management
- Error handling and logging
- Data formatting and display utilities
- Performance monitoring

Requirements:
    pip install psycopg2-binary
"""

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import argparse
import logging
from contextlib import contextmanager

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    from psycopg2 import sql
except ImportError:
    print("❌ Error: psycopg2 library not found!")
    print("📦 Install with: pip install psycopg2-binary")
    sys.exit(1)


class PostgreSQLConfig:
    """PostgreSQL configuration for building block apps."""

    # PostgreSQL settings (from your setup)
    HOST = "192.168.1.184"
    PORT = 5432
    DATABASE = "analytics_db"
    USER = "dataeng"
    PASSWORD = "password"

    # Connection pool settings
    MIN_CONNECTIONS = 1
    MAX_CONNECTIONS = 20

    # Query timeout settings
    QUERY_TIMEOUT = 300
    CONNECTION_TIMEOUT = 30

    # Performance settings
    AUTOCOMMIT = True
    ISOLATION_LEVEL = psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED


class PostgreSQLConnection:
    """Enhanced PostgreSQL connection manager with pooling and monitoring."""

    def __init__(self, config: Optional[PostgreSQLConfig] = None):
        self.config = config or PostgreSQLConfig()
        self.pool = None
        self.stats = {"queries": 0, "errors": 0, "connections": 0}

    def create_connection_pool(self) -> psycopg2.pool.ThreadedConnectionPool:
        """Create a connection pool for efficient connection management."""
        try:
            dsn = (
                f"host={self.config.HOST} port={self.config.PORT} "
                f"dbname={self.config.DATABASE} user={self.config.USER} "
                f"password={self.config.PASSWORD}"
            )

            self.pool = psycopg2.pool.ThreadedConnectionPool(
                self.config.MIN_CONNECTIONS,
                self.config.MAX_CONNECTIONS,
                dsn,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )

            print(
                f"🔌 Created connection pool: {self.config.MIN_CONNECTIONS}-{self.config.MAX_CONNECTIONS} connections"
            )
            print(
                f"📍 Target: {self.config.HOST}:{self.config.PORT}/{self.config.DATABASE}"
            )
            return self.pool

        except Exception as e:
            print(f"❌ Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        if not self.pool:
            self.create_connection_pool()

        conn = None
        try:
            conn = self.pool.getconn()
            self.stats["connections"] += 1
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def execute_query(
        self,
        query: Union[str, sql.SQL],
        params: Tuple = None,
        description: str = "",
        fetch_results: bool = True,
    ) -> Tuple[List, float]:
        """
        Execute a PostgreSQL query with timing and error handling.

        Args:
            query: SQL query to execute
            params: Query parameters
            description: Description for logging
            fetch_results: Whether to fetch and return results

        Returns:
            Tuple of (results, execution_time_seconds)
        """
        print(f"\n🔍 {description or 'Executing query'}")
        query_str = (
            query.as_string(self.pool.getconn())
            if hasattr(query, "as_string")
            else str(query)
        )
        print(f"📝 Query: {query_str[:100]}{'...' if len(query_str) > 100 else ''}")

        start_time = time.time()
        results = []

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)

                    if fetch_results and cursor.description:
                        results = cursor.fetchall()
                    elif not fetch_results:
                        conn.commit()

            execution_time = time.time() - start_time

            if fetch_results and results:
                print(
                    f"✅ Query completed in {execution_time:.3f}s, returned {len(results)} rows"
                )
            else:
                print(f"✅ Query completed in {execution_time:.3f}s")

            self.stats["queries"] += 1
            return results, execution_time

        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ Query failed after {execution_time:.3f}s: {e}")
            self.stats["errors"] += 1
            raise

    def close_pool(self):
        """Close the connection pool."""
        if self.pool:
            self.pool.closeall()
            print("🔌 Connection pool closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection and query statistics."""
        success_rate = (
            (self.stats["queries"] - self.stats["errors"])
            / max(self.stats["queries"], 1)
            * 100
        )

        return {
            "queries_executed": self.stats["queries"],
            "errors": self.stats["errors"],
            "connections_used": self.stats["connections"],
            "success_rate": f"{success_rate:.1f}%",
        }


def display_results(results: List[Dict], max_rows: int = 20):
    """
    Display query results in a formatted table.

    Args:
        results: Query results (list of dictionaries)
        max_rows: Maximum number of rows to display
    """
    if not results:
        print("📭 No results to display")
        return

    # Get headers from first row
    headers = list(results[0].keys())

    # Calculate column widths
    widths = [len(str(header)) for header in headers]
    for row in results[:max_rows]:
        for i, header in enumerate(headers):
            widths[i] = max(widths[i], len(str(row.get(header, ""))))

    # Print header
    print("\n📊 Query Results:")
    print("┌" + "┬".join("─" * (w + 2) for w in widths) + "┐")
    print(
        "│"
        + "│".join(f" {headers[i]:<{widths[i]}} " for i in range(len(headers)))
        + "│"
    )
    print("├" + "┼".join("─" * (w + 2) for w in widths) + "┤")

    # Print rows
    displayed_rows = 0
    for row in results:
        if displayed_rows >= max_rows:
            remaining = len(results) - displayed_rows
            print(
                f"│ ... and {remaining} more rows"
                + " " * (sum(widths) + len(widths) * 3 - 20 - len(str(remaining)))
                + "│"
            )
            break

        row_values = [str(row.get(header, "")) for header in headers]
        print(
            "│"
            + "│".join(f" {row_values[i]:<{widths[i]}} " for i in range(len(headers)))
            + "│"
        )
        displayed_rows += 1

    print("└" + "┴".join("─" * (w + 2) for w in widths) + "┘")
    print(
        f"📈 Displayed {min(displayed_rows, len(results))} of {len(results)} total rows"
    )


def get_database_info(pg_conn: PostgreSQLConnection) -> Dict[str, Any]:
    """Get information about the PostgreSQL database."""
    try:
        # Database version and settings
        version_query = "SELECT version() as version"
        version_result, _ = pg_conn.execute_query(
            version_query, description="Getting database version"
        )

        # Database size information
        size_query = """
            SELECT 
                pg_database.datname as database_name,
                pg_size_pretty(pg_database_size(pg_database.datname)) as size
            FROM pg_database
            WHERE datname = current_database()
        """
        size_result, _ = pg_conn.execute_query(
            size_query, description="Getting database size"
        )

        # Table information
        tables_query = """
            SELECT 
                schemaname,
                tablename,
                tableowner,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 10
        """
        tables_result, _ = pg_conn.execute_query(
            tables_query, description="Getting table information"
        )

        return {
            "version": version_result[0] if version_result else {},
            "size": size_result[0] if size_result else {},
            "tables": tables_result,
        }

    except Exception as e:
        print(f"⚠️ Could not retrieve database info: {e}")
        return {}


def create_sample_tables(pg_conn: PostgreSQLConnection):
    """Create sample tables for demonstration purposes."""
    print("\n📝 Creating sample tables...")

    # Drop existing tables if they exist
    drop_queries = [
        "DROP TABLE IF EXISTS orders CASCADE",
        "DROP TABLE IF EXISTS customers CASCADE",
        "DROP TABLE IF EXISTS products CASCADE",
    ]

    for query in drop_queries:
        try:
            pg_conn.execute_query(
                query, description="Dropping existing table", fetch_results=False
            )
        except Exception as e:
            print(f"⚠️ Could not drop table: {e}")

    # Create customers table
    create_customers = """
        CREATE TABLE customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20),
            address TEXT,
            tier VARCHAR(20) DEFAULT 'Standard',
            country VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    # Create products table
    create_products = """
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            product_code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            category VARCHAR(100),
            price DECIMAL(10,2) NOT NULL,
            inventory INTEGER DEFAULT 0,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    # Create orders table
    create_orders = """
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
            order_date DATE DEFAULT CURRENT_DATE,
            status VARCHAR(20) DEFAULT 'pending',
            total_amount DECIMAL(10,2) NOT NULL,
            payment_method VARCHAR(50),
            shipping_address TEXT,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    # Create indexes for performance
    create_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)",
        "CREATE INDEX IF NOT EXISTS idx_customers_country ON customers(country)",
        "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
        "CREATE INDEX IF NOT EXISTS idx_products_price ON products(price)",
        "CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
    ]

    try:
        # Create tables
        pg_conn.execute_query(
            create_customers,
            description="Creating customers table",
            fetch_results=False,
        )
        pg_conn.execute_query(
            create_products, description="Creating products table", fetch_results=False
        )
        pg_conn.execute_query(
            create_orders, description="Creating orders table", fetch_results=False
        )

        # Create indexes
        for idx_query in create_indexes:
            pg_conn.execute_query(
                idx_query, description="Creating index", fetch_results=False
            )

        print("✅ Sample tables and indexes created successfully!")

    except Exception as e:
        print(f"❌ Failed to create sample tables: {e}")
        raise


def insert_sample_data(pg_conn: PostgreSQLConnection):
    """Insert sample data into the tables."""
    print("\n📊 Inserting sample data...")

    # Sample customers
    customers_data = [
        (
            "Alice Johnson",
            "alice@example.com",
            "+1-555-0101",
            "123 Main St, New York, NY",
            "Premium",
            "USA",
        ),
        (
            "Bob Smith",
            "bob@example.com",
            "+1-555-0102",
            "456 Oak Ave, Toronto, ON",
            "Standard",
            "Canada",
        ),
        (
            "Charlie Brown",
            "charlie@example.com",
            "+1-555-0103",
            "789 Pine St, Los Angeles, CA",
            "Premium",
            "USA",
        ),
        (
            "Diana Prince",
            "diana@example.com",
            "+44-555-0104",
            "321 London Rd, London",
            "Standard",
            "UK",
        ),
        (
            "Eve Wilson",
            "eve@example.com",
            "+61-555-0105",
            "654 Sydney Ave, Sydney",
            "Premium",
            "Australia",
        ),
        (
            "Frank Miller",
            "frank@example.com",
            "+1-555-0106",
            "987 Elm St, Chicago, IL",
            "Standard",
            "USA",
        ),
        (
            "Grace Lee",
            "grace@example.com",
            "+82-555-0107",
            "147 Seoul St, Seoul",
            "Premium",
            "South Korea",
        ),
        (
            "Henry Davis",
            "henry@example.com",
            "+49-555-0108",
            "258 Berlin Ave, Berlin",
            "Standard",
            "Germany",
        ),
    ]

    insert_customers = """
        INSERT INTO customers (name, email, phone, address, tier, country)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    # Sample products
    products_data = [
        (
            "LAPTOP-001",
            "Gaming Laptop Pro",
            "High-performance gaming laptop",
            "Electronics",
            1299.99,
            50,
            '{"specs": {"cpu": "Intel i7", "ram": "16GB", "storage": "1TB SSD"}}',
        ),
        (
            "MOUSE-001",
            "Wireless Gaming Mouse",
            "Precision wireless mouse",
            "Electronics",
            79.99,
            200,
            '{"specs": {"dpi": "16000", "buttons": "8", "battery": "70h"}}',
        ),
        (
            "COFFEE-001",
            "Premium Coffee Maker",
            "Programmable coffee maker",
            "Appliances",
            149.99,
            75,
            '{"specs": {"capacity": "12 cups", "features": ["timer", "auto-shutoff"]}}',
        ),
        (
            "CHAIR-001",
            "Ergonomic Office Chair",
            "Comfortable ergonomic chair",
            "Furniture",
            299.99,
            25,
            '{"specs": {"material": "mesh", "adjustable": true, "warranty": "5 years"}}',
        ),
        (
            "MONITOR-001",
            "4K Gaming Monitor",
            "27-inch 4K gaming monitor",
            "Electronics",
            449.99,
            40,
            '{"specs": {"size": "27inch", "resolution": "4K", "refresh_rate": "144Hz"}}',
        ),
        (
            "BOOK-001",
            "Data Engineering Guide",
            "Complete guide to data engineering",
            "Books",
            39.99,
            500,
            '{"specs": {"pages": 450, "format": "hardcover", "isbn": "978-1234567890"}}',
        ),
        (
            "HEADSET-001",
            "Wireless Gaming Headset",
            "Surround sound gaming headset",
            "Electronics",
            129.99,
            100,
            '{"specs": {"driver": "50mm", "battery": "30h", "microphone": "noise-canceling"}}',
        ),
    ]

    insert_products = """
        INSERT INTO products (product_code, name, description, category, price, inventory, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    # Sample orders
    orders_data = [
        (
            1,
            "2024-01-15",
            "completed",
            1379.98,
            "credit_card",
            "123 Main St, New York, NY",
            '{"items": [{"product": "LAPTOP-001", "quantity": 1}, {"product": "MOUSE-001", "quantity": 1}]}',
        ),
        (
            2,
            "2024-01-16",
            "completed",
            149.99,
            "paypal",
            "456 Oak Ave, Toronto, ON",
            '{"items": [{"product": "COFFEE-001", "quantity": 1}]}',
        ),
        (
            3,
            "2024-01-17",
            "completed",
            749.98,
            "credit_card",
            "789 Pine St, Los Angeles, CA",
            '{"items": [{"product": "CHAIR-001", "quantity": 1}, {"product": "MONITOR-001", "quantity": 1}]}',
        ),
        (
            4,
            "2024-01-18",
            "pending",
            39.99,
            "bank_transfer",
            "321 London Rd, London",
            '{"items": [{"product": "BOOK-001", "quantity": 1}]}',
        ),
        (
            5,
            "2024-01-19",
            "completed",
            579.97,
            "credit_card",
            "654 Sydney Ave, Sydney",
            '{"items": [{"product": "MONITOR-001", "quantity": 1}, {"product": "HEADSET-001", "quantity": 1}]}',
        ),
        (
            1,
            "2024-01-20",
            "shipped",
            79.99,
            "credit_card",
            "123 Main St, New York, NY",
            '{"items": [{"product": "MOUSE-001", "quantity": 1}]}',
        ),
        (
            6,
            "2024-01-21",
            "completed",
            169.98,
            "paypal",
            "987 Elm St, Chicago, IL",
            '{"items": [{"product": "HEADSET-001", "quantity": 1}, {"product": "BOOK-001", "quantity": 1}]}',
        ),
    ]

    insert_orders = """
        INSERT INTO orders (customer_id, order_date, status, total_amount, payment_method, shipping_address, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    try:
        # Insert customers
        for customer in customers_data:
            pg_conn.execute_query(
                insert_customers, customer, "Inserting customer", fetch_results=False
            )

        # Insert products
        for product in products_data:
            pg_conn.execute_query(
                insert_products, product, "Inserting product", fetch_results=False
            )

        # Insert orders
        for order in orders_data:
            pg_conn.execute_query(
                insert_orders, order, "Inserting order", fetch_results=False
            )

        print("✅ Sample data inserted successfully!")

    except Exception as e:
        print(f"❌ Failed to insert sample data: {e}")
        raise


class QueryStats:
    """Track query execution statistics."""

    def __init__(self):
        self.queries_executed = 0
        self.total_execution_time = 0.0
        self.total_rows_processed = 0
        self.start_time = time.time()
        self.errors = 0

    def record_query(
        self, execution_time: float, row_count: int = 0, error: bool = False
    ):
        """Record statistics for a query execution."""
        self.queries_executed += 1
        self.total_execution_time += execution_time
        self.total_rows_processed += row_count
        if error:
            self.errors += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        elapsed_time = time.time() - self.start_time
        avg_query_time = self.total_execution_time / max(self.queries_executed, 1)

        return {
            "queries_executed": self.queries_executed,
            "total_execution_time": f"{self.total_execution_time:.2f}s",
            "average_query_time": f"{avg_query_time:.3f}s",
            "total_rows_processed": self.total_rows_processed,
            "errors": self.errors,
            "success_rate": f"{((self.queries_executed - self.errors) / max(self.queries_executed, 1) * 100):.1f}%",
            "session_duration": f"{elapsed_time:.2f}s",
            "queries_per_second": f"{self.queries_executed / max(elapsed_time, 1):.2f}",
        }

    def print_summary(self):
        """Print formatted summary statistics."""
        stats = self.get_summary()
        print("\n📊 Query Execution Summary:")
        print("=" * 40)
        for key, value in stats.items():
            formatted_key = key.replace("_", " ").title()
            print(f"{formatted_key:.<25} {value}")
        print("=" * 40)


def parse_common_args() -> argparse.ArgumentParser:
    """
    Create argument parser with common PostgreSQL options.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="PostgreSQL Building Block Application"
    )

    parser.add_argument("--host", default=PostgreSQLConfig.HOST, help="PostgreSQL host")
    parser.add_argument(
        "--port", type=int, default=PostgreSQLConfig.PORT, help="PostgreSQL port"
    )
    parser.add_argument(
        "--database", default=PostgreSQLConfig.DATABASE, help="Database name"
    )
    parser.add_argument("--user", default=PostgreSQLConfig.USER, help="Database user")
    parser.add_argument(
        "--password", default=PostgreSQLConfig.PASSWORD, help="Database password"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=PostgreSQLConfig.QUERY_TIMEOUT,
        help="Query timeout in seconds",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    return parser


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def handle_errors(func):
    """Decorator for handling common errors."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n🛑 Operation interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            if hasattr(e, "__traceback__"):
                import traceback

                traceback.print_exc()
            sys.exit(1)

    return wrapper


if __name__ == "__main__":
    # Test the common utilities
    print("🧪 Testing PostgreSQL common utilities...")

    try:
        pg_conn = PostgreSQLConnection()

        # Test basic connection
        test_query = "SELECT 1 as test_column, current_timestamp as query_time"
        results, exec_time = pg_conn.execute_query(
            test_query, description="Testing basic query"
        )
        display_results(results)

        # Test database info
        db_info = get_database_info(pg_conn)
        print(
            f"\n🖥️ Database version: {db_info.get('version', {}).get('version', 'Unknown')}"
        )

        pg_conn.close_pool()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
