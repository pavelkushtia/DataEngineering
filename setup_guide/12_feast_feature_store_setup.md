# Feast Feature Store Setup Guide

## Overview
Feast (Feature Store) will be set up across your cluster to provide centralized feature management for ML applications. It will integrate with your existing data infrastructure (PostgreSQL, Redis, Spark) to serve both batch and real-time features.

## What is Feast?
Feast is an open-source feature store that helps teams manage and serve machine learning features. It bridges the gap between data and ML by providing a central repository for feature definitions, enabling feature sharing, and serving features consistently for training and inference.

## Architecture Layout
- **Feature Store Core**: cpu-node1 (192.168.1.184)
- **Online Store**: Redis on cpu-node1
- **Offline Store**: PostgreSQL on cpu-node1  
- **Feature Processing**: Spark cluster
- **ML Consumption**: gpu-node (192.168.1.79)

## Prerequisites
- Python 3.8+
- PostgreSQL (from your existing setup)
- Redis (from your existing setup)
- Spark cluster (from your existing setup)
- At least 2GB RAM for Feast services
- Network connectivity between all nodes

## Architecture Overview
```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Feast Feature Store Architecture                      │
├─────────────────────┬─────────────────────┬─────────────────────┬─────────────────┤
│    cpu-node1        │    cpu-node2        │   worker-node3      │   gpu-node      │
│  - Feast Registry   │    - Spark Worker   │   - Spark Worker    │  - ML Models    │
│  - Redis (Online)   │    - Feature Eng    │   - Feature Eng     │  - Inference    │
│  - PostgreSQL       │                     │                     │  - Training     │
│    (Offline)        │                     │                     │                 │
│  192.168.1.184      │  192.168.1.187      │  192.168.1.190      │ 192.168.1.79    │
└─────────────────────┴─────────────────────┴─────────────────────┴─────────────────┘
```

## Step 1: Install Feast (cpu-node1)

```bash
# Install Python dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv

# Create virtual environment for Feast
python3 -m venv feast-env
source feast-env/bin/activate

# Install Feast with all extras
pip install feast[postgres,redis,spark,aws,gcp,azure]

# Install additional dependencies
pip install pandas numpy scipy scikit-learn jupyter boto3

# Verify installation
feast version
```

## Step 2: Create Feast Project Structure

```bash
# Create Feast project directory
mkdir -p /home/sanzad/feast-store
cd /home/sanzad/feast-store

# Initialize Feast repository with PostgreSQL template
feast init -t postgres feast_repo

# During initialization, you'll be prompted for the following:
# Postgres host [localhost]: 192.168.1.184
# Postgres port [5432]: 5432  
# Postgres database name [feast]: analytics_db
# Postgres schema [public]: public
# Postgres username [feast]: dataeng
# Postgres password: [enter your dataeng password]
# Should I upload example data to Postgres (overwriting "feast_driver_hourly_stats" table)? [Y/n]: Y

cd feast_repo

# Create additional directories
mkdir -p {features,data,scripts,notebooks,tests}
```

## Step 3: Configure Feast Feature Store

### Main Feature Store Configuration:
```bash
# Make sure you're in the feast_repo directory
cd /home/sanzad/feast-store/feast_repo

# Edit the feature_store.yaml file (created by feast init)
nano feature_store.yaml
```

**IMPORTANT: Replace the password placeholder with your actual password:**
- `YOUR_DATAENG_PASSWORD_HERE` → Your PostgreSQL dataeng user password  
- `YOUR_REDIS_PASSWORD_HERE` → Your Redis password (if you have one set)

```yaml
project: homelab_ml_platform
registry: registry.db                           # File-based registry (recommended)
provider: local
online_store:
  type: redis
  connection_string: redis://:YOUR_REDIS_PASSWORD_HERE@192.168.1.184:6379/0

offline_store:
  type: postgres
  host: 192.168.1.184
  port: 5432
  database: analytics_db
  user: dataeng
  password: YOUR_DATAENG_PASSWORD_HERE

batch_engine:
  type: spark.engine
  spark_conf:
    spark.master: "spark://192.168.1.184:7077"
    spark.executor.memory: "2g"
    spark.executor.cores: "2"
    spark.sql.adaptive.enabled: "true"

entity_key_serialization_version: 2

flags:
  alpha_features: true
  beta_features: true
```

## Step 4: No Registry Database Setup Needed

**IMPORTANT CHANGE:** Feast uses a **file-based registry** (not PostgreSQL) in the working configuration. The registry will be automatically created as `registry.db` in your feast repo directory.

**Why file-based registry:**
- Supported and reliable in Feast 0.53.0
- No additional database setup required  
- Automatically backed up with your feast repo
- PostgreSQL registry support is not available in this version

## Step 5: Test Feast with the Generated Example

**IMPORTANT:** Before creating custom features, let's test Feast with the working example that was automatically generated. This ensures everything is working properly.

### Test the basic setup:
```bash
# Make sure you're in the feast_repo directory
cd /home/sanzad/feast-store/feast_repo

# Activate the feast environment and test the generated example
source /home/sanzad/feast-env/bin/activate

# Apply the generated feature definitions (this should work!)
feast apply

# If successful, you should see output about creating feature views and services
```

**What this does:**
- Uses the driver example that was automatically created with sample data
- Tests the core Feast functionality with working PostgreSQL connections
- Validates that your configuration is correct before customizing

### Understanding the Generated Example

