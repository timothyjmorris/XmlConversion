# Quick Start: Running 2-3 Processors Simultaneously

## FASTEST WAY TO START: Option 1 (No Code Changes)

Just open 3 terminals and run:

```powershell
# Terminal 1
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --batch-size 25 --log-level INFO

# Terminal 2
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --batch-size 25 --log-level INFO

# Terminal 3
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --workers 4 --batch-size 25 --log-level INFO
```

### What Happens:
- Each instance gets ~4 workers (12 total workers for CPU parallelism)
- They all query processing_log to skip already-processed apps
- Occasional duplicate attempts are safe (DB constraints prevent duplicate inserts)
- Any crashed instance doesn't interfere with the others

### Expected Throughput:
- Single instance: ~50-100 apps/min (depends on CPU)
- 3 instances: ~120-250 apps/min (3x speedup, minus overhead)

---

## ZERO DUPLICATE ATTEMPTS: Option 2 (Small Code Addition)

If you want to eliminate duplicate processing attempts completely, add partition filter:

### 1. Modify ProductionProcessor

Add to `production_processor.py` in `__init__` method (after line ~150):

```python
# Add instance coordination for multi-processor deployments
self.instance_id = None
self.instance_count = 1
```

Modify `get_xml_records()` method around line ~360:

```python
# After the exclude_failed block, add:
if self.instance_count > 1 and self.instance_id is not None:
    base_conditions += f"""
        AND (ax.app_id % {self.instance_count}) = {self.instance_id}
    """
```

### 2. Add CLI Arguments

Modify `main()` function in `production_processor.py` (add before `args = parser.parse_args()`):

```python
parser.add_argument("--instance-id", type=int, default=None, 
                   help="Instance ID for partitioned processing (0 to instance-count-1)")
parser.add_argument("--instance-count", type=int, default=1, 
                   help="Total number of instances running in parallel")

# Add after processor creation:
if args.instance_id is not None:
    processor.instance_id = args.instance_id
    processor.instance_count = args.instance_count
    processor.logger.info(f"Running as instance {args.instance_id} of {args.instance_count}")
```

### 3. Run with Partitioning

```powershell
# Terminal 1
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
  --workers 4 --batch-size 25 --instance-id 0 --instance-count 3 --log-level INFO

# Terminal 2
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
  --workers 4 --batch-size 25 --instance-id 1 --instance-count 3 --log-level INFO

# Terminal 3
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" ^
  --workers 4 --batch-size 25 --instance-id 2 --instance-count 3 --log-level INFO
```

### Result:
- Instance 0 processes: app_id % 3 == 0 (apps 3, 6, 9, 12, ...)
- Instance 1 processes: app_id % 3 == 1 (apps 1, 4, 7, 10, ...)
- Instance 2 processes: app_id % 3 == 2 (apps 2, 5, 8, 11, ...)
- **Zero duplicate attempts across instances**

---

## Monitoring Tips

### Watch Real-Time Progress

```powershell
# Watch logs from all 3 instances
Get-Content -Path "logs/production_*.log" -Tail 20 -Wait

# Or use PowerShell tail equivalent
Get-Content -Path "logs/production_*.log" -Follow
```

### Check Processing Log

```powershell
# Count processed apps
sqlcmd -S localhost\SQLEXPRESS -d XmlConversionDB ^
  -Q "SELECT COUNT(*), status FROM [sandbox].[processing_log] GROUP BY status"

# See which apps failed
sqlcmd -S localhost\SQLEXPRESS -d XmlConversionDB ^
  -Q "SELECT app_id, failure_reason FROM [sandbox].[processing_log] WHERE status='failed' ORDER BY app_id"

# Track progress by instance
sqlcmd -S localhost\SQLEXPRESS -d XmlConversionDB ^
  -Q "SELECT session_id, COUNT(*), SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) FROM [sandbox].[processing_log] GROUP BY session_id"
```

---

## Comparison

| Aspect | Option 1 | Option 2 |
|--------|----------|----------|
| Code changes | 0 lines | ~20 lines |
| Duplicate attempts | Rare | Zero |
| Setup time | 30 seconds | 5 minutes |
| Implementation | 3 terminals | 3 terminals + code edit |
| Best for | Initial testing | Production runs |

---

## Troubleshooting

### "Primary key violation in processing_log"
- Means two instances tried to process same app_id
- Normal in Option 1 (expected occasionally)
- Should never happen in Option 2 (code error if it does)
- The app_base insert will succeed anyway, processing_log insert fails gracefully

### One instance seems stuck
- Check CPU usage with Task Manager
- All instances competing for same CPU cores
- Consider reducing workers per instance: `--workers 2` instead of 4

### Uneven work distribution
- Instance 1 finishes first, processes more
- Instance 3 still working
- Normal behavior - instance 1 will wait or terminate when done

---

## Production Recommendation

For production use, implement **Option 2** (partitioned processing):
- Eliminates waste from duplicate attempts
- Clear work allocation
- Easy to understand operationally
- Scales to many instances without coordination server

For testing/development, use **Option 1** (uncoordinated):
- No code changes
- Good enough for exploring throughput
- Simple to stop/restart

---

See `RESUMABILITY_AND_CONCURRENT_PROCESSING_ANALYSIS.md` for detailed technical explanation.
