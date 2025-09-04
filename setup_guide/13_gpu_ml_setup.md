# GPU-Enabled ML Setup Guide (TensorFlow, PyTorch, Spark MLlib)

## Overview
This guide sets up a comprehensive GPU-accelerated machine learning environment on the gpu-node (192.168.1.79) with RTX 2060 Super. The setup includes TensorFlow, PyTorch, Spark MLlib with GPU support, and integration with your existing data engineering infrastructure.

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

## Step 1: NVIDIA Driver and CUDA Installation

### Install NVIDIA Driver:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y build-essential dkms

# Add NVIDIA PPA
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# Install recommended driver
sudo ubuntu-drivers autoinstall

# Or install specific driver version
# sudo apt install nvidia-driver-525

# Reboot to load driver
sudo reboot
```

After reboot, verify driver installation:
```bash
nvidia-smi
lspci | grep -i nvidia
```

### Install CUDA Toolkit:
```bash
# Download and install CUDA 12.0 (compatible with RTX 2060 Super)
wget https://developer.download.nvidia.com/compute/cuda/12.0.0/local_installers/cuda_12.0.0_525.60.13_linux.run

# Make installer executable
chmod +x cuda_12.0.0_525.60.13_linux.run

# Run installer
sudo sh cuda_12.0.0_525.60.13_linux.run

# Follow installer prompts:
# - Uncheck Driver installation (already installed)
# - Check CUDA Toolkit installation
# - Accept license and continue
```

### Set up CUDA environment:
```bash
# Add to ~/.bashrc
echo 'export PATH=/usr/local/cuda-12.0/bin${PATH:+:${PATH}}' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.0/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}' >> ~/.bashrc
echo 'export CUDA_HOME=/usr/local/cuda-12.0' >> ~/.bashrc

# Reload environment
source ~/.bashrc

# Verify CUDA installation
nvcc --version
nvidia-smi
```

### Install cuDNN:
```bash
# Download cuDNN from NVIDIA Developer (requires registration)
# https://developer.nvidia.com/cudnn

# For this example, download cuDNN 8.6.0 for CUDA 12.0
# wget https://developer.download.nvidia.com/compute/cudnn/secure/8.6.0/local_installers/12.0/cudnn-linux-x86_64-8.6.0.163_cuda12-archive.tar.xz

# Extract and install
tar -xvf cudnn-linux-x86_64-8.6.0.163_cuda12-archive.tar.xz

# Copy files to CUDA directory
sudo cp cudnn-linux-x86_64-8.6.0.163_cuda12-archive/include/cudnn*.h /usr/local/cuda-12.0/include
sudo cp cudnn-linux-x86_64-8.6.0.163_cuda12-archive/lib/libcudnn* /usr/local/cuda-12.0/lib64
sudo chmod a+r /usr/local/cuda-12.0/include/cudnn*.h /usr/local/cuda-12.0/lib64/libcudnn*
```

## Step 2: Python Environment Setup

### Install Python and dependencies:
```bash
# Install Python 3.10 and pip
sudo apt install -y python3.10 python3.10-pip python3.10-dev python3.10-venv

# Create Python environment for ML
python3.10 -m venv ml-env
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

# Install TensorFlow GPU 
pip install tensorflow[and-cuda]==2.13.0

# Install additional TensorFlow tools
pip install tensorflow-datasets tensorflow-hub tensorflow-probability
pip install tensorboard tensorflow-addons
pip install tf-agents tensorflow-recommenders

# Install TensorFlow Serving for model deployment
pip install tensorflow-serving-api
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
print(f"GPU available: {tf.test.is_gpu_available()}")

# List physical devices
print("Physical devices:")
for device in tf.config.list_physical_devices():
    print(f"  {device}")

# List GPU devices specifically
gpu_devices = tf.config.list_physical_devices('GPU')
print(f"\nGPU devices: {len(gpu_devices)}")
for gpu in gpu_devices:
    print(f"  {gpu}")
    
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
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install additional PyTorch libraries
pip install torchtext torchdata
pip install pytorch-lightning
pip install transformers datasets accelerate
pip install torch-geometric torch-scatter torch-sparse

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

## Step 5: Spark MLlib with GPU Support

### Install Java and Spark:
```bash
# Install Java 11 (required for Spark)
sudo apt install -y openjdk-11-jdk

# Set JAVA_HOME
echo 'export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64' >> ~/.bashrc
source ~/.bashrc

# Download and install Spark (keeping compatible version)
cd /home/$(whoami)
wget https://dlcdn.apache.org/spark/spark-3.5.6/spark-3.5.6-bin-hadoop3.tgz
tar -xzf spark-3.5.6-bin-hadoop3.tgz
mv spark-3.5.6-bin-hadoop3 spark

# Add Spark to PATH
echo 'export SPARK_HOME=/home/'$(whoami)'/spark' >> ~/.bashrc
echo 'export PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin' >> ~/.bashrc
source ~/.bashrc
```

