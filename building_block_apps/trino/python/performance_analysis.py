#!/usr/bin/env python3
"""
Trino Performance Analysis - Building Block Application

This script demonstrates Trino performance analysis and optimization techniques:
- Query execution monitoring and profiling
- Memory usage analysis
- Performance tuning recommendations  
- Connector-specific optimizations
- Resource utilization tracking

Usage:
    bazel run //trino/python:performance_analysis
    bazel run //trino/python:performance_analysis -- --duration 300 --iterations 50

Examples:
    # Basic performance analysis
    bazel run //trino/python:performance_analysis
    
    # Extended performance test
    bazel run //trino/python:performance_analysis -- --duration 600 --iterations 100
    
    # Focus on specific query types
    bazel run //trino/python:performance_analysis -- --focus joins --benchmark

Requirements:
    pip install trino requests psutil
"""

import sys
import time
import argparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from trino_common import (
    get_trino_connection,
    execute_query,
    display_results,
    QueryStats,
    get_cluster_info,
    parse_common_args,
    setup_logging,
    handle_errors,
)

try:
    import psutil
except ImportError:
    print("⚠️ Warning: psutil not found. System monitoring will be limited.")
    psutil = None


class PerformanceAnalyzer:
    """Comprehensive performance analysis for Trino queries."""

    def __init__(self, conn):
        self.conn = conn
        self.stats = QueryStats()
        self.query_history = []

    def get_query_performance_metrics(self, query_id: str = None) -> List[Tuple]:
        """Get detailed performance metrics for queries."""
        if query_id:
            perf_query = f"""
                SELECT 
                    query_id,
                    state,
                    query_type,
                    total_cpu_time,
                    total_scheduled_time,
                    total_memory_reservation,
                    peak_memory_reservation,
                    total_rows,
                    total_bytes,
                    elapsed_time,
                    queued_time,
                    planning_time,
                    analysis_time,
                    execution_time
                FROM system.runtime.queries
                WHERE query_id = '{query_id}'
            """
        else:
            perf_query = """
                SELECT 
                    query_id,
                    state,
                    query_type,
                    total_cpu_time / 1000.0 as cpu_seconds,
                    total_scheduled_time / 1000.0 as scheduled_seconds,
                    total_memory_reservation / 1024.0 / 1024.0 as memory_mb,
                    peak_memory_reservation / 1024.0 / 1024.0 as peak_memory_mb,
                    total_rows,
                    total_bytes / 1024.0 / 1024.0 as data_mb,
                    elapsed_time / 1000.0 as elapsed_seconds
                FROM system.runtime.queries
                WHERE created > current_timestamp - INTERVAL '1' HOUR
                    AND state IN ('FINISHED', 'FAILED', 'RUNNING')
                ORDER BY created DESC
                LIMIT 20
            """

        try:
            results, _ = execute_query(
                self.conn, perf_query, "Getting query performance metrics"
            )
            return results
        except Exception as e:
            print(f"⚠️ Could not retrieve performance metrics: {e}")
            return []

    def analyze_cluster_resource_usage(self) -> Dict[str, Any]:
        """Analyze cluster-wide resource usage."""
        print("\n🖥️ Cluster Resource Analysis")
        print("-" * 40)

        # Node resource usage
        nodes_query = """
            SELECT 
                node_id,
                http_uri,
                coordinator,
                processor_count,
                heap_available / 1024.0 / 1024.0 as heap_available_mb,
                heap_used / 1024.0 / 1024.0 as heap_used_mb,
                (heap_used * 100.0 / heap_available) as heap_utilization_percent,
                recent_cpu_usage,
                recent_system_memory_usage
            FROM system.runtime.nodes
            ORDER BY coordinator DESC, node_id
        """

        try:
            results, _ = execute_query(
                self.conn, nodes_query, "Analyzing cluster resources"
            )
            display_results(
                results,
                [
                    "Node",
                    "URI",
                    "Coord",
                    "CPUs",
                    "HeapAvail(MB)",
                    "HeapUsed(MB)",
                    "Heap%",
                    "CPU%",
                    "SysMem%",
                ],
            )
            return {"nodes": results}
        except Exception as e:
            print(f"⚠️ Could not analyze cluster resources: {e}")
            return {}

    def benchmark_query_types(self, iterations: int = 10) -> Dict[str, List[float]]:
        """Benchmark different types of queries."""
        print(f"\n⚡ Query Performance Benchmarking ({iterations} iterations)")
        print("-" * 50)

        benchmark_queries = {
            "simple_select": "SELECT 1, current_timestamp",
            "mathematical": """
                SELECT 
                    power(2, 10) as power_result,
                    sqrt(625) as sqrt_result,
                    sin(pi()/2) as sin_result,
                    random() as random_result
            """,
            "string_operations": """
                SELECT 
                    upper('performance test') as upper_result,
                    length('Trino Performance Analysis') as length_result,
                    substring('Hello World', 1, 5) as substring_result,
                    concat('Test-', cast(random() * 1000 as varchar)) as concat_result
            """,
            "aggregation": """
                WITH numbers AS (
                    SELECT value 
                    FROM UNNEST(ARRAY[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]) AS t(value)
                )
                SELECT 
                    count(*) as total_count,
                    sum(value) as sum_result,
                    avg(value) as avg_result,
                    stddev(value) as stddev_result
                FROM numbers
            """,
            "window_functions": """
                WITH data AS (
                    SELECT 
                        value,
                        value % 5 as group_id
                    FROM UNNEST(ARRAY[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]) AS t(value)
                )
                SELECT 
                    value,
                    group_id,
                    row_number() OVER (PARTITION BY group_id ORDER BY value) as rn,
                    lag(value) OVER (ORDER BY value) as prev_value,
                    sum(value) OVER (PARTITION BY group_id) as group_sum
                FROM data
            """,
            "json_operations": """
                WITH json_data AS (
                    SELECT JSON '{"name": "test", "values": [1,2,3,4,5], "metadata": {"type": "performance"}}' as data
                )
                SELECT 
                    json_extract_scalar(data, '$.name') as name,
                    json_array_length(json_extract(data, '$.values')) as array_length,
                    json_extract_scalar(data, '$.metadata.type') as metadata_type
                FROM json_data
            """,
        }

        benchmark_results = {}

        for query_name, query in benchmark_queries.items():
            print(f"\n🔍 Benchmarking: {query_name}")
            execution_times = []

            for i in range(iterations):
                try:
                    start_time = time.time()
                    results, exec_time = execute_query(
                        self.conn,
                        query,
                        f"{query_name} iteration {i+1}",
                        fetch_results=True,
                    )
                    execution_times.append(exec_time)
                    self.stats.record_query(exec_time, len(results))

                    if i == 0:  # Show results for first iteration only
                        print(f"  Sample result: {len(results)} rows returned")

                except Exception as e:
                    print(f"  ❌ Iteration {i+1} failed: {e}")
                    self.stats.record_query(0, 0, error=True)
                    execution_times.append(0)

            # Calculate statistics
            valid_times = [t for t in execution_times if t > 0]
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                min_time = min(valid_times)
                max_time = max(valid_times)
                print(
                    f"  ⚡ Average: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s"
                )

            benchmark_results[query_name] = execution_times

        return benchmark_results

    def analyze_memory_usage_patterns(self):
        """Analyze memory usage patterns across different query types."""
        print("\n🧠 Memory Usage Analysis")
        print("-" * 30)

        memory_query = """
            SELECT 
                query_type,
                state,
                COUNT(*) as query_count,
                AVG(peak_memory_reservation / 1024.0 / 1024.0) as avg_peak_memory_mb,
                MAX(peak_memory_reservation / 1024.0 / 1024.0) as max_peak_memory_mb,
                AVG(total_memory_reservation / 1024.0 / 1024.0) as avg_total_memory_mb,
                SUM(total_bytes / 1024.0 / 1024.0) as total_data_processed_mb
            FROM system.runtime.queries
            WHERE created > current_timestamp - INTERVAL '1' HOUR
                AND peak_memory_reservation > 0
            GROUP BY query_type, state
            ORDER BY avg_peak_memory_mb DESC
        """

        try:
            results, _ = execute_query(
                self.conn, memory_query, "Analyzing memory usage patterns"
            )
            headers = [
                "QueryType",
                "State",
                "Count",
                "AvgPeakMB",
                "MaxPeakMB",
                "AvgTotalMB",
                "DataProcessedMB",
            ]
            display_results(results, headers)
            return results
        except Exception as e:
            print(f"⚠️ Could not analyze memory usage: {e}")
            return []

    def generate_performance_recommendations(
        self, benchmark_results: Dict[str, List[float]]
    ) -> List[str]:
        """Generate performance tuning recommendations based on analysis."""
        recommendations = []

        print("\n💡 Performance Recommendations")
        print("-" * 35)

        # Analyze benchmark results
        for query_type, times in benchmark_results.items():
            valid_times = [t for t in times if t > 0]
            if valid_times:
                avg_time = sum(valid_times) / len(valid_times)
                if avg_time > 1.0:
                    recommendations.append(
                        f"🔍 {query_type} queries are slow (avg: {avg_time:.2f}s) - consider optimization"
                    )

                # Check for high variance
                if len(valid_times) > 1:
                    variance = sum((t - avg_time) ** 2 for t in valid_times) / len(
                        valid_times
                    )
                    std_dev = variance**0.5
                    if std_dev / avg_time > 0.5:  # High coefficient of variation
                        recommendations.append(
                            f"⚠️ {query_type} has inconsistent performance - check for resource contention"
                        )

        # General recommendations
        recommendations.extend(
            [
                "🚀 Enable query result caching for repeated queries",
                "🧠 Monitor memory usage and adjust query.max-memory-per-node if needed",
                "⚡ Use EXPLAIN ANALYZE to identify slow operations",
                "📊 Consider partitioning large tables for better query performance",
                "🔗 Use appropriate join algorithms (broadcast vs hash joins)",
                "📈 Monitor cluster resource utilization during peak hours",
            ]
        )

        for i, rec in enumerate(recommendations, 1):
            print(f"{i:2d}. {rec}")

        return recommendations

    def concurrent_query_stress_test(
        self, num_threads: int = 4, duration_seconds: int = 60
    ):
        """Run concurrent queries to test cluster performance under load."""
        print(f"\n🔥 Concurrent Query Stress Test")
        print(f"Threads: {num_threads}, Duration: {duration_seconds}s")
        print("-" * 40)

        stress_queries = [
            "SELECT COUNT(*) FROM UNNEST(ARRAY[1,2,3,4,5,6,7,8,9,10]) AS t(value)",
            "SELECT SUM(value), AVG(value) FROM UNNEST(ARRAY[1,2,3,4,5,6,7,8,9,10]) AS t(value)",
            "SELECT value, ROW_NUMBER() OVER (ORDER BY value) FROM UNNEST(ARRAY[1,2,3,4,5,6,7,8,9,10]) AS t(value)",
            "SELECT UPPER('stress test'), LENGTH('concurrent queries'), CURRENT_TIMESTAMP",
        ]

        def worker_function(thread_id: int):
            """Worker function for concurrent query execution."""
            local_stats = {"queries": 0, "errors": 0, "total_time": 0}
            end_time = time.time() + duration_seconds

            # Create separate connection for each thread
            try:
                local_conn = get_trino_connection()

                while time.time() < end_time:
                    query = stress_queries[thread_id % len(stress_queries)]
                    try:
                        start_time = time.time()
                        cursor = local_conn.cursor()
                        cursor.execute(query)
                        results = cursor.fetchall()
                        cursor.close()

                        exec_time = time.time() - start_time
                        local_stats["queries"] += 1
                        local_stats["total_time"] += exec_time

                        # Small delay to prevent overwhelming the cluster
                        time.sleep(0.1)

                    except Exception as e:
                        local_stats["errors"] += 1
                        print(f"Thread {thread_id} error: {e}")
                        time.sleep(1)  # Longer delay on error

                local_conn.close()

            except Exception as e:
                print(f"Thread {thread_id} connection failed: {e}")

            return thread_id, local_stats

        # Execute concurrent stress test
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_function, i) for i in range(num_threads)]
            thread_results = {}

            for future in as_completed(futures):
                thread_id, stats = future.result()
                thread_results[thread_id] = stats

        total_time = time.time() - start_time

        # Analyze results
        total_queries = sum(stats["queries"] for stats in thread_results.values())
        total_errors = sum(stats["errors"] for stats in thread_results.values())
        total_exec_time = sum(stats["total_time"] for stats in thread_results.values())

        print(f"\n📊 Stress Test Results:")
        print(f"  Total Duration:     {total_time:.1f}s")
        print(f"  Queries Executed:   {total_queries}")
        print(f"  Errors:            {total_errors}")
        print(
            f"  Success Rate:      {((total_queries - total_errors) / max(total_queries, 1) * 100):.1f}%"
        )
        print(f"  Queries per Second: {total_queries / total_time:.1f}")
        print(f"  Avg Query Time:    {(total_exec_time / max(total_queries, 1)):.3f}s")

        print(f"\n📈 Per-Thread Results:")
        for thread_id, stats in thread_results.items():
            qps = stats["queries"] / max(total_time, 1)
            avg_time = stats["total_time"] / max(stats["queries"], 1)
            print(
                f"  Thread {thread_id}: {stats['queries']} queries, {qps:.1f} QPS, {avg_time:.3f}s avg"
            )

        return thread_results


