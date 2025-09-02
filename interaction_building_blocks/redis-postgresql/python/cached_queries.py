#!/usr/bin/env python3
"""
Redis-PostgreSQL Cached Queries - Interaction Building Block

This application demonstrates the cache-aside pattern using Redis as a caching layer
for PostgreSQL database queries. It showcases:
- High-performance cached database queries
- Cache hit/miss monitoring and optimization
- Cache invalidation strategies
- Performance benchmarking with and without cache
- Multiple query patterns and caching strategies

Usage:
    bazel run //redis-postgresql/python:cached_queries -- --cache-ttl 300 --benchmark
    bazel run //redis-postgresql/python:cached_queries -- --query-type analytics --duration 120

Examples:
    # Basic cached queries with performance monitoring
    bazel run //redis-postgresql/python:cached_queries
    
    # Performance benchmark comparing cached vs uncached
    bazel run //redis-postgresql/python:cached_queries -- --benchmark --iterations 100
    
    # Analytics queries with custom TTL
    bazel run //redis-postgresql/python:cached_queries -- --query-type analytics --cache-ttl 600

Requirements:
    pip install redis psycopg2-binary hiredis
"""

import sys
import time
import random
from typing import List, Dict, Any
from redis_postgresql_common import (
    CachedDatabaseManager,
    RedisPostgreSQLConfig,
    create_sample_queries,
    parse_common_args,
    setup_logging,
    handle_errors,
)


@handle_errors
def demonstrate_cached_queries(args):
    """
    Demonstrate cached database queries with performance monitoring.

    Args:
        args: Command line arguments
    """
    print("🚀 Starting Redis-PostgreSQL Cached Queries Demo")
    print("=" * 55)

    # Initialize configuration
    config = RedisPostgreSQLConfig()
    if args.cache_ttl:
        config.DEFAULT_TTL = args.cache_ttl

    # Create cached database manager
    cache_manager = CachedDatabaseManager(config)

    print(f"🔧 Configuration:")
    print(f"   Redis: {config.REDIS_HOST}:{config.REDIS_PORT}")
    print(f"   PostgreSQL: {config.POSTGRESQL_HOST}:{config.POSTGRESQL_PORT}")
    print(f"   Cache TTL: {config.DEFAULT_TTL}s")

    if hasattr(args, "benchmark") and args.benchmark:
        run_performance_benchmark(cache_manager, args)
    else:
        run_cached_query_examples(cache_manager, args)

    # Display final performance summary
    perf_summary = cache_manager.get_performance_summary()
    print("\n📊 Final Performance Summary:")
    print("=" * 40)
    print(f"Cache Hit Rate: {perf_summary['cache']['hit_rate']}")
    print(f"Total Queries: {perf_summary['database']['queries']}")
    print(f"Avg Query Time: {perf_summary['database']['avg_query_time']}")
    print(f"Cache Sets: {perf_summary['cache']['sets']}")
    print(f"Cache Hits: {perf_summary['cache']['hits']}")
    print(f"Cache Misses: {perf_summary['cache']['misses']}")

    # Cleanup
    cache_manager.close()
    print("\n✅ Cached queries demonstration completed!")


def run_cached_query_examples(cache_manager: CachedDatabaseManager, args):
    """Run various cached query examples."""
    print("\n🔍 Running Cached Query Examples")
    print("-" * 35)

    # Example 1: Basic table information (frequently accessed)
    print("\n1️⃣ Querying table information (should be cached)...")
    for i in range(3):
        results = cache_manager.cached_query(
            """
            SELECT 
                table_name,
                table_type,
                table_schema
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            LIMIT 10
            """,
            cache_key="public_tables",
            cache_ttl=args.cache_ttl or 3600,
        )
        print(f"   Iteration {i+1}: Found {len(results)} tables")
        time.sleep(0.5)  # Small delay to see caching effect

    # Example 2: Column information (medium frequency)
    print("\n2️⃣ Querying column information for specific tables...")
    table_names = ["customers", "orders", "products"]  # Common table names

    for table_name in table_names:
        results = cache_manager.cached_query(
            """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = %s
            AND table_schema = 'public'
            ORDER BY ordinal_position
            """,
            params=(table_name,),
            cache_key=f"columns_{table_name}",
            cache_ttl=args.cache_ttl or 1800,
        )
        print(f"   Table '{table_name}': {len(results)} columns")

    # Example 3: Database statistics (expensive query, good for caching)
    print("\n3️⃣ Running expensive analytical query...")
    results = cache_manager.cached_query(
        """
        SELECT 
            schemaname,
            COUNT(*) as table_count,
            STRING_AGG(tablename, ', ') as table_names
        FROM pg_tables 
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
        GROUP BY schemaname
        ORDER BY table_count DESC
        """,
        cache_key="schema_analytics",
        cache_ttl=args.cache_ttl or 7200,
    )
    print(f"   Found statistics for {len(results)} schemas")

    # Example 4: Repeat expensive query to demonstrate cache hit
    print("\n4️⃣ Repeating expensive query (should hit cache)...")
    start_time = time.time()
    results = cache_manager.cached_query(
        """
        SELECT 
            schemaname,
            COUNT(*) as table_count,
            STRING_AGG(tablename, ', ') as table_names
        FROM pg_tables 
        WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
        GROUP BY schemaname
        ORDER BY table_count DESC
        """,
        cache_key="schema_analytics",
    )
    cache_time = time.time() - start_time
    print(f"   Query completed in {cache_time:.4f}s (cached result)")

    # Example 5: Cache invalidation demonstration
    print("\n5️⃣ Demonstrating cache invalidation...")
    print("   Current cache statistics:")
    cache_stats = cache_manager.cache.get_stats()
    print(f"   - Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}")

    # Invalidate specific cache entries
    cache_manager.invalidate_cache(keys=["public_tables", "schema_analytics"])

    # Re-run one of the queries to see cache miss
    print("   Re-running table query after invalidation...")
    results = cache_manager.cached_query(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 5",
        cache_key="public_tables",
        cache_ttl=300,
    )
    print(f"   Query returned {len(results)} results (should be cache miss)")


