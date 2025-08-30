# Apache Iceberg Local Setup Guide

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
cd /home/sanzad/iceberg-local
./start-spark-iceberg.sh
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

## Step 7: Integration Examples

### Reading from CSV and writing to Iceberg:
```scala
// Read CSV file
val csvData = spark.read
  .option("header", "true")
  .option("inferSchema", "true")
  .csv("file:///path/to/your/data.csv")

// Write to Iceberg table
csvData.writeTo("iceberg.nyc.csv_data").createOrReplace()
```

### Reading from PostgreSQL and writing to Iceberg:
```scala
// Read from PostgreSQL
val pgData = spark.read
  .format("jdbc")
  .option("url", "jdbc:postgresql://192.168.1.184:5432/analytics_db")
  .option("dbtable", "sales_data")
  .option("user", "dataeng")
  .option("password", "password")
  .load()

// Write to Iceberg with partitioning
pgData.writeTo("iceberg.analytics.sales")
  .partitionedBy("region", "year")
  .createOrReplace()
```

### Streaming with Kafka to Iceberg:
```scala
import org.apache.spark.sql.streaming.Trigger

// Read from Kafka
val kafkaStream = spark
  .readStream
  .format("kafka")
  .option("kafka.bootstrap.servers", "192.168.1.184:9092")
  .option("subscribe", "user-events")
  .load()

// Parse JSON and write to Iceberg
val parsedStream = kafkaStream
  .selectExpr("CAST(value AS STRING) as json_data")
  .select(from_json($"json_data", schema).as("data"))
  .select("data.*")

parsedStream
  .writeStream
  .format("iceberg")
  .outputMode("append")
  .trigger(Trigger.ProcessingTime("1 minute"))
  .option("path", "iceberg.events.user_activity")
  .option("checkpointLocation", "/home/sanzad/iceberg-local/checkpoints/user_events")
  .start()
```

## Step 8: Python Integration (PyIceberg)

### Install PyIceberg:
```bash
pip3 install pyiceberg[hive,s3fs,adlfs,gcs]
```

### Python example:
```python
# Create Python script
nano /home/sanzad/iceberg-local/scripts/pyiceberg_example.py
```

```python
from pyiceberg.catalog import load_catalog
import pyarrow as pa

# Configure catalog
catalog = load_catalog(
    name="local",
    **{
        "type": "rest",
        "uri": "http://localhost:8181",
    }
)

# Alternative: File-based catalog
# from pyiceberg.catalog.hive import HiveCatalog
# catalog = HiveCatalog("thrift://localhost:9083")

# Create table
schema = pa.schema([
    pa.field("id", pa.int64()),
    pa.field("name", pa.string()),
    pa.field("age", pa.int32()),
])

# Create namespace and table
try:
    catalog.create_namespace("python_demo")
except:
    pass  # Namespace might already exist

table = catalog.create_table("python_demo.users", schema=schema)

# Insert data
data = [
    {"id": 1, "name": "Alice", "age": 25},
    {"id": 2, "name": "Bob", "age": 30},
    {"id": 3, "name": "Charlie", "age": 35},
]

table.append([pa.Table.from_pylist(data)])

# Query data
df = table.scan().to_pandas()
print(df)
```

## Step 9: Jupyter Notebook Setup

### Install Jupyter with Spark:
```bash
pip3 install jupyter pyspark pandas matplotlib seaborn
```

### Create Jupyter kernel for Iceberg:
```bash
nano /home/sanzad/iceberg-local/jupyter-iceberg.py
```

```python
import os
import sys
from pyspark.sql import SparkSession

# Set environment variables
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"
os.environ["SPARK_HOME"] = "/home/spark/spark"

# Create Spark session with Iceberg
spark = SparkSession.builder \
    .appName("Iceberg-Jupyter") \
    .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
    .config("spark.sql.catalog.iceberg", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.iceberg.type", "hadoop") \
    .config("spark.sql.catalog.iceberg.warehouse", "file:///home/sanzad/iceberg-local/warehouse") \
    .config("spark.sql.defaultCatalog", "iceberg") \
    .config("spark.jars.packages", "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.4.3") \
    .getOrCreate()

print("Spark session with Iceberg initialized successfully!")
print(f"Spark version: {spark.version}")
print(f"Available catalogs: {spark.catalog.listCatalogs()}")
```