@handle_errors
def demonstrate_performance_analysis(args):
    """
    Main demonstration of performance analysis capabilities.

    Args:
        args: Command line arguments
    """
    print("⚡ Starting Trino Performance Analysis Demo")
    print("=" * 50)

    # Connect to Trino
    conn = get_trino_connection(user=args.user)

    try:
        # Initialize performance analyzer
        analyzer = PerformanceAnalyzer(conn)

        # Cluster resource analysis
        if args.include_resources or args.include_all:
            analyzer.analyze_cluster_resource_usage()

        # Query performance benchmarking
        if args.include_benchmark or args.include_all:
            benchmark_results = analyzer.benchmark_query_types(args.iterations)
        else:
            benchmark_results = {}

        # Memory usage analysis
        if args.include_memory or args.include_all:
            analyzer.analyze_memory_usage_patterns()

        # Performance recommendations
        if args.include_recommendations or args.include_all:
            analyzer.generate_performance_recommendations(benchmark_results)

        # Concurrent query stress test
        if args.include_stress or args.include_all:
            analyzer.concurrent_query_stress_test(
                num_threads=args.threads, duration_seconds=args.duration
            )

        # Recent query performance metrics
        if args.include_metrics or args.include_all:
            print("\n📊 Recent Query Performance Metrics")
            print("-" * 40)
            recent_metrics = analyzer.get_query_performance_metrics()
            if recent_metrics:
                headers = [
                    "QueryID",
                    "State",
                    "Type",
                    "CPU(s)",
                    "Scheduled(s)",
                    "Memory(MB)",
                    "PeakMem(MB)",
                    "Rows",
                    "Data(MB)",
                    "Elapsed(s)",
                ]
                display_results(recent_metrics, headers, max_rows=10)

        # Display final statistics
        analyzer.stats.print_summary()

    finally:
        conn.close()
        print("\n🔌 Connection closed")

    print("\n✅ Performance analysis completed!")


