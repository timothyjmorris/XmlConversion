# Data Mapping Principles

This document outlines the core principles implemented in the XML Database Extraction system for contract-driven data mapping and transformation.

## Contract-Driven Architecture

The system implements a **contract-driven architecture** where mapping contracts are enhanced with schema-derived metadata (nullable/required/default_value fields) from the database schema. This ensures data integrity and prevents silent data corruption.

### Schema-Derived Validation
- **Nullable/Required Fields**: Contract fields include database schema constraints
- **Default Values**: Schema-derived defaults replace application-level defaults
- **Type Safety**: Contract-driven data type transformations with proper NULL handling
- **Data Integrity**: Pre-flight validation ensures database constraints are respected

## Core Mapping Principles

### Principle 1: Contract-Driven Data Integrity
**Use schema-derived metadata to validate and transform data**

- Mapping contracts include nullable/required/default_value fields from database schema
- Only explicitly mapped data is processed (no default injection)
- NULL values are preserved to distinguish missing data from default assignments
- Database constraints are validated before insertion

### Principle 2: Selective Column Insertion
**Exclude columns from INSERT when no valid value exists**

- If a mapping returns `None`, the column is excluded from the INSERT statement entirely
- This prevents inserting NULL values where business logic requires valid data
- Applies to all mapping types, especially enum mappings with no valid mapping
- Preserves data integrity by not fabricating values

### Principle 3: Enum Mapping Integrity
**Always use contract-defined enum mappings, never resolve to invalid values**

- Enum columns with no valid mapping return `None` and are excluded from INSERT entirely
- Enum columns cannot be 0 or any invalid enum value
- Case-insensitive matching is supported for enum values
- Contract-driven validation ensures only valid enum codes are inserted

### Principle 4: Contact Deduplication
**Apply 'last valid element' logic for duplicate contact handling**

- Multiple contacts with same role are deduplicated using last valid element approach
- Primary contacts (PR role) take precedence over other roles
- Address filtering prioritizes CURR (current) over PREV/MAIL types
- Ensures consistent contact data extraction across XML structures

## Implementation Details

### Contract-Driven Validation
```python
# Schema-derived defaults from contract
def _get_default_for_mapping(self, mapping):
    if hasattr(mapping, 'default_value') and mapping.default_value:
        return self.transform_data_types(mapping.default_value, mapping.data_type)
    return None  # No default injection
```

### Selective Column Insertion
```python
# Exclude None values from INSERT
if value is None:
    # Column not included in INSERT statement
    continue
```

### Enum Mapping with Contract Validation
```python
# Contract-driven enum mapping
def _apply_enum_mapping(self, value, mapping):
    # ... contract-based mapping logic ...
    if no_valid_mapping_found:
        return None  # Exclude from INSERT, preserve NULL
```

### Contact Deduplication Logic
```python
# Last valid element approach
def _extract_valid_contacts(self, xml_data):
    # Group contacts by role and con_id
    # Apply 'last valid element' deduplication
    # Return deduplicated contact list
```

## Benefits

1. **Data Integrity**: Schema-derived validation prevents data corruption
2. **Contract Compliance**: Database constraints respected through contract metadata
3. **NULL Semantics**: Proper distinction between missing data and default values
4. **Performance**: Bulk operations optimized with selective column insertion
5. **Maintainability**: Clear contract-driven principles guide all mapping decisions