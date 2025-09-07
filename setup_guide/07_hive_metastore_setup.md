# Apache Hive Metastore Distributed Setup Guide

## Overview

Apache Hive Metastore is a central repository for metadata about Hadoop datasets. It provides metadata management services for table formats like Iceberg and Delta Lake, and is required by query engines like Trino for lakehouse analytics.

**What we'll set up:**
- Hive Metastore service on cpu-node1 (192.168.1.184)
- PostgreSQL backend for metadata storage
- Integration with HDFS for warehouse directories
- Systemd service management

## Prerequisites

✅ **Must be completed first:**
- [01_postgresql_setup.md](./01_postgresql_setup.md) - PostgreSQL database
- [06_hdfs_distributed_setup.md](./06_hdfs_distributed_setup.md) - HDFS storage

## Node Architecture

```
cpu-node1 (192.168.1.184):   Hive Metastore Service
cpu-node2 (192.168.1.185):   Client access only  
worker-node3 (192.168.1.186): Client access only
```

## Step 1: User and Directory Setup

### Create hive user on cpu-node1:

```bash
# Create hive user
sudo useradd -m -s /bin/bash hive
sudo passwd hive  # Set password
sudo usermod -aG sudo hive

# Create installation directory
sudo mkdir -p /opt/hive
sudo chown hive:hive /opt/hive
```

## Step 2: Download and Install Hive

### On cpu-node1 (192.168.1.184):

```bash
# Switch to hive user
sudo su - hive

# Download Hive 3.1.3 (compatible with Hadoop 3.3.6)
cd /opt/hive
wget https://archive.apache.org/dist/hive/hive-3.1.3/apache-hive-3.1.3-bin.tar.gz
tar -xzf apache-hive-3.1.3-bin.tar.gz
mv apache-hive-3.1.3-bin current
rm apache-hive-3.1.3-bin.tar.gz

# Set ownership
sudo chown -R hive:hive /opt/hive/
```

### Set environment variables:

```bash
# Add to /home/hive/.bashrc
echo 'export HIVE_HOME=/opt/hive/current' >> /home/hive/.bashrc
echo 'export PATH=$HIVE_HOME/bin:$PATH' >> /home/hive/.bashrc
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> /home/hive/.bashrc
echo 'export HADOOP_HOME=/opt/hadoop/current' >> /home/hive/.bashrc
echo 'export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop' >> /home/hive/.bashrc

# Apply changes
source /home/hive/.bashrc
```

## Step 3: Database Setup

### Create metastore database in PostgreSQL:

```bash
# Connect to PostgreSQL as postgres user
sudo su - postgres

# Create metastore database and user
createdb metastore
createuser hive

# Set password and permissions
psql -c "ALTER USER hive WITH PASSWORD 'hive123';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE metastore TO hive;"
psql -c "ALTER DATABASE metastore OWNER TO hive;"

exit
```

### Download PostgreSQL JDBC driver:

```bash
# As hive user
sudo su - hive
cd $HIVE_HOME/lib

# Download PostgreSQL JDBC driver
wget https://jdbc.postgresql.org/download/postgresql-42.7.2.jar
```

## Step 4: Configuration

### Create Hive configuration:

```bash
sudo su - hive
cd $HIVE_HOME/conf

# Create hive-site.xml
cat > hive-site.xml << 'EOF'
<?xml version="1.0"?>
<configuration>
    <!-- Database Connection -->
    <property>
        <name>javax.jdo.option.ConnectionURL</name>
        <value>jdbc:postgresql://192.168.1.184:5432/metastore</value>
        <description>PostgreSQL connection string</description>
    </property>
    
    <property>
        <name>javax.jdo.option.ConnectionDriverName</name>
        <value>org.postgresql.Driver</value>
        <description>PostgreSQL JDBC driver</description>
    </property>
    
    <property>
        <name>javax.jdo.option.ConnectionUserName</name>
        <value>hive</value>
        <description>Database username</description>
    </property>
    
    <property>
        <name>javax.jdo.option.ConnectionPassword</name>
        <value>hive123</value>
        <description>Database password</description>
    </property>
    
    <!-- Metastore Configuration -->
    <property>
        <name>hive.metastore.warehouse.dir</name>
        <value>hdfs://192.168.1.184:9000/lakehouse</value>
        <description>Default warehouse location in HDFS</description>
    </property>
    
    <property>
        <name>hive.metastore.uris</name>
        <value>thrift://192.168.1.184:9083</value>
        <description>Thrift server location</description>
    </property>
    
    <property>
        <name>hive.metastore.schema.verification</name>
        <value>false</value>
        <description>Disable schema verification for initial setup</description>
    </property>
    
    <property>
        <name>datanucleus.autoCreateSchema</name>
        <value>true</value>
        <description>Auto create database schema</description>
    </property>
    
    <property>
        <name>datanucleus.fixedDatastore</name>
        <value>false</value>
        <description>Allow schema modifications</description>
    </property>
    
    <!-- HDFS Integration -->
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://192.168.1.184:9000</value>
        <description>Default filesystem</description>
    </property>
</configuration>
EOF
```

### Create hive-env.sh:

```bash
cat > hive-env.sh << 'EOF'
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export HADOOP_HOME=/opt/hadoop/current
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
export HIVE_CONF_DIR=/opt/hive/current/conf
EOF

chmod +x hive-env.sh
```

## Step 5: Initialize Schema

### Initialize the metastore database schema:

```bash
# As hive user
sudo su - hive

# Initialize schema (this creates all required tables)
cd $HIVE_HOME/bin
./schematool -dbType postgres -initSchema
```

**Expected output:**
```
Starting metastore schema initialization to postgres
Initialization script hive-schema-3.1.0.postgres.sql
Initialization script completed
schemaTool completed
```

## Step 6: Create HDFS Directories

### Create warehouse directories in HDFS:

```bash
# As hadoop user (HDFS admin)
sudo su - hadoop -c "export HADOOP_HOME=/opt/hadoop/current && export PATH=\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$PATH && hdfs dfs -mkdir -p /lakehouse"

# Set permissions for Hive Metastore access
sudo su - hadoop -c "export HADOOP_HOME=/opt/hadoop/current && export PATH=\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$PATH && hdfs dfs -chmod 755 /lakehouse"

# Create specific directories for different table formats
sudo su - hadoop -c "export HADOOP_HOME=/opt/hadoop/current && export PATH=\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$PATH && hdfs dfs -mkdir -p /lakehouse/iceberg"
sudo su - hadoop -c "export HADOOP_HOME=/opt/hadoop/current && export PATH=\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$PATH && hdfs dfs -mkdir -p /lakehouse/delta"
sudo su - hadoop -c "export HADOOP_HOME=/opt/hadoop/current && export PATH=\$HADOOP_HOME/bin:\$HADOOP_HOME/sbin:\$PATH && hdfs dfs -mkdir -p /lakehouse/hive"
```

## Step 7: Create System Service

### Create systemd service file:

**Note:** We use `Type=simple` because Hive Metastore runs in foreground. Using `Type=forking` would cause startup timeouts.

```bash
sudo tee /etc/systemd/system/hive-metastore.service > /dev/null << 'EOF'
[Unit]
Description=Apache Hive Metastore
Documentation=https://hive.apache.org/
Requires=network.target remote-fs.target
After=network.target remote-fs.target

[Service]
Type=simple
User=hive
Group=hive
ExecStart=/opt/hive/current/bin/hive --service metastore
WorkingDirectory=/opt/hive/current
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
Environment=HIVE_HOME=/opt/hive/current
Environment=HADOOP_HOME=/opt/hadoop/current
Environment=HADOOP_CONF_DIR=/opt/hadoop/current/etc/hadoop
Restart=on-failure
RestartSec=5
StartLimitInterval=60s
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF
```

### Enable and start the service:

```bash
# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable hive-metastore

# Start the service
sudo systemctl start hive-metastore

# Check status
sudo systemctl status hive-metastore
```

## Step 8: Firewall Configuration

### Open port 9083 for Metastore access:

```bash
# On cpu-node1 (Metastore server)
sudo ufw allow from 192.168.1.0/24 to any port 9083 comment 'Hive Metastore'
```

## Step 9: Verification

### Test Metastore connectivity:

```bash
# Check if service is listening on port 9083
sudo netstat -tlnp | grep 9083

# Test from local machine
sudo su - hive -c "$HIVE_HOME/bin/hive --service metatool -listFSRoot"
```

### Test from other nodes:

```bash
# From cpu-node2 or worker-node3
telnet 192.168.1.184 9083
# Should connect successfully, type 'quit' to exit
```

### Test with beeline (Hive CLI) - **OPTIONAL**:

**⚠️ Note:** This test requires HiveServer2 (port 10000) which is **not included in this metastore-only setup**. If you get "Connection refused" errors, that's expected. See the **Optional HiveServer2 Setup** section below if you want direct Hive SQL access.

```bash
# Connect to Hive via beeline (requires HiveServer2 service)
sudo su - hive -c "$HIVE_HOME/bin/beeline -u 'jdbc:hive2://192.168.1.184:10000' -n hive"

# Inside beeline, test basic operations:
# > CREATE DATABASE test_db;
# > SHOW DATABASES;
# > USE test_db;
# > CREATE TABLE test_table (id INT, name STRING);
# > SHOW TABLES;
# > DROP TABLE test_table;
# > DROP DATABASE test_db;
# > !quit
```

## Step 9.5: Optional HiveServer2 Setup

**⚠️ This is OPTIONAL:** HiveServer2 provides direct Hive SQL access via beeline/JDBC. It's not required for Trino/Spark/Flink integration, which only need the Hive Metastore (port 9083).

### When you might need HiveServer2:
- Direct Hive SQL queries via beeline
- Legacy applications using Hive JDBC drivers
- Testing Hive queries without Trino/Spark

### Install HiveServer2 service:

```bash
# Create HiveServer2 systemd service
sudo tee /etc/systemd/system/hiveserver2.service > /dev/null << 'EOF'
[Unit]
Description=Apache HiveServer2
Documentation=https://hive.apache.org/
After=hive-metastore.service
Requires=hive-metastore.service

[Service]
Type=simple
User=hive
Group=hive
ExecStart=/opt/hive/current/bin/hive --service hiveserver2
WorkingDirectory=/opt/hive/current
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
Environment=HIVE_HOME=/opt/hive/current
Environment=HADOOP_HOME=/opt/hadoop/current
Environment=HADOOP_CONF_DIR=/opt/hadoop/current/etc/hadoop
Restart=on-failure
RestartSec=5
StartLimitInterval=60s
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
EOF

# Enable and start HiveServer2
sudo systemctl daemon-reload
sudo systemctl enable hiveserver2
sudo systemctl start hiveserver2

# Check status
sudo systemctl status hiveserver2

# Verify port 10000 is listening
sudo netstat -tlnp | grep 10000
```

### Configure firewall (if HiveServer2 is enabled):

```bash
# Allow HiveServer2 access from local network
sudo ufw allow from 192.168.1.0/24 to any port 10000 comment 'HiveServer2'
```

### Test HiveServer2 connection:

```bash
# Test with beeline (should work now if HiveServer2 is running)
sudo su - hive -c "$HIVE_HOME/bin/beeline -u 'jdbc:hive2://192.168.1.184:10000' -n hive"
```

## Step 10: Integration Testing

### Test PostgreSQL metadata storage:

```bash
# Connect to PostgreSQL and check metastore tables
sudo su - postgres -c "psql metastore"

# Inside PostgreSQL:
# \dt                    -- List all tables
# SELECT * FROM "DBS";   -- Show databases
# SELECT * FROM "TBLS";  -- Show tables
# \q                     -- Quit
```

