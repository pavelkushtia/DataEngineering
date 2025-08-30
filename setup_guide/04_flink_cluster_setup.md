# Apache Flink Cluster Setup Guide

## Overview
Apache Flink will be set up in cluster mode with cpu-node1 as the JobManager and cpu-node2 as TaskManager. Worker-node3 can be added as an additional TaskManager for more processing capacity.

## Cluster Configuration
- **JobManager**: cpu-node1 (192.168.1.184) - Coordinates jobs and manages cluster
- **TaskManager 1**: cpu-node2 (192.168.1.187) - Executes tasks
- **TaskManager 2**: worker-node3 (192.168.1.190) - Optional additional capacity

## Prerequisites
- Java 8 or Java 11 installed on all nodes
- At least 4GB RAM per node
- At least 20GB free disk space per node
- SSH key-based authentication between JobManager and TaskManagers

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   worker-node3      │
│   (JobManager)      │    │  (TaskManager 1)    │    │  (TaskManager 2)    │
│  - Job Coordination │    │  - Task Execution   │    │  - Task Execution   │
│  - Checkpointing    │    │  - State Backend    │    │  - State Backend    │
│  - Web UI (8081)    │    │  - Local Storage    │    │  - Local Storage    │
│  192.168.1.184      │    │  192.168.1.187      │    │  192.168.1.190      │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Step 1: Java Installation (All Nodes)

```bash
# Install OpenJDK 11
sudo apt update
sudo apt install -y openjdk-11-jdk

# Verify Java installation
java -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

## Step 2: Create Flink User and SSH Setup

### Create flink user on all nodes:
```bash
sudo useradd -m -s /bin/bash flink
sudo passwd flink
sudo usermod -aG sudo flink
```

### Set up SSH keys (from cpu-node1):
```bash
# Switch to flink user
sudo su - flink

# Generate SSH key
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa

# Copy public key to TaskManager nodes
ssh-copy-id flink@192.168.1.187
ssh-copy-id flink@192.168.1.190

# Test SSH connectivity
ssh flink@192.168.1.187 "hostname"
ssh flink@192.168.1.190 "hostname"
```

## Step 3: Download and Install Flink (All Nodes)

```bash
# Switch to flink user
sudo su - flink
cd /home/flink

# Download Flink
wget https://downloads.apache.org/flink/flink-1.18.0/flink-1.18.0-bin-scala_2.12.tgz

# Extract and setup
tar -xzf flink-1.18.0-bin-scala_2.12.tgz
mv flink-1.18.0 flink
rm flink-1.18.0-bin-scala_2.12.tgz

# Add Flink to PATH
echo 'export FLINK_HOME=/home/flink/flink' >> ~/.bashrc
echo 'export PATH=$PATH:$FLINK_HOME/bin' >> ~/.bashrc
source ~/.bashrc
```

## Step 4: Configure Flink JobManager (cpu-node1)

### Main Flink configuration:
```bash
cd $FLINK_HOME/conf

# Backup original configuration
cp flink-conf.yaml flink-conf.yaml.backup

# Edit main configuration
nano flink-conf.yaml
```

Add these configurations:
```yaml
################################################################################
# Common Configuration
################################################################################

# JobManager and TaskManager configuration
jobmanager.rpc.address: 192.168.1.184
jobmanager.rpc.port: 6123
jobmanager.bind-host: 0.0.0.0

# Memory configuration for JobManager
jobmanager.memory.process.size: 2048m
jobmanager.memory.jvm-overhead.fraction: 0.1

# TaskManager configuration
taskmanager.memory.process.size: 4096m
taskmanager.memory.managed.fraction: 0.4
taskmanager.numberOfTaskSlots: 4

# Network configuration
taskmanager.bind-host: 0.0.0.0
taskmanager.rpc.port: 6122

# Parallelism
parallelism.default: 4

################################################################################
# High Availability Configuration
################################################################################

# Enable high availability
high-availability: zookeeper
high-availability.zookeeper.quorum: 192.168.1.184:2181,192.168.1.187:2181,192.168.1.190:2181
high-availability.storageDir: file:///home/flink/flink/ha-storage
high-availability.zookeeper.path.root: /flink

################################################################################
# Checkpointing and State Backend Configuration
################################################################################

# State backend configuration
state.backend: rocksdb
state.checkpoints.dir: file:///home/flink/flink/checkpoints
state.savepoints.dir: file:///home/flink/flink/savepoints

# Checkpoint configuration
execution.checkpointing.interval: 10000ms
execution.checkpointing.timeout: 600000ms
execution.checkpointing.min-pause: 5000ms
execution.checkpointing.max-concurrent-checkpoints: 1
execution.checkpointing.unaligned: true

