# GPU-Enabled ML Setup Guide (TensorFlow, PyTorch, Spark MLlib)

## Overview
This guide sets up a comprehensive GPU-accelerated machine learning environment on the gpu-node (192.168.1.79) with RTX 2060 Super. The setup includes TensorFlow, PyTorch, Spark MLlib with GPU support, and integration with your existing data engineering infrastructure.

## ⚠️ CRITICAL WARNING
**Configuration files DO NOT expand shell variables like `$(whoami)` or `$HOME`!**
- In systemd service files, JSON files, and other config files: Use actual paths like `/home/sanzad/spark`
- Only bash commands and environment variable exports (in .bashrc) expand variables
- This documentation assumes username `sanzad` - replace with your actual username throughout

## 🔧 GPU Resource Detection Requirements
**For Spark to detect GPU resources, you need ALL of these:**
1. **worker-resources.json** - Defines GPU discovery script path
2. **spark-defaults.conf** - Contains GPU resource properties (CRITICAL!)
3. **gpu-discovery.sh** - Script that detects GPUs using nvidia-smi
4. **systemd service** - Must have SPARK_WORKER_RESOURCE_FILE environment variable

**Missing any of these will result in "No custom resources configured" error!**

## Machine Configuration
- **GPU Node**: gpu-node (192.168.1.79)
- **GPU**: NVIDIA RTX 2060 Super (8GB VRAM)
- **Role**: ML training, inference, and GPU-accelerated data processing
- **Integration**: Connected to your data pipeline via Feast, Redis, and Spark

## Prerequisites
- Ubuntu 20.04+ or compatible Linux distribution
- NVIDIA RTX 2060 Super GPU
- At least 16GB RAM (32GB recommended)
- At least 100GB free disk space for ML models and datasets
- Network connectivity to other cluster nodes

## Architecture Overview
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         GPU-Accelerated ML Architecture                        │
├─────────────────────┬─────────────────────┬─────────────────────┬─────────────────┤
│    cpu-node1        │    cpu-node2        │   worker-node3      │   gpu-node      │
│  - Feature Store    │    - Neo4j Graph    │   - Additional      │  - TensorFlow   │
│  - Redis Cache      │    - Spark Worker   │     Capacity        │  - PyTorch      │
│  - Data Sources     │                     │                     │  - Spark MLlib  │
│  192.168.1.184      │  192.168.1.187      │  192.168.1.190      │  - CUDA/cuDNN   │
└─────────────────────┴─────────────────────┴─────────────────────┤  - Jupyter Hub  │
                                    ↑                                │  - MLflow      │
                            Data Pipeline Integration                │ 192.168.1.79   │
                                                                    └─────────────────┘
```

## Step 1: NVIDIA Driver Installation

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

### First, Check if NVIDIA is Already Working:
```bash
# Test if NVIDIA driver is already working
nvidia-smi
lspci | grep -i nvidia
```

**If `nvidia-smi` shows your GPU properly, SKIP the installation steps below and proceed to Step 2.**

### If NVIDIA Driver Installation is Needed:

⚠️ **Important**: Use Ubuntu's official repositories only. Do not add third-party CUDA repositories as they can cause version conflicts.

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Check what Ubuntu recommends for your GPU
ubuntu-drivers devices

# Install the recommended driver automatically (recommended)
sudo ubuntu-drivers autoinstall

# OR install a specific version if you prefer
# sudo apt install nvidia-driver-535

# Reboot to load driver
sudo reboot
```

### After reboot, verify installation:
```bash
# Test NVIDIA driver
nvidia-smi

# Should show your GPU with driver version and CUDA version
# Example output:
# Driver Version: 535.247.01   CUDA Version: 12.2
```

### If nvidia-smi fails after reboot:
```bash
# Check if modules are loaded
lsmod | grep nvidia

# If not loaded, load manually
sudo modprobe nvidia
sudo modprobe nvidia_drm
sudo modprobe nvidia_modeset

# Test again
nvidia-smi
```

### CUDA Toolkit Installation (Optional - Only if Needed):

**Note**: Modern TensorFlow and PyTorch handle CUDA automatically. Only install CUDA toolkit if you need `nvcc` compiler or specific CUDA development tools.

```bash
# For Ubuntu 24.04, install from Ubuntu repositories
sudo apt install nvidia-cuda-toolkit

# Or for specific CUDA version, use Ubuntu's packages [Usually not needed as above is sufficient]
sudo apt search cuda-toolkit
sudo apt install cuda-toolkit-12-2

# Verify installation (if installed)
nvcc --version  # Only works if CUDA toolkit installed
nvidia-smi      # Always works with just the driver
```

## Step 2: Python Environment Setup

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

### Install Python and dependencies:

**Note**: For Ubuntu 24.04, Python 3.12 is the default version. Python 3.10 is not available in the standard repositories.

⚠️ **Important**: TensorFlow 2.16.1+ is required for Python 3.12 compatibility. Older versions (like 2.13.0) will NOT work.

```bash
# For Ubuntu 24.04 - Install Python 3.12 and pip
sudo apt install -y python3 python3-pip python3-dev python3-venv

# Create Python environment for ML
python3 -m venv ml-env
source ml-env/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install common scientific computing packages
pip install numpy pandas scipy scikit-learn matplotlib seaborn plotly
pip install jupyter jupyterlab ipython
pip install requests urllib3 tqdm
```

## Step 3: TensorFlow GPU Installation

```bash
# Activate ML environment
source ml-env/bin/activate

# Install TensorFlow GPU (2.16.1+ required for Python 3.12 support)
# Option A: Install base TensorFlow first (faster)
pip install tensorflow>=2.16.1

# Option B: Install with CUDA in one step (slower, larger download)
# pip install tensorflow[and-cuda]>=2.16.1

# Install additional TensorFlow tools
pip install tensorflow-datasets tensorflow-hub tensorflow-probability
pip install tensorboard

# Note: tensorflow-addons is DISCONTINUED and doesn't work with Python 3.12/TensorFlow 2.16+
# Note: tf-agents may have compatibility issues with newer TensorFlow versions
# pip install tf-agents tensorflow-recommenders  # Install only if needed and compatible

# Install TensorFlow Serving for model deployment
pip install tensorflow-serving-api

# Add CUDA support after basic installation (REQUIRED for GPU)
pip install tensorflow[and-cuda]
```

### Troubleshooting TensorFlow GPU Issues:

**Problem: "Cannot dlopen some GPU libraries" or "No GPU devices found"**

This means CUDA libraries are missing. Solutions:

```bash
# Option 1: Install TensorFlow CUDA support (recommended)
pip install tensorflow[and-cuda]

# Option 2: Install system CUDA toolkit
sudo apt install nvidia-cuda-toolkit

# Verify CUDA installation
python -c "import tensorflow as tf; print('GPUs:', len(tf.config.list_physical_devices('GPU')))"
```

### Troubleshooting Slow TensorFlow Installation:

If TensorFlow installation is taking too long:

```bash
# Check installation progress
pip install --verbose tensorflow>=2.16.1

# Clear pip cache if stuck
pip cache purge

# Use conda as alternative (often faster)
# conda install tensorflow-gpu -c conda-forge
```

### Test TensorFlow GPU:
```python
# Create test script
nano test_tensorflow_gpu.py
```

```python
import tensorflow as tf
import numpy as np
from datetime import datetime

print(f"TensorFlow version: {tf.__version__}")
print(f"CUDA available: {tf.test.is_built_with_cuda()}")

# List physical devices
print("Physical devices:")
for device in tf.config.list_physical_devices():
    print(f"  {device}")

# List GPU devices specifically  
gpu_devices = tf.config.list_physical_devices('GPU')
print(f"\nGPU devices: {len(gpu_devices)}")
for gpu in gpu_devices:
    print(f"  {gpu}")

# Check if GPU is available (newer API)
print(f"GPU available: {len(gpu_devices) > 0}")
    
# Test GPU computation
if gpu_devices:
    print("\n=== GPU Performance Test ===")
    
    # Create random data
    with tf.device('/GPU:0'):
        a = tf.random.normal([10000, 10000])
        b = tf.random.normal([10000, 10000])
        
        # Time matrix multiplication
        start_time = datetime.now()
        c = tf.matmul(a, b)
        gpu_time = (datetime.now() - start_time).total_seconds()
        
        print(f"GPU Matrix multiplication (10000x10000): {gpu_time:.4f} seconds")
    
    # Compare with CPU
    with tf.device('/CPU:0'):
        start_time = datetime.now()
        c_cpu = tf.matmul(a, b)
        cpu_time = (datetime.now() - start_time).total_seconds()
        
        print(f"CPU Matrix multiplication (10000x10000): {cpu_time:.4f} seconds")
        print(f"GPU speedup: {cpu_time/gpu_time:.2f}x")

else:
    print("No GPU devices found")
```

Run the test:
```bash
python test_tensorflow_gpu.py
```

## Step 4: PyTorch GPU Installation

