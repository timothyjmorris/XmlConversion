# MAC Data Model 2.0 - Dictionary & Usage Guide
*Last Updated: 2026-02-14*

## Overview
>The MAC operational data model serves as the source of truth for loan applications across multiple product lines. The design is built on Domain-Driven Design (DDD) principles, creating a system that deeply reflects our business domain, rules, and processes. Some of our goals were to provide intuitive clarity, increase performance, reduce maintenance and allow simple integration for non-operations systems. The design separates concerns into core data, operational state, transactional flags, pricing decisions, funding, contact information and so on. 

>Previously, the database had this shared responsibility with an XML document representing the application data as the "source of truth". The XML application data has been migrated to the new data model. Full reports from services such as TransUnion and Experian will still be stored in the `reports` table as an XML blob, which is parsed for decisioning data during processing.
---

## Core Design Principles

### 1. Product-Agnostic Core with Product-Specific Extensions
The model uses a **ubiquitous language** that both technical and business teams understand. All core applications begin with `app_base` - regardless of product type. In fact, the pattern for all app-centric tables begin with `app_*`.  Each product line has similarily categorized data such as *"transactional"* or *"operational"* with a product-specific suffix:

- `*_cc` for Credit Cards
- `*_rl` for Recreational Lending

This approach **reduces complexity** by separating universal concerns from product-specific ones.

