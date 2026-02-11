import pyodbc
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--app-id", required=True, type=int)
    args = parser.parse_args()
    
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={args.server};DATABASE={args.database};Trusted_Connection=yes;TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print(f"--- History for App {args.app_id} ---")
    cursor.execute("SELECT * FROM [dbo].[processing_log] WHERE app_id = ? ORDER BY processed_at DESC", args.app_id)
    cols = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    
    for r in rows:
        print(dict(zip(cols, r)))

if __name__ == "__main__":
    main()
