# Elasticsearch Cluster Setup Guide

## Overview
Elasticsearch will be set up in cluster mode with cpu-node1 as the master-eligible coordinator node, cpu-node2 as a data node, and worker-node3 as an additional data node. This setup provides distributed search, analytics, and data storage capabilities.

## Cluster Configuration
- **Master/Coordinator Node**: cpu-node1 (192.168.1.184) - Cluster coordination and search coordination
- **Data Node 1**: cpu-node2 (192.168.1.187) - Primary data storage and processing
- **Data Node 2**: worker-node3 (192.168.1.190) - Additional data storage and processing

## Prerequisites
- Java 11 or later installed on all nodes
- At least 8GB RAM per node (4GB minimum for testing)
- At least 50GB free disk space per node
- Network connectivity between all nodes
- Sufficient virtual memory (vm.max_map_count)

## Architecture Overview
```
┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
│      cpu-node1          │    │      cpu-node2          │    │     worker-node3        │
│   (Master/Coordinator)  │    │     (Data Node 1)       │    │     (Data Node 2)       │
│  - Cluster Management   │    │  - Data Storage         │    │  - Data Storage         │
│  - Search Coordination  │    │  - Query Execution      │    │  - Query Execution      │
│  - Index Management     │    │  - Aggregations         │    │  - Aggregations         │
│  - Kibana Dashboard     │    │  - Machine Learning     │    │  - Machine Learning     │
│  - API Gateway (9200)   │    │  - Analytics            │    │  - Analytics            │
│  192.168.1.184          │    │  192.168.1.187          │    │  192.168.1.190          │
└─────────────────────────┘    └─────────────────────────┘    └─────────────────────────┘
```

## Step 1: System Prerequisites (All Nodes)

### Install Java 11+
```bash
# Update package repository
sudo apt update

# Install OpenJDK 11
sudo apt install -y openjdk-11-jdk

# Verify Java installation
java -version

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc
```

### Configure System Settings
```bash
# Increase virtual memory for Elasticsearch
sudo sysctl -w vm.max_map_count=262144

# Make it permanent
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf

# Increase file descriptor limits
echo 'elasticsearch soft nofile 65536' | sudo tee -a /etc/security/limits.conf
echo 'elasticsearch hard nofile 65536' | sudo tee -a /etc/security/limits.conf
echo 'elasticsearch soft nproc 4096' | sudo tee -a /etc/security/limits.conf
echo 'elasticsearch hard nproc 4096' | sudo tee -a /etc/security/limits.conf

# Disable swap for better performance
sudo swapoff -a
echo '# Disable swap for Elasticsearch' | sudo tee -a /etc/fstab
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab
```

## Step 2: Create Elasticsearch User (All Nodes)

```bash
# Create elasticsearch user
sudo useradd -m -s /bin/bash elasticsearch
sudo passwd elasticsearch

# Create directories
sudo mkdir -p /opt/elasticsearch
sudo mkdir -p /var/lib/elasticsearch
sudo mkdir -p /var/log/elasticsearch
sudo mkdir -p /etc/elasticsearch

# Set ownership
sudo chown -R elasticsearch:elasticsearch /opt/elasticsearch
sudo chown -R elasticsearch:elasticsearch /var/lib/elasticsearch
sudo chown -R elasticsearch:elasticsearch /var/log/elasticsearch
sudo chown -R elasticsearch:elasticsearch /etc/elasticsearch
```

## Step 3: Download and Install Elasticsearch (All Nodes)

```bash
# Switch to elasticsearch user
sudo su - elasticsearch

# Download Elasticsearch 8.15.0 (latest stable)
cd /opt
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.15.0-linux-x86_64.tar.gz

# Extract and setup
tar -xzf elasticsearch-8.15.0-linux-x86_64.tar.gz
mv elasticsearch-8.15.0 elasticsearch
rm elasticsearch-8.15.0-linux-x86_64.tar.gz

# Set environment variables
echo 'export ES_HOME=/opt/elasticsearch' >> ~/.bashrc
echo 'export ES_PATH_CONF=/etc/elasticsearch' >> ~/.bashrc
echo 'export PATH=$PATH:$ES_HOME/bin' >> ~/.bashrc
source ~/.bashrc

# Create necessary directories
mkdir -p /var/lib/elasticsearch/data
mkdir -p /var/log/elasticsearch
```

