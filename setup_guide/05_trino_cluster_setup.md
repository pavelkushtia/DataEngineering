# Trino (formerly Presto) Cluster Setup Guide

## Overview
Trino will be set up in cluster mode with cpu-node1 as the coordinator and cpu-node2 as a worker node. Worker-node3 can be added as an additional worker for more query processing capacity.

## Cluster Configuration
- **Coordinator**: cpu-node1 (192.168.1.184) - Query planning and coordination
- **Worker 1**: cpu-node2 (192.168.1.187) - Query execution
- **Worker 2**: worker-node3 (192.168.1.190) - Optional additional capacity

## Prerequisites
- Java 17 or later (Trino requires Java 17+)
- At least 4GB RAM per node (8GB recommended for coordinator)
- At least 20GB free disk space per node
- Network connectivity between all nodes

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   worker-node3      │
│   (Coordinator)     │    │    (Worker 1)       │    │    (Worker 2)       │
│  - Query Planning   │    │  - Query Execution  │    │  - Query Execution  │
│  - Client Interface │    │  - Data Processing  │    │  - Data Processing  │
│  - Web UI (8081)    │    │  - Connectors       │    │  - Connectors       │
│  192.168.1.184      │    │  192.168.1.187      │    │  192.168.1.190      │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Step 1: Java 17 Installation (All Nodes)

```bash
# Install OpenJDK 17
sudo apt update
sudo apt install -y openjdk-17-jdk

# Verify Java installation
java -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

## Step 2: Create Trino User (All Nodes)

```bash
# Create trino user
sudo useradd -m -s /bin/bash trino
sudo passwd trino
```

## Step 3: Download and Install Trino (All Nodes)

```bash
# Switch to trino user
sudo su - trino
cd /home/trino

# Download latest Trino server
wget https://repo1.maven.org/maven2/io/trino/trino-server/435/trino-server-435.tar.gz

# Extract Trino
tar -xzf trino-server-435.tar.gz
mv trino-server-435 trino-server
rm trino-server-435.tar.gz

# Create symbolic link
ln -s trino-server trino

# Set permissions
chmod +x trino/bin/launcher

