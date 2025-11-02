# Quick Start: Run 3 Concurrent Processors

## One-Liner Setup

Open 3 PowerShell windows and run these commands:

### Terminal 1 (Instance 0)
```powershell
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --instance-id 0 --instance-count 3 --log-level INFO
```

### Terminal 2 (Instance 1)
```powershell
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --instance-id 1 --instance-count 3 --log-level INFO
```

### Terminal 3 (Instance 2)
```powershell
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --instance-id 2 --instance-count 3 --log-level INFO
```

## Watch Progress

Look for this in each terminal:

```
ProductionProcessor initialized:
  Server: localhost\SQLEXPRESS
  Database: XmlConversionDB
  Target Schema: sandbox
  Workers: 4
  Processing Batch Size: 1000
  Concurrent Instances: 1/3 (partition-based)     ← Shows it's partitioned
  Session ID: 20250101_143022

Extracting XML records (limit=None, last_app_id=0, exclude_failed=True)
  Partition: app_id % 3 == 0                       ← Shows this instance's partition
Extracted 485 XML records (excluding already processed and failed)
```

## Expected Performance

- Instance 0: ~85-117 apps/min
- Instance 1: ~85-117 apps/min  
- Instance 2: ~85-117 apps/min
- **Total: 250-350 apps/min** (2.3-2.5x faster than single instance)

## Resume if One Crashes

Simply restart that instance:

```powershell
# Instance 0 crashed - restart it with same command
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --instance-id 0 --instance-count 3 --log-level INFO
```

It automatically:
- Skips already-processed records
- Resumes from failure point
- No duplicates or data loss

## Monitor in SQL Server

```sql
-- See what each instance has processed
SELECT 
    instance_id,
    COUNT(*) as processed_count,
    MIN(start_time) as first_processed,
    MAX(start_time) as last_processed,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
FROM [sandbox].[processing_log]
GROUP BY instance_id
ORDER BY instance_id;
```

## Verify Partition Distribution

```sql
-- Check that records are distributed evenly by partition
SELECT 
    app_id,
    (app_id % 3) as partition_num,
    COUNT(*) as count
FROM [dbo].[app_xml]
GROUP BY app_id % 3
ORDER BY partition_num;
```

Example output (ideal case):
```
partition_num | count
0             | 334
1             | 333
2             | 333
```

## Troubleshooting

### "Invalid instance configuration"
```
ValueError: Invalid instance configuration: instance_id=3 must be < instance_count=3
```
**Fix**: Use 0, 1, 2 for 3 instances (instance_id must be < instance_count)

### Instance not processing many records
Check if:
1. Records are already processed (check processing_log)
2. Distribution is uneven (normal with odd-sized databases)
3. XML is too small (< 100 bytes is filtered out)

### One instance is much slower
This is expected - depends on XML complexity, not record count.

## Stopping

Just Ctrl+C in each terminal. Processing is atomic per app_id, so:
- No partial records
- No data loss
- Safe to restart anytime

## Next Level: Multiple Machines

Once this works, scale to multiple machines:

```powershell
# Machine 1
python production_processor.py --server "prod-server" --database "XmlConversionDB" --workers 8 --instance-id 0 --instance-count 3 --enable-pooling

# Machine 2
python production_processor.py --server "prod-server" --database "XmlConversionDB" --workers 8 --instance-id 1 --instance-count 3 --enable-pooling

# Machine 3
python production_processor.py --server "prod-server" --database "XmlConversionDB" --workers 8 --instance-id 2 --instance-count 3 --enable-pooling
```

Expected: 600-1000+ apps/min (true 3x+ scaling)

---

That's it! Run the three commands in separate terminals and watch the throughput increase. 🚀
