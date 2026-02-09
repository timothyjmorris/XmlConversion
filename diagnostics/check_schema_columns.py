"""Check schema for ip_address and wholesale_value columns."""
import sys
sys.path.insert(0, 'c:\\Users\\tmorris\\Repos_local\\XmlConversion')

from xml_extractor.config.config_manager import get_config_manager
import pyodbc

# Get database connection string from config manager
config = get_config_manager()
connection_string = config.get_database_connection_string()
conn = pyodbc.connect(connection_string)
cursor = conn.cursor()

# Check app_base columns
print("\n=== app_base columns ===")
cursor.execute("""
    SELECT COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='migration' AND TABLE_NAME='app_base' 
    ORDER BY ORDINAL_POSITION
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

# Check for ip_address specifically
cursor.execute("""
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='migration' AND TABLE_NAME='app_base' 
    AND COLUMN_NAME='ip_address'
""")
ip_exists = cursor.fetchone()[0]
print(f"\nip_address column exists: {ip_exists > 0}")

# Check app_collateral_rl columns
print("\n=== app_collateral_rl columns ===")
cursor.execute("""
    SELECT COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='migration' AND TABLE_NAME='app_collateral_rl' 
    ORDER BY ORDINAL_POSITION
""")
for row in cursor.fetchall():
    print(f"  {row[0]}")

# Check for wholesale_value specifically
cursor.execute("""
    SELECT COUNT(*) 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='migration' AND TABLE_NAME='app_collateral_rl' 
    AND COLUMN_NAME='wholesale_value'
""")
wholesale_exists = cursor.fetchone()[0]
print(f"\nwholesale_value column exists: {wholesale_exists > 0}")

conn.close()
