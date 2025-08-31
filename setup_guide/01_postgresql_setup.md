# PostgreSQL Setup Guide

## Overview
PostgreSQL will be set up on **cpu-node1** as the primary database server for the Data Engineering HomeLab.

## Machine Configuration
- **Primary Node**: cpu-node1 (192.168.1.184)
- **Backup Node**: cpu-node2 (192.168.1.187) - optional streaming replica

## Prerequisites
- Ubuntu/Debian-based Linux distribution
- At least 4GB RAM recommended
- At least 20GB free disk space

## Installation Steps

### 1. Install PostgreSQL on cpu-node1

```bash
# Update package repository
sudo apt update

# Install PostgreSQL and additional contrib packages
sudo apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Check service status
sudo systemctl status postgresql
```

### 2. Initial Configuration

```bash
# Switch to postgres user
sudo -i -u postgres

# Create a database user for your data engineering work
createuser --interactive --pwprompt dataeng

# Create databases for different projects
createdb -O dataeng analytics_db
createdb -O dataeng lakehouse_db
createdb -O dataeng streaming_db

# Exit postgres user
exit
```

### 3. Network Configuration

Edit PostgreSQL configuration files:

```bash
# Edit postgresql.conf
sudo nano /etc/postgresql/*/main/postgresql.conf
```

Update these settings:
```conf
# Connection settings
listen_addresses = '*'
port = 5432
max_connections = 200

# Memory settings (adjust based on available RAM)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# WAL settings for replication
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB
```

Edit pg_hba.conf for network access:
```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Add these lines:
```conf
# Allow connections from HomeLab network
host    all             all             192.168.1.0/24          md5
host    replication     all             192.168.1.0/24          md5
```

### 4. Restart PostgreSQL
```bash
sudo systemctl restart postgresql
```

### 5. Firewall Configuration
```bash
sudo ufw allow 5432/tcp
sudo ufw reload
```

## Optional: Set up Streaming Replication on cpu-node2

---

### 🔴 STEP 1: Run on PRIMARY SERVER (cpu-node1 / 192.168.1.184)
```bash
# SSH into cpu-node1 or run locally if you're already on cpu-node1
# Create replication user
sudo -u postgres createuser --replication --pwprompt replica_user
# When prompted for password, use: HomeLab_Replica_2024!
```

---

### 🔵 STEP 2: Run on STANDBY SERVER (cpu-node2 / 192.168.1.187)
```bash
# SSH into cpu-node2: ssh sanzad@192.168.1.187
# Or run these commands if you're directly on cpu-node2

# Install PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Stop PostgreSQL service
sudo systemctl stop postgresql

