# Delta Lake Local Setup Guide

## Overview
Delta Lake will be set up locally for lakehouse functionality, integrated with Spark for data processing and analytics. This setup allows you to experiment with Delta Lake's features like ACID transactions, schema enforcement, time travel, and data versioning.

## What is Delta Lake?
Delta Lake is an open-source storage framework that enables building a Lakehouse architecture with compute engines including Spark, PrestoDB, Flink, Trino, and Hive and APIs for Scala, Java, Rust, Ruby, and Python.

## Prerequisites
- Java 8 or Java 11
- Apache Spark 3.3+ (from our Spark cluster setup)
- Python 3.7+
- At least 4GB RAM
- At least 10GB free disk space for data and logs

## Key Benefits of Local Setup
1. **Learning Environment**: Perfect for understanding Delta Lake concepts
2. **Development & Testing**: Test applications before deploying to cluster
3. **Prototyping**: Quick setup for proof-of-concepts
4. **Data Quality Experimentation**: Test schema enforcement and constraints

## Step 1: Local Directory Setup

```bash
# Create Delta Lake workspace
mkdir -p /home/sanzad/deltalake-local
cd /home/sanzad/deltalake-local

# Create required directories
mkdir -p delta-tables
mkdir -p checkpoints
mkdir -p logs
mkdir -p data
mkdir -p notebooks
mkdir -p scripts
mkdir -p temp
```

## Step 2: Download Delta Lake JAR Files

```bash
cd /home/sanzad/deltalake-local
mkdir -p libs

# Download Delta Lake core for Spark
wget -P libs https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.4.0/delta-core_2.12-2.4.0.jar

# Download Delta Lake storage
wget -P libs https://repo1.maven.org/maven2/io/delta/delta-storage/2.4.0/delta-storage-2.4.0.jar

# Download additional dependencies (if needed)
wget -P libs https://repo1.maven.org/maven2/org/antlr/antlr4-runtime/4.8/antlr4-runtime-4.8.jar
```

## Step 3: Configure Spark for Delta Lake

### Create Spark configuration:
```bash
nano /home/sanzad/deltalake-local/spark-delta.conf
```

```properties
# Spark configuration for Delta Lake
spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension
spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog

# Serialization
spark.serializer=org.apache.spark.serializer.KryoSerializer

# Adaptive query execution
spark.sql.adaptive.enabled=true
spark.sql.adaptive.coalescePartitions.enabled=true

# Delta Lake specific configurations
spark.databricks.delta.retentionDurationCheck.enabled=false
spark.databricks.delta.vacuum.parallelDelete.enabled=true

# Memory settings for local development
spark.driver.memory=2g
spark.executor.memory=2g
spark.sql.shuffle.partitions=4

# Checkpoint and log settings
spark.sql.streaming.checkpointLocation=/home/sanzad/deltalake-local/checkpoints
spark.eventLog.enabled=true
spark.eventLog.dir=/home/sanzad/deltalake-local/logs
```

### Create launch script:
```bash
nano /home/sanzad/deltalake-local/start-spark-delta.sh
```

```bash
#!/bin/bash

DELTA_HOME="/home/sanzad/deltalake-local"
SPARK_HOME="/home/spark/spark"  # Adjust to your Spark installation

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

# Start Spark with Delta Lake
$SPARK_HOME/bin/spark-shell \
    --packages io.delta:delta-core_2.12:2.4.0 \
    --conf "spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension" \
    --conf "spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog" \
    --conf "spark.sql.adaptive.enabled=true" \
    --conf "spark.sql.adaptive.coalescePartitions.enabled=true" \
    --conf "spark.databricks.delta.retentionDurationCheck.enabled=false" \
    --conf "spark.eventLog.dir=file://$DELTA_HOME/logs" \
    --conf "spark.sql.shuffle.partitions=4"
```

### Create PySpark launch script:
```bash
nano /home/sanzad/deltalake-local/start-pyspark-delta.sh
```

```bash
#!/bin/bash

DELTA_HOME="/home/sanzad/deltalake-local"
SPARK_HOME="/home/spark/spark"

export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export PYSPARK_PYTHON=python3

# Start PySpark with Delta Lake
$SPARK_HOME/bin/pyspark \
    --packages io.delta:delta-core_2.12:2.4.0 \
    --conf "spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension" \
    --conf "spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog" \
    --conf "spark.sql.adaptive.enabled=true" \
    --conf "spark.databricks.delta.retentionDurationCheck.enabled=false"
```

Make scripts executable:
```bash
chmod +x /home/sanzad/deltalake-local/start-spark-delta.sh
chmod +x /home/sanzad/deltalake-local/start-pyspark-delta.sh
```

