# Neo4j Graph Database Setup Guide

## Overview
Neo4j will be set up on cpu-node2 to provide graph database capabilities for advanced analytics, social network analysis, fraud detection, and recommendation systems. This setup integrates with your existing data engineering ecosystem.

## What is Neo4j?
Neo4j is a highly scalable, native graph database that leverages data relationships as first-class entities, helping enterprises build intelligent applications to meet today's evolving connected data challenges.

## Machine Configuration
- **Primary Node**: cpu-node2 (192.168.1.187)
- **Backup/Read Replica**: worker-node3 (192.168.1.190) - optional

## Prerequisites
- Ubuntu/Debian-based Linux distribution
- Java 17 (required for Neo4j 5.x)
- At least 4GB RAM (8GB recommended)
- At least 20GB free disk space
- Network connectivity to other nodes

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   gpu-node          │
│  - PostgreSQL       │────│  - Neo4j Primary    │────│  - ML Pipelines     │
│  - Kafka            │    │  - Bolt Protocol    │    │  - Graph ML         │
│  - Spark Master     │    │  - Web Interface    │    │  - TensorFlow       │
│  192.168.1.184      │    │  192.168.1.187      │    │  192.168.1.79       │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Step 1: Java 17 Installation (cpu-node2)

```bash
# Update package repository
sudo apt update

# Install OpenJDK 17 (required for Neo4j 5.x)
sudo apt install -y openjdk-17-jdk

# Verify Java installation
java -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

## Step 2: Neo4j Installation

```bash
# Add Neo4j repository
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 5' | sudo tee -a /etc/apt/sources.list.d/neo4j.list

# Update package list
sudo apt update

# Install Neo4j Community Edition
sudo apt install -y neo4j
```

## Step 3: Configuration Setup

### Main Neo4j Configuration:
```bash
sudo nano /etc/neo4j/neo4j.conf
```

```properties
# The name of the default database
initial.dbms.default_database=neo4j

# Paths of directories in the installation.
server.directories.data=/var/lib/neo4j/data
server.directories.plugins=/var/lib/neo4j/plugins
server.directories.logs=/var/log/neo4j
server.directories.lib=/usr/share/neo4j/lib
#server.directories.run=run
#server.directories.licenses=licenses
#server.directories.transaction.logs.root=data/transactions
server.logs.config=/etc/neo4j/server-logs.xml
server.logs.user.config=/etc/neo4j/user-logs.xml

# This setting constrains all `LOAD CSV` import files to be under the `import` directory. Remove or comment it out to
# allow files to be loaded from anywhere in the filesystem; this introduces possible security problems. See the
# `LOAD CSV` section of the manual for details.
server.directories.import=/var/lib/neo4j/import

# Whether requests to Neo4j are authenticated.
# To disable authentication, uncomment this line
dbms.security.auth_enabled=true

# Anonymous usage data reporting
# To disable, uncomment this line
#dbms.usage_report.enabled=false

#********************************************************************
# Memory Settings
#********************************************************************
#
# Memory settings are specified kibibytes with the 'k' suffix, mebibytes with
# 'm' and gibibytes with 'g'.
# If Neo4j is running on a dedicated server, then it is generally recommended
# to leave about 2-4 gigabytes for the operating system, give the JVM enough
# heap to hold all your transaction state and query context, and then leave the
# rest for the page cache.

# Java Heap Size: by default the Java heap size is dynamically calculated based
# on available system resources. Uncomment these lines to set specific initial
# and maximum heap size.
server.memory.heap.initial_size=2G
server.memory.heap.max_size=4G

# The amount of memory to use for mapping the store files.
# The default page cache memory assumes the machine is dedicated to running
# Neo4j, and is heuristically set to 50% of RAM minus the Java heap size.
server.memory.pagecache.size=2G

# Limit the amount of memory that all of the running transaction can consume.
# The default value is 70% of the heap size limit.
#dbms.memory.transaction.total.max=256m

