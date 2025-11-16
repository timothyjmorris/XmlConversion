# IL (RecLending) Contract Analysis & Remediation Plan

Purpose
-------
This document captures the results of a quick code scan of `xml_extractor` for hard-coded XML element names, attribute names, and enum literals that must be made contract-driven before the new IL (RecLending) mapping contract is fully supported. It also lists tests and scripts that must be reconciled with the new contract and provides a prioritized remediation plan.

Summary of findings
-------------------
I scanned the `xml_extractor` package and found multiple locations that reference Provenir-specific element names and attribute names directly in code and tests. These are brittle when adding a new product that uses different XML element names or attribute names.

High-level categories of hard-coded patterns found
- XML root / paths: `/Provenir/Request`, `/Provenir/Request/CustData/application`
- Element names: `contact`, `contact_address`, `contact_employment`
- Attribute names: `ac_role_tp_c`, `address_tp_c`, `employment_tp_c`, `con_id`
- Enum literal lists / validations: `['PR', 'AUTHU']` (primary contact roles), other numeric enum IDs referenced in tests
- Other structural checks: `path.endswith('/contact')` and XPath checks for `.//contact[@ac_role_tp_c]`

Files & example hard-coded occurrences (representative — not exhaustive)
- `xml_extractor/mapping/data_mapper.py`
  - Uses `/Provenir/Request` as request path and checks `/Provenir/Request/@ID` for app_id.
  - Uses `.//contact[@ac_role_tp_c]` and does `path.endswith('/contact')` in some logic.
  - Contains logic for building element-name cache but still contains references to `contact_employment` and `contact_address` as target table names (these are allowed), and several code comments showing assumptions.
  - References `('ac_role_tp_c', ['PR', 'AUTHU'])` and other contact-type expectations in comments and docstrings.

- `xml_extractor/validation/pre_processing_validator.py`
  - Validates presence of `/Provenir/Request/@ID`.
  - Explicitly enforces valid roles `valid_roles = ['PR', 'AUTHU']` and raises errors referencing `PR`.
  - Uses `contact.get('ac_role_tp_c', '')` in logic and selects PR contacts with `c.get('ac_role_tp_c') == 'PR'` (hard-coded literal).

- `xml_extractor/parsing/xml_parser.py`
  - Documentation and checks referencing `/Provenir/Request/CustData/application` and looks for closing `</Provenir>` tag.

- `xml_extractor/validation/data_integrity_validator.py` and `xml_extractor/validation/future/data_integrity_validator.py`
  - Use lists of tables including `contact_address`, `contact_employment` and expected foreign key columns.

- `xml_extractor/processing/parallel_coordinator.py` and various processing modules
  - Contain `table_order` and lists including `contact_base`, `contact_address`, `contact_employment` (these are destination tables; per your note these are OK to remain as the target tables but related assumptions about XML element names must be contract-driven).

Tests & scripts that need reconciliation
- `tests/contracts/test_mapping_contract_schema.py` — will need mapping of new IL DDL/enum IDs; also checks field mappings start with `/Provenir/Request`.
- `tests/contracts/test_mapping_types_and_expressions.py` — contains many assumptions about paths, enums, and calculated fields tied to Provenir XML. Needs to be rewritten to be contract-driven and to accept multiple product structures.
- `tests/e2e/test_pipeline_full_integration.py` — end-to-end test uses `sample-source-xml-contact-test.xml` (Provenir) and asserts specific enum IDs and attribute values (e.g., PR=281). We need a RL equivalent with edge cases and adapt assertions to read values from the contract's `enum_mappings` rather than hard-coding numeric IDs.
- `env_prep/load_xml_to_db.py` — currently looks for `<Request>` directly under root and extracts `Request/@ID` — should either accept contract selection or be used only for Provenir samples and documented as such.

Why these are problems for IL (RecLending)
- IL product may prefix element names (e.g., `IL_contact`, `IL_contact_address`) or use different attribute names (e.g., `role_type` instead of `ac_role_tp_c`). Hard-coded code will fail to find elements or will mis-validate.
- Tests that assert specific element paths or enum numeric values will break and mask whether failures are due to mapping contract errors or test brittleness.

Remediation approach (prioritized)
1. Short-term: Keep product-specific contract files and pass `--mapping-contract-path` to tools/tests
   - Create `config/mapping_contract_IL.json` and run tests pointing explicitly to it when validating IL
   - Use `load_xml_to_db.py` and existing tests only when configured to the appropriate contract

2. Medium-term: Remove hard-coded XML paths and attribute names from code
   - Replace `'/Provenir/Request'` usage with contract-driven `xml_root_path` or functions from `ConfigManager`.
   - Replace `contact_elements = xml_root.xpath('.//contact[@ac_role_tp_c]')` with a contract-based lookup that uses `DataMapper._get_child_element_name('contact_base')` or a `ConfigManager` helper to get element name and attribute names for filtering.
   - Replace literal `ac_role_tp_c` checks and role lists with calls to `ConfigManager`/contract (e.g., `get_element_type_filters('contact')` returning (`attribute_name`, `valid_values`)).

