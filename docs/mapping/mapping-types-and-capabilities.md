# Mapping Types & Capabilities

**Last Updated**: 2026-02-09

This document is the canonical reference for mapping types supported by the DataMapper and used in mapping contracts. It is derived from DataMapper behavior plus contract usage across CC and RL.

## How Mapping Types Are Applied

- `mapping_type` can be a string or list; when a list, types are applied in order.
- A chain stops early if a step returns `None` (except `enum` and `default_getutcdate_if_null`).
- After the chain, a final `data_type` conversion is applied (when needed).
- `numbers_only` is enforced after the chain for string outputs.
- Row-creating mapping types are dispatched by `target_table` and build grouped records (not single-column fields).

## Field-Level Mapping Types

### `calculated_field`
Evaluates a SQL-like expression using the calculated field engine. Expressions can reference app-level context, so the mapper builds a flattened XML context before evaluation. Returns `None` when the expression yields no value.

**Supported Features**:
- Arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Conditionals: `CASE WHEN ... THEN ... ELSE ... END`
- Comparisons: `=`, `!=`, `<`, `>`, `<=`, `>=`
- Logical: `AND`, `OR`
- NULL checks: `IS NULL`, `IS NOT NULL`, `IS EMPTY`, `IS NOT EMPTY`
- String: `LIKE` pattern matching
- Date: `DATE('yyyy-mm-dd')` parsing, `DATEADD(day, number, date)` arithmetic
- Cross-element references: `element.field` notation

**📖 See [calculated-field-expressions.md](calculated-field-expressions.md) for comprehensive expression reference with examples.**

### `enum`
Maps a string to an integer enum value. If no mapping exists and the field is nullable, it returns `None` (column excluded from INSERT). For NOT NULL enums, missing mappings raise a `DataMappingError` unless a contract default exists.

### `char_to_bit`
Converts Y/N (and configured variants) to bit values using contract-defined bit maps. Empty/null values map to the default (0).

### `boolean_to_bit`
Converts boolean-like values to bit values using contract-defined bit maps. Empty/null values map to the default (0).

### `last_valid_pr_contact`
Extracts values from the last valid primary contact (first value in the contract’s contact type array). Supports contact, address, and child element extraction via contract-driven element names.

### `last_valid_sec_contact`
Extracts values from the last valid secondary contact (second value in the contract’s contact type array). Mirrors `last_valid_pr_contact` behavior.

### `authu_contact`
Extracts values from the AUTHU contact type (second value in the contract’s contact type array) instead of PR. Used when fields are tied to authorized user data.

### `curr_address_only`
Filters to the preferred (current) address for the contact in context, using contract-driven address type filters.

### `extract_numeric`
Extracts numeric values from formatted strings prior to type conversion (handles commas and mixed characters). Intended for numeric types when inputs contain currency or formatting.

### `numbers_only`
Extracts digits only. Used for fields that must contain digits exclusively (e.g., year). It is applied during the chain and enforced again after chaining for string outputs.

### `default_getutcdate_if_null`
If the input value is empty, returns the current UTC timestamp. Otherwise, applies the standard `data_type` conversion.

### `extract_date`
Present in RL contracts. There is no dedicated handler in DataMapper; it is currently treated as an unknown mapping type and falls back to standard `data_type` conversion.

### `identity_insert`
Present in contracts as a marker. There is no DataMapper-specific behavior; enabling IDENTITY_INSERT is handled in the database insert pipeline when explicitly configured.

### Default (no mapping type)
If no mapping type is specified, the mapper applies direct extraction and `data_type` conversion. For integer types with non-digit content, it automatically attempts numeric extraction before conversion.

## Row-Creating Mapping Types

### `add_score(<identifier>)` → scores
Creates one row per mapped score. Values are type-converted and inserted as `{app_id, score_identifier, score}`. Rows are skipped when the score value is empty or non-convertible.

### `add_indicator(<name>)` → indicators
Creates one row per indicator when the source value is truthy (`Y`, `YES`, `TRUE`, `T`, `1`). Values are stored as `{app_id, indicator, value='1'}`.

### `add_history` → app_historical_lookup
Creates a row when the value is meaningful (not empty and not literal `null`/`none`). The mapper derives:
- `name` from the XML attribute (wrapped in brackets)
- `source` from the rightmost XML path segment (wrapped in brackets)

### `add_report_lookup(<source_report_key?>)` → app_report_results_lookup
Creates a row when the value is meaningful. `name` is the XML attribute, `value` is the trimmed source value, and `source_report_key` is included when a parameter is provided.

### `policy_exceptions(<enum>)` and `policy_exceptions()` → app_policy_exceptions_rl
- `policy_exceptions()` (empty param) provides shared `notes`.
- `policy_exceptions(<enum>)` rows are created when `reason_code` has meaningful data.
Each row includes `{app_id, policy_exception_type_enum, reason_code, notes}`.

### `warranty_field(<enum>)` → app_warranties_rl
Creates one row per warranty enum (620–626). Rows include `{app_id, warranty_type_enum, company_name, amount, term_months, policy_number}` and `merrick_lienholder_flag` (via `char_to_bit` for GAP). Rows are created only when at least one non-bit field has meaningful data. `merrick_lienholder_flag` defaults to 0 when missing.

### `add_collateral(<N>)` → app_collateral_rl
Creates one row per collateral slot (`N=1..4`). Supports chained types within a slot:
- `calculated_field` for `collateral_type_enum` (uses app-level context)
- `char_to_bit` for `used_flag`
- `numbers_only` or `extract_numeric` for `year`

**Meaningful Data Logic:**
- Rows are created **only** when the slot contains meaningful data  
- `wholesale_value=0` alone does not create a row
- `calculated_field` and `char_to_bit` do NOT trigger row creation (they only populate columns in already-created rows)
- If no meaningful data exists → no row created (even if `default_value` set)

**Default Value Application:**
- Applied **after** meaningful data check passes
- For NOT NULL columns (`make`, `year`, `used_flag`): `default_value` fills missing fields  
- For `collateral_type_enum`: CASE expression with `ELSE` clause ensures value always returned (no `default_value` needed)
- `sort_order` is set to the slot number

**Removed Redundancies:**
- `exclude_default_when_record_empty` - Redundant; the meaningful data check already prevents empty record creation
- `default_value` on `collateral_type_enum` - Redundant; CASE ELSE clause ensures non-NULL return

## Known Gaps / Items to Track

- `extract_date` appears in the RL contract but has no dedicated handler (currently default type conversion).
- `identity_insert` appears in contracts but has no DataMapper-specific behavior (requires pipeline-level enablement).

## Related Documentation

- [datamapper-functions.md](datamapper-functions.md)
- [mapping-principles.md](mapping-principles.md)