# Limit the amount of memory that a single transaction can consume.
# By default there is no limit.
#db.memory.transaction.max=16m

#*****************************************************************
# Network connector configuration
#*****************************************************************

# With default configuration Neo4j only accepts local connections.
# To accept non-local connections, uncomment this line:
server.default_listen_address=0.0.0.0

# You can also choose a specific network interface, and configure a non-default
# port for each connector, by setting their individual listen_address.

# The address at which this server can be reached by its clients. This may be the server's IP address or DNS name, or
# it may be the address of a reverse proxy which sits in front of the server. This setting may be overridden for
# individual connectors below.
server.default_advertised_address=192.168.1.187

# You can also choose a specific advertised hostname or IP address, and
# configure an advertised port for each connector, by setting their
# individual advertised_address.

# By default, encryption is turned off.
# To turn on encryption, an ssl policy for the connector needs to be configured
# Read more in SSL policy section in this file for how to define a SSL policy.

# Bolt connector
server.bolt.enabled=true
#server.bolt.tls_level=DISABLED
server.bolt.listen_address=0.0.0.0:7687
server.bolt.advertised_address=192.168.1.187:7687

# HTTP Connector. There can be zero or one HTTP connectors.
server.http.enabled=true
server.http.listen_address=0.0.0.0:7474
server.http.advertised_address=192.168.1.187:7474

# HTTPS Connector. There can be zero or one HTTPS connectors.
server.https.enabled=false
server.https.listen_address=0.0.0.0:7473
#server.https.advertised_address=:7473

# Number of Neo4j worker threads.
#server.threads.worker_count=

#*****************************************************************
# Logging configuration
#*****************************************************************

# To enable HTTP logging, uncomment this line
#dbms.logs.http.enabled=true

# To enable GC Logging, uncomment this line
#server.logs.gc.enabled=true

# GC Logging Options
# see https://docs.oracle.com/en/java/javase/11/tools/java.html#GUID-BE93ABDC-999C-4CB5-A88B-1994AAAC74D5
#server.logs.gc.options=-Xlog:gc*,safepoint,age*=trace

# Number of GC logs to keep.
#server.logs.gc.rotation.keep_number=5

# Size of each GC log that is kept.
#server.logs.gc.rotation.size=20m

#*****************************************************************
# Miscellaneous configuration
#*****************************************************************

# Determines if Cypher will allow using file URLs when loading data using
# `LOAD CSV`. Setting this value to `false` will cause Neo4j to fail `LOAD CSV`
# clauses that load data from the file system.
#dbms.security.allow_csv_import_from_file_urls=true

# Value of the Access-Control-Allow-Origin header sent over any HTTP or HTTPS
# connector. This defaults to '*', which allows broadest compatibility. Note
# that any URI provided here limits HTTP/HTTPS access to that URI only.
#dbms.security.http_access_control_allow_origin=*

# Value of the HTTP Strict-Transport-Security (HSTS) response header. This header
# tells browsers that a webpage should only be accessed using HTTPS instead of HTTP.
# It is attached to every HTTPS response. Setting is not set by default so
# 'Strict-Transport-Security' header is not sent. Value is expected to contain
# directives like 'max-age', 'includeSubDomains' and 'preload'.
#dbms.security.http_strict_transport_security=

# Retention policy for transaction logs needed to perform recovery and backups.
db.tx_log.rotation.retention_policy=2 days 2G

# Whether or not any database on this instance are read_only by default.
# If false, individual databases may be marked as read_only using dbms.database.read_only.
# If true, individual databases may be marked as writable using dbms.databases.writable.
dbms.databases.default_to_read_only=false

# Comma separated list of JAX-RS packages containing JAX-RS resources, one
# package name for each mountpoint. The listed package names will be loaded
# under the mountpoints specified. Uncomment this line to mount the
# org.neo4j.examples.server.unmanaged.HelloWorldResource.java from
# neo4j-server-examples under /examples/unmanaged, resulting in a final URL of
# http://localhost:7474/examples/unmanaged/helloworld/{nodeId}
#server.unmanaged_extension_classes=org.neo4j.examples.server.unmanaged=/examples/unmanaged

