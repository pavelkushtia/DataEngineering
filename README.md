# DataEngineering HomeLab

Full Data Engineering Setup in the HomeLab featuring Iceberg, Delta Lake, PostgreSQL, Kafka, Flink, Spark, Trino (Presto) and comprehensive example applications leveraging the capabilities of these systems.

## 🏗️ Architecture Overview

This project provides a complete data engineering ecosystem deployed across multiple nodes in a home lab environment:

### Infrastructure Layout
- **cpu-node1** (192.168.1.184): Primary coordinator node
  - PostgreSQL Primary + Feast Registry
  - Redis Master (caching & feature serving)
  - Kafka Broker 1
  - Spark Master
  - Flink JobManager
  - Trino Coordinator
  
- **cpu-node2** (192.168.1.187): Secondary processing node
  - PostgreSQL Replica (optional)
  - Redis Replica
  - Neo4j Graph Database
  - Kafka Broker 2  
  - Spark Worker 1
  - Flink TaskManager 1
  - Trino Worker 1
  
- **worker-node3** (192.168.1.190): Additional capacity (overflow)
  - Kafka Broker 3
  - Flink TaskManager 2
  - Trino Worker 2
  - Neo4j Replica (optional)
  
- **worker-node4** (192.168.1.191): Additional capacity (overflow)
  - Available for scaling when needed

- **gpu-node** (192.168.1.79): ML & AI processing node
  - NVIDIA RTX 2060 Super GPU
  - TensorFlow + PyTorch
  - Spark MLlib with GPU acceleration
  - Jupyter Lab + MLflow
  - Model serving APIs

### Technology Stack
- **Storage Layer**: PostgreSQL, Delta Lake, Apache Iceberg, Neo4j Graph DB
- **Caching & Features**: Redis, Feast Feature Store
- **Message Streaming**: Apache Kafka (3-node cluster)
- **Batch Processing**: Apache Spark (distributed cluster)
- **Stream Processing**: Apache Flink (JobManager + TaskManagers)
- **Query Engine**: Trino (formerly Presto) for federated queries
- **ML & AI**: TensorFlow, PyTorch, Spark MLlib, MLflow, CUDA
- **Data Formats**: Parquet, Avro, JSON, Graph formats
- **Orchestration**: Built-in schedulers + custom workflows

## 📁 **Repository Structure**

```
DataEngineering/
├── building_block_apps/     ← 🧱 Language-agnostic examples (Python, Java, C++)
│   ├── kafka/              ← Complete Kafka producer/consumer examples
│   ├── spark/              ← Complete Spark batch, streaming, SQL, ETL examples
│   ├── flink/              ← Coming soon: Flink streaming jobs
│   └── postgresql/         ← Coming soon: Database clients
├── setup_guide/            ← 📚 Step-by-step deployment guides
├── architecture/           ← 🏗️ In-depth architecture documentation
└── README.md              ← You are here!
```

## 🏗️ Architecture Guides

For in-depth understanding of distributed system architectures:

- **[Kafka Architecture Guide](architecture/kafka_architecture_guide.md)** - Comprehensive guide to your 3-node Kafka setup with scaling strategies
- **[Spark Architecture Guide](architecture/spark_architecture_guide.md)** - Complete Spark distributed architecture from basics to advanced optimization

---

## 🧱 **Building Block Applications**

Before diving into complex end-to-end applications, master the fundamentals with our **language-agnostic building blocks**:

### **[Building Block Apps](building_block_apps/README.md)** - Foundation Components in Python, Java & C++

**Ready-to-Run Examples with Bazel Build System:**
- **✅ Kafka**: Producers/consumers in Python, Java, C++ with comprehensive error handling
- **✅ Spark**: Batch processing, structured streaming, SQL analytics, ETL pipelines
- **🔄 Flink**: Coming soon - DataStream API, Table API, and complex event processing  
- **🔄 PostgreSQL**: Coming soon - Advanced queries, connection pooling, CDC clients
- **🔄 Trino**: Coming soon - Federated queries and performance optimization

