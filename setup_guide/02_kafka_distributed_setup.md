# Apache Kafka Distributed Setup Guide

## Overview
Apache Kafka will be set up as a distributed cluster across multiple nodes for high availability and scalability in the Data Engineering HomeLab.

## Cluster Configuration
- **Kafka Broker 1**: cpu-node1 (192.168.1.184) - Primary broker
- **Kafka Broker 2**: cpu-node2 (192.168.1.187) - Secondary broker  
- **Kafka Broker 3**: worker-node3 (192.168.1.190) - Optional third broker for full redundancy

## Prerequisites
- Java 11 or later installed on all nodes
- At least 4GB RAM per node
- At least 50GB free disk space per node for Kafka logs
- Network connectivity between all nodes

## Architecture Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   cpu-node1     │    │   cpu-node2     │    │  worker-node3   │
│ (Kafka Broker 1)│    │ (Kafka Broker 2)│    │ (Kafka Broker 3)│
│ ZooKeeper 1     │    │ ZooKeeper 2     │    │ ZooKeeper 3     │
│ 192.168.1.184   │    │ 192.168.1.187   │    │ 192.168.1.190   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Step 1: Java Installation (All Nodes)

```bash
# Install OpenJDK 11
sudo apt update
sudo apt install -y openjdk-11-jdk

# Verify Java installation
java -version
javac -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

## Step 2: Download and Install Kafka (All Nodes)

```bash
# Create kafka user
sudo useradd -r -s /bin/false kafka

# Download Kafka
cd /opt
sudo wget https://downloads.apache.org/kafka/2.8.2/kafka_2.13-2.8.2.tgz
sudo tar -xzf kafka_2.13-2.8.2.tgz
sudo mv kafka_2.13-2.8.2 kafka
sudo chown -R kafka:kafka /opt/kafka

# Create data directories
sudo mkdir -p /var/lib/kafka/logs
sudo mkdir -p /var/lib/zookeeper
sudo chown -R kafka:kafka /var/lib/kafka
sudo chown -R kafka:kafka /var/lib/zookeeper
```

## Step 3: ZooKeeper Configuration (All Nodes)

### Create ZooKeeper configuration on cpu-node1:
```bash
sudo nano /opt/kafka/config/zookeeper.properties
```

```properties
# cpu-node1 ZooKeeper configuration
dataDir=/var/lib/zookeeper
clientPort=2181
maxClientCnxns=0
admin.enableServer=false

# ZooKeeper cluster configuration
initLimit=10
syncLimit=5
server.1=192.168.1.184:2888:3888
server.2=192.168.1.187:2888:3888
server.3=192.168.1.190:2888:3888
```

### Create ZooKeeper configuration on cpu-node2:
```bash
sudo nano /opt/kafka/config/zookeeper.properties
```

```properties
# cpu-node2 ZooKeeper configuration
dataDir=/var/lib/zookeeper
clientPort=2181
maxClientCnxns=0
admin.enableServer=false

# ZooKeeper cluster configuration
initLimit=10
syncLimit=5
server.1=192.168.1.184:2888:3888
server.2=192.168.1.187:2888:3888
server.3=192.168.1.190:2888:3888
```

### Create ZooKeeper configuration on worker-node3:
```bash
sudo nano /opt/kafka/config/zookeeper.properties
```

```properties
# worker-node3 ZooKeeper configuration
dataDir=/var/lib/zookeeper
clientPort=2181
maxClientCnxns=0
admin.enableServer=false

# ZooKeeper cluster configuration
initLimit=10
syncLimit=5
server.1=192.168.1.184:2888:3888
server.2=192.168.1.187:2888:3888
server.3=192.168.1.190:2888:3888
```

### Create ZooKeeper ID files:

**On cpu-node1:**
```bash
echo "1" | sudo tee /var/lib/zookeeper/myid
```

**On cpu-node2:**
```bash
echo "2" | sudo tee /var/lib/zookeeper/myid
```

**On worker-node3:**
```bash
echo "3" | sudo tee /var/lib/zookeeper/myid
```

## Step 4: Kafka Broker Configuration

### Kafka configuration on cpu-node1:
```bash
sudo nano /opt/kafka/config/server.properties
```

```properties
# cpu-node1 Kafka Broker configuration
broker.id=1
listeners=PLAINTEXT://192.168.1.184:9092
advertised.listeners=PLAINTEXT://192.168.1.184:9092
log.dirs=/var/lib/kafka/logs
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Log configuration
num.partitions=3
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

