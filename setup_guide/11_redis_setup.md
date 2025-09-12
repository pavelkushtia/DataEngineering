# Redis Setup Guide

## Overview
Redis will be set up on cpu-node1 as a high-performance in-memory data store, cache, and message broker. It will serve as a caching layer, real-time analytics store, and feature serving system for ML applications.

## What is Redis?
Redis (Remote Dictionary Server) is an open-source, in-memory data structure store used as a database, cache, message broker, and streaming engine. It supports various data structures such as strings, hashes, lists, sets, sorted sets with range queries, bitmaps, hyperloglogs, geospatial indexes, and streams.

## Machine Configuration
- **Primary Node**: cpu-node1 (192.168.1.184)
- **Replica Node**: cpu-node2 (192.168.1.187) - for high availability
- **Integration**: Works with all existing components

## Prerequisites
- Ubuntu/Debian-based Linux distribution
- At least 2GB RAM (4GB+ recommended for production)
- At least 5GB free disk space
- Network connectivity between nodes

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   gpu-node          │
│  - Redis Master     │────│  - Redis Replica    │    │  - Redis Client     │
│  - PostgreSQL       │    │  - Neo4j            │    │  - ML Feature Store │
│  - Kafka Broker     │    │  - Other Services   │    │  - Model Serving    │
│  192.168.1.184      │    │  192.168.1.187      │    │  192.168.1.79       │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## Step 1: Redis Installation (cpu-node1)

```bash
# Update package repository
sudo apt update

# Install Redis
sudo apt install -y redis-server redis-tools

# Verify installation
redis-server --version
redis-cli --version
```

## Step 2: Redis Configuration

### Complete Redis Configuration File

**Important:** Before modifying your Redis configuration, always create a backup:

```bash
# Create backup of current configuration
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup.$(date +%Y%m%d_%H%M%S)

# Edit the configuration file
sudo nano /etc/redis/redis.conf
```

### Option 1: Use Current System Configuration (Recommended)

Your current Redis installation already has a complete and properly configured `redis.conf` file. You can view the current configuration:

```bash
# View current configuration
sudo cat /etc/redis/redis.conf | head -50

# See the complete configuration structure
sudo less /etc/redis/redis.conf
```

### Option 2: Key Configuration Settings to Customize

Since your current configuration is already comprehensive (Redis 7.0.15), you only need to modify specific sections for your setup. Here are the key settings to customize:

```bash
# Edit specific settings in the existing config
sudo nano /etc/redis/redis.conf
```

**Critical settings to modify:**

1. **Network Configuration (around line 90-120):**
```conf
# CUSTOMIZE: Change to 0.0.0.0 to accept connections from any IP
bind 0.0.0.0

# CUSTOMIZE: Set to 'no' if binding to 0.0.0.0  
protected-mode no

# Port configuration
port 6379
```

2. **Security Configuration (around line 790-810):**
```conf
# CUSTOMIZE: Set a strong password for Redis authentication
requirepass your-strong-redis-password-here
```

3. **Memory Management (around line 1020-1040):**
```conf
# CUSTOMIZE: Set based on available system RAM (leave some for OS)
# Uncomment and set appropriate value based on your RAM
maxmemory 2gb

# Memory eviction policy
maxmemory-policy allkeys-lru
```

4. **Persistence Configuration (around line 400-450):**
```conf
# CUSTOMIZE: Adjust save points based on your needs
save 3600 1 300 100 60 10000

# Enable AOF persistence for better durability
appendonly yes
appendfsync everysec
```

5. **For Replica Setup (uncomment when setting up replica):**
```conf
# CUSTOMIZE for replica setup: 
# replicaof 192.168.1.184 6379
# masterauth your-redis-password
```

### Configuration Template for Direct Replacement

If you prefer to replace the entire configuration file, here's a production-ready template based on Redis 7.0+ defaults:

```bash
# Download Redis 7.0+ default configuration
wget https://raw.githubusercontent.com/redis/redis/7.0/redis.conf -O /tmp/redis.conf.template

# Or create from your current config
sudo cp /etc/redis/redis.conf /tmp/redis-template.conf

# Customize the template, then replace
sudo cp /tmp/redis-template.conf /etc/redis/redis.conf
```

