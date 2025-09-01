# Apache Kafka Distributed Setup Guide

## 📖 Architecture Guide

**🎯 New to Kafka?** Read our comprehensive **[Kafka Architecture Guide](../architecture/kafka_architecture_guide.md)** first!

This architecture guide explains:
- How Kafka's distributed architecture works with YOUR exact setup
- Message flow and partition distribution with detailed diagrams
- ZooKeeper cluster coordination and broker management
- How to scale from 3 to 5 or 7 nodes
- Performance impact and fault tolerance analysis

---

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

# Download Kafka (Current stable version)
cd /opt
sudo wget https://downloads.apache.org/kafka/3.9.1/kafka_2.13-3.9.1.tgz
sudo tar -xzf kafka_2.13-3.9.1.tgz
sudo mv kafka_2.13-3.9.1 kafka

# Note: If the above version is not available, check the latest version at:
# https://kafka.apache.org/downloads
# Alternative download command for any version:
# sudo wget https://archive.apache.org/dist/kafka/[VERSION]/kafka_2.13-[VERSION].tgz
sudo chown -R kafka:kafka /opt/kafka

# Create data directories
sudo mkdir -p /var/lib/kafka/logs
sudo mkdir -p /var/lib/zookeeper
sudo chown -R kafka:kafka /var/lib/kafka
sudo chown -R kafka:kafka /var/lib/zookeeper
```

## Step 3: ZooKeeper Configuration (All Nodes)

**The ZooKeeper configuration is IDENTICAL on all three nodes.** Create the same file on each:

### On ALL nodes (cpu-node1, cpu-node2, worker-node3):
```bash
sudo nano /opt/kafka/config/zookeeper.properties
```

```properties
# ZooKeeper configuration (same on all nodes)
dataDir=/var/lib/zookeeper
clientPort=2181
maxClientCnxns=0
admin.enableServer=false

# ZooKeeper cluster configuration (all nodes listed)
initLimit=10
syncLimit=5
server.1=192.168.1.184:2888:3888
server.2=192.168.1.187:2888:3888
server.3=192.168.1.190:2888:3888
```

### Create unique ZooKeeper ID files (ONLY difference per node):

**On cpu-node1 (192.168.1.184):**
```bash
echo "1" | sudo tee /var/lib/zookeeper/myid
```

**On cpu-node2 (192.168.1.187):**
```bash
echo "2" | sudo tee /var/lib/zookeeper/myid
```

**On worker-node3 (192.168.1.190):**
```bash
echo "3" | sudo tee /var/lib/zookeeper/myid
```

💡 **Key Point**: The configuration file is identical across all nodes. Only the `myid` file differs (1, 2, 3).

## Step 4: Kafka Broker Configuration

**Most of the Kafka configuration is IDENTICAL on all nodes.** Use this template on each node:

### On ALL nodes, create the base configuration:
```bash
sudo nano /opt/kafka/config/server.properties
```

**Common configuration (same on all nodes):**
```properties
# Basic Kafka configuration
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

# ZooKeeper (same cluster connection for all brokers)
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

### Node-specific settings (ONLY differences per node):

**cpu-node1 (192.168.1.184) - ADD these lines:**
```properties
broker.id=1
listeners=PLAINTEXT://192.168.1.184:9092
advertised.listeners=PLAINTEXT://192.168.1.184:9092
```

**cpu-node2 (192.168.1.187) - ADD these lines:**
```properties
broker.id=2
listeners=PLAINTEXT://192.168.1.187:9092
advertised.listeners=PLAINTEXT://192.168.1.187:9092
```

**worker-node3 (192.168.1.190) - ADD these lines:**
```properties
broker.id=3
listeners=PLAINTEXT://192.168.1.190:9092
advertised.listeners=PLAINTEXT://192.168.1.190:9092
```

💡 **Key Point**: Use the same common configuration + add the 3 node-specific lines for each broker.

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
# REST API settings - bind to all interfaces but advertise specific IP
rest.host.name=0.0.0.0
rest.port=8083
rest.advertised.host.name=192.168.1.184
rest.advertised.port=8083
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

### 📋 Quick Reference - Where to Run Monitoring Commands:

| Command Type | Where to Run | Example |
|--------------|-------------|---------|
| **Cluster-wide commands** | Any node | Consumer lag, topic management |
| **Node-specific logs** | Each specific node | `tail -f /opt/kafka/logs/server.log` |
| **ZooKeeper status** | Any node (local or remote) | `echo "ruok" \| nc <IP> 2181` |
| **Kafka Connect** | cpu-node1 only | `curl localhost:8083/connectors` |
| **Health check script** | Any node or external machine | Comprehensive cluster status |

**🚨 Important:** Use the node's IP address, **NOT localhost**:
- **cpu-node1**: Use `192.168.1.184:9092`
- **cpu-node2**: Use `192.168.1.187:9092`
- **worker-node3**: Use `192.168.1.190:9092`

### 📊 Cluster-wide monitoring (run from ANY node):
```bash
# Monitor consumer lag across all brokers
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 \
  --describe --all-groups

# List all topics in cluster
/opt/kafka/bin/kafka-topics.sh --list \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092

# Check topic details and partition distribution
/opt/kafka/bin/kafka-topics.sh --describe \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092

# Check broker configurations
/opt/kafka/bin/kafka-configs.sh --bootstrap-server 192.168.1.184:9092 \
  --entity-type brokers --describe
```

### 🖥️ Node-specific monitoring (run on each node):

**On cpu-node1 (192.168.1.184):**
```bash
# Check local broker logs
tail -f /opt/kafka/logs/server.log

# Check local ZooKeeper logs  
tail -f /opt/kafka/logs/zookeeper.out

# Check broker metadata (ZooKeeper mode) - use node's IP, not localhost
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server 192.168.1.184:9092

# List log directories and segments
ls -la /var/lib/kafka/logs/

# Check specific topic log segments (example)
ls -la /var/lib/kafka/logs/test-topic-*/ 2>/dev/null || echo "No test-topic found"

# Local ZooKeeper status
echo "ruok" | nc localhost 2181
# or: echo "ruok" | nc 192.168.1.184 2181

# Check Kafka Connect status (if running Connect on this node)
curl -s localhost:8083/connectors | jq
systemctl status kafka-connect
```

**On cpu-node2 (192.168.1.187):**
```bash
# Check local broker logs
tail -f /opt/kafka/logs/server.log

# Check local ZooKeeper logs
tail -f /opt/kafka/logs/zookeeper.out

# Check broker metadata for THIS node
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server 192.168.1.187:9092

# Local ZooKeeper status  
echo "ruok" | nc localhost 2181
# or: echo "ruok" | nc 192.168.1.187 2181
```

**On worker-node3 (192.168.1.190):**
```bash
# Check local broker logs
tail -f /opt/kafka/logs/server.log

# Check local ZooKeeper logs
tail -f /opt/kafka/logs/zookeeper.out

# Check broker metadata for THIS node
/opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server 192.168.1.190:9092

# Local ZooKeeper status
echo "ruok" | nc localhost 2181  
# or: echo "ruok" | nc 192.168.1.190 2181
```

### 🌐 Remote monitoring (run from external machine or any node):
```bash
# Check ZooKeeper cluster health from any node
echo "ruok" | nc 192.168.1.184 2181  # Should return "imok"
echo "ruok" | nc 192.168.1.187 2181  # Should return "imok"
echo "ruok" | nc 192.168.1.190 2181  # Should return "imok"

# Get ZooKeeper cluster status
echo "stat" | nc 192.168.1.184 2181

# Check if Kafka brokers are reachable
nc -zv 192.168.1.184 9092
nc -zv 192.168.1.187 9092  
nc -zv 192.168.1.190 9092

# Test Kafka Connect REST API (if running on cpu-node1)
curl -s 192.168.1.184:8083/ | jq
```