## Step 4: Install Delta Lake Python Package

```bash
# Install delta-spark for Python
pip3 install delta-spark==2.4.0 pyspark==3.5.0

# Install additional dependencies
pip3 install pandas numpy matplotlib seaborn jupyter
```

## Step 5: Basic Delta Lake Operations

### Start Spark with Delta Lake:
```bash
cd /home/sanzad/deltalake-local
./start-spark-delta.sh
```

### Create your first Delta table:
```scala
import org.apache.spark.sql.types._
import org.apache.spark.sql.functions._

// Create sample data
val data = Seq(
  (1, "Alice", 25, "Engineering", 75000, "2023-01-15"),
  (2, "Bob", 30, "Marketing", 65000, "2023-01-16"),
  (3, "Charlie", 35, "Engineering", 85000, "2023-01-17"),
  (4, "Diana", 28, "Sales", 70000, "2023-01-18"),
  (5, "Eve", 32, "Engineering", 90000, "2023-01-19")
)

val df = data.toDF("id", "name", "age", "department", "salary", "hire_date")

// Write as Delta table
df.write
  .format("delta")
  .mode("overwrite")
  .save("/home/sanzad/deltalake-local/delta-tables/employees")

// Create table reference
spark.sql("""
  CREATE TABLE employees 
  USING DELTA 
  LOCATION '/home/sanzad/deltalake-local/delta-tables/employees'
""")

// Query the table
spark.sql("SELECT * FROM employees").show()
```

### Update and merge operations:
```scala
import io.delta.tables._

// Load Delta table
val deltaTable = DeltaTable.forPath(spark, "/home/sanzad/deltalake-local/delta-tables/employees")

// Update operation
deltaTable.update(
  condition = expr("department = 'Engineering'"),
  set = Map("salary" -> expr("salary * 1.1"))  // 10% raise for engineering
)

// Merge operation (UPSERT)
val newEmployees = Seq(
  (6, "Frank", 29, "Engineering", 80000, "2023-01-20"),
  (2, "Bob", 30, "Marketing", 68000, "2023-01-16")  // Updated salary
).toDF("id", "name", "age", "department", "salary", "hire_date")

deltaTable.as("target")
  .merge(newEmployees.as("source"), "target.id = source.id")
  .whenMatched()
  .updateAll()
  .whenNotMatched()
  .insertAll()
  .execute()

// Verify results
spark.sql("SELECT * FROM employees ORDER BY id").show()
```

## Step 6: Delta Lake Advanced Features

### Time Travel:
```scala
// Show table history
deltaTable.history().show()

// Query historical versions
// By version number
val version1 = spark.read.format("delta").option("versionAsOf", 1).load("/home/sanzad/deltalake-local/delta-tables/employees")
version1.show()

// By timestamp
val historical = spark.read
  .format("delta")
  .option("timestampAsOf", "2023-01-01 00:00:00")
  .load("/home/sanzad/deltalake-local/delta-tables/employees")

// Using SQL
spark.sql("""
  SELECT * FROM employees VERSION AS OF 1
""").show()

spark.sql("""
  SELECT * FROM employees TIMESTAMP AS OF '2023-01-01 00:00:00'
""").show()
```

### Schema Evolution and Enforcement:
```scala
// Schema enforcement - this will fail
val badData = Seq(
  (7, "Grace", "thirty-five", "HR", 75000, "2023-01-21")  // age as string
).toDF("id", "name", "age", "department", "salary", "hire_date")

try {
  badData.write.format("delta").mode("append").save("/home/sanzad/deltalake-local/delta-tables/employees")
} catch {
  case e: Exception => println(s"Schema enforcement caught error: ${e.getMessage}")
}

// Schema evolution - add new column
val expandedData = Seq(
  (7, "Grace", 35, "HR", 75000, "2023-01-21", "remote")
).toDF("id", "name", "age", "department", "salary", "hire_date", "work_location")

expandedData.write
  .format("delta")
  .mode("append")
  .option("mergeSchema", "true")
  .save("/home/sanzad/deltalake-local/delta-tables/employees")

// Verify new schema
spark.sql("DESCRIBE employees").show()
spark.sql("SELECT * FROM employees").show()
```

### Data Quality with Constraints:
```scala
// Add check constraint
spark.sql("""
  ALTER TABLE employees 
  ADD CONSTRAINT age_check CHECK (age > 18 AND age < 65)
""")

// Add not null constraint
spark.sql("""
  ALTER TABLE employees 
  ADD CONSTRAINT name_not_null CHECK (name IS NOT NULL)
""")

// Try to insert invalid data
val invalidData = Seq(
  (8, "Invalid", 17, "Engineering", 75000, "2023-01-22", "office")  // age < 18
).toDF("id", "name", "age", "department", "salary", "hire_date", "work_location")

try {
  invalidData.write.format("delta").mode("append").save("/home/sanzad/deltalake-local/delta-tables/employees")
} catch {
  case e: Exception => println(s"Constraint violation: ${e.getMessage}")
}
```

