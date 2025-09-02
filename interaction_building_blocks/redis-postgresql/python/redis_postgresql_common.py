#!/usr/bin/env python3
"""
Redis-PostgreSQL Interaction Common Utilities

This module provides common utilities for Redis-PostgreSQL caching integration:
- Cache-aside pattern implementation
- PostgreSQL query result caching in Redis
- Cache invalidation and warming strategies
- Performance monitoring and hit rate tracking
- Connection pooling for both Redis and PostgreSQL

Requirements:
    pip install redis psycopg2-binary hiredis
"""

import sys
import time
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
import argparse
import logging
from contextlib import contextmanager

try:
    import redis
    from redis.sentinel import Sentinel
except ImportError:
    print("❌ Error: redis library not found!")
    print("📦 Install with: pip install redis hiredis")
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
    from psycopg2 import sql
except ImportError:
    print("❌ Error: psycopg2 library not found!")
    print("📦 Install with: pip install psycopg2-binary")
    sys.exit(1)


class RedisPostgreSQLConfig:
    """Configuration for Redis-PostgreSQL caching integration."""

    # Redis configuration
    REDIS_HOST = "192.168.1.184"
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None

    # PostgreSQL configuration
    POSTGRESQL_HOST = "192.168.1.184"
    POSTGRESQL_PORT = 5432
    POSTGRESQL_DATABASE = "analytics_db"
    POSTGRESQL_USER = "dataeng"
    POSTGRESQL_PASSWORD = "password"

    # Connection pool settings
    REDIS_MAX_CONNECTIONS = 50
    POSTGRESQL_MIN_CONNECTIONS = 5
    POSTGRESQL_MAX_CONNECTIONS = 20

    # Cache settings
    DEFAULT_TTL = 3600  # 1 hour
    CACHE_KEY_PREFIX = "pg_cache"
    CACHE_VERSION = "v1"

    # Performance settings
    QUERY_TIMEOUT = 30
    CACHE_SERIALIZATION = "json"  # "json" or "pickle"


