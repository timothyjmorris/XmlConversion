"""Check database schema and E2E data for potentially missing mappings."""
import sys
sys.path.insert(0, 'c:\\Users\\tmorris\\Repos_local\\XmlConversion')

from xml_extractor.config.config_manager import get_config_manager
import pyodbc

config = get_config_manager()
connection_string = config.get_database_connection_string()
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

print("\n" + "="*80)
print("CHECKING POTENTIALLY MISSING MAPPINGS")
print("="*80)

# Get designated E2E test app_id
test_app_id = 325725
print(f"\nE2E test app_id: {test_app_id}")

# 1. dealer_proceeds_amount
print("\n1. dealer_proceeds_amount (app_funding_contract_rl):")
cursor.execute(f"""
    SELECT dealer_proceeds_amount 
    FROM [migration].[app_funding_contract_rl]
    WHERE app_id = {test_app_id}
""")
row = cursor.fetchone()
print(f"   Value: {row[0] if row else 'NO ROW FOUND'}")

# 2. motor_ucc_vin_confirmed_enum
print("\n2. motor_ucc_vin_confirmed_enum (app_funding_checklist_rl):")
cursor.execute(f"""
    SELECT motor_ucc_vin_confirmed_enum 
    FROM [migration].[app_funding_checklist_rl]
    WHERE app_id = {test_app_id}
""")
row = cursor.fetchone()
print(f"   Value: {row[0] if row else 'NO ROW FOUND'}")

# 3. assess_florida_doc_fee_flag
print("\n3. assess_florida_doc_fee_flag (app_transactional_rl):")
cursor.execute(f"""
    SELECT assess_florida_doc_fee_flag 
    FROM [migration].[app_transactional_rl]
    WHERE app_id = {test_app_id}
""")
row = cursor.fetchone()
print(f"   Value: {row[0] if row else 'NO ROW FOUND'}")

# 4. assess_tennessee_doc_fee_flag
print("\n4. assess_tennessee_doc_fee_flag (app_transactional_rl):")
cursor.execute(f"""
    SELECT assess_tennessee_doc_fee_flag 
    FROM [migration].[app_transactional_rl]
    WHERE app_id = {test_app_id}
""")
row = cursor.fetchone()
print(f"   Value: {row[0] if row else 'NO ROW FOUND'}")

# 5. other_monthly_income and other_income_source_detail
print("\n5. other_monthly_income (app_contact_employment):")
cursor.execute(f"""
    SELECT e.other_monthly_income
    FROM [migration].[app_contact_employment] e
    INNER JOIN [migration].[app_contact_base] c ON e.con_id = c.con_id
    WHERE c.app_id = {test_app_id}
""")
rows = cursor.fetchall()
if rows:
    for i, row in enumerate(rows, 1):
        print(f"   Record {i}: other_monthly_income={row[0]}")
else:
    print("   NO ROWS FOUND")

# Check if other_income_source_detail column exists
cursor.execute("""
    SELECT COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='migration' 
    AND TABLE_NAME='app_contact_employment' 
    AND COLUMN_NAME LIKE '%other%'
""")
other_cols = cursor.fetchall()
print(f"   Columns with 'other' in name: {[c[0] for c in other_cols]}")

print("\n" + "="*80)
print("SCHEMA CHECK COMPLETE")
print("="*80)

conn.close()