Core application tables continue to use [supporting tables](#integration-with-common-supporting-application-tables) such as `scores` and `indicators`.

### 2. Lifecycle-Based Table Separation

The model separates data by lifecycle and mutability, **modeling the business** flow of loan processing. See the [Data Dictionary] for detailed column definitions.

| Table Type 				 | Purpose 						| Lifecycle | Data Volatility 						|
|----------------------------|------------------------------|-----------|---------------------------------------|
| **app_base** 				 | Core immutable facts 		| Permanent | Never changes 						|
| **app_operational_*** 	 | Working operational data 	| Permanent | Changes frequently during processing 	|
| **app_transactional_*** 	 | Temporary flags/state 		| Temporary | Short-lived, cleaned after decision 	|
| **app_pricing_*** 		 | Decisioning & pricing 		| Permanent | Set during decision, rarely changes 	|
| **app_solicited_*** 		 | Mail offer pre-fill data 	| Permanent | Set at creation, never changes 		|
| **app_contact_base** 		 | Primary applicant identity 	| Permanent | Rarely changes after initial entry 	|
| **app_contact_address** 	 | Address information 			| Permanent | May change (address updates) 			|
| **app_contact_employment** | Employment & income 			| Permanent | May change (job changes) 				|

This separation **improves maintainability** by grouping data with similar change patterns.

### 3. Enum-Driven Type Safety
We use the "enum" convention to look up a value from a list, such as "Approved" or "Declined". To avoid 'brittle' links by storing those values - that can change over timey, we store a link to the value as an integer (Foreign Key). Then the value or name is lookup up in `app_enums`. This adds a layer of flexibility to change the display name while maintaining data integrity and performance. 
This also means that if you're looking directly at the data, you'll see a lot more of these linking numbers. You'll want to join on the `app_enums` table and probably want to know about [a few key enums to remember](#important-enum-values-to-remember).

- Transforms primitives (600) into business concepts ("Credit Card")
- Single source of truth for consistency
- Easy to extend without schema changes
- **Better alignment** between business terminology and code

>For [complete list of `app_enums`](data-model-2.0-enum-list)

### 4. Composite Keys for Multi-Instance Relationships
Contact-related tables support multiple instances per application, **focusing on the domain** requirements:
- `app_contact_base`: Multiple contacts per app (PRIMARY, CO-APPLICANT)
- `app_contact_address`: Multiple addresses per contact (PRIMARY=320, PREVIOUS, MAILING)
- `app_contact_employment`: Multiple employments per contact (CURRENT=350, PREVIOUS)

This design **increases flexibility** to handle complex applicant scenarios.

---

## Table Relationships

### Application Core Hierarchy
See the [Data Dictionary](#data-dictionary-common-tables) below for complete table details

**Credit Card Product Line**
```folder
app_base
   .
   ├── app_operational_cc
   ├── app_transactional_cc
   ├── app_pricing_cc
   ├── app_solicited_cc
   ├── app_campaign_cc
   ├── app_contact_base (1:many)
   │      ├── app_contact_address (1:many per contact)
   │      └── app_contact_employment (1:many per contact)
   │
   ├── app_report_results_lookup (1:many)
   └── app_historical_lookup (1:many)
```

**Recreational Lending Product Line**
```folder
app_base
   .
   ├── app_collateral_rl (1:many)
   ├── app_dealer_rl
   ├── app_funding_rl
   ├── app_funding_checklist_rl
   ├── app_funding_contract_rl
   ├── app_operational_rl
   ├── app_pricing_rl
   ├── app_policy_exceptions_rl (1:many)
   ├── app_transactional_rl
   ├── app_warranties_rl (1:many)
   ├── app_contact_base (1:many)
   │      ├── app_contact_address (1:many per contact)
   │      └── app_contact_employment (1:many per contact)
   │
   ├── app_report_results_lookup (1:many)
   ├── app_historical_lookup (1:many)
   │
   ├── app_boarding_rl
   ├── app_cri_index_rl
   ├── app_loanpro_dealer_lookup_rl
   ├── app_participation_index_rl
   └── app_terms_index_rl
```

### Key Foreign Key Patterns
1. **CASCADE DELETE**: All child tables delete automatically when parent app is deleted (includes contacts)
2. **PK = FK**: Product-specific tables use `app_id` as both primary and foreign key (1:1 relationship)
3. **Composite PK**: Contact tables prevent duplicates via `(con_id, *_type_enum)` keys

This structure **enables simple integration** through a single entry point (`app_id`).

---

## Common Query Patterns

### Get Complete Application (Single Row)
```sql
SELECT *
FROM app_base AS a
INNER JOIN app_enums AS prod ON prod.enum_id = a.product_line_enum
LEFT JOIN app_operational_cc AS o ON o.app_id = a.app_id
LEFT JOIN app_pricing_cc AS p ON p.app_id = a.app_id
LEFT JOIN app_solicited_cc AS s ON s.app_id = a.app_id
LEFT JOIN app_transactional_cc AS t ON t.app_id = a.app_id
INNER JOIN app_campaign_cc AS cam ON cam.campaign_num = p.campaign_num
INNER JOIN app_contact_base AS c ON c.app_id = a.app_id
LEFT JOIN app_contact_address AS ca 
	ON ca.con_id = c.con_id AND ca.address_type_enum = 320  -- PRIMARY address
LEFT JOIN app_contact_employment AS ce 
	ON ce.con_id = c.con_id AND ce.employment_type_enum = 350  -- CURRENT employment
WHERE a.app_id = @app_id;
```

### Get Application with All Addresses
```sql
SELECT 
	a.app_id,
	c.con_id,
	c.first_name,
	c.last_name,
	addr_type.value AS address_type,
	ca.address_line_1,
	ca.city,
	ca.state,
	ca.zip
FROM app_base AS a
INNER JOIN app_contact_base AS c ON c.app_id = a.app_id
INNER JOIN app_contact_address AS ca ON ca.con_id = c.con_id
INNER JOIN app_enums AS addr_type ON addr_type.enum_id = ca.address_type_enum
WHERE a.app_id = @app_id;
```

### Get Application with All Employment History
```sql
SELECT 
	a.app_id,
	c.con_id,
	c.first_name,
	c.last_name,
	emp_type.value AS employment_type,
	ce.business_name,
	ce.job_title,
	ce.monthly_salary,
	ce.months_at_job
FROM app_base AS a
INNER JOIN app_contact_base AS c ON c.app_id = a.app_id
INNER JOIN app_contact_employment AS ce ON ce.con_id = c.con_id
INNER JOIN app_enums AS emp_type ON emp_type.enum_id = ce.employment_type_enum
WHERE a.app_id = @app_id
ORDER BY ce.employment_type_enum;  -- CURRENT first (350)
```

### Lookup Enum Values
```sql
-- Get all product lines
SELECT enum_id, value 
FROM app_enums 
WHERE type = 'product_line';

-- Get all address types
SELECT enum_id, value 
FROM app_enums 
WHERE type = 'address_type';

-- Get application decision text
SELECT e.value AS decision
FROM app_base AS a
INNER JOIN app_enums AS e ON e.enum_id = a.decision_enum
WHERE a.app_id = @app_id;
```

---

## Important Enum Values to Remember

| Enum Type | Key Values | Notes |
|-----------|------------|-------|
| `product_line_enum` | 600 = Credit Card | Determines which `*_cc` tables to join |
| `contact_type_enum` | 281 = PRIMARY | Identifies the primary applicant |
| `address_type_enum` | 320 = PRIMARY | Most common address filter |
| `employment_type_enum` | 350 = CURRENT | Most common employment filter |

---

## Deprecated Tables

- `app_product`
- `app_prod_bcard`
- `campaign_booking_letters` 
- `campaign_expiration`

## Special Tables

### [app_report_results_lookup]
**Purpose**: Store key/value pairs from external reports without re-parsing XML/JSON. Some specialized fields are needed for analytics outside of MAC -- but don't fit into the `scores` or `analytics` shape and purpose very well. MAC can store normalized values in this table rather than having to parse XML from the raw reports.

**Example Values**:
- `GIACT_Response`
- `InstantID_Score`
- `VeridQA_Result`

**Usage**:
```sql
SELECT value 
FROM app_report_results_lookup
WHERE app_id = @app_id 
  AND name = 'InstantID_Score'
  AND source_report_key = 'IDV';
```

### [app_historical_lookup]
**Purpose**: Archive retired/deprecated column values for historical applications

**Why it exists**: As the schema evolves, old columns may be removed but their historical data needs preservation

**Usage**:
```sql
SELECT name, value, source
FROM app_historical_lookup
WHERE app_id = @app_id;
```

---

## Integration with Common Supporting Application Tables
There are a set of tables that support the application and core Data Model and the loan lifecycle.
The `app_base.app_id` is the universal foreign key for non-operations systems, **enabling simple integration**:

| Schema | Tables | Purpose |
|--------|--------|---------|
| **analytics** | Various | Analytics tracking and metrics - used outside of MAC |
| **comments** | Comments | User comments and system notes |
| **communication** | Communication | Adverse action letters, communication in a formal letter format sent to consumers |
| **documents** | Documents | Uploaded documents and images |
| **indicators** | Indicators | Structured key/values related to the application |
| **journals** | Journals | Audit trail and change history |
| **reports** | Reports | Raw external report responses (XML/JSON) |
| **rules** | Rules | Business rule evaluations and overrides |
| **scores** | Scores | Credit scores and model scores |

---

## Integration with Decisioning Domain (Scores & Indicators)

The `scores` and `indicators` tables integrate with the Application aggregate via `app_id` and store decisioning data:

**Indicators**: Boolean/categorical flags from fraud checks and verification
- Examples: `AlloyJourneyStatus`, `CreditBureauPulled`, `TU_Doc_Result`

**Scores**: Numeric scores from credit bureaus and risk models
- Examples: `email_risk`, `FRAUDFORCE`, `SL_1_Synth`, `SB`

### Basic Query Pattern
```sql
-- Get application with indicators and scores
SELECT 
	a.app_id,
	a.decision_date,
	o.backend_fico_grade,
	
	-- Get all indicators as JSON
	(SELECT indicator, value FROM indicators WHERE app_id = a.app_id FOR JSON PATH) AS indicators,
	
	-- Get all scores as JSON
	(SELECT score_identifier, score FROM scores WHERE app_id = a.app_id FOR JSON PATH) AS scores
	
FROM app_base AS a
LEFT JOIN app_operational_cc AS o ON o.app_id = a.app_id
WHERE a.app_id = @app_id;
```

**For detailed query examples and analysis patterns**, see the companion document: **"Scores & Indicators Query Guide"**.

---

## Data Migration Strategy

### Migration Overview
The new operational data model will be populated through a **hybrid transformation approach**:

1. **Legacy XML Transformation**: Historical application data stored in XML format will be parsed and transformed into the new normalized table structure
2. **Direct Source Data Mapping**: Where available, data will be sourced directly from the original legacy tables and mapped to the new schema
3. **Enrichment & Derivation**: Some fields will be calculated or derived during migration (e.g., `debt_to_income_ratio`, `ssn_last_4`)

All transformations will be logged in the `journals` table for audit trail.

### Known Data Quality Issues (Pre-2008)
1. **app_contact_base.birth_date**: Contains NULLs for AUTHU accounts
   - **Migration Strategy**: Default to `1900-01-01`
2. **app_contact_base.ssn**: Contains NULLs for AUTHU accounts
   - **Migration Strategy**: Default to `000000000`
3. **XML Structure Variations**: Early applications have inconsistent XML schemas
   - **Migration Strategy**: Use defensive parsing with fallback to `app_historical_lookup` for unmapped fields

---

## Performance Optimization Tips

### 1. Always Filter by Product Line First
```sql
WHERE a.product_line_enum = 600  -- Credit Card
```

### 2. Use Specific Enum Filters for Contact Data
```sql
-- Instead of joining all addresses
LEFT JOIN app_contact_address AS ca ON ca.con_id = c.con_id

-- Filter for PRIMARY only
LEFT JOIN app_contact_address AS ca 
	ON ca.con_id = c.con_id AND ca.address_type_enum = 320
```

### 3. Join Pattern for Single Row Results
When you need a single application row with PRIMARY contact, address, and employment:
```sql
INNER JOIN app_contact_base (first by contact_type_enum)
LEFT JOIN app_contact_address (filtered to address_type_enum = 320)
LEFT JOIN app_contact_employment (filtered to employment_type_enum = 350)
```

---

## Schema Evolution Strategy

### Retiring Columns
1. Copy existing data to `app_historical_lookup` table
2. Drop column from source table
3. Document in `app_historical_lookup.source` which table it came from
4. Remove from "MAC Portal"

### Adding New Enum Types
```sql
INSERT INTO app_enums (enum_id, type, value)
VALUES 
	(950, 'new_category', 'New Value 1'),
	(951, 'new_category', 'New Value 2');
```

---

## Best Practices

### ✅ DO
- Always join `app_enums` for human-readable enum values
- Filter contact-related tables by specific `*_type_enum` values
- Use LEFT JOIN for all optional product-specific tables

### ❌ DON'T
- Don't join all contact addresses/employments without filtering by type
- Don't query `app_transactional_*` tables for historical analysis (they may be purged)
- Don't forget to filter by `product_line_enum` when querying product-specific tables
- Don't update `app_base` fields after initial creation (they're meant to be immutable)
- Don't create circular dependencies between enum-referenced columns

---

## Questions to Consider

Before implementing queries or updates, ask yourself:

1. **Which product line am I working with?** (Filter by `product_line_enum`)
2. **Do I need operational, transactional, or pricing data?** (Choose the right table)
3. **Am I looking for PRIMARY contact data only?** (Filter contact tables by type enum)
4. **Will this data be purged?** (Avoid using `app_transactional_*` for long-term reporting)

---

## Data Dictionary: Common Tables

### [app_base]
**Purpose**: Parent table with core immutable application data for all product types

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Unique application identifier (PK, IDENTITY) |
| app_source_enum | smallint | Source channel of application (FK to app_enums) |
| app_type_enum | smallint | Type of application (FK to app_enums) |
| booked_date | datetime | Date application was booked/funded |
| decision_enum | smallint | Final decision outcome (FK to app_enums) |
| decision_date | datetime | Date final decision was made |
| funding_date | datetime | Date funds were disbursed |
| ip_address | varchar(39) | IP address of applicant |
| product_line_enum | smallint | Product line (600=Credit Card) (FK to app_enums) |
| receive_date | datetime | Date application was received (DEFAULT GETUTCDATE()) |
| retain_until_date | datetime | Data retention expiration date |
| sc_multran_booked_date | datetime | Secured Card multran booking date |
| sub_type_enum | smallint | Application sub-type for RecLending (FK to app_enums) |

### [app_enums]
**Purpose**: Central reference table for all common lookup values

| Column | Type | Description |
|--------|------|-------------|
| enum_id | smallint | Unique identifier for enum value (PK) |
| type | varchar(50) | Category/type of enum (e.g., 'product_line', 'address_type') |
| value | varchar(100) | Human-readable description (e.g., 'APPROVED', 'RENTAL PROPERTY') |
```sql
-- List all of the categories
SELECT DISTINCT [type] FROM app_enums;
```

### [app_contact_base]
**Purpose**: Base identity information for contacts, all product-lines (applicants, co-applicants, authorized users)

| Column | Type | Description |
|--------|------|-------------|
| con_id | int | Unique contact identifier (PK, IDENTITY) |
| app_id | int | Application ID (FK to `app_base`, CASCADE DELETE) |
| contact_type_enum | smallint | Contact type (281=PRIMARY) (FK to app_enums) |
| birth_date | smalldatetime | Date of birth |
| cell_phone | varchar(10) | Cell phone number |
| email | varchar(100) | Email address |
| esign_consent_flag | bit | E-signature consent (DEFAULT 0) |
| first_name | varchar(50) | First name |
| fraud_type_enum | smallint | Fraud type if detected (FK to app_enums) |
| home_phone | varchar(10) | Home phone number |
| last_name | varchar(50) | Last name |
| middle_initial | varchar(1) | Middle initial |
| mother_maiden_name | varchar(50) | Mother's maiden name |
| paperless_flag | bit | Paperless statements consent (DEFAULT 0) |
| sms_consent_flag | bit | SMS consent (DEFAULT 0) |
| ssn | varchar(9) | Social Security Number |
| ssn_last_4 | computed | CALCULATED Field: Last 4 of SSN (PERSISTED, indexed) |
| suffix | varchar(10) | Name suffix |


### [app_contact_address]
**Purpose**: Address information for contacts

| Column | Type | Description |
|--------|------|-------------|
| con_id | int | Contact ID (PK, FK to `app_contact_base`, CASCADE DELETE) |
| address_type_enum | smallint | Address type (320=PRIMARY) (PK, FK to app_enums) |
| address_line_1 | varchar(100) | Address line 1 |
| city | varchar(50) | City |
| months_at_address | smallint | Months at this address |
| ownership_type_enum | smallint | Ownership type (FK to app_enums) |
| po_box | varchar(10) | PO Box |
| rural_route | varchar(10) | Rural route |
| state | char(2) | State abbreviation |
| street_name | varchar(50) | Street name |
| street_number | varchar(10) | Street number |
| unit | varchar(10) | Unit/Apt number |
| zip | varchar(9) | ZIP code |


### [app_contact_employment]
**Purpose**: Employment and income information for contacts (supports multiple employments per contact)

| Column | Type | Description |
|--------|------|-------------|
| con_id | int | Contact ID (PK, FK to `app_contact_base`, CASCADE DELETE) |
| employment_type_enum | smallint | Employment type (350=CURRENT) (PK, FK to app_enums) |
| address_line_1 | varchar(100) | Employer address line 1 |
| city | varchar(50) | Employer city |
| business_name | varchar(100) | Employer business name |
| income_source_nontaxable_flag | bit | Income is non-taxable |
| income_type_enum | smallint | Income type (FK to app_enums) |
| job_title | varchar(100) | Job title |
| monthly_salary | decimal(12,2) | Monthly salary |
| months_at_job | smallint | Months at current job |
| other_monthly_income | decimal(12,2) | Other monthly income |
| other_income_type_enum | smallint | Other income type (FK to app_enums) |
| other_income_source_detail | varchar(50) | Free-text for other income source detail |
| phone | char(10) | Employer phone number |
| self_employed_flag | bit | Self-employed (DEFAULT 0) |
| state | char(2) | Employer state |
| street_name | varchar(50) | Employer street name |
| street_number | varchar(10) | Employer street number |
| unit | varchar(10) | Employer unit/suite |
| zip | varchar(9) | Employer ZIP code |


### [app_historical_lookup]
**Purpose**: Archived values from retired/deprecated columns

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| name | varchar(100) | Original column name (PK) |
| source | varchar(50) | Original table name |
| value | varchar(250) | Column value |
| rowstamp | datetime | Timestamp (DEFAULT GETUTCDATE()) |


### [app_report_results_lookup]
**Purpose**: Key/value pairs extracted from external reports for quick access

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| name | varchar(100) | Name/key of the report result value (PK) |
| value | varchar(250) | Flattened result value |
| source_report_key | varchar(20) | Source report identifier (PK), e.g., "NOVA" from `reports.source` |
| rowstamp | datetime | Timestamp (DEFAULT GETUTCDATE()) |


---

## Data Dictionary: Credit Card Product Line

### [app_operational_cc]
**Purpose**: Credit Card operational data that changes during application processing

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| assigned_to | varchar(80) | User assigned to process application |
| auth_user_spouse_flag | bit | Authorized user is spouse (DEFAULT 0) |
| backend_fico_grade | char(1) | FICO grade from backend system |
| backend_risk_grade | char(1) | Risk grade from backend system |
| cb_score_factor_code_1-5 | varchar(10) | Credit bureau score factor codes |
| cb_score_factor_type_1-5 | varchar(25) | Credit bureau score factor descriptions |
| housing_monthly_payment | decimal(12,2) | Monthly housing payment amount |
| last_bureau_pulled_type | varchar(5) | Type of last credit bureau pulled |
| last_updated_by | varchar(80) | User who last updated record |
| last_updated_date | datetime | Date record was last updated |
| meta_url | varchar(50) | Metadata URL reference - see `analytics`|
| payment_protection_plan | char(1) | Payment protection plan indicator |
| priority_enum | smallint | Processing priority (FK to app_enums) |
| process_enum | smallint | Current process state (FK to app_enums) |
| regb_end_date | datetime | Reg B adverse action end date |
| regb_start_date | datetime | Reg B adverse action start date (DEFAULT GETUTCDATE()) |
| risk_model_score_factor_code_1-4 | varchar(10) | Risk model factor codes |
| risk_model_score_factor_type_1-4 | varchar(25) | Risk model factor descriptions |
| sc_ach_amount | decimal(12,2) | Secured card ACH amount |
| sc_bank_aba | varchar(9) | Secured card bank routing number |
| sc_bank_account_num | varchar(17) | Secured card bank account number |
| sc_bank_account_type_enum | smallint | Secured card account type (FK to app_enums) |
| sc_debit_funding_source_enum | smallint | Debit funding source (FK to app_enums) |
| sc_debit_initial_deposit_amount | decimal(12,2) | Initial deposit amount |
| sc_debit_initial_deposit_date | datetime | Initial deposit date |
| sc_debit_nsf_return_date | datetime | NSF return date |
| sc_debit_refund_amount | decimal(12,2) | Refund amount |
| sc_debit_refund_date | datetime | Refund date |
| sc_funding_reference | int | Funding reference number |
| signature_flag | bit | Signature received (DEFAULT 0) |
| ssn_match_type_enum | smallint | SSN match type (FK to app_enums) |
| status_enum | smallint | Current application status (FK to app_enums) |
| verification_source_enum | smallint | Verification source (FK to app_enums) |


### [app_pricing_cc]
**Purpose**: Credit Card pricing, terms, and decisioning data

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| account_number | varchar(16) | Credit card account number |
| campaign_num | varchar(6) | Marketing campaign number (FK to `app_campaign_cc`) |
| card_art_code | varchar(2) | Card design/artwork code |
| card_account_setup_fee | tinyint | Account setup fee |
| card_additional_card_fee | tinyint | Additional card fee |
| card_annual_fee | smallint | Annual fee amount |
| card_cash_advance_apr | decimal(5,2) | Cash advance APR |
| card_cash_advance_fee | tinyint | Cash advance fee |
| card_cash_advance_percent | decimal(5,2) | Cash advance percentage |
| card_cash_advance_margin_apr | decimal(5,2) | Cash advance margin APR |
| card_foreign_percent | decimal(5,2) | Foreign transaction percentage |
| card_intro_cash_advance_apr | decimal(8,5) | Introductory cash advance APR |
| card_intro_purchase_apr | decimal(8,5) | Introductory purchase APR |
| card_late_payment_fee | tinyint | Late payment fee |
| card_min_payment_fee | tinyint | Minimum payment fee |
| card_min_payment_percent | decimal(5,2) | Minimum payment percentage |
| card_min_interest_charge | decimal(5,2) | Minimum interest charge |
| card_over_limit_fee | tinyint | Over limit fee |
| card_purchase_apr | decimal(5,2) | Purchase APR |
| card_purchase_apr_margin | decimal(5,2) | Purchase APR margin |
| card_returned_payment_fee | tinyint | Returned payment fee |
| clear_card_flag | bit | Clear card pricing flag |
| credit_line | smallint | Approved credit line |
| credit_line_max | smallint | Maximum possible credit line |
| credit_line_possible | smallint | Possible credit line offered |
| debt_to_income_ratio | decimal(12,2) | Calculated debt-to-income ratio |
| decision_model_enum | smallint | Decision model used (FK to app_enums) |
| marketing_segment | varchar(10) | Marketing segment code from solicitation |
| min_payment_due | decimal(12,2) | Minimum payment due |
| monthly_debt | decimal(12,2) | Total monthly debt |
| monthly_income | decimal(12,2) | Total monthly income |
| population_assignment_enum | smallint | Population assignment (FK to app_enums) |
| pricing_tier | varchar(2) | Pricing tier code |
| sc_multran_account_num | varchar(16) | Secured card multran account number |
| segment_plan_version | varchar(3) | Segmentation plan version |
| solicitation_num | varchar(15) | Solicitation number |
| special_flag_5-8 | char(1) | Special flags for custom use |


### [app_solicited_cc]
**Purpose**: Credit Card pre-filled data from mail solicitation offers

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to app_base, CASCADE DELETE) |
| birth_date | smalldatetime | Date of birth from solicitation |
| city | varchar(50) | City from solicitation |
| first_name | varchar(50) | First name from solicitation |
| last_name | varchar(50) | Last name from solicitation |
| middle_initial | varchar(1) | Middle initial from solicitation |
| po_box | varchar(10) | PO Box from solicitation |
| prescreen_fico_grade | char(1) | Pre-screen FICO grade |
| prescreen_risk_grade | char(1) | Pre-screen risk grade |
| rural_route | varchar(10) | Rural route from solicitation |
| ssn | char(9) | SSN from solicitation |
| state | char(2) | State from solicitation |
| street_name | varchar(50) | Street name from solicitation |
| street_number | varchar(10) | Street number from solicitation |
| suffix | varchar(10) | Name suffix from solicitation |
| unit | varchar(10) | Unit/Apt number from solicitation |
| zip | varchar(9) | ZIP code from solicitation |


