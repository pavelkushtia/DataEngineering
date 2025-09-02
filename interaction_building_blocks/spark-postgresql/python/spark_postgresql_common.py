#!/usr/bin/env python3
"""
Spark-PostgreSQL Interaction Common Utilities

This module provides common utilities for Spark-PostgreSQL integration examples:
- Spark session configuration with PostgreSQL JDBC
- Database connection management and table operations
- ETL utilities for data transformation and loading
- Performance monitoring and optimization helpers
- Data quality validation and error handling

Requirements:
    pip install pyspark psycopg2-binary
"""

import sys
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import argparse
import logging

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql.functions import (
        col,
        when,
        lit,
        current_timestamp,
        date_format,
        regexp_replace,
        count,
        sum as spark_sum,
        avg,
        max as spark_max,
        min as spark_min,
        coalesce,
        isnan,
        isnull,
    )
    from pyspark.sql.types import (
        StructType,
        StructField,
        StringType,
        IntegerType,
        LongType,
        DoubleType,
        DecimalType,
        TimestampType,
        BooleanType,
        DateType,
    )
except ImportError:
    print("❌ Error: PySpark not found. Install with: pip install pyspark")
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("❌ Error: psycopg2 not found. Install with: pip install psycopg2-binary")
    sys.exit(1)


class SparkPostgreSQLConfig:
    """Configuration for Spark-PostgreSQL integration."""

    # Spark cluster configuration
    SPARK_MASTER = "spark://192.168.1.184:7077"
    SPARK_APP_NAME = "SparkPostgreSQLETL"

    # PostgreSQL configuration
    POSTGRESQL_HOST = "192.168.1.184"
    POSTGRESQL_PORT = 5432
    POSTGRESQL_DATABASE = "analytics_db"
    POSTGRESQL_USER = "dataeng"
    POSTGRESQL_PASSWORD = "password"

    # JDBC configuration
    POSTGRESQL_URL = (
        f"jdbc:postgresql://{POSTGRESQL_HOST}:{POSTGRESQL_PORT}/{POSTGRESQL_DATABASE}"
    )
    POSTGRESQL_DRIVER = "org.postgresql.Driver"

    # Spark configuration for PostgreSQL integration
    SPARK_CONF = {
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        "spark.sql.adaptive.skewJoin.enabled": "true",
        "spark.executor.memory": "2g",
        "spark.executor.cores": "2",
        "spark.sql.shuffle.partitions": "200",
    }

    # JDBC connection properties
    JDBC_PROPERTIES = {
        "user": POSTGRESQL_USER,
        "password": POSTGRESQL_PASSWORD,
        "driver": POSTGRESQL_DRIVER,
        "stringtype": "unspecified",  # Handle VARCHAR properly
        "batchsize": "10000",  # Batch size for inserts
        "reWriteBatchedInserts": "true",  # PostgreSQL optimization
    }

    # Default batch processing settings
    DEFAULT_BATCH_SIZE = 10000
    DEFAULT_PARTITIONS = 4


class SparkPostgreSQLSession:
    """Enhanced Spark session manager with PostgreSQL integration."""

    def __init__(self, config: SparkPostgreSQLConfig = None, app_name: str = None):
        self.config = config or SparkPostgreSQLConfig()
        self.spark = None
        self.app_name = app_name or self.config.SPARK_APP_NAME

    def create_spark_session(self, master: str = None) -> SparkSession:
        """Create Spark session with PostgreSQL JDBC configuration."""
        master = master or self.config.SPARK_MASTER

        builder = SparkSession.builder.appName(self.app_name).master(master)

        # Add Spark configuration
        for key, value in self.config.SPARK_CONF.items():
            builder = builder.config(key, value)

        # Add PostgreSQL JDBC driver (in production, add via --jars or --packages)
        # builder = builder.config("spark.jars.packages", "org.postgresql:postgresql:42.7.2")

        self.spark = builder.getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")  # Reduce log verbosity

        print(f"🚀 Created Spark session: {self.app_name}")
        print(f"   Master: {master}")
        print(f"   Executor Memory: {self.config.SPARK_CONF['spark.executor.memory']}")
        print(f"   Executor Cores: {self.config.SPARK_CONF['spark.executor.cores']}")

        return self.spark

    def get_spark_session(self) -> SparkSession:
        """Get existing Spark session or create new one."""
        if not self.spark:
            self.create_spark_session()
        return self.spark

    def close_session(self):
        """Close Spark session."""
        if self.spark:
            self.spark.stop()
            print("🔌 Spark session closed")


