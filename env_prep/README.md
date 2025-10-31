# Environment Preparation Scripts

This folder contains scripts for setting up and preparing the development/test environment.

## Available Scripts

### `generate_mock_xml.py`
**Purpose**: Generate mock XML data with unique app_ids for testing

**Features**:
- ✅ Generates valid Provenir XML records
- ✅ Each record has unique app_id and con_ids
- ✅ SET IDENTITY_INSERT ON/OFF for explicit ID insertion
- ✅ Supports multiple dataset sizes: 50, 200, 500, or custom
- ✅ Safe duplicate handling (skips if app_id already exists)

**Usage**:
```bash
python generate_mock_xml.py
```

**Interactive Menu**:
```
1. Small (50 records) - Quick testing
2. Medium (200 records) - Batch size testing
3. Large (500 records) - Phase II benchmarking
4. Custom size
```

**What It Does**:
1. Checks current app_xml record count
2. Prompts for dataset size
3. Generates mock XMLs with unique IDs
4. Enables IDENTITY_INSERT ON
5. Inserts records into app_xml table
6. Disables IDENTITY_INSERT OFF
7. Reports success/failure

**Key Changes from Original**:
- ✅ Path fixed: `Path(__file__).parent.parent` (was `Path(__file__).parent`)
- ✅ IDENTITY_INSERT ON enabled before inserts
- ✅ IDENTITY_INSERT OFF disabled after inserts
- ✅ Allows explicit app_id insertion without auto-increment conflicts

### `establish_baseline.py`
**Purpose**: Establish performance baseline by running production_processor multiple times

**Features**:
- ✅ Runs production_processor 10 times with clean database between runs
- ✅ Measures throughput (records/minute) for each iteration
- ✅ Calculates median, mean, std dev, min, max
- ✅ Clears app_base and processing_log tables between runs
- ✅ Saves results to `baseline_metrics.json`
- ✅ No interference from accumulated data

**Usage**:
```bash
python establish_baseline.py
```

**What It Does**:
1. Prepares test dataset (750 records)
2. Clears database
3. Runs production_processor 10 times
4. Clears database between each run
5. Records throughput for each iteration
6. Calculates statistics
7. Saves results to baseline_metrics.json

**Output Example**:
```
Throughput Statistics (records/minute):
  Median:     959.5
  Mean:       941.2
  Std Dev:    114.3
  Min:        653.5
  Max:        1047.6
```

**Configuration**:
- Records: 750
- Workers: 4
- Batch Size: 1000
- Iterations: 10
- Connection Pooling: Disabled (default)

**Output File**:
- `baseline_metrics.json` - Performance baseline metrics

---

## Usage in Phase II

### Phase II.1 (Batch Size Optimization)
1. Run `generate_mock_xml.py` (select size 3: 500 records)
2. Run `establish_baseline.py` to get baseline
3. Use `/performance_tuning/test_modules/batch_size_optimizer.py` to test different batch sizes

### Phase II.2 (Connection Pooling)
1. Keep 750 records from Phase II.1
2. Run `establish_baseline.py` with pooling disabled (default)
3. Run with `--enable-pooling` flag to compare
4. Compare metrics

### Regular Development
1. Use `generate_mock_xml.py` to set up test data
2. Use `establish_baseline.py` to verify performance after code changes
3. Reference `baseline_metrics.json` as baseline for comparisons

---

## Output Files

- `baseline_metrics.json` - Performance statistics from establish_baseline.py

---

## Integration with Performance Tuning

These scripts work with performance_tuning folder:
- Setup test data with `generate_mock_xml.py` here
- Run baseline with `establish_baseline.py` here
- Use `/performance_tuning/test_modules/batch_size_optimizer.py` for detailed testing
- Use `/performance_tuning/benchmarks/` for advanced benchmarking

See `/performance_tuning/README.md` for complete performance tuning guide.

This script is essential for Phase II.1 (Batch Size Optimization):

```bash
# 1. Generate test data
python env_prep/generate_mock_xml.py
# Select: 3 (500 records)

# 2. Test different batch sizes
# For each batch size: run establish_baseline.py
# Before each run: database is automatically cleared by establish_baseline.py

# 3. Find optimal batch size
# Results recorded in baseline_metrics.json
```

---

## How IDENTITY_INSERT Works

**Why it's needed**:
- By default, SQL Server auto-increments app_id
- We want to use specific app_ids for testing
- IDENTITY_INSERT allows explicit ID insertion

**Process**:
1. `SET IDENTITY_INSERT app_xml ON` - Allow explicit IDs
2. Insert records with specific app_ids
3. `SET IDENTITY_INSERT app_xml OFF` - Re-enable auto-increment

**Important**: Always disable IDENTITY_INSERT when done to prevent conflicts with future auto-incremented inserts.

---

## Other Scripts

See `/env_prep/` for other environment preparation scripts that may be added.

---

**Note**: This script should be run from the env_prep directory or with python env_prep/generate_mock_xml.py from the project root.
