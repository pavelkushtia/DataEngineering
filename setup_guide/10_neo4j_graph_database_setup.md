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
#*****************************************************************
# Network connector configuration
#*****************************************************************

# Bolt connector
server.bolt.enabled=true
server.bolt.listen_address=0.0.0.0:7687
server.bolt.advertised_address=192.168.1.187:7687

# HTTP connector
server.http.enabled=true
server.http.listen_address=0.0.0.0:7474
server.http.advertised_address=192.168.1.187:7474

# HTTPS connector (optional)
server.https.enabled=false
server.https.listen_address=0.0.0.0:7473

#*****************************************************************
# Memory settings
#*****************************************************************

# Java Heap Size
server.memory.heap.initial_size=2G
server.memory.heap.max_size=4G

# Page cache size (should be ~50% of available RAM)
server.memory.pagecache.size=2G

#*****************************************************************
# Database configuration
#*****************************************************************

# Default database
server.default_database=neo4j

# Enable multi-database
server.databases.default_to_read_only=false

#*****************************************************************
# Security configuration
#*****************************************************************

# Authentication and authorization
dbms.security.auth_enabled=true

# Initial password (change after first login)
dbms.security.auth_minimum_password_length=8

#*****************************************************************
# Logging configuration
#*****************************************************************

# Query logging
dbms.logs.query.enabled=true
dbms.logs.query.threshold=1000ms
dbms.logs.query.parameter_logging_enabled=true

# Debug logging
server.logs.debug.level=INFO

#*****************************************************************
# Performance tuning
#*****************************************************************

# Transaction timeout
dbms.transaction.timeout=60s

# Lock acquisition timeout
dbms.lock.acquisition.timeout=60s

# Maximum number of concurrent transactions
dbms.transaction.concurrent.maximum=1000

#*****************************************************************
# Clustering (for future expansion)
#*****************************************************************

# Uncomment for clustering setup
# causal_clustering.minimum_core_cluster_size_at_formation=3
# causal_clustering.initial_discovery_members=192.168.1.187:5000,192.168.1.190:5000
# causal_clustering.discovery_listen_address=0.0.0.0:5000
# causal_clustering.raft_listen_address=0.0.0.0:7000
# causal_clustering.transaction_listen_address=0.0.0.0:6000

#*****************************************************************
# Import configuration
#*****************************************************************

# Allow file import from anywhere (use cautiously)
dbms.security.allow_csv_import_from_file_urls=true

# Import directory
server.directories.import=/var/lib/neo4j/import

#*****************************************************************
# APOC configuration
#*****************************************************************

# Enable APOC procedures
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.allowlist=apoc.*
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

## Step 5: Install APOC and Additional Plugins

```bash
# Navigate to plugins directory
cd /var/lib/neo4j/plugins

# Download APOC plugin (required for most advanced operations)
sudo wget https://github.com/neo4j/apoc/releases/download/5.15.0/apoc-5.15.0-extended.jar

# Download Graph Data Science (GDS) plugin
sudo wget https://neo4j.com/artifact.php?name=neo4j-graph-data-science-2.5.0.jar

# Download GraphQL plugin
sudo wget https://github.com/neo4j-graphql/neo4j-graphql-java/releases/download/1.5.0/neo4j-graphql-1.5.0.jar

# Download Elasticsearch integration
sudo wget https://github.com/neo4j-contrib/neo4j-elasticsearch/releases/download/4.4.0.2/elasticsearch-6.5.4.jar

# Set ownership
sudo chown neo4j:neo4j *.jar

# Restart Neo4j to load the plugins
sudo systemctl restart neo4j
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
```cypher
// Enable query logging in neo4j.conf
dbms.logs.query.enabled=true
dbms.logs.query.threshold=1000ms

// View slow queries
CALL dbms.queryJmx("org.neo4j:instance=kernel#0,name=Query*")
YIELD attributes
RETURN attributes.question, attributes.QueryExecutionLatency
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
