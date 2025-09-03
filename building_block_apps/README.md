# Building Block Applications

## Overview

This directory contains **building block applications** that demonstrate how to work with individual data engineering components using **Bazel** as a unified build system. Each component provides examples in multiple programming languages (Python, Java, C++) with consistent interfaces and comprehensive documentation.

The building blocks serve as the foundation for the advanced application ideas described in [`12_application_ideas_medium_to_advanced.md`](../setup_guide/12_application_ideas_medium_to_advanced.md).

## 🏗️ **Architecture Philosophy**

### **Language-Agnostic Approach**
- **Bazel Build System**: Uniform build commands across all languages
- **Consistent APIs**: Similar interfaces and patterns across implementations  
- **Cross-Language Learning**: Compare implementations to understand language-specific optimizations
- **Production Ready**: Include proper error handling, monitoring, and configuration

### **Component-Based Structure**
```
building_block_apps/
├── kafka/           ← Kafka producers/consumers in Python, Java, C++
├── spark/           ← Spark batch processing and streaming (complete)
├── flink/           ← Flink streaming jobs and analytics (complete)
├── postgresql/      ← Database operations and advanced queries (complete)
├── trino/           ← Federated queries and performance analysis (complete)
├── redis/           ← Caching, pub/sub, and Redis operations (complete)
├── cassandra/       ← NoSQL wide-column store operations (complete)
└── integration/     ← Multi-component examples (future)
```

---

## 🚀 **Quick Start**

### **Prerequisites**
```bash
# Install Bazel
sudo apt update
sudo apt install bazel

# Install language-specific dependencies
sudo apt install python3-pip default-jdk librdkafka-dev postgresql-client

# Install Python libraries for all components
pip install kafka-python psycopg2-binary redis hiredis trino requests cassandra-driver
```

### **Build Everything**
```bash
# From the building_block_apps directory
bazel build //...
```

### **Run Examples**
```bash
# Kafka: Python Producer
bazel run //kafka/python:producer -- --topic test-topic --count 100

# Spark: Batch Processing
bazel run //spark/python:batch_processing -- --records 10000 --master spark://192.168.1.184:7077

# Flink: Streaming Analytics
bazel run //flink/python:streaming_analytics -- --kafka-topic events --duration 60

# PostgreSQL: Basic Database Operations
bazel run //postgresql/python:basic_operations -- --create-tables --insert-data

# Trino: Federated Queries
bazel run //trino/python:federated_queries -- --include-all

# Redis: Basic Caching
bazel run //redis/python:basic_caching -- --operations all

# Cassandra: Basic Operations
bazel run //cassandra/python:basic_operations -- --create-tables --insert-data
```

---

## 📦 **Available Components**

### ✅ **Kafka (Complete)**

**Languages**: Python, Java, C++  
**Build Targets**: `//kafka/python:*`, `//kafka/java:*`, `//kafka/cpp:*`

#### **Features**
- **Producer Examples**: Configurable message generation with delivery confirmation
- **Consumer Examples**: Message processing with offset management and error handling
- **Performance Monitoring**: Real-time statistics and throughput measurement
- **Error Handling**: Comprehensive error handling and graceful shutdown
- **Configuration**: Production-ready settings with reasonable defaults

#### **Quick Examples**

**Producer (Python)**:
```bash
# Send 1000 messages at 10 messages/second
bazel run //kafka/python:producer -- \
    --topic building-blocks-demo \
    --count 1000 \
    --rate 10
```

**Consumer (Java)**:
```bash
# Consume for 60 seconds
bazel run //kafka/java:Consumer -- \
    --topic building-blocks-demo \
    --group java-consumer-group \
    --timeout 60
```

**Producer (C++)**:
```bash
# Send messages with no rate limit
bazel run //kafka/cpp:producer -- \
    --topic building-blocks-demo \
    --count 500 \
    --rate 0
```

#### **Message Format**
All examples use a consistent JSON message format:
```json
{
  "id": 123,
  "type": "producer_demo",
  "timestamp": 1693478400000,
  "data": {
    "user_id": "user_123",
    "action": "view_product",
    "product_id": "product_23",
    "session_id": "session_12",
    "value": 123.45
  },
  "metadata": {
    "source": "python_producer",
    "version": "1.0",
    "environment": "development"
  }
}
```

