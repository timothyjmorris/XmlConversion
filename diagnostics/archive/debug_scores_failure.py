import pyodbc
import argparse
from lxml import etree
import json

def load_contract(path):
    with open(path, 'r') as f:
        return json.load(f)

def get_kv_mappings(contract):
    mappings = { 'scores': [] }
    for m in contract.get('mappings', []):
        m_types = m.get('mapping_type', [])
        str_types = [str(t) for t in m_types]
        add_score = next((t for t in str_types if 'add_score' in t), None)
        if add_score:
            identifier = add_score.split('(')[1].strip(')') if '(' in add_score else None
            mappings['scores'].append({
                'xml_path': m.get('xml_path'),
                'xml_attribute': m.get('xml_attribute'),
                'identifier': identifier
            })
    return mappings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--app-id", required=True, type=int)
    parser.add_argument("--contract", default="config/mapping_contract_rl.json")
    args = parser.parse_args()
    
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={args.server};DATABASE={args.database};Trusted_Connection=yes;TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    contract = load_contract(args.contract)
    score_mappings = get_kv_mappings(contract)['scores']
    
    # Get XML
    cursor.execute(f"SELECT app_XML FROM [dbo].[app_xml_staging_rl] WHERE app_id = ?", args.app_id)
    row = cursor.fetchone()
    if not row:
        print(f"App {args.app_id} not found in app_xml_staging_rl")
        return
        
    xml_str = row[0]
    root = etree.fromstring(xml_str.encode('utf-8'))
    
    print(f"--- XML Analysis for App {args.app_id} ---")
    
    expected_scores = set()
    for sm in score_mappings:
        node_name = sm['xml_path'].split('/')[-1]
        attr = sm['xml_attribute']
        if not attr: continue 
        
        nodes = root.xpath(f"//{node_name}")
        for node in nodes:
            val = node.get(attr)
            print(f"Scanning {sm['identifier']} -> {node_name}@{attr}: Value='{val}'")
            if val is not None and val.strip() not in ['']:
                print("  -> EXPECTED")
                expected_scores.add(sm['identifier'])
            else:
                print("  -> Ignored (empty)")

    print(f"\nExpected Scores: {expected_scores}")
    
    # 2. Check DB
    print("\n--- DB Analysis ---")
    try:
        cursor.execute(f"SELECT score_identifier, score FROM [dbo].[scores] WHERE app_id = ?", args.app_id)
        rows = cursor.fetchall()
        print(f"Rows in scores table: {len(rows)}")
        db_scores = set()
        for r in rows:
            print(f"  {r.score_identifier}: {r.score}")
            db_scores.add(r.score_identifier)
            
        missing = expected_scores - db_scores
        print(f"\nMissing: {missing}")
    except Exception as e:
        print(f"Error querying DB: {e}")

if __name__ == "__main__":
    main()
