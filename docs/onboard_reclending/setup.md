# RecLending Requirements & Background Reference

> **Note**: This document provides domain requirements and background context for the RecLending onboarding effort. For the active implementation plan with phased tasks and acceptance criteria, see [implementation-plan.md](implementation-plan.md).

## Introduction

While the RecLending product line has much less volume in production that needs to be migrated, there are additional complexities that must be accounted for. This document outlines those known differences and requirements.

### Guiding Principles

1. **DO NO HARM** - The app currently works with CreditCard as default. No CC functionality changes without explicit decision.
2. **Verify new features** - Test-first development with acceptance criteria.
3. **Small batches** - Work in phases with incremental delivery.

## Priority for Shared Functionality
  This document uncovers and summarizes work on 4 new destination tables that all product lines need to support, which will need new `mapping_type`'s. 
  First ensure current system stability by 
  1. Running the test suite with 100% required passing status
  2. Running the [environment prep tool](../../env_prep/appxml_staging_orchestrator.py)
  3. Running the [xml migrator](../../run_production_processor.py) with manual smoke validation

  Then prioritize this shared work (for current CreditCard) with manual and automated or scripted source-to-destination validation. The shared work prepares us for the new and unique work that is required to support the RecLending product line with confidence.

## Resources

  1. [create-reclending-tables](/config/samples/create_destination_tables_rl.sql) 
  2. [mac-data-model-dictionary-guide](../mac-data-model-dictionary-guide.md)
  3. [migrate-reclending-tables](/config/samples/migrate_table_logic_rl.sql)
  4. [spreadsheet for initial mapping](xml-source-to-database-contract-rl.csv)
  5. [folder of example fource files, ending in '-rl'](../../config/samples/xml_files/reclending)

  Challenge and adopt these documents: ensure they accurately reflect current functionality down to a low level:
  - [validation-and-testing](../validation-and-testing-strategy.md) - NOTE: this much be re-boarded, updated, and embedded into the current work
  - [data-intake-and-prep](../data-intake-and-preparation.md) - NOTE: this much be re-boarded, updated, and embedded into the current work