### 🔍 ZooKeeper Cluster Metadata (run from any node):
```bash
# Check ZooKeeper cluster members
echo "conf" | nc 192.168.1.184 2181

# List brokers registered in ZooKeeper
/opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092

# Check ZooKeeper broker registration
/opt/kafka/bin/zookeeper-shell.sh 192.168.1.184:2181 <<< "ls /brokers/ids"

# Check topic metadata in ZooKeeper  
/opt/kafka/bin/zookeeper-shell.sh 192.168.1.184:2181 <<< "ls /brokers/topics"

# Check controller information
/opt/kafka/bin/zookeeper-shell.sh 192.168.1.184:2181 <<< "get /controller"

# Verify cluster ID
/opt/kafka/bin/zookeeper-shell.sh 192.168.1.184:2181 <<< "get /cluster/id"
```

### 📈 Continuous monitoring script (run from monitoring node):
```bash
# Create monitoring script
cat > /tmp/kafka-health-check.sh << 'EOF'
#!/bin/bash
echo "=== Kafka Cluster Health Check $(date) ==="

echo "## ZooKeeper Status:"
for host in 192.168.1.184 192.168.1.187 192.168.1.190; do
  echo -n "$host:2181 - "
  echo "ruok" | nc -w 2 $host 2181 || echo "DOWN"
done

echo -e "\n## Kafka Broker Status:" 
for host in 192.168.1.184 192.168.1.187 192.168.1.190; do
  echo -n "$host:9092 - "
  nc -zv -w 2 $host 9092 2>&1 | grep -q "succeeded" && echo "UP" || echo "DOWN"
done

echo -e "\n## Topic Count:"
/opt/kafka/bin/kafka-topics.sh --list \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 \
  | wc -l

echo -e "\n## Consumer Group Lag:"
/opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 \
  --describe --all-groups | grep -E "GROUP|LAG"

echo -e "\n## Kafka Connect Status (if available):"
curl -s -w "%{http_code}" 192.168.1.184:8083/ -o /dev/null || echo "Connect not available"

echo -e "\n=========================="
EOF

chmod +x /tmp/kafka-health-check.sh
/tmp/kafka-health-check.sh
```

## Kafka Web UI (Optional but Recommended)

### 🌟 **Recommended for Java 17+: Modern Kafka UI** (Requires Java 17+)

**⚠️ Java Version Requirement:** Kafka UI v0.4.0+ requires **Java 13+**, v0.7.1+ requires **Java 17+**

### 🎯 **Recommended for Java 11: Kafdrop** (Works with Java 8+)

**✅ Install Kafdrop on cpu-node1:**
```bash
# Download Kafdrop (Java 11 compatible)
cd /opt
sudo wget https://github.com/obsidiandynamics/kafdrop/releases/download/3.31.0/kafdrop-3.31.0.jar
sudo chown kafka:kafka kafdrop-3.31.0.jar

# Create Kafdrop service
sudo tee /etc/systemd/system/kafdrop.service << EOF
[Unit]
Description=Kafdrop Kafka UI
After=network.target kafka.service

[Service]
Type=simple
User=kafka
Group=kafka
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/usr/bin/java -jar /opt/kafdrop-3.31.0.jar --kafka.brokerConnect=192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 --server.port=9001
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# Start Kafdrop
sudo systemctl daemon-reload
sudo systemctl start kafdrop
sudo systemctl enable kafdrop

# Open firewall
sudo ufw allow 9001/tcp

# Verify it's running
sudo systemctl status kafdrop

echo "✅ Kafdrop available at: http://192.168.1.184:9001"
```

### 💎 **Alternative for Java 17+: Modern Kafka UI**

**Install Kafka UI on cpu-node1 (requires Java 17+):**
```bash
# Download Java 11-compatible Kafka UI (modern, lightweight)
cd /opt
sudo wget https://github.com/provectus/kafka-ui/releases/download/v0.4.0/kafka-ui-api-v0.4.0.jar
sudo chown kafka:kafka kafka-ui-api-v0.4.0.jar

# Create configuration
sudo tee /opt/kafka-ui-config.yml << EOF
kafka:
  clusters:
    - name: HomeLab-Kafka-Cluster
      bootstrapServers: 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
      zookeeper: 192.168.1.184:2181,192.168.1.187:2181,192.168.1.190:2181

server:
  port: 8082
  
spring:
  jmx:
    enabled: true

management:
  endpoints:
    web:
      exposure:
        include: "*"
EOF

# Create systemd service
sudo tee /etc/systemd/system/kafka-ui.service << EOF
[Unit]
Description=Kafka UI
Documentation=https://github.com/provectus/kafka-ui
Requires=network.target remote-fs.target
After=network.target remote-fs.target kafka.service

[Service]
Type=simple
User=kafka
Group=kafka
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/usr/bin/java -jar /opt/kafka-ui-api-v0.4.0.jar --spring.config.location=/opt/kafka-ui-config.yml
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# Start Kafka UI
sudo systemctl daemon-reload
sudo systemctl start kafka-ui
sudo systemctl enable kafka-ui
sudo systemctl status kafka-ui

# Open firewall for web access
sudo ufw allow 8082/tcp

echo "✅ Kafka UI available at: http://192.168.1.184:8082"
```

