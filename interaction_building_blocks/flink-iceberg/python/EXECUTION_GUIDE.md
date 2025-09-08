# Flink-Iceberg Streaming Execution Guide

## Overview
This guide provides complete execution steps, testing instructions, and expected output for the Flink-Iceberg streaming integration.

## Prerequisites Checklist

Before running the streaming job, ensure all these components are running:

- [ ] **Flink Cluster**: JobManager and TaskManagers running
- [ ] **Kafka Cluster**: All brokers running with topic 'user-events'
- [ ] **Hive Metastore**: Running on cpu-node1:9083
- [ ] **HDFS**: Distributed file system running
- [ ] **JAR Files**: Iceberg and Hadoop JARs in Flink lib directory

## Step 1: Verify Prerequisites

### Check Flink Cluster Status
```bash
# Check Flink processes
jps | grep -E "(JobManager|TaskManager)"

# Check Flink Web UI
curl -s -I http://192.168.1.184:8081

# Expected: HTTP/1.1 200 OK
```

### Check Kafka Topic
```bash
# List topics
/home/kafka/kafka/bin/kafka-topics.sh --bootstrap-server 192.168.1.184:9092 --list

# Create topic if it doesn't exist
/home/kafka/kafka/bin/kafka-topics.sh \
    --bootstrap-server 192.168.1.184:9092 \
    --topic user-events \
    --create \
    --partitions 3 \
    --replication-factor 2
```

### Verify JAR Files
```bash
# Check required JARs are in Flink lib directory
ls -la /home/flink/flink/lib/ | grep -E "(iceberg|hadoop)"

# Expected output:
# iceberg-flink-runtime-1.19-1.9.2.jar
# hadoop-client-3.3.6.jar
```

### Test Hive Metastore Connection
```bash
# Test connection
telnet 192.168.1.184 9083

# Expected: Connected to 192.168.1.184
```

## Step 2: Install Python Dependencies

```bash
# Install required Python packages
cd /home/sanzad/git/DataEngineering/interaction_building_blocks/flink-iceberg/python

# Install PyFlink and dependencies
pip install apache-flink kafka-python

# Verify installation
python3 -c "import pyflink; print('PyFlink version:', pyflink.__version__)"
```

## Step 3: Run the Streaming Job

### Terminal 1: Start Data Producer
```bash
# Navigate to the directory
cd /home/sanzad/git/DataEngineering/interaction_building_blocks/flink-iceberg/python

# Run the main streaming script to generate test producer
python3 kafka_to_iceberg_streaming.py

# This will create /tmp/test_data_producer.py
# Run the test producer in another terminal:
python3 /tmp/test_data_producer.py
```

**Expected Output from Producer:**
```
🚀 Starting test data producer...
📤 Sent event 1: page_view from us-east
📤 Sent event 2: click from eu-central
📤 Sent event 3: purchase from us-west
📤 Sent event 4: signup from asia-pacific
...
```

### Terminal 2: Start Streaming Job
```bash
cd /home/sanzad/git/DataEngineering/interaction_building_blocks/flink-iceberg/python

# Set FLINK_HOME if not already set
export FLINK_HOME=/home/flink/flink

# Run the streaming job
python3 kafka_to_iceberg_streaming.py
```

