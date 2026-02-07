"""
Script to apply schema corrections to mapping_contract_rl.json based on actual DB schema.
Fixes data_type, nullable, and data_length mismatches.
"""
import json
import pyodbc
from pathlib import Path
from xml_extractor.config.config_manager import get_config_manager

CONTRACT_PATH = Path("config/mapping_contract_rl.json")

def get_db_schema(target_schema="dbo"):
    config = get_config_manager()
    db_conf = config.database_config
    conn_str = db_conf.connection_string
    
    schema = {}
    print(f"Connecting to {db_conf.server} / {db_conf.database}...")
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_NAME, COLUMN_NAME, IS_NULLABLE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ?
            """, (target_schema,))
            rows = cursor.fetchall()
            for row in rows:
                tbl = row.TABLE_NAME
                col = row.COLUMN_NAME
                schema.setdefault(tbl, {})[col] = {
                    "nullable": row.IS_NULLABLE == "YES",
                    "data_type": row.DATA_TYPE,
                    "data_length": row.CHARACTER_MAXIMUM_LENGTH,
                }
    except Exception as e:
        print(f"Error fetching schema: {e}")
        return None
    return schema

def apply_corrections():
    if not CONTRACT_PATH.exists():
        print(f"Contract not found at {CONTRACT_PATH}")
        return

    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        contract = json.load(f)

    target_schema_name = contract.get("target_schema", "dbo")
    db_schema = get_db_schema(target_schema_name)
    
    if not db_schema:
        print("Could not retrieve DB schema. Aborting.")
        return

    updated_count = 0
    removed_count = 0
    
    new_mappings = []
    
    for mapping in contract.get("mappings", []):
        tbl = mapping.get("target_table")
        col = mapping.get("target_column")
        
        # Skip special row-creating mappings
        if not col:
            new_mappings.append(mapping)
            continue
            
        if tbl not in db_schema:
            print(f"WARNING: Table {tbl} not found in DB schema. Keeping mapping as is.")
            new_mappings.append(mapping)
            continue
            
        if col not in db_schema[tbl]:
            print(f"REMOVING: Column {tbl}.{col} not found in DB schema.")
            removed_count += 1
            continue
            
        # Update properties
        db_col = db_schema[tbl][col]
        
        # Type mapping - preserve smallint for enum columns
        db_type = db_col['data_type'].lower()
        if db_type in ('varchar', 'nvarchar', 'char', 'nchar', 'text'):
            new_type = 'string'
        elif db_type == 'smallint':
            new_type = 'smallint'
        elif db_type in ('int', 'bigint'):
            new_type = 'int'
        elif db_type == 'tinyint':
            new_type = 'tinyint'
        elif db_type in ('decimal', 'numeric', 'float', 'real', 'money'):
            new_type = 'decimal'
        elif db_type in ('datetime', 'smalldatetime', 'date'):
            new_type = 'datetime'
        elif db_type == 'bit':
            new_type = 'bit'
        else:
            new_type = db_type
            
        mapping['data_type'] = new_type
        mapping['nullable'] = db_col['nullable']
        if db_col['data_length']:
             mapping['data_length'] = int(db_col['data_length'])
        
        # Helper: 'required' is roughly opposite of nullable, but logic can vary.
        # Ensure 'required' is false if nullable is true.
        if mapping.get('nullable') is True:
             mapping['required'] = False
        
        updated_count += 1
        new_mappings.append(mapping)

    contract['mappings'] = new_mappings
    
    with open(CONTRACT_PATH, 'w', encoding='utf-8') as f:
        json.dump(contract, f, indent=2)
        
    print(f"Done. Updated {updated_count} mappings. Removed {removed_count} invalid mappings.")

if __name__ == "__main__":
    apply_corrections()
