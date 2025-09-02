#!/usr/bin/env python3
"""
Trino Common Utilities for Building Block Applications

This module provides common utilities for Trino building block examples:
- Connection management and configuration
- Query execution helpers
- Performance monitoring utilities
- Error handling and logging
- Data formatting and display utilities

Requirements:
    pip install trino requests
"""

import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import argparse
import logging

try:
    import trino
    from trino.auth import BasicAuthentication
except ImportError:
    print("❌ Error: trino library not found!")
    print("📦 Install with: pip install trino")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("❌ Error: requests library not found!")
    print("📦 Install with: pip install requests")
    sys.exit(1)


class TrinoConfig:
    """Trino cluster configuration for building block apps."""

    # Trino cluster settings (from your setup)
    COORDINATOR_HOST = "192.168.1.184"
    COORDINATOR_PORT = 8084

    # Connection settings
    USER = "dataeng"
    CATALOG = "postgresql"  # Default catalog
    SCHEMA = "public"  # Default schema

    # Request timeout settings
    REQUEST_TIMEOUT = 300
    HTTP_TIMEOUT = 60

    # Performance settings
    QUERY_MAX_RUN_TIME = "1h"
    QUERY_MAX_MEMORY = "2GB"


def get_trino_connection(
    catalog: str = None, schema: str = None, user: str = None, **kwargs
) -> trino.dbapi.Connection:
    """
    Create a Trino connection with standard configuration.

    Args:
        catalog: Trino catalog to connect to
        schema: Schema within the catalog
        user: Username for the connection
        **kwargs: Additional connection parameters

    Returns:
        trino.dbapi.Connection: Active Trino connection
    """
    config = TrinoConfig()

    connection_params = {
        "host": config.COORDINATOR_HOST,
        "port": config.COORDINATOR_PORT,
        "user": user or config.USER,
        "catalog": catalog or config.CATALOG,
        "schema": schema or config.SCHEMA,
        "http_scheme": "http",
        "request_timeout": config.REQUEST_TIMEOUT,
        **kwargs,
    }

    print(
        f"🔌 Connecting to Trino: {connection_params['host']}:{connection_params['port']}"
    )
    print(
        f"📂 Catalog: {connection_params['catalog']}, Schema: {connection_params['schema']}"
    )

    try:
        conn = trino.dbapi.connect(**connection_params)
        print("✅ Connected to Trino successfully!")
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to Trino: {e}")
        raise


def execute_query(
    conn: trino.dbapi.Connection,
    query: str,
    description: str = "",
    fetch_results: bool = True,
) -> Tuple[List, float]:
    """
    Execute a Trino query with timing and error handling.

    Args:
        conn: Trino connection
        query: SQL query to execute
        description: Description for logging
        fetch_results: Whether to fetch and return results

    Returns:
        Tuple of (results, execution_time_seconds)
    """
    print(f"\n🔍 {description or 'Executing query'}")
    print(f"📝 Query: {query[:100]}{'...' if len(query) > 100 else ''}")

    start_time = time.time()

    try:
        cursor = conn.cursor()
        cursor.execute(query)

        results = []
        if fetch_results:
            results = cursor.fetchall()

        execution_time = time.time() - start_time

        if fetch_results and results:
            print(
                f"✅ Query completed in {execution_time:.2f}s, returned {len(results)} rows"
            )
        else:
            print(f"✅ Query completed in {execution_time:.2f}s")

        return results, execution_time

    except Exception as e:
        execution_time = time.time() - start_time
        print(f"❌ Query failed after {execution_time:.2f}s: {e}")
        raise
    finally:
        if "cursor" in locals():
            cursor.close()


def display_results(results: List, headers: List[str] = None, max_rows: int = 20):
    """
    Display query results in a formatted table.

    Args:
        results: Query results
        headers: Column headers
        max_rows: Maximum number of rows to display
    """
    if not results:
        print("📭 No results to display")
        return

    # Determine headers if not provided
    if headers is None:
        headers = [f"col_{i+1}" for i in range(len(results[0]) if results else 0)]

    # Calculate column widths
    if results:
        widths = [len(str(header)) for header in headers]
        for row in results[:max_rows]:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(cell)))

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

        print(
            "│"
            + "│".join(f" {str(row[i]):<{widths[i]}} " for i in range(len(row)))
            + "│"
        )
        displayed_rows += 1

    print("└" + "┴".join("─" * (w + 2) for w in widths) + "┘")
    print(
        f"📈 Displayed {min(displayed_rows, len(results))} of {len(results)} total rows"
    )


