# Phase II.1: Batch Size Optimization Guide

## Quick Start

```bash
# 1. Test batch size 50
python establish_baseline.py  # Will use batch_size=50 (after editing ParallelCoordinator)

# 2. Test batch size 100
# ... edit ParallelCoordinator.batch_size to 100 ...
python establish_baseline.py

# Continue for sizes: 200, 500, 1000, 2000
```

## Current Setup
- **Baseline:** 553.8 rec/min (median, 50 records, batch=1000)
- **Test Dataset:** 750 records (should give more stable metrics)
- **Recommended Test Config:** 5 runs per size (faster than 10)
- **Expected Range:** 500-650 rec/min (based on overhead)

## Edit ParallelCoordinator.batch_size

File: `xml_extractor/parsing/parallel_coordinator.py`

Find this line (~line 40):
```python
self.batch_size = 1000
```

Change to test value, e.g.:
```python
self.batch_size = 50  # or 100, 200, 500, 1000, 2000
```

## Batch Sizes to Test (in order)

1. **50** - Very small, high overhead
2. **100** - Small, more overhead
3. **200** - Medium-small
4. **500** - Medium
5. **1000** - Current (baseline)
6. **2000** - Large, diminishing returns

## Expected Results

For 750 records with 2 workers:

- **50:** ~500-550 (high overhead per batch)
- **100:** ~520-570 (good balance)
- **200:** ~540-590 (better throughput)
- **500:** ~570-620 (optimal zone, less setup/teardown)
- **1000:** 553.8 (baseline, current)
- **2000:** ~560-600 (diminishing returns, memory pressure)

**Expected optimal:** 500 or 1000 rec/min

## Testing Procedure

For each batch size:

```bash
# 1. Edit ParallelCoordinator.batch_size
vim xml_extractor/parsing/parallel_coordinator.py  # Change batch_size

# 2. Run baseline (5 iterations to save time)
python establish_baseline.py

# 3. Record results in PHASE2_RESULTS.md
# Copy the Median throughput value
# Note: vs Baseline calculation
```

## Key Metrics to Record

- Median throughput (rec/min)
- Std Dev (consistency)
- Min/Max range
- Improvement vs baseline %

## When Done

1. Pick the best batch size
2. Keep that value in ParallelCoordinator
3. Commit with message: "Phase II.1: Batch size optimization - Optimal: XXX (+ Y% improvement)"
4. Update PHASE2_RESULTS.md with final results

## Tips

- If variance is high with 750 records, add more mock data
- If testing is slow, run only 3-5 iterations per size
- Database should auto-clear between runs (processing_log + app_base)
- Watch for memory usage spikes with very large batches
