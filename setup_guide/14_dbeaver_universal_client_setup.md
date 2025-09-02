# DBeaver Universal Database Client Setup Guide

## Overview
DBeaver is a powerful, free, and open-source universal database tool that will serve as our primary SQL client and database administration interface for the entire Data Engineering HomeLab. This guide sets up DBeaver with connections to all available data sources in your distributed environment.

## Why DBeaver for Data Engineering?
- **Universal Connectivity**: Supports 80+ database types via JDBC/ODBC drivers
- **Advanced SQL Editor**: Syntax highlighting, auto-completion, and formatting
- **Data Visualization**: Built-in charts, graphs, and export capabilities  
- **Schema Navigation**: Visual database browser and ER diagrams
- **Query Performance**: Execution plans, query history, and optimization tools
- **Data Transfer**: ETL capabilities between different data sources
- **Free & Open Source**: No licensing costs with professional features

## Target Data Sources in HomeLab
Based on your existing setup guides, DBeaver will connect to:

### Primary Data Sources
- **PostgreSQL** - Primary (cpu-node1) + Replica (cpu-node2) 
- **Apache Trino** - Distributed query engine (coordinator on cpu-node1)
- **Redis** - In-memory data store (cpu-node1)
- **Elasticsearch** - Search and analytics (3-node cluster)

### Secondary Data Sources  
- **Neo4j** - Graph database (cpu-node1)
- **Apache Spark** - Via Thrift JDBC server
- **Apache Kafka** - Via specialized connectors
- **File Sources** - CSV, Parquet, JSON, etc.

## Architecture Overview
```
┌─────────────────────────────────────────────────────────────────────┐
│                        DBeaver Workstation                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │ PostgreSQL  │ │   Trino     │ │   Redis     │ │Elasticsearch│  │
│  │ Connection  │ │ Connection  │ │ Connection  │ │ Connection  │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   cpu-node1     │    │   cpu-node2     │    │  worker-node3   │
│  - PostgreSQL   │    │  - PostgreSQL   │    │  - Elasticsearch│
│  - Trino Coord  │    │  - Trino Worker │    │  - Trino Worker │
│  - Redis        │    │  - Elasticsearch│    │  - Kafka Broker │
│  - Kafka Broker │    │  - Kafka Broker │    │                 │
│  192.168.1.184  │    │  192.168.1.187  │    │  192.168.1.190  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Port Allocation Summary
**⚠️ Important**: These are the ports your data sources are using (from existing setup guides):

### Database Ports
- **PostgreSQL**: 5432 (Primary: cpu-node1, Replica: cpu-node2)
- **Redis**: 6379 (cpu-node1)
- **Trino Coordinator**: 8084 (cpu-node1)
- **Trino Workers**: 8082 (cpu-node2), 8083 (worker-node3)

### Search & Analytics Ports
- **Elasticsearch**: 9200 (HTTP), 9300 (Transport) - All nodes
- **Kibana**: 5601 (cpu-node1)

### Stream Processing Ports  
- **Kafka Brokers**: 9092 (all nodes)
- **ZooKeeper**: 2181 (all nodes)
- **Kafka Connect**: 8083 (conflicts with Trino worker-node3)
- **Kafdrop**: 9001 (Kafka UI)

### Big Data Ports
- **Spark Master**: 8080 (WebUI), 7077 (Master) - cpu-node1
- **Spark Workers**: 8081 (WebUI), 7078 (Worker) - cpu-node2, worker-node3  
- **Flink JobManager**: 8081 (WebUI), 6123 (RPC) - cpu-node1
- **Flink TaskManager**: 6122 (RPC) - workers

### ML & Feature Store Ports
- **MLflow**: 5000 (cpu-node1)
- **Feast**: 6566 (cpu-node1)
- **Jupyter**: 8888 (gpu-node)

## Step 1: DBeaver Installation

### Option 1: Install via APT (Recommended)
```bash
# Add DBeaver repository
curl -fsSL https://dbeaver.io/debs/dbeaver.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/dbeaver.gpg
echo "deb [signed-by=/usr/share/keyrings/dbeaver.gpg] https://dbeaver.io/debs/dbeaver-ce /" | sudo tee /etc/apt/sources.list.d/dbeaver.list

