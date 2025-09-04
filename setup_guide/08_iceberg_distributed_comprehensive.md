# Apache Iceberg Distributed & Comprehensive Setup Guide

## Overview
This guide sets up Apache Iceberg with distributed HDFS storage and integrations with all engines in your cluster: Spark, Trino, Flink, Python analytics, and multi-engine coordination patterns.

## Prerequisites

✅ **Must be completed first:**
- [06_hdfs_distributed_setup.md](./06_hdfs_distributed_setup.md) - HDFS cluster running
- [07_hive_metastore_setup.md](./07_hive_metastore_setup.md) - Hive Metastore service
- All cluster components operational (Spark, Flink, Trino, Kafka, PostgreSQL)

## Phase 1: Core Distributed Setup

### Step 1: Update Iceberg for HDFS Storage

**⚠️ IMPORTANT: Run on ALL THREE NODES (cpu-node1, cpu-node2, worker-node3)**

**Why all nodes?**
- Spark workers on all nodes need Iceberg runtime JARs
- Flink TaskManagers on all nodes need Iceberg runtime JARs  
- All nodes may run Iceberg clients for distributed processing

#### **Commands to run on each node:**

**On cpu-node1 (192.168.1.184):**
```bash
# Create new distributed workspace
mkdir -p /home/sanzad/iceberg-distributed
cd /home/sanzad/iceberg-distributed

# Create required directories
mkdir -p libs conf scripts notebooks logs
```

**On cpu-node2 (192.168.1.187):**
```bash
# SSH into cpu-node2 and repeat setup
ssh sanzad@192.168.1.187
mkdir -p /home/sanzad/iceberg-distributed
cd /home/sanzad/iceberg-distributed
mkdir -p libs conf scripts notebooks logs
```

**On worker-node3 (192.168.1.190):**
```bash
# SSH into worker-node3 and repeat setup  
ssh sanzad@192.168.1.190
mkdir -p /home/sanzad/iceberg-distributed
cd /home/sanzad/iceberg-distributed
mkdir -p libs conf scripts notebooks logs
```

#### **Download JAR files on ALL THREE NODES:**

**Run these commands on each node (cpu-node1, cpu-node2, worker-node3):**
```bash
cd /home/sanzad/iceberg-distributed/libs

# Core Iceberg JARs
wget https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.4.3/iceberg-spark-runtime-3.5_2.12-1.4.3.jar
wget https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-1.19/1.9.2/iceberg-flink-runtime-1.19-1.9.2.jar

# Hadoop integration
wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client/3.3.6/hadoop-client-3.3.6.jar

# Database drivers
wget https://jdbc.postgresql.org/download/postgresql-42.7.2.jar

# AWS SDK (for future S3 compatibility)
wget https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar
```

**Verify downloads on each node:**
```bash
ls -la /home/sanzad/iceberg-distributed/libs/
# Should show 5 JAR files on each node
```

### Step 2: Distributed Spark Configuration

**⚠️ IMPORTANT: Configuration needed on ALL THREE NODES**

**Why all nodes?** All nodes run Spark workers that need Iceberg configuration for distributed processing.

#### **Create configuration file on each node:**

**On cpu-node1 (192.168.1.184):**
```bash
nano /home/sanzad/iceberg-distributed/conf/spark-iceberg-distributed.conf
```

**On cpu-node2 (192.168.1.187):**
```bash
ssh sanzad@192.168.1.187
nano /home/sanzad/iceberg-distributed/conf/spark-iceberg-distributed.conf
```

**On worker-node3 (192.168.1.190):**
```bash
ssh sanzad@192.168.1.190
nano /home/sanzad/iceberg-distributed/conf/spark-iceberg-distributed.conf
```

#### **Configuration content (same on all nodes):**

```properties
# Spark configuration for distributed Iceberg
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions

# HDFS configuration
spark.hadoop.fs.defaultFS=hdfs://192.168.1.184:9000

# Iceberg catalog configuration - HDFS-based
spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.iceberg.type=hadoop
spark.sql.catalog.iceberg.warehouse=hdfs://192.168.1.184:9000/lakehouse/iceberg

# JDBC catalog for better metadata management
spark.sql.catalog.iceberg_jdbc=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.iceberg_jdbc.type=jdbc
spark.sql.catalog.iceberg_jdbc.uri=jdbc:postgresql://192.168.1.184:5432/iceberg_catalog
spark.sql.catalog.iceberg_jdbc.jdbc.user=dataeng
spark.sql.catalog.iceberg_jdbc.jdbc.password=password
spark.sql.catalog.iceberg_jdbc.warehouse=hdfs://192.168.1.184:9000/lakehouse/iceberg

# Hive catalog (using your Trino's Hive Metastore)
spark.sql.catalog.iceberg_hive=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.iceberg_hive.type=hive
spark.sql.catalog.iceberg_hive.uri=thrift://192.168.1.184:9083
spark.sql.catalog.iceberg_hive.warehouse=hdfs://192.168.1.184:9000/lakehouse/iceberg

# Default catalog
spark.sql.defaultCatalog=iceberg_hive

# Performance optimization for distributed setup
spark.serializer=org.apache.spark.serializer.KryoSerializer
spark.sql.adaptive.enabled=true
spark.sql.adaptive.coalescePartitions.enabled=true
spark.sql.adaptive.coalescePartitions.minPartitionNum=2
spark.sql.adaptive.coalescePartitions.initialPartitionNum=8

# Optimize for your 3-node cluster
spark.sql.shuffle.partitions=12
spark.dynamicAllocation.enabled=true
spark.dynamicAllocation.minExecutors=1
spark.dynamicAllocation.maxExecutors=6

# Iceberg-specific optimizations
spark.sql.iceberg.vectorization.enabled=true
spark.sql.iceberg.handle-timestamp-without-timezone=true

# HDFS client settings
spark.hadoop.dfs.client.use.datanode.hostname=false
spark.hadoop.dfs.client.cache.drop.behind.reads=true
```

