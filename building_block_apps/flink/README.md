# Flink Building Block Applications

This directory contains comprehensive Apache Flink examples demonstrating production-ready patterns for real-time stream processing. These building blocks are designed to be adapted and extended for various real-time data processing scenarios in your data engineering projects.

## 🏗️ Architecture Overview

The Flink building blocks are organized into several categories:

```
flink/
├── python/                     # PyFlink implementations
│   ├── flink_common.py          # Shared utilities and configurations
│   ├── streaming_analytics.py   # Real-time analytics with complex processing
│   ├── sql_streaming.py         # Flink SQL declarative stream processing
│   ├── cdc_processing.py        # Change Data Capture processing
│   ├── windowing_aggregations.py # Advanced windowing patterns
│   └── state_management.py      # Sophisticated state management
├── java/                       # Java implementations
│   └── StreamingAnalytics.java  # Core streaming analytics in Java
├── cpp/                        # C++ implementations (placeholder)
└── BUILD.bazel                 # Build configuration
```

## 🚀 Quick Start

### Prerequisites

1. **Flink Cluster**: Running Flink cluster (see `setup_guide/04_flink_cluster_setup.md`)
2. **Kafka**: Running Kafka cluster for data sources/sinks
3. **PostgreSQL**: Database for CDC and analytics storage
4. **Python Dependencies**:
   ```bash
   pip install apache-flink confluent-kafka psycopg2-binary
   ```

### Running Examples

#### 1. Basic Streaming Analytics
```bash
# Python version
bazel run //flink/python:streaming_analytics

# With custom parameters
bazel run //flink/python:streaming_analytics -- \
    --kafka-topic user-events \
    --duration 300 \
    --parallelism 8

# Java version
bazel run //flink/java:StreamingAnalytics
```

#### 2. SQL-Based Stream Processing
```bash
bazel run //flink/python:sql_streaming -- \
    --duration 180 \
    --enable-cdc
```

#### 3. Change Data Capture Processing
```bash
bazel run //flink/python:cdc_processing -- \
    --source-tables users,orders,products \
    --enable-validation \
    --duration 600
```

#### 4. Advanced Windowing
```bash
bazel run //flink/python:windowing_aggregations -- \
    --window-types tumbling,sliding,session,pattern \
    --tumbling-minutes 5 \
    --sliding-minutes 10
```

#### 5. State Management
```bash
bazel run //flink/python:state_management -- \
    --state-types keyed,complex,features \
    --state-ttl 24 \
    --enable-cep
```

## 📊 Building Block Details

### 1. Streaming Analytics (`streaming_analytics.py`)

**Purpose**: Comprehensive real-time event processing with complex analytics

**Key Features**:
- Real-time revenue tracking with 1-minute windows
- User session analysis with timeout handling
- Fraud detection with pattern matching
- Product popularity tracking
- High-value transaction monitoring

**Use Cases**:
- E-commerce real-time analytics
- User behavior analysis
- Fraud detection systems
- Product recommendation engines

**Example Output**:
```json
{
  "window_key": "ELECTRONICS",
  "window_start": 1703123400000,
  "window_end": 1703123460000,
  "total_revenue": 15642.50,
  "order_count": 47,
  "unique_users": 23,
  "avg_order_value": 332.61,
  "max_order_value": 1299.99
}
```

### 2. SQL Streaming (`sql_streaming.py`)

**Purpose**: Declarative stream processing using Flink SQL

**Key Features**:
- Real-time analytics with SQL syntax
- Temporal joins with CDC data
- Multi-sink streaming pipelines
- Complex windowing in SQL
- Data enrichment patterns

**Use Cases**:
- Business analyst-friendly stream processing
- Real-time data warehouse updates
- Multi-table CDC synchronization
- Compliance and audit trails

