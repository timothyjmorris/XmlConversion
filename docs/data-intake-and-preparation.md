# Data Intake and Preparation Pipeline

## Overview

The data intake and preparation pipeline is the **most critical component** of the XML extraction system. Since bulk inserts use batch-level atomicity (entire batch fails if one record fails), every piece of data must be perfectly prepared before reaching the database.

## Pipeline Architecture

```
Raw XML → Parse → Transform → Validate → Relationship Resolution → Final Validation → Bulk Insert
   ↓        ↓        ↓         ↓              ↓                    ↓              ↓
Source   Extract  Convert   Check        Generate FKs         Batch Check    Database
Data     Elements  Types    Formats      Link Records        All Perfect     Success
```

## Phase 1: XML Parsing and Extraction

### XMLParser Responsibilities
- **Stream processing**: Handle large XML files without loading entirely into memory
- **Namespace handling**: Resolve XML namespaces and prefixes
- **Element extraction**: Navigate complex nested XML structures
- **Attribute extraction**: Capture both element text and attribute values

### Example: Provenir Credit Application XML
```xml
<Provenir>
    <Request ID="154284">
        <CustData>
            <application app_receive_date="05/20/2016" campaign_num="P2F" solicitation_num="06165216226T" ssn_match_flag="Y">
                <app_product decision_tp_c="NONE" prescreen_fico_score="565" fraud_rev_ind="N"/>
                <contact con_id="277449" ac_role_tp_c="PR" last_name="WILLIAMS" first_name="JOHN" birth_date="12/17/1968" ssn="666621502" email="johnwiliams@xmlconversion.org">
                    <contact_address address_tp_c="CURR" cell_phone="8012223333" residence_monthly_pymnt="500.00" street_number="4815" street_name="S 16TH" city="FARGO" state="ND" zip="58103"/>
                    <contact_employment employment_tp_c="CURR" b_salary="75000"/>
                </contact>
            </application>
        </CustData>
    </Request>
</Provenir>
```

### Parsed Output (Raw Dictionary)
```python
{
    "request_id": "154284",
    "app_receive_date": "05/20/2016",
    "campaign_num": "P2F",
    "solicitation_num": "06165216226T",
    "ssn_match_flag": "Y",
    "decision_tp_c": "NONE",
    "prescreen_fico_score": "565",
    "fraud_rev_ind": "N",
    "con_id": "277449",
    "ac_role_tp_c": "PR",
    "last_name": "WILLIAMS",
    "first_name": "JOHN",
    "birth_date": "12/17/1968",
    "ssn": "666621502",
    "email": "johnwiliams@xmlconversion.org",
    "address_tp_c": "CURR",
    "cell_phone": "8012223333",
    "residence_monthly_pymnt": "500.00",
    "street_number": "4815",
    "street_name": "S 16TH",
    "city": "FARGO",
    "state": "ND",
    "zip": "58103",
    "employment_tp_c": "CURR",
    "b_salary": "75000"
}
```

## Phase 2: Data Transformation and Type Conversion

### DataMapper Responsibilities
- **Type conversion**: String → appropriate database types
- **Format standardization**: Consistent formats for phones, SSNs, dates
- **Enum mapping**: Text values → database codes
- **Length validation**: Ensure strings fit target columns
- **Null handling**: Convert empty strings to proper nulls

### Critical Transformations

#### 1. Data Type Conversion
```python
# BEFORE (from XML - all strings)
{
    "prescreen_fico_score": "565",           # String
    "b_salary": "75000",                     # String  
    "birth_date": "12/17/1968",             # String
    "ssn_match_flag": "Y",                  # String
    "residence_monthly_pymnt": "500.00"     # String
}

# AFTER (database-ready types)
{
    "prescreen_fico_score": 565,                        # int
    "b_salary": Decimal("75000.00"),                    # decimal(10,2)
    "birth_date": datetime(1968, 12, 17),               # datetime
    "ssn_match_flag": True,                             # bit/boolean
    "residence_monthly_pymnt": Decimal("500.00")        # decimal(8,2)
}
```