**📝 Note:** Using v0.4.0 for Java 11 compatibility. If you have Java 17+, you can use v0.7.1+ for more features.

### 🔧 **Alternative: CMAK (Classic Kafka Manager)**

**If you prefer the classic Yahoo Kafka Manager:**
```bash
# Install CMAK on cpu-node1
cd /opt
sudo wget https://github.com/yahoo/CMAK/releases/download/3.0.0.5/cmak-3.0.0.5.zip
sudo unzip cmak-3.0.0.5.zip
sudo mv cmak-3.0.0.5 cmak
sudo chown -R kafka:kafka cmak

# Configure CMAK
sudo tee /opt/cmak/conf/application.conf << EOF
# ZooKeeper configuration
kafka-manager.zkhosts="192.168.1.184:2181,192.168.1.187:2181,192.168.1.190:2181"

# Application settings
play.http.context="/kafka-manager"
play.application.loader=loader.KafkaManagerLoader
kafka-manager.consumer.properties.file=/opt/cmak/conf/consumer.properties

# Security (basic auth)
basicAuthentication.enabled=false

# JMX settings
kafka-manager.broker-view-thread-pool-size=10
kafka-manager.broker-view-max-queue-size=1000
kafka-manager.broker-view-update-seconds=30

# Consumer offset settings
kafka-manager.offset-cache-thread-pool-size=10
kafka-manager.offset-cache-max-queue-size=1000

# Logback configuration
logger.kafka-manager=INFO
logger.application=INFO
EOF

# Create CMAK service
sudo tee /etc/systemd/system/cmak.service << EOF
[Unit]
Description=Kafka Manager (CMAK)
After=network.target kafka.service

[Service]
Type=forking
User=kafka
Group=kafka
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/opt/cmak/bin/cmak -Dconfig.file=/opt/cmak/conf/application.conf -Dhttp.port=9000 &
ExecStop=/bin/kill \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start CMAK
sudo systemctl daemon-reload
sudo systemctl start cmak
sudo systemctl enable cmak

# Open firewall
sudo ufw allow 9000/tcp

echo "✅ CMAK available at: http://192.168.1.184:9000"
```

### 🚀 **Alternative: Kafdrop (Lightweight)**

**For a simple, lightweight option:**
```bash
# Install Kafdrop on cpu-node1
cd /opt
sudo wget https://github.com/obsidiandynamics/kafdrop/releases/download/3.31.0/kafdrop-3.31.0.jar
sudo chown kafka:kafka kafdrop-3.31.0.jar

# Create Kafdrop service
sudo tee /etc/systemd/system/kafdrop.service << EOF
[Unit]
Description=Kafdrop Kafka UI
After=network.target kafka.service

[Service]
Type=simple
User=kafka
Group=kafka
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/usr/bin/java -jar /opt/kafdrop-3.31.0.jar --kafka.brokerConnect=192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 --server.port=9001
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

# Start Kafdrop
sudo systemctl daemon-reload
sudo systemctl start kafdrop
sudo systemctl enable kafdrop

# Open firewall
sudo ufw allow 9001/tcp

echo "✅ Kafdrop available at: http://192.168.1.184:9001"
```

### 📊 **UI Comparison & Recommendation:**

