# Trino Distributed Architecture Guide

## 🏗️ Your Current 3-Node Trino Setup

This guide explains the Trino architecture based on **your exact setup**:
- **cpu-node1** (192.168.1.184) - Trino Coordinator + Web UI
- **cpu-node2** (192.168.1.187) - Trino Worker 1  
- **worker-node3** (192.168.1.190) - Trino Worker 2

---

## 📚 Table of Contents

1. [What is Trino? (Simple Explanation)](#what-is-trino-simple-explanation)
2. [Your Current Architecture](#your-current-architecture)
3. [Coordinator Architecture](#coordinator-architecture)
4. [Worker Architecture](#worker-architecture)
5. [Query Execution Flow](#query-execution-flow)
6. [Memory Architecture](#memory-architecture)
7. [Connectors Architecture](#connectors-architecture)
8. [Discovery & Communication](#discovery--communication)
9. [Query Planning & Optimization](#query-planning--optimization)
10. [Distributed Joins & Aggregations](#distributed-joins--aggregations)
11. [Security Architecture](#security-architecture)
12. [Scaling Your Setup](#scaling-your-setup)
13. [Performance Tuning](#performance-tuning)
14. [Architecture Changes When Adding Nodes](#architecture-changes-when-adding-nodes)

---

## 🤔 What is Trino? (Simple Explanation)

**Think of Trino like a distributed data query orchestra:**

- **Coordinator** = Orchestra Conductor (plans the music, coordinates everything)
- **Workers** = Orchestra Musicians (execute their assigned parts)
- **Connectors** = Musical Instruments (interface with different data sources)
- **Catalogs** = Sheet Music (metadata about where data lives)
- **Splits** = Musical Measures (chunks of data to process)
- **Stages** = Orchestra Sections (groups of related tasks)
- **Exchanges** = Musical Handoffs (data flowing between stages)

**Why distributed?** Just like an orchestra can play complex symphonies by having specialized musicians, Trino can query massive datasets across different systems by coordinating specialized workers.

**Key Difference from Spark:** Trino is **SQL-only** and **interactive** - built for fast analytics, not batch processing or machine learning.

---

## 🏛️ Your Current Architecture

### Overall System View

**What you have:** A 3-node distributed Trino cluster in Coordinator-Worker architecture.

### **Plain English Explanation:**
- **1 Coordinator** - The "conductor" that plans queries and coordinates execution
- **2 Workers** - The "performers" that actually read data and execute query logic
- **HTTP Communication** - All coordination happens via REST APIs (no SSH needed)
- **Multiple Catalogs** - Can query PostgreSQL, Kafka, memory, and more simultaneously

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Your Trino Cluster                          │
├─────────────────────┬─────────────────────┬─────────────────────────┤
│    cpu-node1        │    cpu-node2        │   worker-node3          │
│   (Coordinator)     │    (Worker 1)       │    (Worker 2)           │
│                     │                     │                         │
│  ┌───────────────┐  │  ┌───────────────┐  │  ┌───────────────────┐  │
│  │ Trino         │  │  │ Trino Worker  │  │  │  Trino Worker     │  │
│  │ Coordinator   │  │  │ - Task Exec   │  │  │  - Task Exec      │  │
│  │ - Query Plan  │  │  │ - Data Proc   │  │  │  - Data Proc      │  │
│  │ - Resource    │  │  │ - Connectors  │  │  │  - Connectors     │  │
│  │   Scheduling  │  │  │ - Memory Mgmt │  │  │  - Memory Mgmt    │  │
│  │ - Web UI:8081 │  │  │ - Exchange    │  │  │  - Exchange       │  │
│  └───────────────┘  │  └───────────────┘  │  └───────────────────┘  │
│                     │                     │                         │
│  ┌───────────────┐  │  ┌───────────────┐  │  ┌───────────────────┐  │
│  │   Catalogs    │  │  │   Catalogs    │  │  │    Catalogs       │  │
│  │ - PostgreSQL  │  │  │ - PostgreSQL  │  │  │  - PostgreSQL     │  │
│  │ - Kafka       │  │  │ - Kafka       │  │  │  - Kafka          │  │
│  │ - Iceberg     │  │  │ - Iceberg     │  │  │  - Iceberg        │  │
│  │ - Delta Lake  │  │  │ - Delta Lake  │  │  │  - Delta Lake     │  │
│  │ - Memory      │  │  │ - Memory      │  │  │  - Memory         │  │
│  │ - TPC-H       │  │  │ - TPC-H       │  │  │  - TPC-H          │  │
│  └───────────────┘  │  └───────────────┘  │  └───────────────────┘  │
│                     │                     │                         │
│  192.168.1.184      │  192.168.1.187      │  192.168.1.190          │
└─────────────────────┴─────────────────────┴─────────────────────────┘
```

### **Network Communication Ports:**
- **8081**: HTTP API & Web UI (primary communication)
- **6123**: Discovery service (optional clustering)
- **8443**: HTTPS (if SSL enabled)

---

## 🎯 Coordinator Architecture

### **Role: The Query Orchestrator**

The Trino Coordinator is the **query brain** that plans, schedules, and monitors all queries but doesn't process data itself.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Trino Coordinator (cpu-node1)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Web UI & API  │    │  Query Planner  │    │  Resource Mgr   │  │
│  │                 │    │                 │    │                 │  │
│  │ • REST API      │    │ • SQL Parsing   │    │ • Memory Pools  │  │
│  │ • Web Interface │    │ • Optimization  │    │ • CPU Allocation│  │
│  │ • Authentication│    │ • Cost Analysis │    │ • Node Discovery│  │
│  │ • Session Mgmt  │    │ • Join Strategy │    │ • Load Balancing│  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │        │
│           └───────────────────────┼───────────────────────┘        │
│                                   │                                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ Query Execution │    │ Metadata Cache  │    │  Fault Tolerance│  │
│  │                 │    │                 │    │                 │  │
│  │ • Stage Creation│    │ • Table Schemas │    │ • Query Retry   │  │
│  │ • Task Assign   │    │ • Partition Info│    │ • Node Failure  │  │
│  │ • Progress Track│    │ • Statistics    │    │ • Graceful Stop │  │
│  │ • Result Collect│    │ • Catalog Cache │    │ • Health Checks │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### **Key Coordinator Components:**

#### **1. Query Parser & Planner**
- **SQL Analysis**: Parses SQL into Abstract Syntax Tree (AST)
- **Semantic Analysis**: Validates tables, columns, types
- **Query Optimization**: Cost-based optimization (CBO)
- **Execution Planning**: Creates distributed execution plan

#### **2. Resource Manager**
- **Memory Management**: Tracks memory usage per query
- **CPU Scheduling**: Distributes tasks across workers
- **Admission Control**: Prevents cluster overload
- **Node Health**: Monitors worker availability

#### **3. Metadata Manager**
- **Catalog Integration**: Connects to multiple data sources
- **Schema Caching**: Caches table definitions for performance
- **Statistics**: Maintains table/column statistics for optimization
- **Security**: Enforces access controls

---

## ⚙️ Worker Architecture

### **Role: The Data Processing Engines**

Trino Workers are the **workhorses** that actually read data from sources and execute query logic.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Trino Worker (cpu-node2/worker-node3)            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Task Executor  │    │  Memory Manager │    │   Data Exchange │  │
│  │                 │    │                 │    │                 │  │
│  │ • Pipeline Exec │    │ • Memory Pools  │    │ • Shuffle Data  │  │
│  │ • Operator Tree │    │ • Spill to Disk │    │ • Network I/O   │  │
│  │ • Thread Mgmt   │    │ • GC Management │    │ • Compression   │  │
│  │ • Page Buffers  │    │ • Buffer Pools  │    │ • Serialization │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│           │                       │                       │        │
│           └───────────────────────┼───────────────────────┘        │
│                                   │                                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │   Connectors    │    │  Local Storage  │    │   Monitoring    │  │
│  │                 │    │                 │    │                 │  │
│  │ • PostgreSQL    │    │ • Temp Files    │    │ • Metrics       │  │
│  │ • Kafka         │    │ • Spill Space   │    │ • Health Checks │  │
│  │ • Iceberg       │    │ • Page Cache    │    │ • Resource Usage│  │
│  │ • Delta Lake    │    │ • File Buffers  │    │ • Task Progress │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### **Key Worker Components:**

#### **1. Task Execution Engine**
- **Pipeline Processing**: Vectorized execution for performance
- **Operator Trees**: Implements joins, aggregations, filters
- **Parallelism**: Multiple threads per worker
- **Memory-Aware**: Tracks memory usage per operation

#### **2. Connector Framework**
- **Plugin Architecture**: Modular connector system
- **Data Source Abstraction**: Uniform interface to different systems
- **Predicate Pushdown**: Pushes filters to data sources
- **Projection Pushdown**: Only reads needed columns

#### **3. Exchange Service**
- **Data Shuffling**: Moves data between query stages
- **Network Optimization**: Compression and batching
- **Fault Tolerance**: Handles network failures
- **Backpressure**: Prevents memory overflow

---

## 🔄 Query Execution Flow

### **From SQL to Results: The Complete Journey**

Here's how your query `SELECT * FROM postgresql.sales JOIN kafka.events` executes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Query Execution Flow                       │
└─────────────────────────────────────────────────────────────────────┘

1️⃣ SQL SUBMISSION (Client → Coordinator)
   ┌─────────────┐    HTTP POST     ┌─────────────────┐
   │   Client    │ ──────────────→  │   Coordinator   │
   │ (sql query) │                  │   (parse SQL)   │
   └─────────────┘                  └─────────────────┘

2️⃣ QUERY PLANNING (Coordinator)
   ┌─────────────────────────────────────────────────────────────────┐
   │  Step 1: Parse SQL → AST (Abstract Syntax Tree)                │
   │  Step 2: Semantic Analysis (validate tables, columns)          │
   │  Step 3: Cost-Based Optimization (join order, algorithms)      │
   │  Step 4: Create Distributed Plan (stages, splits, tasks)       │
   └─────────────────────────────────────────────────────────────────┘

3️⃣ STAGE CREATION (Coordinator → Workers)
   ┌─────────────────┐                    ┌─────────────────┐
   │   Stage 1       │                    │   Stage 2       │
   │ (Scan postgres) │                    │ (Scan kafka)    │
   │                 │                    │                 │
   │ Worker 1: Split │                    │ Worker 1: Topic │
   │ Worker 2: Split │                    │ Worker 2: Topic │
   └─────────────────┘                    └─────────────────┘
            │                                      │
            └──────────────────┬───────────────────┘
                               │
                     ┌─────────────────┐
                     │   Stage 3       │
                     │  (Join + Send)  │
                     │                 │
                     │ Worker 1: Join  │
                     │ Worker 2: Join  │
                     └─────────────────┘

4️⃣ TASK EXECUTION (Workers)
   Worker 1:                           Worker 2:
   ┌─────────────────────┐              ┌─────────────────────┐
   │ ▸ Read PostgreSQL   │              │ ▸ Read Kafka        │
   │ ▸ Apply Filters     │              │ ▸ Parse JSON        │
   │ ▸ Send via Exchange │              │ ▸ Send via Exchange │
   └─────────────────────┘              └─────────────────────┘
                │                                  │
                └──────────── Join Data ──────────┘
                               │
                    ┌─────────────────────┐
                    │ ▸ Hash Join         │
                    │ ▸ Send Results      │
                    └─────────────────────┘

5️⃣ RESULT COLLECTION (Coordinator)
   ┌─────────────────────────────────────────────────────────────────┐
   │ ▸ Collect data from all workers                                 │
   │ ▸ Apply final ordering/limiting                                 │
   │ ▸ Stream results back to client                                 │
   └─────────────────────────────────────────────────────────────────┘
```

### **Stage Types:**

#### **Source Stages**
- **Purpose**: Read data from connectors
- **Parallelism**: Based on data splits (files, partitions, etc.)
- **Location**: Run on workers with best data locality

#### **Shuffle Stages**
- **Purpose**: Redistribute data for joins/aggregations
- **Parallelism**: Based on hash functions or ranges
- **Network**: Heavy data exchange between workers

#### **Final Stages**
- **Purpose**: Collect and return results
- **Parallelism**: Usually single-threaded on coordinator
- **Output**: Stream results to client

---

## 🧠 Memory Architecture

### **Memory Management Across the Cluster**

Trino uses sophisticated memory management to handle large queries efficiently:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Memory Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  COORDINATOR MEMORY (2GB)          WORKER MEMORY (4GB each)        │
│  ┌─────────────────────────┐      ┌─────────────────────────────┐   │
│  │   Query Management      │      │      Query Execution       │   │
│  │ ┌─────────────────────┐ │      │ ┌─────────────────────────┐ │   │
│  │ │ Query Metadata      │ │      │ │ Operator Memory         │ │   │
│  │ │ • Execution Plans   │ │      │ │ • Hash Tables          │ │   │
│  │ │ • Task Assignments  │ │      │ │ • Sort Buffers         │ │   │
│  │ │ • Progress Tracking │ │      │ │ • Aggregation Buffers  │ │   │
│  │ └─────────────────────┘ │      │ └─────────────────────────┘ │   │
│  │                         │      │                             │   │
│  │ ┌─────────────────────┐ │      │ ┌─────────────────────────┐ │   │
│  │ │ Metadata Cache      │ │      │ │ Page Buffers            │ │   │
│  │ │ • Table Schemas     │ │      │ │ • Input Pages          │ │   │
│  │ │ • Column Stats      │ │      │ │ • Output Pages         │ │   │
│  │ │ • Partition Info    │ │      │ │ • Exchange Buffers     │ │   │
│  │ └─────────────────────┘ │      │ └─────────────────────────┘ │   │
│  └─────────────────────────┘      │                             │   │
│                                   │ ┌─────────────────────────┐ │   │
│                                   │ │ Connector Memory        │ │   │
│                                   │ │ • JDBC Buffers         │ │   │
│                                   │ │ • Kafka Consumers      │ │   │
│                                   │ │ • File System Cache   │ │   │
│                                   │ └─────────────────────────┘ │   │
│                                   └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

Memory Limits (from your config):
┌─────────────────────────────────────────────────────────────────────┐
│ query.max-memory=8GB                (total across all workers)     │
│ query.max-memory-per-node=2GB       (per worker limit)             │
│ query.max-total-memory-per-node=3GB (per worker + overhead)        │
└─────────────────────────────────────────────────────────────────────┘
```

### **Memory Pool Management:**

#### **General Pool**
- **Purpose**: Normal query execution
- **Size**: Most of available memory
- **Usage**: Joins, aggregations, sorting

#### **Reserved Pool**
- **Purpose**: Large queries that exceed general pool
- **Size**: Small portion of memory
- **Usage**: Emergency allocation to prevent deadlocks

#### **System Pool**
- **Purpose**: System operations and metadata
- **Size**: Fixed small allocation
- **Usage**: Connector metadata, internal operations

### **Memory Pressure Handling:**

```
Low Memory → Spill to Disk → Kill Queries → Reject New Queries
    ↓              ↓              ↓              ↓
 Normal Ops    Performance    Free Memory    Protect Cluster
```

---

## 🔌 Connectors Architecture

### **Multi-Source Query Capability**

Your Trino setup can query multiple data sources in a single SQL statement:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Connector Architecture                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│    COORDINATOR & WORKERS                                            │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                     Trino SQL Engine                           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                    Uniform SQL Interface                            │
│                                  │                                  │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   Connector Framework                          │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │ │
│  │  │ PostgreSQL  │ │   Kafka     │ │  Iceberg    │ │  Memory   │ │ │
│  │  │ Connector   │ │ Connector   │ │ Connector   │ │ Connector │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │ │
│  │                                                                 │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │ │
│  │  │ Delta Lake  │ │   TPC-H     │ │ File System │ │   Redis   │ │ │
│  │  │ Connector   │ │ Connector   │ │ Connector   │ │ Connector │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│               Data Source Protocols                                 │
│                                  │                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │PostgreSQL│  │  Kafka   │  │  HDFS/   │  │ In-Memory│             │
│  │Database  │  │ Clusters │  │   S3     │  │   Data   │             │
│  │          │  │          │  │          │  │          │             │
│  │Port: 5432│  │Port: 9092│  │ Files    │  │   RAM    │             │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

### **How Connectors Work:**

#### **1. Metadata Operations**
```sql
-- When you run: SHOW TABLES FROM postgresql.public;
┌─────────────────────────────────────────────────┐
│ Coordinator asks PostgreSQL Connector:         │
│ "What tables exist in schema 'public'?"        │
│                                                 │
│ PostgreSQL Connector:                           │
│ ▸ Connects to PostgreSQL (192.168.1.184:5432) │
│ ▸ Runs: SELECT table_name FROM information_schema │
│ ▸ Returns list to Coordinator                   │
└─────────────────────────────────────────────────┘
```

#### **2. Data Splitting**
```sql
-- When you run: SELECT * FROM postgresql.sales;
┌─────────────────────────────────────────────────┐
│ Coordinator asks PostgreSQL Connector:         │
│ "How should we split this table for parallel reading?" │
│                                                 │
│ PostgreSQL Connector:                           │
│ ▸ Analyzes table size and structure             │
│ ▸ Creates splits (e.g., by primary key ranges)  │
│ ▸ Returns: [Split1: id 1-1000, Split2: id 1001-2000] │
└─────────────────────────────────────────────────┘
```

#### **3. Parallel Data Reading**
```sql
┌─────────────────────────────────────────────────┐
│ Worker 1 (cpu-node2):                          │
│ ▸ Gets Split1: "SELECT * FROM sales WHERE id BETWEEN 1 AND 1000" │
│ ▸ Executes SQL against PostgreSQL               │
│ ▸ Streams results to query engine               │
│                                                 │
│ Worker 2 (worker-node3):                       │
│ ▸ Gets Split2: "SELECT * FROM sales WHERE id BETWEEN 1001 AND 2000" │
│ ▸ Executes SQL against PostgreSQL               │
│ ▸ Streams results to query engine               │
└─────────────────────────────────────────────────┘
```

### **Connector-Specific Optimizations:**

#### **PostgreSQL Connector**
- **Predicate Pushdown**: Filters pushed to database
- **Projection Pushdown**: Only selected columns retrieved
- **Connection Pooling**: Reuses database connections
- **Parallel Reads**: Multiple connections per worker

#### **Kafka Connector**
- **Partition Assignment**: Each split = Kafka partition
- **Offset Management**: Tracks message positions
- **Schema Registry**: Handles Avro/JSON schemas
- **Time-based Splits**: Can split by timestamp

#### **Iceberg Connector**
- **Snapshot Isolation**: Consistent table snapshots
- **Partition Pruning**: Skips irrelevant partitions
- **File-level Splits**: Each file becomes a split
- **Vectorized Reading**: High-performance columnar reads

---

## 🔍 Discovery & Communication

### **How Nodes Find Each Other**

Unlike Spark/Flink, Trino uses **HTTP-based discovery** - no SSH required:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Discovery Process                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  STEP 1: Coordinator Starts                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ cpu-node1 (Coordinator)                                        │ │
│  │ ▸ Starts discovery service on port 8081                        │ │
│  │ ▸ discovery.uri=http://192.168.1.184:8081                     │ │
│  │ ▸ Waits for workers to register                                │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  STEP 2: Workers Auto-Register                                     │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐   │
│  │ cpu-node2 (Worker 1)     │    │ worker-node3 (Worker 2)      │   │
│  │                          │    │                              │   │
│  │ ▸ Reads discovery.uri    │    │ ▸ Reads discovery.uri        │   │
│  │ ▸ HTTP POST to           │    │ ▸ HTTP POST to               │   │
│  │   192.168.1.184:8081     │    │   192.168.1.184:8081         │   │
│  │ ▸ Sends: node info       │    │ ▸ Sends: node info           │   │
│  │   - IP address           │    │   - IP address               │   │
│  │   - Available memory     │    │   - Available memory         │   │
│  │   - CPU cores            │    │   - CPU cores                │   │
│  │   - Connectors           │    │   - Connectors               │   │
│  └──────────────────────────┘    └──────────────────────────────┘   │
│                                  │                                  │
│                                  ▼                                  │
│  STEP 3: Cluster Formation                                         │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Coordinator maintains registry:                                 │ │
│  │                                                                 │ │
│  │ Active Nodes:                                                   │ │
│  │ ▸ cpu-node1    (Coordinator) - 192.168.1.184:8081             │ │
│  │ ▸ cpu-node2    (Worker)      - 192.168.1.187:8081             │ │
│  │ ▸ worker-node3 (Worker)      - 192.168.1.190:8081             │ │
│  │                                                                 │ │
│  │ Total Resources:                                                │ │
│  │ ▸ Memory: 6GB (2GB coord + 2GB worker1 + 2GB worker2)          │ │
│  │ ▸ CPU: 6 cores total                                           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### **Ongoing Communication:**

#### **Health Checks**
```
Every 30 seconds:
Workers → Coordinator: "I'm alive and have X memory available"
Coordinator → Workers: "Here are your new tasks"
```

#### **Task Assignment**
```
Query arrives:
Coordinator → Worker 1: "Execute Stage 1, Split A"
Coordinator → Worker 2: "Execute Stage 1, Split B"
Workers → Coordinator: "Stage 1 complete, here's the data"
```

#### **No SSH Needed Because:**
- **Service Architecture**: Each node runs as systemd service
- **HTTP Communication**: All coordination via REST APIs
- **Self-Registration**: Workers find coordinator automatically
- **Graceful Handling**: Automatic retry and failover

---

## 🧮 Query Planning & Optimization

### **Cost-Based Optimization (CBO)**

Trino uses sophisticated optimization to make your cross-system queries fast:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Query Optimization Process                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  INPUT: SQL Query                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ SELECT c.name, SUM(o.amount)                                   │ │
│  │ FROM postgresql.customers c                                     │ │
│  │ JOIN kafka.orders o ON c.id = o.customer_id                    │ │
│  │ WHERE c.country = 'USA'                                        │ │
│  │ GROUP BY c.name                                                │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  STEP 1: Parse & Validate                                          │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ ▸ Parse SQL to Abstract Syntax Tree (AST)                      │ │
│  │ ▸ Resolve table/column references across catalogs              │ │
│  │ ▸ Type checking and validation                                  │ │
│  │ ▸ Permission checks per connector                              │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  STEP 2: Rule-Based Optimization                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ ▸ Predicate Pushdown:                                          │ │
│  │   - Push "country = 'USA'" to PostgreSQL                       │ │
│  │   - Reduce data movement                                        │ │
│  │                                                                 │ │
│  │ ▸ Projection Pushdown:                                         │ │
│  │   - Only read c.name, c.id from PostgreSQL                     │ │
│  │   - Only read o.customer_id, o.amount from Kafka               │ │
│  │                                                                 │ │
│  │ ▸ Join Reordering:                                             │ │
│  │   - Filter first, then join (smaller datasets)                │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  STEP 3: Cost-Based Optimization                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Statistics Collection:                                          │ │
│  │ ▸ PostgreSQL: ANALYZE results (row counts, data distribution)  │ │
│  │ ▸ Kafka: Topic partition info, message rates                   │ │
│  │                                                                 │ │
│  │ Join Algorithm Selection:                                       │ │
│  │ ▸ Hash Join vs Broadcast Join vs Merge Join                    │ │
│  │ ▸ Which table to build/probe                                   │ │
│  │                                                                 │ │
│  │ Parallelism Planning:                                           │ │
│  │ ▸ How many splits per data source                              │ │
│  │ ▸ Optimal number of workers per stage                          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  OUTPUT: Distributed Execution Plan                                │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Stage 0: [Source]                                              │ │
│  │ ▸ Worker 1: Scan PostgreSQL customers WHERE country='USA'      │ │
│  │ ▸ Worker 2: Scan PostgreSQL customers WHERE country='USA'      │ │
│  │                                                                 │ │
│  │ Stage 1: [Source]                                              │ │
│  │ ▸ Worker 1: Scan Kafka orders (partitions 0,1)                │ │
│  │ ▸ Worker 2: Scan Kafka orders (partitions 2,3)                │ │
│  │                                                                 │ │
│  │ Stage 2: [Join + Aggregate]                                    │ │
│  │ ▸ Worker 1: Hash join + group by (hash(customer_id) % 2 = 0)   │ │
│  │ ▸ Worker 2: Hash join + group by (hash(customer_id) % 2 = 1)   │ │
│  │                                                                 │ │
│  │ Stage 3: [Final Aggregate]                                     │ │
│  │ ▸ Coordinator: Combine results from workers                    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### **Optimization Techniques:**

#### **Cross-System Optimizations**
- **Data Locality**: Minimize network traffic between systems
- **Format Awareness**: Leverage Parquet column pruning, partition elimination
- **Parallel Reading**: Coordinate parallel reads across different systems
- **Join Location**: Decide where to perform joins (memory vs. network cost)

#### **Connector-Specific Optimizations**
```
PostgreSQL:
▸ SQL pushdown (WHERE, ORDER BY, LIMIT)
▸ Connection pooling
▸ Batch fetching

Kafka:
▸ Partition-aware parallelism
▸ Schema registry integration
▸ Consumer group management

Iceberg:
▸ Snapshot isolation
▸ Partition pruning
▸ File-level parallelism
```

---

## 🤝 Distributed Joins & Aggregations

### **How Cross-System Joins Work**

The most complex part of distributed query processing - joining data from different systems:

```
┌─────────────────────────────────────────────────────────────────────┐
│           Cross-System Join: PostgreSQL ⟵⟶ Kafka                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  QUERY: SELECT * FROM postgresql.customers c                       │
│         JOIN kafka.orders o ON c.id = o.customer_id                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

STAGE 1: PARALLEL DATA EXTRACTION
┌─────────────────────────────────────────────────────────────────────┐
│  Worker 1 (cpu-node2)              Worker 2 (worker-node3)         │
│  ┌─────────────────────────┐       ┌─────────────────────────────┐  │
│  │ PostgreSQL Scan         │       │ PostgreSQL Scan             │  │
│  │ ▸ customers (id 1-5000) │       │ ▸ customers (id 5001-10000) │  │
│  │ ▸ Extract: id, name     │       │ ▸ Extract: id, name         │  │
│  │ ▸ Apply local filters   │       │ ▸ Apply local filters       │  │
│  └─────────────────────────┘       └─────────────────────────────┘  │
│              │                                     │                │
│              ▼                                     ▼                │
│  ┌─────────────────────────┐       ┌─────────────────────────────┐  │
│  │ Kafka Scan              │       │ Kafka Scan                  │  │
│  │ ▸ orders (partitions 0,1)│      │ ▸ orders (partitions 2,3)  │  │
│  │ ▸ Extract: customer_id, │       │ ▸ Extract: customer_id,     │  │
│  │           amount        │       │           amount            │  │
│  └─────────────────────────┘       └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

STAGE 2: DATA REDISTRIBUTION (SHUFFLE)
┌─────────────────────────────────────────────────────────────────────┐
│  Data gets redistributed by join key (customer_id)                 │
│                                                                     │
│  Worker 1 will get:                Worker 2 will get:              │
│  ┌─────────────────────────┐       ┌─────────────────────────────┐  │
│  │ All customers where     │       │ All customers where         │  │
│  │ hash(id) % 2 = 0        │       │ hash(id) % 2 = 1            │  │
│  │                         │       │                             │  │
│  │ All orders where        │       │ All orders where            │  │
│  │ hash(customer_id) % 2=0 │       │ hash(customer_id) % 2 = 1   │  │
│  └─────────────────────────┘       └─────────────────────────────┘  │
│                                                                     │
│  Network Transfer: Each worker sends data to correct destination   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Worker 1 → Worker 1: customers(id=even), orders(cust_id=even)  │ │
│  │ Worker 1 → Worker 2: customers(id=odd),  orders(cust_id=odd)   │ │
│  │ Worker 2 → Worker 1: customers(id=even), orders(cust_id=even)  │ │
│  │ Worker 2 → Worker 2: customers(id=odd),  orders(cust_id=odd)   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

STAGE 3: LOCAL JOINS
┌─────────────────────────────────────────────────────────────────────┐
│  Each worker performs local hash join on their subset              │
│                                                                     │
│  Worker 1:                          Worker 2:                      │
│  ┌─────────────────────────┐       ┌─────────────────────────────┐  │
│  │ 1. Build hash table     │       │ 1. Build hash table         │  │
│  │    from customers       │       │    from customers           │  │
│  │    (key = id)           │       │    (key = id)               │  │
│  │                         │       │                             │  │
│  │ 2. Probe with orders    │       │ 2. Probe with orders        │  │
│  │    (key = customer_id)  │       │    (key = customer_id)      │  │
│  │                         │       │                             │  │
│  │ 3. Output joined rows   │       │ 3. Output joined rows       │  │
│  └─────────────────────────┘       └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

STAGE 4: RESULT COLLECTION
┌─────────────────────────────────────────────────────────────────────┐
│  Coordinator collects results from all workers                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Worker 1 Results → Coordinator                                  │ │
│  │ Worker 2 Results → Coordinator                                  │ │
│  │                                                                 │ │
│  │ Optional final operations:                                      │ │
│  │ ▸ Global ORDER BY                                              │ │
│  │ ▸ LIMIT/OFFSET                                                 │ │
│  │ ▸ Final projections                                            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### **Join Algorithm Selection:**

#### **Hash Join (Most Common)**
- **When**: General purpose, most joins
- **How**: Build hash table from smaller side, probe with larger
- **Memory**: Builds hash table in memory
- **Performance**: O(M + N) where M, N are table sizes

#### **Broadcast Join**
- **When**: One side is very small (< 100MB)
- **How**: Send small table to all workers
- **Memory**: Small table replicated everywhere
- **Performance**: No shuffle needed, very fast

#### **Merge Join**
- **When**: Both sides are pre-sorted on join key
- **How**: Merge sorted streams
- **Memory**: Very low memory usage
- **Performance**: Good for very large tables

### **Aggregation Strategies:**

#### **Two-Phase Aggregation**
```
Phase 1 (Workers): Partial aggregation per worker
  Worker 1: GROUP BY customer_id → partial counts
  Worker 2: GROUP BY customer_id → partial counts

Phase 2 (Coordinator): Final aggregation
  Coordinator: Combine partial results → final counts
```

#### **Hash-Based Distribution**
```
Distribute by grouping key:
  hash(customer_id) % num_workers = target_worker
  
Each worker gets complete groups for final aggregation
```

---

## 🔒 Security Architecture

### **Your Current Security Setup**

Based on your configuration, here's how security works:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Security Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CLIENT ACCESS                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ HTTP (not HTTPS) - Basic setup                                 │ │
│  │ ▸ Port: 8081                                                   │ │
│  │ ▸ No authentication required                                   │ │
│  │ ▸ Internal network only (good for HomeLA)                      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  COORDINATOR                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ No built-in authentication (commented out)                     │ │
│  │ ▸ http-server.authentication.type=PASSWORD (disabled)          │ │
│  │ ▸ Access control via network (firewall, VPN)                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                  │                                  │
│                                  ▼                                  │
│  CONNECTOR-LEVEL SECURITY                                           │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ PostgreSQL Connector:                                           │ │
│  │ ▸ connection-user=dataeng                                       │ │
│  │ ▸ connection-password=password                                  │ │
│  │ ▸ Uses PostgreSQL's role-based access                          │ │
│  │                                                                 │ │
│  │ Kafka Connector:                                                │ │
│  │ ▸ Direct connection to brokers                                  │ │
│  │ ▸ No SASL/SSL configured                                       │ │
│  │ ▸ Relies on network security                                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### **Security Best Practices for Production:**

#### **Network Security (Your Current Approach)**
- ✅ **Firewall**: Only allow 8081 from trusted networks
- ✅ **VPN**: Access Trino through VPN tunnel
- ✅ **Internal Network**: Keep cluster on private network

#### **Application-Level Security (Optional Upgrades)**
```bash
# Enable HTTPS
http-server.https.enabled=true
http-server.https.port=8443
http-server.https.keystore.path=/path/to/keystore.jks

# Enable authentication
http-server.authentication.type=PASSWORD
http-server.authentication.password.user-mapping.pattern=(.*)
```

#### **Data Source Security**
- **PostgreSQL**: Use dedicated service accounts with minimal privileges
- **Kafka**: Enable SASL/SCRAM authentication in production
- **File Systems**: Use service accounts with read-only access

---

## 📈 Scaling Your Setup

### **Current vs. Scaled Architecture**

Your current 3-node setup vs. what it could become:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CURRENT (3 nodes)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │ cpu-node1   │    │ cpu-node2   │    │worker-node3 │              │
│  │(Coordinator)│    │ (Worker 1)  │    │ (Worker 2)  │              │
│  │             │    │             │    │             │              │
│  │ Memory: 2GB │    │ Memory: 2GB │    │ Memory: 2GB │              │
│  │ CPU: 2 cores│    │ CPU: 2 cores│    │ CPU: 2 cores│              │
│  └─────────────┘    └─────────────┘    └─────────────┘              │
│                                                                     │
│  Total Capacity: 6GB memory, 6 CPU cores                           │
│  Max Concurrent Queries: ~3 small or 1 large                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        SCALED (10 nodes)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌───────────────────────────────────────────┐    │
│  │ Coordinator │    │              Workers                      │    │
│  │             │    │                                           │    │
│  │ cpu-node1   │    │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ │    │
│  │ Memory: 4GB │    │  │Node2│ │Node3│ │Node4│ │Node5│ │Node6│ │    │
│  │ CPU: 4 cores│    │  │ 8GB │ │ 8GB │ │ 8GB │ │ 8GB │ │ 8GB │ │    │
│  └─────────────┘    │  │4core│ │4core│ │4core│ │4core│ │4core│ │    │
│                     │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ │    │
│                     │                                           │    │
│                     │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐         │    │
│                     │  │Node7│ │Node8│ │Node9│ │Nod10│         │    │
│                     │  │ 8GB │ │ 8GB │ │ 8GB │ │ 8GB │         │    │
│                     │  │4core│ │4core│ │4core│ │4core│         │    │
│                     │  └─────┘ └─────┘ └─────┘ └─────┘         │    │
│                     └───────────────────────────────────────────┘    │
│                                                                     │
│  Total Capacity: 76GB memory, 40 CPU cores                         │
│  Max Concurrent Queries: ~30 small or 10 large                     │
└─────────────────────────────────────────────────────────────────────┘
```

### **Scaling Strategies:**

#### **Horizontal Scaling (Add More Workers)**
```bash
# Add new worker node (node4)
# 1. Install Trino on new node
# 2. Configure as worker:
coordinator=false
discovery.uri=http://192.168.1.184:8081

# 3. Start service
systemctl start trino

# 4. Worker auto-registers with coordinator
# 5. More parallelism automatically available
```

#### **Vertical Scaling (Bigger Machines)**
```bash
# Increase memory per node
query.max-memory-per-node=8GB
query.max-total-memory-per-node=12GB

# Increase task concurrency
task.concurrency=32
task.max-worker-threads=400
```

#### **Workload Isolation**
```bash
# Separate clusters for different workloads
Cluster 1: Interactive analytics (small, fast queries)
Cluster 2: ETL processing (large, batch queries)
Cluster 3: Reporting (scheduled, predictable queries)
```

### **When to Scale:**

#### **Add Workers When:**
- Queries frequently hit memory limits
- High CPU utilization across all workers
- Query queueing becomes common
- Need more parallelism for large tables

#### **Upgrade Coordinator When:**
- Many concurrent connections
- Complex query planning takes too long
- Metadata operations are slow
- Web UI becomes unresponsive

---

## ⚡ Performance Tuning

### **Tuning Your Current Setup**

Here are optimizations specific to your 3-node cluster:

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Performance Tuning                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  COORDINATOR TUNING (cpu-node1)                                    │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Memory Management:                                              │ │
│  │ ▸ query.max-memory=6GB               (total across workers)    │ │
│  │ ▸ query.max-queued-queries=1000      (queue size)              │ │
│  │ ▸ query.max-concurrent-queries=10    (active queries)          │ │
│  │                                                                 │ │
│  │ Query Optimization:                                             │ │
│  │ ▸ query.max-run-time=1h              (prevent runaway)         │ │
│  │ ▸ query.low-memory-killer.delay=5m   (kill slow queries)       │ │
│  │                                                                 │ │
│  │ Planning Optimization:                                          │ │
│  │ ▸ optimizer.join-reordering-strategy=AUTOMATIC                 │ │
│  │ ▸ optimizer.join-distribution-type=AUTOMATIC                   │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  WORKER TUNING (cpu-node2, worker-node3)                          │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Task Execution:                                                 │ │
│  │ ▸ task.concurrency=4                 (per worker)              │ │
│  │ ▸ task.max-worker-threads=100        (thread pool)             │ │
│  │ ▸ task.writer-count=1                (output writers)          │ │
│  │                                                                 │ │
│  │ Memory Configuration:                                           │ │
│  │ ▸ query.max-memory-per-node=2GB      (per worker limit)        │ │
│  │ ▸ memory.heap-headroom-per-node=512MB (JVM overhead)           │ │
│  │                                                                 │ │
│  │ Spill Configuration:                                            │ │
│  │ ▸ spill-enabled=true                 (spill to disk)           │ │
│  │ ▸ spiller-spill-path=/tmp/trino-spill (spill location)         │ │
│  │ ▸ spiller-max-used-space-threshold=0.9 (disk usage limit)      │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### **Connector-Specific Tuning:**

#### **PostgreSQL Connector Optimization**
```properties
# In your postgresql.properties:
connection-pool.max-size=50
connection-pool.max-connection-lifetime=2m
connection-pool.max-idle-time=1m

# Enable pushdown optimizations
postgresql.experimental.enable-predicate-pushdown-with-varchar-equality=true
postgresql.experimental.enable-predicate-pushdown-with-varchar-inequality=true
```

#### **Kafka Connector Optimization**
```properties
# In your kafka.properties:
kafka.buffer-size=1MB
kafka.messages-per-split=100000
kafka.consumer-timeout=1m

# For high-throughput topics
kafka.max-partition-fetch-bytes=1MB
kafka.fetch-min-bytes=1MB
```

### **Query-Level Optimizations:**

#### **Efficient Join Patterns**
```sql
-- ✅ GOOD: Filter before joining
SELECT c.name, SUM(o.amount)
FROM postgresql.customers c
JOIN kafka.orders o ON c.id = o.customer_id
WHERE c.country = 'USA'  -- Filter pushdown to PostgreSQL
  AND o.order_date >= DATE '2023-01-01'  -- Filter on Kafka
GROUP BY c.name;

-- ❌ BAD: Filter after joining
SELECT c.name, SUM(o.amount)
FROM postgresql.customers c
JOIN kafka.orders o ON c.id = o.customer_id
WHERE c.country = 'USA'  -- Lots of unnecessary data transferred
GROUP BY c.name;
```

#### **Memory-Efficient Aggregations**
```sql
-- ✅ GOOD: Use approximate functions for large datasets
SELECT customer_id, approx_distinct(product_id) as unique_products
FROM kafka.events
GROUP BY customer_id;

-- ❌ BAD: Exact distinct on large dataset
SELECT customer_id, COUNT(DISTINCT product_id) as unique_products
FROM kafka.events
GROUP BY customer_id;
```

### **Monitoring Performance:**

#### **Key Metrics to Watch**
```sql
-- Query execution time
SELECT query_id, state, elapsed_time_millis, queued_time_millis
FROM system.runtime.queries
WHERE state = 'RUNNING'
ORDER BY elapsed_time_millis DESC;

-- Memory usage per query
SELECT query_id, total_memory_reservation, peak_memory_reservation
FROM system.runtime.queries
WHERE state = 'RUNNING'
ORDER BY peak_memory_reservation DESC;

-- Worker utilization
SELECT node_id, processor_count, heap_available, heap_used
FROM system.runtime.nodes;
```

#### **Performance Troubleshooting Queries**
```sql
-- Find slow queries
SELECT query_id, query, state, total_cpu_time, total_scheduled_time
FROM system.runtime.queries
WHERE total_cpu_time > INTERVAL '30' SECOND
ORDER BY total_cpu_time DESC;

-- Check for memory pressure
SELECT query_id, memory_reservation, peak_memory_reservation
FROM system.runtime.queries
WHERE memory_reservation > 1000000000  -- > 1GB
ORDER BY peak_memory_reservation DESC;

-- Analyze failed queries
SELECT query_id, error_type, error_message
FROM system.runtime.queries
WHERE state = 'FAILED'
ORDER BY created DESC
LIMIT 10;
```

---

## 🏗️ Architecture Changes When Adding Nodes

### **Evolution of Your Cluster**

Here's how your architecture changes as you add more nodes:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      3-Node Setup (Current)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Single Coordinator + 2 Workers                                 │ │
│  │                                                                 │ │
│  │ Characteristics:                                                │ │
│  │ ▸ Simple setup and management                                  │ │
│  │ ▸ All queries routed through one coordinator                   │ │
│  │ ▸ Limited parallelism (2 workers)                              │ │
│  │ ▸ Good for: Small teams, development, light analytics          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      5-7 Node Setup (Small Scale)                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Single Coordinator + 4-6 Workers                               │ │
│  │                                                                 │ │
│  │ Characteristics:                                                │ │
│  │ ▸ Better parallelism for medium queries                        │ │
│  │ ▸ Can handle more concurrent users                             │ │
│  │ ▸ Coordinator may become bottleneck                            │ │
│  │ ▸ Good for: Department-level analytics                         │ │
│  │                                                                 │ │
│  │ Configuration Changes:                                          │ │
│  │ ▸ Increase coordinator memory (4-8GB)                          │ │
│  │ ▸ Tune task.concurrency per worker                             │ │
│  │ ▸ Enable spilling for large queries                            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                     10+ Node Setup (Large Scale)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Dedicated Coordinator + Many Workers                           │ │
│  │                                                                 │ │
│  │ Characteristics:                                                │ │
│  │ ▸ Coordinator doesn't run worker tasks                         │ │
│  │ ▸ High parallelism for complex queries                         │ │
│  │ ▸ Can handle many concurrent users                             │ │
│  │ ▸ Good for: Enterprise-wide analytics                          │ │
│  │                                                                 │ │
│  │ Configuration Changes:                                          │ │
│  │ ▸ coordinator=true, node-scheduler.include-coordinator=false   │ │
│  │ ▸ Dedicated coordinator hardware                               │ │
│  │ ▸ Resource groups for workload isolation                       │ │
│  │ ▸ Query queuing and admission control                          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   High Availability Setup                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Multiple Coordinators + Load Balancer                          │ │
│  │                                                                 │ │
│  │      ┌─────────────┐                                           │ │
│  │      │Load Balancer│                                           │ │
│  │      └─────────────┘                                           │ │
│  │           │                                                     │ │
│  │    ┌──────┴──────┐                                             │ │
│  │    │             │                                             │ │
│  │ ┌──▼──┐       ┌──▼──┐                                          │ │
│  │ │Coord│       │Coord│                                          │ │
│  │ │  1  │       │  2  │                                          │ │
│  │ └─────┘       └─────┘                                          │ │
│  │                                                                 │ │
│  │ Characteristics:                                                │ │
│  │ ▸ No single point of failure                                   │ │
│  │ ▸ Automatic failover                                           │ │
│  │ ▸ Horizontal scaling of query planning                         │ │
│  │ ▸ Good for: Mission-critical systems                           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### **Adding Nodes to Your Current Setup:**

#### **Step 1: Add Worker Node (Easiest)**
```bash
# On new node (e.g., node4)
# 1. Install Trino
sudo apt install openjdk-17-jdk
# Download and extract Trino...

# 2. Configure as worker
nano /home/trino/trino/etc/config.properties
coordinator=false
http-server.http.port=8081
discovery.uri=http://192.168.1.184:8081  # Points to your coordinator

# 3. Copy catalog configurations
scp -r cpu-node1:/home/trino/trino/etc/catalog/* /home/trino/trino/etc/catalog/

# 4. Start service
systemctl start trino

# 5. Verify in coordinator web UI (http://192.168.1.184:8081)
# Should see new worker auto-registered
```

#### **Step 2: Resource Adjustments**
```bash
# Update total memory limits
query.max-memory=9GB  # Was 6GB, now 6GB + 3GB for new worker
query.max-memory-per-node=3GB  # Increase per-node limit
```

#### **Step 3: Optimize for More Workers**
```bash
# Increase parallelism
task.concurrency=8  # More tasks per worker
task.max-worker-threads=200  # More threads

# Better memory management
spill-enabled=true
spiller-threads=8
```

### **What Changes When You Scale:**

#### **Query Distribution Patterns**
```
3 Workers: Simple hash distribution
  hash(key) % 3 = {0, 1, 2}

6 Workers: Better granularity
  hash(key) % 6 = {0, 1, 2, 3, 4, 5}

12 Workers: Very fine-grained
  hash(key) % 12 = {0, 1, 2, ..., 11}
```

#### **Memory Considerations**
```
More Workers = More Total Memory = Larger Queries Possible

3 Workers × 2GB = 6GB total → Can handle 6GB queries
6 Workers × 3GB = 18GB total → Can handle 18GB queries
12 Workers × 4GB = 48GB total → Can handle 48GB queries
```

#### **Network Traffic Patterns**
```
More Workers = More Shuffle Traffic

3-node joins: 3×3 = 9 network connections
6-node joins: 6×6 = 36 network connections
12-node joins: 12×12 = 144 network connections

→ Network becomes more important with scale
```

---

## 🎯 Summary: Your Trino Architecture

### **What You Have Today**

Your 3-node Trino cluster provides:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Current Capabilities                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ✅ Multi-Source Queries                                           │
│     ▸ Join PostgreSQL + Kafka + Iceberg + Delta Lake in one SQL    │ │
│     ▸ No ETL needed - query data where it lives                    │ │
│                                                                     │
│  ✅ Interactive Performance                                         │
│     ▸ Sub-second queries on small datasets                         │ │
│     ▸ Minute-scale queries on medium datasets                      │ │
│     ▸ Distributed parallel execution                               │ │
│                                                                     │
│  ✅ SQL Analytics Power                                             │
│     ▸ Complex JOINs across different systems                       │ │
│     ▸ Window functions, CTEs, advanced analytics                   │ │
│     ▸ Approximate functions for big data                           │ │
│                                                                     │
│  ✅ Easy Management                                                 │
│     ▸ Simple systemd services (no SSH complexity)                  │ │
│     ▸ HTTP-based communication                                     │ │
│     ▸ Auto-discovery and self-registration                         │ │
│                                                                     │
│  ✅ Integration Ready                                               │
│     ▸ Connects to your existing PostgreSQL, Kafka                  │ │
│     ▸ Ready for Iceberg and Delta Lake tables                      │ │
│     ▸ BI tools can connect via JDBC/ODBC                           │ │
└─────────────────────────────────────────────────────────────────────┘
```

### **Key Architectural Principles**

1. **Coordinator-Worker Model**: Single brain, multiple hands
2. **HTTP Communication**: No SSH complexity like Spark/Flink
3. **Connector Architecture**: Pluggable data source access
4. **Memory-Centric**: Optimized for interactive queries
5. **Cost-Based Optimization**: Smart query planning across systems

### **When to Use Trino vs. Other Tools**

**Use Trino for:**
- ✅ Interactive analytics and dashboards
- ✅ Cross-system joins and federation
- ✅ Ad-hoc data exploration
- ✅ Real-time reporting

**Use Spark for:**
- 🔄 ETL and data transformation jobs
- 🔄 Machine learning pipelines
- 🔄 Batch processing workflows

**Use Flink for:**
- 🔄 Real-time stream processing
- 🔄 Event-driven applications
- 🔄 Low-latency data pipelines

### **Your Next Steps**

1. **Start Simple**: Use your current 3-node setup for analytics
2. **Monitor Performance**: Watch memory usage and query times
3. **Scale Horizontally**: Add workers as query load increases
4. **Optimize Queries**: Use connector pushdown and efficient joins
5. **Consider HA**: Add coordinator redundancy for production

Your Trino cluster is a powerful addition to your data engineering stack - perfect for the "analytics" layer that sits on top of your Kafka streams, PostgreSQL databases, and lakehouse tables! 🚀

---

*This guide covers the architecture of **your specific Trino setup**. For production deployments, consider additional topics like high availability, security hardening, and advanced performance tuning.*
