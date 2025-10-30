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
cd env_prep
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

---

## Usage in Phase II

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
