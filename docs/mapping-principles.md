# Data Mapping Principles

This document outlines the core principles implemented in the XML Database Extraction system for data mapping and transformation.

## Core Mapping Principles

### Principle 1: Selective Column Insertion
**Do not add columns to INSERT statement if there isn't a valid value**

- If a mapping returns `None`, the column is excluded from the INSERT statement entirely
- This prevents inserting NULL values where business logic requires valid data
- Applies to all mapping types, especially enum mappings

### Principle 2: Enum Mapping Integrity
**Always use enum mapping from contract, never resolve to invalid values**

- Enum columns with no valid mapping return `None` and are excluded from INSERT entirely
- Enum columns cannot be 0 or any invalid enum value
- Case-insensitive matching is supported for enum values
- If no mapping is found, the column is excluded rather than using a default

### Principle 3: Character Encoding Handling
**Handle pyodbc encoding issues with targeted workarounds**

- Specific tables (`contact_address`, `contact_employment`) use individual `execute()` calls instead of `executemany()` due to pyodbc encoding issues
- This prevents string corruption (question marks) in SQL Server
- Most tables still benefit from bulk `executemany()` performance

## Implementation Details

### None Value Handling
```python
# If mapping returns None, column is excluded from INSERT
if value is None:
    # Column not included in INSERT statement
    continue
```

### Enum Mapping
```python
# Enum mapping returns None for invalid values
def _apply_enum_mapping(self, value, mapping):
    # ... mapping logic ...
    if no_valid_mapping_found:
        return None  # Exclude from INSERT
```

### Bulk Insert Optimization
```python
# Targeted workaround for encoding issues
force_individual_executes = table_name in ['contact_address', 'contact_employment']
if use_executemany and not force_individual_executes:
    cursor.executemany(sql, batch_data)  # Fast bulk insert
else:
    # Individual executes for problematic tables
    for record in batch_data:
        cursor.execute(sql, record)
```

## Benefits

1. **Data Integrity**: Only valid data is inserted into the database
2. **Performance**: Bulk operations used where possible
3. **Reliability**: Character encoding issues are handled transparently
4. **Maintainability**: Clear principles guide mapping decisions