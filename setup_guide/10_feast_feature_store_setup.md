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

# Initialize Feast repository
feast init -t postgres feast_repo
cd feast_repo

# Create additional directories
mkdir -p {features,data,scripts,notebooks,tests}
```

## Step 3: Configure Feast Feature Store

### Main Feature Store Configuration:
```python
# Edit feature_store.yaml
nano feature_store.yaml
```

```yaml
project: homelab_ml_platform
registry: postgresql://dataeng:password@192.168.1.184:5432/feast_registry
provider: local
online_store:
  type: redis
  connection_string: redis://:your-redis-password@192.168.1.184:6379/0

offline_store:
  type: postgres
  host: 192.168.1.184
  port: 5432
  database: analytics_db
  user: dataeng
  password: password

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

## Step 4: Set Up Feast Registry Database

```bash
# Connect to PostgreSQL and create Feast registry database
psql -U dataeng -h 192.168.1.184 -d postgres

CREATE DATABASE feast_registry;
GRANT ALL PRIVILEGES ON DATABASE feast_registry TO dataeng;

# Exit PostgreSQL
\q
```

## Step 5: Define Feature Entities and Sources

### Create entity definitions:
```python
# Create features/entities.py
nano features/entities.py
```

```python
from feast import Entity, ValueType

# User entity
user = Entity(
    name="user",
    description="User entity for personalization features",
    value_type=ValueType.INT64,
)

# Product entity  
product = Entity(
    name="product",
    description="Product entity for product features",
    value_type=ValueType.STRING,
)

# Transaction entity
transaction = Entity(
    name="transaction",
    description="Transaction entity for financial features", 
    value_type=ValueType.STRING,
)

# Location entity
location = Entity(
    name="location",
    description="Geographic location entity",
    value_type=ValueType.STRING,
)
```

### Create data sources:
```python
# Create features/sources.py
nano features/sources.py
```

```python
from feast import BigQuerySource, FileSource
from feast.data_source import DataSource
from feast.infra.offline_stores.postgres_source import PostgreSQLSource
from datetime import datetime

# PostgreSQL data sources
user_profile_source = PostgreSQLSource(
    name="user_profile_source",
    query="""
        SELECT 
            user_id,
            age,
            income,
            signup_date,
            last_login,
            account_status,
            preferred_category,
            created_timestamp
        FROM user_profiles
    """,
    timestamp_field="created_timestamp",
)

user_activity_source = PostgreSQLSource(
    name="user_activity_source", 
    query="""
        SELECT
            user_id,
            total_sessions_7d,
            total_sessions_30d,
            avg_session_duration_7d,
            total_pageviews_7d,
            total_purchases_30d,
            avg_order_value_30d,
            last_purchase_amount,
            days_since_last_purchase,
            created_timestamp
        FROM user_activity_features
    """,
    timestamp_field="created_timestamp",
)

product_features_source = PostgreSQLSource(
    name="product_features_source",
    query="""
        SELECT
            product_id,
            category,
            price,
            avg_rating,
            total_reviews,
            inventory_count,
            brand,
            popularity_score_7d,
            popularity_score_30d,
            created_timestamp
        FROM product_features
    """,
    timestamp_field="created_timestamp",
)

transaction_features_source = PostgreSQLSource(
    name="transaction_features_source",
    query="""
        SELECT
            transaction_id,
            user_id,
            amount,
            payment_method,
            is_weekend,
            hour_of_day,
            merchant_category,
            location_risk_score,
            velocity_1h,
            velocity_24h,
            created_timestamp
        FROM transaction_features
    """,
    timestamp_field="created_timestamp",
)

# Real-time streaming source (for future use)
kafka_source = {
    'name': 'user_events_kafka',
    'kafka_bootstrap_servers': '192.168.1.184:9092,192.168.1.187:9092,192.168.1.190:9092',
    'topic': 'user-events',
    'timestamp_field': 'event_timestamp',
}
```

### Create feature views:
```python
# Create features/feature_views.py  
nano features/feature_views.py
```

