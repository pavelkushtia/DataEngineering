# HDFS Distributed Setup Guide

## Overview
HDFS (Hadoop Distributed File System) will provide distributed storage for your Iceberg and Delta Lake tables across all 3 nodes. This enables true distributed lakehouse architecture with fault tolerance and parallel I/O.

## Why HDFS for Lakehouse?
- **Distributed Storage**: Data spread across all nodes (cpu-node1, cpu-node2, worker-node3)
- **Fault Tolerance**: Data replicated across nodes, survives single node failure
- **Parallel I/O**: All engines (Spark, Flink, Trino) can read/write simultaneously
- **Native Integration**: Iceberg and Delta Lake designed to work with HDFS

## Architecture Layout
- **NameNode**: cpu-node1 (192.168.1.184) - Metadata management
- **DataNode 1**: cpu-node1 (192.168.1.184) - Data storage + metadata
- **DataNode 2**: cpu-node2 (192.168.1.187) - Data storage
- **DataNode 3**: worker-node3 (192.168.1.190) - Data storage

## Prerequisites
- Java 11+ installed on all nodes
- At least 20GB free disk space per node for HDFS data
- Network connectivity between all nodes
- Same user account on all nodes for HDFS

## Step 1: Create HDFS User and Directories (All Nodes)

```bash
# Create hadoop user
sudo useradd -m -s /bin/bash hadoop
sudo passwd hadoop

# Create HDFS directories
sudo mkdir -p /opt/hadoop
sudo mkdir -p /data/hadoop/hdfs/namenode
sudo mkdir -p /data/hadoop/hdfs/datanode
sudo mkdir -p /data/hadoop/logs

# Set ownership
sudo chown -R hadoop:hadoop /opt/hadoop
sudo chown -R hadoop:hadoop /data/hadoop
```

## Step 2: Download and Install Hadoop (All Nodes)

```bash
# Switch to hadoop user
sudo su - hadoop

# Download Hadoop 3.3.6 (LTS version)
cd /opt/hadoop
wget https://downloads.apache.org/hadoop/common/hadoop-3.3.6/hadoop-3.3.6.tar.gz
tar -xzf hadoop-3.3.6.tar.gz
mv hadoop-3.3.6 current
rm hadoop-3.3.6.tar.gz

# Set environment variables
echo 'export HADOOP_HOME=/opt/hadoop/current' >> ~/.bashrc
echo 'export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop' >> ~/.bashrc
echo 'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin' >> ~/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc

# Reload environment
source ~/.bashrc
```

## Step 3: Configure HDFS (NameNode - cpu-node1)

### Edit core-site.xml:
```bash
nano $HADOOP_CONF_DIR/core-site.xml
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://192.168.1.184:9000</value>
        <description>Default file system URI</description>
    </property>
    
    <property>
        <name>hadoop.tmp.dir</name>
        <value>/data/hadoop/tmp</value>
        <description>Temporary directory for Hadoop</description>
    </property>
    
    <property>
        <name>hadoop.http.staticuser.user</name>
        <value>hadoop</value>
    </property>
</configuration>
```

### Edit hdfs-site.xml:
```bash
nano $HADOOP_CONF_DIR/hdfs-site.xml
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <property>
        <name>dfs.replication</name>
        <value>2</value>
        <description>Default block replication (2 copies for 3-node cluster)</description>
    </property>
    
    <property>
        <name>dfs.namenode.name.dir</name>
        <value>/data/hadoop/hdfs/namenode</value>
        <description>NameNode directory for namespace and transaction logs</description>
    </property>
    
    <property>
        <name>dfs.datanode.data.dir</name>
        <value>/data/hadoop/hdfs/datanode</value>
        <description>DataNode directory</description>
    </property>
    
    <property>
        <name>dfs.namenode.http-address</name>
        <value>192.168.1.184:9870</value>
        <description>NameNode web interface</description>
    </property>
    
    <property>
        <name>dfs.namenode.secondary.http-address</name>
        <value>192.168.1.184:9868</value>
        <description>Secondary NameNode web interface</description>
    </property>
    
    <property>
        <name>dfs.blocksize</name>
        <value>134217728</value>
        <description>Block size (128MB)</description>
    </property>
    
    <property>
        <name>dfs.permissions.enabled</name>
        <value>false</value>
        <description>Disable permissions for development (enable in production)</description>
    </property>
</configuration>
```