| Feature | **Kafka UI** ⭐ | CMAK | Kafdrop |
|---------|-----------------|------|---------|
| **Ease of Setup** | ✅ Very Easy | ❌ Complex | ✅ Easy |
| **Modern UI** | ✅ Beautiful | ❌ Dated | ✅ Clean |
| **Active Development** | ✅ Active | ❌ Legacy | ✅ Active |
| **Topic Management** | ✅ Full | ✅ Full | ✅ Basic |
| **Consumer Groups** | ✅ Advanced | ✅ Advanced | ✅ Basic |
| **Schema Registry** | ✅ Yes | ❌ No | ❌ No |
| **Connect Management** | ✅ Yes | ❌ No | ❌ No |
| **Resource Usage** | ✅ Light | ❌ Heavy | ✅ Very Light |

**🎯 Recommendation:** 
- **Java 11**: Use **Kafdrop** ⭐ (works perfectly with your setup)
- **Java 17+**: Use **Kafka UI** (more features but requires newer Java)

### 🔥 **Quick Access Summary:**

After setup, access your Kafka cluster via:
- **Kafdrop**: `http://192.168.1.184:9001` ⭐ **Recommended for Java 11**
- **Kafka UI**: `http://192.168.1.184:8082` (Requires Java 17+)
- **CMAK**: `http://192.168.1.184:9000` (Classic)

## High Availability Considerations

1. **Replication Factor**: Always use replication factor ≥ 3 for important topics
2. **Min In-Sync Replicas**: Set `min.insync.replicas=2` for critical topics
3. **Acks Configuration**: Use `acks=all` for producers requiring durability
4. **Unclean Leader Election**: Set `unclean.leader.election.enable=false`

### 📋 **Replication Factor Best Practices for Your 3-Broker Cluster:**

**Always Use RF=3 for:**
- ✅ **User topics** (your application data)
- ✅ **Kafka Connect internal topics** (`connect-offsets`, `connect-configs`, `connect-status`)
- ✅ **Consumer offset topics** (automatically RF=3)

**Why RF=3 in 3-broker clusters:**
```
┌─────────────────┬─────────────┬─────────────────┬─────────────────┐
│ Replication     │ Fault       │ Brokers         │ Recommendation  │
│ Factor          │ Tolerance   │ Required        │                 │
├─────────────────┼─────────────┼─────────────────┼─────────────────┤
│ RF = 1          │ 0 failures  │ 1 broker        │ ❌ Never use    │
│ RF = 2          │ 1 failure   │ 2 brokers       │ ❌ Poor choice  │
│ RF = 3          │ 2 failures  │ 3 brokers       │ ✅ Perfect fit  │
└─────────────────┴─────────────┴─────────────────┴─────────────────┘
```

**Key Point:** With RF=3, you can lose **any 2 brokers** and still have all your data!

## Backup and Recovery

```bash
# Backup Kafka topics
/opt/kafka/bin/kafka-mirror-maker.sh --consumer.config consumer.properties --producer.config producer.properties --whitelist=".*"

# Backup ZooKeeper data
sudo tar -czf zookeeper-backup-$(date +%Y%m%d).tar.gz /var/lib/zookeeper
```

## Debezium PostgreSQL CDC Connector

### 🚨 **PREREQUISITE: Configure PostgreSQL for CDC (MUST BE DONE FIRST)**

**Step 0: Enable logical replication in PostgreSQL**

**🔥 Important:** PostgreSQL must be configured for **logical replication** to support CDC. This is different from streaming replication.

```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/16/main/postgresql.conf

# Update these settings (logical includes everything replica does):
wal_level = logical                    # Change from 'replica' to 'logical' 
max_replication_slots = 4              # Add if missing
max_wal_senders = 4                    # Should already exist

# Restart PostgreSQL to apply changes
sudo systemctl restart postgresql

# Verify logical replication is enabled
sudo -u postgres psql -c "SHOW wal_level;"
# Must show: logical (not replica)
```

**✅ Don't worry:** Changing to `logical` **will NOT break** your existing streaming replication - it's a superset that includes everything `replica` does plus CDC capabilities.

**Step 1: Create CDC Database User**

