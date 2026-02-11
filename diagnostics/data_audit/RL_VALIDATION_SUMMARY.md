# MAC Data Model 2.0 - RL Product Line Validation Summary

**Date:** February 10, 2026  
**Last Updated:** February 10, 2026  
**Status:** 🔄 In Progress (Phase 5 — 791 apps processed, full validation pending)  
**Population:** 791 applications (dbo.app_xml_staging_rl)

## 1. Validation Methodology

Employed a multi-layered validation strategy to certify the `RL` product line migration:

### Definition: Heuristic Smell Scan & Deep Audit
An **Exhaustive Heuristic Smell Scan** is a diagnostic technique that searches the destination database for specific data patterns ("smells") that strongly suggest mapping failures or data loss.

1.  **Random Sampling (Confidence Check)**:
    - Validated random samples (N=20, N=50). **Result**: 100% Pass.

2.  **"Smell Test" Application**:
    - **Signals Scanned**:
        - `collateral_type_enum` = 423 (Default).
        - `birth_date = '1900-01-01'` (Default Epoch).
        - 100% NULL columns.

3.  **Column Completeness Audit**:
    - **Strategy**: Checked for columns that are 100% NULL across the entire dataset.
    - **Finding**: `app_operational_rl.priority_enum` contains **0 populated rows**. Confirmed: source XML attribute missing across entire population.

4.  **Source-First KV Reconciliation**:
    - **Strategy**: Started from XML SOURCE, extracted expected score/collateral/warranty rows, compared with DB.
    - **Tool**: `reconcile_kv_source_first.py` — the most comprehensive audit tool in the suite.
    - **Result**: 0 missing scores, 0 value mismatches for all processed apps.

5.  **Score Pipeline Deep Trace**:
    - **Strategy**: Traced specific app_ids through the full pipeline (XMLParser → DataMapper → MigrationEngine) to verify score routing.
    - **Result**: All 6 score types (CRI_pr, CRI_sec, MRV_pr, MRV_sec, V4P, V4S) verified correct.

## 2. Findings

- **Date Format Issue**: Found **43 applications** where `birth_date` was default `1900-01-01` but Source XML had `DD/MM/YYYY`. **Fixed**.
- **Collateral Defaults**: Found **84 applications** with default `collateral_type_enum=423`. Verified source data was missing specific collateral type tags.
- **Priority Enum**: Source `priority_enum` is missing across entire population — legitimate source gap.
- **Score Routing**: All 96 V4P scores correctly routed. 53 positive values + 43 zeros. 0 missing from DB.
- **Contact Silent Drop**: 4 apps affected — 1 con_id collision (source data issue), 3 sparse contacts filtered by `_is_meaningful_contact()` (by-design behavior).

## 3. Bugs Fixed During RL Validation

| Bug | Root Cause | Fix | Severity |
|-----|-----------|-----|----------|
| V4P/V4S `target_table` mismatch | Contract pointed at `app_historical_lookup` instead of `scores` | Updated `mapping_contract_rl.json` | Critical |
| `MigrationEngine` schema routing | Constructor loaded default CC contract, ignoring RL contract | Added `mapping_contract_path` parameter to `MigrationEngine.__init__()` | Critical |
| E2E test stale assertions | V4P/V4S assertions checked wrong table (`app_historical_lookup`) | Updated `_verify_scores()` and `_verify_historical_lookup()` | Important |
| `birth_date` DD/MM/YYYY | DataMapper didn't support international date format | Added precedence: ISO → US → Intl | Important |
| Scores `int` conversion | 6 RL score mappings had wrong `data_type` | Corrected to `int` in contract | Important |
| `DATEADD()` expression error | Expression engine didn't support date arithmetic | Implemented ~140-line DATEADD function | Important |

## 4. Calculated Field Verification

### Audit Target: `cb_score_factor_type_pr_1`
- **Logic Rule**:
  - `IF Vantage4P_decline_code1 IS NOT EMPTY AND app_entry_date > '2020-01-01'` → Return `'V4'`
  - `ELSE` → Return mapped code value.
- **Verification Method**: Re-implemented the logic in Python (`verify_calculated_fields_rl.py`) and compared against database values for 50 random records.
- **Result**: **50/50 Passed** (100% Logic Match).

## 5. Processing Summary

| Metric | Value |
|--------|-------|
| Total source apps | 791 |
| Successfully processed | 790 |
| Failed | 1 (app 325318 — CC app misrouted to RL staging) |
| Success rate | 99.87% |
| Score rows created | 96 V4P + 96 V4S + 787 CRI_pr + 787 MRV_pr |
| Contact rows created | 786 (4 apps with no contacts — see §2) |
| Tables populated | 16 RL-specific + shared (scores, app_historical_lookup, indicators) |

## 6. Known Limitations

| Issue | Impact | Resolution |
|-------|--------|------------|
| `priority_enum` 100% NULL | Column unpopulated | Source XML doesn't contain attribute — legitimate gap |
| 4 apps missing contacts | 3 sparse, 1 con_id collision | By-design: `_is_meaningful_contact()` filters sparse contacts; con_id collision is source data issue |
| 1 failed app (325318) | CC app in RL staging table | Source data issue — misrouted at staging time |

## 7. Validation Tools Used

| Tool | Purpose |
|------|---------|
| `reconcile_kv_source_first.py` | Source-first reconciliation: coverage, completeness, accuracy |
| `trace_score_pipeline.py` | Step-through single-app pipeline trace |
| `verify_calculated_fields_rl.py` | Re-implemented CASE logic, compared with DB |
| `audit_kv_tables_rl.py` | KV table completeness audit (scores, collateral, warranties, policy exceptions) |
| `gap_analysis_rl.py` | Processing gap analysis: source vs processed |
| `generate_suspect_logs.py` | Smell scan: flagged suspect app_ids |
| `audit_contract_targets.py` | Contract integrity: mapping_type → target_table consistency |

## Appendix: Suspect Application Log

The following applications were flagged by the Heuristic Smell Scan as potential failures but were verified to be **legitimate missing data** or **mapping correct** (after fixes).

**Full Manifest**: [logs/rl_suspect_apps.txt](logs/rl_suspect_apps.txt)

| App ID | Flagged For | Verification Result |
|:-------|:------------|:--------------------|
| **262279** | `birth_date='1900-01-01'` | **FIXED**: Source had `DD/MM/YYYY`. DataMapper updated. |
| **123926** | `collateral_type_enum=423` | **PASS**: Source XML missing collateral type attribute. |
| **325722** | Missing contacts | **PASS**: con_id collision with app 325725 (source data issue). |
| **326242-326244** | Missing contacts | **PASS**: Sparse contacts filtered by `_is_meaningful_contact()`. |
| **...** | *100+ others* | Confirmed valid defaults or date format fix applied. |