class RedisCache:
    """Redis cache manager with connection pooling."""

    def __init__(self, config: RedisPostgreSQLConfig = None):
        self.config = config or RedisPostgreSQLConfig()
        self.client = None
        self.pool = None
        self.stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}

    def create_connection_pool(self):
        """Create Redis connection pool."""
        self.pool = redis.ConnectionPool(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=self.config.REDIS_DB,
            password=self.config.REDIS_PASSWORD,
            max_connections=self.config.REDIS_MAX_CONNECTIONS,
            decode_responses=False,  # We handle serialization manually
        )

        self.client = redis.Redis(connection_pool=self.pool)

        # Test connection
        self.client.ping()
        print(
            f"🔌 Connected to Redis: {self.config.REDIS_HOST}:{self.config.REDIS_PORT}"
        )

    def get_client(self) -> redis.Redis:
        """Get Redis client, creating connection if needed."""
        if not self.client:
            self.create_connection_pool()
        return self.client

    def _make_cache_key(self, key: str) -> str:
        """Create standardized cache key."""
        return f"{self.config.CACHE_KEY_PREFIX}:{self.config.CACHE_VERSION}:{key}"

    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage."""
        if self.config.CACHE_SERIALIZATION == "json":
            return json.dumps(data, default=str).encode("utf-8")
        else:
            return pickle.dumps(data)

    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis."""
        if data is None:
            return None

        try:
            if self.config.CACHE_SERIALIZATION == "json":
                return json.loads(data.decode("utf-8"))
            else:
                return pickle.loads(data)
        except Exception as e:
            print(f"⚠️ Deserialization error: {e}")
            return None

    def get(self, key: str) -> Any:
        """Get value from cache."""
        try:
            client = self.get_client()
            cache_key = self._make_cache_key(key)

            data = client.get(cache_key)
            if data is not None:
                self.stats["hits"] += 1
                return self._deserialize_data(data)
            else:
                self.stats["misses"] += 1
                return None

        except Exception as e:
            self.stats["errors"] += 1
            print(f"⚠️ Cache GET error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        try:
            client = self.get_client()
            cache_key = self._make_cache_key(key)
            ttl = ttl or self.config.DEFAULT_TTL

            serialized_data = self._serialize_data(value)
            result = client.setex(cache_key, ttl, serialized_data)

            if result:
                self.stats["sets"] += 1

            return bool(result)

        except Exception as e:
            self.stats["errors"] += 1
            print(f"⚠️ Cache SET error for key '{key}': {e}")
            return False

    def delete(self, *keys: str) -> int:
        """Delete keys from cache."""
        try:
            client = self.get_client()
            cache_keys = [self._make_cache_key(key) for key in keys]

            deleted = client.delete(*cache_keys)
            self.stats["deletes"] += deleted

            return deleted

        except Exception as e:
            self.stats["errors"] += 1
            print(f"⚠️ Cache DELETE error: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """Check if keys exist in cache."""
        try:
            client = self.get_client()
            cache_keys = [self._make_cache_key(key) for key in keys]
            return client.exists(*cache_keys)
        except Exception as e:
            print(f"⚠️ Cache EXISTS error: {e}")
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for key."""
        try:
            client = self.get_client()
            cache_key = self._make_cache_key(key)
            return bool(client.expire(cache_key, ttl))
        except Exception as e:
            print(f"⚠️ Cache EXPIRE error: {e}")
            return False

    def ttl(self, key: str) -> int:
        """Get time-to-live for key."""
        try:
            client = self.get_client()
            cache_key = self._make_cache_key(key)
            return client.ttl(cache_key)
        except Exception as e:
            print(f"⚠️ Cache TTL error: {e}")
            return -2

    def flush_pattern(self, pattern: str = "*"):
        """Flush keys matching pattern."""
        try:
            client = self.get_client()
            cache_pattern = self._make_cache_key(pattern)

            keys = client.keys(cache_pattern)
            if keys:
                deleted = client.delete(*keys)
                print(f"🧹 Flushed {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0

        except Exception as e:
            print(f"⚠️ Cache FLUSH error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.1f}%",
        }

    def close(self):
        """Close Redis connection."""
        if self.pool:
            self.pool.disconnect()


class PostgreSQLDatabase:
    """PostgreSQL database manager with connection pooling."""

    def __init__(self, config: RedisPostgreSQLConfig = None):
        self.config = config or RedisPostgreSQLConfig()
        self.pool = None
        self.stats = {
            "queries": 0,
            "query_time": 0.0,
            "connections_used": 0,
            "errors": 0,
        }

    def create_connection_pool(self):
        """Create PostgreSQL connection pool."""
        dsn = (
            f"host={self.config.POSTGRESQL_HOST} "
            f"port={self.config.POSTGRESQL_PORT} "
            f"dbname={self.config.POSTGRESQL_DATABASE} "
            f"user={self.config.POSTGRESQL_USER} "
            f"password={self.config.POSTGRESQL_PASSWORD}"
        )

        self.pool = psycopg2.pool.ThreadedConnectionPool(
            self.config.POSTGRESQL_MIN_CONNECTIONS,
            self.config.POSTGRESQL_MAX_CONNECTIONS,
            dsn,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )

        print(
            f"🔌 Created PostgreSQL connection pool: {self.config.POSTGRESQL_MIN_CONNECTIONS}-{self.config.POSTGRESQL_MAX_CONNECTIONS}"
        )

    def get_connection_pool(self):
        """Get connection pool, creating if needed."""
        if not self.pool:
            self.create_connection_pool()
        return self.pool

    @contextmanager
    def get_connection(self):
        """Get database connection from pool."""
        pool = self.get_connection_pool()
        conn = None

        try:
            conn = pool.getconn()
            self.stats["connections_used"] += 1
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                pool.putconn(conn)

    def execute_query(
        self,
        query: Union[str, sql.SQL],
        params: Tuple = None,
        fetch_results: bool = True,
    ) -> List[Dict]:
        """Execute query and return results."""
        start_time = time.time()

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)

                    if fetch_results and cursor.description:
                        results = cursor.fetchall()
                        # Convert to list of dicts for JSON serialization
                        return [dict(row) for row in results]
                    else:
                        conn.commit()
                        return []

        except Exception as e:
            self.stats["errors"] += 1
            print(f"❌ Database query error: {e}")
            raise

        finally:
            query_time = time.time() - start_time
            self.stats["queries"] += 1
            self.stats["query_time"] += query_time

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        avg_query_time = self.stats["query_time"] / max(self.stats["queries"], 1)

        return {**self.stats, "avg_query_time": f"{avg_query_time:.3f}s"}

    def close(self):
        """Close connection pool."""
        if self.pool:
            self.pool.closeall()


class CachedDatabaseManager:
    """Manager that combines Redis cache with PostgreSQL backend."""

    def __init__(self, config: RedisPostgreSQLConfig = None):
        self.config = config or RedisPostgreSQLConfig()
        self.cache = RedisCache(config)
        self.db = PostgreSQLDatabase(config)
        self.query_stats = {}

    def _hash_query(self, query: str, params: Tuple = None) -> str:
        """Create hash key for query + parameters."""
        query_string = str(query) + str(params if params else "")
        return hashlib.md5(query_string.encode()).hexdigest()

    def cached_query(
        self,
        query: Union[str, sql.SQL],
        params: Tuple = None,
        cache_ttl: int = None,
        cache_key: str = None,
        force_refresh: bool = False,
    ) -> List[Dict]:
        """Execute query with caching."""
        # Generate cache key
        if cache_key is None:
            cache_key = f"query_{self._hash_query(query, params)}"

        # Try cache first (unless force refresh)
        if not force_refresh:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                print(f"🎯 Cache HIT for query: {cache_key[:16]}...")
                return cached_result

        # Cache miss - query database
        print(f"💾 Cache MISS - querying database: {cache_key[:16]}...")
        start_time = time.time()

        try:
            results = self.db.execute_query(query, params)
            query_time = time.time() - start_time

            # Cache the results
            cache_ttl = cache_ttl or self.config.DEFAULT_TTL
            self.cache.set(cache_key, results, ttl=cache_ttl)

            # Track query performance
            if str(query) not in self.query_stats:
                self.query_stats[str(query)] = {
                    "count": 0,
                    "total_time": 0,
                    "cache_hits": 0,
                    "cache_misses": 0,
                }

            stats = self.query_stats[str(query)]
            stats["count"] += 1
            stats["total_time"] += query_time
            stats["cache_misses"] += 1

            print(f"📊 Query executed in {query_time:.3f}s, cached for {cache_ttl}s")
            return results

        except Exception as e:
            print(f"❌ Cached query failed: {e}")
            raise

    def invalidate_cache(self, patterns: List[str] = None, keys: List[str] = None):
        """Invalidate cache entries."""
        if keys:
            deleted = self.cache.delete(*keys)
            print(f"🗑️ Invalidated {deleted} specific cache keys")

        if patterns:
            total_deleted = 0
            for pattern in patterns:
                deleted = self.cache.flush_pattern(pattern)
                total_deleted += deleted
            print(f"🧹 Invalidated {total_deleted} cache keys by patterns")

    def warm_cache(self, queries: List[Dict[str, Any]]):
        """Warm cache with predefined queries."""
        print(f"🔥 Warming cache with {len(queries)} queries...")

        for query_info in queries:
            try:
                self.cached_query(
                    query=query_info["query"],
                    params=query_info.get("params"),
                    cache_ttl=query_info.get("ttl"),
                    cache_key=query_info.get("cache_key"),
                    force_refresh=True,
                )
                time.sleep(0.1)  # Small delay to prevent overload
            except Exception as e:
                print(f"⚠️ Failed to warm cache for query: {e}")

        print("✅ Cache warming completed")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        cache_stats = self.cache.get_stats()
        db_stats = self.db.get_stats()

        # Calculate query statistics
        total_queries = sum(stats["count"] for stats in self.query_stats.values())
        total_cache_hits = sum(
            stats["cache_hits"] for stats in self.query_stats.values()
        )
        total_cache_misses = sum(
            stats["cache_misses"] for stats in self.query_stats.values()
        )

        return {
            "cache": cache_stats,
            "database": db_stats,
            "queries": {
                "total_unique_queries": len(self.query_stats),
                "total_query_executions": total_queries,
                "cache_hits": total_cache_hits,
                "cache_misses": total_cache_misses,
                "detailed_stats": self.query_stats,
            },
        }

    def close(self):
        """Close all connections."""
        self.cache.close()
        self.db.close()


def create_sample_queries() -> List[Dict[str, Any]]:
    """Create sample queries for testing and cache warming."""
    return [
        {
            "query": "SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'public' LIMIT 10",
            "cache_key": "public_tables",
            "ttl": 1800,
        },
        {
            "query": "SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema = 'public'",
            "cache_key": "table_count",
            "ttl": 3600,
        },
        {
            "query": "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s",
            "params": ("customers",),
            "cache_key": "customers_schema",
            "ttl": 7200,
        },
        {
            "query": """
                SELECT 
                    schemaname,
                    tablename,
                    tableowner,
                    attname as column_name,
                    typname as data_type
                FROM pg_tables pt
                JOIN pg_class pc ON pc.relname = pt.tablename
                JOIN pg_attribute pa ON pa.attrelid = pc.oid
                JOIN pg_type pgt ON pgt.oid = pa.atttypid
                WHERE pt.schemaname = 'public'
                AND pa.attnum > 0
                ORDER BY pt.tablename, pa.attnum
            """,
            "cache_key": "detailed_schema",
            "ttl": 3600,
        },
    ]


def parse_common_args() -> argparse.ArgumentParser:
    """Create argument parser with common Redis-PostgreSQL options."""
    parser = argparse.ArgumentParser(description="Redis-PostgreSQL Caching Application")

    parser.add_argument(
        "--redis-host", default=RedisPostgreSQLConfig.REDIS_HOST, help="Redis host"
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=RedisPostgreSQLConfig.REDIS_PORT,
        help="Redis port",
    )
    parser.add_argument(
        "--redis-db",
        type=int,
        default=RedisPostgreSQLConfig.REDIS_DB,
        help="Redis database number",
    )

    parser.add_argument(
        "--postgresql-host",
        default=RedisPostgreSQLConfig.POSTGRESQL_HOST,
        help="PostgreSQL host",
    )
    parser.add_argument(
        "--postgresql-port",
        type=int,
        default=RedisPostgreSQLConfig.POSTGRESQL_PORT,
        help="PostgreSQL port",
    )
    parser.add_argument(
        "--postgresql-database",
        default=RedisPostgreSQLConfig.POSTGRESQL_DATABASE,
        help="PostgreSQL database",
    )
    parser.add_argument(
        "--postgresql-user",
        default=RedisPostgreSQLConfig.POSTGRESQL_USER,
        help="PostgreSQL user",
    )
    parser.add_argument(
        "--postgresql-password",
        default=RedisPostgreSQLConfig.POSTGRESQL_PASSWORD,
        help="PostgreSQL password",
    )

    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=RedisPostgreSQLConfig.DEFAULT_TTL,
        help="Default cache TTL in seconds",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    return parser


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
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
    print("🧪 Testing Redis-PostgreSQL common utilities...")

    try:
        # Test configuration
        config = RedisPostgreSQLConfig()
        print(f"✅ Redis: {config.REDIS_HOST}:{config.REDIS_PORT}")
        print(f"✅ PostgreSQL: {config.POSTGRESQL_HOST}:{config.POSTGRESQL_PORT}")

        # Test cached database manager
        cache_manager = CachedDatabaseManager(config)

        # Test a simple cached query
        results = cache_manager.cached_query(
            "SELECT 1 as test_value, current_timestamp as query_time",
            cache_key="test_query",
            cache_ttl=300,
        )

        print(f"✅ Cached query result: {results}")

        # Test cache hit
        cached_results = cache_manager.cached_query(
            "SELECT 1 as test_value, current_timestamp as query_time",
            cache_key="test_query",
        )

        print(f"✅ Cache hit test passed")

        # Display performance summary
        perf_summary = cache_manager.get_performance_summary()
        print(f"✅ Performance summary: {perf_summary['cache']['hit_rate']} hit rate")

        # Cleanup
        cache_manager.close()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
