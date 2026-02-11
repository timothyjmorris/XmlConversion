import json
import sys

def check_contract(file_path):
    with open(file_path, 'r') as f:
        contract = json.load(f)
    
    mappings = contract.get('mappings', [])
    
    errors = []
    
    for m in mappings:
        target_table = m.get('target_table', '')
        mapping_types = m.get('mapping_type', [])
        
        # Check add_score
        has_add_score = any('add_score' in str(mt) for mt in mapping_types)
        if has_add_score and target_table != 'scores':
            errors.append(f"FAIL: {m.get('xml_attribute')} uses add_score but targets '{target_table}'")

        # Check add_indicator
        has_add_indicator = any('add_indicator' in str(mt) for mt in mapping_types)
        if has_add_indicator and target_table != 'indicators':
            errors.append(f"FAIL: {m.get('xml_attribute')} uses add_indicator but targets '{target_table}'")
            
        # Check add_history
        has_add_history = any('add_history' in str(mt) for mt in mapping_types)
        if has_add_history and target_table != 'app_historical_lookup':
            errors.append(f"FAIL: {m.get('xml_attribute')} uses add_history but targets '{target_table}'")

    if errors:
        print(f"Found {len(errors)} Contract Errors:")
        for e in errors:
            print(e)
    else:
        print("Contract Integrity Check Passed")

if __name__ == "__main__":
    check_contract(sys.argv[1])