### [app_transactional_cc]
**Purpose**: Credit Card temporary transactional flags (short-lived, cleaned after decision)

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to app_base, CASCADE DELETE) |
| alloy_tag_list | varchar(max) | Delimited list of "tags" returned from last Alloy report -- used for `rules`|
| analyst_review_flag | bit | Requires analyst review (DEFAULT 0) |
| billing_tree_response_status | varchar(20) | Secured card |
| billing_tree_token | varchar(500) | Secured card |
| booking_paused_flag | bit | Booking is paused (DEFAULT 0) |
| disclosures_read_flag | bit | Disclosures were read (DEFAULT 0) |
| duplicate_ssn_flag | bit | Duplicate SSN detected (DEFAULT 0) |
| error_message | varchar(255) | Internal error message text |
| ex_freeze_code | varchar(4) | Experian code |
| fraud_review_flag | bit | Requires fraud review (DEFAULT 0) |
| iovation_blackbox | varchar(max) | Used for Alloy Identity Verification |
| locked_by_user | varchar(80) | User who locked the application |
| pending_verification_flag | bit | Pending verification (DEFAULT 0) |
| sc_ach_sent_flag | bit | Secured card ACH sent (DEFAULT 0) |
| sc_debit_refund_failed_flag | bit | Debit refund failed (DEFAULT 0) |
| supervisor_review_flag | bit | Requires supervisor review (DEFAULT 0) |
| use_alloy_service_flag | bit | Indicates if Alloy tags & rules will be used for the application |


