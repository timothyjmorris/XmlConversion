/*
=============================================================================
CC Data Validation Scripts - Phase 0.5
=============================================================================
Purpose: Detect data quality issues in CC migration to identify mapping bugs
Created: 2026-02-05
Updated: 2026-02-05 - Fixed column names to match actual schema
Related: docs/onboard_reclending/implementation-plan.md Phase 0.5

Tables Covered (CC only):
  - app_base (shared)
  - app_contact_base (shared)
  - app_contact_address (shared)
  - app_contact_employment (shared)
  - app_operational_cc
  - app_pricing_cc
  - app_solicited_cc

Categories:
1. Column Population Overview
2. Adjacent Data Mismatches  
3. Enum Distribution Analysis
4. Sparse Row Detection
5. Data Quality Summary

Usage:
  Run each section independently in SSMS against the target database
  Or run the entire script for a full validation report
=============================================================================
*/

-- ============================================================================
-- CATEGORY 1: COLUMN POPULATION OVERVIEW
-- Check NULL rates for key columns in each CC table
-- ============================================================================

PRINT '=== CATEGORY 1: COLUMN POPULATION OVERVIEW ===';

-- app_base: Key columns
SELECT 
    'app_base' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN app_source_enum IS NULL THEN 1 ELSE 0 END) AS null_app_source_enum,
    SUM(CASE WHEN app_type_enum IS NULL THEN 1 ELSE 0 END) AS null_app_type_enum,
    SUM(CASE WHEN decision_enum IS NULL THEN 1 ELSE 0 END) AS null_decision_enum,
    SUM(CASE WHEN product_line_enum IS NULL THEN 1 ELSE 0 END) AS null_product_line_enum,
    SUM(CASE WHEN sub_type_enum IS NULL THEN 1 ELSE 0 END) AS null_sub_type_enum,
    SUM(CASE WHEN receive_date IS NULL THEN 1 ELSE 0 END) AS null_receive_date,
    SUM(CASE WHEN decision_date IS NULL THEN 1 ELSE 0 END) AS null_decision_date
FROM dbo.app_base WITH (NOLOCK);

-- app_contact_base: Key columns
SELECT 
    'app_contact_base' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN contact_type_enum IS NULL THEN 1 ELSE 0 END) AS null_contact_type_enum,
    SUM(CASE WHEN fraud_type_enum IS NULL THEN 1 ELSE 0 END) AS null_fraud_type_enum,
    SUM(CASE WHEN birth_date IS NULL THEN 1 ELSE 0 END) AS null_birth_date,
    SUM(CASE WHEN ssn IS NULL THEN 1 ELSE 0 END) AS null_ssn,
    SUM(CASE WHEN first_name IS NULL THEN 1 ELSE 0 END) AS null_first_name,
    SUM(CASE WHEN last_name IS NULL THEN 1 ELSE 0 END) AS null_last_name,
    SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) AS null_email
FROM dbo.app_contact_base WITH (NOLOCK);

-- app_contact_address: Key columns
SELECT 
    'app_contact_address' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN address_type_enum IS NULL THEN 1 ELSE 0 END) AS null_address_type_enum,
    SUM(CASE WHEN ownership_type_enum IS NULL THEN 1 ELSE 0 END) AS null_ownership_type_enum,
    SUM(CASE WHEN city IS NULL THEN 1 ELSE 0 END) AS null_city,
    SUM(CASE WHEN state IS NULL THEN 1 ELSE 0 END) AS null_state,
    SUM(CASE WHEN zip IS NULL THEN 1 ELSE 0 END) AS null_zip
FROM dbo.app_contact_address WITH (NOLOCK);

-- app_contact_employment: Key columns
SELECT 
    'app_contact_employment' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN employment_type_enum IS NULL THEN 1 ELSE 0 END) AS null_employment_type_enum,
    SUM(CASE WHEN income_type_enum IS NULL THEN 1 ELSE 0 END) AS null_income_type_enum,
    SUM(CASE WHEN other_income_type_enum IS NULL THEN 1 ELSE 0 END) AS null_other_income_type_enum,
    SUM(CASE WHEN monthly_salary IS NULL THEN 1 ELSE 0 END) AS null_monthly_salary,
    SUM(CASE WHEN business_name IS NULL THEN 1 ELSE 0 END) AS null_business_name