# Remove default data directory (IMPORTANT: Use correct path for PostgreSQL 16)
sudo rm -rf /var/lib/postgresql/16/main/*

# Verify directory is empty
sudo ls -la /var/lib/postgresql/16/main/

# Ensure proper directory structure and permissions
sudo mkdir -p /var/lib/postgresql/16/main
sudo chown postgres:postgres /var/lib/postgresql/16/main
sudo chmod 700 /var/lib/postgresql/16/main
```

---

### 🔵 STEP 3: Run on STANDBY SERVER (cpu-node2 / 192.168.1.187)
```bash
# Still on cpu-node2 - Create base backup from primary server
sudo -u postgres pg_basebackup \
    -h 192.168.1.184 \
    -D /var/lib/postgresql/16/main \
    -U replica_user \
    -P -v -R -W
# When prompted for password, enter: HomeLab_Replica_2024!

# Set proper permissions after backup
sudo chown -R postgres:postgres /var/lib/postgresql/16/main
sudo chmod 700 /var/lib/postgresql/16/main
```

### 🔵 STEP 3b: Configure STANDBY SERVER (cpu-node2 / 192.168.1.187)
```bash
# IMPORTANT: Configure replica to match or exceed primary settings
sudo nano /etc/postgresql/16/main/postgresql.conf
```

**Update these settings to match the primary server:**
```conf
# Connection settings (MUST match or exceed primary)
listen_addresses = '*'
port = 5432
max_connections = 200                # Primary has 200, replica must be >= 200

# Memory settings (adjust based on available RAM)
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# WAL settings for replication
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB
```

**Configure replica network access:**
```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Add these lines:
```conf
# Allow connections from HomeLab network
host    all             all             192.168.1.0/24          md5
host    replication     all             192.168.1.0/24          md5
```

**Configure firewall and start PostgreSQL:**
```bash
# Open PostgreSQL port on replica
sudo ufw allow 5432/tcp
sudo ufw reload

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify PostgreSQL is actually running (not just "active (exited)")
sudo systemctl status postgresql
ps aux | grep postgres  # Should show postgres processes running
```

---

### 🟢 STEP 4: Verify Replication is Working

**🔴 On PRIMARY (cpu-node1 / 192.168.1.184):**
```bash
# Check replication connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_replication;"
# You should see a row showing connection from cpu-node2
```

**🔵 On STANDBY (cpu-node2 / 192.168.1.187):**
```bash
# Verify it's in recovery mode (replica)
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
# Should return: t (true)

# Check replication receiver status
sudo -u postgres psql -c "SELECT * FROM pg_stat_wal_receiver;"
# Should show active connection to primary
```

---

## Troubleshooting Replication Issues

### Issue: PostgreSQL shows "active (exited)" on Replica

**Symptoms:**
```bash
sudo systemctl status postgresql
# Shows: Active: active (exited)
ps aux | grep postgres
# Shows: No PostgreSQL processes running
```

**🔧 Solution:**
```bash
# Check PostgreSQL logs for errors
sudo journalctl -u postgresql@16-main -n 30

# Common error: "max_connections = 100 is lower than on primary server"
# Fix: Edit replica configuration
sudo nano /etc/postgresql/16/main/postgresql.conf

# Ensure these match or exceed primary settings:
max_connections = 200
shared_buffers = 256MB
wal_level = replica

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Issue: pg_basebackup fails with "directory not empty"

**🔧 Solution:**
```bash
# On replica server (cpu-node2):
sudo systemctl stop postgresql
sudo rm -rf /var/lib/postgresql/16/main/*
sudo chown postgres:postgres /var/lib/postgresql/16/main
sudo chmod 700 /var/lib/postgresql/16/main

# Then retry pg_basebackup
```

### Issue: Authentication failed during pg_basebackup

**🔧 Solution:**
```bash
# On primary server (cpu-node1), verify replication user:
sudo -u postgres psql -c "\du replica_user"

# If user doesn't exist, create it:
sudo -u postgres psql -c "CREATE USER replica_user WITH REPLICATION PASSWORD 'HomeLab_Replica_2024!';"

# Verify pg_hba.conf allows replication from replica IP:
sudo grep replica /etc/postgresql/16/main/pg_hba.conf
# Should show: host replication all 192.168.1.0/24 md5
```

## Useful Extensions for Data Engineering

### 🔴 Run on PRIMARY SERVER (cpu-node1 / 192.168.1.184)

**Step 1: Connect to PostgreSQL as superuser:**
```bash
# Connect to PostgreSQL as postgres user
sudo -u postgres psql
```

**Step 2: Inside PostgreSQL prompt, connect to analytics_db and install extensions:**
```sql
-- Connect to the analytics database (\c means "connect to database")
\c analytics_db

-- Install useful extensions for data engineering
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "hstore";         -- Key-value pairs
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements"; -- Query performance tracking
CREATE EXTENSION IF NOT EXISTS "btree_gin";      -- Advanced indexing
CREATE EXTENSION IF NOT EXISTS "btree_gist";     -- Geometric and text indexing
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Text similarity search

-- For time-series data (install TimescaleDB if needed)
-- CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Exit PostgreSQL
\q
```

**Note:** Extensions are automatically replicated to the standby server (cpu-node2), so you only need to install them on the primary.

## Optional: TimescaleDB Installation for Time-Series Data

### 🔴 Install TimescaleDB on PRIMARY SERVER (cpu-node1 / 192.168.1.184)

**Step 1: Exit PostgreSQL if still connected:**
```sql
\q
```

**Step 2: Install TimescaleDB repository and package:**
```bash
# Add TimescaleDB repository
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list

# Add GPG key
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# Update package list
sudo apt update

# Install TimescaleDB for PostgreSQL 16
sudo apt install timescaledb-2-postgresql-16
```

**Step 3: Configure PostgreSQL for TimescaleDB:**
```bash
# Run TimescaleDB configuration tool
sudo timescaledb-tune --quiet --yes

# Restart PostgreSQL to apply changes
sudo systemctl restart postgresql
```

**Step 4: Create TimescaleDB extension:**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Connect to analytics database
\c analytics_db

# Create TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

# Exit PostgreSQL
\q
```

### 🔵 Install TimescaleDB on REPLICA SERVER (cpu-node2 / 192.168.1.187)

**Important:** TimescaleDB must be installed on the replica as well for replication to work:

```bash
# SSH to replica server
ssh sanzad@192.168.1.187

# Install TimescaleDB (same steps as primary)
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" | sudo tee /etc/apt/sources.list.d/timescaledb.list
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt update
sudo apt install timescaledb-2-postgresql-16

# Configure TimescaleDB
sudo timescaledb-tune --quiet --yes

# Restart PostgreSQL
sudo systemctl restart postgresql

# Exit SSH session
exit
```

**Note:** The extension itself (CREATE EXTENSION) only needs to be run on the primary - it will automatically replicate to the standby.

### 📊 Using TimescaleDB

### 🔴 Create Time-Series Tables on PRIMARY SERVER (cpu-node1 / 192.168.1.184)

**Step 1: Connect to PostgreSQL:**
```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql
```

**Step 2: Create time-series tables:**
```sql
-- Connect to analytics database
\c analytics_db

-- Create a regular table
CREATE TABLE sensor_data (
    time TIMESTAMPTZ NOT NULL,
    sensor_id INT NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION
);

-- Convert to TimescaleDB hypertable (this enables time-series features)
SELECT create_hypertable('sensor_data', 'time');

-- Insert sample data
INSERT INTO sensor_data VALUES 
  (NOW(), 1, 23.5, 65.2),
  (NOW(), 2, 24.1, 68.7);

-- Query the data
SELECT * FROM sensor_data ORDER BY time DESC;

-- Exit PostgreSQL
\q
```

**Note:** TimescaleDB tables and data automatically replicate to the standby server (cpu-node2) for high availability.

### 🕒 Understanding Hypertables

A **hypertable** is TimescaleDB's core concept - it's essentially a "smart" PostgreSQL table optimized for time-series data.

#### 📊 Regular Table vs Hypertable:

**🔴 Regular PostgreSQL Table:**
```sql
CREATE TABLE sensor_data (
    time TIMESTAMPTZ,
    sensor_id INT,
    temperature DOUBLE PRECISION
);
-- All data goes into ONE big table
-- Gets slower as data grows
-- Hard to manage old data
```

**🚀 TimescaleDB Hypertable:**
```sql
CREATE TABLE sensor_data (
    time TIMESTAMPTZ,
    sensor_id INT, 
    temperature DOUBLE PRECISION
);

-- Convert to hypertable (the magic happens here!)
SELECT create_hypertable('sensor_data', 'time');
-- Data automatically splits into "chunks" by time
-- Each chunk = 1 week of data (configurable)
-- Queries only touch relevant chunks = FAST!
```

#### 🧩 How Hypertables Work (Chunking):

```
Regular Table:           Hypertable:
┌─────────────────┐     ┌───────┐ ┌───────┐ ┌───────┐
│   ALL DATA      │     │Week 1 │ │Week 2 │ │Week 3 │ 
│                 │ --> │ Chunk │ │ Chunk │ │ Chunk │
│  (gets slower)  │     └───────┘ └───────┘ └───────┘
└─────────────────┘      (fast queries + easy cleanup)
```

#### ⚡ Key Benefits:

1. **Automatic Partitioning** - Splits data by time automatically
2. **Fast Queries** - Only searches relevant time periods
3. **Easy Data Management** - Drop old chunks instead of deleting rows
4. **Parallel Processing** - Multiple chunks can be processed simultaneously
5. **Transparent** - Looks like a regular table to your applications

#### 🔍 Real-World Performance Example:

**Without Hypertable (slow):**
```sql
-- Query 1 day from 1 year of sensor data
SELECT * FROM sensor_data 
WHERE time >= '2024-01-15' AND time < '2024-01-16';
-- PostgreSQL scans ALL 365 days of data! 🐌
```

**With Hypertable (fast):**
```sql
-- Same query on hypertable
SELECT * FROM sensor_data 
WHERE time >= '2024-01-15' AND time < '2024-01-16';
-- TimescaleDB only scans the 1-day chunk! ⚡
```

#### 📈 When to Use Hypertables:

**✅ Perfect for:**
- Sensor data (IoT)
- Application logs
- Financial data (stock prices)
- Metrics and monitoring
- Any time-stamped data

**❌ Not needed for:**
- User profiles
- Product catalogs
- Small datasets
- Non time-series data

#### 🛠️ Advanced Hypertable Commands:

```sql
-- Create hypertable with custom chunk size (1 day chunks)
SELECT create_hypertable('table_name', 'time_column', 
                        chunk_time_interval => INTERVAL '1 day');

-- Create with space partitioning (by device_id)
SELECT create_hypertable('table_name', 'time_column', 
                        partitioning_column => 'device_id',
                        number_partitions => 4);

-- View hypertable information
SELECT * FROM timescaledb_information.hypertables;

-- View chunks
SELECT * FROM timescaledb_information.chunks 
WHERE hypertable_name = 'sensor_data';

-- Drop old data (older than 1 month)
SELECT drop_chunks('sensor_data', INTERVAL '1 month');
```

#### 🎯 The Magic:

When you run `SELECT create_hypertable('sensor_data', 'time')`:

1. TimescaleDB keeps your table looking normal
2. Behind the scenes, it splits data into time-based chunks
3. Your apps work exactly the same (SQL queries unchanged)
4. But performance becomes **dramatically faster**
5. Data management becomes **much easier**

**In summary:** A hypertable is like having a time-traveling filing cabinet that automatically organizes your data by date and only looks in the right drawer when you ask for something! 🗂️⚡

This is why TimescaleDB is so powerful for analytics and monitoring workloads - you get PostgreSQL's reliability with time-series superpowers! 🚀

## Change Data Capture (CDC) Setup

### 🔴 Configure CDC on PRIMARY SERVER (cpu-node1 / 192.168.1.184)

For real-time data streaming to Kafka (Debezium) and Flink CDC, enable logical replication:

**Step 1: Enable logical replication:**
```bash
# Edit PostgreSQL configuration
sudo nano /etc/postgresql/16/main/postgresql.conf

# Add/modify these settings:
wal_level = logical                    # Enable logical replication
max_replication_slots = 4              # Allow CDC connections
max_wal_senders = 4                    # Increased for CDC
```

**Step 2: Configure client authentication for CDC:**
```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/16/main/pg_hba.conf

# Add CDC user access (add after existing replication line):
host    replication     cdc_user        192.168.1.0/24          md5
host    all             cdc_user        192.168.1.0/24          md5
```

**Step 3: Create CDC user and configure database:**
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create CDC user
CREATE USER cdc_user WITH REPLICATION LOGIN PASSWORD 'cdc_password123';

# Connect to analytics_db
\c analytics_db

# Grant necessary permissions for CDC
GRANT SELECT ON ALL TABLES IN SCHEMA public TO cdc_user;
GRANT USAGE ON SCHEMA public TO cdc_user;

-- Create publication for all tables (for Debezium)
CREATE PUBLICATION debezium_publication FOR ALL TABLES;

-- Enable row-level security bypass for CDC user (if needed)
ALTER USER cdc_user WITH BYPASSRLS;

-- Exit PostgreSQL
\q
```

**Step 4: Restart PostgreSQL to apply changes:**
```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Verify logical replication is enabled
sudo -u postgres psql -c "SHOW wal_level;"
# Should show: logical
```

**Step 5: Test CDC connectivity:**
```bash
# Test CDC user connection
psql -h 192.168.1.184 -U cdc_user -d analytics_db -c "SELECT version();"

# Test replication slot creation (for verification)
sudo -u postgres psql -d analytics_db -c "SELECT * FROM pg_create_logical_replication_slot('test_slot', 'pgoutput');"

# Clean up test slot
sudo -u postgres psql -d analytics_db -c "SELECT pg_drop_replication_slot('test_slot');"
```

### 🔵 CDC Configuration on REPLICA SERVER (cpu-node2 / 192.168.1.187)

**Important:** Update replica configuration to match primary:

```bash
# SSH to replica server
ssh sanzad@192.168.1.187

# Edit PostgreSQL configuration to match primary
sudo nano /etc/postgresql/16/main/postgresql.conf

# Update these settings to match primary:
wal_level = logical                    # Must match primary
max_replication_slots = 4              # Must match primary
max_wal_senders = 4                    # Must match primary

# Restart PostgreSQL
sudo systemctl restart postgresql

# Exit SSH
exit
```

### 📊 CDC Monitoring Queries:

**Monitor replication slots (run on PRIMARY):**
```sql
-- View active replication slots
SELECT slot_name, plugin, slot_type, database, active 
FROM pg_replication_slots;

-- Monitor CDC lag
SELECT slot_name, 
       pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn) as lag_bytes
FROM pg_replication_slots 
WHERE slot_type = 'logical';
```

## Testing the Setup

### 🔴 On PRIMARY SERVER (cpu-node1 / 192.168.1.184):
```bash
# Test local connection on primary
psql -U dataeng -d analytics_db -h localhost

# Check replication status (should show replica connected)
sudo -u postgres psql -c "SELECT * FROM pg_stat_replication;"
```

### 🔵 On REPLICA SERVER (cpu-node2 / 192.168.1.187):
```bash
# Test local connection on replica (read-only)
psql -U dataeng -d analytics_db -h localhost

# Verify replica status
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
```

### 🌐 From ANY OTHER MACHINE (test remote connections):
```bash
# Test connection to primary (read/write)
psql -U dataeng -d analytics_db -h 192.168.1.184

# Test connection to replica (read-only)  
psql -U dataeng -d analytics_db -h 192.168.1.187
```

## Monitoring and Maintenance

### 🔴 Basic Monitoring Queries (PRIMARY - cpu-node1):
```bash
# Connect to PostgreSQL on primary server
sudo -u postgres psql
```

Then run these SQL queries:
```sql
-- Check database sizes
SELECT datname, pg_size_pretty(pg_database_size(datname)) as size 
FROM pg_database;

-- Check active connections
SELECT count(*) as active_connections FROM pg_stat_activity;

-- Check replication lag (only works on primary)
SELECT client_addr, state, sync_state, 
       pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn) as lag_bytes
FROM pg_stat_replication;

-- Exit PostgreSQL
\q
```

### 🔵 Replica Monitoring (REPLICA - cpu-node2):
```bash
# Connect to PostgreSQL on replica server
sudo -u postgres psql
```

```sql
-- Check if still in recovery mode
SELECT pg_is_in_recovery();

-- Check replica lag
SELECT now() - pg_last_xact_replay_timestamp() AS replica_lag;

-- Check replication receiver status
SELECT * FROM pg_stat_wal_receiver;

-- Exit PostgreSQL
\q
```

### 🔴 Backup Strategy (PRIMARY - cpu-node1):
```bash
# Create daily backup script on PRIMARY server
sudo nano /opt/postgres_backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/postgresql_backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create full database backup
sudo -u postgres pg_dumpall > $BACKUP_DIR/full_backup_$DATE.sql

# Remove backups older than 7 days
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/full_backup_$DATE.sql"
```

```bash
# Make executable and add to cron
sudo chmod +x /opt/postgres_backup.sh

# Add to crontab for daily backups at 2 AM
sudo crontab -e
# Add this line: 0 2 * * * /opt/postgres_backup.sh
```

## Performance Tuning

For data engineering workloads, consider these additional settings:

```conf
# For analytical workloads
random_page_cost = 1.1
effective_io_concurrency = 200
min_wal_size = 1GB
max_wal_size = 4GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

## Integration Notes

- **Spark Integration**: Use JDBC driver `org.postgresql:postgresql:42.7.2`
- **Flink Integration**: Use PostgreSQL CDC connector for change data capture
- **Kafka Integration**: Use Debezium PostgreSQL connector for CDC to Kafka

## Troubleshooting

### Common issues:
1. **Connection refused**: Check firewall and pg_hba.conf
2. **Authentication failed**: Verify user credentials and pg_hba.conf method
3. **High memory usage**: Tune shared_buffers and work_mem
4. **Slow queries**: Enable pg_stat_statements and analyze query performance

### Log locations:
- Main log: `/var/log/postgresql/postgresql-*-main.log`
- Configuration: `/etc/postgresql/*/main/`
- Data directory: `/var/lib/postgresql/*/main/`
