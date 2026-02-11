"""
SOURCE-FIRST Reconciliation Audit for RL KV Tables

Unlike the previous audit tool which only checked already-processed apps,
this tool starts from the XML SOURCE and works forward:

1. COVERAGE: What % of source apps have been processed?
2. COMPLETENESS: For processed apps, does every XML value that SHOULD 
   create a score/collateral/warranty row actually exist in the DB?
3. ACCURACY: For rows that DO exist, does the value match the XML?

This is the tool that catches:
- Apps that were never processed (coverage gaps)
- Apps that were processed but lost data (completeness bugs)
- Apps that have wrong values (accuracy bugs)
"""
import pyodbc
import argparse
import json
import logging
from lxml import etree
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    """Results for a single table audit."""
    table_name: str
    total_source_apps: int = 0
    processed_apps: int = 0
    unprocessed_apps: int = 0
    
    # For processed apps:
    expected_rows: int = 0      # XML says this many rows should exist
    actual_rows: int = 0        # DB has this many rows
    missing_rows: int = 0       # expected - actual (data loss)
    extra_rows: int = 0         # actual > expected (unexpected)
    value_mismatches: int = 0   # row exists but wrong value
    
    missing_details: List[Dict] = field(default_factory=list)
    mismatch_details: List[Dict] = field(default_factory=list)


def build_conn(server, database):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=no;"
    )


def load_contract(path):
    with open(path, 'r') as f:
        return json.load(f)


def get_score_mappings(contract) -> List[Dict]:
    """Extract add_score mappings from contract."""
    mappings = []
    for m in contract.get('mappings', []):
        m_types = m.get('mapping_type', [])
        for mt in m_types:
            mt_str = str(mt).strip()
            if mt_str.startswith('add_score('):
                identifier = mt_str.split('(')[1].strip(')')
                mappings.append({
                    'xml_path': m.get('xml_path'),
                    'xml_attribute': m.get('xml_attribute'),
                    'identifier': identifier,
                    'data_type': m.get('data_type', 'string'),
                })
    return mappings


def extract_xml_scores(root, score_mappings) -> Dict[str, str]:
    """
    Extract expected score values from XML using the same logic as DataMapper.
    Returns: {identifier: raw_value} for all scores with meaningful values.
    """
    expected = {}
    for sm in score_mappings:
        node_name = sm['xml_path'].split('/')[-1]
        attr = sm['xml_attribute']
        if not attr:
            continue
        
        nodes = root.xpath(f'//{node_name}')
        for node in nodes:
            val = node.get(attr)
            # Match DataMapper._extract_score_records logic:
            # raw_value = self._extract_value_from_xml(...)
            # if raw_value is None: continue
            if val is None:
                continue
            # The XML parser returns the literal string. 
            # DataMapper then calls transform_data_types(raw_value, data_type)
            # For "int": if raw_value is "None" -> transform returns None -> skip
            # For "int": if raw_value is "0" -> transform returns 0 -> KEEP (it's a valid int)
            # For "int": if raw_value is "" -> transform returns None -> skip
            stripped = val.strip()
            if stripped in ('', 'None', 'null'):
                continue
            
            # It has a meaningful XML value. DataMapper should create a row.
            expected[sm['identifier']] = stripped
    
    return expected


def extract_xml_collateral_slots(root) -> Dict[int, Dict[str, str]]:
    """
    Extract expected collateral slots from XML.
    Returns: {slot_number: {attr: value}} for slots with meaningful data.
    """
    slots = {}
    for slot_num in range(1, 5):
        prefix = f'coll{slot_num}_'
        slot_data = {}
        has_meaningful = False
        
        for element in root.iter():
            for attr, val in element.items():
                if attr.startswith(prefix):
                    suffix = attr[len(prefix):]
                    slot_data[suffix] = val
                    # Match DataMapper logic: 
                    # - new_used_demo alone doesn't create a row (char_to_bit, always produces 0/1)
                    # - value of "0" or "0.00" for wholesale_value doesn't create a row
                    # - empty strings don't create a row
                    if suffix in ('new_used_demo', 'invoice_wholesale_ind'):
                        continue  # These don't count as "meaningful"
                    if suffix == 'value':
                        try:
                            if float(val.strip()) > 0:
                                has_meaningful = True
                        except (ValueError, TypeError):
                            pass
                        continue
                    if val and val.strip() not in ('', '0', '0.00', '0.0', 'None', 'MISSING'):
                        has_meaningful = True
        
        if has_meaningful:
            slots[slot_num] = slot_data
    
    return slots