# Update and install
sudo apt update
sudo apt install -y dbeaver-ce

# Verify installation
dbeaver --version
```

### Option 2: Install via Snap
```bash
sudo snap install dbeaver-ce
```

### Option 3: Download DEB Package
```bash
# Download latest DEB package
wget -O dbeaver.deb https://dbeaver.io/files/dbeaver-ce_latest_amd64.deb

# Install
sudo dpkg -i dbeaver.deb

# Fix dependencies if needed
sudo apt-get install -f
```

### Option 4: Portable Installation
```bash
# Download portable version
wget https://dbeaver.io/files/dbeaver-ce-latest-linux.gtk.x86_64.tar.gz

# Extract
tar -xzf dbeaver-ce-latest-linux.gtk.x86_64.tar.gz
mv dbeaver /opt/dbeaver

# Create desktop entry
cat << EOF | sudo tee /usr/share/applications/dbeaver.desktop
[Desktop Entry]
Name=DBeaver Community Edition
Comment=Universal Database Tool
Exec=/opt/dbeaver/dbeaver
Icon=/opt/dbeaver/dbeaver.png
Type=Application
Categories=Development;Database;
EOF
```

## Step 2: Required JDBC Drivers Installation

DBeaver includes many drivers, but some require manual installation:

### Essential Drivers Setup
```bash
# Create driver directory
mkdir -p ~/.dbeaver/drivers

# Download additional drivers if needed
cd ~/.dbeaver/drivers

# Trino JDBC Driver (if not included)
wget https://repo1.maven.org/maven2/io/trino/trino-jdbc/435/trino-jdbc-435.jar

# Redis JDBC Driver
wget https://github.com/RedisLabs/JRediSearch/releases/download/v2.8.4/jedis-4.4.3.jar

# Apache Kafka JDBC Driver (optional, for specialized tools)
wget https://packages.confluent.io/maven/io/confluent/kafka-jdbc/10.7.6/kafka-jdbc-10.7.6.jar
```

### Verify Java Installation (Required for JDBC)
```bash
java -version
# Should show Java 11+ for compatibility with all drivers

# If Java is not installed:
sudo apt install -y openjdk-17-jdk
```

## Step 3: Database Connection Configuration

### Connection 1: PostgreSQL Primary (READ/WRITE)
```
Connection Name: PostgreSQL-Primary-cpu-node1
Host: 192.168.1.184
Port: 5432
Database: analytics_db
Username: dataeng
Password: [your-password]
Driver: PostgreSQL
```

**Connection String:**
```
jdbc:postgresql://192.168.1.184:5432/analytics_db
```

**Additional Databases to Configure:**
- `lakehouse_db` - For Iceberg/Delta Lake metadata
- `streaming_db` - For real-time analytics
- `metastore` - For Hive Metastore (if configured)

### Connection 2: PostgreSQL Replica (READ-ONLY)
```
Connection Name: PostgreSQL-Replica-cpu-node2
Host: 192.168.1.187  
Port: 5432
Database: analytics_db
Username: dataeng
Password: [your-password]
Driver: PostgreSQL
Read-only: true
```

### Connection 3: Trino Coordinator (FEDERATED QUERIES)
```
Connection Name: Trino-Coordinator-cpu-node1
Host: 192.168.1.184
Port: 8084
Catalog: postgresql (or tpch, memory, etc.)
Schema: public
Username: [your-username]
Driver: Trino
```

**Connection URL:**
```
jdbc:trino://192.168.1.184:8084/postgresql/public
```

**Available Trino Catalogs** (from your setup):
- `postgresql` - Federated PostgreSQL access
- `kafka` - Stream processing queries
- `iceberg` - Lakehouse queries
- `delta` - Delta Lake queries  
- `memory` - Temporary tables
- `tpch` - Benchmarking

### Connection 4: Redis (KEY-VALUE STORE)
```
Connection Name: Redis-cpu-node1
Host: 192.168.1.184
Port: 6379
Password: [your-redis-password]
Driver: Redis
Database: 0 (default)
```

**Note**: Redis support in DBeaver requires the Redis plugin. Install via:
`Help → Install New Software → Add → Name: DBeaver Redis → Location: https://dbeaver.io/update/redis/latest/`

