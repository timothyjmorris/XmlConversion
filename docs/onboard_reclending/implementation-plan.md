# RecLending Implementation Plan

**Status**: Active Working Document  
**Created**: 2026-02-05  
**Last Updated**: 2026-02-06

## Overview

This plan guides the onboarding of the RecLending (IL) product line to the XML Database Extraction System. It follows a phased approach prioritizing "DO NO HARM" to existing CreditCard functionality while incrementally adding shared and RL-specific capabilities.

### Resources

| Resource | Location | Purpose |
|----------|----------|---------|
| DDL Script | [create_destination_tables_rl.sql](../../config/samples/create_destination_tables_rl.sql) | Authoritative table definitions |
| DML Script | [migrate_table_logic_rl.sql](../../config/samples/migrate_table_logic_rl.sql) | Enum derivation logic, transformation patterns |
| CSV Seed | [xml-source-to-database-contract-rl.csv](xml-source-to-database-contract-rl.csv) | Initial mapping data (500 rows) for contract creation |
| Sample XML | [config/samples/xml_files/reclending/](../../config/samples/xml_files/reclending/) | 15 RL sample files |
| Requirements | [setup.md](setup.md) | Domain requirements and background |

## Guiding Principles

1. **DO NO HARM** - No changes to CC functionality without explicit decision
2. **Verify new features** - Test-first development with acceptance criteria
3. **Small batches** - Incremental delivery in phases
4. **Contract-driven** - All transformations defined in mapping contracts, not code
5. **Evidence-based** - Prove correctness through data validation, not assumptions

## Key Technical Decisions

| Decision | Resolution |
|----------|------------|
| Composite PK tables | `table_insertion_order` in contract handles sequencing; `app_id` uniqueness enforced upstream |
| ELSE clause behavior | Omit ELSE for NULL; CC fields use `ELSE ''` (no change needed) |
| Y/N enum columns | Derive common `char_to_bit` mapping from `migrate_table_logic_rl.sql` |
| Upsert for scores/indicators | Update existing on constraint violation |
| `code_to_email_enum` | Dual-use: direct enum lookup + chained fallback for `check_requested_by_user` |
| Schema isolation | `migration` for dev, `dbo` for production (contract-driven) |
| CSV file | Seed for contract creation, archive after use |

---

## Phase 0: Stabilization Baseline

**Goal**: Establish verified baseline before any changes  
**Status**: ✅ COMPLETE (2026-02-06)

### Tasks
- [x] Run full test suite - 100% pass required → **214 passed, 0 failed**
- [ ] **BLOCKER**: Fix `env_prep/appxml_staging_orchestrator.py` - currently not working, needed for environment setup
- [x] Run `production_processor.py` with manual smoke validation
- [x] Capture baseline performance metrics
- [x] Document any failing tests with root cause → `authu_contact` added to supported_types
- [x] Verify AUTHU mapping end-to-end (XML → mapper → DB)
- [x] Fix contract/schema mismatch alignment and visibility
- [x] Ensure commit-time tests enforce pass/fail correctly

### Acceptance Criteria
- All tests pass ✅
- Production processor completes without errors
- Performance baseline documented

---

## Phase 0.5: CC Data Validation (SQL Patterns)

**Goal**: Validate existing CC data migration quality, uncover bugs that benefit the whole application

### Validation Categories

#### 1. Unpopulated Columns Analysis
Identify columns with 0% population that should have data.

```sql
-- Pattern: Find columns that are entirely NULL across all rows
-- May indicate mapping gaps or source data issues
```

#### 2. Adjacent Data Mismatches
Detect value/enum pairs where one is populated and the other is NULL.

**Example discovered**: `sc_ach_amount` has value, `sc_bank_account_type_enum` is NULL

```sql
-- Pattern: amount/value columns with data but adjacent enum/type is NULL
-- Examples:
--   sc_ach_amount has value, sc_bank_account_type_enum is NULL
--   payment_amount has value, payment_type_enum is NULL
```

#### 3. Enum Without Associated Value
Inverse pattern - enum populated but value field empty.

```sql
-- Pattern: enum/type populated but associated value is NULL/0
-- May indicate incorrect mapping or partial data
```

#### 4. Sparse Row Detection
Rows with >80% NULL columns in tables like `app_pricing_cc` - may indicate incomplete applications.

```sql
-- Pattern: rows where most columns are NULL
-- Especially in pricing, operational tables
-- May indicate failed processing or edge case data
```

#### 5. Expected Enum Coverage
NULL enums where sibling data suggests they should have values.

