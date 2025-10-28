# Credit Card Application Data Model

## Overview
This system extracts credit card application data from Provenir XML documents stored in the `app_xml` table and transforms it into a normalized relational structure for processing and analysis. The system supports comprehensive mapping of XML attributes to database columns with enum conversions, bit transformations, and data validation.

## Configuration Files
- **`mapping_contract.json`**: Complete mapping contract with XML paths, target tables, enum mappings, and validation rules
- **`create_destination_tables.sql`**: SQL script to create the target database schema
- **`insert_enum_values.sql`**: SQL script to populate enum lookup values
- **`validate_mapping_contract.sql`**: SQL script to validate schema compatibility
- **Sample XML files**: `sample-source-xml-*.xml` for testing and validation

## XML Source Structure
- **Root Element**: `<Provenir>` containing `<Request>` with application data
- **Key Identifiers**: 
  - `app_id`: `/Provenir/Request/@ID` (required)
  - `con_id` (primary): `/Provenir/Request/CustData/application/contact[@ac_role_tp_c='PR']/@con_id` (required)
  - `con_id` (auth user): `/Provenir/Request/CustData/application/contact[@ac_role_tp_c='AUTH']/@con_id` (optional)
- **Main Sections**:
  - Request metadata: `/Provenir/Request/` (Status, Process, LastUpdatedBy, etc.)
  - Application data: `/Provenir/Request/CustData/application/` (receive_date, app_source_ind, signature_ind, etc.)
  - Product data: `/Provenir/Request/CustData/application/app_product/` (decision data, scores, risk grades)
  - Contact data: `/Provenir/Request/CustData/application/contact/` (may have multiple with different ac_role_tp_c)
  - Address data: `/Provenir/Request/CustData/application/contact/contact_address/` (may have multiple per contact)
  - Employment data: `/Provenir/Request/CustData/application/contact/contact_employment/` (may have multiple per contact)
  - Pricing data: `/Provenir/Request/CustData/application/rmts_info/` (campaign, pricing tier, fees)
  - Comments: `/Provenir/Request/CustData/application/comments/` (processing notes and history)

## Database Schema

### Core Application Tables
- **`app_base`**: Primary application record with basic information
- **`app_operational_cc`**: Operational data (status, assignments, scores)
- **`app_transactional_cc`**: Temporary processing flags (cleared after decisioning)
- **`app_pricing_cc`**: Pricing and product configuration
- **`app_solicited_cc`**: Prescreen/solicitation data

### Contact Tables
- **`contact_base`**: Primary contact information
- **`contact_address`**: Address information (current, previous, etc.)
- **`contact_employment`**: Employment and income data

### Lookup Tables
- **`app_enums`**: Enumeration values for all coded fields
- **`report_results_lookup`**: Key-value pairs from credit reports
- **`historical_lookup`**: Legacy/retired field values

## Relationships
- `app_base` is the parent for all `app_*_cc` tables (1:1 relationship)
- `contact_base` links to `app_base` via `app_id` (1:many relationship)
- `contact_address` and `contact_employment` link to `contact_base` via `con_id`
- All enum fields reference `app_enums` table

## Data Transformation Rules

### Enum Mappings
The `mapping_contract.json` file contains mappings for all enum fields. The `enum_mappings` section defines the mapping between XML attributes and enum values. The `enum_mappings` section also defines the default value for missing XML attributes. This contract is derived from source SQL `insert_enum_values.sql` with the mapping in `migrate_table_logic.sql`

### Type Conversions
- **Char to Bit**: Y=1, N/empty/space=0 for signature_flag, self_employed_flag, etc.
- **Boolean to Bit**: true=1, false/empty=0 for consent flags
- **Date Handling**: Default to GETUTCDATE() if null for receive_date
- **Phone Numbers**: Strip formatting, numbers only (home_phone, cell_phone, work phone)
- **Numbers Only**: Remove non-numeric characters from ZIP codes and phone numbers
- **Calculated Fields**: Combine months/years for tenure calculations (months_at_address, months_at_job)
- **Identity Insert**: Use existing app_id and con_id values from XML for primary keys

### Default Values
- `product_line_enum`: 600 (Credit Card)
- `esign_consent_flag`: 0 (false)
- `paperless_flag`: 0 (false) 
- `sms_consent_flag`: 0 (false)
- `auth_user_spouse_flag`: 0 (false)
- `signature_flag`: 0 (false)
- `self_employed_flag`: 0 (false)
- `income_source_nontaxable_flag`: 0 (false)
- Processing flags default to 0 (false)

## Validation Rules
- **Pre-flight Check**: Validate `app_id` and at least one `con_id` exist before processing
- **Identifier Validation**: 
  - `app_id` must be integer between 1 and 999,999,999
  - `con_id` must be integer between 1 and 999,999,999
