import pyodbc
import argparse
from lxml import etree

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--app-id", required=True, type=int)
    args = parser.parse_args()
    
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={args.server};DATABASE={args.database};Trusted_Connection=yes;TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Get XML
    cursor.execute(f"SELECT app_XML FROM [dbo].[app_xml_staging_rl] WHERE app_id = ?", args.app_id)
    row = cursor.fetchone()
    if not row:
        print(f"App {args.app_id} not found in app_xml_staging_rl")
        return
        
    xml_str = row[0]
    root = etree.fromstring(xml_str.encode('utf-8'))
    
    print(f"--- XML Analysis for App {args.app_id} ---")
    
    # 1. Scan for coll1_ attributes in XML
    prefixes = ['coll1_', 'coll2_', 'coll3_', 'coll4_']
    expected_count = 0
    
    for prefix in prefixes:
        print(f"Scanning for {prefix}...")
        found_prefix = False
        for element in root.iter():
            for attr, val in element.items():
                if attr.startswith(prefix):
                    print(f"  {attr} = '{val}'")
                    if val and val.strip() not in ['', '0', 'None']:
                        found_prefix = True
        
        if found_prefix:
            print(f"  -> Expects row for {prefix}")
            expected_count += 1
        else:
            print(f"  -> No significant data for {prefix}")
            
    print(f"\nTotal Expected Rows: {expected_count}")
    
    # 2. Check DB
    print("\n--- DB Analysis ---")
    cursor.execute(f"SELECT * FROM [dbo].[app_collateral_rl] WHERE app_id = ?", args.app_id)
    rows = cursor.fetchall()
    print(f"Rows in app_collateral_rl: {len(rows)}")
    for r in rows:
        print(f"  {r}")

if __name__ == "__main__":
    main()