## Step 11: Log Management

### Configure logging:

```bash
sudo su - hive
cd $HIVE_HOME/conf

# Create log4j2.properties
cat > hive-log4j2.properties << 'EOF'
status = INFO
name = HiveLog4j2

# Appenders
appender.console.type = Console
appender.console.name = console
appender.console.target = SYSTEM_ERR
appender.console.layout.type = PatternLayout
appender.console.layout.pattern = %d{yy/MM/dd HH:mm:ss} [%t]: %p %c{2}: %m%n

appender.file.type = RollingFile
appender.file.name = file
appender.file.fileName = /opt/hive/current/logs/hive.log
appender.file.filePattern = /opt/hive/current/logs/hive.log.%i
appender.file.layout.type = PatternLayout
appender.file.layout.pattern = %d{yy/MM/dd HH:mm:ss} [%t]: %p %c{2}: %m%n
appender.file.policies.type = Policies
appender.file.policies.size.type = SizeBasedTriggeringPolicy
appender.file.policies.size.size = 100MB
appender.file.strategy.type = DefaultRolloverStrategy
appender.file.strategy.max = 10

# Loggers
logger.DataNucleus.name = DataNucleus
logger.DataNucleus.level = ERROR

logger.Datastore.name = Datastore
logger.Datastore.level = ERROR

rootLogger.level = INFO
rootLogger.appenderRefs = console, file
rootLogger.appenderRef.console.ref = console
rootLogger.appenderRef.file.ref = file
EOF

# Create logs directory
mkdir -p /opt/hive/current/logs
```

## Step 12: Client Configuration (All Nodes)

### Install Hive client libraries on cpu-node2 and worker-node3:

```bash
# On each client node (cpu-node2, worker-node3)
sudo mkdir -p /opt/hive/client
cd /opt/hive/client

# Download and extract (client-only, no service)
sudo wget https://archive.apache.org/dist/hive/hive-3.1.3/apache-hive-3.1.3-bin.tar.gz
sudo tar -xzf apache-hive-3.1.3-bin.tar.gz
sudo mv apache-hive-3.1.3-bin current
sudo rm apache-hive-3.1.3-bin.tar.gz

# Copy configuration from metastore server
sudo scp hive@192.168.1.184:/opt/hive/current/conf/hive-site.xml /opt/hive/client/current/conf/
sudo scp hive@192.168.1.184:/opt/hive/current/conf/hive-env.sh /opt/hive/client/current/conf/

# Download PostgreSQL JDBC driver
sudo wget -P /opt/hive/client/current/lib/ https://jdbc.postgresql.org/download/postgresql-42.7.2.jar
```

## Troubleshooting

### Common Issues:

**1. Service won't start:**
```bash
# Check logs
sudo journalctl -u hive-metastore -f

# Check if PostgreSQL is running
sudo systemctl status postgresql

# Verify database connectivity
sudo su - hive -c "psql -h 192.168.1.184 -U hive -d metastore -c '\\dt'"
```

**2. Connection refused on port 9083:**
```bash
# Check if service is running
sudo systemctl status hive-metastore

# Check listening ports
sudo ss -tlnp | grep 9083

# Check firewall
sudo ufw status
```

**3. Schema initialization fails:**
```bash
# Check PostgreSQL permissions
sudo su - postgres -c "psql -c 'SELECT datname, datdba, datacl FROM pg_database WHERE datname = '\''metastore'\'';'"

# Reinitialize if needed
sudo su - hive -c "$HIVE_HOME/bin/schematool -dbType postgres -initSchema"
```

**4. Beeline connection refused (EXPECTED):**
```bash
# If beeline fails with "Connection refused" on port 10000:
# Error: Could not open client transport with JDBC Uri: jdbc:hive2://192.168.1.184:10000

# This is EXPECTED in metastore-only setup. Solutions:
# Option 1: Skip beeline test (recommended for lakehouse)
# Option 2: Install HiveServer2 (see Step 9.5 - Optional HiveServer2 Setup)
```

