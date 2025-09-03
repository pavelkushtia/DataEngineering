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

# Download Spark (Latest Stable Version)
wget https://dlcdn.apache.org/spark/spark-3.5.6/spark-3.5.6-bin-hadoop3.tgz

# Extract and setup
tar -xzf spark-3.5.6-bin-hadoop3.tgz
mv spark-3.5.6-bin-hadoop3 spark
rm spark-3.5.6-bin-hadoop3.tgz

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
# Create/edit the workers file (defines which nodes are Spark workers)
nano workers
```

**Replace the entire contents** with your worker node IP addresses:
```
192.168.1.187
192.168.1.190
```

**Note**: 
- Remove any existing content (including `localhost` if present)
- Each IP address should be on its own line
- These are the nodes that will run Spark executors
- The master node (192.168.1.184) is NOT included in this file

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

## Step 7: Configure Workers (cpu-node2 and worker-node3)

Copy the configuration from master to workers:

```bash
# From cpu-node1 (as spark user)
scp -r $SPARK_HOME/conf/* spark@192.168.1.187:$SPARK_HOME/conf/
scp -r $SPARK_HOME/conf/* spark@192.168.1.190:$SPARK_HOME/conf/

# Create directories on workers
ssh spark@192.168.1.187 "mkdir -p $SPARK_HOME/{logs,work,recovery,warehouse} /home/spark/{iceberg-warehouse,delta-warehouse}"
ssh spark@192.168.1.190 "mkdir -p $SPARK_HOME/{logs,work,recovery,warehouse} /home/spark/{iceberg-warehouse,delta-warehouse}"
```

## Step 8: Create Systemd Services

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

**For Physical Machines or Standard VMs:**
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

**For Hyper-V Virtual Machines (worker-node3):**
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
Environment=SPARK_LOCAL_IP=192.168.1.190
ExecStart=/home/spark/spark/sbin/start-worker.sh --host 192.168.1.190 spark://192.168.1.184:7077
ExecStop=/home/spark/spark/sbin/stop-worker.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

> **Note**: The Hyper-V configuration includes explicit IP binding to resolve network binding issues with Hyper-V's synthetic network adapter (`hv_netvsc`). See the Hyper-V troubleshooting section below for details.

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

## Step 9: Start Spark Cluster

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

## Step 10: Firewall Configuration (All Nodes)

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
  ./examples/jars/spark-examples_2.12-3.5.6.jar \
  100
```

## Step 11: Additional Dependencies for Data Engineering

### Download and install additional JARs (Run on Master Node):
```bash
# Create jars directory
sudo su - spark
mkdir -p $SPARK_HOME/jars-ext

cd $SPARK_HOME/jars-ext

# PostgreSQL JDBC driver
wget https://jdbc.postgresql.org/download/postgresql-42.7.2.jar

# Kafka integration
wget https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.6/spark-sql-kafka-0-10_2.12-3.5.6.jar
wget https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar

# Delta Lake (REQUIRED - fixes ClassNotFoundException)
wget https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.4.0/delta-core_2.12-2.4.0.jar
wget https://repo1.maven.org/maven2/io/delta/delta-storage/2.4.0/delta-storage-2.4.0.jar

# Iceberg
wget https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/1.4.3/iceberg-spark-runtime-3.5_2.12-1.4.3.jar

# AWS S3 (if using S3 for storage)
wget https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/3.3.4/hadoop-aws-3.3.4.jar
wget https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.12.367/aws-java-sdk-bundle-1.12.367.jar

# Copy JARs to main jars directory
cp *.jar $SPARK_HOME/jars/

# Copy JARs to worker nodes
scp *.jar spark@192.168.1.187:$SPARK_HOME/jars/
scp *.jar spark@192.168.1.190:$SPARK_HOME/jars/
```

### Restart Spark services after adding JARs:
```bash
# Restart services on all nodes
sudo systemctl restart spark-master
sudo systemctl restart spark-worker  # Run on worker nodes
sudo systemctl restart spark-history
```

## Step 12: Create Sample Applications

### Create Python example:
```bash
mkdir -p /home/spark/sample_apps
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
5. **Hyper-V VM binding issues**: See Hyper-V specific troubleshooting below
6. **Delta Lake ClassNotFoundException**: See Delta Lake specific troubleshooting below

### 🔧 **Delta Lake ClassNotFoundException Fix**

#### **Problem: `java.lang.ClassNotFoundException: io.delta.sql.DeltaSparkSessionExtension`**

**Symptoms:**
- Spark shell starts but shows warning about unable to configure Delta Lake extensions
- Error: `Cannot use io.delta.sql.DeltaSparkSessionExtension to configure session extensions`
- Long stack trace mentioning `ClassNotFoundException`

**Root Cause:**
The Spark configuration includes Delta Lake extensions in `spark-defaults.conf`, but the required JAR files are missing from the classpath.

**Solution: Install Delta Lake JARs**

```bash
# 1. Switch to spark user
sudo su - spark

# 2. Download Delta Lake JARs
cd $SPARK_HOME/jars-ext
wget https://repo1.maven.org/maven2/io/delta/delta-core_2.12/2.4.0/delta-core_2.12-2.4.0.jar
wget https://repo1.maven.org/maven2/io/delta/delta-storage/2.4.0/delta-storage-2.4.0.jar

# 3. Copy to Spark jars directory
cp *.jar $SPARK_HOME/jars/

# 4. Copy to worker nodes
scp delta-*.jar spark@192.168.1.187:$SPARK_HOME/jars/
scp delta-*.jar spark@192.168.1.190:$SPARK_HOME/jars/

# 5. Restart Spark services
exit  # Exit spark user
sudo systemctl restart spark-master
ssh 192.168.1.187 "sudo systemctl restart spark-worker"
ssh 192.168.1.190 "sudo systemctl restart spark-worker"
sudo systemctl restart spark-history
```

**Alternative Solution: Remove Delta Lake from Configuration**

If you don't need Delta Lake, remove these lines from `$SPARK_HOME/conf/spark-defaults.conf`:
```bash
# Comment out or remove these lines
# spark.sql.extensions            io.delta.sql.DeltaSparkSessionExtension
# spark.sql.catalog.spark_catalog org.apache.spark.sql.delta.catalog.DeltaCatalog
```

**Verification:**
```bash
# Test Spark shell without warnings
sudo su - spark
cd $SPARK_HOME
./bin/spark-shell --master spark://192.168.1.184:7077

# Should start without Delta Lake warnings
# In Spark shell, test Delta Lake:
scala> import io.delta.tables._
scala> spark.range(5).write.format("delta").save("/tmp/test-delta")
scala> :quit
```

**Success Indicators:**
- ✅ No `ClassNotFoundException` warnings during startup
- ✅ Can import `io.delta.tables._` in Spark shell
- ✅ Can write Delta format tables

### 🚨 **Hyper-V Virtual Machine Specific Issues**

#### **Problem: `java.net.BindException: Cannot assign requested address`**

**Symptoms:**
- Spark worker fails to start on Hyper-V VMs
- Error: `Service 'sparkWorker' failed after 16 retries`
- All ports in range 7078-7094 fail to bind
- Multiple `Cannot assign requested address` errors

**Root Cause:**
Hyper-V's synthetic network adapter (`hv_netvsc`) creates a virtualization layer that interferes with Java/Netty binding to `0.0.0.0` (all interfaces). This is specific to:
- **Hyper-V VMs** (not VMware, KVM, or physical machines)
- **Complex IPv6 configurations** generated by Hyper-V
- **Netty binding behavior** (different from standard sockets)

**Solution 1: Explicit IP Binding (Recommended)**
```bash
# Update systemd service to use explicit IP binding
sudo nano /etc/systemd/system/spark-worker.service

# Add these environment variables and host parameter:
Environment=SPARK_LOCAL_IP=192.168.1.190
ExecStart=/home/spark/spark/sbin/start-worker.sh --host 192.168.1.190 spark://192.168.1.184:7077
```

**Solution 2: Disable IPv6 (If Solution 1 doesn't work)**
```bash
# Temporarily disable IPv6
sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
sudo sysctl -w net.ipv6.conf.eth0.disable_ipv6=1

# Make permanent
echo 'net.ipv6.conf.all.disable_ipv6 = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.default.disable_ipv6 = 1' | sudo tee -a /etc/sysctl.conf
echo 'net.ipv6.conf.eth0.disable_ipv6 = 1' | sudo tee -a /etc/sysctl.conf
```

**Verification Steps:**
```bash
# 1. Test basic network binding
nc -l 192.168.1.190 8999 &
jobs
kill %1

# 2. Test manual Spark worker with explicit IP
sudo -u spark JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64 \
  SPARK_HOME=/home/spark/spark \
  SPARK_LOCAL_IP=192.168.1.190 \
  /home/spark/spark/bin/spark-class org.apache.spark.deploy.worker.Worker \
  --webui-port 8081 --port 7078 --host 192.168.1.190 \
  spark://192.168.1.184:7077

# 3. Check IPv6 is disabled
ip addr show eth0  # Should only show IPv4 address

# 4. Restart service with new configuration
sudo systemctl daemon-reload
sudo systemctl restart spark-worker
sudo systemctl status spark-worker
```

**Success Indicators:**
- ✅ `Successfully started service 'sparkWorker' on port 7078`
- ✅ `Successfully registered with master spark://192.168.1.184:7077`
- ✅ Worker appears in Spark Master Web UI (http://192.168.1.184:8080)

#### **Hyper-V Environment Identification:**
```bash
# Check if running on Hyper-V
systemd-detect-virt          # Should return: microsoft
lsmod | grep hv_             # Should show: hv_netvsc, hv_vmbus, etc.
dmidecode -s system-manufacturer  # Should show Hyper-V related info
```

### Useful debugging commands:
```bash
# Check cluster status
$SPARK_HOME/bin/spark-shell --master spark://192.168.1.184:7077 --conf "spark.driver.bindAddress=192.168.1.184"

# Test connectivity
telnet 192.168.1.184 7077

# Check logs
tail -f $SPARK_HOME/logs/*.out

# Monitor systemd service
journalctl -u spark-worker -f

# Check network binding issues
sudo netstat -tlnp | grep java
sudo ss -tlnp | grep ":707[8-9]\|:708[0-9]\|:709[0-4]"
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
