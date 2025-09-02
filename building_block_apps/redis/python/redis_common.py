#!/usr/bin/env python3
"""
Redis Common Utilities for Building Block Applications

This module provides common utilities for Redis building block examples:
- Connection management and configuration
- Caching utilities and patterns
- Pub/Sub messaging helpers
- Error handling and logging
- Performance monitoring
- Data serialization helpers

Requirements:
    pip install redis hiredis
"""

import json
import sys
import time
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import argparse
import logging

try:
    import redis
    import redis.sentinel
except ImportError:
    print("❌ Error: redis library not found!")
    print("📦 Install with: pip install redis hiredis")
    sys.exit(1)


class RedisConfig:
    """Redis configuration for building block apps."""

    # Redis settings (from your setup)
    HOST = "192.168.1.184"
    PORT = 6379
    DATABASE = 0
    PASSWORD = None  # Set if authentication is required

    # Connection pool settings
    MAX_CONNECTIONS = 20
    SOCKET_TIMEOUT = 5
    SOCKET_CONNECT_TIMEOUT = 5

    # Default TTL settings
    DEFAULT_TTL = 3600  # 1 hour
    SHORT_TTL = 300  # 5 minutes
    LONG_TTL = 86400  # 24 hours


class RedisConnection:
    """Enhanced Redis connection manager with monitoring."""

    def __init__(self, config: Optional[RedisConfig] = None):
        self.config = config or RedisConfig()
        self.client = None
        self.pool = None
        self.stats = {"operations": 0, "hits": 0, "misses": 0, "errors": 0}

    def create_connection(self) -> redis.Redis:
        """Create a Redis connection with connection pooling."""
        try:
            # Create connection pool
            self.pool = redis.ConnectionPool(
                host=self.config.HOST,
                port=self.config.PORT,
                db=self.config.DATABASE,
                password=self.config.PASSWORD,
                max_connections=self.config.MAX_CONNECTIONS,
                socket_timeout=self.config.SOCKET_TIMEOUT,
                socket_connect_timeout=self.config.SOCKET_CONNECT_TIMEOUT,
                decode_responses=True,  # Automatically decode bytes to strings
            )

            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            self.client.ping()

            print(f"🔌 Connected to Redis: {self.config.HOST}:{self.config.PORT}")
            print(f"📊 Connection pool: {self.config.MAX_CONNECTIONS} max connections")

            return self.client

        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            raise

    def get_client(self) -> redis.Redis:
        """Get Redis client, creating connection if needed."""
        if not self.client:
            self.create_connection()
        return self.client

    def execute_operation(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute Redis operation with monitoring and error handling."""
        start_time = time.time()

        try:
            result = operation_func(*args, **kwargs)
            execution_time = time.time() - start_time

            self.stats["operations"] += 1

            # Track hits/misses for GET operations
            if operation_name.lower() in ["get", "hget", "lrange", "smembers"]:
                if result:
                    self.stats["hits"] += 1
                else:
                    self.stats["misses"] += 1

            print(f"✅ {operation_name} completed in {execution_time:.3f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.stats["errors"] += 1
            print(f"❌ {operation_name} failed after {execution_time:.3f}s: {e}")
            raise

    def close_connection(self):
        """Close Redis connection and connection pool."""
        if self.pool:
            self.pool.disconnect()
            print("🔌 Redis connection closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get connection and operation statistics."""
        total_ops = max(self.stats["operations"], 1)
        hit_rate = (
            self.stats["hits"] / max(self.stats["hits"] + self.stats["misses"], 1)
        ) * 100

        return {
            "operations_executed": self.stats["operations"],
            "cache_hits": self.stats["hits"],
            "cache_misses": self.stats["misses"],
            "errors": self.stats["errors"],
            "hit_rate": f"{hit_rate:.1f}%",
            "error_rate": f"{(self.stats['errors'] / total_ops * 100):.1f}%",
        }


def serialize_data(data: Any) -> str:
    """Serialize Python data for Redis storage."""
    if isinstance(data, (str, int, float, bool)):
        return str(data)
    elif isinstance(data, (dict, list)):
        return json.dumps(data)
    else:
        # Use pickle for complex objects
        return pickle.dumps(data).hex()


def deserialize_data(data: str, data_type: str = "json") -> Any:
    """Deserialize data from Redis."""
    if not data:
        return None

    try:
        if data_type == "json":
            return json.loads(data)
        elif data_type == "pickle":
            return pickle.loads(bytes.fromhex(data))
        else:
            return data
    except Exception as e:
        print(f"⚠️ Deserialization failed: {e}")
        return data


def get_redis_info(redis_conn: RedisConnection) -> Dict[str, Any]:
    """Get Redis server information."""
    try:
        client = redis_conn.get_client()
        info = client.info()

        # Extract key metrics
        server_info = {
            "version": info.get("redis_version", "Unknown"),
            "mode": info.get("redis_mode", "standalone"),
            "uptime": info.get("uptime_in_seconds", 0),
            "memory_used": info.get("used_memory_human", "Unknown"),
            "memory_peak": info.get("used_memory_peak_human", "Unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "db_keys": {},
        }

        # Get database key counts
        for key, value in info.items():
            if key.startswith("db"):
                db_info = dict(item.split("=") for item in value.split(","))
                server_info["db_keys"][key] = db_info.get("keys", "0")

        return server_info

    except Exception as e:
        print(f"⚠️ Could not retrieve Redis info: {e}")
        return {}


def display_redis_info(redis_conn: RedisConnection):
    """Display Redis server information in a formatted way."""
    info = get_redis_info(redis_conn)

    if info:
        print("\n🔍 Redis Server Information:")
        print("=" * 35)
        print(f"Version:         {info.get('version', 'Unknown')}")
        print(f"Mode:            {info.get('mode', 'Unknown')}")
        print(f"Uptime:          {info.get('uptime', 0)} seconds")
        print(f"Memory Used:     {info.get('memory_used', 'Unknown')}")
        print(f"Memory Peak:     {info.get('memory_peak', 'Unknown')}")
        print(f"Connected Clients: {info.get('connected_clients', 0)}")
        print(f"Total Commands:  {info.get('total_commands', 0)}")

        # Calculate hit rate
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        if hits + misses > 0:
            hit_rate = (hits / (hits + misses)) * 100
            print(f"Hit Rate:        {hit_rate:.1f}%")

        # Database information
        db_keys = info.get("db_keys", {})
        if db_keys:
            print("\nDatabase Keys:")
            for db, count in db_keys.items():
                print(f"  {db}: {count} keys")

        print("=" * 35)


class CacheManager:
    """High-level cache management utilities."""

    def __init__(self, redis_conn: RedisConnection, default_ttl: int = None):
        self.redis_conn = redis_conn
        self.client = redis_conn.get_client()
        self.default_ttl = default_ttl or RedisConfig.DEFAULT_TTL

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with automatic deserialization."""
        try:
            result = self.redis_conn.execute_operation("GET", self.client.get, key)

            if result is None:
                return default

            # Try to deserialize JSON first, fall back to string
            try:
                return json.loads(result)
            except (json.JSONDecodeError, ValueError):
                return result

        except Exception as e:
            print(f"⚠️ Cache GET failed for key '{key}': {e}")
            return default

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with automatic serialization."""
        try:
            serialized_value = serialize_data(value)
            ttl = ttl or self.default_ttl

            result = self.redis_conn.execute_operation(
                "SET", self.client.setex, key, ttl, serialized_value
            )

            return bool(result)

        except Exception as e:
            print(f"⚠️ Cache SET failed for key '{key}': {e}")
            return False

    def delete(self, *keys: str) -> int:
        """Delete one or more keys from cache."""
        try:
            result = self.redis_conn.execute_operation(
                "DELETE", self.client.delete, *keys
            )
            return result

        except Exception as e:
            print(f"⚠️ Cache DELETE failed: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        """Check if keys exist in cache."""
        try:
            result = self.redis_conn.execute_operation(
                "EXISTS", self.client.exists, *keys
            )
            return result

        except Exception as e:
            print(f"⚠️ Cache EXISTS failed: {e}")
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key."""
        try:
            result = self.redis_conn.execute_operation(
                "EXPIRE", self.client.expire, key, ttl
            )
            return bool(result)

        except Exception as e:
            print(f"⚠️ Cache EXPIRE failed for key '{key}': {e}")
            return False

    def ttl(self, key: str) -> int:
        """Get time-to-live for a key."""
        try:
            result = self.redis_conn.execute_operation("TTL", self.client.ttl, key)
            return result

        except Exception as e:
            print(f"⚠️ Cache TTL failed for key '{key}': {e}")
            return -2


class PubSubManager:
    """Pub/Sub messaging utilities."""

    def __init__(self, redis_conn: RedisConnection):
        self.redis_conn = redis_conn
        self.client = redis_conn.get_client()
        self.pubsub = None

    def create_pubsub(self) -> redis.client.PubSub:
        """Create a pub/sub connection."""
        if not self.pubsub:
            self.pubsub = self.client.pubsub()
        return self.pubsub

    def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a channel."""
        try:
            serialized_message = serialize_data(message)
            result = self.redis_conn.execute_operation(
                "PUBLISH", self.client.publish, channel, serialized_message
            )
            return result

        except Exception as e:
            print(f"⚠️ PUBLISH failed for channel '{channel}': {e}")
            return 0

    def subscribe(self, *channels: str):
        """Subscribe to one or more channels."""
        try:
            pubsub = self.create_pubsub()
            pubsub.subscribe(*channels)
            print(f"📡 Subscribed to channels: {', '.join(channels)}")
            return pubsub

        except Exception as e:
            print(f"⚠️ SUBSCRIBE failed: {e}")
            return None

    def listen_for_messages(self, pubsub, timeout: int = None):
        """Listen for messages on subscribed channels."""
        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    # Try to deserialize the message
                    try:
                        data = json.loads(message["data"])
                    except (json.JSONDecodeError, ValueError):
                        data = message["data"]

                    yield {
                        "channel": message["channel"],
                        "data": data,
                        "timestamp": datetime.now().isoformat(),
                    }

        except Exception as e:
            print(f"⚠️ Message listening failed: {e}")


class RedisBenchmark:
    """Redis performance benchmarking utilities."""

    def __init__(self, redis_conn: RedisConnection):
        self.redis_conn = redis_conn
        self.client = redis_conn.get_client()

    def benchmark_operations(
        self, iterations: int = 1000
    ) -> Dict[str, Dict[str, float]]:
        """Benchmark various Redis operations."""
        results = {}

        # SET benchmark
        print(f"🏃 Benchmarking SET operations ({iterations} iterations)...")
        start_time = time.time()
        for i in range(iterations):
            self.client.set(f"benchmark:set:{i}", f"value_{i}", ex=300)
        set_time = time.time() - start_time

        results["SET"] = {
            "total_time": set_time,
            "ops_per_second": iterations / set_time,
            "avg_time_ms": (set_time / iterations) * 1000,
        }

        # GET benchmark
        print(f"🏃 Benchmarking GET operations ({iterations} iterations)...")
        start_time = time.time()
        for i in range(iterations):
            self.client.get(f"benchmark:set:{i}")
        get_time = time.time() - start_time

        results["GET"] = {
            "total_time": get_time,
            "ops_per_second": iterations / get_time,
            "avg_time_ms": (get_time / iterations) * 1000,
        }

        # DELETE benchmark
        print(f"🏃 Benchmarking DELETE operations ({iterations} iterations)...")
        start_time = time.time()
        keys_to_delete = [f"benchmark:set:{i}" for i in range(iterations)]
        self.client.delete(*keys_to_delete)
        delete_time = time.time() - start_time

        results["DELETE"] = {
            "total_time": delete_time,
            "ops_per_second": iterations / delete_time,
            "avg_time_ms": (delete_time / iterations) * 1000,
        }

        return results

    def display_benchmark_results(self, results: Dict[str, Dict[str, float]]):
        """Display benchmark results in a formatted table."""
        print("\n📊 Redis Benchmark Results:")
        print("=" * 60)
        print(
            f"{'Operation':<10} {'Total Time':<12} {'Ops/Sec':<12} {'Avg Time (ms)':<15}"
        )
        print("-" * 60)

        for operation, metrics in results.items():
            print(
                f"{operation:<10} {metrics['total_time']:<12.3f} "
                f"{metrics['ops_per_second']:<12.1f} {metrics['avg_time_ms']:<15.3f}"
            )

        print("=" * 60)


def parse_common_args() -> argparse.ArgumentParser:
    """
    Create argument parser with common Redis options.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(description="Redis Building Block Application")

    parser.add_argument("--host", default=RedisConfig.HOST, help="Redis host")
    parser.add_argument("--port", type=int, default=RedisConfig.PORT, help="Redis port")
    parser.add_argument(
        "--database",
        type=int,
        default=RedisConfig.DATABASE,
        help="Redis database number",
    )
    parser.add_argument(
        "--password", default=RedisConfig.PASSWORD, help="Redis password"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=RedisConfig.SOCKET_TIMEOUT,
        help="Socket timeout in seconds",
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
    print("🧪 Testing Redis common utilities...")

    try:
        redis_conn = RedisConnection()

        # Test basic connection
        client = redis_conn.get_client()
        client.set("test:common", "Hello Redis!", ex=60)
        result = client.get("test:common")
        print(f"✅ Basic test result: {result}")

        # Test cache manager
        cache = CacheManager(redis_conn, default_ttl=60)
        cache.set("test:cache", {"message": "Cache test", "timestamp": time.time()})
        cached_result = cache.get("test:cache")
        print(f"✅ Cache test result: {cached_result}")

        # Display Redis info
        display_redis_info(redis_conn)

        # Cleanup
        client.delete("test:common", "test:cache")
        redis_conn.close_connection()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