### Connection 5: Elasticsearch (SEARCH & ANALYTICS)
```
Connection Name: Elasticsearch-Cluster
Host: 192.168.1.184
Port: 9200
Index: [your-index-pattern]
Driver: Elasticsearch
Authentication: None (or basic auth if configured)
```

**Connection URL:**
```
http://192.168.1.184:9200
```

**Note**: Elasticsearch support requires the Elasticsearch plugin from DBeaver marketplace.

### Connection 6: Neo4j (GRAPH DATABASE)
```
Connection Name: Neo4j-cpu-node1
Host: 192.168.1.184  
Port: 7687 (Bolt)
Database: neo4j
Username: neo4j
Password: [your-neo4j-password]
Driver: Neo4j
```

### Connection 7: Apache Spark (BIG DATA PROCESSING)
```
Connection Name: Spark-ThriftServer-cpu-node1
Host: 192.168.1.184
Port: 10000 (Thrift Server port)
Database: default
Username: [spark-user]
Driver: Spark
```

**Note**: Requires Spark Thrift Server to be running:
```bash
# Start Spark Thrift Server on cpu-node1
$SPARK_HOME/sbin/start-thriftserver.sh \
  --master spark://192.168.1.184:7077 \
  --hiveconf hive.server2.thrift.port=10000
```

## Step 4: Advanced Connection Features

### Connection Pooling Configuration
For each connection, configure connection pooling:

```
Connection Properties:
- Initial pool size: 2
- Maximum pool size: 10
- Connection timeout: 30 seconds
- Keep alive interval: 600 seconds
```

### SSL/TLS Configuration (If Enabled)
For production setups with SSL:

```
SSL Mode: require
SSL Factory: org.postgresql.ssl.DefaultJavaSSLFactory
SSL Cert: /path/to/client-cert.pem
SSL Key: /path/to/client-key.pem
SSL Root Cert: /path/to/ca-cert.pem
```

### Connection Variables
Set connection-specific variables:

**PostgreSQL:**
```sql
-- Set work_mem for analytics queries
SET work_mem = '256MB';
-- Set search path
SET search_path = analytics, public;
```

**Trino:**
```sql
-- Set session properties
SET SESSION query_max_run_time = '1h';
SET SESSION query_max_memory = '8GB';
```

## Step 5: DBeaver Configuration Optimization

### Performance Settings
Edit `~/.dbeaver/dbeaver.ini`:

```ini
# Increase memory allocation
-Xmx4G
-Xms1G

# Optimize garbage collection
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200

# Enable SQL formatter
-Ddbeaver.sql.format.enabled=true

# Connection timeout
-Ddbeaver.net.timeout=60000
```

### SQL Editor Configuration
```
Preferences → Editors → SQL Editor:
- Enable auto-completion: true
- Auto-completion delay: 500ms
- Statement delimiter: semicolon
- Enable SQL formatting: true
- Max result set size: 10000 rows
```

### Data Transfer Settings
```
Preferences → Data Transfer:
- Default fetch size: 1000
- Max memory per query: 1GB  
- Enable streaming for large results: true
```

## Step 6: Testing All Connections

### PostgreSQL Connection Test
```sql
-- Test primary connection
SELECT 
    version() as postgres_version,
    current_database() as database,
    current_user as user,
    inet_server_addr() as server_ip;

-- Test replica connection (should be read-only)
SELECT pg_is_in_recovery() as is_replica;

-- Test table access
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public'
LIMIT 10;
```