## Step 4: Configure Elasticsearch Cluster

### Master/Coordinator Node Configuration (cpu-node1)

```bash
# Create main configuration file
sudo tee /etc/elasticsearch/elasticsearch.yml << 'EOF'
# ======================== Elasticsearch Configuration =========================

# ---------------------------------- Cluster -----------------------------------
cluster.name: homelab-es-cluster
node.name: master-node-1

# ----------------------------------- Paths ------------------------------------
path.data: /var/lib/elasticsearch/data
path.logs: /var/log/elasticsearch

# ---------------------------------- Network -----------------------------------
network.host: 192.168.1.184
http.port: 9200
transport.port: 9300

# --------------------------------- Discovery ----------------------------------
discovery.seed_hosts: ["192.168.1.184:9300", "192.168.1.187:9300", "192.168.1.190:9300"]
cluster.initial_master_nodes: ["master-node-1"]

# ----------------------------------- Nodes ------------------------------------
node.roles: [ master, ingest ]
node.master: true
node.data: false
node.ingest: true
node.ml: false

# ---------------------------------- Security ----------------------------------
xpack.security.enabled: false
xpack.security.enrollment.enabled: false
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: false

# ---------------------------------- Memory -----------------------------------
bootstrap.memory_lock: false

# ----------------------------------- Misc ------------------------------------
action.destructive_requires_name: true
cluster.routing.allocation.disk.threshold_enabled: true
cluster.routing.allocation.disk.watermark.low: 85%
cluster.routing.allocation.disk.watermark.high: 90%
cluster.routing.allocation.disk.watermark.flood_stage: 95%

# -------------------------------- Performance ---------------------------------
indices.query.bool.max_clause_count: 10000
search.max_buckets: 100000

# ---------------------------------- Logging -----------------------------------
logger.org.elasticsearch.discovery: INFO
logger.org.elasticsearch.cluster.service: INFO
EOF
```

### Data Node 1 Configuration (cpu-node2)

```bash
# Create main configuration file
sudo tee /etc/elasticsearch/elasticsearch.yml << 'EOF'
# ======================== Elasticsearch Configuration =========================

# ---------------------------------- Cluster -----------------------------------
cluster.name: homelab-es-cluster
node.name: data-node-1

# ----------------------------------- Paths ------------------------------------
path.data: /var/lib/elasticsearch/data
path.logs: /var/log/elasticsearch

# ---------------------------------- Network -----------------------------------
network.host: 192.168.1.187
http.port: 9200
transport.port: 9300

# --------------------------------- Discovery ----------------------------------
discovery.seed_hosts: ["192.168.1.184:9300", "192.168.1.187:9300", "192.168.1.190:9300"]
cluster.initial_master_nodes: ["master-node-1"]

# ----------------------------------- Nodes ------------------------------------
node.roles: [ data, ingest, ml ]
node.master: false
node.data: true
node.ingest: true
node.ml: true

# ---------------------------------- Security ----------------------------------
xpack.security.enabled: false
xpack.security.enrollment.enabled: false
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: false

# ---------------------------------- Memory -----------------------------------
bootstrap.memory_lock: false

# ----------------------------------- Misc ------------------------------------
action.destructive_requires_name: true
cluster.routing.allocation.disk.threshold_enabled: true
cluster.routing.allocation.disk.watermark.low: 85%
cluster.routing.allocation.disk.watermark.high: 90%
cluster.routing.allocation.disk.watermark.flood_stage: 95%

# -------------------------------- Performance ---------------------------------
indices.query.bool.max_clause_count: 10000
search.max_buckets: 100000

# ---------------------------------- Logging -----------------------------------
logger.org.elasticsearch.discovery: INFO
logger.org.elasticsearch.cluster.service: INFO
EOF
```

### Data Node 2 Configuration (worker-node3)