```python
from feast import FeatureView, Field
from feast.types import Float32, Int64, String, Bool, UnixTimestamp
from datetime import timedelta
from features.entities import user, product, transaction
from features.sources import (
    user_profile_source, 
    user_activity_source,
    product_features_source,
    transaction_features_source
)

# User profile features
user_profile_fv = FeatureView(
    name="user_profile_features",
    entities=[user],
    ttl=timedelta(days=365),
    schema=[
        Field(name="age", dtype=Int64),
        Field(name="income", dtype=Float32),
        Field(name="account_status", dtype=String),
        Field(name="preferred_category", dtype=String),
        Field(name="days_since_signup", dtype=Int64),
    ],
    source=user_profile_source,
    tags={"team": "user_analytics"},
)

# User activity features
user_activity_fv = FeatureView(
    name="user_activity_features", 
    entities=[user],
    ttl=timedelta(days=30),
    schema=[
        Field(name="total_sessions_7d", dtype=Int64),
        Field(name="total_sessions_30d", dtype=Int64),
        Field(name="avg_session_duration_7d", dtype=Float32),
        Field(name="total_pageviews_7d", dtype=Int64),
        Field(name="total_purchases_30d", dtype=Int64),
        Field(name="avg_order_value_30d", dtype=Float32),
        Field(name="last_purchase_amount", dtype=Float32),
        Field(name="days_since_last_purchase", dtype=Int64),
    ],
    source=user_activity_source,
    tags={"team": "user_analytics", "pii": "false"},
)

# Product features
product_features_fv = FeatureView(
    name="product_features",
    entities=[product], 
    ttl=timedelta(days=30),
    schema=[
        Field(name="category", dtype=String),
        Field(name="price", dtype=Float32),
        Field(name="avg_rating", dtype=Float32),
        Field(name="total_reviews", dtype=Int64),
        Field(name="inventory_count", dtype=Int64),
        Field(name="brand", dtype=String),
        Field(name="popularity_score_7d", dtype=Float32),
        Field(name="popularity_score_30d", dtype=Float32),
    ],
    source=product_features_source,
    tags={"team": "product_analytics"},
)

# Transaction risk features
transaction_risk_fv = FeatureView(
    name="transaction_risk_features",
    entities=[transaction],
    ttl=timedelta(days=1),  # Short TTL for fraud detection
    schema=[
        Field(name="amount", dtype=Float32),
        Field(name="payment_method", dtype=String),
        Field(name="is_weekend", dtype=Bool),
        Field(name="hour_of_day", dtype=Int64),
        Field(name="merchant_category", dtype=String),
        Field(name="location_risk_score", dtype=Float32),
        Field(name="velocity_1h", dtype=Float32),
        Field(name="velocity_24h", dtype=Float32),
    ],
    source=transaction_features_source,
    tags={"team": "fraud_detection", "criticality": "high"},
)
```

### Create feature services:
```python
# Create features/feature_services.py
nano features/feature_services.py
```

```python
from feast import FeatureService
from features.feature_views import (
    user_profile_fv, 
    user_activity_fv, 
    product_features_fv,
    transaction_risk_fv
)

# Recommendation service
recommendation_service = FeatureService(
    name="recommendation_v1",
    features=[
        user_profile_fv[["age", "preferred_category"]],
        user_activity_fv[["total_sessions_7d", "avg_order_value_30d", "days_since_last_purchase"]],
        product_features_fv[["category", "price", "avg_rating", "popularity_score_7d"]],
    ],
    tags={"team": "ml_platform", "use_case": "recommendations"},
)

# Fraud detection service  
fraud_detection_service = FeatureService(
    name="fraud_detection_v1",
    features=[
        user_profile_fv[["age", "account_status"]],
        user_activity_fv[["total_purchases_30d", "avg_order_value_30d"]],
        transaction_risk_fv[["amount", "payment_method", "location_risk_score", "velocity_1h", "velocity_24h"]],
    ],
    tags={"team": "fraud_team", "use_case": "fraud_detection", "criticality": "high"},
)

# Customer segmentation service
customer_segmentation_service = FeatureService(
    name="customer_segmentation_v1", 
    features=[
        user_profile_fv[["age", "income", "account_status", "preferred_category"]],
        user_activity_fv,  # All features
    ],
    tags={"team": "marketing", "use_case": "segmentation"},
)

# Real-time personalization service
personalization_service = FeatureService(
    name="personalization_v1",
    features=[
        user_profile_fv[["age", "preferred_category"]],
        user_activity_fv[["total_sessions_7d", "avg_session_duration_7d", "days_since_last_purchase"]],
    ],
    tags={"team": "personalization", "latency": "real_time"},
)
```

### Create the main definitions file:
```python
# Create feature_definitions.py
nano feature_definitions.py
```

```python
from features.entities import user, product, transaction, location
from features.feature_views import (
    user_profile_fv,
    user_activity_fv, 
    product_features_fv,
    transaction_risk_fv
)
from features.feature_services import (
    recommendation_service,
    fraud_detection_service,
    customer_segmentation_service,
    personalization_service
)
```

## Step 6: Apply Feast Configuration

```bash
# Activate Feast environment
source /home/sanzad/feast-env/bin/activate
cd /home/sanzad/feast-store/feast_repo

# Apply feature store configuration  
feast apply

# Verify deployment
feast feature-views list
feast entities list
feast feature-services list
```

## Step 7: Create Sample Data and Feature Engineering

### Create sample data generation script:
```python
# Create data/generate_sample_data.py
nano data/generate_sample_data.py
```