#### 2. Format Standardization
```python
# BEFORE (inconsistent formats)
{
    "ssn": "666621502",             # Raw digits
    "cell_phone": "8012223333",     # Raw digits
    "zip": "58103",                 # 5-digit zip
    "birth_date": "12/17/1968"      # MM/DD/YYYY format
}

# AFTER (standardized)
{
    "ssn": "666621502",             # Validated 9 digits, fits char(9)
    "cell_phone": "8012223333",     # Validated 10 digits, fits char(10)  
    "zip": "58103",                 # Validated 5 digits, fits char(5)
    "birth_date": "1968-12-17"      # ISO format YYYY-MM-DD
}
```

#### 3. Enum and Lookup Mapping
```python
# BEFORE (text values)
{
    "state": "ND",                  # State abbreviation
    "decision_tp_c": "NONE",        # Decision type code
    "ac_role_tp_c": "PR",           # Account role type code
    "address_tp_c": "CURR",         # Address type code
    "employment_tp_c": "CURR"       # Employment type code
}

# AFTER (database IDs/codes)
{
    "state_id": 35,                 # FK to states lookup (ND = 35)
    "decision_type_id": 1,          # FK to decision_types (NONE = 1)
    "account_role_id": 2,           # FK to account_roles (PR = 2)
    "address_type_id": 1,           # FK to address_types (CURR = 1)
    "employment_type_id": 1         # FK to employment_types (CURR = 1)
}
```

#### 4. Length Validation and Truncation
```python
# BEFORE (potentially oversized)
{
    "first_name": "JOHN",                   # 4 chars - fits
    "last_name": "WILLIAMS",                # 8 chars - fits
    "email": "johnwiliams@xmlconversion.org",  # 31 chars
    "street_name": "S 16TH"                 # 6 chars - fits
}

# AFTER (validated against schema limits)
{
    "first_name": "JOHN",                   # Fits varchar(50)
    "last_name": "WILLIAMS",                # Fits varchar(50)
    "email": "johnwiliams@xmlconversion.org", # Fits varchar(100)
    "street_name": "S 16TH"                 # Fits varchar(50)
}
```

### Transformation Rules Engine

#### Configuration-Driven Transformations
```python
# From mapping contract
{
    "xml_path": "application/@ssn_match_flag",
    "target_column": "ssn_match_flag", 
    "data_type": "bit",
    "transformation": "y_n_to_bit",     # Y/N → True/False
    "mapping_type": "char_to_bit"
}

# Transformation function
def transform_y_n_to_bit(value: str) -> bool:
    if value.upper() == 'Y':
        return True
    elif value.upper() == 'N':
        return False
    else:
        raise ValueError(f"Invalid Y/N value: {value}")
```

## Phase 3: Relationship Resolution and Foreign Keys

### Parent-Child Relationship Handling

#### Example: Provenir XML Hierarchy and Cascading IDs
```xml
<contact con_id="277449" ac_role_tp_c="PR" last_name="WILLIAMS" first_name="JOHN">
    <contact_address address_tp_c="CURR" cell_phone="8012223333" street_number="4815"/>
    <contact_employment employment_tp_c="CURR" b_salary="75000"/>
</contact>
```

