#!/usr/bin/env python3
"""
Debug script to show what SQL would be generated from the mapping contract.
"""

import sys
from pathlib import Path
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def debug_sql_generation():
    """Show what SQL would be generated."""
    
    # Load the mapping contract
    mapping_contract_path = Path("config/credit_card_mapping_contract.json")
    with open(mapping_contract_path, 'r') as f:
        mapping_contract = json.load(f)
    
    print("🔍 SQL Generation Debug")
    print("="*50)
    
    # Group mappings by target table
    tables = {}
    for mapping in mapping_contract['mappings']:
        table = mapping['target_table']
        if table not in tables:
            tables[table] = []
        tables[table].append(mapping)
    
    # Show what SQL would be generated for each table
    for table_name, mappings in tables.items():
        print(f"\n📊 Table: {table_name}")
        
        # Extract column names
        columns = [m['target_column'] for m in mappings]
        
        # Show INSERT statement structure
        column_list = ', '.join(f"[{col}]" for col in columns)
        placeholders = ', '.join('?' * len(columns))
        
        # Check if table needs IDENTITY_INSERT
        identity_columns = [m for m in mappings if m.get('mapping_type') == 'identity_insert']
        needs_identity_insert = len(identity_columns) > 0
        
        if needs_identity_insert:
            print(f"   🔑 IDENTITY_INSERT required for: {[m['target_column'] for m in identity_columns]}")
            print(f"   SET IDENTITY_INSERT [{table_name}] ON")
        
        sql = f"INSERT INTO [{table_name}] ({column_list}) VALUES ({placeholders})"
        print(f"   SQL: {sql}")
        
        if needs_identity_insert:
            print(f"   SET IDENTITY_INSERT [{table_name}] OFF")
        
        # Show sample data structure expected
        print(f"   Expected data structure:")
        for mapping in mappings[:3]:  # Show first 3
            source = mapping.get('xml_path', 'N/A')
            attr = mapping.get('xml_attribute', '')
            if attr:
                source += f"/@{attr}"
            print(f"     {mapping['target_column']}: from {source} ({mapping['data_type']})")
        if len(mappings) > 3:
            print(f"     ... and {len(mappings) - 3} more columns")
    
    # Show enum mappings that would be used
    print(f"\n📋 Enum Mappings:")
    enums = mapping_contract.get('enum_mappings', {})
    for enum_name, values in enums.items():
        if enum_name in ['contact_type_enum', 'address_type_enum', 'employment_type_enum']:
            print(f"   {enum_name}: {values}")

if __name__ == '__main__':
    debug_sql_generation()