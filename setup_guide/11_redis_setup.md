# Redis Setup Guide

## Overview
Redis will be set up on cpu-node1 as a high-performance in-memory data store, cache, and message broker. It will serve as a caching layer, real-time analytics store, and feature serving system for ML applications.

## What is Redis?
Redis (Remote Dictionary Server) is an open-source, in-memory data structure store used as a database, cache, message broker, and streaming engine. It supports various data structures such as strings, hashes, lists, sets, sorted sets with range queries, bitmaps, hyperloglogs, geospatial indexes, and streams.

## Machine Configuration
- **Primary Node**: cpu-node1 (192.168.1.184) - Redis Master
- **Replica Node**: cpu-node2 (192.168.1.187) - Redis Replica for high availability  
- **Worker Node**: worker-node3 (IP: TBD) - Additional Redis node (role TBD)
- **Client Node**: gpu-node (192.168.1.79) - Redis client for ML workloads
- **Integration**: Works with all existing components

## Prerequisites
- Ubuntu/Debian-based Linux distribution
- At least 2GB RAM (4GB+ recommended for production)
- At least 5GB free disk space
- Network connectivity between nodes

## Architecture Overview
```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│    cpu-node1        │    │    cpu-node2        │    │   worker-node3      │    │   gpu-node          │
│  - Redis Master     │────│  - Redis Replica    │────│  - Redis Node       │    │  - Redis Client     │
│  - PostgreSQL       │    │  - Neo4j            │    │  - (Role TBD)       │    │  - ML Feature Store │
│  - Kafka Broker     │    │  - Other Services   │    │  - Other Services   │    │  - Model Serving    │
│  192.168.1.184      │    │  192.168.1.187      │    │  192.168.1.XXX      │    │  192.168.1.79       │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘    └─────────────────────┘
```

## 🚀 CPU-NODE1 SETUP OVERVIEW

**Complete setup requires 5 main steps - follow in order:**

1. **📦 Install Redis** → Install packages and verify
2. **⚙️ Configure Redis** → Choose ONE configuration method (A, B, or C)  
3. **🖥️ System Optimization** → Choose ONE system method (A or B)
4. **📁 Setup Directories** → Create required directories and permissions  
5. **🔥 Start & Test** → Enable services and verify everything works

---

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

⚠️ **IMPORTANT: Choose ONE configuration method below. Do NOT mix methods!**

### Prerequisites - Backup First (REQUIRED)

```bash
# ALWAYS create backup first
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup.$(date +%Y%m%d_%H%M%S)
```

---

### METHOD A: Manual Configuration (Recommended for Learning)

**Use this if:** You want to understand each setting and customize manually.

```bash
# Edit the configuration file
sudo nano /etc/redis/redis.conf
```

**Find and modify these sections (use Ctrl+W to search):**

1. **Network (search for "bind"):**
```conf
bind 0.0.0.0                    # Accept connections from any IP
protected-mode no               # Disable protected mode when binding to 0.0.0.0
port 6379                       # Default Redis port
```

2. **Security (search for "requirepass"):**
```conf
requirepass your-strong-password-here    # Set a strong password
```

3. **Memory (search for "maxmemory"):**
```conf
# Uncomment and set these lines:
maxmemory 2gb                   # Adjust based on your RAM
maxmemory-policy allkeys-lru    # Eviction policy
```

4. **Persistence (search for "appendonly"):**
```conf
appendonly yes                  # Enable AOF for durability
appendfsync everysec           # Sync every second (balanced performance/safety)
```

---

### METHOD B: Automated Configuration (Recommended for Production)

**Use this if:** You want quick, consistent setup without manual editing.

```bash
# Run these commands in sequence (DO NOT run if you used Method A!)

# 1. Network configuration
sudo sed -i 's/^bind 127.0.0.1 -::1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf

# 2. Security configuration
sudo sed -i 's/^# requirepass foobared/requirepass your-strong-password/' /etc/redis/redis.conf

# 3. Memory configuration (only add if not already present)
if ! grep -q "^maxmemory" /etc/redis/redis.conf; then
    echo "maxmemory 2gb" | sudo tee -a /etc/redis/redis.conf
    echo "maxmemory-policy allkeys-lru" | sudo tee -a /etc/redis/redis.conf
fi

# 4. Persistence configuration
sudo sed -i 's/^appendonly no/appendonly yes/' /etc/redis/redis.conf
```

