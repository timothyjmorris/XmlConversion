# Diagnostics Tools

Post-processing analysis, data auditing, and troubleshooting utilities.

## Directory Structure

```
diagnostics/
├── data_audit/                    # Data validation & reconciliation tools
│   ├── CC_VALIDATION_SUMMARY.md   # CC product line validation report
│   ├── RL_VALIDATION_SUMMARY.md   # RL product line validation report
│   ├── logs/                      # Suspect app_id manifests
│   └── archive/                   # Completed investigation scripts
├── archive/                       # Archived debug scripts (kept for reference)
├── README.md                      # This file
└── *.py / *.sql                   # Active diagnostic tools
```

## Failure Analysis

### summarize_failures.py

Consolidate and analyze failed applications from production metrics files.

```powershell
# Analyze latest metrics file
python diagnostics/summarize_failures.py

# Analyze all metrics from a specific session (useful for parallel runs)
python diagnostics/summarize_failures.py --session 20260206_001448

# Export failures to CSV for further analysis
python diagnostics/summarize_failures.py --session 20260206_001448 --csv failures.csv
```

### find_unprocessed_apps.py

Identify applications that exist in staging table but were never processed (not in `processing_log`).

```powershell
# Find all unprocessed apps
python diagnostics/find_unprocessed_apps.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB"

# With app_id range filter and file export
python diagnostics/find_unprocessed_apps.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --app-id-start 1 --app-id-end 50000 --output unprocessed.txt
```

---

## Data Auditing (diagnostics/data_audit/)

### reconcile_kv_source_first.py ⭐

**Best-in-class audit tool.** Source-first reconciliation for KV tables (scores, collateral). Starts from XML source data and works forward to detect coverage gaps, missing rows, and value mismatches.

```powershell
python diagnostics/data_audit/reconcile_kv_source_first.py --server "..." --database "..." --schema migration
```

### audit_kv_tables_rl.py

Comprehensive KV table audit: scores, collateral, warranties, policy exceptions. Compares XML attribute presence with DB row existence.

```powershell
python diagnostics/data_audit/audit_kv_tables_rl.py --server "..." --database "..." --schema migration --sample 50
```

### trace_score_pipeline.py

Step-through diagnostic: trace a single app_id through the full pipeline (XML → Parser → Mapper → output) showing exactly what happens to score data at each stage.

```powershell
python diagnostics/data_audit/trace_score_pipeline.py --app-id 325725 --server "..." --database "..."
```

### verify_calculated_fields.py / verify_calculated_fields_rl.py

Re-implement CASE/WHEN logic in Python and compare results against database values. Used to certify calculated field transformations.

### gap_analysis_rl.py

Processing gap analysis: total source population vs processed count, session breakdown, score coverage cross-check.

### generate_suspect_logs.py

Heuristic smell scan: flags apps with suspicious patterns (default enums, epoch dates, sparse rows) and generates suspect app_id manifests.

### audit_enums_and_defaults.py / audit_missing_kv_data.py

Enum distribution analysis and KV data completeness checks.

---

## Contract & Mapping Verification

### audit_contract_targets.py

Validates that `mapping_type` functions (`add_score`, `add_indicator`, etc.) target the correct tables in both CC and RL contracts.

```powershell
python diagnostics/audit_contract_targets.py
```

### list_mapping_types.py

Scans both mapping contracts and lists all `mapping_type` values (raw and normalized). Useful for auditing mapping type coverage.

### check_enums.py

Comprehensive enum column inspector: correlates contract enum maps with DB values and source XML.

```powershell
python diagnostics/check_enums.py --server "..." --database "..." --column population_assignment_enum
```

### reconcile_kv_mappings.py

Full reconciliation of KV mappings: contract ↔ XML ↔ mapper ↔ destination. Generates JSON report.

---

## Operational Tools

### clean_apps.py

Delete all migrated data for given app_ids across all target tables (parameterized). Used for re-processing cleanup.

```powershell
python diagnostics/clean_apps.py --server "..." --database "..." --schema migration --app-ids "325725,325726"
```

### backfill_kv_rows.py

Insert-only backfill of missing KV rows (scores, indicators, history) for a given app_id. Dry-run by default.

### check_app_history.py

Show processing_log history for an app_id.

### dump_kv_data.py

Dump all KV table rows for an app_id across scores, collateral, warranties, policy exceptions, indicators, and historical lookup.

### inspect_mapped_app.py

Fetch app XML, run parser + mapper, and inspect the mapped output for a specific app.

### list_suspect_apps.py

Scan migrated data for suspect apps (address defaults, sparse rows, etc.).

---

## Performance & Monitoring

### resource_profiler.py

Monitor CPU, memory, disk, and DB performance during processing runs. Threaded sampling with configurable intervals.

### validate_source_to_dest.py

Full source-to-destination reconciliation for CC product line. Parameterized with validation report output.

---

## SQL Validation

### cc_data_validation.sql

Comprehensive CC data quality validation queries: column population, enum distribution, sparse rows, adjacent mismatches.

---

## Common Workflow

**After a production run:**

1. **Check for failures:**
   ```powershell
   python diagnostics/summarize_failures.py --session <session_id>
   ```

2. **Find unprocessed apps:**
   ```powershell
   python diagnostics/find_unprocessed_apps.py --server <server> --database <database>
   ```

3. **Run source-first reconciliation:**
   ```powershell
   python diagnostics/data_audit/reconcile_kv_source_first.py --server <server> --database <database>
   ```

4. **Export failures for deeper analysis:**
   ```powershell
   python diagnostics/summarize_failures.py --session <session_id> --csv failures.csv
   ```