The generated example includes:
- **Driver entity** - represents drivers in a ride-sharing scenario
- **Driver stats table** - `feast_driver_hourly_stats` (already created with sample data)
- **Feature views** - driver performance metrics (conversion rate, acceptance rate, daily trips)
- **Feature services** - grouped features for ML models

You can examine these files:
```bash
# View the working example
cat feast_repo/feature_repo/example_repo.py

# This file shows the correct import syntax and working feature definitions
```

### Working Example Structure

The successful setup creates these files:

**1. feature_store.yaml** (main configuration)
**2. example_repo.py** (feature definitions) 
**3. registry.db** (created automatically)

### Creating Custom Features (After Basic Test Works)

If you want to create your own features, here's the **working pattern**:

```python
# Create a new feature file (e.g., my_features.py)
from datetime import timedelta
from feast import Entity, FeatureService, FeatureView, Field
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource
from feast.types import Float32, Int64, String

# 1. Define Entity
user = Entity(
    name="user", 
    join_keys=["user_id"],
    description="User entity"
)

# 2. Define Data Source
user_source = PostgreSQLSource(
    name="user_stats_source",
    query="SELECT user_id, total_orders, avg_order_value, event_timestamp, created FROM user_stats",
    timestamp_field="event_timestamp",
    created_timestamp_column="created",
)

# 3. Define Feature View
user_stats_fv = FeatureView(
    name="user_stats",
    entities=[user],
    ttl=timedelta(days=7),
    schema=[
        Field(name="total_orders", dtype=Int64),
        Field(name="avg_order_value", dtype=Float32),
    ],
    online=True,
    source=user_source,
    tags={"team": "analytics"},
)

# 4. Define Feature Service
user_service = FeatureService(
    name="user_features_v1",
    features=[user_stats_fv],
)
```

**Key points that make this work:**
- Use the **correct import path** for PostgreSQL sources
- Keep it **simple** - don't create complex nested directories
- **Test each addition** with `feast apply`
- Make sure your database tables exist before creating sources
- **Quote numeric passwords** in YAML configuration

## Step 6: Verify Feast Deployment

After successfully running `feast apply` in Step 5, verify everything is working:

```bash
# Make sure you're in the right directory and environment is active
cd /home/sanzad/feast-store/feast_repo
source /home/sanzad/feast-env/bin/activate

# Check what was deployed
feast feature-views list
feast entities list  
feast feature-services list

# Test feature serving (optional - materializes features to online store)
feast materialize-incremental $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)
```

**Expected output:**
- You should see the `driver_hourly_stats` feature view
- The `driver` entity should be listed
- Feature services like `driver_activity_v1` should appear
- Materialization should complete successfully

## Step 7: Basic Feature Serving Test

Test that you can actually retrieve features:

```bash
# Test online feature serving
cd /home/sanzad/feast-store/feast_repo
source /home/sanzad/feast-env/bin/activate

# Create a simple test script
cat > test_features.py << 'EOF'
from feast import FeatureStore
import pandas as pd
from datetime import datetime

# Initialize feature store
fs = FeatureStore(repo_path=".")

# Test getting features
entity_rows = [
    {"driver": 1001},
    {"driver": 1002},
]

# Get online features
features = fs.get_online_features(
    feature_service="driver_activity_v1",
    entity_rows=entity_rows,
).to_df()

print("Retrieved features:")
print(features)
EOF

# Run the test
python test_features.py
```

**If this works, your Feast Feature Store is fully operational!**

## Step 8: Optional - Create Custom Features

Only after the basic setup works, you can add your own features following the working pattern shown above.

## Step 9: Monitoring and Basic Operations

### Start Feast Feature Server (for REST API access):
```bash
cd /home/sanzad/feast-store/feast_repo
source /home/sanzad/feast-env/bin/activate

# Start feature server in background
nohup feast serve --host 0.0.0.0 --port 6566 > feast-server.log 2>&1 &
```

### Basic operational commands:
```bash
# List all feature components
feast feature-views list
feast entities list
feast feature-services list

# Validate feature definitions  
feast validate

# Materialize features to online store
feast materialize-incremental $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)
```

## Conclusion

🎉 **Congratulations!** You now have a **working Feast Feature Store** integrated with your HomeLab infrastructure.

### What You've Accomplished:

✅ **Feature Store Core** - Running on cpu-node1 with file-based registry  
✅ **Online Store** - Redis for fast feature serving (< 10ms)  
✅ **Offline Store** - PostgreSQL for training data and historical features  
✅ **Working Example** - Driver statistics features ready to use  
✅ **Integration Ready** - Can connect to your GPU node for ML models  

### Next Steps:

1. **Create your own features** using the working pattern shown above
2. **Connect your ML models** on the GPU node to consume features  
3. **Set up regular materialization** with cron jobs for fresh features
4. **Monitor feature freshness** and performance

### Key Lessons Learned:

- **File-based registry** works better than PostgreSQL registry in Feast 0.53.0
- **Quote numeric passwords** in YAML configurations  
- **Use correct import paths** for PostgreSQL sources
- **Keep it simple** - complex nested directories cause import issues
- **Test incrementally** - add one feature at a time and verify with `feast apply`

Your Feast Feature Store is now the **central nervous system** for your ML infrastructure, ensuring consistent, reliable features across all your machine learning applications! 🚀

---

**Documentation Status:** ✅ **Updated to reflect working configuration**  
**Last Tested:** Successfully working with Feast 0.53.0, PostgreSQL, and Redis
