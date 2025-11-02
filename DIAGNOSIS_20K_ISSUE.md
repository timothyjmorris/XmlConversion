# Diagnosis: Why 20k Instead of 15k?

## Quick Analysis

If you ran 3 instances with `--limit 5000` each:
- Instance 0: should process ~1667 records (5000 / 3)
- Instance 1: should process ~1667 records (5000 / 3)  
- Instance 2: should process ~1667 records (5000 / 3)
- **Total: 5000 records** (not 15k or 20k)

But you got 20k, which suggests:

**Option A: Each instance processed 5000 (no partitioning)**
- 3 instances × 5000 = 15k (close to 20k with some overlap/collisions)

**Option B: Each instance processed 5000-6667**
- 3 instances × 6667 = 20k (perfect match!)

## Root Cause: The Partition Filter Might Not Be Applied

The problem is likely here in `production_processor.py` line ~387-390:

```python
# Add instance-based partitioning if running concurrently
if self.instance_count > 1:
    base_conditions += f"""
        AND (ax.app_id % {self.instance_count}) = {self.instance_id}
    """
```

**Possible Issues:**

1. **instance_count is being set to 1** when you think it's 3
   - Check: Do the logs show `Concurrent Instances: 1/3`?

2. **The WHERE clause has a syntax error** and is being silently ignored
   - Modulo operator `%` might not work in SQL Server T-SQL (it should be `%`)
   - Could have an issue with integer division

3. **The partition isn't actually reducing records** because:
   - With 30k total records and partition: `app_id % 3`
   - App_ids 1-30000 distributed: `1%3=1`, `2%3=2`, `3%3=0`, etc.
   - Instance 0 should get: 3, 6, 9, 12... (10,000 records)
   - But if `--limit 5000`, it stops at first 5000 matched

## How to Verify

Run this SQL query to see partition distribution:

```sql
-- Check if partitions are even
SELECT 
    (app_id % 3) as partition_id,
    COUNT(*) as record_count
FROM [dbo].[app_xml]
GROUP BY (app_id % 3)
ORDER BY partition_id;
```

Expected output (with 30k records):
```
partition_id | record_count
0            | 10000
1            | 10000
2            | 10000
```

If you see something like:
```
partition_id | record_count
0            | 20000
1            | 5000
2            | 5000
```

Then the issue is: **app_ids are NOT sequential or 1-based**. They might be clustered.

##  Check processing_log for Evidence

```sql
-- See which instances processed what
SELECT DISTINCT
    session_id,
    COUNT(*) as apps_processed,
    MIN(app_id) as first_app_id,
    MAX(app_id) as last_app_id
FROM [sandbox].[processing_log]
GROUP BY session_id
ORDER BY session_id DESC;
```

Look for:
- **3 different session_ids** (good - each instance has unique session)
- **Each processed ~5000** (bad - means no partitioning)
- **One session got 0-100, another got 101-5000, another got 5001-20000** (bad - instances aren't partitioned by modulo)

## The Real Issue

Based on your observation "app_ids processed in order" (`3, 6, 9, 12, 15...`), the partition IS working BUT:

1. **You're getting 20k total** = each instance processed 6667 instead of 1667
2. **resume picks up at app_id 15001** = that's after 15k

This suggests:
- Maybe `--limit` is being applied **PER BATCH**, not total?
- Or the coordinator is running multiple batches?

Check the logs for how many batches processed per instance.

## Fix Depends On Answer

Once you run the SQL queries above, we'll know if:
- **Partition filter works**: Then issue is in batch/limit logic
- **Partition filter doesn't work**: Then issue is SQL syntax (% operator or integer conversion)
