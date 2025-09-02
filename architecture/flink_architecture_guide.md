# Apache Flink Distributed Architecture Guide

## 🏗️ Your Current 3-Node Flink Setup

This guide explains the Apache Flink architecture based on **your exact setup**:
- **cpu-node1** (192.168.1.184) - JobManager + Web UI
- **cpu-node2** (192.168.1.187) - TaskManager 1  
- **worker-node3** (192.168.1.190) - TaskManager 2

---

## 📚 Table of Contents

1. [What is Flink? (Simple Explanation)](#what-is-flink-simple-explanation)
2. [Your Current Architecture](#your-current-architecture)
3. [JobManager Architecture](#jobmanager-architecture)
4. [TaskManager Architecture](#taskmanager-architecture)
5. [Application Execution Flow](#application-execution-flow)
6. [Flink's Execution Model](#flinks-execution-model)
7. [Memory Architecture](#memory-architecture)
8. [Streaming Architecture & Event Time](#streaming-architecture--event-time)
9. [State Management & Checkpointing](#state-management--checkpointing)
10. [Watermarks & Late Data Handling](#watermarks--late-data-handling)
11. [Flink SQL & Table API](#flink-sql--table-api)
12. [Integration Patterns](#integration-patterns)
13. [Scaling Your Setup](#scaling-your-setup)
14. [Performance Optimization](#performance-optimization)
15. [Monitoring & Troubleshooting](#monitoring--troubleshooting)

---

## 🤔 What is Flink? (Simple Explanation)

**Think of Flink like a real-time data processing factory:**

- **JobManager** = Factory Supervisor (coordinates all work, manages resources)
- **TaskManagers** = Assembly Line Workers (execute the actual processing)
- **DataStreams** = Conveyor Belts (continuous flow of data)
- **Operators** = Processing Stations (transform data as it flows)
- **Checkpoints** = Save Points (backup factory state for recovery)
- **Watermarks** = Quality Control Timestamps (handle late-arriving data)
- **State** = Memory of the Factory (remembers previous data for processing)
- **Slots** = Workstations (parallel processing units)

**Why streaming-first?** Unlike batch processing that waits for all data, Flink processes each piece of data immediately as it arrives - like a factory that never stops running!

---

## 🏛️ Your Current Architecture

### Overall System View

**What you have:** A 3-node distributed Flink cluster with JobManager-TaskManager architecture optimized for real-time stream processing.

### **Plain English Explanation:**
- **1 JobManager Node** - The "supervisor" that coordinates all streaming jobs
- **2 TaskManager Nodes** - The "workers" that process data streams in real-time
- **Distributed State** - All nodes share state management for fault tolerance

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Your Flink Cluster                          │
├─────────────────────┬─────────────────────┬─────────────────────────┤
│    cpu-node1        │    cpu-node2        │   worker-node3          │
│   (JobManager)      │  (TaskManager 1)    │  (TaskManager 2)        │
│                     │                     │                         │
│  ┌───────────────┐  │  ┌───────────────┐  │  ┌───────────────────┐  │
│  │ JobManager    │  │  │ TaskManager   │  │  │  TaskManager      │  │
│  │ - Job Coord   │  │  │ - Task Exec   │  │  │  - Task Exec      │  │
│  │ - Checkpoints │  │  │ - State       │  │  │  - State          │  │
│  │ - Resource    │  │  │ - Slots: 4    │  │  │  - Slots: 4       │  │
│  │   Management  │  │  │ - Memory Pool │  │  │  - Memory Pool    │  │
│  │ - Web UI:8081 │  │  │ - Local State │  │  │  - Local State    │  │
│  └───────────────┘  │  └───────────────┘  │  └───────────────────┘  │
│                     │                     │                         │
│  ┌───────────────┐  │  ┌───────────────┐  │  ┌───────────────────┐  │
│  │ REST API      │  │  │ Data Stream   │  │  │  Data Stream      │  │
│  │ - Job Submit  │  │  │ Processing    │  │  │  Processing       │  │
│  │ - Monitoring  │  │  │ - Windowing   │  │  │  - Windowing      │  │
│  │ - Metrics     │  │  │ - Aggregation │  │  │  - Aggregation    │  │
│  │ - Logs        │  │  │ - Filtering   │  │  │  - Filtering      │  │
│  └───────────────┘  │  └───────────────┘  │  └───────────────────┘  │
│                     │                     │                         │
│  192.168.1.184      │  192.168.1.187      │  192.168.1.190          │
└─────────────────────┴─────────────────────┴─────────────────────────┘
```

### **Network Communication Ports:**
- **6123**: JobManager RPC port (coordination)
- **6122**: TaskManager RPC port (communication)
- **8081**: Flink Web Dashboard
- **6124**: JobManager data port
- **Dynamic**: TaskManager blob server ports

---

## 🎯 JobManager Architecture

### **Role: The Stream Processing Coordinator**

The JobManager is the **central brain** that orchestrates all streaming jobs but doesn't process data directly.

```
┌─────────────────────────────────────────────────────────────────┐
│                  JobManager (cpu-node1)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   Job           │    │    Checkpoint   │    │   Resource  │  │
│  │   Coordination  │    │    Coordinator  │    │   Manager   │  │
│  │                 │    │                 │    │             │  │
│  │ • Job Graph     │    │ • State Backup  │    │ • TaskMgr   │  │
│  │ • Execution     │    │ • Recovery      │    │   Registry  │  │
│  │   Graph         │    │ • Fault         │    │ • Slot      │  │
│  │ • Task Deploy   │    │   Tolerance     │    │   Alloc     │  │
│  │ • Scheduling    │    │ • Consistency   │    │ • Load Bal  │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                Job Execution Monitoring                     │  │
│  │                                                             │  │
│  │  Job 1: Kafka→Filter→Aggregate→PostgreSQL                  │  │
│  │  ├─ Status: RUNNING                                         │  │
│  │  ├─ Parallelism: 8                                          │  │
│  │  ├─ Checkpoints: Enabled (every 10s)                       │  │
│  │  └─ Backpressure: None                                      │  │
│  │                                                             │  │
│  │  Job 2: CDC→Transform→Elasticsearch                        │  │
│  │  ├─ Status: RUNNING                                         │  │
│  │  ├─ Parallelism: 4                                          │  │
│  │  ├─ Checkpoints: Enabled (every 30s)                       │  │
│  │  └─ Backpressure: Low                                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### **JobManager's Core Responsibilities:**

#### **1. Job Lifecycle Management**
- **Job Graph Creation**: Convert user programs into execution graphs
- **Task Deployment**: Distribute tasks across TaskManagers
- **Job Monitoring**: Track job progress and health
- **Job Recovery**: Restart failed jobs from checkpoints

#### **2. Checkpoint Coordination** ⭐
- **Periodic Snapshots**: Trigger consistent state snapshots
- **Recovery Management**: Restore jobs from last successful checkpoint
- **Exactly-Once Semantics**: Ensure no data loss or duplication
- **Checkpoint Storage**: Manage checkpoint metadata and locations

#### **3. Resource Management**
- **TaskManager Registration**: Accept and track available TaskManagers
- **Slot Allocation**: Assign task slots to operators
- **Load Balancing**: Distribute work evenly across resources
- **Failure Detection**: Monitor TaskManager health via heartbeats

#### **4. High Availability Configuration**
```yaml
# In your flink-conf.yaml
high-availability: zookeeper
high-availability.zookeeper.quorum: 192.168.1.184:2181,192.168.1.187:2181,192.168.1.190:2181
high-availability.storageDir: file:///home/flink/flink/ha-storage
high-availability.zookeeper.path.root: /flink

# JobManager will automatically failover to standby if configured
```

---

## ⚙️ TaskManager Architecture

### **Role: The Stream Processing Workers**

TaskManagers are the **execution engines** that process data streams in real-time across multiple parallel slots.

```
┌─────────────────────────────────────────────────────────────────┐
│               TaskManager (cpu-node2 & worker-node3)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │   Task Slots    │    │    Memory       │    │   Network   │  │
│  │   Management    │    │    Management   │    │   Buffers   │  │
│  │                 │    │                 │    │             │  │
│  │ • 4 Slots/Node  │    │ • Managed Mem   │    │ • Input     │  │
│  │ • Parallel Exec │    │ • Network Mem   │    │   Channels  │  │
│  │ • Slot Sharing  │    │ • State Backend │    │ • Output    │  │
│  │ • Isolation     │    │ • RocksDB       │    │   Buffers   │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Active Task Slots                       │  │
│  │                                                             │  │
│  │  Slot 1              │  Slot 2              │  Slot 3      │  │
│  │  ┌─────────────────┐ │  ┌─────────────────┐ │  ┌─────────┐ │  │
│  │  │ Kafka Source    │ │  │ Filter Operator │ │  │ Window  │ │  │
│  │  │ - Read Events   │ │  │ - Age > 18      │ │  │ Aggr    │ │  │
│  │  │ - Checkpointing │ │  │ - Rate: 5k/s    │ │  │ 5min    │ │  │
│  │  │ - Watermarks    │ │  │ - State: 50MB   │ │  │ window  │ │  │
│  │  └─────────────────┘ │  └─────────────────┘ │  └─────────┘ │  │
│  │                      │                      │              │  │
│  │  Slot 4              │  Available           │              │  │
│  │  ┌─────────────────┐ │  for new             │              │  │
│  │  │ PostgreSQL Sink │ │  operators           │              │  │
│  │  │ - Write Results │ │                      │              │  │
│  │  │ - Transactions  │ │                      │              │  │
│  │  │ - Retry Logic   │ │                      │              │  │
│  │  └─────────────────┘ │                      │              │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### **TaskManager's Core Responsibilities:**

#### **1. Task Execution**
- **Operator Chains**: Execute multiple operators in the same slot for efficiency
- **Streaming Processing**: Process records one-by-one in real-time
- **State Management**: Maintain operator state (keyed state, operator state)
- **Watermark Handling**: Process event-time watermarks for windowing

#### **2. Memory Management** 🧠
```yaml
# Memory allocation in your setup
taskmanager.memory.process.size: 4096m

# Breakdown:
# ├── Network Memory (10%): ~409MB - for input/output buffers
# ├── Managed Memory (40%): ~1638MB - for state backend (RocksDB)
# ├── Framework Memory: ~128MB - for Flink framework
# └── Task Memory: ~1638MB - for user code and operators
```

#### **3. Checkpoint Participation**
- **State Snapshots**: Snapshot local operator state on checkpoint triggers
- **Barrier Alignment**: Coordinate with other operators for consistent snapshots
- **State Upload**: Upload state snapshots to distributed storage
- **Recovery**: Restore state from checkpoints during failures

#### **4. Network Communication**
- **Inter-Operator Communication**: Exchange data between operators
- **Backpressure Handling**: Slow down upstream when downstream is overloaded
- **Credit-Based Flow Control**: Manage data flow efficiently
- **Partition Shuffling**: Redistribute data based on keys

---

## 🔄 Application Execution Flow

### **From Code to Real-Time Processing: The Complete Journey**

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Flink Application Lifecycle                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: Application Submission                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  flink run my_streaming_app.jar --jobmanager 192.168.1.184 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  Step 2: Job Graph Creation                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                JobManager (cpu-node1)                      │    │
│  │  ┌─────────────────┐    ┌─────────────────┐               │    │
│  │  │  DataStream API │    │  Job Graph      │               │    │
│  │  │  ├─ Source      │    │  ├─ Vertices    │               │    │
│  │  │  ├─ Transform   │    │  ├─ Edges       │               │    │
│  │  │  └─ Sink        │    │  └─ Config      │               │    │
│  │  └─────────────────┘    └─────────────────┘               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  Step 3: Execution Graph Creation & Optimization                    │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  • Parallelism Assignment: 8 parallel operators            │    │
│  │  • Operator Chaining: Combine compatible operators         │    │
│  │  • Slot Assignment: Allocate to TaskManager slots          │    │
│  │  • Resource Calculation: Memory and CPU requirements       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  Step 4: Task Deployment                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  TaskManager 1 (cpu-node2)  │  TaskManager 2 (worker-node3) │    │
│  │  ┌─────────────────┐        │  ┌─────────────────┐          │    │
│  │  │ Source Tasks    │        │  │ Transform Tasks │          │    │
│  │  │ - Kafka Reader  │        │  │ - Filter Logic  │          │    │
│  │  │ - Parallelism: 4│        │  │ - Parallelism: 4│          │    │
│  │  └─────────────────┘        │  └─────────────────┘          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  Step 5: Real-Time Stream Processing                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  ┌─ Record 1 ─►Filter─►Aggregate─►Sink─┐                   │    │
│  │  ┌─ Record 2 ─►Filter─►Aggregate─►Sink─┘                   │    │
│  │  ┌─ Record 3 ─►Filter─►Aggregate─►Sink─┐                   │    │
│  │  │                                                        │    │
│  │  • Continuous processing (never stops)                    │    │
│  │  • Event-by-event processing                              │    │
│  │  • Checkpoints every 10 seconds                           │    │
│  │  • State maintained across events                         │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎮 Flink's Execution Model

### **Understanding Jobs, Operators, and Tasks**

Unlike batch processing, Flink's execution model is designed for continuous, never-ending data streams:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Flink Execution Hierarchy                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📱 FLINK JOB                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  "Real-time Customer Analytics Pipeline"                   │    │
│  │  • Runs continuously (streaming)                           │    │
│  │  • Processes events as they arrive                         │    │
│  │  • Never completes (until explicitly stopped)             │    │
│  │  • Maintains state across events                           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  🔗 OPERATOR CHAIN (Optimized for Performance)                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Chain 1: Source → Filter → Map                            │    │
│  │  Chain 2: Window → Aggregate                               │    │
│  │  Chain 3: Sink → Database Writer                           │    │
│  │                                                            │    │
│  │  💡 Chaining reduces network overhead by combining         │    │
│  │     compatible operators in the same task slot            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ⚡ PARALLEL TASKS (One per Parallelism Level)                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Source Tasks (Parallelism: 4)                            │    │
│  │  ├─ Task 1: Read Kafka Partition 0                        │    │
│  │  ├─ Task 2: Read Kafka Partition 1                        │    │
│  │  ├─ Task 3: Read Kafka Partition 2                        │    │
│  │  └─ Task 4: Read Kafka Partition 3                        │    │
│  │                                                            │    │
│  │  Window Tasks (Parallelism: 8)                            │    │
│  │  ├─ Task 1: Process keys hash % 8 == 0                    │    │
│  │  ├─ Task 2: Process keys hash % 8 == 1                    │    │
│  │  └─ ... (one task per key range)                          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Real Example: E-Commerce Analytics**

```python
# Your Flink Streaming Application
env = StreamExecutionEnvironment.get_execution_environment()

# Step 1: Create DataStream from Kafka
orders_stream = env.add_source(
    FlinkKafkaConsumer("orders", json_schema, kafka_props)
).set_parallelism(4)  # 4 parallel Kafka readers

# Step 2: Transform data
filtered_orders = orders_stream.filter(lambda order: order['amount'] > 100)
enriched_orders = filtered_orders.map(enrich_with_customer_data)

# Step 3: Windowed aggregation  
windowed_sales = enriched_orders \
    .key_by(lambda order: order['customer_id']) \
    .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
    .aggregate(SalesAggregator()) \
    .set_parallelism(8)  # 8 parallel aggregation tasks

# Step 4: Sink to database
windowed_sales.add_sink(
    PostgreSQLSink("postgresql://192.168.1.184:5432/analytics")
).set_parallelism(2)  # 2 parallel database writers

# Execute the streaming job
env.execute("Real-time Sales Analytics")

# This creates:
# ├── 4 Source Tasks (reading Kafka)
# ├── 4 Filter+Map Tasks (chained together)  
# ├── 8 Window+Aggregate Tasks
# └── 2 Sink Tasks (writing to PostgreSQL)
# Total: 18 parallel tasks across your 8 TaskManager slots
```

### **Task Scheduling Across Your Cluster:**

```
┌─────────────────────────────────────────────────────────────────────┐
│              Task Distribution Across Your 3-Node Cluster          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  cpu-node2 (TaskManager 1)     │  worker-node3 (TaskManager 2)     │
│  ┌─────────────────┐            │  ┌─────────────────┐               │
│  │ Slot 1          │            │  │ Slot 1          │               │
│  │ Source Task 1   │            │  │ Source Task 3   │               │
│  │ (Kafka Part 0)  │            │  │ (Kafka Part 2)  │               │
│  └─────────────────┘            │  └─────────────────┘               │
│  ┌─────────────────┐            │  ┌─────────────────┐               │
│  │ Slot 2          │            │  │ Slot 2          │               │
│  │ Source Task 2   │            │  │ Source Task 4   │               │
│  │ (Kafka Part 1)  │            │  │ (Kafka Part 3)  │               │
│  └─────────────────┘            │  └─────────────────┘               │
│  ┌─────────────────┐            │  ┌─────────────────┐               │
│  │ Slot 3          │            │  │ Slot 3          │               │
│  │ Window Task 1   │            │  │ Window Task 5   │               │
│  │ (Key Range 0-1) │            │  │ (Key Range 4-5) │               │
│  └─────────────────┘            │  └─────────────────┘               │
│  ┌─────────────────┐            │  ┌─────────────────┐               │
│  │ Slot 4          │            │  │ Slot 4          │               │
│  │ Sink Task 1     │            │  │ Window Task 6   │               │
│  │ (DB Writer)     │            │  │ (Key Range 6-7) │               │
│  └─────────────────┘            │  └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────┘

Slot Sharing: Multiple operators can share the same slot if they're
from different operator chains and don't have data dependencies.
```

---

## 🧠 Memory Architecture

### **Understanding Flink's Memory Management**

Flink has a sophisticated memory management system optimized for streaming workloads with state management:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Flink Memory Architecture                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │               TaskManager Memory (4GB Total)                │    │
│  │                                                            │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │               Framework Memory                      │   │    │
│  │  │                 (~128MB)                           │   │    │
│  │  │                                                    │   │    │
│  │  │ • Flink Framework Objects                          │   │    │
│  │  │ • Network Stacks                                   │   │    │
│  │  │ • Metrics & Monitoring                             │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                            │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │               Task Heap Memory                      │   │    │
│  │  │              (~1638MB - 40%)                       │   │    │
│  │  │                                                    │   │    │
│  │  │ ┌────────────────┐  ┌────────────────────────────┐ │   │    │
│  │  │ │  User Code     │  │  Operator State Objects   │ │   │    │
│  │  │ │  Objects       │  │                            │ │   │    │
│  │  │ │                │  │ • Window State             │ │   │    │
│  │  │ │ • Custom       │  │ • Keyed State              │ │   │    │
│  │  │ │   Classes      │  │ • Broadcast State          │ │   │    │
│  │  │ • Business      │  │ • Timers                   │ │   │    │
│  │  │   Logic         │  │                            │ │   │    │
│  │  │ • Serializers   │  │   📊 Hot Path Access       │ │   │    │
│  │  │                 │  │   (Frequently Used)        │ │   │    │
│  │  │ └────────────────┘  └────────────────────────────┘ │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                            │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │              Managed Memory                         │   │    │
│  │  │             (~1638MB - 40%)                        │   │    │
│  │  │                                                    │   │    │
│  │  │ ┌──────────────────────────────────────────────┐   │   │    │
│  │  │ │           State Backend Storage              │   │   │    │
│  │  │ │            (RocksDB)                        │   │   │    │
│  │  │ │                                             │   │   │    │
│  │  │ │ • Compressed State Data                     │   │   │    │
│  │  │ │ • Write Buffers                             │   │   │    │
│  │  │ │ • Block Cache                               │   │   │    │
│  │  │ │ • Index Blocks                              │   │   │    │
│  │  │ │                                             │   │   │    │
│  │  │ │   📊 Cold Storage                           │   │   │    │
│  │  │ │   (Large State, Infrequent Access)          │   │   │    │
│  │  │ └──────────────────────────────────────────────┘   │   │    │
│  │  │                                                    │   │    │
│  │  │ ┌──────────────────────────────────────────────┐   │   │    │
│  │  │ │        Batch Operators Memory               │   │   │    │
│  │  │ │                                             │   │   │    │
│  │  │ │ • Sort Buffers                              │   │   │    │
│  │  │ │ • Hash Tables                               │   │   │    │
│  │  │ │ • Spill Files Management                    │   │   │    │
│  │  │ └──────────────────────────────────────────────┘   │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                            │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │              Network Memory                         │   │    │
│  │  │               (~410MB - 10%)                       │   │    │
│  │  │                                                    │   │    │
│  │  │ ┌────────────────┐  ┌────────────────────────────┐ │   │    │
│  │  │ │ Input Gates    │  │ Result Partitions          │ │   │    │
│  │  │ │                │  │                            │ │   │    │
│  │  │ │ • Receive      │  │ • Send Buffers             │ │   │    │
│  │  │ │   Buffers      │  │ • Backpressure            │ │   │    │
│  │  │ │ • Deserialization│ │   Management               │ │   │    │
│  │  │ │ • Flow Control │  │ • Credit-Based Flow        │ │   │    │
│  │  │ │                │  │                            │ │   │    │
│  │  │ │   📊 ~205MB    │  │   📊 ~205MB                │ │   │    │
│  │  │ └────────────────┘  └────────────────────────────┘ │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                            │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │             JVM Metaspace & Overhead                │   │    │
│  │  │                 (~410MB - 10%)                     │   │    │
│  │  │                                                    │   │    │
│  │  │ • Class Metadata                                   │   │    │
│  │  │ • GC Overhead                                      │   │    │
│  │  │ • Direct Memory                                    │   │    │
│  │  │ • Code Cache                                       │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Memory Configuration for Your Setup:**

#### **Current Configuration (Basic)**
```yaml
# In your flink-conf.yaml
taskmanager.memory.process.size: 4096m
taskmanager.memory.managed.fraction: 0.4
taskmanager.memory.network.fraction: 0.1

# Breakdown per TaskManager:
# ├── Task Memory: ~1638MB (40%)
# ├── Managed Memory: ~1638MB (40%) - for RocksDB
# ├── Network Memory: ~410MB (10%)
# └── Framework + JVM: ~410MB (10%)
```

#### **Optimized for Large State (Production)**
```yaml
# Recommended for production workloads
taskmanager.memory.process.size: 8192m
taskmanager.memory.managed.fraction: 0.6    # More for state backend
taskmanager.memory.network.fraction: 0.15   # More for network throughput
taskmanager.memory.task.heap.size: 2048m    # Fixed heap size

# State backend optimizations
state.backend.rocksdb.memory.managed: true
state.backend.rocksdb.memory.fixed-per-slot: 512MB
```

#### **Memory Monitoring Commands:**
```bash
# Check current memory usage
curl -s http://192.168.1.184:8081/taskmanagers | jq '.taskmanagers[].freeSlots'

# Monitor heap usage
curl -s http://192.168.1.184:8081/taskmanagers/{tm-id}/metrics?get=Status.JVM.Memory.Heap.Used

# Check managed memory
curl -s http://192.168.1.184:8081/taskmanagers/{tm-id}/metrics?get=Status.Flink.Memory.Managed.Used
```

---

## 🌊 Streaming Architecture & Event Time

### **Real-Time Data Processing with Event Time Semantics**

Flink's streaming architecture is built around the concept of **event time** - processing events based on when they actually occurred, not when they arrive:

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Flink Streaming Time Semantics                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📅 EVENT TIME vs PROCESSING TIME                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Event Time:    When event actually happened              │    │
│  │  ┌──────────────────────────────────────────────────────┐ │    │
│  │  │ 09:00:00  09:05:00  09:10:00  09:15:00  09:20:00     │ │    │
│  │  │    ↓         ↓         ↓         ↓         ↓        │ │    │
│  │  │  Event1    Event2   Event3    Event4    Event5      │ │    │
│  │  └──────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  Processing Time: When event arrives at Flink             │    │
│  │  ┌──────────────────────────────────────────────────────┐ │    │
│  │  │ 09:10:30  09:10:45  09:11:00  09:11:15  09:12:00     │ │    │
│  │  │    ↓         ↓         ↓         ↓         ↓        │ │    │
│  │  │  Event1    Event2   Event3    Event4    Event5      │ │    │
│  │  └──────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  💡 Event1 is 10 minutes late! But processed correctly   │    │
│  │     based on its original timestamp (09:00:00)           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  🌊 WATERMARKS: Handling Late Events                                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Watermark = "No events older than this time expected"     │    │
│  │                                                            │    │
│  │  Timeline:                                                 │    │
│  │  ├─ 09:00 ──► Event(09:00) ──► Watermark(08:55)          │    │
│  │  ├─ 09:05 ──► Event(09:05) ──► Watermark(09:00)          │    │
│  │  ├─ 09:10 ──► Event(09:10) ──► Watermark(09:05)          │    │
│  │  ├─ 09:12 ──► Event(08:58) ──► LATE EVENT!               │    │
│  │  │                             (handled by late data)     │    │
│  │  └─ 09:15 ──► Event(09:15) ──► Watermark(09:10)          │    │
│  │                                                            │    │
│  │  Window [09:00-09:05) triggers when Watermark >= 09:05    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  🪟 WINDOWING: Time-Based Data Grouping                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Tumbling Windows (Non-overlapping)                       │    │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │    │
│  │  │09:00-05 │ │09:05-10 │ │09:10-15 │ │09:15-20 │          │    │
│  │  │ Count=5 │ │ Count=8 │ │ Count=3 │ │ Count=6 │          │    │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │    │
│  │                                                            │    │
│  │  Sliding Windows (Overlapping)                            │    │
│  │  ┌─────────────────┐                                      │    │
│  │  │   09:00-10      │ ┌─────────────────┐                 │    │
│  │  │   Count=13      │ │   09:05-15      │                 │    │
│  │  └─────────────────┘ │   Count=11      │                 │    │
│  │                      └─────────────────┘                 │    │
│  │                                                            │    │
│  │  Session Windows (Activity-based)                         │    │
│  │  ┌─────┐     ┌─────────────┐          ┌────────┐         │    │
│  │  │User1│ GAP │   User1     │   GAP    │ User1  │         │    │
│  │  │Act. │     │  Activity   │          │Activity│         │    │
│  │  └─────┘     └─────────────┘          └────────┘         │    │
│  │   Session1     Session2                Session3          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Real-World Streaming Example:**

```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.common import WatermarkStrategy, Time
from pyflink.datastream.window import TumblingEventTimeWindows

env = StreamExecutionEnvironment.get_execution_environment()

# Enable event time processing
env.set_stream_time_characteristic(TimeCharacteristic.EventTime)

# Configure watermark strategy for handling late events
watermark_strategy = WatermarkStrategy \
    .for_bounded_out_of_orderness(Duration.of_seconds(20)) \
    .with_timestamp_assigner(TimestampAssigner.create(
        lambda event, ts: event['timestamp']
    ))

# Create stream from Kafka with event time
events_stream = env.add_source(
    FlinkKafkaConsumer("user-events", json_schema, kafka_props)
).assign_timestamps_and_watermarks(watermark_strategy)

# Windowed aggregation using event time
windowed_metrics = events_stream \
    .key_by(lambda event: event['user_id']) \
    .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
    .aggregate(UserActivityAggregator()) \
    .allow_lateness(Time.minutes(1))  # Handle events up to 1 min late

# Handle late events separately
late_events_stream = windowed_metrics.get_side_output(late_events_tag)

# Execute the streaming job
env.execute("Event Time Analytics")
```

### **Watermark Generation in Your Cluster:**

```
┌─────────────────────────────────────────────────────────────────────┐
│              Watermark Flow Across Your TaskManagers               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Kafka Source (cpu-node2)           Window Operator (worker-node3)  │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐  │
│  │ Partition 0: Event(09:10)   │    │ Window [09:05-09:10)        │  │
│  │ ├─ Generate Watermark(09:05)│────│►├─ Waiting for Watermark    │  │
│  │ ├─ Event(09:11)            │    │ ├─ Events: 143               │  │
│  │ └─ Generate Watermark(09:06)│────│►├─ Trigger when WM >= 09:10 │  │
│  └─────────────────────────────┘    │ └─ Current WM: 09:06        │  │
│                                     └─────────────────────────────┘  │
│  ┌─────────────────────────────┐    ┌─────────────────────────────┐  │
│  │ Partition 1: Event(09:12)   │    │ Window [09:10-09:15)        │  │
│  │ ├─ Generate Watermark(09:07)│────│►├─ Collecting events        │  │
│  │ ├─ Event(09:13)            │    │ ├─ Events: 67                │  │
│  │ └─ Generate Watermark(09:08)│────│►├─ Will trigger at WM 09:15 │  │
│  └─────────────────────────────┘    │ └─ Current WM: min(09:06,09:08)│  │
│                                     └─────────────────────────────┘  │
│                                                                     │
│  💡 Minimum Watermark Rule:                                         │
│     Window receives minimum watermark from all upstream operators   │
│     This ensures consistent event time processing across all data   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💾 State Management & Checkpointing

### **Flink's Stateful Stream Processing Engine**

One of Flink's most powerful features is its ability to maintain **exactly-once** state consistency across distributed failures:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Flink State Management Architecture              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🎯 STATE TYPES                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Keyed State (Most Common)                                 │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ Key: "user123"                                        │ │    │
│  │  │ ├─ ValueState: last_login = "2024-01-15"             │ │    │
│  │  │ ├─ ListState: recent_purchases = [item1, item2]      │ │    │
│  │  │ ├─ MapState: preferences = {lang: "en", theme: "dark"}│ │    │
│  │  │ └─ ReducingState: total_spent = $1,247.50           │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  Operator State (Broadcast, List)                         │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • Configuration rules (broadcasted to all operators)  │ │    │
│  │  │ • Kafka partition offsets                            │ │    │
│  │  │ • File reading positions                              │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  🏪 STATE BACKENDS                                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  RocksDB State Backend (Your Current Setup)               │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ ✅ Advantages:                                        │ │    │
│  │  │ • Handles TBs of state                               │ │    │
│  │  │ • Efficient for large state                          │ │    │
│  │  │ • Incremental checkpoints                           │ │    │
│  │  │ • Asynchronous snapshots                            │ │    │
│  │  │                                                      │ │    │
│  │  │ ⚠️ Trade-offs:                                       │ │    │
│  │  │ • Higher latency (disk-based)                       │ │    │
│  │  │ • More CPU overhead                                  │ │    │
│  │  │ • Serialization cost                                │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  Alternative: Heap State Backend                          │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ ✅ Advantages:                                        │ │    │
│  │  │ • Ultra-low latency                                  │ │    │
│  │  │ • No serialization overhead                          │ │    │
│  │  │ • Simple configuration                               │ │    │
│  │  │                                                      │ │    │
│  │  │ ⚠️ Limitations:                                      │ │    │
│  │  │ • Limited by heap size                               │ │    │
│  │  │ • Full checkpoint overhead                           │ │    │
│  │  │ • Not suitable for large state                       │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ⏰ CHECKPOINTING MECHANISM                                         │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Timeline of Checkpoint Process (Every 10 seconds):       │    │
│  │                                                            │    │
│  │  T+0s:  JobManager initiates checkpoint                   │    │
│  │  T+1s:  ├─ Send checkpoint barriers to sources            │    │
│  │  T+2s:  ├─ Sources inject barriers into data stream       │    │
│  │  T+3s:  ├─ Barriers flow through operator chain           │    │
│  │  T+4s:  ├─ Each operator snapshots state upon barrier     │    │
│  │  T+5s:  ├─ State uploaded to shared storage               │    │
│  │  T+6s:  ├─ All operators confirm checkpoint completion    │    │
│  │  T+7s:  └─ JobManager marks checkpoint as successful      │    │
│  │                                                            │    │
│  │  💡 Exactly-Once Guarantee:                               │    │
│  │     All operators snapshot state at the same logical time │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Checkpoint Flow Across Your Cluster:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Distributed Checkpointing Process                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: JobManager Triggers Checkpoint                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  JobManager (cpu-node1)                                    │    │
│  │  "Start Checkpoint #47 at event time 09:15:30"             │    │
│  │  ├─ Generate unique checkpoint ID                           │    │
│  │  ├─ Send checkpoint request to all sources                  │    │
│  │  └─ Start checkpoint timer (timeout: 10 minutes)           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  Step 2: Barrier Injection & Propagation                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Source Tasks (cpu-node2)    │  Window Tasks (worker-node3)  │    │
│  │  ┌─────────────────┐        │  ┌─────────────────┐          │    │
│  │  │ Kafka Source 1  │        │  │ Window Operator │          │    │
│  │  │ ├─ Snapshot:     │        │  │ ├─ Wait for     │          │    │
│  │  │ │  offset=12847  │◄───────┼──┤ │  barriers     │          │    │
│  │  │ ├─ Inject        │        │  │ ├─ Align        │          │    │
│  │  │ │  Barrier(#47)  │────────┼──┤►│  barriers     │          │    │
│  │  │ └─ Continue      │        │  │ ├─ Snapshot:    │          │    │
│  │  │    processing    │        │  │ │  window_state │          │    │
│  │  └─────────────────┘        │  │ └─ Forward      │          │    │
│  │                             │  │    Barrier(#47) │          │    │
│  │  ┌─────────────────┐        │  └─────────────────┘          │    │
│  │  │ Kafka Source 2  │        │                               │    │
│  │  │ ├─ Snapshot:     │        │  ┌─────────────────┐          │    │
│  │  │ │  offset=12853  │        │  │ Sink Operator   │          │    │
│  │  │ ├─ Inject        │        │  │ ├─ Receive       │          │    │
│  │  │ │  Barrier(#47)  │────────┼──┤►│  Barrier(#47)  │          │    │
│  │  │ └─ Continue      │        │  │ ├─ Snapshot:     │          │    │
│  │  │    processing    │        │  │ │  transaction   │          │    │
│  │  └─────────────────┘        │  │ │  state         │          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  Step 3: State Snapshot & Upload                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  State Storage (Shared across cluster)                     │    │
│  │  /home/flink/flink/checkpoints/                            │    │
│  │                                                            │    │
│  │  checkpoint-47/                                            │    │
│  │  ├─ metadata                                               │    │
│  │  ├─ task-source-1-state.snapshot                          │    │
│  │  ├─ task-source-2-state.snapshot                          │    │
│  │  ├─ task-window-1-rocksdb/                                │    │
│  │  │  ├─ sst-files/                                          │    │
│  │  │  └─ manifest                                            │    │
│  │  └─ task-sink-1-state.snapshot                            │    │
│  │                                                            │    │
│  │  💾 Total Size: 2.3GB (incremental from checkpoint-46)    │    │
│  │  ⏱️ Duration: 4.2 seconds                                 │    │
│  │  ✅ Status: COMPLETED                                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **State Configuration for Your Setup:**

```yaml
# Current configuration in flink-conf.yaml
state.backend: rocksdb
state.checkpoints.dir: file:///home/flink/flink/checkpoints
state.savepoints.dir: file:///home/flink/flink/savepoints

# Checkpoint settings
execution.checkpointing.interval: 10000ms
execution.checkpointing.timeout: 600000ms
execution.checkpointing.min-pause: 5000ms
execution.checkpointing.max-concurrent-checkpoints: 1

# RocksDB optimizations
state.backend.rocksdb.memory.managed: true
state.backend.rocksdb.memory.fixed-per-slot: 256MB
state.backend.incremental: true
```

### **Practical State Management Examples:**

```python
# Example 1: User Session Tracking
class UserSessionProcessor(KeyedProcessFunction):
    def __init__(self):
        self.session_state = None  # ValueState[UserSession]
        self.last_activity = None  # ValueState[Long]
        
    def open(self, config):
        # Initialize state descriptors
        session_descriptor = ValueStateDescriptor(
            "user_session", UserSession, UserSession.empty()
        )
        self.session_state = self.get_runtime_context().get_state(session_descriptor)
        
        activity_descriptor = ValueStateDescriptor(
            "last_activity", Long, 0L
        )
        self.last_activity = self.get_runtime_context().get_state(activity_descriptor)
    
    def process_element(self, event, ctx, out):
        current_session = self.session_state.value()
        last_time = self.last_activity.value()
        
        # Session timeout: 30 minutes
        if event.timestamp - last_time > 30 * 60 * 1000:
            # Start new session
            current_session = UserSession.new(event.user_id, event.timestamp)
        
        # Update session with current event
        current_session.add_event(event)
        
        # Update state
        self.session_state.update(current_session)
        self.last_activity.update(event.timestamp)
        
        # Set timer for session timeout
        ctx.timer_service().register_event_time_timer(
            event.timestamp + 30 * 60 * 1000
        )
        
        out.collect(current_session)

# Example 2: Real-time Feature Store
class FeatureStoreProcessor(CoProcessFunction):
    def __init__(self):
        self.features = None  # MapState[String, FeatureValue]
        
    def open(self, config):
        feature_descriptor = MapStateDescriptor(
            "user_features", String, FeatureValue
        )
        self.features = self.get_runtime_context().get_map_state(feature_descriptor)
    
    def process_element1(self, feature_update, ctx, out):
        # Stream 1: Feature updates
        self.features.put(feature_update.feature_name, feature_update.value)
    
    def process_element2(self, prediction_request, ctx, out):
        # Stream 2: Prediction requests
        user_features = {}
        for feature_name in prediction_request.required_features:
            value = self.features.get(feature_name)
            if value is not None:
                user_features[feature_name] = value
        
        prediction = self.predict(user_features)
        out.collect(PredictionResult(prediction_request.user_id, prediction))
```

---

## 🌊 Watermarks & Late Data Handling

### **Advanced Event Time Processing**

Watermarks are critical for handling real-world data streams where events don't arrive in perfect order:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Watermark Strategies & Late Data               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🎯 WATERMARK STRATEGIES                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  1. Bounded Out-of-Orderness (Most Common)                │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • Assumption: Events arrive within X seconds/minutes  │ │    │
│  │  │ • Watermark = max(event_time) - max_out_of_orderness │ │    │
│  │  │ • Good for: Network delays, system hiccups           │ │    │
│  │  │                                                      │ │    │
│  │  │ Example: Max 30 seconds late                         │ │    │
│  │  │ Event time: 09:10:00 → Watermark: 09:09:30          │ │    │
│  │  │ Event time: 09:10:15 → Watermark: 09:09:45          │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  2. Periodic Watermarks                                   │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • Generate watermarks at regular intervals            │ │    │
│  │  │ • Good for: High-throughput, regular event patterns  │ │    │
│  │  │ • Configure: auto.watermark.interval (default 200ms) │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  3. Punctuated Watermarks                                 │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • Generate watermarks based on event content          │ │    │
│  │  │ • Good for: Special marker events, end-of-batch      │ │    │
│  │  │ • Example: "heartbeat" events from IoT devices       │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  🕐 LATE DATA HANDLING STRATEGIES                                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Strategy 1: Allowed Lateness                             │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ window.allowedLateness(Time.minutes(5))               │ │    │
│  │  │                                                      │ │    │
│  │  │ Timeline:                                            │ │    │
│  │  │ 09:00-09:05 window                                   │ │    │
│  │  │ ├─ 09:06: Watermark triggers window                  │ │    │
│  │  │ ├─ 09:07: Late event → Update + re-emit result      │ │    │
│  │  │ ├─ 09:09: Another late event → Update + re-emit     │ │    │
│  │  │ └─ 09:11: Window finally closed (5 min lateness)    │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  Strategy 2: Side Outputs for Late Events                 │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ val lateTag = OutputTag[Event]("late-events")        │ │    │
│  │  │                                                      │ │    │
│  │  │ Main Stream:    [Window Results]                     │ │    │
│  │  │     ↓                                                │ │    │
│  │  │ Side Output:    [Late Events] → Separate Processing  │ │    │
│  │  │                                                      │ │    │
│  │  │ • Log late events for analysis                       │ │    │
│  │  │ • Store in separate table                            │ │    │
│  │  │ • Alert on high late event rates                     │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Practical Watermark Configuration:**

```python
from pyflink.common import WatermarkStrategy, Duration
from pyflink.datastream.window import TumblingEventTimeWindows

# Strategy 1: Bounded out-of-orderness (most common)
watermark_strategy = WatermarkStrategy \
    .for_bounded_out_of_orderness(Duration.of_seconds(30)) \
    .with_timestamp_assigner(lambda event, ts: event['event_time'])

# Strategy 2: Custom watermark generator
class CustomWatermarkGenerator(WatermarkGenerator):
    def __init__(self, max_out_of_orderness):
        self.max_out_of_orderness = max_out_of_orderness
        self.current_max_timestamp = Long.MIN_VALUE
    
    def on_event(self, event, event_timestamp, output):
        self.current_max_timestamp = max(self.current_max_timestamp, event_timestamp)
    
    def on_periodic_emit(self, output):
        watermark_timestamp = self.current_max_timestamp - self.max_out_of_orderness - 1
        output.emit_watermark(Watermark(watermark_timestamp))

# Apply watermark strategy
events_stream = kafka_source.assign_timestamps_and_watermarks(watermark_strategy)

# Handle late events with allowed lateness
late_event_tag = OutputTag("late-events", Types.of(Event))

windowed_stream = events_stream \
    .key_by(lambda e: e['user_id']) \
    .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
    .allowed_lateness(Time.minutes(2)) \
    .side_output_late_data(late_event_tag) \
    .aggregate(EventAggregator())

# Process late events separately
late_events = windowed_stream.get_side_output(late_event_tag)
late_events.add_sink(late_events_kafka_sink)
```

---

## 📊 Flink SQL & Table API

### **Declarative Stream Processing**

Flink SQL provides a high-level, declarative interface for stream processing that automatically handles many low-level concerns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Flink SQL Architecture                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📝 SQL LAYER                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  CREATE TABLE kafka_source (                               │    │
│  │    user_id INT,                                            │    │
│  │    product_id STRING,                                      │    │
│  │    amount DECIMAL(10,2),                                   │    │
│  │    event_time TIMESTAMP(3),                                │    │
│  │    WATERMARK FOR event_time AS                             │    │
│  │      event_time - INTERVAL '30' SECOND                     │    │
│  │  ) WITH (                                                  │    │
│  │    'connector' = 'kafka',                                  │    │
│  │    'topic' = 'user-events',                                │    │
│  │    'properties.bootstrap.servers' = '192.168.1.184:9092'   │    │
│  │  );                                                        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  🔧 QUERY OPTIMIZATION                                              │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Calcite-based Query Optimizer:                           │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ 1. Parse SQL → Logical Plan                          │ │    │
│  │  │ 2. Apply Optimization Rules:                         │ │    │
│  │  │    • Predicate Pushdown                              │ │    │
│  │  │    • Projection Pushdown                             │ │    │
│  │  │    • Join Reordering                                 │ │    │
│  │  │    • Constant Folding                                │ │    │
│  │  │ 3. Generate Streaming Physical Plan                  │ │    │
│  │  │ 4. Convert to DataStream Operations                  │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                      │
│                              ▼                                      │
│  ⚡ EXECUTION LAYER                                                  │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Generated DataStream Job:                                 │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ Source (Kafka)                                        │ │    │
│  │  │     ↓                                                 │ │    │
│  │  │ Watermark Assigner                                    │ │    │
│  │  │     ↓                                                 │ │    │
│  │  │ Filter/Map Operations                                 │ │    │
│  │  │     ↓                                                 │ │    │
│  │  │ Window Aggregation                                    │ │    │
│  │  │     ↓                                                 │ │    │
│  │  │ Sink (Database/Kafka)                                 │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Real-World SQL Examples for Your Setup:**

#### **Example 1: Real-time Sales Analytics**
```sql
-- Connect to Flink SQL CLI: ./bin/sql-client.sh

-- Create Kafka source table for order events
CREATE TABLE order_events (
    order_id BIGINT,
    user_id INT,
    product_id STRING,
    amount DECIMAL(10,2),
    category STRING,
    event_time TIMESTAMP(3),
    WATERMARK FOR event_time AS event_time - INTERVAL '30' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'order-events',
    'properties.bootstrap.servers' = '192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092',
    'properties.group.id' = 'flink-sql-analytics',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json'
);

-- Create PostgreSQL sink table for analytics results
CREATE TABLE hourly_sales_metrics (
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    category STRING,
    total_orders BIGINT,
    total_revenue DECIMAL(12,2),
    avg_order_value DECIMAL(10,2),
    unique_customers BIGINT,
    PRIMARY KEY (window_start, category) NOT ENFORCED
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://192.168.1.184:5432/analytics_db',
    'table-name' = 'hourly_sales_metrics',
    'username' = 'dataeng',
    'password' = 'password',
    'sink.buffer-flush.max-rows' = '1000',
    'sink.buffer-flush.interval' = '10s'
);

-- Real-time hourly sales aggregation
INSERT INTO hourly_sales_metrics
SELECT 
    TUMBLE_START(event_time, INTERVAL '1' HOUR) as window_start,
    TUMBLE_END(event_time, INTERVAL '1' HOUR) as window_end,
    category,
    COUNT(*) as total_orders,
    SUM(amount) as total_revenue,
    AVG(amount) as avg_order_value,
    COUNT(DISTINCT user_id) as unique_customers
FROM order_events
WHERE amount > 0
GROUP BY 
    TUMBLE(event_time, INTERVAL '1' HOUR),
    category;
```

#### **Example 2: Real-time Fraud Detection**
```sql
-- Create user behavior pattern table
CREATE TABLE user_behavior_patterns (
    user_id INT,
    pattern_type STRING,
    avg_amount DECIMAL(10,2),
    location_pattern STRING,
    update_time TIMESTAMP(3),
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://192.168.1.184:5432/analytics_db',
    'table-name' = 'user_behavior_patterns',
    'username' = 'dataeng',
    'password' = 'password'
);

-- Create alerts table for anomalies
CREATE TABLE fraud_alerts (
    alert_id STRING,
    user_id INT,
    order_id BIGINT,
    alert_type STRING,
    confidence_score DECIMAL(3,2),
    alert_time TIMESTAMP(3)
) WITH (
    'connector' = 'kafka',
    'topic' = 'fraud-alerts',
    'properties.bootstrap.servers' = '192.168.1.184:9092',
    'format' = 'json'
);

-- Temporal join for real-time fraud detection
INSERT INTO fraud_alerts
SELECT 
    CONCAT('fraud_', CAST(o.order_id AS STRING)) as alert_id,
    o.user_id,
    o.order_id,
    CASE 
        WHEN o.amount > p.avg_amount * 5 THEN 'AMOUNT_ANOMALY'
        WHEN o.amount > 10000 THEN 'HIGH_VALUE_TRANSACTION'
        ELSE 'PATTERN_DEVIATION'
    END as alert_type,
    CASE 
        WHEN o.amount > p.avg_amount * 10 THEN 0.95
        WHEN o.amount > p.avg_amount * 5 THEN 0.80
        ELSE 0.60
    END as confidence_score,
    o.event_time as alert_time
FROM order_events o
LEFT JOIN user_behavior_patterns FOR SYSTEM_TIME AS OF o.event_time AS p
    ON o.user_id = p.user_id
WHERE 
    o.amount > 1000 AND (
        p.avg_amount IS NULL OR 
        o.amount > p.avg_amount * 3
    );
```

#### **Example 3: CDC-powered Real-time Data Pipeline**
```sql
-- Create CDC source for PostgreSQL user table
CREATE TABLE user_changes_cdc (
    user_id INT,
    username STRING,
    email STRING,
    status STRING,
    created_at TIMESTAMP(3),
    updated_at TIMESTAMP(3),
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'postgres-cdc',
    'hostname' = '192.168.1.184',
    'port' = '5432',
    'username' = 'cdc_user',
    'password' = 'cdc_password123',
    'database-name' = 'analytics_db',
    'schema-name' = 'public',
    'table-name' = 'users',
    'slot.name' = 'flink_cdc_user_slot'
);

-- Create enriched user events stream
CREATE TABLE enriched_events AS
SELECT 
    o.order_id,
    o.user_id,
    u.username,
    u.email,
    u.status as user_status,
    o.amount,
    o.category,
    o.event_time
FROM order_events o
LEFT JOIN user_changes_cdc FOR SYSTEM_TIME AS OF o.event_time AS u
    ON o.user_id = u.user_id;

-- Stream enriched events to analytics warehouse
CREATE TABLE enriched_events_sink (
    order_id BIGINT,
    user_id INT,
    username STRING,
    email STRING,
    user_status STRING,
    amount DECIMAL(10,2),
    category STRING,
    event_time TIMESTAMP(3)
) WITH (
    'connector' = 'elasticsearch',
    'hosts' = 'http://192.168.1.184:9200',
    'index' = 'enriched-orders-{yyyy-MM-dd}',
    'document-type' = '_doc',
    'sink.bulk-flush.max-actions' = '1000',
    'sink.bulk-flush.interval' = '10s'
);

INSERT INTO enriched_events_sink
SELECT * FROM enriched_events;
```

---

## 🔗 Integration Patterns

### **Connecting Flink with Your Data Ecosystem**

Flink excels at integrating with various data systems in your infrastructure:

```
┌─────────────────────────────────────────────────────────────────────┐
│                 Flink Integration Ecosystem                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  📥 SOURCES (Data Input)                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Message Queues:                                           │    │
│  │  ├─ Apache Kafka (Your Setup)      ─► Streaming Events    │    │
│  │  ├─ Apache Pulsar                  ─► Event Streams       │    │
│  │  ├─ RabbitMQ                       ─► Message Processing  │    │
│  │  └─ AWS Kinesis                    ─► Cloud Streaming     │    │
│  │                                                            │    │
│  │  Databases:                                                │    │
│  │  ├─ PostgreSQL CDC (Your Setup)    ─► Change Streams      │    │
│  │  ├─ MySQL Binlog                   ─► Database Changes    │    │
│  │  ├─ Oracle CDC                     ─► Enterprise Changes  │    │
│  │  └─ MongoDB Change Streams         ─► Document Changes    │    │
│  │                                                            │    │
│  │  File Systems:                                             │    │
│  │  ├─ HDFS                          ─► Batch Files          │    │
│  │  ├─ S3                            ─► Cloud Storage        │    │
│  │  ├─ Local Files                   ─► Development/Testing  │    │
│  │  └─ Network File Systems          ─► Shared Storage       │    │
│  │                                                            │    │
│  │  Real-time APIs:                                           │    │
│  │  ├─ TCP/UDP Sockets               ─► Network Streams      │    │
│  │  ├─ WebSocket                     ─► Real-time Feeds      │    │
│  │  └─ HTTP APIs                     ─► REST Endpoints       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  📤 SINKS (Data Output)                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Analytics Databases:                                      │    │
│  │  ├─ PostgreSQL (Your Setup)       ─► Structured Analytics │    │
│  │  ├─ ClickHouse                    ─► OLAP Queries        │    │
│  │  ├─ Apache Druid                  ─► Real-time Analytics  │    │
│  │  └─ TimescaleDB                   ─► Time Series Data     │    │
│  │                                                            │    │
│  │  Search & Analytics:                                       │    │
│  │  ├─ Elasticsearch (Your Setup)    ─► Search & Analytics   │    │
│  │  ├─ Apache Solr                   ─► Search Platform      │    │
│  │  └─ OpenSearch                    ─► Open Source Search   │    │
│  │                                                            │    │
│  │  Data Warehouses:                                          │    │
│  │  ├─ Apache Iceberg                ─► Data Lake Tables     │    │
│  │  ├─ Delta Lake                    ─► ACID Transactions    │    │
│  │  ├─ Apache Hudi                   ─► Incremental Updates  │    │
│  │  └─ Parquet Files                 ─► Columnar Storage     │    │
│  │                                                            │    │
│  │  Message Systems:                                          │    │
│  │  ├─ Kafka (Your Setup)            ─► Event Publishing     │    │
│  │  ├─ Redis                         ─► Caching Layer       │    │
│  │  └─ Apache Pulsar                 ─► Event Distribution   │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Advanced Integration Examples:**

#### **1. Kafka → Flink → PostgreSQL Analytics Pipeline**
```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment
from pyflink.table.descriptors import (
    Kafka, Json, Schema, Rowtime, FileSystem, OldCsv
)

env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(4)
t_env = StreamTableEnvironment.create(env)

# Configure Kafka source
t_env.execute_sql("""
    CREATE TABLE kafka_events (
        event_id STRING,
        user_id INT,
        event_type STRING,
        event_data ROW<
            page STRING,
            duration INT,
            source STRING
        >,
        event_time TIMESTAMP(3),
        WATERMARK FOR event_time AS event_time - INTERVAL '10' SECOND
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'user-events',
        'properties.bootstrap.servers' = '192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092',
        'properties.group.id' = 'analytics-consumer',
        'scan.startup.mode' = 'latest-offset',
        'format' = 'json',
        'json.fail-on-missing-field' = 'false',
        'json.ignore-parse-errors' = 'true'
    )
""")

# Configure PostgreSQL sink with proper connection pooling
t_env.execute_sql("""
    CREATE TABLE user_analytics (
        window_start TIMESTAMP(3),
        window_end TIMESTAMP(3),
        user_id INT,
        page_views BIGINT,
        total_duration BIGINT,
        avg_duration DOUBLE,
        unique_pages BIGINT,
        PRIMARY KEY (window_start, user_id) NOT ENFORCED
    ) WITH (
        'connector' = 'jdbc',
        'url' = 'jdbc:postgresql://192.168.1.184:5432/analytics_db',
        'table-name' = 'user_analytics',
        'username' = 'dataeng',
        'password' = 'dataeng_password',
        'sink.buffer-flush.max-rows' = '1000',
        'sink.buffer-flush.interval' = '30s',
        'sink.max-retries' = '3',
        'connection.max-retry-timeout' = '60s'
    )
""")

# Real-time user behavior analytics
t_env.execute_sql("""
    INSERT INTO user_analytics
    SELECT 
        TUMBLE_START(event_time, INTERVAL '5' MINUTE) as window_start,
        TUMBLE_END(event_time, INTERVAL '5' MINUTE) as window_end,
        user_id,
        COUNT(*) as page_views,
        SUM(event_data.duration) as total_duration,
        AVG(CAST(event_data.duration AS DOUBLE)) as avg_duration,
        COUNT(DISTINCT event_data.page) as unique_pages
    FROM kafka_events
    WHERE event_type = 'page_view' 
      AND event_data.duration IS NOT NULL
    GROUP BY 
        TUMBLE(event_time, INTERVAL '5' MINUTE),
        user_id
""")
```

#### **2. PostgreSQL CDC → Flink → Multiple Sinks**
```python
# Multi-sink architecture for real-time data distribution
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment

env = StreamExecutionEnvironment.get_execution_environment()
env.enable_checkpointing(10000)  # 10 second checkpoints
t_env = StreamTableEnvironment.create(env)

# PostgreSQL CDC source for orders table
t_env.execute_sql("""
    CREATE TABLE orders_cdc (
        order_id BIGINT,
        customer_id INT,
        product_id STRING,
        quantity INT,
        price DECIMAL(10,2),
        order_status STRING,
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3),
        PRIMARY KEY (order_id) NOT ENFORCED
    ) WITH (
        'connector' = 'postgres-cdc',
        'hostname' = '192.168.1.184',
        'port' = '5432',
        'username' = 'cdc_user',
        'password' = 'cdc_password123',
        'database-name' = 'analytics_db',
        'schema-name' = 'public',
        'table-name' = 'orders',
        'slot.name' = 'orders_cdc_slot'
    )
""")

# Kafka sink for real-time order events
t_env.execute_sql("""
    CREATE TABLE orders_stream (
        order_id BIGINT,
        customer_id INT,
        product_id STRING,
        order_value DECIMAL(12,2),
        order_status STRING,
        event_timestamp TIMESTAMP(3)
    ) WITH (
        'connector' = 'kafka',
        'topic' = 'order-stream',
        'properties.bootstrap.servers' = '192.168.1.184:9092',
        'format' = 'json',
        'sink.partitioner' = 'fixed'
    )
""")

# Elasticsearch sink for search and analytics
t_env.execute_sql("""
    CREATE TABLE orders_search (
        order_id BIGINT,
        customer_id INT,
        product_id STRING,
        order_value DECIMAL(12,2),
        order_status STRING,
        created_at TIMESTAMP(3),
        updated_at TIMESTAMP(3)
    ) WITH (
        'connector' = 'elasticsearch-7',
        'hosts' = 'http://192.168.1.184:9200',
        'index' = 'orders-{yyyy-MM-dd}',
        'sink.bulk-flush.max-actions' = '1000',
        'sink.bulk-flush.interval' = '10s',
        'sink.bulk-flush.backoff.enable' = 'true'
    )
""")

# Redis sink for caching layer
t_env.execute_sql("""
    CREATE TABLE orders_cache (
        order_id BIGINT,
        order_data STRING
    ) WITH (
        'connector' = 'redis',
        'host' = '192.168.1.184',
        'port' = '6379',
        'redis-mode' = 'single',
        'key.column' = 'order_id',
        'value.column' = 'order_data',
        'sink.max-retries' = '3'
    )
""")

# Stream processing with multiple outputs
t_env.execute_sql("""
    -- Stream order changes to Kafka
    INSERT INTO orders_stream
    SELECT 
        order_id,
        customer_id,
        product_id,
        quantity * price as order_value,
        order_status,
        COALESCE(updated_at, created_at) as event_timestamp
    FROM orders_cdc
    WHERE order_status IN ('confirmed', 'shipped', 'delivered', 'cancelled')
""")

t_env.execute_sql("""
    -- Index orders in Elasticsearch
    INSERT INTO orders_search
    SELECT * FROM orders_cdc
    WHERE order_status <> 'draft'
""")

t_env.execute_sql("""
    -- Cache recent orders in Redis
    INSERT INTO orders_cache
    SELECT 
        order_id,
        CONCAT('{"customer_id":', CAST(customer_id AS STRING), 
               ',"total":', CAST(quantity * price AS STRING), 
               ',"status":"', order_status, '"}') as order_data
    FROM orders_cdc
    WHERE order_status = 'confirmed'
      AND COALESCE(updated_at, created_at) > CURRENT_TIMESTAMP - INTERVAL '1' HOUR
""")
```

#### **3. Advanced Machine Learning Integration**
```python
# Real-time feature engineering and ML inference
import json
from pyflink.common import Row
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import MapFunction, ProcessFunction

class FeatureExtractor(MapFunction):
    def map(self, event):
        # Extract features for ML model
        features = {
            'user_id': event['user_id'],
            'hour_of_day': event['timestamp'].hour,
            'day_of_week': event['timestamp'].weekday(),
            'amount': float(event['amount']),
            'merchant_category': event['merchant_category'],
            'location_risk_score': self.get_location_risk(event['location']),
            'user_velocity': self.calculate_velocity(event['user_id'], event['timestamp'])
        }
        return Row(**features)
    
    def get_location_risk(self, location):
        # Simple risk scoring based on location
        high_risk_locations = ['foreign', 'atm', 'online']
        return 0.8 if location in high_risk_locations else 0.2
    
    def calculate_velocity(self, user_id, timestamp):
        # Calculate transaction velocity (simplified)
        # In practice, this would use state to track user history
        return 1.0  # Placeholder

class MLInferenceFunction(ProcessFunction):
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
    
    def open(self, runtime_context):
        # Load ML model (TensorFlow, PyTorch, Scikit-learn, etc.)
        import joblib
        self.model = joblib.load(self.model_path)
    
    def process_element(self, features, ctx, out):
        # Prepare feature vector
        feature_vector = [
            features.hour_of_day,
            features.day_of_week,
            features.amount,
            features.location_risk_score,
            features.user_velocity
        ]
        
        # Make prediction
        fraud_probability = self.model.predict_proba([feature_vector])[0][1]
        
        # Emit result with threshold
        if fraud_probability > 0.7:
            alert = Row(
                user_id=features.user_id,
                fraud_score=fraud_probability,
                alert_type='high_risk',
                timestamp=ctx.timestamp()
            )
            out.collect(alert)

# Set up the streaming pipeline
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(4)

# Source: Transaction events from Kafka
transaction_stream = env.add_source(
    FlinkKafkaConsumer(
        "transactions", 
        json_deserializer, 
        kafka_properties
    )
)

# Feature engineering
features_stream = transaction_stream.map(FeatureExtractor())

# ML inference
fraud_alerts = features_stream.process(
    MLInferenceFunction("/path/to/fraud_model.pkl")
)

# Sink: Fraud alerts to multiple destinations
fraud_alerts.add_sink(
    FlinkKafkaProducer("fraud-alerts", json_serializer, kafka_properties)
)

fraud_alerts.add_sink(
    JdbcSink.sink(
        "INSERT INTO fraud_alerts (user_id, fraud_score, alert_type, timestamp) VALUES (?, ?, ?, ?)",
        fraud_alert_statement_builder,
        jdbc_connection_options
    )
)

env.execute("Real-time Fraud Detection with ML")
```

---

## 📈 Scaling Your Setup

### **Horizontal Scaling Strategies**

Your current 3-node setup provides an excellent foundation that can be expanded systematically:

#### **Current State (3 Nodes)**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   cpu-node1     │    │   cpu-node2     │    │ worker-node3    │
│  (JobManager)   │    │ (TaskManager 1) │    │ (TaskManager 2) │
│                 │    │                 │    │                 │
│ • Coordination  │    │ • 4 Slots       │    │ • 4 Slots       │
│ • Checkpointing │    │ • 4GB Memory    │    │ • 4GB Memory    │
│ • Web UI:8081   │    │ • RocksDB State │    │ • RocksDB State │
│ • Resource Mgmt │    │ • Network I/O   │    │ • Network I/O   │
└─────────────────┘    └─────────────────┘    └─────────────────┘

Total Capacity: 8 task slots, 8GB processing memory
Suitable for: Development, small-scale production (< 100k events/sec)
```

#### **Scaling Path 1: Adding More TaskManagers (5 Nodes)**
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   cpu-node1     │  │   cpu-node2     │  │ worker-node3    │  │ worker-node4    │  │ worker-node5    │
│  (JobManager)   │  │ (TaskManager 1) │  │ (TaskManager 2) │  │ (TaskManager 3) │  │ (TaskManager 4) │
│                 │  │                 │  │                 │  │    NEW!         │  │    NEW!         │
│ • Coordination  │  │ • 4 Slots       │  │ • 4 Slots       │  │ • 4 Slots       │  │ • 4 Slots       │
│ • Checkpointing │  │ • 4GB Memory    │  │ • 4GB Memory    │  │ • 4GB Memory    │  │ • 4GB Memory    │
│ • Web UI:8081   │  │ • Processing    │  │ • Processing    │  │ • Processing    │  │ • Processing    │
│ • Resource Mgmt │  │ • State Storage │  │ • State Storage │  │ • State Storage │  │ • State Storage │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘

Total Capacity: 16 task slots, 16GB processing memory
Suitable for: Medium-scale production (100k-500k events/sec)
```

#### **Scaling Path 2: High Availability Setup (6 Nodes)**
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   cpu-node1     │  │   cpu-node2     │  │ worker-node3    │  │   zk-node1      │
│(Active JobMgr)  │  │(Standby JobMgr) │  │ (TaskManager 1) │  │  (ZooKeeper)    │
│                 │  │                 │  │                 │  │                 │
│ • Active Coord  │  │ • Backup Ready  │  │ • 8 Slots       │  │ • Leader Elect  │
│ • Checkpointing │  │ • Monitoring    │  │ • 8GB Memory    │  │ • State Store   │
│ • Web UI:8081   │  │ • Web UI:8082   │  │ • Processing    │  │ • Config Mgmt   │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘

┌─────────────────┐  ┌─────────────────┐
│ worker-node4    │  │ worker-node5    │  
│ (TaskManager 2) │  │ (TaskManager 3) │
│                 │  │                 │
│ • 8 Slots       │  │ • 8 Slots       │
│ • 8GB Memory    │  │ • 8GB Memory    │
│ • Processing    │  │ • Processing    │
└─────────────────┘  └─────────────────┘

Total Capacity: 24 task slots, 24GB memory + High Availability
Suitable for: Production workloads requiring 99.9% uptime
```

### **Step-by-Step Scaling Guide:**

#### **Adding TaskManager Nodes:**

**1. Prepare New Node (worker-node4):**
```bash
# Install Java and create flink user
sudo apt update && sudo apt install -y openjdk-11-jdk
sudo useradd -m -s /bin/bash flink
sudo usermod -aG sudo flink

# Setup SSH access from JobManager
# (Run on cpu-node1 as flink user)
ssh-copy-id flink@192.168.1.191  # Assuming worker-node4 IP

# Install Flink on new node
sudo su - flink
cd /home/flink
wget https://downloads.apache.org/flink/flink-1.18.0/flink-1.18.0-bin-scala_2.12.tgz
tar -xzf flink-1.18.0-bin-scala_2.12.tgz
mv flink-1.18.0 flink
rm flink-1.18.0-bin-scala_2.12.tgz
```

**2. Configure TaskManager:**
```bash
# Copy configuration from existing TaskManager
scp -r flink@192.168.1.187:/home/flink/flink/conf/* /home/flink/flink/conf/

# Create necessary directories
mkdir -p /home/flink/flink/{ha-storage,checkpoints,savepoints,web-uploads,logs}

# Set environment variables
echo 'export FLINK_HOME=/home/flink/flink' >> ~/.bashrc
echo 'export PATH=$PATH:$FLINK_HOME/bin' >> ~/.bashrc
source ~/.bashrc
```

**3. Start TaskManager:**
```bash
# Start TaskManager service
cd $FLINK_HOME
./bin/taskmanager.sh start

# Verify registration with JobManager
curl -s http://192.168.1.184:8081/taskmanagers | jq '.taskmanagers[].id'
```

**4. Update firewall:**
```bash
sudo ufw allow from 192.168.1.0/24 to any port 6122
sudo ufw allow from 192.168.1.0/24 to any port 8081
sudo ufw reload
```

#### **Optimizing for Larger Scale:**

**Memory Configuration for Production:**
```yaml
# Upgrade TaskManager memory for production workloads
# Edit flink-conf.yaml on all TaskManagers

# For 16GB RAM nodes:
taskmanager.memory.process.size: 12288m  # 12GB total
taskmanager.memory.managed.fraction: 0.6 # 7.2GB for state backend
taskmanager.memory.network.fraction: 0.15 # 1.8GB for network
taskmanager.numberOfTaskSlots: 8         # More slots per node

# For high-throughput streaming:
taskmanager.network.numberOfBuffers: 4096
taskmanager.network.memory.buffers-per-channel: 16
taskmanager.network.memory.floating-buffers-per-gate: 32
```

**JobManager Scaling Configuration:**
```yaml
# Increase JobManager memory for larger clusters
jobmanager.memory.process.size: 4096m
jobmanager.memory.jvm-overhead.fraction: 0.1

# Optimize for more concurrent jobs
jobmanager.execution.failover-strategy: region
scheduler-mode: reactive

# Enhanced checkpointing for scale
execution.checkpointing.interval: 30000ms
execution.checkpointing.timeout: 900000ms
state.checkpoints.num-retained: 5
```

### **Auto-Scaling with Reactive Mode:**

#### **Enable Reactive Scheduling:**
```yaml
# Add to flink-conf.yaml
scheduler-mode: reactive
execution.checkpointing.interval: 10000ms

# This allows Flink to automatically adjust parallelism
# when TaskManagers are added or removed dynamically
```

#### **Dynamic TaskManager Addition:**
```bash
# Add TaskManager without stopping jobs
# On new node:
./bin/taskmanager.sh start

# Flink automatically detects and integrates new resources
# Current jobs will rescale to use additional capacity

# Remove TaskManager gracefully:
./bin/taskmanager.sh stop
# Jobs automatically rescale to remaining resources
```

### **Performance Optimization Strategies:**

#### **🥉 Bronze Level: Basic Optimizations**

**1. Parallelism Tuning:**
```python
# Set appropriate parallelism for your cluster
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(16)  # Match your total available slots

# Or configure per operator
stream.filter(my_filter).set_parallelism(8)  # CPU-intensive
stream.map(my_mapper).set_parallelism(16)    # Balanced
stream.sink(my_sink).set_parallelism(4)      # I/O-intensive
```

**2. Checkpoint Optimization:**
```yaml
# Optimize checkpoint performance
execution.checkpointing.interval: 30000ms    # 30 seconds for production
execution.checkpointing.timeout: 600000ms    # 10 minutes timeout
state.backend.incremental: true              # Incremental RocksDB checkpoints
state.checkpoints.num-retained: 3            # Keep last 3 checkpoints
```

**3. Network Buffer Tuning:**
```yaml
# Increase network buffers for high throughput
taskmanager.network.numberOfBuffers: 8192
taskmanager.memory.network.fraction: 0.2
taskmanager.network.memory.buffers-per-channel: 32
```

#### **🥈 Silver Level: Advanced Optimizations**

**1. State Backend Optimization:**
```yaml
# RocksDB tuning for large state
state.backend.rocksdb.memory.managed: true
state.backend.rocksdb.memory.fixed-per-slot: 1024MB
state.backend.rocksdb.block.cache-size: 512MB
state.backend.rocksdb.write-buffer-size: 128MB
state.backend.rocksdb.max-background-jobs: 4

# Enable compression for storage efficiency
state.backend.rocksdb.compression.per.level: LZ4_COMPRESSION,LZ4_COMPRESSION,LZ4_COMPRESSION,ZSTD_COMPRESSION,ZSTD_COMPRESSION,ZSTD_COMPRESSION,ZSTD_COMPRESSION
```

**2. Advanced Memory Management:**
```yaml
# Fine-tune memory allocation
taskmanager.memory.task.heap.size: 2048m
taskmanager.memory.managed.size: 4096m
taskmanager.memory.framework.heap.size: 256m

# Enable off-heap memory for large datasets
taskmanager.memory.task.off-heap.size: 1024m
```

**3. Operator Chain Optimization:**
```python
# Control operator chaining for performance
stream.filter(lambda x: x.value > 0) \
    .disable_chaining() \  # Force separate task
    .map(lambda x: x.value * 2) \
    .start_new_chain() \   # Start new chain here
    .key_by(lambda x: x.user_id) \
    .window(TumblingEventTimeWindows.of(Time.minutes(5))) \
    .aggregate(MyAggregator())
```

#### **🥇 Gold Level: Expert Optimizations**

**1. Custom Resource Profiles:**
```python
# Define resource profiles for different operators
light_profile = ResourceProfile.new_builder() \
    .set_cpu_cores(0.5) \
    .set_task_heap_memory(MemorySize.parse("512MB")) \
    .set_managed_memory(MemorySize.parse("256MB")) \
    .build()

heavy_profile = ResourceProfile.new_builder() \
    .set_cpu_cores(2.0) \
    .set_task_heap_memory(MemorySize.parse("2GB")) \
    .set_managed_memory(MemorySize.parse("1GB")) \
    .build()

# Apply profiles to operators
stream.filter(lightweight_filter).slot_sharing_group("light", light_profile)
stream.window(...).aggregate(heavy_aggregator).slot_sharing_group("heavy", heavy_profile)
```

**2. Backpressure Management:**
```yaml
# Configure backpressure handling
execution.buffer-timeout: 1ms
taskmanager.network.credit-model: true
taskmanager.network.netty.transport: epoll  # Linux optimization

# Monitor backpressure
web.backpressure.refresh-interval: 10000
web.backpressure.num-samples: 100
```

**3. Advanced Checkpointing Strategies:**
```python
# Custom checkpoint configuration per job
env.get_checkpoint_config().set_checkpoint_interval(10000)
env.get_checkpoint_config().set_min_pause_between_checkpoints(5000)
env.get_checkpoint_config().set_checkpoint_timeout(300000)
env.get_checkpoint_config().enable_unaligned_checkpoints(True)

# External checkpointing for recovery
env.get_checkpoint_config().enable_externalized_checkpoints(
    ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION
)
```

### **Monitoring Performance at Scale:**

#### **Key Metrics to Track:**
```bash
# Throughput metrics
curl -s http://192.168.1.184:8081/jobs/{job-id}/metrics?get=numRecordsInPerSecond
curl -s http://192.168.1.184:8081/jobs/{job-id}/metrics?get=numRecordsOutPerSecond

# Latency metrics
curl -s http://192.168.1.184:8081/jobs/{job-id}/metrics?get=latency.source_id.operator_id.latency
curl -s http://192.168.1.184:8081/jobs/{job-id}/metrics?get=latency.source_id.operator_id.latency_p99

# Backpressure monitoring
curl -s http://192.168.1.184:8081/jobs/{job-id}/vertices/{vertex-id}/backpressure

# Resource utilization
curl -s http://192.168.1.184:8081/taskmanagers/{tm-id}/metrics?get=Status.JVM.Memory.Heap.Used
curl -s http://192.168.1.184:8081/taskmanagers/{tm-id}/metrics?get=Status.Flink.Memory.Managed.Used
```

#### **Performance Benchmarking:**
```python
# Built-in performance testing
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import SourceFunction
import time

class ThroughputTestSource(SourceFunction):
    def __init__(self, events_per_second):
        self.events_per_second = events_per_second
        self.running = True
        
    def run(self, ctx):
        interval = 1.0 / self.events_per_second
        event_count = 0
        
        while self.running:
            start_time = time.time()
            ctx.collect(f"event_{event_count}")
            event_count += 1
            
            # Rate limiting
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)
    
    def cancel(self):
        self.running = False

# Performance test pipeline
env = StreamExecutionEnvironment.get_execution_environment()
env.set_parallelism(16)

# Test source: 100k events/second
test_stream = env.add_source(ThroughputTestSource(100000))

# Processing pipeline
result = test_stream \
    .map(lambda x: x.upper()) \
    .filter(lambda x: "event" in x) \
    .key_by(lambda x: hash(x) % 100) \
    .map(lambda x: f"processed_{x}")

# Sink with throughput measurement
result.print()

env.execute("Throughput Test")
```

### **Load Testing Your Cluster:**

#### **Kafka Load Generator:**
```python
# Generate test data to Kafka for Flink consumption
from kafka import KafkaProducer
import json
import time
import random
from concurrent.futures import ThreadPoolExecutor

def generate_test_events(events_per_second, duration_seconds):
    producer = KafkaProducer(
        bootstrap_servers=['192.168.1.184:9092', '192.168.1.187:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    total_events = events_per_second * duration_seconds
    interval = 1.0 / events_per_second
    
    for i in range(total_events):
        event = {
            'event_id': i,
            'user_id': random.randint(1, 10000),
            'event_type': random.choice(['click', 'view', 'purchase']),
            'amount': round(random.uniform(10, 1000), 2),
            'timestamp': int(time.time() * 1000)
        }
        
        producer.send('test-events', event)
        time.sleep(interval)
    
    producer.flush()
    producer.close()

# Load test: 50k events/second for 10 minutes
generate_test_events(50000, 600)
```

#### **Monitoring During Load Tests:**
```bash
# Create monitoring script
cat << 'EOF' > monitor_flink_load.sh
#!/bin/bash

JOB_ID=$1
DURATION=${2:-300}  # 5 minutes default

echo "Monitoring Flink job $JOB_ID for $DURATION seconds"
echo "Time,RecordsIn/sec,RecordsOut/sec,Backpressure,HeapUsed%"

for i in $(seq 1 $DURATION); do
    TIMESTAMP=$(date '+%H:%M:%S')
    
    # Get throughput metrics
    RECORDS_IN=$(curl -s "http://192.168.1.184:8081/jobs/$JOB_ID/metrics?get=numRecordsInPerSecond" | jq -r '.[] | select(.id=="numRecordsInPerSecond") | .value')
    RECORDS_OUT=$(curl -s "http://192.168.1.184:8081/jobs/$JOB_ID/metrics?get=numRecordsOutPerSecond" | jq -r '.[] | select(.id=="numRecordsOutPerSecond") | .value')
    
    # Get backpressure ratio
    BACKPRESSURE=$(curl -s "http://192.168.1.184:8081/jobs/$JOB_ID/vertices" | jq -r '.vertices[0].backpressure')
    
    # Get heap usage
    HEAP_USED=$(curl -s "http://192.168.1.184:8081/taskmanagers" | jq -r '.taskmanagers[0].freeSlots')
    
    echo "$TIMESTAMP,$RECORDS_IN,$RECORDS_OUT,$BACKPRESSURE,$HEAP_USED"
    sleep 1
done
EOF

chmod +x monitor_flink_load.sh

# Run monitoring
./monitor_flink_load.sh <job-id> 300
```

---

## 📊 Monitoring & Troubleshooting

### **Comprehensive Monitoring Strategy**

Effective monitoring is crucial for maintaining healthy Flink clusters in production:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Flink Monitoring Architecture                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🎯 MONITORING LAYERS                                               │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                                                            │    │
│  │  Layer 1: Infrastructure Monitoring                       │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • CPU, Memory, Disk I/O                              │ │    │
│  │  │ • Network throughput                                  │ │    │
│  │  │ • System load averages                               │ │    │
│  │  │ • Disk space utilization                             │ │    │
│  │  │ • Tools: Prometheus, Grafana, Node Exporter          │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  Layer 2: Flink Cluster Monitoring                        │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • JobManager/TaskManager health                       │ │    │
│  │  │ • Slot utilization                                    │ │    │
│  │  │ • Checkpoint success rates                            │ │    │
│  │  │ • Memory pool usage                                   │ │    │
│  │  │ • Network buffer utilization                          │ │    │
│  │  │ • Tools: Flink Web UI, REST API, Metrics Reporters   │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  Layer 3: Job-Level Monitoring                            │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • Throughput (records/sec)                            │ │    │
│  │  │ • Latency (end-to-end, operator)                      │ │    │
│  │  │ • Backpressure indicators                             │ │    │
│  │  │ • Operator state sizes                                │ │    │
│  │  │ • Watermark progression                               │ │    │
│  │  │ • Tools: Custom metrics, Application logs             │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  │                                                            │    │
│  │  Layer 4: Business Logic Monitoring                       │    │
│  │  ┌───────────────────────────────────────────────────────┐ │    │
│  │  │ • Data quality metrics                                │ │    │
│  │  │ • Business KPIs                                       │ │    │
│  │  │ • SLA compliance                                      │ │    │
│  │  │ • Data freshness                                      │ │    │
│  │  │ • Tools: Custom dashboards, Alerting systems         │ │    │
│  │  └───────────────────────────────────────────────────────┘ │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### **Setting Up Monitoring for Your Cluster:**

#### **1. Prometheus Integration:**
```yaml
# Add to flink-conf.yaml
metrics.reporters: prom
metrics.reporter.prom.class: org.apache.flink.metrics.prometheus.PrometheusReporter
metrics.reporter.prom.port: 9249-9259
metrics.reporter.prom.host: 0.0.0.0

# Include additional metrics groups
metrics.scope.jm: flink.jobmanager
metrics.scope.jm.job: flink.jobmanager.job
metrics.scope.tm: flink.taskmanager
metrics.scope.tm.job: flink.taskmanager.job
metrics.scope.task: flink.taskmanager.task
metrics.scope.operator: flink.taskmanager.task.operator
```

#### **2. Grafana Dashboard Setup:**
```json
{
  "dashboard": {
    "title": "Flink Cluster Monitoring",
    "panels": [
      {
        "title": "Job Throughput",
        "targets": [
          {
            "expr": "rate(flink_taskmanager_job_task_operator_numRecordsIn[1m])",
            "legendFormat": "Records In/sec - {{job_name}}"
          },
          {
            "expr": "rate(flink_taskmanager_job_task_operator_numRecordsOut[1m])",
            "legendFormat": "Records Out/sec - {{job_name}}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "flink_taskmanager_Status_JVM_Memory_Heap_Used",
            "legendFormat": "Heap Used - {{instance}}"
          },
          {
            "expr": "flink_taskmanager_Status_Flink_Memory_Managed_Used",
            "legendFormat": "Managed Memory - {{instance}}"
          }
        ]
      },
      {
        "title": "Checkpoint Duration",
        "targets": [
          {
            "expr": "flink_jobmanager_job_lastCheckpointDuration",
            "legendFormat": "Checkpoint Duration - {{job_name}}"
          }
        ]
      }
    ]
  }
}
```

#### **3. Custom Metrics in Applications:**
```python
from pyflink.common import Row
from pyflink.datastream.functions import ProcessFunction

class MetricsTrackingFunction(ProcessFunction):
    def __init__(self):
        self.processed_counter = None
        self.error_counter = None
        self.processing_latency = None
        
    def open(self, runtime_context):
        # Register custom metrics
        self.processed_counter = runtime_context.get_metrics_group() \
            .counter("records_processed")
        self.error_counter = runtime_context.get_metrics_group() \
            .counter("processing_errors")
        self.processing_latency = runtime_context.get_metrics_group() \
            .histogram("processing_latency_ms")
    
    def process_element(self, value, ctx, out):
        start_time = time.time()
        
        try:
            # Process the element
            result = self.process_logic(value)
            
            # Track successful processing
            self.processed_counter.inc()
            processing_time = (time.time() - start_time) * 1000
            self.processing_latency.update(processing_time)
            
            out.collect(result)
            
        except Exception as e:
            # Track errors
            self.error_counter.inc()
            logger.error(f"Processing error: {e}")
            # Optionally emit to error stream
```

### **Health Checks and Alerting:**

#### **JobManager Health Check:**
```bash
#!/bin/bash
# health_check_jobmanager.sh

JOBMANAGER_HOST="192.168.1.184"
JOBMANAGER_PORT="8081"

# Check if JobManager is responsive
if curl -f -s http://$JOBMANAGER_HOST:$JOBMANAGER_PORT/overview > /dev/null; then
    echo "JobManager is healthy"
    
    # Check for failed jobs
    FAILED_JOBS=$(curl -s http://$JOBMANAGER_HOST:$JOBMANAGER_PORT/jobs | jq '.jobs[] | select(.state=="FAILED") | .id' | wc -l)
    
    if [ $FAILED_JOBS -gt 0 ]; then
        echo "WARNING: $FAILED_JOBS failed jobs detected"
        exit 1
    fi
    
    exit 0
else
    echo "ERROR: JobManager is not responding"
    exit 2
fi
```

#### **TaskManager Health Check:**
```bash
#!/bin/bash
# health_check_taskmanagers.sh

JOBMANAGER_HOST="192.168.1.184"
JOBMANAGER_PORT="8081"

# Get all TaskManagers
TASKMANAGERS=$(curl -s http://$JOBMANAGER_HOST:$JOBMANAGER_PORT/taskmanagers | jq -r '.taskmanagers[].id')

for tm_id in $TASKMANAGERS; do
    # Check TaskManager status
    TM_STATUS=$(curl -s http://$JOBMANAGER_HOST:$JOBMANAGER_PORT/taskmanagers/$tm_id | jq -r '.status')
    
    if [ "$TM_STATUS" != "RUNNING" ]; then
        echo "ERROR: TaskManager $tm_id is not running (status: $TM_STATUS)"
        exit 1
    fi
    
    # Check memory usage
    HEAP_USED=$(curl -s http://$JOBMANAGER_HOST:$JOBMANAGER_PORT/taskmanagers/$tm_id/metrics?get=Status.JVM.Memory.Heap.Used | jq -r '.[0].value')
    HEAP_MAX=$(curl -s http://$JOBMANAGER_HOST:$JOBMANAGER_PORT/taskmanagers/$tm_id/metrics?get=Status.JVM.Memory.Heap.Max | jq -r '.[0].value')
    
    HEAP_USAGE=$(echo "scale=2; $HEAP_USED / $HEAP_MAX * 100" | bc)
    
    if (( $(echo "$HEAP_USAGE > 90" | bc -l) )); then
        echo "WARNING: TaskManager $tm_id heap usage is ${HEAP_USAGE}%"
    fi
done

echo "All TaskManagers are healthy"
```

#### **Alerting Rules (Prometheus):**
```yaml
# flink_alerts.yml
groups:
  - name: flink.alerts
    rules:
      - alert: FlinkJobManagerDown
        expr: up{job="flink-jobmanager"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Flink JobManager is down"
          description: "JobManager on {{ $labels.instance }} has been down for more than 1 minute"

      - alert: FlinkTaskManagerDown
        expr: up{job="flink-taskmanager"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Flink TaskManager is down"
          description: "TaskManager on {{ $labels.instance }} has been down for more than 2 minutes"

      - alert: FlinkJobFailed
        expr: flink_jobmanager_job_restarting_time > 0
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "Flink job is restarting"
          description: "Job {{ $labels.job_name }} is restarting"

      - alert: FlinkHighLatency
        expr: flink_taskmanager_job_task_operator_latency_p99 > 10000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected in Flink job"
          description: "99th percentile latency is {{ $value }}ms for job {{ $labels.job_name }}"

      - alert: FlinkHighBackpressure
        expr: flink_taskmanager_job_task_backpressure_ratio > 0.8
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "High backpressure in Flink job"
          description: "Backpressure ratio is {{ $value }} for job {{ $labels.job_name }}"

      - alert: FlinkCheckpointFailure
        expr: increase(flink_jobmanager_job_numberOfFailedCheckpoints[10m]) > 3
        for: 0m
        labels:
          severity: critical
        annotations:
          summary: "Multiple checkpoint failures"
          description: "Job {{ $labels.job_name }} has had {{ $value }} checkpoint failures in the last 10 minutes"
```

### **Troubleshooting Common Issues:**

#### **🚨 Critical Issues and Solutions:**

**1. OutOfMemoryError:**
```bash
# Symptoms: TaskManager crashes, jobs fail to restart
# Diagnosis:
tail -f $FLINK_HOME/log/flink-flink-taskmanager-*.log | grep -i "outofmemory"

# Solutions:
# a) Increase TaskManager memory
taskmanager.memory.process.size: 8192m

# b) Optimize state backend
state.backend.rocksdb.memory.managed: true
state.backend.rocksdb.memory.fixed-per-slot: 512MB

# c) Reduce parallelism temporarily
env.set_parallelism(4)  # Reduce from 8
```

**2. Checkpoint Timeouts:**
```bash
# Symptoms: Frequent checkpoint failures, job restarts
# Diagnosis:
curl -s http://192.168.1.184:8081/jobs/{job-id}/checkpoints | jq '.latest.failed'

# Solutions:
# a) Increase checkpoint timeout
execution.checkpointing.timeout: 900000ms  # 15 minutes

# b) Enable incremental checkpoints
state.backend.incremental: true

# c) Reduce checkpoint frequency
execution.checkpointing.interval: 60000ms  # 1 minute
```

**3. Backpressure Issues:**
```bash
# Symptoms: Declining throughput, increasing latency
# Diagnosis:
curl -s http://192.168.1.184:8081/jobs/{job-id}/vertices/{vertex-id}/backpressure

# Solutions:
# a) Increase parallelism for bottleneck operators
bottleneck_stream.window(...).set_parallelism(16)

# b) Optimize network buffers
taskmanager.network.numberOfBuffers: 4096
taskmanager.memory.network.fraction: 0.2

# c) Review operator efficiency
# Look for expensive operations in hot paths
```

**4. High Latency:**
```bash
# Symptoms: Slow processing, SLA violations
# Diagnosis:
curl -s http://192.168.1.184:8081/jobs/{job-id}/metrics?get=latency

# Solutions:
# a) Optimize operator chaining
stream.filter(...).map(...)  # Chain compatible operations

# b) Reduce checkpoint frequency
execution.checkpointing.interval: 30000ms

# c) Use appropriate time semantics
# Avoid processing time if event time is not required
```

#### **⚠️ Performance Issues:**

**1. Low Throughput:**
```python
# Diagnostic checklist:
# - Check source parallelism matches partition count
source_parallelism = kafka_consumer.set_parallelism(4)  # Match Kafka partitions

# - Verify network is not saturated
# - Monitor CPU utilization
# - Check for data skew in keys

# Solutions:
# a) Increase parallelism
env.set_parallelism(16)

# b) Optimize serialization
env.get_config().enable_object_reuse()

# c) Use broadcast state for lookups
broadcast_stream = control_stream.broadcast(state_descriptor)
```

**2. Memory Leaks:**
```bash
# Symptoms: Gradually increasing memory usage
# Diagnosis:
# Monitor heap growth over time
watch -n 30 'curl -s http://192.168.1.184:8081/taskmanagers/{tm-id}/metrics?get=Status.JVM.Memory.Heap.Used'

# Solutions:
# a) Enable periodic garbage collection
env.java.opts.taskmanager: "-XX:+UseG1GC -XX:MaxGCPauseMillis=200"

# b) Review state cleanup
# Implement state TTL for time-bounded state
state_descriptor.set_ttl(TTL_CONFIG)
```

### **Log Analysis and Debugging:**

#### **Centralized Logging Setup:**
```bash
# Configure log shipping to centralized system
# Add to logback.xml or log4j2.xml

# For ELK Stack integration:
# Install filebeat on all Flink nodes
sudo apt install filebeat

# Configure filebeat.yml:
```

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /home/flink/flink/log/*.log
  fields:
    service: flink
    environment: production
  multiline.pattern: '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
  multiline.negate: true
  multiline.match: after

output.elasticsearch:
  hosts: ["192.168.1.184:9200"]
  index: "flink-logs-%{+yyyy.MM.dd}"
```

#### **Log Analysis Queries:**
```bash
# Common troubleshooting queries

# 1. Find errors in the last hour
grep -i error $FLINK_HOME/log/*.log | grep "$(date +'%Y-%m-%d %H')"

# 2. Check for checkpoint failures
grep -i "checkpoint.*fail" $FLINK_HOME/log/*.log

# 3. Monitor GC activity
grep -i "gc" $FLINK_HOME/log/*.log | tail -20

# 4. Find job restarts
grep -i "job.*restart" $FLINK_HOME/log/*.log

# 5. Check for network issues
grep -i "connection.*timeout\|network.*error" $FLINK_HOME/log/*.log
```

### **Disaster Recovery Procedures:**

#### **Backup Strategy:**
```bash
#!/bin/bash
# backup_flink_cluster.sh

BACKUP_DIR="/backup/flink/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# 1. Backup configuration
tar -czf $BACKUP_DIR/flink-config.tar.gz $FLINK_HOME/conf/

# 2. Backup running job information
curl -s http://192.168.1.184:8081/jobs > $BACKUP_DIR/running-jobs.json

# 3. Create savepoints for all running jobs
JOBS=$(curl -s http://192.168.1.184:8081/jobs | jq -r '.jobs[] | select(.state=="RUNNING") | .id')

for job_id in $JOBS; do
    echo "Creating savepoint for job $job_id"
    SAVEPOINT_PATH=$(curl -s -X POST http://192.168.1.184:8081/jobs/$job_id/savepoints \
        -H "Content-Type: application/json" \
        -d '{"target-directory":"file:///home/flink/flink/savepoints","cancel-job":false}' | \
        jq -r '.["request-id"]')
    
    echo "Savepoint request $SAVEPOINT_PATH created for job $job_id"
done

# 4. Backup checkpoint metadata
cp -r /home/flink/flink/checkpoints $BACKUP_DIR/

echo "Backup completed in $BACKUP_DIR"
```

#### **Recovery Procedures:**
```bash
#!/bin/bash
# recover_flink_cluster.sh

BACKUP_DIR=$1
SAVEPOINT_PATH=$2

if [ -z "$BACKUP_DIR" ] || [ -z "$SAVEPOINT_PATH" ]; then
    echo "Usage: $0 <backup_dir> <savepoint_path>"
    exit 1
fi

# 1. Stop all Flink services
$FLINK_HOME/bin/stop-cluster.sh

# 2. Restore configuration
tar -xzf $BACKUP_DIR/flink-config.tar.gz -C $FLINK_HOME/

# 3. Start cluster
$FLINK_HOME/bin/start-cluster.sh

# 4. Wait for cluster to be ready
sleep 30

# 5. Restore jobs from savepoints
echo "Restoring job from savepoint: $SAVEPOINT_PATH"
$FLINK_HOME/bin/flink run -s $SAVEPOINT_PATH your-job.jar

echo "Recovery completed"
```

---

## 🎯 Summary: Your Flink Architecture Mastery

### **What You Now Understand:**

#### **🏗️ Architecture Fundamentals**
- **JobManager-TaskManager Pattern**: How coordination and execution are distributed
- **Event Time Processing**: Real-time processing with proper handling of late events
- **State Management**: Distributed, fault-tolerant state with exactly-once guarantees
- **Execution Model**: From jobs → operators → tasks with dynamic scaling

#### **⚡ Streaming Mastery**
- **Watermarks & Late Data**: Handling real-world data arrival patterns
- **Checkpointing**: Consistent snapshots for fault tolerance
- **Window Processing**: Time-based aggregations with event time semantics
- **Backpressure Management**: Automatic handling of varying load conditions

#### **🔧 Operational Excellence**
- **Scaling Strategies**: Growing from 3 to 50+ nodes systematically
- **Performance Optimization**: Bronze, Silver, Gold level tuning strategies
- **Monitoring & Alerting**: Comprehensive observability at all layers
- **Troubleshooting**: Systematic approaches to common production issues

#### **🚀 Advanced Capabilities**
- **Multi-System Integration**: Kafka, databases, search engines, ML systems
- **SQL Interface**: Declarative stream processing with automatic optimization
- **CDC Processing**: Real-time data synchronization across systems
- **ML Integration**: Real-time feature engineering and model inference

### **Your Current Setup Capabilities:**

#### **Current State Assessment:**
```bash
✅ Cluster Status:      3-node distributed setup
✅ Processing Capacity: 8 task slots, ~100k events/sec
✅ Fault Tolerance:     Checkpointing with RocksDB state backend
✅ Integration:         Kafka, PostgreSQL, Elasticsearch ready
✅ Monitoring:          Basic Web UI, ready for Prometheus/Grafana
```

#### **Immediate Optimizations (This Week):**
```yaml
# Enable advanced checkpointing
execution.checkpointing.interval: 30000ms
state.backend.incremental: true

# Optimize memory for production
taskmanager.memory.process.size: 8192m
taskmanager.memory.managed.fraction: 0.6

# Enable reactive scaling
scheduler-mode: reactive
```

#### **Medium-Term Enhancements (Next Month):**
- **Add worker-node4 + worker-node5** for 20+ task slots capacity
- **Implement Prometheus monitoring** with custom dashboards
- **Setup CDC pipelines** for real-time data synchronization
- **Optimize parallelism** based on actual workload patterns

#### **Long-Term Architecture (Next Quarter):**
- **High Availability Setup** with ZooKeeper and standby JobManager
- **Multi-cluster deployment** for different workload types
- **Advanced monitoring stack** with centralized logging and alerting
- **Auto-scaling integration** with Kubernetes or cloud platforms

### **Performance Monitoring Checklist:**

```bash
✅ Web UI:              http://192.168.1.184:8081
✅ Job Monitoring:      Real-time throughput and latency metrics
✅ Resource Tracking:   Memory, CPU, network utilization
✅ Health Checks:       Automated JobManager/TaskManager monitoring

Key Metrics to Watch:
📊 Throughput:          Records/second per operator
🧠 Memory Usage:        < 80% heap, managed memory utilization
⏱️ Latency:            P99 latency < job SLA requirements
🌊 Backpressure:        < 20% sustained backpressure
✅ Checkpoints:         > 95% success rate, < 30 second duration
```

### **Next Steps for Production:**

#### **Week 1: Monitoring Setup**
```bash
# Deploy Prometheus and Grafana
# Configure Flink metrics reporting
# Set up basic alerting rules
# Create operational dashboards
```

#### **Week 2-3: Load Testing**
```bash
# Generate realistic test data
# Measure actual throughput limits
# Identify bottlenecks
# Tune configurations based on results
```

#### **Week 4: Production Deployment**
```bash
# Implement backup/recovery procedures
# Deploy monitoring alerts
# Document operational procedures
# Train team on troubleshooting
```

### **Integration Roadmap:**

```
Current State → Intermediate → Advanced
      ↓              ↓           ↓
   3 Nodes        5 Nodes    10+ Nodes
   Basic Mon.     Full Mon.  Enterprise
   Dev Workload   Prod Load  Multi-tenant
   Manual Scale   Auto Scale  Cloud Native
```

Your 3-node Flink cluster provides a solid foundation for real-time stream processing that can scale to handle enterprise workloads. The architecture you've learned scales from thousands to millions of events per second - the principles remain consistent, only the capacity grows! 🚀

---

**🎓 You now have comprehensive mastery of Flink's distributed stream processing architecture - from fundamental concepts to advanced production patterns. This knowledge empowers you to build sophisticated real-time data pipelines that scale with your business needs!**

