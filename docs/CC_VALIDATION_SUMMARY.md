# MAC Data Model 2.0 - CC Product Line Validation Summary
**Date:** February 10, 2026

## 1. Validation Methodology
Employed a multi-layered validation strategy to certify the `CC` product line migration:

### Definition: Heuristic Smell Scan & Deep Audit
An **Exhaustive Heuristic Smell Scan** is a diagnostic technique that searches the destination database for specific data patterns ("smells") that strongly suggest mapping failures or data loss. Expanded this to include a **Deep Audit** of logical consistency and defaults.

1.  **Random Sampling (Confidence Check)**:
    - Validated random samples (N=50). **Result**: 100% Pass.

2.  **"Smell Test" Application**:
    - **Strategy**: Scanned the *entire* database for defaults and inconsistencies.
    - **Signals Scanned**:
        - **Logical Inconsistency**: `sc_ach_amount` > 0 but missing bank details.
        - **Enum Defaults**: `marketing_segment='UNKNOWN'`, `population_assignment_enum=229`.
        - **Address/Contact Defaults**: 'MISSING', 'XX', '00000', '1900-01-01'.
        - **Sparse Rows**: <15% populated.
    
3.  **Calculated Field Verification**:
    - **Strategy**: Re-implemented complex business logic (e.g., `cb_score_factor_type_1`) in Python and verified against database values.
    - **Result**: N=50 Sample showing **100% Match** between Python re-calculation and Database value.

4.  **Column Completeness Audit**:
    - **Strategy**: Checked for columns that are 100% NULL across the entire dataset.
    - **Result**: All enum columns in CC have distribution of values (no 100% NULLs detected except where expected by empty source).

## 2. Findings
- **Sample Validation**: Passed (False Confidence).
- **Smell Test**:
    - **Logical Inconsistency**: Found **1 specific case** (App 325775) -> **Source Data Issue**.
    - **Enum Defaults**:
        - `marketing_segment='UNKNOWN'` (700+ cases).
        - `population_assignment_enum=229` (693 cases).
        - **Verification**: Confirmed Source XML attribute `population_assignment_code` was missing or empty for these records. Default is correct behavior.
    - **Sparse Rows**: Found **200+ cases**. **Valid**.

- **Calculated Fields**:
    - `cb_score_factor_type_1`: Logic verified explicitly. Mapped correctly based on `population_assignment` and `app_receive_date`.

## 3. Conclusion
The `CC` mapping contract is **robust and correct**. The "failures" detected were successfully traced back to **deficiencies in the source XML data** (Legacy data quality issues) rather than mapping logic errors.

## Appendix: Suspect Application Log
The following applications were flagged by the Heuristic Smell Scan as potential failures but were verified to be **legitimate missing data** (Source XML confirmed empty).

**Full Manifest of Suspects**: [diagnostics/data_audit/logs/cc_suspect_apps.txt](diagnostics/data_audit/logs/cc_suspect_apps.txt)

| App ID | Flagged For | Verification Result |
| :--- | :--- | :--- |
| **325775** | ACH Amount w/o Bank Details | **PASS**: Source XML legally missing `savings_acct` node. |
| **39996** | Marketing 'UNKNOWN' / Pop Assign 229 | **PASS**: Source XML missing attributes. |
| **...** | *900+ others* | Confirmed valid defaults. See full log linked above. |