### [app_campaign_cc]
**Purpose**: Mail solicitation / Marketing campaign information
Combines and replaces [campaign_booking_letters] and [campaign_expiration]

| Column | Type | Description |
|--------|------|-------------|
| campaign_num | varchar(6) | Campaign number (PK) |
| agreement_num | varchar | Agreement number |
| booking_on_flag | bit | Booking enabled |
| in_home_date | datetime | In-home mail date |
| internet_responses_on_flag | bit | Internet responses enabled |
| letters_on_flag | bit | Letters enabled |
| processing_complete_flag | bit | Processing complete |
| processing_expiration_date | datetime | Processing expiration date |
| solicitation_expiration_date | datetime | Solicitation expiration date |

---

## Data Dictionary: Recreational Lending Product Line

### **Core Application Tables**
These tables all directly related to the application (by `app_id`) and are specific to RecLending. 

### [app_collateral_rl]
**Purpose**: Store each collateral details and related add-on options using `collateral_type_enum`
NOTE: this structure enables us to stop using fixed position 1 - 4 to have special meaning, and instead uses the enum key to designate the type (e.g. 'BOAT', 'MOTOR', 'SNOWMOBILE', etc).

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| collateral_type_enum | smallint |  (FK to app_enums) |
| length | smallint |  |
| make | varchar(50) |  |
| mileage | int |  |
| model | varchar(50) |  |
| motor_size | smallint |  |
| option_1_description | varchar(100) |  |
| option_1_value | decimal(12,2) |  |
| option_2_description | varchar(100) |  |
| option_2_value | decimal(12,2) |  |
| sort_order | smallint |  |
| used_flag | bit |  |
| vin | varchar(60) |  |
| wholesale_value | decimal(12,2) |  |
| year | smallint |  |


