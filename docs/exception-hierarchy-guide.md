# Exception Hierarchy Guide

## Overview

The XML Database Extraction System uses a structured exception hierarchy to provide clear error categorization and enable specific error handling throughout the codebase.

**Base Exception:** `XMLExtractionError`  
**Location:** `xml_extractor/exceptions.py`

## Exception Hierarchy

```
Exception
  └── XMLExtractionError (base for all extraction errors)
       ├── XMLParsingError
       ├── MappingContractError
       ├── DataTransformationError
       ├── DatabaseConnectionError
       ├── DatabaseConstraintError (NEW)
       ├── SchemaValidationError
       ├── ConfigurationError
       ├── ValidationError
       ├── DataMappingError
       ├── PerformanceError
       ├── TransactionAtomicityError (NEW)
       └── BulkInsertError (NEW)
```

## When to Use Each Exception Type

### XMLParsingError
**Used for:** XML parsing failures (lxml errors, malformed XML)

```python
try:
    tree = lxml.etree.fromstring(xml_content)
except lxml.etree.XMLSyntaxError as e:
    raise XMLParsingError(
        message=f"Failed to parse XML: {e}",
        xml_content=xml_content,  # First 500 chars stored for debugging
        source_record_id=record_id
    )
```

### MappingContractError
**Used for:** Contract validation and loading failures

```python
try:
    contract = self._load_mapping_contract()
except (FileNotFoundError, json.JSONDecodeError) as e:
    raise MappingContractError(f"Invalid mapping contract: {e}")
```

### DataTransformationError
**Used for:** Field-level transformations that fail

```python
try:
    converted = self._convert_to_target_type(value, target_type)
except (ValueError, TypeError) as e:
    raise DataTransformationError(
        message=f"Failed to convert {field_name}",
        field_name=field_name,
        source_value=value,
        target_type=target_type,
        source_record_id=record_id
    )
```

### DatabaseConnectionError
**Used for:** Connection failures (server unreachable, auth failed, etc.)

```python
try:
    conn = pyodbc.connect(connection_string, timeout=30)
except pyodbc.OperationalError as e:
    if "Connection" in str(e) or "login" in str(e).lower():
        raise DatabaseConnectionError(f"Failed to connect: {e}")
    else:
        # Other pyodbc errors - let them bubble or wrap appropriately
        raise
```

### DatabaseConstraintError ⭐ (NEW)
**Used for:** Database constraint violations (PK, FK, NOT NULL, CHECK)

```python
except pyodbc.Error as e:
    error_msg = str(e).lower()
    if 'primary key constraint' in error_msg or 'duplicate key' in error_msg:
        raise DatabaseConstraintError(
            message=f"Primary key violation in {table_name}: {e}",
            error_category="primary_key_violation"
        )
    elif 'foreign key constraint' in error_msg:
        raise DatabaseConstraintError(
            message=f"Foreign key violation in {table_name}: {e}",
            error_category="foreign_key_violation"
        )
    # ... handle other constraint types
```

**Specific error_category values:**
- `"primary_key_violation"` - PK or unique constraint violated
- `"foreign_key_violation"` - FK reference error
- `"check_constraint_violation"` - CHECK constraint violated
- `"not_null_violation"` - NOT NULL constraint violated

### SchemaValidationError
**Used for:** Target schema doesn't match contract expectations

```python
try:
    self._validate_target_schema()
except Exception as e:
    raise SchemaValidationError(f"Schema validation failed: {e}")
```

### ConfigurationError
**Used for:** Invalid or missing configuration

```python
if not self.connection_string:
    raise ConfigurationError("connection_string is required")
```

### ValidationError
**Used for:** Data or configuration validation failures

```python
if not validate_data(record):
    raise ValidationError(f"Record validation failed: {record}")
```

### DataMappingError
**Used for:** Data mapping operation failures

```python
try:
    mapped_data = self.data_mapper.apply_mapping_contract(records)
except Exception as e:
    raise DataMappingError(f"Failed to apply mapping contract: {e}")
```

### PerformanceError
**Used for:** Performance threshold breaches

```python
if processing_rate < MIN_RECORDS_PER_MINUTE:
    raise PerformanceError(
        message=f"Processing rate too slow: {processing_rate} rec/min",
        metric_name="processing_rate",
        current_value=processing_rate,
        threshold_value=MIN_RECORDS_PER_MINUTE
    )
```

### TransactionAtomicityError ⭐ (NEW)
**Used for:** Transaction rollback failures (critical database errors)

```python
except pyodbc.Error as rollback_error:
    logger.critical(f"ROLLBACK FAILED: {rollback_error}")
    raise TransactionAtomicityError(
        message=f"Failed to rollback transaction: {rollback_error}",
        error_category="transaction_atomicity"
    )
```