## Step 7: Python Integration

### Create Python example:
```python
# Create Python script
nano /home/sanzad/deltalake-local/scripts/delta_python_example.py
```

```python
from pyspark.sql import SparkSession
from delta.tables import *
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Create Spark session with Delta Lake
spark = SparkSession.builder \
    .appName("Delta Lake Python Example") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
    .getOrCreate()

# Create sales data
sales_data = [
    (1, "Product A", "Electronics", 100, 25.50, "2023-01-01", "North"),
    (2, "Product B", "Clothing", 75, 45.00, "2023-01-02", "South"),
    (3, "Product C", "Electronics", 150, 199.99, "2023-01-03", "East"),
    (4, "Product D", "Books", 50, 15.99, "2023-01-04", "West"),
    (5, "Product E", "Clothing", 200, 35.75, "2023-01-05", "North")
]

columns = ["id", "product_name", "category", "quantity", "price", "sale_date", "region"]
sales_df = spark.createDataFrame(sales_data, columns)

# Write to Delta table
delta_path = "/home/sanzad/deltalake-local/delta-tables/sales"
sales_df.write.format("delta").mode("overwrite").save(delta_path)

print("✓ Sales table created successfully")

# Read Delta table
sales_delta = spark.read.format("delta").load(delta_path)
sales_delta.show()

# Create DeltaTable object for advanced operations
delta_table = DeltaTable.forPath(spark, delta_path)

# Show table details
print("\n=== Table History ===")
delta_table.history().show(truncate=False)

print("\n=== Table Detail ===")
delta_table.detail().show(truncate=False)

# Perform merge operation
new_sales = [
    (6, "Product F", "Electronics", 80, 299.99, "2023-01-06", "Central"),
    (2, "Product B", "Clothing", 100, 45.00, "2023-01-02", "South")  # Update quantity
]

new_sales_df = spark.createDataFrame(new_sales, columns)

# Merge (upsert) operation
delta_table.alias("target") \
    .merge(new_sales_df.alias("source"), "target.id = source.id") \
    .whenMatchedUpdate(set={
        "quantity": col("source.quantity"),
        "price": col("source.price")
    }) \
    .whenNotMatchedInsert(values={
        "id": col("source.id"),
        "product_name": col("source.product_name"),
        "category": col("source.category"),
        "quantity": col("source.quantity"),
        "price": col("source.price"),
        "sale_date": col("source.sale_date"),
        "region": col("source.region")
    }) \
    .execute()

print("✓ Merge operation completed")

# Show updated data
print("\n=== Updated Sales Data ===")
spark.read.format("delta").load(delta_path).show()

# Demonstrate time travel
print("\n=== Time Travel Example ===")
print("Version 0 (original):")
spark.read.format("delta").option("versionAsOf", 0).load(delta_path).show()

print("Version 1 (after merge):")
spark.read.format("delta").option("versionAsOf", 1).load(delta_path).show()

spark.stop()
```

### Run Python example:
```bash
cd /home/sanzad/deltalake-local
python3 scripts/delta_python_example.py
```

## Step 8: Streaming with Delta Lake

### Create streaming example:
```python
# Create streaming script
nano /home/sanzad/deltalake-local/scripts/delta_streaming_example.py
```

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import time
import threading
import random

# Create Spark session
spark = SparkSession.builder \
    .appName("Delta Lake Streaming") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
    .getOrCreate()

# Define schema for streaming data
schema = StructType([
    StructField("timestamp", TimestampType(), True),
    StructField("user_id", IntegerType(), True),
    StructField("event_type", StringType(), True),
    StructField("page", StringType(), True),
    StructField("session_id", StringType(), True)
])

# Simulate data generation
def generate_data():
    import json
    import os
    import uuid
    
    data_dir = "/home/sanzad/deltalake-local/data/streaming"
    os.makedirs(data_dir, exist_ok=True)
    
    events = ["page_view", "click", "scroll", "exit"]
    pages = ["home", "products", "about", "contact", "checkout"]
    
    for i in range(100):
        data = {
            "timestamp": "2023-01-01T" + f"{10 + i//10}:{i%60:02d}:00",
            "user_id": random.randint(1, 100),
            "event_type": random.choice(events),
            "page": random.choice(pages),
            "session_id": str(uuid.uuid4())[:8]
        }
        
        with open(f"{data_dir}/events_{i:03d}.json", "w") as f:
            json.dump(data, f)
        
        time.sleep(0.1)  # Generate data every 100ms

