# Production Deployment Guide

## Overview

This guide covers deploying the XML Database Extraction system in a production environment with optimal performance, monitoring, and operational procedures.

## 🚀 **Quick Production Setup**

### Prerequisites
- **Python 3.8+** installed on production server
- **SQL Server** with ODBC Driver 17 for SQL Server
- **Database tables** already created (system assumes tables exist)
- **Network connectivity** between processing server and SQL Server
- **Sufficient disk space** for logs and metrics (recommend 10GB+)

### Installation Steps

#### 1. Environment Setup
```bash
# Create production directory
mkdir /opt/xml-processor  # Linux
# or
mkdir C:\xml-processor    # Windows

cd /opt/xml-processor

# Clone or copy application files
# (Copy entire project directory to production server)

# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configuration Validation
```bash
# Test database connectivity
python production_processor.py --server "your-sql-server" --database "YourDB" --limit 1 --log-level DEBUG

# Expected output: Successful connection and processing of 1 record
```

#### 3. Performance Baseline
```bash
# Run performance benchmark
python production_processor.py --server "your-sql-server" --database "YourDB" --workers 4 --batch-size 50 --limit 100 --log-level ERROR

# Target: >150 records/minute with >90% success rate
```

## 📊 **Production Configuration**

### Schema Configuration

The system supports configurable database schema prefixes for different environments (production, sandbox, development) without requiring code changes:

```bash
# Production (default schema)
python production_processor.py --server "prod-server" --database "ProductionDB"
# Tables accessed as: [app_base], [contact_base], etc.

# Sandbox environment
set XML_EXTRACTOR_DB_SCHEMA_PREFIX=sandbox
python production_processor.py --server "test-server" --database "TestDB"
# Tables accessed as: [sandbox].[app_base], [sandbox].[contact_base], etc.

# Development environment
set XML_EXTRACTOR_DB_SCHEMA_PREFIX=dev
python production_processor.py --server "dev-server" --database "DevDB"
# Tables accessed as: [dev].[app_base], [dev].[contact_base], etc.
```

**Key Benefits:**
- ✅ **Zero code changes** - existing scripts work unchanged
- ✅ **Environment flexibility** - easy switching between schemas
- ✅ **Centralized configuration** - one environment variable controls all operations
- ✅ **Automatic application** - all SQL operations (INSERT, DELETE, IDENTITY_INSERT) use schema prefix

See `docs/schema-configuration.md` for detailed configuration options.

### Recommended Settings

#### High-Performance Configuration
```bash
python production_processor.py \
  --server "prod-sql-server" \
  --database "ProductionDB" \
  --workers 4 \
  --batch-size 100 \
  --log-level ERROR
```

#### Memory-Constrained Environment
```bash
python production_processor.py \
  --server "prod-sql-server" \
  --database "ProductionDB" \
  --workers 2 \
  --batch-size 50 \
  --log-level ERROR
```

#### Development/Testing
```bash
python production_processor.py \
  --server "dev-sql-server" \
  --database "TestDB" \
  --workers 2 \
  --batch-size 25 \
  --limit 1000 \
  --log-level INFO
```

### Configuration Parameters

| Parameter | Production | Development | Description |
|-----------|------------|-------------|-------------|
| `--workers` | 4 | 2 | Parallel processes (match CPU cores) |
| `--batch-size` | 100 | 25 | Records per processing batch |
| `--log-level` | ERROR | INFO | Logging verbosity (ERROR = max performance) |
| `--limit` | (none) | 1000 | Total records to process (omit for all) |

## 🔧 **Database Configuration**

### SQL Server Optimization

#### Connection Settings
```sql
-- Increase connection timeout for bulk operations
ALTER DATABASE [YourDB] SET REMOTE_QUERY_TIMEOUT 600;

-- Optimize for bulk insert operations
ALTER DATABASE [YourDB] SET AUTO_UPDATE_STATISTICS_ASYNC ON;
ALTER DATABASE [YourDB] SET PAGE_VERIFY CHECKSUM;
```

#### Index Maintenance
```sql
-- Rebuild indexes before large batch processing
ALTER INDEX ALL ON [app_base] REBUILD;
ALTER INDEX ALL ON [contact_base] REBUILD;
ALTER INDEX ALL ON [contact_address] REBUILD;
ALTER INDEX ALL ON [contact_employment] REBUILD;