**5. Service timeout during startup:**
```bash
# If service fails with "start operation timed out. Terminating."
# Check logs for this pattern:
sudo journalctl -u hive-metastore.service --no-pager -n 20

# Fix: The service type is wrong, update it:
sudo systemctl stop hive-metastore
sudo sed -i 's/Type=forking/Type=simple/' /etc/systemd/system/hive-metastore.service
sudo sed -i '/PIDFile=/d' /etc/systemd/system/hive-metastore.service
sudo sed -i '/ExecStop=/d' /etc/systemd/system/hive-metastore.service
sudo systemctl daemon-reload
sudo systemctl start hive-metastore
```

**5. HDFS connection issues:**
```bash
# Test HDFS connectivity as hive user
sudo su - hive -c "export HADOOP_HOME=/opt/hadoop/current && export HADOOP_CONF_DIR=\$HADOOP_HOME/etc/hadoop && \$HADOOP_HOME/bin/hdfs dfs -ls /"

# Check HDFS is running
sudo systemctl status hadoop-namenode
sudo systemctl status hadoop-datanode
```

## Security Considerations

### Production Security Enhancements:

```bash
# 1. Change default passwords
sudo su - postgres -c "psql -c \"ALTER USER hive WITH PASSWORD 'your-secure-password';\""

# 2. Enable SSL for PostgreSQL connections
# Edit hive-site.xml:
# javax.jdo.option.ConnectionURL = jdbc:postgresql://192.168.1.184:5432/metastore?ssl=true

# 3. Restrict network access
sudo ufw allow from 192.168.1.0/24 to any port 9083
sudo ufw deny 9083

# 4. Enable Kerberos authentication (advanced)
# This requires additional Kerberos setup - consult Apache Hive documentation
```

## Performance Tuning

### Optimize for production workloads:

```xml
<!-- Add to hive-site.xml -->
<property>
    <name>datanucleus.connectionPool.maxActive</name>
    <value>10</value>
    <description>Maximum active connections to database</description>
</property>

<property>
    <name>datanucleus.connectionPool.maxIdle</name>
    <value>5</value>
    <description>Maximum idle connections in pool</description>
</property>

<property>
    <name>hive.metastore.client.cache.enabled</name>
    <value>true</value>
    <description>Enable client-side metastore caching</description>
</property>
```

## Integration with Other Services

### This Hive Metastore service enables:

1. **Trino Catalogs** - See [05_trino_cluster_setup.md](./05_trino_cluster_setup.md)
   - Iceberg catalog: `thrift://192.168.1.184:9083`
   - Hive catalog: `thrift://192.168.1.184:9083`

2. **Spark with Iceberg** - See [08_iceberg_distributed_comprehensive.md](./08_iceberg_distributed_comprehensive.md)
   - Iceberg catalog configuration: `spark.sql.catalog.iceberg_hive.uri=thrift://192.168.1.184:9083`

3. **Spark with Delta Lake** - See [09_deltalake_distributed_comprehensive.md](./09_deltalake_distributed_comprehensive.md)
   - Hive metastore integration for Delta Lake tables

## Maintenance

### Regular maintenance tasks:

```bash
# 1. Backup metastore database
sudo su - postgres -c "pg_dump metastore > /backup/metastore-$(date +%Y%m%d).sql"

# 2. Clean old logs
sudo find /opt/hive/current/logs -name "*.log.*" -mtime +30 -delete

# 3. Monitor service health
sudo systemctl status hive-metastore

# 4. Check database connections
sudo su - hive -c "$HIVE_HOME/bin/hive --service metatool -listFSRoot"
```

## Step 11: Client Usage Examples

### **How to Connect from Different Engines**

Now that your Hive Metastore is running, here are practical examples of how to use it from various clients:

#### **1. Trino Connection**

