/*
=============================================================================
CC Data Validation Scripts - Phase 0.5
=============================================================================
Purpose: Detect data quality issues in CC migration to identify mapping bugs
Created: 2026-02-05
Related: docs/onboard_reclending/implementation-plan.md Phase 0.5

Categories:
1. Unpopulated Columns Analysis
2. Adjacent Data Mismatches  
3. Enum Without Associated Value
4. Sparse Row Detection
5. Expected Enum Coverage

Usage:
  Run each section independently in SSMS against the target database
  Adjust schema name (dbo/sandbox/migration) as needed
=============================================================================
*/

-- Configuration: Set your target schema
DECLARE @schema NVARCHAR(50) = 'dbo';

-- ============================================================================
-- CATEGORY 1: UNPOPULATED COLUMNS ANALYSIS
-- Find columns that are entirely NULL across all rows
-- May indicate mapping gaps or source data issues
-- ============================================================================

PRINT '=== CATEGORY 1: UNPOPULATED COLUMNS ==='

-- app_operational_cc: Check for columns with 0% population
SELECT 
    'app_operational_cc' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN assigned_credit_analyst IS NULL THEN 1 ELSE 0 END) AS null_assigned_credit_analyst,
    SUM(CASE WHEN auth_user_issue_card_flag IS NULL THEN 1 ELSE 0 END) AS null_auth_user_issue_card_flag,
    SUM(CASE WHEN auth_user_spouse_flag IS NULL THEN 1 ELSE 0 END) AS null_auth_user_spouse_flag,
    SUM(CASE WHEN cb_score_factor_code_1 IS NULL THEN 1 ELSE 0 END) AS null_cb_score_factor_code_1,
    SUM(CASE WHEN last_updated_by IS NULL THEN 1 ELSE 0 END) AS null_last_updated_by,
    SUM(CASE WHEN last_updated_date IS NULL THEN 1 ELSE 0 END) AS null_last_updated_date,
    SUM(CASE WHEN priority_enum IS NULL THEN 1 ELSE 0 END) AS null_priority_enum,
    SUM(CASE WHEN process_enum IS NULL THEN 1 ELSE 0 END) AS null_process_enum,
    SUM(CASE WHEN status_enum IS NULL THEN 1 ELSE 0 END) AS null_status_enum,
    SUM(CASE WHEN sc_ach_amount IS NULL THEN 1 ELSE 0 END) AS null_sc_ach_amount,
    SUM(CASE WHEN sc_bank_account_type_enum IS NULL THEN 1 ELSE 0 END) AS null_sc_bank_account_type_enum
FROM dbo.app_operational_cc;

-- app_pricing_cc: Check for columns with 0% population
SELECT 
    'app_pricing_cc' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN credit_limit IS NULL THEN 1 ELSE 0 END) AS null_credit_limit,
    SUM(CASE WHEN annual_fee IS NULL THEN 1 ELSE 0 END) AS null_annual_fee,
    SUM(CASE WHEN cash_advance_apr IS NULL THEN 1 ELSE 0 END) AS null_cash_advance_apr,
    SUM(CASE WHEN purchase_apr IS NULL THEN 1 ELSE 0 END) AS null_purchase_apr
FROM dbo.app_pricing_cc;

-- Dynamic version: Find ALL columns that are 100% NULL in any CC table
SELECT 
    t.name AS table_name,
    c.name AS column_name,
    'SELECT COUNT(*) AS total, SUM(CASE WHEN [' + c.name + '] IS NULL THEN 1 ELSE 0 END) AS nulls FROM ' + @schema + '.' + t.name AS check_query
FROM sys.tables t
INNER JOIN sys.columns c ON t.object_id = c.object_id
WHERE t.name LIKE 'app_%_cc' OR t.name IN ('app_base', 'app_contact_base', 'app_contact_address', 'app_contact_employment')
ORDER BY t.name, c.name;


-- ============================================================================
-- CATEGORY 2: ADJACENT DATA MISMATCHES
-- Detect value/enum pairs where one is populated and the other is NULL
-- Example: sc_ach_amount has value, sc_bank_account_type_enum is NULL
-- ============================================================================