### Quick Configuration Commands

For quick configuration without manual editing:

```bash
# 1. Set Redis to accept external connections
sudo sed -i 's/^bind 127.0.0.1 -::1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf

# 2. Set password (replace 'your-password' with actual password)
sudo sed -i 's/^# requirepass foobared/requirepass your-password/' /etc/redis/redis.conf

# 3. Set memory limit (adjust 2gb as needed)
echo "maxmemory 2gb" | sudo tee -a /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" | sudo tee -a /etc/redis/redis.conf

# 4. Enable AOF persistence
sudo sed -i 's/^appendonly no/appendonly yes/' /etc/redis/redis.conf

# 5. Apply changes
sudo systemctl restart redis-server
```

### Verify Configuration

After making changes, verify the configuration is correct:

```bash
# Test configuration syntax
sudo redis-server /etc/redis/redis.conf --test-config

# Check if Redis starts successfully
sudo systemctl restart redis-server
sudo systemctl status redis-server

# Test connection
redis-cli -h 192.168.1.184 -a your-password ping

# View current settings
redis-cli -h 192.168.1.184 -a your-password CONFIG GET "*"
```

## Step 3: System Configuration

### Configure system settings for Redis:
```bash
# Increase system limits
sudo nano /etc/security/limits.conf
```

Add these lines:
```
redis soft nofile 65535
redis hard nofile 65535
redis soft nproc 65535
redis hard nproc 65535
```

### Configure kernel parameters:
```bash
sudo nano /etc/sysctl.conf
```

Add these settings:
```
# Redis optimization
vm.overcommit_memory = 1
net.core.somaxconn = 65535

# Disable transparent huge pages
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag
```

Apply the changes:
```bash
sudo sysctl -p
```

### Make THP disable persistent:
```bash
sudo nano /etc/rc.local
```

Add before `exit 0`:
```bash
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag
```

## Step 4: Create Redis Directories and Permissions

```bash
# Create necessary directories
sudo mkdir -p /var/lib/redis
sudo mkdir -p /var/log/redis
sudo mkdir -p /var/run/redis

# Set ownership
sudo chown redis:redis /var/lib/redis
sudo chown redis:redis /var/log/redis
sudo chown redis:redis /var/run/redis

# Set permissions
sudo chmod 755 /var/lib/redis
sudo chmod 755 /var/log/redis
sudo chmod 755 /var/run/redis
```

## Step 5: Start and Enable Redis

```bash
# Start Redis service
sudo systemctl start redis-server

# Enable auto-start
sudo systemctl enable redis-server

# Check status
sudo systemctl status redis-server

# Test Redis connection
redis-cli -h 192.168.1.184 -a your-redis-password ping
```

## Step 6: Redis Replica Setup (cpu-node2)

### Install Redis on cpu-node2:
```bash
# On cpu-node2
sudo apt update
sudo apt install -y redis-server redis-tools
```

### Configure Redis replica:
```bash
sudo nano /etc/redis/redis.conf
```

Add/modify these settings:
```conf
# Replica configuration
replicaof 192.168.1.184 6379
masterauth your-redis-password
requirepass your-redis-password

# Same network and general settings as master
bind 0.0.0.0
protected-mode no
port 6379

# Different data directory
dir /var/lib/redis
```

Start the replica:
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

## Step 7: Firewall Configuration

```bash
# On both nodes, open Redis port
sudo ufw allow 6379/tcp
sudo ufw reload
```

## Step 8: Redis Monitoring Setup

### Create monitoring script:
```python
# Create monitoring script
sudo nano /opt/redis-monitor.py
```

