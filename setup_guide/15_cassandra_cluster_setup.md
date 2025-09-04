# Apache Cassandra Cluster Setup Guide

## Overview
Apache Cassandra will be set up as a distributed NoSQL cluster across three nodes for high availability, fault tolerance, and horizontal scalability. This setup provides eventually consistent, partition-tolerant database capabilities for your data engineering platform.

## What is Apache Cassandra?
Cassandra is a highly scalable, distributed NoSQL database designed to handle large amounts of data across many commodity servers, providing high availability with no single point of failure. It's perfect for time-series data, IoT applications, and high-write workloads.

## Cluster Configuration
- **Seed Node 1**: cpu-node1 (192.168.1.184) - Primary seed node
- **Node 2**: cpu-node2 (192.168.1.187) - Secondary node
- **Node 3**: worker-node3 (192.168.1.190) - Third node

## Prerequisites
- Java 11 or later on all nodes
- At least 8GB RAM per node (16GB recommended)
- At least 50GB free disk space per node
- Network connectivity between all nodes
- Same timezone on all nodes

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   worker-node3      │
│  (Seed Node 1)      │◄──►│    (Node 2)         │◄──►│    (Node 3)         │
│  - Gossip Protocol  │    │  - Data Replication │    │  - Load Distribution│
│  - Cluster Metadata │    │  - Query Coordinator│    │  - Fault Tolerance  │
│  192.168.1.184:9042 │    │  192.168.1.187:9042 │    │  192.168.1.190:9042 │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
                 │                     │                     │
                 └─────────────────────┼─────────────────────┘
                         Ring Topology - Consistent Hashing
```

## Step 1: Java Installation (All Nodes)

Run on **cpu-node1, cpu-node2, and worker-node3**:

```bash
# Update package repository
sudo apt update

# Install OpenJDK 11 (recommended for Cassandra)
sudo apt install -y openjdk-11-jdk

# Verify Java installation
java -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc

# Verify JAVA_HOME
echo $JAVA_HOME
```

## Step 2: Create Cassandra User (All Nodes)

```bash
# Create cassandra system user
sudo useradd -r -s /bin/false cassandra

# Create data directories
sudo mkdir -p /var/lib/cassandra/data
sudo mkdir -p /var/lib/cassandra/commitlog
sudo mkdir -p /var/lib/cassandra/saved_caches
sudo mkdir -p /var/log/cassandra

# Set ownership
sudo chown -R cassandra:cassandra /var/lib/cassandra
sudo chown -R cassandra:cassandra /var/log/cassandra
```

## Step 3: Install Cassandra (All Nodes)

```bash
# Add Cassandra repository key
wget -q -O - https://downloads.apache.org/cassandra/KEYS | sudo apt-key add -

# Add Cassandra repository (version 4.1 - stable LTS)
echo "deb https://downloads.apache.org/cassandra/debian 41x main" | sudo tee /etc/apt/sources.list.d/cassandra.sources.list

# Update package list
sudo apt update

# Install Cassandra
sudo apt install -y cassandra

# Stop Cassandra (we'll configure before starting)
sudo systemctl stop cassandra
sudo systemctl disable cassandra
```

## Step 4: Configure Cassandra Cluster

### Configure cpu-node1 (Seed Node):
```bash
sudo nano /etc/cassandra/cassandra.yaml
```

Key configuration changes for **cpu-node1**:
```yaml
# Cluster name (must be same on all nodes)
cluster_name: 'DataEng_HomeLab_Cluster'

# Node-specific settings
listen_address: 192.168.1.184
rpc_address: 192.168.1.184
broadcast_address: 192.168.1.184
broadcast_rpc_address: 192.168.1.184

# Seeds configuration (seed nodes for cluster discovery)
seed_provider:
    - class_name: org.apache.cassandra.locator.SimpleSeedProvider
      parameters:
          - seeds: "192.168.1.184,192.168.1.187"

# Data directories
data_file_directories:
    - /var/lib/cassandra/data
commitlog_directory: /var/lib/cassandra/commitlog
saved_caches_directory: /var/lib/cassandra/saved_caches

# Network settings
native_transport_port: 9042
storage_port: 7000
ssl_storage_port: 7001

