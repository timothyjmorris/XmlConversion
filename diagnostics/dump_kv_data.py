import pyodbc
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="migration")
    parser.add_argument("--app-id", type=int, required=True)
    args = parser.parse_args()
    
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={args.server};DATABASE={args.database};Trusted_Connection=yes;TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    tables = ['scores', 'app_collateral_rl', 'app_warranties_rl', 'app_policy_exceptions_rl', 'identifiers', 'app_historical_lookup']
    
    print(f"--- Data Dump for App {args.app_id} in Schema '{args.schema}' ---")
    
    for table in tables:
        try:
            print(f"\n[Table: {table}]")
            cursor.execute(f"SELECT * FROM [{args.schema}].[{table}] WHERE app_id = ?", args.app_id)
            rows = cursor.fetchall()
            if rows:
                cols = [c[0] for c in cursor.description]
                for r in rows:
                    print(dict(zip(cols, r)))
            else:
                print("  (No rows)")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    main()