### Create distributed launch script:
```bash
nano /home/sanzad/iceberg-distributed/start-spark-iceberg-distributed.sh
```

```bash
#!/bin/bash

ICEBERG_HOME="/home/sanzad/iceberg-distributed"
SPARK_HOME="/home/spark/spark"
HADOOP_HOME="/opt/hadoop/current"

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop

# Build classpath with all required JARs
ICEBERG_JARS="${ICEBERG_HOME}/libs/iceberg-spark-runtime-3.5_2.12-1.4.3.jar"
HADOOP_JARS="${ICEBERG_HOME}/libs/hadoop-client-3.3.6.jar"
POSTGRES_JAR="${ICEBERG_HOME}/libs/postgresql-42.7.2.jar"
AWS_JARS="${ICEBERG_HOME}/libs/aws-java-sdk-bundle-1.12.367.jar"

ALL_JARS="${ICEBERG_JARS},${HADOOP_JARS},${POSTGRES_JAR},${AWS_JARS}"

echo "Starting Spark with distributed Iceberg..."
echo "HDFS Warehouse: hdfs://192.168.1.184:9000/lakehouse/iceberg"

# Start Spark with distributed configuration
$SPARK_HOME/bin/spark-shell \
    --master spark://192.168.1.184:7077 \
    --jars $ALL_JARS \
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
    --conf spark.sql.catalog.iceberg_hive=org.apache.iceberg.spark.SparkCatalog \
    --conf spark.sql.catalog.iceberg_hive.type=hive \
    --conf spark.sql.catalog.iceberg_hive.uri=thrift://192.168.1.184:9083 \
    --conf spark.sql.catalog.iceberg_hive.warehouse=hdfs://192.168.1.184:9000/lakehouse/iceberg \
    --conf spark.sql.defaultCatalog=iceberg_hive \
    --conf spark.hadoop.fs.defaultFS=hdfs://192.168.1.184:9000 \
    --conf spark.eventLog.dir=hdfs://192.168.1.184:9000/lakehouse/spark/event-logs \
    --conf spark.sql.adaptive.enabled=true \
    --conf spark.sql.shuffle.partitions=12 \
    --executor-memory 2g \
    --driver-memory 1g \
    --executor-cores 2 \
    --total-executor-cores 6
```

```bash
chmod +x /home/sanzad/iceberg-distributed/start-spark-iceberg-distributed.sh

# Allow spark user to access the script directory
chmod 755 /home/sanzad
```

### Step 3: Test Distributed Setup

**⚠️ IMPORTANT: Run test on COORDINATOR NODE (cpu-node1)**

**Why cpu-node1?** The Spark Master runs on cpu-node1, and it will coordinate distributed processing across all worker nodes.

#### **Test commands to run on cpu-node1 (192.168.1.184):**

```bash
# Start distributed Spark session (run as spark user)
sudo su - spark -c "cd /home/sanzad/iceberg-distributed && ./start-spark-iceberg-distributed.sh"
```

```scala
// Test distributed Iceberg setup
import org.apache.spark.sql.functions._

// Create namespace
spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg_hive.lakehouse")

// Create distributed table with partitioning
spark.sql("""
CREATE TABLE iceberg_hive.lakehouse.distributed_events (
  event_id bigint,
  user_id bigint,
  event_type string,
  event_time timestamp,
  properties map<string, string>,
  region string,
  year int,
  month int,
  day int
) USING iceberg
PARTITIONED BY (region, year, month)
""")

// Generate sample data across multiple partitions
import java.sql.Timestamp
import scala.util.Random

val regions = Array("us-east", "us-west", "eu-central", "asia-pacific")
val eventTypes = Array("page_view", "click", "purchase", "signup", "logout")

val sampleData = (1 to 10000).map { i =>
  val region = regions(Random.nextInt(regions.length))
  val eventType = eventTypes(Random.nextInt(eventTypes.length))
  val eventTime = Timestamp.valueOf(f"2024-${Random.nextInt(12) + 1}%02d-${Random.nextInt(28) + 1}%02d ${Random.nextInt(24)}%02d:${Random.nextInt(60)}%02d:00")
  val properties = Map("source" -> "web", "device" -> "mobile")
  
  (i.toLong, Random.nextLong(), eventType, eventTime, properties, region, 2024, eventTime.getMonth + 1, eventTime.getDate)
}

val eventsDF = sampleData.toDF("event_id", "user_id", "event_type", "event_time", "properties", "region", "year", "month", "day")

// Write to distributed Iceberg table
eventsDF.write
  .format("iceberg")
  .mode("append")
  .saveAsTable("iceberg_hive.lakehouse.distributed_events")

// Verify data distribution
spark.sql("SELECT region, count(*) FROM iceberg_hive.lakehouse.distributed_events GROUP BY region").show()

// Check files are distributed across HDFS
spark.sql("SELECT * FROM iceberg_hive.lakehouse.distributed_events.files").show()
```

## Phase 2: Trino Integration

### Step 4: Configure Trino for Iceberg

**⚠️ IMPORTANT: Configure Trino ONLY on COORDINATOR NODE (cpu-node1)**