```python
# XML hierarchy processing with cascading con_id
def process_contact_element(contact_element, request_id):
    """Process contact and its children, cascading con_id from parent."""
    
    # Extract con_id from parent contact element
    con_id = contact_element.get('con_id')
    ac_role_tp_c = contact_element.get('ac_role_tp_c')
    
    # Validation: Skip contact if missing required attributes
    if not con_id or not ac_role_tp_c:
        logger.warning(f"Skipping contact - missing con_id or ac_role_tp_c")
        return None, [], []
    
    # Process contact_base record
    contact_base_record = {
        "con_id": con_id,                    # From parent element
        "request_id": request_id,            # Cascaded from application
        "ac_role_tp_c": ac_role_tp_c,
        "first_name": contact_element.get('first_name'),
        "last_name": contact_element.get('last_name'),
        # ... other contact fields
    }
    
    # Process child elements with cascaded con_id
    address_records = []
    employment_records = []
    
    for address_elem in contact_element.findall('contact_address'):
        address_tp_c = address_elem.get('address_tp_c')
        
        # Validation: Skip address if missing required enum
        if not address_tp_c:
            logger.warning(f"Skipping contact_address for con_id {con_id} - missing address_tp_c")
            continue
            
        address_record = {
            "con_id": con_id,                # Cascaded from parent contact
            "address_tp_c": address_tp_c,
            "cell_phone": address_elem.get('cell_phone'),
            "street_number": address_elem.get('street_number'),
            # ... other address fields
        }
        address_records.append(address_record)
    
    for employment_elem in contact_element.findall('contact_employment'):
        employment_tp_c = employment_elem.get('employment_tp_c')
        
        # Validation: Skip employment if missing required enum
        if not employment_tp_c:
            logger.warning(f"Skipping contact_employment for con_id {con_id} - missing employment_tp_c")
            continue
            
        employment_record = {
            "con_id": con_id,                # Cascaded from parent contact
            "employment_tp_c": employment_tp_c,
            "b_salary": employment_elem.get('b_salary'),
            # ... other employment fields
        }
        employment_records.append(employment_record)
    
    return contact_base_record, address_records, employment_records

# Final database records with cascaded relationships
app_base_record = {
    "request_id": "154284",              # Primary key (app_id)
    "app_receive_date": datetime(2016, 5, 20),
    "campaign_num": "P2F",
    "solicitation_num": "06165216226T"
}

contact_base_record = {
    "con_id": "277449",                  # Primary key (from XML)
    "request_id": "154284",              # Foreign key to app_base
    "ac_role_tp_c": "PR",               # Required enum
    "first_name": "JOHN",
    "last_name": "WILLIAMS"
}

contact_address_record = {
    "con_id": "277449",                  # Cascaded from parent contact
    "address_tp_c": "CURR",             # Required enum
    "cell_phone": "8012223333",
    "street_number": "4815",
    "street_name": "S 16TH"
}

contact_employment_record = {
    "con_id": "277449",                  # Cascaded from parent contact  
    "employment_tp_c": "CURR",          # Required enum
    "b_salary": Decimal("75000.00")
}
```

#### Cascading ID Strategy and Natural Keys

The Provenir XML uses natural keys that cascade through the hierarchy:

```python
def extract_cascading_ids(xml_element):
    """Extract IDs that cascade through XML hierarchy."""
    
    # Level 1: Application ID (top level)
    request_elem = xml_element.find('.//Request')
    app_id = request_elem.get('ID')  # e.g., "154284"
    
    # Level 2: Contact ID (cascades to children)
    contact_elem = xml_element.find('.//contact')
    con_id = contact_elem.get('con_id')  # e.g., "277449"
    
    # Level 3: Child elements inherit parent IDs
    return {
        'app_id': app_id,        # Used in: app_base (PK), contact_base (FK)
        'con_id': con_id         # Used in: contact_base (PK), contact_address (FK), contact_employment (FK)
    }

# ID Cascading Pattern:
# app_id="154284" → contact_base.request_id (FK)
# con_id="277449" → contact_address.con_id (FK)
# con_id="277449" → contact_employment.con_id (FK)
```

#### Identity Column Handling
```python
# For tables with IDENTITY columns - use natural keys from XML
contact_base_record = {
    "con_id": "277449",              # Natural key from XML (not IDENTITY)
    "request_id": "154284",          # Foreign key to app_base
    "first_name": "JOHN",
    "last_name": "WILLIAMS"
}

# Child records use the same natural key
contact_address_record = {
    "con_id": "277449",              # Same natural key (foreign key)
    "address_type_id": 1,            # CURR mapped to lookup ID
    "street_number": "4815",
    "street_name": "S 16TH",
    "city": "FARGO"
}

contact_employment_record = {
    "con_id": "277449",              # Same natural key (foreign key)
    "employment_type_id": 1,         # CURR mapped to lookup ID
    "b_salary": Decimal("75000.00")
}
```

## Phase 4: Data Validation and Quality Checks

### XML Element Validation and Filtering Rules

#### Critical Validation Rules for Provenir XML
Before any data transformation, elements must be validated and filtered based on required attributes. This filtering is centralized and follows data-model.md rules strictly:

```python
def validate_and_filter_xml_elements(xml_root):
    """Apply Provenir-specific validation rules to filter valid elements."""
    
    valid_contacts = []
    valid_addresses = []
    valid_employments = []
    
    # Extract app_id from Request element
    request_elem = xml_root.find('.//Request')
    app_id = request_elem.get('ID') if request_elem is not None else None
    
    # Validation: Application must have app_id
    if not app_id:
        raise ValidationError("Application missing required app_id (Request/@ID)")
    
    # Process each contact element
    for contact_elem in xml_root.findall('.//contact'):
        con_id = contact_elem.get('con_id')
        ac_role_tp_c = contact_elem.get('ac_role_tp_c')
        
        # Rule: Ignore contact if missing con_id OR ac_role_tp_c
        if not con_id or not ac_role_tp_c:
            logger.warning(f"Ignoring contact - con_id: {con_id}, ac_role_tp_c: {ac_role_tp_c}")
            continue
        
        # Valid contact - add to processing list
        valid_contacts.append({
            'element': contact_elem,
            'con_id': con_id,
            'app_id': app_id  # Cascade app_id to contact
        })
        
        # Process child address elements
        for address_elem in contact_elem.findall('contact_address'):
            address_tp_c = address_elem.get('address_tp_c')
            
            # Rule: Ignore address if missing address_tp_c
            if not address_tp_c:
                logger.warning(f"Ignoring contact_address for con_id {con_id} - missing address_tp_c")
                continue
            
            valid_addresses.append({
                'element': address_elem,
                'con_id': con_id,      # Cascaded from parent contact
                'app_id': app_id       # Cascaded from application
            })
        
        # Process child employment elements  
        for employment_elem in contact_elem.findall('contact_employment'):
            employment_tp_c = employment_elem.get('employment_tp_c')
            
            # Rule: Ignore employment if missing employment_tp_c
            if not employment_tp_c:
                logger.warning(f"Ignoring contact_employment for con_id {con_id} - missing employment_tp_c")
                continue
            
            valid_employments.append({
                'element': employment_elem,
                'con_id': con_id,      # Cascaded from parent contact
                'app_id': app_id       # Cascaded from application
            })
    
    # Final validation: Application must have at least one valid contact
    if not valid_contacts:
        raise ValidationError(f"Application {app_id} has no valid contacts (missing con_id or ac_role_tp_c)")
    
    return {
        'app_id': app_id,
        'contacts': valid_contacts,
        'addresses': valid_addresses,
        'employments': valid_employments
    }
```

#### Element Filtering Summary
| Element | Required Attributes | Valid Values | Action if Missing/Invalid |
|---------|-------------------|--------------|---------------------------|
| `<Request>` | `ID` (app_id) | Any integer | **Reject entire application** |
| `<contact>` | `con_id` AND `ac_role_tp_c` | ac_role_tp_c: "PR" or "AUTH" | **Ignore contact and all children** |
| `<contact_address>` | `address_tp_c` | "CURR", "PREV", "PATR" | **Ignore this address only** |
| `<contact_employment>` | `employment_tp_c` | "CURR", "PREV" | **Ignore this employment only** |

#### Last Valid Contact Logic
For duplicate `con_id` + `ac_role_tp_c` combinations, use the **last occurrence** in document order (not first_name comparison).

#### Graceful Degradation Strategy
- **Application level**: Must have `app_id` and at least one valid contact
- **Contact level**: Must have both `con_id` and `ac_role_tp_c` 
- **Address/Employment level**: Can be missing (outliers) - application still processes
- **Cascading IDs**: `app_id` → `con_id` → address/employment records

### Pre-Insert Validation (Critical!)

#### 1. Schema Compliance Validation
```python
def validate_schema_compliance(records: List[Dict], table_schema: Dict) -> ValidationResult:
    """Ensure every record matches target schema exactly."""
    
    for record in records:
        for column_name, column_def in table_schema.items():
            value = record.get(column_name)
            
            # Check required fields
            if column_def['nullable'] == False and value is None:
                raise ValidationError(f"Required field {column_name} is null")
            
            # Check data types
            if value is not None and not isinstance(value, column_def['python_type']):
                raise ValidationError(f"Wrong type for {column_name}: expected {column_def['python_type']}")
            
            # Check string lengths
            if column_def['data_type'] == 'varchar' and len(str(value)) > column_def['max_length']:
                raise ValidationError(f"Value too long for {column_name}: {len(str(value))} > {column_def['max_length']}")
```