```sql
-- Pattern: NULL enums where related non-enum fields have data
-- Cross-reference with mapping_contract to identify expected defaults
```

### Known Bugs to Fix

| Bug | Description | Impact | Status |
|-----|-------------|--------|--------|
| `authu_contact` not implemented | ~~Mapping type `["char_to_bit", "authu_contact"]` extracts from PR contact, not AUTHU contact~~ | `auth_user_issue_card_flag` in `app_operational_cc` may be incorrect | **FIXED** |
| `use_alloy_service_flag` contract mismatch | Contract marked column nullable/optional while DB is NOT NULL | Contract/schema validation failed | **FIXED** |
| Contract/schema mismatch visibility | Failures only written to diff file; unclear in console | Slows triage | **FIXED** |
| Test suite exit code | Suite returned non-zero when E2E had zero tests | Pre-commit blocked commits | **FIXED** |
| `sc_bank_account_type_num` mapping missing | Enum not populated when `sc_ach_amount` has value | Data quality gap in `app_operational_cc` | **FIXED** |

#### Bug Fix: `authu_contact` Mapping Type (2025-02-06)

**Problem**: The `authu_contact` mapping type was defined in the contract but not implemented in DataMapper. It fell through to the "unknown mapping type" handler and applied standard data type transformation, extracting from the wrong contact.

**Solution**: 
1. Added handler in `_apply_single_mapping_type()` for `authu_contact`
2. Created `_extract_from_authu_contact()` method that extracts from the second contact type in `valid_contact_types` array (AUTHU)
3. Uses contract-defined contact type attribute (`ac_role_tp_c`) instead of hardcoded attribute

**Files Modified**:
- `xml_extractor/mapping/data_mapper.py` - Added `authu_contact` handler and `_extract_from_authu_contact()` method

**Tests Added**:
- `tests/unit/test_authu_contact_mapping.py` - 4 test cases covering extraction scenarios

**Test Baseline After Fix**: 214 passed, 0 failed

### Deliverables
- [x] SQL validation scripts in `diagnostics/` folder → `diagnostics/cc_data_validation.sql`
- [x] Python utility for source-to-destination comparison → `diagnostics/validate_source_to_dest.py`
- [x] Batch failure summarization outputs JSON from latest metrics batch
- [x] Pre-commit test enforcement added (blocks commits on critical test failures)
- [x] Fixes applied and regression tests added
- [x] `authu_contact` mapping type implemented or field removed from contract
- [ ] Bug list with severity and fix recommendations (no open bugs at present; keep as periodic audit)

### Acceptance Criteria
- All validation categories have working queries ✅
- Known anomalies documented with explanations (none currently open)
- Critical bugs fixed before Phase 1

### CC Data Validation Tracking List

| Item | Validation Tool | Status | Notes |
|------|------------------|--------|-------|
| AUTHU issue_card_ind → auth_user_issue_card_flag | `diagnostics/validate_source_to_dest.py` + targeted DB checks | ✅ Verified | Confirmed in `migration` schema data |
| sc_bank_account_type_enum populated | `diagnostics/validate_source_to_dest.py` (adjacent mismatch check) | ✅ Verified | Confirmed populated in data |
| Missing enum/value pairs | `diagnostics/cc_data_validation.sql` | ✅ Clean | No open anomalies reported |
| Sparse rows (>80% NULL) | `diagnostics/cc_data_validation.sql` | ✅ Clean | No open anomalies reported |

---

## Phase 1: Shared Functionality

**Goal**: Add mapping types that benefit both CC and RL product lines

### 1.1 `add_score(identifier)` Mapping Type

**Contract syntax**:
```json
{
    "source_field": "TU_TIE_score",
    "mapping_type": "add_score(TU_TIE)",
    "destination_table": "scores"
}

```

**Implementation requirements**:
- Insert to `scores` table with `score_identifier`
- **Upsert** on constraint violation (update existing) ✅ (handled in bulk insert fallback)
- Handle integer coercion (0 allowed, empty disallowed) ✅ (decimal strings rounded to int)

### 1.2 `add_indicator(name)` Mapping Type

**Contract syntax**:
```json
{
    "source_field": "intrnl_fraud_ssn_ind",
    "mapping_type": "add_indicator(InternalFraudSSN)",
    "destination_table": "indicators"
}
```

**Implementation requirements**:
- Insert to `indicators` table
- Only insert when value='Y' → value='1'
- **Upsert** on constraint violation ✅ (handled in bulk insert fallback)

