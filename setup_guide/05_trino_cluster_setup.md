# Trino (formerly Presto) Cluster Setup Guide

## Overview
Trino will be set up in cluster mode with cpu-node1 as the coordinator and cpu-node2 as a worker node. Worker-node3 can be added as an additional worker for more query processing capacity.

## Cluster Configuration
- **Coordinator**: cpu-node1 (192.168.1.184) - Query planning and coordination
- **Worker 1**: cpu-node2 (192.168.1.187) - Query execution
- **Worker 2**: worker-node3 (192.168.1.190) - Optional additional capacity

## Prerequisites
- Java 17 or later (Java 21 LTS recommended for stability and performance)
- Python symlink (Ubuntu 24.04+ needs `python-is-python3` package)
- At least 4GB RAM per node (8GB recommended for coordinator)
- At least 20GB free disk space per node
- Network connectivity between all nodes

## Version Note
This guide uses **Trino 435** which is stable with Java 17/21. For latest Trino versions (476+), you need Java 22+.

### ⚠️ Configuration Compatibility Warning
**Trino 435 removed several properties** that existed in newer versions:
- ❌ `query.max-total-memory-per-node` - **REMOVED** (causes startup failure)
- ❌ `discovery-server.enabled` - **DEPRECATED** (causes warnings)

**Always check Trino release notes** when changing versions!

### 🚨 Port Conflict Warning
**CRITICAL**: Trino uses different ports to avoid conflicts with other services:
- **cpu-node1**: Trino coordinator (8084) ✅ - Avoids conflict with Flink JobManager (8081) and Spark Master (8080)
- **cpu-node2**: Trino worker (8082) ✅ - Avoids conflict with Spark Worker (8081)
- **worker-node3**: Trino worker (8083) ✅ - Avoids conflict with Spark Worker (8081)

**Port allocation summary for cpu-node1:**
- Spark Master: 8080
- Flink JobManager: 8081  
- Trino Coordinator: 8084

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   worker-node3      │
│   (Coordinator)     │    │    (Worker 1)       │    │    (Worker 2)       │
│  - Query Planning   │    │  - Query Execution  │    │  - Query Execution  │
│  - Client Interface │    │  - Data Processing  │    │  - Data Processing  │
│  - Web UI (8084)    │    │  - Web UI (8082)    │    │  - Web UI (8083)    │
│  192.168.1.184      │    │  192.168.1.187      │    │  192.168.1.190      │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Step 1: Prerequisites Installation (All Nodes)

### Install Java 21:
```bash
# Install OpenJDK 21 (LTS)
sudo apt update
sudo apt install -y openjdk-21-jdk

# Verify Java installation
java -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

### Install Python symlink (Ubuntu 24.04+ requirement):
```bash
# Trino launcher expects 'python' command but Ubuntu 24.04 only has 'python3'
sudo apt install -y python-is-python3

# Verify python command works
python --version  # Should show Python 3.x.x
```

## Step 2: Create Trino User (All Nodes)

```bash
# Create trino user
sudo useradd -m -s /bin/bash trino
sudo passwd trino
sudo usermod -aG sudo trino
```

## Step 3: Download and Install Trino (All Nodes)

```bash
# Switch to trino user
sudo su - trino
cd /home/trino

# Download Trino 435 (stable with Java 17/21)
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
http-server.http.port=8084
query.max-memory=8GB
query.max-memory-per-node=2GB
discovery.uri=http://192.168.1.184:8084
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
http-server.http.port=8082
query.max-memory-per-node=2GB
discovery.uri=http://192.168.1.184:8084
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
http-server.http.port=8083
query.max-memory-per-node=2GB
discovery.uri=http://192.168.1.184:8084
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

