# Enum Handling Guide for Credit Application Processing

## Overview
This guide explains the enum handling strategy for processing Provenir XML documents into the credit application database schema.

## Core Principle: NULL-Friendly Approach

Most enum columns in the database schema allow NULL values. When an XML attribute is missing or empty, we **do not include that column in the INSERT statement**, allowing the database to set it to NULL.

## Enum Handling Categories

### 1. Standard Enums (Allow NULL)
**Behavior**: Missing XML attribute → Column not included in INSERT → Database sets to NULL

**Examples**:
- `status_enum` (Request/@Status)
- `app_source_enum` (application/@app_source_ind)  
- `decision_enum` (app_product/@decision_tp_c)
- `process_enum` (Request/@Process)
- `priority_enum` (Request/@Priority)
- `verification_source_enum` (application/@verification_source)
- `ssn_match_type_enum` (application/@ssn_match_flag)
- `fraud_type_enum` (contact/@fraud_ind)
- `ownership_type_enum` (contact_address/@ownership_tp_c)
- `income_type_enum` (contact_employment/@b_primary_income_source_tp_c)
- `other_income_type_enum` (contact_employment/@b_other_income_source_tp_c)

### 2. Required Enum with Default (NOT NULL Column)
**Behavior**: Missing XML attribute → Use default value

**Example**:
- `population_assignment_enum` (application/@population_assignment)
  - Default value: 229 (empty string mapping)
  - This column has NOT NULL constraint in database

### 3. Critical Enums (Record-Level Validation)
**Behavior**: Missing XML attribute → Skip entire record insert for that table

**Examples**:
- `contact_type_enum` (contact/@ac_role_tp_c)
  - Missing → Abandon entire application processing
  - Required to determine if contact is Primary (PR) or Authorized User (AUTH)
  
- `address_type_enum` (contact_address/@address_tp_c)  
  - Missing → Skip this address record insert
  - Required to determine if address is Current (CURR) or Previous (PREV)
  
- `employment_type_enum` (contact_employment/@employment_tp_c)
  - Missing → Skip this employment record insert  
  - Required to determine if employment is Current (CURR) or Previous (PREV)

## Processing Logic

### Application Level
```
IF missing app_id OR missing con_id_primary:
    ABANDON entire application processing
    
IF missing contact_type_enum for primary contact:
    ABANDON entire application processing
    
ELSE:
    Process application and contacts
```

### Contact Address Level  
```
FOR each contact_address in XML:
    IF missing address_tp_c:
        SKIP this address record
    ELSE:
        INSERT contact_address record
```

### Contact Employment Level
```
FOR each contact_employment in XML:
    IF missing employment_tp_c:
        SKIP this employment record  
    ELSE:
        INSERT contact_employment record
```

### Standard Column Level
```
FOR each mapped column:
    IF XML attribute exists AND has value:
        Include column in INSERT with converted value
    ELSE IF column is population_assignment_enum:
        Include column in INSERT with default value (229)
    ELSE:
        Exclude column from INSERT (allows NULL)
```

## Secondary Contact Handling

The secondary contact (con_id_auth) is completely optional:

- **XML present**: Process secondary contact with same validation rules as primary
- **XML missing**: Skip secondary contact processing entirely
- **No separate validation needed**: Existing con_id_validation rules apply when processing

## Benefits of This Approach

1. **Database Flexibility**: Allows NULL values for optional enum fields
2. **Data Integrity**: Critical enums ensure required relationships exist  
3. **Graceful Degradation**: Missing optional data doesn't break processing
4. **Performance**: Fewer INSERT columns when data is sparse
5. **Maintainability**: Clear rules for when to include/exclude columns

## Implementation Notes

- **INSERT statement generation**: Dynamically build column list based on available XML attributes
- **Enum validation**: Check enum mappings exist before INSERT, use NULL for unmapped values (except population_assignment_enum)
- **Transaction integrity**: Wrap related INSERTs in transactions to maintain FK relationships
- **Error handling**: Log skipped records for audit trail and troubleshooting