```python
#!/usr/bin/env python3

import redis
import json
import time
from datetime import datetime

class RedisMonitor:
    def __init__(self, host='192.168.1.184', port=6379, password='your-redis-password'):
        self.r = redis.Redis(host=host, port=port, password=password, decode_responses=True)
        
    def get_info(self):
        """Get comprehensive Redis info"""
        info = self.r.info()
        return {
            'server': {
                'redis_version': info.get('redis_version'),
                'uptime_in_seconds': info.get('uptime_in_seconds'),
                'connected_clients': info.get('connected_clients'),
                'used_memory_human': info.get('used_memory_human'),
                'used_memory_peak_human': info.get('used_memory_peak_human')
            },
            'stats': {
                'total_connections_received': info.get('total_connections_received'),
                'total_commands_processed': info.get('total_commands_processed'),
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec'),
                'keyspace_hits': info.get('keyspace_hits'),
                'keyspace_misses': info.get('keyspace_misses'),
                'expired_keys': info.get('expired_keys')
            },
            'replication': {
                'role': info.get('role'),
                'connected_slaves': info.get('connected_slaves', 0)
            },
            'persistence': {
                'rdb_last_save_time': info.get('rdb_last_save_time'),
                'rdb_changes_since_last_save': info.get('rdb_changes_since_last_save'),
                'aof_enabled': info.get('aof_enabled')
            }
        }
    
    def get_slow_log(self, count=10):
        """Get slow query log"""
        return self.r.slowlog_get(count)
    
    def get_config(self, pattern='*'):
        """Get Redis configuration"""
        return self.r.config_get(pattern)
    
    def monitor_continuously(self, interval=30):
        """Continuously monitor Redis"""
        while True:
            try:
                info = self.get_info()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                print(f"\n=== Redis Monitor - {timestamp} ===")
                print(f"Memory Usage: {info['server']['used_memory_human']}")
                print(f"Connected Clients: {info['server']['connected_clients']}")
                print(f"Operations/sec: {info['stats']['instantaneous_ops_per_sec']}")
                print(f"Hit Rate: {self.calculate_hit_rate(info['stats']):.2f}%")
                print(f"Role: {info['replication']['role']}")
                
                if info['replication']['role'] == 'master':
                    print(f"Connected Replicas: {info['replication']['connected_slaves']}")
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval)
    
    def calculate_hit_rate(self, stats):
        """Calculate cache hit rate"""
        hits = stats.get('keyspace_hits', 0)
        misses = stats.get('keyspace_misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0

if __name__ == "__main__":
    monitor = RedisMonitor()
    monitor.monitor_continuously()
```

Make it executable:
```bash
sudo chmod +x /opt/redis-monitor.py
```

## Step 9: Integration Examples

### Redis with Python (Feature Store):
```python
# Feature store implementation
import redis
import json
import pandas as pd
from datetime import datetime, timedelta

class RedisFeatureStore:
    def __init__(self, host='192.168.1.184', port=6379, password='your-redis-password'):
        self.r = redis.Redis(host=host, port=port, password=password, decode_responses=True)
    
    def store_features(self, entity_id, features, ttl=3600):
        """Store features for an entity with TTL"""
        key = f"features:{entity_id}"
        feature_data = {
            'features': features,
            'timestamp': datetime.now().isoformat(),
            'ttl': ttl
        }
        
        self.r.setex(key, ttl, json.dumps(feature_data))
    
    def get_features(self, entity_id):
        """Retrieve features for an entity"""
        key = f"features:{entity_id}"
        data = self.r.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    def batch_store_features(self, feature_batch):
        """Store multiple features efficiently"""
        pipe = self.r.pipeline()
        
        for entity_id, features, ttl in feature_batch:
            key = f"features:{entity_id}"
            feature_data = {
                'features': features,
                'timestamp': datetime.now().isoformat(),
                'ttl': ttl
            }
            pipe.setex(key, ttl, json.dumps(feature_data))
        
        pipe.execute()
    
    def batch_get_features(self, entity_ids):
        """Retrieve multiple features efficiently"""
        pipe = self.r.pipeline()
        
        for entity_id in entity_ids:
            key = f"features:{entity_id}"
            pipe.get(key)
        
        results = pipe.execute()
        
        feature_dict = {}
        for i, result in enumerate(results):
            if result:
                feature_dict[entity_ids[i]] = json.loads(result)
        
        return feature_dict
    
    def store_model_predictions(self, model_name, entity_id, predictions, ttl=1800):
        """Store model predictions"""
        key = f"predictions:{model_name}:{entity_id}"
        pred_data = {
            'predictions': predictions,
            'model_name': model_name,
            'timestamp': datetime.now().isoformat()
        }
        
        self.r.setex(key, ttl, json.dumps(pred_data))
    
    def get_model_predictions(self, model_name, entity_id):
        """Get model predictions"""
        key = f"predictions:{model_name}:{entity_id}"
        data = self.r.get(key)
        
        if data:
            return json.loads(data)
        return None

# Usage example
fs = RedisFeatureStore()

# Store user features
user_features = {
    'age': 30,
    'income': 75000,
    'credit_score': 750,
    'purchase_frequency': 2.5,
    'avg_order_value': 125.50
}

fs.store_features('user_12345', user_features, ttl=3600)

# Retrieve features
retrieved = fs.get_features('user_12345')
print(f"Retrieved features: {retrieved}")
```