# Performance settings
concurrent_reads: 32
concurrent_writes: 32
concurrent_counter_writes: 32

# Memory settings (adjust based on available RAM)
# For 8GB system:
# heap_size: 2G (set in jvm.options)
# For 16GB system:  
# heap_size: 4G (set in jvm.options)

# Replication and consistency
partitioner: org.apache.cassandra.dht.Murmur3Partitioner
endpoint_snitch: SimpleSnitch

# Enable authentication (optional but recommended)
authenticator: PasswordAuthenticator
authorizer: CassandraAuthorizer

# Logging
log_level: INFO
```

### Configure cpu-node2:
```bash
sudo nano /etc/cassandra/cassandra.yaml
```

Key configuration changes for **cpu-node2** (same as cpu-node1 except IPs):
```yaml
cluster_name: 'DataEng_HomeLab_Cluster'

# Node-specific settings for cpu-node2
listen_address: 192.168.1.187
rpc_address: 192.168.1.187
broadcast_address: 192.168.1.187
broadcast_rpc_address: 192.168.1.187

# Same seed configuration
seed_provider:
    - class_name: org.apache.cassandra.locator.SimpleSeedProvider
      parameters:
          - seeds: "192.168.1.184,192.168.1.187"

# All other settings same as cpu-node1
```

### Configure worker-node3:
```bash
sudo nano /etc/cassandra/cassandra.yaml
```

Key configuration changes for **worker-node3**:
```yaml
cluster_name: 'DataEng_HomeLab_Cluster'

# Node-specific settings for worker-node3
listen_address: 192.168.1.190
rpc_address: 192.168.1.190
broadcast_address: 192.168.1.190
broadcast_rpc_address: 192.168.1.190

# Same seed configuration
seed_provider:
    - class_name: org.apache.cassandra.locator.SimpleSeedProvider
      parameters:
          - seeds: "192.168.1.184,192.168.1.187"

# All other settings same as cpu-node1
```

## Step 5: Configure JVM Settings (All Nodes)

```bash
# Edit JVM options
sudo nano /etc/cassandra/jvm.options
```

Recommended settings for 8GB RAM systems:
```bash
# Heap size (adjust based on available RAM)
-Xms2G
-Xmx2G

# For 16GB systems, use:
# -Xms4G
# -Xmx4G

# GC settings (already configured in default jvm.options)
-XX:+UseG1GC
-XX:G1RSetUpdatingPauseTimePercent=5
-XX:MaxGCPauseMillis=300
-XX:InitiatingHeapOccupancyPercent=70

# Additional recommended settings
-XX:+UnlockExperimentalVMOptions
-XX:+UseCGroupMemoryLimitForHeap
```

## Step 6: Firewall Configuration (All Nodes)

```bash
# Open required Cassandra ports
sudo ufw allow 7000/tcp    # Inter-node communication
sudo ufw allow 7001/tcp    # Inter-node SSL communication
sudo ufw allow 9042/tcp    # CQL native transport port
sudo ufw allow 7199/tcp    # JMX monitoring port (optional)

# Reload firewall
sudo ufw reload

# Verify firewall status
sudo ufw status
```

## Step 7: Start Cassandra Cluster

### Start nodes in sequence (important for initial cluster formation):

**Step 1: Start seed node first (cpu-node1)**:
```bash
# Start Cassandra on cpu-node1
sudo systemctl start cassandra
sudo systemctl enable cassandra

# Check status
sudo systemctl status cassandra

# Monitor logs
sudo tail -f /var/log/cassandra/system.log
```

**Step 2: Wait and start cpu-node2**:
```bash
# Wait 30 seconds, then start cpu-node2
sleep 30
sudo systemctl start cassandra
sudo systemctl enable cassandra

# Check status and logs
sudo systemctl status cassandra
sudo tail -f /var/log/cassandra/system.log
```

**Step 3: Wait and start worker-node3**:
```bash
# Wait 30 seconds, then start worker-node3
sleep 30
sudo systemctl start cassandra
sudo systemctl enable cassandra