```bash
# Install PyTorch with CUDA support (for CUDA 12.x)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install additional PyTorch libraries
pip install torchtext torchdata
pip install pytorch-lightning
pip install transformers datasets accelerate

# Install PyTorch Geometric libraries (may require compilation)
pip install torch-geometric torch-scatter

# torch-sparse often fails to compile - try alternatives:
# Option 1: Skip if not needed
# Option 2: Try pre-built wheel: pip install torch-sparse -f https://data.pyg.org/whl/torch-2.4.0+cu121.html
# Option 3: Install build dependencies first: sudo apt install ninja-build

# Install Optuna for hyperparameter optimization
pip install optuna optuna-dashboard

# Install ONNX for model interchange
pip install onnx onnxruntime-gpu
```

### Test PyTorch GPU:
```python
# Create test script
nano test_pytorch_gpu.py
```

```python
import torch
import torch.nn as nn
import numpy as np
from datetime import datetime

print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"cuDNN version: {torch.backends.cudnn.version()}")

if torch.cuda.is_available():
    print(f"GPU count: {torch.cuda.device_count()}")
    
    for i in range(torch.cuda.device_count()):
        gpu_name = torch.cuda.get_device_name(i)
        gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1024**3
        print(f"  GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
    
    print("\n=== GPU Performance Test ===")
    device = torch.device("cuda:0")
    
    # Create random tensors
    size = 10000
    a = torch.randn(size, size, device=device)
    b = torch.randn(size, size, device=device)
    
    # Warm up GPU
    for _ in range(5):
        _ = torch.matmul(a, b)
    torch.cuda.synchronize()
    
    # Time GPU computation
    start_time = datetime.now()
    c = torch.matmul(a, b)
    torch.cuda.synchronize()
    gpu_time = (datetime.now() - start_time).total_seconds()
    
    print(f"GPU Matrix multiplication ({size}x{size}): {gpu_time:.4f} seconds")
    
    # Compare with CPU
    a_cpu = a.cpu()
    b_cpu = b.cpu()
    
    start_time = datetime.now()
    c_cpu = torch.matmul(a_cpu, b_cpu)
    cpu_time = (datetime.now() - start_time).total_seconds()
    
    print(f"CPU Matrix multiplication ({size}x{size}): {cpu_time:.4f} seconds")
    print(f"GPU speedup: {cpu_time/gpu_time:.2f}x")
    
    # Memory usage
    print(f"\nGPU Memory Usage:")
    print(f"  Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
    print(f"  Reserved: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")

else:
    print("CUDA not available")
```

Run the test:
```bash
python test_pytorch_gpu.py
```

### Troubleshooting PyTorch Geometric Installation:

**Problem: "internal compiler error: Segmentation fault" when installing torch-sparse**

This is a common issue due to compilation complexity. Solutions:

```bash
# Option 1: Install build dependencies
sudo apt install ninja-build build-essential

# Option 2: Use pre-built wheels
pip install torch-sparse -f https://data.pyg.org/whl/torch-2.4.0+cu121.html

# Option 3: Skip torch-sparse (not always required)
# Most PyTorch Geometric functionality works without torch-sparse

# Option 4: Free up memory and retry
pip cache purge
# Close other applications to free RAM, then retry installation
```

## Step 5: Spark MLlib with GPU Support

> **Note**: This setup uses the existing Spark cluster from `setup_guide/03_spark_cluster_setup.md` as the compute backend. The GPU node acts as a Spark **client/driver** only, leveraging the distributed cluster for MLlib computations while keeping GPU-specific operations local.

### Install Java and PySpark Client:

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Install Java 11 (required for Spark client)
sudo apt install -y openjdk-11-jdk

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc

# Activate ML environment and install PySpark client
source ml-env/bin/activate
pip install pyspark==3.5.0

# Install Spark client dependencies
pip install py4j findspark
```

### Install RAPIDS and GPU-accelerated libraries:

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Activate ML environment (created in Step 2)
source ml-env/bin/activate

# Install RAPIDS for GPU-accelerated data science (OPTIONAL - Often problematic)
# Note: RAPIDS has complex compatibility requirements with Python 3.12 and CUDA versions
# 
# Option 1: Skip RAPIDS (recommended for basic ML setup)
# Most ML workflows work fine without RAPIDS
#
# Option 2: If you need RAPIDS, try CUDA 12 versions:
# pip install cudf-cu12 cuml-cu12 cugraph-cu12 --extra-index-url https://pypi.nvidia.com
#
# Option 3: Use CUDA 11 with NVIDIA index:
# pip install cudf-cu11 cuml-cu11 cugraph-cu11 --extra-index-url https://pypi.nvidia.com
# pip install rapids-dependency-file-generator

# Install CuPy (more reliable than full RAPIDS stack)
pip install cupy-cuda12x

# Install PySpark (compatible with Spark 3.5.6 and Python 3.12)  
pip install pyspark==3.5.0

# Install XGBoost with GPU support
pip install xgboost

# Install LightGBM with GPU support
pip install lightgbm

# Install CatBoost
pip install catboost
```

### Option A: Add GPU Node as Spark Worker (Recommended for GPU MLlib)

**This approach adds the GPU node as a worker to leverage GPU for Spark ML:**

#### A.1: Install Spark on GPU Node

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Install full Spark on GPU node (same version as cluster)
cd /home/$(whoami)
wget https://dlcdn.apache.org/spark/spark-3.5.6/spark-3.5.6-bin-hadoop3.tgz
tar -xzf spark-3.5.6-bin-hadoop3.tgz
mv spark-3.5.6-bin-hadoop3 spark

# Add to PATH
echo 'export SPARK_HOME=/home/'$(whoami)'/spark' >> ~/.bashrc
echo 'export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin' >> ~/.bashrc
source ~/.bashrc

# Create GPU-enabled worker configuration
mkdir -p $SPARK_HOME/conf
nano $SPARK_HOME/conf/spark-env.sh
```

#### A.2: Configure GPU Worker

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)/spark/conf`**

```bash
#!/usr/bin/env bash

# Java and Spark paths
export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export SPARK_HOME=/home/sanzad/spark

# GPU Worker Configuration
export SPARK_WORKER_CORES=8
export SPARK_WORKER_MEMORY=16g
export SPARK_WORKER_PORT=7078
export SPARK_WORKER_WEBUI_PORT=8081
export SPARK_WORKER_DIR=/home/sanzad/spark/work

# GPU Resource Discovery
export SPARK_WORKER_RESOURCE_FILE=/home/sanzad/spark/conf/worker-resources.json
```

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)/spark/conf`**

```bash
# Create GPU resource configuration
nano $SPARK_HOME/conf/worker-resources.json
```

```json
{
  "gpu": {
    "amount": 1,
    "discoveryScript": "/home/sanzad/spark/conf/gpu-discovery.sh"
  }
}
```

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)/spark/conf`**

```bash
# Create GPU discovery script
nano $SPARK_HOME/conf/gpu-discovery.sh
chmod +x $SPARK_HOME/conf/gpu-discovery.sh
```

```bash
#!/bin/bash
# GPU Discovery Script for Spark
nvidia-smi --query-gpu=index --format=csv,noheader,nounits | \
awk '{print "{\"name\": \"gpu\", \"addresses\": [\"" $1 "\"]}"}'
```

#### A.3: Integrate GPU Node into Existing Cluster

**Step 1: Set up SSH access from master to GPU node**

**🖥️ Machine: `cpu-node1` (192.168.1.184) - Spark Master**  
**👤 User: `spark`**  
**📁 Directory: `/home/spark`**

```bash
# Connect to master node as spark user
ssh spark@192.168.1.184

# Generate or use existing SSH key (run on master)
ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa  # Skip if key already exists

# Copy public key to GPU node (replace 'YOUR_GPU_USER' with the actual username on GPU node)
ssh-copy-id sanzad@192.168.1.79

# Test SSH connectivity  
ssh sanzad@192.168.1.79 "hostname"
# Should return: gpu-node

# Exit master node
exit
```

**Step 2: Update cluster configuration on master**

**🖥️ Machine: `cpu-node1` (192.168.1.184) - Spark Master**  
**👤 User: `spark`**  
**📁 Directory: `/home/spark/spark/conf`**

```bash
# Add GPU worker to workers file (run from your local machine)
ssh spark@192.168.1.184 "echo '192.168.1.79' >> /home/spark/spark/conf/workers"

# Verify the workers file now contains all nodes
ssh spark@192.168.1.184 "cat /home/spark/spark/conf/workers"
# Should show:
# 192.168.1.187
# 192.168.1.190  
# 192.168.1.79
```

**Step 3: Copy and configure cluster configuration**

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)/spark/conf`**

```bash
# Copy master's configuration to GPU node for consistency
scp spark@192.168.1.184:/home/spark/spark/conf/spark-defaults.conf $SPARK_HOME/conf/
scp spark@192.168.1.184:/home/spark/spark/conf/log4j2.properties $SPARK_HOME/conf/ 2>/dev/null || true

# Create directories that master expects
mkdir -p $SPARK_HOME/{logs,work,recovery,warehouse}
```

**CRITICAL: Add GPU Resource Configuration to spark-defaults.conf**

```bash
# Edit spark-defaults.conf to add GPU resource configuration
nano $SPARK_HOME/conf/spark-defaults.conf
```

**Add these lines to the end of spark-defaults.conf:**
```properties
# GPU Resource Configuration (REQUIRED for GPU detection)
spark.worker.resource.gpu.amount                1
spark.worker.resource.gpu.discoveryScript       /home/sanzad/spark/conf/gpu-discovery.sh

