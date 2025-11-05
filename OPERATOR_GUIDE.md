# XML Processing System - Operator Guide

**Quick Reference for Production Operations**

---

## 🚀 Quick Start (Most Common Scenarios)

### Test Run (10k records)
```powershell
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB"
```
- Uses sensible defaults: 4 workers, 500 records/batch, 10k safety limit
- Perfect for testing before larger runs

### Production Run (Single Range)
```powershell
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
    --app-id-start 1 --app-id-end 180000 --log-level INFO
```
- Processes specific app_id range
- Shows progress with INFO logging

### Chunked Processing (Recommended for >100k records)
```powershell
python run_production_processor.py --app-id-start 1 --app-id-end 180000
```
- Automatically breaks into 10k chunks
- Fresh Python process per chunk (prevents memory degradation)
- Sequential execution with automatic progress tracking

---

## 📋 Tool Selection Guide

| Scenario | Use This Tool | Why |
|----------|--------------|-----|
| Quick test (<10k records) | `production_processor.py` | Simple, fast, one command |
| Single production run | `production_processor.py` with ranges | Direct control, good for moderate datasets |
| Very large dataset (>100k) | `run_production_processor.py` | Process lifecycle management prevents memory issues |
| Concurrent processing | Multiple `production_processor.py` instances | Maximum throughput with non-overlapping ranges |

---

## 🎯 Core Concepts

### 1. Processing Modes (Mutually Exclusive)

**Limit Mode** (Testing/Safety Cap)
```powershell
--limit 10000
```
- Processes up to N records total
- Good for: development, testing, safety-limited runs
- Starts from beginning or resumes where left off
- **Default: 10,000 records**

**Range Mode** (Production/Concurrent-Safe)
```powershell
--app-id-start 1 --app-id-end 50000
```
- Processes specific app_id boundaries
- Good for: production, large datasets, concurrent processing
- Required for running multiple instances simultaneously
- No default (must specify both start and end)

### 2. Batch Size vs Limit

**--batch-size** (Memory Management)
- How many records to fetch and process at once
- Default: 500 records/batch
- Larger = better throughput but more memory
- Sweet spot: 500-1000

**--limit** (Safety Cap)
- Total records to process before stopping
- Default: 10,000 records
- Example: `--batch-size 500 --limit 10000` = 20 batches of 500 each

### 3. Schema Isolation (Contract-Driven)

Target schema is defined in `config/mapping_contract.json`:
```json
{
  "target_schema": "sandbox",  // or "dbo" for production
  ...
}
```

- `target_schema: "sandbox"` → All outputs go to `[sandbox].[table_name]`
- `target_schema: "dbo"` → All outputs go to `[dbo].[table_name]`
- Source XML always read from `[dbo].[app_xml]` (read-only)
- Enables safe dev/test/prod isolation in same database

### 4. Resume Capability

Processing automatically skips records already in `processing_log`:
```powershell
# Run 1: Processes app_id 1-5000, then crashes
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --limit 10000

# Run 2: Automatically resumes from app_id 5001
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --limit 10000
```
- No need to track progress manually
- Safe to Ctrl+C and restart
- Works for both limit and range modes

---

## 🔧 Common Usage Patterns

### Pattern 1: Development Testing
```powershell
# Quick 10k test with defaults
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB"

# See detailed progress
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --log-level INFO
```

### Pattern 2: Production Single Run
```powershell
# Process specific range
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
    --app-id-start 1 --app-id-end 180000 --log-level INFO
```

### Pattern 3: Concurrent Processing (Maximum Speed)
```powershell
# Terminal 1 (app_id 1-60,000)
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
    --app-id-start 1 --app-id-end 60000 --log-level INFO

# Terminal 2 (app_id 60,001-120,000)
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
    --app-id-start 60001 --app-id-end 120000 --log-level INFO

# Terminal 3 (app_id 120,001-180,000)
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
    --app-id-start 120001 --app-id-end 180000 --log-level INFO
```
**Key**: Non-overlapping ranges eliminate lock contention

### Pattern 4: Chunked Processing (Large Datasets)
```powershell
# Sequential chunked processing (10k per chunk)
python run_production_processor.py --app-id-start 1 --app-id-end 180000

# Custom chunk size
python run_production_processor.py --app-id-start 1 --app-id-end 180000 --chunk-size 5000

# Limit mode (for testing orchestrator)
python run_production_processor.py --limit 50000
```

### Pattern 5: Concurrent Chunked Processing (Ultimate Speed)
```powershell
# Terminal 1: Process first third
python run_production_processor.py --app-id-start 1 --app-id-end 60000

# Terminal 2: Process second third
python run_production_processor.py --app-id-start 60001 --app-id-end 120000

# Terminal 3: Process third third
python run_production_processor.py --app-id-start 120001 --app-id-end 180000
```
**Combines**: Process lifecycle management + concurrent execution

---

## 📊 Performance Tuning

### Expected Throughput
- **Typical**: 1,500-1,600 applications/minute (4 workers, batch-size=500)
- **Peak**: Up to 1,800 applications/minute
- **Warmup**: First 1-2 batches may be slower (~1,400 apps/min)

### Tuning Parameters