### 1.3 `add_history` Mapping Type

**Contract syntax**:
```json
{
    "source_field": "old_deprecated_field",
    "mapping_type": "add_history",
    "destination_table": "app_historical_lookup"
}
```

**Implementation requirements**:
- Insert to `app_historical_lookup` table
- Derive `name` from XML attribute name wrapped in `[]`
- Derive `source` from rightmost path segment wrapped in `[]`
- Only insert if value non-empty

### 1.4 `add_report_lookup` Mapping Type

**Contract syntax**:
```json
{
    "source_field": "InstantID_Score",
    "mapping_type": "add_report_lookup",
    "destination_table": "app_report_results_lookup"
}
```

**Implementation requirements**:
- Insert to `app_report_results_lookup` table
- Derive `name` from XML attribute name
- Only insert if value non-empty
- Support `source_report_key` when needed (e.g., InstantID = `IDV`) ✅ via `add_report_lookup(<key>)`

### Deliverables
- [x] DataMapper handlers for each mapping type
    - Implemented in `DataMapper._extract_kv_table_records()` and helpers
- [x] Unit tests covering KV mapping semantics (mapper-only)
    - `tests/unit/test_shared_kv_mapping_types.py`
    - `tests/contracts/test_post_validation_kv_mapper_semantics.py` (contract regression)
- [x] Unit tests covering upsert-on-duplicate behavior
    - `tests/unit/test_kv_upsert_behavior.py` (BulkInsertStrategy update-on-duplicate)
- [x] Integration-level coverage with real XML fixtures
    - Manual E2E insert + verify: `tests/e2e/manual_test_pipeline_full_integration_cc.py`
    - DB-read reconciliation: `diagnostics/reconcile_kv_mappings.py`
- [x] Update `docs/mapping/datamapper-functions.md`

### Acceptance Criteria
- All new mapping types have unit + regression coverage ✅ (see tests above)
- CC regression tests still pass ✅ (full suite green)
- Performance within 5% of baseline (not re-measured; changes are localized and bulk insert remains fast-path-first)

**Phase 1 Status**: ✅ COMPLETE (2026-02-06)

**Performance Baseline** (2026-02-07):
- **2,700 apps/min** (pyodbc fast_executemany-optimized, 6 workers, 1000 batch size)
- Acceptable for production; ~2.5 days to process 11MM records
- Lower than target 3,000 app/min but stable and resilient
- Room for incremental optimization in Phase 3+ if needed

---

## Phase 2: CLI & Contract Infrastructure

**Goal**: Support multiple product lines via CLI and contracts  
**Status**: 🔄 IN PROGRESS (started 2026-02-07)

### 2.1 Product Line CLI Support

```powershell
# Proposed CLI syntax:
python production_processor.py --product-line RL --server "..." --database "..."
python production_processor.py --product-line CC --server "..." --database "..."  # Default
```

**Implementation tasks**:
- Add `--product-line` argument to `production_processor.py`
- Add `--product-line` argument to `xml_extractor/cli.py`
- Map: `CC` → `mapping_contract.json`, `RL` → `mapping_contract_rl.json`

### 2.2 Create `mapping_contract_rl.json`

**Workflow**:
```
CSV Seed (500 rows)
    ↓
Parse & validate against DDL
    ↓
Generate mapping_contract_rl.json
    ↓
Run schema validation tests
    ↓
Reconcile mismatches
    ↓
Archive CSV to docs/onboard_reclending/archived/
```

**Key tables from DDL**:

| Table | PK Type | Column Count | Notes |
|-------|---------|--------------|-------|
| `app_operational_rl` | Simple | ~60 | Score factors, analysts |
| `app_pricing_rl` | Simple | ~20 | Loan amounts, DTI |
| `app_funding_rl` | Simple | ~30 | Boarding, LoanPro IDs |
| `app_funding_checklist_rl` | Simple | ~50 | ~30 enum columns (Y/N pattern) |
| `app_funding_contract_rl` | Simple | ~40 | APR, fees, note details |
| `app_warranties_rl` | **Composite** | 7 | PK: (app_id, warranty_type_enum) |
| `app_policy_exceptions_rl` | **Composite** | 4 | PK: (app_id, policy_exception_type_enum) |
| `app_collateral_rl` | **Composite** | 16 | PK: (app_id, collateral_type_enum, sort_order) |
| `app_dealer_rl` | Simple | ~22 | Dealer snapshot |
| `app_transactional_rl` | Simple | ~11 | Temp processing data |

