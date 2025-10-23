# Database Performance Optimization Guide

## Overview

This guide covers SQL Server performance optimizations specifically for the XML Database Extraction system, focusing on bulk insert operations, connection management, and database configuration.

## 🚀 **Connection String Optimizations**

### Enhanced Connection Configuration

The system now includes optimized connection parameters:

```bash
# Environment variables for performance tuning
set XML_EXTRACTOR_DB_CONNECTION_POOLING=true    # Enable connection pooling (default: true)
set XML_EXTRACTOR_DB_PACKET_SIZE=8192          # Increase packet size for bulk operations (default: 4096)
set XML_EXTRACTOR_DB_MARS_CONNECTION=true      # Multiple Active Result Sets (default: true)
set XML_EXTRACTOR_DB_CONNECTION_TIMEOUT=60     # Connection timeout in seconds (default: 30)
set XML_EXTRACTOR_DB_COMMAND_TIMEOUT=600       # Command timeout in seconds (default: 300)
```

### Generated Connection String Example
```
DRIVER={ODBC Driver 17 for SQL Server};
SERVER=your-server;
DATABASE=YourDB;
Trusted_Connection=yes;
Connection Timeout=60;
TrustServerCertificate=yes;
Encrypt=no;
MultipleActiveResultSets=True;
Pooling=True;
Packet Size=8192;
```

## 📊 **SQL Server Database Optimizations**

### 1. Database Configuration Settings

```sql
-- Optimize for bulk operations
ALTER DATABASE [YourDB] SET AUTO_UPDATE_STATISTICS_ASYNC ON;
ALTER DATABASE [YourDB] SET AUTO_CREATE_STATISTICS ON;
ALTER DATABASE [YourDB] SET AUTO_UPDATE_STATISTICS ON;

-- Optimize transaction log for bulk inserts
ALTER DATABASE [YourDB] SET RECOVERY SIMPLE;  -- During bulk processing only
-- Switch back to FULL after processing: ALTER DATABASE [YourDB] SET RECOVERY FULL;

-- Increase transaction log size to prevent auto-growth during processing
ALTER DATABASE [YourDB] MODIFY FILE (
    NAME = 'YourDB_Log',
    SIZE = 5GB,
    MAXSIZE = 20GB,
    FILEGROWTH = 1GB
);

-- Optimize tempdb for parallel operations
ALTER DATABASE [tempdb] MODIFY FILE (NAME = 'tempdev', SIZE = 2GB, FILEGROWTH = 512MB);
ALTER DATABASE [tempdb] MODIFY FILE (NAME = 'templog', SIZE = 1GB, FILEGROWTH = 256MB);
```

### 2. Index Optimization Strategy

#### Pre-Processing Index Maintenance
```sql
-- Rebuild indexes before large batch processing
ALTER INDEX ALL ON [app_base] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);
ALTER INDEX ALL ON [contact_base] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);
ALTER INDEX ALL ON [contact_address] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);
ALTER INDEX ALL ON [contact_employment] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);
ALTER INDEX ALL ON [app_operational_cc] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);
ALTER INDEX ALL ON [app_pricing_cc] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);
ALTER INDEX ALL ON [app_transactional_cc] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);
ALTER INDEX ALL ON [app_solicited_cc] REBUILD WITH (FILLFACTOR = 90, ONLINE = ON);

-- Update statistics for optimal query plans
UPDATE STATISTICS [app_base] WITH FULLSCAN;
UPDATE STATISTICS [contact_base] WITH FULLSCAN;
UPDATE STATISTICS [contact_address] WITH FULLSCAN;
UPDATE STATISTICS [contact_employment] WITH FULLSCAN;
```

#### Optimal Index Strategy for Bulk Inserts
```sql
-- Consider dropping non-clustered indexes during bulk processing
-- and recreating them afterward for maximum insert performance

-- Example: Drop indexes before processing
DROP INDEX IF EXISTS [IX_app_base_receive_date] ON [app_base];
DROP INDEX IF EXISTS [IX_contact_base_app_id] ON [contact_base];

-- Recreate indexes after processing
CREATE NONCLUSTERED INDEX [IX_app_base_receive_date] 
ON [app_base] ([receive_date]) 
WITH (FILLFACTOR = 90, ONLINE = ON);

CREATE NONCLUSTERED INDEX [IX_contact_base_app_id] 
ON [contact_base] ([app_id]) 
WITH (FILLFACTOR = 90, ONLINE = ON);
```