```python
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import psycopg2
from sqlalchemy import create_engine
import random

class SampleDataGenerator:
    def __init__(self):
        self.engine = create_engine('postgresql://dataeng:password@192.168.1.184:5432/analytics_db')
        
    def generate_user_profiles(self, num_users=10000):
        """Generate user profile data"""
        users = []
        
        for i in range(1, num_users + 1):
            user = {
                'user_id': i,
                'age': np.random.normal(35, 12),
                'income': np.random.lognormal(10.5, 0.5),
                'signup_date': datetime.now() - timedelta(days=random.randint(1, 1000)),
                'last_login': datetime.now() - timedelta(days=random.randint(0, 30)),
                'account_status': random.choice(['active', 'inactive', 'suspended']),
                'preferred_category': random.choice(['electronics', 'clothing', 'books', 'sports', 'home']),
                'created_timestamp': datetime.now()
            }
            users.append(user)
        
        df = pd.DataFrame(users)
        df['age'] = df['age'].clip(18, 80).astype(int)
        df['income'] = df['income'].clip(20000, 500000).astype(float)
        
        # Save to PostgreSQL
        df.to_sql('user_profiles', self.engine, if_exists='replace', index=False)
        print(f"Generated {len(df)} user profiles")
        return df
    
    def generate_user_activity_features(self, user_df):
        """Generate user activity features"""
        activities = []
        
        for _, user in user_df.iterrows():
            activity = {
                'user_id': user['user_id'],
                'total_sessions_7d': np.random.poisson(5),
                'total_sessions_30d': np.random.poisson(20), 
                'avg_session_duration_7d': np.random.exponential(15),
                'total_pageviews_7d': np.random.poisson(25),
                'total_purchases_30d': np.random.poisson(3),
                'avg_order_value_30d': np.random.lognormal(4, 0.5),
                'last_purchase_amount': np.random.lognormal(3.5, 0.8),
                'days_since_last_purchase': random.randint(0, 60),
                'created_timestamp': datetime.now()
            }
            activities.append(activity)
        
        df = pd.DataFrame(activities)
        df.to_sql('user_activity_features', self.engine, if_exists='replace', index=False)
        print(f"Generated {len(df)} user activity records")
        return df
    
    def generate_product_features(self, num_products=5000):
        """Generate product features"""
        products = []
        categories = ['electronics', 'clothing', 'books', 'sports', 'home', 'beauty', 'automotive']
        brands = ['Brand_' + str(i) for i in range(1, 51)]
        
        for i in range(1, num_products + 1):
            product = {
                'product_id': f'product_{i}',
                'category': random.choice(categories),
                'price': np.random.lognormal(3, 1),
                'avg_rating': np.random.normal(4, 0.5),
                'total_reviews': np.random.poisson(100),
                'inventory_count': random.randint(0, 1000),
                'brand': random.choice(brands),
                'popularity_score_7d': np.random.exponential(10),
                'popularity_score_30d': np.random.exponential(30),
                'created_timestamp': datetime.now()
            }
            products.append(product)
        
        df = pd.DataFrame(products)
        df['price'] = df['price'].clip(5, 5000).round(2)
        df['avg_rating'] = df['avg_rating'].clip(1, 5).round(1)
        
        df.to_sql('product_features', self.engine, if_exists='replace', index=False)
        print(f"Generated {len(df)} product records")
        return df
    
    def generate_transaction_features(self, num_transactions=50000):
        """Generate transaction features for fraud detection"""
        transactions = []
        payment_methods = ['credit_card', 'debit_card', 'paypal', 'apple_pay', 'bank_transfer']
        merchant_categories = ['retail', 'restaurant', 'gas_station', 'online', 'grocery']
        
        for i in range(1, num_transactions + 1):
            is_weekend = random.choice([True, False])
            hour = random.randint(0, 23)
            
            transaction = {
                'transaction_id': f'txn_{i}',
                'user_id': random.randint(1, 10000),
                'amount': np.random.lognormal(3, 1),
                'payment_method': random.choice(payment_methods),
                'is_weekend': is_weekend,
                'hour_of_day': hour,
                'merchant_category': random.choice(merchant_categories),
                'location_risk_score': np.random.beta(2, 5),  # Biased towards low risk
                'velocity_1h': np.random.poisson(2),
                'velocity_24h': np.random.poisson(10), 
                'created_timestamp': datetime.now() - timedelta(days=random.randint(0, 30))
            }
            transactions.append(transaction)
        
        df = pd.DataFrame(transactions)
        df['amount'] = df['amount'].clip(1, 10000).round(2)
        df['location_risk_score'] = df['location_risk_score'].round(3)
        
        df.to_sql('transaction_features', self.engine, if_exists='replace', index=False)
        print(f"Generated {len(df)} transaction records")
        return df
    
    def generate_all_data(self):
        """Generate all sample datasets"""
        print("Generating sample data for Feast feature store...")
        
        user_df = self.generate_user_profiles()
        self.generate_user_activity_features(user_df)
        self.generate_product_features()
        self.generate_transaction_features()
        
        print("Sample data generation completed!")

if __name__ == "__main__":
    generator = SampleDataGenerator()
    generator.generate_all_data()
```