```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create CDC user with replication privileges
CREATE USER cdc_user WITH REPLICATION LOGIN PASSWORD 'cdc_password123';

# Connect to analytics_db 
\c analytics_db

# Grant necessary permissions for CDC
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cdc_user;
GRANT USAGE ON SCHEMA public TO cdc_user;
ALTER USER cdc_user WITH BYPASSRLS;

-- Create publication for Debezium
CREATE PUBLICATION debezium_publication FOR ALL TABLES;

-- Verify user was created
\du cdc_user

-- Exit PostgreSQL
\q

# Test CDC user connection
psql -h 192.168.1.184 -U cdc_user -d analytics_db -c "SELECT current_user, current_database();"
# Password: cdc_password123
```

---

### 🔴 Install Debezium on PRIMARY BROKER (cpu-node1 / 192.168.1.184)

**Step 2: Download and install Debezium PostgreSQL connector:**
```bash
# Create Kafka Connect plugins directory
sudo mkdir -p /opt/kafka/plugins

# Download Debezium PostgreSQL connector
cd /tmp
wget https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.4.2.Final/debezium-connector-postgres-2.4.2.Final-plugin.tar.gz

# Extract to plugins directory
sudo tar -xzf debezium-connector-postgres-2.4.2.Final-plugin.tar.gz -C /opt/kafka/plugins/

# Set ownership
sudo chown -R kafka:kafka /opt/kafka/plugins/
```

**Step 3: Configure Kafka Connect:**
```bash
# Create Connect configuration
sudo nano /opt/kafka/config/connect-distributed.properties
```

**🔥 Important:** Always use **replication factor = 3** in a 3-broker cluster for maximum fault tolerance.

Add/modify these settings:
```properties
# Kafka Connect distributed configuration
bootstrap.servers=192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
group.id=connect-cluster

# Converter settings for JSON
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=false
value.converter.schemas.enable=false

# Internal topic settings (use RF=3 for 3-broker cluster)
offset.storage.topic=connect-offsets
offset.storage.replication.factor=3
config.storage.topic=connect-configs
config.storage.replication.factor=3
status.storage.topic=connect-status
status.storage.replication.factor=3

# Plugin path
plugin.path=/opt/kafka/plugins

# REST API settings - bind to all interfaces but advertise specific IP
rest.host.name=0.0.0.0
rest.port=8083
rest.advertised.host.name=192.168.1.184
rest.advertised.port=8083
```

**Step 4: Create Kafka Connect systemd service:**
```bash
# Create systemd service file
sudo nano /etc/systemd/system/kafka-connect.service
```

**🚨 Important:** Make sure `JAVA_HOME` points to your actual Java installation path!

```ini
[Unit]
Description=Apache Kafka Connect
Documentation=https://kafka.apache.org/
Requires=network.target remote-fs.target
After=network.target remote-fs.target kafka.service

[Service]
Type=simple
User=kafka
Group=kafka
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ExecStart=/opt/kafka/bin/connect-distributed.sh /opt/kafka/config/connect-distributed.properties
ExecStop=/bin/kill -TERM $MAINPID
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

**Step 5: Start Kafka Connect:**
```bash
# Reload systemd and start Kafka Connect
sudo systemctl daemon-reload
sudo systemctl start kafka-connect
sudo systemctl enable kafka-connect

# Verify Kafka Connect is running
sudo systemctl status kafka-connect

# Test REST API locally (should work)
curl -s 192.168.1.184:8083/ | jq

# Test REST API via advertised address (should also work)
curl -s 192.168.1.184:8083/ | jq

# Test from other nodes in cluster (should work)
# From cpu-node2 or worker-node3: curl -s 192.168.1.184:8083/ | jq

# Check available connector plugins
curl -s 192.168.1.184:8083/connector-plugins | jq
```

### 🔧 Configure Debezium PostgreSQL Connector

**Step 1: Create connector configuration:**
```bash
# Create PostgreSQL connector configuration
cat > /tmp/postgres-connector.json << 'EOF'
{
  "name": "postgres-debezium-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",
    "database.hostname": "192.168.1.184",
    "database.port": "5432",
    "database.user": "cdc_user",
    "database.password": "cdc_password123",
    "database.dbname": "analytics_db",
    "database.server.name": "postgres-server",
    "table.include.list": "public.*",
    "publication.name": "debezium_publication",
    "slot.name": "debezium_slot",
    "topic.prefix": "postgres",
    "schema.include.list": "public",
    "plugin.name": "pgoutput",
    "transforms": "route",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "([^.]+)\\.([^.]+)\\.([^.]+)",
    "transforms.route.replacement": "cdc.$3"
  }
}
EOF
```

**Step 2: Deploy the connector:**
```bash
# Deploy PostgreSQL CDC connector
curl -X POST -H "Content-Type: application/json" --data @/tmp/postgres-connector.json 192.168.1.184:8083/connectors