# Start data generation in background
data_thread = threading.Thread(target=generate_data)
data_thread.daemon = True
data_thread.start()

# Wait a bit for some data to be generated
time.sleep(2)

# Set up streaming source
streaming_df = spark.readStream \
    .format("json") \
    .schema(schema) \
    .option("path", "/home/sanzad/deltalake-local/data/streaming") \
    .load()

# Process streaming data
processed_df = streaming_df \
    .withColumn("hour", hour("timestamp")) \
    .groupBy("hour", "event_type", "page") \
    .count()

# Write stream to Delta table
delta_stream_path = "/home/sanzad/deltalake-local/delta-tables/user_events_stream"
checkpoint_path = "/home/sanzad/deltalake-local/checkpoints/user_events"

query = processed_df.writeStream \
    .format("delta") \
    .outputMode("complete") \
    .option("checkpointLocation", checkpoint_path) \
    .option("path", delta_stream_path) \
    .trigger(processingTime='10 seconds') \
    .start()

print("Streaming query started. Let it run for 30 seconds...")
time.sleep(30)

# Stop the streaming query
query.stop()

# Read the results
print("\n=== Streaming Results ===")
results = spark.read.format("delta").load(delta_stream_path)
results.orderBy("hour", "count").show()

spark.stop()
```

## Step 9: Integration with Other Systems

### Kafka Integration:
```python
# Create Kafka integration script
nano /home/sanzad/deltalake-local/scripts/delta_kafka_integration.py
```

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Create Spark session
spark = SparkSession.builder \
    .appName("Delta Lake Kafka Integration") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Read from Kafka (assuming Kafka is running)
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "192.168.1.184:9092") \
    .option("subscribe", "user-events") \
    .option("startingOffsets", "latest") \
    .load()

# Parse JSON data from Kafka
event_schema = StructType([
    StructField("user_id", IntegerType(), True),
    StructField("event_time", TimestampType(), True),
    StructField("event_type", StringType(), True),
    StructField("properties", MapType(StringType(), StringType()), True)
])

parsed_df = kafka_df \
    .select(from_json(col("value").cast("string"), event_schema).alias("data")) \
    .select("data.*") \
    .withColumn("processing_time", current_timestamp())

# Write to Delta Lake
delta_kafka_path = "/home/sanzad/deltalake-local/delta-tables/kafka_events"
checkpoint_kafka_path = "/home/sanzad/deltalake-local/checkpoints/kafka_events"

kafka_query = parsed_df.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", checkpoint_kafka_path) \
    .option("path", delta_kafka_path) \
    .trigger(processingTime='5 seconds') \
    .start()

print("Kafka to Delta Lake streaming started...")
# kafka_query.awaitTermination(60)  # Run for 60 seconds

spark.stop()
```

### PostgreSQL Integration:
```python
# Create PostgreSQL integration script
nano /home/sanzad/deltalake-local/scripts/delta_postgres_integration.py
```

```python
from pyspark.sql import SparkSession

# Create Spark session
spark = SparkSession.builder \
    .appName("Delta Lake PostgreSQL Integration") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Read from PostgreSQL
postgres_df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://192.168.1.184:5432/analytics_db") \
    .option("dbtable", "sales_data") \
    .option("user", "dataeng") \
    .option("password", "password") \
    .option("driver", "org.postgresql.Driver") \
    .load()

print(f"Read {postgres_df.count()} rows from PostgreSQL")

# Write to Delta Lake with partitioning
delta_pg_path = "/home/sanzad/deltalake-local/delta-tables/sales_from_pg"

postgres_df.write \
    .format("delta") \
    .mode("overwrite") \
    .option("path", delta_pg_path) \
    .partitionBy("region") \
    .save()

print("✓ Data written to Delta Lake with partitioning")

# Read back and verify
delta_data = spark.read.format("delta").load(delta_pg_path)
print(f"Delta table contains {delta_data.count()} rows")
delta_data.show(5)

# Write aggregated data back to PostgreSQL
aggregated = delta_data.groupBy("region").agg(
    sum("amount").alias("total_sales"),
    count("*").alias("transaction_count"),
    avg("amount").alias("avg_transaction")
)

aggregated.write \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://192.168.1.184:5432/analytics_db") \
    .option("dbtable", "sales_summary_delta") \
    .option("user", "dataeng") \
    .option("password", "password") \
    .option("driver", "org.postgresql.Driver") \
    .mode("overwrite") \
    .save()

print("✓ Aggregated data written back to PostgreSQL")

spark.stop()
```

## Step 10: Jupyter Notebook Setup

