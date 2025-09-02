#!/usr/bin/env python3
"""
Trino Basic Queries - Building Block Application

This script demonstrates basic Trino query operations:
- Connection management
- Simple SELECT queries
- Catalog and schema exploration  
- Basic aggregations and filtering
- Working with different data types

Usage:
    bazel run //trino/python:basic_queries -- --catalog postgresql --schema public
    bazel run //trino/python:basic_queries -- --catalog kafka --schema default

Examples:
    # Query PostgreSQL tables
    bazel run //trino/python:basic_queries -- --catalog postgresql
    
    # Explore Kafka topics
    bazel run //trino/python:basic_queries -- --catalog kafka
    
    # Query with custom timeout
    bazel run //trino/python:basic_queries -- --timeout 120

Requirements:
    pip install trino requests
"""

import sys
import argparse
from trino_common import (
    get_trino_connection,
    execute_query,
    display_results,
    QueryStats,
    get_available_catalogs,
    get_catalog_schemas,
    get_schema_tables,
    get_cluster_info,
    parse_common_args,
    setup_logging,
    handle_errors,
    SAMPLE_QUERIES,
)


@handle_errors
def demonstrate_basic_queries(args):
    """
    Demonstrate basic Trino query operations.

    Args:
        args: Command line arguments
    """
    stats = QueryStats()

    print("🚀 Starting Trino Basic Queries Demo")
    print("=" * 50)

    # Connect to Trino
    conn = get_trino_connection(
        catalog=args.catalog, schema=args.schema, user=args.user
    )

    try:
        # 1. Cluster Information
        print("\n🏗️ STEP 1: Cluster Information")
        print("-" * 30)

        cluster_info = get_cluster_info(conn)
        if cluster_info.get("nodes"):
            print("📊 Cluster Nodes:")
            for node in cluster_info["nodes"]:
                node_type = "Coordinator" if node[3] else "Worker"
                print(f"  • {node[0]} ({node_type}) - {node[1]}")

        # 2. Catalog Exploration
        print("\n📂 STEP 2: Catalog Exploration")
        print("-" * 30)

        catalogs = get_available_catalogs(conn)
        print(f"Available catalogs: {', '.join(catalogs)}")

        if args.catalog in catalogs:
            schemas = get_catalog_schemas(conn, args.catalog)
            print(f"Schemas in '{args.catalog}': {', '.join(schemas[:10])}")

            if args.schema in schemas:
                tables = get_schema_tables(conn, args.catalog, args.schema)
                print(
                    f"Tables in '{args.catalog}.{args.schema}': {', '.join(tables[:10])}"
                )

        # 3. Basic SELECT Queries
        print("\n🔍 STEP 3: Basic SELECT Queries")
        print("-" * 30)

        # Simple test query
        query = "SELECT 1 as number, 'Hello Trino' as message, current_timestamp as query_time"
        results, exec_time = execute_query(conn, query, "Simple SELECT query")
        display_results(results, ["Number", "Message", "Query Time"])
        stats.record_query(exec_time, len(results))

        # System functions
        query = """
            SELECT 
                version() as trino_version,
                current_user as user_name,
                current_catalog as catalog_name,
                current_schema as schema_name,
                now() as current_time
        """
        results, exec_time = execute_query(conn, query, "System information query")
        display_results(results, ["Version", "User", "Catalog", "Schema", "Time"])
        stats.record_query(exec_time, len(results))

        # 4. Data Type Examples
        print("\n🔢 STEP 4: Data Type Examples")
        print("-" * 30)

        query = """
            SELECT 
                -- Numeric types
                CAST(42 AS BIGINT) as big_integer,
                CAST(3.14159 AS DOUBLE) as double_precision,
                CAST(99.99 AS DECIMAL(10,2)) as decimal_value,
                
                -- String types
                'Sample Text' as varchar_text,
                CAST('Fixed Length' AS CHAR(12)) as char_text,
                
                -- Date/Time types
                DATE '2024-01-01' as date_value,
                TIMESTAMP '2024-01-01 12:00:00' as timestamp_value,
                
                -- Boolean
                true as boolean_value,
                
                -- Array
                ARRAY[1, 2, 3, 4, 5] as array_value,
                
                -- JSON
                JSON '{"key": "value", "number": 123}' as json_value
        """
        results, exec_time = execute_query(conn, query, "Data type examples")
        headers = [
            "BigInt",
            "Double",
            "Decimal",
            "Varchar",
            "Char",
            "Date",
            "Timestamp",
            "Boolean",
            "Array",
            "JSON",
        ]
        display_results(results, headers)
        stats.record_query(exec_time, len(results))

        # 5. Mathematical Functions
        print("\n🧮 STEP 5: Mathematical Functions")
        print("-" * 30)

        query = """
            SELECT 
                abs(-42) as absolute_value,
                ceil(3.7) as ceiling,
                floor(3.7) as floor_value,
                round(3.14159, 2) as rounded,
                power(2, 3) as power_result,
                sqrt(16) as square_root,
                sin(pi() / 2) as sine_90_degrees,
                cos(0) as cosine_0_degrees,
                random() as random_number
        """
        results, exec_time = execute_query(conn, query, "Mathematical functions")
        headers = [
            "Abs",
            "Ceil",
            "Floor",
            "Round",
            "Power",
            "Sqrt",
            "Sin",
            "Cos",
            "Random",
        ]
        display_results(results, headers)
        stats.record_query(exec_time, len(results))

        # 6. String Functions
        print("\n🔤 STEP 6: String Functions")
        print("-" * 30)

        query = """
            SELECT 
                upper('hello world') as uppercase,
                lower('HELLO WORLD') as lowercase,
                length('Trino Query Engine') as string_length,
                substring('Hello World', 1, 5) as substring_result,
                concat('Hello', ' ', 'World') as concatenated,
                trim('  padded string  ') as trimmed,
                replace('Hello World', 'World', 'Trino') as replaced,
                split('a,b,c,d', ',') as split_array,
                regexp_extract('abc123def', '([0-9]+)') as regex_extract
        """
        results, exec_time = execute_query(conn, query, "String functions")
        headers = [
            "Upper",
            "Lower",
            "Length",
            "Substring",
            "Concat",
            "Trim",
            "Replace",
            "Split",
            "RegexExtract",
        ]
        display_results(results, headers)
        stats.record_query(exec_time, len(results))

        # 7. Date/Time Functions
        print("\n📅 STEP 7: Date/Time Functions")
        print("-" * 30)

        query = """
            SELECT 
                current_date as today,
                current_time as current_time,
                current_timestamp as now,
                date_add('day', 30, current_date) as thirty_days_later,
                date_diff('day', DATE '2024-01-01', current_date) as days_since_2024,
                extract(year from current_timestamp) as current_year,
                extract(month from current_timestamp) as current_month,
                extract(day from current_timestamp) as current_day,
                format_datetime(current_timestamp, 'yyyy-MM-dd HH:mm:ss') as formatted_time
        """
        results, exec_time = execute_query(conn, query, "Date/time functions")
        headers = [
            "Today",
            "Time",
            "Now",
            "30DaysLater",
            "DaysSince2024",
            "Year",
            "Month",
            "Day",
            "Formatted",
        ]
        display_results(results, headers)
        stats.record_query(exec_time, len(results))

        # 8. Conditional Logic
        print("\n🔀 STEP 8: Conditional Logic")
        print("-" * 30)

        query = """
            WITH numbers AS (
                SELECT value 
                FROM UNNEST(ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) AS t(value)
            )
            SELECT 
                value,
                CASE 
                    WHEN value % 2 = 0 THEN 'Even'
                    ELSE 'Odd'
                END as even_or_odd,
                IF(value > 5, 'Large', 'Small') as size_category,
                COALESCE(NULLIF(value, 5), 999) as coalesce_example,
                TRY(10 / NULLIF(value - value, 0)) as safe_division
            FROM numbers
        """
        results, exec_time = execute_query(conn, query, "Conditional logic examples")
        display_results(
            results, ["Value", "Even/Odd", "Size", "Coalesce", "SafeDiv"], max_rows=10
        )
        stats.record_query(exec_time, len(results))

        # 9. Aggregation Examples
        print("\n📊 STEP 9: Aggregation Examples")
        print("-" * 30)

        query = """
            WITH sample_data AS (
                SELECT 
                    value,
                    value % 3 as group_id,
                    CASE WHEN value % 2 = 0 THEN 'even' ELSE 'odd' END as parity
                FROM UNNEST(ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) AS t(value)
            )
            SELECT 
                group_id,
                COUNT(*) as count,
                SUM(value) as sum_value,
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                STRING_AGG(CAST(value AS VARCHAR), ',') as values_list
            FROM sample_data
            GROUP BY group_id
            ORDER BY group_id
        """
        results, exec_time = execute_query(conn, query, "Aggregation examples")
        headers = ["Group", "Count", "Sum", "Avg", "Min", "Max", "Values"]
        display_results(results, headers)
        stats.record_query(exec_time, len(results))

        # 10. Window Functions
        print("\n🪟 STEP 10: Window Functions")
        print("-" * 30)

        query = """
            WITH sales_data AS (
                SELECT 
                    value as amount,
                    (value % 3) + 1 as department_id,
                    'Q' || CAST((value % 4) + 1 AS VARCHAR) as quarter
                FROM UNNEST(ARRAY[100, 200, 150, 300, 250, 180, 220, 350, 120, 280]) AS t(value)
            )
            SELECT 
                amount,
                department_id,
                quarter,
                ROW_NUMBER() OVER (ORDER BY amount DESC) as row_num,
                RANK() OVER (PARTITION BY department_id ORDER BY amount DESC) as dept_rank,
                LAG(amount, 1) OVER (ORDER BY amount) as previous_amount,
                SUM(amount) OVER (PARTITION BY department_id) as dept_total,
                AVG(amount) OVER (ORDER BY amount ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as moving_avg
            FROM sales_data
            ORDER BY amount DESC
        """
        results, exec_time = execute_query(conn, query, "Window function examples")
        headers = [
            "Amount",
            "Dept",
            "Quarter",
            "RowNum",
            "Rank",
            "PrevAmt",
            "DeptTotal",
            "MovingAvg",
        ]
        display_results(results, headers, max_rows=10)
        stats.record_query(exec_time, len(results))

    finally:
        conn.close()
        print("\n🔌 Connection closed")

    # Display final statistics
    stats.print_summary()
    print("\n✅ Basic queries demonstration completed!")


def main():
    """Main function for basic queries demo."""
    parser = parse_common_args()
    parser.add_argument(
        "--examples",
        nargs="*",
        choices=[
            "cluster",
            "catalogs",
            "select",
            "types",
            "math",
            "strings",
            "dates",
            "conditions",
            "aggregation",
            "windows",
        ],
        default=None,
        help="Run specific examples only",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    if args.examples:
        print(f"🎯 Running selected examples: {', '.join(args.examples)}")

    demonstrate_basic_queries(args)


if __name__ == "__main__":
    main()