# A comma separated list of procedures and user defined functions that are allowed
# full access to the database through unsupported/insecure internal APIs.
#dbms.security.procedures.unrestricted=my.extensions.example,my.procedures.*

# A comma separated list of procedures to be loaded by default.
# Leaving this unconfigured will load all procedures found.
#dbms.security.procedures.allowlist=apoc.coll.*,apoc.load.*,gds.*

#********************************************************************
# JVM Parameters
#********************************************************************

# G1GC generally strikes a good balance between throughput and tail
# latency, without too much tuning.
server.jvm.additional=-XX:+UseG1GC

# Have common exceptions keep producing stack traces, so they can be
# debugged regardless of how often logs are rotated.
server.jvm.additional=-XX:-OmitStackTraceInFastThrow

# Make sure that `initmemory` is not only allocated, but committed to
# the process, before starting the database. This reduces memory
# fragmentation, increasing the effectiveness of transparent huge
# pages. It also reduces the possibility of seeing performance drop
# due to heap-growing GC events, where a decrease in available page
# cache leads to an increase in mean IO response time.
# Try reducing the heap memory, if this flag degrades performance.
server.jvm.additional=-XX:+AlwaysPreTouch

# Trust that non-static final fields are really final.
# This allows more optimizations and improves overall performance.
# NOTE: Disable this if you use embedded mode, or have extensions or dependencies that may use reflection or
# serialization to change the value of final fields!
server.jvm.additional=-XX:+UnlockExperimentalVMOptions
server.jvm.additional=-XX:+TrustFinalNonStaticFields

# Disable explicit garbage collection, which is occasionally invoked by the JDK itself.
server.jvm.additional=-XX:+DisableExplicitGC

# Restrict size of cached JDK buffers to 1 KB
server.jvm.additional=-Djdk.nio.maxCachedBufferSize=1024

# More efficient buffer allocation in Netty by allowing direct no cleaner buffers.
server.jvm.additional=-Dio.netty.tryReflectionSetAccessible=true

# Exits JVM on the first occurrence of an out-of-memory error. Its preferable to restart VM in case of out of memory errors.
# server.jvm.additional=-XX:+ExitOnOutOfMemoryError

# Expand Diffie Hellman (DH) key size from default 1024 to 2048 for DH-RSA cipher suites used in server TLS handshakes.
# This is to protect the server from any potential passive eavesdropping.
server.jvm.additional=-Djdk.tls.ephemeralDHKeySize=2048

# This mitigates a DDoS vector.
server.jvm.additional=-Djdk.tls.rejectClientInitiatedRenegotiation=true

# Enable remote debugging
#server.jvm.additional=-agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005

# This filter prevents deserialization of arbitrary objects via java object serialization, addressing potential vulnerabilities.
# By default this filter whitelists all neo4j classes, as well as classes from the hazelcast library and the java standard library.
# These defaults should only be modified by expert users!
# For more details (including filter syntax) see: https://openjdk.java.net/jeps/290
#server.jvm.additional=-Djdk.serialFilter=java.**;org.neo4j.**;com.neo4j.**;com.hazelcast.**;net.sf.ehcache.Element;com.sun.proxy.*;org.openjdk.jmh.**;!*

# Increase the default flight recorder stack sampling depth from 64 to 256, to avoid truncating frames when profiling.
server.jvm.additional=-XX:FlightRecorderOptions=stackdepth=256

# Allow profilers to sample between safepoints. Without this, sampling profilers may produce less accurate results.
server.jvm.additional=-XX:+UnlockDiagnosticVMOptions
server.jvm.additional=-XX:+DebugNonSafepoints

# Open modules for neo4j to allow internal access
server.jvm.additional=--add-opens=java.base/java.nio=ALL-UNNAMED
server.jvm.additional=--add-opens=java.base/java.io=ALL-UNNAMED
server.jvm.additional=--add-opens=java.base/sun.nio.ch=ALL-UNNAMED