Run the data generation:
```bash
cd /home/sanzad/feast-store/feast_repo
python data/generate_sample_data.py
```

## Step 8: Materialize Features to Online Store

```bash
# Materialize features from offline to online store
feast materialize-incremental $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S)

# Or materialize for specific time range
feast materialize 2023-01-01T00:00:00 2023-12-31T23:59:59
```

## Step 9: Feature Serving Examples

### Python SDK for feature retrieval:
```python
# Create scripts/feature_serving_examples.py
nano scripts/feature_serving_examples.py
```

```python
import os
import sys
from feast import FeatureStore
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Change to feast repo directory
os.chdir('/home/sanzad/feast-store/feast_repo')

# Initialize feature store
fs = FeatureStore(repo_path=".")

class FeatureServingExamples:
    def __init__(self):
        self.fs = fs
    
    def get_online_features_example(self):
        """Example of real-time feature serving"""
        print("=== Online Feature Serving Example ===")
        
        # Define entity keys
        entity_rows = [
            {"user": 1},
            {"user": 2}, 
            {"user": 3},
        ]
        
        # Get features from feature service
        features = self.fs.get_online_features(
            features=[
                "user_profile_features:age",
                "user_profile_features:preferred_category",
                "user_activity_features:total_sessions_7d",
                "user_activity_features:avg_order_value_30d",
            ],
            entity_rows=entity_rows,
        )
        
        # Convert to DataFrame
        features_df = features.to_df()
        print("Online features:")
        print(features_df)
        return features_df
    
    def get_historical_features_example(self):
        """Example of batch feature serving for training"""
        print("\n=== Historical Feature Serving Example ===")
        
        # Create entity DataFrame with timestamps  
        entity_df = pd.DataFrame({
            "user": [1, 2, 3, 4, 5],
            "event_timestamp": [datetime.now() - timedelta(days=i) for i in range(5)]
        })
        
        # Get historical features
        training_df = self.fs.get_historical_features(
            entity_df=entity_df,
            features=[
                "user_profile_features:age",
                "user_profile_features:income", 
                "user_profile_features:preferred_category",
                "user_activity_features:total_sessions_7d",
                "user_activity_features:total_purchases_30d",
                "user_activity_features:avg_order_value_30d",
            ],
        ).to_df()
        
        print("Historical features for training:")
        print(training_df.head())
        return training_df
    
    def feature_service_example(self):
        """Example using feature services"""
        print("\n=== Feature Service Example ===")
        
        entity_rows = [{"user": i} for i in range(1, 6)]
        
        # Use recommendation feature service
        rec_features = self.fs.get_online_features(
            feature_service="recommendation_v1",
            entity_rows=entity_rows,
        ).to_df()
        
        print("Recommendation service features:")
        print(rec_features)
        
        # Use fraud detection feature service
        fraud_entity_rows = [
            {"user": 1, "transaction": "txn_1"},
            {"user": 2, "transaction": "txn_2"},
        ]
        
        fraud_features = self.fs.get_online_features(
            feature_service="fraud_detection_v1", 
            entity_rows=fraud_entity_rows,
        ).to_df()
        
        print("\nFraud detection service features:")
        print(fraud_features)
        
        return rec_features, fraud_features
    
    def batch_scoring_example(self):
        """Example of batch scoring for ML model"""
        print("\n=== Batch Scoring Example ===")
        
        # Create scoring dataset
        scoring_entities = pd.DataFrame({
            "user": range(1, 101),  # Score for 100 users
            "event_timestamp": [datetime.now()] * 100
        })
        
        # Get features for scoring
        scoring_features = self.fs.get_historical_features(
            entity_df=scoring_entities,
            features=[
                "user_profile_features:age",
                "user_profile_features:income",
                "user_activity_features:total_sessions_7d",
                "user_activity_features:days_since_last_purchase",
            ],
        ).to_df()
        
        print(f"Batch scoring features shape: {scoring_features.shape}")
        print(scoring_features.head())
        
        return scoring_features
    
    def real_time_inference_example(self):
        """Simulate real-time model inference"""
        print("\n=== Real-time Inference Simulation ===")
        
        # Simulate incoming requests
        for user_id in [1, 2, 3]:
            # Get features for real-time inference
            features = self.fs.get_online_features(
                feature_service="recommendation_v1",
                entity_rows=[{"user": user_id}],
            ).to_df()
            
            # Extract feature values (would feed into ML model)
            age = features['age'].values[0] 
            preferred_category = features['preferred_category'].values[0]
            sessions_7d = features['total_sessions_7d'].values[0]
            avg_order_value = features['avg_order_value_30d'].values[0]
            
            # Simulate model prediction (placeholder)
            prediction_score = np.random.random()
            
            print(f"User {user_id}: Age={age}, Category={preferred_category}, "
                  f"Sessions={sessions_7d}, AOV=${avg_order_value:.2f} "
                  f"-> Prediction: {prediction_score:.3f}")

def main():
    examples = FeatureServingExamples()
    
    # Run all examples
    examples.get_online_features_example()
    examples.get_historical_features_example() 
    examples.feature_service_example()
    examples.batch_scoring_example()
    examples.real_time_inference_example()

if __name__ == "__main__":
    main()
```