---

### ✅ **Spark (Complete)**

**Languages**: Python, Java, C++  
**Build Targets**: `//spark/python:*`, `//spark/java:*`, `//spark/cpp:*`

#### **Features**
- **Batch Processing**: Complete ETL workflows with data transformations, aggregations, and quality checks
- **Structured Streaming**: Real-time Kafka stream processing with windowing and watermarks
- **SQL Analytics**: Complex queries with CTEs, window functions, and statistical analysis
- **ETL Pipelines**: Multi-source data integration with comprehensive validation
- **Performance Monitoring**: Metrics tracking and optimization techniques
- **Multiple Formats**: Parquet, CSV, JSON output with partitioning strategies

#### **Quick Examples**

**Batch Processing (Python)**:
```bash
# Process 50K records with comprehensive analytics
bazel run //spark/python:batch_processing -- \
    --records 50000 \
    --output-path /tmp/spark-batch \
    --master spark://192.168.1.184:7077
```

**Streaming (Java)**:
```bash
# Real-time Kafka stream processing for 5 minutes
bazel run //spark/java:Streaming -- \
    --kafka-topic real-time-events \
    --duration 300 \
    --output-path /tmp/spark-streaming
```

**ETL Pipeline (C++)**:
```bash
# Multi-stage ETL with data quality validation
bazel run //spark/cpp:etl_pipeline -- \
    --records 100000 \
    --output-path /tmp/spark-etl
```

**SQL Analytics (Python)**:
```bash
# Advanced SQL queries with window functions
bazel run //spark/python:sql_queries -- \
    --records 75000 \
    --output-path /tmp/spark-sql
```

#### **Integration with Existing Setup**
All Spark examples are pre-configured for the distributed Spark cluster from [`03_spark_cluster_setup.md`](../setup_guide/03_spark_cluster_setup.md):

```properties
# Spark cluster configuration
spark.master=spark://192.168.1.184:7077
spark.executor.memory=2g
spark.executor.cores=2

# Integration points
kafka.servers=192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
output.warehouse=/home/spark/spark/warehouse
checkpoint.dir=/tmp/spark-checkpoints
```

#### **Architecture Comparison**
- **Python**: Rapid development, rich ecosystem, DataFrame API
- **Java**: Production robustness, type safety, enterprise integration  
- **C++**: High-performance data generation, system integration, Spark job orchestration

### ✅ **Flink (Complete)**

**Languages**: Python, Java, C++  
**Build Targets**: `//flink/python:*`, `//flink/java:*`, `//flink/cpp:*`

#### **Features**
- **DataStream API**: Low-level streaming processing with stateful operations
- **Table API/SQL**: High-level streaming analytics and complex queries
- **CEP (Complex Event Processing)**: Pattern detection and event correlations  
- **Windowing**: Tumbling, sliding, and session windows with watermarks
- **State Management**: Checkpoint/savepoint support and fault tolerance
- **Connectors**: Kafka, PostgreSQL, Elasticsearch integration

#### **Quick Examples**

**Streaming Analytics (Python)**:
```bash
# Real-time event processing with windowing
bazel run //flink/python:streaming_analytics -- \
    --kafka-topic user-events \
    --duration 300 \
    --parallelism 4
```

**Windowing Aggregations (Java)**:
```bash
# Tumbling window aggregations
bazel run //flink/java:StreamingAnalytics -- \
    --window-size 60 \
    --kafka-topic metrics
```

**SQL Streaming (Python)**:
```bash
# SQL-based stream processing
bazel run //flink/python:sql_streaming -- \
    --query-type aggregation \
    --duration 180
```

---

### ✅ **PostgreSQL (Complete)**

**Languages**: Python, Java, C++  
**Build Targets**: `//postgresql/python:*`, `//postgresql/java:*`, `//postgresql/cpp:*`

