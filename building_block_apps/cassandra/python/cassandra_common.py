#!/usr/bin/env python3
"""
Cassandra Common Utilities for Building Block Applications

This module provides common utilities for Cassandra building block examples:
- Connection management with load balancing
- Session management and connection pooling
- Query execution helpers with prepared statements
- Time-series and wide-row optimized patterns
- Error handling and logging
- Performance monitoring and metrics
- Data modeling utilities for NoSQL patterns

Requirements:
    pip install cassandra-driver
"""

import json
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
import argparse
import logging
from contextlib import contextmanager

try:
    from cassandra.cluster import Cluster, Session
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.policies import DCAwareRoundRobinPolicy, WhiteListRoundRobinPolicy
    from cassandra.query import SimpleStatement, PreparedStatement, BatchStatement, BatchType
    from cassandra.metadata import Metadata
    from cassandra import InvalidRequest, Unauthorized, OperationTimedOut
except ImportError:
    print("❌ Error: cassandra-driver library not found!")
    print("📦 Install with: pip install cassandra-driver")
    sys.exit(1)


class CassandraConfig:
    """Cassandra configuration for building block apps."""

    # Cassandra cluster settings (from your distributed setup)
    HOSTS = ["192.168.1.184", "192.168.1.187", "192.168.1.190"]
    PORT = 9042
    KEYSPACE = "homelab_analytics"
    
    # Authentication (set if authentication is enabled)
    USERNAME = None
    PASSWORD = None
    
    # Connection pool settings
    MAX_CONNECTIONS_PER_HOST = 8
    MAX_REQUESTS_PER_CONNECTION = 128
    
    # Query timeout settings
    REQUEST_TIMEOUT = 30.0
    CONNECT_TIMEOUT = 5.0
    
    # Consistency settings
    DEFAULT_CONSISTENCY_LEVEL = "LOCAL_QUORUM"
    READ_CONSISTENCY_LEVEL = "LOCAL_ONE"
    WRITE_CONSISTENCY_LEVEL = "LOCAL_QUORUM"
    
    # Performance settings
    MAX_SCHEMA_AGREEMENT_WAIT = 10
    CONTROL_CONNECTION_TIMEOUT = 2.0


