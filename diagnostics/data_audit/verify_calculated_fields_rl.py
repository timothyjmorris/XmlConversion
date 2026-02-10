import pyodbc
import json
import argparse
import logging
from lxml import etree
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_connection_string(server, database):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=CalcFieldVerifyRL;"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

def parse_date(date_str):
    if not date_str: return None
    try:
        # Handle formats with T separator
        if 'T' in date_str:
            return datetime.fromisoformat(date_str)
        
        # Handle standard date only
        if len(date_str) == 10:
            return datetime.strptime(date_str, "%Y-%m-%d")
            
        # Handle milliseconds (e.g., 2021-3-30 13:37:37.566)
        if '.' in date_str:
            # Handle variable millisecond precision by truncation or flexible parsing
            # Simple approach: split on dot
            main_part, ms_part = date_str.split('.')
            dt = datetime.strptime(main_part, "%Y-%m-%d %H:%M:%S")
            # Re-add microseconds if needed, but for > 2020 comparison, date part is usually enough
            return dt
            
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def calculate_cb_score_factor_type_pr(xml_root, decline_code_1, index=1):
    """
    Re-implementation of the CASE logic for cb_score_factor_type_pr_1 in RL.
    Mapping expression:
    CASE WHEN Vantage4P_decline_code1 IS NOT EMPTY 
         AND IL_application.app_entry_date > '2020-01-01' THEN 'V4' 
         WHEN score_factor_code_pr_1 IS NOT EMPTY THEN score_factor_code_pr_1 
    END
    """
    if not decline_code_1:
         # If the code (mapped from Vantage4P_decline_code1) is missing, 
         # likely the type is also missing, BUT... 
         # the logic expression depends on attributes.
         # Wait, target_column 'cb_score_factor_code_pr_1' maps directly from 'Vantage4P_decline_code1'.
         # So 'decline_code_1' PASSED IN is essentially 'Vantage4P_decline_code1'.
         # If it's valid, then "Vantage4P_decline_code1 IS NOT EMPTY" is true.
         pass

    # Trust the DB value for the input variable to the calculation
    # (Since we are verifying the CASE logic, not the extraction of the input itself)
    v4_decline_code = decline_code_1
    
    # Extract source attributes for date comparison
    app_nodes = xml_root.xpath("//IL_application")
    if not app_nodes: return None
    app_node = app_nodes[0]
    
    app_entry_date_str = app_node.get("app_entry_date")
    app_entry_date = parse_date(app_entry_date_str)
    
    decision_nodes = xml_root.xpath("//IL_app_decision_info")
    decision_node = decision_nodes[0] if decision_nodes else None
    
    # Check for the fallback field
    score_factor_code_pr_1 = None
    if decision_node is not None:
         score_factor_code_pr_1 = decision_node.get(f"score_factor_code_pr_{index}")

    # Logic Re-implementation
    cutoff = datetime(2020, 1, 1)
    
    # 1. First condition
    if v4_decline_code and app_entry_date and app_entry_date > cutoff:
        return 'V4'
        
    # 2. Second condition
    # The mapping implies "score_factor_code_pr_1" in expression is essentially "when fallback available"
    # But in the DB, cb_score_factor_code_pr_1 IS the value we started with.
    # If condition 1 is met, we return 'V4'.
    # If condition 1 is NOT met, and code is present, we return the code itself?
    # Mapping: "WHEN score_factor_code_pr_1 IS NOT EMPTY THEN score_factor_code_pr_1"
    
    # Wait, inspect the mapping logic again:
    # "CASE WHEN Vantage4P_decline_code1 IS NOT EMPTY AND IL_application.app_entry_date > '2020-01-01' THEN 'V4' 
    #       WHEN score_factor_code_pr_1 IS NOT EMPTY THEN score_factor_code_pr_1 END"
    
    # Are `Vantage4P_decline_code1` and `score_factor_code_pr_1` the SAME attribute in XML?
    # Or different?
    # Let's check if the XML has `score_factor_code_pr_1`.
    
    if score_factor_code_pr_1:
         return score_factor_code_pr_1
         
    return None

def verify_calculations(conn, schema, sample_size=50):
    print(f"--- Verifying RL Calculated Fields (Sample N={sample_size}) ---")
    cursor = conn.cursor()
    
    # Select apps that have a factor code (so we have something to calc)
    query = f"""
    SELECT TOP {sample_size} 
        b.app_id, 
        x.app_XML, 
        o.cb_score_factor_code_pr_1, 
        o.cb_score_factor_type_pr_1
    FROM [{schema}].[app_base] b
    JOIN [{schema}].[app_xml_staging_rl] x ON b.app_id = x.app_id
    JOIN [{schema}].[app_operational_rl] o ON b.app_id = o.app_id
    WHERE o.cb_score_factor_code_pr_1 IS NOT NULL
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Error fetching rows: {e}")
        return
    
    if not rows:
        print("No rows found with cb_score_factor_code_pr_1 populated.")
        return

    passed = 0
    failed = 0
    
    print(f"Verifying {len(rows)} records for cb_score_factor_type_pr_1 logic...")
    
    for row in rows:
        app_id, xml_str, db_code, db_type = row
        
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
            calc_type = calculate_cb_score_factor_type_pr(root, db_code, index=1)
            
            # Normalize for comparison
            expected = calc_type if calc_type else ''
            actual = db_type if db_type else ''
            
            # DB might return None as None
            if actual is None: actual = ''
            if expected is None: expected = ''
            
            if expected == actual:
                passed += 1
            else:
                failed += 1
                # Debug info
                app_nodes = root.xpath("//IL_application")
                entry_date = "N/A"
                if app_nodes:
                    entry_date = app_nodes[0].get("app_entry_date")
                
                print(f"  [FAIL] App {app_id}: Expected '{expected}', Got '{actual}'")
                print(f"         Inputs: Code='{db_code}', Date='{entry_date}'")
                
        except Exception as e:
            print(f"  [ERROR] App {app_id}: {e}")
            failed += 1

    print(f"\nResult: {passed} Passed, {failed} Failed")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="dbo")
    args = parser.parse_args()
    
    conn_str = build_connection_string(args.server, args.database)
    try:
        conn = pyodbc.connect(conn_str)
        verify_calculations(conn, args.schema)
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    main()