### Install RAPIDS and GPU-accelerated libraries:
```bash
# Activate ML environment
source ml-env/bin/activate

# Install RAPIDS for GPU-accelerated data science
pip install cudf-cu11 cuml-cu11 cugraph-cu11 cuspatial-cu11 cupy-cuda11x
pip install rapids-dependency-file-generator

# Install PySpark (compatible with Spark 3.5.6)
pip install pyspark==3.5.0

# Install XGBoost with GPU support
pip install xgboost

# Install LightGBM with GPU support
pip install lightgbm

# Install CatBoost
pip install catboost
```

### Configure Spark for GPU:
```bash
# Create Spark GPU configuration
mkdir -p $SPARK_HOME/conf
nano $SPARK_HOME/conf/spark-defaults.conf
```

```properties
# Spark GPU Configuration
spark.master                    spark://192.168.1.184:7077
spark.eventLog.enabled          true
spark.eventLog.dir              /home/$(whoami)/spark/logs
spark.sql.adaptive.enabled      true
spark.sql.adaptive.coalescePartitions.enabled true

# GPU Configuration
spark.task.cpus                 1
spark.executor.cores            2
spark.executor.memory           4g
spark.executor.memoryFraction   0.8

# RAPIDS Integration
spark.sql.execution.arrow.pyspark.enabled true
spark.sql.execution.arrow.pyspark.fallback.enabled true

# GPU ML Libraries
spark.jars.packages             com.nvidia:xgboost4j-spark-gpu_2.12:1.7.3,com.nvidia:xgboost4j-gpu_2.12:1.7.3

# Driver configuration for GPU node
spark.driver.memory             2g
spark.driver.cores              2
```

### Test Spark MLlib with GPU:
```python
# Create test script
nano test_spark_gpu_ml.py
```

```python
import os
os.environ['PYSPARK_PYTHON'] = '/home/' + os.getenv('USER') + '/ml-env/bin/python'
os.environ['PYSPARK_DRIVER_PYTHON'] = '/home/' + os.getenv('USER') + '/ml-env/bin/python'

from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.sql.functions import rand, randn
import cudf
import cuml
import numpy as np
import time

def test_spark_ml():
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("GPU-ML-Test") \
        .config("spark.master", "local[*]") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()
    
    print("=== Spark MLlib Test ===")
    
    # Generate sample data
    df = spark.range(0, 100000).select(
        "id",
        (rand() * 10).alias("feature1"),
        (randn() * 5).alias("feature2"),
        (rand() * 20 + randn() * 3).alias("label")
    )
    
    # Prepare features
    assembler = VectorAssembler(
        inputCols=["feature1", "feature2"],
        outputCol="features"
    )
    
    df_assembled = assembler.transform(df)
    
    # Split data
    train_df, test_df = df_assembled.randomSplit([0.8, 0.2], seed=42)
    
    # Train linear regression
    lr = LinearRegression(featuresCol="features", labelCol="label")
    
    start_time = time.time()
    model = lr.fit(train_df)
    train_time = time.time() - start_time
    
    # Make predictions
    predictions = model.transform(test_df)
    
    # Evaluate
    evaluator = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="rmse")
    rmse = evaluator.evaluate(predictions)
    
    print(f"Spark MLlib Training time: {train_time:.4f} seconds")
    print(f"RMSE: {rmse:.4f}")
    
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

Run the test:
```bash
python test_spark_gpu_ml.py
```

## Step 6: Jupyter Lab Setup with GPU Support

### Install and configure Jupyter:
```bash
# Activate ML environment
source ml-env/bin/activate

# Install JupyterLab with extensions
pip install jupyterlab
pip install jupyterlab-git jupyterlab-github
pip install ipywidgets widgetsnbextension
pip install jupyter-dash

# Install GPU monitoring extensions
pip install jupyterlab-system-monitor
pip install jupyterlab-nvdashboard

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
        tf_model_path = "/home/$(whoami)/models/recommendation_tf"
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
User=$(whoami)
Group=$(whoami)
WorkingDirectory=/home/$(whoami)
Environment=PATH=/home/$(whoami)/ml-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=CUDA_VISIBLE_DEVICES=0
ExecStart=/home/$(whoami)/ml-env/bin/jupyter lab --config=/home/$(whoami)/.jupyter/jupyter_lab_config.py
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
User=$(whoami)
Group=$(whoami)
WorkingDirectory=/home/$(whoami)
Environment=PATH=/home/$(whoami)/ml-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/$(whoami)/ml-env/bin/mlflow server --backend-store-uri postgresql://dataeng:password@192.168.1.184:5432/mlflow_db --default-artifact-root file:///home/$(whoami)/mlflow/artifacts --host 0.0.0.0 --port 5000
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

This comprehensive GPU ML setup provides a powerful platform for training and serving machine learning models while integrating seamlessly with your existing data engineering infrastructure!