#### 2. Referential Integrity Validation
```python
def validate_foreign_keys(records: List[Dict], fk_constraints: Dict) -> ValidationResult:
    """Ensure all foreign keys reference existing records."""
    
    for record in records:
        for fk_column, parent_table in fk_constraints.items():
            fk_value = record.get(fk_column)
            
            if fk_value is not None:
                # Check if parent record exists
                if not parent_record_exists(parent_table, fk_value):
                    raise ValidationError(f"Foreign key violation: {fk_column}={fk_value} not found in {parent_table}")
```

#### 3. Business Rule Validation
```python
def validate_business_rules(record: Dict, table_name: str) -> ValidationResult:
    """Apply business-specific validation rules based on table."""
    
    if table_name == 'app_base':
        # Application must have app_id (request_id)
        if not record.get('request_id'):
            raise ValidationError("Application missing required app_id")
    
    elif table_name == 'contact_base':
        # Contact must have both app_id and con_id
        if not record.get('request_id'):
            raise ValidationError("Contact missing required app_id")
        if not record.get('con_id'):
            raise ValidationError("Contact missing required con_id")
        
        # Validate ac_role_tp_c enum exists
        if not record.get('ac_role_tp_c'):
            raise ValidationError("Contact missing required ac_role_tp_c")
    
    elif table_name == 'contact_address':
        # Address must have con_id and address_tp_c
        if not record.get('con_id'):
            raise ValidationError("Address missing required con_id (cascaded from parent)")
        if not record.get('address_tp_c'):
            raise ValidationError("Address missing required address_tp_c")
    
    elif table_name == 'contact_employment':
        # Employment must have con_id and employment_tp_c
        if not record.get('con_id'):
            raise ValidationError("Employment missing required con_id (cascaded from parent)")
        if not record.get('employment_tp_c'):
            raise ValidationError("Employment missing required employment_tp_c")
    
    # Common validations across tables
    
    # FICO score range validation
    if record.get('prescreen_fico_score') and not (300 <= record['prescreen_fico_score'] <= 850):
        raise ValidationError(f"FICO score out of range: {record['prescreen_fico_score']}")
    
    # Date validation
    if record.get('birth_date'):
        age = calculate_age(record['birth_date'])
        if age < 18:
            raise ValidationError(f"Applicant too young: {age} years old")
    
    # Salary validation
    if record.get('b_salary') and record['b_salary'] <= 0:
        raise ValidationError(f"Invalid salary amount: {record['b_salary']}")
    
    # SSN validation
    if record.get('ssn') and len(record['ssn']) != 9:
        raise ValidationError(f"Invalid SSN length: {len(record['ssn'])} digits")
```

## Phase 5: Batch Preparation and Final Validation

### Batch Assembly
```python
def prepare_batch_for_insert(validated_records: List[Dict], batch_size: int = 1000) -> List[List[Dict]]:
    """Split validated records into insertion-ready batches."""
    
    batches = []
    for i in range(0, len(validated_records), batch_size):
        batch = validated_records[i:i + batch_size]
        
        # Final batch validation
        validate_batch_consistency(batch)
        validate_batch_size_limits(batch)
        
        batches.append(batch)
    
    return batches
```

### Final Pre-Insert Checks
```python
def validate_batch_consistency(batch: List[Dict]) -> None:
    """Ensure entire batch will succeed together."""
    
    # Check for duplicate primary keys within batch
    primary_keys = [record['request_id'] for record in batch if 'request_id' in record]
    if len(primary_keys) != len(set(primary_keys)):
        raise ValidationError("Duplicate request_id values in batch")
    
    # Check for duplicate contact IDs within batch
    contact_ids = [record['con_id'] for record in batch if 'con_id' in record]
    if len(contact_ids) != len(set(contact_ids)):
        raise ValidationError("Duplicate con_id values in batch")
    
    # Check for foreign key consistency within batch
    validate_intra_batch_relationships(batch)
    
    # Check memory usage
    estimated_memory = calculate_batch_memory_usage(batch)
    if estimated_memory > MAX_BATCH_MEMORY:
        raise ValidationError(f"Batch too large: {estimated_memory}MB > {MAX_BATCH_MEMORY}MB")
```