FROM dbo.app_contact_employment WITH (NOLOCK);

-- app_operational_cc: All columns with NULL counts
SELECT 
    'app_operational_cc' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN priority_enum IS NULL THEN 1 ELSE 0 END) AS null_priority_enum,
    SUM(CASE WHEN process_enum IS NULL THEN 1 ELSE 0 END) AS null_process_enum,
    SUM(CASE WHEN status_enum IS NULL THEN 1 ELSE 0 END) AS null_status_enum,
    SUM(CASE WHEN ssn_match_type_enum IS NULL THEN 1 ELSE 0 END) AS null_ssn_match_type_enum,
    SUM(CASE WHEN verification_source_enum IS NULL THEN 1 ELSE 0 END) AS null_verification_source_enum,
    SUM(CASE WHEN sc_bank_account_type_enum IS NULL THEN 1 ELSE 0 END) AS null_sc_bank_account_type_enum,
    SUM(CASE WHEN sc_debit_funding_source_enum IS NULL THEN 1 ELSE 0 END) AS null_sc_debit_funding_source_enum,
    SUM(CASE WHEN sc_ach_amount IS NULL THEN 1 ELSE 0 END) AS null_sc_ach_amount,
    SUM(CASE WHEN sc_bank_aba IS NULL THEN 1 ELSE 0 END) AS null_sc_bank_aba,
    SUM(CASE WHEN sc_bank_account_num IS NULL THEN 1 ELSE 0 END) AS null_sc_bank_account_num,
    SUM(CASE WHEN housing_monthly_payment IS NULL THEN 1 ELSE 0 END) AS null_housing_monthly_payment,
    SUM(CASE WHEN assigned_to IS NULL THEN 1 ELSE 0 END) AS null_assigned_to,
    SUM(CASE WHEN last_updated_by IS NULL THEN 1 ELSE 0 END) AS null_last_updated_by
FROM dbo.app_operational_cc WITH (NOLOCK);

-- app_pricing_cc: Key columns
SELECT 
    'app_pricing_cc' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN decision_model_enum IS NULL THEN 1 ELSE 0 END) AS null_decision_model_enum,
    SUM(CASE WHEN population_assignment_enum IS NULL THEN 1 ELSE 0 END) AS null_population_assignment_enum,
    SUM(CASE WHEN credit_line IS NULL THEN 1 ELSE 0 END) AS null_credit_line,
    SUM(CASE WHEN credit_line_max IS NULL THEN 1 ELSE 0 END) AS null_credit_line_max,
    SUM(CASE WHEN credit_line_possible IS NULL THEN 1 ELSE 0 END) AS null_credit_line_possible,
    SUM(CASE WHEN card_annual_fee IS NULL THEN 1 ELSE 0 END) AS null_card_annual_fee,
    SUM(CASE WHEN card_purchase_apr IS NULL THEN 1 ELSE 0 END) AS null_card_purchase_apr,
    SUM(CASE WHEN card_cash_advance_apr IS NULL THEN 1 ELSE 0 END) AS null_card_cash_advance_apr,
    SUM(CASE WHEN monthly_income IS NULL THEN 1 ELSE 0 END) AS null_monthly_income,
    SUM(CASE WHEN monthly_debt IS NULL THEN 1 ELSE 0 END) AS null_monthly_debt,
    SUM(CASE WHEN debt_to_income_ratio IS NULL THEN 1 ELSE 0 END) AS null_debt_to_income_ratio
FROM dbo.app_pricing_cc WITH (NOLOCK);


-- ============================================================================
-- CATEGORY 2: ADJACENT DATA MISMATCHES
-- Detect value/enum pairs where one is populated and the other is NULL
-- These may indicate mapping bugs or source data issues
-- ============================================================================

PRINT '';
PRINT '=== CATEGORY 2: ADJACENT DATA MISMATCHES ===';