### Trino Connection Test  
```sql
-- Show available catalogs
SHOW CATALOGS;

-- Test federation query
SELECT 
    'postgresql' as source,
    count(*) as table_count
FROM information_schema.tables 
WHERE table_schema = 'public'

UNION ALL

SELECT 
    'tpch' as source,
    count(*) as table_count  
FROM tpch.information_schema.tables
WHERE table_schema = 'tiny';

-- Test cross-catalog join
SELECT 
    p.name as postgres_data,
    t.name as tpch_data
FROM postgresql.public.users p
CROSS JOIN tpch.tiny.nation t
LIMIT 5;
```

### Redis Connection Test
```sql
-- Redis commands (if Redis plugin is installed)
PING
INFO server
KEYS *
GET some_key
```

### Elasticsearch Test (via HTTP)
```bash
# Test cluster health
curl "http://192.168.1.184:9200/_cluster/health?pretty"

# List indices
curl "http://192.168.1.184:9200/_cat/indices?v"
```

## Step 7: Advanced Features Setup

### Data Visualization
Create charts and graphs directly from query results:

```sql
-- Sample query for visualization
SELECT 
    DATE_TRUNC('day', created_at) as day,
    count(*) as daily_orders,
    sum(amount) as daily_revenue
FROM postgresql.public.orders 
WHERE created_at >= current_date - interval '30 days'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY day;
```

**Create visualization:**
1. Execute query
2. Right-click results → "View/Format" → "View Chart"
3. Select chart type (Line, Bar, Pie, etc.)
4. Configure axes and styling

### Data Export/Import
Set up data transfer between sources:

```sql
-- Export PostgreSQL data to CSV
-- Right-click table → Export Data → CSV

-- Import CSV to PostgreSQL  
-- Right-click database → Import Data → CSV
```

### SQL Script Management
Organize your SQL scripts:

```
Project Structure:
├── PostgreSQL/
│   ├── DDL/
│   │   ├── table_creation.sql
│   │   └── index_creation.sql
│   ├── DML/
│   │   ├── data_inserts.sql
│   │   └── data_updates.sql
│   └── Analytics/
│       ├── daily_reports.sql
│       └── performance_queries.sql
├── Trino/
│   ├── Federation/
│   │   ├── cross_catalog_joins.sql
│   │   └── data_lake_queries.sql
│   └── Performance/
│       ├── optimization_queries.sql
│       └── partition_analysis.sql
└── Utilities/
    ├── monitoring_queries.sql
    └── maintenance_scripts.sql
```

## Step 8: Security Best Practices

### Connection Security
```
1. Use connection-specific passwords
2. Enable SSL/TLS where available
3. Limit connection privileges
4. Use read-only connections for reporting
5. Regularly rotate credentials
```

### Query Security
```sql
-- Use parameterized queries
SELECT * FROM users WHERE id = ?;

-- Avoid dynamic SQL construction
-- BAD: "SELECT * FROM " + table_name
-- GOOD: Pre-defined table whitelist
```

### Audit Configuration
```
Enable query logging:
Preferences → Editors → SQL Editor → Log file: ~/.dbeaver/query.log
```

## Step 9: Monitoring and Maintenance

### Connection Health Monitoring
Create a monitoring dashboard:

```sql
-- PostgreSQL connection monitoring
SELECT 
    datname,
    numbackends,
    xact_commit,
    xact_rollback,
    blks_read,
    blks_hit,
    tup_returned,
    tup_fetched
FROM pg_stat_database
WHERE datname NOT IN ('template0', 'template1', 'postgres');

-- Trino cluster monitoring  
SELECT 
    node_id,
    http_uri,
    node_version,
    coordinator,
    state
FROM system.runtime.nodes;
```

### Performance Monitoring
```sql
-- Long-running queries (PostgreSQL)
SELECT 
    pid,
    now() - pg_stat_activity.query_start AS duration,
    query,
    state,
    client_addr
FROM pg_stat_activity 
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
AND state = 'active';

-- Query statistics (Trino)
SELECT 
    query_id,
    state,
    total_cpu_time,
    total_scheduled_time,
    memory_reservation
FROM system.runtime.queries 
ORDER BY created DESC 
LIMIT 20;
```