```bash
# Create main configuration file
sudo tee /etc/elasticsearch/elasticsearch.yml << 'EOF'
# ======================== Elasticsearch Configuration =========================

# ---------------------------------- Cluster -----------------------------------
cluster.name: homelab-es-cluster
node.name: data-node-2

# ----------------------------------- Paths ------------------------------------
path.data: /var/lib/elasticsearch/data
path.logs: /var/log/elasticsearch

# ---------------------------------- Network -----------------------------------
network.host: 192.168.1.190
http.port: 9200
transport.port: 9300

# --------------------------------- Discovery ----------------------------------
discovery.seed_hosts: ["192.168.1.184:9300", "192.168.1.187:9300", "192.168.1.190:9300"]
cluster.initial_master_nodes: ["master-node-1"]

# ----------------------------------- Nodes ------------------------------------
node.roles: [ data, ingest, ml ]
node.master: false
node.data: true
node.ingest: true
node.ml: true

# ---------------------------------- Security ----------------------------------
xpack.security.enabled: false
xpack.security.enrollment.enabled: false
xpack.security.http.ssl.enabled: false
xpack.security.transport.ssl.enabled: false

# ---------------------------------- Memory -----------------------------------
bootstrap.memory_lock: false

# ----------------------------------- Misc ------------------------------------
action.destructive_requires_name: true
cluster.routing.allocation.disk.threshold_enabled: true
cluster.routing.allocation.disk.watermark.low: 85%
cluster.routing.allocation.disk.watermark.high: 90%
cluster.routing.allocation.disk.watermark.flood_stage: 95%

# -------------------------------- Performance ---------------------------------
indices.query.bool.max_clause_count: 10000
search.max_buckets: 100000

# ---------------------------------- Logging -----------------------------------
logger.org.elasticsearch.discovery: INFO
logger.org.elasticsearch.cluster.service: INFO
EOF
```

## Step 5: Configure JVM Settings (All Nodes)

```bash
# Configure JVM heap size (adjust based on available RAM)
# Use 50% of available RAM, max 32GB
sudo tee /etc/elasticsearch/jvm.options << 'EOF'
# Xms represents the initial size of total heap space
# Xmx represents the maximum size of total heap space
-Xms2g
-Xmx2g

# Expert settings
-XX:+UseConcMarkSweepGC
-XX:CMSInitiatingOccupancyFraction=75
-XX:+UseCMSInitiatingOccupancyOnly

# GC logging
-Xlog:gc*,gc+age=trace,safepoint:gc.log:utctime,level,tags
-XX:+UseG1GC
-XX:G1HeapRegionSize=32m
-XX:+UnlockExperimentalVMOptions
-XX:+UseG1NewGenCollector

# Ensure UTF-8 encoding by default
-Dfile.encoding=UTF-8

# Use our provided JNA always versus the system one
-Djna.nosys=true

# Turn off a JDK optimization that throws away stack traces for common exceptions
-XX:-OmitStackTraceInFastThrow

# Flags to configure Netty
-Dio.netty.noUnsafe=true
-Dio.netty.noKeySetOptimization=true
-Dio.netty.recycler.maxCapacityPerThread=0
-Dlog4j.shutdownHookEnabled=false
-Dlog4j2.disable.jmx=true

# Temporary workaround for C2 compiler crashes
-XX:+UnlockDiagnosticVMOptions
-XX:+LogVMOutput
-XX:LogFile=/var/log/elasticsearch/gc.log

# Security manager
-Djava.security.policy=all.policy
EOF
```

## Step 6: Create Systemd Service (All Nodes)