PRINT '=== CATEGORY 2: ADJACENT DATA MISMATCHES ==='

-- sc_* columns: ACH amount without bank account type
SELECT 
    'sc_ach_amount vs sc_bank_account_type_enum' AS mismatch_type,
    COUNT(*) AS mismatch_count
FROM dbo.app_operational_cc
WHERE sc_ach_amount IS NOT NULL 
  AND sc_bank_account_type_enum IS NULL;

-- Show sample rows with mismatched sc_ columns
SELECT TOP 10
    app_id,
    sc_ach_amount,
    sc_bank_account_type_enum,
    sc_ach_routing_num,
    sc_ach_account_num
FROM dbo.app_operational_cc
WHERE sc_ach_amount IS NOT NULL 
  AND sc_bank_account_type_enum IS NULL;

-- Check all sc_* related columns for consistency
SELECT 
    app_id,
    sc_ach_amount,
    sc_ach_account_num,
    sc_ach_routing_num,
    sc_bank_account_type_enum,
    CASE 
        WHEN sc_ach_amount IS NOT NULL AND sc_bank_account_type_enum IS NULL THEN 'AMOUNT_WITHOUT_TYPE'
        WHEN sc_ach_amount IS NULL AND sc_bank_account_type_enum IS NOT NULL THEN 'TYPE_WITHOUT_AMOUNT'
        WHEN sc_ach_account_num IS NOT NULL AND sc_bank_account_type_enum IS NULL THEN 'ACCOUNT_WITHOUT_TYPE'
        ELSE 'OK'
    END AS validation_status
FROM dbo.app_operational_cc
WHERE sc_ach_amount IS NOT NULL 
   OR sc_ach_account_num IS NOT NULL 
   OR sc_ach_routing_num IS NOT NULL 
   OR sc_bank_account_type_enum IS NOT NULL;


-- ============================================================================
-- CATEGORY 3: ENUM WITHOUT ASSOCIATED VALUE
-- Inverse pattern - enum populated but value field empty
-- ============================================================================

PRINT '=== CATEGORY 3: ENUM WITHOUT ASSOCIATED VALUE ==='

-- Bank account type enum without any account data
SELECT 
    'sc_bank_account_type_enum without account data' AS mismatch_type,
    COUNT(*) AS mismatch_count
FROM dbo.app_operational_cc
WHERE sc_bank_account_type_enum IS NOT NULL 
  AND sc_ach_amount IS NULL
  AND sc_ach_account_num IS NULL
  AND sc_ach_routing_num IS NULL;

-- Decision enum without related decision data (check app_base)
SELECT 
    'decision_enum analysis' AS check_type,
    decision_enum,
    COUNT(*) AS count_by_enum
FROM dbo.app_base
GROUP BY decision_enum
ORDER BY decision_enum;


-- ============================================================================
-- CATEGORY 4: SPARSE ROW DETECTION
-- Rows with >80% NULL columns - may indicate failed processing
-- ============================================================================

PRINT '=== CATEGORY 4: SPARSE ROW DETECTION ==='

-- app_operational_cc: Count non-null columns per row
-- Adjust threshold as needed (e.g., <5 non-null columns out of ~40)
SELECT 
    app_id,
    (CASE WHEN assigned_credit_analyst IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN auth_user_issue_card_flag IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN auth_user_spouse_flag IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN cb_score_factor_code_1 IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN cb_score_factor_code_2 IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN cb_score_factor_code_3 IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN cb_score_factor_code_4 IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN cb_score_factor_code_5 IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN last_updated_by IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN last_updated_date IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN priority_enum IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN process_enum IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN status_enum IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN regb_end_date IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN regb_start_date IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN sc_ach_amount IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN sc_bank_account_type_enum IS NOT NULL THEN 1 ELSE 0 END
    ) AS non_null_count
