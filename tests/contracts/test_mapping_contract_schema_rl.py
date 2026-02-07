"""
Test script to validate the RL mapping contract configuration.
Checks the JSON mapping contract for completeness and consistency against RL schema.
"""

import json
import pytest
import pyodbc

from pathlib import Path
from xml_extractor.config.config_manager import get_config_manager


# --- Constants and globals ---
CONTRACT_PATH = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
DIFF_OUTPUT_PATH = Path(__file__).parent / "mapping_contract_schema_rl_diff.json"


# SQL Server type to contract type translation (Shared logic)
SQL_TO_CONTRACT_TYPE = {
    "varchar": "string",
    "nvarchar": "string",
    "varchar": "string",
    "nvarchar": "string",
    "char": "string",
    "nchar": "string",
    "text": "string",
    "datetime": "datetime",
    "smalldatetime": "datetime",
    "date": "datetime",
    "int": "int",
    "bigint": "int",
    "smallint": "int",
    "tinyint": "int",
    "float": "float",
    "decimal": "float",
    "numeric": "float",
    "bit": "bit"
    }

# --- Fixtures ---
def load_mapping_contract():
    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

@pytest.fixture(scope="module")
def contract():
    if not CONTRACT_PATH.exists():
        pytest.skip(f"RL Mapping contract file not found: {CONTRACT_PATH}")
    return load_mapping_contract()

# --- Helper functions ---
def get_db_schema(contract):
    config = get_config_manager()
    db_conf = config.database_config
    # Force use of target_schema 'dbo' if checking against local sample DDL execution 
    # Or respect contract. 
    # We will assume user creates tables in the schema defined in contract.
    schema_name = contract.get("target_schema", "dbo")
    
    conn_str = db_conf.connection_string
    schema = {}
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, IS_NULLABLE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ?
            """, (schema_name,))
            rows = cursor.fetchall()
            if not rows:
                print(f"WARNING: No tables found in schema '{schema_name}'. Validation may fail.")
            
            for row in rows:
                tbl = row.TABLE_NAME
                col = row.COLUMN_NAME
                schema.setdefault(tbl, {})[col] = {
                    "nullable": row.IS_NULLABLE == "YES",
                    "data_type": row.DATA_TYPE,
                    "data_length": row.CHARACTER_MAXIMUM_LENGTH,
                }
    except pyodbc.Error as e:
        pytest.fail(f"Database connection failed: {e}")
        
    return schema

def compare_contract_to_schema(contract, schema):
    mismatches = []
    for mapping in contract.get("mappings", []):
        tbl = mapping["target_table"]
        col = mapping["target_column"]

        # Row-creating mapping types intentionally leave target_column blank.
        if not col:
            mapping_types = mapping.get('mapping_type') or []
            if isinstance(mapping_types, str):
                mapping_types = [mt.strip() for mt in mapping_types.split(',') if mt.strip()]
            row_creating_prefixes = (
                'add_score',
                'add_indicator',
                'add_history',
                'add_report_lookup',
                'policy_exceptions',
                'warranty_field',
                'add_collateral',
            )
            if any(str(mt).strip().startswith(row_creating_prefixes) for mt in mapping_types):
                continue

        contract_type = mapping.get("data_type")
        contract_nullable = mapping.get("nullable")
        contract_required = mapping.get("required")
        contract_length = mapping.get("data_length")
        if tbl not in schema or col not in schema[tbl]:
            mismatches.append({
                "table": tbl,
                "column": col,
                "issue": "Missing in DB schema",
            })
            continue
        db_col = schema[tbl][col]
        # Compare raw SQL type to contract type
        db_raw_type = db_col["data_type"].lower()
        contract_type_norm = contract_type.lower() if contract_type else None
        
        type_equiv = False
        if contract_type_norm == db_raw_type:
            type_equiv = True
        elif contract_type_norm == "string" and db_raw_type in ("varchar", "nvarchar", "char", "nchar", "text"):
            type_equiv = True
        elif contract_type_norm in ("decimal", "numeric", "float") and db_raw_type in ("decimal", "numeric", "float"):
            type_equiv = True
        elif contract_type_norm in ("datetime", "smalldatetime", "date") and db_raw_type in ("datetime", "smalldatetime", "date"):
            type_equiv = True
        elif contract_type_norm == "bit" and db_raw_type == "bit":
            type_equiv = True
        elif contract_type_norm == "int" and db_raw_type in ("int", "bigint", "smallint", "tinyint"):
            type_equiv = True
            
        if not type_equiv:
            mismatches.append({
                "table": tbl,
                "column": col,
                "property": "data_type",
                "contract_value": contract_type,
                "db_value": db_raw_type,
                "recommendation": db_raw_type,
            })
        
        # Nullability check
        # CSV generator defaults nullable=True. DB might be NOT NULL.
        # This will flag mismatches if generator defaults don't match DDL.
        if contract_nullable != db_col["nullable"]:
            mismatches.append({
                "table": tbl,
                "column": col,
                "property": "nullable",
                "contract_value": contract_nullable,
                "db_value": db_col["nullable"],
                "recommendation": db_col["nullable"],
            })

    return mismatches

# --- Tests ---
def test_valid_rl_tables(contract):
    """Ensure target tables are valid RL tables."""
    errors = []
    mappings = contract.get('mappings', [])
    valid_tables = {
        'app_base', 'app_operational_rl', 'app_pricing_rl', 'app_transactional_rl', 
        'app_funding_rl', 'app_funding_checklist_rl', 'app_funding_contract_rl',
        'app_warranties_rl', 'app_policy_exceptions_rl', 'app_collateral_rl', 'app_dealer_rl',
        'app_contact_base', 'app_contact_address', 'app_contact_employment',
        'scores', 'indicators', 'app_historical_lookup', 'app_report_results_lookup',
        'processing_log'
    }
    for i, mapping in enumerate(mappings):
        target_table = mapping.get('target_table', '')
        if target_table and target_table not in valid_tables:
            # Allow stripped array notation if any slipped through (shouldn't)
            if '[' not in target_table: 
                errors.append(f"Mapping {i} invalid target table: {target_table}")
    assert not errors, f"Field mapping validation errors: {errors}"

def test_contract_field_mappings_vs_db_schema(contract):
    schema = get_db_schema(contract)
    if not schema:
        pytest.skip("No schema found (tables might not be created yes). Skipping schema validation test.")
        
    mismatches = compare_contract_to_schema(contract, schema)
    if mismatches:
        with open(DIFF_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(mismatches, f, indent=2)
        
        # Summary
        mismatches_by_table = {}
        for mismatch in mismatches:
            tbl = mismatch.get("table")
            if tbl not in mismatches_by_table:
                mismatches_by_table[tbl] = []
            mismatches_by_table[tbl].append(mismatch)
            
        print("\n" + "="*80)
        print("RL CONTRACT/DATABASE SCHEMA MISMATCHES")
        print("="*80)
        for tbl, items in mismatches_by_table.items():
            print(f"[{tbl}] - {len(items)} mismatches")
        print(f"\nSee {DIFF_OUTPUT_PATH} for details.")
        
    assert not mismatches, f"RL Contract/DB schema mismatches found. See {DIFF_OUTPUT_PATH}."