**Why cpu-node1 only?** Trino coordinator runs only on cpu-node1, and worker nodes connect to it.

#### **Update Trino configuration on cpu-node1 (192.168.1.184):**

```bash
# Update existing iceberg.properties
sudo nano /home/trino/trino/etc/catalog/iceberg.properties
```

```properties
connector.name=iceberg
hive.metastore.uri=thrift://192.168.1.184:9083
iceberg.catalog.type=hive

# HDFS configuration
hive.hdfs.authentication.type=NONE
hive.hdfs.impersonation.enabled=false

# Performance optimizations
iceberg.file-format=PARQUET
iceberg.compression-codec=ZSTD
iceberg.max-partitions-per-query=1000

# Enable advanced features
iceberg.delete-as-join-rewrite-enabled=true
iceberg.expire-snapshots.enabled=true
iceberg.remove-orphan-files.enabled=true
```

### Test Trino integration:
```bash
# Connect to Trino
trino --server http://192.168.1.184:8080 --catalog iceberg --schema lakehouse
```

```sql
-- Query distributed Iceberg table from Trino
SELECT region, event_type, count(*) as event_count 
FROM distributed_events 
GROUP BY region, event_type 
ORDER BY event_count DESC;

-- Test time travel
SELECT count(*) FROM distributed_events FOR VERSION AS OF 1;

-- Analyze table statistics
ANALYZE TABLE distributed_events;

-- Show table properties
SHOW CREATE TABLE distributed_events;
```

## Phase 3: Flink Streaming Integration

### Step 5: Configure Flink for Iceberg Streaming

**⚠️ IMPORTANT: Configure Flink on ALL THREE NODES**

**Why all nodes?**
- JobManager on cpu-node1 needs configuration
- TaskManagers on all nodes (cpu-node2, worker-node3) need JARs for distributed processing

#### **Copy JARs on all nodes:**

**On cpu-node1 (192.168.1.184):**
```bash
# Copy Iceberg Flink JAR to Flink lib directory
sudo cp /home/sanzad/iceberg-distributed/libs/iceberg-flink-runtime-1.19-1.9.2.jar /home/flink/flink/lib/
sudo cp /home/sanzad/iceberg-distributed/libs/hadoop-client-3.3.6.jar /home/flink/flink/lib/
```

**On cpu-node2 (192.168.1.187):**
```bash
ssh sanzad@192.168.1.187
sudo cp /home/sanzad/iceberg-distributed/libs/iceberg-flink-runtime-1.19-1.9.2.jar /home/flink/flink/lib/
sudo cp /home/sanzad/iceberg-distributed/libs/hadoop-client-3.3.6.jar /home/flink/flink/lib/
```

**On worker-node3 (192.168.1.190):**
```bash
ssh sanzad@192.168.1.190
sudo cp /home/sanzad/iceberg-distributed/libs/iceberg-flink-runtime-1.19-1.9.2.jar /home/flink/flink/lib/
sudo cp /home/sanzad/iceberg-distributed/libs/hadoop-client-3.3.6.jar /home/flink/flink/lib/
```

#### **Update Flink configuration (ONLY on cpu-node1 - JobManager):**

```bash
# Update Flink configuration
sudo nano /home/flink/flink/conf/flink-conf.yaml
```

Add these lines:
```yaml
# HDFS configuration
fs.hdfs.hadoop.conf.dir: /opt/hadoop/current/etc/hadoop

# Iceberg configuration
table.sql-dialect: default
```

### Create Flink streaming to Iceberg script:
```bash
nano /home/sanzad/iceberg-distributed/scripts/flink_kafka_to_iceberg.py
```

```python
from pyflink.table import EnvironmentSettings, TableEnvironment
from pyflink.table.expressions import col
import os

def kafka_to_iceberg_streaming():
    # Set up Flink environment
    env_settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    table_env = TableEnvironment.create(env_settings)
    
    # Add Iceberg JAR
    iceberg_jar = "file:///home/flink/flink/lib/iceberg-flink-runtime-1.19-1.9.2.jar"
    table_env.get_config().get_configuration().set_string("pipeline.jars", iceberg_jar)
    
    # Configure Iceberg catalog in Flink
    table_env.execute_sql("""
        CREATE CATALOG iceberg_catalog WITH (
            'type' = 'iceberg',
            'catalog-type' = 'hive',
            'uri' = 'thrift://192.168.1.184:9083',
            'warehouse' = 'hdfs://192.168.1.184:9000/lakehouse/iceberg'
        )
    """)
    
    table_env.execute_sql("USE CATALOG iceberg_catalog")
    table_env.execute_sql("USE lakehouse")
    
    # Create Kafka source table
    table_env.execute_sql("""
        CREATE TABLE kafka_events (
            event_id BIGINT,
            user_id BIGINT,
            event_type STRING,
            event_time TIMESTAMP(3),
            properties MAP<STRING, STRING>,
            region STRING,
            processing_time AS PROCTIME(),
            event_time_attr AS event_time,
            WATERMARK FOR event_time_attr AS event_time_attr - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'user-events',
            'properties.bootstrap.servers' = '192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092',
            'properties.group.id' = 'iceberg-sink',
            'format' = 'json',
            'scan.startup.mode' = 'latest-offset'
        )
    """)
    
    # Create Iceberg sink table
    table_env.execute_sql("""
        CREATE TABLE IF NOT EXISTS streaming_events (
            event_id BIGINT,
            user_id BIGINT,
            event_type STRING,
            event_time TIMESTAMP(3),
            properties MAP<STRING, STRING>,
            region STRING,
            year INT,
            month INT,
            day INT,
            hour INT
        ) PARTITIONED BY (region, year, month, day, hour)
        WITH (
            'connector' = 'iceberg',
            'catalog-name' = 'iceberg_catalog',
            'database-name' = 'lakehouse',
            'table-name' = 'streaming_events'
        )
    """)
    
    # Stream from Kafka to Iceberg with transformations
    table_env.execute_sql("""
        INSERT INTO streaming_events
        SELECT 
            event_id,
            user_id,
            event_type,
            event_time,
            properties,
            region,
            EXTRACT(YEAR FROM event_time) as year,
            EXTRACT(MONTH FROM event_time) as month,
            EXTRACT(DAY FROM event_time) as day,
            EXTRACT(HOUR FROM event_time) as hour
        FROM kafka_events
    """)

if __name__ == "__main__":
    kafka_to_iceberg_streaming()
```