-- ACH Banking Fields: When amount exists, bank details should too
SELECT 
    'ACH Banking Mismatch Analysis' AS check_name,
    COUNT(*) AS total_with_ach_data,
    SUM(CASE WHEN sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL THEN 1 ELSE 0 END) AS amount_without_type,
    SUM(CASE WHEN sc_ach_amount > 0 AND sc_bank_aba IS NULL THEN 1 ELSE 0 END) AS amount_without_aba,
    SUM(CASE WHEN sc_ach_amount > 0 AND sc_bank_account_num IS NULL THEN 1 ELSE 0 END) AS amount_without_account_num,
    SUM(CASE WHEN sc_bank_account_type_enum IS NOT NULL AND sc_ach_amount IS NULL THEN 1 ELSE 0 END) AS type_without_amount
FROM dbo.app_operational_cc WITH (NOLOCK)
WHERE sc_ach_amount IS NOT NULL 
   OR sc_bank_account_type_enum IS NOT NULL 
   OR sc_bank_aba IS NOT NULL 
   OR sc_bank_account_num IS NOT NULL;

-- Sample rows with ACH mismatches (for investigation)
SELECT TOP 20
    app_id,
    sc_ach_amount,
    sc_bank_account_type_enum,
    sc_bank_aba,
    sc_bank_account_num,
    CASE 
        WHEN sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL THEN 'AMOUNT_WITHOUT_TYPE'
        WHEN sc_bank_account_type_enum IS NOT NULL AND sc_ach_amount IS NULL THEN 'TYPE_WITHOUT_AMOUNT'
        WHEN sc_ach_amount > 0 AND sc_bank_aba IS NULL THEN 'AMOUNT_WITHOUT_ABA'
        ELSE 'OK'
    END AS mismatch_type
FROM dbo.app_operational_cc WITH (NOLOCK)
WHERE (sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL)
   OR (sc_bank_account_type_enum IS NOT NULL AND sc_ach_amount IS NULL);

-- Credit Line Fields: When credit_line exists, related fields may be expected
SELECT 
    'Credit Line Field Analysis' AS check_name,
    COUNT(*) AS total_with_credit_line,
    SUM(CASE WHEN credit_line IS NOT NULL AND credit_line_max IS NULL THEN 1 ELSE 0 END) AS line_without_max,
    SUM(CASE WHEN credit_line IS NOT NULL AND credit_line_possible IS NULL THEN 1 ELSE 0 END) AS line_without_possible,
    SUM(CASE WHEN credit_line IS NULL AND credit_line_max IS NOT NULL THEN 1 ELSE 0 END) AS max_without_line
FROM dbo.app_pricing_cc WITH (NOLOCK)
WHERE credit_line IS NOT NULL 
   OR credit_line_max IS NOT NULL 
   OR credit_line_possible IS NOT NULL;

-- Employment with salary but no income type
SELECT 
    'Employment Income Mismatch' AS check_name,
    COUNT(*) AS total_employment_rows,
    SUM(CASE WHEN monthly_salary > 0 AND income_type_enum IS NULL THEN 1 ELSE 0 END) AS salary_without_income_type,
    SUM(CASE WHEN other_monthly_income > 0 AND other_income_type_enum IS NULL THEN 1 ELSE 0 END) AS other_income_without_type
FROM dbo.app_contact_employment WITH (NOLOCK);


-- ============================================================================
-- CATEGORY 3: ENUM DISTRIBUTION ANALYSIS
-- Show value distribution for all enum columns
-- Helps identify unmapped values or unexpected distributions
-- ============================================================================

PRINT '';
PRINT '=== CATEGORY 3: ENUM DISTRIBUTION ANALYSIS ===';

-- app_base enums
SELECT 'app_base.app_source_enum' AS enum_column, app_source_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_base WITH (NOLOCK) GROUP BY app_source_enum ORDER BY count DESC;

SELECT 'app_base.app_type_enum' AS enum_column, app_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_base WITH (NOLOCK) GROUP BY app_type_enum ORDER BY count DESC;

SELECT 'app_base.decision_enum' AS enum_column, decision_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_base WITH (NOLOCK) GROUP BY decision_enum ORDER BY count DESC;

SELECT 'app_base.product_line_enum' AS enum_column, product_line_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_base WITH (NOLOCK) GROUP BY product_line_enum ORDER BY count DESC;

-- app_contact_base enums
SELECT 'app_contact_base.contact_type_enum' AS enum_column, contact_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_contact_base WITH (NOLOCK) GROUP BY contact_type_enum ORDER BY count DESC;

SELECT 'app_contact_base.fraud_type_enum' AS enum_column, fraud_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_contact_base WITH (NOLOCK) GROUP BY fraud_type_enum ORDER BY count DESC;

