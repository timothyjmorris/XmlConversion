---
name: common-patterns
description: Tested, copy-paste-ready code patterns for extending the XML Database Extraction System. Includes 21 patterns for XML parsing, data mapping, validation, database operations, and testing. Use when implementing new features, adding product lines, or needing working examples of contract-driven transformations.
metadata:
  last-updated: "2026-02-14"
  project: xml-database-extraction
  pattern-count: "21"
---

# Common Patterns & Reusable Code Examples

---

## 1. XML Parsing Patterns

### Pattern 1.1: Parse All Elements (Baseline)

**When to use:** Processing straightforward XML with all elements needed

```python
from xml_extractor.parsing.xml_parser import XMLParser

# Parse all elements
parser = XMLParser()
records = parser.parse(xml_content)

# Returns: list of dicts with all extracted elements
for record in records:
    print(record)  # {'app': {...}, 'contact': {...}, ...}
```

### Pattern 1.2: Selective Element Extraction

**When to use:** Large XML with many elements you don't need (performance optimization)

```python
from xml_extractor.parsing.xml_parser import XMLParser

# Only extract specific elements (memory-efficient)
parser = XMLParser(select_elements=['app', 'contact'])
records = parser.parse(xml_content)

# Only app and contact elements extracted
# Other elements skipped during parsing (faster, less memory)
```

### Pattern 1.3: Streaming Parser for Large Files

**When to use:** XML files > 100MB (avoid loading entire file into memory)

```python
from xml_extractor.parsing.xml_parser import XMLParser

# Enable streaming mode
parser = XMLParser(streaming=True, select_elements=['app', 'contact'])

# Process records one at a time
for record in parser.parse_stream(xml_filepath):
    # Memory usage constant regardless of file size
    mapper.map(record)
    engine.migrate(record)
```

**Note:** Current implementation uses `parser.parse()` (loads full file). Consider implementing streaming if product line has multi-GB XML files.

---

## 2. Data Mapping Patterns

### Pattern 2.1: Basic Contract-Driven Mapping

**When to use:** Standard field extraction with enum mappings

**In mapping_contract.json:**
```json
{
  "product_line": "standard",
  "target_schema": "sandbox",
  "mappings": {
    "app_base": [
      {
        "column": "app_id",
        "source_path": "application/id",
        "type": "int",
        "nullable": false
      },
      {
        "column": "status_code",
        "source_path": "application/status",
        "type": "enum",
        "nullable": false,
        "enum_mappings": {
          "ACTIVE": "A",
          "INACTIVE": "I",
          "PENDING": "P"
        }
      }
    ]
  }
}
```

**DataMapper applies automatically:**
```python
from xml_extractor.mapping.data_mapper import DataMapper

mapper = DataMapper(mapping_contract)
mapped_data = mapper.map_record(parsed_xml)

# Result: 
# {
#   "app_base": {
#     "app_id": 12345,
#     "status_code": "A"  (enum translated)
#   }
# }
```

### Pattern 2.2: Calculated Fields

**When to use:** Fields derived from source data (not direct mappings)

**In mapping_contract.json:**
```json
{
  "calculated_fields": {
    "app_base": {
      "created_at_utc": "datetime.utcnow()",
      "name_full": "concat(first_name, ' ', last_name)",
      "is_high_value": "revenue > 100000"
    }
  }
}
```

**In DataMapper code:**
```python
def apply_calculated_fields(self, record, target_table):
    """Apply contract-defined calculated fields"""
    
    config = self.contract['calculated_fields'].get(target_table, {})
    
    for field_name, formula in config.items():
        if formula == "datetime.utcnow()":
            record[field_name] = datetime.utcnow()
        elif "concat(" in formula:
            # Parse concat(field1, sep, field2)
            parts = self._parse_concat(formula)
            record[field_name] = ''.join(str(record.get(p, '')) for p in parts)
        elif ">" in formula:
            # Parse comparison (is_high_value: revenue > 100000)
            value = self._evaluate_expression(formula, record)
            record[field_name] = value
    
    return record
```

### Pattern 2.3: Product-Line-Specific Mapping

**When to use:** Product lines with fundamentally different XML structures

**Approach: Dispatch in DataMapper based on product_line**