```bash
# Create systemd service file
sudo tee /etc/systemd/system/elasticsearch.service << 'EOF'
[Unit]
Description=Elasticsearch
Documentation=https://www.elastic.co
Wants=network-online.target
After=network-online.target
ConditionNetwork=true

[Service]
RuntimeDirectory=elasticsearch
PrivateTmp=true
Environment=ES_HOME=/opt/elasticsearch
Environment=ES_PATH_CONF=/etc/elasticsearch
Environment=PID_DIR=/var/run/elasticsearch
Environment=ES_SD_NOTIFY=true
EnvironmentFile=-/etc/default/elasticsearch

WorkingDirectory=/opt/elasticsearch

User=elasticsearch
Group=elasticsearch

ExecStart=/opt/elasticsearch/bin/elasticsearch

# StandardOutput is configured to redirect to journalctl since
# some error messages may be logged in standard output before
# elasticsearch logging system is initialized. Elasticsearch
# stores its logs in /var/log/elasticsearch and does not use
# journalctl by default. If you also want to enable journalctl
# logging, you can simply remove the "quiet" option from ExecStart.
StandardOutput=journal
StandardError=inherit

# Specifies the maximum file descriptor number that can be opened by this process
LimitNOFILE=65535

# Specifies the maximum number of processes
LimitNPROC=4096

# Specifies the maximum size of virtual memory
LimitAS=infinity

# Specifies the maximum file size
LimitFSIZE=infinity

# Disable timeout logic and wait until process is stopped
TimeoutStopSec=0

# SIGTERM signal is used to stop the Java process
KillSignal=SIGTERM

# Send the signal only to the JVM rather than its control group
KillMode=process

# Java process is never killed
SendSIGKILL=no

# When a JVM receives a SIGTERM signal it exits with code 143
SuccessExitStatus=143

# Allow a slow startup before the systemd notifier module kicks in to extend the timeout
TimeoutStartSec=75

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch
```

## Step 7: Start Elasticsearch Cluster

### Start nodes in order (Master first, then data nodes)

```bash
# Start master node first (cpu-node1)
sudo systemctl start elasticsearch

# Check status
sudo systemctl status elasticsearch

# Check logs
sudo journalctl -u elasticsearch -f

# Wait 30 seconds, then start data nodes
# On cpu-node2:
sudo systemctl start elasticsearch

# On worker-node3:
sudo systemctl start elasticsearch
```

## Step 8: Verify Cluster Status

```bash
# Check cluster health
curl -X GET "192.168.1.184:9200/_cluster/health?pretty"

# Check nodes
curl -X GET "192.168.1.184:9200/_cat/nodes?v"

# Check cluster state
curl -X GET "192.168.1.184:9200/_cluster/state?pretty"

# Check indices
curl -X GET "192.168.1.184:9200/_cat/indices?v"
```

Expected output for healthy cluster:
```json
{
  "cluster_name" : "homelab-es-cluster",
  "status" : "green",
  "timed_out" : false,
  "number_of_nodes" : 3,
  "number_of_data_nodes" : 2,
  "active_primary_shards" : 0,
  "active_shards" : 0,
  "relocating_shards" : 0,
  "initializing_shards" : 0,
  "unassigned_shards" : 0,
  "delayed_unassigned_shards" : 0,
  "number_of_pending_tasks" : 0,
  "number_of_in_flight_fetch" : 0,
  "task_max_waiting_in_queue_millis" : 0,
  "active_shards_percent_as_number" : 100.0
}
```

## Step 9: Install and Configure Kibana (cpu-node1)

```bash
# Download and install Kibana
cd /opt
sudo wget https://artifacts.elastic.co/downloads/kibana/kibana-8.15.0-linux-x86_64.tar.gz
sudo tar -xzf kibana-8.15.0-linux-x86_64.tar.gz
sudo mv kibana-8.15.0 kibana
sudo rm kibana-8.15.0-linux-x86_64.tar.gz

# Set ownership
sudo chown -R elasticsearch:elasticsearch /opt/kibana

# Create Kibana configuration
sudo mkdir -p /etc/kibana
sudo tee /etc/kibana/kibana.yml << 'EOF'
# Kibana configuration

server.port: 5601
server.host: "192.168.1.184"
server.name: "homelab-kibana"

elasticsearch.hosts: ["http://192.168.1.184:9200"]
elasticsearch.requestTimeout: 30000
elasticsearch.shardTimeout: 30000

# Logging
logging.appenders:
  file:
    type: file
    fileName: /var/log/kibana/kibana.log
    layout:
      type: json

logging.root:
  level: info
  appenders: [file]

# Security
xpack.security.enabled: false
xpack.encryptedSavedObjects.encryptionKey: "something_at_least_32_characters_for_encryption"

# Performance
server.maxPayloadBytes: 1048576
elasticsearch.pingTimeout: 1500
EOF

# Create log directory
sudo mkdir -p /var/log/kibana
sudo chown -R elasticsearch:elasticsearch /var/log/kibana

# Create Kibana systemd service
sudo tee /etc/systemd/system/kibana.service << 'EOF'
[Unit]
Description=Kibana
Documentation=https://www.elastic.co
Wants=network-online.target
After=network-online.target elasticsearch.service
ConditionNetwork=true

[Service]
Environment=KIBANA_HOME=/opt/kibana
Environment=KIBANA_PATH_CONF=/etc/kibana
WorkingDirectory=/opt/kibana

User=elasticsearch
Group=elasticsearch

ExecStart=/opt/kibana/bin/kibana --path.config=/etc/kibana

Restart=on-failure
RestartSec=5

StandardOutput=journal
StandardError=inherit

[Install]
WantedBy=multi-user.target
EOF

# Enable and start Kibana
sudo systemctl daemon-reload
sudo systemctl enable kibana
sudo systemctl start kibana

# Check status
sudo systemctl status kibana
```