### Create sample notebook:
```bash
nano /home/sanzad/iceberg-local/notebooks/iceberg_demo.ipynb
```

```json
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "exec(open('/home/sanzad/iceberg-local/jupyter-iceberg.py').read())"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Create sample table\n",
    "spark.sql(\"\"\"\n",
    "CREATE OR REPLACE TABLE iceberg.demo.sample_table (\n",
    "    id bigint,\n",
    "    name string,\n",
    "    age int,\n",
    "    created_at timestamp\n",
    ") USING iceberg\n",
    "PARTITIONED BY (days(created_at))\n",
    "\"\"\")"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

### Start Jupyter:
```bash
cd /home/sanzad/iceberg-local/notebooks
jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser
```

## Step 10: Testing and Validation

### Create comprehensive test script:
```bash
nano /home/sanzad/iceberg-local/scripts/test_iceberg.sh
```

```bash
#!/bin/bash

echo "Testing Iceberg Setup..."

# Start Spark and run tests
$SPARK_HOME/bin/spark-submit \
    --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.4.3 \
    --conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
    --conf spark.sql.catalog.iceberg=org.apache.iceberg.spark.SparkCatalog \
    --conf spark.sql.catalog.iceberg.type=hadoop \
    --conf spark.sql.catalog.iceberg.warehouse=file:///home/sanzad/iceberg-local/warehouse \
    --conf spark.sql.defaultCatalog=iceberg \
    /home/sanzad/iceberg-local/scripts/iceberg_test.py

echo "Iceberg test completed!"
```

```bash
# Create test Python script
nano /home/sanzad/iceberg-local/scripts/iceberg_test.py
```

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
import sys

def test_iceberg():
    spark = SparkSession.builder.appName("IcebergTest").getOrCreate()
    
    try:
        # Test 1: Create namespace
        spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.test")
        print("✓ Namespace creation successful")
        
        # Test 2: Create table
        spark.sql("""
            CREATE OR REPLACE TABLE iceberg.test.sample (
                id bigint,
                data string,
                ts timestamp
            ) USING iceberg
        """)
        print("✓ Table creation successful")
        
        # Test 3: Insert data
        test_data = [(1, "test1", "2023-01-01 10:00:00"), 
                     (2, "test2", "2023-01-01 11:00:00")]
        df = spark.createDataFrame(test_data, ["id", "data", "ts"])
        df.writeTo("iceberg.test.sample").append()
        print("✓ Data insertion successful")
        
        # Test 4: Query data
        result = spark.sql("SELECT COUNT(*) as cnt FROM iceberg.test.sample").collect()[0][0]
        assert result == 2, f"Expected 2 rows, got {result}"
        print("✓ Data query successful")
        
        # Test 5: Schema evolution
        spark.sql("ALTER TABLE iceberg.test.sample ADD COLUMN new_col string")
        print("✓ Schema evolution successful")
        
        print("\n🎉 All tests passed! Iceberg is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)
    
    finally:
        spark.stop()

if __name__ == "__main__":
    test_iceberg()
```

Make scripts executable:
```bash
chmod +x /home/sanzad/iceberg-local/scripts/test_iceberg.sh
chmod +x /home/sanzad/iceberg-local/scripts/iceberg_test.py
```

Run the test:
```bash
/home/sanzad/iceberg-local/scripts/test_iceberg.sh
```

## Step 11: Performance Tips for Local Development

### Optimize for local development:
```properties
# Add to spark-iceberg.conf
spark.sql.adaptive.enabled=true
spark.sql.adaptive.coalescePartitions.enabled=true
spark.sql.adaptive.coalescePartitions.minPartitionNum=1
spark.sql.adaptive.coalescePartitions.initialPartitionNum=4

# Reduce shuffle partitions for small datasets
spark.sql.shuffle.partitions=4

# Enable dynamic allocation
spark.dynamicAllocation.enabled=true
spark.dynamicAllocation.minExecutors=1
spark.dynamicAllocation.maxExecutors=2
```

### Local storage optimization:
```bash
# Create data organization script
nano /home/sanzad/iceberg-local/scripts/optimize_tables.py
```

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("IcebergOptimizer").getOrCreate()