## Step 7: Configure Connectors (Execute in cpu-node1 and scp to All Nodes)

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
```

### TPC-H connector (for benchmarking):
```bash
nano /home/trino/trino/etc/catalog/tpch.properties
```

```properties
connector.name=tpch
tpch.splits-per-node=4
```

## ⚠️ **IMPORTANT: Lakehouse Catalogs Require Hive Metastore**

**Before creating Iceberg and Delta Lake catalogs below**, you need **Hive Metastore service** running on port 9083.

### **Two Options:**

**Option A: Skip Lakehouse Catalogs (Recommended for basic setup)**
- Skip the Iceberg and Delta Lake sections below
- Trino will work with PostgreSQL, Kafka, TPC-H, and Memory catalogs
- Add lakehouse catalogs later when needed

**Option B: Install Hive Metastore First**
- Complete **[07_hive_metastore_setup.md](./07_hive_metastore_setup.md)** (Hive Metastore installation)
- Then return here to create the catalogs below
- **Warning:** Creating these catalogs without Hive Metastore will cause Trino startup failures

### **If You Accidentally Create These Catalogs:**
```bash
# Disable problematic catalogs
sudo mv /home/trino/trino/etc/catalog/iceberg.properties /home/trino/trino/etc/catalog/iceberg.properties.disabled
sudo mv /home/trino/trino/etc/catalog/delta.properties /home/trino/trino/etc/catalog/delta.properties.disabled
sudo systemctl restart trino
```

---

### Iceberg connector (for lakehouse):
```bash
nano /home/trino/trino/etc/catalog/iceberg.properties
```

```properties
connector.name=iceberg
hive.metastore.uri=thrift://192.168.1.184:9083
iceberg.catalog.type=hive_metastore
```

### Hive connector:
```bash
nano /home/trino/trino/etc/catalog/hive.properties
```

```properties
connector.name=hive
hive.metastore.uri=thrift://192.168.1.184:9083
```

### Delta Lake connector:
```bash
nano /home/trino/trino/etc/catalog/delta.properties
```

```properties
connector.name=delta-lake
hive.metastore.uri=thrift://192.168.1.184:9083
delta.enable-non-concurrent-writes=true
# Note: Advanced Delta properties may not be available in Trino 435
# For complete list of compatible properties, see 09_deltalake_distributed_comprehensive.md
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
Environment=JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
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
sudo ufw allow 8084/tcp   # Trino coordinator HTTP port (cpu-node1)
sudo ufw allow 8082/tcp   # Trino worker HTTP port (cpu-node2) 
sudo ufw allow 8083/tcp   # Trino worker HTTP port (worker-node3)
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
Open browser and access the Trino Web UIs:
- **Coordinator**: http://192.168.1.184:8084
- **Worker 1 (cpu-node2)**: http://192.168.1.187:8082  
- **Worker 2 (worker-node3)**: http://192.168.1.190:8083

### Test with CLI:
```bash
# Connect to Trino
./trino-cli --server http://192.168.1.184:8084 --catalog tpch --schema tiny

# Or using the symbolic link
trino --server http://192.168.1.184:8084 --catalog tpch --schema tiny
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

Add these Trino 435-compatible optimizations:
```properties
# Basic query management
query.max-run-time=1h
query.max-queued-queries=100
query.max-concurrent-queries=50

# Memory management
query.low-memory-killer.delay=5m
query.low-memory-killer.policy=total-reservation

# Basic spilling configuration
spill-enabled=true
spiller-spill-path=/home/trino/trino/data/spill

# Task management (conservative settings for Trino 435)
task.concurrency=8
task.http-response-threads=50
task.info-update-interval=3s
task.max-partial-aggregation-memory=16MB
task.max-worker-threads=100
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

**📍 REQUIRED:** For Iceberg and Delta Lake catalogs, you **must** install Hive Metastore first.

**Complete the dedicated setup guide:**
👉 **[07_hive_metastore_setup.md](./07_hive_metastore_setup.md)**