### 2.3 Contract Schema Validation

- Create `tests/contracts/test_mapping_contract_schema_rl.py`
- Validate all RL tables and columns against DDL
- Mirror structure of existing `test_mapping_contract_schema.py`

### Deliverables
- [ ] CLI `--product-line` argument implemented
- [ ] `config/mapping_contract_rl.json` created and validated
- [ ] Contract schema tests passing
- [ ] CSV archived to `docs/onboard_reclending/archived/`

### Acceptance Criteria
- CLI correctly routes to product-specific contracts
- Contract validates against DDL with 0 mismatches
- CC functionality unchanged

**Phase 2 Status**: 🔄 IN PROGRESS (2026-02-07)

---

## Phase 3: RL-Specific Mapping Types

**Goal**: Implement complex RL transformation patterns

### 3.1 `policy_exceptions(enum)` Mapping Type

**Contract syntax**:
```json
{
    "source_field": "override_capacity",
    "mapping_type": "policy_exceptions(630)",
    "notes_field": "capacity_exception_notes",
    "fallback_notes_field": "override_type_code_notes"
}
```

**Implementation requirements**:
- COALESCE logic for notes (specific notes → fallback notes)
- Handle multiple reason_codes with same notes
- Insert to `app_policy_exceptions_rl` with composite PK

### 3.2 `warranty_field(enum)` Mapping Type

**Pattern**: 5-field set per warranty type

```json
{
    "mapping_type": "warranty_field(623)",
    "field_pattern": "gap"
}
```

**Derives**: `gap_amount`, `gap_company`, `gap_policy`, `gap_term`, `gap_lien`

**Implementation requirements**:
- Handle `term_months` default (0 if empty)
- Handle `merrick_lienholder_flag` conversion ('Y' → 1, else 0)
- Insert to `app_warranties_rl` with composite PK

### 3.3 `contact_type_to_field` Mapping Type

**Purpose**: Route PR/SEC contact values to different columns

```json
{
    "source_field": "residence_monthly_pymnt",
    "mapping_type": "contact_type_to_field",
    "pr_destination": "housing_monthly_payment_pr",
    "sec_destination": "housing_monthly_payment_sec",
    "role_attribute": "ac_role_tp_c"
}
```

### 3.4 Dynamic Collateral Enum

**Purpose**: Derive `collateral_type_enum` from `app_type_code` + `sub_type_code`

Implement as calculated field expression:
```sql
CASE 
    WHEN TRIM(IL_application.app_type_code) = 'MARINE' THEN 412 
    WHEN TRIM(IL_application.app_type_code) = 'RV' THEN 413
    ... 
END
```

### Deliverables
- [ ] DataMapper handlers for each mapping type
- [ ] Unit tests with edge cases
- [ ] Integration tests with RL sample XML

### Acceptance Criteria
- All mapping types handle edge cases correctly
- Composite PK tables insert correctly via `table_insertion_order`

---

## Phase 4: Calculated Field Enhancements

**Goal**: Support chained mappings and conditional enum application

### 4.1 Chained Mapping Types

**Proposed syntax**:
```json
{
    "mapping_type": ["calculated_field", "code_to_email_enum"]
}
```

**Behavior**: Apply enum only if calculated field returns blank/NULL

### 4.2 `code_to_email_enum`

Dual-use implementation:
1. **Direct lookup**: Standalone enum mapping
2. **Fallback**: Chained with `check_requested_by_user` - apply only if primary field is blank

### 4.3 Verify TRIM Support

- Audit `calculated_field_engine.py` for TRIM function
- Add test cases for empty string handling
- Verify `IS EMPTY` / `IS NOT EMPTY` operators

### Deliverables
- [ ] Chained mapping type support in DataMapper
- [ ] `code_to_email_enum` implementation
- [ ] Tests for chained "apply if blank" behavior

### Acceptance Criteria
- Chaining works with "apply if blank" semantics
- Existing calculated fields unchanged

---

## Phase 5: RL Integration & Validation

**Goal**: Full RL pipeline validation

### 5.1 Load RL Sample XML

- Use existing 15 samples in `config/samples/xml_files/reclending/`
- **Curated E2E RL fixtures (initial):**
    - `sample-source-xml--325725-e2e--rl.xml`
    - `sample-source-xml--409321-e2e-rl.xml`
- Extend these two files with any missing combinations/elements as needed
- Load via `load_xml_to_db.py` (may need RL variant: `load_xml_to_db_rl.py`)

### 5.2 Create `generate_mock_xml_rl.py`