# Enable GPU resource scheduling
spark.resources.discoveryPlugin                 org.apache.spark.resource.ResourceDiscoveryScriptPlugin
```

⚠️ **IMPORTANT**: Replace `/home/sanzad/` with your actual username path!

**CRITICAL: Add GPU Resource Configuration to Master's spark-defaults.conf**

The master also needs GPU scheduling configuration:

```bash
# Add GPU scheduling configuration to master
ssh spark@192.168.1.184 "echo 'spark.executor.resource.gpu.amount 1' >> /home/spark/spark/conf/spark-defaults.conf"
ssh spark@192.168.1.184 "echo 'spark.task.resource.gpu.amount 0.1' >> /home/spark/spark/conf/spark-defaults.conf"
ssh spark@192.168.1.184 "echo 'spark.scheduler.resource.profileMergeConflicts false' >> /home/spark/spark/conf/spark-defaults.conf"

# Verify configuration
ssh spark@192.168.1.184 "grep -E '(gpu|profileMergeConflicts)' /home/spark/spark/conf/spark-defaults.conf"

# Restart master to pick up GPU configuration  
ssh spark@192.168.1.184 "sudo systemctl restart spark-master"
```

**Expected output:**
```
spark.executor.resource.gpu.amount 1
spark.task.resource.gpu.amount 0.1
spark.scheduler.resource.profileMergeConflicts false
```

**CRITICAL: Synchronize All Integration JARs from Master**

The GPU worker needs ALL integration JARs (not just Delta Lake) because it's a full cluster participant:

```bash
# Copy ALL integration JARs from master (where they should already exist)
mkdir -p $SPARK_HOME/jars-ext

# Copy all integration JARs from master
scp spark@192.168.1.184:/home/spark/spark/jars-ext/delta-spark_2.12-3.3.2.jar $SPARK_HOME/jars-ext/
scp spark@192.168.1.184:/home/spark/spark/jars-ext/delta-storage-3.3.2.jar $SPARK_HOME/jars-ext/
scp spark@192.168.1.184:/home/spark/spark/jars-ext/postgresql-42.7.2.jar $SPARK_HOME/jars-ext/
scp spark@192.168.1.184:/home/spark/spark/jars-ext/kafka-clients-3.4.0.jar $SPARK_HOME/jars-ext/
scp spark@192.168.1.184:/home/spark/spark/jars-ext/spark-sql-kafka-0-10_2.12-3.5.6.jar $SPARK_HOME/jars-ext/
scp spark@192.168.1.184:/home/spark/spark/jars-ext/iceberg-spark-runtime-3.5_2.12-1.4.3.jar $SPARK_HOME/jars-ext/
scp spark@192.168.1.184:/home/spark/spark/jars-ext/hadoop-aws-3.3.4.jar $SPARK_HOME/jars-ext/
scp spark@192.168.1.184:/home/spark/spark/jars-ext/aws-java-sdk-bundle-1.12.367.jar $SPARK_HOME/jars-ext/