```python
class DataMapper:
    def map_record(self, parsed_record):
        product_line = self.contract.get('product_line')
        
        if product_line == 'standard':
            return self._map_standard_product_line(parsed_record)
        elif product_line == 'healthcare':
            return self._map_healthcare_product_line(parsed_record)
        elif product_line == 'financial':
            return self._map_financial_product_line(parsed_record)
        else:
            raise ValueError(f"Unknown product line: {product_line}")
    
    def _map_standard_product_line(self, record):
        # Extract standard fields
        return {
            'app_base': {
                'app_id': record.get('application/id'),
                'name': record.get('application/name')
            }
        }
    
    def _map_healthcare_product_line(self, record):
        # Extract healthcare-specific fields
        return {
            'provider_base': {
                'provider_id': record.get('provider/npi'),
                'credential_type': record.get('provider/credentials/type')
            }
        }
```

**Better: Use contract extension instead of code branching (see Pattern 2.4)**

### Pattern 2.4: Contract-Based Product-Line Variations

**When to use:** Different product lines with different field mappings (avoids code branching)

**Each product line has its own contract file:**
- CC (Credit Card): `config/mapping_contract.json`
- RL (ReCLending): `config/mapping_contract_rl.json`

**Runtime selection via `--product-line` flag:**
```python
# In production_processor.py
if self.product_line == "RL":
    self.mapping_contract_path = "config/mapping_contract_rl.json"
else:
    self.mapping_contract_path = "config/mapping_contract.json"

# Load the correct contract
self.mapping_contract = config_manager.load_mapping_contract(
    contract_path=self.mapping_contract_path
)

# MigrationEngine MUST receive the path to derive schema metadata correctly
engine = MigrationEngine(
    connection_string,
    mapping_contract_path=self.mapping_contract_path
)
```

**DataMapper works unchanged â€” different contract â†’ different mappings:**
```python
mapper = DataMapper(rl_contract)
result = mapper.map_record(rl_xml)
# Returns app_base, scores, indicators (RL tables)
```

**âš ï¸ Gotcha (Fixed Feb 2026):** `MigrationEngine.__init__()` previously called
`config_manager.load_mapping_contract()` WITHOUT a path, always loading the CC
contract. Fixed by adding `mapping_contract_path` parameter throughout the chain.

---

## 3. Validation Patterns

### Pattern 3.1: Pre-Processing Validation (XML Structure)

**When to use:** Validate XML is well-formed before parsing

```python
from xml_extractor.validation.validator import Validator

validator = Validator(mapping_contract)

# Validate XML structure
result = validator.validate_preprocessing(raw_xml_content)

if not result.is_valid:
    print(f"XML validation failed: {result.errors}")
    return result

# Continue to parsing
parsed = parser.parse(raw_xml_content)
```

### Pattern 3.2: Data Mapping Validation (Contract Compliance)

**When to use:** Validate all contract-required fields present and correctly typed

```python
# After parsing and mapping
result = validator.validate_mapping(mapped_data, mapping_contract)

if not result.is_valid:
    print(f"Mapping validation failed: {result.errors}")
    # Log which fields are missing or incorrectly typed
    return result

# Continue to database insertion
engine.migrate(mapped_data)
```

### Pattern 3.3: Database Constraint Validation (FK Integrity)

**When to use:** Verify FK relationships satisfied before insertion

```python
# After mapping, before insertion
result = validator.validate_database_constraints(
    mapped_data,
    target_schema=mapping_contract['target_schema'],
    connection=db_connection
)

if not result.is_valid:
    print(f"Database validation failed: {result.errors}")
    # Duplicate detected or FK parent missing
    return result

# Safe to insert
engine.migrate(mapped_data)
```

### Pattern 3.4: Custom Validation Rule (Product-Line-Specific)

**When to use:** Domain-specific validation beyond contract requirements

**Add to mapping_contract.json:**
```json
{
  "validation_rules": {
    "provider_base": [
      {
        "rule": "credential_count_gt_zero",
        "message": "Provider must have at least one credential"
      },
      {
        "rule": "npi_format",
        "message": "NPI must be 10-digit number"
      }
    ]
  }
}
```

**Implement in Validator:**
```python
class Validator:
    def _validate_custom_rules(self, record, target_table, rules):
        """Apply contract-defined custom validation rules"""
        
        errors = []
        
        for rule_config in rules:
            rule_name = rule_config['rule']
            
            if rule_name == 'credential_count_gt_zero':
                if 'credentials' not in record or len(record['credentials']) == 0:
                    errors.append(rule_config['message'])
            
            elif rule_name == 'npi_format':
                npi = record.get('npi', '')
                if not (len(npi) == 10 and npi.isdigit()):
                    errors.append(rule_config['message'])
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors)
```