def run_performance_benchmark(cache_manager: CachedDatabaseManager, args):
    """Run performance benchmark comparing cached vs uncached queries."""
    print("\n⚡ Running Performance Benchmark")
    print("-" * 35)

    # Define benchmark queries
    benchmark_queries = [
        {
            "name": "Table Count",
            "query": "SELECT COUNT(*) as total FROM information_schema.tables WHERE table_schema = 'public'",
            "cache_key": "table_count_bench",
        },
        {
            "name": "Column Details",
            "query": """
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                ORDER BY table_name, ordinal_position 
                LIMIT 50
            """,
            "cache_key": "column_details_bench",
        },
        {
            "name": "Table Sizes",
            "query": """
                SELECT 
                    schemaname, 
                    tablename,
                    tableowner
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """,
            "cache_key": "table_sizes_bench",
        },
    ]

    iterations = getattr(args, "iterations", 20)
    print(f"Running {iterations} iterations of {len(benchmark_queries)} queries...")

    results = {}

    for query_info in benchmark_queries:
        query_name = query_info["name"]
        results[query_name] = {
            "uncached_times": [],
            "cached_times": [],
            "cache_times": [],
        }

        print(f"\n📊 Benchmarking: {query_name}")

        # First, ensure cache is empty for this query
        cache_manager.invalidate_cache(keys=[query_info["cache_key"]])

        # Run uncached iterations (force refresh each time)
        print("   Running uncached iterations...")
        for i in range(min(iterations, 5)):  # Limit uncached runs to avoid overload
            start_time = time.time()
            cache_manager.cached_query(
                query_info["query"],
                cache_key=query_info["cache_key"],
                force_refresh=True,
                cache_ttl=3600,
            )
            uncached_time = time.time() - start_time
            results[query_name]["uncached_times"].append(uncached_time)
            print(f"     Uncached {i+1}: {uncached_time:.4f}s")

        # Run cached iterations
        print("   Running cached iterations...")
        for i in range(iterations):
            start_time = time.time()
            cache_manager.cached_query(
                query_info["query"], cache_key=query_info["cache_key"]
            )
            cached_time = time.time() - start_time
            results[query_name]["cached_times"].append(cached_time)
            if i < 5:  # Only print first few
                print(f"     Cached {i+1}: {cached_time:.4f}s")

    # Display benchmark results
    print("\n📈 Benchmark Results Summary:")
    print("=" * 60)
    print(f"{'Query':<20} {'Uncached Avg':<15} {'Cached Avg':<15} {'Speedup':<10}")
    print("-" * 60)

    for query_name, timings in results.items():
        uncached_avg = sum(timings["uncached_times"]) / len(timings["uncached_times"])
        cached_avg = sum(timings["cached_times"]) / len(timings["cached_times"])
        speedup = uncached_avg / cached_avg if cached_avg > 0 else float("inf")

        print(
            f"{query_name:<20} {uncached_avg:<15.4f} {cached_avg:<15.4f} {speedup:<10.1f}x"
        )

    # Overall statistics
    all_uncached = [
        t for timings in results.values() for t in timings["uncached_times"]
    ]
    all_cached = [t for timings in results.values() for t in timings["cached_times"]]

    overall_uncached_avg = sum(all_uncached) / len(all_uncached)
    overall_cached_avg = sum(all_cached) / len(all_cached)
    overall_speedup = overall_uncached_avg / overall_cached_avg

    print("-" * 60)
    print(
        f"{'OVERALL':<20} {overall_uncached_avg:<15.4f} {overall_cached_avg:<15.4f} {overall_speedup:<10.1f}x"
    )
    print("=" * 60)


def main():
    """Main function for cached queries demo."""
    parser = parse_common_args()

    # Add cached queries specific arguments
    parser.add_argument(
        "--query-type",
        choices=["basic", "analytics", "mixed"],
        default="mixed",
        help="Type of queries to run",
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Run performance benchmark"
    )
    parser.add_argument(
        "--iterations", type=int, default=20, help="Number of iterations for benchmark"
    )
    parser.add_argument(
        "--duration", type=int, default=60, help="Duration for continuous query testing"
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    demonstrate_cached_queries(args)


if __name__ == "__main__":
    main()
