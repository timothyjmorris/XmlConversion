"""
Script to deduplicate mappings in mapping_contract_rl.json and fix empty target columns.
"""
import json
from pathlib import Path

CONTRACT_PATH = Path("config/mapping_contract_rl.json")

def clean_contract():
    if not CONTRACT_PATH.exists():
        print(f"Contract not found at {CONTRACT_PATH}")
        return

    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        contract = json.load(f)

    mappings = contract.get("mappings", [])
    
    seen_targets = set()
    cleaned_mappings = []
    
    duplicates_removed = 0
    empty_target_fixed = 0
    
    row_creating_prefixes = (
        'add_score',
        'add_indicator',
        'add_history',
        'add_report_lookup',
        'policy_exceptions',
    )


    for i, m in enumerate(mappings):
        table = m.get("target_table")
        col = m.get("target_column")
        
        # Check for empty target column
        if not col:
            # Check if it is a valid row creator
            mapping_types = m.get("mapping_type") or []
            if isinstance(mapping_types, str):
                mapping_types = [mapping_types]
                
            is_valid_row_creator = False
            for mt in mapping_types:
                if any(str(mt).strip().startswith(p) for p in row_creating_prefixes):
                    is_valid_row_creator = True
                    break
            
            if not is_valid_row_creator:
                print(f"Skipping invalid empty target column mapping at index {i}: {m}")
                empty_target_fixed += 1
                continue
            
            # Valid row creator - keep it
            cleaned_mappings.append(m)
            continue

        # Check for duplicates
        key = (table, col)
        if key in seen_targets:
            # Duplicate - skip
            print(f"Skipping duplicate target for {table}.{col} at index {i}")
            duplicates_removed += 1
            continue
            
        seen_targets.add(key)
        cleaned_mappings.append(m)

    contract['mappings'] = cleaned_mappings
    
    with open(CONTRACT_PATH, 'w', encoding='utf-8') as f:
        json.dump(contract, f, indent=4)
        
    print(f"Deduplication complete.")
    print(f"Removed {duplicates_removed} duplicate mappings.")
    print(f"Removed {empty_target_fixed} invalid empty target mappings.")
    print(f"Remaining mappings: {len(cleaned_mappings)}")

if __name__ == "__main__":
    clean_contract()
