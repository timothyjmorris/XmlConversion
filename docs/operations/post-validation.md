# Post Validation (KV Mapping Coverage)

This runbook organizes the **post-validation** checks that confirm key/value (KV) “row-creating” mapping types are behaving correctly end-to-end.

Scope: the four KV mapping types that create rows (not single-column updates):
- `add_score(<identifier>)` → `[target_schema].scores`
- `add_indicator(<name>)` → `[target_schema].indicators`
- `add_history` → `[target_schema].app_historical_lookup`
- `add_report_lookup(<source_report_key?>)` → `[target_schema].app_report_results_lookup`

## 1) Contract + Mapper regression (no DB writes)

Runs a contract-driven regression that checks that for a known fixture XML, the mapper produces the expected KV records.

```powershell
python -m pytest tests/contracts/test_post_validation_kv_mapper_semantics.py -v
```

## 2) Manual E2E insert + verification (DB writes)

Runs the CC manual end-to-end test that performs an actual insert and then verifies destination KV tables.

```powershell
python tests/e2e/manual_test_pipeline_full_integration_cc.py
```

Optional: force a specific app_id to avoid collisions with existing test data:

```powershell
$env:XMLCONVERSION_E2E_APP_ID = "443306"
python tests/e2e/manual_test_pipeline_full_integration_cc.py
```

## 3) Reconcile contract ↔ XML ↔ mapper ↔ destination (DB reads only)

Reconciles expectations against the destination tables and emits a JSON report under `metrics/`.

- Reconcile a local XML fixture:

```powershell
python diagnostics/reconcile_kv_mappings.py --xml-file config/samples/sample-source-xml-contact-test.xml
```

- Reconcile a specific app_id (fetches source XML from DB based on contract `source_table`/`source_column`):

```powershell
python diagnostics/reconcile_kv_mappings.py --app-id 443306
```

## 4) Backfill missing KV rows (insert-only; no deletes, no DDL)

If mappings changed after an app was already processed, you may want to backfill only the missing KV rows.

Dry-run (recommended first):

```powershell
python diagnostics/backfill_kv_rows.py --app-id 443306
```

Apply (performs INSERTs only for missing rows):

```powershell
python diagnostics/backfill_kv_rows.py --app-id 443306 --apply
```

Outputs a JSON report under `metrics/` with what would be inserted / was inserted.
