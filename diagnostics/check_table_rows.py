"""Check if rows exist in target tables for E2E test."""
import sys
sys.path.insert(0, 'c:\\Users\\tmorris\\Repos_local\\XmlConversion')

from xml_extractor.config.config_manager import get_config_manager
import pyodbc

conn = pyodbc.connect(get_config_manager().get_database_connection_string())
cursor = conn.cursor()

test_app_id = 325725  # Designated E2E test ID

print(f"\nChecking row existence for app_id={test_app_id}:")
tables = [
    'app_base',
    'app_funding_contract_rl', 
    'app_funding_checklist_rl', 
    'app_transactional_rl',
    'app_contact_employment'
]

for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM [migration].[{table}] WHERE app_id = {test_app_id}")
        count = cursor.fetchone()[0]
        print(f"  {table}: {count} rows")
    except Exception as e:
        # Try with con_id for contact tables
        try:
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM [migration].[{table}] e
                INNER JOIN [migration].[app_contact_base] c ON e.con_id = c.con_id
                WHERE c.app_id = {test_app_id}
            """)
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows (via con_id)")
        except:
            print(f"  {table}: ERROR - {str(e)[:50]}")

conn.close()