Run the examples:
```bash
cd /home/sanzad/feast-store/feast_repo
python scripts/feature_serving_examples.py
```

## Step 10: Integration with ML Pipeline (GPU Node)

### Create ML integration script for the GPU node:
```python
# Create scripts/gpu_node_integration.py
nano scripts/gpu_node_integration.py
```

```python
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime
import redis
import pickle

class GPUNodeFeatureClient:
    """Feature client for GPU node ML applications"""
    
    def __init__(self, feast_server_url='http://192.168.1.184:6566',
                 redis_host='192.168.1.184', redis_password='your-redis-password'):
        self.feast_server_url = feast_server_url
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=6379, 
            password=redis_password,
            decode_responses=True
        )
    
    def get_features_for_inference(self, user_ids, use_cache=True):
        """Get features for real-time inference on GPU node"""
        
        # Check cache first if enabled
        if use_cache:
            cached_features = self.get_cached_features(user_ids)
            if cached_features is not None and len(cached_features) == len(user_ids):
                return cached_features
        
        # If not in cache, get from Feast
        from feast import FeatureStore
        import os
        
        # Initialize feature store (assuming mounted/shared filesystem)
        fs = FeatureStore(repo_path="/shared/feast_repo")  # Adjust path
        
        entity_rows = [{"user": user_id} for user_id in user_ids]
        
        features = fs.get_online_features(
            feature_service="recommendation_v1",
            entity_rows=entity_rows,
        ).to_df()
        
        # Cache the features for future use
        if use_cache:
            self.cache_features(user_ids, features)
        
        return features
    
    def get_cached_features(self, user_ids):
        """Get features from Redis cache"""
        try:
            cached_data = []
            all_found = True
            
            for user_id in user_ids:
                cache_key = f"features:user:{user_id}"
                cached = self.redis_client.get(cache_key)
                
                if cached:
                    cached_data.append(json.loads(cached))
                else:
                    all_found = False
                    break
            
            if all_found:
                return pd.DataFrame(cached_data)
                
        except Exception as e:
            print(f"Cache retrieval error: {e}")
        
        return None
    
    def cache_features(self, user_ids, features_df, ttl=300):
        """Cache features in Redis"""
        try:
            for i, user_id in enumerate(user_ids):
                cache_key = f"features:user:{user_id}"
                feature_dict = features_df.iloc[i].to_dict()
                
                self.redis_client.setex(
                    cache_key, 
                    ttl, 
                    json.dumps(feature_dict, default=str)
                )
        
        except Exception as e:
            print(f"Cache storage error: {e}")
    
    def prepare_features_for_model(self, features_df, model_name):
        """Prepare features in the format expected by specific models"""
        
        if model_name == "recommendation_model":
            # Prepare features for recommendation model
            feature_columns = [
                'age', 'total_sessions_7d', 'avg_order_value_30d', 'days_since_last_purchase'
            ]
            
            # Handle missing values
            processed_features = features_df[feature_columns].fillna(0)
            
            # Normalize if needed
            processed_features['age'] = processed_features['age'] / 100.0  # Scale age
            processed_features['avg_order_value_30d'] = np.log1p(processed_features['avg_order_value_30d'])
            
            return processed_features.values
        
        elif model_name == "fraud_detection_model":
            # Different preprocessing for fraud model
            feature_columns = ['amount', 'velocity_1h', 'velocity_24h', 'location_risk_score']
            return features_df[feature_columns].fillna(0).values
        
        else:
            return features_df.values
    
    def batch_feature_engineering(self, entity_df, target_date=None):
        """Perform batch feature engineering for training"""
        if target_date is None:
            target_date = datetime.now()
        
        # Add timestamp column
        entity_df['event_timestamp'] = target_date
        
        from feast import FeatureStore
        fs = FeatureStore(repo_path="/shared/feast_repo")
        
        # Get historical features for training
        training_features = fs.get_historical_features(
            entity_df=entity_df,
            features=[
                "user_profile_features:age",
                "user_profile_features:income",
                "user_profile_features:preferred_category", 
                "user_activity_features:total_sessions_7d",
                "user_activity_features:total_sessions_30d",
                "user_activity_features:total_purchases_30d",
                "user_activity_features:avg_order_value_30d",
                "user_activity_features:days_since_last_purchase",
            ],
        ).to_df()
        
        return training_features
    
    def stream_features_for_online_learning(self):
        """Stream features for online learning models"""
        # This would integrate with your streaming pipeline
        # For now, simulate streaming data
        
        while True:
            # Get random user for simulation
            user_id = np.random.randint(1, 1000)
            
            # Get fresh features
            features = self.get_features_for_inference([user_id], use_cache=False)
            
            # Yield features for online learning
            yield {
                'user_id': user_id,
                'features': features.iloc[0].to_dict(),
                'timestamp': datetime.now()
            }

# Usage example
if __name__ == "__main__":
    client = GPUNodeFeatureClient()
    
    # Example: Get features for inference
    test_users = [1, 2, 3, 4, 5]
    features = client.get_features_for_inference(test_users)
    print("Features for inference:")
    print(features)
    
    # Example: Prepare features for specific model
    model_features = client.prepare_features_for_model(features, "recommendation_model")
    print(f"Model-ready features shape: {model_features.shape}")
```

