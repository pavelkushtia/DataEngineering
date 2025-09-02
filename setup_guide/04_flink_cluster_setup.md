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

# Download Flink 1.19.3 (stable version)
wget https://downloads.apache.org/flink/flink-1.19.3/flink-1.19.3-bin-scala_2.12.tgz

# Extract and setup
tar -xzf flink-1.19.3-bin-scala_2.12.tgz
mv flink-1.19.3 flink
rm flink-1.19.3-bin-scala_2.12.tgz

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

# Kafka SQL connector (compatible with Flink 1.19.x)
wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.3.0-1.19/flink-sql-connector-kafka-3.3.0-1.19.jar

# PostgreSQL JDBC connector (compatible with Flink 1.19.x)
wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc/3.3.0-1.19/flink-connector-jdbc-3.3.0-1.19.jar
wget https://jdbc.postgresql.org/download/postgresql-42.7.2.jar

# PostgreSQL CDC connector (for real-time change data capture)
wget https://repo1.maven.org/maven2/com/ververica/flink-connector-postgres-cdc/3.0.1/flink-connector-postgres-cdc-3.0.1.jar

# Elasticsearch connector (compatible with Flink 1.19.x)
wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-elasticsearch7/3.1.0-1.19/flink-sql-connector-elasticsearch7-3.1.0-1.19.jar

# Hadoop filesystem support (for basic file I/O)
wget https://repo1.maven.org/maven2/org/apache/flink/flink-shaded-hadoop-2-uber/2.8.3-10.0/flink-shaded-hadoop-2-uber-2.8.3-10.0.jar

# Iceberg connector (for Iceberg table format)
wget https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-1.19/1.9.2/iceberg-flink-runtime-1.19-1.9.2.jar

# Delta Lake connector (for Delta Lake table format)
wget https://repo1.maven.org/maven2/io/delta/delta-flink/3.3.2/delta-flink-3.3.2.jar

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

### PostgreSQL CDC Real-Time Streaming:

**Step 1: SQL API - Create CDC Source Table:**
```sql
-- Connect to Flink SQL CLI
./bin/sql-client.sh

-- Create PostgreSQL CDC source table
CREATE TABLE user_events_cdc (
    id BIGINT,
    user_id INT,
    event_type STRING,
    event_data STRING,
    created_at TIMESTAMP(3),
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '192.168.1.184',
    'port' = '5432',
    'username' = 'cdc_user',
    'password' = 'cdc_password123',
    'database-name' = 'analytics_db',
    'schema-name' = 'public',
    'table-name' = 'user_events',
    'slot.name' = 'flink_cdc_slot'
);

-- Create Kafka sink table for CDC events
CREATE TABLE user_events_kafka (
    id BIGINT,
    user_id INT,
    event_type STRING,
    event_data STRING,
    created_at TIMESTAMP(3)
) WITH (
    'connector' = 'kafka',
    'topic' = 'flink-cdc-user-events',
    'properties.bootstrap.servers' = '192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092',
    'format' = 'json'
);

-- Stream CDC changes to Kafka
INSERT INTO user_events_kafka 
SELECT * FROM user_events_cdc;
```

**Step 2: Java API - PostgreSQL CDC to Analytics:**
```java
import com.ververica.cdc.connectors.postgres.PostgreSQLSource;
import com.ververica.cdc.debezium.JsonDebeziumDeserializationSchema;

public class PostgresCDCJob {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        
        // Enable checkpointing for exactly-once processing
        env.enableCheckpointing(5000);
        
        // PostgreSQL CDC Source
        SourceFunction<String> postgresSource = PostgreSQLSource.<String>builder()
            .hostname("192.168.1.184")
            .port(5432)
            .database("analytics_db")
            .schemaList("public")
            .tableList("public.user_events,public.orders")
            .username("cdc_user")
            .password("cdc_password123")
            .slotName("flink_cdc_slot")
            .deserializer(new JsonDebeziumDeserializationSchema())
            .build();
        
        // Process CDC stream
        DataStream<String> cdcStream = env.addSource(postgresSource)
            .name("PostgreSQL CDC Source");
            
        // Parse and transform CDC events
        DataStream<UserEvent> events = cdcStream
            .map(new CDCEventParser())
            .filter(event -> event.getOperation().equals("INSERT") || 
                           event.getOperation().equals("UPDATE"));
        
        // Real-time aggregations
        DataStream<UserEventStats> stats = events
            .keyBy(UserEvent::getEventType)
            .window(TumblingProcessingTimeWindows.of(Time.minutes(1)))
            .aggregate(new UserEventAggregator());
        
        // Sink to analytics store
        stats.addSink(JdbcSink.sink(
            "INSERT INTO event_stats (event_type, count, window_start) VALUES (?, ?, ?)",
            new UserEventStatsSinkFunction(),
            JdbcExecutionOptions.builder()
                .withBatchSize(100)
                .withBatchIntervalMs(1000)
                .build(),
            new JdbcConnectionOptions.JdbcConnectionOptionsBuilder()
                .withUrl("jdbc:postgresql://192.168.1.184:5432/analytics_db")
                .withDriverName("org.postgresql.Driver")
                .withUsername("dataeng")
                .withPassword("dataeng_password")
                .build()
        ));
        
        env.execute("PostgreSQL CDC Analytics Job");
    }
}
```