# Check status and logs
sudo systemctl status cassandra
sudo tail -f /var/log/cassandra/system.log
```

## Step 8: Verify Cluster Status

From any node, check cluster status:

```bash
# Check node status
nodetool status

# Expected output:
# Datacenter: datacenter1
# =======================
# Status=Up/Down
# |/ State=Normal/Leaving/Joining/Moving
# --  Address         Load       Tokens  Owns (effective)  Host ID                               Rack
# UN  192.168.1.184   108.45 KiB  16      66.7%            <uuid>                                rack1
# UN  192.168.1.187   108.45 KiB  16      66.7%            <uuid>                                rack1
# UN  192.168.1.190   108.45 KiB  16      66.6%            <uuid>                                rack1

# Check ring information
nodetool ring

# Check cluster information
nodetool info

# Check gossip state
nodetool gossipinfo
```

## Step 9: Basic Security Setup

### Create admin user and disable default superuser:

Connect to Cassandra on cpu-node1:
```bash
# Connect using cqlsh
cqlsh 192.168.1.184 9042
```

```sql
-- Create admin user
CREATE ROLE admin WITH PASSWORD = 'secure_admin_password123' AND SUPERUSER = true AND LOGIN = true;

-- Verify admin user was created
LIST ROLES;

-- Exit and reconnect as admin
EXIT;
```

```bash
# Connect as admin user
cqlsh 192.168.1.184 9042 -u admin -p secure_admin_password123
```

```sql
-- Change default cassandra user password
ALTER ROLE cassandra WITH PASSWORD = 'disabled_default_password' AND SUPERUSER = false;

-- Create application users
CREATE ROLE dataeng_user WITH PASSWORD = 'dataeng_password123' AND LOGIN = true;
CREATE ROLE analytics_user WITH PASSWORD = 'analytics_password123' AND LOGIN = true;

-- Create keyspaces with replication
CREATE KEYSPACE analytics_ks 
WITH REPLICATION = {
    'class': 'SimpleStrategy',
    'replication_factor': 3
};

CREATE KEYSPACE timeseries_ks 
WITH REPLICATION = {
    'class': 'SimpleStrategy', 
    'replication_factor': 3
};

-- Grant permissions
GRANT ALL ON KEYSPACE analytics_ks TO dataeng_user;
GRANT ALL ON KEYSPACE timeseries_ks TO analytics_user;

-- Verify keyspaces
DESCRIBE KEYSPACES;
```

## Step 10: Test Basic Operations

### Create test table and insert data:

```sql
-- Use analytics keyspace
USE analytics_ks;

-- Create test table
CREATE TABLE user_events (
    user_id UUID,
    event_time TIMESTAMP,
    event_type TEXT,
    event_data MAP<TEXT, TEXT>,
    PRIMARY KEY (user_id, event_time)
) WITH CLUSTERING ORDER BY (event_time DESC);

-- Insert test data
INSERT INTO user_events (user_id, event_time, event_type, event_data)
VALUES (uuid(), '2024-01-15 10:30:00', 'login', {'ip': '192.168.1.100', 'device': 'mobile'});

INSERT INTO user_events (user_id, event_time, event_type, event_data)  
VALUES (uuid(), '2024-01-15 10:31:00', 'page_view', {'page': '/dashboard', 'duration': '45'});

-- Query data
SELECT * FROM user_events LIMIT 10;

-- Check data distribution across nodes
SELECT token(user_id), user_id, event_type FROM user_events;
```

## Step 11: Monitoring and Maintenance

### Create monitoring script:
```bash
nano /home/sanzad/monitor-cassandra.sh
```

```bash
#!/bin/bash

echo "=== Cassandra Cluster Status ==="
nodetool status

echo -e "\n=== Node Health Check ==="
for node in 192.168.1.184 192.168.1.187 192.168.1.190; do
    echo "Checking $node..."
    nodetool -h $node info | grep -E "(Load|Uptime)"
done

echo -e "\n=== Ring Status ==="
nodetool ring | head -20

echo -e "\n=== Keyspace Info ==="
nodetool cfstats analytics_ks

echo -e "\n=== Disk Usage ==="
df -h /var/lib/cassandra/data

