import pyodbc
import argparse
import json
import logging
import random
from lxml import etree
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_connection_string(server, database):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=AuditKV_RL;"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

def load_contract(path):
    with open(path, 'r') as f:
        return json.load(f)

def get_kv_mappings(contract):
    """
    Explore contract to find mappings for:
    - scores (add_score)
    - app_historical_lookup (add_history or direct)
    - indicators (add_indicator)
    """
    mappings = {
        'scores': [],
        'history': [],
        'indicators': []
    }
    
    for m in contract.get('mappings', []):
        m_types = m.get('mapping_type', [])
        str_types = [str(t) for t in m_types]
        
        # Scores
        add_score = next((t for t in str_types if 'add_score' in t), None)
        if add_score:
            # Parse identifier from add_score(ID)
            identifier = add_score.split('(')[1].strip(')') if '(' in add_score else None
            mappings['scores'].append({
                'xml_path': m.get('xml_path'),
                'xml_attribute': m.get('xml_attribute'),
                'identifier': identifier
            })
            
        # Indicators
        add_ind = next((t for t in str_types if 'add_indicator' in t), None)
        if add_ind:
            identifier = add_ind.split('(')[1].strip(')') if '(' in add_ind else None
            mappings['indicators'].append({
                'xml_path': m.get('xml_path'),
                'xml_attribute': m.get('xml_attribute'),
                'identifier': identifier
            })

    return mappings

def audit_scores(conn, schema, rows, score_mappings):
    logger.info(f"Auditing SCORES table (N={len(rows)})...")
    cursor = conn.cursor()
    
    passed = 0
    failed = 0
    failed_apps = []
    
    for row in rows:
        app_id, xml_str = row
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
        except:
            logger.error(f"Failed to parse XML for App {app_id}")
            continue
            
        # 1. Determine expected scores from XML
        expected_scores = set()
        for sm in score_mappings:
            node_name = sm['xml_path'].split('/')[-1]
            attr = sm['xml_attribute']
            if not attr: continue 
            
            # Find nodes
            nodes = root.xpath(f"//{node_name}")
            for node in nodes:
                val = node.get(attr)
                # DataMapper logic: if val exists and is meaningful.
                if val is not None and val.strip() not in ['']:
                    expected_scores.add(sm['identifier'])
        
        # 2. Get Actual DB Scores
        cursor.execute(f"SELECT score_identifier FROM [{schema}].[scores] WHERE app_id = ?", app_id)
        db_scores = {r[0] for r in cursor.fetchall()}
        
        # 3. Compare
        missing = expected_scores - db_scores
        
        if missing:
            failed += 1
            # logger.warning(f"App {app_id} Missing Scores: {missing}")
            failed_apps.append(app_id)
        else:
            passed += 1
            
    logger.info(f"SCORES Result: {passed} Passed, {failed} Failed")
    if failed_apps:
        logger.warning(f"  First 5 Failed Apps: {failed_apps[:5]}")
    return failed_apps