### Configure workers:
```bash
nano $HADOOP_CONF_DIR/workers
```

```
192.168.1.184
192.168.1.187
192.168.1.190
```

### Set Java home:
```bash
nano $HADOOP_CONF_DIR/hadoop-env.sh
```

Add this line:
```bash
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
```

## Step 4: Copy Configuration to All Nodes

```bash
# From cpu-node1 (as hadoop user)
scp -r $HADOOP_CONF_DIR/* hadoop@192.168.1.187:$HADOOP_CONF_DIR/
scp -r $HADOOP_CONF_DIR/* hadoop@192.168.1.190:$HADOOP_CONF_DIR/
```

## Step 5: Set up SSH Keys (Password-less SSH)

```bash
# On cpu-node1 (as hadoop user)
ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa

# Copy public key to all nodes (including localhost)
ssh-copy-id hadoop@192.168.1.184
ssh-copy-id hadoop@192.168.1.187
ssh-copy-id hadoop@192.168.1.190

# Test connections
ssh hadoop@192.168.1.187 "hostname"
ssh hadoop@192.168.1.190 "hostname"
```

## Step 6: Format HDFS and Start Services

```bash
# Format the namenode (ONLY run once on cpu-node1)
cd /opt/hadoop/current
bin/hdfs namenode -format -force

# Start HDFS services (from cpu-node1)
sbin/start-dfs.sh

# Check if services are running
jps
# Should show: NameNode, DataNode, SecondaryNameNode

# Check on other nodes
ssh hadoop@192.168.1.187 "jps"  # Should show: DataNode
ssh hadoop@192.168.1.190 "jps"  # Should show: DataNode
```

## Step 7: Verify HDFS Installation

```bash
# Check HDFS status
hdfs dfsadmin -report

# Create test directory
hdfs dfs -mkdir /user
hdfs dfs -mkdir /user/hadoop
hdfs dfs -mkdir /tmp

# Test file operations
echo "Hello HDFS!" > test.txt
hdfs dfs -put test.txt /user/hadoop/
hdfs dfs -ls /user/hadoop/
hdfs dfs -cat /user/hadoop/test.txt

# Check web interface
echo "HDFS Web UI: http://192.168.1.184:9870"
```

## Step 8: Create Lakehouse Directories

```bash
# Create directory structure for lakehouse
hdfs dfs -mkdir -p /lakehouse
hdfs dfs -mkdir -p /lakehouse/iceberg
hdfs dfs -mkdir -p /lakehouse/delta-lake
hdfs dfs -mkdir -p /lakehouse/raw-data
hdfs dfs -mkdir -p /lakehouse/processed-data

# Set permissions (for development)
hdfs dfs -chmod -R 777 /lakehouse

# Verify structure
hdfs dfs -ls -R /lakehouse
```

## Step 9: Performance Tuning

### Adjust memory settings:
```bash
nano $HADOOP_CONF_DIR/hadoop-env.sh
```

Add these lines:
```bash
# Memory settings for 4GB RAM nodes
export HADOOP_NAMENODE_OPTS="-Xmx1g -Xms1g"
export HADOOP_DATANODE_OPTS="-Xmx512m -Xms512m"
export HADOOP_SECONDARYNAMENODE_OPTS="-Xmx512m -Xms512m"
```

### Restart HDFS:
```bash
sbin/stop-dfs.sh
sbin/start-dfs.sh
```

## Step 10: Create Systemd Services

### NameNode service (cpu-node1):
```bash
sudo nano /etc/systemd/system/hadoop-namenode.service
```