def main():
    """Main function for performance analysis demo."""
    parser = parse_common_args()

    # Add performance analysis specific arguments
    parser.add_argument(
        "--include-all",
        action="store_true",
        default=True,
        help="Run all analyses (default)",
    )
    parser.add_argument(
        "--include-resources",
        action="store_true",
        help="Include cluster resource analysis",
    )
    parser.add_argument(
        "--include-benchmark", action="store_true", help="Include query benchmarking"
    )
    parser.add_argument(
        "--include-memory", action="store_true", help="Include memory usage analysis"
    )
    parser.add_argument(
        "--include-recommendations",
        action="store_true",
        help="Include performance recommendations",
    )
    parser.add_argument(
        "--include-stress",
        action="store_true",
        help="Include concurrent stress testing",
    )
    parser.add_argument(
        "--include-metrics", action="store_true", help="Include recent query metrics"
    )

    parser.add_argument(
        "--iterations", type=int, default=10, help="Number of iterations for benchmarks"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=4,
        help="Number of concurrent threads for stress test",
    )
    parser.add_argument(
        "--duration", type=int, default=60, help="Duration in seconds for stress test"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # If specific includes are set, disable include_all
    if any(
        [
            args.include_resources,
            args.include_benchmark,
            args.include_memory,
            args.include_recommendations,
            args.include_stress,
            args.include_metrics,
        ]
    ):
        args.include_all = False

    demonstrate_performance_analysis(args)


if __name__ == "__main__":
    main()
