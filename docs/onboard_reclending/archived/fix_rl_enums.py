"""
Script to fix invalid enum mappings in mapping_contract_rl.json.
Removes 'enum' mapping_type if the enum definition is missing.
"""
import json
from pathlib import Path

CONTRACT_PATH = Path("config/mapping_contract_rl.json")

def fix_enums():
    if not CONTRACT_PATH.exists():
        print(f"Contract not found at {CONTRACT_PATH}")
        return

    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        contract = json.load(f)

    mappings = contract.get("mappings", [])
    enum_definitions = contract.get("enum_mappings", {})
    
    fixed_count = 0
    
    for m in mappings:
        mapping_types = m.get("mapping_type")
        if not mapping_types:
            continue
            
        if isinstance(mapping_types, str):
            mapping_types = [mapping_types]
            
        if "enum" in mapping_types:
            col = m.get("target_column")
            # Logic from DataMapper._determine_enum_type
            if col.endswith("_enum"):
                enum_name = col
            elif col.endswith("_code"):
                enum_name = col[:-5] + "_enum"
            else:
                enum_name = col + "_enum" # Fallback guess
                
            # Check if defined
            if enum_name not in enum_definitions:
                print(f"Removing invalid 'enum' mapping for {col} (enum {enum_name} not defined)")
                mapping_types.remove("enum")
                if not mapping_types:
                    del m["mapping_type"]
                else:
                    m["mapping_type"] = mapping_types
                fixed_count += 1

    contract['mappings'] = mappings
    
    with open(CONTRACT_PATH, 'w', encoding='utf-8') as f:
        json.dump(contract, f, indent=4)
        
    print(f"Enum fix complete. Fixed {fixed_count} mappings.")

if __name__ == "__main__":
    fix_enums()