### Create Jupyter kernel configuration:
```python
# Create Jupyter initialization script
nano /home/sanzad/deltalake-local/jupyter-delta.py
```

```python
import os
from pyspark.sql import SparkSession

# Set environment variables
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-11-openjdk-amd64"
os.environ["SPARK_HOME"] = "/home/spark/spark"

# Create Spark session with Delta Lake
spark = SparkSession.builder \
    .appName("Delta-Lake-Jupyter") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.shuffle.partitions", "4") \
    .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
    .getOrCreate()

# Import common libraries
from delta.tables import *
from pyspark.sql.functions import *
from pyspark.sql.types import *
import pandas as pd

print("✓ Spark session with Delta Lake initialized!")
print(f"Spark version: {spark.version}")
print(f"Delta Lake tables location: /home/sanzad/deltalake-local/delta-tables/")

# Helper function to list Delta tables
def list_delta_tables():
    import os
    tables_dir = "/home/sanzad/deltalake-local/delta-tables"
    if os.path.exists(tables_dir):
        return [d for d in os.listdir(tables_dir) if os.path.isdir(os.path.join(tables_dir, d))]
    return []

print(f"Available Delta tables: {list_delta_tables()}")
```

### Create sample notebook:
```bash
nano /home/sanzad/deltalake-local/notebooks/delta_lake_tutorial.ipynb
```

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Delta Lake Tutorial\n",
    "\n",
    "This notebook demonstrates key Delta Lake features including:\n",
    "- Creating Delta tables\n",
    "- ACID transactions\n",
    "- Time travel\n",
    "- Schema evolution\n",
    "- Data quality constraints"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Initialize Spark with Delta Lake\n",
    "exec(open('/home/sanzad/deltalake-local/jupyter-delta.py').read())"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Create sample e-commerce data\n",
    "ecommerce_data = [\n",
    "    (1, \"Electronics\", \"Laptop\", 999.99, 10, \"2023-01-01\"),\n",
    "    (2, \"Electronics\", \"Phone\", 699.99, 25, \"2023-01-02\"),\n",
    "    (3, \"Books\", \"Python Guide\", 39.99, 100, \"2023-01-03\"),\n",
    "    (4, \"Clothing\", \"T-Shirt\", 19.99, 50, \"2023-01-04\")\n",
    "]\n",
    "\n",
    "columns = [\"product_id\", \"category\", \"name\", \"price\", \"inventory\", \"last_updated\"]\n",
    "products_df = spark.createDataFrame(ecommerce_data, columns)\n",
    "\n",
    "# Save as Delta table\n",
    "delta_path = \"/home/sanzad/deltalake-local/delta-tables/products\"\n",
    "products_df.write.format(\"delta\").mode(\"overwrite\").save(delta_path)\n",
    "\n",
    "print(\"✓ Products table created\")\n",
    "spark.read.format(\"delta\").load(delta_path).show()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Demonstrate UPSERT operations\n",
    "from delta.tables import DeltaTable\n",
    "\n",
    "delta_table = DeltaTable.forPath(spark, delta_path)\n",
    "\n",
    "# New product data with updates\n",
    "new_data = [\n",
    "    (2, \"Electronics\", \"Phone\", 649.99, 30, \"2023-01-05\"),  # Price reduction, inventory update\n",
    "    (5, \"Books\", \"Data Engineering\", 49.99, 75, \"2023-01-05\")  # New product\n",
    "]\n",
    "\n",
    "new_df = spark.createDataFrame(new_data, columns)\n",
    "\n",
    "# Perform merge operation\n",
    "delta_table.alias(\"target\") \\\n",
    "    .merge(new_df.alias(\"source\"), \"target.product_id = source.product_id\") \\\n",
    "    .whenMatchedUpdateAll() \\\n",
    "    .whenNotMatchedInsertAll() \\\n",
    "    .execute()\n",
    "\n",
    "print(\"✓ Merge completed\")\n",
    "spark.read.format(\"delta\").load(delta_path).show()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.8.10"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
```

### Start Jupyter:
```bash
cd /home/sanzad/deltalake-local/notebooks
jupyter notebook --ip=0.0.0.0 --port=8889 --no-browser --allow-root
```

## Step 11: Testing and Validation

### Create comprehensive test script:
```python
nano /home/sanzad/deltalake-local/scripts/test_delta_lake.py
```

```python
#!/usr/bin/env python3

from pyspark.sql import SparkSession
from delta.tables import *
from pyspark.sql.functions import *
from pyspark.sql.types import *
import tempfile
import shutil
import sys