# Add Trino to PATH
echo 'export TRINO_HOME=/home/trino/trino' >> ~/.bashrc
echo 'export PATH=$PATH:$TRINO_HOME/bin' >> ~/.bashrc
source ~/.bashrc
```

## Step 4: Create Data and Log Directories (All Nodes)

```bash
# As trino user
mkdir -p /home/trino/trino/etc
mkdir -p /home/trino/trino/data
mkdir -p /home/trino/trino/logs
mkdir -p /home/trino/trino/plugin-cache
```

## Step 5: Configure Trino Coordinator (cpu-node1)

### Main configuration file:
```bash
nano /home/trino/trino/etc/config.properties
```

```properties
# Coordinator configuration
coordinator=true
node-scheduler.include-coordinator=false
http-server.http.port=8081
query.max-memory=8GB
query.max-memory-per-node=2GB
query.max-total-memory-per-node=3GB
discovery-server.enabled=true
discovery.uri=http://192.168.1.184:8081
```

### Node properties:
```bash
nano /home/trino/trino/etc/node.properties
```

```properties
node.environment=production
node.id=cpu-node1-coordinator
node.data-dir=/home/trino/trino/data
```

### JVM configuration:
```bash
nano /home/trino/trino/etc/jvm.config
```

```
-server
-Xmx6G
-XX:+UseG1GC
-XX:G1HeapRegionSize=32M
-XX:+UseGCOverheadLimit
-XX:+ExplicitGCInvokesConcurrent
-XX:+HeapDumpOnOutOfMemoryError
-XX:+ExitOnOutOfMemoryError
-Djdk.attach.allowAttachSelf=true
-XX:ReservedCodeCacheSize=512M
-XX:PerMethodRecompilationCutoff=10000
-XX:PerBytecodeRecompilationCutoff=10000
-Djdk.nio.maxCachedBufferSize=2000000
```

### Log configuration:
```bash
nano /home/trino/trino/etc/log.properties
```

```properties
io.trino=INFO
root=WARN
io.trino.server.PluginManager=DEBUG
io.trino.connector=DEBUG
```

## Step 6: Configure Trino Workers (cpu-node2 and worker-node3)

### Worker configuration for cpu-node2:
```bash
nano /home/trino/trino/etc/config.properties
```

```properties
# Worker configuration
coordinator=false
http-server.http.port=8081
query.max-memory-per-node=2GB
query.max-total-memory-per-node=3GB
discovery.uri=http://192.168.1.184:8081
```

### Node properties for cpu-node2:
```bash
nano /home/trino/trino/etc/node.properties
```

```properties
node.environment=production
node.id=cpu-node2-worker1
node.data-dir=/home/trino/trino/data
```

### Worker configuration for worker-node3:
```bash
nano /home/trino/trino/etc/config.properties
```

```properties
# Worker configuration
coordinator=false
http-server.http.port=8081
query.max-memory-per-node=2GB
query.max-total-memory-per-node=3GB
discovery.uri=http://192.168.1.184:8081
```

### Node properties for worker-node3:
```bash
nano /home/trino/trino/etc/node.properties
```

```properties
node.environment=production
node.id=worker-node3-worker2
node.data-dir=/home/trino/trino/data
```

### Copy JVM and log configuration to workers:
```bash
# From coordinator (cpu-node1)
scp /home/trino/trino/etc/jvm.config trino@192.168.1.187:/home/trino/trino/etc/
scp /home/trino/trino/etc/log.properties trino@192.168.1.187:/home/trino/trino/etc/
scp /home/trino/trino/etc/jvm.config trino@192.168.1.190:/home/trino/trino/etc/
scp /home/trino/trino/etc/log.properties trino@192.168.1.190:/home/trino/trino/etc/
```

## Step 7: Configure Connectors (All Nodes)

### Create catalog directory:
```bash
mkdir -p /home/trino/trino/etc/catalog
```

### PostgreSQL connector:
```bash
nano /home/trino/trino/etc/catalog/postgresql.properties
```

```properties
connector.name=postgresql
connection-url=jdbc:postgresql://192.168.1.184:5432/analytics_db
connection-user=dataeng
connection-password=password
```

### Kafka connector:
```bash
nano /home/trino/trino/etc/catalog/kafka.properties
```

```properties
connector.name=kafka
kafka.nodes=192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
kafka.table-names=test-topic,user-events,sales-data
kafka.hide-internal-columns=false
```

### Memory connector (for testing):
```bash
nano /home/trino/trino/etc/catalog/memory.properties
```

```properties
connector.name=memory
memory.max-data-size-per-node=128MB
```

### TPC-H connector (for benchmarking):
```bash
nano /home/trino/trino/etc/catalog/tpch.properties
```

```properties
connector.name=tpch
tpch.splits-per-node=4
```

### Iceberg connector (for lakehouse):
```bash
nano /home/trino/trino/etc/catalog/iceberg.properties
```

```properties
connector.name=iceberg
hive.metastore.uri=thrift://192.168.1.184:9083
iceberg.catalog.type=hive
```

### Delta Lake connector:
```bash
nano /home/trino/trino/etc/catalog/delta.properties
```

```properties
connector.name=delta-lake
hive.metastore.uri=thrift://192.168.1.184:9083
delta.enable-non-concurrent-writes=true
```

### Copy catalog configurations to workers:
```bash
# From coordinator
scp -r /home/trino/trino/etc/catalog/* trino@192.168.1.187:/home/trino/trino/etc/catalog/
scp -r /home/trino/trino/etc/catalog/* trino@192.168.1.190:/home/trino/trino/etc/catalog/
```

## Step 8: Create Systemd Services (All Nodes)

### Trino service:
```bash
sudo nano /etc/systemd/system/trino.service
```

```ini
[Unit]
Description=Trino Server
After=network.target
Wants=network.target

[Service]
Type=forking
User=trino
Group=trino
WorkingDirectory=/home/trino/trino
Environment=JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ExecStart=/home/trino/trino/bin/launcher start
ExecStop=/home/trino/trino/bin/launcher stop
Restart=always
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

## Step 9: Start Trino Cluster

```bash
# Reload systemd on all nodes
sudo systemctl daemon-reload

# Start coordinator first (cpu-node1)
sudo systemctl start trino
sudo systemctl enable trino

# Wait a few seconds, then start workers
sudo systemctl start trino  # on cpu-node2
sudo systemctl start trino  # on worker-node3
sudo systemctl enable trino # on both workers

# Check status
sudo systemctl status trino
```

## Step 10: Firewall Configuration (All Nodes)

```bash
# Open required ports
sudo ufw allow 8081/tcp   # Trino HTTP port
sudo ufw reload
```

## Step 11: Install and Configure Trino CLI

### Download Trino CLI (on coordinator):
```bash
# As trino user
cd /home/trino
wget https://repo1.maven.org/maven2/io/trino/trino-cli/435/trino-cli-435-executable.jar
mv trino-cli-435-executable.jar trino-cli
chmod +x trino-cli

# Create symbolic link for easy access
sudo ln -s /home/trino/trino-cli /usr/local/bin/trino
```

## Step 12: Testing the Cluster

### Access Trino Web UI:
Open browser and go to: http://192.168.1.184:8081

### Test with CLI:
```bash
# Connect to Trino
./trino-cli --server http://192.168.1.184:8081 --catalog tpch --schema tiny

# Or using the symbolic link
trino --server http://192.168.1.184:8081 --catalog tpch --schema tiny
```

### Run test queries:
```sql
-- Show catalogs
SHOW CATALOGS;

-- Show schemas in TPC-H catalog
SHOW SCHEMAS FROM tpch;

-- Show tables in tiny schema
SHOW TABLES FROM tpch.tiny;

-- Simple query
SELECT * FROM tpch.tiny.nation LIMIT 5;

-- More complex query
SELECT 
    n.name as nation,
    count(*) as customer_count
FROM tpch.tiny.nation n
JOIN tpch.tiny.customer c ON n.nationkey = c.nationkey
GROUP BY n.name
ORDER BY customer_count DESC;
```

### Test PostgreSQL connector:
```sql
-- Switch to PostgreSQL catalog
USE postgresql.public;

-- Show tables
SHOW TABLES;

-- Query PostgreSQL data
SELECT * FROM your_table_name LIMIT 10;
```

## Step 13: Performance Tuning

### Coordinator tuning:
```bash
nano /home/trino/trino/etc/config.properties
```

Add these optimizations:
```properties
# Query management
query.max-run-time=1h
query.max-queued-queries=1000
query.max-concurrent-queries=500

# Memory management
query.low-memory-killer.delay=5m
query.low-memory-killer.policy=total-reservation-on-blocked-nodes

# Spilling configuration
spill-enabled=true
spiller-spill-path=/home/trino/trino/data/spill
spiller-max-used-space-threshold=0.9
spiller-threads=4

# Exchange manager
exchange.http-client.max-connections=1000
exchange.http-client.max-connections-per-server=1000
exchange.http-client.max-requests-queued-per-destination=1000

# Task management
task.concurrency=16
task.http-response-threads=100
task.http-timeout-threads=3
task.info-update-interval=3s
task.max-partial-aggregation-memory=16MB
task.max-worker-threads=200
task.min-drivers=task.concurrency * 2
```

### Worker-specific tuning:
```properties
# Add to workers' config.properties
task.writer-count=1
task.partitioned-writer-count=4
```

## Step 14: Security Configuration

### Enable HTTPS (optional):
```bash
# Generate keystore
keytool -genkeypair -alias trino -keyalg RSA -keystore /home/trino/trino/keystore.jks

# Add to config.properties
http-server.https.enabled=true
http-server.https.port=8443
http-server.https.keystore.path=/home/trino/trino/keystore.jks
http-server.https.keystore.key=password
```

### Configure authentication (optional):
```bash
nano /home/trino/trino/etc/config.properties
```

Add:
```properties
http-server.authentication.type=PASSWORD
http-server.https.enabled=true
```

Create password file:
```bash
nano /home/trino/trino/etc/password-authenticator.properties
```

```properties
password-authenticator.name=file
file.password-file=/home/trino/trino/etc/password.db
```

## Step 15: Monitoring and Logging

### JMX monitoring:
```bash
# Add to jvm.config
-Dcom.sun.management.jmxremote
-Dcom.sun.management.jmxremote.port=9999
-Dcom.sun.management.jmxremote.authenticate=false
-Dcom.sun.management.jmxremote.ssl=false
```

### Log rotation:
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/trino
```

```
/home/trino/trino/var/log/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 trino trino
}
```

### Monitoring queries:
```sql
-- Show running queries
SELECT * FROM system.runtime.queries WHERE state = 'RUNNING';

-- Show cluster nodes
SELECT * FROM system.runtime.nodes;

-- Show memory usage
SELECT * FROM system.runtime.memory;

-- Show query statistics
SELECT 
    query_id,
    state,
    total_cpu_time,
    total_scheduled_time,
    total_blocked_time,
    memory_reservation,
    peak_memory_reservation
FROM system.runtime.queries 
ORDER BY created DESC 
LIMIT 10;
```

## Step 16: Advanced Connectors Setup

### Hive Metastore (for Iceberg/Delta Lake):

First, set up Hive Metastore:
```bash
# Download Hive
wget https://downloads.apache.org/hive/hive-3.1.3/apache-hive-3.1.3-bin.tar.gz
tar -xzf apache-hive-3.1.3-bin.tar.gz
mv apache-hive-3.1.3-bin hive

# Configure Hive Metastore
nano hive/conf/hive-site.xml
```

```xml
<?xml version="1.0"?>
<configuration>
    <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:postgresql://192.168.1.184:5432/metastore</value>
    </property>
    <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>org.postgresql.Driver</value>
    </property>
    <property>
        <name>javax.jdo.option.ConnectionUserName</name>
        <value>hive</value>
    </property>
    <property>
        <name>javax.jdo.option.ConnectionPassword</name>
        <value>password</value>
    </property>
    <property>
        <name>hive.metastore.warehouse.dir</name>
        <value>/home/trino/warehouse</value>
    </property>
</configuration>
```

## Step 17: Sample Queries and Use Cases

### Data Federation Query:
```sql
-- Join data from PostgreSQL and TPC-H
SELECT 
    p.name as postgres_name,
    t.name as tpch_name,
    count(*) as record_count
FROM postgresql.public.users p
FULL OUTER JOIN tpch.tiny.customer t ON p.id = t.custkey
GROUP BY p.name, t.name
LIMIT 10;
```

### Kafka Streaming Analysis:
```sql
-- Analyze Kafka topics
SELECT 
    _key,
    _message,
    _timestamp
FROM kafka.default."user-events"
WHERE _timestamp > current_timestamp - interval '1' hour
ORDER BY _timestamp DESC
LIMIT 100;
```

### Complex Analytics:
```sql
-- Window functions and analytics
WITH sales_analysis AS (
    SELECT 
        region,
        product_category,
        sales_amount,
        ROW_NUMBER() OVER (PARTITION BY region ORDER BY sales_amount DESC) as rank,
        SUM(sales_amount) OVER (PARTITION BY region) as total_regional_sales,
        LAG(sales_amount) OVER (PARTITION BY product_category ORDER BY sale_date) as prev_amount
    FROM postgresql.public.sales_data
)
SELECT 
    region,
    product_category,
    sales_amount,
    total_regional_sales,
    sales_amount / total_regional_sales * 100 as percentage_of_region
FROM sales_analysis 
WHERE rank <= 5;
```

## Step 18: Backup and Maintenance

### Configuration backup:
```bash
# Backup Trino configuration
tar -czf trino-config-backup-$(date +%Y%m%d).tar.gz /home/trino/trino/etc

# Backup data directory
tar -czf trino-data-backup-$(date +%Y%m%d).tar.gz /home/trino/trino/data
```

### Log cleanup:
```bash
# Clean old logs (weekly)
find /home/trino/trino/var/log -name "*.log.*" -mtime +7 -delete

# Clean spill data
find /home/trino/trino/data/spill -type f -mtime +1 -delete
```

### Health checks:
```bash
#!/bin/bash
# Health check script
COORDINATOR="192.168.1.184:8081"
WORKERS=("192.168.1.187:8081" "192.168.1.190:8081")

# Check coordinator
if curl -f -s http://$COORDINATOR/v1/info > /dev/null; then
    echo "Coordinator is healthy"
else
    echo "Coordinator is unhealthy"
fi

# Check workers
for worker in "${WORKERS[@]}"; do
    if curl -f -s http://$worker/v1/info > /dev/null; then
        echo "Worker $worker is healthy"
    else
        echo "Worker $worker is unhealthy"
    fi
done
```

## Troubleshooting

### Common Issues:
1. **OutOfMemoryError**: Increase JVM heap size in jvm.config
2. **Connection refused**: Check firewall and network connectivity
3. **Metastore connection errors**: Verify Hive Metastore setup
4. **Slow queries**: Check query plans and add appropriate connectors

### Debug commands:
```bash
# Check Trino logs
tail -f /home/trino/trino/var/log/server.log

# Check if port is listening
netstat -tlnp | grep 8081

# Test network connectivity
telnet 192.168.1.184 8081

# Check Java processes
jps | grep -i trino
```

### Query debugging:
```sql
-- Explain query execution plan
EXPLAIN (FORMAT TEXT) SELECT * FROM tpch.tiny.customer LIMIT 10;

-- Show query statistics
SELECT * FROM system.runtime.queries WHERE query = 'your-query-here';
```

This comprehensive Trino setup provides a scalable, distributed query engine that can federate queries across multiple data sources including PostgreSQL, Kafka, Iceberg, and Delta Lake tables.