class PostgreSQLTableManager:
    """Manage PostgreSQL tables for Spark integration."""

    def __init__(self, config: SparkPostgreSQLConfig = None):
        self.config = config or SparkPostgreSQLConfig()
        self.connection = None

    def get_connection(self):
        """Get PostgreSQL connection."""
        if not self.connection:
            self.connection = psycopg2.connect(
                host=self.config.POSTGRESQL_HOST,
                port=self.config.POSTGRESQL_PORT,
                database=self.config.POSTGRESQL_DATABASE,
                user=self.config.POSTGRESQL_USER,
                password=self.config.POSTGRESQL_PASSWORD,
            )
        return self.connection

    def create_table_from_spark_schema(
        self, table_name: str, spark_df: DataFrame, drop_existing: bool = False
    ):
        """Create PostgreSQL table based on Spark DataFrame schema."""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if drop_existing:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                print(f"🗑️ Dropped existing table: {table_name}")

            # Convert Spark schema to PostgreSQL DDL
            ddl = self._spark_schema_to_postgresql_ddl(table_name, spark_df.schema)
            cursor.execute(ddl)
            conn.commit()

            print(f"✅ Created table: {table_name}")

        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to create table {table_name}: {e}")
            raise
        finally:
            cursor.close()

    def _spark_schema_to_postgresql_ddl(
        self, table_name: str, schema: StructType
    ) -> str:
        """Convert Spark schema to PostgreSQL DDL."""
        columns = []

        for field in schema.fields:
            pg_type = self._spark_type_to_postgresql_type(field.dataType)
            nullable = "NULL" if field.nullable else "NOT NULL"
            columns.append(f"{field.name} {pg_type} {nullable}")

        ddl = f"""
        CREATE TABLE {table_name} (
            {','.join(columns)},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        return ddl

    def _spark_type_to_postgresql_type(self, spark_type) -> str:
        """Convert Spark data type to PostgreSQL type."""
        type_mapping = {
            StringType(): "TEXT",
            IntegerType(): "INTEGER",
            LongType(): "BIGINT",
            DoubleType(): "DOUBLE PRECISION",
            BooleanType(): "BOOLEAN",
            TimestampType(): "TIMESTAMP",
            DateType(): "DATE",
            DecimalType(): "DECIMAL(10,2)",
        }

        return type_mapping.get(type(spark_type), "TEXT")

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about PostgreSQL table."""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            # Get table metadata
            cursor.execute(
                """
                SELECT 
                    column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """,
                (table_name,),
            )

            columns = cursor.fetchall()

            # Get row count
            cursor.execute(f"SELECT COUNT(*) as row_count FROM {table_name}")
            row_count = cursor.fetchone()["row_count"]

            return {
                "table_name": table_name,
                "columns": columns,
                "row_count": row_count,
            }

        except Exception as e:
            print(f"⚠️ Could not get table info for {table_name}: {e}")
            return {}
        finally:
            cursor.close()

    def close_connection(self):
        """Close PostgreSQL connection."""
        if self.connection:
            self.connection.close()


