# Performance Test Modules

Reusable test and diagnostic scripts for establishing baselines, testing optimizations, and troubleshooting performance issues.

## Available Modules

### `establish_baseline.py`
**Purpose:** Establish performance baseline by running production processor multiple times

**Usage:**
```bash
python establish_baseline.py
```

**What it does:**
- Runs production_processor.py 10 times with clean database between runs
- Clears app_base and processing_log tables between iterations
- Measures throughput (records/minute) for each run
- Calculates statistics: median, mean, std dev, min, max
- Saves results to baseline_metrics.json

**Output:**
```
Throughput Statistics (records/minute):
  Median:     959.5
  Mean:       941.2
  Std Dev:    114.3
  Min:        653.5
  Max:        1047.6
```

**Configuration:**
- **Records:** 750 (full dataset generated)
- **Workers:** 4
- **Batch Size:** 1000
- **Iterations:** 10
- **Clean DB:** Between each run

**When to use:**
- Establishing baseline on new environment
- After major code changes
- Before/after optimization to measure impact
- Validating performance in Dev/Prod

---

### `generate_mock_xml.py`
**Purpose:** Generate realistic test XML data for performance testing

**Usage:**
```bash
python generate_mock_xml.py [--count 700]
```

**What it does:**
- Generates N random XML records with realistic structure
- Inserts into app_xml table
- Creates associated contact, address, employment records
- Each record includes 1-3 contacts with addresses and employment
- Formats XML exactly like production data

**Options:**
- `--count` (default: 700) - Number of records to generate
- `--connection-string` (optional) - Override database connection

**Output:**
```
Generated 700 mock XML records and inserted into database
Total records in app_xml: 750 (50 original + 700 generated)
```

**When to use:**
- Building test datasets
- Setting up new environment with sample data
- Performance testing with varying dataset sizes
- Creating reproducible test scenarios

---

### `debug_connection_string.py`
**Purpose:** Verify and display the database connection string being used

**Usage:**
```bash
python debug_connection_string.py
```

**What it does:**
- Creates ProductionProcessor instance
- Displays exact connection string
- Parses and shows each component
- Verifies pooling parameters are present (if enabled)

**Output:**
```
ACTUAL CONNECTION STRING BEING USED:
DRIVER={ODBC Driver 17 for SQL Server};
SERVER=localhost\SQLEXPRESS;
DATABASE=XmlConversionDB;
Connection Timeout=30;
Trusted_Connection=yes;
TrustServerCertificate=yes;
Encrypt=no;
MultipleActiveResultSets=True;
Pooling=True;
Min Pool Size=4;
Max Pool Size=20;

POOLING STATUS:
✅ Connection pooling is ENABLED
✅ MARS is ENABLED
✅ Min Pool Size set to 4
✅ Max Pool Size set to 20
```

**When to use:**
- Verifying pooling configuration
- Troubleshooting connection issues
- Validating environment-specific settings
- Before/after connection string changes

---

### `batch_size_optimizer.py`
**Purpose:** Test different batch sizes to find optimal performance

**Usage:**
```bash
python batch_size_optimizer.py [--sizes 50,100,200,500,1000,2000]
```

**What it does:**
- Tests multiple batch sizes
- Runs establish_baseline for each size (3 iterations)
- Measures throughput
- Compares to baseline
- Identifies optimal batch size

**Options:**
- `--sizes` (default: 50,100,200,500,1000,2000) - Batch sizes to test
- `--iterations` (default: 3) - Iterations per batch size

**Output:**
```
Batch Size = 50:   Mean 553.8 rec/min (Baseline)
Batch Size = 100:  Mean 787.0 rec/min (+42% improvement)
Batch Size = 200:  Mean 955.2 rec/min (+72% improvement)
Batch Size = 500:  Mean 845.2 rec/min (+52% improvement)
Batch Size = 1000: Mean 901.8 rec/min (+63% improvement) ← OPTIMAL
Batch Size = 2000: Mean 697.9 rec/min (+26% improvement)

RECOMMENDATION: Use batch size 1000
```

**When to use:**
- Testing on new environment to find optimal batch size
- After database changes that affect query performance
- Validating Phase II.1 results on different machines
- Production tuning

---

