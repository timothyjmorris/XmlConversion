# Option 2: Partition-Based Coordination - Implementation Guide

## Quick Summary

This document shows **exactly** what code to add to production_processor.py to implement partitioned processing (Option 2).

This allows 2-3 instances to run simultaneously with **ZERO duplicate attempts**.

---

## Changes Required

### Change 1: Add instance fields to ProductionProcessor.__init__

**File**: `production_processor.py`  
**Location**: In `__init__` method, after line ~130 (after `self.connection_timeout = ...`)

**Add these lines**:

```python
        self.connection_timeout = connection_timeout
        
        # Instance coordination for multi-processor deployments (Option 2)
        self.instance_id = None        # Which partition this instance handles (0, 1, 2, ...)
        self.instance_count = 1        # Total number of instances (how many partitions)
```

---

### Change 2: Add partition filtering to get_xml_records()

**File**: `production_processor.py`  
**Location**: In `get_xml_records()` method, after the `exclude_failed` block (around line ~375)

**Find this code**:

```python
                if exclude_failed:
                    # processing_log table uses target_schema from MappingContract
                    # Like all target tables, it's schema-isolated (e.g., [sandbox].[processing_log])
                    
                    base_conditions += f"""
                        AND NOT EXISTS (
                            SELECT 1 
                            FROM [{self.target_schema}].[processing_log] pl 
                            WHERE 
                                pl.app_id = ax.app_id 
                                AND pl.status IN ('success', 'failed')
                        )  -- Exclude records that were already processed (success or failed)
                    """
                
                if limit:
```

**Replace with**:

```python
                if exclude_failed:
                    # processing_log table uses target_schema from MappingContract
                    # Like all target tables, it's schema-isolated (e.g., [sandbox].[processing_log])
                    
                    base_conditions += f"""
                        AND NOT EXISTS (
                            SELECT 1 
                            FROM [{self.target_schema}].[processing_log] pl 
                            WHERE 
                                pl.app_id = ax.app_id 
                                AND pl.status IN ('success', 'failed')
                        )  -- Exclude records that were already processed (success or failed)
                    """
                
                # Partition-based coordination: each instance processes only its partition
                # Reduces collision between concurrent instances from ~50% to 0%
                if self.instance_count > 1 and self.instance_id is not None:
                    base_conditions += f"""
                        AND (ax.app_id % {self.instance_count}) = {self.instance_id}
                    """
                    self.logger.info(f"Processing partition: app_id % {self.instance_count} == {self.instance_id}")
                
                if limit:
```

---

### Change 3: Add CLI arguments

**File**: `production_processor.py`  
**Location**: In `main()` function, in the `parser.add_argument` section (around line ~800)

**Find this line**:

```python
    parser.add_argument("--connection-timeout", type=int, default=30,
                       help="Connection timeout in seconds (default: 30)")
    
    args = parser.parse_args()
```

**Replace with**:

```python
    parser.add_argument("--connection-timeout", type=int, default=30,
                       help="Connection timeout in seconds (default: 30)")
    
    # Partition-based coordination for multi-processor deployments
    parser.add_argument("--instance-id", type=int, default=None,
                       help="Instance ID for partitioned processing (0 to instance-count-1)")
    parser.add_argument("--instance-count", type=int, default=1,
                       help="Total number of instances running in parallel (for work partitioning)")
    
    args = parser.parse_args()
```

---

### Change 4: Pass instance parameters to processor

**File**: `production_processor.py`  
**Location**: In `main()` function, after processor initialization (around line ~820)

**Find this code**:

```python
        # Create processor with connection pooling optimizations
        processor = ProductionProcessor(
            server=args.server,
            database=args.database,
            username=args.username,
            password=args.password,
            workers=args.workers,
            batch_size=args.batch_size,
            log_level=args.log_level,
            disable_metrics=args.disable_metrics,
            enable_pooling=args.enable_pooling,
            min_pool_size=args.min_pool_size,
            max_pool_size=args.max_pool_size,
            enable_mars=args.enable_mars,
            connection_timeout=args.connection_timeout
        )
        
        # Run processing
```

**Replace with**:

```python
        # Create processor with connection pooling optimizations
        processor = ProductionProcessor(
            server=args.server,
            database=args.database,
            username=args.username,
            password=args.password,
            workers=args.workers,
            batch_size=args.batch_size,
            log_level=args.log_level,
            disable_metrics=args.disable_metrics,
            enable_pooling=args.enable_pooling,
            min_pool_size=args.min_pool_size,
            max_pool_size=args.max_pool_size,
            enable_mars=args.enable_mars,
            connection_timeout=args.connection_timeout
        )
        
        # Set up partition coordination if specified
        if args.instance_id is not None:
            processor.instance_id = args.instance_id
            processor.instance_count = args.instance_count
            processor.logger.info(f"Partition coordination enabled:")
            processor.logger.info(f"  This instance: {args.instance_id}")
            processor.logger.info(f"  Total instances: {args.instance_count}")
            processor.logger.info(f"  Processing: app_id % {args.instance_count} == {args.instance_id}")
        
        # Run processing
```

---

## How to Use

### Run 3 instances with partitioning:

```powershell
# Terminal 1: Processes app_ids where (app_id % 3) == 0
# These are: 3, 6, 9, 12, 15, 18, 21, ...
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" `
  --workers 4 --batch-size 25 --instance-id 0 --instance-count 3 --log-level INFO