-- app_contact_address enums
SELECT 'app_contact_address.address_type_enum' AS enum_column, address_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_contact_address WITH (NOLOCK) GROUP BY address_type_enum ORDER BY count DESC;

SELECT 'app_contact_address.ownership_type_enum' AS enum_column, ownership_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_contact_address WITH (NOLOCK) GROUP BY ownership_type_enum ORDER BY count DESC;

-- app_contact_employment enums
SELECT 'app_contact_employment.employment_type_enum' AS enum_column, employment_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_contact_employment WITH (NOLOCK) GROUP BY employment_type_enum ORDER BY count DESC;

SELECT 'app_contact_employment.income_type_enum' AS enum_column, income_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_contact_employment WITH (NOLOCK) GROUP BY income_type_enum ORDER BY count DESC;

SELECT 'app_contact_employment.other_income_type_enum' AS enum_column, other_income_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_contact_employment WITH (NOLOCK) GROUP BY other_income_type_enum ORDER BY count DESC;

-- app_operational_cc enums
SELECT 'app_operational_cc.process_enum' AS enum_column, process_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_operational_cc WITH (NOLOCK) GROUP BY process_enum ORDER BY count DESC;

SELECT 'app_operational_cc.status_enum' AS enum_column, status_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_operational_cc WITH (NOLOCK) GROUP BY status_enum ORDER BY count DESC;

SELECT 'app_operational_cc.priority_enum' AS enum_column, priority_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_operational_cc WITH (NOLOCK) GROUP BY priority_enum ORDER BY count DESC;

SELECT 'app_operational_cc.ssn_match_type_enum' AS enum_column, ssn_match_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_operational_cc WITH (NOLOCK) GROUP BY ssn_match_type_enum ORDER BY count DESC;

SELECT 'app_operational_cc.verification_source_enum' AS enum_column, verification_source_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_operational_cc WITH (NOLOCK) GROUP BY verification_source_enum ORDER BY count DESC;

SELECT 'app_operational_cc.sc_bank_account_type_enum' AS enum_column, sc_bank_account_type_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_operational_cc WITH (NOLOCK) GROUP BY sc_bank_account_type_enum ORDER BY count DESC;

SELECT 'app_operational_cc.sc_debit_funding_source_enum' AS enum_column, sc_debit_funding_source_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_operational_cc WITH (NOLOCK) GROUP BY sc_debit_funding_source_enum ORDER BY count DESC;

-- app_pricing_cc enums
SELECT 'app_pricing_cc.decision_model_enum' AS enum_column, decision_model_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_pricing_cc WITH (NOLOCK) GROUP BY decision_model_enum ORDER BY count DESC;

SELECT 'app_pricing_cc.population_assignment_enum' AS enum_column, population_assignment_enum AS enum_value, COUNT(*) AS count
FROM dbo.app_pricing_cc WITH (NOLOCK) GROUP BY population_assignment_enum ORDER BY count DESC;


-- ============================================================================
-- CATEGORY 4: SPARSE ROW DETECTION
-- Rows with very few populated columns may indicate failed processing
-- ============================================================================

PRINT '';
PRINT '=== CATEGORY 4: SPARSE ROW DETECTION ===';

-- app_operational_cc: Find rows with minimal data
-- Count non-null columns per row (excluding app_id which is always populated)
WITH sparse_check AS (
    SELECT 
        app_id,
        (CASE WHEN assigned_to IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN auth_user_spouse_flag IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN backend_fico_grade IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN backend_risk_grade IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN cb_score_factor_code_1 IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN housing_monthly_payment IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN last_bureau_pulled_type IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN priority_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN process_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN status_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN ssn_match_type_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN verification_source_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN sc_ach_amount IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN sc_bank_account_type_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN regb_start_date IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN regb_end_date IS NOT NULL THEN 1 ELSE 0 END
        ) AS non_null_count
    FROM dbo.app_operational_cc WITH (NOLOCK)
)
SELECT 
    'app_operational_cc sparse rows' AS check_name,
    non_null_count,
    COUNT(*) AS row_count
FROM sparse_check
GROUP BY non_null_count
ORDER BY non_null_count;