## Phase 4: Python Analytics Integration

### Step 6: Enhanced Python Setup

**⚠️ IMPORTANT: Install on COORDINATOR NODE (cpu-node1) for analysis**

**Why cpu-node1?** Python analytics typically run from the coordinator node where you have direct access to cluster management and can efficiently coordinate distributed queries.

#### **Install Python dependencies on cpu-node1 (192.168.1.184):**

```bash
# Install PyIceberg and additional dependencies
pip3 install pyiceberg[hive,s3fs,adlfs,gcs] duckdb pandas pyarrow polars
```

### Create comprehensive Python analytics script:
```bash
nano /home/sanzad/iceberg-distributed/scripts/python_analytics_comprehensive.py
```

```python
import os
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import duckdb
from pyiceberg.catalog.hive import HiveCatalog
from pyiceberg.expressions import GreaterThanOrEqual, LessThan, And
from datetime import datetime, timedelta

class IcebergAnalytics:
    def __init__(self):
        # Initialize Hive catalog
        self.catalog = HiveCatalog(
            name="hive_catalog",
            uri="thrift://192.168.1.184:9083"
        )
        
        # Initialize DuckDB for local analytics
        self.duck_conn = duckdb.connect()
        
        # Enable HDFS support in DuckDB
        self.duck_conn.execute("INSTALL httpfs")
        self.duck_conn.execute("LOAD httpfs")
    
    def get_table(self, namespace: str, table_name: str):
        """Get Iceberg table reference"""
        return self.catalog.load_table(f"{namespace}.{table_name}")
    
    def query_with_predicate_pushdown(self, table_name: str, start_date: str, end_date: str, region: str = None):
        """Demonstrate predicate pushdown for efficient querying"""
        table = self.get_table("lakehouse", table_name)
        
        # Build filter expressions
        filters = [
            GreaterThanOrEqual("event_time", start_date),
            LessThan("event_time", end_date)
        ]
        
        if region:
            from pyiceberg.expressions import EqualTo
            filters.append(EqualTo("region", region))
        
        # Combine filters
        combined_filter = And(*filters) if len(filters) > 1 else filters[0]
        
        # Scan with predicate pushdown
        scan = table.scan(row_filter=combined_filter)
        
        # Convert to pandas for analysis
        return scan.to_pandas()
    
    def time_travel_analysis(self, table_name: str):
        """Demonstrate time travel capabilities"""
        table = self.get_table("lakehouse", table_name)
        
        # Get table history
        history = []
        for snapshot in table.metadata.snapshots:
            history.append({
                'snapshot_id': snapshot.snapshot_id,
                'timestamp': datetime.fromtimestamp(snapshot.timestamp_ms / 1000),
                'operation': snapshot.summary.get('operation', 'unknown'),
                'added_files': snapshot.summary.get('added-data-files', 0),
                'total_records': snapshot.summary.get('total-records', 0)
            })
        
        return pd.DataFrame(history)
    
    def duckdb_federated_query(self):
        """Use DuckDB to query Iceberg data alongside other sources"""
        
        # Query PostgreSQL data
        pg_query = """
        SELECT region, SUM(amount) as total_sales
        FROM postgres_scan('host=192.168.1.184 port=5432 dbname=analytics_db user=dataeng password=password', 'public', 'sales_data')
        GROUP BY region
        """
        
        pg_data = self.duck_conn.execute(pg_query).fetchdf()
        
        # Query Iceberg data (using HDFS)
        iceberg_query = """
        SELECT region, COUNT(*) as event_count
        FROM read_parquet('hdfs://192.168.1.184:9000/lakehouse/iceberg/lakehouse/distributed_events/data/*.parquet')
        GROUP BY region
        """
        
        try:
            iceberg_data = self.duck_conn.execute(iceberg_query).fetchdf()
            
            # Join datasets
            result = pd.merge(pg_data, iceberg_data, on='region', how='outer')
            return result
        except Exception as e:
            print(f"HDFS access not available in DuckDB: {e}")
            return pg_data
    
    def polars_performance_analysis(self, table_name: str):
        """Use Polars for high-performance analytics"""
        try:
            import polars as pl
            
            table = self.get_table("lakehouse", table_name)
            
            # Scan to Arrow table first
            arrow_table = table.scan().to_arrow()
            
            # Convert to Polars for high-performance operations
            df = pl.from_arrow(arrow_table)
            
            # Perform complex aggregations
            result = (
                df
                .filter(pl.col("event_time") >= datetime(2024, 1, 1))
                .group_by(["region", "event_type"])
                .agg([
                    pl.count().alias("event_count"),
                    pl.col("user_id").n_unique().alias("unique_users"),
                    pl.col("event_time").min().alias("first_event"),
                    pl.col("event_time").max().alias("last_event")
                ])
                .sort("event_count", descending=True)
            )
            
            return result.to_pandas()
            
        except ImportError:
            print("Polars not available, falling back to pandas")
            return None
    
    def advanced_time_series_analysis(self, table_name: str):
        """Advanced time series analysis with Iceberg"""
        table = self.get_table("lakehouse", table_name)
        
        # Get recent data
        yesterday = datetime.now() - timedelta(days=1)
        scan = table.scan(row_filter=GreaterThanOrEqual("event_time", yesterday.isoformat()))
        df = scan.to_pandas()
        
        if df.empty:
            return None
        
        # Time series aggregations
        df['event_time'] = pd.to_datetime(df['event_time'])
        df.set_index('event_time', inplace=True)
        
        # Hourly aggregations by region and event type
        hourly_stats = (
            df.groupby(['region', 'event_type'])
            .resample('1H')
            .agg({
                'event_id': 'count',
                'user_id': 'nunique'
            })
            .rename(columns={'event_id': 'event_count', 'user_id': 'unique_users'})
            .reset_index()
        )
        
        return hourly_stats

def main():
    analytics = IcebergAnalytics()
    
    print("=== Iceberg Python Analytics Demo ===\n")
    
    # 1. Predicate pushdown query
    print("1. Querying with predicate pushdown...")
    try:
        recent_data = analytics.query_with_predicate_pushdown(
            "distributed_events", 
            "2024-01-01", 
            "2024-12-31", 
            region="us-east"
        )
        print(f"Retrieved {len(recent_data)} records for us-east region")
        print(recent_data.head())
    except Exception as e:
        print(f"Error in predicate pushdown: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 2. Time travel analysis
    print("2. Time travel analysis...")
    try:
        history = analytics.time_travel_analysis("distributed_events")
        print("Table history:")
        print(history)
    except Exception as e:
        print(f"Error in time travel: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 3. DuckDB federated query
    print("3. DuckDB federated analysis...")
    try:
        federated_result = analytics.duckdb_federated_query()
        print("Federated query result:")
        print(federated_result)
    except Exception as e:
        print(f"Error in federated query: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # 4. Polars performance analysis
    print("4. Polars high-performance analysis...")
    try:
        polars_result = analytics.polars_performance_analysis("distributed_events")
        if polars_result is not None:
            print("Polars analysis result:")
            print(polars_result.head(10))
    except Exception as e:
        print(f"Error in Polars analysis: {e}")

if __name__ == "__main__":
    main()
```

