# Apache Spark Cluster Setup Guide

## Overview
Apache Spark will be set up in standalone cluster mode with cpu-node1 as the master and cpu-node2 as a worker node. Worker-node3 can be added as an additional worker if needed.

## Cluster Configuration
- **Spark Master**: cpu-node1 (192.168.1.184)
- **Spark Worker 1**: cpu-node2 (192.168.1.187)
- **Spark Worker 2**: worker-node3 (192.168.1.190) - Optional for additional capacity

## Prerequisites
- Java 8 or Java 11 installed on all nodes
- Scala 2.12 (recommended)
- At least 4GB RAM per node
- At least 20GB free disk space per node
- SSH key-based authentication between master and workers

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   worker-node3      │
│  (Spark Master)     │    │  (Spark Worker 1)   │    │  (Spark Worker 2)   │
│  - Driver Programs  │    │  - Executor JVMs    │    │  - Executor JVMs    │
│  - Web UI (8080)    │    │  - Local Storage    │    │  - Local Storage    │
│  192.168.1.184      │    │  192.168.1.187      │    │  192.168.1.190      │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Step 1: Java and Scala Installation (All Nodes)

```bash
# Install OpenJDK 11
sudo apt update
sudo apt install -y openjdk-11-jdk scala

# Verify installations
java -version
scala -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
echo 'export SCALA_HOME=/usr/share/scala' >> ~/.bashrc
source ~/.bashrc
```

## Step 2: Create Spark User and SSH Setup

### Create spark user on all nodes:
```bash
sudo useradd -m -s /bin/bash spark
sudo passwd spark
sudo usermod -aG sudo spark
```

### Set up SSH keys (from cpu-node1):
```bash
# Switch to spark user
sudo su - spark

# Generate SSH key
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa

# Copy public key to worker nodes
ssh-copy-id spark@192.168.1.187
ssh-copy-id spark@192.168.1.190

# Test SSH connectivity
ssh spark@192.168.1.187 "hostname"
ssh spark@192.168.1.190 "hostname"
```

## Step 3: Download and Install Spark (All Nodes)

```bash
# Switch to spark user
sudo su - spark
cd /home/spark

# Download Spark
wget https://downloads.apache.org/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz

# Extract and setup
tar -xzf spark-3.5.0-bin-hadoop3.tgz
mv spark-3.5.0-bin-hadoop3 spark
rm spark-3.5.0-bin-hadoop3.tgz

# Add Spark to PATH
echo 'export SPARK_HOME=/home/spark/spark' >> ~/.bashrc
echo 'export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin' >> ~/.bashrc
source ~/.bashrc
```

## Step 4: Configure Spark Master (cpu-node1)

### Create Spark configuration:
```bash
cd $SPARK_HOME/conf

# Copy template files
cp spark-defaults.conf.template spark-defaults.conf
cp spark-env.sh.template spark-env.sh
cp workers.template workers
```

### Configure spark-env.sh:
```bash
nano spark-env.sh
```

Add these configurations:
```bash
#!/usr/bin/env bash

# Java and Spark paths
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export SPARK_HOME=/home/spark/spark
export SPARK_CONF_DIR=$SPARK_HOME/conf

# Master configuration
export SPARK_MASTER_HOST=192.168.1.184
export SPARK_MASTER_PORT=7077
export SPARK_MASTER_WEBUI_PORT=8080

# Worker configuration
export SPARK_WORKER_CORES=4
export SPARK_WORKER_MEMORY=4g
export SPARK_WORKER_PORT=7078
export SPARK_WORKER_WEBUI_PORT=8081
export SPARK_WORKER_DIR=/home/spark/spark/work

# History Server
export SPARK_HISTORY_OPTS="-Dspark.history.ui.port=18080 -Dspark.history.fs.logDirectory=/home/spark/spark/logs"

# Performance tuning
export SPARK_DAEMON_MEMORY=1g
export SPARK_MASTER_OPTS="-Dspark.deploy.recoveryMode=FILESYSTEM -Dspark.deploy.recoveryDirectory=/home/spark/spark/recovery"
```

