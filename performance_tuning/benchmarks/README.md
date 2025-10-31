# Performance Benchmarking Scripts

Useful benchmarking scripts for measuring performance under different conditions and configurations.

## Available Scripts

### `benchmark_current_state.py`
**Purpose:** Establish a baseline by running production_processor and measuring current performance.

**Usage:**
```bash
python benchmark_current_state.py
```

**Output:**
- Runs production_processor once
- Measures throughput (records/minute)
- Reports timing and performance metrics
- Useful for quick performance checks

**When to use:**
- Before/after optimization comparison
- Quick performance sanity check
- Comparing different configurations

### `benchmark_parallel.py`
**Purpose:** Performance debugging for parallel processing - measure impact of different worker counts.

**Usage:**
```bash
python benchmark_parallel.py
```

**Output:**
- Tests different worker counts
- Measures throughput for each configuration
- Shows scaling efficiency
- Identifies performance plateau

**When to use:**
- Determining optimal worker count for your environment
- Understanding parallelization limits
- Debugging performance issues with parallelization

### `benchmark_logging_impact.py`
**Purpose:** Measure the performance impact of logging overhead.

**Usage:**
```bash
python benchmark_logging_impact.py
```

**Output:**
- Tests with different logging levels
- Compares throughput with/without logging
- Shows logging overhead as percentage

**When to use:**
- Tuning production log level
- Understanding logging impact on performance
- Production readiness validation

## Integration with Test Modules

These benchmarks work with the test modules in `../test_modules/`:
- `establish_baseline.py` - More comprehensive baseline (multiple iterations)
- `batch_size_optimizer.py` - Optimize batch size
- `debug_connection_string.py` - Verify connection configuration

## Recommended Workflow

1. **Quick check:** Run `benchmark_current_state.py`
2. **Detailed baseline:** Run `../test_modules/establish_baseline.py`
3. **Optimize workers:** Run `benchmark_parallel.py`
4. **Check logging:** Run `benchmark_logging_impact.py`
5. **Production ready:** Compare against baseline_metrics.json

## Output Files

These scripts may create:
- `benchmark_results.json` - Results from benchmarking
- `logs/` - Benchmark run logs
- `metrics/` - Performance metrics

## Notes

- All benchmarks use production_processor.py with current configuration
- Results depend on system resources (CPU, memory, disk, network)
- Close other applications for accurate measurements
- Run multiple times for reliable averages

See `../README.md` for overall performance tuning strategy.