# ZooKeeper
zookeeper.connect=192.168.1.184:2181,192.168.1.187:2181,192.168.1.190:2181
zookeeper.connection.timeout.ms=18000

# Group coordinator configuration
group.initial.rebalance.delay.ms=0

# Performance tuning
replica.fetch.max.bytes=1048576
message.max.bytes=1000012
replica.socket.timeout.ms=30000
replica.socket.receive.buffer.bytes=65536
```

### Kafka configuration on cpu-node2:
```bash
sudo nano /opt/kafka/config/server.properties
```

```properties
# cpu-node2 Kafka Broker configuration
broker.id=2
listeners=PLAINTEXT://192.168.1.187:9092
advertised.listeners=PLAINTEXT://192.168.1.187:9092
log.dirs=/var/lib/kafka/logs
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Log configuration
num.partitions=3
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

# ZooKeeper
zookeeper.connect=192.168.1.184:2181,192.168.1.187:2181,192.168.1.190:2181
zookeeper.connection.timeout.ms=18000

# Group coordinator configuration
group.initial.rebalance.delay.ms=0

# Performance tuning
replica.fetch.max.bytes=1048576
message.max.bytes=1000012
replica.socket.timeout.ms=30000
replica.socket.receive.buffer.bytes=65536
```

### Kafka configuration on worker-node3:
```bash
sudo nano /opt/kafka/config/server.properties
```

```properties
# worker-node3 Kafka Broker configuration
broker.id=3
listeners=PLAINTEXT://192.168.1.190:9092
advertised.listeners=PLAINTEXT://192.168.1.190:9092
log.dirs=/var/lib/kafka/logs
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Log configuration
num.partitions=3
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

# ZooKeeper
zookeeper.connect=192.168.1.184:2181,192.168.1.187:2181,192.168.1.190:2181
zookeeper.connection.timeout.ms=18000

# Group coordinator configuration
group.initial.rebalance.delay.ms=0

# Performance tuning
replica.fetch.max.bytes=1048576
message.max.bytes=1000012
replica.socket.timeout.ms=30000
replica.socket.receive.buffer.bytes=65536
```

## Step 5: Create Systemd Services (All Nodes)

### ZooKeeper service:
```bash
sudo nano /etc/systemd/system/zookeeper.service
```

```ini
[Unit]
Description=Apache ZooKeeper
After=network.target

[Service]
Type=forking
User=kafka
Group=kafka
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/opt/kafka/bin/zookeeper-server-start.sh -daemon /opt/kafka/config/zookeeper.properties
ExecStop=/opt/kafka/bin/zookeeper-server-stop.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Kafka service:
```bash
sudo nano /etc/systemd/system/kafka.service
```

```ini
[Unit]
Description=Apache Kafka
After=network.target zookeeper.service
Requires=zookeeper.service

[Service]
Type=forking
User=kafka
Group=kafka
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/opt/kafka/bin/kafka-server-start.sh -daemon /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Step 6: Start Services (All Nodes)

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start ZooKeeper first (on all nodes)
sudo systemctl start zookeeper
sudo systemctl enable zookeeper

# Wait a few seconds, then start Kafka (on all nodes)
sleep 10
sudo systemctl start kafka
sudo systemctl enable kafka

# Check service status
sudo systemctl status zookeeper
sudo systemctl status kafka
```

## Step 7: Firewall Configuration (All Nodes)

```bash
# Open required ports
sudo ufw allow 2181/tcp  # ZooKeeper client port
sudo ufw allow 2888/tcp  # ZooKeeper peer communication
sudo ufw allow 3888/tcp  # ZooKeeper leader election
sudo ufw allow 9092/tcp  # Kafka broker port
sudo ufw reload
```

## Step 8: Testing the Cluster

### Create a test topic:
```bash
# Run from any node
/opt/kafka/bin/kafka-topics.sh --create \
  --topic test-topic \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 \
  --partitions 6 \
  --replication-factor 3
```

### List topics:
```bash
/opt/kafka/bin/kafka-topics.sh --list \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
```

### Describe topic:
```bash
/opt/kafka/bin/kafka-topics.sh --describe \
  --topic test-topic \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
```

### Producer test:
```bash
/opt/kafka/bin/kafka-console-producer.sh \
  --topic test-topic \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
```

