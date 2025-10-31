# Environment-Specific Performance Setup

Configuration guidance for different SQL Server environments (SQLExpress, SQL Server Dev, Production).

## Quick Reference

| Environment | Pooling | Min Pool | Max Pool | Expected Throughput | Notes |
|-------------|---------|----------|----------|---------------------|-------|
| **SQLExpress (Local)** | ❌ Disabled | - | - | 950-1000 rec/min | Default setting, optimized for local I/O |
| **SQL Server Dev** | ✅ Enabled | 8 | 40 | 1500-2000 rec/min | Network latency makes pooling valuable |
| **SQL Server Prod** | ✅ Enabled | 16 | 64 | 3000-5000+ rec/min | Large pool for concurrent connections |

---

## SQLExpress (Local Development)

**What it is:** SQL Server Express on local machine, I/O bound workload on local disk.

**Why pooling is disabled by default:**
- Pooling adds ODBC state reset overhead (~10-20ms per connection reuse)
- On local disk I/O-bound workload, this overhead is NOT recovered by connection reuse
- Result: Pooling makes performance WORSE (tested: 677.5 vs 959.5 rec/min, -29% regression)

**Configuration:**

```bash
# Default (pooling disabled) - RECOMMENDED for SQLExpress
python production_processor.py \
  --server "localhost\SQLEXPRESS" \
  --database "XmlConversionDB" \
  --workers 4 \
  --batch-size 1000 \
  --log-level INFO
```

**Performance Characteristics:**
- Baseline: 950-1000 rec/min
- Variance: ±10-15% (small dataset, local disk variability)
- Bottleneck: Disk I/O (CPU <10%, RAM <300MB)
- Recommendation: Focus on I/O optimization, not connection pooling

**Diagnostic Commands:**

```bash
# Verify pooling is disabled
python debug_connection_string.py

# Expected output: "Pooling=False"

# Establish baseline
python performance_tuning/test_modules/establish_baseline.py
# Expected: ~950 rec/min median throughput
```

**When to enable pooling on SQLExpress:**
- Only if testing Dev/Prod configurations locally (for comparison)
- Use `--enable-pooling` flag if needed
- Not recommended for actual local development

---

## SQL Server Dev

**What it is:** SQL Server (full edition) on network, typical team development setup.

**Why pooling helps:**
- Network latency to SQL Server makes connection reuse valuable
- Each new connection requires network round-trip + TCP handshake (~50-100ms)
- Pooling reuses connections, eliminating this overhead
- Result: Pooling helps significantly (typically +20-40% improvement)

**Configuration:**

```bash
# Dev environment - pooling enabled with moderate pool size
python production_processor.py \
  --server "dev-sql-server\instance" \
  --database "YourDatabase" \
  --workers 8 \
  --batch-size 1000 \
  --log-level INFO \
  --enable-pooling \
  --min-pool-size 8 \
  --max-pool-size 40
```

**Pool Size Tuning:**
- **Min Pool Size:** Match number of workers (if using 8 workers, set to 8)
- **Max Pool Size:** 3-5x workers for burst capacity (8 workers → 40 max)
- Start conservative, increase if you see pool exhaustion warnings

**Performance Characteristics:**
- Baseline: 1500-2000 rec/min (2-3x SQLExpress)
- Variance: ±5-10% (better hardware, network stability)
- Bottleneck: Network latency (if slow) or database CPU (if fast network)
- Recommendation: Tuning depends on network speed and server resources

**Diagnostic Commands:**

```bash
# Verify pooling configuration
python debug_connection_string.py
# Expected output: "Pooling=True" with pool size settings

# Establish baseline for comparison
python performance_tuning/test_modules/establish_baseline.py

# Test different pool sizes
python performance_tuning/test_modules/batch_size_optimizer.py \
  --sizes 1000,2000
```

**Troubleshooting:**

If performance is poor despite pooling:
1. Check network latency: `ping dev-sql-server`
2. Check SQL Server CPU/memory during run
3. May need to increase max pool size
4. Check for blocking queries in SQL Server

---

## SQL Server Production

**What it is:** Dedicated SQL Server, high-performance environment, large-scale processing.

**Why pooling is essential:**
- Production environments typically have:
  - High concurrency (multiple clients, batch jobs)
  - Network distance to database
  - Dedicated server resources
  - Large connection pools allow resource reuse
- Pooling reduces connection overhead dramatically (>50% improvement)

**Configuration:**

```bash
# Production environment - maximum pool size for performance
python production_processor.py \
  --server "prod-sql-server.company.com" \
  --database "ProductionDB" \
  --workers 16 \
  --batch-size 1000 \
  --log-level WARNING \
  --enable-pooling \
  --min-pool-size 16 \
  --max-pool-size 64 \
  --connection-timeout 60
```

**Pool Size Tuning for Production:**
- **Min Pool Size:** Number of workers (16 workers → 16 min)
- **Max Pool Size:** 3-5x workers for high concurrency (16 workers → 64 max)
- **Connection Timeout:** Increase to 60 seconds (more lenient for production)
- Monitor for "connection pool exhausted" errors; adjust max size if needed

**Performance Characteristics:**
- Baseline: 3000-5000+ rec/min (3-5x SQL Server Dev)
- Variance: ±2-5% (production hardware stability)
- Bottleneck: Database query optimization (if CPU runs high)
- Recommendation: Monitor query execution and indexes

**Diagnostic Commands:**

