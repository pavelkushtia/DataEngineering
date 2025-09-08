#!/usr/bin/env python3
"""
Iceberg Streaming Analytics

This script provides real-time analytics on streaming data written to Iceberg tables.
It demonstrates reading from Iceberg using various engines and performing analytics.
"""

import sys
import time
import logging
from typing import Dict, List, Optional
from flink_iceberg_common import FlinkIcebergManager, FlinkIcebergConfig
import subprocess
import json

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IcebergStreamingAnalytics:
    """Analytics for Iceberg streaming data"""

    def __init__(self, config: Optional[FlinkIcebergConfig] = None):
        self.config = config or FlinkIcebergConfig()
        self.manager = FlinkIcebergManager(self.config)

    def setup_analytics_environment(self):
        """Setup analytics environment"""
        logger.info("🔧 Setting up analytics environment...")

        try:
            # Create table environment for analytics
            table_env = self.manager.create_table_environment()
            self.manager.create_iceberg_catalog("iceberg_catalog")

            # Use lakehouse namespace
            table_env.execute_sql("USE lakehouse")

            logger.info("✅ Analytics environment ready")
            return table_env

        except Exception as e:
            logger.error(f"❌ Failed to setup analytics environment: {e}")
            raise

    def get_streaming_table_stats(self, table_name: str = "streaming_events") -> Dict:
        """Get basic statistics about the streaming table"""
        logger.info(f"📊 Getting statistics for table: {table_name}")

        try:
            table_env = self.manager.table_env

            # Get record count by region
            region_stats_sql = f"""
                SELECT 
                    region,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT event_type) as unique_event_types
                FROM {table_name} 
                GROUP BY region
                ORDER BY event_count DESC
            """

            region_result = table_env.execute_sql(region_stats_sql)
            region_stats = []

            with region_result.collect() as results:
                for row in results:
                    region_stats.append(
                        {
                            "region": row[0],
                            "event_count": row[1],
                            "unique_users": row[2],
                            "unique_event_types": row[3],
                        }
                    )

            # Get hourly statistics
            hourly_stats_sql = f"""
                SELECT 
                    year, month, day, hour,
                    COUNT(*) as hourly_events,
                    COUNT(DISTINCT user_id) as hourly_unique_users
                FROM {table_name} 
                GROUP BY year, month, day, hour
                ORDER BY year, month, day, hour
            """

            hourly_result = table_env.execute_sql(hourly_stats_sql)
            hourly_stats = []

            with hourly_result.collect() as results:
                for row in results:
                    hourly_stats.append(
                        {
                            "timestamp": f"{row[0]}-{row[1]:02d}-{row[2]:02d} {row[3]:02d}:00",
                            "events": row[4],
                            "unique_users": row[5],
                        }
                    )

            return {
                "table_name": table_name,
                "region_stats": region_stats,
                "hourly_stats": hourly_stats,
                "total_regions": len(region_stats),
                "total_hours": len(hourly_stats),
            }

        except Exception as e:
            logger.error(f"❌ Failed to get table stats: {e}")
            return {"error": str(e)}

    def run_real_time_aggregations(self, table_name: str = "streaming_events") -> None:
        """Run real-time aggregations on streaming data"""
        logger.info("🔄 Running real-time aggregations...")

        try:
            table_env = self.manager.table_env

            # Create a view for windowed aggregations
            windowed_sql = f"""
                CREATE TEMPORARY VIEW windowed_events AS
                SELECT 
                    region,
                    event_type,
                    TUMBLE_START(event_time, INTERVAL '1' HOUR) as window_start,
                    TUMBLE_END(event_time, INTERVAL '1' HOUR) as window_end,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM {table_name}
                GROUP BY 
                    region, 
                    event_type,
                    TUMBLE(event_time, INTERVAL '1' HOUR)
            """

            table_env.execute_sql(windowed_sql)

            # Query the windowed aggregations
            result_sql = """
                SELECT * FROM windowed_events 
                ORDER BY window_start DESC, event_count DESC 
                LIMIT 20
            """

            result = table_env.execute_sql(result_sql)

            logger.info("📈 Real-time aggregation results:")
            with result.collect() as results:
                for row in results:
                    logger.info(
                        f"  {row[0]} | {row[1]} | {row[2]} to {row[3]} | Events: {row[4]} | Users: {row[5]}"
                    )

        except Exception as e:
            logger.error(f"❌ Real-time aggregations failed: {e}")

    def query_with_trino(self, table_name: str = "streaming_events") -> Dict:
        """Query streaming data using Trino for comparison"""
        logger.info("🔍 Querying streaming data with Trino...")

        try:
            trino_query = f"""
                SELECT 
                    region,
                    event_type,
                    date_trunc('hour', event_time) as hour,
                    count(*) as event_count,
                    count(distinct user_id) as unique_users
                FROM iceberg.lakehouse.{table_name} 
                GROUP BY region, event_type, date_trunc('hour', event_time)
                ORDER BY hour DESC, event_count DESC
                LIMIT 10
            """

            # Execute Trino query
            cmd = [
                "trino",
                "--server",
                "http://192.168.1.184:8084",
                "--catalog",
                "iceberg",
                "--schema",
                "lakehouse",
                "--output-format",
                "JSON",
                "--execute",
                trino_query,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                logger.info("✅ Trino query executed successfully")
                # Parse JSON results
                results = []
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

                return {
                    "engine": "Trino",
                    "query_status": "success",
                    "results": results,
                    "result_count": len(results),
                }
            else:
                logger.error(f"❌ Trino query failed: {result.stderr}")
                return {
                    "engine": "Trino",
                    "query_status": "failed",
                    "error": result.stderr,
                }

        except subprocess.TimeoutExpired:
            logger.error("❌ Trino query timeout")
            return {"engine": "Trino", "query_status": "timeout"}
        except Exception as e:
            logger.error(f"❌ Trino query error: {e}")
            return {"engine": "Trino", "query_status": "error", "error": str(e)}

    def monitor_streaming_health(
        self,
        table_name: str = "streaming_events",
        check_interval: int = 30,
        duration_minutes: int = 5,
    ) -> None:
        """Monitor streaming data health"""
        logger.info(
            f"🩺 Starting streaming health monitoring for {duration_minutes} minutes..."
        )

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        check_count = 0

        while time.time() < end_time:
            try:
                check_count += 1
                logger.info(f"📊 Health check #{check_count}")

                # Get current stats
                stats = self.get_streaming_table_stats(table_name)

                if "error" not in stats:
                    total_events = sum(r["event_count"] for r in stats["region_stats"])
                    total_users = sum(r["unique_users"] for r in stats["region_stats"])

                    logger.info(f"  📈 Total events: {total_events}")
                    logger.info(f"  👥 Total unique users: {total_users}")
                    logger.info(f"  🌍 Active regions: {stats['total_regions']}")

                    # Check for data freshness (recent hours should have data)
                    if stats["hourly_stats"]:
                        latest_hour = stats["hourly_stats"][-1]["timestamp"]
                        logger.info(f"  🕐 Latest data hour: {latest_hour}")

                else:
                    logger.warning(f"⚠️ Health check failed: {stats['error']}")

                # Sleep until next check
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("⚠️ Health monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")
                time.sleep(check_interval)

        logger.info("✅ Health monitoring completed")

    def generate_analytics_report(self, table_name: str = "streaming_events") -> None:
        """Generate comprehensive analytics report"""
        logger.info("📋 Generating comprehensive analytics report...")

        try:
            # Get Flink statistics
            flink_stats = self.get_streaming_table_stats(table_name)

            # Get Trino comparison
            trino_stats = self.query_with_trino(table_name)

            # Print report
            print("\n" + "=" * 80)
            print("📊 ICEBERG STREAMING ANALYTICS REPORT")
            print("=" * 80)

            if "error" not in flink_stats:
                print(f"\n🎯 TABLE: {flink_stats['table_name']}")
                print(f"🌍 REGIONS: {flink_stats['total_regions']}")
                print(f"⏰ TIME PERIODS: {flink_stats['total_hours']} hours")

                print("\n📈 REGION BREAKDOWN:")
                for region in flink_stats["region_stats"]:
                    print(
                        f"  {region['region']:12} | Events: {region['event_count']:6} | Users: {region['unique_users']:4} | Event Types: {region['unique_event_types']}"
                    )

                print("\n⏱️ RECENT HOURLY ACTIVITY:")
                for hour in flink_stats["hourly_stats"][-5:]:  # Last 5 hours
                    print(
                        f"  {hour['timestamp']} | Events: {hour['events']:6} | Users: {hour['unique_users']:4}"
                    )

            print(
                f"\n🔍 TRINO QUERY STATUS: {trino_stats.get('query_status', 'unknown')}"
            )
            if trino_stats.get("query_status") == "success":
                print(f"📊 TRINO RESULTS: {trino_stats.get('result_count', 0)} rows")

            print("\n" + "=" * 80)
            print("✅ Report generation completed!")

        except Exception as e:
            logger.error(f"❌ Report generation failed: {e}")


def main():
    """Main function for streaming analytics"""

    print("📊 Iceberg Streaming Analytics Starting...")
    print("=" * 50)

    try:
        # Create analytics instance
        analytics = IcebergStreamingAnalytics()

        # Setup analytics environment
        analytics.setup_analytics_environment()

        # Wait a moment for any streaming data to arrive
        logger.info("⏳ Waiting for streaming data (30 seconds)...")
        time.sleep(30)

        # Generate initial report
        analytics.generate_analytics_report()

        # Ask if user wants continuous monitoring
        monitor = input("\n🔄 Start continuous monitoring? (y/N): ").lower().strip()

        if monitor == "y":
            analytics.monitor_streaming_health(
                table_name="streaming_events", check_interval=30, duration_minutes=10
            )

        print("\n🎉 Analytics session completed!")

    except KeyboardInterrupt:
        logger.info("⚠️ Analytics interrupted by user")
    except Exception as e:
        logger.error(f"❌ Analytics failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