### [app_dealer_rl]
**Purpose**: Snapshot of Dealer information (*updated through lifecycle of application if details change*)

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| bank_account_num | varchar(20) |  |
| bank_account_type_enum | smallint |  (FK to app_enums) |
| bank_name | varchar(50) |  |
| bank_phone | char(10) |  |
| bank_routing_num | char(9) |  |
| broker_flag | bit |  |
| dealer_address_line_1 | varchar(100) |  |
| dealer_city | varchar(50) |  |
| dealer_email | varchar(100) |  |
| dealer_fax | char(10) |  |
| dealer_name | varchar(100) |  |
| dealer_num_child | int |  |
| dealer_num_parent | int |  |
| dealer_phone | char(10) |  |
| dealer_state | char(2) |  |
| dealer_zip | varchar(9) |  |
| fsp_email | varchar(100) |  |
| fsp_fax | char(10) |  |
| fsp_name | varchar(100) |  |
| fsp_num | int |  |
| fsp_phone | char(10) |  |


### [app_funding_rl]
**Purpose**: Immutable calculated system values related to the funding process

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| account_number | int | |
| amount_financed_within_policy_flag | bit |  |
| boarding_date | datetime | |
| collateral_ages_within_policy_flag | bit |  |
| credit_bureau_expire_date | date |  |
| credit_pulled_within_30_days_flag | bit |  |
| creditscore_within_policy_flag | bit |  |
| dealer_proceeds_amount | decimal(12,2) |  |
| down_payment_within_policy_flag | bit |  |
| dti_within_policy_flag | bit |  |
| first_payment_not_in_7_days_flag | bit |  |
| loan_amount_approved_flag | bit |  |
| loan_amount_within_policy_flag | bit |  |
| loanpro_customer_id_pr | int |  |
| loanpro_customer_id_sec | int |  |
| loanpro_loan_id | int |  |
| ltv_within_policy_flag | bit |  |
| note_date_in_range_flag | bit |  |
| participation_percentage | decimal(12,2) |  |
| participation_proceeds | decimal(12,2) |  |
| paystub_within_30days_pr_flag | bit |  |
| paystub_within_30days_sec_flag | bit |  |
| product_number | varchar(10) |  |
| subtotal | decimal(12,2) |  |
| term_within_policy_flag | bit |  |
| total_of_payments_amount | decimal(12,2) |  |
| validated_finance_charge | decimal(12,2) |  |
| verification_number | varchar(10) | |