### 3. Memory and CPU Optimization

```sql
-- Configure SQL Server memory (adjust based on available RAM)
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;

-- Set max server memory (leave 2-4GB for OS)
-- Example: For 16GB server, set to 12GB (12288 MB)
EXEC sp_configure 'max server memory', 12288;
RECONFIGURE;

-- Configure max degree of parallelism (MAXDOP)
-- Recommended: Number of CPU cores / 2, max 8
EXEC sp_configure 'max degree of parallelism', 4;
RECONFIGURE;

-- Configure cost threshold for parallelism
EXEC sp_configure 'cost threshold for parallelism', 25;
RECONFIGURE;
```

### 4. TempDB Optimization

```sql
-- Add multiple tempdb data files (one per CPU core, up to 8)
-- This reduces contention for bulk operations

ALTER DATABASE [tempdb] ADD FILE (
    NAME = 'tempdev2',
    FILENAME = 'C:\Program Files\Microsoft SQL Server\MSSQL15.MSSQLSERVER\MSSQL\DATA\tempdb2.mdf',
    SIZE = 2GB,
    FILEGROWTH = 512MB
);

ALTER DATABASE [tempdb] ADD FILE (
    NAME = 'tempdev3',
    FILENAME = 'C:\Program Files\Microsoft SQL Server\MSSQL15.MSSQLSERVER\MSSQL\DATA\tempdb3.mdf',
    SIZE = 2GB,
    FILEGROWTH = 512MB
);

-- Continue for each CPU core...
```

## ⚡ **Application-Level Optimizations**

### 1. Batch Size Tuning

```bash
# Test different batch sizes for your environment
python production_processor.py --batch-size 50 --limit 1000   # Conservative
python production_processor.py --batch-size 100 --limit 1000  # Recommended
python production_processor.py --batch-size 200 --limit 1000  # Aggressive

# Monitor performance and memory usage
# Optimal batch size balances throughput vs memory usage
```

### 2. Worker Process Optimization

```bash
# Test parallel worker configurations
python production_processor.py --workers 2 --limit 1000   # Conservative
python production_processor.py --workers 4 --limit 1000   # Recommended
python production_processor.py --workers 6 --limit 1000   # High-end systems

# Monitor CPU and database connection usage
# More workers = more database connections
```

### 3. Connection Pool Configuration

```bash
# Fine-tune connection pooling
set XML_EXTRACTOR_DB_CONNECTION_POOLING=true
set XML_EXTRACTOR_DB_PACKET_SIZE=8192          # Larger packets for bulk data
set XML_EXTRACTOR_DB_CONNECTION_TIMEOUT=60     # Longer timeout for busy systems
set XML_EXTRACTOR_DB_COMMAND_TIMEOUT=900       # 15 minutes for large batches
```

## 📈 **Performance Monitoring**

### 1. SQL Server Performance Counters

Monitor these key metrics during processing:

```sql
-- Monitor batch requests per second
SELECT cntr_value 
FROM sys.dm_os_performance_counters 
WHERE counter_name = 'Batch Requests/sec';

-- Monitor page life expectancy (should be > 300 seconds)
SELECT cntr_value 
FROM sys.dm_os_performance_counters 
WHERE counter_name = 'Page life expectancy';

-- Monitor buffer cache hit ratio (should be > 95%)
SELECT cntr_value 
FROM sys.dm_os_performance_counters 
WHERE counter_name = 'Buffer cache hit ratio';

-- Monitor lock waits per second (should be low)
SELECT cntr_value 
FROM sys.dm_os_performance_counters 
WHERE counter_name = 'Lock Waits/sec';
```

### 2. Real-time Monitoring Queries