# Enable native memory access
server.jvm.additional=--enable-native-access=ALL-UNNAMED

# Enable access to JDK vector API
# server.jvm.additional=--add-modules=jdk.incubator.vector

# Disable logging JMX endpoint.
server.jvm.additional=-Dlog4j2.disable.jmx=true

# Increasing the JSON log string maximum length
server.jvm.additional=-Dlog4j.layout.jsonTemplate.maxStringLength=32768

# Limit JVM metaspace and code cache to allow garbage collection. Used by cypher for code generation and may grow indefinitely unless constrained.
# Useful for memory constrained environments
#server.jvm.additional=-XX:MaxMetaspaceSize=1024m
#server.jvm.additional=-XX:ReservedCodeCacheSize=512m

# Allow big methods to be JIT compiled.
# Useful for big queries and big expressions where cypher code generation can create large methods.
#server.jvm.additional=-XX:-DontCompileHugeMethods

#********************************************************************
# Wrapper Windows NT/2000/XP Service Properties
#********************************************************************
# WARNING - Do not modify any of these properties when an application
#  using this configuration file has been installed as a service.
#  Please uninstall the service before modifying this section.  The
#  service can then be reinstalled.

# Name of the service
server.windows_service_name=neo4j
```

## Step 4: Create Neo4j User and Directories

```bash
# Create neo4j user (if not created by package)
sudo useradd -r -s /bin/false neo4j || true

# Create necessary directories
sudo mkdir -p /var/lib/neo4j/{data,logs,plugins,import,certificates}
sudo mkdir -p /var/log/neo4j

# Set ownership
sudo chown -R neo4j:neo4j /var/lib/neo4j
sudo chown -R neo4j:neo4j /var/log/neo4j
sudo chown -R neo4j:neo4j /etc/neo4j

# Set permissions
sudo chmod 755 /var/lib/neo4j/import
```

## Step 5: Install APOC and GDS Plugins

**For Neo4j Community Edition (installed via apt)** - plugins need to be downloaded manually:

**IMPORTANT - Version Compatibility:**
- Neo4j 5.26.x → GDS 2.13.x (we use 2.13.4)
- Neo4j 5.26.x → APOC 5.26.x (we use 5.26.0)
- Check [Neo4j GDS Compatibility Matrix](https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/) for latest versions

```bash
# Navigate to plugins directory
cd /var/lib/neo4j/plugins

# Download APOC plugin for Neo4j 5.26 (WORKING URLS)
sudo wget https://github.com/neo4j/apoc/releases/download/5.26.0/apoc-5.26.0-core.jar

# Download Graph Data Science (GDS) plugin for Neo4j 5.26 (COMPATIBLE VERSION)
sudo wget https://github.com/neo4j/graph-data-science/releases/download/2.13.4/neo4j-graph-data-science-2.13.4.jar

# Set ownership
sudo chown neo4j:neo4j *.jar

# Enable plugins in configuration (add to neo4j.conf)
echo "" | sudo tee -a /etc/neo4j/neo4j.conf
echo "# Enable APOC and GDS procedures" | sudo tee -a /etc/neo4j/neo4j.conf
echo "dbms.security.procedures.unrestricted=apoc.*,gds.*" | sudo tee -a /etc/neo4j/neo4j.conf
echo "dbms.security.procedures.allowlist=apoc.*,gds.*" | sudo tee -a /etc/neo4j/neo4j.conf

# Restart Neo4j to load the plugins
sudo systemctl restart neo4j

# Verify plugins are loaded
sudo systemctl status neo4j
```

**Verify Plugin Installation:**

```bash
# Test APOC in Neo4j Browser or cypher-shell
cypher-shell -u neo4j -p 12345678 "RETURN apoc.version();"

# Test GDS
cypher-shell -u neo4j -p 12345678 "RETURN gds.version();"