## Step 10: Configure Data Retention and Index Templates

```bash
# Create index template for log data
curl -X PUT "192.168.1.184:9200/_index_template/logs_template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["logs-*"],
    "template": {
      "settings": {
        "number_of_shards": 2,
        "number_of_replicas": 1,
        "index.refresh_interval": "30s",
        "index.lifecycle.name": "logs_policy",
        "index.lifecycle.rollover_alias": "logs"
      },
      "mappings": {
        "properties": {
          "@timestamp": {
            "type": "date"
          },
          "level": {
            "type": "keyword"
          },
          "message": {
            "type": "text",
            "analyzer": "standard"
          },
          "host": {
            "type": "keyword"
          },
          "service": {
            "type": "keyword"
          }
        }
      }
    }
  }'

# Create ILM policy for log retention
curl -X PUT "192.168.1.184:9200/_ilm/policy/logs_policy" \
  -H 'Content-Type: application/json' \
  -d '{
    "policy": {
      "phases": {
        "hot": {
          "actions": {
            "rollover": {
              "max_size": "1GB",
              "max_age": "1d"
            }
          }
        },
        "warm": {
          "min_age": "7d",
          "actions": {
            "allocate": {
              "number_of_replicas": 0
            }
          }
        },
        "cold": {
          "min_age": "30d",
          "actions": {
            "allocate": {
              "number_of_replicas": 0
            }
          }
        },
        "delete": {
          "min_age": "90d"
        }
      }
    }
  }'

# Create metrics template
curl -X PUT "192.168.1.184:9200/_index_template/metrics_template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": ["metrics-*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1,
        "index.refresh_interval": "5s"
      },
      "mappings": {
        "properties": {
          "@timestamp": {
            "type": "date"
          },
          "metric_name": {
            "type": "keyword"
          },
          "value": {
            "type": "double"
          },
          "host": {
            "type": "keyword"
          },
          "tags": {
            "type": "object"
          }
        }
      }
    }
  }'
```

## Step 11: Performance Optimization

### Cluster Settings
```bash
# Configure cluster-level settings
curl -X PUT "192.168.1.184:9200/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "persistent": {
      "cluster.routing.allocation.disk.threshold_enabled": true,
      "cluster.routing.allocation.disk.watermark.low": "85%",
      "cluster.routing.allocation.disk.watermark.high": "90%",
      "cluster.routing.allocation.disk.watermark.flood_stage": "95%",
      "cluster.routing.rebalance.enable": "all",
      "cluster.routing.allocation.cluster_concurrent_rebalance": 2,
      "cluster.routing.allocation.node_concurrent_recoveries": 2,
      "indices.recovery.max_bytes_per_sec": "40mb",
      "indices.breaker.total.limit": "70%",
      "indices.breaker.request.limit": "40%",
      "indices.breaker.fielddata.limit": "40%"
    }
  }'
```

### Node-specific Optimizations (All Nodes)
```bash
# Add to elasticsearch.yml for better performance
sudo tee -a /etc/elasticsearch/elasticsearch.yml << 'EOF'

# -------------------------------- Performance Tuning -----------------------
# Thread pool settings
thread_pool.write.queue_size: 1000
thread_pool.search.queue_size: 1000

# Cache settings
indices.fielddata.cache.size: 40%
indices.requests.cache.size: 2%
indices.queries.cache.size: 10%

# Indexing settings
index.refresh_interval: 30s
index.number_of_replicas: 1
index.routing.allocation.total_shards_per_node: 1000

# Search settings
search.max_buckets: 100000
search.default_search_timeout: 60s
EOF

# Restart Elasticsearch to apply changes
sudo systemctl restart elasticsearch
```