echo -e "\n=== JVM Memory Usage ==="
nodetool info | grep -E "(Heap|Off heap)"
```

```bash
chmod +x /home/sanzad/monitor-cassandra.sh
```

### Regular maintenance commands:
```bash
# Repair a node (run weekly)
nodetool repair

# Cleanup unused data after node changes
nodetool cleanup

# Flush memtables to disk
nodetool flush

# Compact SSTables
nodetool compact

# Check and repair inconsistencies  
nodetool scrub
```

## Step 12: Integration with Data Pipeline

### Example: Kafka-Cassandra Integration

Create connector configuration for streaming data:

```bash
# Example Kafka Connect Cassandra Sink configuration
nano /home/sanzad/cassandra-sink.json
```

```json
{
  "name": "cassandra-sink-connector",
  "config": {
    "connector.class": "com.datastax.kafka.connect.cassandra.CassandraSinkConnector",
    "tasks.max": "1",
    "topics": "user-events",
    "contactPoints": "192.168.1.184,192.168.1.187,192.168.1.190",
    "port": "9042",
    "loadBalancing.localDc": "datacenter1",
    "auth.username": "dataeng_user",
    "auth.password": "dataeng_password123",
    "keyspace": "analytics_ks",
    "table": "user_events"
  }
}
```

### Example: Spark-Cassandra Integration

```scala
// Spark configuration for Cassandra
val spark = SparkSession.builder()
  .appName("Cassandra Analytics")
  .config("spark.cassandra.connection.host", "192.168.1.184,192.168.1.187,192.168.1.190")
  .config("spark.cassandra.connection.port", "9042")
  .config("spark.cassandra.auth.username", "dataeng_user")
  .config("spark.cassandra.auth.password", "dataeng_password123")
  .getOrCreate()

// Read from Cassandra
val df = spark
  .read
  .format("org.apache.spark.sql.cassandra")
  .options(Map("table" -> "user_events", "keyspace" -> "analytics_ks"))
  .load()

// Perform analytics
df.groupBy("event_type").count().show()
```

## Troubleshooting

### Common Issues:

1. **Nodes not joining cluster:**
   ```bash
   # Check network connectivity
   telnet 192.168.1.184 7000
   
   # Check seed configuration in cassandra.yaml
   grep -A 5 "seed_provider" /etc/cassandra/cassandra.yaml
   
   # Check logs for errors
   sudo tail -f /var/log/cassandra/system.log
   ```

2. **Authentication errors:**
   ```bash
   # Reset to no authentication temporarily
   sudo sed -i 's/authenticator: PasswordAuthenticator/authenticator: AllowAllAuthenticator/' /etc/cassandra/cassandra.yaml
   sudo systemctl restart cassandra
   ```

3. **Memory issues:**
   ```bash
   # Check JVM heap usage
   nodetool info | grep -E "Heap Memory"
   
   # Adjust heap size in jvm.options
   sudo nano /etc/cassandra/jvm.options
   ```

4. **High load/slow queries:**
   ```bash
   # Check compaction status
   nodetool compactionstats
   
   # Monitor thread pools
   nodetool tpstats
   
   # Check slow queries (enable in cassandra.yaml)
   tail /var/log/cassandra/debug.log
   ```

## Performance Tuning

### Production recommendations:

```yaml
# In cassandra.yaml
concurrent_reads: 64
concurrent_writes: 64
memtable_heap_space_in_mb: 2048
memtable_offheap_space_in_mb: 2048
commitlog_segment_size_in_mb: 32
```

### Monitoring with external tools:

```bash
# Install DataStax OpsCenter (optional)
# Or integrate with Prometheus + Grafana
# Enable JMX metrics
echo 'JVM_OPTS="$JVM_OPTS -Dcom.sun.management.jmxremote.port=7199"' >> /etc/cassandra/cassandra-env.sh
```

## Next Steps

After Cassandra is running:
1. Integrate with Kafka for real-time data ingestion
2. Connect Spark for large-scale analytics  
3. Set up monitoring with Grafana dashboards
4. Implement backup and disaster recovery procedures
5. Consider adding more nodes for increased capacity

Your Cassandra cluster is now ready to handle high-volume, distributed NoSQL workloads!
