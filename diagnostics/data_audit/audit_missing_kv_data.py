import pyodbc
import argparse
from lxml import etree

def build_connection_string(server, database):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=AuditMissingKV;"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

def audit_app(conn, app_id, schema):
    cursor = conn.cursor()
    
    # 1. Get XML
    cursor.execute(f"SELECT app_XML FROM [{schema}].[app_xml_staging_rl] WHERE app_id = ?", app_id)
    row = cursor.fetchone()
    if not row:
        print(f"[FAIL] App {app_id}: No XML found")
        return

    xml_str = row[0]
    try:
        root = etree.fromstring(xml_str.encode('utf-8'))
    except Exception as e:
        print(f"[FAIL] App {app_id}: XML Parse Error - {e}")
        return

    # 2. Extract Values
    decision_nodes = root.xpath("//IL_app_decision_info")
    if not decision_nodes:
        print(f"[INFO] App {app_id}: No IL_app_decision_info node")
        return

    node = decision_nodes[0]
    v4p = node.get("experian_vantage4_score")
    v4s = node.get("experian_vantage4_score2")
    
    print(f"--- App {app_id} ---")
    print(f"  XML Source: V4P='{v4p}', V4S='{v4s}'")
    
    # 3. Check DB Tables
    # Check Scores
    cursor.execute(f"SELECT score_identifier, score FROM [{schema}].[scores] WHERE app_id = ?", app_id)
    scores = cursor.fetchall()
    print(f"  DB Scores Table: {[list(s) for s in scores]}")
    
    # Check History Lookup
    # Note: Column name is likely 'value' based on data_mapper
    try:
        cursor.execute(f"SELECT name, value FROM [{schema}].[app_historical_lookup] WHERE app_id = ?", app_id)
        history = cursor.fetchall()
        print(f"  DB History Lookup: {[list(h) for h in history]}")
    except Exception as e:
        print(f"  DB History Lookup Error: {e}")

    # Verdict
    missing = []
    if v4p and v4p != '0': # Assuming 0 might be skipped or handled differently? Contract says int.
        # Check if V4P exists in scores
        found = any(s[0] == 'V4P' for s in scores)
        if not found: missing.append('V4P')
        
    if v4s and v4s != '0':
        found = any(s[0] == 'V4S' for s in scores)
        if not found: missing.append('V4S')

    if missing:
        print(f"  [FAIL] Missing Scores in DB: {missing}")
    else:
        print(f"  [PASS] All expected scores found (or source was empty)")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="dbo")
    args = parser.parse_args()
    
    conn = pyodbc.connect(build_connection_string(args.server, args.database))
    
    apps = [173413, 325169, 326111]
    
    print(f"Auditing Apps: {apps}")
    for app_id in apps:
        audit_app(conn, app_id, args.schema)

if __name__ == "__main__":
    main()
