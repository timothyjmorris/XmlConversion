# Code Exemplars

This document highlights high-quality, representative examples from this codebase. Use these as reference patterns when implementing new features or refactoring existing code.

## Table of Contents

- [XML Parsing](#xml-parsing)
- [Mapping and Transformation](#mapping-and-transformation)
- [Database and Transactions](#database-and-transactions)
- [Validation and Configuration](#validation-and-configuration)
- [Orchestration](#orchestration)
- [Tests](#tests)
- [Diagnostics and Audits](#diagnostics-and-audits)
- [JSON Contracts](#json-contracts)
- [SQL Scripts](#sql-scripts)

## XML Parsing

### XMLParser selective parsing

- File: [xml_extractor/parsing/xml_parser.py](xml_extractor/parsing/xml_parser.py)
- Why exemplary: Contract-driven selective parsing, streaming approach, strong documentation.
- Pattern: Build required paths from mapping contracts to reduce parsing overhead.

```python
if mapping_contract:
    self._build_required_paths()
    self._build_core_structure_elements()
```

## Mapping and Transformation

### DataMapper contract-driven orchestration

- File: [xml_extractor/mapping/data_mapper.py](xml_extractor/mapping/data_mapper.py)
- Why exemplary: Central orchestration with schema isolation, enum mapping, and validation hooks.
- Pattern: Load mapping contract via centralized config and cache mapping helpers.

```python
self._config_manager = get_config_manager()
self._mapping_contract_path = mapping_contract_path or self._config_manager.paths.mapping_contract_path
```

## Database and Transactions

### MigrationEngine schema isolation and qualification

- File: [xml_extractor/database/migration_engine.py](xml_extractor/database/migration_engine.py)
- Why exemplary: Contract-driven schema isolation, atomic transaction focus, and bulk insert strategy.
- Pattern: Schema-qualified table names based on contract.

```python
if table_name.lower() == (self.source_table or 'app_xml').lower():
    return f'[dbo].[{self.source_table}]'
return f'[{self.target_schema}].[{table_name}]'
```

## Validation and Configuration

### MappingContractValidator pre-flight checks

- File: [xml_extractor/validation/mapping_contract_validator.py](xml_extractor/validation/mapping_contract_validator.py)
- Why exemplary: Defensive contract validation with clear error reporting and guidance.
- Pattern: Validate required sections and relationships before processing.

```python
self._validate_element_filtering()
self._validate_relationships()
self._validate_enum_mappings()
```

### DataIntegrityValidator (future enhancement)

- File: [xml_extractor/validation/data_integrity_validator.py](xml_extractor/validation/data_integrity_validator.py)
- Why exemplary: Comprehensive validation framework, clear separation of checks.
- Pattern: Orchestrate multiple validation phases and capture metrics.

## Orchestration

### ProductionProcessor contract routing

- File: [production_processor.py](production_processor.py)
- Why exemplary: Clear product line handling and contract selection with schema isolation.
- Pattern: Resolve contract path based on product line.

```python
if self.product_line == "RL":
    self.mapping_contract_path = str(project_root / "config" / "mapping_contract_rl.json")
else:
    self.mapping_contract_path = str(project_root / "config" / "mapping_contract.json")
```

## Tests

### Integration: config and contract wiring

- File: [tests/integration/test_config_integration.py](tests/integration/test_config_integration.py)
- Why exemplary: Validates centralized configuration with realistic contract setup.
- Pattern: End-to-end wiring for config manager and core components.

### Integration: bulk insert error paths

- File: [tests/integration/test_migration_engine_error_paths.py](tests/integration/test_migration_engine_error_paths.py)
- Why exemplary: Exercises error handling for bulk insert strategy with clear assertions.
- Pattern: Test fast path and fallback behavior using mocks.

### End-to-end: credit card pipeline

- File: [tests/e2e/test_pipeline_creditcard_integration.py](tests/e2e/test_pipeline_creditcard_integration.py)
- Why exemplary: Validates full XML-to-database pipeline for CC product line.
- Pattern: Uses real pipeline components to verify database outcomes.

### End-to-end: ReLending pipeline

- File: [tests/e2e/test_pipeline_reclending_integration.py](tests/e2e/test_pipeline_reclending_integration.py)
- Why exemplary: Validates full XML-to-database pipeline for RL product line.
- Pattern: End-to-end verification with database assertions.

## Diagnostics and Audits

### Data audit utilities

- Folder: [diagnostics/data_audit](diagnostics/data_audit)
- Why exemplary: Provides targeted audits that validate migration outcomes in the database.
- Pattern: Use focused audit scripts to reconcile source-to-destination data and flag gaps.

### Source-to-destination reconciliation

- File: [diagnostics/data_audit/validate_source_to_dest.py](diagnostics/data_audit/validate_source_to_dest.py)
- Why exemplary: Compares source XML-derived data to destination tables for correctness.
- Pattern: Data-driven verification for ETL results.

## JSON Contracts

### Credit card contract (CC)

- File: [config/mapping_contract.json](config/mapping_contract.json)
- Why exemplary: Structured mappings, element filtering rules, and insertion order.
- Pattern: Contract-driven schema isolation and mapping definitions.

```json
"table_insertion_order": [
  "app_base",
  "app_contact_base",
  "app_operational_cc"
]
```

### ReLending contract (RL)

- File: [config/mapping_contract_rl.json](config/mapping_contract_rl.json)
- Why exemplary: Product-line specific paths, relationships, and mapping rules.
- Pattern: Dedicated contract per product line.

## SQL Scripts

### CC data validation

- File: [diagnostics/cc_data_validation.sql](diagnostics/cc_data_validation.sql)
- Why exemplary: Structured validation sections, clear headers, and NOLOCK usage.
- Pattern: Data quality checks grouped by category.

### Mapping contract validation

- File: [config/samples/validate_mapping_contract.sql](config/samples/validate_mapping_contract.sql)
- Why exemplary: Validates table existence, enums, and FK relationships.
- Pattern: Uses INFORMATION_SCHEMA and sys tables for schema checks.

## Conclusion

Use these exemplars as reference points when extending the system. Prefer aligning new code with these patterns over introducing new styles or structures. If you add a new pattern, update this document with a concrete example and rationale.
