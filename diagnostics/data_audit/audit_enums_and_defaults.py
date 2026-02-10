import pyodbc
import json
import argparse
import os

def build_connection_string(server, database):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=AuditEnums;"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

def audit_defaults_and_nulls(conn, schema):
    print("--- Auditing Defaults and Nulls ---")
    cursor = conn.cursor()
    
    # 1. Check for specific defaults mentioned by user
    print("\n1. Checking Known Defaults:")
    defaults_to_check = [
        ("app_collateral_rl", "collateral_type_enum", 423, "Default Collateral Type"),
        ("app_pricing_cc", "population_assignment_enum", 229, "Default Population Assignment"),
        ("app_pricing_cc", "marketing_segment", "UNKNOWN", "Default Marketing Segment")
    ]
    
    for table, col, val, desc in defaults_to_check:
        try:
            val_repr = f"'{val}'" if isinstance(val, str) else val
            query = f"SELECT count(*) FROM [{schema}].[{table}] WHERE {col} = {val_repr}"
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"  - {desc} ({table}.{col} = {val_repr}): Found {count} rows")
            
            if count > 0:
                # Log a few examples
                query_ids = f"SELECT TOP 5 app_id FROM [{schema}].[{table}] WHERE {col} = {val_repr}"
                cursor.execute(query_ids)
                ids = [str(r[0]) for r in cursor.fetchall()]
                print(f"    Sample IDs: {', '.join(ids)}")
                
        except Exception as e:
            print(f"    Error checking {table}.{col}: {e}")

    # 2. Check for 100% NULL enum columns
    print("\n2. Checking for 100% NULL Enum Columns:")
    # We'll look at columns ending in '_enum' in specific tables
    tables = ['app_base', 'app_operational_cc', 'app_pricing_cc', 'app_collateral_rl', 'app_operational_rl']
    
    for table in tables:
        try:
            # Get columns
            cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table}' AND TABLE_SCHEMA = '{schema}'")
            columns = [row[0] for row in cursor.fetchall()]
            enum_cols = [c for c in columns if c.endswith('_enum')]
            
            for col in enum_cols:
                query = f"SELECT COUNT(*) FROM [{schema}].[{table}] WHERE {col} IS NOT NULL"
                cursor.execute(query)
                count = cursor.fetchone()[0]
                if count == 0:
                    print(f"  [SMELL] {table}.{col} is 100% NULL (0 populated rows)")
                else:
                    # Optional: Print populated count if low?
                    pass
                    # print(f"  {table}.{col}: {count} populated")
                    
        except Exception as e:
            print(f"  Error checking table {table}: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="dbo")
    args = parser.parse_args()
    
    conn_str = build_connection_string(args.server, args.database)
    try:
        conn = pyodbc.connect(conn_str)
        audit_defaults_and_nulls(conn, args.schema)
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    main()