# Test both plugins are loaded
cypher-shell -u neo4j -p 12345678 "CALL dbms.procedures() YIELD name WHERE name STARTS WITH 'apoc' OR name STARTS WITH 'gds' RETURN count(name) as plugin_procedures;"
```

**Elasticsearch Integration Status**

```bash
# IMPORTANT: No official Elasticsearch integration exists for Neo4j 5.x
# 
# Available plugins only support Neo4j 3.x:
# - neo4j-contrib/neo4j-elasticsearch (max: Neo4j 3.5.6)
# - GraphAware plugins (abandoned for Neo4j 5.x)
#
# Alternative approaches:
# 1. Custom integration via APOC + REST APIs
# 2. Use Kafka to stream data: Neo4j → Kafka → Elasticsearch  
# 3. Keep systems separate (recommended)
#
# Your Elasticsearch cluster (192.168.1.184:9200) works independently
```

## Step 6: Start and Enable Neo4j

```bash
# Start Neo4j service
sudo systemctl start neo4j

# Enable auto-start
sudo systemctl enable neo4j

# Check status
sudo systemctl status neo4j

# Check logs
sudo tail -f /var/log/neo4j/neo4j.log
```

## Step 7: Initial Setup and Security

```bash
# Set initial password using cypher-shell
sudo -u neo4j /usr/bin/cypher-shell -u neo4j -p neo4j

# In cypher-shell, change the default password
ALTER CURRENT USER SET PASSWORD FROM 'neo4j' TO 'your-secure-password';
:exit
```

## Step 8: Firewall Configuration

```bash
# Open required ports
sudo ufw allow 7474/tcp   # HTTP interface
sudo ufw allow 7687/tcp   # Bolt protocol
sudo ufw allow 7473/tcp   # HTTPS (if enabled)

# For clustering (optional)
# sudo ufw allow 5000/tcp   # Discovery
# sudo ufw allow 6000/tcp   # Transaction
# sudo ufw allow 7000/tcp   # Raft

sudo ufw reload
```

## Step 9: Testing the Installation

### Access Neo4j Browser:
Open your web browser and go to: http://192.168.1.187:7474

### Test with Cypher queries:
```cypher
// Create sample nodes
CREATE (p1:Person {name: 'Alice', age: 30})
CREATE (p2:Person {name: 'Bob', age: 25})
CREATE (p3:Person {name: 'Charlie', age: 35})

// Create relationships
MATCH (a:Person {name: 'Alice'}), (b:Person {name: 'Bob'})
CREATE (a)-[:KNOWS]->(b)

MATCH (a:Person {name: 'Bob'}), (c:Person {name: 'Charlie'})
CREATE (a)-[:KNOWS]->(c)

// Query the graph
MATCH (p:Person)-[:KNOWS]->(friend)
RETURN p.name, friend.name

// Delete test data
MATCH (n:Person) DETACH DELETE n
```

## Step 10: Integration with Data Engineering Stack

### Kafka to Neo4j Streaming:
```python
# Example Python script for Kafka to Neo4j
from kafka import KafkaConsumer
from neo4j import GraphDatabase
import json