FROM dbo.app_operational_cc
HAVING (CASE WHEN assigned_credit_analyst IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN auth_user_issue_card_flag IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN auth_user_spouse_flag IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN cb_score_factor_code_1 IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN cb_score_factor_code_2 IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN cb_score_factor_code_3 IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN cb_score_factor_code_4 IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN cb_score_factor_code_5 IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN last_updated_by IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN last_updated_date IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN priority_enum IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN process_enum IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN status_enum IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN regb_end_date IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN regb_start_date IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN sc_ach_amount IS NOT NULL THEN 1 ELSE 0 END +
        CASE WHEN sc_bank_account_type_enum IS NOT NULL THEN 1 ELSE 0 END
       ) < 3
ORDER BY non_null_count;

-- app_pricing_cc: Find rows that are mostly empty
SELECT 
    app_id,
    credit_limit,
    annual_fee,
    purchase_apr,
    cash_advance_apr,
    (CASE WHEN credit_limit IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN annual_fee IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN purchase_apr IS NOT NULL THEN 1 ELSE 0 END +
     CASE WHEN cash_advance_apr IS NOT NULL THEN 1 ELSE 0 END
    ) AS non_null_count
FROM dbo.app_pricing_cc
WHERE (CASE WHEN credit_limit IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN annual_fee IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN purchase_apr IS NOT NULL THEN 1 ELSE 0 END +
       CASE WHEN cash_advance_apr IS NOT NULL THEN 1 ELSE 0 END
      ) < 2;


-- ============================================================================
-- CATEGORY 5: EXPECTED ENUM COVERAGE
-- NULL enums where sibling data suggests they should have values
-- ============================================================================

PRINT '=== CATEGORY 5: EXPECTED ENUM COVERAGE ==='

-- status_enum should always have a value (from Request/@status)
SELECT 
    'NULL status_enum' AS issue,
    COUNT(*) AS count
FROM dbo.app_operational_cc
WHERE status_enum IS NULL;

-- process_enum should always have a value (from Request/@process)
SELECT 
    'NULL process_enum' AS issue,
    COUNT(*) AS count
FROM dbo.app_operational_cc
WHERE process_enum IS NULL;

-- decision_enum in app_base - distribution check
SELECT 
    decision_enum,
    e.enum_label,
    COUNT(*) AS count
FROM dbo.app_base ab
LEFT JOIN dbo.app_enums e ON ab.decision_enum = e.enum_id
GROUP BY decision_enum, e.enum_label
ORDER BY count DESC;

-- app_source_enum in app_base - distribution check
SELECT 
    app_source_enum,
    e.enum_label,
    COUNT(*) AS count
FROM dbo.app_base ab
LEFT JOIN dbo.app_enums e ON ab.app_source_enum = e.enum_id
GROUP BY app_source_enum, e.enum_label
ORDER BY count DESC;

-- contact_type_enum distribution
SELECT 
    contact_type_enum,
    e.enum_label,
    COUNT(*) AS count
FROM dbo.app_contact_base cb
LEFT JOIN dbo.app_enums e ON cb.contact_type_enum = e.enum_id
GROUP BY contact_type_enum, e.enum_label
ORDER BY count DESC;


-- ============================================================================
-- SUMMARY: Data Quality Dashboard
-- ============================================================================

PRINT '=== DATA QUALITY SUMMARY ==='

SELECT 
    'app_base' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN decision_enum IS NULL THEN 1 ELSE 0 END) AS null_decision,
    SUM(CASE WHEN app_source_enum IS NULL THEN 1 ELSE 0 END) AS null_app_source
FROM dbo.app_base

UNION ALL

SELECT 
    'app_operational_cc' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN status_enum IS NULL THEN 1 ELSE 0 END) AS null_status,
    SUM(CASE WHEN process_enum IS NULL THEN 1 ELSE 0 END) AS null_process
FROM dbo.app_operational_cc

UNION ALL

SELECT 
    'app_contact_base' AS table_name,
    COUNT(*) AS total_rows,
    SUM(CASE WHEN contact_type_enum IS NULL THEN 1 ELSE 0 END) AS null_contact_type,
    0 AS placeholder
FROM dbo.app_contact_base;