```sql
-- Monitor active sessions and blocking
SELECT 
    s.session_id,
    s.login_name,
    s.host_name,
    s.program_name,
    s.status,
    s.cpu_time,
    s.memory_usage,
    s.reads,
    s.writes,
    s.logical_reads,
    r.blocking_session_id,
    r.wait_type,
    r.wait_time,
    r.command,
    t.text AS current_sql
FROM sys.dm_exec_sessions s
LEFT JOIN sys.dm_exec_requests r ON s.session_id = r.session_id
OUTER APPLY sys.dm_exec_sql_text(r.sql_handle) t
WHERE s.is_user_process = 1
ORDER BY s.cpu_time DESC;

-- Monitor transaction log usage
SELECT 
    DB_NAME(database_id) AS database_name,
    log_reuse_wait_desc,
    (total_log_size_in_bytes / 1024.0 / 1024.0) AS log_size_mb,
    (used_log_space_in_bytes / 1024.0 / 1024.0) AS log_used_mb,
    (used_log_space_in_percent) AS log_used_percent
FROM sys.dm_db_log_space_usage;

-- Monitor wait statistics
SELECT TOP 10
    wait_type,
    waiting_tasks_count,
    wait_time_ms,
    max_wait_time_ms,
    signal_wait_time_ms,
    (wait_time_ms - signal_wait_time_ms) AS resource_wait_time_ms
FROM sys.dm_os_wait_stats
WHERE wait_type NOT IN (
    'CLR_SEMAPHORE', 'LAZYWRITER_SLEEP', 'RESOURCE_QUEUE', 'SLEEP_TASK',
    'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH', 'WAITFOR', 'LOGMGR_QUEUE',
    'CHECKPOINT_QUEUE', 'REQUEST_FOR_DEADLOCK_SEARCH', 'XE_TIMER_EVENT',
    'BROKER_TO_FLUSH', 'BROKER_TASK_STOP', 'CLR_MANUAL_EVENT', 'CLR_AUTO_EVENT',
    'DISPATCHER_QUEUE_SEMAPHORE', 'FT_IFTS_SCHEDULER_IDLE_WAIT',
    'XE_DISPATCHER_WAIT', 'XE_DISPATCHER_JOIN'
)
ORDER BY wait_time_ms DESC;
```

## 🎯 **Performance Benchmarking**

### Expected Performance Targets

| Configuration | Target Throughput | Use Case |
|---------------|------------------|----------|
| **2 workers, batch 50** | 150+ rec/min | Development |
| **4 workers, batch 100** | 200+ rec/min | Production |
| **6 workers, batch 200** | 250+ rec/min | High-end systems |

### Benchmark Testing Script

```bash
#!/bin/bash
# performance_test.sh - Test different configurations

echo "=== Database Performance Benchmark ==="

# Test configurations
CONFIGS=(
    "2 50"   # workers batch_size
    "4 100"
    "6 200"
)

for config in "${CONFIGS[@]}"; do
    read -r workers batch_size <<< "$config"
    
    echo "Testing: $workers workers, batch size $batch_size"
    
    python production_processor.py \
        --server "your-server" \
        --database "YourDB" \
        --workers $workers \
        --batch-size $batch_size \
        --limit 1000 \
        --log-level ERROR
    
    echo "Completed configuration: $workers workers, $batch_size batch size"
    echo "---"
    sleep 30  # Cool-down between tests
done
```

## 🔧 **Troubleshooting Performance Issues**

### Common Performance Problems

#### 1. Slow Insert Performance
**Symptoms**: < 100 records/minute
**Solutions**:
```sql
-- Check for blocking
SELECT * FROM sys.dm_exec_requests WHERE blocking_session_id > 0;

-- Check index fragmentation
SELECT 
    OBJECT_NAME(object_id) AS table_name,
    index_id,
    avg_fragmentation_in_percent
FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED')
WHERE avg_fragmentation_in_percent > 30;

-- Rebuild fragmented indexes
ALTER INDEX ALL ON [table_name] REBUILD;
```

#### 2. High Memory Usage
**Symptoms**: System slowdown, out of memory errors
**Solutions**:
```bash
# Reduce batch size
--batch-size 50

# Reduce worker count
--workers 2

# Monitor memory usage
SELECT 
    (physical_memory_kb / 1024) AS physical_memory_mb,
    (virtual_memory_kb / 1024) AS virtual_memory_mb,
    (committed_kb / 1024) AS committed_memory_mb
FROM sys.dm_os_process_memory;
```