class SparkETLUtilities:
    """Utilities for Spark ETL operations with PostgreSQL."""

    def __init__(self, spark_session: SparkPostgreSQLSession):
        self.spark_session = spark_session
        self.spark = spark_session.get_spark_session()
        self.config = spark_session.config

    def read_from_postgresql(
        self, table_name: str, partition_column: str = None, num_partitions: int = None
    ) -> DataFrame:
        """Read data from PostgreSQL table into Spark DataFrame."""
        reader = (
            self.spark.read.format("jdbc")
            .option("url", self.config.POSTGRESQL_URL)
            .option("dbtable", table_name)
            .option("user", self.config.POSTGRESQL_USER)
            .option("password", self.config.POSTGRESQL_PASSWORD)
            .option("driver", self.config.POSTGRESQL_DRIVER)
        )

        # Add partitioning for large tables
        if partition_column and num_partitions:
            # Get min/max values for partitioning
            bounds_query = f"(SELECT MIN({partition_column}), MAX({partition_column}) FROM {table_name}) AS bounds"
            reader = (
                reader.option("partitionColumn", partition_column)
                .option("numPartitions", str(num_partitions))
                .option("dbtable", bounds_query)
            )

        df = reader.load()
        print(f"📖 Read {df.count()} rows from PostgreSQL table: {table_name}")

        return df

    def write_to_postgresql(
        self,
        df: DataFrame,
        table_name: str,
        mode: str = "append",
        batch_size: int = None,
    ):
        """Write Spark DataFrame to PostgreSQL table."""
        batch_size = batch_size or self.config.DEFAULT_BATCH_SIZE

        writer = (
            df.write.format("jdbc")
            .option("url", self.config.POSTGRESQL_URL)
            .option("dbtable", table_name)
            .option("user", self.config.POSTGRESQL_USER)
            .option("password", self.config.POSTGRESQL_PASSWORD)
            .option("driver", self.config.POSTGRESQL_DRIVER)
            .option("batchsize", str(batch_size))
            .option("rewriteBatchedStatements", "true")
            .mode(mode)
        )

        start_time = time.time()
        writer.save()
        write_time = time.time() - start_time

        print(f"📝 Wrote {df.count()} rows to PostgreSQL table: {table_name}")
        print(f"   Write time: {write_time:.2f}s")
        print(f"   Write mode: {mode}")
        print(f"   Batch size: {batch_size}")

    def create_sample_data(self, num_records: int = 10000) -> DataFrame:
        """Create sample data for testing."""
        from pyspark.sql.functions import rand, randn, when, round as spark_round

        # Generate sample data
        df = (
            self.spark.range(num_records)
            .withColumn("user_id", (col("id") % 1000 + 1))
            .withColumn("product_id", (col("id") % 100 + 1))
            .withColumn("amount", spark_round(rand() * 500 + 10, 2))
            .withColumn("quantity", (rand() * 5 + 1).cast("int"))
            .withColumn(
                "category",
                when(col("product_id") % 4 == 0, "Electronics")
                .when(col("product_id") % 4 == 1, "Books")
                .when(col("product_id") % 4 == 2, "Clothing")
                .otherwise("Home"),
            )
            .withColumn(
                "transaction_date",
                (current_timestamp() - (rand() * 30).cast("int") * 86400).cast(
                    "timestamp"
                ),
            )
            .withColumn("status", when(rand() > 0.1, "completed").otherwise("pending"))
            .drop("id")
        )

        print(f"🎲 Generated {num_records} sample records")
        return df

    def perform_data_quality_checks(
        self, df: DataFrame, table_name: str = ""
    ) -> Dict[str, Any]:
        """Perform data quality checks on DataFrame."""
        print(
            f"🔍 Performing data quality checks{' for ' + table_name if table_name else ''}..."
        )

        total_rows = df.count()

        quality_report = {
            "table_name": table_name,
            "total_rows": total_rows,
            "columns": len(df.columns),
            "null_counts": {},
            "duplicate_rows": 0,
            "summary_stats": {},
        }

        # Check for nulls in each column
        for column in df.columns:
            null_count = df.filter(col(column).isNull()).count()
            quality_report["null_counts"][column] = {
                "count": null_count,
                "percentage": (null_count / total_rows * 100) if total_rows > 0 else 0,
            }

        # Check for duplicates (if reasonable dataset size)
        if total_rows < 100000:
            distinct_rows = df.distinct().count()
            quality_report["duplicate_rows"] = total_rows - distinct_rows

        # Basic statistics for numeric columns
        numeric_columns = [
            f.name
            for f in df.schema.fields
            if f.dataType in [IntegerType(), LongType(), DoubleType()]
        ]

        if numeric_columns:
            stats_df = df.select(numeric_columns).describe()
            quality_report["summary_stats"] = {
                row["summary"]: {
                    col_name: row[col_name] for col_name in numeric_columns
                }
                for row in stats_df.collect()
            }

        print("📊 Data Quality Report:")
        print(f"   Total Rows: {quality_report['total_rows']:,}")
        print(f"   Columns: {quality_report['columns']}")
        print(f"   Duplicate Rows: {quality_report['duplicate_rows']}")

        # Show null percentages
        for col_name, null_info in quality_report["null_counts"].items():
            if null_info["percentage"] > 0:
                print(f"   {col_name}: {null_info['percentage']:.1f}% null")

        return quality_report

    def optimize_dataframe(
        self,
        df: DataFrame,
        partition_columns: List[str] = None,
        target_partitions: int = None,
    ) -> DataFrame:
        """Optimize DataFrame for better performance."""
        target_partitions = target_partitions or self.config.DEFAULT_PARTITIONS

        # Repartition if needed
        if df.rdd.getNumPartitions() != target_partitions:
            if partition_columns:
                df = df.repartition(target_partitions, *partition_columns)
                print(
                    f"📊 Repartitioned data by {partition_columns} into {target_partitions} partitions"
                )
            else:
                df = df.repartition(target_partitions)
                print(f"📊 Repartitioned data into {target_partitions} partitions")

        # Cache if DataFrame will be reused
        df.cache()
        print("💾 DataFrame cached for reuse")

        return df