-- Update statistics for optimal query plans
UPDATE STATISTICS [app_base];
UPDATE STATISTICS [contact_base];
UPDATE STATISTICS [contact_address];
UPDATE STATISTICS [contact_employment];
```

#### Transaction Log Management
```sql
-- Ensure sufficient transaction log space
ALTER DATABASE [YourDB] MODIFY FILE (
    NAME = 'YourDB_Log',
    SIZE = 5GB,
    MAXSIZE = 20GB,
    FILEGROWTH = 1GB
);

-- Consider switching to SIMPLE recovery model during large batches
ALTER DATABASE [YourDB] SET RECOVERY SIMPLE;
-- (Switch back to FULL after processing)
ALTER DATABASE [YourDB] SET RECOVERY FULL;
```

### Database Monitoring Queries
```sql
-- Monitor active connections
SELECT 
    session_id,
    login_name,
    host_name,
    program_name,
    status,
    cpu_time,
    memory_usage,
    reads,
    writes
FROM sys.dm_exec_sessions 
WHERE is_user_process = 1;

-- Monitor transaction log usage
SELECT 
    name,
    log_reuse_wait_desc,
    log_reuse_wait,
    (size * 8.0 / 1024) AS log_size_mb,
    (FILEPROPERTY(name, 'SpaceUsed') * 8.0 / 1024) AS log_used_mb
FROM sys.database_files 
WHERE type = 1;

-- Monitor table sizes
SELECT 
    t.name AS table_name,
    p.rows AS row_count,
    (a.total_pages * 8) / 1024 AS total_space_mb,
    (a.used_pages * 8) / 1024 AS used_space_mb
FROM sys.tables t
INNER JOIN sys.indexes i ON t.object_id = i.object_id
INNER JOIN sys.partitions p ON i.object_id = p.object_id AND i.index_id = p.index_id
INNER JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE i.index_id <= 1
GROUP BY t.name, p.rows, a.total_pages, a.used_pages
ORDER BY row_count DESC;
```

## 📈 **Monitoring and Alerting**

### Real-time Monitoring

#### Progress Tracking
The system provides real-time progress updates:
```
2024-10-21 15:30:15 - Progress: 2,500/10,000 (25.0%) - Rate: 185.2 rec/min - ETA: 22.4 min - Success: 2,498, Failed: 2
2024-10-21 15:35:15 - Progress: 3,425/10,000 (34.3%) - Rate: 185.0 rec/min - ETA: 17.8 min - Success: 3,421, Failed: 4
```

#### Performance Metrics
Metrics are automatically saved to JSON files:
```json
{
  "session_id": "20241021_153000",
  "records_processed": 10000,
  "success_rate": 98.2,
  "records_per_minute": 185.2,
  "total_processing_time": 3240.5,
  "parallel_efficiency": 0.863,
  "worker_count": 4,
  "server": "prod-sql-server",
  "database": "ProductionDB"
}
```

### Log File Management

#### Log Directory Structure
```
logs/
├── production_20241021_153000.log    # Main processing log
├── production_20241021_160000.log    # Next batch log
└── archived/                         # Archived logs (optional)
    ├── production_20241020_*.log
    └── production_20241019_*.log

metrics/
├── metrics_20241021_153000.json      # Performance metrics
├── metrics_20241021_160000.json      # Next batch metrics
└── archived/                         # Archived metrics (optional)
    ├── metrics_20241020_*.json
    └── metrics_20241019_*.json
```

#### Log Rotation Script
```bash
#!/bin/bash
# log_rotation.sh - Archive old logs and metrics

LOG_DIR="logs"
METRICS_DIR="metrics"
ARCHIVE_DAYS=30

# Create archive directories
mkdir -p ${LOG_DIR}/archived
mkdir -p ${METRICS_DIR}/archived