```ini
[Unit]
Description=Hadoop NameNode
After=network.target

[Service]
Type=forking
User=hadoop
Group=hadoop
WorkingDirectory=/opt/hadoop/current
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
Environment=HADOOP_HOME=/opt/hadoop/current
Environment=HADOOP_CONF_DIR=/opt/hadoop/current/etc/hadoop
ExecStart=/opt/hadoop/current/sbin/hadoop-daemon.sh start namenode
ExecStop=/opt/hadoop/current/sbin/hadoop-daemon.sh stop namenode
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### DataNode service (all nodes):
```bash
sudo nano /etc/systemd/system/hadoop-datanode.service
```

```ini
[Unit]
Description=Hadoop DataNode
After=network.target

[Service]
Type=forking
User=hadoop
Group=hadoop
WorkingDirectory=/opt/hadoop/current
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
Environment=HADOOP_HOME=/opt/hadoop/current
Environment=HADOOP_CONF_DIR=/opt/hadoop/current/etc/hadoop
ExecStart=/opt/hadoop/current/sbin/hadoop-daemon.sh start datanode
ExecStop=/opt/hadoop/current/sbin/hadoop-daemon.sh stop datanode
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and start services:
```bash
# Enable services
sudo systemctl daemon-reload
sudo systemctl enable hadoop-namenode  # Only on cpu-node1
sudo systemctl enable hadoop-datanode  # On all nodes

# Start services
sudo systemctl start hadoop-namenode   # Only on cpu-node1
sudo systemctl start hadoop-datanode   # On all nodes
```

## Step 11: Monitoring and Maintenance

### Create monitoring script:
```bash
nano /home/hadoop/monitor-hdfs.sh
```

```bash
#!/bin/bash

echo "=== HDFS Cluster Status ==="
hdfs dfsadmin -report

echo -e "\n=== DataNode Status ==="
for node in 192.168.1.184 192.168.1.187 192.168.1.190; do
    echo "Checking $node..."
    ssh hadoop@$node "jps | grep DataNode || echo 'DataNode not running'"
done

echo -e "\n=== HDFS Health ==="
hdfs fsck / -summary

echo -e "\n=== Disk Usage ==="
hdfs dfs -df -h /

echo -e "\n=== Directory Listing ==="
hdfs dfs -ls /lakehouse/
```

```bash
chmod +x /home/hadoop/monitor-hdfs.sh
```

## Step 12: Integration with Existing Services

### Update Spark configuration:
```bash
# Add to spark-defaults.conf
nano /home/spark/spark/conf/spark-defaults.conf
```

Add:
```properties
spark.hadoop.fs.defaultFS                hdfs://192.168.1.184:9000
spark.sql.warehouse.dir                  hdfs://192.168.1.184:9000/lakehouse
```

### Update Flink configuration:
```bash
# Add to flink-conf.yaml
nano /home/flink/flink/conf/flink-conf.yaml
```

Add:
```yaml
fs.hdfs.hadoop.conf.dir: /opt/hadoop/current/etc/hadoop
```

## Troubleshooting

### Common issues:

1. **DataNode not starting:**
   ```bash
   # Check logs
   tail -f $HADOOP_HOME/logs/hadoop-hadoop-datanode-*.log
   
   # Remove old data if needed (CAUTION: loses data!)
   rm -rf /data/hadoop/hdfs/datanode/*
   ```

2. **Safe mode issues:**
   ```bash
   # Leave safe mode manually
   hdfs dfsadmin -safemode leave
   ```

3. **Storage space:**
   ```bash
   # Check disk usage
   df -h /data/hadoop/
   hdfs dfs -df -h /
   ```

## Next Steps

Now that HDFS is running, you can:
1. Convert Iceberg setup to use HDFS storage
2. Convert Delta Lake setup to use HDFS storage  
3. Configure all engines (Spark, Flink, Trino) to use distributed lakehouse
4. Set up monitoring and backup strategies

Your lakehouse is now truly distributed across all 3 nodes! 🎉