-- app_pricing_cc: Find rows with minimal data
WITH sparse_check AS (
    SELECT 
        app_id,
        (CASE WHEN account_number IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN campaign_num IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN card_annual_fee IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN card_purchase_apr IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN card_cash_advance_apr IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN credit_line IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN credit_line_max IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN decision_model_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN population_assignment_enum IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN monthly_income IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN monthly_debt IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN debt_to_income_ratio IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN pricing_tier IS NOT NULL THEN 1 ELSE 0 END
        ) AS non_null_count
    FROM dbo.app_pricing_cc WITH (NOLOCK)
)
SELECT 
    'app_pricing_cc sparse rows' AS check_name,
    non_null_count,
    COUNT(*) AS row_count
FROM sparse_check
GROUP BY non_null_count
ORDER BY non_null_count;

-- Show sample of very sparse operational rows (< 3 non-null fields)
SELECT TOP 10 
    o.app_id,
    o.process_enum,
    o.status_enum,
    o.ssn_match_type_enum,
    b.decision_enum,
    b.receive_date
FROM dbo.app_operational_cc o WITH (NOLOCK)
INNER JOIN dbo.app_base b WITH (NOLOCK) ON o.app_id = b.app_id
WHERE (CASE WHEN o.process_enum IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN o.status_enum IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN o.ssn_match_type_enum IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN o.verification_source_enum IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN o.sc_ach_amount IS NOT NULL THEN 1 ELSE 0 END
      ) < 2;


-- ============================================================================
-- CATEGORY 5: DATA QUALITY SUMMARY
-- Overall statistics for quick assessment
-- ============================================================================

PRINT '';
PRINT '=== CATEGORY 5: DATA QUALITY SUMMARY ===';

SELECT 
    'Row Counts' AS metric,
    (SELECT COUNT(*) FROM dbo.app_base WITH (NOLOCK)) AS app_base,
    (SELECT COUNT(*) FROM dbo.app_contact_base WITH (NOLOCK)) AS app_contact_base,
    (SELECT COUNT(*) FROM dbo.app_contact_address WITH (NOLOCK)) AS app_contact_address,
    (SELECT COUNT(*) FROM dbo.app_contact_employment WITH (NOLOCK)) AS app_contact_employment,
    (SELECT COUNT(*) FROM dbo.app_operational_cc WITH (NOLOCK)) AS app_operational_cc,
    (SELECT COUNT(*) FROM dbo.app_pricing_cc WITH (NOLOCK)) AS app_pricing_cc,
    (SELECT COUNT(*) FROM dbo.app_solicited_cc WITH (NOLOCK)) AS app_solicited_cc;

-- Key enum population rates
SELECT 
    'Enum Population %' AS metric,
    CAST(100.0 * SUM(CASE WHEN app_source_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS app_source,
    CAST(100.0 * SUM(CASE WHEN app_type_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS app_type,
    CAST(100.0 * SUM(CASE WHEN decision_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS decision,
    CAST(100.0 * SUM(CASE WHEN product_line_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS product_line
FROM dbo.app_base WITH (NOLOCK);

SELECT 
    'Operational Enum %' AS metric,
    CAST(100.0 * SUM(CASE WHEN process_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS process_enum,
    CAST(100.0 * SUM(CASE WHEN status_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS status_enum,
    CAST(100.0 * SUM(CASE WHEN ssn_match_type_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS ssn_match,
    CAST(100.0 * SUM(CASE WHEN sc_bank_account_type_enum IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS DECIMAL(5,1)) AS bank_acct_type
FROM dbo.app_operational_cc WITH (NOLOCK);

-- Critical issues summary
SELECT 
    'Critical Issues' AS category,
    (SELECT COUNT(*) FROM dbo.app_operational_cc WITH (NOLOCK) 
     WHERE sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL) AS ach_without_bank_type,
    (SELECT COUNT(*) FROM dbo.app_operational_cc WITH (NOLOCK) 
     WHERE process_enum IS NULL) AS missing_process_enum,
    (SELECT COUNT(*) FROM dbo.app_base WITH (NOLOCK) 
     WHERE decision_enum IS NULL) AS missing_decision_enum,
    (SELECT COUNT(*) FROM dbo.app_contact_base WITH (NOLOCK) 
     WHERE contact_type_enum IS NULL) AS missing_contact_type;