**Example SQL**:
```sql
INSERT INTO analytics_sink
SELECT 
    TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
    category,
    SUM(price * quantity) as total_revenue,
    COUNT(DISTINCT user_id) as unique_users,
    AVG(price * quantity) as avg_order_value
FROM events_source
GROUP BY 
    TUMBLE(event_time, INTERVAL '1' MINUTE),
    category
```

### 3. CDC Processing (`cdc_processing.py`)

**Purpose**: Real-time Change Data Capture processing for database synchronization

**Key Features**:
- Multi-table CDC from PostgreSQL
- Real-time analytics warehouse updates
- Data quality monitoring and validation
- User lifecycle event detection
- Inventory level monitoring

**Use Cases**:
- Real-time data lake synchronization
- Operational analytics
- Data quality monitoring
- Event-driven architectures

**Data Flow**:
```
PostgreSQL → Debezium → Kafka → Flink CDC → Analytics DB
                                       → Event Streams
                                       → Quality Alerts
```

### 4. Windowing Aggregations (`windowing_aggregations.py`)

**Purpose**: Advanced windowing patterns and custom aggregations

**Key Features**:
- Multiple window types (tumbling, sliding, session, global)
- Custom triggers and evictors
- Multi-level windowing hierarchies
- Pattern detection in windows
- Late data handling strategies

**Use Cases**:
- Time-series analytics
- Session analysis
- Pattern detection
- Trend analysis

**Window Types**:
- **Tumbling**: Non-overlapping fixed-size windows
- **Sliding**: Overlapping windows for smooth aggregations
- **Session**: Dynamic windows based on user activity
- **Global**: Custom trigger-based windows

### 5. State Management (`state_management.py`)

**Purpose**: Sophisticated stateful stream processing patterns

**Key Features**:
- ValueState for user profiles with TTL
- ListState for session event tracking
- MapState for product popularity metrics
- Complex event processing for feature generation
- State evolution and migration patterns

**Use Cases**:
- User profiling and personalization
- Session analytics
- Real-time feature stores
- Complex event processing

**State Types**:
- **ValueState**: Single values per key (user profiles)
- **ListState**: Lists of values (session events)
- **MapState**: Key-value maps (product metrics)
- **BroadcastState**: Shared configuration state

## 🔧 Configuration

### Environment Variables
```bash
export FLINK_HOME="/home/flink/flink"
export KAFKA_SERVERS="192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092"
export POSTGRES_URL="jdbc:postgresql://192.168.1.184:5432/analytics_db"
```

### Flink Configuration
```yaml
# flink-conf.yaml additions for building blocks
state.backend: rocksdb
state.backend.rocksdb.memory.managed: true
state.backend.incremental: true
execution.checkpointing.interval: 10s
execution.checkpointing.timeout: 10min
restart-strategy: fixed-delay
restart-strategy.fixed-delay.attempts: 3
```

### Common Parameters

All applications support these common parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--app-name` | FlinkBuildingBlock | Application name |
| `--parallelism` | 4 | Parallelism level |
| `--duration` | 60 | Runtime duration (seconds) |
| `--kafka-servers` | 192.168.1.184:9092,... | Kafka bootstrap servers |
| `--output-path` | /tmp/flink-output | Output path for results |

## 📈 Monitoring and Metrics

### Flink Web UI
- **URL**: http://192.168.1.184:8081
- **Features**: Job monitoring, metrics, checkpoint status

### Custom Metrics
Each application tracks custom metrics:
- Events processed
- Processing latency
- State size
- Checkpoint duration
- Backpressure indicators

### Kafka Topics for Results
- `analytics-results`: Real-time analytics
- `fraud-alerts`: Fraud detection alerts
- `user-sessions`: Session analytics
- `revenue-metrics`: Revenue tracking
- `inventory-alerts`: Inventory monitoring

## 🔍 Troubleshooting

### Common Issues

1. **OutOfMemoryError**
   ```bash
   # Increase TaskManager memory
   taskmanager.memory.process.size: 4gb
   taskmanager.memory.managed.fraction: 0.6
   ```

2. **Checkpoint Timeouts**
   ```bash
   # Adjust checkpoint settings
   execution.checkpointing.timeout: 15min
   state.backend.rocksdb.checkpoint.transfer.thread.num: 4
   ```

3. **High Latency**
   ```bash
   # Tune network buffers
   taskmanager.network.memory.fraction: 0.2
   taskmanager.network.memory.buffer-timeout: 10ms
   ```

4. **CDC Connection Issues**
   ```sql
   -- Check PostgreSQL replication settings
   SELECT name, setting FROM pg_settings 
   WHERE name IN ('wal_level', 'max_wal_senders', 'max_replication_slots');
   ```

### Debugging Commands

```bash
# Check Flink job status
curl http://192.168.1.184:8081/jobs