---

## 4. Database Patterns

### Pattern 4.1: Basic Atomic Transaction

**When to use:** Insert multiple tables for one application (all-or-nothing)

```python
from xml_extractor.database.migration_engine import MigrationEngine

# CC pipeline (default contract)
engine = MigrationEngine(connection_string)

# RL pipeline (explicit contract path)
engine = MigrationEngine(
    connection_string,
    mapping_contract_path='config/mapping_contract_rl.json'
)

# One transaction per application
with engine.get_connection(app_id) as conn:
    # All inserts use same connection (not auto-commit)
    
    # Insert in FK order
    engine.insert_table('app_base', app_data['app_base'], conn)
    engine.insert_table('contact_base', app_data['contact_base'], conn)
    engine.insert_table('contact_address', app_data['contact_address'], conn)
    engine.insert_table('processing_log', audit_entry, conn)
    
    # conn.commit() called automatically on exit
    # or conn.rollback() if any insert fails

# If crash or error, entire transaction rolled back (no orphans)
```

### Pattern 4.2: Bulk Insert with Batch Size

**When to use:** Insert many applications efficiently

```python
# MigrationEngine handles batching internally
engine.migrate(
    app_records=[app1_data, app2_data, app3_data, ...],
    batch_size=1000,  # Proven optimal for this setup
    workers=4  # One per CPU core
)

# Result: 1000 apps per batch, 4 parallel workers
# Performance: ~2000 apps/min on local laptop
```

### Pattern 4.3: Resume with Duplicate Detection

**When to use:** Retry failed apps without creating duplicates

```python
# Get apps that haven't completed (using cursor-based pagination)
query = f"""
SELECT TOP @batch_size app_id, xml_content
FROM [{source_schema}].[app_xml]
WHERE app_id > @last_app_id
  AND app_id NOT IN (
    SELECT app_id FROM [{target_schema}].[processing_log] WITH (NOLOCK)
    WHERE target_table = 'app_base'
      AND status IN ('success', 'failed')
  )
ORDER BY app_id ASC
"""

# Process these apps
for app_record in engine.fetch_resumable_apps(batch_size=1000):
    parsed = parser.parse(app_record['xml_content'])
    mapped = mapper.map_record(parsed)
    engine.migrate(mapped, app_id=app_record['app_id'])

# Effect:
# - Successful apps skipped (no duplicate)
# - Failed apps retried (can fix and resume)
# - New apps processed normally
```

### Pattern 4.4: Schema-Isolated Testing

**When to use:** Test product line in isolation without affecting production

```python
# In test setup
contract = {
    'target_schema': 'test_healthcare',  # Isolated schema (created by you beforehand)
    # ... rest of contract
}

engine = MigrationEngine(
    server='localhost\SQLEXPRESS',
    database='XmlConversionDB',
    target_schema='test_healthcare'  # Uses test schema
)

# Run test (inserts into [test_healthcare].[provider_base], etc.)
test_data = load_fixture('healthcare_provider.xml')
engine.migrate(test_data)

# Verify in test schema
cursor.execute("SELECT COUNT(*) FROM [test_healthcare].[provider_base]")
count = cursor.fetchone()[0]
assert count == 1

# In teardown: Do NOT drop schema
# The test schema should be created and cleaned up by you outside the application
# (Either manually or via DBA/IT operations, not via automated scripts)
```

**Important:** 
- Test schemas must be created **by you** before the test suite runs (not by the application)
- Do NOT use DDL (CREATE/DROP) statements in test code
- Clean up happens outside the application (manual or ops-driven)

---

## 5. Testing Patterns

### Pattern 5.1: Unit Test - Enum Mapping

**When to use:** Test isolated function behavior

```python
import pytest
from xml_extractor.mapping.data_mapper import DataMapper

@pytest.mark.unit
def test_enum_mapping_valid():
    """Test enum mapping with valid value"""
    contract = {
        'mappings': {
            'app_base': [{
                'column': 'status',
                'source_path': 'status',
                'enum_mappings': {'ACTIVE': 'A', 'INACTIVE': 'I'}
            }]
        }
    }
    
    mapper = DataMapper(contract)
    record = {'status': 'ACTIVE'}
    result = mapper.apply_enum_mappings(record)
    
    assert result['status'] == 'A'

@pytest.mark.unit
def test_enum_mapping_invalid():
    """Test enum mapping with missing value (returns None)"""
    contract = {
        'mappings': {
            'app_base': [{
                'column': 'status',
                'source_path': 'status',
                'enum_mappings': {'ACTIVE': 'A', 'INACTIVE': 'I'}
            }]
        }
    }
    
    mapper = DataMapper(contract)
    record = {'status': 'UNKNOWN'}  # Not in mapping
    result = mapper.apply_enum_mappings(record)
    
    # When enum mapping missing, column excluded (None value not inserted)
    assert 'status' not in result or result['status'] is None
```