## Testing and Acceptance Criteria
  My hope is that based on what we _know_ about current functionality and the additional requirements for RecLending, that our test-first approach will include Acceptance Criteria derived from our plan and used build and test our product as a living and guiding list of requirements that help us determine when we're done and provides the confidence to make incremental adjustments.

  Something I've really only done manually, is validate or reconcile data.  We need to expand and "prove" that the data outcome was correct. We need to secondarily account for verifying destination data against xml. This might be done with some testing, or a utility. I need some options here.

  Note: not all tests have to begin automated; work in smaller batches to provide incremental solutions. There is an opportunity to create some other SQL scripts (to find patterns, like certain data that is expected to be together, or fallback defaults/enums we don't really want to see) or Python utility to help discover anomolous or unexpected behaviour outside of what the mapping_contract expects (which can happen from unexpected structures or data for sure). It would be helpful to be able to compare the source app_xml to the destination data model to start with (which can be expanded to include some risk-based sampling).

  I am ok with simpler bullet-point requirements over full Gherkin-style BDD.

### Current Tests
  We have a variety of tests that you will need to compare against functionality in code to find gaps and suggests "meaningful" tests. Code coverage is not the deliverable, software that performs correctly is. Being able to release with confidence is the goal, and that implies a responsible level of coverage. 
    def test_all_mapping_types_supported(self):
  - All tests in the [full test suite](../../tests/run_comprehensive_suite.py) pass except for one test (`test_all_mapping_types_supported`), which should be easy to reconcile.
  - There are two very helpful e2e tests that are run manually.
  - There are a few tests that check for RL schema so that it will be excluded. The application and tests of course will need to be adjusted so that product lines check and only use the appropriate schema.


## Updating Current Documentation
  It is very **important** that as we build and refine new functionality or features, that our documentation remains accurate and relevant. These include ADRs/decisions, feature lists, readme's, etc
    - `datamapper-functions.md`, reconcile this now against tests and application functionality first - and then update it as we iterate
    - `architecture-quickstart.md`
    - `deployment-guide.md`
    - `data-intake-and-preparation.md`
    - `exception-hierarchy-guide.md`

## New Schema to Isolate testing
  We'll be configuring the mapping contracts to use `migration` as the schema to use for initial development

## Applicants
  Different than the occaisional 'AUTHU' role in CreditCard, the RecLending product line frequently has a secondary applicant that plays a prominent role in the decision process. Therefore, there are lots of fields that are companions to each other, always named with a `_pr` or `_sec` in the new destination column name `ac_role_tp_c` is the key distguisher - and already built-in to the mapping contract. 

## New RecLending-specific Tables
  - app_collateral_rl, **Purpose**: Store all collaterals by `collateral_type_enum`
  - app_dealer_rl, **Purpose**: Snapshot of Dealer information (may update through lifecycle of application)
  - app_funding_rl, **Purpose**: Immutable calculated system values
  - app_funding_checklist_rl, **Purpose**: Decisions made or validation to approve a loan for funding
  - app_funding_contract_rl, **Purpose**: Final "Contract" details
  - app_policy_exceptions_rl, **Purpose**: AKA "Backend Policies", enum (key) / value pair for exceptions (1:many)
  - app_pricing_rl, **Purpose**: columns need to calculate the loan
  - app_transactional_rl, **Purpose**: values only exist until loan is decisioned (cleaned out by a separate job)
  - app_warranties_rl, **Purpose**: Enum (key) / value pair for warranties (1:many)
  - 
  
  [See guide](../mac-data-model-dictionary-guide.md)

  ```
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
    ├── app_report_results_lookup (1:many)
    ├── app_historical_lookup (1:many)
    │
    ├── indicators (1:many common)
    └── scores (1:many common)
  ```

## Mapping Contract
  Obviously, we'll need to support an additional mapping contract.
  - incorporate "product_line=RL" into our CLI (default to CC)
  - which points to `mapping_contract_rl.json`
  - if it's helpful, we can include a specific node in the contract to additionally call out the product line.

  I've created a spreadsheet as the initial source for the mapping contract, which includes source-to-destination, mapping type, and expressions for calculated fields. The mapping type's that are set simply as 'enums' will need you to derive those lists from [script](../../config/samples/migrate_table_logic_rl.sql).
  
  We use the **structure** for the [CC mapping contract](../../config/mapping_contract.json), but not the content - except probably the `enum_mappings` section.

  Once that's setup, I think we can create a new RL mirror of a test we have for CC that compares the JSON contract to the actual database schema for column/field and type reconciliation, [test](../../tests/contracts/test_mapping_contract_schema.py). The SQL script is there for early reference, the database and the mapping contract wil be the source of truth and direction.

  In the spirit of TDD and writing failing tests first, I think this will be very helpful to start and reconcile for all of our new mapping types and expression functionality [test](../../tests/contracts/test_mapping_types_and_expressions.py)


## Resources Provided
The schema is a similar nested structure with everything we need in the "IL_application" node. It follows the same pattern as CreditCard with multiple contacts inside the application node.

- DDL Script that created the RL tables, [script](../../config/samples/create_destination_tables_rl.sql)
- DML Script that ran on existing tables as a Proof of Concept, [script](../../config/samples/migrate_table_logic_rl.sql) - we should be able to derive new enum lists for mapping contract
- DML Script used to create enums, [script](../../config/samples/insert_enum_values.sql)
- Example source XML files, with "-rl" in the name added to "config/samples/xml_files"
- Spreadsheet as initial source for `TODO`
  

## Collaterals
  Collateral is type of vehicle or vehicle-component that the RecLending Installment Loan is being used for. There are currently up to 4 fixed positions in the xml that will be mapped into a new normalized table using the fixed (1-4) position and some other information to infer a collateral_type_enum.
  We may need some new functionality to support this dynamic enum. Here is an example of the proposed dynamic-to-enum field CASE statement that we can probabaly used as a calculated_field type to dynamically determine the enum as output. I'm open to suggestions here, maybe it makes sense to have a new field type.
  ```
  "CASE 
  WHEN TRIM(IL_application.app_type_code) = 'MARINE' THEN 412
  WHEN TRIM(IL_application.app_type_code) = 'RV' THEN 419 
  WHEN TRIM(IL_application.app_type_code) = 'HT' THEN 415 
  WHEN TRIM(IL_application.app_type_code) = 'UT' THEN 421 
  WHEN TRIM(IL_application.app_type_code) = 'MC' THEN 416 
  WHEN TRIM(IL_application.app_type_code) = 'OR' AND TRIM(IL_application.sub_type_code) = 'ATV' THEN 410
  WHEN TRIM(IL_application.app_type_code) = 'OR' AND TRIM(IL_application.sub_type_code) = 'UTV' THEN 422
  WHEN TRIM(IL_application.app_type_code) = 'OR' AND TRIM(IL_application.sub_type_code) = 'PWC' THEN 418 
  WHEN TRIM(IL_application.app_type_code) = 'OR' AND TRIM(IL_application.sub_type_code) = 'SNOWMOBILE' THEN 420 
  WHEN TRIM(IL_application.app_type_code) IS NOT EMPTY THEN 423
  END"
  ```

  > See [create-reclending-tables](/config/samples/create_destination_tables_rl.sql) as the authoritative table definitions and [mac-data-model-dictionary-guide](../mac-data-model-dictionary-guide.md) as a guide -- the guide **MUST BE UPDATED** to reflect the actual tables.


## Calculated Fields
  - If it's not already implicit in our handling of strings with spaces before/after, we need have a `TRIM()` function for calculated_field types. We need it to help evaluate if a field is really empty an also for character-padded fields
  - Confirm that `ELSE ''` returns `NULL` in a calculated_field type - and doesn't result in a value being inserted into the database. Otherwise, we'll need `EMPTY` or something.
  - We'll need a new mapping type to support the scenerio where we have a field in each contact-type with each one going to a different fixed destination column. For example
  -  - `<IL_address ac_role_tp_c="PR" residence_monthly_pymnt="944.38" />` -> `app_operational_rl.housing_monthly_payment_pr`
  -  - `<IL_address ac_role_tp_c="SEC" residence_monthly_pymnt="1377" />` -> `app_operational_rl.housing_monthly_payment_sec`
  
  We might be able to chain some mapping_type functionality together, i.e. use `last_valid_pr_contact` -- oh, implicit that we should have a new `last_valid_sec_contact`. There's a limited number of these fields (2 that I know of), but we may opt for using a function-like syntax passing it the destination field (`contact-type-to-field(housing_monthly_payment_pr)`) and creating a mapping entry twice - seems kludgy, or just flagging the field and deriving what to do based on it's attribute name.  Please advise.


## Additional `address_type_enum`'s
  - `PATR` for Patriot Act address
  - `COLL` for address where Collateral will be located at (address handled like a contact address)


## [app_historical_lookup] Table
  **Purpose**: this is specifically used for older columns in the xml and old data model that are being deprecated, but we want to save the old value (for auditing).  
  This is a new type of output table and supports all product lines. This is essentially a key/value pair table - which an additional `source` field to note where it originally came from. We'll need to make an accommodation for this with a new mapping type I think, because we need `name` and `source` in addition to the `value`. Only create a row in the table if there is "meaningful" data, defined by having a value. Unlike the `scores` data type, we don't need to pass it a value; we can derive it from the mapping_contract and the xml attribute value -- unless it's easier (less code to pass it the name of the table like a parameter or something).  Call it `add_history`.

  - name: use the old xml attribute
  - source: derive from the xml path from the right, up until the first slash it finds
  - both name and source should be surrounded in square brackets to signify they are SQL objects.

  > See [create-reclending-tables](/config/samples/create_destination_tables_rl.sql) as the authoritative table definitions and [mac-data-model-dictionary-guide](../mac-data-model-dictionary-guide.md) as a guide -- the guide **MUST BE UPDATED** to reflect the actual tables.


## [app_report_results_lookup] Table
  **Purpose**: similar to the historical lookup, this moves attributes to another key-pair table. This is not an archive table. The name for the pair will be the source attribute.  Call it `add_report_lookup`.



## [scores] Table
  **Purpose**: this is an existing table that supports all product line loan applications. It is a key/value pair that stores numeric scores from credit bureau's and risk models by a type or tag. Only one type is allowed per app_id, enforced by table constraint - so we should fail gracefully from that (without consequence) - or potentially update the value. 
  We'll need a specific new `mapping_type` for the mapping_contract. I suggest passing it the name of the score being created from the attribute value being used, like `add_score(TU_TIE)`. There won't be any spaces in the name and the value will need to be coerced to an integer, 0 is allowed but non-meangingful empty rows are disallowed.

  `scores` table
  | column           | datatype      |
  |------------------|---------------|
  | app_id           | numeric(18,0) |
  | score            | int           |
  | score_identifier | varchar(50)   |


## [indicators] Table
  **Purpose**: this is an existing table that supports all product line loan applications. It is a key/value pair that stores persisted information about the application by a type or ("indicator"). Only one type is allowed per app_id, enforced by table constraint - so we should fail gracefully from that (without consequence) - or potentially update the value. 
  We'll need two different mapping types to support indicators

  `indicators` table
  | column    | datatype      |
  |-----------|---------------|
  | app_id    | numeric(18,0) |
  | indicator | varchar(50)   |
  | value     | varchar(250)  |

### Field-to-Indicator Mapping Type 
  An XML field value will trigger an insert into the `indicators` table by passing it the name for the indicator and the value will be the XML attribute value. There's only a handful of these types, so we're not going to make it super flexible.  The known fields we want to add have a value of 'Y' and we'll just put that in without a complicated expression.
  For example, a source of: `<app_product intrnl_fraud_ssn_ind="Y" />`, and a mapping_type of `add_indicator(InternalFraudSSN)`, when it equals 'Y' then we'll insert indicator='InternalFraudSSN' and value='1'. Ignore all the other values. Sort of hard-coded instead of passing the value we're looking for and the value we want to map it to. Non-meaningful empty rows are disallowed.

### [ ] TBD: Indicator-to-Field Mapping Type
  The case here is that in the XML application element / attribute combination that needs to be formalized as a lookup value for `priority_enum`. Here again, I only have a few examples, so we don't have to make it flexible; there are just two fixed value-pairs. The thing that is **VERY DIFFERENT** is that this is an array in the application element, not a field-level map. I think that means we'd have to look here for every application -- maybe using a lookup from the contract to specify ID, value, and target field and value. For this reason, I'm marking as lower-priority for your analysis and suggestions.
  
  Example XML  
  ```xml
  <Indicators>
    <Indicator ID="TU_Doc_Verification" value="P" />
    <Indicator ID="rlaudit" value="R" />
  </Indicators>
  ```

  Transformation
  - `ID="TU_Doc_Verification" value="R"` is `priority_enum` = 83
  - `ID="TU_Doc_Verification" value="P"` is `priority_enum` = 84
  - `ID="rlaudit" value="" value="R"` is `audit_type_enum` = 706
  - `ID="rlaudit" value="" value="P"` is `audit_type_enum` = 707


## [app_policy_exceptions_rl] Table
  AKA "Backend Policies". We'll need a new mapping type to capture notes, type, and code.
  There are 3 sets of fields that need to be converted to a normalized table, and a companion 'notes' field. We'll use a new mapping type, but the question is what's the simplest way to get these values out? We don't have to worry about future purposes, since this is a one-time migration. Let's use a mapping type with a clear parameter that we pass the enum value `policy_exceptions(630)` which will derive the notes from the correct source. Only create a row in the table if there is "meaningful" data, defined by notes. As you'll see, there is one of the sources that won't pass an enum `override_type_code_notes`.

  **It looks like the data format has changed over time that we'll have to accommodate**, which I think we can COALESCE for.

  Three core fields: capacity, collateral, and credit. They used to each have a companion notes field

  | enum | reason_code                     | notes                                |
  |------|---------------------------------|--------------------------------------|
  | 630  | `override_capacity`             | `capacity_exception_notes`           |
  | 631  | `override_credit`               | `credit_exception_notes`             |
  | 632  | `override_collateral_program`   | `collateral_program_exception_notes` |

  Recently the data is arranged with a single notes field: `override_type_code_notes` which corresponds to one or many core fields/`reason_code`. In this case, we will insert each reason_code listed with the same value from `@override_type_code_notes` attribute.

  Example current data

  | override_capacity | override_collateral_program | override_credit | override_type_code_notes                   |
  |-------------------|-----------------------------|-----------------|--------------------------------------------|
  | EXDTIIR           |                             |                 | DTI at Experian 45%, okay based on ....    |
  |                   |                             | MFSCORE         | Reprocessed credit, no material change ... |
  |                   | LTLGT1K                     |                 | Downpayment is 9.48% over for...           |
  | MDPGT1M           |                             | RTALT90         | New dealer did not understand program ...  |

  > See [create-reclending-tables](/config/samples/create_destination_tables_rl.sql) as the authoritative table definitions and [mac-data-model-dictionary-guide](../mac-data-model-dictionary-guide.md) as a guide -- the guide **MUST BE UPDATED** to reflect the actual tables.


## [app_warranties_rl] Table
  Another normalized table that we need to put xml values into and distinguish it now by type (`warranty_type_enum`). They all behave similiarly, just using different fields. Again, open to simple sturdy implementation options. Only create a row in the table if there is "meaningful" data, defined by an amount.
  We'll need a specific new `mapping_type` for the mapping_contract, similar to some other new ones, I suggest we clarify purpose by passing it the enum value like `warranty_field(623)`.

  There 6 types:
    - Credit Disability   | warranty_type_enum = 620
    - Credit Life         | warranty_type_enum = 621
    - Extended Warranty   | warranty_type_enum = 622
    - Gap Insurance       | warranty_type_enum = 623
    - Other               | warranty_type_enum = 624
    - Roadside Assistance | warranty_type_enum = 625
    - Service Contract    | warranty_type_enum = 626

  Each type come in a set of 5 (actually there's only one merrick_lienholder_flag, from `gap_lien`, but I think we can apply the same pattern because they won't be there), here's the pattern (all source field will be in the contract)
    - amount = [field_name]_amount
    - company_name = [field_name]_company
    - policy_number = [field_name]_policy
    - term_months = If [field_name]_term IS EMPTY THEN 0
    - merrick_lienholder_flag = If [field_name]_lien = 'Y' Then 1 Else 0

  > See [create-reclending-tables](/config/samples/create_destination_tables_rl.sql) as the authoritative table definitions and [mac-data-model-dictionary-guide](../mac-data-model-dictionary-guide.md) as a guide -- the guide **MUST BE UPDATED** to reflect the actual tables.


## Enum lookup values for `code_to_email_enum`
  This maps `loan_officer_responsible_code` to their email. The interesting thing about this is that I'd like to use it also as the fallback to an ELSE condition on a calculated field (`check_requested_by_user`), which has a combination of names and codes. This is the list for those codes. Probably just defined a specific new type of calculated field for "check_requested_by_user". Open to suggestions if it makes sense and keeps it simpler to leverage another field type.

  > See [migrate-reclending-tables](/config/samples/migrate_table_logic_rl.sql)


```json
"officer_code_to_email_enum": {
	"6009": "abbey.harrison@merrickbank.com",
	"6019": "alejandro.sanabria@merrickbank.com",
	"6012": "ashley.hille@merrickbank.com",
	"6020": "austin.murray@merrickbank.com",
	"5094": "barrett.wardenburg@merrickbank.com",
	"6015": "carolyn.blair@merrickbank.com",
	"6000": "chelsea.beall@merrickbank.com",
	"5036": "chelsey.rowberry@merrickbank.com",
	"6013": "christy.russell@merrickbank.com",
	"5089": "david.dennison@merrickbank.com",
	"6010": "david.mendenhall@merrickbank.com",
	"6001": "debbie.williams@merrickbank.com",
	"6103": "diana.guzman@merrickbank.com",
	"5077": "elisha.rhodes@merrickbank.com",
	"6005": "erin.mortensen@merrickbank.com",
	"6107": "gina.voravongsa@merrickbank.com",
	"6016": "heather.kessler@merrickbank.com",
	"5069": "jana.jensen@merrickbank.com",
	"5065": "jason.fitzsimmons@merrickbank.com",
	"5095": "jax.esmay@merrickbank.com",
	"6008": "jessica.fortmuller@merrickbank.com",
	"5072": "joshua.bryant@merrickbank.com",
	"9998": "joshua.ramsey@merrickbank.com",
	"6210": "kaley.gillis@merrickbank.com",
	"3000": "merrick.bank@merrickbank.com",
	"5061": "mike.tsouras@merrickbank.com",
	"6007": "mindi.bartlam@merrickbank.com",
	"6004": "natalie.lee@merrickbank.com",
	"5059": "scott.garton@merrickbank.com"
}
```