def test_delta_lake():
    """Comprehensive Delta Lake functionality test"""
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("DeltaLakeTest") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.databricks.delta.retentionDurationCheck.enabled", "false") \
        .getOrCreate()
    
    test_results = []
    
    try:
        # Test 1: Basic table creation
        print("🧪 Test 1: Basic table creation")
        test_path = "/home/sanzad/deltalake-local/delta-tables/test_table"
        
        test_data = [(1, "test1", 100), (2, "test2", 200)]
        test_df = spark.createDataFrame(test_data, ["id", "name", "value"])
        test_df.write.format("delta").mode("overwrite").save(test_path)
        
        result_count = spark.read.format("delta").load(test_path).count()
        assert result_count == 2, f"Expected 2 rows, got {result_count}"
        test_results.append("✓ Basic table creation")
        
        # Test 2: ACID transactions
        print("🧪 Test 2: ACID transactions")
        delta_table = DeltaTable.forPath(spark, test_path)
        
        # Concurrent update simulation
        delta_table.update(condition = expr("id = 1"), set = {"value": expr("value + 50")})
        updated_value = spark.read.format("delta").load(test_path).filter("id = 1").collect()[0]["value"]
        assert updated_value == 150, f"Expected 150, got {updated_value}"
        test_results.append("✓ ACID transactions")
        
        # Test 3: Time travel
        print("🧪 Test 3: Time travel")
        history = delta_table.history()
        version_count = history.count()
        assert version_count >= 2, f"Expected at least 2 versions, got {version_count}"
        
        # Read previous version
        old_data = spark.read.format("delta").option("versionAsOf", 0).load(test_path)
        old_value = old_data.filter("id = 1").collect()[0]["value"]
        assert old_value == 100, f"Expected original value 100, got {old_value}"
        test_results.append("✓ Time travel")
        
        # Test 4: Schema evolution
        print("🧪 Test 4: Schema evolution")
        new_data = [(3, "test3", 300, "extra_column")]
        new_df = spark.createDataFrame(new_data, ["id", "name", "value", "extra"])
        
        new_df.write.format("delta").mode("append").option("mergeSchema", "true").save(test_path)
        
        schema_fields = len(spark.read.format("delta").load(test_path).schema.fields)
        assert schema_fields == 4, f"Expected 4 columns after schema evolution, got {schema_fields}"
        test_results.append("✓ Schema evolution")
        
        # Test 5: Merge operations
        print("🧪 Test 5: Merge operations")
        merge_data = [(1, "updated_test1", 999, "updated"), (4, "test4", 400, "new")]
        merge_df = spark.createDataFrame(merge_data, ["id", "name", "value", "extra"])
        
        delta_table.alias("target") \
            .merge(merge_df.alias("source"), "target.id = source.id") \
            .whenMatchedUpdateAll() \
            .whenNotMatchedInsertAll() \
            .execute()
        
        final_count = spark.read.format("delta").load(test_path).count()
        assert final_count == 4, f"Expected 4 rows after merge, got {final_count}"
        test_results.append("✓ Merge operations")
        
        # Test 6: Vacuum operation
        print("🧪 Test 6: Vacuum operation")
        delta_table.vacuum(0)  # Retain 0 hours for testing
        test_results.append("✓ Vacuum operation")
        
        print("\n🎉 All tests passed! Delta Lake is working correctly.")
        print("Test Results:")
        for result in test_results:
            print(f"  {result}")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        spark.stop()

if __name__ == "__main__":
    test_delta_lake()
```

Make it executable and run:
```bash
chmod +x /home/sanzad/deltalake-local/scripts/test_delta_lake.py
python3 /home/sanzad/deltalake-local/scripts/test_delta_lake.py
```

## Step 12: Performance Optimization

### File management and optimization:
```python
nano /home/sanzad/deltalake-local/scripts/optimize_delta_tables.py
```

```python
from pyspark.sql import SparkSession
from delta.tables import *
import os

def optimize_delta_tables():
    """Optimize Delta Lake tables for better performance"""
    
    spark = SparkSession.builder \
        .appName("DeltaOptimizer") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()
    
    tables_dir = "/home/sanzad/deltalake-local/delta-tables"
    
    # Find all Delta tables
    if os.path.exists(tables_dir):
        table_dirs = [d for d in os.listdir(tables_dir) 
                     if os.path.isdir(os.path.join(tables_dir, d))]
        
        for table_name in table_dirs:
            table_path = os.path.join(tables_dir, table_name)
            print(f"Optimizing table: {table_name}")
            
            try:
                delta_table = DeltaTable.forPath(spark, table_path)
                
                # Optimize (compact small files)
                delta_table.optimize().executeCompaction()
                print(f"  ✓ Compaction completed for {table_name}")
                
                # Z-ordering (if table has suitable columns)
                # This is a placeholder - add actual Z-order columns based on query patterns
                # delta_table.optimize().executeZOrderBy("column1", "column2")
                
                # Vacuum old files (retain last 7 days)
                delta_table.vacuum(168)  # 168 hours = 7 days
                print(f"  ✓ Vacuum completed for {table_name}")
                
            except Exception as e:
                print(f"  ❌ Error optimizing {table_name}: {str(e)}")
    
    spark.stop()

