# MAC Data Model 2.0 - RL Product Line Validation Summary
**Date:** February 10, 2026

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
    - **Finding**: `app_operational_rl.priority_enum` contains **0 populated rows**. This warrants investigation (likely missing in Source).

## 2. Findings
- **Date Format Issue**: Found **43 applications** where `birth_date` was default `1900-01-01` but Source XML had `DD/MM/YYYY`. **Fixed**.
- **Collateral Defaults**: Found **84 applications** with default `collateral_type_enum=423`. Verified source data was missing specific collateral type tags.
- **Priority Enum**: Source `priority_enum` is missing in all 10k processed records.

## 3. Fixes Implemented
- **DataMapper Upgrade**: Updated `xml_extractor/mapping/data_mapper.py` to support `DD/MM/YYYY` formats.
- **Precedence Logic**: ISO -> US -> Intl (`DD/MM/YYYY`).

## 4. Calculated Field Verification
To ensure complex transformation logic (conditional `CASE` statements) is executed correctly during migration, performed a logic-based audit on specific calculated fields.

### Audit Target: `cb_score_factor_type_pr_1`
- **Logic Rule**: 
  - `IF Vantage4P_decline_code1 IS NOT EMPTY AND app_entry_date > '2020-01-01'` -> Return `'V4'`
  - `ELSE` -> Return mapped code value.
- **Verification Method**: Re-implemented the logic in Python (`diagnostics/data_audit/verify_calculated_fields_rl.py`) and compared the Python-calculated result against the value actually persisted in the database for 50 random records.
- **Result**: **50/50 Passed** (100% Logic Match).

## Appendix: Suspect Application Log
The following applications were flagged by the Heuristic Smell Scan as potential failures but were verified to be **legitimate missing data** or **mapping correct** (after fixes).

**Full Manifest of Suspects**: [diagnostics/data_audit/logs/rl_suspect_apps.txt](diagnostics/data_audit/logs/rl_suspect_apps.txt)

| App ID | Flagged For | Verification Result |
| :--- | :--- | :--- |
| **262279** | `birth_date='1900-01-01'` | **FIXED**: Source had `DD/MM/YYYY`. DataMapper updated. |
| **123926** | `collateral_type_enum=423` | **PASS**: Source XML missing collateral type attribute. |
| **...** | *100+ others* | Confirmed valid defaults or date format fix applied. |
