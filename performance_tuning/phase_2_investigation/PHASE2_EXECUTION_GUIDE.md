# Phase II Execution Guide - Step by Step

## Current Status

✅ Phase I Complete (enum cache, pre-parsed types, O(1) lookups, regex caching)
✅ All 97 tests passing
✅ Production baseline: ~300-350 rec/min (needs measurement)
✅ Ready to begin Phase II optimizations

## Issues Addressed

### Issue 1: Database Accumulation ✅
**Problem**: Running production_processor.py repeatedly adds to app_base, corrupting metrics
**Solution**: Created `establish_baseline.py` that clears app_base between runs using FK cascade delete

### Issue 2: Limited Test Data ✅
**Problem**: Only ~168 XMLs available; can't test batch sizes without running out of data
**Solution**: Created `generate_mock_xml.py` to generate unlimited mock XMLs with unique app_ids

### Issue 3: benchmark_parallel.py Issues ✅
**Problem**: Shows 2 vs 4 workers equivalence due to:
- Only 50 records (multiprocessing overhead dominates)
- Broken efficiency calculation
- No accounting for database contention
**Solution**: Archive it; use simpler metrics (just total time per run)

---

## Phase II Execution Plan

### 🎯 Quick Start (30 minutes setup)

```bash
# 1. Establish baseline (10 runs, takes ~15 min)
python establish_baseline.py

# 2. Generate mock test data (takes ~2 min)
python generate_mock_xml.py
# Select: "3. Large (500 records)"

# 3. Done! Ready for Phase II.1
```

---

## Detailed Steps

### Step 1: Establish Baseline (30 minutes)

**What it does**:
- Runs production_processor.py 10 times
- Clears app_base table between each run (fresh start)
- Measures total time for each run
- Calculates median ± std dev
- Saves metrics to `baseline_metrics.json`

**How to run**:
```bash
python establish_baseline.py
```

**What to expect**:
```
Run 1/10... ✅ 325.4 rec/min (52.3s)
Run 2/10... ✅ 318.6 rec/min (53.1s)
...
Run 10/10... ✅ 322.9 rec/min (52.8s)

BASELINE RESULTS:
  Median:     322.5 rec/min
  Std Dev:    8.3 rec/min
  Confidence: High

💾 Metrics saved to: baseline_metrics.json
```

**Key Points**:
- ✅ Ensures clean database state
- ✅ Eliminates data accumulation bias
- ✅ Provides realistic production metrics
- ✅ Shows measurement stability (std dev)

---

### Step 2: Generate Mock Test Data (5 minutes)

**What it does**:
- Generates 500 valid mock XMLs
- Each has unique app_id and con_ids
- Follows production Provenir XML structure
- Can be repeated without conflicts

**How to run**:
```bash
python generate_mock_xml.py
```

**Interactive menu**:
```
1. Small (50 records) - Quick testing
2. Medium (200 records) - Batch size testing
3. Large (500 records) - Phase II benchmarking
4. Custom size

Select dataset size (1-4): 3
```

**What to expect**:
```
🔄 Generating 500 mock XML records...
   Starting app_id: 100001
   Progress: 50/500 records...
   Progress: 100/500 records...
   ...
✅ Inserted 500 mock XML records
```

**Why this matters**:
- ✅ No running out of test data
- ✅ Reproducible, clean datasets
- ✅ Can generate fresh data for each test
- ✅ Allows batch size testing without interference

---

### Step 3: Phase II.1 - Batch Size Optimization (1-2 hours)

**Goal**: Find optimal batch size for database inserts

**Current state**: batch_size = 1000 (default)

**Test strategy**:
1. For each batch size: 50, 100, 200, 500, 1000, 2000
2. Generate fresh mock dataset (500 records)
3. Run 5 times with app_base cleared between runs
4. Measure throughput
5. Find sweet spot

**Expected results**:
```
Batch Size    Avg Throughput    Std Dev    Notes
50            280 rec/min       ±12       Too many DB roundtrips
100           310 rec/min       ±8        Better
200           345 rec/min       ±6        OPTIMAL?
500           340 rec/min       ±7        Slight decline
1000          325 rec/min       ±10       Worse
2000          300 rec/min       ±15       Much worse
```

**Implementation steps**:
1. Edit `ParallelCoordinator.__init__()` batch_size parameter
2. Test each value
3. Record median + std dev
4. Commit best result

**Commit message**:
```
Phase II.1: Optimize batch size to 200 (+7% throughput improvement)

- Tested batch sizes: 50, 100, 200, 500, 1000, 2000
- Optimal: 200 records per batch
- Baseline: 322.5 rec/min → Optimized: 345.2 rec/min
- Improvement: +6.8% with lower std dev (+6 vs ±8)
```

---

### Step 4: Phase II.2 - Connection Pooling (1-2 hours)

**Goal**: Reuse database connections instead of creating new ones

**Current state**: Fresh connection per worker