**Configure Trino Catalog** (`/opt/trino/etc/catalog/hive.properties`):
```properties
connector.name=hive
hive.metastore.uri=thrift://192.168.1.184:9083
hive.allow-drop-table=true
hive.allow-rename-table=true
```

**Test from Trino CLI:**
```sql
-- Connect to Trino
trino --server localhost:8080 --catalog hive --schema default

-- Verify metastore connection
SHOW SCHEMAS;

-- Create a test table
CREATE TABLE hive.default.test_table (
    id INTEGER,
    name VARCHAR(50),
    created_date DATE
);

-- Insert test data
INSERT INTO hive.default.test_table VALUES 
(1, 'Alice', DATE '2023-01-01'),
(2, 'Bob', DATE '2023-01-02');

-- Query the data
SELECT * FROM hive.default.test_table;

-- Verify in PostgreSQL metastore
-- (Run this in separate terminal)
-- sudo su - postgres -c "psql metastore -c 'SELECT * FROM \"TBLS\";'"
```

#### **2. Spark Connection**

**Configure Spark with Hive Metastore** (`spark-defaults.conf`):
```properties
spark.sql.catalog.spark_catalog=org.apache.spark.sql.hive.HiveSessionCatalog
spark.sql.catalog.spark_catalog.type=hive
spark.hadoop.hive.metastore.uris=thrift://192.168.1.184:9083
```

**Test from Spark Shell:**
```scala
// Start spark-shell or pyspark
spark-shell

// Verify metastore connection
spark.sql("SHOW DATABASES").show()

// Create a test table
spark.sql("""
    CREATE TABLE IF NOT EXISTS spark_test (
        user_id INT,
        username STRING,
        login_time TIMESTAMP
    ) USING PARQUET
    LOCATION 'hdfs://192.168.1.184:9000/lakehouse/spark_test'
""")

// Insert test data
spark.sql("""
    INSERT INTO spark_test VALUES 
    (101, 'user1', current_timestamp()),
    (102, 'user2', current_timestamp())
""")

// Query the data
spark.sql("SELECT * FROM spark_test").show()

// List tables
spark.sql("SHOW TABLES").show()
```

**Python/PySpark Example:**
```python
from pyspark.sql import SparkSession

# Create Spark session with Hive support
spark = SparkSession.builder \
    .appName("HiveMetastoreTest") \
    .config("spark.sql.catalog.spark_catalog.type", "hive") \
    .config("spark.hadoop.hive.metastore.uris", "thrift://192.168.1.184:9083") \
    .enableHiveSupport() \
    .getOrCreate()

# Test connection
spark.sql("SHOW DATABASES").show()

# Create DataFrame and save as table
data = [(1, "John", 25), (2, "Jane", 30), (3, "Bob", 35)]
columns = ["id", "name", "age"]
df = spark.createDataFrame(data, columns)

df.write \
  .mode("overwrite") \
  .option("path", "hdfs://192.168.1.184:9000/lakehouse/python_test") \
  .saveAsTable("python_test")

# Read back the table
result = spark.sql("SELECT * FROM python_test")
result.show()
```

#### **3. Flink Connection**

**Configure Flink with Hive Catalog** (`flink-conf.yaml`):
```yaml
table.catalog.hive_catalog.type: hive
table.catalog.hive_catalog.hive-conf-dir: /opt/hive/current/conf
table.catalog.hive_catalog.default-database: default
```

**Test from Flink SQL Client:**
```sql
-- Start Flink SQL Client
./bin/sql-client.sh

-- Set catalog
USE CATALOG hive_catalog;

-- Show databases
SHOW DATABASES;

-- Create table
CREATE TABLE flink_test (
    event_id INT,
    event_name STRING,
    event_time TIMESTAMP(3)
) WITH (
    'connector' = 'filesystem',
    'path' = 'hdfs://192.168.1.184:9000/lakehouse/flink_test',
    'format' = 'parquet'
);

-- Insert data
INSERT INTO flink_test VALUES 
(1, 'login', LOCALTIMESTAMP),
(2, 'logout', LOCALTIMESTAMP);

-- Query data
SELECT * FROM flink_test;
```