**Why Building Blocks?**
- **Language-Agnostic Learning**: Compare Python simplicity, Java robustness, C++ performance
- **Uniform Build System**: Single `bazel` command for all languages and components  
- **Production-Ready**: Error handling, monitoring, and configuration best practices
- **Foundation for Advanced Apps**: Combine blocks to build the [12 application ideas](setup_guide/12_application_ideas_medium_to_advanced.md)

```bash
# Quick start with building blocks
cd building_block_apps

# Python Kafka producer
bazel run //kafka/python:producer -- --topic demo --count 100

# Java Kafka consumer
bazel run //kafka/java:Consumer -- --topic demo --group my-group

# Python Spark batch processing
bazel run //spark/python:batch_processing -- --records 10000

# C++ Spark ETL pipeline
bazel run //spark/cpp:etl_pipeline -- --records 5000
```

**Learning Path**: Start with building blocks → Master component interactions → Build advanced applications

---

## 📚 Setup Guides

### Core Components Setup
1. **[PostgreSQL Setup](setup_guide/01_postgresql_setup.md)** - Primary database with streaming replication
2. **[Kafka Distributed Setup](setup_guide/02_kafka_distributed_setup.md)** - 3-node Kafka cluster with ZooKeeper
3. **[Spark Cluster Setup](setup_guide/03_spark_cluster_setup.md)** - Distributed Spark with master/worker architecture
4. **[Flink Cluster Setup](setup_guide/04_flink_cluster_setup.md)** - Stream processing with JobManager/TaskManager setup
5. **[Trino Cluster Setup](setup_guide/05_trino_cluster_setup.md)** - Distributed SQL query engine

### Lakehouse Technologies (Local Setup)
6. **[Apache Iceberg Local Setup](setup_guide/06_iceberg_local_setup.md)** - Table format for analytics workloads
7. **[Delta Lake Local Setup](setup_guide/07_deltalake_local_setup.md)** - ACID transactions for data lakes

### Advanced Components
8. **[Neo4j Graph Database Setup](setup_guide/08_neo4j_graph_database_setup.md)** - Graph analytics and social network analysis
9. **[Redis Setup](setup_guide/09_redis_setup.md)** - High-performance caching and real-time analytics
10. **[Feast Feature Store Setup](setup_guide/10_feast_feature_store_setup.md)** - Centralized ML feature management
11. **[GPU ML Setup](setup_guide/11_gpu_ml_setup.md)** - TensorFlow, PyTorch, and Spark MLlib with NVIDIA GPU

### Learning & Projects
12. **[Application Ideas: Medium to Advanced](setup_guide/12_application_ideas_medium_to_advanced.md)** - 12 comprehensive project ideas

## 🚀 Quick Start Guide

### Prerequisites
- 5 machines: 4 CPU nodes + 1 GPU node (physical or virtual)
- SSH access configured between nodes
- At least 4GB RAM per node (8GB recommended for primary nodes, 16GB+ for GPU node)
- 20GB+ free disk space per node (100GB+ for GPU node)
- NVIDIA GPU for ml-enabled features (RTX 2060 Super or better)

### Setup Order
1. **Foundation Layer**: Start with PostgreSQL on cpu-node1
2. **Caching Layer**: Set up Redis cluster (cpu-node1 primary, cpu-node2 replica)
3. **Streaming Layer**: Deploy Kafka cluster (all 3 nodes)
4. **Processing Layer**: Configure Spark and Flink clusters
5. **Query Layer**: Install Trino cluster
6. **Graph Layer**: Set up Neo4j on cpu-node2
7. **Feature Layer**: Deploy Feast Feature Store
8. **ML Layer**: Configure GPU node with TensorFlow, PyTorch, MLflow
9. **Data Lakes**: Set up local Iceberg and Delta Lake environments
10. **Applications**: Begin with project implementations

## 🎯 Learning Path

### Beginner Level
- Complete all component setups
- Understand distributed system concepts
- Work through basic integration examples

### Medium Level  
- **E-commerce Analytics Pipeline**: Real-time user behavior analysis with Redis caching
- **IoT Sensor Platform**: Time-series data processing with GPU-accelerated anomaly detection
- **Customer 360 Platform**: Unified customer view with Feast feature store and ML insights