## Step 12: Monitoring and Alerting Setup

```bash
# Create monitoring index template
curl -X PUT "192.168.1.184:9200/_index_template/monitoring_template" \
  -H 'Content-Type: application/json' \
  -d '{
    "index_patterns": [".monitoring-*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.refresh_interval": "10s"
      }
    }
  }'

# Enable monitoring collection
curl -X PUT "192.168.1.184:9200/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "persistent": {
      "xpack.monitoring.collection.enabled": true,
      "xpack.monitoring.collection.interval": "30s"
    }
  }'
```

### Create Health Check Script
```bash
# Create health check script
sudo tee /opt/elasticsearch/health_check.sh << 'EOF'
#!/bin/bash

ES_HOST="192.168.1.184:9200"
LOG_FILE="/var/log/elasticsearch/health_check.log"

# Function to log with timestamp
log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

# Check cluster health
HEALTH=$(curl -s -X GET "$ES_HOST/_cluster/health" | jq -r '.status')

if [ "$HEALTH" = "green" ]; then
    log_with_timestamp "Cluster health: GREEN - All good"
    exit 0
elif [ "$HEALTH" = "yellow" ]; then
    log_with_timestamp "Cluster health: YELLOW - Warning"
    exit 1
else
    log_with_timestamp "Cluster health: RED - Critical"
    exit 2
fi
EOF

sudo chmod +x /opt/elasticsearch/health_check.sh
sudo chown elasticsearch:elasticsearch /opt/elasticsearch/health_check.sh

# Add to crontab for regular health checks
(crontab -u elasticsearch -l 2>/dev/null; echo "*/5 * * * * /opt/elasticsearch/health_check.sh") | sudo crontab -u elasticsearch -
```

## Step 13: Security Hardening (Optional)

### Enable Security Features
```bash
# Stop Elasticsearch
sudo systemctl stop elasticsearch

# Generate certificates
sudo /opt/elasticsearch/bin/elasticsearch-certutil ca --out /etc/elasticsearch/elastic-stack-ca.p12 --pass ""
sudo /opt/elasticsearch/bin/elasticsearch-certutil cert --ca /etc/elasticsearch/elastic-stack-ca.p12 --out /etc/elasticsearch/elastic-certificates.p12 --pass ""

# Set permissions
sudo chown elasticsearch:elasticsearch /etc/elasticsearch/elastic-*.p12
sudo chmod 660 /etc/elasticsearch/elastic-*.p12

# Update configuration to enable security
sudo tee -a /etc/elasticsearch/elasticsearch.yml << 'EOF'

# ---------------------------------- Security ----------------------------------
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.transport.ssl.verification_mode: certificate
xpack.security.transport.ssl.client_authentication: required
xpack.security.transport.ssl.keystore.path: elastic-certificates.p12
xpack.security.transport.ssl.truststore.path: elastic-certificates.p12

xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.keystore.path: elastic-certificates.p12
EOF

# Start Elasticsearch
sudo systemctl start elasticsearch

# Set passwords for built-in users
sudo /opt/elasticsearch/bin/elasticsearch-setup-passwords auto
```

## Step 14: Integration with Other Services

### Logstash Configuration Example
```bash
# Create Logstash pipeline configuration
sudo mkdir -p /etc/logstash/conf.d
sudo tee /etc/logstash/conf.d/beats-elasticsearch.conf << 'EOF'
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][log_type] == "syslog" {
    grok {
      match => { "message" => "%{SYSLOGTIMESTAMP:timestamp} %{WORD:host} %{WORD:process}: %{GREEDYDATA:msg}" }
    }
    date {
      match => [ "timestamp", "MMM  d HH:mm:ss", "MMM dd HH:mm:ss" ]
    }
  }
}

output {
  elasticsearch {
    hosts => ["192.168.1.184:9200", "192.168.1.187:9200", "192.168.1.190:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }
}
EOF
```