class CassandraConnection:
    """Enhanced Cassandra connection manager with load balancing and monitoring."""

    def __init__(self, config: Optional[CassandraConfig] = None):
        self.config = config or CassandraConfig()
        self.cluster = None
        self.session = None
        self.prepared_statements = {}
        self.stats = {
            "queries": 0, 
            "prepared_queries": 0,
            "batch_queries": 0,
            "errors": 0, 
            "connections": 0,
            "query_time": 0.0
        }

    def create_cluster_connection(self) -> Cluster:
        """Create a Cassandra cluster connection with load balancing."""
        try:
            # Configure authentication if needed
            auth_provider = None
            if self.config.USERNAME and self.config.PASSWORD:
                auth_provider = PlainTextAuthProvider(
                    username=self.config.USERNAME,
                    password=self.config.PASSWORD
                )

            # Configure load balancing policy
            load_balancing_policy = DCAwareRoundRobinPolicy(
                local_dc='datacenter1',  # Default datacenter name
                used_hosts_per_remote_dc=1
            )

            # Create cluster
            self.cluster = Cluster(
                contact_points=self.config.HOSTS,
                port=self.config.PORT,
                auth_provider=auth_provider,
                load_balancing_policy=load_balancing_policy,
                max_schema_agreement_wait=self.config.MAX_SCHEMA_AGREEMENT_WAIT,
                control_connection_timeout=self.config.CONTROL_CONNECTION_TIMEOUT
            )

            # Create session
            self.session = self.cluster.connect()
            self.stats["connections"] += 1

            print(f"🔌 Connected to Cassandra cluster: {', '.join(self.config.HOSTS)}")
            print(f"📊 Load balancing: {len(self.config.HOSTS)} nodes")
            
            # Set default keyspace if it exists
            try:
                self.session.set_keyspace(self.config.KEYSPACE)
                print(f"📁 Using keyspace: {self.config.KEYSPACE}")
            except InvalidRequest:
                print(f"⚠️ Keyspace '{self.config.KEYSPACE}' not found - will operate without default keyspace")

            return self.cluster

        except Exception as e:
            print(f"❌ Failed to connect to Cassandra cluster: {e}")
            raise

    def get_session(self) -> Session:
        """Get Cassandra session, creating connection if needed."""
        if not self.session:
            self.create_cluster_connection()
        return self.session

    def execute_query(
        self,
        query: Union[str, SimpleStatement, PreparedStatement],
        parameters: List[Any] = None,
        description: str = "",
        consistency_level: str = None,
    ) -> Any:
        """
        Execute a Cassandra query with timing and error handling.

        Args:
            query: CQL query to execute
            parameters: Query parameters for prepared statements
            description: Description for logging
            consistency_level: Override default consistency level

        Returns:
            Query result set
        """
        print(f"\n🔍 {description or 'Executing query'}")
        
        # Handle different query types
        if isinstance(query, str):
            query_str = query
            statement = SimpleStatement(query, consistency_level=consistency_level)
        elif isinstance(query, PreparedStatement):
            query_str = "prepared_statement"
            statement = query
        else:
            query_str = str(query)
            statement = query

        print(f"📝 Query: {query_str[:100]}{'...' if len(query_str) > 100 else ''}")

        start_time = time.time()
        session = self.get_session()

        try:
            if parameters:
                result = session.execute(statement, parameters)
            else:
                result = session.execute(statement)

            execution_time = time.time() - start_time
            
            # Convert to list for easier handling
            if result:
                result_list = list(result)
                row_count = len(result_list)
                print(f"✅ Query completed in {execution_time:.3f}s, returned {row_count} rows")
            else:
                result_list = []
                print(f"✅ Query completed in {execution_time:.3f}s")

            self.stats["queries"] += 1
            self.stats["query_time"] += execution_time
            
            if isinstance(query, PreparedStatement):
                self.stats["prepared_queries"] += 1

            return result_list

        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ Query failed after {execution_time:.3f}s: {e}")
            self.stats["errors"] += 1
            raise

    def prepare_statement(self, query: str, cache_key: str = None) -> PreparedStatement:
        """
        Prepare a CQL statement for efficient repeated execution.

        Args:
            query: CQL query to prepare
            cache_key: Optional cache key for prepared statement

        Returns:
            Prepared statement
        """
        cache_key = cache_key or query
        
        if cache_key in self.prepared_statements:
            print(f"🎯 Using cached prepared statement: {cache_key[:30]}...")
            return self.prepared_statements[cache_key]

        try:
            session = self.get_session()
            prepared = session.prepare(query)
            self.prepared_statements[cache_key] = prepared
            
            print(f"⚡ Prepared statement cached: {cache_key[:30]}...")
            return prepared

        except Exception as e:
            print(f"❌ Failed to prepare statement: {e}")
            raise

    def execute_batch(
        self,
        statements: List[Tuple[Union[str, PreparedStatement], List[Any]]],
        batch_type: BatchType = BatchType.LOGGED,
        description: str = "",
    ) -> None:
        """
        Execute multiple statements in a batch for atomic operations.

        Args:
            statements: List of (statement, parameters) tuples
            batch_type: Type of batch (LOGGED, UNLOGGED, COUNTER)
            description: Description for logging
        """
        print(f"\n🔄 {description or 'Executing batch'}")
        print(f"📦 Batch size: {len(statements)} statements")

        start_time = time.time()
        session = self.get_session()
        batch = BatchStatement(batch_type=batch_type)

        try:
            for statement, parameters in statements:
                if isinstance(statement, str):
                    prepared = self.prepare_statement(statement)
                    batch.add(prepared, parameters)
                else:
                    batch.add(statement, parameters)

            session.execute(batch)
            execution_time = time.time() - start_time

            print(f"✅ Batch completed in {execution_time:.3f}s")
            self.stats["batch_queries"] += 1
            self.stats["query_time"] += execution_time

        except Exception as e:
            execution_time = time.time() - start_time
            print(f"❌ Batch failed after {execution_time:.3f}s: {e}")
            self.stats["errors"] += 1
            raise

    def close_connection(self):
        """Close Cassandra connection and cluster."""
        if self.cluster:
            self.cluster.shutdown()
            print("🔌 Cassandra connection closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection and query statistics."""
        total_queries = max(self.stats["queries"], 1)
        avg_query_time = self.stats["query_time"] / total_queries
        success_rate = ((total_queries - self.stats["errors"]) / total_queries) * 100

        return {
            "queries_executed": self.stats["queries"],
            "prepared_statements_used": self.stats["prepared_queries"], 
            "batch_operations": self.stats["batch_queries"],
            "errors": self.stats["errors"],
            "connections_created": self.stats["connections"],
            "avg_query_time": f"{avg_query_time:.3f}s",
            "total_query_time": f"{self.stats['query_time']:.2f}s",
            "success_rate": f"{success_rate:.1f}%",
        }


def display_results(results: List[Any], max_rows: int = 20):
    """
    Display query results in a formatted table.

    Args:
        results: Query results (list of Row objects)
        max_rows: Maximum number of rows to display
    """
    if not results:
        print("📭 No results to display")
        return

    # Get column names from first row
    if hasattr(results[0], '_fields'):
        headers = results[0]._fields
    else:
        # If no field names, create generic headers
        headers = [f"col_{i}" for i in range(len(results[0]))]

    # Calculate column widths
    widths = [len(str(header)) for header in headers]
    for row in results[:max_rows]:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(str(value)))

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

        row_values = [str(value) for value in row]
        print(
            "│"
            + "│".join(f" {row_values[i]:<{widths[i]}} " for i in range(len(headers)))
            + "│"
        )
        displayed_rows += 1

    print("└" + "┴".join("─" * (w + 2) for w in widths) + "┘")
    print(f"📈 Displayed {min(displayed_rows, len(results))} of {len(results)} total rows")