**Expected Output from Streaming Job:**
```
🎯 Kafka to Iceberg Streaming Job Starting...
============================================================
🔍 Validating environment...
✅ All Python dependencies available
✅ Environment validation passed
🚀 Setting up Kafka to Iceberg streaming pipeline...
1️⃣ Creating Flink table environment...
✅ Flink table environment created successfully
2️⃣ Setting up Iceberg catalog...
✅ Iceberg catalog 'iceberg_catalog' created and activated
3️⃣ Creating Kafka source table...
✅ Kafka source table 'kafka_events' created for topic 'user-events'
4️⃣ Creating Iceberg sink table...
✅ Iceberg sink table 'lakehouse.streaming_events' created
✅ Pipeline setup completed successfully!
📝 Test data producer script created at /tmp/test_data_producer.py
🎉 Setup completed! Ready to start streaming...
📋 Next steps:
  1. Run test data producer: python3 /tmp/test_data_producer.py
  2. This script will start consuming and streaming to Iceberg
  3. Monitor in Flink Web UI: http://192.168.1.184:8081

▶️  Start streaming now? (y/N): y

📝 Executing streaming SQL:
INSERT INTO streaming_events
SELECT 
    event_id,
    user_id,
    event_type,
    event_time,
    properties,
    region,
    EXTRACT(YEAR FROM event_time) as year,
    EXTRACT(MONTH FROM event_time) as month,
    EXTRACT(DAY FROM event_time) as day,
    EXTRACT(HOUR FROM event_time) as hour
FROM kafka_events

🚀 Flink streaming job started successfully!
📊 Job ID: 00000000000000000000000000000001
🔄 Streaming data from Kafka to Iceberg...
📈 Monitor progress in Flink Web UI: http://192.168.1.184:8081
👀 Monitoring streaming job for 5 minutes...
📊 Job is running... Check Flink Web UI for detailed metrics
🌐 Web UI: http://192.168.1.184:8081
```

## Step 4: Monitor the Job

### Check Flink Web UI
1. Open browser: http://192.168.1.184:8081
2. Navigate to "Running Jobs"
3. Click on your job to see detailed metrics
4. Check task status, throughput, and backpressure

### Check Job Status via CLI
```bash
# List running jobs
/home/flink/flink/bin/flink list

# Expected output:
# Waiting for response...
# ------------------ Running/Restarting Jobs -------------------
# 12345678901234567890 : Flink Streaming Job (RUNNING)
```

## Step 5: Verify Data in Iceberg

### Terminal 3: Run Analytics Script
```bash
cd /home/sanzad/git/DataEngineering/interaction_building_blocks/flink-iceberg/python

# Run analytics to verify data
python3 iceberg_streaming_analytics.py
```

**Expected Output from Analytics:**
```
📊 Iceberg Streaming Analytics Starting...
==================================================
🔧 Setting up analytics environment...
✅ Flink table environment created successfully
✅ Iceberg catalog 'iceberg_catalog' created and activated
✅ Analytics environment ready
⏳ Waiting for streaming data (30 seconds)...
📊 Getting statistics for table: streaming_events
📋 Generating comprehensive analytics report...

================================================================================
📊 ICEBERG STREAMING ANALYTICS REPORT
================================================================================

🎯 TABLE: streaming_events
🌍 REGIONS: 4
⏰ TIME PERIODS: 2 hours

📈 REGION BREAKDOWN:
  us-east      | Events:     25 | Users:   15 | Event Types: 5
  eu-central   | Events:     23 | Users:   12 | Event Types: 4
  us-west      | Events:     22 | Users:   14 | Event Types: 5
  asia-pacific | Events:     20 | Users:   11 | Event Types: 4

⏱️ RECENT HOURLY ACTIVITY:
  2024-12-01 14:00 | Events:     45 | Users:   25
  2024-12-01 15:00 | Events:     45 | Users:   27

🔍 TRINO QUERY STATUS: success
📊 TRINO RESULTS: 10 rows

================================================================================
✅ Report generation completed!

🔄 Start continuous monitoring? (y/N): y
🩺 Starting streaming health monitoring for 10 minutes...
📊 Health check #1
  📈 Total events: 90
  👥 Total unique users: 52
  🌍 Active regions: 4
  🕐 Latest data hour: 2024-12-01 15:00
...
```

### Verify with Trino CLI
```bash
# Connect to Trino
sudo su - trino -c "./trino-cli --server http://192.168.1.184:8084 --catalog iceberg --schema lakehouse"
```

```sql
-- Check table exists
SHOW TABLES;

-- Query streaming data
SELECT 
    region, 
    event_type, 
    count(*) as events,
    count(distinct user_id) as users
FROM streaming_events 
GROUP BY region, event_type 
ORDER BY events DESC;

-- Check partitions
SELECT 
    region, year, month, day, hour,
    count(*) as events
FROM streaming_events 
GROUP BY region, year, month, day, hour
ORDER BY year, month, day, hour;

-- Time travel query
SELECT count(*) FROM "streaming_events$snapshots";
```

