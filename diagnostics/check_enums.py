"""
Check all enum columns in CC tables to verify they're being populated correctly.
"""
import pyodbc
from xml_extractor.config.config_manager import get_config_manager

def main():
    config = get_config_manager()
    db_config = config.database_config
    
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={db_config.server};"
        f"DATABASE={db_config.database};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
        f"Encrypt=no"
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("=== ACH / Banking Field Relationship Check (dbo schema) ===")
    queries = [
        ('sc_ach_amount > 0 AND sc_bank_aba IS NULL', 
         'SELECT COUNT(*) FROM dbo.app_operational_cc WHERE sc_ach_amount > 0 AND sc_bank_aba IS NULL'),
        ('sc_ach_amount > 0 AND sc_bank_account_num IS NULL', 
         'SELECT COUNT(*) FROM dbo.app_operational_cc WHERE sc_ach_amount > 0 AND sc_bank_account_num IS NULL'),
        ('sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL', 
         'SELECT COUNT(*) FROM dbo.app_operational_cc WHERE sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL'),
        ('TOTAL rows with sc_ach_amount > 0', 
         'SELECT COUNT(*) FROM dbo.app_operational_cc WHERE sc_ach_amount > 0'),
    ]
    for name, query in queries:
        cursor.execute(query)
        print(f"  {name}: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT DISTINCT sc_bank_account_type_enum FROM dbo.app_operational_cc')
    print(f"\n  DISTINCT sc_bank_account_type_enum: {[r[0] for r in cursor.fetchall()]}")
    
    print("\n=== ALL ENUM COLUMNS POPULATION CHECK (dbo schema) ===")
    # Find all enum columns in dbo schema tables
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'dbo'
          AND COLUMN_NAME LIKE '%_enum'
          AND TABLE_NAME LIKE 'app_%'
        ORDER BY TABLE_NAME, COLUMN_NAME
    """)
    enum_columns = cursor.fetchall()
    
    print(f"Found {len(enum_columns)} enum columns to check\n")
    
    for table, col in enum_columns:
        # Get distinct values and counts
        cursor.execute(f"""
            SELECT {col}, COUNT(*) as cnt 
            FROM dbo.{table} 
            GROUP BY {col}
            ORDER BY cnt DESC
        """)
        results = cursor.fetchall()
        
        total = sum(r[1] for r in results)
        null_count = sum(r[1] for r in results if r[0] is None)
        non_null_count = total - null_count
        distinct_values = [r[0] for r in results if r[0] is not None]
        
        # Flag potential issues
        status = "OK" if non_null_count > 0 else "⚠️ NEVER POPULATED"
        if total > 0 and null_count / total > 0.95 and non_null_count == 0:
            status = "⚠️ NEVER POPULATED"
        elif total > 0 and non_null_count > 0:
            status = f"OK ({len(distinct_values)} distinct values)"
        
        print(f"{table}.{col}")
        print(f"  Total: {total}, Non-NULL: {non_null_count}, NULL: {null_count}")
        print(f"  Values: {distinct_values[:10]}{'...' if len(distinct_values) > 10 else ''}")
        print(f"  Status: {status}")
        print()

if __name__ == "__main__":
    main()