#### **Features**
- **CRUD Operations**: Comprehensive database operations with transactions
- **Advanced Queries**: Window functions, CTEs, JSON operations, complex joins
- **Connection Pooling**: Production-ready connection management
- **Data Types**: JSON/JSONB, arrays, custom types, and PostgreSQL extensions
- **Performance Monitoring**: Query analysis and optimization techniques
- **Bulk Operations**: Efficient batch processing and data import/export

#### **Quick Examples**

**Basic Operations (Python)**:
```bash
# Complete CRUD operations with sample data
bazel run //postgresql/python:basic_operations -- \
    --create-tables --insert-data \
    --operations all
```

**Advanced Queries (Python)**:
```bash
# Complex analytical queries and window functions
bazel run //postgresql/python:advanced_queries -- \
    --include-analytics --include-json
```

**Connection Management (Java)**:
```bash
# Connection pooling and performance testing
bazel run //postgresql/java:AdvancedQueries -- \
    --pool-size 10 --benchmark
```

---

### ✅ **Trino (Complete)**

**Languages**: Python, Java, C++  
**Build Targets**: `//trino/python:*`, `//trino/java:*`, `//trino/cpp:*`

#### **Features**
- **Federated Queries**: Cross-system analytics (PostgreSQL + Kafka + Iceberg + Delta Lake)
- **Connector Usage**: Native integration with all your data sources
- **Performance Analysis**: Query optimization and cluster monitoring
- **Advanced Analytics**: Window functions, CTEs, statistical analysis
- **Interactive Queries**: Sub-second response times for exploration
- **Cost-Based Optimization**: Smart query planning across different systems

#### **Quick Examples**

**Basic Queries (Python)**:
```bash
# Explore catalogs and basic SQL operations
bazel run //trino/python:basic_queries -- \
    --catalog postgresql --schema public
```

**Federated Queries (Python)**:
```bash
# Cross-system joins and analytics
bazel run //trino/python:federated_queries -- \
    --include-all
```

**Performance Analysis (Python)**:
```bash
# Cluster monitoring and query optimization
bazel run //trino/python:performance_analysis -- \
    --include-benchmark --threads 4
```

---

### ✅ **Redis (Complete)**

**Languages**: Python, Java, C++  
**Build Targets**: `//redis/python:*`, `//redis/java:*`, `//redis/cpp:*`

#### **Features**
- **Caching Operations**: High-performance key-value operations with TTL
- **Data Structures**: Strings, hashes, lists, sets, sorted sets, and streams
- **Pub/Sub Messaging**: Real-time messaging and event distribution
- **Advanced Operations**: Lua scripting, transactions, and pipelining
- **Performance Monitoring**: Benchmarking and optimization techniques
- **Connection Pooling**: Efficient connection management

#### **Quick Examples**

**Basic Caching (Python)**:
```bash
# Key-value operations and TTL management
bazel run //redis/python:basic_caching -- \
    --operations all --benchmark
```

**Advanced Operations (Python)**:
```bash
# Data structures and complex operations
bazel run //redis/python:advanced_operations -- \
    --include-all --duration 120
```

**Pub/Sub Messaging (Python)**:
```bash
# Real-time messaging demonstration
bazel run //redis/python:pubsub_messaging -- \
    --channels events,notifications --duration 60
```

---

### ✅ **Cassandra (Complete)**

**Languages**: Python, Java, C++  
**Build Targets**: `//cassandra/python:*`, `//cassandra/java:*`, `//cassandra/cpp:*`

#### **Features**
- **NoSQL Data Modeling**: Wide-column store patterns for scalable data storage
- **Time-Series Operations**: Optimized schemas for time-series data and analytics
- **High-Throughput Writes**: Batch operations and prepared statements for performance
- **Distributed Queries**: Cross-node query execution with load balancing
- **Advanced Data Types**: Collections, UDTs, counters, and TTL support
- **Connection Pooling**: Efficient connection management for high-concurrency applications

#### **Quick Examples**

**Basic Operations (Python)**:
```bash
# Complete CRUD operations with sample data
bazel run //cassandra/python:basic_operations -- \
    --create-tables --insert-data \
    --operations all
```

**Time-Series Operations (Python)**:
```bash
# Time-series data modeling and querying
bazel run //cassandra/python:timeseries_operations -- \
    --time-range 7days --batch-size 1000
```

