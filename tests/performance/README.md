# DataMapper Performance Regression Testing

This directory contains comprehensive performance testing infrastructure for validating DataMapper performance before, during, and after refactors.

MOST TESTS ARE INTENTIONALLY SKIPPED FOR NOW UNTIL IMPLEMENTED
- Need better XML data integration to work properly

## 🎯 Purpose

The performance regression tests ensure that:
- **Throughput** remains above 1,400 records/minute baseline
- **Memory usage** doesn't increase significantly during refactoring  
- **Processing times** stay within acceptable ranges
- **Cache effectiveness** is maintained across code changes
- **Scalability** characteristics remain stable

## 📁 Files Overview

```
tests/performance/
├── test_datamapper_performance_regression.py  # Main test suite
├── run_performance_tests.py                   # Python test runner
├── run_performance.ps1                        # Windows PowerShell runner
├── performance_config.json                    # Configuration & thresholds
└── README.md                                  # This file

performance_results/                           # Generated during tests
├── performance_baseline.json                  # Saved baseline metrics
└── performance_history.json                   # Historical test results
```

## 🚀 Quick Start

### 1. Establish Performance Baseline (Before Refactoring)
```powershell
# Windows PowerShell
cd tests/performance
.\run_performance.ps1 baseline

# Or using Python directly
python run_performance_tests.py --save-baseline
```

### 2. Run Performance Tests (During/After Refactoring)
```powershell
# Check for performance regression
.\run_performance.ps1 compare

# Run full test suite
.\run_performance.ps1 run -Verbose

# OR using pytest directly
pytest tests/performance/ -m slow -v  # Run full performance suite
```

### 3. Validate Infrastructure Only
```powershell
# Test that performance testing infrastructure is ready
pytest tests/performance/ -v  # Runs infrastructure test, skips slow tests

# Run specific infrastructure test
pytest tests/performance/test_datamapper_performance_regression.py::TestDataMapperPerformanceRegression::test_performance_infrastructure_ready -v
```

### 4. Integration with Main Test Suite
```powershell
# Performance tests are automatically excluded from main test suite
pytest tests/ -q  # Runs all tests except performance tests

# Include performance tests explicitly
pytest tests/ -m "slow or not slow" -v  # Run everything including performance tests
```

## 📊 Test Suite Components

### Core Performance Tests

1. **`test_baseline_throughput_performance`**
   - Measures records/minute processing rate
   - Validates against 1,400 rec/min minimum threshold
   - Establishes baseline for regression comparison

2. **`test_memory_usage_stability`**  
   - Detects memory leaks across multiple processing batches
   - Validates stable memory usage patterns
   - Tests garbage collection effectiveness

3. **`test_cache_effectiveness`**
   - Validates enum type cache and regex cache performance
   - Measures cold vs warm cache processing times
   - Ensures optimization mechanisms remain effective

4. **`test_performance_under_load`**
   - Tests various batch sizes (100, 500, 1000, 2000 records)
   - Validates scalability characteristics  
   - Identifies performance bottlenecks

5. **`test_regression_comparison`**
   - Compares current performance against saved baseline
   - Fails if throughput, memory, or timing regression detected
   - Provides detailed performance delta analysis

### Performance Metrics Captured

- **Throughput**: Records processed per minute
- **Response Time**: Average and 95th percentile processing times
- **Memory Usage**: Peak memory consumption and growth trends
- **Cache Performance**: Hit rates and speedup measurements
- **Transformation Stats**: Detailed breakdown of mapping operations

## ⚙️ Configuration

### Performance Thresholds (`performance_config.json`)
```json
{
  "performance_thresholds": {
    "baseline_throughput_min": 1400,        # Minimum acceptable throughput
    "max_memory_increase_percent": 10,      # Allow 10% memory increase
    "max_processing_time_increase_percent": 15,  # Allow 15% time increase
    "min_cache_speedup_percent": 5          # Cache must provide 5%+ speedup
  }
}
```