## Phase 5: Multi-Engine Coordination

### Step 7: Multi-Engine Coordination Patterns

**⚠️ IMPORTANT: Create orchestration script on COORDINATOR NODE (cpu-node1)**

**Why cpu-node1?** Multi-engine coordination requires orchestrating Spark, Trino, and Flink from a central location with access to all cluster services.

#### **Create coordination script on cpu-node1 (192.168.1.184):**

```bash
nano /home/sanzad/iceberg-distributed/scripts/multi_engine_coordination.py
```

```python
from pyspark.sql import SparkSession
import subprocess
import time
import threading

class MultiEngineCoordinator:
    def __init__(self):
        self.spark = self._create_spark_session()
        
    def _create_spark_session(self):
        return SparkSession.builder \
            .appName("MultiEngineCoordinator") \
            .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
            .config("spark.sql.catalog.iceberg_hive", "org.apache.iceberg.spark.SparkCatalog") \
            .config("spark.sql.catalog.iceberg_hive.type", "hive") \
            .config("spark.sql.catalog.iceberg_hive.uri", "thrift://192.168.1.184:9083") \
            .config("spark.sql.catalog.iceberg_hive.warehouse", "hdfs://192.168.1.184:9000/lakehouse/iceberg") \
            .config("spark.sql.defaultCatalog", "iceberg_hive") \
            .config("spark.hadoop.fs.defaultFS", "hdfs://192.168.1.184:9000") \
            .getOrCreate()
    
    def create_table_for_multi_engine_access(self):
        """Create table optimized for multi-engine access"""
        self.spark.sql("""
            CREATE TABLE IF NOT EXISTS iceberg_hive.lakehouse.multi_engine_table (
                transaction_id bigint,
                user_id bigint,
                product_id string,
                amount decimal(10,2),
                transaction_time timestamp,
                region string,
                channel string,
                year int,
                month int,
                day int
            ) USING iceberg
            PARTITIONED BY (region, year, month)
            TBLPROPERTIES (
                'write.format.default' = 'parquet',
                'write.parquet.compression-codec' = 'zstd',
                'read.parquet.vectorization.enabled' = 'true',
                'write.distribution-mode' = 'hash',
                'write.fanout.enabled' = 'true'
            )
        """)
        
        print("✓ Multi-engine table created with optimized properties")
    
    def spark_batch_processing(self):
        """Spark batch processing simulation"""
        print("🔄 Starting Spark batch processing...")
        
        # Generate batch data
        batch_data = self.spark.range(1000, 2000).select(
            col("id").alias("transaction_id"),
            (col("id") % 100).alias("user_id"),
            concat(lit("PROD_"), col("id")).alias("product_id"),
            (rand() * 1000).cast("decimal(10,2)").alias("amount"),
            current_timestamp().alias("transaction_time"),
            when(col("id") % 4 == 0, "us-east")
            .when(col("id") % 4 == 1, "us-west")
            .when(col("id") % 4 == 2, "eu-central")
            .otherwise("asia-pacific").alias("region"),
            when(col("id") % 3 == 0, "web")
            .when(col("id") % 3 == 1, "mobile")
            .otherwise("api").alias("channel"),
            year(current_timestamp()).alias("year"),
            month(current_timestamp()).alias("month"),
            dayofmonth(current_timestamp()).alias("day")
        )
        
        # Write to Iceberg table
        batch_data.write \
            .format("iceberg") \
            .mode("append") \
            .saveAsTable("iceberg_hive.lakehouse.multi_engine_table")
        
        print("✓ Spark batch processing completed")
    
    def schedule_table_maintenance(self):
        """Schedule regular table maintenance"""
        print("🔧 Running table maintenance...")
        
        # Expire old snapshots (keep last 10)
        self.spark.sql("""
            CALL iceberg_hive.system.expire_snapshots(
                'lakehouse.multi_engine_table', 
                older_than => current_timestamp() - interval '7' day,
                retain_last => 10
            )
        """)
        
        # Compact data files
        self.spark.sql("""
            CALL iceberg_hive.system.rewrite_data_files(
                'lakehouse.multi_engine_table'
            )
        """)
        
        # Remove orphan files
        self.spark.sql("""
            CALL iceberg_hive.system.remove_orphan_files(
                table => 'lakehouse.multi_engine_table'
            )
        """)
        
        print("✓ Table maintenance completed")
    
    def execute_trino_query(self, query: str):
        """Execute query via Trino CLI"""
        cmd = [
            "trino",
            "--server", "http://192.168.1.184:8080",
            "--catalog", "iceberg",
            "--schema", "lakehouse",
            "--execute", query
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            return result.stdout
        except subprocess.TimeoutExpired:
            return "Query timeout"
        except Exception as e:
            return f"Error: {e}"
    
    def demonstrate_concurrent_access(self):
        """Demonstrate concurrent access from multiple engines"""
        print("🔄 Demonstrating concurrent multi-engine access...")
        
        def spark_query():
            """Spark query thread"""
            print("  Spark: Running aggregation query...")
            result = self.spark.sql("""
                SELECT region, channel, 
                       count(*) as transaction_count,
                       avg(amount) as avg_amount
                FROM iceberg_hive.lakehouse.multi_engine_table 
                GROUP BY region, channel
                ORDER BY transaction_count DESC
            """).collect()
            print(f"  Spark: Query completed, {len(result)} rows")
        
        def trino_query():
            """Trino query thread"""
            print("  Trino: Running time-based analysis...")
            query = """
                SELECT date_trunc('hour', transaction_time) as hour,
                       count(*) as hourly_transactions,
                       sum(amount) as hourly_revenue
                FROM multi_engine_table 
                WHERE transaction_time >= current_timestamp - interval '1' day
                GROUP BY date_trunc('hour', transaction_time)
                ORDER BY hour DESC
                LIMIT 24
            """
            result = self.execute_trino_query(query)
            print(f"  Trino: Query completed")
        
        # Execute queries concurrently
        spark_thread = threading.Thread(target=spark_query)
        trino_thread = threading.Thread(target=trino_query)
        
        spark_thread.start()
        trino_thread.start()
        
        spark_thread.join()
        trino_thread.join()
        
        print("✓ Concurrent access demonstration completed")
    
    def monitor_table_health(self):
        """Monitor table health across engines"""
        print("📊 Monitoring table health...")
        
        # Get table statistics
        stats = self.spark.sql("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT region) as unique_regions,
                COUNT(DISTINCT user_id) as unique_users,
                MIN(transaction_time) as earliest_transaction,
                MAX(transaction_time) as latest_transaction,
                SUM(amount) as total_amount
            FROM iceberg_hive.lakehouse.multi_engine_table
        """).collect()[0]
        
        print(f"  Total records: {stats['total_records']:,}")
        print(f"  Unique regions: {stats['unique_regions']}")
        print(f"  Unique users: {stats['unique_users']:,}")
        print(f"  Date range: {stats['earliest_transaction']} to {stats['latest_transaction']}")
        print(f"  Total amount: ${stats['total_amount']:,.2f}")
        
        # Check file distribution
        files_info = self.spark.sql("""
            SELECT 
                COUNT(*) as file_count,
                SUM(file_size_in_bytes) as total_size_bytes,
                AVG(file_size_in_bytes) as avg_file_size_bytes,
                MIN(file_size_in_bytes) as min_file_size_bytes,
                MAX(file_size_in_bytes) as max_file_size_bytes
            FROM iceberg_hive.lakehouse.multi_engine_table.files
        """).collect()[0]
        
        print(f"  File count: {files_info['file_count']}")
        print(f"  Total size: {files_info['total_size_bytes'] / (1024*1024):.2f} MB")
        print(f"  Average file size: {files_info['avg_file_size_bytes'] / (1024*1024):.2f} MB")
        
        if files_info['avg_file_size_bytes'] < 10 * 1024 * 1024:  # Less than 10MB
            print(f"  ⚠️  Warning: Small files detected, consider running OPTIMIZE.")

def main():
    coordinator = MultiEngineCoordinator()
    
    print("=== Multi-Engine Iceberg Coordination Demo ===\n")
    
    # 1. Create optimized table
    coordinator.create_table_for_multi_engine_access()
    print()
    
    # 2. Spark batch processing
    coordinator.spark_batch_processing()
    print()
    
    # 3. Demonstrate concurrent access
    coordinator.demonstrate_concurrent_access()
    print()
    
    # 4. Monitor table health
    coordinator.monitor_table_health()
    print()
    
    # 5. Schedule maintenance
    coordinator.schedule_table_maintenance()
    
    print("\n🎉 Multi-engine coordination demo completed!")

if __name__ == "__main__":
    main()
```