---

### METHOD C: Template Replacement (Advanced Users Only)

**Use this if:** You have a specific template or want to completely replace the config.

```bash
# Get official Redis template
wget https://raw.githubusercontent.com/redis/redis/7.0/redis.conf -O /tmp/redis.conf.template

# Customize the template as needed, then replace
sudo cp /tmp/redis.conf.template /etc/redis/redis.conf

# Then edit for your specific settings
sudo nano /etc/redis/redis.conf
```

---

### Verification (Run After ANY Method Above)

```bash
# Test configuration syntax
sudo redis-server /etc/redis/redis.conf --test-config

# Restart Redis with new config
sudo systemctl restart redis-server

# Check service status
sudo systemctl status redis-server

# Test connection (replace 'your-password' with actual password)
redis-cli -h 192.168.1.184 -a your-password ping

# Should return: PONG
```

## Step 3: System Configuration

⚠️ **IMPORTANT: Choose ONE system configuration method below. Do NOT mix methods!**

### Check Current System State (REQUIRED - Run First)

```bash
# Check current kernel parameters
echo "=== Current System State ==="
echo "vm.overcommit_memory = $(sysctl -n vm.overcommit_memory)"
echo "net.core.somaxconn = $(sysctl -n net.core.somaxconn)"
echo "vm.swappiness = $(sysctl -n vm.swappiness)"
echo "THP enabled: $(cat /sys/kernel/mm/transparent_hugepage/enabled)"
echo "THP defrag: $(cat /sys/kernel/mm/transparent_hugepage/defrag)"

# Check existing configurations
echo "=== Existing Configuration Files ==="
ls -la /etc/sysctl.d/ | grep -v total
```

---

### METHOD A: Manual Configuration (Step-by-Step)

**Use this if:** You want to understand each step and have full control.

#### A1. System Limits Configuration
```bash
# Configure system limits for Redis
sudo tee -a /etc/security/limits.conf > /dev/null <<EOF
redis soft nofile 65535
redis hard nofile 65535
redis soft nproc 65535
redis hard nproc 65535
EOF
```

#### A2. Kernel Parameters (Choose ONE option below)

**Option A2a: Dedicated Redis Config File (Recommended)**
```bash
sudo tee /etc/sysctl.d/99-redis.conf > /dev/null <<EOF
# Redis optimization settings
vm.overcommit_memory = 1
net.core.somaxconn = 65535
vm.swappiness = 1
EOF
```

**Option A2b: Add to Main sysctl.conf (if you prefer centralized config)**
```bash
# Backup first
sudo cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d_%H%M%S)

# Add Redis settings
sudo tee -a /etc/sysctl.conf > /dev/null <<EOF

# Redis optimization settings
vm.overcommit_memory = 1
net.core.somaxconn = 65535
EOF
```

#### A3. Disable Transparent Huge Pages (Choose ONE method)

**Method A3a: systemd Service (Recommended)**
```bash
sudo tee /etc/systemd/system/disable-thp.service > /dev/null <<EOF
[Unit]
Description=Disable Transparent Huge Pages (THP)
DefaultDependencies=false
After=sysinit.target local-fs.target
Before=redis-server.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/defrag'

[Install]
WantedBy=basic.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable disable-thp.service
```

**Method A3b: rc.local (Alternative)**
```bash
if [ -f /etc/rc.local ]; then
    sudo cp /etc/rc.local /etc/rc.local.backup
    sudo sed -i '/^exit 0/i echo never > /sys/kernel/mm/transparent_hugepage/enabled\necho never > /sys/kernel/mm/transparent_hugepage/defrag' /etc/rc.local
else
    sudo tee /etc/rc.local > /dev/null <<EOF
#!/bin/bash
echo never > /sys/kernel/mm/transparent_hugepage/enabled
echo never > /sys/kernel/mm/transparent_hugepage/defrag
exit 0
EOF
    sudo chmod +x /etc/rc.local
fi
```

