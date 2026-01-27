# Plan: Add IL (RecLending) Product Mapping Contract

## Purpose
A task-oriented plan to add a new product line ("IL" / RecLending) to the mapping contract used by the XML Database Extraction system. This plan includes required inputs (explicitly: SQL `CREATE TABLE` scripts and sample mappings), concrete JSON structure guidance, tests, validation steps, and rollout tasks.

## High-level goals
- Add a product-specific mapping contract for IL that allows the existing `DataMapper` to map IL XML element names to the existing destination tables.
- Ensure contract-driven rules (element filtering, enum mappings, relationships, schema isolation) are provided for IL.
- Validate with unit and integration tests and a small performance smoke test.

## Assumptions
- The codebase uses `ConfigManager` to load mapping contracts and the `DataMapper` expects `relationships` and `element_filtering` blocks in the contract.
- Destination database schema (target tables and column definitions) must be authoritative for mapping decisions.
- The quickest, safest approach is to create a product-specific contract file (e.g., `config/mapping_contract_IL.json`) and test it locally before consolidating multiple products into a single contract file.

## Mandatory input you must provide before drafting the IL contract
1. SQL `CREATE TABLE` scripts for all destination tables that IL will populate (at minimum):
   - `app_base` (or equivalent application table)
   - `contact_base`
   - `contact_address`
   - `contact_employment`
   - Any lookup/enums tables referenced (e.g., `address_types`, `decision_types`, `states`) or a mapping that shows enum IDs

   For each table include:
   - Full `CREATE TABLE` DDL (column names, types, NULL/NOT NULL, identity, defaults)
   - Sample rows for any lookup tables with their integer IDs (so we can build `enum_mappings` correctly)

2. Example snippet(s) of the IL (RecLending) XML showing the element names the product uses (top-level structure and child elements). If different element names or prefixes are used (e.g., `IL_contact` instead of `contact`), include sample XML.

3. A short mapping sample table (CSV or JSON) that lists targeted columns and their intended XML path/attribute for at least the critical columns (app id, con_id, ac_role_tp_c, address_tp_c, employment_tp_c, key enums). Example format:
   ```json
   [
     {"xml_path":"/IL_Provenir/IL_Request/IL_CustData/IL_application/@app_receive_date","target_column":"app_receive_date","data_type":"datetime"},
     {"xml_path":"/IL_Provenir/.../IL_contact/@con_id","target_column":"con_id","data_type":"varchar(50)"}
   ]
   ```

> Note: Without the SQL DDL and sample enum rows, the mapping contract cannot be reliably authored — the `DataMapper` uses schema-derived metadata (nullable/required/default) and enum integer values to validate and transform fields.

## Deliverables produced by this plan
- `config/mapping_contract_IL.json` (draft)
- `docs/mapping_contract_IL_plan.md` (this document)
- `tests/unit/mapping/test_contract_parsing_il.py` (skeleton)
- `tests/unit/mapping/test_data_mapper_element_name_cache.py` (skeleton)
- `tests/integration/test_data_mapper_il_product.py` (skeleton + sample XML)
- Validation checklist and example commands for running locally

## Detailed task list (execution steps)
1. Prepare inputs (user action) — REQUIRED
   - Provide SQL DDL for destination tables and sample enum lookup rows.
   - Provide representative IL XML sample(s).
   - Provide the short mapping sample table (CSV/JSON) for critical fields.

2. Draft contract (implementation)
   - Create `config/mapping_contract_IL.json` using the schema used by the repository. Key sections must include:
     - `product_name` (e.g., "IL_lending")
     - `target_schema` (e.g., `sandbox` or `dbo`)
     - `relationships`: array mapping `child_table` → `xml_child_path` (full path; `DataMapper` extracts last segment for element name)
     - `element_filtering`: `filter_rules` with `element_type`, `attribute_name`, `required_attributes`, and ordered `valid_values`
     - `enum_mappings`: textual → integer maps for each enum type used by IL
     - `bit_conversions` (if needed)
     - Optional: `xml_root_path` or `product_identifier` if contract loader uses it

   - Use the SQL DDL to determine `required_attributes` and `nullable`/`default_value` metadata for fields.

3. Unit tests & parsing validation
   - Add tests validating JSON contract structure (presence of `relationships` and `element_filtering` entries).
   - Add test asserting `DataMapper._build_element_name_cache()` returns expected XML element names for child tables referenced by the IL contract.

4. Integration test
   - Add a small sample IL XML file to `tests/harness/` (or `tests/integration/fixtures/`).
   - Write `tests/integration/test_data_mapper_il_product.py` to:
     - Load `mapping_contract_IL.json` via `ConfigManager` or by passing `--mapping-contract-path` to `DataMapper`
     - Instantiate `DataMapper` and call `apply_mapping_contract()` or `map_xml_to_database()` in dry-run mode (no real DB writes) if available, or assert constructed records match expectations.