## Step 11: Monitoring and Observability

### Create feature store monitoring:
```python
# Create scripts/feast_monitoring.py
nano scripts/feast_monitoring.py
```

```python
import os
import time
import psutil
import redis
from feast import FeatureStore
from datetime import datetime, timedelta
import pandas as pd

class FeastMonitoring:
    def __init__(self):
        self.fs = FeatureStore(repo_path="/home/sanzad/feast-store/feast_repo")
        self.redis_client = redis.Redis(
            host='192.168.1.184', 
            password='your-redis-password',
            decode_responses=True
        )
    
    def check_feature_store_health(self):
        """Check overall feature store health"""
        health_status = {
            'timestamp': datetime.now(),
            'registry_accessible': False,
            'online_store_accessible': False,
            'offline_store_accessible': False,
            'feature_views_count': 0,
            'entities_count': 0,
            'feature_services_count': 0,
        }
        
        try:
            # Check registry
            feature_views = self.fs.list_feature_views()
            health_status['feature_views_count'] = len(feature_views)
            health_status['registry_accessible'] = True
            
            entities = self.fs.list_entities()
            health_status['entities_count'] = len(entities)
            
            feature_services = self.fs.list_feature_services()
            health_status['feature_services_count'] = len(feature_services)
            
            # Check online store (Redis)
            self.redis_client.ping()
            health_status['online_store_accessible'] = True
            
            # Check offline store (PostgreSQL)
            test_query = """
                SELECT 1 as test
                FROM user_profiles 
                LIMIT 1
            """
            from sqlalchemy import create_engine, text
            engine = create_engine('postgresql://dataeng:password@192.168.1.184:5432/analytics_db')
            with engine.connect() as conn:
                result = conn.execute(text(test_query))
                health_status['offline_store_accessible'] = True
            
        except Exception as e:
            print(f"Health check error: {e}")
        
        return health_status
    
    def monitor_feature_freshness(self):
        """Monitor feature freshness"""
        freshness_report = {}
        
        try:
            # Check when features were last materialized
            feature_views = self.fs.list_feature_views()
            
            for fv in feature_views:
                # Get metadata about last materialization
                # This is a simplified check - in production you'd have more sophisticated monitoring
                freshness_report[fv.name] = {
                    'ttl_days': fv.ttl.days if fv.ttl else None,
                    'last_materialization': 'unknown',  # Would need to track this
                    'status': 'unknown'
                }
        
        except Exception as e:
            print(f"Freshness monitoring error: {e}")
        
        return freshness_report
    
    def monitor_online_store_performance(self):
        """Monitor online store (Redis) performance"""
        try:
            redis_info = self.redis_client.info()
            
            performance_metrics = {
                'connected_clients': redis_info.get('connected_clients', 0),
                'used_memory_human': redis_info.get('used_memory_human', '0B'),
                'used_memory_peak_human': redis_info.get('used_memory_peak_human', '0B'),
                'total_commands_processed': redis_info.get('total_commands_processed', 0),
                'instantaneous_ops_per_sec': redis_info.get('instantaneous_ops_per_sec', 0),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0),
                'hit_rate': self.calculate_hit_rate(redis_info)
            }
            
            return performance_metrics
            
        except Exception as e:
            print(f"Redis monitoring error: {e}")
            return {}
    
    def calculate_hit_rate(self, redis_info):
        """Calculate cache hit rate"""
        hits = redis_info.get('keyspace_hits', 0)
        misses = redis_info.get('keyspace_misses', 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0
    
    def monitor_feature_serving_latency(self, sample_size=10):
        """Monitor feature serving latency"""
        latencies = []
        
        try:
            # Test online feature serving latency
            entity_rows = [{"user": i} for i in range(1, sample_size + 1)]
            
            start_time = time.time()
            
            features = self.fs.get_online_features(
                features=[
                    "user_profile_features:age",
                    "user_activity_features:total_sessions_7d",
                ],
                entity_rows=entity_rows,
            )
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            return {
                'online_serving_latency_ms': latency_ms,
                'sample_size': sample_size,
                'avg_latency_per_entity_ms': latency_ms / sample_size
            }
            
        except Exception as e:
            print(f"Latency monitoring error: {e}")
            return {}
    
    def generate_monitoring_report(self):
        """Generate comprehensive monitoring report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'health_status': self.check_feature_store_health(),
            'freshness_report': self.monitor_feature_freshness(),
            'online_store_performance': self.monitor_online_store_performance(),
            'serving_latency': self.monitor_feature_serving_latency(),
        }
        
        return report
    
    def continuous_monitoring(self, interval_seconds=60):
        """Run continuous monitoring"""
        print("Starting Feast monitoring...")
        
        while True:
            try:
                report = self.generate_monitoring_report()
                
                print(f"\n=== Feast Monitoring Report - {report['timestamp']} ===")
                
                # Health status
                health = report['health_status']
                print(f"Registry: {'✓' if health['registry_accessible'] else '✗'}")
                print(f"Online Store: {'✓' if health['online_store_accessible'] else '✗'}")
                print(f"Offline Store: {'✓' if health['offline_store_accessible'] else '✗'}")
                print(f"Feature Views: {health['feature_views_count']}")
                print(f"Entities: {health['entities_count']}")
                print(f"Feature Services: {health['feature_services_count']}")
                
                # Performance
                perf = report['online_store_performance']
                if perf:
                    print(f"Redis Memory: {perf['used_memory_human']}")
                    print(f"Ops/sec: {perf['instantaneous_ops_per_sec']}")
                    print(f"Hit Rate: {perf['hit_rate']:.1f}%")
                
                # Latency
                latency = report['serving_latency']
                if latency:
                    print(f"Serving Latency: {latency['online_serving_latency_ms']:.2f}ms")
                
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")
                break
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(interval_seconds)

if __name__ == "__main__":
    monitor = FeastMonitoring()
    monitor.continuous_monitoring(interval_seconds=30)
```