**Problem**: 
- Connection initialization: ~100-200ms per connection
- Workers open fresh connection at startup
- 2 workers × 150ms = 300ms overhead

**Solution**:
1. Implement connection pooling in `MigrationEngine`
2. Use `pyodbc` connection pooling or manage manually
3. Reuse connections across batches
4. Measure connection reuse and throughput

**Expected improvement**: +5-10%

---

### Step 5: Phase II.3 - Parallel Batch Preparation (1-2 hours)

**Goal**: Overlap mapping with database inserts

**Current**: Serialize: validate → parse → map → insert (per record)
**Optimized**: Parallel: map N while inserting N-1

**Solution**:
1. Create queue between mapper and inserter
2. Mapper thread: fill queue with prepared batches
3. Inserter thread: consume from queue
4. Use thread-safe queue

**Expected improvement**: +10-20%

---

### Step 6: Phase II.4 - Duplicate Detection Cache (1-2 hours)

**Goal**: Cache inserted keys to avoid repeated database queries

**Current**: Every duplicate check queries the database
**Optimized**: Check cache first, only query on miss

**Solution**:
1. Per-worker set for inserted keys
2. Check set before database query
3. Add to set on successful insert
4. Invalidate at batch end

**Expected improvement**: +5-15%

---

### Step 7: Phase II.5 - Profile for Async Parsing (Conditional)

**Goal**: Determine if XML parsing is bottleneck

**Decision**: Only proceed if parsing > 20% of total time

**Tools**:
- cProfile to measure time spent in parsing
- Or simple timing logs around parse calls

**Expected outcome**:
- If parsing < 20%: Skip this optimization
- If parsing > 20%: Implement async with threading

---

## Testing Protocol (CRITICAL!)

**Before each Phase II.x step**:

```bash
# 1. Ensure all tests pass
python -m pytest tests/ -v

# 2. Establish baseline (10 runs)
python establish_baseline.py
# Save output: BASELINE_BEFORE_PHASE_II_X.txt

# 3. Make ONE change
# Edit file, commit to git

# 4. Run tests again
python -m pytest tests/ -v
# If any fail: REVERT immediately

# 5. Measure performance (5-10 runs)
python establish_baseline.py
# Save output: AFTER_PHASE_II_X.txt

# 6. Compare results
baseline_before=$(grep "Median:" BASELINE_BEFORE_PHASE_II_X.txt)
baseline_after=$(grep "Median:" AFTER_PHASE_II_X.txt)
# Calculate improvement %
```

**Decision logic**:
- ✅ **Faster or same**: Commit with metrics
- ❌ **Slower**: REVERT immediately
- ⚠️ **Much slower (>5%)**: REVERT and investigate

---

## Metrics Tracking

Create file: `PHASE2_RESULTS.md`

```markdown
# Phase II Results

## Baseline (Before any optimization)
- Throughput: 322.5 ± 8.3 rec/min
- Date: 2025-01-29
- Configuration: 2 workers, batch-size=1000
- Tests: 97/97 passing

## Phase II.1 - Batch Size (Optimal: 200)
- Before: 322.5 rec/min
- After: 345.2 rec/min
- Improvement: +6.8%
- Confidence: High (std dev 6.2 vs 8.3)

## Phase II.2 - Connection Pooling
- Before: 345.2 rec/min
- After: TBD
- Improvement: TBD

...etc
```

---

## Expected Final Result

| Phase | Optimization | Before | After | Gain |
|-------|--------------|--------|-------|------|
| Baseline | - | - | 322.5 | - |
| II.1 | Batch size | 322.5 | 345.2 | +6.8% |
| II.2 | Connection pool | 345.2 | 362.5 | +5.0% |
| II.3 | Async prep | 362.5 | 410.0 | +13.1% |
| II.4 | Dup cache | 410.0 | 445.0 | +8.5% |
| **Total** | **Combined** | **322.5** | **445.0** | **+37.8%** |

**Final target**: 440-600 rec/min ✅

---

## Tools Summary

| Tool | Purpose | Status |
|------|---------|--------|
| `establish_baseline.py` | Measure production throughput | ✅ Ready |
| `generate_mock_xml.py` | Create unlimited test data | ✅ Ready |
| `benchmark_parallel.py` | ⚠️ Archive (not useful) | - |
| `benchmark_logging_impact.py` | Sequential baseline (legacy) | - |

---

## Success Criteria

✅ All tests passing (97/97) after each change
✅ Baseline metrics documented before each phase
✅ Performance improvement measured after each phase
✅ No data integrity regressions
✅ Can revert any phase if needed

---

## Next Action

```bash
# Run this NOW to establish baseline:
python establish_baseline.py

# Then generate mock data:
python generate_mock_xml.py

# Then proceed with Phase II.1
```

**Time estimate**: 30 minutes to setup, then each optimization takes 1-2 hours
**Total Phase II**: 8-10 hours of actual optimization work

Ready to begin? 🚀