#### A4. Apply Changes
```bash
# Apply sysctl changes
sudo sysctl -p
if [ -f /etc/sysctl.d/99-redis.conf ]; then
    sudo sysctl -p /etc/sysctl.d/99-redis.conf
fi

# Disable THP immediately
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag

# Start THP service (if using systemd method)
if [ -f /etc/systemd/system/disable-thp.service ]; then
    sudo systemctl start disable-thp.service
fi
```

---

### METHOD B: Automated Script (One-Shot Setup)

**Use this if:** You want everything done automatically with sensible defaults.

```bash
# Save this as redis-system-setup.sh and run it
# DO NOT run this if you used Method A!

#!/bin/bash
echo "=== Redis System Optimization (Automated) ==="

# System limits
echo "Configuring system limits..."
sudo tee -a /etc/security/limits.conf > /dev/null <<EOF
redis soft nofile 65535
redis hard nofile 65535
redis soft nproc 65535
redis hard nproc 65535
EOF

# Kernel parameters (dedicated file)
echo "Configuring kernel parameters..."
sudo tee /etc/sysctl.d/99-redis.conf > /dev/null <<EOF
# Redis optimization settings
vm.overcommit_memory = 1
net.core.somaxconn = 65535
vm.swappiness = 1
EOF

# THP disable service
echo "Creating THP disable service..."
sudo tee /etc/systemd/system/disable-thp.service > /dev/null <<EOF
[Unit]
Description=Disable Transparent Huge Pages (THP)
DefaultDependencies=false
After=sysinit.target local-fs.target
Before=redis-server.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/enabled'
ExecStart=/bin/sh -c 'echo never > /sys/kernel/mm/transparent_hugepage/defrag'

[Install]
WantedBy=basic.target
EOF

# Apply all changes
echo "Applying changes..."
sudo systemctl daemon-reload
sudo systemctl enable disable-thp.service
sudo systemctl start disable-thp.service
sudo sysctl -p /etc/sysctl.d/99-redis.conf

# Disable THP immediately
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag

echo "=== Configuration Complete! ==="
```

---

### Verification (Run After ANY Method Above)

```bash
# Verify all settings
echo "=== Final System Configuration ==="
echo "vm.overcommit_memory = $(sysctl -n vm.overcommit_memory)  (should be 1)"
echo "net.core.somaxconn = $(sysctl -n net.core.somaxconn)     (should be 65535)"  
echo "vm.swappiness = $(sysctl -n vm.swappiness)               (should be 1)"
echo "THP enabled: $(cat /sys/kernel/mm/transparent_hugepage/enabled)   (should show [never])"
echo "THP defrag: $(cat /sys/kernel/mm/transparent_hugepage/defrag)     (should show [never])"

echo "=== Redis User Configuration ==="
getent passwd redis
echo "Redis service limits:"
sudo systemctl show redis-server | grep -E "(LimitNOFILE|LimitNPROC)"

echo "=== Redis Process Status ==="
ps aux | grep redis | grep -v grep
sudo ls -la /var/lib/redis
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

# Enable auto-start on boot
sudo systemctl enable redis-server

# Check status (should show "active (running)")
sudo systemctl status redis-server

# Test connection (replace 'your-redis-password' with actual password)
redis-cli -h 192.168.1.184 -a your-redis-password ping

# Should return: PONG
```

---

## ✅ CPU-NODE1 SETUP COMPLETE!

If all tests pass above, your Redis master is now ready. Next steps:
- **Step 6**: Set up cpu-node2 as a replica (optional but recommended)
- **Step 7**: Set up worker-node3 (choose role based on your needs)
- **Step 8+**: Configure monitoring, backups, and integration

---

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

## Step 7: Worker-Node3 Redis Setup

**Please specify worker-node3 details:**
- **IP Address**: What is the IP address of worker-node3?  
- **Role**: What role should worker-node3 serve?

### Option A: Additional Redis Replica (High Availability)

If worker-node3 should be another Redis replica:

```bash
# On worker-node3 (IP: 192.168.1.XXX)
sudo apt update
sudo apt install -y redis-server redis-tools

# Configure as replica
sudo nano /etc/redis/redis.conf
```

Add/modify these settings:
```conf
# Network configuration
bind 0.0.0.0
protected-mode no
port 6379

# Replica configuration
replicaof 192.168.1.184 6379
masterauth your-redis-password
requirepass your-redis-password

# Data directory
dir /var/lib/redis

# Logging
logfile /var/log/redis/redis-server.log
```

### Option B: Redis Sentinel (Automatic Failover)

If worker-node3 should run Redis Sentinel for automatic failover:

```bash
# On worker-node3
sudo apt update
sudo apt install -y redis-sentinel

# Configure Sentinel
sudo nano /etc/redis/sentinel.conf
```

Sentinel configuration:
```conf
# Sentinel port
port 26379

# Monitor master
sentinel monitor mymaster 192.168.1.184 6379 2

# Authentication
sentinel auth-pass mymaster your-redis-password

# Failover configuration
sentinel down-after-milliseconds mymaster 30000
sentinel parallel-syncs mymaster 1
sentinel failover-timeout mymaster 180000

# Notification scripts (optional)
# sentinel notification-script mymaster /var/redis/notify.sh
```

### Option C: Redis Cluster Node (Horizontal Scaling)

If you want to set up Redis Cluster for horizontal scaling:

```bash
# On all nodes (cpu-node1, cpu-node2, worker-node3)
# Modify redis.conf for cluster mode

sudo nano /etc/redis/redis.conf
```

Add cluster configuration:
```conf
# Enable cluster mode
cluster-enabled yes
cluster-config-file nodes.conf
cluster-node-timeout 15000

# Different ports for each node
# cpu-node1: port 7001
# cpu-node2: port 7002  
# worker-node3: port 7003

# Network configuration
bind 0.0.0.0
protected-mode no
```

Create cluster:
```bash
# After configuring all nodes
redis-cli --cluster create 192.168.1.184:7001 192.168.1.187:7002 192.168.1.XXX:7003 --cluster-replicas 0
```

### Option D: Redis Client Only (Like gpu-node)

If worker-node3 should only be a Redis client:

```bash
# On worker-node3
sudo apt update
sudo apt install -y redis-tools

# Test connection
redis-cli -h 192.168.1.184 -p 6379 -a your-redis-password ping
```

### Common Setup Steps (after choosing role above)

⚠️ **Note**: For any Redis server role (Options A, B, or C), you also need to:

1. **System Optimization**: Follow **Step 3** from cpu-node1 setup (choose Method A or B)
2. **Directory Setup**: Run **Step 4** from cpu-node1 setup  
3. **Service Management**: Run **Step 5** from cpu-node1 setup

### Worker-Node3 Specific Commands

After completing the common steps above:

```bash
# Firewall configuration (adjust ports based on chosen role)
sudo ufw allow 6379/tcp          # Redis (Options A, D)
# sudo ufw allow 26379/tcp       # Redis Sentinel (Option B)  
# sudo ufw allow 7003/tcp        # Redis Cluster (Option C)
# sudo ufw allow 17003/tcp       # Cluster bus port (Option C)
sudo ufw reload

# Test connection (replace IP and password)
redis-cli -h 192.168.1.XXX -p 6379 -a your-password ping

# For replicas (Option A), verify replication:
redis-cli -h 192.168.1.XXX -a your-password info replication
```

**⚠️ Please provide:**
1. **Worker-node3 IP address**
2. **Preferred setup option** (A, B, C, or D)

I can then update the documentation with specific commands for your chosen configuration.

## Step 8: Firewall Configuration

```bash
# On both nodes, open Redis port
sudo ufw allow 6379/tcp
sudo ufw reload
```

## Step 9: Redis Monitoring Setup

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

## Step 10: Integration Examples

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

## Step 11: Redis for ML Model Serving

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

## Step 12: Performance Tuning and Optimization

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

## Step 13: Backup and Recovery

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

## Step 14: Troubleshooting

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
