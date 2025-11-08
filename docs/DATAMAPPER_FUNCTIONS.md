## DataMapper Functions Grouped by Purpose (~2,287 lines)

### **CONTRACT INTERROGATION** (New - added by our refactoring)
- `_find_filter_rule_by_element_type()` - Find filter rules by element type
- `_get_contact_type_config_from_contract()` - Extract (attribute_name, valid_values) for contacts
- `_get_contact_type_priority_map()` - Build priority map from contact type array order
- `_get_address_type_config_from_contract()` - Extract (attribute_name, preferred_value) for addresses

### **INITIALIZATION & CACHING**
- `__init__()` - Initialize mapper with contract and caching
- `_build_enum_type_cache()` - Pre-build enum type lookup cache

### **PUBLIC ORCHESTRATION API**
- `apply_mapping_contract()` - Main entry point for XML→DB transformation
- `map_xml_to_database()` - Map XML to database records by table
- `get_transformation_stats()` - Return transformation statistics
- `get_validation_errors()` - Return validation errors

### **PRE-FLIGHT VALIDATION**
- `_extract_app_id()` - Extract application ID from XML
- `_pre_flight_validation()` - Validate XML has required elements before processing

### **CONTACT EXTRACTION & FILTERING**
- `_extract_valid_contacts()` - Extract and deduplicate contacts by type priority
- `_navigate_to_contacts()` - Navigate to contact elements in XML
- `_parse_all_contacts_from_root()` - Parse all contact elements from XML root
- `_get_attribute_case_insensitive()` - Get XML attribute with case-insensitive matching

### **XML VALUE EXTRACTION**
- `_extract_value_from_xml()` - Extract value from XML using XPath
- `_extract_from_curr_address_only()` - Extract from preferred address (contract-driven)
- `_extract_from_last_valid_pr_contact()` - Extract from primary contact (contract-driven)

### **FIELD TRANSFORMATION PIPELINE**
- `_apply_field_transformation()` - Apply transformation chain to field value
- `_apply_single_mapping_type()` - Apply single mapping type transformation
- `_apply_calculated_field_mapping()` - Evaluate calculated field expressions

### **ENUM PROCESSING**
- `_apply_enum_mapping()` - Map string value to enum integer
- `_determine_enum_type()` - Determine enum type from column name

### **TYPE TRANSFORMATIONS**
- `transform_data_types()` - Main type transformation dispatcher
- `_transform_to_string()` - Transform to varchar/nvarchar
- `_transform_to_integer()` - Transform to int/smallint/bigint
- `_transform_to_decimal()` - Transform to decimal/numeric
- `_transform_to_decimal_with_precision()` - Transform decimal with precision/scale
- `_transform_to_datetime()` - Transform to datetime/datetime2
- `_transform_to_bit()` - Transform to bit (0/1)
- `_transform_to_boolean()` - Transform to boolean

### **BIT CONVERSIONS**
- `_apply_bit_conversion()` - Convert Y/N to bit
- `_apply_boolean_to_bit_conversion()` - Convert boolean to bit
- `_apply_bit_conversion_with_default_tracking()` - Bit conversion with default tracking

### **NUMERIC EXTRACTION**
- `_extract_numbers_only()` - Extract only numeric characters
- `_extract_numeric_value()` - Extract numeric value from formatted string
- `_extract_numeric_value_preserving_decimals()` - Extract numeric preserving decimals

### **DATETIME UTILITIES**
- `_clean_datetime_string()` - Clean datetime string for parsing

### **RECORD BUILDING**
- `_group_mappings_by_table()` - Group field mappings by target table
- `_process_table_mappings()` - Process mappings for specific table
- `_create_record_from_mappings()` - Create single record from field mappings
- `_should_skip_record()` - Determine if record should be skipped (keys-only)
- `_should_exclude_conditional_defaults()` - Exclude conditional default columns
- `_extract_contact_address_records()` - Extract multiple address records per contact
- `_extract_contact_employment_records()` - Extract multiple employment records per contact
- `handle_nested_elements()` - Handle nested child element extraction

### **CONTEXT BUILDING**
- `_build_app_level_context()` - Build flattened XML context for calculated fields

### **DEFAULT VALUE HANDLING**
- `_get_default_for_mapping()` - Get default value for field mapping
- `_get_fallback_for_mapping()` - Get fallback value on transformation error
- `_get_fallback_value()` - Get fallback value by target type
- `_is_transformation_default()` - Check if value is transformation default

### **POST-PROCESSING (Stubs)**
- `_apply_relationships()` - Apply relationship rules (placeholder)
- `_apply_calculated_fields()` - Apply calculated field rules (placeholder)
- `_validate_data_integrity()` - Validate data integrity (placeholder)

---

## Key Observations

### **MAJOR DUPLICATION PATTERNS:**

1. **Contract Interrogation Pattern (NEW)** - All follow same structure:
   - Find filter rule by element_type
   - Extract required_attributes dict
   - Loop through to find list-valued attribute
   - Return (attribute_name, values/preferred_value)
   - **DUPLICATION**: `_get_contact_type_config_from_contract()` and `_get_address_type_config_from_contract()` are 90% identical

2. **Element Extraction Pattern** - Multiple similar methods:
   - `_extract_from_curr_address_only()` - Extract from preferred address
   - `_extract_from_last_valid_pr_contact()` - Extract from primary contact
   - `_extract_contact_address_records()` - Extract all addresses
   - `_extract_contact_employment_records()` - Extract all employment
   - **DUPLICATION**: All navigate element hierarchies and extract values similarly

---