### [app_funding_checklist_rl]
**Purpose**: Decisions made or validation to approve a loan for funding

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| addendum_signed_pr_enum | smallint |  (FK to app_enums) |
| addendum_signed_sec_enum | smallint |  (FK to app_enums) |
| address_confirmed_flag | bit |  |
| applicant_references_checked_flag | bit |  |
| apr_within_guidelines_flag | bit |  |
| check_requested_by_user | varchar(80) |  |
| collateral_percent_used_confirmed_enum | smallint |  (FK to app_enums) |
| collateral_worksheet_unit_confirmed_enum | smallint |  (FK to app_enums) |
| contract_signed_pr_flag | bit |  |
| contract_signed_sec_flag | bit |  |
| correct_contract_state_flag | bit |  |
| credit_app_signed_pr_enum | smallint |  (FK to app_enums) |
| credit_app_signed_sec_enum | smallint |  (FK to app_enums) |
| down_payment_approved_flag | bit |  |
| drivers_license_confirmed_pr_enum | smallint |  (FK to app_enums) |
| drivers_license_confirmed_sec_enum | smallint |  (FK to app_enums) |
| drivers_license_dob_confirmed_pr_enum | smallint |  (FK to app_enums) |
| drivers_license_dob_confirmed_sec_enum | smallint |  (FK to app_enums) |
| guarantee_of_lien_enum | smallint |  (FK to app_enums) |
| initials_presented_flag | bit |  |
| insurance_deductible_within_policy_enum | smallint |  (FK to app_enums) |
| insurance_mb_lienholder_enum | smallint |  (FK to app_enums) |
| insurance_motor_vin_confirm_enum | smallint |  (FK to app_enums) |
| insurance_rv_boat_vin_confirm_enum | smallint |  (FK to app_enums) |
| insurance_trailer_vin_confirm_enum | smallint |  (FK to app_enums) |
| itemization_confirmed_flag | bit |  |
| motor_title_mb_lienholder_enum | smallint |  (FK to app_enums) |
| motor_title_vin_confirmed_enum | smallint |  (FK to app_enums) |
| motor_ucc_mb_lienholder_enum | smallint |  (FK to app_enums) |
| motor_ucc_vin_confirmed_enum | smallint |  (FK to app_enums) |
| new_motor_1_invoice_confirmed_enum | smallint |  (FK to app_enums) |
| new_motor_2_invoice_confirmed_enum | smallint |  (FK to app_enums) |
| new_rv_boat_invoice_confirmed_enum | smallint |  (FK to app_enums) |
| new_trailer_invoice_confirmed_enum | smallint |  (FK to app_enums) |
| payment_schedule_confirmed_flag | bit |  |
| payoff_mb_loan_verified_enum | smallint |  (FK to app_enums) |
| paystub_expire_date_pr | smalldatetime |  |
| paystub_expire_date_sec | smalldatetime |  |
| rv_boat_title_mb_lienholder_enum | smallint |  (FK to app_enums) |
| rv_boat_title_vin_confirmed_enum | smallint |  (FK to app_enums) |
| rv_boat_ucc_mb_lienholder_enum | smallint |  (FK to app_enums) |
| rv_boat_ucc_vin_confirmed_enum | smallint |  (FK to app_enums) |
| trailer_title_mb_lienholder_enum | smallint |  (FK to app_enums) |
| trailer_title_vin_confirmed_enum | smallint |  (FK to app_enums) |
| trailer_ucc_mb_lienholder_enum | smallint |  (FK to app_enums) |
| trailer_ucc_vin_confirmed_enum | smallint |  (FK to app_enums) |
| ucc_filed_by_mb_enum | smallint |  (FK to app_enums) |
| unit_confirmed_flag | bit |  |
| verified_against_program_flag | bit |  |