class Neo4jKafkaConsumer:
    def __init__(self, neo4j_uri, neo4j_user, neo4j_password):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
    def consume_events(self):
        consumer = KafkaConsumer(
            'user-interactions',
            bootstrap_servers=['192.168.1.184:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        for message in consumer:
            event = message.value
            self.process_event(event)
    
    def process_event(self, event):
        with self.driver.session() as session:
            if event['type'] == 'user_action':
                session.write_transaction(self.create_user_action, event)
    
    def create_user_action(self, tx, event):
        query = """
        MERGE (u:User {id: $user_id})
        MERGE (p:Product {id: $product_id})
        CREATE (u)-[:VIEWED {timestamp: $timestamp}]->(p)
        """
        tx.run(query, user_id=event['user_id'], 
               product_id=event['product_id'], 
               timestamp=event['timestamp'])
```

### Spark to Neo4j Integration:
```scala
// Spark DataFrame to Neo4j
import org.neo4j.spark._

// Read data from your data lake
val df = spark.read.format("delta").load("/path/to/your/table")

// Write to Neo4j
df.write
  .format("org.neo4j.spark.DataSource")
  .mode("Overwrite")
  .option("url", "neo4j://192.168.1.187:7687")
  .option("authentication.basic.username", "neo4j")
  .option("authentication.basic.password", "password")
  .option("labels", ":Person")
  .option("node.keys", "id")
  .save()
```

### PostgreSQL to Neo4j ETL:
```python
# ETL script for PostgreSQL to Neo4j
import psycopg2
from neo4j import GraphDatabase

def sync_postgres_to_neo4j():
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(
        host="192.168.1.184",
        database="analytics_db",
        user="dataeng",
        password="password"
    )
    
    # Connect to Neo4j
    neo4j_driver = GraphDatabase.driver(
        "neo4j://192.168.1.187:7687",
        auth=("neo4j", "password")
    )
    
    with pg_conn.cursor() as pg_cursor:
        # Extract customer relationships
        pg_cursor.execute("""
            SELECT c1.customer_id, c1.name, c2.customer_id, c2.name, r.relationship_type
            FROM customers c1
            JOIN relationships r ON c1.customer_id = r.customer1_id
            JOIN customers c2 ON r.customer2_id = c2.customer_id
        """)
        
        relationships = pg_cursor.fetchall()
        
        # Load into Neo4j
        with neo4j_driver.session() as session:
            for rel in relationships:
                session.write_transaction(create_relationship, rel)

def create_relationship(tx, relationship):
    query = """
    MERGE (c1:Customer {id: $id1, name: $name1})
    MERGE (c2:Customer {id: $id2, name: $name2})
    MERGE (c1)-[r:RELATED {type: $rel_type}]->(c2)
    """
    tx.run(query, 
           id1=relationship[0], name1=relationship[1],
           id2=relationship[2], name2=relationship[3],
           rel_type=relationship[4])
```

## Step 11: Advanced Use Cases

### Social Network Analysis:
```cypher
// Find influential users (high degree centrality)
MATCH (u:User)
WITH u, size((u)--()) as degree
ORDER BY degree DESC
LIMIT 10
RETURN u.name, degree

// Find communities using Label Propagation
CALL gds.labelPropagation.stream('myGraph')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name AS name, communityId
ORDER BY communityId
```

### Fraud Detection Patterns:
```cypher
// Find suspicious transaction patterns
MATCH path = (a:Account)-[:TRANSFER*2..4]->(b:Account)
WHERE a.id <> b.id
AND all(r in relationships(path) WHERE r.amount > 10000)
AND all(r in relationships(path) WHERE r.timestamp > datetime() - duration('PT1H'))
RETURN path, length(path) as hops, 
       reduce(total = 0, r in relationships(path) | total + r.amount) as total_amount
```

### Recommendation Engine:
```cypher
// Collaborative filtering recommendations
MATCH (user:User {id: $userId})-[:PURCHASED]->(product:Product)
MATCH (product)<-[:PURCHASED]-(otherUser:User)-[:PURCHASED]->(recommendation:Product)
WHERE NOT (user)-[:PURCHASED]->(recommendation)
WITH recommendation, count(*) as score
ORDER BY score DESC
LIMIT 10
RETURN recommendation.name, score
```

## Step 12: Performance Optimization

### Index Creation:
```cypher
// Create indexes for better performance
CREATE INDEX user_id_index FOR (u:User) ON (u.id);
CREATE INDEX product_id_index FOR (p:Product) ON (p.id);
CREATE INDEX transaction_timestamp_index FOR ()-[t:TRANSACTION]-() ON (t.timestamp);

// Create composite indexes
CREATE INDEX user_age_location FOR (u:User) ON (u.age, u.location);

// Full-text search indexes
CREATE FULLTEXT INDEX product_search FOR (p:Product) ON EACH [p.name, p.description];
```

### Memory Configuration Tuning:
```bash
# Edit configuration for production workloads
sudo nano /etc/neo4j/neo4j.conf

# Increase heap size for large datasets
server.memory.heap.initial_size=8G
server.memory.heap.max_size=12G

# Increase page cache for better I/O
server.memory.pagecache.size=8G

# Enable parallel GC
server.jvm.additional=-XX:+UseG1GC
server.jvm.additional=-XX:+UnlockExperimentalVMOptions
server.jvm.additional=-XX:+UseTransparentHugePages
```

## Step 13: Monitoring and Maintenance

### Query Performance Monitoring:
```bash
# Enable query logging in neo4j.conf (uncomment these lines)
# Note: Query logging is not enabled by default in Neo4j 5.x
# You need to configure logging in server-logs.xml or user-logs.xml

# Monitor slow queries in logs
sudo tail -f /var/log/neo4j/debug.log | grep "SLOW"

# Check database statistics
```

```cypher
// View database statistics
CALL dbms.queryJmx("*:*")
YIELD name, attributes
WHERE name CONTAINS "Primitive"
RETURN name, attributes

// Check transaction statistics  
CALL dbms.listTransactions()
YIELD transactionId, currentQuery, status, startTime
RETURN transactionId, currentQuery, status, startTime
```

### Health Checks:
```python
# Health check script
from neo4j import GraphDatabase

def check_neo4j_health():
    driver = GraphDatabase.driver("neo4j://192.168.1.187:7687", 
                                  auth=("neo4j", "password"))
    
    with driver.session() as session:
        # Check connectivity
        result = session.run("RETURN 1 as test")
        print(f"Connection test: {result.single()['test']}")
        
        # Check database size
        result = session.run("""
            CALL apoc.meta.stats() YIELD nodeCount, relCount, labelCount
            RETURN nodeCount, relCount, labelCount
        """)
        stats = result.single()
        print(f"Nodes: {stats['nodeCount']}, Relationships: {stats['relCount']}")
        
        # Check memory usage
        result = session.run("CALL dbms.queryJmx('java.lang:type=Memory')")
        for record in result:
            memory_info = record['attributes']
            heap_used = memory_info['HeapMemoryUsage']['used']
            heap_max = memory_info['HeapMemoryUsage']['max']
            print(f"Heap Usage: {heap_used}/{heap_max} ({heap_used/heap_max*100:.1f}%)")

if __name__ == "__main__":
    check_neo4j_health()
```

### Backup Strategy:
```bash
# Create backup script
sudo nano /opt/neo4j-backup.sh

#!/bin/bash
BACKUP_DIR="/opt/neo4j-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Stop Neo4j for consistent backup
sudo systemctl stop neo4j

# Copy database files
sudo tar -czf $BACKUP_DIR/neo4j_backup_$DATE.tar.gz /var/lib/neo4j/data/

# Start Neo4j
sudo systemctl start neo4j

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/neo4j_backup_$DATE.tar.gz"

# Make executable and add to cron
sudo chmod +x /opt/neo4j-backup.sh

# Add to crontab for daily backups at 2 AM
# 0 2 * * * /opt/neo4j-backup.sh
```

## Step 14: Integration with ML Pipeline (GPU Node)

### Graph Feature Engineering:
```python
# Extract graph features for ML models
from neo4j import GraphDatabase
import pandas as pd
import numpy as np

class GraphFeatureExtractor:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def extract_user_features(self, user_ids):
        with self.driver.session() as session:
            query = """
            UNWIND $user_ids as user_id
            MATCH (u:User {id: user_id})
            OPTIONAL MATCH (u)-[:FRIEND]-(friends)
            OPTIONAL MATCH (u)-[:PURCHASED]->(products)
            WITH u, count(DISTINCT friends) as friend_count, 
                 count(DISTINCT products) as purchase_count
            RETURN u.id as user_id, u.age, u.location,
                   friend_count, purchase_count,
                   u.account_age_days
            """
            
            result = session.run(query, user_ids=user_ids)
            return pd.DataFrame([dict(record) for record in result])
    
    def extract_network_features(self, user_ids):
        with self.driver.session() as session:
            # Calculate centrality measures
            session.run("""
                CALL gds.graph.project('userNetwork', 'User', 'FRIEND')
            """)
            
            # PageRank
            result = session.run("""
                CALL gds.pageRank.stream('userNetwork')
                YIELD nodeId, score
                WHERE gds.util.asNode(nodeId).id IN $user_ids
                RETURN gds.util.asNode(nodeId).id as user_id, score as pagerank
            """, user_ids=user_ids)
            
            pagerank_df = pd.DataFrame([dict(record) for record in result])
            
            # Cleanup
            session.run("CALL gds.graph.drop('userNetwork')")
            
            return pagerank_df

# Usage example
extractor = GraphFeatureExtractor(
    "neo4j://192.168.1.187:7687", 
    "neo4j", 
    "password"
)

user_features = extractor.extract_user_features([1, 2, 3, 4, 5])
network_features = extractor.extract_network_features([1, 2, 3, 4, 5])

# Merge features for ML model
features = user_features.merge(network_features, on='user_id')
```

## Troubleshooting

### Common Issues:
1. **Connection refused**: Check if Neo4j is running and firewall allows connections
2. **Out of memory errors**: Increase heap size in neo4j.conf
3. **Slow queries**: Add appropriate indexes and analyze query plans
4. **Import failures**: Check file permissions in import directory
5. **HTTP interface not accessible**: Check that HTTP connector is correctly configured with port 7474 (not 7687)
6. **GDS Plugin ClassNotFoundException**: Wrong GDS version for your Neo4j version

### GDS Plugin Compatibility Error:
```bash
# Error: ClassNotFoundException: org.neo4j.internal.batchimport.Configuration
# Cause: Incompatible GDS version

# Fix - Remove incompatible version and install correct one:
cd /var/lib/neo4j/plugins
sudo rm neo4j-graph-data-science-*.jar
sudo wget https://github.com/neo4j/graph-data-science/releases/download/2.13.4/neo4j-graph-data-science-2.13.4.jar
sudo chown neo4j:neo4j *.jar
sudo systemctl restart neo4j

# COMPATIBILITY MATRIX (Official Neo4j):
# Neo4j 5.26 → GDS 2.13.x (Use 2.13.4)
```

### Critical Configuration Fix Required:
**IMPORTANT**: Your current config has an ERROR - HTTP port is set to 7687 instead of 7474!

```bash
# Check your current HTTP configuration
grep "server.http.listen_address" /etc/neo4j/neo4j.conf
# Currently shows: server.http.listen_address=0.0.0.0:7687 ← THIS IS WRONG!

# FIX IT - Change HTTP port from 7687 to 7474:
sudo sed -i 's/server.http.listen_address=0.0.0.0:7687/server.http.listen_address=0.0.0.0:7474/' /etc/neo4j/neo4j.conf

# Verify the fix
grep "server.http.listen_address" /etc/neo4j/neo4j.conf
# Should now show: server.http.listen_address=0.0.0.0:7474 ← CORRECT!

# Restart Neo4j to apply changes
sudo systemctl restart neo4j

# Check status
sudo systemctl status neo4j
```

**Without this fix, your Neo4j Browser will NOT be accessible!**

### Performance Troubleshooting:
```cypher
// Analyze query performance
PROFILE MATCH (u:User)-[:KNOWS*2]->(friend)
RETURN u.name, collect(friend.name) as friends

// Check index usage
SHOW INDEXES

// Monitor active transactions
CALL dbms.listTransactions()
```

### Log Analysis:
```bash
# Monitor Neo4j logs
sudo tail -f /var/log/neo4j/neo4j.log

# Check query logs
sudo tail -f /var/log/neo4j/query.log

# Monitor system resources
htop
iotop -ao
```

This Neo4j setup provides a robust graph database foundation for advanced analytics, fraud detection, social network analysis, and recommendation systems, fully integrated with your data engineering ecosystem.