After completing the Hive Metastore setup, return to **Step 7** above to enable the Iceberg and Delta Lake catalogs.

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
COORDINATOR="192.168.1.184:8084"
WORKERS=("192.168.1.187:8082" "192.168.1.190:8083")

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
1. **Iceberg Catalog Configuration Error** (Most Common):
   - **Error**: `Invalid value 'hive' for type CatalogType (property 'iceberg.catalog.type')`
   - **Symptoms**: Service exits with code 100, continuous restarts
   - **Cause**: Trino 435 changed Iceberg catalog type values
   - **Solution**: Fix Iceberg catalog configuration:
     ```bash
     sudo su - trino -c "sed -i 's/iceberg.catalog.type=hive/iceberg.catalog.type=hive_metastore/' /home/trino/trino/etc/catalog/iceberg.properties"
     sudo systemctl restart trino
     ```
   - **Alternative**: Temporarily disable problematic catalogs:
     ```bash
     sudo su - trino -c "mv /home/trino/trino/etc/catalog/iceberg.properties /home/trino/trino/etc/catalog/iceberg.properties.disabled"
     ```

2. **Missing Hive Connector Configuration**:
   - **Error**: `Catalog configuration does not contain connector.name`
   - **Symptoms**: Worker nodes fail with Guice injection errors
   - **Solution**: Ensure hive.properties exists on all nodes:
     ```bash
     sudo tee /home/trino/trino/etc/catalog/hive.properties > /dev/null << 'EOF'
connector.name=hive
hive.metastore.uri=thrift://192.168.1.184:9083
EOF
     ```

3. **Service Crash Loop** (Exit Code 100):
   - **Symptoms**: `activating (auto-restart) (Result: exit-code)`, restart counter increasing
   - **Check logs**: `sudo journalctl -u trino.service --no-pager -n 50`
   - **Common causes**: 
     - Invalid catalog configuration (see #1)
     - Missing required properties
     - Java version compatibility issues

2. **Java Version Compatibility**: 
   - **Trino 435 (this guide)**: Works with Java 17/21
   - **Trino 476+**: Requires Java 22+
   - If you get "Java version not supported" errors, check: `java -version`
   - **Solution**: Ensure Java 17+ is installed: `sudo apt install openjdk-21-jdk`

3. **OutOfMemoryError**: Increase JVM heap size in jvm.config

4. **Connection refused**: Check firewall and network connectivity

5. **Metastore connection errors**: Verify Hive Metastore setup

6. **Slow queries**: Check query plans and add appropriate connectors

7. **Python Command Not Found**:
   - **Error**: `/usr/bin/env: 'python': No such file or directory`
   - **Cause**: Ubuntu 24.04+ doesn't create python → python3 symlink by default
   - **Solution**: `sudo apt install -y python-is-python3`

8. **Service fails to start**: Check `journalctl -xeu trino.service` for detailed errors

### Debug commands:
```bash
# Check Trino logs
tail -f /home/trino/trino/var/log/server.log

# Check if port is listening
netstat -tlnp | grep 8084

# Test network connectivity
telnet 192.168.1.184 8084

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

## Upgrading to Newer Trino Versions

If you want to upgrade to Trino 476+ later for latest features:

### Prerequisites for Trino 476+:
1. **Java 22+**: Install from Adoptium/Eclipse Temurin
2. **Configuration Updates**: Review release notes for breaking changes
3. **Testing**: Test in staging environment first

### Safe upgrade path:
```bash
# 1. Backup current setup
sudo systemctl stop trino
tar -czf trino-435-backup-$(date +%Y%m%d).tar.gz /home/trino/

# 2. Install Java 22 (if needed)
# Follow Adoptium installation instructions

# 3. Download newer Trino version
# Update configuration properties per release notes

# 4. Test and validate
```

### Version comparison:
- **Trino 435**: Stable, Java 17/21, fewer features
- **Trino 476+**: Latest features, Java 22+, more complex setup