| Parameter | Default | Tuning Guidance |
|-----------|---------|-----------------|
| `--workers` | 4 | More workers = more parallelism. Diminishing returns after 6. Try 6 or 8 for faster servers. |
| `--batch-size` | 500 | Larger = better throughput but more memory. Sweet spot: 500-1000. Max tested: 1000. |
| `--chunk-size` | 10000 | (orchestrator only) Larger chunks = fewer restarts but more memory over time. 5k-15k recommended. |
| `--log-level` | WARNING | INFO = progress updates, WARNING = errors only, DEBUG = verbose (slow) |

### Connection Options

**Local SQLExpress** (default settings are optimal)
```powershell
# Connection pooling disabled (adds overhead for local connections)
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB"
```

**Remote SQL Server / Production**
```powershell
# Enable connection pooling for network efficiency
python production_processor.py --server "prod-server" --database "XmlConversionDB" ^
    --username "sqluser" --password "password" --enable-pooling
```

---

## 📁 Output Files

### Logs
```
logs/production_YYYYMMDD_HHMMSS.log
logs/production_YYYYMMDD_HHMMSS_range_1_180000.log  (for range-based runs)
```
- Full processing details
- Error messages and stack traces
- Controlled by `--log-level` parameter

### Metrics
```
metrics/metrics_YYYYMMDD_HHMMSS.json
metrics/metrics_YYYYMMDD_HHMMSS_range_1_180000.json  (for range-based runs)
```
- Performance statistics
- Batch-level breakdown
- Failed application details
- JSON format for programmatic analysis

### Processing Log (Database)
```sql
SELECT * FROM [target_schema].[processing_log]
ORDER BY processed_at DESC
```
- Tracks every application processed
- Status: 'success' or 'failed'
- Includes session_id, app_id_start, app_id_end for tracking
- Enables resume capability

---

## 🔍 Monitoring & Troubleshooting

### Check Progress During Run
```powershell
# Console shows real-time batches (with --log-level INFO)
   - Batch 1 completed: 500/500 successful in 20.93s (1433.7 rec/min)
   - Batch 2 completed: 500/500 successful in 20.91s (1434.9 rec/min)
```

### Query Processing Status
```sql
-- Count processed applications
SELECT 
    status,
    COUNT(*) as count
FROM [sandbox].[processing_log]  -- or [dbo] depending on target_schema
GROUP BY status

-- Find failed applications
SELECT 
    app_id,
    failure_reason,
    processed_at
FROM [sandbox].[processing_log]
WHERE status = 'failed'
ORDER BY processed_at DESC

-- Check session progress
SELECT 
    session_id,
    app_id_start,
    app_id_end,
    COUNT(*) as apps_processed,
    SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
    MIN(processed_at) as started_at,
    MAX(processed_at) as last_processed
FROM [sandbox].[processing_log]
GROUP BY session_id, app_id_start, app_id_end
ORDER BY started_at DESC
```

### Common Issues

**"Processing interrupted by user"**
- You pressed Ctrl+C (normal, expected)
- Exit code 1 is correct behavior
- Just restart same command to resume

**Slow performance (<1000 apps/min)**
- Check `--workers` parameter (try 6 or 8)
- Check `--batch-size` (try 1000)
- Check database server load (CPU/memory)
- Enable `--log-level WARNING` to reduce console overhead

**"Database connection failed"**
- Verify server name (use `localhost\SQLEXPRESS` not `localhost\\SQLEXPRESS` in PowerShell)
- Check Windows authentication vs SQL authentication
- Test connection: `python production_processor.py --server "..." --database "..." --limit 1`

**Memory usage grows over time**
- Expected behavior for long runs (>100k records)
- Solution: Use `run_production_processor.py` for automatic process recycling
- Fresh Python process every 10k records prevents memory accumulation

**"No XML records to process"**
- All records already processed (check `processing_log`)
- Or app_id range has no data
- Query to check: `SELECT COUNT(*) FROM [dbo].[app_xml] WHERE app_id BETWEEN X AND Y`

---

## ⚡ Quick Decision Tree

```
Need to process XML records?
├─ Testing/Development (<10k records)?
│  └─ Use: production_processor.py (defaults)
│
├─ Production run (<100k records)?
│  ├─ Single machine, moderate speed?
│  │  └─ Use: production_processor.py with ranges
│  └─ Maximum speed needed?
│     └─ Use: Multiple production_processor.py instances (concurrent ranges)
│
└─ Large dataset (>100k records)?
   ├─ Single machine?
   │  └─ Use: run_production_processor.py (sequential)
   └─ Maximum speed needed?
      └─ Use: Multiple run_production_processor.py instances (concurrent chunked)
```

---

## 📞 Quick Reference Commands

```powershell
# Get help
python production_processor.py --help
python run_production_processor.py --help

# Test connection
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --limit 1

# Check configuration
python xml_extractor/cli.py show-status

# View logs in real-time
Get-Content logs\production_*.log -Tail 50 -Wait

# Cancel running process
Ctrl+C  (safe to interrupt, will resume on restart)
```

---

**System Version**: 1.0  
**Last Updated**: November 2025  
**Typical Throughput**: ~1,500-1,600 applications/minute  
**For detailed API documentation**: See docstrings in `production_processor.py` and `run_production_processor.py`