### Configure workers file:
```bash
nano workers
```

Add worker nodes:
```
192.168.1.187
192.168.1.190
```

### Configure spark-defaults.conf:
```bash
nano spark-defaults.conf
```

Add these configurations:
```properties
# Application Properties
spark.master                     spark://192.168.1.184:7077
spark.eventLog.enabled           true
spark.eventLog.dir               /home/spark/spark/logs
spark.history.fs.logDirectory    /home/spark/spark/logs

# Runtime Environment  
spark.executorEnv.JAVA_HOME      /usr/lib/jvm/java-11-openjdk-amd64
spark.yarn.appMasterEnv.JAVA_HOME /usr/lib/jvm/java-11-openjdk-amd64

# Shuffle and IO
spark.serializer                 org.apache.spark.serializer.KryoSerializer
spark.io.compression.codec       snappy

# Memory Management
spark.executor.memory            2g
spark.executor.cores             2
spark.driver.memory              1g
spark.driver.cores               2

# Network
spark.network.timeout            800s
spark.executor.heartbeatInterval 60s

# SQL and Catalyst
spark.sql.adaptive.enabled              true
spark.sql.adaptive.coalescePartitions.enabled true
spark.sql.adaptive.skewJoin.enabled     true

# Integration with other systems
spark.sql.catalogImplementation  hive
spark.sql.warehouse.dir          /home/spark/spark/warehouse

# Iceberg Integration
spark.sql.extensions            org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
spark.sql.catalog.spark_catalog org.apache.iceberg.spark.SparkSessionCatalog
spark.sql.catalog.spark_catalog.type hive
spark.sql.catalog.iceberg       org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.iceberg.type  hadoop
spark.sql.catalog.iceberg.warehouse /home/spark/iceberg-warehouse

# Delta Lake Integration  
spark.sql.extensions            io.delta.sql.DeltaSparkSessionExtension
spark.sql.catalog.spark_catalog org.apache.spark.sql.delta.catalog.DeltaCatalog
```

## Step 5: Create Required Directories (All Nodes)

```bash
# Create directories as spark user
sudo su - spark

mkdir -p $SPARK_HOME/logs
mkdir -p $SPARK_HOME/work  
mkdir -p $SPARK_HOME/recovery
mkdir -p $SPARK_HOME/warehouse
mkdir -p /home/spark/iceberg-warehouse
mkdir -p /home/spark/delta-warehouse

# Set permissions
chmod 755 $SPARK_HOME/logs
chmod 755 $SPARK_HOME/work
chmod 755 $SPARK_HOME/recovery
```

## Step 6: Configure Workers (cpu-node2 and worker-node3)

Copy the configuration from master to workers:

```bash
# From cpu-node1 (as spark user)
scp -r $SPARK_HOME/conf/* spark@192.168.1.187:$SPARK_HOME/conf/
scp -r $SPARK_HOME/conf/* spark@192.168.1.190:$SPARK_HOME/conf/

# Create directories on workers
ssh spark@192.168.1.187 "mkdir -p $SPARK_HOME/{logs,work,recovery,warehouse} /home/spark/{iceberg-warehouse,delta-warehouse}"
ssh spark@192.168.1.190 "mkdir -p $SPARK_HOME/{logs,work,recovery,warehouse} /home/spark/{iceberg-warehouse,delta-warehouse}"
```

## Step 7: Create Systemd Services

### Spark Master Service (cpu-node1):
```bash
sudo nano /etc/systemd/system/spark-master.service
```

```ini
[Unit]
Description=Apache Spark Master
After=network.target
Wants=network.target

[Service]
Type=forking
User=spark
Group=spark
WorkingDirectory=/home/spark/spark
Environment=SPARK_HOME=/home/spark/spark
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/home/spark/spark/sbin/start-master.sh
ExecStop=/home/spark/spark/sbin/stop-master.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Spark Worker Service (cpu-node2 and worker-node3):
```bash
sudo nano /etc/systemd/system/spark-worker.service
```

```ini
[Unit]
Description=Apache Spark Worker
After=network.target
Wants=network.target

