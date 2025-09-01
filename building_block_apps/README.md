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
├── spark/           ← Spark applications (future)
├── flink/           ← Flink streaming jobs (future)
├── postgresql/      ← Database clients and utilities (future)
├── trino/           ← Query engine clients (future)
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
sudo apt install python3-pip default-jdk librdkafka-dev

# Install Python Kafka client
pip install kafka-python
```

### **Build Everything**
```bash
# From the building_block_apps directory
bazel build //...
```

### **Run Examples**
```bash
# Python Kafka Producer
bazel run //kafka/python:producer -- --topic test-topic --count 100

# Java Kafka Consumer  
bazel run //kafka/java:Consumer -- --topic test-topic --group my-group

# C++ Kafka Producer
bazel run //kafka/cpp:producer -- --topic test-topic --rate 5.0
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

### 🔜 **Planned Components**

#### **Flink** (Coming Soon)
- **DataStream API**: Low-level streaming processing
- **Table API/SQL**: High-level streaming analytics
- **CEP (Complex Event Processing)**: Pattern detection
- **Connectors**: Kafka, PostgreSQL, Elasticsearch

#### **PostgreSQL** (Coming Soon)
- **CRUD Operations**: Basic database operations
- **Advanced Queries**: Window functions, CTEs, JSON operations
- **Connection Pooling**: Production-ready connection management
- **Change Data Capture**: Logical replication clients

#### **Trino** (Coming Soon)
- **Federated Queries**: Cross-system query examples  
- **Connector Usage**: Kafka, Delta Lake, Iceberg
- **Performance Optimization**: Query tuning and analysis
- **Custom Functions**: UDFs and aggregates

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
# Build all Kafka examples
bazel build //kafka:all_kafka_examples

# Build specific language
bazel build //kafka/python:all_python_examples
bazel build //kafka/java:all_java_examples  
bazel build //kafka/cpp:all_cpp_examples

# Run with arguments
bazel run //kafka/python:producer -- --help

# Clean build artifacts
bazel clean

# Test (when tests are added)
bazel test //kafka/...
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

### **Kafka Cluster Configuration**
Examples are pre-configured for the distributed Kafka setup from [`02_kafka_distributed_setup.md`](../setup_guide/02_kafka_distributed_setup.md):

```properties
# Bootstrap servers
192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092

# Default topic
building-blocks-demo

# Consumer group
building-blocks-consumer-group
```

### **Customizing Configuration**
Each language provides configuration utilities:

**Python**: `kafka_common.py` - `get_kafka_config()`  
**Java**: `KafkaCommon.java` - `getProducerConfig()`, `getConsumerConfig()`  
**C++**: `kafka_common.h` - `KafkaConfig::getProducerConfig()`

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
```bash
# Terminal 1: Start consumer
bazel run //kafka/java:Consumer -- --topic e2e-test --group test-group

# Terminal 2: Send messages  
bazel run //kafka/python:producer -- --topic e2e-test --count 50 --rate 2

# Terminal 3: Monitor with C++ consumer
bazel run //kafka/cpp:consumer -- --topic e2e-test --group monitor-group --timeout 60
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

### **Phase 1: Core Components** (Next 2-3 months)
- ✅ Kafka (Complete)
- 🔄 Spark (In Progress)
- 🔄 Flink (In Progress)  
- 🔄 PostgreSQL (In Progress)

### **Phase 2: Advanced Components** (3-6 months)
- Trino query engine
- Redis caching
- Neo4j graph database
- TimescaleDB time series

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