def parse_common_args() -> argparse.ArgumentParser:
    """Create argument parser with common Spark-PostgreSQL options."""
    parser = argparse.ArgumentParser(
        description="Spark-PostgreSQL Interaction Application"
    )

    parser.add_argument(
        "--master", default=SparkPostgreSQLConfig.SPARK_MASTER, help="Spark master URL"
    )
    parser.add_argument(
        "--app-name",
        default=SparkPostgreSQLConfig.SPARK_APP_NAME,
        help="Spark application name",
    )

    parser.add_argument(
        "--postgresql-host",
        default=SparkPostgreSQLConfig.POSTGRESQL_HOST,
        help="PostgreSQL host",
    )
    parser.add_argument(
        "--postgresql-port",
        type=int,
        default=SparkPostgreSQLConfig.POSTGRESQL_PORT,
        help="PostgreSQL port",
    )
    parser.add_argument(
        "--postgresql-database",
        default=SparkPostgreSQLConfig.POSTGRESQL_DATABASE,
        help="PostgreSQL database name",
    )
    parser.add_argument(
        "--postgresql-user",
        default=SparkPostgreSQLConfig.POSTGRESQL_USER,
        help="PostgreSQL user",
    )
    parser.add_argument(
        "--postgresql-password",
        default=SparkPostgreSQLConfig.POSTGRESQL_PASSWORD,
        help="PostgreSQL password",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=SparkPostgreSQLConfig.DEFAULT_BATCH_SIZE,
        help="Batch size for database operations",
    )
    parser.add_argument(
        "--partitions",
        type=int,
        default=SparkPostgreSQLConfig.DEFAULT_PARTITIONS,
        help="Number of partitions for processing",
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
    print("🧪 Testing Spark-PostgreSQL common utilities...")

    try:
        # Test configuration
        config = SparkPostgreSQLConfig()
        print(f"✅ Spark Master: {config.SPARK_MASTER}")
        print(f"✅ PostgreSQL URL: {config.POSTGRESQL_URL}")

        # Test Spark session creation
        spark_session = SparkPostgreSQLSession(config)
        spark = spark_session.create_spark_session()
        print(f"✅ Created Spark session: {spark.sparkContext.appName}")

        # Test sample data generation
        etl_utils = SparkETLUtilities(spark_session)
        sample_df = etl_utils.create_sample_data(100)
        print(f"✅ Created sample DataFrame with {sample_df.count()} rows")

        # Test data quality checks
        quality_report = etl_utils.perform_data_quality_checks(sample_df, "sample_data")
        print(f"✅ Generated data quality report")

        # Cleanup
        spark_session.close_session()
        print("✅ All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
