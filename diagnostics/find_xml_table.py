"""Find the app_xml table structure"""
from xml_extractor.config.config_manager import get_config_manager
import pyodbc

config = get_config_manager()
db_config = config.database_config

conn_str = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={db_config.server};'
    f'DATABASE={db_config.database};'
    f'Trusted_Connection=yes;'
    f'TrustServerCertificate=yes;'
    f'Encrypt=no'
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

cursor.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME LIKE '%xml%' OR TABLE_NAME LIKE '%app_xml%'
""")
print("Tables with 'xml' in name:")
for row in cursor.fetchall():
    print(f"  {row[0]}.{row[1]}.{row[2]}")