### BulkInsertError ⭐ (NEW)
**Used for:** Bulk insert operations that fail completely

```python
if fast_executemany_failed and fallback_insert_failed:
    raise BulkInsertError(
        message=f"All insert strategies failed for {table_name}",
        error_category="bulk_insert_failure"
    )
```

## Best Practices

### 1. Use Specific Exception Types in Catch Blocks

❌ **Bad:** Catches everything, loses error information
```python
try:
    self.migrate_data()
except Exception as e:
    logger.error(f"Migration failed: {e}")
    raise
```

✅ **Good:** Catches specific exceptions, enables targeted handling
```python
try:
    self.migrate_data()
except DatabaseConstraintError as e:
    logger.warning(f"Duplicate record skipped: {e.error_category}")
    # Can choose to skip this record and continue
except DatabaseConnectionError as e:
    logger.error(f"Connection lost, aborting: {e}")
    raise
except XMLExtractionError as e:
    logger.error(f"Extraction failed: {e}")
    raise
```

### 2. Provide Context Information

```python
# Include record ID, field name, or table name for debugging
raise DataTransformationError(
    message=f"Cannot convert {field_name} in record {record_id}",
    field_name=field_name,
    source_value=raw_value,
    target_type=target_type,
    source_record_id=record_id
)
```

### 3. Chain Exceptions

```python
try:
    cursor.execute(sql, params)
except pyodbc.Error as e:
    # Transform to domain exception while preserving original
    raise DatabaseConstraintError(
        message=f"Insert failed: {e}"
    ) from e
```

### 4. Use error_category for Programmatic Handling

```python
try:
    cursor.execute(sql, params)
except XMLExtractionError as e:
    if e.error_category == "primary_key_violation":
        # Skip duplicates
        continue
    elif e.error_category == "foreign_key_violation":
        # Log and report
        raise
    else:
        # Other errors
        raise
```

## Migration from Generic Exceptions

### Before (Generic Exception)
```python
except Exception as e:
    logger.error(f"Error: {e}")
    raise XMLExtractionError(f"Operation failed: {e}")
```

### After (Specific Exception Type)
```python
except pyodbc.Error as e:
    if "PRIMARY KEY" in str(e):
        raise DatabaseConstraintError(
            f"Duplicate record: {e}",
            error_category="primary_key_violation"
        )
    else:
        raise XMLExtractionError(f"Database error: {e}")
except DataTransformationError:
    # Already domain-specific, just re-raise
    raise
except Exception as e:
    # Catch-all for unexpected errors
    logger.critical(f"Unexpected error: {e}")
    raise XMLExtractionError(f"Unexpected error: {e}")
```

## Testing Exception Handling

```python
import pytest
from xml_extractor.exceptions import (
    DatabaseConstraintError,
    XMLExtractionError
)

def test_duplicate_key_raises_constraint_error():
    """Verify PK violations raise DatabaseConstraintError."""
    strategy = BulkInsertStrategy()
    cursor = MockCursor()
    
    def raise_pk_error(*args, **kwargs):
        raise pyodbc.Error("Violation of PRIMARY KEY")
    
    cursor.executemany = raise_pk_error
    
    with pytest.raises(DatabaseConstraintError) as exc_info:
        strategy.insert(cursor, records, "contact_base", "[dbo].[contact_base]")
    
    assert exc_info.value.error_category == "primary_key_violation"

def test_transaction_atomicity_error_on_rollback_failure():
    """Verify rollback failures raise TransactionAtomicityError."""
    engine = MigrationEngine()
    
    with pytest.raises(TransactionAtomicityError):
        with engine.transaction(mock_connection):
            # Simulate error that occurs
            raise pyodbc.Error("Insert failed")
```

## Summary of Changes in Issue #9

1. ✅ **Enhanced exceptions.py** with 3 new domain-specific exceptions:
   - `DatabaseConstraintError` - for constraint violations
   - `TransactionAtomicityError` - for transaction rollback failures
   - `BulkInsertError` - for bulk insert failures

2. ✅ **Updated BulkInsertStrategy**:
   - Now raises `DatabaseConstraintError` for constraint violations
   - Provides specific `error_category` values for each violation type
   - Improved error messages with context

3. ✅ **Updated MigrationEngine**:
   - Transaction method now uses specific exception types
   - Distinguishes between different error scenarios
   - Provides clear error categorization for upstream handlers

4. ✅ **All 145 tests passing** - zero regressions from exception hierarchy changes

## References

- **File:** `xml_extractor/exceptions.py` - Complete exception hierarchy
- **Usage:** `xml_extractor/database/bulk_insert_strategy.py` - Example implementation
- **Usage:** `xml_extractor/database/migration_engine.py` - Example in transaction management