# Check connector status
curl -s 192.168.1.184:8083/connectors/postgres-debezium-connector/status | jq

# List all connectors
curl -s 192.168.1.184:8083/connectors | jq
```

### 📊 Test CDC Streaming

**Step 1: Create test table in PostgreSQL:**
```bash
# Connect to PostgreSQL on primary
psql -h 192.168.1.184 -U dataeng -d analytics_db

# Create test table
CREATE TABLE user_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    event_type VARCHAR(50),
    event_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

# Insert test data
INSERT INTO user_events (user_id, event_type, event_data) VALUES
(1001, 'login', '{"ip": "192.168.1.100", "device": "mobile"}'),
(1002, 'purchase', '{"product_id": 123, "amount": 99.99}'),
(1003, 'logout', '{"session_duration": 1800}');

-- Exit PostgreSQL
\q
```

**Step 2: Verify CDC data in Kafka:**
```bash
# List Kafka topics (should see CDC topics)
/opt/kafka/bin/kafka-topics.sh --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 --list | grep cdc

# Consume CDC messages from user_events topic
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 \
  --topic cdc.user_events \
  --from-beginning \
  --property print.headers=true \
  --property print.timestamp=true
```

**Step 3: Test real-time CDC:**
```bash
# In one terminal, start consuming CDC messages:
/opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server 192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092 \
  --topic cdc.user_events

# In another terminal, insert more data:
psql -h 192.168.1.184 -U dataeng -d analytics_db -c \
"INSERT INTO user_events (user_id, event_type, event_data) VALUES (1004, 'signup', '{\"email\": \"test@example.com\"}');"

# You should see the CDC message appear immediately in the consumer!
```

### 🔧 CDC Monitoring and Management

**Monitor connector health:**
```bash
# Check connector status
curl -s 192.168.1.184:8083/connectors/postgres-debezium-connector/status | jq '.connector.state'

# Check task status
curl -s 192.168.1.184:8083/connectors/postgres-debezium-connector/tasks/0/status | jq

# View connector metrics
curl -s 192.168.1.184:8083/connectors/postgres-debezium-connector | jq
```

**Manage CDC connector:**
```bash
# Pause connector
curl -X PUT 192.168.1.184:8083/connectors/postgres-debezium-connector/pause

# Resume connector
curl -X PUT 192.168.1.184:8083/connectors/postgres-debezium-connector/resume

# Restart connector
curl -X POST 192.168.1.184:8083/connectors/postgres-debezium-connector/restart

# Delete connector
curl -X DELETE 192.168.1.184:8083/connectors/postgres-debezium-connector
```

### 📈 **OPTIONAL: Advanced CDC Configuration**

**🤔 Skip This Section Unless You Need:**
- Multiple CDC connectors
- Specific table filtering
- Custom message transformations
- Different topic naming

**🚨 If you just want basic CDC working, SKIP this section and proceed to Integration!**

---

#### **🔧 Alternative: Production-Ready CDC Connector**

**Run on cpu-node1 ONLY - This REPLACES the basic connector if you want more features:**

```bash
# Step 1: Delete the basic connector (if you deployed it)
curl -X DELETE 192.168.1.184:8083/connectors/postgres-debezium-connector