**Advanced Queries (Java)**:
```bash
# Complex queries with prepared statements
bazel run //cassandra/java:AdvancedQueries -- \
    --query-type analytics --parallelism 4
```

**Performance Testing (Python)**:
```bash
# Benchmark operations for throughput testing
bazel run //cassandra/python:performance_test -- \
    --operations 10000 --batch-size 100 --threads 8
```

#### **Integration with Existing Setup**
All Cassandra examples are pre-configured for the distributed Cassandra cluster from [`15_cassandra_distributed_setup.md`](../setup_guide/15_cassandra_distributed_setup.md):

```properties
# Cassandra cluster configuration
cassandra.hosts=192.168.1.184,192.168.1.187,192.168.1.190
cassandra.port=9042
cassandra.keyspace=homelab_analytics

# Load balancing and performance
cassandra.load_balancing=DCAwareRoundRobinPolicy
cassandra.consistency=LOCAL_QUORUM
cassandra.max_connections_per_host=8
```

#### **Data Modeling Patterns**
- **Wide-Row Pattern**: Efficient storage for user timelines and activity logs
- **Time-Series Pattern**: Optimized schemas for metrics and event data
- **Counter Pattern**: Distributed counters for real-time analytics
- **Materialized Views**: Denormalized views for query optimization

#### **Architecture Comparison**
- **Python**: Rapid development with cassandra-driver, ideal for analytics
- **Java**: Production robustness with DataStax driver, enterprise integration
- **C++**: High-performance applications, system-level integration

### 🔜 **Planned Components**

#### **Neo4j** (Coming Soon)
- **Graph Operations**: Node and relationship management
- **Cypher Queries**: Complex graph traversal and pattern matching
- **Graph Analytics**: PageRank, community detection, shortest paths
- **Data Import**: Bulk loading and graph construction

#### **Elasticsearch** (Coming Soon)
- **Document Indexing**: Full-text search and document operations
- **Complex Queries**: Aggregations, filters, and search analytics
- **Real-time Search**: Live indexing and search capabilities
- **Performance Tuning**: Index optimization and query analysis

---

## 🛠️ **Build System Details**

### **Bazel Advantages**
- **Incremental Builds**: Only rebuild what changed
- **Reproducible**: Hermetic builds with exact dependencies
- **Scalable**: Efficient parallel builds
- **Language Agnostic**: Same commands for Python, Java, C++
- **Remote Caching**: Share build artifacts across team (future)

### **Common Build Commands**

```bash
# Build all examples for a component
bazel build //kafka:all_kafka_examples
bazel build //spark:all_spark_examples
bazel build //flink:all_flink_examples
bazel build //postgresql:all_postgresql_examples
bazel build //trino:all_trino_examples
bazel build //redis:all_redis_examples
bazel build //cassandra:all_cassandra_examples

# Build specific language for a component
bazel build //kafka/python:all_python_examples
bazel build //spark/java:all_java_examples  
bazel build //flink/cpp:all_cpp_examples
bazel build //cassandra/python:all_python_examples

# Run with arguments
bazel run //kafka/python:producer -- --help
bazel run //trino/python:basic_queries -- --help

# Clean build artifacts
bazel clean

# Test (when tests are added)
bazel test //kafka/...
bazel test //postgresql/...
```

### **Development Workflow**

```bash
# 1. Make changes to source code
vim kafka/python/producer.py

# 2. Build and test
bazel build //kafka/python:producer
bazel run //kafka/python:producer -- --topic test --count 5

# 3. Build all affected targets
bazel build //kafka/...

# 4. Integration test with multiple languages
bazel run //kafka/java:Producer -- --topic integration-test --count 100 &
bazel run //kafka/python:consumer -- --topic integration-test --timeout 30
```

---

## 📚 **Learning Path**

### **Beginner (Start Here)**
1. **Kafka Python Examples**: Learn basic producer/consumer patterns
2. **Compare Implementations**: See how Java and C++ solve the same problems
3. **Configuration Deep Dive**: Understand production-ready settings