### Advanced Level
- **Financial Trading Platform**: Low-latency market data processing with graph risk analysis
- **Fraud Detection System**: Multi-layered fraud prevention using Neo4j network analysis
- **MLOps Platform**: Complete ML lifecycle with GPU training and feature serving
- **Social Network Analytics**: Graph-based recommendations and community detection
- **Real-time Personalization**: Feature store-driven personalization with GPU inference

### Expert Level
- **Custom Time Series Database**: High-performance specialized storage with GPU acceleration
- **Global Streaming Platform**: Multi-region event streaming with intelligent routing
- **Event-Driven Microservices**: Complete distributed architecture with graph workflows
- **AI-Powered Graph Analytics**: Advanced ML models on graph data structures
- **Federated Learning Platform**: Distributed ML training across multiple nodes

## 🛠️ Key Features Implemented

### Data Processing Capabilities
- **Real-time Stream Processing**: Kafka + Flink for low-latency processing
- **Batch Processing**: Spark for large-scale data transformations  
- **GPU-Accelerated ML**: TensorFlow, PyTorch with CUDA support
- **Federated Queries**: Trino for cross-system analytics
- **Graph Analytics**: Neo4j for network and relationship analysis
- **ACID Transactions**: Delta Lake for reliable data lakes
- **Schema Evolution**: Iceberg for flexible table formats

### Integration Patterns
- **Change Data Capture (CDC)**: PostgreSQL → Kafka → Data Lake
- **Lambda Architecture**: Batch and stream processing combined
- **Lakehouse Architecture**: Best of data lakes and warehouses
- **Event-Driven Architecture**: Microservices with event streaming
- **Feature Store Pattern**: Centralized ML feature management with Feast
- **Graph-Relational Integration**: Seamless data flow between SQL and graph systems

### ML & AI Capabilities
- **Feature Engineering**: Automated feature pipelines with caching
- **Model Training**: Distributed training across CPU and GPU nodes
- **Model Serving**: Real-time inference APIs with load balancing
- **Experiment Tracking**: MLflow for versioning and reproducibility
- **A/B Testing**: Feature flag-driven experimentation framework

### Operational Excellence
- **High Availability**: Multi-node redundancy across all components
- **Scalability**: Horizontal scaling from CPU to GPU workloads
- **Performance Optimization**: Redis caching and GPU acceleration
- **Monitoring**: Built-in observability across the entire stack
- **Security**: Network isolation, authentication, and encryption
- **Backup & Recovery**: Comprehensive data protection and disaster recovery

## 📊 Use Cases Covered

### Business Intelligence & Analytics
- Real-time dashboards with Redis-backed caching
- Customer analytics and behavioral segmentation  
- Sales performance tracking with graph relationship analysis
- Operational metrics monitoring across distributed systems

### Machine Learning & AI
- Feature engineering pipelines with Feast feature store
- GPU-accelerated model training (TensorFlow/PyTorch)
- Real-time model serving and inference
- A/B testing frameworks with feature flags
- Recommendation systems with hybrid approaches
- Deep learning for computer vision and NLP

### Graph Analytics & Network Intelligence
- Social network analysis and community detection
- Fraud detection through network pattern analysis
- Supply chain optimization and risk assessment
- Knowledge graphs for entity relationship mapping
- Influence analysis and viral coefficient tracking

### Advanced Analytics
- Time-series forecasting with GPU acceleration
- Anomaly detection using unsupervised learning
- Natural language processing and sentiment analysis
- Computer vision for image and video analysis
- Reinforcement learning for optimization problems

### Operational Analytics  
- Application monitoring with distributed tracing
- Infrastructure metrics with GPU utilization tracking
- Log analysis and alerting with ML-powered insights
- Performance optimization using predictive analytics

### Compliance & Governance
- Data lineage tracking across all systems
- Feature store governance and versioning
- Schema registry management with evolution tracking
- Model governance and explainability
- GDPR compliance with data masking and deletion
- Audit trail maintenance across ML lifecycle

## 🔧 Advanced Topics Covered

### Performance Optimization
- Query optimization across SQL and graph databases
- GPU memory management and CUDA optimization
- Redis caching strategies and cache warming
- Partitioning strategies for massive datasets
- Index optimization for graph traversals
- Model inference optimization and batching