# Step 2: Create advanced connector configuration
cat > /tmp/postgres-advanced-connector.json << 'EOF'
{
  "name": "postgres-production-cdc-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "2",
    "database.hostname": "192.168.1.184",
    "database.port": "5432",
    "database.user": "cdc_user",
    "database.password": "cdc_password123",
    "database.dbname": "analytics_db",
    "database.server.name": "postgres-production",
    "table.include.list": "public.user_events,public.orders,public.products",
    "publication.name": "debezium_publication",
    "slot.name": "debezium_production_slot",
    "topic.prefix": "postgres-prod",
    "schema.include.list": "public",
    "plugin.name": "pgoutput",
    "snapshot.mode": "initial",
    "decimal.handling.mode": "string",
    "time.precision.mode": "adaptive",
    "include.schema.changes": "true",
    "message.key.columns": "public.user_events:id;public.orders:order_id",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false"
  }
}
EOF

# Step 3: Deploy the advanced connector
curl -X POST -H "Content-Type: application/json" --data @/tmp/postgres-advanced-connector.json 192.168.1.184:8083/connectors

# Step 4: Verify deployment
curl -s 192.168.1.184:8083/connectors/postgres-production-cdc-connector/status | jq
```

**🎯 Key Differences from Basic Setup:**
- ✅ **Multiple tasks** (`tasks.max: 2`) for better performance
- ✅ **Specific table filtering** (only user_events, orders, products)
- ✅ **Custom topic prefix** (`postgres-prod.*` instead of `postgres.*`)
- ✅ **Message unwrapping** (removes Debezium metadata envelope)
- ✅ **Custom key columns** for proper partitioning

**📊 Result Topics:**
```
postgres-prod.user_events    ← CDC events for user_events table
postgres-prod.orders         ← CDC events for orders table  
postgres-prod.products       ← CDC events for products table
```

## Integration with Other Components

### ✅ **Fully Documented Integrations:**

- **📊 Spark Integration**: ✅ **[Spark Cluster Setup Guide](03_spark_cluster_setup.md)** - Complete Kafka Structured Streaming examples
- **🌊 Flink Integration**: ✅ **[Flink Cluster Setup Guide](04_flink_cluster_setup.md)** - Kafka SQL connectors & CDC streaming  
- **🔍 Trino Integration**: ✅ **[Trino Cluster Setup Guide](05_trino_cluster_setup.md)** - Kafka connector & streaming analysis
- **🏔️ Iceberg Integration**: ✅ **[Iceberg Setup Guide](06_iceberg_local_setup.md)** - Kafka to Iceberg streaming
- **🌊 Delta Lake Integration**: ✅ **[Delta Lake Setup Guide](07_deltalake_local_setup.md)** - Complete Kafka integration script
- **📈 PostgreSQL Integration**: ✅ **Debezium CDC configured above** - Real-time change data capture
- **🗄️ Redis Integration**: ✅ **[Redis Setup Guide](09_redis_setup.md)** - Kafka to Redis Stream processing
- **🍽️ Feast Integration**: ✅ **[Feast Setup Guide](10_feast_feature_store_setup.md)** - Kafka feature sources

### 🔄 **Additional Integrations Available:**

- **📊 Neo4j Integration**: ✅ **[Neo4j Setup Guide](08_neo4j_graph_database_setup.md)** - Kafka to Neo4j streaming

### 🏗️ **Not Yet Implemented:**

- **Schema Registry**: Consider Confluent Schema Registry for Avro/JSON schema management
- **Kafka Streams**: Native stream processing within Kafka ecosystem
- **Connect Transforms**: Custom message transformations in Kafka Connect

## Troubleshooting

### Common Issues:
1. **OutOfMemory errors**: Increase heap size in KAFKA_HEAP_OPTS
2. **Network partitions**: Check ZooKeeper connectivity
3. **Slow consumers**: Monitor consumer lag and tune fetch settings
4. **Disk space**: Monitor log retention and cleanup policies
5. **"Connection to localhost:9092 could not be established"**: 
   - ❌ **Don't use** `localhost:9092`
   - ✅ **Use the node's IP** (`192.168.1.184:9092`, `192.168.1.187:9092`, or `192.168.1.190:9092`)
   - **Reason**: Kafka is configured to bind to specific IPs, not localhost

### Log Locations:
- Kafka logs: `/opt/kafka/logs/server.log`
- ZooKeeper logs: `/opt/kafka/logs/zookeeper.out`
- Data directories: `/var/lib/kafka/logs/`, `/var/lib/zookeeper/`