## Step 12: Feature Store Operations

### Create operational scripts:
```bash
# Create scripts/feast_operations.sh
nano scripts/feast_operations.sh
```

```bash
#!/bin/bash

FEAST_REPO_PATH="/home/sanzad/feast-store/feast_repo"
cd $FEAST_REPO_PATH

# Activate Feast environment
source /home/sanzad/feast-env/bin/activate

case "$1" in
    "deploy")
        echo "Deploying Feast feature store..."
        feast apply
        ;;
    "materialize")
        echo "Materializing features..."
        START_DATE=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S)
        END_DATE=$(date -u +%Y-%m-%dT%H:%M:%S)
        feast materialize $START_DATE $END_DATE
        ;;
    "serve")
        echo "Starting Feast feature server..."
        feast serve --host 0.0.0.0 --port 6566
        ;;
    "status")
        echo "Feature Store Status:"
        feast feature-views list
        echo ""
        feast entities list
        echo ""
        feast feature-services list
        ;;
    "validate")
        echo "Validating feature definitions..."
        feast validate
        ;;
    "teardown")
        echo "Tearing down feature store..."
        feast teardown
        ;;
    "backup")
        echo "Creating feature store backup..."
        DATE=$(date +%Y%m%d_%H%M%S)
        BACKUP_DIR="/opt/feast-backups"
        mkdir -p $BACKUP_DIR
        
        # Backup registry
        pg_dump -h 192.168.1.184 -U dataeng -d feast_registry > $BACKUP_DIR/feast_registry_$DATE.sql
        
        # Backup feature definitions
        tar -czf $BACKUP_DIR/feast_definitions_$DATE.tar.gz $FEAST_REPO_PATH
        
        echo "Backup completed: $BACKUP_DIR/"
        ;;
    *)
        echo "Usage: $0 {deploy|materialize|serve|status|validate|teardown|backup}"
        exit 1
        ;;
esac
```

Make it executable:
```bash
chmod +x /home/sanzad/feast-store/feast_repo/scripts/feast_operations.sh
```

## Step 13: Web UI and REST API Setup

### Start Feast UI (optional):
```bash
# Install Feast UI
pip install feast[ui]

# Start UI
cd /home/sanzad/feast-store/feast_repo
feast ui
```

