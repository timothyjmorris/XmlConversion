# Performance Analysis & Configuration Findings

**Last Updated:** December 2024  
**Status:** Baseline established, configuration optimized

---

## Performance Baseline

**Current Throughput:** ~2,000 applications/minute  
**Target:** 3,500+ applications/minute  
**Environment:** Local laptop (4 cores), SQL Server Express, Windows

---

## Root Cause Analysis: CPU-Bound Processing

**Bottleneck Identified:** XML parsing and data transformation (CPU-bound), NOT database I/O

### Tests Performed (All showed NO improvement):

1. **Database Optimization**
   - Removed foreign keys temporarily
   - Rebuilt indexes
   - Result: No measurable improvement

2. **Logging Reduction**
   - Implemented conditional DEBUG logs
   - Result: Logging overhead negligible

3. **Connection Pooling**
   - Tested various pool sizes (min: 4, max: 20)
   - Result: No improvement (disabled for SQLExpress)

**Conclusion:** Database I/O is NOT the bottleneck. CPU cycles spent on:
- XML parsing (`lxml.etree`)
- Data transformation (mapping contract application)
- Python object creation/manipulation

---

## Optimal Configuration (Local Development)

### Batch Size: 1000 applications/batch

**What it controls:** Number of App XMLs fetched per SQL query (pagination size)

**Tested values:** 20, 50, 100, 500, 1000, 2000

**Results:**
| Batch Size | Throughput (apps/min) | Notes |
|------------|----------------------|-------|
| 20 | ~400 | Too small, overhead dominates |
| 50 | ~800 | Better but still overhead |
| 100 | ~1,200 | Decent |
| 500 | ~1,800 | Good |
| **1000** | **~2,000** | **Optimal (peak)** |
| 2000 | ~1,900 | Memory pressure, diminishing returns |

**Recommendation:** Use 1000 for local dev, may vary for production SQL Server

**Note:** Batch-size is distinct from:
- `--limit` (total applications cap - safety limit)
- `--chunk-size` (process boundaries for runs >100k apps)

---

### Workers: 4 (one per CPU core)

**What it controls:** Degree of parallelism

**Recommendation:** Match CPU core count
- Each worker has isolated pyodbc connection
- Parallelizes well without context-switching overhead
- More workers than cores = diminishing returns

**Production Note:** May scale linearly on servers with more cores

---

### Logging Level: WARNING (production)

**Development:** INFO or DEBUG for visibility  
**Production:** WARNING to reduce noise

**Finding:** Logging overhead is negligible; level choice is about clarity, not performance

---

### Connection Pooling: Disabled (for SQL Server Express)

**Tested:** Various pool configurations  
**Result:** No improvement for Express edition

**Production Note:** Enable for Enterprise/Standard SQL Server editions:
- Min pool size: 4
- Max pool size: 20
- Different performance characteristics expected

---

## Performance Optimization History

### Initial Performance: ~500 apps/min
**Issues:**
- Lock contention (workers serialized)
- Suboptimal batch size (100)

### After Bug Fixes: ~1,200 apps/min
**Fixes:**
- Lock contention resolved (WITH NOLOCK)
- Resume logic corrected
- Pagination bug fixed

### After Configuration Tuning: ~2,000 apps/min
**Optimizations:**
- Batch-size increased to 1000
- Workers set to 4 (match cores)
- Cursor-based pagination

---

## Known Limitations & Future Improvements

### Current Bottleneck
- **CPU-bound:** XML parsing (lxml) and Python data transformation
- Database I/O is NOT limiting factor

### Potential Improvements
1. **Cython compilation** - Compile hot-path Python code to C
2. **Batch XML parsing** - Parse multiple XMLs in one lxml call
3. **Production SQL Server** - Better parallelism, more cores
4. **Memory-mapped files** - If XML source becomes file-based

### Target Not Yet Met
- **Current:** ~2,000 apps/min
- **Target:** 3,500+ apps/min
- **Gap:** 43% below target

**Next Steps:** Profiling with production SQL Server to determine scaling characteristics

---

## Production Deployment Checklist

Before deploying to production:
- [ ] Test with production SQL Server (different performance profile)
- [ ] Adjust batch-size for production hardware (benchmark 500-1500 range)
- [ ] Enable connection pooling for production SQL Server
- [ ] Measure baseline throughput on production hardware
- [ ] Tune workers based on production server CPU count
- [ ] Monitor memory usage during large runs

---

## References

- [FINAL_PERFORMANCE_SUMMARY.md](../../performance_tuning/FINAL_PERFORMANCE_SUMMARY.md) - Detailed analysis
- [Archived Analysis](../../performance_tuning/archived_analysis/) - Investigation history
- [bug-fixes.md](bug-fixes.md) - Critical bugs that were resolved