```bash
chmod +x /home/sanzad/iceberg-distributed/scripts/*.py
```

This comprehensive setup gives you:

**✅ Distributed Storage**: HDFS across all 3 nodes with fault tolerance
**✅ Multi-Engine Support**: Spark, Trino, Flink all accessing same distributed data  
**✅ Advanced Analytics**: Python, DuckDB, Polars integration
**✅ Concurrent Access**: Multiple engines working simultaneously
**✅ Performance Optimization**: Partitioning, compaction, predicate pushdown
**✅ Operational Excellence**: Monitoring, maintenance, health checks

---

# Appendix: Local Iceberg Setup Guide

> **Note**: This local setup is for learning and development purposes. For production use, always use the distributed setup above.

## Overview
Apache Iceberg will be set up locally for lakehouse functionality, integrated with Spark for data processing and analytics. This setup allows you to experiment with Iceberg's features like schema evolution, time travel, and ACID transactions.

## What is Apache Iceberg?
Apache Iceberg is an open table format for huge analytic datasets that brings the reliability and simplicity of SQL tables to big data, while making it possible for engines like Spark, Trino, Flink, Presto, and Hive to safely work with the same tables, at the same time.

## Prerequisites
- Java 8 or Java 11
- Apache Spark 3.3+ (from our Spark cluster setup)
- At least 4GB RAM
- At least 10GB free disk space for data and metadata