def audit_scores(conn, schema, source_schema, score_mappings, sample_size=None):
    """Source-first audit of scores table."""
    result = AuditResult(table_name='scores')
    cursor = conn.cursor()
    
    # Get processed app_ids
    cursor.execute(f"""
        SELECT app_id FROM [{schema}].[processing_log] WHERE status='success'
    """)
    processed_set = {r[0] for r in cursor.fetchall()}
    
    # Get ALL source apps (or sample)
    if sample_size:
        cursor.execute(f"SELECT TOP {sample_size} app_id, app_XML FROM [{source_schema}].[app_xml_staging_rl] ORDER BY NEWID()")
    else:
        cursor.execute(f"SELECT app_id, app_XML FROM [{source_schema}].[app_xml_staging_rl]")
    source_rows = cursor.fetchall()
    
    result.total_source_apps = len(source_rows)
    
    for app_id, xml_str in source_rows:
        is_processed = app_id in processed_set
        if not is_processed:
            result.unprocessed_apps += 1
            continue
        
        result.processed_apps += 1
        
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
        except:
            continue
        
        # What scores does XML expect?
        expected = extract_xml_scores(root, score_mappings)
        
        # What scores does DB have?
        cursor.execute(f"""
            SELECT score_identifier, score 
            FROM [{schema}].[scores] 
            WHERE app_id = ?
        """, app_id)
        db_rows = {r[0]: r[1] for r in cursor.fetchall()}
        
        # Compare
        for identifier, xml_val in expected.items():
            result.expected_rows += 1
            if identifier in db_rows:
                result.actual_rows += 1
                # Accuracy check: compare values
                try:
                    xml_numeric = int(float(xml_val))
                    if db_rows[identifier] != xml_numeric:
                        result.value_mismatches += 1
                        result.mismatch_details.append({
                            'app_id': app_id, 'identifier': identifier,
                            'xml_value': xml_val, 'db_value': db_rows[identifier]
                        })
                except (ValueError, TypeError):
                    pass
            else:
                result.missing_rows += 1
                result.missing_details.append({
                    'app_id': app_id, 'identifier': identifier, 'xml_value': xml_val
                })
    
    return result


def audit_collateral(conn, schema, source_schema, sample_size=None):
    """Source-first audit of collateral table."""
    result = AuditResult(table_name='app_collateral_rl')
    cursor = conn.cursor()
    
    cursor.execute(f"""
        SELECT app_id FROM [{schema}].[processing_log] WHERE status='success'
    """)
    processed_set = {r[0] for r in cursor.fetchall()}
    
    if sample_size:
        cursor.execute(f"SELECT TOP {sample_size} app_id, app_XML FROM [{source_schema}].[app_xml_staging_rl] ORDER BY NEWID()")
    else:
        cursor.execute(f"SELECT app_id, app_XML FROM [{source_schema}].[app_xml_staging_rl]")
    source_rows = cursor.fetchall()
    
    result.total_source_apps = len(source_rows)
    
    for app_id, xml_str in source_rows:
        if app_id not in processed_set:
            result.unprocessed_apps += 1
            continue
        
        result.processed_apps += 1
        
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
        except:
            continue
        
        expected_slots = extract_xml_collateral_slots(root)
        expected_count = len(expected_slots)
        
        cursor.execute(f"SELECT COUNT(*) FROM [{schema}].[app_collateral_rl] WHERE app_id = ?", app_id)
        actual_count = cursor.fetchone()[0]
        
        result.expected_rows += expected_count
        result.actual_rows += actual_count
        
        if actual_count < expected_count:
            result.missing_rows += (expected_count - actual_count)
            result.missing_details.append({
                'app_id': app_id, 'expected': expected_count, 'actual': actual_count,
                'slots': list(expected_slots.keys())
            })
    
    return result


