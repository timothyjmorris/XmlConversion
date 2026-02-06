# Diagnostics Tools

Post-processing analysis and troubleshooting utilities for production runs.

## Failure Analysis

### summarize_failures.py

Consolidate and analyze failed applications from production metrics files.

```powershell
# Analyze latest metrics file
python diagnostics/summarize_failures.py

# Analyze all metrics from a specific session (useful for parallel runs)
python diagnostics/summarize_failures.py --session 20260206_001448

# Analyze specific metrics file
python diagnostics/summarize_failures.py --metrics-file metrics/metrics_20260206_001448.json

# Export failures to CSV for further analysis
python diagnostics/summarize_failures.py --session 20260206_001448 --csv failures.csv
```

**Output:**
- Total failed applications count
- Breakdown by error stage (validation, parsing, mapping, constraint_violation, etc.)
- Detailed list of failed app_ids with error messages
- Optional CSV export with full details

---

### find_unprocessed_apps.py

Identify applications that exist in staging table but were never processed (not in `processing_log`).

```powershell
# Find all unprocessed apps
python diagnostics/find_unprocessed_apps.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB"

# With app_id range filter
python diagnostics/find_unprocessed_apps.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --app-id-start 1 --app-id-end 50000

# Save to file
python diagnostics/find_unprocessed_apps.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --output unprocessed.txt

# For production database with SQL auth
python diagnostics/find_unprocessed_apps.py --server "prod-server" --database "ProdDB" --username "user" --password "pass" --target-schema "migration"
```

**Use Cases:**
- Verify all staging apps were attempted
- Find apps silently skipped due to empty XML or other pre-processing filters
- Gap analysis after parallel runs

---

## Performance Analysis

### resource_profiler.py

Profile CPU, memory, and I/O during processing runs (existing tool).

### check_metrics.py

Quick metrics validation (existing tool).

---

## Common Workflow

**After a production run:**

1. **Check for failures:**
   ```powershell
   python diagnostics/summarize_failures.py --session <session_id>
   ```

2. **Find any unprocessed apps:**
   ```powershell
   python diagnostics/find_unprocessed_apps.py --server <server> --database <database>
   ```

3. **Export failures for deeper analysis:**
   ```powershell
   python diagnostics/summarize_failures.py --session <session_id> --csv failures.csv
   ```

4. **Investigate specific failures in database:**
   ```sql
   SELECT * FROM migration.processing_log WHERE app_id IN (<failed_ids>);
   ```