### Redis with Spark (Caching):
```scala
// Spark with Redis integration
import com.redislabs.provider.redis._
import org.apache.spark.sql.SparkSession

val spark = SparkSession.builder()
  .appName("Redis-Spark Integration")
  .config("spark.redis.host", "192.168.1.184")
  .config("spark.redis.port", "6379")
  .config("spark.redis.auth", "your-redis-password")
  .getOrCreate()

// Cache DataFrame to Redis
val df = spark.read
  .format("jdbc")
  .option("url", "jdbc:postgresql://192.168.1.184:5432/analytics_db")
  .option("dbtable", "user_profiles")
  .option("user", "dataeng")
  .option("password", "password")
  .load()

// Write to Redis
df.write
  .format("org.apache.spark.sql.redis")
  .option("table", "user_profiles")
  .option("key.column", "user_id")
  .mode("overwrite")
  .save()

// Read from Redis
val cachedDF = spark.read
  .format("org.apache.spark.sql.redis")
  .option("table", "user_profiles")
  .option("key.column", "user_id")
  .load()

cachedDF.show()
```

### Redis Stream Processing with Kafka:
```python
# Redis as a stream processor buffer
import redis
import json
from kafka import KafkaConsumer
import threading
import time

class RedisStreamProcessor:
    def __init__(self, redis_host='192.168.1.184', redis_port=6379, 
                 redis_password='your-redis-password'):
        self.r = redis.Redis(host=redis_host, port=redis_port, 
                           password=redis_password, decode_responses=True)
    
    def consume_kafka_to_redis_stream(self):
        """Consume from Kafka and write to Redis Stream"""
        consumer = KafkaConsumer(
            'user-events',
            bootstrap_servers=['192.168.1.184:9092'],
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        
        for message in consumer:
            event = message.value
            
            # Add to Redis Stream
            stream_key = f"events:{event.get('event_type', 'unknown')}"
            self.r.xadd(stream_key, event)
            
            # Also cache latest user activity
            user_id = event.get('user_id')
            if user_id:
                user_key = f"user_activity:{user_id}"
                self.r.setex(user_key, 3600, json.dumps(event))
    
    def process_redis_streams(self):
        """Process Redis streams for real-time analytics"""
        streams = ['events:page_view', 'events:purchase', 'events:click']
        
        while True:
            try:
                # Read from multiple streams
                messages = self.r.xread({stream: '$' for stream in streams}, 
                                      count=100, block=1000)
                
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        self.process_event(stream, msg_id, fields)
                        
            except Exception as e:
                print(f"Stream processing error: {e}")
                time.sleep(5)
    
    def process_event(self, stream, msg_id, fields):
        """Process individual events for real-time metrics"""
        event_type = stream.split(':')[1]
        
        # Increment counters
        self.r.incr(f"counter:daily:{event_type}")
        self.r.incr(f"counter:hourly:{event_type}")
        
        # Update user activity
        user_id = fields.get('user_id')
        if user_id:
            # Add to user activity sorted set (score = timestamp)
            timestamp = time.time()
            self.r.zadd(f"user_activity:{user_id}", {msg_id: timestamp})
            
            # Keep only last 100 activities
            self.r.zremrangebyrank(f"user_activity:{user_id}", 0, -101)
    
    def get_real_time_metrics(self):
        """Get real-time metrics"""
        return {
            'daily_page_views': self.r.get('counter:daily:page_view') or 0,
            'daily_purchases': self.r.get('counter:daily:purchase') or 0,
            'daily_clicks': self.r.get('counter:daily:click') or 0,
            'active_users': self.r.scard('active_users'),
            'total_sessions': self.r.get('counter:daily:session') or 0
        }

# Usage
processor = RedisStreamProcessor()

# Start processing in separate threads
kafka_thread = threading.Thread(target=processor.consume_kafka_to_redis_stream)
stream_thread = threading.Thread(target=processor.process_redis_streams)

kafka_thread.daemon = True
stream_thread.daemon = True

kafka_thread.start()
stream_thread.start()
```

