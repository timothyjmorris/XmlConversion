import json
import argparse
from typing import List, Dict, Any

def audit_contract(file_path: str, product_line: str):
    print(f"\n--- Auditing {product_line} Contract: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            contract = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return

    # Define validation rules
    # key = special mapping_type function
    # value = expected target_table
    rules = {
        'add_score': 'scores',
        'add_indicator': 'indicators',
        'add_collateral': 'app_collateral', # Prefix match
        'add_warranty': 'app_warranties',   # Prefix match
        'add_policy_exception': 'app_policy_exceptions' # Prefix match
    }
    
    mismatches = []
    
    for m in contract.get('mappings', []):
        mapping_types = m.get('mapping_type', [])
        target_table = m.get('target_table', '')
        xml_path = m.get('xml_path', '')
        xml_attr = m.get('xml_attribute', '')
        
        # Check mapping types against rules
        for mt in mapping_types:
            mt_str = str(mt).strip()
            
            for key, expected_table_param in rules.items():
                if mt_str.startswith(key):
                    # For RL, collateral tables have _rl suffix, so used startswith logic for some
                    is_match = False
                    if expected_table_param == 'scores' and target_table == 'scores':
                        is_match = True
                    elif expected_table_param == 'indicators' and target_table == 'indicators':
                        is_match = True
                    elif expected_table_param == 'app_collateral' and target_table.startswith('app_collateral'):
                        is_match = True
                    elif expected_table_param == 'app_warranties' and target_table.startswith('app_warranties'):
                        is_match = True
                    elif expected_table_param == 'app_policy_exceptions' and target_table.startswith('app_policy_exceptions'):
                        is_match = True
                        
                    if not is_match:
                        # Special case: add_history is used somewhat loosely in the dump
                        # But user specifically asked about scores/indicators mismatch
                        mismatches.append({
                            'key': mt_str,
                            'target_table': target_table,
                            'expected_table_hint': expected_table_param,
                            'xml': f"{xml_path}@{xml_attr}"
                        })

    if mismatches:
        print(f"Found {len(mismatches)} mismatches:")
        for mis in mismatches:
            print(f"  FAILED: {mis['key']} -> Table '{mis['target_table']}' (Expected ~ {mis['expected_table_hint']})")
            print(f"     XML: {mis['xml']}")
    else:
        print("No mismatched field-to-row fields found (Scores, Indicators, Collateral, Warranties, PolicyExceptions).")

def main():
    audit_contract('config/mapping_contract.json', 'CC')
    audit_contract('config/mapping_contract_rl.json', 'RL')

if __name__ == "__main__":
    main()