# Install ALL JARs to runtime location
cp $SPARK_HOME/jars-ext/*.jar $SPARK_HOME/jars/

# Verify complete JAR installation
echo "=== VERIFYING ALL INTEGRATION JARS ==="
ls -la $SPARK_HOME/jars/delta-*.jar          # Delta Lake
ls -la $SPARK_HOME/jars/postgresql*.jar      # PostgreSQL
ls -la $SPARK_HOME/jars/kafka*.jar           # Kafka
ls -la $SPARK_HOME/jars/iceberg*.jar         # Iceberg
ls -la $SPARK_HOME/jars/hadoop-aws*.jar      # AWS S3
ls -la $SPARK_HOME/jars/aws-java-sdk*.jar    # AWS SDK
```

**Add Delta Lake configuration to worker spark-defaults.conf:**

```bash
# Add Delta Lake configuration to GPU worker
echo 'spark.sql.extensions io.delta.sql.DeltaSparkSessionExtension' >> $SPARK_HOME/conf/spark-defaults.conf
echo 'spark.sql.catalog.spark_catalog org.apache.spark.sql.delta.catalog.DeltaCatalog' >> $SPARK_HOME/conf/spark-defaults.conf

# Restart worker to pick up new JARs and configuration
sudo systemctl restart spark-worker
```

**Step 4: Configure GPU worker systemd service**

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `root` (via sudo)**  
**📁 Directory: `/etc/systemd/system`**

```bash
sudo nano /etc/systemd/system/spark-worker.service
```

**⚠️ IMPORTANT**: Replace `YOUR_USERNAME` with your actual username (e.g., `sanzad`) **EVERYWHERE** in the file, including:
- `User=YOUR_USERNAME` → `User=sanzad` 
- `WorkingDirectory=/home/YOUR_USERNAME/spark` → `WorkingDirectory=/home/sanzad/spark`
- `Environment=SPARK_HOME=/home/YOUR_USERNAME/spark` → `Environment=SPARK_HOME=/home/sanzad/spark`
- `ExecStart=/home/YOUR_USERNAME/spark/sbin/...` → `ExecStart=/home/sanzad/spark/sbin/...`

**DO NOT** use `$(whoami)` in systemd files as it won't be expanded.

**🚨 CRITICAL**: The `Environment=SPARK_WORKER_RESOURCE_FILE` line is **REQUIRED** for GPU detection! Without it, you'll get "No custom resources configured" error even if all other files are correct.

```ini
[Unit]
Description=Apache Spark GPU Worker
After=network.target
Wants=network.target

[Service]
Type=forking
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/spark
Environment=SPARK_HOME=/home/YOUR_USERNAME/spark
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
Environment=SPARK_LOCAL_IP=192.168.1.79
Environment=SPARK_WORKER_RESOURCE_FILE=/home/YOUR_USERNAME/spark/conf/worker-resources.json
ExecStart=/home/YOUR_USERNAME/spark/sbin/start-worker.sh --host 192.168.1.79 spark://192.168.1.184:7077
ExecStop=/home/YOUR_USERNAME/spark/sbin/stop-worker.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Example for user `sanzad`:**
```ini
[Unit]
Description=Apache Spark GPU Worker
After=network.target
Wants=network.target

[Service]
Type=forking
User=sanzad
Group=sanzad
WorkingDirectory=/home/sanzad/spark
Environment=SPARK_HOME=/home/sanzad/spark
Environment=JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
Environment=SPARK_LOCAL_IP=192.168.1.79
Environment=SPARK_WORKER_RESOURCE_FILE=/home/sanzad/spark/conf/worker-resources.json
ExecStart=/home/sanzad/spark/sbin/start-worker.sh --host 192.168.1.79 spark://192.168.1.184:7077
ExecStop=/home/sanzad/spark/sbin/stop-worker.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Step 5: Update firewall on GPU node**

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Open Spark worker ports
sudo ufw allow 7078/tcp   # Spark Worker port
sudo ufw allow 8081/tcp   # Spark Worker Web UI
sudo ufw reload
```

**Step 6: Start GPU worker and restart master**

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Enable and start GPU worker service
sudo systemctl daemon-reload
sudo systemctl enable spark-worker
sudo systemctl start spark-worker

# Check GPU worker status
sudo systemctl status spark-worker

# If it fails with "Failed to determine user credentials", fix the systemd file
```

### Troubleshooting Spark Worker Issues:

**Problem: "Failed to determine user credentials" or status=217/USER**

This happens when systemd can't expand shell variables. Fix by:

```bash
# Check service status
sudo systemctl status spark-worker

# If failed, edit service file with actual username (not $(whoami))
sudo nano /etc/systemd/system/spark-worker.service

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl start spark-worker

# Check logs for other issues
journalctl -xeu spark-worker.service

# Check worker logs
tail -f /home/YOUR_USERNAME/spark/logs/spark-*-worker-*.out
```

**Problem: "No custom resources configured for spark.worker"**

This means GPU resources aren't being detected. Fix by:

```bash
# 1. Ensure both worker-resources.json AND spark-defaults.conf are configured
cat $SPARK_HOME/conf/worker-resources.json
cat $SPARK_HOME/conf/spark-defaults.conf | grep gpu

# 2. Check GPU discovery script works
bash $SPARK_HOME/conf/gpu-discovery.sh
# Should output: {"name": "gpu", "addresses": ["0"]}

# 3. Add missing GPU configuration to spark-defaults.conf
nano $SPARK_HOME/conf/spark-defaults.conf
# Add the GPU resource properties shown above

# 4. Restart worker and verify
sudo systemctl restart spark-worker
tail -10 /home/sanzad/spark/logs/spark-*-worker-*.out
# Should show: "Custom resources for spark.worker: gpu -> [name: gpu, addresses: 0]"

# 5. Verify in Web UI
curl -s http://192.168.1.79:8081/json/ | jq '.resources'
```

**Problem: "No executor resource configs were specified for the following task configs: gpu"**

This means master is missing GPU executor configuration:

```bash
# Add missing executor GPU configuration to master
ssh spark@192.168.1.184 "echo 'spark.executor.resource.gpu.amount 1' >> /home/spark/spark/conf/spark-defaults.conf"
ssh spark@192.168.1.184 "echo 'spark.scheduler.resource.profileMergeConflicts false' >> /home/spark/spark/conf/spark-defaults.conf"

# Verify GPU configurations are present
ssh spark@192.168.1.184 "grep -E '(gpu|profileMergeConflicts)' /home/spark/spark/conf/spark-defaults.conf"
# Should show:
# spark.task.resource.gpu.amount 0.1
# spark.executor.resource.gpu.amount 1
# spark.scheduler.resource.profileMergeConflicts false

# Restart master
ssh spark@192.168.1.184 "sudo systemctl restart spark-master"
```

**Problem: "ClassNotFoundException: io.delta.sql.DeltaSparkSessionExtension"**

This means integration JARs are missing from the GPU worker:

```bash
# Check if JARs exist
ls -la $SPARK_HOME/jars/delta-*.jar
ls -la $SPARK_HOME/jars/postgresql*.jar
ls -la $SPARK_HOME/jars/kafka*.jar

# If missing, copy ALL integration JARs from master (see JAR synchronization section above)
# DO NOT download individually - copy from master where they should already exist

# Verify master has the JARs first
ssh spark@192.168.1.184 "ls -la /home/spark/spark/jars-ext/"

# If master is missing JARs, follow setup_guide/03_spark_cluster_setup.md Step 11 first
# Then copy from master to GPU worker as documented above

# Restart worker after copying JARs
sudo systemctl restart spark-worker
```

**🖥️ Machine: `cpu-node1` (192.168.1.184) - Spark Master**  
**👤 User: `spark`**  
**📁 Directory: `/home/spark`**

```bash
# Restart master to recognize new worker (IMPORTANT!)
ssh spark@192.168.1.184 "sudo systemctl restart spark-master"

# Check master status
ssh spark@192.168.1.184 "sudo systemctl status spark-master"
```

**Step 7: Synchronize ALL JAR files from master (MOVED TO EARLIER SECTION)**

⚠️ **NOTE**: JAR synchronization is now handled in the "CRITICAL: Synchronize All Integration JARs from Master" section above to avoid redundancy.

**Step 8: Verify cluster integration**

**🖥️ Machine: `gpu-node` (192.168.1.79) or your local machine**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Check Spark Master Web UI - should show 3 workers now
# http://192.168.1.184:8080

# Check GPU worker is registered
curl -s http://192.168.1.184:8080/json/ | grep -A 5 "192.168.1.79"

# Verify GPU worker resources are detected
curl -s http://192.168.1.79:8081/json/ | grep -i gpu

# Check GPU worker's own Web UI
# http://192.168.1.79:8081

# Test cluster with all 3 workers
ssh spark@192.168.1.184 '/home/spark/spark/bin/spark-shell --master spark://192.168.1.184:7077 --conf "spark.sql.adaptive.enabled=true"'
```

**Expected Result:**
- Master Web UI shows **3 workers**: 192.168.1.187, 192.168.1.190, 192.168.1.79
- GPU worker shows **GPU resources available**
- Worker logs show: `Custom resources for spark.worker: gpu -> [name: gpu, addresses: 0]`
- GPU worker Web UI: `http://192.168.1.79:8081/json/` shows GPU in resources section
- Applications can now schedule GPU-accelerated tasks on 192.168.1.79

**Verification Commands:**
```bash
# Check GPU worker Web UI
curl -s http://192.168.1.79:8081/json/ | jq '.resources'
# Should show: {"gpu": {"addresses": ["0"]}}

# Check worker logs for GPU detection
tail -20 /home/sanzad/spark/logs/spark-sanzad-org.apache.spark.deploy.worker.Worker-1-gpu-node.out | grep -i gpu

# Check master shows GPU worker
curl -s http://192.168.1.184:8080/json/ | jq '.workers[] | select(.host=="192.168.1.79") | .resources'
```

**Test Spark Cluster Integration:**

```bash
# Test Spark shell connection
ssh spark@192.168.1.184 '/home/spark/spark/bin/spark-shell --master spark://192.168.1.184:7077'

# In Spark shell, run these verification commands:
sc.getConf.get("spark.master")  // Should show: spark://192.168.1.184:7077
sc.statusTracker.getExecutorInfos().length  // Should show number of executors
sc.resources  // Should show available driver resources (may be empty)

# Test RDD distribution across workers
val rdd = sc.parallelize(1 to 100, 10)
println(s"RDD partitions: ${rdd.getNumPartitions}")
rdd.glom().mapPartitions(iter => Array(java.net.InetAddress.getLocalHost.getHostName).iterator).collect()

# Exit
:quit
```

**Expected Results:**
- Should connect to all 3 workers (192.168.1.187, 192.168.1.190, 192.168.1.79)
- RDD operations should distribute across worker nodes  
- Last command shows which hosts are processing partitions

**Test GPU Resource Scheduling:**

```bash
# Test Spark shell WITH GPU resource requirements
ssh spark@192.168.1.184 '/home/spark/spark/bin/spark-shell --master spark://192.168.1.184:7077 --conf spark.executor.resource.gpu.amount=1 --conf spark.task.resource.gpu.amount=0.1'

# Should start successfully with these indicators:
# 1. Optimization warning (NORMAL): 
#    WARN ResourceUtils: The configuration of resource: gpu (exec = 1, task = 0.1/10, runnable tasks = 10)
# 2. NO Delta Lake ClassNotFoundException warnings (if JARs installed correctly)
# 3. Application gets assigned ID (e.g., app-20251005201320-0001)

# In shell, test operations:
sc.getConf.get("spark.master")
sc.parallelize(1 to 100).collect()

# Test Delta Lake if JARs installed:
import io.delta.tables._
:quit
```

**Success Indicators:**
- ✅ Spark shell starts without "No executor resource configs" error
- ✅ Applications get assigned app IDs (e.g., app-20251005201320-0001)  
- ✅ Basic operations work (parallelize/collect)
- ✅ NO Delta Lake ClassNotFoundException (if JARs installed)
- ⚠️ GPU/CPU resource optimization warning (this is normal - not an error)

### Option B: Client-Only Setup (No GPU MLlib Acceleration)

**Use this only if you want CPU-based MLlib + local GPU libraries:**

### Configure Spark Client Connection:

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Create configuration directory for client
mkdir -p ~/.spark/conf

# Create client configuration file
nano ~/.spark/conf/spark-defaults.conf
```

```properties
# Connection to existing Spark cluster
spark.master                    spark://192.168.1.184:7077

# Driver configuration (runs on GPU node)
spark.driver.memory             4g
spark.driver.cores              4
spark.driver.host               192.168.1.79
spark.driver.bindAddress        192.168.1.79

# Executor configuration (runs on cluster workers)
spark.executor.cores            2
spark.executor.memory           4g
spark.executor.instances        4

# Performance optimizations
spark.sql.adaptive.enabled      true
spark.sql.adaptive.coalescePartitions.enabled true
spark.sql.execution.arrow.pyspark.enabled true
spark.sql.execution.arrow.pyspark.fallback.enabled true

# Enable event logging to cluster history server
spark.eventLog.enabled          true
spark.eventLog.dir              /home/spark/spark/logs

# Network configuration
spark.network.timeout           800s
spark.executor.heartbeatInterval 60s

# Serialization
spark.serializer                org.apache.spark.serializer.KryoSerializer
```

### Set environment variables:

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Add to ~/.bashrc
echo 'export SPARK_CONF_DIR=~/.spark/conf' >> ~/.bashrc
echo 'export PYSPARK_PYTHON=/home/'$(whoami)'/ml-env/bin/python' >> ~/.bashrc
echo 'export PYSPARK_DRIVER_PYTHON=/home/'$(whoami)'/ml-env/bin/python' >> ~/.bashrc
source ~/.bashrc
```

### How Spark MLlib Distributes with Client-Only Setup:

**Key Understanding: MLlib Algorithms Execute on Cluster Workers, Not Driver**

```
What Happens When You Run: model = lr.fit(training_data)

GPU Node (Driver/Client)              Spark Cluster (Workers)
┌─────────────────────────┐          ┌──────────────────────────┐
│ 1. Your Python Code    │          │  4. Actual ML Computation │
│    lr = LinearRegression│    ──►   │  • Matrix multiplications │
│    model = lr.fit(df)   │          │  • Gradient calculations  │
│                         │          │  • Iterative optimization │
│ 2. Job Planning         │          │                          │
│    • Break into tasks   │    ──►   │  5. Distributed Execution │
│    • Send to executors  │          │  • Task 1 → Worker 187   │
│                         │          │  • Task 2 → Worker 190   │
│ 3. Result Collection    │    ◄──   │  • Parallel processing   │
│    • Gather coefficients│          │  • Send results back     │
│    • Build final model │          │                          │
└─────────────────────────┘          └──────────────────────────┘
```

**What Requires Network Transfer:**
- ✅ Serialized algorithm parameters
- ✅ Training data partitions  
- ✅ Gradient updates and model coefficients
- ❌ NOT the algorithm implementation (already on workers)

### Test Distributed Spark MLlib:

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```python
# Create test script to demonstrate cluster distribution
nano test_spark_cluster_ml.py
```

```python
import os
os.environ['PYSPARK_PYTHON'] = '/home/' + os.getenv('USER') + '/ml-env/bin/python'
os.environ['PYSPARK_DRIVER_PYTHON'] = '/home/' + os.getenv('USER') + '/ml-env/bin/python'

from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import rand, randn, when
import cudf
import cuml
import numpy as np
import time

def test_spark_ml():
    # Initialize Spark - connects to cluster (not local)
    spark = SparkSession.builder \
        .appName("Distributed-MLlib-Test") \
        .getOrCreate()  # Uses spark-defaults.conf settings
    
    # Show cluster connection info
    print(f"Connected to: {spark.sparkContext.master}")
    print(f"Default parallelism: {spark.sparkContext.defaultParallelism}")
    
    # Show executors using Spark REST API (PySpark StatusTracker doesn't have getExecutorInfos)
    import requests
    import json
    
    try:
        # Get executor info via Spark REST API
        app_id = spark.sparkContext.applicationId
        rest_url = f"http://192.168.1.184:4040/api/v1/applications/{app_id}/executors"
        
        response = requests.get(rest_url, timeout=5)
        executors_data = response.json()
        
        print(f"Active executors: {len(executors_data)}")
        for executor in executors_data:
            host = executor['hostPort'].split(':')[0]  # Remove port number
            print(f"  Executor {executor['id']}: {host}")
        
        print("=== Spark MLlib Test ===")
        
        # Show cluster composition (CPU vs GPU workers)
        print(f"\n=== Cluster Worker Analysis ===")
        for executor in executors_data:
            host = executor['hostPort'].split(':')[0]
            if host == "192.168.1.79":
                print(f"  ✅ GPU Worker: {host} (RTX 2060 Super)")
            else:
                print(f"  ⚠️  CPU Worker: {host} (No GPU)")
                
    except Exception as e:
        print(f"Could not get executor info via REST API: {e}")
        print("Continuing with basic cluster test...")
        
        # Fallback to basic info
        status = spark.sparkContext.statusTracker()
        app_info = status.getApplicationInfo()
        print(f"Application ID: {app_info.appId}")
        print(f"Application Name: {app_info.name}")
        print("=== Spark MLlib Test ===")
    
    # Generate larger dataset to benefit from GPU acceleration
    print(f"\n=== Testing GPU-Accelerated MLlib ===")
    df = spark.range(0, 1000000).select(  # 1M rows for GPU benefit
        "id",
        (rand() * 10).alias("feature1"),
        (randn() * 5).alias("feature2"),
        (rand() * 8).alias("feature3"),
        (randn() * 12).alias("feature4"),
        (rand() * 20 + randn() * 3).alias("label")
    )
    
    print(f"Dataset size: {df.count():,} rows")
    print(f"Dataset partitions: {df.rdd.getNumPartitions()}")
    
    # Prepare features
    assembler = VectorAssembler(
        inputCols=["feature1", "feature2", "feature3", "feature4"],
        outputCol="features"
    )
    
    df_assembled = assembler.transform(df)
    train_df, test_df = df_assembled.randomSplit([0.8, 0.2], seed=42)
    
    # Test GPU-aware Random Forest (benefits from GPU acceleration)
    print(f"\n--- Random Forest with GPU Resources ---")
    from pyspark.ml.classification import RandomForestClassifier
    
    # Create binary classification target
    df_classification = df_assembled.withColumn("class_label",
        when(df_assembled.label > 15, 1.0).otherwise(0.0)
    )
    
    rf = RandomForestClassifier(
        featuresCol="features",
        labelCol="class_label", 
        numTrees=100,
        maxDepth=15,
        # Request GPU resources if available
        # Spark will automatically utilize GPU node for computation
    )
    
    start_time = time.time()
    rf_model = rf.fit(df_classification)
    gpu_train_time = time.time() - start_time
    
    print(f"Random Forest training time: {gpu_train_time:.2f} seconds")
    print(f"Trees trained: {rf_model.getNumTrees}")
    
    # Test Linear Regression with iterative algorithm
    print(f"\n--- Linear Regression with Distributed Gradient Descent ---")
    lr = LinearRegression(
        featuresCol="features", 
        labelCol="label",
        maxIter=50,
        regParam=0.01,
        # GPU node will handle gradient computations
    )
    
    start_time = time.time()  
    lr_model = lr.fit(train_df)
    lr_train_time = time.time() - start_time
    
    print(f"Linear Regression training time: {lr_train_time:.2f} seconds")
    print(f"Coefficients: {lr_model.coefficients[:2]}...")  # Show first 2
    print(f"RMSE: {lr_model.summary.rootMeanSquaredError:.4f}")
    
    # Show resource utilization
    print(f"\n=== Resource Utilization ===")
    print("Note: GPU computations happened on worker 192.168.1.79")
    print("CPU workers (187, 190) handled data shuffling and coordination")
    
    spark.stop()

def test_rapids_gpu():
    print("\n=== RAPIDS GPU Test ===")
    
    try:
        # Generate GPU data with cuDF
        n_rows = 1000000
        df_gpu = cudf.DataFrame({
            'feature1': np.random.rand(n_rows),
            'feature2': np.random.randn(n_rows),
            'target': np.random.rand(n_rows) * 10 + np.random.randn(n_rows)
        })
        
        print(f"Created GPU DataFrame with {len(df_gpu):,} rows")
        
        # Prepare features
        X = df_gpu[['feature1', 'feature2']]
        y = df_gpu['target']
        
        # Train linear regression with cuML
        from cuml.linear_model import LinearRegression as cuLinearRegression
        
        model = cuLinearRegression()
        
        start_time = time.time()
        model.fit(X, y)
        gpu_train_time = time.time() - start_time
        
        # Make predictions
        predictions = model.predict(X)
        
        print(f"RAPIDS GPU training time: {gpu_train_time:.4f} seconds")
        print(f"Model score: {model.score(X, y):.4f}")
        
    except Exception as e:
        print(f"RAPIDS test failed: {e}")

if __name__ == "__main__":
    test_spark_ml()
    test_rapids_gpu()
```

**Run the test:**

**🖥️ Machine: `gpu-node` (192.168.1.79)**  
**👤 User: `$(whoami)` (your regular user)**  
**📁 Directory: `/home/$(whoami)`**

```bash
# Activate ML environment first
source ml-env/bin/activate

# Run the test
python test_spark_cluster_ml.py
```

## Step 6: Jupyter Lab Setup with GPU Support

### Install and configure Jupyter:
```bash
# Activate ML environment
source ml-env/bin/activate

# Install JupyterLab with extensions (JupyterLab 4.x for better GPU support)
pip install 'jupyterlab>=4.0'
pip install jupyterlab-git jupyterlab-github
pip install ipywidgets widgetsnbextension
pip install jupyter-dash

# Install monitoring extensions (compatible with JupyterLab 4.x)
pip install jupyter-resource-usage  # System monitoring (replaces jupyterlab-system-monitor)
pip install jupyterlab-nvdashboard   # GPU monitoring (requires JupyterLab 4.x)

# ⚠️ DEPENDENCY CONFLICT FIX (if needed)
# If you see "jupyterlab 3.6.8 which is incompatible" errors:
# pip uninstall -y jupyterlab-system-monitor jupyterlab-topbar
# pip install 'jupyterlab>=4.0' --force-reinstall
# pip install jupyter-resource-usage

# Generate Jupyter config
jupyter lab --generate-config

# Configure Jupyter
nano ~/.jupyter/jupyter_lab_config.py
```

```python
# Jupyter Lab Configuration for GPU Node
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.port = 8888
c.ServerApp.open_browser = False
c.ServerApp.token = ''  # Set empty for no token (use only in secure network)
c.ServerApp.password = ''
c.ServerApp.allow_remote_access = True
c.ServerApp.notebook_dir = '/home/' + os.getenv('USER') + '/notebooks'

# Enable extensions
c.ServerApp.jpserver_extensions = {
    'jupyterlab': True,
    'jupyterlab_git': True,
    'jupyterlab_nvdashboard': True,
}
```

### Create Jupyter startup script:
```bash
nano start_jupyter.sh
```

```bash
#!/bin/bash

# Activate ML environment
source /home/$(whoami)/ml-env/bin/activate

# Set environment variables
export CUDA_VISIBLE_DEVICES=0
export TF_FORCE_GPU_ALLOW_GROWTH=true
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# Create notebooks directory
mkdir -p /home/$(whoami)/notebooks

# Start Jupyter Lab
jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --notebook-dir=/home/$(whoami)/notebooks
```

Make it executable:
```bash
chmod +x start_jupyter.sh
```

### Test Jupyter Lab Setup:

```bash
# Test 1: Start Jupyter Lab manually to check for errors
source ml-env/bin/activate
jupyter lab --generate-config  # Ensure config exists

# Test 2: Run Jupyter Lab in foreground (Ctrl+C to stop)
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root

# Should see output like:
# [I 2025-10-05 22:00:00.000 ServerApp] Serving at http://0.0.0.0:8888/lab
# [I 2025-10-05 22:00:00.000 ServerApp] Use Control-C to stop this server
```

**If successful, stop with Ctrl+C and test systemd service:**

```bash
# Test 3: Start as systemd service  
sudo systemctl start jupyter-gpu
sudo systemctl status jupyter-gpu

# Should show: active (running)
```

**Test 4: Access Jupyter Lab Web Interface:**

Open browser and navigate to: **http://192.168.1.79:8888**

Expected results:
- ✅ Jupyter Lab interface loads
- ✅ Can create new notebook
- ✅ Python kernel starts successfully
- ✅ GPU extensions visible (nvdashboard, resource usage)

**Test 5: Create test notebook to verify GPU detection:**

Create new notebook and run:
```python
# Test GPU detection in Jupyter
import torch
import tensorflow as tf

print("=== GPU Detection Test ===")
print(f"PyTorch CUDA available: {torch.cuda.is_available()}")
print(f"TensorFlow GPUs: {len(tf.config.list_physical_devices('GPU'))}")

# Test NVIDIA monitoring
import pynvml
pynvml.nvmlInit()
gpu_count = pynvml.nvmlDeviceGetCount()
print(f"NVIDIA GPUs detected: {gpu_count}")

if gpu_count > 0:
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    name = pynvml.nvmlDeviceGetName(handle)
    print(f"GPU 0: {name}")
```

**Test 6: Verify Extensions:**
- **GPU Dashboard**: Look for "GPU Dashboards" in left sidebar
- **Resource Monitor**: Look for CPU/Memory usage in top bar  
- **Git Extension**: Look for Git tab in left sidebar

**Troubleshooting Common Issues:**

```bash
# Issue 1: "Address already in use"
sudo lsof -i :8888
sudo kill -9 <PID>

# Issue 2: Permission denied
sudo chown -R sanzad:sanzad ~/.jupyter/
chmod 644 ~/.jupyter/jupyter_lab_config.py

# Issue 3: Extension not loading
jupyter lab build --minimize=False
jupyter lab clean
jupyter lab build

# Issue 4: Kernel not found
python -m ipykernel install --user --name ml-env --display-name "ML Environment"

# Check logs if service fails
journalctl -xeu jupyter-gpu.service -f
```

## Step 7: MLflow Setup for Experiment Tracking

```bash
# Install MLflow
pip install mlflow

# Install additional tracking dependencies
pip install mlflow[extras]
pip install psycopg2-binary  # For PostgreSQL backend

# Create MLflow directories
mkdir -p /home/$(whoami)/mlflow/{artifacts,db}
```

### Configure MLflow with PostgreSQL backend:
```bash
# Create MLflow database in PostgreSQL
psql -U dataeng -h 192.168.1.184 -d postgres
CREATE DATABASE mlflow_db;
GRANT ALL PRIVILEGES ON DATABASE mlflow_db TO dataeng;
\q
```

### Create MLflow server startup script:
```bash
nano start_mlflow.sh
```

```bash
#!/bin/bash

# Activate ML environment
source /home/$(whoami)/ml-env/bin/activate

# Start MLflow tracking server
mlflow server \
    --backend-store-uri postgresql://dataeng:password@192.168.1.184:5432/mlflow_db \
    --default-artifact-root file:///home/$(whoami)/mlflow/artifacts \
    --host 0.0.0.0 \
    --port 5000 \
    --workers 2
```

Make it executable:
```bash
chmod +x start_mlflow.sh
```

## Step 8: Integration with Data Pipeline

### Create data pipeline integration:
```python
# Create integration/data_pipeline_integration.py
mkdir -p integration
nano integration/data_pipeline_integration.py
```

```python
import os
import sys
import pandas as pd
import numpy as np
import redis
import psycopg2
from sqlalchemy import create_engine
import tensorflow as tf
import torch
import mlflow
import mlflow.tensorflow
import mlflow.pytorch
from datetime import datetime

# Add feast repo to path (if using shared filesystem)
sys.path.append('/home/sanzad/feast-store/feast_repo')

class GPUMLPipeline:
    """GPU-accelerated ML pipeline with data integration"""
    
    def __init__(self):
        # Database connections
        self.pg_engine = create_engine('postgresql://dataeng:password@192.168.1.184:5432/analytics_db')
        
        # Redis connection for feature cache
        self.redis_client = redis.Redis(
            host='192.168.1.184',
            port=6379,
            password='your-redis-password',
            decode_responses=True
        )
        
        # MLflow setup
        mlflow.set_tracking_uri("http://192.168.1.79:5000")
        
        # GPU setup
        self.setup_gpu()
    
    def setup_gpu(self):
        """Configure GPU settings"""
        # TensorFlow GPU configuration
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            try:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
            except RuntimeError as e:
                print(f"GPU configuration error: {e}")
        
        # PyTorch GPU configuration
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print(f"PyTorch using GPU: {torch.cuda.get_device_name()}")
    
    def load_data_from_postgres(self, query, params=None):
        """Load data from PostgreSQL"""
        return pd.read_sql(query, self.pg_engine, params=params)
    
    def get_features_from_feast(self, user_ids):
        """Get features from Feast feature store"""
        try:
            # This would use the Feast client
            # For now, simulate with Redis cache
            features = []
            
            for user_id in user_ids:
                cache_key = f"features:user:{user_id}"
                cached = self.redis_client.get(cache_key)
                
                if cached:
                    import json
                    features.append(json.loads(cached))
                else:
                    # Fallback to database
                    feature = self.get_user_features_from_db(user_id)
                    features.append(feature)
                    
                    # Cache for future use
                    self.redis_client.setex(cache_key, 300, json.dumps(feature, default=str))
            
            return pd.DataFrame(features)
            
        except Exception as e:
            print(f"Feature retrieval error: {e}")
            return pd.DataFrame()
    
    def get_user_features_from_db(self, user_id):
        """Fallback method to get features from database"""
        query = """
        SELECT 
            u.user_id,
            u.age,
            u.income,
            u.preferred_category,
            a.total_sessions_7d,
            a.avg_order_value_30d,
            a.days_since_last_purchase
        FROM user_profiles u
        LEFT JOIN user_activity_features a ON u.user_id = a.user_id
        WHERE u.user_id = %s
        """
        
        result = pd.read_sql(query, self.pg_engine, params=[user_id])
        return result.iloc[0].to_dict() if len(result) > 0 else {}
    
    def train_tensorflow_model(self, X, y, experiment_name="tf_experiment"):
        """Train TensorFlow model with GPU acceleration"""
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run():
            # Log parameters
            mlflow.log_param("framework", "tensorflow")
            mlflow.log_param("gpu_used", tf.test.is_gpu_available())
            
            # Build model
            model = tf.keras.Sequential([
                tf.keras.layers.Dense(128, activation='relu', input_shape=(X.shape[1],)),
                tf.keras.layers.Dropout(0.3),
                tf.keras.layers.Dense(64, activation='relu'),
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.Dense(1)
            ])
            
            model.compile(
                optimizer=tf.keras.optimizers.Adam(0.001),
                loss='mse',
                metrics=['mae']
            )
            
            # Train on GPU
            with tf.device('/GPU:0'):
                history = model.fit(
                    X, y,
                    batch_size=256,
                    epochs=50,
                    validation_split=0.2,
                    verbose=1
                )
            
            # Log metrics
            final_loss = history.history['loss'][-1]
            final_val_loss = history.history['val_loss'][-1]
            
            mlflow.log_metric("final_loss", final_loss)
            mlflow.log_metric("final_val_loss", final_val_loss)
            
            # Save model
            mlflow.tensorflow.log_model(model, "model")
            
            return model
    
    def train_pytorch_model(self, X, y, experiment_name="pytorch_experiment"):
        """Train PyTorch model with GPU acceleration"""
        mlflow.set_experiment(experiment_name)
        
        with mlflow.start_run():
            # Log parameters
            mlflow.log_param("framework", "pytorch")
            mlflow.log_param("gpu_used", torch.cuda.is_available())
            
            # Convert to tensors
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            X_tensor = torch.FloatTensor(X.values).to(device)
            y_tensor = torch.FloatTensor(y.values).to(device)
            
            # Define model
            class MLModel(torch.nn.Module):
                def __init__(self, input_size):
                    super(MLModel, self).__init__()
                    self.layers = torch.nn.Sequential(
                        torch.nn.Linear(input_size, 128),
                        torch.nn.ReLU(),
                        torch.nn.Dropout(0.3),
                        torch.nn.Linear(128, 64),
                        torch.nn.ReLU(),
                        torch.nn.Dropout(0.2),
                        torch.nn.Linear(64, 1)
                    )
                
                def forward(self, x):
                    return self.layers(x)
            
            model = MLModel(X.shape[1]).to(device)
            criterion = torch.nn.MSELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            
            # Training loop
            model.train()
            for epoch in range(100):
                optimizer.zero_grad()
                outputs = model(X_tensor)
                loss = criterion(outputs.squeeze(), y_tensor)
                loss.backward()
                optimizer.step()
                
                if epoch % 20 == 0:
                    print(f'Epoch [{epoch}/100], Loss: {loss.item():.4f}')
                    mlflow.log_metric("loss", loss.item(), step=epoch)
            
            # Save model
            mlflow.pytorch.log_model(model, "model")
            
            return model
    
    def run_recommendation_pipeline(self):
        """Run complete recommendation pipeline"""
        print("=== Running Recommendation Pipeline ===")
        
        # Load user data
        user_query = """
        SELECT user_id, age, income, preferred_category
        FROM user_profiles 
        WHERE account_status = 'active'
        LIMIT 10000
        """
        
        users_df = self.load_data_from_postgres(user_query)
        print(f"Loaded {len(users_df)} users")
        
        # Get features
        features_df = self.get_features_from_feast(users_df['user_id'].tolist())
        print(f"Retrieved features for {len(features_df)} users")
        
        # Prepare training data
        feature_columns = ['age', 'income', 'total_sessions_7d', 'avg_order_value_30d']
        X = features_df[feature_columns].fillna(0)
        
        # Create synthetic target (in real scenario, this would be actual engagement data)
        y = pd.Series(np.random.random(len(X)))
        
        # Train TensorFlow model
        tf_model = self.train_tensorflow_model(X, y, "recommendation_tf")
        
        # Train PyTorch model  
        pytorch_model = self.train_pytorch_model(X, y, "recommendation_pytorch")
        
        print("Pipeline completed successfully!")
        
        return tf_model, pytorch_model
    
    def run_fraud_detection_pipeline(self):
        """Run fraud detection pipeline"""
        print("=== Running Fraud Detection Pipeline ===")
        
        # Load transaction data
        transaction_query = """
        SELECT 
            transaction_id,
            user_id,
            amount,
            payment_method,
            location_risk_score,
            velocity_1h,
            velocity_24h,
            CASE 
                WHEN amount > 1000 OR velocity_1h > 5 THEN 1 
                ELSE 0 
            END as is_fraud
        FROM transaction_features
        WHERE created_timestamp >= NOW() - INTERVAL '30 days'
        LIMIT 50000
        """
        
        transactions_df = self.load_data_from_postgres(transaction_query)
        print(f"Loaded {len(transactions_df)} transactions")
        
        # Prepare features
        feature_columns = ['amount', 'location_risk_score', 'velocity_1h', 'velocity_24h']
        X = transactions_df[feature_columns].fillna(0)
        y = transactions_df['is_fraud']
        
        # Train fraud detection model
        fraud_model = self.train_tensorflow_model(X, y, "fraud_detection")
        
        print("Fraud detection pipeline completed!")
        
        return fraud_model

def main():
    pipeline = GPUMLPipeline()
    
    # Run recommendation pipeline
    rec_models = pipeline.run_recommendation_pipeline()
    
    # Run fraud detection pipeline
    fraud_model = pipeline.run_fraud_detection_pipeline()
    
    print("All ML pipelines completed successfully!")

if __name__ == "__main__":
    main()
```

## Step 9: Model Serving Setup

### Install model serving frameworks:
```bash
# Install TensorFlow Serving
echo "deb [arch=amd64] http://storage.googleapis.com/tensorflow-serving-apt stable tensorflow-model-server tensorflow-model-server-universal" | sudo tee /etc/apt/sources.list.d/tensorflow-serving.list

curl https://storage.googleapis.com/tensorflow-serving-apt/tensorflow-serving.release.pub.gpg | sudo apt-key add -

sudo apt update
sudo apt install tensorflow-model-server

# Install TorchServe
pip install torchserve torch-model-archiver torch-workflow-archiver

# Install FastAPI for custom model serving
pip install fastapi uvicorn
pip install pydantic

# Install model optimization tools
pip install tensorflow-model-optimization
pip install onnx onnxruntime-gpu
pip install tensorrt  # If using TensorRT
```

### Create model serving API:
```python
# Create serving/model_server.py
mkdir -p serving
nano serving/model_server.py
```

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tensorflow as tf
import torch
import numpy as np
import redis
import json
import logging
from typing import List, Dict, Any
import uvicorn

app = FastAPI(title="GPU ML Model Serving API", version="1.0.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client for feature serving
redis_client = redis.Redis(
    host='192.168.1.184',
    port=6379,
    password='your-redis-password',
    decode_responses=True
)

# Model storage
models = {}

class PredictionRequest(BaseModel):
    model_name: str
    features: List[float]
    user_id: int = None

class BatchPredictionRequest(BaseModel):
    model_name: str
    batch_features: List[List[float]]
    user_ids: List[int] = None

class PredictionResponse(BaseModel):
    prediction: float
    model_name: str
    timestamp: str

class BatchPredictionResponse(BaseModel):
    predictions: List[float]
    model_name: str
    timestamp: str

@app.on_event("startup")
async def load_models():
    """Load models on startup"""
    try:
        # Load TensorFlow model
        tf_model_path = "/home/sanzad/models/recommendation_tf"
        if os.path.exists(tf_model_path):
            models['recommendation_tf'] = tf.keras.models.load_model(tf_model_path)
            logger.info("Loaded TensorFlow recommendation model")
        
        # Load PyTorch model (placeholder)
        # models['recommendation_pytorch'] = torch.load('/path/to/pytorch/model.pth')
        
    except Exception as e:
        logger.error(f"Error loading models: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    gpu_available = tf.test.is_gpu_available()
    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "loaded_models": list(models.keys()),
        "redis_connected": redis_client.ping()
    }

@app.get("/models")
async def list_models():
    """List available models"""
    return {"models": list(models.keys())}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Make single prediction"""
    if request.model_name not in models:
        raise HTTPException(status_code=404, detail="Model not found")
    
    try:
        model = models[request.model_name]
        features = np.array(request.features).reshape(1, -1)
        
        if 'tf' in request.model_name:
            prediction = model.predict(features)[0][0]
        else:
            # Handle PyTorch models
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features)
                if torch.cuda.is_available():
                    features_tensor = features_tensor.cuda()
                    model = model.cuda()
                prediction = model(features_tensor).cpu().numpy()[0]
        
        # Cache prediction if user_id provided
        if request.user_id:
            cache_key = f"prediction:{request.model_name}:{request.user_id}"
            redis_client.setex(cache_key, 300, json.dumps(float(prediction)))
        
        return PredictionResponse(
            prediction=float(prediction),
            model_name=request.model_name,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def batch_predict(request: BatchPredictionRequest):
    """Make batch predictions"""
    if request.model_name not in models:
        raise HTTPException(status_code=404, detail="Model not found")
    
    try:
        model = models[request.model_name]
        features = np.array(request.batch_features)
        
        if 'tf' in request.model_name:
            predictions = model.predict(features).flatten()
        else:
            # Handle PyTorch models
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features)
                if torch.cuda.is_available():
                    features_tensor = features_tensor.cuda()
                    model = model.cuda()
                predictions = model(features_tensor).cpu().numpy().flatten()
        
        return BatchPredictionResponse(
            predictions=predictions.tolist(),
            model_name=request.model_name,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail="Batch prediction failed")

@app.get("/metrics")
async def get_metrics():
    """Get model serving metrics"""
    # This would integrate with monitoring systems
    return {
        "gpu_memory_used": get_gpu_memory_usage(),
        "model_count": len(models),
        "cache_stats": get_cache_stats()
    }

def get_gpu_memory_usage():
    """Get GPU memory usage"""
    if tf.test.is_gpu_available():
        gpu_devices = tf.config.experimental.list_physical_devices('GPU')
        if gpu_devices:
            # This is a simplified implementation
            return {"gpu_0": "Available"}
    return {}

def get_cache_stats():
    """Get Redis cache statistics"""
    try:
        info = redis_client.info()
        return {
            "used_memory": info.get('used_memory_human'),
            "keyspace_hits": info.get('keyspace_hits'),
            "keyspace_misses": info.get('keyspace_misses')
        }
    except:
        return {}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Step 10: Monitoring and System Services

### Create GPU monitoring script:
```bash
nano monitoring/gpu_monitor.py
```

```python
import psutil
import GPUtil
import time
import json
import redis
from datetime import datetime
import logging

class GPUMonitor:
    def __init__(self):
        self.redis_client = redis.Redis(
            host='192.168.1.184',
            password='your-redis-password'
        )
    
    def get_gpu_stats(self):
        """Get GPU statistics"""
        try:
            gpus = GPUtil.getGPUs()
            gpu_stats = []
            
            for gpu in gpus:
                stats = {
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': gpu.load * 100,
                    'memory_used': gpu.memoryUsed,
                    'memory_total': gpu.memoryTotal,
                    'memory_percent': (gpu.memoryUsed / gpu.memoryTotal) * 100,
                    'temperature': gpu.temperature,
                    'timestamp': datetime.now().isoformat()
                }
                gpu_stats.append(stats)
            
            return gpu_stats
            
        except Exception as e:
            logging.error(f"GPU monitoring error: {e}")
            return []
    
    def get_system_stats(self):
        """Get system statistics"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }
    
    def publish_metrics(self, gpu_stats, system_stats):
        """Publish metrics to Redis"""
        try:
            # Publish GPU metrics
            self.redis_client.setex(
                'gpu_metrics',
                60,
                json.dumps(gpu_stats)
            )
            
            # Publish system metrics
            self.redis_client.setex(
                'system_metrics',
                60,
                json.dumps(system_stats)
            )
            
        except Exception as e:
            logging.error(f"Metrics publishing error: {e}")
    
    def run_monitoring(self, interval=30):
        """Run continuous monitoring"""
        while True:
            gpu_stats = self.get_gpu_stats()
            system_stats = self.get_system_stats()
            
            # Print to console
            print(f"\n=== GPU Monitor - {datetime.now()} ===")
            for gpu in gpu_stats:
                print(f"GPU {gpu['id']}: {gpu['load']:.1f}% load, "
                      f"{gpu['memory_percent']:.1f}% memory, {gpu['temperature']}°C")
            
            print(f"System: CPU {system_stats['cpu_percent']}%, "
                  f"RAM {system_stats['memory_percent']}%")
            
            # Publish metrics
            self.publish_metrics(gpu_stats, system_stats)
            
            time.sleep(interval)

if __name__ == "__main__":
    monitor = GPUMonitor()
    monitor.run_monitoring()
```

### Create systemd services:
```bash
# Jupyter service
sudo nano /etc/systemd/system/jupyter-gpu.service
```

```ini
[Unit]
Description=Jupyter Lab GPU Server
After=network.target

[Service]
Type=simple
User=sanzad
Group=sanzad
WorkingDirectory=/home/sanzad
Environment=PATH=/home/sanzad/ml-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=CUDA_VISIBLE_DEVICES=0
ExecStart=/home/sanzad/ml-env/bin/jupyter lab --config=/home/sanzad/.jupyter/jupyter_lab_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# MLflow service
sudo nano /etc/systemd/system/mlflow-gpu.service
```

```ini
[Unit]
Description=MLflow Tracking Server
After=network.target postgresql.service

[Service]
Type=simple
User=sanzad
Group=sanzad
WorkingDirectory=/home/sanzad
Environment=PATH=/home/sanzad/ml-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/sanzad/ml-env/bin/mlflow server --backend-store-uri postgresql://dataeng:password@192.168.1.184:5432/mlflow_db --default-artifact-root file:///home/sanzad/mlflow/artifacts --host 0.0.0.0 --port 5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jupyter-gpu
sudo systemctl enable mlflow-gpu
sudo systemctl start jupyter-gpu  
sudo systemctl start mlflow-gpu
```

## Step 11: Firewall Configuration

```bash
# Open required ports
sudo ufw allow 8888/tcp   # Jupyter Lab
sudo ufw allow 5000/tcp   # MLflow
sudo ufw allow 8000/tcp   # FastAPI Model Server
sudo ufw reload
```

## Access Information

After completing the setup, you can access:

- **Jupyter Lab**: http://192.168.1.79:8888
- **MLflow UI**: http://192.168.1.79:5000
- **Model Serving API**: http://192.168.1.79:8000
- **API Documentation**: http://192.168.1.79:8000/docs

## Performance Optimization Tips

1. **GPU Memory Management**:
   - Use `tf.config.experimental.set_memory_growth()` for TensorFlow
   - Set `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128` for PyTorch

2. **Batch Size Optimization**:
   - Start with batch size 64-256 for the RTX 2060 Super
   - Monitor GPU memory usage and adjust accordingly

3. **Mixed Precision Training**:
   - Use AMP (Automatic Mixed Precision) to utilize Tensor Cores
   - Can provide 1.5-2x speedup with minimal accuracy loss

4. **Data Loading Optimization**:
   - Use `tf.data` or PyTorch DataLoader with multiple workers
   - Pre-load data to GPU memory when possible

## Troubleshooting

### NVIDIA Driver Issues

#### Problem: "NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver"

**Symptoms:**
- `nvidia-smi` fails even though `lspci | grep nvidia` shows the GPU
- Error about driver communication

**Solutions:**
1. **Check if already working first**: Always run `nvidia-smi` before making changes
2. **Check kernel modules**: `lsmod | grep nvidia`
3. **Load modules manually**: 
   ```bash
   sudo modprobe nvidia
   sudo modprobe nvidia_drm
   sudo modprobe nvidia_modeset
   ```
4. **If still failing**: `sudo reboot`

#### Problem: Package Version Conflicts

**Symptoms:**
- `Unable to correct problems, you have held broken packages`
- Different NVIDIA package versions (e.g., 535.x vs 570.x)
- Dependencies on `libssl1.1` that doesn't exist

**Root Cause:** 
Mixing Ubuntu repositories with third-party CUDA repositories (e.g., Ubuntu 20.04 CUDA repo on Ubuntu 24.04)

**Solution:**
```bash
# 1. Remove problematic repositories
sudo rm /etc/apt/sources.list.d/cuda-ubuntu20*
sudo rm /etc/apt/sources.list.d/*graphics-drivers*

# 2. Clean up NVIDIA packages
sudo apt purge nvidia-* libnvidia-*
sudo apt autoremove

# 3. Use Ubuntu's repositories only
sudo apt update
sudo ubuntu-drivers autoinstall
# OR: sudo apt install nvidia-driver-535

# 4. Reboot
sudo reboot
```

#### Problem: Secure Boot Interference

**Symptoms:**
- Modules won't load: `modprobe nvidia` fails
- `dmesg` shows signature verification errors

**Solution:**
```bash
# Check secure boot status
sudo apt install mokutil
mokutil --sb-state

# If enabled, either:
# Option A: Disable secure boot in BIOS (easier)
# Option B: Sign NVIDIA modules (more complex)
```

### Best Practices

1. **Always check existing setup first**: Run `nvidia-smi` before making changes
2. **Use Ubuntu's official packages**: Avoid third-party CUDA repositories
3. **Match Ubuntu version**: Don't use Ubuntu 20.04 packages on Ubuntu 24.04
4. **Let TensorFlow/PyTorch handle CUDA**: They include CUDA libraries automatically
5. **Only install CUDA toolkit if needed**: For `nvcc` compiler or development tools

This comprehensive GPU ML setup provides a powerful platform for training and serving machine learning models while integrating seamlessly with your existing data engineering infrastructure!

## 🚀 **Complete Setup Verification**

**Run these commands to verify your entire setup is working correctly:**

### **1. Verify GPU and Drivers**
```bash
# GPU driver check
nvidia-smi
# Should show: GPU details, driver version (e.g., 535.247.01), CUDA version (e.g., 12.2)

# GPU discovery script check
bash $SPARK_HOME/conf/gpu-discovery.sh
# Should output: {"name": "gpu", "addresses": ["0"]}
```

### **2. Verify Python ML Environment**
```bash
# Activate ML environment
source ml-env/bin/activate

# Test TensorFlow GPU
python -c "import tensorflow as tf; print(f'TensorFlow: {tf.__version__}'); print(f'GPUs: {len(tf.config.list_physical_devices(\"GPU\"))}')"
# Should show: TensorFlow version >=2.16.1, GPUs: 1

# Test PyTorch GPU  
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')"
# Should show: PyTorch version, CUDA available: True
```

### **3. Verify Spark GPU Integration**
```bash
# Check worker service status
sudo systemctl status spark-worker
# Should show: active (running)

# Check GPU resources detected by worker
curl -s http://192.168.1.79:8081/json/ | jq '.resources'
# Should show: {"gpu": {"amount": 1, "addresses": ["0"]}}

# Check worker logs for GPU detection
tail -5 /home/sanzad/spark/logs/spark-*-worker-*.out | grep -i gpu
# Should show: "Custom resources for spark.worker: gpu -> [name: gpu, addresses: 0]"
```

### **4. Verify Complete Spark GPU Cluster**
```bash
# Test GPU-enabled Spark application
ssh spark@192.168.1.184 '/home/spark/spark/bin/spark-shell --master spark://192.168.1.184:7077 --conf spark.executor.resource.gpu.amount=1 --conf spark.task.resource.gpu.amount=0.1'

# In Spark shell, run verification:
# ✅ Should start without "No executor resource configs" error
# ✅ Should show GPU optimization warning (normal behavior)
# ✅ Should NOT show Delta Lake ClassNotFoundException (if JARs installed)

# Test basic operations:
sc.getConf.get("spark.master")  // Should return: spark://192.168.1.184:7077
sc.parallelize(1 to 100).count  // Should return: 100

# Test Delta Lake (if installed):
import io.delta.tables._  // Should import without errors

:quit
```

### **5. Verify Services and Access**
```bash
# Check all services running
sudo systemctl status spark-worker jupyter-gpu mlflow-gpu

# Test web interfaces (open in browser):
# - Spark Worker UI: http://192.168.1.79:8081
# - Jupyter Lab: http://192.168.1.79:8888  
# - MLflow UI: http://192.168.1.79:5000
```

### **🎯 Success Checklist**
- ✅ `nvidia-smi` shows GPU and driver working
- ✅ TensorFlow detects GPU (`GPUs: 1`)
- ✅ PyTorch has CUDA available (`True`)
- ✅ Spark worker shows GPU resources in web UI
- ✅ Spark applications can request GPU resources without errors
- ✅ Delta Lake imports work (no ClassNotFoundException)
- ✅ All services (worker, jupyter, mlflow) are running
- ✅ Web UIs are accessible

**If any step fails, check the troubleshooting section above for specific fixes!**