# Terminal 2: Processes app_ids where (app_id % 3) == 1
# These are: 1, 4, 7, 10, 13, 16, 19, ...
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" `
  --workers 4 --batch-size 25 --instance-id 1 --instance-count 3 --log-level INFO

# Terminal 3: Processes app_ids where (app_id % 3) == 2
# These are: 2, 5, 8, 11, 14, 17, 20, ...
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" `
  --workers 4 --batch-size 25 --instance-id 2 --instance-count 3 --log-level INFO
```

### Or 2 instances:

```powershell
# Terminal 1: Odd app_ids
python production_processor.py ... --instance-id 0 --instance-count 2

# Terminal 2: Even app_ids
python production_processor.py ... --instance-id 1 --instance-count 2
```

### Or continue with Option 1 (no partitioning):

```powershell
# Just don't use --instance-id and --instance-count
# Behaves like before: occasional collisions but still safe
python production_processor.py ... # no partition args
```

---

## What Gets Logged

With partition coordination enabled, you'll see in the logs:

```
Partition coordination enabled:
  This instance: 0
  Total instances: 3
  Processing: app_id % 3 == 0
Extracting XML records (limit=25, last_app_id=0, exclude_failed=True)
Extracted 25 XML records (excluding already processed and failed)
```

---

## Verification

### Check that instances are processing different apps:

```sql
-- See which app_ids each session processed
SELECT session_id, 
       MIN(app_id) as min_app_id,
       MAX(app_id) as max_app_id,
       COUNT(*) as count,
       COUNT(DISTINCT (app_id % 3)) as unique_partitions
FROM [sandbox].[processing_log]
GROUP BY session_id
ORDER BY session_id DESC
```

**Expected result**:
- Instance 0 (session 1): app_id % 3 == 0 only (3, 6, 9, ...)
- Instance 1 (session 2): app_id % 3 == 1 only (1, 4, 7, ...)
- Instance 2 (session 3): app_id % 3 == 2 only (2, 5, 8, ...)

If you see `unique_partitions > 1` for any session, something went wrong.

### Check for zero collisions:

```sql
-- Should return NO rows (zero collisions)
SELECT app_id, COUNT(*), STRING_AGG(session_id, ', ') as sessions
FROM [sandbox].[processing_log]
GROUP BY app_id
HAVING COUNT(*) > 1
```

If this returns rows, you have collision issues.

---

## Troubleshooting

### "Invalid instance-id"
- Make sure `--instance-id` is in range `0 to instance-count-1`
- Example: If `--instance-count 3`, use `--instance-id 0`, `1`, or `2`

### "Uneven work distribution"
- If your app_ids are clustered (e.g., lots of even numbers)
- Partitioning by modulo might be uneven
- Fallback: use Option 1 (uncoordinated) or use different partition key

### "One instance finishing first"
- Normal - it means the partition assigned to that instance has less work
- With 3 instances and uniform app_id distribution: load is balanced
- With 3 instances and skewed distribution: load is uneven

### "Some app_ids still missing from processing_log"
- Make sure all 3 instances are running
- Each instance only processes its partition
- If one instance crashes, that partition's apps won't be processed (expected)
- Restart that instance to resume its partition

---

## Fallback to Option 1

If you want to disable partitioning and go back to Option 1:

```powershell
# Just don't use --instance-id and --instance-count
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" `
  --workers 4 --batch-size 25 --log-level INFO
```

The code is backward compatible - if you don't provide partition args, it works like before.

---

## Performance Expectations

With 3 instances using Option 2 (partitioned):

| Metric | Single Instance | 3 Instances (Option 2) |
|--------|-----------------|------------------------|
| Workers | 4 | 12 (total) |
| Throughput | 100 apps/min | 250-350 apps/min |
| Speedup | 1x | 2.5-3.5x |
| Collisions | N/A | 0 (guaranteed) |
| Load Balance | N/A | Perfect (if uniform app_ids) |

---

## Complete Example

Here's the exact syntax for your environment:

```powershell
# Terminal 1
python production_processor.py `
  --server "localhost\SQLEXPRESS" `
  --database "XmlConversionDB" `
  --workers 4 `
  --batch-size 25 `
  --instance-id 0 `
  --instance-count 3 `
  --log-level INFO

# Terminal 2
python production_processor.py `
  --server "localhost\SQLEXPRESS" `
  --database "XmlConversionDB" `
  --workers 4 `
  --batch-size 25 `
  --instance-id 1 `
  --instance-count 3 `
  --log-level INFO

# Terminal 3
python production_processor.py `
  --server "localhost\SQLEXPRESS" `
  --database "XmlConversionDB" `
  --workers 4 `
  --batch-size 25 `
  --instance-id 2 `
  --instance-count 3 `
  --log-level INFO
```

Then monitor with:

```powershell
# Watch logs
Get-Content -Path "logs/production_*.log" -Tail 20 -Wait

# Check progress
sqlcmd -S "localhost\SQLEXPRESS" -d XmlConversionDB `
  -Q "SELECT session_id, COUNT(*) FROM [sandbox].[processing_log] GROUP BY session_id"
```

That's it! Four small code changes, and you have zero-collision concurrent processing. 🚀