### [app_funding_contract_rl]
**Purpose**: Final Loan "Contract" details

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| apr | decimal(12,2) |  |
| cash_down_payment | decimal(12,2) |  |
| cash_proceeds | decimal(12,2) |  |
| contract_state | char(2) |  |
| document_prep_fee | decimal(12,2) |  |
| document_tax_fee | decimal(12,2) |  |
| down_payment_percentage | decimal(12,2) |  |
| finance_charge | decimal(12,2) |  |
| first_payment_by_dealer | decimal(12,2) |  |
| first_payment_date | datetime |  |
| income_expiration_date | smalldatetime |  |
| license_fee | decimal(12,2) |  |
| loan_to_value_percentage | decimal(12,2) |  |
| loan_to_value_percentage_with_fees | decimal(12,2) |  |
| monthly_payment_amount | decimal(12,2) |  |
| net_tradein_allowance | decimal(12,2) |  |
| note_payment_amount | decimal(12,2) |  |
| note_signed_date | datetime |  |
| other_dealer_fee_1 | decimal(12,2) |  |
| other_dealer_fee_2 | decimal(12,2) |  |
| other_dealer_fee_3 | decimal(12,2) |  |
| other_dealer_fee_4 | decimal(12,2) |  |
| other_dealer_fee_5 | decimal(12,2) |  |
| other_dealer_fee_6 | decimal(12,2) |  |
| other_public_official_fee_1 | decimal(12,2) |  |
| other_public_official_fee_2 | decimal(12,2) |  |
| other_public_official_fee_3 | decimal(12,2) |  |
| payoff_mb_loan_amount | decimal(12,2) |  |
| payoff_mb_loan_number | int |  |
| registration_fee | decimal(12,2) |  |
| sale_price | decimal(12,2) |  |
| taxes | decimal(12,2) |  |
| title_fee | decimal(12,2) |  |
| titled_in_state | char(2) |  |
| total_amount_financed | decimal(12,2) |  |
| total_dealer_proceeds | decimal(12,2) |  |
| ucc_fee | decimal(12,2) |  |
| ucc_principal_refund | decimal(12,2) |  |


### [app_operational_rl]
**Purpose**: RecLending operational data that changes during application processing

| Column | Type | Description |
|--------|------|-------------|
| app_id | int |  |
| assigned_credit_analyst | varchar(80) |  |
| assigned_funding_analyst | varchar(80) |  |
| cb_score_factor_code_pr_1 | varchar(10) |  |
| cb_score_factor_code_pr_2 | varchar(10) |  |
| cb_score_factor_code_pr_3 | varchar(10) |  |
| cb_score_factor_code_pr_4 | varchar(10) |  |
| cb_score_factor_code_pr_5 | varchar(10) |  |
| cb_score_factor_code_sec_1 | varchar(10) |  |
| cb_score_factor_code_sec_2 | varchar(10) |  |
| cb_score_factor_code_sec_3 | varchar(10) |  |
| cb_score_factor_code_sec_4 | varchar(10) |  |
| cb_score_factor_code_sec_5 | varchar(10) |  |
| cb_score_factor_type_pr_1 | varchar(25) |  |
| cb_score_factor_type_pr_2 | varchar(25) |  |
| cb_score_factor_type_pr_3 | varchar(25) |  |
| cb_score_factor_type_pr_4 | varchar(25) |  |
| cb_score_factor_type_pr_5 | varchar(25) |  |
| cb_score_factor_type_sec_1 | varchar(25) |  |
| cb_score_factor_type_sec_2 | varchar(25) |  |
| cb_score_factor_type_sec_3 | varchar(25) |  |
| cb_score_factor_type_sec_4 | varchar(25) |  |
| cb_score_factor_type_sec_5 | varchar(25) |  |
| housing_monthly_payment_pr | int |  |
| housing_monthly_payment_sec | int |  |
| joint_app_flag | bit |  |
| last_updated_by | varchar(80) |  |
| last_updated_date | datetime |  |
| mrv_lead_indicator_pr_enum | smallint |  (FK to app_enums) |
| mrv_lead_indicator_sec_enum | smallint |  (FK to app_enums) |
| priority_enum | smallint |  (FK to app_enums) |
| process_enum | smallint |  (FK to app_enums) |
| regb_end_date | datetime |  |
| regb_start_date | datetime |  |
| risk_model_score_factor_code_pr_1 | varchar(10) |  |
| risk_model_score_factor_code_pr_2 | varchar(10) |  |
| risk_model_score_factor_code_pr_3 | varchar(10) |  |
| risk_model_score_factor_code_pr_4 | varchar(10) |  |
| risk_model_score_factor_code_pr_5 | varchar(10) |  |
| risk_model_score_factor_code_sec_1 | varchar(10) |  |
| risk_model_score_factor_code_sec_2 | varchar(10) |  |
| risk_model_score_factor_code_sec_3 | varchar(10) |  |
| risk_model_score_factor_code_sec_4 | varchar(10) |  |
| risk_model_score_factor_code_sec_5 | varchar(10) |  |
| risk_model_score_factor_type_pr_1 | varchar(25) |  |
| risk_model_score_factor_type_pr_2 | varchar(25) |  |
| risk_model_score_factor_type_pr_3 | varchar(25) |  |
| risk_model_score_factor_type_pr_4 | varchar(25) |  |
| risk_model_score_factor_type_pr_5 | varchar(25) |  |
| risk_model_score_factor_type_sec_1 | varchar(25) |  |
| risk_model_score_factor_type_sec_2 | varchar(25) |  |
| risk_model_score_factor_type_sec_3 | varchar(25) |  |
| risk_model_score_factor_type_sec_4 | varchar(25) |  |
| risk_model_score_factor_type_sec_5 | varchar(25) |  |
| status_enum | smallint |  (FK to app_enums) |