## Error Handling and Recovery Strategies

### Validation Error Categories

#### 1. **Fatal Errors** (Stop Processing)
- Invalid XML structure
- Missing required configuration
- Database connection failures
- Schema mismatches

#### 2. **Record-Level Errors** (Skip Record)
- Invalid data formats that can't be converted
- Business rule violations
- Missing required fields

#### 3. **Batch-Level Errors** (Retry with Smaller Batch)
- Memory limitations
- Transaction timeouts
- Temporary database issues

### Recovery Strategies

#### Dead Letter Queue
```python
def handle_problematic_records(failed_records: List[Dict], error_type: str) -> None:
    """Isolate problematic records for manual review."""
    
    dead_letter_file = f"failed_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(dead_letter_file, 'w') as f:
        json.dump({
            'error_type': error_type,
            'failed_count': len(failed_records),
            'records': failed_records
        }, f, indent=2)
    
    logger.error(f"Moved {len(failed_records)} failed records to {dead_letter_file}")
```

#### Batch Size Reduction
```python
def retry_with_smaller_batches(failed_batch: List[Dict], original_batch_size: int) -> None:
    """Retry failed batch with progressively smaller batch sizes."""
    
    retry_sizes = [original_batch_size // 2, original_batch_size // 4, 1]
    
    for batch_size in retry_sizes:
        try:
            sub_batches = split_into_batches(failed_batch, batch_size)
            for sub_batch in sub_batches:
                migration_engine.execute_bulk_insert(sub_batch, table_name)
            return  # Success
        except Exception as e:
            logger.warning(f"Retry with batch size {batch_size} failed: {e}")
    
    # All retries failed - move to dead letter queue
    handle_problematic_records(failed_batch, "batch_retry_exhausted")
```

## Performance Considerations

### Memory Management
- **Stream processing**: Don't load entire XML files into memory
- **Batch size tuning**: Balance performance vs. memory usage
- **Garbage collection**: Clear processed batches immediately

### Processing Speed Optimization
- **Parallel validation**: Validate multiple records simultaneously
- **Cached lookups**: Cache enum mappings and foreign key validations
- **Bulk operations**: Group similar transformations together

### Monitoring and Metrics
```python
# Track validation performance
validation_metrics = {
    'records_processed': 50000,
    'validation_time_seconds': 45.2,
    'records_per_second': 1106,
    'error_rate_percent': 2.1,
    'memory_usage_mb': 128
}
```

## Best Practices

### 1. **Fail Fast Principle**
- Validate XML structure before processing any records
- Check database connectivity before starting
- Verify mapping contracts are complete

### 2. **Data Quality First**
- Reject entire batches rather than allow partial data
- Log all transformation decisions for audit trails
- Maintain strict type safety throughout pipeline

### 3. **Comprehensive Logging**
```python
# Log every transformation decision
logger.info(f"Transformed {original_value} → {transformed_value} using rule {rule_name}")

# Log validation results
logger.info(f"Validated batch of {len(batch)} records for table {table_name}")

# Log performance metrics
logger.info(f"Processing rate: {records_per_second:.1f} records/second")
```

### 4. **Configuration-Driven Processing**
- All transformation rules defined in mapping contracts
- No hard-coded business logic in transformation code
- Easy to modify rules without code changes

## Conclusion

The data intake and preparation pipeline is where **data quality is won or lost**. Since bulk inserts use batch-level atomicity, every single record must be perfect before reaching the database. This makes the validation and transformation phases the most critical components of the entire system.

**Key Success Factors:**
- **Comprehensive validation** at every stage
- **Strict type safety** and format consistency  
- **Robust error handling** with clear recovery strategies
- **Performance optimization** without compromising data quality
- **Detailed logging** for troubleshooting and auditing

The pipeline's design philosophy: **"Perfect data, every time"** - because in a batch-atomic system, there's no room for "good enough."