## Test Module Workflow

### Scenario 1: Setting Up New Environment
1. **Generate test data:** `python generate_mock_xml.py`
2. **Establish baseline:** `python establish_baseline.py`
3. **Verify configuration:** `python debug_connection_string.py`
4. **Document results:** Save baseline_metrics.json
5. **Optional - Optimize batch size:** `python batch_size_optimizer.py`

### Scenario 2: Troubleshooting Performance Issues
1. **Check connection:** `python debug_connection_string.py`
2. **Establish fresh baseline:** `python establish_baseline.py`
3. **Compare to expected:** See phase_2_investigation/
4. **Run diagnostics:** See phase_2_investigation/POOLING_TEST_PLAN.md
5. **Document findings:** Add to phase_2_investigation/

### Scenario 3: Testing New Optimization
1. **Establish baseline before:** `python establish_baseline.py` → baseline_before.json
2. **Apply optimization:** Edit code, run tests
3. **Establish baseline after:** `python establish_baseline.py` → baseline_after.json
4. **Compare:** Calculate % improvement
5. **Document:** Add to appropriate phase folder

---

## Configuration Files

### baseline_metrics.json (Output)
Generated by `establish_baseline.py`

```json
{
  "median": 959.5,
  "mean": 941.2,
  "std_dev": 114.3,
  "min": 653.5,
  "max": 1047.6,
  "samples": 10,
  "dataset_size": 750,
  "workers": 4,
  "batch_size": 1000,
  "timestamp": "2025-10-30T17:00:00"
}
```

---

## Environment-Specific Notes

### SQLExpress (Local Development)
- **Recommended Baseline:** 950-1000 rec/min
- **Key Setting:** Connection pooling = FALSE
- **Batch Size:** 1000 (from Phase II.1)
- **Workers:** 4 (match CPU cores)
- **Expected variance:** ±10-15% between runs (small dataset, local disk)

### SQL Server Dev
- **Recommended Baseline:** 1500-2000 rec/min
- **Key Setting:** Connection pooling = TRUE
- **Batch Size:** 1000 (validate with optimizer)
- **Workers:** 8 (if available)
- **Expected variance:** ±5-10% (better hardware, network stable)

### SQL Server Production
- **Recommended Baseline:** 3000-5000+ rec/min
- **Key Setting:** Connection pooling = TRUE, Min=16, Max=64
- **Batch Size:** Test with optimizer
- **Workers:** 16+ (or 2x CPU cores)
- **Expected variance:** ±2-5% (production hardware stable)

---

## Troubleshooting

### "Baseline is much slower than expected"
1. Run `debug_connection_string.py` - verify pooling settings
2. Check SQL Server CPU/memory during run (should not be 100%)
3. Check database size (is it 750 records as expected?)
4. See phase_2_investigation/POOLING_TEST_PLAN.md for diagnostics

### "Baseline varies widely (>15% std dev)"
1. Close other applications (may be competing for resources)
2. Check disk health (slow disk = high variance)
3. SQLExpress may be running in parallel (check task manager)
4. Try running with fewer workers to isolate

### "Connection string shows unexpected values"
1. Run `debug_connection_string.py`
2. Compare to expected output in phase_2_investigation/
3. Check if environment variables are overriding defaults
4. See environment_setup/ for env-specific guidance

---

## Integration with Performance Investigation

These test modules are designed to work with the investigation documents:

- **establish_baseline.py** ↔ phase_2_investigation/PHASE2_RESULTS.md
- **batch_size_optimizer.py** ↔ phase_2_investigation/ (Phase II.1 results)
- **debug_connection_string.py** ↔ phase_2_investigation/ (Phase II.2 investigation)
- **generate_mock_xml.py** ↔ phase_2_investigation/ (test data generation)

See phase_2_investigation/README.md for cross-references.

---

## Location and Setup

All modules are located here in `test_modules/`. They can be run from the root project directory:

```bash
cd /path/to/XmlConversionKiro/MB_XmlConversionKiro
python performance_tuning/test_modules/establish_baseline.py
```

Or from the test_modules directory:

```bash
cd /path/to/XmlConversionKiro/MB_XmlConversionKiro/performance_tuning/test_modules
python establish_baseline.py
```