```bash
# Verify production configuration
python debug_connection_string.py
# Should show: "Pooling=True" with large pool sizes

# Baseline with production settings
python performance_tuning/test_modules/establish_baseline.py

# Compare different batch sizes
python performance_tuning/test_modules/batch_size_optimizer.py \
  --sizes 500,1000,2000,5000

# Generate test data at production scale
python performance_tuning/test_modules/generate_mock_xml.py \
  --count 10000
```

**Production Best Practices:**

1. **Monitor during deployment:**
   - Watch SQL Server resource usage (CPU, RAM, I/O)
   - Check application logs for connection errors
   - Measure actual throughput vs baseline

2. **Scale pool size with concurrency:**
   - Each worker needs a connection
   - Add 20-30% buffer for safety
   - Example: 20 workers → 20-24 min, 60-100 max

3. **Connection timeout strategy:**
   - Set to at least 2x expected initial connection time
   - Longer timeout = better for high-load scenarios
   - 60 seconds is safe default for production

4. **Monitor and adjust:**
   - Track "Connection Pool Exhausted" errors
   - Increase max pool size if seen
   - May eventually hit SQL Server connection limits

---

## Migration Guide: Dev → Prod

### Phase 1: Validate on SQL Server Dev

1. Deploy code to dev environment
2. Run baseline with dev pooling settings:
   ```bash
   python production_processor.py \
     --server "dev-sql-server" \
     --database "DevDB" \
     --workers 8 \
     --enable-pooling \
     --min-pool-size 8 \
     --max-pool-size 40
   ```
3. Compare to baseline_metrics.json (should see improvement)

### Phase 2: Scale to Production

1. Update connection string to production server
2. Increase pool size for higher concurrency:
   ```bash
   python production_processor.py \
     --server "prod-sql-server" \
     --database "ProdDB" \
     --workers 16 \
     --enable-pooling \
     --min-pool-size 16 \
     --max-pool-size 64
   ```
3. Run limited baseline to verify: `--limit 1000`
4. Monitor for 30+ minutes of production load
5. Scale to full dataset

### Phase 3: Production Operations

- Monitor baseline metrics daily (track in dashboard)
- If throughput drops >10%, investigate:
  - SQL Server CPU/IO
  - Network latency
  - Connection pool exhaustion
  - Query performance changes
- Adjust pool size based on observed metrics

---

## Switching Between Environments

### SQLExpress → SQL Server Dev

```bash
# Before (SQLExpress)
python production_processor.py --server "localhost\SQLEXPRESS" ...

# After (SQL Server Dev with pooling)
python production_processor.py \
  --server "dev-sql-server" \
  --database "DevDB" \
  --enable-pooling \
  --min-pool-size 8 \
  --max-pool-size 40
```

Expected performance improvement: 2-3x (950 → 1500-2000 rec/min)

### SQL Server Dev → Production

```bash
# Before (Dev)
python production_processor.py --server "dev-sql-server" \
  --enable-pooling \
  --min-pool-size 8 \
  --max-pool-size 40

# After (Production)
python production_processor.py --server "prod-sql-server" \
  --enable-pooling \
  --min-pool-size 16 \
  --max-pool-size 64 \
  --workers 16
```

Expected performance improvement: 1.5-2x (1500 → 3000+ rec/min)

---

## Architecture Note: Why Connection Pooling Works

### SQLExpress (Doesn't help)
```
Worker 1 → New Connection (10-20ms overhead)
Worker 2 → New Connection (10-20ms overhead)  ← Overhead > Benefit
Worker 3 → New Connection (10-20ms overhead)
Worker 4 → New Connection (10-20ms overhead)
```

Problem: Local I/O wait >> connection overhead, so overhead is just waste.

### SQL Server Dev/Prod (Helps significantly)
```
Worker 1 → Pool Connection (reuse, 1-2ms)
Worker 2 → Pool Connection (reuse, 1-2ms)   ← Saves 50-100ms each!
Worker 3 → Pool Connection (reuse, 1-2ms)
Worker 4 → Pool Connection (reuse, 1-2ms)

If new connection: 100-150ms (TCP + handshake + SQL Server init)
Reused from pool:  1-2ms (already connected, state preserved)
Savings:          98-148ms per connection reuse
```

Benefit: Network latency eliminated through connection reuse.

---

## Troubleshooting

### "Performance is slow on SQL Server Dev (with pooling enabled)"

1. Verify pooling is actually enabled:
   ```bash
   python debug_connection_string.py
   # Check for "Pooling=True" in output
   ```

2. Check network latency:
   ```bash
   ping dev-sql-server  # Should be <50ms for good perf
   ```

3. Check SQL Server CPU/memory during run
   - If CPU at 100%, SQL Server is bottleneck (not connections)
   - If memory high, may need to adjust batch size

4. Try without pooling to compare:
   ```bash
   python production_processor.py ... --enable-pooling=False
   ```

### "Connection pool exhausted" error

1. Increase max pool size:
   ```bash
   --max-pool-size 80  # Or higher
   ```

2. Check how many workers you're running
   - Min pool should >= workers
   - Max pool should be 3-5x workers

3. Monitor for connection leaks in application code

### "Performance dropped after migration to production"

1. Verify pooling is enabled:
   ```bash
   python debug_connection_string.py
   ```

2. Compare pool sizes to expected:
   - Min should match workers
   - Max should be 3-5x workers

3. Check production SQL Server health:
   - CPU usage
   - Memory usage
   - I/O wait times

4. Verify batch size is still optimal (may differ on production hardware)
   ```bash
   python performance_tuning/test_modules/batch_size_optimizer.py
   ```

---

## References

- See `performance_tuning/test_modules/README.md` for diagnostic commands
- See `performance_tuning/phase_2_investigation/` for pooling analysis details
- See `performance_tuning/README.md` for complete performance tuning guide