### Consumer test:
```bash
/opt/kafka/bin/kafka-console-consumer.sh \
  --topic test-topic \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 \
  --from-beginning
```

## Step 9: Kafka Connect Setup (Optional)

### Install Kafka Connect on cpu-node1:
```bash
# Kafka Connect is included with Kafka
# Create Connect configuration
sudo nano /opt/kafka/config/connect-distributed.properties
```

```properties
# Kafka Connect Distributed Mode Configuration
bootstrap.servers=192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
group.id=connect-cluster
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=true
value.converter.schemas.enable=true
offset.storage.topic=connect-offsets
offset.storage.replication.factor=3
config.storage.topic=connect-configs
config.storage.replication.factor=3
status.storage.topic=connect-status
status.storage.replication.factor=3
offset.flush.interval.ms=10000
rest.host.name=192.168.1.184
rest.port=8083
```

## Performance Tuning

### JVM Options for Kafka:
Create `/opt/kafka/bin/kafka-server-start-custom.sh`:

```bash
#!/bin/bash
export KAFKA_HEAP_OPTS="-Xmx2G -Xms2G"
export KAFKA_JVM_PERFORMANCE_OPTS="-server -XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:+ExplicitGCInvokesConcurrent -XX:MaxInlineLevel=15 -Djava.awt.headless=true"
/opt/kafka/bin/kafka-server-start.sh "$@"
```

### Operating System tuning:
```bash
# Add to /etc/sysctl.conf
vm.swappiness=1
vm.dirty_ratio=80
vm.dirty_background_ratio=5
net.core.rmem_default=262144
net.core.rmem_max=16777216
net.core.wmem_default=262144
net.core.wmem_max=16777216

# Apply changes
sudo sysctl -p
```

## Monitoring

### Useful monitoring commands:
```bash
# Check cluster metadata
/opt/kafka/bin/kafka-metadata-shell.sh --snapshot /var/lib/kafka/logs/__cluster_metadata-0/00000000000000000000.log

# Monitor consumer lag
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server 192.168.1.184:9092 --describe --all-groups

# Check broker logs
tail -f /opt/kafka/logs/server.log

# ZooKeeper status
echo "ruok" | nc 192.168.1.184 2181
```

### Kafka Manager (Optional UI):
```bash
# Install Kafka Manager on cpu-node1
cd /opt
sudo wget https://github.com/yahoo/CMAK/releases/download/3.0.0.5/cmak-3.0.0.5.zip
sudo unzip cmak-3.0.0.5.zip
sudo mv cmak-3.0.0.5 kafka-manager
sudo chown -R kafka:kafka kafka-manager

# Configure and start
# Edit application.conf to point to your ZooKeeper cluster
```

## High Availability Considerations

1. **Replication Factor**: Always use replication factor ≥ 3 for important topics
2. **Min In-Sync Replicas**: Set `min.insync.replicas=2` for critical topics
3. **Acks Configuration**: Use `acks=all` for producers requiring durability
4. **Unclean Leader Election**: Set `unclean.leader.election.enable=false`

## Backup and Recovery

```bash
# Backup Kafka topics
/opt/kafka/bin/kafka-mirror-maker.sh --consumer.config consumer.properties --producer.config producer.properties --whitelist=".*"

# Backup ZooKeeper data
sudo tar -czf zookeeper-backup-$(date +%Y%m%d).tar.gz /var/lib/zookeeper
```

## Integration with Other Components

- **Spark Integration**: Use Spark Streaming with Kafka for real-time processing
- **Flink Integration**: Use Flink Kafka connectors for stream processing
- **PostgreSQL Integration**: Use Debezium for CDC from PostgreSQL to Kafka
- **Schema Registry**: Consider Confluent Schema Registry for Avro/JSON schema management

## Troubleshooting

### Common Issues:
1. **OutOfMemory errors**: Increase heap size in KAFKA_HEAP_OPTS
2. **Network partitions**: Check ZooKeeper connectivity
3. **Slow consumers**: Monitor consumer lag and tune fetch settings
4. **Disk space**: Monitor log retention and cleanup policies

### Log Locations:
- Kafka logs: `/opt/kafka/logs/server.log`
- ZooKeeper logs: `/opt/kafka/logs/zookeeper.out`
- Data directories: `/var/lib/kafka/logs/`, `/var/lib/zookeeper/`