### Test Configuration
- **Batch Sizes**: 50 (warmup), 500 (standard), up to 2000 (load testing)
- **Memory Monitoring**: 5 iterations for leak detection
- **Cache Testing**: Cold vs warm performance comparison

## 🔧 Integration with Refactoring Workflow

### Phase 1: Pre-Refactoring Baseline
```powershell
# Establish baseline before any code changes
.\run_performance.ps1 baseline
```

### Phase 2: During Refactoring Validation
```powershell
# After each component extraction
pytest test_datamapper_performance_regression.py::TestDataMapperPerformanceRegression::test_regression_comparison -v

# Full validation
.\run_performance.ps1 compare
```

### Phase 3: Post-Refactoring Verification  
```powershell
# Comprehensive performance validation
.\run_performance.ps1 run -Verbose

# Update baseline if performance improved
.\run_performance.ps1 baseline  # Only if performance is better
```

## 📈 Understanding Test Output

### Successful Test Output
```
BASELINE PERFORMANCE MEASUREMENT
============================================================
Warmup: PerformanceMetrics(throughput=1450.2 rec/min, memory=45.3MB, avg_time=1.8ms)
Throughput: 1523.4 records/minute
Processing Time: avg=1.65ms, p95=3.2ms
Memory Usage: 48.2MB (peak: +12.5MB)
Transformation Stats: {'enum_mappings': 1247, 'type_conversions': 2843}
✅ Baseline performance test PASSED
```

### Performance Regression Detection
```
PERFORMANCE REGRESSION CHECK
============================================================
Throughput change: -8.5%  ❌ REGRESSION DETECTED
Processing time change: +22.3%  ❌ REGRESSION DETECTED  
Memory usage change: +5.1%  ✅ Within tolerance
❌ Performance regression test FAILED
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```powershell
   # Ensure Python environment is configured
   python -c "from xml_extractor.mapping.data_mapper import DataMapper; print('OK')"
   ```

2. **Missing Dependencies**
   ```powershell
   pip install psutil pytest
   ```

3. **Performance Test Failures**
   - Check system load during testing
   - Ensure no other resource-intensive processes running
   - Verify test data generation is working correctly

4. **Memory Monitoring Issues**
   ```python
   # Test psutil functionality
   import psutil, os
   process = psutil.Process(os.getpid())
   print(f"Memory: {process.memory_info().rss / 1024 / 1024:.1f}MB")
   ```

### Performance Debugging

1. **Profile Specific Components**
   ```python
   # Add to test for detailed profiling
   import cProfile
   cProfile.run('data_mapper.apply_mapping_contract(xml_data, contract)')
   ```

2. **Memory Leak Investigation**
   ```python
   # Monitor object counts
   import gc
   gc.collect()
   print(f"Objects: {len(gc.get_objects())}")
   ```

## 🔄 CI/CD Integration

The performance tests are designed to integrate with continuous integration:

### GitHub Actions Example
```yaml
- name: Performance Regression Test
  run: |
    cd tests/performance
    python run_performance_tests.py --compare-only
  continue-on-error: false  # Fail build on performance regression
```

### Local Development Workflow
```powershell
# Before committing refactored code
.\run_performance.ps1 compare

# Only commit if performance tests pass
git add . && git commit -m "Refactor: Extract EnumMapper component"
```

## 📚 Related Documentation

- **[TESTING_GAPS_ANALYSIS.md](../docs/TESTING_GAPS_ANALYSIS.md)** - Testing infrastructure requirements  
- **[FINAL_PERFORMANCE_SUMMARY.md](../../performance_tuning/FINAL_PERFORMANCE_SUMMARY.md)** - Current performance characteristics

## 🎯 Success Criteria

Performance tests should **PASS** with:
- ✅ Throughput ≥ 1,400 records/minute
- ✅ Memory increase ≤ 10%  
- ✅ Processing time increase ≤ 15%
- ✅ Cache speedup ≥ 5%
- ✅ No memory leaks detected
- ✅ Stable performance across load scenarios

**Ready for refactors when all performance tests consistently pass! 🚀**