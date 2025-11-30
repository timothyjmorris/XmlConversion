# Stage app_XML Runbook

This runbook describes how to run the `appxml_staging_extractor.py` pre-processor (Stage `app_XML`), scale it for production-sized runs, and safely execute a multi-worker load to stage ~11M rows into `dbo.app_xml_staging` in under 18 hours.

Place: `env_prep/appxml_staging_extractor.py`

---

## Overview

- Purpose: extract `/Provenir/Request/CustData` from the large `app_XML` payloads and store reduced rows in `dbo.app_xml_staging` so the main pipeline processes much smaller payloads.
- Script: `appxml_staging_extractor.py` — supports batching, partitioned workers (`--mod`/`--rem`), optional index drop/recreate, and metrics output. The script reconstructs a minimal full `app_XML` payload and stores it in the staging `app_XML` column so the main pipeline can process it directly.

## Prerequisites

- Python 3.8+ on the worker host.
- Required Python packages: `lxml`, `pyodbc`.
  - Install with:
    ```powershell
    pip install -r requirements.txt
    ```
- ODBC driver for SQL Server: `ODBC Driver 17 for SQL Server` (configured in `config/database_config.json`).
- Database credentials and `config/database_config.json` present and pointing to the target SQL Server.
- Ensure `config/mapping_contract.json` contains `source_table` and `source_column` (defaults used are `app_xml` and `app_XML`).

## Staging table

The runbook and script create (if missing) a staging table:

```sql
CREATE TABLE dbo.app_xml_staging (
  app_id INT NOT NULL PRIMARY KEY,
  app_XML NVARCHAR(MAX) NULL,
  extracted_at DATETIME2 NOT NULL DEFAULT (SYSUTCDATETIME())
);
CREATE INDEX IX_app_xml_staging_app_id ON dbo.app_xml_staging (app_id);
```

Use the `--drop-index` option on the initial load to drop `IX_app_xml_staging_app_id` (if present), and `--recreate-index` after the load to recreate it.

## Quick smoke tests

- Small real run (single worker):
```powershell
python .\env_prep\appxml_staging_extractor.py --batch 500 --limit 10000 --drop-index --metrics metrics\appxml_w0.json
```

## Parallel worker orchestration (PowerShell example)

This example launches N workers partitioned by `app_id % N` (each worker writes `app_XML` into the staging table).

```powershell
$workers = 8
$batch = 1000

# Create directories for logs + metrics
New-Item -ItemType Directory -Path .\logs -Force
New-Item -ItemType Directory -Path .\metrics -Force

for ($i=0; $i -lt $workers; $i++) {
  $args = "env_prep\appxml_staging_extractor.py --batch $batch --mod $workers --rem $i --metrics metrics\appxml_$i.json"
  # Let only worker 0 drop the index
  if ($i -eq 0) { $args += " --drop-index" }
  Start-Process -FilePath python -ArgumentList $args -RedirectStandardOutput ".\logs\appxml_$i.out" -RedirectStandardError ".\logs\appxml_$i.err" -NoNewWindow
}

# After all workers finish, run a recreation step (single-shot):
python .\env_prep\appxml_staging_extractor.py --batch 1 --recreate-index
```

Notes:
- Adjust `$workers` depending on DB capacity. Start small (2), validate, then ramp (4, 8, 12).
- `--drop-index` should be used once at start; `--recreate-index` once at end.

## Suggested scaling parameters (initial plan)

- Observed baseline in DEV: ~13k rows in 320s → ~40 rows/sec per worker `--batch 500`.
- Target overall throughput for <18 hours: ~170 rows/sec total.
- Suggested starting configuration: **8 workers**, `--batch 1000`. Best-case completion ≈ 11.5 hours.
- If DB can scale, consider 12 workers for ~7.7 hours (expect diminishing returns).

## DB-side guidance (coordinate with DBA)

- Consider setting the database recovery model to `SIMPLE` or `BULK_LOGGED` for the load window to reduce transaction log growth and speed inserts.
- Monitor transaction log size and disk space; large bulk loads can spike log growth.
- If inserting into a table with indexes, dropping nonessential indexes before the load and recreating them afterwards often yields significant speedups.
- Consider running the staging table on fast storage (separate log device) or temporarily increasing I/O priority.

## Monitoring and validation

- Each worker writes an optional metrics JSON (use `--metrics metrics/appxml_worker_X.json`). The JSON contains `processed`, `duration_s`, `rows_per_sec` and `finished_at`.
- Tail stdout logs for per-batch progress:
```powershell
Get-Content .\logs\appxml_0.out -Wait
```
- Check metrics after workers finish:
```powershell
Get-Content .\metrics\appxml_0.json | ConvertFrom-Json
```
- Verify row counts in staging:
```sql
SELECT COUNT(*) FROM dbo.app_xml_staging;
```

## Safety checklist before a full run

- Run a small real load (small `--limit`) to validate parsing and inserts.
- Confirm there is enough disk space for transaction logs and the staging table.
- Verify backups and maintenance windows; coordinate to avoid interference.
- Validate a single partition run (e.g., mod=8 rem=0) to confirm expected throughput.

## Troubleshooting

- If inserts are very slow, reduce batch size, or temporarily pause workers and re-run a single-worker test.
- If you see many `custdata_xml` missing, check source data distribution; the script will skip rows without `CustData`.
- If ODBC errors appear, check `config/database_config.json` and ensure the ODBC driver is installed.

---

## Orchestrator: `appxml_staging_orchestrator.py`

I added `env_prep/appxml_staging_orchestrator.py` to simplify launching and monitoring multiple workers. It:

- Creates `logs/` and `metrics/` directories (if missing).
- Launches N workers with `--mod N` and `--rem <0..N-1>` so each worker processes a disjoint partition.
- Optionally sets `--drop-index` on worker 0 to drop the staging index before the load.
- Waits for all workers to finish and aggregates per-worker metrics into `metrics/appxml_aggregate.json`.
- Optionally runs a final `--recreate-index` single invocation to rebuild the index.

Usage example:

```powershell
python .\env_prep\appxml_staging_orchestrator.py --workers 8 --batch 2000 --drop-index --recreate-index
```

Advanced: pass additional worker args after `--` to forward them to each worker. Example:

```powershell
python .\env_prep\appxml_staging_orchestrator.py --workers 8 --batch 2000 --drop-index -- --limit 1375000
```

The orchestrator will write per-worker metrics to `metrics/appxml_<rem>.json` and an aggregate summary to `metrics/appxml_aggregate.json`.