# Monitor Kafka topics
kafka-console-consumer.sh --bootstrap-server 192.168.1.184:9092 \
    --topic analytics-results --from-beginning

# Check PostgreSQL CDC slot
SELECT slot_name, active, restart_lsn FROM pg_replication_slots;
```

## 🧪 Testing

### Unit Tests
```bash
# Test common utilities
bazel test //flink/python:flink_common_test

# Test streaming analytics
bazel test //flink/python:streaming_analytics_test
```

### Integration Tests
```bash
# Run with sample data
bazel run //flink/python:streaming_analytics -- \
    --duration 30 \
    --records 1000
```

### Load Testing
```bash
# High-throughput test
bazel run //flink/python:streaming_analytics -- \
    --parallelism 16 \
    --duration 600
```

## 🚀 Production Deployment

### Scaling Guidelines

1. **Small Scale** (< 1K events/sec):
   - Parallelism: 2-4
   - Memory: 2GB per TaskManager
   - Checkpointing: 30s intervals

2. **Medium Scale** (1K-10K events/sec):
   - Parallelism: 8-16
   - Memory: 4GB per TaskManager
   - Checkpointing: 10s intervals

3. **Large Scale** (> 10K events/sec):
   - Parallelism: 32+
   - Memory: 8GB+ per TaskManager
   - Checkpointing: 5s intervals
   - Multiple TaskManagers per node

### Performance Optimization

1. **Operator Chaining**
   ```python
   # Chain compatible operators
   stream.map(...).filter(...).keyBy(...)
   ```

2. **Resource Profiles**
   ```python
   # Use custom resource profiles
   env.set_default_local_parallelism(1)
   ```

3. **State Backend Tuning**
   ```yaml
   state.backend.rocksdb.block.cache-size: 256mb
   state.backend.rocksdb.write-buffer-size: 128mb
   ```

## 📚 Advanced Patterns

### 1. Multi-Stream Joins
```python
# Join streams with different schemas
enriched_stream = orders_stream.connect(users_stream).process(EnrichmentFunction())
```

### 2. Dynamic Configuration
```python
# Broadcast configuration updates
config_stream = env.from_collection([...])
main_stream.connect(config_stream.broadcast(config_descriptor)).process(ConfigurableFunction())
```

### 3. Backpressure Handling
```python
# Monitor and respond to backpressure
stream.map(MapFunction()).set_parallelism(8).set_max_parallelism(16)
```

### 4. Exactly-Once Semantics
```python
# Configure for exactly-once processing
env.get_checkpoint_config().set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)
```

## 🤝 Contributing

To add new building blocks:

1. Create new Python/Java files in appropriate directories
2. Follow existing naming conventions
3. Add comprehensive documentation
4. Include unit tests
5. Update BUILD.bazel files
6. Add examples to this README

## 📖 References

- [Apache Flink Documentation](https://flink.apache.org/docs/)
- [PyFlink Documentation](https://flink.apache.org/docs/stable/api/python/)
- [Flink SQL Documentation](https://flink.apache.org/docs/stable/table/sql/)
- [Flink CDC Documentation](https://ververica.github.io/flink-cdc-connectors/)

## 🏷️ License

These building blocks are part of the DataEngineering project and follow the same license terms.