# RocksDB state backend options
state.backend.rocksdb.memory.managed: true
state.backend.rocksdb.memory.fixed-per-slot: 256MB

################################################################################
# Web UI and Metrics Configuration
################################################################################

# Web UI
web.submit.enable: true
web.upload.dir: /home/flink/flink/web-uploads

# REST API
rest.port: 8081
rest.address: 192.168.1.184
rest.bind-address: 0.0.0.0

# Metrics
metrics.reporters: slf4j
metrics.reporter.slf4j.class: org.apache.flink.metrics.slf4j.Slf4jReporter
metrics.reporter.slf4j.interval: 60

################################################################################
# Network and IO Configuration  
################################################################################

# Network buffers
taskmanager.memory.network.fraction: 0.1
taskmanager.memory.network.min: 128MB
taskmanager.memory.network.max: 1GB

# IO configuration
taskmanager.network.numberOfBuffers: 2048

################################################################################
# Security Configuration
################################################################################

# SSL (optional)
security.ssl.enabled: false

################################################################################
# Integration Configuration
################################################################################

# Kafka integration
connector.kafka.sink.delivery-guarantee: at-least-once

# Checkpoint storage
state.checkpoint-storage: filesystem

################################################################################
# Resource Management
################################################################################

# Slot sharing and resource management
slotmanager.number-of-slots.max: 16
cluster.evenly-spread-out-slots: true

################################################################################
# Logging Configuration
################################################################################

# Log configuration
rootLogger.level: INFO
logger.akka.level: INFO
logger.kafka.level: INFO
logger.hadoop.level: WARN
logger.zookeeper.level: INFO
```

### Configure workers (TaskManagers):
```bash
nano workers
```

Add TaskManager hosts:
```
192.168.1.187
192.168.1.190
```

### Configure masters (JobManager):
```bash
nano masters
```

Add JobManager host:
```
192.168.1.184:8081
```

## Step 5: Create Required Directories (All Nodes)

```bash
# Create directories as flink user
sudo su - flink

mkdir -p $FLINK_HOME/ha-storage
mkdir -p $FLINK_HOME/checkpoints
mkdir -p $FLINK_HOME/savepoints
mkdir -p $FLINK_HOME/web-uploads
mkdir -p $FLINK_HOME/logs