- **SSN Validation**: 
  - Must be 9 digits
  - Cannot be all same digits (000000000, 111111111, etc.)
- **Critical Enum Validation**: 
  - Missing `contact_type_enum` (ac_role_tp_c) → abandon entire application insert
  - Missing `address_type_enum` (address_tp_c) → skip address record insert
  - Missing `employment_type_enum` (employment_tp_c) → skip employment record insert
- **Enum Handling**: 
  - Most enum columns allow NULL - missing XML attributes are omitted from INSERT
  - Only `population_assignment_enum` has default value for empty/missing XML attributes
- **Data Integrity**: All FK relationships must be valid
- **Required Fields**: Non-null constraints enforced per table schema
- **Data Types**: Type conversions applied with error handling and fallback values
- **Contact Role Validation**: At least one contact with ac_role_tp_c='PR' (Primary) required
- **Secondary Contact**: Optional con_id_auth only inserted if con_id exists in XML

## Enhanced Mapping Contract Features

### Key Identifiers
The mapping contract now includes comprehensive identifier validation:
- **app_id**: Primary application identifier from `/Provenir/Request/@ID`
- **con_id_primary**: Required primary contact from `contact[@ac_role_tp_c='PR']/@con_id`
- **con_id_auth**: Optional authorized user from `contact[@ac_role_tp_c='AUTH']/@con_id`

### Comprehensive Enum Mappings
- **15+ enum types** covering all coded fields (status, decision, contact types, etc.)
- **NULL handling**: Most enum columns allow NULL - missing XML attributes are not inserted
- **Required enum default**: Only `population_assignment_enum` has empty string default (NOT NULL column)
- **Critical enum validation**: Missing `contact_type_enum`, `address_type_enum`, or `employment_type_enum` skips record insert

### Enhanced Bit Conversions
- **char_to_bit**: Y/N/empty/space → 1/0 conversion
- **boolean_to_bit**: true/false → 1/0 conversion
- **Default bit values** for consent and flag fields

### Data Transformation Rules
- **numbers_only**: Strip formatting from phone numbers and ZIP codes
- **identity_insert**: Preserve existing app_id and con_id values
- **calculated fields**: Combine months/years for tenure calculations
- **default_getutcdate_if_null**: Auto-populate receive_date if missing

### Validation Framework
- **SSN validation**: 9-digit format, exclude invalid patterns
- **Identifier ranges**: app_id and con_id must be 1-999,999,999
- **Required field validation**: Enforce non-null constraints
- **FK relationship validation**: Ensure referential integrity

## Insert Logic and Processing Rules

### Conditional Insert Logic
- **Missing XML attributes**: Do not include column in INSERT statement (allows NULL)
- **Exception**: `population_assignment_enum` uses default value (229) if XML attribute missing
- **Critical enum missing**: Skip entire record insert for that table
  - No `ac_role_tp_c` → abandon application processing
  - No `address_tp_c` → skip contact_address insert for that address
  - No `employment_tp_c` → skip contact_employment insert for that employment

### Contact Processing Rules
- **Primary contact** (ac_role_tp_c='PR'): Required - must exist or abandon application
- **Secondary contact** (ac_role_tp_c='AUTH'): Optional - only process if con_id exists
- **Multiple addresses per contact**: Process each address with valid address_tp_c
- **Multiple employment records per contact**: Process each employment with valid employment_tp_c

### Column Inclusion Rules
1. **Always include**: Required fields (app_id, con_id, first_name, last_name, etc.)
2. **Include if present**: Optional fields with XML attribute values
3. **Exclude if missing**: Enum columns without XML attribute (except population_assignment_enum)
4. **Apply defaults**: Bit flags default to 0, population_assignment_enum defaults to 229

## Processing Order
1. **Pre-flight Validation**: Check for required identifiers (app_id, con_id with ac_role_tp_c='PR')
2. **Insert app_base**: Primary application record (IDENTITY INSERT for `app_id`)
3. **Insert contact_base**: Primary contact record (IDENTITY INSERT for `con_id`)
4. **Insert secondary contact**: Only if con_id_auth exists in XML
5. **Insert application children**: `app_operational_cc`, `app_pricing_cc`, `app_transactional_cc`, etc.
6. **Insert contact children**: `contact_address`, `contact_employment` (only with valid enum types)
7. **Insert lookup entries**: `report_results_lookup`, `historical_lookup` as needed
8. **Post-processing validation**: Verify data integrity and FK relationships

## Notes
- Only XML elements listed in mapping contract are extracted
- Mixed case XML converted to lowercase for comparison
- Missing or malformed data handled gracefully with defaults
- Transaction integrity maintained across all related inserts