### Filebeat Configuration Example
```yaml
# /etc/filebeat/filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/*.log
  fields:
    log_type: syslog
  fields_under_root: true

output.logstash:
  hosts: ["192.168.1.184:5044"]

processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
```

## Step 15: Testing and Validation

### Basic CRUD Operations Test
```bash
# Create a test index
curl -X PUT "192.168.1.184:9200/test_index" \
  -H 'Content-Type: application/json' \
  -d '{
    "settings": {
      "number_of_shards": 2,
      "number_of_replicas": 1
    }
  }'

# Index a document
curl -X POST "192.168.1.184:9200/test_index/_doc/1" \
  -H 'Content-Type: application/json' \
  -d '{
    "timestamp": "2024-01-01T10:00:00",
    "message": "Test message",
    "level": "INFO",
    "service": "test-service"
  }'

# Search documents
curl -X GET "192.168.1.184:9200/test_index/_search?pretty"

# Update document
curl -X POST "192.168.1.184:9200/test_index/_update/1" \
  -H 'Content-Type: application/json' \
  -d '{
    "doc": {
      "level": "DEBUG"
    }
  }'

# Delete document
curl -X DELETE "192.168.1.184:9200/test_index/_doc/1"

# Delete index
curl -X DELETE "192.168.1.184:9200/test_index"
```

### Performance Test
```bash
# Bulk indexing test
curl -X POST "192.168.1.184:9200/performance_test/_bulk" \
  -H 'Content-Type: application/json' \
  --data-binary @- << 'EOF'
{"index":{"_id":"1"}}
{"timestamp":"2024-01-01T10:00:00","cpu_usage":45.2,"memory_usage":60.1,"host":"server1"}
{"index":{"_id":"2"}}
{"timestamp":"2024-01-01T10:01:00","cpu_usage":48.7,"memory_usage":62.3,"host":"server1"}
{"index":{"_id":"3"}}
{"timestamp":"2024-01-01T10:02:00","cpu_usage":52.1,"memory_usage":58.9,"host":"server2"}
EOF

# Aggregation test
curl -X GET "192.168.1.184:9200/performance_test/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "aggs": {
      "avg_cpu": {
        "avg": {
          "field": "cpu_usage"
        }
      },
      "hosts": {
        "terms": {
          "field": "host"
        }
      }
    }
  }'
```

## Step 16: Backup and Recovery

### Snapshot Repository Setup
```bash
# Create snapshot repository directory
sudo mkdir -p /opt/elasticsearch/backups
sudo chown elasticsearch:elasticsearch /opt/elasticsearch/backups

# Register snapshot repository
curl -X PUT "192.168.1.184:9200/_snapshot/backup_repo" \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "fs",
    "settings": {
      "location": "/opt/elasticsearch/backups"
    }
  }'

# Create snapshot
curl -X PUT "192.168.1.184:9200/_snapshot/backup_repo/snapshot_1" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "*",
    "ignore_unavailable": true,
    "include_global_state": false
  }'

# Check snapshot status
curl -X GET "192.168.1.184:9200/_snapshot/backup_repo/snapshot_1"

# Restore snapshot (example)
curl -X POST "192.168.1.184:9200/_snapshot/backup_repo/snapshot_1/_restore" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "test_index",
    "ignore_unavailable": true,
    "include_global_state": false
  }'
```