def get_cluster_info(cassandra_conn: CassandraConnection) -> Dict[str, Any]:
    """Get information about the Cassandra cluster."""
    try:
        session = cassandra_conn.get_session()
        metadata = session.cluster.metadata

        # Cluster information
        cluster_info = {
            "cluster_name": metadata.cluster_name,
            "partitioner": metadata.partitioner,
            "hosts": [],
            "keyspaces": list(metadata.keyspaces.keys()),
            "total_hosts": len(metadata.all_hosts()),
        }

        # Host information
        for host in metadata.all_hosts():
            host_info = {
                "address": str(host.address),
                "datacenter": host.datacenter,
                "rack": host.rack,
                "is_up": host.is_up,
                "cassandra_version": host.release_version,
            }
            cluster_info["hosts"].append(host_info)

        return cluster_info

    except Exception as e:
        print(f"⚠️ Could not retrieve cluster info: {e}")
        return {}


def create_sample_keyspace_and_tables(cassandra_conn: CassandraConnection):
    """Create sample keyspace and tables for demonstration purposes."""
    print("\n📝 Creating sample keyspace and tables...")

    session = cassandra_conn.get_session()

    # Create keyspace
    create_keyspace_query = f"""
        CREATE KEYSPACE IF NOT EXISTS {cassandra_conn.config.KEYSPACE}
        WITH replication = {{
            'class': 'NetworkTopologyStrategy',
            'datacenter1': 3
        }}
    """
    
    cassandra_conn.execute_query(
        create_keyspace_query,
        description="Creating sample keyspace"
    )

    # Use the keyspace
    session.set_keyspace(cassandra_conn.config.KEYSPACE)

    # Create user events table (time-series pattern)
    create_events_table = """
        CREATE TABLE IF NOT EXISTS user_events (
            user_id UUID,
            event_date date,
            event_time timestamp,
            event_id timeuuid,
            event_type text,
            properties map<text, text>,
            PRIMARY KEY ((user_id, event_date), event_time, event_id)
        ) WITH CLUSTERING ORDER BY (event_time DESC, event_id DESC)
          AND compaction = {
            'class': 'TimeWindowCompactionStrategy',
            'compaction_window_unit': 'DAYS',
            'compaction_window_size': 7
          }
    """

    # Create users table (wide-row pattern)
    create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            user_id UUID PRIMARY KEY,
            username text,
            email text,
            created_at timestamp,
            last_login timestamp,
            profile map<text, text>,
            preferences set<text>,
            login_history list<timestamp>
        )
    """

    # Create time-series metrics table
    create_metrics_table = """
        CREATE TABLE IF NOT EXISTS system_metrics (
            metric_name text,
            time_bucket timestamp,
            metric_time timestamp,
            value double,
            tags map<text, text>,
            PRIMARY KEY ((metric_name, time_bucket), metric_time)
        ) WITH CLUSTERING ORDER BY (metric_time DESC)
          AND default_time_to_live = 2592000
    """

    # Create counters table
    create_counters_table = """
        CREATE TABLE IF NOT EXISTS event_counters (
            event_type text,
            date date,
            hour int,
            count counter,
            PRIMARY KEY ((event_type, date), hour)
        ) WITH CLUSTERING ORDER BY (hour DESC)
    """

    try:
        cassandra_conn.execute_query(
            create_events_table,
            description="Creating user_events table"
        )
        cassandra_conn.execute_query(
            create_users_table,
            description="Creating users table"
        )
        cassandra_conn.execute_query(
            create_metrics_table,
            description="Creating system_metrics table"
        )
        cassandra_conn.execute_query(
            create_counters_table,
            description="Creating event_counters table"
        )

        print("✅ Sample keyspace and tables created successfully!")

    except Exception as e:
        print(f"❌ Failed to create sample tables: {e}")
        raise


def insert_sample_data(cassandra_conn: CassandraConnection):
    """Insert sample data into the tables."""
    print("\n📊 Inserting sample data...")

    session = cassandra_conn.get_session()

    # Sample users data
    user_ids = [uuid.uuid4() for _ in range(5)]
    
    # Prepare statements for efficient insertion
    insert_user = cassandra_conn.prepare_statement("""
        INSERT INTO users (user_id, username, email, created_at, profile, preferences)
        VALUES (?, ?, ?, ?, ?, ?)
    """)

    insert_event = cassandra_conn.prepare_statement("""
        INSERT INTO user_events (user_id, event_date, event_time, event_id, event_type, properties)
        VALUES (?, ?, ?, ?, ?, ?)
    """)

    insert_metric = cassandra_conn.prepare_statement("""
        INSERT INTO system_metrics (metric_name, time_bucket, metric_time, value, tags)
        VALUES (?, ?, ?, ?, ?)
    """)

    try:
        # Insert users
        user_batch = []
        for i, user_id in enumerate(user_ids):
            user_data = (
                user_id,
                f"user_{i+1}",
                f"user{i+1}@example.com",
                datetime.now() - timedelta(days=30-i),
                {"city": f"City_{i+1}", "country": "USA", "age": str(25+i)},
                {f"feature_{j}" for j in range(3)}
            )
            user_batch.append((insert_user, user_data))

        cassandra_conn.execute_batch(
            user_batch,
            description="Inserting sample users"
        )

        # Insert events for each user
        event_batch = []
        for user_id in user_ids:
            for day_offset in range(7):  # Last 7 days
                event_date = datetime.now().date() - timedelta(days=day_offset)
                for hour in range(3):  # 3 events per day
                    event_time = datetime.combine(event_date, datetime.min.time()) + timedelta(hours=hour*8)
                    event_data = (
                        user_id,
                        event_date,
                        event_time,
                        uuid.uuid1(),  # timeuuid
                        "page_view",
                        {"page": f"/page_{hour}", "duration": str(30+hour*10)}
                    )
                    event_batch.append((insert_event, event_data))

        cassandra_conn.execute_batch(
            event_batch,
            description="Inserting sample events"
        )

        # Insert system metrics
        metrics_batch = []
        for hour_offset in range(24):  # Last 24 hours
            metric_time = datetime.now() - timedelta(hours=hour_offset)
            time_bucket = metric_time.replace(minute=0, second=0, microsecond=0)
            
            # CPU metric
            cpu_data = (
                "cpu_usage",
                time_bucket,
                metric_time,
                50.0 + (hour_offset % 10) * 5.0,
                {"host": "server1", "core": "0"}
            )
            metrics_batch.append((insert_metric, cpu_data))

            # Memory metric
            memory_data = (
                "memory_usage",
                time_bucket,
                metric_time,
                70.0 + (hour_offset % 15) * 2.0,
                {"host": "server1", "type": "used"}
            )
            metrics_batch.append((insert_metric, memory_data))

        cassandra_conn.execute_batch(
            metrics_batch,
            description="Inserting sample metrics"
        )

        print("✅ Sample data inserted successfully!")

    except Exception as e:
        print(f"❌ Failed to insert sample data: {e}")
        raise


def parse_common_args() -> argparse.ArgumentParser:
    """
    Create argument parser with common Cassandra options.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Cassandra Building Block Application"
    )

    parser.add_argument(
        "--hosts", 
        nargs='+',
        default=CassandraConfig.HOSTS, 
        help="Cassandra host addresses"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=CassandraConfig.PORT, 
        help="Cassandra port"
    )
    parser.add_argument(
        "--keyspace", 
        default=CassandraConfig.KEYSPACE, 
        help="Keyspace name"
    )
    parser.add_argument(
        "--username", 
        default=CassandraConfig.USERNAME, 
        help="Cassandra username"
    )
    parser.add_argument(
        "--password", 
        default=CassandraConfig.PASSWORD, 
        help="Cassandra password"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=CassandraConfig.REQUEST_TIMEOUT,
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


if __name__ == "__main__":
    # Test the common utilities
    print("🧪 Testing Cassandra common utilities...")

    try:
        cassandra_conn = CassandraConnection()

        # Test basic connection
        cluster_info = get_cluster_info(cassandra_conn)
        print(f"✅ Connected to cluster: {cluster_info.get('cluster_name', 'Unknown')}")
        print(f"📊 Cluster hosts: {cluster_info.get('total_hosts', 0)}")

        # Test query execution
        test_query = "SELECT cluster_name, release_version FROM system.local"
        results = cassandra_conn.execute_query(
            test_query, 
            description="Testing basic query"
        )
        display_results(results)

        # Display connection statistics
        stats = cassandra_conn.get_stats()
        print(f"\n📈 Connection Stats:")
        for key, value in stats.items():
            print(f"  {key.replace('_', ' ').title()}: {value}")

        cassandra_conn.close_connection()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