### Regular Maintenance Tasks
```sql
-- PostgreSQL maintenance
VACUUM ANALYZE;
REINDEX DATABASE analytics_db;

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

## Step 10: Integration with Other Tools

### Jupyter Notebook Integration
Install DBeaver plugin for Jupyter:

```bash
# Install SQL magic extension
pip install ipython-sql

# In Jupyter notebook
%load_ext sql
%sql postgresql://dataeng:password@192.168.1.184:5432/analytics_db
```

### Git Integration
Version control your SQL scripts:

```bash
# Initialize git repository
cd ~/.dbeaver/scripts
git init
git add .
git commit -m "Initial DBeaver scripts"

# Connect to remote repository
git remote add origin https://github.com/yourusername/dbeaver-scripts.git
git push -u origin main
```

### REST API Integration
Use DBeaver's REST API (Enterprise feature) or create custom scripts:

```python
# Python script for automated queries
import psycopg2
import pandas as pd

def run_query(query):
    conn = psycopg2.connect(
        host="192.168.1.184",
        port=5432,
        database="analytics_db",
        user="dataeng",
        password="your-password"
    )
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Usage
result = run_query("SELECT * FROM users LIMIT 10")
print(result)
```

## Step 11: Backup and Recovery

### Connection Profiles Backup
```bash
# Backup DBeaver configuration
tar -czf dbeaver-config-$(date +%Y%m%d).tar.gz ~/.dbeaver

# Restore configuration
tar -xzf dbeaver-config-20241201.tar.gz -C ~/
```

### Script Repository Backup
```bash
# Create backup of all SQL scripts
find ~/.dbeaver -name "*.sql" -exec cp {} backup/scripts/ \;

# Create compressed backup
tar -czf dbeaver-scripts-$(date +%Y%m%d).tar.gz backup/scripts/
```

## Step 12: Troubleshooting Guide

### Common Connection Issues

#### Issue 1: PostgreSQL Connection Timeout
**Symptoms:** Connection timeout after 30 seconds
**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check network connectivity  
telnet 192.168.1.184 5432

# Verify pg_hba.conf allows connections
sudo grep "192.168.1.0/24" /etc/postgresql/16/main/pg_hba.conf
```

#### Issue 2: Trino Connection Refused
**Symptoms:** "Connection refused" on port 8084
**Solution:**
```bash
# Check Trino coordinator status
sudo systemctl status trino

# Verify Trino is listening
netstat -tlnp | grep 8084

# Check firewall
sudo ufw status | grep 8084
```

#### Issue 3: Out of Memory Errors
**Symptoms:** DBeaver crashes with large result sets
**Solution:**
```bash
# Increase DBeaver memory in ~/.dbeaver/dbeaver.ini
-Xmx8G
-XX:MaxDirectMemorySize=2G

# Limit result set size in queries
SELECT * FROM large_table LIMIT 1000;
```

#### Issue 4: Driver Not Found
**Symptoms:** "No suitable driver found for jdbc:..."
**Solution:**
```bash
# Download missing driver
cd ~/.dbeaver/drivers
wget [driver-url]

# In DBeaver: Driver Manager → Add → Select JAR file
```

### Performance Troubleshooting

#### Slow Query Performance
```sql
-- PostgreSQL: Enable query timing
\timing on

-- Analyze query execution plan
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM large_table WHERE condition;

-- Trino: Show query statistics
SHOW STATS FOR (SELECT * FROM catalog.schema.table);
```

#### Connection Pool Issues
```
Symptoms: "Too many connections" errors
Solutions:
1. Reduce max pool size in connection properties
2. Enable connection timeout
3. Use read replicas for reporting queries
```

## Step 13: Advanced Use Cases

### Cross-Database Analytics
```sql
-- Join data from PostgreSQL and Trino Iceberg tables
WITH postgres_sales AS (
    SELECT 
        product_id,
        sum(amount) as pg_sales
    FROM postgresql.public.sales 
    WHERE date >= '2024-01-01'
    GROUP BY product_id
),
iceberg_inventory AS (
    SELECT 
        product_id,
        current_stock
    FROM iceberg.warehouse.inventory
)
SELECT 
    p.product_id,
    p.pg_sales,
    i.current_stock,
    p.pg_sales / NULLIF(i.current_stock, 0) as turnover_ratio
FROM postgres_sales p
JOIN iceberg_inventory i ON p.product_id = i.product_id;
```