if __name__ == "__main__":
    optimize_delta_tables()
```

### Performance monitoring:
```python
nano /home/sanzad/deltalake-local/scripts/monitor_delta_performance.py
```

```python
from pyspark.sql import SparkSession
from delta.tables import *
import os
import json

def monitor_delta_performance():
    """Monitor Delta Lake table performance metrics"""
    
    spark = SparkSession.builder \
        .appName("DeltaMonitor") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()
    
    tables_dir = "/home/sanzad/deltalake-local/delta-tables"
    
    print("=== Delta Lake Performance Report ===\n")
    
    if os.path.exists(tables_dir):
        table_dirs = [d for d in os.listdir(tables_dir) 
                     if os.path.isdir(os.path.join(tables_dir, d))]
        
        for table_name in table_dirs:
            table_path = os.path.join(tables_dir, table_name)
            print(f"📊 Table: {table_name}")
            
            try:
                delta_table = DeltaTable.forPath(spark, table_path)
                
                # Table details
                detail = delta_table.detail().collect()[0]
                print(f"  📁 Location: {detail['location']}")
                print(f"  📈 Number of files: {detail['numFiles']}")
                print(f"  💾 Size in bytes: {detail['sizeInBytes']:,}")
                print(f"  🔢 Partitions: {detail['partitionColumns']}")
                
                # History information
                history = delta_table.history(5)  # Last 5 operations
                print(f"  📜 Recent operations:")
                for row in history.collect():
                    operation = row['operation']
                    timestamp = row['timestamp']
                    print(f"    - {operation} at {timestamp}")
                
                # File size distribution
                files_df = spark.sql(f"DESCRIBE DETAIL delta.`{table_path}`").collect()[0]
                avg_file_size = files_df['sizeInBytes'] / max(files_df['numFiles'], 1)
                print(f"  📊 Average file size: {avg_file_size:,.0f} bytes")
                
                if avg_file_size < 1024 * 1024:  # Less than 1MB
                    print(f"  ⚠️  Warning: Small files detected. Consider running OPTIMIZE.")
                
                print()
                
            except Exception as e:
                print(f"  ❌ Error analyzing {table_name}: {str(e)}\n")
    
    # Overall workspace statistics
    total_size = sum(
        sum(os.path.getsize(os.path.join(dirpath, filename))
            for filename in filenames)
        for dirpath, dirnames, filenames in os.walk(tables_dir)
    )
    print(f"📈 Total workspace size: {total_size / (1024*1024):.2f} MB")
    
    spark.stop()

if __name__ == "__main__":
    monitor_delta_performance()
```

Make scripts executable:
```bash
chmod +x /home/sanzad/deltalake-local/scripts/optimize_delta_tables.py
chmod +x /home/sanzad/deltalake-local/scripts/monitor_delta_performance.py
```

## Step 13: Data Quality and Governance

### Create data quality framework:
```python
nano /home/sanzad/deltalake-local/scripts/data_quality_framework.py
```

```python
from pyspark.sql import SparkSession
from delta.tables import *
from pyspark.sql.functions import *
from pyspark.sql.types import *