def audit_generic_kv(conn, schema, rows, table_name, xml_prefix_list, ignore_suffixes=None):
    """
    Generic audit for multi-row tables based on XML prefix existence.
    e.g. Collateral: coll1_, coll2_, coll3_, coll4_
    ignore_suffixes: list of suffixes that should not trigger a row creation (e.g. new_used_demo)
    """
    logger.info(f"Auditing {table_name} (N={len(rows)})...")
    cursor = conn.cursor()
    passed = 0
    failed = 0
    failed_apps = []
    
    for row in rows:
        app_id, xml_str = row
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
        except:
            continue
            
        expected_count = 0
        for prefix in xml_prefix_list:
            p_found = False
            # Scan elements for attributes starting with prefix
            # Optimization: assumes flattened structure matches expected node types
            # But simpler: scan ALL elements
            for element in root.iter():
                for attr, val in element.items():
                    # Ignore empty/zero values to prevent phantom row expectation
                    if attr.startswith(prefix) and val and val.strip() not in ['0', '0.00', '0.0', '', 'None', 'MISSING']:
                        # Check suffix ignore list
                        if ignore_suffixes:
                            is_ignored = False
                            for suffix in ignore_suffixes:
                                if attr.endswith(suffix):
                                    is_ignored = True
                                    break
                            if is_ignored:
                                continue

                        p_found = True
                        break
                if p_found: break
            
            if p_found:
                expected_count += 1
                
        # Get Actual
        try:
            cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[{table_name}] WHERE app_id = ?", app_id)
            actual_count = cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error querying {table_name}: {e}")
            return

        if actual_count < expected_count:
            # logger.warning(f"App {app_id} {table_name}: Expected >={expected_count}, Got {actual_count}")
            failed += 1
            failed_apps.append(app_id)
        else:
            passed += 1
            
    logger.info(f"{table_name} Result: {passed} Passed, {failed} Failed")
    if failed_apps:
        logger.warning(f"  First 5 Failed Apps: {failed_apps[:5]}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="migration")
    parser.add_argument("--source-schema", default="dbo")
    parser.add_argument("--contract", default="config/mapping_contract_rl.json")
    parser.add_argument("--sample", type=int, default=50)
    parser.add_argument("--use-processed-apps", action="store_true", help="Audit apps found in processing_log")
    parser.add_argument("--app-ids", help="Comma-separated list of app_ids to audit")
    args = parser.parse_args()
    
    conn = pyodbc.connect(build_connection_string(args.server, args.database))
    contract = load_contract(args.contract)
    kv_mappings = get_kv_mappings(contract)
    
    specific_apps = [int(x) for x in args.app_ids.split(',')] if args.app_ids else None
    
    cursor = conn.cursor()
    rows = []
    
    if args.use_processed_apps:
        logger.info(f"Fetching last {args.sample} processed apps from {args.schema}.processing_log...")
        # Use log_id for ordering since processed_at may not exist
        cursor.execute(f"SELECT TOP {args.sample} app_id FROM [{args.schema}].[processing_log] WHERE status='success' ORDER BY log_id DESC")
        processed_ids = [r[0] for r in cursor.fetchall()]
        if not processed_ids:
            logger.warning("No processed apps found.")
            return
        # Fetch XML for these
        id_list = ",".join(str(i) for i in processed_ids)
        cursor.execute(f"SELECT app_id, app_XML FROM [{args.source_schema}].[app_xml_staging_rl] WHERE app_id IN ({id_list})")
        rows = cursor.fetchall()
        
    elif specific_apps:
        ids_str = ",".join(str(i) for i in specific_apps)
        cursor.execute(f"SELECT app_id, app_XML FROM [{args.source_schema}].[app_xml_staging_rl] WHERE app_id IN ({ids_str})")
        rows = cursor.fetchall()
    else:
        cursor.execute(f"SELECT TOP {args.sample} app_id, app_XML FROM [{args.source_schema}].[app_xml_staging_rl] ORDER BY NEWID()")
        rows = cursor.fetchall()

    logger.info(f"Loaded {len(rows)} apps for comprehensive KV audit.")

    # 1. Audit Scores
    audit_scores(conn, args.schema, rows, kv_mappings['scores'])

    # 2. Audit Collateral (Prefixes coll1_, coll2_, coll3_, coll4_)
    audit_generic_kv(conn, args.schema, rows, "app_collateral_rl", 
                    ['coll1_', 'coll2_', 'coll3_', 'coll4_'],
                    ignore_suffixes=['new_used_demo'])

    # 3. Audit Warranties (Prefixes warranty1_, warranty2_)
    audit_generic_kv(conn, args.schema, rows, "app_warranties_rl", 
                    ['warranty1_', 'warranty2_'])

    # 4. Audit Policy Exceptions
    audit_generic_kv(conn, args.schema, rows, "app_policy_exceptions_rl",
                    ['policy_exception1', 'policy_exception2', 'policy_exception3'])

    # 5. Audit Historical Lookup (Check count > 0 if specific keys found)
    # Just checking generic existence for now if XML implies history.
    # Hard to genericize without iterating all possible history keys.
    pass

if __name__ == "__main__":
    main()
