"""Check database values for ip_address and wholesale_value from last E2E run."""
import sys
sys.path.insert(0, 'c:\\Users\\tmorris\\Repos_local\\XmlConversion')

from xml_extractor.config.config_manager import get_config_manager
import pyodbc

# Get database connection
config = get_config_manager()
connection_string = config.get_database_connection_string()
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

# Find most recent test app_id (format is MMDDhhmmss)
print("\n=== Finding most recent E2E test run ===")
cursor.execute("""
    SELECT TOP 5 app_id, receive_date, ip_address 
    FROM [migration].[app_base]
    WHERE app_id >= 200000000  -- E2E test IDs start with date format
    ORDER BY app_id DESC
""")
print("\nRecent E2E test apps:")
for row in cursor.fetchall():
    print(f"  app_id={row[0]}, receive_date={row[1]}, ip_address={row[2]}")

# Check the most recent one
cursor.execute("""
    SELECT TOP 1 app_id 
    FROM [migration].[app_base]
    WHERE app_id >= 200000000 
    ORDER BY app_id DESC
""")
latest_app_id = cursor.fetchone()[0]

print(f"\n=== Checking latest E2E test: app_id={latest_app_id} ===")

# Check ip_address in app_base
cursor.execute(f"""
    SELECT ip_address 
    FROM [migration].[app_base]
    WHERE app_id = {latest_app_id}
""")
ip_result = cursor.fetchone()
print(f"app_base.ip_address: {ip_result[0] if ip_result else 'NOT FOUND'}")

# Check wholesale_value in app_collateral_rl
cursor.execute(f"""
    SELECT sort_order, wholesale_value 
    FROM [migration].[app_collateral_rl]
    WHERE app_id = {latest_app_id}
    ORDER BY sort_order
""")
collateral_results = cursor.fetchall()
if collateral_results:
    print(f"\napp_collateral_rl wholesale_value:")
    for row in collateral_results:
        print(f"  sort_order={row[0]}, wholesale_value={row[1]}")
else:
    print(f"\napp_collateral_rl: NO ROWS FOUND")

conn.close()