#### **4. Direct Metastore Client Testing**

**Test Metastore Connectivity:**
```bash
# Test from any client machine
telnet 192.168.1.184 9083
# Should connect successfully

# List filesystem roots
sudo su - hive -c "export HIVE_HOME=/opt/hive/current && \$HIVE_HOME/bin/hive --service metatool -listFSRoot"

# Check metastore status
sudo su - hive -c "export HIVE_HOME=/opt/hive/current && \$HIVE_HOME/bin/hive --service metatool -info"
```

**Monitor Table Creation in PostgreSQL:**
```bash
# Watch tables being created in real-time
sudo su - postgres -c "psql metastore -c 'SELECT TBL_NAME, TBL_TYPE, CREATE_TIME FROM \"TBLS\" ORDER BY CREATE_TIME DESC;'"

# Check table schemas
sudo su - postgres -c "psql metastore -c 'SELECT t.TBL_NAME, c.COLUMN_NAME, c.TYPE_NAME FROM \"TBLS\" t JOIN \"SDS\" s ON t.SD_ID = s.SD_ID JOIN \"COLUMNS_V2\" c ON s.CD_ID = c.CD_ID ORDER BY t.TBL_NAME, c.INTEGER_IDX;'"
```

### **5. Client Configuration Files**

**For Other Nodes (cpu-node2, worker-node3):**

Create `hive-site.xml` for client access:
```xml
<?xml version="1.0"?>
<configuration>
    <property>
        <name>hive.metastore.uris</name>
        <value>thrift://192.168.1.184:9083</value>
        <description>Hive Metastore Server</description>
    </property>
    
    <property>
        <name>hive.metastore.warehouse.dir</name>
        <value>hdfs://192.168.1.184:9000/lakehouse</value>
        <description>Warehouse directory</description>
    </property>
    
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://192.168.1.184:9000</value>
        <description>Default filesystem</description>
    </property>
</configuration>
```

### **6. Troubleshooting Client Connections**

```bash
# Test connectivity
telnet 192.168.1.184 9083

# Check if metastore is accepting connections
sudo netstat -an | grep 9083

# Test from client with hive command
hive --service metatool -listFSRoot

# Check logs for connection issues
sudo journalctl -u hive-metastore -f
```

## Next Steps

✅ **Hive Metastore is now running and ready!**

**What you have installed:**
- ✅ **Hive Metastore** (Port 9083) - Required for Trino/Spark/Flink lakehouse integration
- ⚠️ **HiveServer2** (Port 10000) - Optional, only if you completed Step 9.5

**Note:** For lakehouse analytics with Trino, Spark, and Flink, you only need the Metastore service.

**Continue with lakehouse table formats:**
- [08_iceberg_distributed_comprehensive.md](./08_iceberg_distributed_comprehensive.md) - Apache Iceberg tables
- [09_deltalake_distributed_comprehensive.md](./09_deltalake_distributed_comprehensive.md) - Delta Lake tables

**Or enable Trino catalogs:**
- Return to [05_trino_cluster_setup.md - Step 7](./05_trino_cluster_setup.md#step-7-lakehouse-connectors-iceberg--delta-lake) to enable Iceberg and Delta Lake catalogs

---

**Service Status Check:**
```bash
# Verify core components are running:
sudo systemctl status hive-metastore    # ✅ Should be active
sudo systemctl status postgresql        # ✅ Should be active  
sudo systemctl status hadoop-namenode   # ✅ Should be active
sudo netstat -tlnp | grep 9083         # ✅ Should show hive metastore listening

# Optional: If you installed HiveServer2 (Step 9.5):
sudo systemctl status hiveserver2       # ✅ Should be active (if installed)
sudo netstat -tlnp | grep 10000        # ✅ Should show hiveserver2 listening (if installed)
```

🎉 **Your Hive Metastore is ready for lakehouse analytics!**