#### 3. Connection Pool Exhaustion
**Symptoms**: Connection timeout errors
**Solutions**:
```bash
# Reduce worker count
--workers 2

# Increase connection timeout
set XML_EXTRACTOR_DB_CONNECTION_TIMEOUT=120

# Monitor connection count
SELECT 
    DB_NAME(database_id) AS database_name,
    COUNT(*) AS connection_count
FROM sys.dm_exec_sessions
WHERE is_user_process = 1
GROUP BY database_id;
```

## 📋 **Performance Optimization Checklist**

### Pre-Processing Setup
- [ ] Set database to SIMPLE recovery model
- [ ] Rebuild all indexes with 90% fill factor
- [ ] Update statistics with FULLSCAN
- [ ] Increase transaction log size
- [ ] Configure SQL Server memory settings
- [ ] Set optimal MAXDOP and cost threshold

### Application Configuration
- [ ] Enable connection pooling (`Pooling=True`)
- [ ] Set optimal packet size (8192 for bulk operations)
- [ ] Configure appropriate timeouts
- [ ] Set logging to ERROR level for production
- [ ] Choose optimal worker count (4 recommended)
- [ ] Set appropriate batch size (100 recommended)

### Post-Processing Cleanup
- [ ] Switch database back to FULL recovery model
- [ ] Rebuild indexes if dropped during processing
- [ ] Update statistics after large data loads
- [ ] Archive or compress transaction logs
- [ ] Monitor database file sizes

### Ongoing Monitoring
- [ ] Monitor CPU and memory usage
- [ ] Track processing throughput
- [ ] Watch for blocking sessions
- [ ] Monitor transaction log growth
- [ ] Check index fragmentation levels

## 🚀 **Advanced Optimizations**

### 1. Partitioned Tables (For Very Large Datasets)

```sql
-- Create partition function for date-based partitioning
CREATE PARTITION FUNCTION pf_app_base_date (datetime)
AS RANGE RIGHT FOR VALUES 
('2024-01-01', '2024-02-01', '2024-03-01', '2024-04-01');

-- Create partition scheme
CREATE PARTITION SCHEME ps_app_base_date
AS PARTITION pf_app_base_date
TO ([PRIMARY], [PRIMARY], [PRIMARY], [PRIMARY], [PRIMARY]);

-- Create partitioned table
CREATE TABLE [app_base_partitioned] (
    [app_id] int IDENTITY(1,1) NOT NULL,
    [receive_date] datetime NOT NULL,
    -- ... other columns
    CONSTRAINT [PK_app_base_partitioned] PRIMARY KEY CLUSTERED 
    ([app_id], [receive_date])
) ON ps_app_base_date([receive_date]);
```

### 2. Columnstore Indexes (For Analytics)

```sql
-- Create columnstore index for analytical queries
CREATE NONCLUSTERED COLUMNSTORE INDEX [NCCI_app_base_analytics]
ON [app_base] ([app_id], [receive_date], [decision_enum], [app_type_enum]);
```

### 3. In-Memory OLTP (For High-Throughput Scenarios)

```sql
-- Enable In-Memory OLTP
ALTER DATABASE [YourDB] ADD FILEGROUP [memory_optimized_data] 
CONTAINS MEMORY_OPTIMIZED_DATA;

ALTER DATABASE [YourDB] ADD FILE (
    NAME = 'memory_optimized_data',
    FILENAME = 'C:\Data\YourDB_memory_optimized_data'
) TO FILEGROUP [memory_optimized_data];

-- Create memory-optimized staging table
CREATE TABLE [app_base_staging] (
    [app_id] int NOT NULL,
    [receive_date] datetime NOT NULL,
    -- ... other columns
    CONSTRAINT [PK_app_base_staging] PRIMARY KEY NONCLUSTERED ([app_id])
) WITH (MEMORY_OPTIMIZED = ON, DURABILITY = SCHEMA_ONLY);
```

---

**Performance Target**: 200+ records/minute with 4 workers and optimized database configuration  
**Last Updated**: October 2024  
**Recommended Configuration**: Connection pooling enabled, 8KB packet size, 4 workers, 100 batch size