## Key Benefits of Local Setup
1. **Learning and Experimentation**: Perfect for understanding Iceberg concepts
2. **Development Environment**: Test applications before deploying to cluster
3. **Prototyping**: Quick setup for proof-of-concepts
4. **Integration Testing**: Test with multiple engines locally

## Step 1: Local Directory Setup

```bash
# Create iceberg workspace
mkdir -p /home/sanzad/iceberg-local
cd /home/sanzad/iceberg-local

# Create required directories
mkdir -p warehouse/tables
mkdir -p metadata
mkdir -p logs
mkdir -p data
mkdir -p notebooks
mkdir -p scripts
```

## Step 2: Download Iceberg JAR Files

```bash
cd /home/sanzad/iceberg-local
mkdir -p libs

# Download Iceberg runtime for Spark
wget -P libs https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.4.3/iceberg-spark-runtime-3.5_2.12-1.4.3.jar

# Download AWS SDK (if planning to use S3)
wget -P libs https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar
wget -P libs https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar

# Download PostgreSQL driver (for catalog backend)
wget -P libs https://jdbc.postgresql.org/download/postgresql-42.7.2.jar
```

## Step 3: Configure Spark for Iceberg

### Create Spark configuration:
```bash
nano /home/sanzad/iceberg-local/spark-iceberg.conf
```

```properties
# Spark configuration for Iceberg
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions

# Iceberg catalog configuration - Hadoop catalog (file-based)
spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.iceberg.type=hadoop
spark.sql.catalog.iceberg.warehouse=file:///home/sanzad/iceberg-local/warehouse

# Alternative: Hive catalog (if you have Hive Metastore)
# spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog
# spark.sql.catalog.iceberg.type=hive
# spark.sql.catalog.iceberg.uri=thrift://localhost:9083

# JDBC catalog (using PostgreSQL)
spark.sql.catalog.iceberg_pg=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.iceberg_pg.type=jdbc
spark.sql.catalog.iceberg_pg.uri=jdbc:postgresql://192.168.1.184:5432/iceberg_catalog
spark.sql.catalog.iceberg_pg.jdbc.user=dataeng
spark.sql.catalog.iceberg_pg.jdbc.password=password
spark.sql.catalog.iceberg_pg.warehouse=file:///home/sanzad/iceberg-local/warehouse

# Default catalog
spark.sql.defaultCatalog=iceberg

# Serialization
spark.serializer=org.apache.spark.serializer.KryoSerializer

# Adaptive query execution
spark.sql.adaptive.enabled=true
spark.sql.adaptive.coalescePartitions.enabled=true
```

### Create launch script:
```bash
nano /home/sanzad/iceberg-local/start-spark-iceberg.sh
```

```bash
#!/bin/bash

ICEBERG_HOME="/home/sanzad/iceberg-local"
SPARK_HOME="/home/spark/spark"  # Adjust to your Spark installation

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# Add Iceberg JARs to Spark classpath
ICEBERG_JARS="${ICEBERG_HOME}/libs/iceberg-spark-runtime-3.5_2.12-1.4.3.jar"
POSTGRES_JAR="${ICEBERG_HOME}/libs/postgresql-42.7.2.jar"
AWS_JARS="${ICEBERG_HOME}/libs/aws-java-sdk-bundle-1.12.367.jar,${ICEBERG_HOME}/libs/hadoop-aws-3.3.4.jar"

# Start Spark with Iceberg
$SPARK_HOME/bin/spark-shell \
    --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.4.3 \
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
    --conf spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog \
    --conf spark.sql.catalog.iceberg.type=hadoop \
    --conf spark.sql.catalog.iceberg.warehouse=file:///home/sanzad/iceberg-local/warehouse \
    --conf spark.sql.defaultCatalog=iceberg \
    --conf spark.eventLog.dir=file:///home/sanzad/iceberg-local/logs \
    --conf spark.sql.adaptive.enabled=true
```

Make it executable:
```bash
chmod +x /home/sanzad/iceberg-local/start-spark-iceberg.sh
```

## Step 4: Create PostgreSQL Catalog Database