- Based on `generate_mock_xml.py` structure
- Generate RL-specific XML for performance testing
- Support IL_application, IL_contact, IL_collateral elements

### 5.3 RL Integration Tests

- `tests/integration/test_data_mapper_rl_product.py`
- `tests/e2e/test_pipeline_reclending_integration.py`

### 5.5 CC E2E Test Parity (Manual → Curated)

**Goal**: Convert the two CC manual E2E tests into deterministic, file-backed tests using the full application pipeline.

**Approach**:
- Curate 2 specific CC XML files with predictable content
- Process via full pipeline: `production_processor.py` with `--product-line CC`
- Validate end-to-end: XML source → parsing → mapping → database writes
- Assert key outputs (row counts, enum values, calculated fields) against curated expected results

**Deliverables**:
- [ ] Curated CC XML fixtures (2 files) with stable IDs and documented expected outputs
- [ ] E2E test suite that processes XML and validates database state
- [ ] Documentation of expected transformation results
- [ ] Update test runner to include CC E2E suite

### 5.4 Data Validation

- Apply Phase 0.5 validation patterns to RL data
- Source-to-destination reconciliation
- Risk-based sampling validation

### Deliverables
- [ ] RL samples loaded and processed
- [ ] `generate_mock_xml_rl.py` created
- [ ] Full integration test suite
- [ ] Validation report

### Acceptance Criteria
- All 15 sample files process without errors
- Data validation passes all categories
- Performance within target (3,500+ records/min)

---

## Technical Reference

### Hard-Coded Patterns to Refactor

| Pattern | Location | Priority |
|---------|----------|----------|
| `/Provenir/Request` | `data_mapper.py`, `xml_parser.py` | High |
| `ac_role_tp_c` | `pre_processing_validator.py`, `data_mapper.py` | High |
| `['PR', 'AUTHU']` | `pre_processing_validator.py` | High |
| `contact`, `contact_address` | Various XPath queries | Medium |
| Path.endswith checks | `data_mapper.py` | Medium |

### Contract Helper Functions Needed

Add to `ConfigManager` or `contract_utils.py`:
- `get_xml_root_path()` - Replace hard-coded `/Provenir/Request`
- `get_child_element_name(child_table)` - Element name lookup
- `get_filter_attribute(element_type)` - e.g., `ac_role_tp_c` for contacts
- `get_valid_values(element_type)` - e.g., `['PR', 'AUTHU']` for contacts

### Y/N Enum Columns (app_funding_checklist_rl)

~30 columns use common pattern - derive `char_to_bit` mapping from DDL FK constraints:
- `addendum_signed_pr_enum`
- `addendum_signed_sec_enum`
- `collateral_percent_used_confirmed_enum`
- `collateral_worksheet_unit_confirmed_enum`
- ... (see DDL for full list)

### Test Audit (Hard-Coded Values)

Tests that need updating for multi-product support:

| Test File | Hard-Coded Pattern |
|-----------|-------------------|
| `test_mapping_contract_schema.py` | `/Provenir/Request` path assertions |
| `test_mapping_types_and_expressions.py` | Enum IDs, element names |
| `test_pipeline_full_integration.py` | `PR=281`, specific enum values |

---

## Acceptance Criteria Checklist

### Phase 0: Stabilization
- [ ] All existing tests pass
- [ ] Production processor smoke test succeeds
- [ ] Baseline metrics captured

### Phase 0.5: CC Data Validation
- [ ] Validation queries for all 5 categories
- [ ] Anomalies documented with explanations
- [ ] Critical bugs fixed

### Phase 1: Shared Functionality
- [ ] `add_score` implemented with upsert
- [ ] `add_indicator` implemented with upsert
- [ ] `add_history` implemented
- [ ] Unit tests passing

### Phase 2: CLI & Contract
- [ ] `--product-line` CLI working
- [ ] `mapping_contract_rl.json` validated against DDL
- [ ] CSV archived

### Phase 3: RL Mapping Types
- [ ] `policy_exceptions(enum)` implemented
- [ ] `warranty_field(enum)` implemented
- [ ] `contact_type_to_field` implemented
- [ ] Collateral enum derivation working

### Phase 4: Calculated Field Enhancements
- [ ] Chained mapping types working
- [ ] `code_to_email_enum` dual-use verified
- [ ] TRIM support verified

### Phase 5: RL Integration
- [ ] All 15 RL samples processed
- [ ] E2E tests passing
- [ ] Performance target met (3,500+ records/min)
