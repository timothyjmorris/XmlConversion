# IL (RecLending) Reconciliation & Test Audit

This companion document captures the reconciliation steps, test audit checklist, required artifacts, and commands to validate the IL (RecLending) mapping contract once you provide the SQL DDL and IL XML samples.

## Reconciliation Steps

1. Run `tests/contracts/test_mapping_contract_schema.py` against the IL contract to detect schema mismatches.
   - Fix any `data_type`, `nullable`, `required`, or `data_length` mismatches in the contract until the script reports no mismatches.
2. Run unit tests that validate contract parsing and the DataMapper element-name cache.
3. Load IL sample XML files into the `app_xml` staging table using `env_prep/load_xml_to_db.py` (make loader contract-aware or set `SAMPLES_DIR` to IL samples).
4. Run the RL integration test (`tests/e2e/test_pipeline_reclending_integration.py`) to:
   - Validate pre-processing and contact filtering with IL contract rules
   - Map and perform a dry-run insert (no destructive writes in CI)
   - Verify that enum numeric values are resolved from the IL contract
5. Investigate integration failures and check for missing `relationships`, `element_filtering`, or enum mapping entries.

## Test Audit Checklist (rewrite candidates)

The following tests/files are likely brittle and should be rewritten to be contract-driven:

- `tests/contracts/test_mapping_contract_schema.py`
  - Read `xml_root_element` and `enum_mappings` from the contract instead of asserting `/Provenir/Request` and fixed enum IDs.
- `tests/contracts/test_mapping_types_and_expressions.py`
  - Remove hard-coded `/Provenir` paths, PR/AUTHU role checks and numeric enum IDs; derive expected enum IDs via `contract['enum_mappings']` and element names via `contract['relationships']`.
- `tests/e2e/test_pipeline_full_integration.py`
  - Clone to `tests/e2e/test_pipeline_reclending_integration.py` and parameterize to run against the IL contract and sample XML. Replace fixed expectations with contract-derived values.
- Any test referencing `'/Provenir'`, `'ac_role_tp_c'`, `'PR'`, `'AUTHU'`, or product-specific values must be updated to use contract helpers.

Action: run a grep search for the above strings and list all test files that contain them for the rewrite backlog.

## Required Artifacts (recap)

Before drafting the IL contract we MUST have:

- SQL `CREATE TABLE` DDL for destination tables and lookup/enum tables with sample rows (IDs and labels).
- Representative IL XML sample files covering happy path and edge cases.
- Small mapping sample (CSV/JSON) mapping key columns to XML paths/attributes.

## Quick commands (PowerShell)

Install editable package and run CLI summary:

```powershell
pip install -e .
python -m xml_extractor.cli
```

Run contract schema check (after placing IL contract at `config/mapping_contract_IL.json`):

```powershell
pytest tests/contracts/test_mapping_contract_schema.py -q
```

Load sample IL XML files into the `app_xml` table (adjust path and env as needed):

```powershell
# edit load_xml_to_db.py or set SAMPLES_DIR to IL samples location before running
python env_prep\load_xml_to_db.py
```

Run the RL integration test (once created):

```powershell
pytest tests/e2e/test_pipeline_reclending_integration.py -q
```

## Next Steps (after you provide DDL and samples)

1. Draft `config/mapping_contract_IL.json` with accurate `relationships`, `element_filtering`, and `enum_mappings`.
2. Add unit test skeletons (`tests/unit/mapping/test_contract_parsing_il.py`, `tests/unit/mapping/test_data_mapper_element_name_cache.py`).
3. Create RL E2E integration test skeleton `tests/e2e/test_pipeline_reclending_integration.py` and a gnarly sample XML fixture.
4. Optionally start refactoring `pre_processing_validator.py` to read contact/role filters from contract.

If you want, I can begin drafting the IL contract with placeholder enum IDs, but it will need refinement against the authoritative DDL and enum rows you provide.