```bash
# Connect to PostgreSQL
psql -U dataeng -h 192.168.1.184 -d postgres

# Create Iceberg catalog database
CREATE DATABASE iceberg_catalog;

# Create user for Iceberg
CREATE USER iceberg_user WITH PASSWORD 'iceberg_pass';
GRANT ALL PRIVILEGES ON DATABASE iceberg_catalog TO iceberg_user;

\q
```

## Step 5: Basic Iceberg Operations

### Start Spark with Iceberg:
```bash
# Run as spark user to access Spark binaries
sudo su - spark -c "cd /home/sanzad/iceberg-local && ./start-spark-iceberg.sh"
```

### Create your first Iceberg table:
```scala
// Create a namespace (schema)
spark.sql("CREATE NAMESPACE iceberg.nyc")

// Create an Iceberg table
spark.sql("""
CREATE TABLE iceberg.nyc.taxis (
  vendor_id bigint,
  trip_id bigint, 
  trip_distance float,
  fare_amount double,
  store_and_fwd_flag string,
  pickup_datetime timestamp,
  dropoff_datetime timestamp,
  passenger_count int,
  pickup_location string,
  dropoff_location string
) USING iceberg
PARTITIONED BY (days(pickup_datetime))
""")

// Show tables
spark.sql("SHOW TABLES IN iceberg.nyc").show()
```

### Insert sample data:
```scala
import java.sql.Timestamp
import spark.implicits._

// Create sample data
val sampleData = Seq(
  (1L, 1001L, 2.5f, 9.95, "N", Timestamp.valueOf("2023-01-01 10:30:00"), Timestamp.valueOf("2023-01-01 10:45:00"), 1, "Manhattan", "Brooklyn"),
  (2L, 1002L, 1.8f, 7.50, "N", Timestamp.valueOf("2023-01-01 11:00:00"), Timestamp.valueOf("2023-01-01 11:12:00"), 2, "Queens", "Manhattan"),
  (1L, 1003L, 3.2f, 12.80, "Y", Timestamp.valueOf("2023-01-01 12:15:00"), Timestamp.valueOf("2023-01-01 12:35:00"), 1, "Brooklyn", "Queens"),
  (2L, 1004L, 0.9f, 5.25, "N", Timestamp.valueOf("2023-01-02 09:20:00"), Timestamp.valueOf("2023-01-02 09:28:00"), 1, "Manhattan", "Manhattan")
).toDF("vendor_id", "trip_id", "trip_distance", "fare_amount", "store_and_fwd_flag", 
       "pickup_datetime", "dropoff_datetime", "passenger_count", "pickup_location", "dropoff_location")

// Insert data into Iceberg table
sampleData.writeTo("iceberg.nyc.taxis").append()

// Query the table
spark.sql("SELECT * FROM iceberg.nyc.taxis").show()
```

## Step 6: Iceberg Advanced Features

### Schema Evolution:
```scala
// Add a new column
spark.sql("ALTER TABLE iceberg.nyc.taxis ADD COLUMN tip_amount double")

// Insert data with new column
val newData = Seq(
  (3L, 1005L, 4.1f, 15.75, "N", Timestamp.valueOf("2023-01-03 14:30:00"), Timestamp.valueOf("2023-01-03 14:55:00"), 2, "Bronx", "Manhattan", 3.15)
).toDF("vendor_id", "trip_id", "trip_distance", "fare_amount", "store_and_fwd_flag", 
       "pickup_datetime", "dropoff_datetime", "passenger_count", "pickup_location", "dropoff_location", "tip_amount")

newData.writeTo("iceberg.nyc.taxis").append()

// Query with new column
spark.sql("SELECT vendor_id, trip_distance, fare_amount, tip_amount FROM iceberg.nyc.taxis").show()
```

### Time Travel:
```scala
// Show table history
spark.sql("SELECT * FROM iceberg.nyc.taxis.history").show()

// Show snapshots
spark.sql("SELECT * FROM iceberg.nyc.taxis.snapshots").show()

// Query table at specific timestamp
spark.sql("SELECT * FROM iceberg.nyc.taxis TIMESTAMP AS OF '2023-01-01 12:00:00'").show()

// Query table at specific snapshot
val snapshotId = spark.sql("SELECT snapshot_id FROM iceberg.nyc.taxis.snapshots LIMIT 1").collect()(0)(0)
spark.sql(s"SELECT * FROM iceberg.nyc.taxis VERSION AS OF $snapshotId").show()
```

### Maintenance Operations:
```scala
// Expire old snapshots (cleanup)
spark.sql("CALL iceberg.system.expire_snapshots('iceberg.nyc.taxis', TIMESTAMP '2023-01-01 00:00:00')")

// Rewrite data files (compaction)
spark.sql("CALL iceberg.system.rewrite_data_files('iceberg.nyc.taxis')")

// Remove orphan files
spark.sql("CALL iceberg.system.remove_orphan_files(table => 'iceberg.nyc.taxis')")
```

For the complete local setup guide including integration examples, Python setup, Jupyter notebooks, testing, and maintenance, see the full content in the original `06_iceberg_local_setup.md` file.

## Next Steps for Production

1. **Distributed Setup**: Move to distributed file systems (HDFS, S3)
2. **Catalog Management**: Implement proper catalog with Hive Metastore or Nessie
3. **Multi-Engine**: Integrate with Trino, Flink for broader ecosystem
4. **Monitoring**: Implement comprehensive monitoring and alerting
5. **Security**: Add authentication, authorization, and encryption

This local setup provides a solid foundation for learning Iceberg concepts and can easily be extended for production use cases.