# Set permissions
chmod 755 $FLINK_HOME/ha-storage
chmod 755 $FLINK_HOME/checkpoints
chmod 755 $FLINK_HOME/savepoints
chmod 755 $FLINK_HOME/web-uploads
```

## Step 6: Configure TaskManagers (cpu-node2 and worker-node3)

Copy configuration from JobManager to TaskManagers:

```bash
# From cpu-node1 (as flink user)
scp -r $FLINK_HOME/conf/* flink@192.168.1.187:$FLINK_HOME/conf/
scp -r $FLINK_HOME/conf/* flink@192.168.1.190:$FLINK_HOME/conf/

# Create directories on TaskManager nodes
ssh flink@192.168.1.187 "mkdir -p $FLINK_HOME/{ha-storage,checkpoints,savepoints,web-uploads,logs}"
ssh flink@192.168.1.190 "mkdir -p $FLINK_HOME/{ha-storage,checkpoints,savepoints,web-uploads,logs}"
```

## Step 7: Additional Dependencies for Data Engineering

### Download connector JARs:
```bash
cd $FLINK_HOME/lib

# Kafka SQL connector
wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/1.18.0/flink-sql-connector-kafka-1.18.0.jar

# PostgreSQL JDBC connector
wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.1.1-1.18/flink-connector-jdbc-3.1.1-1.18.jar
wget https://jdbc.postgresql.org/download/postgresql-42.7.2.jar

# Elasticsearch connector
wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-elasticsearch7/3.0.1-1.18/flink-sql-connector-elasticsearch7-3.0.1-1.18.jar

# Hadoop filesystem support
wget https://repo1.maven.org/maven2/org/apache/flink/flink-shaded-hadoop-2-uber/2.8.3-10.0/flink-shaded-hadoop-2-uber-2.8.3-10.0.jar

# Copy JARs to all nodes
scp *.jar flink@192.168.1.187:$FLINK_HOME/lib/
scp *.jar flink@192.168.1.190:$FLINK_HOME/lib/
```

## Step 8: Create Systemd Services

### JobManager Service (cpu-node1):
```bash
sudo nano /etc/systemd/system/flink-jobmanager.service
```

```ini
[Unit]
Description=Apache Flink JobManager
After=network.target
Wants=network.target

[Service]
Type=forking
User=flink
Group=flink
WorkingDirectory=/home/flink/flink
Environment=FLINK_HOME=/home/flink/flink
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/home/flink/flink/bin/jobmanager.sh start
ExecStop=/home/flink/flink/bin/jobmanager.sh stop
Restart=always
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### TaskManager Service (cpu-node2 and worker-node3):
```bash
sudo nano /etc/systemd/system/flink-taskmanager.service
```

```ini
[Unit]
Description=Apache Flink TaskManager
After=network.target
Wants=network.target

[Service]
Type=forking
User=flink
Group=flink
WorkingDirectory=/home/flink/flink
Environment=FLINK_HOME=/home/flink/flink
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/home/flink/flink/bin/taskmanager.sh start
ExecStop=/home/flink/flink/bin/taskmanager.sh stop
Restart=always
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

## Step 9: Start Flink Cluster

### Start services:
```bash
# Reload systemd on all nodes
sudo systemctl daemon-reload

# Start JobManager (cpu-node1)
sudo systemctl start flink-jobmanager
sudo systemctl enable flink-jobmanager

# Start TaskManagers (cpu-node2 and worker-node3)
sudo systemctl start flink-taskmanager
sudo systemctl enable flink-taskmanager

# Check status
sudo systemctl status flink-jobmanager
sudo systemctl status flink-taskmanager
```

### Alternative: Start using Flink scripts:
```bash
# Start entire cluster from JobManager
sudo su - flink
cd $FLINK_HOME

# Start cluster
./bin/start-cluster.sh

# Stop cluster
./bin/stop-cluster.sh
```

## Step 10: Firewall Configuration (All Nodes)

```bash
# Open required ports
sudo ufw allow 6123/tcp   # JobManager RPC port
sudo ufw allow 6122/tcp   # TaskManager RPC port
sudo ufw allow 8081/tcp   # Flink Web UI
sudo ufw allow 6124/tcp   # JobManager data port
sudo ufw reload
```

## Step 11: Testing the Cluster

### Access Flink Web UI:
Open browser and go to: http://192.168.1.184:8081

### Run WordCount example:
```bash
# As flink user
sudo su - flink
cd $FLINK_HOME

# Submit WordCount job
./bin/flink run examples/streaming/WordCount.jar

# Check running jobs
./bin/flink list

# Cancel job (replace <job-id> with actual ID)
./bin/flink cancel <job-id>
```

### Test with DataStream API:
```bash
# Create test data
echo -e "hello world\nhello flink\nworld of flink" > /tmp/input.txt

# Run SocketWindowWordCount example
./bin/flink run examples/streaming/SocketWindowWordCount.jar --hostname localhost --port 9999
```

## Step 12: SQL Client Setup

### Start SQL Client:
```bash
cd $FLINK_HOME
./bin/sql-client.sh
```

### Create sample tables and test:
```sql
-- Create a Kafka source table
CREATE TABLE kafka_source (
    id INT,
    name STRING,
    ts TIMESTAMP(3) METADATA FROM 'timestamp'
) WITH (
    'connector' = 'kafka',
    'topic' = 'test-topic',
    'properties.bootstrap.servers' = '192.168.1.184:9092',
    'properties.group.id' = 'flink-consumer',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);

-- Create a PostgreSQL sink table
CREATE TABLE postgres_sink (
    id INT,
    name STRING,
    ts TIMESTAMP(3)
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://192.168.1.184:5432/analytics_db',
    'table-name' = 'flink_output',
    'username' = 'dataeng',
    'password' = 'password'
);

-- Simple streaming SQL query
INSERT INTO postgres_sink
SELECT id, name, ts
FROM kafka_source;
```

## Step 13: Advanced Configuration

### Memory tuning for TaskManagers:
```yaml
# Add to flink-conf.yaml for production workloads
taskmanager.memory.process.size: 8192m
taskmanager.memory.flink.size: 6144m
taskmanager.memory.managed.size: 2048m
taskmanager.memory.task.heap.size: 3072m

# JVM options
env.java.opts.jobmanager: "-XX:+UseG1GC -XX:MaxGCPauseMillis=200"
env.java.opts.taskmanager: "-XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:+HeapDumpOnOutOfMemoryError"
```

### Checkpoint optimization:
```yaml
# Incremental checkpoints for RocksDB
state.backend.incremental: true

# Checkpoint cleanup
state.checkpoints.num-retained: 3
state.checkpoint.cleanup.on-recovery: true

# Async snapshots
state.backend.async: true
```

## Step 14: Sample Applications

### Create Python PyFlink application:
```bash
mkdir -p /home/flink/apps
nano /home/flink/apps/word_count.py
```

```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment
from pyflink.common.typeinfo import Types
from pyflink.datastream.functions import FlatMapFunction, ReduceFunction
from pyflink.common import Row

class WordCountFlatMap(FlatMapFunction):
    def flat_map(self, value):
        for word in value[1].lower().split():
            yield Row(word, 1)

class WordCountReduce(ReduceFunction):
    def reduce(self, value1, value2):
        return Row(value1[0], value1[1] + value2[1])

def word_count():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)
    
    # Create input data stream
    text_stream = env.from_collection([
        (1, "Hello World"),
        (2, "Hello Flink"),
        (3, "World of Flink")
    ])
    
    # Transform and count words
    word_count_stream = text_stream \
        .flat_map(WordCountFlatMap(), output_type=Types.ROW([Types.STRING(), Types.INT()])) \
        .key_by(lambda x: x[0]) \
        .reduce(WordCountReduce())
    
    # Print results
    word_count_stream.print()
    
    # Execute
    env.execute("Word Count")

if __name__ == '__main__':
    word_count()
```

### Run PyFlink application:
```bash
# Install PyFlink
pip3 install apache-flink

# Run application
python3 /home/flink/apps/word_count.py
```

## Step 15: Integration Examples

### Kafka to PostgreSQL streaming:
```java
// Java application example
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

// Kafka source
FlinkKafkaConsumer<String> kafkaSource = new FlinkKafkaConsumer<>(
    "input-topic",
    new SimpleStringSchema(),
    kafkaProps
);

// PostgreSQL sink
JdbcSink<Tuple2<String, Integer>> postgresqlSink = JdbcSink
    .<Tuple2<String, Integer>>sink(
        "INSERT INTO word_count (word, count) VALUES (?, ?) ON CONFLICT (word) DO UPDATE SET count = ?",
        (statement, tuple) -> {
            statement.setString(1, tuple.f0);
            statement.setInt(2, tuple.f1);
            statement.setInt(3, tuple.f1);
        },
        jdbcConnectionOptions
    );

// Processing pipeline
env.addSource(kafkaSource)
   .flatMap(new WordTokenizer())
   .keyBy(value -> value.f0)
   .window(TumblingProcessingTimeWindows.of(Time.minutes(1)))
   .sum(1)
   .addSink(postgresqlSink);

env.execute("Kafka to PostgreSQL");
```

## Monitoring and Logging

### Log locations:
- JobManager logs: `/home/flink/flink/log/flink-flink-jobmanager-*.log`
- TaskManager logs: `/home/flink/flink/log/flink-flink-taskmanager-*.log`

### Monitoring queries:
```bash
# Check cluster status
curl http://192.168.1.184:8081/overview

# Check running jobs
curl http://192.168.1.184:8081/jobs

# Check TaskManager status
curl http://192.168.1.184:8081/taskmanagers
```

### Metrics integration:
```yaml
# Add to flink-conf.yaml for Prometheus integration
metrics.reporters: prom
metrics.reporter.prom.class: org.apache.flink.metrics.prometheus.PrometheusReporter
metrics.reporter.prom.port: 9249
```

## Performance Tuning

### Network buffer optimization:
```yaml
taskmanager.memory.network.fraction: 0.15
taskmanager.memory.network.min: 256MB
taskmanager.memory.network.max: 2GB
taskmanager.network.numberOfBuffers: 4096
```

### Parallelism and resource optimization:
```yaml
parallelism.default: 8
taskmanager.numberOfTaskSlots: 4
slotmanager.number-of-slots.max: 32
```

## Troubleshooting

### Common Issues:
1. **TaskManager not connecting**: Check network connectivity and ports
2. **OutOfMemory errors**: Increase TaskManager memory or tune GC
3. **Checkpoint failures**: Check filesystem permissions and storage
4. **High latency**: Optimize network buffers and checkpoint intervals

### Debugging commands:
```bash
# Check Flink processes
jps | grep -i flink

# Check logs
tail -f $FLINK_HOME/log/*.log

# Test network connectivity
telnet 192.168.1.184 6123
```

## Backup and Maintenance

### Backup savepoints:
```bash
# Create savepoint
./bin/flink savepoint <job-id> file:///home/flink/flink/savepoints/

# Restore from savepoint
./bin/flink run -s file:///home/flink/flink/savepoints/savepoint-xxx myapp.jar
```

### Regular maintenance:
```bash
# Clean old checkpoints (automated by Flink)
# Clean old logs
find $FLINK_HOME/log -name "*.log" -mtime +7 -delete

# Backup configuration
tar -czf flink-config-backup-$(date +%Y%m%d).tar.gz $FLINK_HOME/conf
```

## Security Considerations

### Enable SSL (optional):
```yaml
security.ssl.enabled: true
security.ssl.keystore: /path/to/flink.keystore
security.ssl.keystore-password: password
security.ssl.key-password: password
security.ssl.truststore: /path/to/flink.truststore
security.ssl.truststore-password: password
```

### Network security:
- Use VPN or private networks for inter-node communication
- Configure firewall rules to restrict access
- Enable authentication if exposing web UI externally