# List all tables
tables = spark.sql("SHOW TABLES IN iceberg").collect()

for table in tables:
    table_name = f"iceberg.{table.namespace}.{table.tableName}"
    
    # Compact small files
    spark.sql(f"CALL iceberg.system.rewrite_data_files('{table_name}')")
    
    # Remove old snapshots (keep last 5)
    spark.sql(f"CALL iceberg.system.expire_snapshots('{table_name}', retain_last => 5)")
    
    print(f"Optimized table: {table_name}")

spark.stop()
```

## Step 12: Monitoring and Maintenance

### Create monitoring script:
```bash
nano /home/sanzad/iceberg-local/scripts/monitor_iceberg.py
```

```python
import os
import json
from pathlib import Path

def monitor_warehouse():
    warehouse_path = Path("/home/sanzad/iceberg-local/warehouse")
    
    print("=== Iceberg Warehouse Status ===")
    print(f"Warehouse location: {warehouse_path}")
    
    # Get warehouse size
    total_size = sum(f.stat().st_size for f in warehouse_path.rglob('*') if f.is_file())
    print(f"Total warehouse size: {total_size / (1024*1024):.2f} MB")
    
    # List namespaces
    namespaces = [d.name for d in warehouse_path.iterdir() if d.is_dir()]
    print(f"Namespaces: {namespaces}")
    
    # List tables in each namespace
    for namespace in namespaces:
        namespace_path = warehouse_path / namespace
        tables = [d.name for d in namespace_path.iterdir() if d.is_dir()]
        print(f"  {namespace}: {len(tables)} tables - {tables}")
    
    print("\n=== Recent Activity ===")
    # Show recent metadata files
    metadata_files = list(warehouse_path.rglob("*.metadata.json"))
    metadata_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for meta_file in metadata_files[:5]:
        mtime = meta_file.stat().st_mtime
        import time
        print(f"  {meta_file.relative_to(warehouse_path)}: {time.ctime(mtime)}")

if __name__ == "__main__":
    monitor_warehouse()
```

### Create cleanup script:
```bash
nano /home/sanzad/iceberg-local/scripts/cleanup_iceberg.sh
```

```bash
#!/bin/bash

WAREHOUSE_DIR="/home/sanzad/iceberg-local/warehouse"
LOGS_DIR="/home/sanzad/iceberg-local/logs"

echo "Cleaning up Iceberg local environment..."

# Clean old log files (older than 7 days)
find $LOGS_DIR -name "*.log" -mtime +7 -delete
echo "✓ Cleaned old log files"

# Remove temporary Spark files
find /tmp -name "spark-*" -user $(whoami) -mtime +1 -exec rm -rf {} \; 2>/dev/null
echo "✓ Cleaned temporary Spark files"

# Get warehouse size before cleanup
BEFORE_SIZE=$(du -sh $WAREHOUSE_DIR | cut -f1)

# Clean orphan files (this requires running through Spark)
echo "✓ Warehouse size before cleanup: $BEFORE_SIZE"

echo "Cleanup completed!"
```

Make it executable:
```bash
chmod +x /home/sanzad/iceberg-local/scripts/cleanup_iceberg.sh
chmod +x /home/sanzad/iceberg-local/scripts/monitor_iceberg.py
```

## Key Learning Outcomes

After completing this local Iceberg setup, you'll understand:

1. **Table Format Concepts**: Hidden partitioning, schema evolution, time travel
2. **ACID Transactions**: How Iceberg provides consistency for big data
3. **Metadata Management**: How Iceberg tracks table changes efficiently
4. **Integration Patterns**: Working with Spark, Python, and other engines
5. **Performance Optimization**: Compaction, partitioning, file sizing
6. **Operational Aspects**: Maintenance, monitoring, troubleshooting

## Next Steps for Production

1. **Distributed Setup**: Move to distributed file systems (HDFS, S3)
2. **Catalog Management**: Implement proper catalog with Hive Metastore or Nessie
3. **Multi-Engine**: Integrate with Trino, Flink for broader ecosystem
4. **Monitoring**: Implement comprehensive monitoring and alerting
5. **Security**: Add authentication, authorization, and encryption

This local setup provides a solid foundation for learning Iceberg concepts and can easily be extended for production use cases.