### Data Governance & MLOps
- Schema evolution patterns across all storage systems
- Feature store governance and lineage tracking
- Model versioning and experiment management
- Data catalog implementation with graph relationships
- Metadata management across heterogeneous systems
- Access control policies for ML and graph data

### Scalability & Architecture Patterns
- Horizontal scaling from CPU to GPU workloads
- Load balancing for model serving and feature retrieval
- Resource allocation optimization across diverse workloads
- Auto-scaling strategies for ML training and inference
- Multi-tenancy patterns for shared infrastructure
- Cost management techniques across cloud and on-premise

### Integration & Interoperability
- Cross-system data movement and transformation
- Real-time feature synchronization strategies
- Graph-relational data integration patterns  
- Stream-batch processing unification
- Model artifact management and deployment
- API design for ML and graph services

## 🤝 Contributing

This is a learning-focused project. Feel free to:
- Suggest improvements to setup guides
- Share additional application ideas
- Report issues with configurations
- Contribute example implementations

## 📝 Documentation Structure

Each setup guide includes:
- **Prerequisites**: What you need before starting
- **Step-by-step Instructions**: Detailed setup process
- **Configuration Examples**: Production-ready configurations
- **Testing Procedures**: Validation and troubleshooting
- **Integration Examples**: How components work together
- **Performance Tuning**: Optimization recommendations
- **Monitoring & Maintenance**: Operational considerations

## 🎓 Certification Alignment

The projects align with industry certifications:

### Core Data Engineering
- **Confluent Certified Developer** (Kafka)
- **Databricks Certified Associate** (Spark)  
- **AWS/GCP/Azure Data Engineering** certifications
- **CDMP** (Data Management Professional)

### Machine Learning & AI
- **TensorFlow Developer Certificate**
- **AWS Certified Machine Learning - Specialty**
- **Google Professional Machine Learning Engineer**
- **Microsoft Azure AI Engineer Associate**
- **NVIDIA Deep Learning Institute Certifications**

### Specialized Technologies
- **Neo4j Certified Professional** (Graph Databases)
- **Redis Certified Developer** (In-Memory Data Structures)
- **Docker Certified Associate** (Containerization)
- **Kubernetes Application Developer (CKAD)**
- **Apache Airflow Certification** (Workflow Orchestration)

## 🌟 Why This Approach?

### Hands-on Learning
- Learn by building real systems
- Understand component interactions
- Gain operational experience
- Develop troubleshooting skills

### Industry Relevance  
- Use production-grade technologies
- Follow best practices and patterns
- Address real-world challenges
- Build portfolio-worthy projects

### Comprehensive Coverage
- Full data engineering lifecycle from ingestion to serving
- Multiple processing paradigms (batch, stream, graph, ML)
- Various storage patterns (relational, NoSQL, graph, lakehouse)
- Integration with cutting-edge ML and AI technologies
- Feature store and MLOps best practices

### Scalable Architecture
- Start simple, add complexity gradually
- Modular component design with clear interfaces
- Easy to extend from CPU to GPU workloads  
- Production deployment ready with monitoring
- Cost-effective scaling strategies

### Real-World Relevance
- Industry-standard technology stack
- Patterns used by major tech companies
- Covers emerging trends (feature stores, graph ML, GPU computing)
- Applicable to various domains and use cases
- Portfolio-ready implementations

---

**Ready to begin your advanced data engineering journey? Start with the [PostgreSQL Setup Guide](setup_guide/01_postgresql_setup.md) and progress through the entire ecosystem!**

## 🌟 **What Makes This Setup Unique**

This HomeLab goes beyond traditional data engineering by integrating:
- **GPU-Accelerated ML** with enterprise-grade feature management
- **Graph Analytics** for complex relationship modeling  
- **Real-time Feature Serving** with sub-millisecond latency
- **Multi-Modal Data Processing** across structured, unstructured, and graph data
- **Production-Ready MLOps** with experiment tracking and model governance

Perfect for aspiring data engineers, ML engineers, and data scientists who want hands-on experience with the complete modern data stack!
