# Phase II.3 Action Card: Queue-Based Parallel Processing

**Current Baseline:** 914 rec/min (pooling disabled)  
**Target:** 1050-1100 rec/min (+15-25%)  
**Approach:** Overlap I/O waits with XML processing via queue-based architecture

---

## The Problem

Workers idle 70-90% of the time waiting for batch inserts to complete. While one batch is being inserted to the database (100+ ms), other workers are idle.

## The Solution

Queue-based architecture: workers continuously parse and queue inserts (non-blocking), while a background thread handles database inserts.

```
Current:  Parse → Wait → Insert batch → Wait → Parse → ...
Queue:    Parse → Queue → Parse → Queue → Parse → ...
          (Insert thread processes queue in background)
```

---

## Implementation Roadmap

### Phase II.3a: Investigation (1-2 hours)
1. Profile insert latency (measure I/O wait time)
2. Measure worker idle time per batch
3. Document findings
4. Estimate improvement potential

### Phase II.3b: Implementation (2-3 hours)
1. Create thread-safe InsertQueue class
2. Modify ParallelCoordinator to use queue
3. Modify workers to queue inserts (non-blocking)
4. Create background insert thread
5. Initial testing

### Phase II.3c: Optimization (1-2 hours)
1. Tune queue size (500-5000)
2. Tune insert batch size (50-500)
3. Tune worker count (2-8)
4. Performance testing and tuning
5. Document results

---

## Expected Timeline

**Total:** 4-7 hours (likely 5-6)

- Phase II.3a: Fri morning (1-2h)
- Phase II.3b: Fri afternoon (2-3h)
- Phase II.3c: Next session (1-2h)

---

## Success Criteria

✅ Queue-based architecture working  
✅ All data inserted correctly (no loss/duplication)  
✅ Performance: 914 → 1050-1100 rec/min (+15-25%)  
✅ Code maintainable and tested

---

## Files to Create/Modify

**Create:**
- PHASE2_3_PROFILING_RESULTS.md
- PHASE2_3_QUEUE_ARCHITECTURE.md
- benchmark_queue_optimization.py

**Modify:**
- parallel_coordinator.py (add queue + insert thread)
- data_mapper.py (queue inserts instead of blocking)

---

## Key Decisions

1. **Use Python queue.Queue** (thread-safe, battle-tested)
2. **Background insert thread** (allows continuous worker processing)
3. **Non-blocking queue operations** (no worker blocking on insert)
4. **Start simple, add complexity gradually** (risk mitigation)

---

## Next Steps

1. ✅ Understand Phase II.3 plan (THIS DOCUMENT)
2. 🔄 Run Phase II.3a profiling
3. 🔄 Implement queue-based architecture
4. 🔄 Optimize parameters
5. 🔄 Verify +15-25% improvement

---

## Key Files

- Implementation Plan: `PHASE2_3_IMPLEMENTATION_PLAN.md`
- Current Baseline: `baseline_metrics.json` (914 rec/min)
- Test Script: `env_prep/establish_baseline.py`
- Benchmarking: `performance_tuning/benchmarks/`

---

**Status:** 🚀 READY TO START  
**Current Baseline:** 914 rec/min  
**Target:** 1050-1100 rec/min