### Real-time Data Monitoring
```sql
-- Monitor streaming data via Kafka connector in Trino
SELECT 
    _key,
    _timestamp,
    json_extract_scalar(_message, '$.user_id') as user_id,
    json_extract_scalar(_message, '$.event_type') as event_type
FROM kafka.default."user-events"
WHERE _timestamp > current_timestamp - interval '5' minute
ORDER BY _timestamp DESC;
```

### Data Quality Checks
```sql
-- Multi-source data quality validation
SELECT 
    'postgresql' as source,
    count(*) as total_records,
    count(DISTINCT id) as unique_ids,
    count(*) - count(DISTINCT id) as duplicates,
    count(*) - count(email) as null_emails
FROM postgresql.public.users

UNION ALL

SELECT 
    'trino_cache' as source,
    count(*) as total_records,
    count(DISTINCT user_id) as unique_ids,
    count(*) - count(DISTINCT user_id) as duplicates,
    count(*) - count(user_email) as null_emails
FROM memory.default.users_cache;
```

## Step 14: Team Collaboration Features

### Shared Connection Profiles
```bash
# Export connection configuration
# File → Export → DBeaver → Connections
# Import on team member machines

# Or use centralized configuration
git clone https://github.com/company/dbeaver-configs.git
ln -s dbeaver-configs/connections ~/.dbeaver/connections
```

### SQL Template Library
Create reusable SQL templates:

```sql
-- Template: Daily Sales Report
SELECT 
    DATE(created_at) as sale_date,
    count(*) as order_count,
    sum(amount) as revenue,
    avg(amount) as avg_order_value
FROM ${catalog}.${schema}.orders 
WHERE created_at >= '${start_date}'
AND created_at < '${end_date}'
GROUP BY DATE(created_at)
ORDER BY sale_date DESC;

-- Usage: Replace variables before execution
-- ${catalog} = postgresql
-- ${schema} = public  
-- ${start_date} = 2024-12-01
-- ${end_date} = 2024-12-02
```

### Code Review Process
```bash
# Version control SQL queries
mkdir -p ~/dbeaver-queries/reviews
git init ~/dbeaver-queries
cd ~/dbeaver-queries

# Create pull request workflow
git checkout -b feature/new-analytics-query
# ... develop query ...
git add analytics_report.sql
git commit -m "Add monthly analytics report"
git push origin feature/new-analytics-query
# Create pull request for review
```

## Conclusion

You now have a comprehensive DBeaver setup that connects to all data sources in your Data Engineering HomeLab:

### Successfully Configured Connections:
✅ **PostgreSQL** (Primary + Replica) - Relational data
✅ **Trino** (Distributed queries) - Data federation
✅ **Redis** (Key-value store) - Caching layer
✅ **Elasticsearch** (Search engine) - Full-text search  
✅ **Neo4j** (Graph database) - Relationships
✅ **Apache Spark** (Big data) - Analytics processing

### Key Benefits Achieved:
- **Unified Interface**: Single tool for all data sources
- **Advanced SQL**: Powerful query editor with intelligence
- **Visual Analytics**: Built-in charting and reporting
- **Data Federation**: Join across different databases
- **Performance**: Optimized connections and query execution
- **Team Collaboration**: Shared templates and configurations

### Next Steps:
1. **Cassandra Setup** (15_cassandra_distributed_setup.md) - Add NoSQL wide-column store
2. **Application Ideas** (16_application_ideas_medium_to_advanced.md) - Build projects using DBeaver
3. **Advanced Analytics**: Leverage DBeaver for complex cross-system queries
4. **Monitoring Dashboards**: Create operational visibility
5. **Data Pipeline Integration**: Use DBeaver for ETL development and testing

Your DBeaver installation provides a professional-grade database workbench that scales with your data engineering needs, from simple queries to complex multi-source analytics!