5. Local verification steps (commands)
   - Install in editable mode (once tests/contract are in place):
     ```powershell
     pip install -e .
     ```
   - Run CLI summary to confirm contract is loadable (or use a small script to print `ConfigManager` loaded contract):
     ```powershell
     python -m xml_extractor.cli
     ```
   - Run unit tests:
     ```powershell
     pytest tests/unit/mapping/test_contract_parsing_il.py -q
     pytest tests/unit/mapping/test_data_mapper_element_name_cache.py -q
     ```
   - Run integration dry-run (example – adjust path/args as needed):
     ```powershell
     python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --limit 10 --mapping-contract-path config/mapping_contract_IL.json
     ```

6. Performance smoke test
   - Generate a small set of sample IL XML records (100–1000) using `env_prep/generate_mock_xml.py` adapted for IL structure.
   - Run a limited run and measure throughput. Compare to baseline. If performance drops >10%, profile the changes.

7. Documentation & PR
   - Add `config/mapping_contract_IL.json`, tests, and this plan to a branch.
   - Open PR including the validation checklist below.

## Validation checklist (what must pass)
- [ ] Contract JSON is syntactically valid and contains required keys (`relationships`, `element_filtering`).
- [ ] `DataMapper._build_element_name_cache()` returns IL child element names as expected.
- [ ] Unit tests for contract parsing pass.
- [ ] Integration test with sample IL XML constructs expected records for core tables (app_base, contact_base, contact_address, contact_employment).
- [ ] No enum lookup failures: textual enum values present in `enum_mappings` or gracefully result in `None` (excluded columns).
- [ ] CLI loads configuration and reports expected `target_schema` for the IL contract.
- [ ] Performance smoke test within acceptable delta from baseline.

## Example JSON snippet to use as a template (adjust to SQL DDL and XML samples you provide)

```json
{
  "product_name": "IL_lending",
  "target_schema": "sandbox",
  "xml_root_path": "/IL_Provenir/IL_Request",
  "relationships": [
    {"child_table":"contact_base","xml_child_path":"/IL_Provenir/IL_Request/IL_CustData/IL_application/IL_contact"},
    {"child_table":"contact_address","xml_child_path":"/IL_Provenir/IL_Request/IL_CustData/IL_application/IL_contact/IL_contact_address"},
    {"child_table":"contact_employment","xml_child_path":"/IL_Provenir/IL_Request/IL_CustData/IL_application/IL_contact/IL_contact_employment"}
  ],
  "element_filtering": {
    "filter_rules": [
      {"element_type":"contact","attribute_name":"ac_role_tp_c","required_attributes":["con_id","ac_role_tp_c"],"valid_values":["PR","AUTH"]},
      {"element_type":"address","attribute_name":"address_tp_c","required_attributes":["address_tp_c"],"valid_values":["CURR","PREV","MAIL"]},
      {"element_type":"employment","attribute_name":"employment_tp_c","required_attributes":["employment_tp_c"],"valid_values":["CURR","PREV"]}
    ]
  },
  "enum_mappings": {
    "address_type_enum": {"CURR":1,"PREV":2,"MAIL":3},
    "decision_enum": {"NONE":1,"APPROVE":2,"DECLINE":3}
  }
}
```

## Notes, caveats, and recommendations
- Start with a product-specific contract file. It's simpler and safer for initial trials.
- Ensure the SQL DDL is authoritative—column nullability and enum numeric values drive contract accuracy.
- Where textual enum values are ambiguous, prefer normalizing to uppercase in `enum_mappings` and rely on case-insensitive matching in `DataMapper`.
- If `ConfigManager` does not yet support a `products` block, do not modify it yet—keep the IL contract as a separate file and pass `--mapping-contract-path` or set the environment variable if implemented.

## Estimated effort
- Draft contract (after receiving DDL/sample XML): 1–2 hours
- Unit tests + integration skeleton: 2–3 hours
- Integration verification & small dry-run: 1 hour
- Performance smoke test & adjustments: 1–2 hours
- PR and documentation: 1 hour

---

If you want, I can now:
- (A) Draft the `config/mapping_contract_IL.json` using placeholder enum IDs (but remember it will be incomplete until you provide SQL DDL and enum rows), or
- (B) Wait for your SQL `CREATE TABLE` scripts and mapping samples, and then produce the contract and tests precisely.

Which do you prefer? If you choose (B), please paste the SQL DDL and a few sample enum rows here and I will continue with step 3.