### **Intermediate**
1. **Performance Tuning**: Optimize throughput and latency
2. **Error Scenarios**: Test failure modes and recovery
3. **Multi-Language Integration**: Mix language examples in pipelines

### **Advanced**  
1. **Custom Configurations**: Adapt examples for specific use cases
2. **Integration Patterns**: Combine with Spark/Flink examples (when available)
3. **Production Deployment**: Scale examples to production workloads

---

## 🔧 **Configuration**

### **Cluster Configuration**
Examples are pre-configured for your distributed cluster setup:

#### **Kafka Configuration**
From [`02_kafka_distributed_setup.md`](../setup_guide/02_kafka_distributed_setup.md):
```properties
# Bootstrap servers
192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092
# Default topic
building-blocks-demo
# Consumer group
building-blocks-consumer-group
```

#### **Spark Configuration** 
From [`03_spark_cluster_setup.md`](../setup_guide/03_spark_cluster_setup.md):
```properties
# Master URL
spark.master=spark://192.168.1.184:7077
# Resource allocation
spark.executor.memory=2g
spark.executor.cores=2
```

#### **Flink Configuration**
From [`04_flink_cluster_setup.md`](../setup_guide/04_flink_cluster_setup.md):
```properties
# JobManager
jobmanager.rpc.address=192.168.1.184
jobmanager.rpc.port=6123
# Web UI
rest.address=192.168.1.184
rest.port=8081
```

#### **PostgreSQL Configuration**
From [`01_postgresql_setup.md`](../setup_guide/01_postgresql_setup.md):
```properties
# Connection settings
host=192.168.1.184
port=5432
database=analytics_db
user=dataeng
```

#### **Trino Configuration**
From [`05_trino_cluster_setup.md`](../setup_guide/05_trino_cluster_setup.md):
```properties
# Coordinator
coordinator.host=192.168.1.184
coordinator.port=8084
# Catalogs: postgresql, kafka, memory, tpch
```

#### **Redis Configuration**
From [`10_redis_setup.md`](../setup_guide/10_redis_setup.md):
```properties
# Redis server
host=192.168.1.184
port=6379
# Database selection (0-15)
```

#### **Cassandra Configuration**
From [`15_cassandra_distributed_setup.md`](../setup_guide/15_cassandra_distributed_setup.md):
```properties
# Cassandra cluster
hosts=192.168.1.184,192.168.1.187,192.168.1.190
port=9042
keyspace=homelab_analytics
# Load balancing and consistency
consistency_level=LOCAL_QUORUM
```

### **Customizing Configuration**
Each component provides configuration utilities in all languages:

**Kafka**: `kafka_common.py/java/cpp` - Connection and producer/consumer configs  
**Spark**: `spark_common.py/java/cpp` - Cluster and application configs  
**Flink**: `flink_common.py/java/cpp` - Job and cluster configurations  
**PostgreSQL**: `postgresql_common.py/java/cpp` - Database connection pooling  
**Trino**: `trino_common.py/java/cpp` - Catalog and query configurations  
**Redis**: `redis_common.py/java/cpp` - Connection pooling and cache settings  
**Cassandra**: `cassandra_common.py/java/cpp` - Cluster connection and NoSQL patterns

### **Environment-Specific Settings**
```bash
# Development (default)
bazel run //kafka/python:producer

# Custom cluster
# Edit the source files to point to different brokers
# Or use environment variables (future enhancement)
```

---

## 🧪 **Testing & Validation**

### **End-to-End Testing**

#### **Multi-Component Integration**
```bash
# Terminal 1: Start Kafka producer
bazel run //kafka/python:producer -- --topic integration-test --count 1000 --rate 10

# Terminal 2: Process with Flink  
bazel run //flink/python:streaming_analytics -- --kafka-topic integration-test --duration 120

# Terminal 3: Query with Trino
bazel run //trino/python:federated_queries -- --include-kafka

# Terminal 4: Cache results in Redis
bazel run //redis/python:advanced_operations -- --cache-results --ttl 300
```