### Automated Backup Script
```bash
# Create backup script
sudo tee /opt/elasticsearch/backup_script.sh << 'EOF'
#!/bin/bash

ES_HOST="192.168.1.184:9200"
SNAPSHOT_REPO="backup_repo"
DATE=$(date +%Y%m%d_%H%M%S)
SNAPSHOT_NAME="auto_snapshot_$DATE"

# Create snapshot
curl -X PUT "$ES_HOST/_snapshot/$SNAPSHOT_REPO/$SNAPSHOT_NAME" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "*",
    "ignore_unavailable": true,
    "include_global_state": false,
    "metadata": {
      "taken_by": "automated_backup",
      "taken_because": "scheduled backup"
    }
  }'

echo "Snapshot $SNAPSHOT_NAME created successfully"

# Clean up old snapshots (keep last 7 days)
SEVEN_DAYS_AGO=$(date -d '7 days ago' +%Y%m%d)
curl -s -X GET "$ES_HOST/_snapshot/$SNAPSHOT_REPO/_all" | \
  jq -r '.snapshots[] | select(.start_time_in_millis < ('$(date -d "$SEVEN_DAYS_AGO" +%s)'000)) | .snapshot' | \
  while read old_snapshot; do
    curl -X DELETE "$ES_HOST/_snapshot/$SNAPSHOT_REPO/$old_snapshot"
    echo "Deleted old snapshot: $old_snapshot"
  done
EOF

sudo chmod +x /opt/elasticsearch/backup_script.sh
sudo chown elasticsearch:elasticsearch /opt/elasticsearch/backup_script.sh

# Add to crontab for daily backups
(crontab -u elasticsearch -l 2>/dev/null; echo "0 2 * * * /opt/elasticsearch/backup_script.sh") | sudo crontab -u elasticsearch -
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Cluster Yellow/Red Status
```bash
# Check unassigned shards
curl -X GET "192.168.1.184:9200/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason"

# Force allocation of unassigned shards
curl -X POST "192.168.1.184:9200/_cluster/reroute" \
  -H 'Content-Type: application/json' \
  -d '{
    "commands": [
      {
        "allocate_empty_primary": {
          "index": "your_index",
          "shard": 0,
          "node": "data-node-1",
          "accept_data_loss": true
        }
      }
    ]
  }'
```

#### 2. Memory Issues
```bash
# Check heap usage
curl -X GET "192.168.1.184:9200/_nodes/stats/jvm?pretty"

# Clear field data cache
curl -X POST "192.168.1.184:9200/_cache/clear?fielddata=true"

# Clear query cache
curl -X POST "192.168.1.184:9200/_cache/clear?query=true"
```

#### 3. Disk Space Issues
```bash
# Check disk usage per node
curl -X GET "192.168.1.184:9200/_cat/allocation?v"

# Force merge to reduce segment count
curl -X POST "192.168.1.184:9200/your_index/_forcemerge?max_num_segments=1"

# Delete old indices
curl -X DELETE "192.168.1.184:9200/old_index_name"
```

#### 4. Performance Issues
```bash
# Check slow queries
curl -X GET "192.168.1.184:9200/_nodes/stats/indices/search?pretty"

# Check thread pool status
curl -X GET "192.168.1.184:9200/_cat/thread_pool?v&h=node_name,name,active,queue,rejected"

# Hot threads analysis
curl -X GET "192.168.1.184:9200/_nodes/hot_threads"
```

### Log Locations
- **Elasticsearch logs**: `/var/log/elasticsearch/`
- **Kibana logs**: `/var/log/kibana/`
- **Service logs**: `journalctl -u elasticsearch -f`

### Useful Monitoring Commands
```bash
# Cluster health check
curl -X GET "192.168.1.184:9200/_cluster/health?pretty"

# Node information
curl -X GET "192.168.1.184:9200/_cat/nodes?v"

# Index statistics
curl -X GET "192.168.1.184:9200/_cat/indices?v&s=store.size:desc"

# Segment information
curl -X GET "192.168.1.184:9200/_cat/segments?v"

# Shard allocation
curl -X GET "192.168.1.184:9200/_cat/allocation?v"
```

## Conclusion

Your Elasticsearch cluster is now ready for production use! The setup provides:

- **High Availability**: Multi-node cluster with proper role separation
- **Scalability**: Easy to add more data nodes as needed
- **Monitoring**: Kibana dashboard and health checking
- **Data Management**: Index lifecycle management and retention policies
- **Backup/Recovery**: Automated snapshot management
- **Performance**: Optimized configuration for your hardware

### Next Steps
1. Configure your applications to send data to Elasticsearch
2. Create custom dashboards in Kibana
3. Set up alerting for critical metrics
4. Implement log aggregation pipelines
5. Explore machine learning features for anomaly detection

### URLs for Access
- **Elasticsearch API**: http://192.168.1.184:9200
- **Kibana Dashboard**: http://192.168.1.184:5601

The cluster is configured for development and testing. For production environments, enable security features and SSL/TLS encryption.
