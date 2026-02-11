# MAC Data Model 2.0 - CC Product Line Validation Summary

**Date:** February 10, 2026  
**Last Updated:** February 10, 2026  
**Status:** ✅ Certified  
**Population:** ~12,240 applications (dbo.app_xml_staging)

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

- **Sample Validation**: Passed (False Confidence — motivated deeper smell scan).
- **Smell Test**:
    - **Logical Inconsistency**: Found **1 specific case** (App 325775) → **Source Data Issue** (XML legally missing `savings_acct` node).
    - **Enum Defaults**:
        - `marketing_segment='UNKNOWN'` (700+ cases).
        - `population_assignment_enum=229` (693 cases).
        - **Verification**: Confirmed Source XML attribute `population_assignment_code` was missing or empty for these records. Default is correct behavior.
    - **Sparse Rows**: Found **200+ cases**. **Valid** — source data is legitimately sparse.

- **Calculated Fields**:
    - `cb_score_factor_type_1`: Logic verified explicitly. Mapped correctly based on `population_assignment` and `app_receive_date`.

## 3. Bugs Fixed During CC Validation (Phase 0.5)

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `authu_contact` filtering | PreProcessingValidator not passing AUTHU contacts | Updated contact role filtering |
| `sc_bank_account_type_num` empty | Missing enum mapping in contract | Added `sc_bank_account_type_enum` mapping |
| Lock contention (serialization) | RangeS-U locks on duplicate detection | Added `WITH (NOLOCK)` to all detection queries |
| Resume logic incomplete | Only excluded `status='success'` | Now excludes both `success` AND `failed` |
| Pagination skipping records | OFFSET-based pagination | Switched to cursor-based (`app_id > last_app_id`) |

## 4. Conclusion

The `CC` mapping contract is **robust and correct**. The "failures" detected were successfully traced back to **deficiencies in the source XML data** (legacy data quality issues) rather than mapping logic errors.

## 5. Validation Tools Used

| Tool | Purpose |
|------|---------|
| `diagnostics/data_audit/generate_suspect_logs.py` | Smell scan: flagged suspect app_ids |
| `diagnostics/data_audit/verify_calculated_fields.py` | Re-implemented CASE logic, compared with DB |
| `diagnostics/validate_source_to_dest.py` | Full source-to-destination reconciliation |
| `diagnostics/cc_data_validation.sql` | Comprehensive SQL validation queries |

## Appendix: Suspect Application Log

The following applications were flagged by the Heuristic Smell Scan as potential failures but were verified to be **legitimate missing data** (Source XML confirmed empty).

**Full Manifest**: [logs/cc_suspect_apps.txt](logs/cc_suspect_apps.txt)

| App ID | Flagged For | Verification Result |
|:-------|:------------|:--------------------|
| **325775** | ACH Amount w/o Bank Details | **PASS**: Source XML legally missing `savings_acct` node. |
| **39996** | Marketing 'UNKNOWN' / Pop Assign 229 | **PASS**: Source XML missing attributes. |
| **...** | *900+ others* | Confirmed valid defaults. See full log linked above. |