**Step 3: CDC Event Processing Functions:**
```java
// CDC Event Parser
public class CDCEventParser implements MapFunction<String, UserEvent> {
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    @Override
    public UserEvent map(String cdcJson) throws Exception {
        JsonNode root = objectMapper.readTree(cdcJson);
        JsonNode payload = root.get("payload");
        
        UserEvent event = new UserEvent();
        event.setOperation(payload.get("op").asText());
        
        JsonNode after = payload.get("after");
        if (after != null) {
            event.setId(after.get("id").asLong());
            event.setUserId(after.get("user_id").asInt());
            event.setEventType(after.get("event_type").asText());
            event.setEventData(after.get("event_data").asText());
            event.setCreatedAt(Instant.ofEpochMilli(after.get("created_at").asLong()));
        }
        
        return event;
    }
}

// User Event Aggregator
public class UserEventAggregator implements AggregateFunction<UserEvent, UserEventStats, UserEventStats> {
    @Override
    public UserEventStats createAccumulator() {
        return new UserEventStats();
    }
    
    @Override
    public UserEventStats add(UserEvent event, UserEventStats accumulator) {
        accumulator.setEventType(event.getEventType());
        accumulator.setCount(accumulator.getCount() + 1);
        accumulator.setWindowStart(Instant.now());
        return accumulator;
    }
    
    @Override
    public UserEventStats getResult(UserEventStats accumulator) {
        return accumulator;
    }
    
    @Override
    public UserEventStats merge(UserEventStats a, UserEventStats b) {
        UserEventStats result = new UserEventStats();
        result.setEventType(a.getEventType());
        result.setCount(a.getCount() + b.getCount());
        result.setWindowStart(a.getWindowStart());
        return result;
    }
}
```

**Step 4: Test CDC Streaming:**
```bash
# Submit CDC job
./bin/flink run \
  --class PostgresCDCJob \
  --jobmanager 192.168.1.184:8081 \
  /path/to/postgres-cdc-job.jar

# Test by inserting data in PostgreSQL
psql -h 192.168.1.184 -U dataeng -d analytics_db -c \
"INSERT INTO user_events (user_id, event_type, event_data) VALUES (2001, 'page_view', '{\"page\": \"/dashboard\", \"duration\": 120}');"

# Check Flink UI for job status: http://192.168.1.184:8081
# Check output in analytics tables or Kafka topics
```

**Step 5: Advanced CDC Configuration:**
```sql
-- Multiple table CDC with pattern matching
CREATE TABLE all_events_cdc (
    table_name STRING METADATA FROM 'table_name' VIRTUAL,
    id BIGINT,
    data ROW<user_id INT, event_type STRING, created_at TIMESTAMP(3)>,
    PRIMARY KEY (id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '192.168.1.184',
    'port' = '5432',
    'username' = 'cdc_user',
    'password' = 'cdc_password123',
    'database-name' = 'analytics_db',
    'schema-name' = 'public',
    'table-name' = 'user_events|orders|products',  -- Multiple tables
    'slot.name' = 'flink_multi_cdc_slot',
    'debezium.snapshot.mode' = 'initial'  -- Include existing data
);

-- Route different tables to different topics
CREATE TABLE events_by_table AS
SELECT 
    table_name,
    id,
    data,
    CASE 
        WHEN table_name = 'user_events' THEN 'events'
        WHEN table_name = 'orders' THEN 'orders'  
        WHEN table_name = 'products' THEN 'products'
    END as topic_suffix
FROM all_events_cdc;
```

### 🔧 CDC Monitoring and Troubleshooting:

**Monitor CDC lag:**
```sql
-- In PostgreSQL, check replication slots
SELECT slot_name, plugin, slot_type, database, active, 
       pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) as lag_bytes
FROM pg_replication_slots 
WHERE slot_name LIKE 'flink%';

-- Check if slot is active
SELECT * FROM pg_stat_replication WHERE application_name LIKE 'flink%';
```

**Flink CDC job monitoring:**
```bash
# Check job status
curl -s http://192.168.1.184:8081/jobs | jq '.jobs[] | select(.name | contains("CDC"))'

# Monitor CDC source metrics  
curl -s "http://192.168.1.184:8081/jobs/{job-id}/metrics?get=Source__PostgreSQL_CDC.numRecordsOut"

# Check for CDC errors in logs
grep -i "cdc\|postgres" /home/flink/flink/log/flink-flink-taskmanager-*.log
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