# Archive logs older than 30 days
find ${LOG_DIR} -name "*.log" -mtime +${ARCHIVE_DAYS} -exec mv {} ${LOG_DIR}/archived/ \;
find ${METRICS_DIR} -name "*.json" -mtime +${ARCHIVE_DAYS} -exec mv {} ${METRICS_DIR}/archived/ \;

# Compress archived files
gzip ${LOG_DIR}/archived/*.log 2>/dev/null
gzip ${METRICS_DIR}/archived/*.json 2>/dev/null

echo "Log rotation completed: $(date)"
```

### Alerting Thresholds

#### Performance Alerts
```bash
# Monitor for performance degradation
CURRENT_RATE=$(grep "Rate:" logs/production_*.log | tail -1 | grep -o "[0-9.]\+ rec/min" | cut -d' ' -f1)
if (( $(echo "$CURRENT_RATE < 100" | bc -l) )); then
    echo "ALERT: Processing rate below threshold: $CURRENT_RATE rec/min"
fi

# Monitor for high error rates
ERROR_RATE=$(grep "Failed:" logs/production_*.log | tail -1 | grep -o "Failed: [0-9]\+" | cut -d' ' -f2)
SUCCESS_COUNT=$(grep "Success:" logs/production_*.log | tail -1 | grep -o "Success: [0-9]\+" | cut -d' ' -f2)
if (( ERROR_RATE > SUCCESS_COUNT / 10 )); then
    echo "ALERT: High error rate: $ERROR_RATE failures"
fi
```

#### System Resource Alerts
```bash
# Monitor disk space
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "ALERT: Disk usage high: ${DISK_USAGE}%"
fi

# Monitor memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEMORY_USAGE -gt 85 ]; then
    echo "ALERT: Memory usage high: ${MEMORY_USAGE}%"
fi
```

## 🔄 **Operational Procedures**

### Daily Operations

#### Pre-Processing Checklist
1. **Verify database connectivity**
   ```bash
   python production_processor.py --server "prod-server" --database "DB" --limit 1
   ```

2. **Check available disk space**
   ```bash
   df -h .  # Linux
   dir     # Windows
   ```

3. **Review previous processing logs**
   ```bash
   tail -50 logs/production_*.log | grep -E "(ERROR|ALERT|Failed)"
   ```

4. **Validate data source availability**
   ```sql
   SELECT COUNT(*) FROM app_xml WHERE xml IS NOT NULL;
   ```

#### Processing Execution
```bash
# Standard production batch
python production_processor.py \
  --server "prod-sql-server" \
  --database "ProductionDB" \
  --workers 4 \
  --batch-size 100 \
  --log-level ERROR \
  > processing_output.log 2>&1 &

# Monitor progress
tail -f processing_output.log
```

#### Post-Processing Validation
```sql
-- Verify record counts
SELECT 
    'app_base' as table_name, COUNT(*) as record_count 
FROM app_base 
WHERE created_date >= CAST(GETDATE() AS DATE)
UNION ALL
SELECT 
    'contact_base', COUNT(*) 
FROM contact_base 
WHERE created_date >= CAST(GETDATE() AS DATE);

-- Check for data quality issues
SELECT 
    COUNT(*) as records_with_nulls
FROM app_base 
WHERE app_id IS NULL OR receive_date IS NULL;
```

### Batch Processing Workflow

#### Large Dataset Processing
```bash
# Process in manageable chunks
TOTAL_RECORDS=$(python -c "
import sys
sys.path.append('.')
from xml_extractor.database.migration_engine import MigrationEngine
engine = MigrationEngine('$CONNECTION_STRING')
with engine.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM app_xml WHERE xml IS NOT NULL')
    print(cursor.fetchone()[0])
")

BATCH_SIZE=10000
OFFSET=0

while [ $OFFSET -lt $TOTAL_RECORDS ]; do
    echo "Processing batch: $OFFSET to $((OFFSET + BATCH_SIZE))"
    
    python production_processor.py \
      --server "prod-sql-server" \
      --database "ProductionDB" \
      --workers 4 \
      --batch-size 100 \
      --limit $BATCH_SIZE \
      --log-level ERROR
    
    OFFSET=$((OFFSET + BATCH_SIZE))
    
    # Brief pause between batches
    sleep 30
done
```

### Error Recovery Procedures

#### Common Error Scenarios

##### 1. Database Connection Failures
```bash
# Symptoms: Connection timeout or authentication errors
# Resolution:
1. Verify SQL Server is running
2. Check network connectivity: ping sql-server
3. Validate credentials and permissions
4. Test with minimal connection:
   python production_processor.py --server "server" --database "db" --limit 1 --log-level DEBUG
```

##### 2. High Memory Usage
```bash
# Symptoms: System slowdown, out of memory errors
# Resolution:
1. Reduce worker count: --workers 2
2. Reduce batch size: --batch-size 50
3. Monitor with: top (Linux) or Task Manager (Windows)
4. Restart processing with lower resource usage
```

##### 3. Data Quality Issues
```bash
# Symptoms: High failure rates, validation errors
# Resolution:
1. Review error logs: grep "ERROR" logs/production_*.log
2. Identify problematic records
3. Check mapping contract configuration
4. Run with smaller batch for detailed debugging: --batch-size 10 --log-level INFO
```

##### 4. Performance Degradation
```bash
# Symptoms: Processing rate below 100 rec/min
# Resolution:
1. Check database performance: run index maintenance
2. Verify log level: should be ERROR for production
3. Monitor system resources: CPU, memory, disk I/O
4. Consider reducing worker count if database is bottleneck
```

## 🔒 **Security Considerations**

### Database Security
- **Use dedicated service account** for database connections
- **Limit database permissions** to required tables only
- **Enable connection encryption** with TrustServerCertificate=yes
- **Regular password rotation** for SQL Server authentication

### Application Security
- **Store credentials securely** (environment variables, not code)
- **Limit file system permissions** on log and metrics directories
- **Regular security updates** for Python and dependencies
- **Network security** - restrict access to processing servers

### Data Protection
- **Encrypt sensitive data** in transit and at rest
- **Audit logging** for compliance requirements
- **Data retention policies** for logs and metrics
- **Backup and recovery** procedures for processed data

## 📋 **Maintenance Schedule**

### Daily Tasks
- [ ] Monitor processing logs for errors
- [ ] Check system resource usage
- [ ] Verify database connectivity
- [ ] Review performance metrics

### Weekly Tasks
- [ ] Archive old log files
- [ ] Database index maintenance
- [ ] Performance trend analysis
- [ ] Backup validation

### Monthly Tasks
- [ ] Security patch updates
- [ ] Capacity planning review
- [ ] Performance optimization review
- [ ] Documentation updates

## 🚨 **Troubleshooting Quick Reference**

| Issue | Symptoms | Quick Fix |
|-------|----------|-----------|
| **Slow Performance** | <100 rec/min | Set `--log-level ERROR`, reduce workers |
| **High Memory** | System slowdown | Reduce `--batch-size` and `--workers` |
| **Connection Errors** | Database timeouts | Check SQL Server status, test connectivity |
| **High Error Rate** | >10% failures | Review logs, check data quality |
| **Disk Space** | Processing stops | Clean old logs, increase disk space |

### Emergency Contacts
- **Database Administrator**: [Contact Info]
- **System Administrator**: [Contact Info]
- **Application Support**: [Contact Info]

## 📞 **Support Information**

### Log Analysis Commands
```bash
# Find recent errors
grep -i error logs/production_*.log | tail -20

# Check processing rates
grep "Rate:" logs/production_*.log | tail -10

# Monitor current processing
tail -f logs/production_$(date +%Y%m%d)_*.log
```

### Performance Analysis
```bash
# Analyze metrics files
python -c "
import json, glob
files = glob.glob('metrics/metrics_*.json')
for f in sorted(files)[-5:]:  # Last 5 runs
    with open(f) as file:
        data = json.load(file)
        print(f'{f}: {data[\"records_per_minute\"]:.1f} rec/min, {data[\"success_rate\"]:.1f}% success')
"
```

---

**Last Updated**: October 2024  
**Deployment Version**: 1.0  
**Recommended Configuration**: 4 workers, 100 batch size, ERROR logging