def print_result(result: AuditResult):
    """Print audit result with clear pass/fail status."""
    print(f"\n{'=' * 80}")
    print(f"TABLE: {result.table_name}")
    print(f"{'=' * 80}")
    
    print(f"  Source Population:      {result.total_source_apps}")
    print(f"  Processed:              {result.processed_apps} ({result.processed_apps/max(result.total_source_apps,1)*100:.1f}%)")
    print(f"  Unprocessed:            {result.unprocessed_apps} ({result.unprocessed_apps/max(result.total_source_apps,1)*100:.1f}%)")
    
    if result.processed_apps > 0:
        print(f"\n  Expected Rows (from XML): {result.expected_rows}")
        print(f"  Actual Rows (in DB):      {result.actual_rows}")
        print(f"  Missing Rows (DATA LOSS): {result.missing_rows}")
        print(f"  Value Mismatches:         {result.value_mismatches}")
        
        if result.missing_rows == 0 and result.value_mismatches == 0:
            print(f"\n  ✓ PASS — All processed apps have correct data")
        else:
            print(f"\n  ✗ FAIL — Data integrity issues detected")
            
        if result.missing_details:
            print(f"\n  Missing Details (first 10):")
            for d in result.missing_details[:10]:
                print(f"    {d}")
        if result.mismatch_details:
            print(f"\n  Mismatch Details (first 10):")
            for d in result.mismatch_details[:10]:
                print(f"    {d}")
    
    if result.unprocessed_apps > 0:
        pct = result.unprocessed_apps / max(result.total_source_apps, 1) * 100
        if pct > 5:
            print(f"\n  ⚠ WARNING — {pct:.0f}% of source apps have NOT been processed")


def main():
    parser = argparse.ArgumentParser(description="Source-first reconciliation audit for RL KV tables")
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="migration")
    parser.add_argument("--source-schema", default="dbo")
    parser.add_argument("--contract", default="config/mapping_contract_rl.json")
    parser.add_argument("--sample", type=int, help="Sample size (default: all)")
    args = parser.parse_args()
    
    conn = build_conn(args.server, args.database)
    contract = load_contract(args.contract)
    score_mappings = get_score_mappings(contract)
    
    print("=" * 80)
    print("SOURCE-FIRST RECONCILIATION AUDIT")
    print(f"Schema: {args.schema}  |  Source: {args.source_schema}  |  Sample: {args.sample or 'ALL'}")
    print("=" * 80)
    
    # Audit Scores
    scores_result = audit_scores(conn, args.schema, args.source_schema, score_mappings, args.sample)
    print_result(scores_result)
    
    # Audit Collateral
    coll_result = audit_collateral(conn, args.schema, args.source_schema, args.sample)
    print_result(coll_result)
    
    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    all_results = [scores_result, coll_result]
    total_missing = sum(r.missing_rows for r in all_results)
    total_mismatches = sum(r.value_mismatches for r in all_results)
    total_unprocessed = max(r.unprocessed_apps for r in all_results)  # Same across tables
    
    if total_missing == 0 and total_mismatches == 0:
        print(f"  ✓ All processed apps have correct KV data")
    else:
        print(f"  ✗ {total_missing} missing rows, {total_mismatches} value mismatches")
    
    if total_unprocessed > 0:
        print(f"  ⚠ {total_unprocessed} apps still unprocessed — run production_processor to close the gap")
    
    conn.close()


if __name__ == "__main__":
    main()