def setup_data_quality():
    """Set up data quality framework with Delta Lake"""
    
    spark = SparkSession.builder \
        .appName("DeltaDataQuality") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()
    
    # Create customer table with constraints
    customers_path = "/home/sanzad/deltalake-local/delta-tables/customers_dq"
    
    # Sample customer data
    customers_data = [
        (1, "john.doe@email.com", "John", "Doe", 28, "2023-01-01"),
        (2, "jane.smith@email.com", "Jane", "Smith", 32, "2023-01-02"),
        (3, "bob.johnson@email.com", "Bob", "Johnson", 45, "2023-01-03")
    ]
    
    customers_schema = ["customer_id", "email", "first_name", "last_name", "age", "signup_date"]
    customers_df = spark.createDataFrame(customers_data, customers_schema)
    
    # Create Delta table
    customers_df.write.format("delta").mode("overwrite").save(customers_path)
    
    # Add constraints
    spark.sql(f"""
        ALTER TABLE delta.`{customers_path}` 
        ADD CONSTRAINT valid_email CHECK (email RLIKE '^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+\.[A-Za-z]{{2,}}$')
    """)
    
    spark.sql(f"""
        ALTER TABLE delta.`{customers_path}` 
        ADD CONSTRAINT valid_age CHECK (age >= 18 AND age <= 100)
    """)
    
    spark.sql(f"""
        ALTER TABLE delta.`{customers_path}` 
        ADD CONSTRAINT non_empty_names CHECK (first_name IS NOT NULL AND last_name IS NOT NULL)
    """)
    
    print("✅ Data quality constraints added successfully!")
    
    # Test constraint violations
    print("\n🧪 Testing constraint violations...")
    
    # Test 1: Invalid email
    try:
        invalid_email_data = [(4, "invalid-email", "Test", "User", 25, "2023-01-04")]
        invalid_df = spark.createDataFrame(invalid_email_data, customers_schema)
        invalid_df.write.format("delta").mode("append").save(customers_path)
        print("❌ Should have failed on invalid email")
    except Exception as e:
        print("✅ Email validation working: constraint violation caught")
    
    # Test 2: Invalid age
    try:
        invalid_age_data = [(5, "young@email.com", "Too", "Young", 15, "2023-01-05")]
        invalid_age_df = spark.createDataFrame(invalid_age_data, customers_schema)
        invalid_age_df.write.format("delta").mode("append").save(customers_path)
        print("❌ Should have failed on invalid age")
    except Exception as e:
        print("✅ Age validation working: constraint violation caught")
    
    # Data profiling
    print("\n📊 Data Profiling:")
    customers_delta = spark.read.format("delta").load(customers_path)
    
    print(f"Total customers: {customers_delta.count()}")
    print(f"Age distribution:")
    customers_delta.groupBy("age").count().orderBy("age").show()
    
    print("Email domain distribution:")
    customers_delta.withColumn("domain", expr("split(email, '@')[1]")) \
        .groupBy("domain").count().show()
    
    spark.stop()

if __name__ == "__main__":
    setup_data_quality()
```

## Step 14: Cleanup and Maintenance

### Create cleanup script:
```bash
nano /home/sanzad/deltalake-local/scripts/cleanup_delta.sh
```

```bash
#!/bin/bash

DELTA_HOME="/home/sanzad/deltalake-local"

echo "🧹 Cleaning up Delta Lake local environment..."

# Clean old log files
echo "Cleaning log files..."
find $DELTA_HOME/logs -name "*.log" -mtime +7 -delete 2>/dev/null
find $DELTA_HOME/logs -name "eventlog_*" -mtime +7 -delete 2>/dev/null

# Clean checkpoints older than 7 days
echo "Cleaning old checkpoints..."
find $DELTA_HOME/checkpoints -type f -mtime +7 -delete 2>/dev/null

# Clean temp directories
echo "Cleaning temp files..."
find $DELTA_HOME/temp -type f -mtime +1 -delete 2>/dev/null

# Display space usage
echo "📊 Current space usage:"
du -sh $DELTA_HOME/delta-tables/* 2>/dev/null | sort -hr

# Display total size
TOTAL_SIZE=$(du -sh $DELTA_HOME | cut -f1)
echo "💾 Total workspace size: $TOTAL_SIZE"

echo "✅ Cleanup completed!"
```

Make it executable:
```bash
chmod +x /home/sanzad/deltalake-local/scripts/cleanup_delta.sh
```

## Key Learning Outcomes

After completing this local Delta Lake setup, you'll understand:

1. **ACID Transactions**: How Delta Lake provides ACID guarantees for big data
2. **Time Travel**: Querying historical versions of your data
3. **Schema Evolution**: Adding, removing, and modifying columns safely
4. **Data Quality**: Implementing constraints and data validation
5. **Performance Optimization**: File compaction, Z-ordering, and vacuum operations
6. **Integration Patterns**: Working with Spark, Python, streaming, and other systems
7. **Operational Aspects**: Monitoring, maintenance, and troubleshooting

## Integration with Cluster Components

This local Delta Lake setup integrates seamlessly with your HomeLab cluster:

- **Spark Cluster**: Use distributed Spark for production workloads
- **Kafka**: Stream processing with Delta Lake as the sink
- **PostgreSQL**: ETL from/to relational databases
- **Trino**: Query Delta tables using SQL federation
- **Flink**: Alternative stream processing engine

## Production Considerations

1. **Distributed Storage**: Move to HDFS, S3, or other distributed file systems
2. **Metastore Integration**: Use Hive Metastore for table discovery
3. **Multi-Writer Scenarios**: Handle concurrent writes properly
4. **Monitoring**: Implement comprehensive monitoring and alerting
5. **Security**: Add authentication, authorization, and encryption
6. **Backup Strategy**: Implement proper backup and disaster recovery

This local setup provides an excellent foundation for learning Delta Lake concepts and can be easily scaled to production environments.