3. Tests: audit and refactor to be contract-driven
   - Update `test_mapping_contract_schema.py` to: read `contract['xml_root_element']` (or `xml_root_path`) dynamically instead of asserting `/Provenir/Request`.
   - Replace numeric enum assertions with `(contract['enum_mappings'][enum_type][text_value])` lookups so tests derive expected numeric IDs from the contract.
   - For `test_mapping_types_and_expressions.py`, parameterize tests by product contract and sample XML files per product. Make sample XML fixture selection driven by a `contract` fixture.
   - Add a test discovery step that warns when tests reference hard-coded `/Provenir` strings — list them for manual rewrite.

4. Create a comprehensive test matrix and RL gnarly sample(s)
   - Build a set of RL sample XML files that exercise edge cases: missing attributes, different attribute names, prefixed element names, unusual enum strings, multiple duplicate contacts, missing children, inconsistent date/time formats, etc.
   - Add a new full integration test `tests/e2e/test_pipeline_reclending_integration.py` modeled on `test_pipeline_full_integration.py` but using contract-driven expectations.

Concrete remediation tasks (actionable)
- Code changes
  1. Update `xml_extractor/parsing/xml_parser.py` and `xml_extractor/mapping/data_mapper.py` to derive the application root path (`/Provenir/Request`) from the mapping contract (`xml_root_path` or mapping of relationships) and avoid looking for `</Provenir>` in a brittle way.
  2. Replace explicit usages of `ac_role_tp_c`, `address_tp_c`, `employment_tp_c` with calls to `DataMapper._get_element_type_filters('contact'|'address'|'employment')` which returns the attribute name (contract-driven) and valid values.
  3. Replace `valid_roles = ['PR', 'AUTHU']` and similar literals with `contract.element_filtering.filter_rules[...]` lookups or a `ConfigManager.get_valid_values('contact')` helper.
  4. Centralize a helper in `ConfigManager` or a small `contract_utils.py` to expose common queries: get_xml_root(), get_child_element_name(child_table), get_filter_attribute_for(element_type), get_enum_mapping(enum_type).
  5. Update `env_prep/load_xml_to_db.py` to accept `--mapping-contract-path` (or document it as Provenir-only sample loader).

- Tests & test data
  1. Inventory tests that contain `'/Provenir'`, `ac_role_tp_c`, `PR`, `AUTHU`, `contact_address`, `contact_employment` and list them for rewrite. Start with those the quick scan surfaced (e.g., `tests/contracts/test_mapping_types_and_expressions.py`, `tests/e2e/test_pipeline_full_integration.py`, contract tests).
  2. Add RL sample XML files into `config/samples/` and unit integration fixtures in `tests/fixtures/`.
  3. Update `tests/contracts/test_mapping_contract_schema.py` to accept `contract['xml_root_element']` and to look up enum numeric IDs from `contract['enum_mappings']` before asserting.

- Validation & reconciliation
  1. After SQL DDL for IL tables is provided and IL contract is drafted, run `test_mapping_contract_schema.py` to find contract vs DB mismatches and iterate until the contract metadata matches the DDL.
  2. Run unit tests and integration dry-runs with `--mapping-contract-path` pointing to `config/mapping_contract_IL.json`.

Files I recommend we start by editing (priority order)
1. `xml_extractor/validation/pre_processing_validator.py` — central validation uses `ac_role_tp_c` and `PR`/`AUTHU` literals (high priority)
2. `xml_extractor/mapping/data_mapper.py` — uses `/Provenir/Request`, XPath searches, and path.endswith checks (high priority)
3. `xml_extractor/parsing/xml_parser.py` — references `/Provenir/Request` and `</Provenir>` tag checks (medium priority)
4. `env_prep/load_xml_to_db.py` — make loader contract-aware or document as Provenir-only (low/medium)
5. `tests/contracts/test_mapping_types_and_expressions.py` and `tests/e2e/test_pipeline_full_integration.py` — test rewrite (high priority)

Remediation time estimate (rough)
- Add `ConfigManager`/contract helper functions + small refactors: 2–4 hours
- Rewrite `pre_processing_validator.py` and `data_mapper.py` validation usage: 4–8 hours
- Create IL contract and run schema reconciliation (given SQL DDL): 1–2 hours
- Update and parametrize tests (skeleton → working): 4–8 hours depending on number of brittle tests
- Create RL gnarly integration test and sample XML: 2–4 hours

Next steps I will take if you approve
1. Add a shorter actionable ticket list to the plan document and update the `docs/mapping_contract_IL_plan.md` to include the reconciliations you requested (tests, load script, e2e rewrite). (I can do that now.)
2. If you provide the SQL DDL and sample IL XML, I will draft `config/mapping_contract_IL.json` and the test skeletons.
3. Optionally, I can start the mechanical refactor in `pre_processing_validator.py` to read filter rules from the contract (submit a patch), but I'll wait for your approval.

If you want me to begin making code edits, say which item to start with (I recommend starting with `pre_processing_validator.py` since it's central to validation and currently contains the most brittle logic).