[Service]
Type=forking
User=spark
Group=spark
WorkingDirectory=/home/spark/spark
Environment=SPARK_HOME=/home/spark/spark
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/home/spark/spark/sbin/start-worker.sh spark://192.168.1.184:7077
ExecStop=/home/spark/spark/sbin/stop-worker.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Spark History Server Service (cpu-node1):
```bash
sudo nano /etc/systemd/system/spark-history.service
```

```ini
[Unit]
Description=Apache Spark History Server
After=spark-master.service
Wants=spark-master.service

[Service]
Type=forking
User=spark
Group=spark
WorkingDirectory=/home/spark/spark
Environment=SPARK_HOME=/home/spark/spark
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/home/spark/spark/sbin/start-history-server.sh
ExecStop=/home/spark/spark/sbin/stop-history-server.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Step 8: Start Spark Cluster

### Start services:
```bash
# Reload systemd on all nodes
sudo systemctl daemon-reload

# Start master (cpu-node1)
sudo systemctl start spark-master
sudo systemctl enable spark-master

# Start workers (cpu-node2 and worker-node3)
sudo systemctl start spark-worker
sudo systemctl enable spark-worker

# Start history server (cpu-node1)
sudo systemctl start spark-history
sudo systemctl enable spark-history

# Check status
sudo systemctl status spark-master
sudo systemctl status spark-worker
sudo systemctl status spark-history
```

## Step 9: Firewall Configuration (All Nodes)

```bash
# Open required ports
sudo ufw allow 7077/tcp   # Spark Master port
sudo ufw allow 8080/tcp   # Spark Master Web UI
sudo ufw allow 7078/tcp   # Spark Worker port
sudo ufw allow 8081/tcp   # Spark Worker Web UI  
sudo ufw allow 18080/tcp  # History Server Web UI
sudo ufw allow 4040/tcp   # Spark Application Web UI
sudo ufw reload
```

## Step 10: Testing the Cluster

### Access Web UIs:
- Master Web UI: http://192.168.1.184:8080
- Worker Web UIs: http://192.168.1.187:8081, http://192.168.1.190:8081
- History Server: http://192.168.1.184:18080

### Run Spark Shell:
```bash
# As spark user
sudo su - spark
cd $SPARK_HOME

# Start Spark shell
./bin/spark-shell --master spark://192.168.1.184:7077
```

### Test with sample application:
```scala
// In Spark shell
val data = 1 to 10000
val distData = sc.parallelize(data)
val result = distData.filter(_ % 2 == 0).count()
println(s"Even numbers count: $result")
```

### Run Pi calculation example:
```bash
./bin/spark-submit \
  --class org.apache.spark.examples.SparkPi \
  --master spark://192.168.1.184:7077 \
  --executor-memory 1g \
  --total-executor-cores 4 \
  ./examples/jars/spark-examples_2.12-3.5.0.jar \
  100
```

## Step 11: Additional Dependencies for Data Engineering

### Download and install additional JARs:
```bash
# Create jars directory
mkdir -p $SPARK_HOME/jars-ext

cd $SPARK_HOME/jars-ext

# PostgreSQL JDBC driver
wget https://jdbc.postgresql.org/download/postgresql-42.7.2.jar

# Kafka integration
wget https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar
wget https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar

# Delta Lake
wget https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.4.0/delta-core_2.12-2.4.0.jar
wget https://repo1.maven.org/maven2/io/delta/delta-storage/2.4.0/delta-storage-2.4.0.jar

# Iceberg
wget https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.4.3/iceberg-spark-runtime-3.5_2.12-1.4.3.jar

# AWS S3 (if using S3 for storage)
wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
wget https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar

# Copy JARs to main jars directory
cp *.jar $SPARK_HOME/jars/
```

## Step 12: Create Sample Applications

### Create Python example:
```bash
nano /home/spark/sample_apps/word_count.py
```

```python
from pyspark.sql import SparkSession

# Create Spark session
spark = SparkSession.builder \
    .appName("WordCount") \
    .master("spark://192.168.1.184:7077") \
    .getOrCreate()