## Step 10: Redis for ML Model Serving

```python
# ML Model serving with Redis
import redis
import pickle
import json
import numpy as np
from sklearn.externals import joblib

class RedisModelServer:
    def __init__(self, redis_host='192.168.1.184', redis_port=6379, 
                 redis_password='your-redis-password'):
        self.r = redis.Redis(host=redis_host, port=redis_port, 
                           password=redis_password)
    
    def store_model(self, model_name, model, metadata=None):
        """Store ML model in Redis"""
        model_data = pickle.dumps(model)
        
        # Store model binary
        self.r.set(f"model:{model_name}:data", model_data)
        
        # Store metadata
        if metadata:
            self.r.set(f"model:{model_name}:metadata", json.dumps(metadata))
        
        # Update model registry
        self.r.sadd("model_registry", model_name)
    
    def load_model(self, model_name):
        """Load ML model from Redis"""
        model_data = self.r.get(f"model:{model_name}:data")
        if model_data:
            return pickle.loads(model_data)
        return None
    
    def predict(self, model_name, features):
        """Make predictions using cached model"""
        model = self.load_model(model_name)
        if model is None:
            raise ValueError(f"Model {model_name} not found")
        
        # Convert features to numpy array if needed
        if isinstance(features, list):
            features = np.array(features).reshape(1, -1)
        
        # Make prediction
        prediction = model.predict(features)
        
        # Cache prediction for a short time
        feature_hash = hash(str(features))
        pred_key = f"prediction:{model_name}:{feature_hash}"
        self.r.setex(pred_key, 300, json.dumps(prediction.tolist()))
        
        return prediction
    
    def batch_predict(self, model_name, batch_features):
        """Batch prediction with caching"""
        model = self.load_model(model_name)
        if model is None:
            raise ValueError(f"Model {model_name} not found")
        
        # Check cache first
        cached_predictions = {}
        uncached_indices = []
        uncached_features = []
        
        for i, features in enumerate(batch_features):
            feature_hash = hash(str(features))
            pred_key = f"prediction:{model_name}:{feature_hash}"
            cached = self.r.get(pred_key)
            
            if cached:
                cached_predictions[i] = json.loads(cached)
            else:
                uncached_indices.append(i)
                uncached_features.append(features)
        
        # Predict uncached features
        if uncached_features:
            uncached_features = np.array(uncached_features)
            predictions = model.predict(uncached_features)
            
            # Cache new predictions
            for i, pred in enumerate(predictions):
                original_idx = uncached_indices[i]
                feature_hash = hash(str(batch_features[original_idx]))
                pred_key = f"prediction:{model_name}:{feature_hash}"
                self.r.setex(pred_key, 300, json.dumps(pred.tolist()))
                cached_predictions[original_idx] = pred
        
        # Combine results
        results = []
        for i in range(len(batch_features)):
            results.append(cached_predictions[i])
        
        return results
    
    def get_model_stats(self, model_name):
        """Get model usage statistics"""
        return {
            'prediction_count': self.r.get(f"stats:{model_name}:predictions") or 0,
            'cache_hits': self.r.get(f"stats:{model_name}:cache_hits") or 0,
            'cache_misses': self.r.get(f"stats:{model_name}:cache_misses") or 0,
            'last_used': self.r.get(f"stats:{model_name}:last_used"),
            'model_size': self.r.memory_usage(f"model:{model_name}:data")
        }

# Usage example
model_server = RedisModelServer()

# Train and store a simple model (example)
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification

X, y = make_classification(n_samples=1000, n_features=10, random_state=42)
model = LogisticRegression()
model.fit(X, y)

# Store model with metadata
metadata = {
    'model_type': 'LogisticRegression',
    'features': ['feature_' + str(i) for i in range(10)],
    'created_at': time.time(),
    'accuracy': 0.95
}

model_server.store_model('user_churn_prediction', model, metadata)

# Make predictions
test_features = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
prediction = model_server.predict('user_churn_prediction', test_features)
print(f"Prediction: {prediction}")
```