**Expected Trino Output:**
```sql
trino:lakehouse> SELECT region, count(*) FROM streaming_events GROUP BY region;
    region    | count
--------------+-------
 us-east      |    25
 eu-central   |    23
 us-west      |    22
 asia-pacific |    20
(4 rows)

Query 20241201_150234_00001_abc123, FINISHED, 3 nodes
Splits: 4 total, 4 done (100.00%)
0:01 [90 rows, 1.2MB] [65 rows/s, 871KB/s]
```

## Step 6: Performance Verification

### Check Kafka Consumer Lag
```bash
# Check consumer group lag
/home/kafka/kafka/bin/kafka-consumer-groups.sh \
    --bootstrap-server 192.168.1.184:9092 \
    --group iceberg-flink-consumer \
    --describe

# Expected: Low or zero lag
```

### Check HDFS Files
```bash
# List Iceberg data files
hadoop fs -ls -R /lakehouse/iceberg/lakehouse/streaming_events/

# Expected: Parquet files organized by partitions
# /lakehouse/iceberg/lakehouse/streaming_events/data/region=us-east/year=2024/month=12/day=01/hour=15/
```

### Check File Sizes and Counts
```bash
# Get file statistics
hadoop fs -du -h /lakehouse/iceberg/lakehouse/streaming_events/
```

**Expected Output:**
```
2.1 M   /lakehouse/iceberg/lakehouse/streaming_events/data
1.2 K   /lakehouse/iceberg/lakehouse/streaming_events/metadata
```

## Step 7: Stop the Job

### Graceful Job Stop
```bash
# List running jobs
/home/flink/flink/bin/flink list

# Stop specific job (replace with actual job ID)
/home/flink/flink/bin/flink stop 12345678901234567890

# Or cancel immediately
/home/flink/flink/bin/flink cancel 12345678901234567890
```

### Stop Data Producer
```bash
# In the producer terminal, press Ctrl+C
# Expected: ⚠️ Producer stopped by user
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Cannot connect to Hive Metastore"
```bash
# Check Hive Metastore service
sudo systemctl status hive-metastore

# Check port accessibility
telnet 192.168.1.184 9083
```

#### Issue: "Kafka topic not found"
```bash
# Create the topic
/home/kafka/kafka/bin/kafka-topics.sh \
    --bootstrap-server 192.168.1.184:9092 \
    --topic user-events \
    --create \
    --partitions 3 \
    --replication-factor 2
```

#### Issue: "JAR file not found"
```bash
# Copy JARs to all Flink nodes
sudo cp /home/sanzad/iceberg-distributed/libs/*.jar /home/flink/flink/lib/
sudo systemctl restart flink-taskmanager
```

#### Issue: "HDFS connection refused"
```bash
# Check HDFS status
hadoop fs -ls /

# Start HDFS if needed
$HADOOP_HOME/sbin/start-dfs.sh
```

### Log Locations
- **Flink Logs**: `/home/flink/flink/log/`
- **Streaming Job Logs**: `/tmp/flink_iceberg_streaming.log`
- **TaskManager Logs**: `/home/flink/flink/log/flink-*-taskexecutor-*.log`
- **JobManager Logs**: `/home/flink/flink/log/flink-*-jobmanager-*.log`

### Performance Expectations

**Throughput**: 
- Should process 100+ events/second
- Latency: < 5 seconds from Kafka to Iceberg
- Memory usage: < 1GB per TaskManager

**Data Quality**:
- Zero data loss (exactly-once processing)
- Proper partitioning by region/time
- Schema evolution support

## Success Criteria

✅ **Streaming Job Running**: Flink job shows RUNNING status
✅ **Data Flowing**: New events appear in Iceberg table
✅ **Partitioning Works**: Data properly partitioned by region/time
✅ **Multi-Engine Access**: Both Flink and Trino can query the data
✅ **No Data Loss**: All producer events appear in Iceberg
✅ **Performance**: Consistent throughput with low latency

This completes the comprehensive execution guide for Flink-Iceberg streaming!