def get_cluster_info(conn: trino.dbapi.Connection) -> Dict[str, Any]:
    """
    Get information about the Trino cluster.

    Args:
        conn: Trino connection

    Returns:
        Dictionary with cluster information
    """
    try:
        # Get node information
        nodes_query = "SELECT node_id, http_uri, node_version, coordinator FROM system.runtime.nodes"
        nodes, _ = execute_query(conn, nodes_query, "Getting cluster nodes", True)

        # Get active queries
        queries_query = (
            "SELECT state, COUNT(*) as count FROM system.runtime.queries GROUP BY state"
        )
        queries, _ = execute_query(
            conn, queries_query, "Getting query statistics", True
        )

        cluster_info = {
            "nodes": nodes,
            "queries": queries,
            "timestamp": datetime.now().isoformat(),
        }

        return cluster_info

    except Exception as e:
        print(f"⚠️ Could not retrieve cluster info: {e}")
        return {}


def get_available_catalogs(conn: trino.dbapi.Connection) -> List[str]:
    """
    Get list of available catalogs in the Trino cluster.

    Args:
        conn: Trino connection

    Returns:
        List of catalog names
    """
    try:
        catalogs_query = "SHOW CATALOGS"
        results, _ = execute_query(
            conn, catalogs_query, "Getting available catalogs", True
        )
        catalogs = [row[0] for row in results]
        return catalogs
    except Exception as e:
        print(f"⚠️ Could not retrieve catalogs: {e}")
        return []


def get_catalog_schemas(conn: trino.dbapi.Connection, catalog: str) -> List[str]:
    """
    Get list of schemas in a specific catalog.

    Args:
        conn: Trino connection
        catalog: Catalog name

    Returns:
        List of schema names
    """
    try:
        schemas_query = f"SHOW SCHEMAS FROM {catalog}"
        results, _ = execute_query(
            conn, schemas_query, f"Getting schemas from {catalog}", True
        )
        schemas = [row[0] for row in results]
        return schemas
    except Exception as e:
        print(f"⚠️ Could not retrieve schemas from {catalog}: {e}")
        return []


def get_schema_tables(
    conn: trino.dbapi.Connection, catalog: str, schema: str
) -> List[str]:
    """
    Get list of tables in a specific schema.

    Args:
        conn: Trino connection
        catalog: Catalog name
        schema: Schema name

    Returns:
        List of table names
    """
    try:
        tables_query = f"SHOW TABLES FROM {catalog}.{schema}"
        results, _ = execute_query(
            conn, tables_query, f"Getting tables from {catalog}.{schema}", True
        )
        tables = [row[0] for row in results]
        return tables
    except Exception as e:
        print(f"⚠️ Could not retrieve tables from {catalog}.{schema}: {e}")
        return []


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
            "average_query_time": f"{avg_query_time:.2f}s",
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
    Create argument parser with common Trino options.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(description="Trino Building Block Application")

    parser.add_argument(
        "--host", default=TrinoConfig.COORDINATOR_HOST, help="Trino coordinator host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=TrinoConfig.COORDINATOR_PORT,
        help="Trino coordinator port",
    )
    parser.add_argument("--user", default=TrinoConfig.USER, help="Trino user")
    parser.add_argument(
        "--catalog", default=TrinoConfig.CATALOG, help="Default catalog"
    )
    parser.add_argument("--schema", default=TrinoConfig.SCHEMA, help="Default schema")
    parser.add_argument(
        "--timeout",
        type=int,
        default=TrinoConfig.REQUEST_TIMEOUT,
        help="Request timeout in seconds",
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


# Sample queries for testing and demonstration
SAMPLE_QUERIES = {
    "cluster_info": "SELECT node_id, http_uri, coordinator FROM system.runtime.nodes",
    "catalogs": "SHOW CATALOGS",
    "postgresql_tables": "SHOW TABLES FROM postgresql.public",
    "kafka_topics": "SHOW TABLES FROM kafka.default",
    "simple_select": "SELECT 1 as test_column, current_timestamp as query_time",
    "postgresql_sample": """
        SELECT table_name, table_type 
        FROM postgresql.information_schema.tables 
        WHERE table_schema = 'public' 
        LIMIT 10
    """,
    "cross_catalog": """
        SELECT 
            p.table_name as postgres_table,
            k.table_name as kafka_topic,
            current_timestamp as query_time
        FROM postgresql.information_schema.tables p
        CROSS JOIN kafka.information_schema.tables k
        WHERE p.table_schema = 'public'
        LIMIT 5
    """,
}


if __name__ == "__main__":
    # Test the common utilities
    print("🧪 Testing Trino common utilities...")

    try:
        conn = get_trino_connection()

        # Test basic query
        results, exec_time = execute_query(
            conn, SAMPLE_QUERIES["simple_select"], "Testing basic query"
        )
        display_results(results, ["Test Column", "Query Time"])

        # Test cluster info
        cluster_info = get_cluster_info(conn)
        print(f"\n🖥️ Cluster has {len(cluster_info.get('nodes', []))} nodes")

        conn.close()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