### Pattern 5.2: Integration Test - End-to-End Pipeline

**When to use:** Verify full XMLâ†’Database pipeline works

```python
import pytest
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine

@pytest.mark.integration
def test_healthcare_provider_roundtrip(fixture_healthcare_xml, db_connection):
    """Test complete healthcare provider pipeline"""
    
    # Setup
    contract = load_contract('healthcare_provider')
    parser = XMLParser()
    mapper = DataMapper(contract)
    engine = MigrationEngine(target_schema='test_healthcare')
    
    # Parse
    parsed = parser.parse(fixture_healthcare_xml)
    assert parsed is not None, "XML parsing failed"
    
    # Map
    mapped = mapper.map_record(parsed)
    assert 'provider_base' in mapped, "provider_base not mapped"
    assert mapped['provider_base']['provider_id'] is not None
    
    # Migrate (insert into DB)
    engine.migrate(mapped)
    
    # Verify in database (data-driven assertion)
    cursor = db_connection.cursor()
    cursor.execute(
        f"SELECT COUNT(*) FROM [test_healthcare].[provider_base] WHERE provider_id = ?",
        (mapped['provider_base']['provider_id'],)
    )
    count = cursor.fetchone()[0]
    assert count == 1, "Provider not inserted"
    
    # Verify FK relationships
    cursor.execute(
        f"SELECT COUNT(*) FROM [test_healthcare].[provider_credentials] WHERE provider_id = ?",
        (mapped['provider_base']['provider_id'],)
    )
    credential_count = cursor.fetchone()[0]
    assert credential_count > 0, "Credentials not inserted"
    
    # Verify atomicity (all tables succeeded)
    cursor.execute(
        f"SELECT status FROM [test_healthcare].[processing_log] WHERE app_id = ?",
        (mapped['provider_base']['provider_id'],)
    )
    status = cursor.fetchone()[0]
    assert status == 'success', f"Processing log shows status={status}"

@pytest.fixture
def fixture_healthcare_xml():
    """Load test XML for healthcare provider"""
    with open('tests/fixtures/healthcare_provider.xml', 'r') as f:
        return f.read()
```

### Pattern 5.3: Test Fixture - Schema Isolation

**When to use:** Tests for new product lines (schema must be created by you beforehand)

```python
import pytest
from pyodbc import connect

@pytest.fixture(scope='function')
def test_schema_healthcare(db_connection):
    """Use isolated test schema for healthcare tests
    
    NOTE: This fixture assumes test schema [test_healthcare] 
    already exists and is empty. Create it before running tests.
    
    The application will NOT create or drop schemas.
    """
    
    # Verify test schema exists (it should, created by you)
    cursor = db_connection.cursor()
    cursor.execute("""
        SELECT 1 FROM sys.schemas WHERE name = 'test_healthcare'
    """)
    
    if not cursor.fetchone():
        raise RuntimeError(
            "Test schema [test_healthcare] not found. "
            "Create it manually before running tests. "
            "The application will not create DDL structures."
        )
    
    # Tables should also exist (created by you via SQL script)
    yield db_connection  # Test uses this connection
    
    # In teardown: Do NOT drop schema or tables
    # The test DBA or you manage cleanup outside the application
```

**Important Notes:**
- Test infrastructure (schemas, tables) must be created **by you** before tests run
- The application never executes DDL (CREATE/DROP/ALTER) statements
- Test cleanup is manual, not automated

---

## 6. Performance Testing Patterns

### Pattern 6.1: Throughput Baseline

**When to use:** Establish performance baseline for new product line