# Read text file
text_file = spark.read.text("/home/spark/sample_data/sample.txt")

# Word count
word_counts = text_file.rdd \
    .flatMap(lambda row: row.value.split(" ")) \
    .map(lambda word: (word, 1)) \
    .reduceByKey(lambda a, b: a + b) \
    .collect()

# Display results
for word, count in word_counts:
    print(f"{word}: {count}")

spark.stop()
```

### Create sample data:
```bash
mkdir -p /home/spark/sample_data
echo "Apache Spark is a unified analytics engine for large-scale data processing" > /home/spark/sample_data/sample.txt
```

### Run Python application:
```bash
./bin/spark-submit \
  --master spark://192.168.1.184:7077 \
  /home/spark/sample_apps/word_count.py
```

## Performance Tuning

### JVM Options for Spark daemons:
```bash
# Add to spark-env.sh
export SPARK_DAEMON_JAVA_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=200"
export SPARK_WORKER_OPTS="-Dspark.worker.cleanup.enabled=true -Dspark.worker.cleanup.interval=1800"
export SPARK_HISTORY_OPTS="$SPARK_HISTORY_OPTS -Dspark.history.retainedApplications=50"
```

### Dynamic allocation configuration:
```properties
# Add to spark-defaults.conf
spark.dynamicAllocation.enabled         true
spark.dynamicAllocation.minExecutors    1
spark.dynamicAllocation.maxExecutors    8
spark.dynamicAllocation.initialExecutors 2
spark.shuffle.service.enabled           true
```

## Monitoring and Logging

### Log locations:
- Master logs: `/home/spark/spark/logs/spark-spark-org.apache.spark.deploy.master.Master-1-cpu-node1.out`
- Worker logs: `/home/spark/spark/logs/spark-spark-org.apache.spark.deploy.worker.Worker-1-*.out`
- Application logs: In Spark Web UI and History Server

### Monitor cluster resources:
```bash
# Check cluster status
curl http://192.168.1.184:8080/json/

# Monitor applications
curl http://192.168.1.184:18080/api/v1/applications
```

## Integration Examples

### Spark with Kafka:
```python
# Structured Streaming with Kafka
stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "192.168.1.184:9092") \
    .option("subscribe", "test-topic") \
    .load()
```

### Spark with PostgreSQL:
```python
# Read from PostgreSQL
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://192.168.1.184:5432/analytics_db") \
    .option("dbtable", "sales_data") \
    .option("user", "dataeng") \
    .option("password", "password") \
    .load()
```

### Spark with Delta Lake:
```python
# Write to Delta table
df.write \
    .format("delta") \
    .mode("overwrite") \
    .save("/home/spark/delta-warehouse/sales")

# Read from Delta table
delta_df = spark.read \
    .format("delta") \
    .load("/home/spark/delta-warehouse/sales")
```

## Troubleshooting

### Common Issues:
1. **Worker not connecting**: Check network connectivity and firewall
2. **OutOfMemory errors**: Increase executor memory or reduce parallelism
3. **Shuffle errors**: Increase spark.sql.shuffle.partitions
4. **Slow startup**: Check DNS resolution and network latency

### Useful debugging commands:
```bash
# Check cluster status
$SPARK_HOME/bin/spark-shell --master spark://192.168.1.184:7077 --conf "spark.driver.bindAddress=192.168.1.184"

# Test connectivity
telnet 192.168.1.184 7077

# Check logs
tail -f $SPARK_HOME/logs/*.out
```

## Backup and Maintenance

### Backup important directories:
```bash
# Backup configuration
tar -czf spark-config-backup-$(date +%Y%m%d).tar.gz $SPARK_HOME/conf

# Backup application logs
tar -czf spark-logs-backup-$(date +%Y%m%d).tar.gz $SPARK_HOME/logs
```

### Regular maintenance:
```bash
# Clean up old application logs (run weekly)
find $SPARK_HOME/work -name "app-*" -type d -mtime +7 -exec rm -rf {} \;

# Clean up history server logs (keep last 50 applications)
# This is handled by spark.history.retainedApplications setting
```
