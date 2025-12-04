/* --------------------------------------------------------------------------------------------------------------------
-- File: validate_mapping_contract.sql
-- Purpose: Validate that the mapping contract is compatible with the database schema
-------------------------------------------------------------------------------------------------------------------- */

-- Check that all target tables exist
SELECT 'Checking target tables...' AS validation_step;

SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'app_base') THEN 'EXISTS'
        ELSE 'MISSING'
    END AS app_base_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'app_operational_cc') THEN 'EXISTS'
        ELSE 'MISSING'
    END AS app_operational_cc_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'app_pricing_cc') THEN 'EXISTS'
        ELSE 'MISSING'
    END AS app_pricing_cc_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'app_contact_base') THEN 'EXISTS'
        ELSE 'MISSING'
    END AS contact_base_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'app_contact_address') THEN 'EXISTS'
        ELSE 'MISSING'
    END AS contact_address_status,
    CASE 
        WHEN EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'app_contact_employment') THEN 'EXISTS'
        ELSE 'MISSING'
    END AS contact_employment_status;

-- Check that all enum values are present
SELECT 'Checking enum values...' AS validation_step;

SELECT 
    enum_id,
    [type],
    [value],
    CASE 
        WHEN [type] LIKE '%_cc' OR [type] LIKE '%_rl' THEN 'Product Specific'
        WHEN [type] = 'product_line' THEN 'Product Line'
        WHEN [type] = 'contact_type' THEN 'Contact Type'
        WHEN [type] = 'address_type' THEN 'Address Type'
        WHEN [type] = 'employment_type' THEN 'Employment Type'
        WHEN [type] = 'ownership_type' THEN 'Ownership Type'
        WHEN [type] = 'income_type' THEN 'Income Type'
        WHEN [type] = 'other_income_type' THEN 'Other Income Type'
        WHEN [type] LIKE 'collateral%' THEN 'Collateral'
        WHEN [type] LIKE 'warranty%' THEN 'Warranty'
        WHEN [type] LIKE 'policy%' THEN 'Policy'
        ELSE 'Other'
    END AS category
FROM app_enums
WHERE [type] IN (
    'app_source_cc', 'app_type_cc', 'decision_type_cc', 'status_cc', 'process_cc', 
    'priority_cc', 'verification_source_cc', 'decision_model_cc', 'population_assignment_cc',
    'ssn_match_cc', 'fraud_type_cc', 'bank_account_type', 'funding_source_sc',
    'contact_type', 'address_type', 'employment_type', 'ownership_type', 
    'income_type', 'other_income_type', 'product_line'
)
ORDER BY [type], enum_id;

-- Check for missing required enum values
SELECT 'Checking for missing required enum values...' AS validation_step;

WITH required_enums AS (
    -- Status enum values (actual production IDs)
    SELECT 160 AS enum_id, 'status_cc' AS type, 'A' AS value
    UNION SELECT 165, 'status_cc', 'P'
    UNION SELECT 162, 'status_cc', 'C'
    -- App source enum values
    UNION SELECT 1, 'app_source_cc', 'INTERNET'
    UNION SELECT 2, 'app_source_cc', 'MAILED-IN'
    -- Decision enum values
    UNION SELECT 50, 'decision_type_cc', 'APPROVED'
    UNION SELECT 51, 'decision_type_cc', 'DECLINED'
    UNION SELECT 56, 'decision_type_cc', 'NO DECISION'
    -- Product line
    UNION SELECT 600, 'product_line', 'CC'
    -- Contact types
    UNION SELECT 281, 'contact_type', 'PRIMARY'
    UNION SELECT 280, 'contact_type', 'AUTHORIZED USER'
    -- Address types
    UNION SELECT 320, 'address_type', 'CURRENT'
    UNION SELECT 321, 'address_type', 'PREVIOUS'
    -- Employment types
    UNION SELECT 350, 'employment_type', 'CURRENT'
    UNION SELECT 351, 'employment_type', 'PREVIOUS'
    -- Population assignment (with default)
    UNION SELECT 229, 'population_assignment_cc', 'MISSING'
)
SELECT 
    r.enum_id,
    r.type,
    r.value,
    CASE WHEN e.enum_id IS NULL THEN 'MISSING' ELSE 'EXISTS' END AS status
FROM required_enums r
LEFT JOIN app_enums e ON r.enum_id = e.enum_id
WHERE e.enum_id IS NULL;

-- Check table column compatibility
SELECT 'Checking column compatibility...' AS validation_step;

-- Check app_base columns
SELECT 
    'app_base' AS table_name,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'app_base'
AND COLUMN_NAME IN ('app_id', 'app_source_enum', 'decision_enum', 'receive_date', 'product_line_enum')
ORDER BY ORDINAL_POSITION;

-- Check contact_base columns
SELECT 
    'app_contact_base' AS table_name,
    COLUMN_NAME,
    DATA_TYPE,
    IS_NULLABLE,
    COLUMN_DEFAULT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'app_contact_base'
AND COLUMN_NAME IN ('con_id', 'app_id', 'contact_type_enum', 'first_name', 'last_name', 'ssn', 'birth_date')
ORDER BY ORDINAL_POSITION;

-- Check foreign key relationships
SELECT 'Checking foreign key relationships...' AS validation_step;

SELECT 
    fk.name AS foreign_key_name,
    tp.name AS parent_table,
    cp.name AS parent_column,
    tr.name AS referenced_table,
    cr.name AS referenced_column
FROM sys.foreign_keys fk
INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
INNER JOIN sys.columns cp ON fkc.parent_column_id = cp.column_id AND fkc.parent_object_id = cp.object_id
INNER JOIN sys.columns cr ON fkc.referenced_column_id = cr.column_id AND fkc.referenced_object_id = cr.object_id
WHERE tp.name IN ('app_base', 'app_operational_cc', 'app_pricing_cc', 'app_contact_base', 'app_contact_address', 'app_contact_employment')
ORDER BY tp.name, fk.name;