### Start Feature Server for REST API:
```bash
# Start feature server
feast serve --host 0.0.0.0 --port 6566
```

Test the API:
```bash
# Test feature serving via REST API
curl -X POST \
  http://192.168.1.184:6566/get-online-features \
  -H 'Content-Type: application/json' \
  -d '{
    "feature_service": "recommendation_v1",
    "entities": {
      "user": [1, 2, 3]
    }
  }'
```

## Step 14: Integration Testing

### Create integration test suite:
```python
# Create tests/test_feast_integration.py
nano tests/test_feast_integration.py
```

```python
import unittest
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Add feast repo to path
sys.path.append('/home/sanzad/feast-store/feast_repo')

from feast import FeatureStore

class TestFeastIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        cls.fs = FeatureStore(repo_path="/home/sanzad/feast-store/feast_repo")
    
    def test_feature_store_connectivity(self):
        """Test basic feature store connectivity"""
        feature_views = self.fs.list_feature_views()
        self.assertGreater(len(feature_views), 0, "No feature views found")
        
        entities = self.fs.list_entities()
        self.assertGreater(len(entities), 0, "No entities found")
    
    def test_online_feature_serving(self):
        """Test online feature serving"""
        entity_rows = [{"user": 1}, {"user": 2}]
        
        features = self.fs.get_online_features(
            features=[
                "user_profile_features:age",
                "user_activity_features:total_sessions_7d",
            ],
            entity_rows=entity_rows,
        )
        
        features_df = features.to_df()
        self.assertEqual(len(features_df), 2, "Wrong number of feature rows returned")
        self.assertIn('age', features_df.columns, "Age feature missing")
        self.assertIn('total_sessions_7d', features_df.columns, "Sessions feature missing")
    
    def test_historical_features(self):
        """Test historical feature serving"""
        entity_df = pd.DataFrame({
            "user": [1, 2, 3],
            "event_timestamp": [datetime.now() - timedelta(days=i) for i in range(3)]
        })
        
        training_df = self.fs.get_historical_features(
            entity_df=entity_df,
            features=[
                "user_profile_features:age",
                "user_activity_features:total_sessions_7d",
            ],
        ).to_df()
        
        self.assertEqual(len(training_df), 3, "Wrong number of training rows")
    
    def test_feature_service(self):
        """Test feature service functionality"""
        entity_rows = [{"user": 1}]
        
        features = self.fs.get_online_features(
            feature_service="recommendation_v1",
            entity_rows=entity_rows,
        )
        
        features_df = features.to_df()
        self.assertEqual(len(features_df), 1, "Feature service returned wrong number of rows")
    
    def test_data_quality(self):
        """Test data quality and completeness"""
        entity_rows = [{"user": i} for i in range(1, 11)]
        
        features = self.fs.get_online_features(
            features=[
                "user_profile_features:age",
                "user_profile_features:income",
            ],
            entity_rows=entity_rows,
        ).to_df()
        
        # Check for reasonable data ranges
        ages = features['age'].dropna()
        if len(ages) > 0:
            self.assertTrue(ages.min() >= 18, "Age values too low")
            self.assertTrue(ages.max() <= 100, "Age values too high")
        
        incomes = features['income'].dropna()
        if len(incomes) > 0:
            self.assertTrue(incomes.min() > 0, "Income values should be positive")

if __name__ == '__main__':
    unittest.main()
```

Run the tests:
```bash
cd /home/sanzad/feast-store/feast_repo
python -m pytest tests/test_feast_integration.py -v
```

## Step 15: Production Deployment Considerations

### Create systemd services:
```bash
# Create Feast feature server service
sudo nano /etc/systemd/system/feast-server.service
```

```ini
[Unit]
Description=Feast Feature Server
After=network.target redis.service postgresql.service
Wants=network.target

[Service]
Type=simple
User=sanzad
Group=sanzad
WorkingDirectory=/home/sanzad/feast-store/feast_repo
Environment=PATH=/home/sanzad/feast-env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/sanzad/feast-env/bin/feast serve --host 0.0.0.0 --port 6566
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable feast-server
sudo systemctl start feast-server
sudo systemctl status feast-server
```

This comprehensive Feast Feature Store setup provides:

1. **Centralized Feature Management**: Single source of truth for ML features
2. **Online/Offline Serving**: Support for both real-time and batch ML workflows
3. **Integration**: Works with your existing PostgreSQL, Redis, and Spark infrastructure
4. **Scalability**: Can handle high-throughput feature serving
5. **Monitoring**: Built-in observability and health checks
6. **Data Quality**: Feature validation and consistency checks
7. **Developer Experience**: Easy-to-use Python SDK and REST API

The feature store is now ready to support your ML applications running on the GPU node and integrates seamlessly with your data engineering ecosystem!
