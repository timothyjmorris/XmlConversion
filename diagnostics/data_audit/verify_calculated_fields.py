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
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=CalcFieldVerify;"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

def parse_date(date_str):
    if not date_str: return None
    try:
        # XML dates often come as YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
        if 'T' in date_str:
            return datetime.fromisoformat(date_str)
        if len(date_str) == 10:
            return datetime.strptime(date_str, "%Y-%m-%d")
        # Handle simple date-time or date-time with milliseconds
        if '.' in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except:
        return None

def calculate_cb_score_factor_type(xml_root, factor_code, index=1):
    """
    Re-implementation of the CASE logic for cb_score_factor_type_X.
    Matches logic in mapping_contract.json for app_operational_cc.cb_score_factor_type_1
    """
    if not factor_code:
        return None
        
    # Extract inputs
    ns = {'ns': 'http://www.provenir.com/Request'} # Adjust based on actual XML, usually we ignore NS in simple XPath
    
    # Helper to clean text
    def get_text(xpath):
        els = xml_root.xpath(xpath)
        if els:
            return str(els[0]).strip()
        return None

    # Inputs
    # Note: Using simple path string matching as per our DataMapper behavior which often ignores NS or handles it loosely
    # But here we use lxml XPath. We'll use local-name() or just assume structure.
    
    # /Provenir/Request/CustData/application/attributes/population_assignment_code
    # Wait, mapping says: application.population_assignment
    # It likely comes from attributes dictionary in DataMapper.
    # We need to find the attribute on the application node.
    
    app_nodes = xml_root.xpath("//application")
    if not app_nodes: return None
    app_node = app_nodes[0]
    
    pop_assign = app_node.get("population_assignment_code") # Check exact attribute name
    if not pop_assign: pop_assign = app_node.get("population_assignment")
    
    receive_date_str = app_node.get("app_receive_date")
    receive_date = parse_date(receive_date_str)
    
    app_type = app_node.get("app_type_code")
    
    # Decision model from app_product
    prod_nodes = xml_root.xpath("//app_product")
    decision_model = prod_nodes[0].get("decision_model") if prod_nodes else None
    
    # Logic Re-implementation
    # CASE WHEN ...
    
    # 2023-10-11 Cutoff
    cutoff = datetime(2023, 10, 11)
    is_after_cutoff = receive_date and receive_date > cutoff
    
    if factor_code: # IS NOT EMPTY
        if pop_assign == 'BL': return '00Q88'
        if pop_assign == 'CV': return 'AJ'
        if pop_assign == 'EV': return 'EV'
        if pop_assign == 'JB': return '00227'
        if pop_assign == 'L2': return '00337'
        if pop_assign == 'SO': return '00A9Q'
        
        if is_after_cutoff:
            if pop_assign == 'CM': return 'AJ'
            if pop_assign == 'DN': return '00W83'
            if pop_assign == 'HD': return '00W83'
            if pop_assign == 'HE': return 'AJ'
            if pop_assign == 'HU': return 'FT'
            if pop_assign == 'HV': return '00V60'
            if pop_assign == 'HW': return 'V4'
            if pop_assign == 'LB': return '00V60'
            if pop_assign == 'SB': return 'FT'
            
            if decision_model and decision_model.startswith('TU'): return '00227'
            
            # LIKE 'V4_%' check for factor code itself? "app_product.adverse_actn1_type_cd LIKE 'V4_%'"
            # Wait, the mapping logic says: 
            # WHEN app_product.adverse_actn1_type_cd LIKE 'V4_%' AND ... AND app_type_code = 'SECURE' THEN 'V4'
            if factor_code.startswith('V4_') and app_type == 'SECURE': return 'V4'
            
            if app_type == 'SECURE': return '00W83'
            
    return '' # ELSE ''

def verify_calculations(conn, schema, sample_size=50):
    print(f"--- Verifying Calculated Fields (Sample N={sample_size}) ---")
    cursor = conn.cursor()
    
    # Select apps that have a factor code (so we have something to calc)
    query = f"""
    SELECT TOP {sample_size} 
        b.app_id, 
        x.app_xml, 
        o.cb_score_factor_code_1, 
        o.cb_score_factor_type_1
    FROM [{schema}].[app_base] b
    JOIN [{schema}].[app_xml] x ON b.app_id = x.app_id
    JOIN [{schema}].[app_operational_cc] o ON b.app_id = o.app_id
    WHERE o.cb_score_factor_code_1 IS NOT NULL
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    passed = 0
    failed = 0
    
    print(f"Verifying {len(rows)} records for cb_score_factor_type_1 logic...")
    
    for row in rows:
        app_id, xml_str, db_code, db_type = row
        
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
            calc_type = calculate_cb_score_factor_type(root, db_code)
            
            # Normalize for comparison
            expected = calc_type if calc_type else ''
            actual = db_type if db_type else ''
            
            # DB might return None as None, our function returns '' or None.
            if actual is None: actual = ''
            if expected is None: expected = ''
            
            if expected == actual:
                passed += 1
            else:
                failed += 1
                # Debug info
                app_nodes = root.xpath("//application")
                if app_nodes:
                    app_node = app_nodes[0]
                    pop = app_node.get("population_assignment_code") or app_node.get("population_assignment")
                    rec_date = app_node.get("app_receive_date")
                print(f"  [FAIL] App {app_id}: Expected '{expected}', Got '{actual}' (Input Code: {db_code})")
                print(f"         Inputs: Pop='{pop}', Date='{rec_date}'")
                
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