### [app_policy_exceptions_rl]
**Purpose**: AKA "Backend Policies", enum (key) / value pair for exceptions such as 'Capacity', 'Credit', and 'Program'

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| notes | varchar(1000) |  |
| policy_exception_type_enum | smallint |  (FK to app_enums) |
| reason_code | varchar(20) |  |


### [app_pricing_rl]
**Purpose**: Data used for calculating loan pricing

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| add_total_to_financed_flag | bit |  |
| cash_down_payment_amount | decimal(12,2) |  |
| debt_to_income_ratio | decimal(12,2) |  |
| invoice_amount | decimal(12,2) |  |
| loan_amount | decimal(12,2) |  |
| loan_term_months | smallint |  |
| manual_adj_dti_ratio | decimal(12,2) |  |
| manual_adj_monthly_debt | decimal(12,2) |  |
| manual_adj_monthly_income | decimal(12,2) |  |
| military_apr | decimal(5,2) |  |
| monthly_debt | decimal(12,2) |  |
| monthly_income | decimal(12,2) |  |
| mrv_grade_pr | char(1) |  |
| mrv_grade_sec | char(1) |  |
| regular_payment_amount | decimal(12,2) |  |
| selling_price | decimal(12,2) |  |
| tradein_allowance | decimal(12,2) |  |
| tradein_down_payment_amount | decimal(12,2) |  |
| tradein_payoff_amount | decimal(12,2) |  |


### [app_transactional_rl]
**Purpose**: values only exist until loan is decisioned (cleaned out by a separate job)

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| assess_florida_doc_fee_flag | bit |  |
| assess_tennessee_doc_fee_flag | bit |  |
| audit_type_enum | smallint |  (FK to app_enums) |
| duplicate_app_flag | bit |  |
| error_message | varchar(255) |  |
| fund_loan_indicator_enum | smallint |  (FK to app_enums) |
| locked_by_user | varchar(80) |  |
| pending_verification_flag | bit |  |
| supervisor_review_indicator_enum | smallint |  (FK to app_enums) |
| suppress_ach_funding_flag | bit |  |


### [app_warranties_rl]
**Purpose**: Enum (key) / value pair for warranties, such as 'Credit Disability', 'Credit Life', 'Extended Warranty', 'Gap Insurance', 'Other', 'Road Side Assistance', and 'Service Contract'

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| amount | decimal(12,2) |  |
| company_name | varchar(50) |  |
| merrick_lienholder_flag | bit |  |
| policy_number | varchar(30) |  |
| term_months | smallint |  |
| warranty_type_enum | smallint |  (FK to app_enums) |

---

### **Additional Recreational Lending Application Support Tables**
Most of the following tables are for lookups that support calculations or track general information that is not related to an specific `app_id`. These values were not in the former XML model; but the tables have been brought into the data model convention to provide visibility

### [app_boarding_rl]
**Purpose**: this table tracks temporary applications waiting to be boarded through a daily 'NACHA' process for finance. This is the one exception from the above statement about using `app_id`. Once an application is boarded, it is removed from this table

| Column | Type | Description |
|--------|------|-------------|
| app_id | int | Application ID (PK, FK to `app_base`, CASCADE DELETE) |
| funding_date | datetime |  |

### [app_cri_index_rl]
**Purpose**: this matrix supplies an APR for each unique 'CRI' score

| Column | Type | Description |
|--------|------|-------------|
| score | int | PK, unique |
| apr | decimal(5,2) |  |

### [app_participation_index_rl]
**Purpose**: lookup table used to determine participation rate

| Column | Type | Description |
|--------|------|-------------|
| id | int | PK |
| app_type_code | varchar(6) |  |
| effective_date | smalldatetime |  |
| is_active_flag | bit |  |
| lookup_priority | tinyint |  |
| participation | decimal(5,2) |  |
| rate_end_range | decimal(5,2) |  |
| rate_start_range | decimal(5,2) |  |

### [app_terms_index_rl]
**Purpose**: lookup table to determine the loan term (months) by loan amount range and application type

| Column | Type | Description |
|--------|------|-------------|
| id | int | PK |
| app_type_code | varchar(6) |  |
| effective_date | smalldatetime |  |
| is_active_flag | bit |  |
| loan_amount_end | decimal(12,2) |  |
| loan_amount_start | decimal(12,2) |  |
| lookup_priority | tinyint |  |
| term | smallint |  |

### [app_vip_dealers_rl]
**Purpose**: this facilitates MAC Portal to display a special 'priority' for loan applications with dealers from this list

| Column | Type | Description |
|--------|------|-------------|
| dealer_num | int | PK, unique  |

### [app_loanpro_dealer_lookup_rl]
**Purpose**: intended as an interim solution, MAC acts as an intermediary for Salesforce (the system-of-record for dealers) to update the dealer information in Loan Pro

| Column | Type | Description |
|--------|------|-------------|
| source_company_id | int | PK, unique |
| dealer_num | int |  |

