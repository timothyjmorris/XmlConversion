# Contract-Driven Mapping & Downstream Simplification Checklist

- The `credit_card_mapping_contract.json` is the authoritative source for your contract-driven mapping: it defines the intended schema, mapping types, data types, default values, and business rules for the pipeline.
- All downstream logic (validation, parsing, mapping, inserting) should use this contract as the basis for how data is processed.
- While there are still other business rules scattered throughout the codebase (e.g., in validators, mappers, or insert logic), these should not override or contradict the contract. The contract is the first and final authority for business rules.

## 1. Upstream (Mapping Logic)
- [ ] Enforce all contract-driven rules (precision, truncation, mapping type chains, enum handling, etc.) in `DataMapper` and related mapping logic.
- [ ] Validate that all mapped data conforms to database schema (length, type, nullability) before passing to the insert step.
- [ ] Remove any reliance on downstream schema-based truncation or type enforcement.
- [ ] Add unit/integration tests to confirm contract-driven enforcement (e.g., string truncation, mapping type chains).

## 2. Downstream (MigrationEngine/Insert Logic)
- [ ] Remove any plans or code for fetching schema from the database for truncation or type enforcement.
- [ ] Do not add logic for truncating or padding values based on database column definitions.
- [ ] Keep only basic error handling for SQL errors (primary key, foreign key, null constraint, etc.).
- [ ] Optionally simplify dynamic column filtering if upstream always provides correct columns.
- [ ] Document that all data preparation and validation is expected to be done upstream.

## 3. Testing & Validation
- [ ] Run end-to-end integration tests to confirm no SQL truncation or type errors occur.
- [ ] Benchmark performance before and after refactor to ensure no significant impact.
- [ ] Audit error logs to confirm that any remaining errors are true data or connectivity issues, not mapping mistakes.

## 4. Documentation & Code Comments
- [ ] Update documentation to clarify that contract-driven rules are enforced in mapping logic, not in insert logic.
- [ ] Add code comments in `MigrationEngine` noting that it expects pre-validated, schema-conformant data.

---

Work through this checklist to ensure robust, maintainable, and high-performance contract-driven mapping and database insertion.

## 1a. Contract Improvements & Ideas
- [ ] Refactor contract and mapping logic to support chained mapping types (e.g., `"mapping_type": "curr_address_only,numbers_only"` or array form).
- [ ] Add `description` field to each mapping for business intent and documentation.
- [ ] Consider standardizing data types (e.g., use `string` with `data_length` instead of `char`/`varchar`).
- [ ] Add `required` or `nullable` flags for clarity on mandatory fields.
- [ ] Add `validation` rules (e.g., regex, allowed values) for fields needing extra checks.
- [ ] Add `default_value` for business-required fallbacks.
- [ ] Document mapping types and business rules in the contract (e.g., `mapping_type_docs`).
- [ ] For calculated fields, add a `business_rule` or `description` to explain logic.
- [ ] Document enum/bit mapping tables and their business meaning.
- [ ] Add `relationships` section for foreign key/parent-child intent if needed.

### Example Mapping Entry (Recommended Structure)
```json
{
  "xml_path": "/Provenir/Request/CustData/application/contact",
  "xml_attribute": "banking_account_number",
  "target_table": "app_operational_cc",
  "target_column": "sc_bank_account_num",
  "data_type": "string",
  "data_length": 17,
  "mapping_type": ["last_valid_pr_contact", "numbers_only"],
  "required": true,
  "nullable": false,
  "default_value": null,
  "description": "Extracts the banking account number from the last valid PR contact, applies numbers_only filter.",
  "validation": {
    "regex": "^\\d{1,17}$"
  }
}
```

### What Makes the Most Sense to Add First?
- `description` (for business intent and maintainability)
- `data_length` (for explicit truncation)
- Chained `mapping_type` (as array or comma-separated string)
- `required`/`nullable` flags (for clarity)

Other fields (validation, relationships, business_rule) can be added as needed for more complex logic.

## Benchmark Check Prior to Refactor
Using #production_proccessor.py, on ~10 runs got an average of 
  "records_per_minute": 344.6427207277106,
  "records_per_second": 5.744045345461843,