## Step 11: Performance Tuning and Optimization

### Memory Optimization:
```bash
# Check memory usage
redis-cli -h 192.168.1.184 -a your-redis-password info memory

# Analyze key sizes
redis-cli -h 192.168.1.184 -a your-redis-password --bigkeys

# Memory usage by data type
redis-cli -h 192.168.1.184 -a your-redis-password memory stats
```

### Performance Benchmarking:
```bash
# Benchmark Redis performance
redis-benchmark -h 192.168.1.184 -p 6379 -a your-redis-password -n 100000 -d 3 -t ping,set,get,incr,lpush,rpush,lpop,rpop,sadd,hset,spop,lrange,mset

# Custom benchmark
redis-benchmark -h 192.168.1.184 -p 6379 -a your-redis-password -n 100000 -r 10000 -d 1000
```

## Step 12: Backup and Recovery

### Backup Script:
```bash
# Create backup script
sudo nano /opt/redis-backup.sh
```

```bash
#!/bin/bash

REDIS_HOST="192.168.1.184"
REDIS_PORT="6379"
REDIS_PASSWORD="your-redis-password"
BACKUP_DIR="/opt/redis-backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Create RDB backup
redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD BGSAVE

# Wait for backup to complete
while [ $(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD LASTSAVE) -eq $(redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD LASTSAVE) ]; do
  sleep 1
done

# Copy RDB file
cp /var/lib/redis/dump.rdb $BACKUP_DIR/dump_$DATE.rdb

# Copy AOF file if enabled
if [ -f /var/lib/redis/appendonly.aof ]; then
    cp /var/lib/redis/appendonly.aof $BACKUP_DIR/appendonly_$DATE.aof
fi

# Compress backups
gzip $BACKUP_DIR/dump_$DATE.rdb
[ -f $BACKUP_DIR/appendonly_$DATE.aof ] && gzip $BACKUP_DIR/appendonly_$DATE.aof

# Clean old backups (keep last 7 days)
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Redis backup completed: $BACKUP_DIR/dump_$DATE.rdb.gz"
```

Make executable and add to cron:
```bash
sudo chmod +x /opt/redis-backup.sh

# Add to crontab for daily backups at 3 AM
# 0 3 * * * /opt/redis-backup.sh
```

## Step 13: Troubleshooting

### Common Issues and Solutions:

**1. Memory Issues:**
```bash
# Check memory usage
redis-cli -h 192.168.1.184 -a your-redis-password info memory

# Find memory-consuming keys
redis-cli -h 192.168.1.184 -a your-redis-password --bigkeys

# Set memory limit and eviction policy
redis-cli -h 192.168.1.184 -a your-redis-password config set maxmemory 2gb
redis-cli -h 192.168.1.184 -a your-redis-password config set maxmemory-policy allkeys-lru
```

**2. Connection Issues:**
```bash
# Test connectivity
redis-cli -h 192.168.1.184 -p 6379 -a your-redis-password ping

# Check connected clients
redis-cli -h 192.168.1.184 -a your-redis-password client list

# Monitor commands in real-time
redis-cli -h 192.168.1.184 -a your-redis-password monitor
```

**3. Performance Issues:**
```bash
# Check slow log
redis-cli -h 192.168.1.184 -a your-redis-password slowlog get 10

# Monitor latency
redis-cli -h 192.168.1.184 -a your-redis-password --latency

# Check stats
redis-cli -h 192.168.1.184 -a your-redis-password info stats
```

**4. Replication Issues:**
```bash
# Check replication status
redis-cli -h 192.168.1.184 -a your-redis-password info replication

# Force replica resync
redis-cli -h 192.168.1.187 -a your-redis-password debug restart
```

This Redis setup provides high-performance caching, feature serving, real-time analytics, and model serving capabilities that integrate seamlessly with your entire data engineering ecosystem.