#### **Single Component Testing**
```bash
# Kafka testing
bazel run //kafka/java:Consumer -- --topic test --group test-group
bazel run //kafka/python:producer -- --topic test --count 100

# PostgreSQL testing
bazel run //postgresql/python:basic_operations -- --create-tables --operations all

# Redis testing
bazel run //redis/python:basic_caching -- --benchmark --operations all

# Cassandra testing
bazel run //cassandra/python:basic_operations -- --create-tables --operations all
```

### **Performance Testing**
```bash
# High throughput test
bazel run //kafka/java:Producer -- --topic perf-test --count 10000 --rate 0

# Measure consumption rate
bazel run //kafka/cpp:consumer -- --topic perf-test --group perf-group --timeout 30
```

### **Integration Testing**
```bash
# Test with actual Kafka setup
cd ../setup_guide
# Follow 02_kafka_distributed_setup.md to start Kafka

# Then run building block examples
cd ../building_block_apps
bazel run //kafka/python:producer -- --topic test --count 100
```

---

## 🚀 **Future Roadmap**

### **Phase 1: Core Components** ✅ **COMPLETED**
- ✅ Kafka (Complete)
- ✅ Spark (Complete)
- ✅ Flink (Complete)  
- ✅ PostgreSQL (Complete)
- ✅ Trino (Complete)
- ✅ Redis (Complete)
- ✅ Cassandra (Complete)

### **Phase 2: Advanced Components** (Next 3-6 months)
- Neo4j graph database
- Elasticsearch search engine
- TimescaleDB time series
- Apache Airflow workflows

### **Phase 3: Integration Examples** (6-12 months)
- Multi-component pipelines
- End-to-end applications from [`12_application_ideas_medium_to_advanced.md`](../setup_guide/12_application_ideas_medium_to_advanced.md)
- Performance benchmarking
- Production deployment guides

### **Phase 4: Advanced Features** (12+ months)
- Automated testing framework
- CI/CD integration
- Monitoring and observability
- Container deployment
- Kubernetes operators

---

## 🤝 **Contributing**

### **Adding New Components**
1. Create directory: `mkdir my_component`
2. Add language subdirectories: `mkdir my_component/{python,java,cpp}`
3. Create BUILD.bazel files for each language
4. Implement examples following Kafka pattern
5. Update this README

### **Adding New Languages**
1. Add language support to root WORKSPACE
2. Create language subdirectory in existing components
3. Implement examples with consistent APIs
4. Add build rules and documentation

### **Code Standards**
- **Error Handling**: Comprehensive error handling in all examples
- **Documentation**: Inline comments and usage examples
- **Configuration**: Consistent configuration patterns
- **Monitoring**: Include basic metrics and logging
- **Testing**: Include validation and testing instructions

---

## 📖 **Additional Resources**

### **Setup Guides**
- [Kafka Distributed Setup](../setup_guide/02_kafka_distributed_setup.md)
- [Spark Cluster Setup](../setup_guide/03_spark_cluster_setup.md)
- [Flink Cluster Setup](../setup_guide/04_flink_cluster_setup.md)

### **Application Ideas**
- [Medium to Advanced Applications](../setup_guide/12_application_ideas_medium_to_advanced.md)

### **Architecture Guides**
- [Kafka Architecture Guide](../architecture/kafka_architecture_guide.md)

### **External Documentation**
- [Bazel Documentation](https://bazel.build/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [librdkafka Documentation](https://github.com/edenhill/librdkafka)

---

## 💡 **Tips & Best Practices**

### **Development Tips**
- Use `bazel run` for development, `bazel build` for CI/CD
- Start with Python examples (easier to understand), then explore Java/C++
- Use consistent topic names across languages for integration testing
- Monitor resource usage during high-throughput tests

### **Production Considerations**
- Adjust batch sizes and timeouts for your workload
- Implement proper logging and monitoring
- Use connection pooling for high-frequency applications
- Consider using schema registry for complex message formats

### **Performance Optimization**
- C++ generally provides highest throughput
- Java offers good balance of performance and ease of use
- Python is best for rapid prototyping and integration
- Use appropriate serialization formats (Avro, Protobuf) for production

Remember: These examples are **building blocks**. Combine them to create sophisticated data engineering applications as described in the [application ideas guide](../setup_guide/12_application_ideas_medium_to_advanced.md)!