```python
import time
from xml_extractor.database.migration_engine import MigrationEngine

def measure_throughput(app_records, batch_size=1000, workers=4):
    """Measure throughput (records/min)"""
    
    engine = MigrationEngine(target_schema='sandbox')
    
    start_time = time.time()
    record_count = len(app_records)
    
    # Process all records
    engine.migrate(
        app_records=app_records,
        batch_size=batch_size,
        workers=workers
    )
    
    elapsed_seconds = time.time() - start_time
    throughput = (record_count / elapsed_seconds) * 60  # records/min
    
    print(f"Processed {record_count} records in {elapsed_seconds:.1f}s")
    print(f"Throughput: {throughput:.0f} records/min")
    
    # Compare to target
    TARGET = 3500  # records/min
    if throughput < TARGET:
        print(f"âš ï¸  Below target ({TARGET} records/min)")
        print("   â†’ Measure batch-size sensitivity")
        print("   â†’ Check worker concurrency")
        print("   â†’ Profile query plans")
    else:
        print(f"âœ“ Meets target ({TARGET} records/min)")
    
    return throughput

# Usage
app_records = load_1000_test_records()
baseline = measure_throughput(app_records)
# Typical results: ~2,700/min (DEV RDS), ~1,500/min (local SQLExpress)
```

### Pattern 6.2: Batch-Size Tuning

**When to use:** Find optimal batch-size for your hardware

```python
def tune_batch_size(test_records_5000):
    """Find optimal batch-size through measurement"""
    
    batch_sizes = [20, 50, 100, 500, 1000, 2000]
    results = {}
    
    for batch_size in batch_sizes:
        throughput = measure_throughput(
            app_records=test_records_5000,
            batch_size=batch_size,
            workers=4
        )
        results[batch_size] = throughput
        print(f"  Batch-size {batch_size:4d}: {throughput:6.0f} records/min")
    
    optimal_size = max(results, key=results.get)
    print(f"\nâœ“ Optimal batch-size: {optimal_size} ({results[optimal_size]:.0f} records/min)")
    
    return optimal_size

# Results from this codebase:
# Batch-size   20:    400 records/min (too small, overhead)
# Batch-size   50:    800 records/min
# Batch-size  100:   1200 records/min
# Batch-size  500:   1800 records/min
# Batch-size 1000:   2000 records/min â† OPTIMAL
# Batch-size 2000:   1900 records/min (memory pressure)
```

---

## 7. Common Pattern Mistakes

### âŒ WRONG: Mixing Contracts and Code

```python
# Mapping defined in code (don't do this)
if app_type == 'healthcare':
    field_mapping = {'npi': 'provider_id', ...}
elif app_type == 'financial':
    field_mapping = {'account_id': 'acct_id', ...}

# Next person doesn't know if this is code or config
# Can't be changed without code deployment
```

### âœ… RIGHT: Contract-Driven, Code-Agnostic

```python
# All mappings in config/mapping_contract.json
contract = {
    'product_line': 'healthcare',
    'mappings': {
        'provider_base': [{
            'column': 'provider_id',
            'source_path': 'provider/npi'
        }]
    }
}

# Code just follows the contract (generic)
mapper = DataMapper(contract)
result = mapper.map_record(parsed_xml)
```

### âŒ WRONG: Testing Code, Not Behavior

```python
def test_mapper():
    mapper = DataMapper(contract)
    result = mapper.map_record(input_data)
    
    assert result is not None  # Useless
    assert isinstance(result, dict)  # Testing Python, not domain
    assert 'app_base' in result  # Maybe, but doesn't verify correctness
```

### âœ… RIGHT: Testing Domain Behavior

```python
def test_mapper_inserts_correct_data():
    mapper = DataMapper(contract)
    result = mapper.map_record(input_data)
    
    # Verify domain behavior: mapped values are correct
    assert result['app_base']['provider_id'] == 'NPI123456'  # Correct mapping
    assert result['app_base']['status'] == 'A'  # Enum translated
    assert 'calculated_at' in result['app_base']  # Calculated field present
```

---

## 8. Where to Find More Examples

- **Parsing examples:** `xml_extractor/parsing/xml_parser.py`
- **Mapping examples:** `xml_extractor/mapping/data_mapper.py`
- **Validation examples:** `xml_extractor/validation/validator.py`
- **Database examples:** `xml_extractor/database/migration_engine.py`
- **Test examples:** `tests/integration/test_end_to_end.py`
- **Fixtures:** `tests/fixtures/`

---

## References
- [system-constraints](../system-constraints/SKILL.md) - Non-negotiable principles for pattern usage
- [decision-frameworks](../decision-frameworks/SKILL.md) - When to use which pattern
- [System code](../../../xml_extractor/) - Reference implementations

