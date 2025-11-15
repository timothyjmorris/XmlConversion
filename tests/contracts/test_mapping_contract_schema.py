
"""
Test script to validate the mapping contract configuration.
Checks the JSON mapping contract for completeness and consistency.
"""

import json
import pytest
import pyodbc

from pathlib import Path
from xml_extractor.config.config_manager import get_config_manager


# --- Constants and globals ---
CONTRACT_PATH = Path(__file__).parent.parent.parent / "config" / "mapping_contract.json"
DIFF_OUTPUT_PATH = Path(__file__).parent / "mapping_contract_schema_diff.json"


# SQL Server type to contract type translation
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
    }

# --- Fixtures ---
def load_mapping_contract():
    with open(CONTRACT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

@pytest.fixture(scope="module")
def contract():
    if not CONTRACT_PATH.exists():
        pytest.skip(f"Mapping contract file not found: {CONTRACT_PATH}")
    return load_mapping_contract()

# --- Helper functions ---
def get_db_schema(contract):
    config = get_config_manager()
    db_conf = config.database_config
    schema_name = contract.get("target_schema", "dbo")
    print('DEBUG target_schema:', schema_name)
    print('DEBUG connection_string:', db_conf.connection_string)
    conn_str = db_conf.connection_string
    schema = {}
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, IS_NULLABLE, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ?
        """, (schema_name,))
        for row in cursor.fetchall():
            tbl = row.TABLE_NAME
            col = row.COLUMN_NAME
            schema.setdefault(tbl, {})[col] = {
                "nullable": row.IS_NULLABLE == "YES",
                "data_type": row.DATA_TYPE,
                "data_length": row.CHARACTER_MAXIMUM_LENGTH,
            }
    return schema

def compare_contract_to_schema(contract, schema):
    mismatches = []
    for mapping in contract.get("mappings", []):
        tbl = mapping["target_table"]
        col = mapping["target_column"]
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
        # Compare raw SQL type to contract type for accuracy
        db_raw_type = db_col["data_type"].lower()
        contract_type_norm = contract_type.lower() if contract_type else None
        # Accept synonyms: string/varchar/char/nchar/text, decimal/numeric/float, smalldatetime/datetime/date
        type_equiv = False
        if contract_type_norm == db_raw_type:
            type_equiv = True
        elif contract_type_norm == "string" and db_raw_type in ("varchar", "nvarchar", "char", "nchar", "text"):
            type_equiv = True
        elif contract_type_norm in ("decimal", "numeric", "float") and db_raw_type in ("decimal", "numeric", "float"):
            type_equiv = True
        elif contract_type_norm in ("datetime", "smalldatetime", "date") and db_raw_type in ("datetime", "smalldatetime", "date"):
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
        if contract_nullable != db_col["nullable"]:
            mismatches.append({
                "table": tbl,
                "column": col,
                "property": "nullable",
                "contract_value": contract_nullable,
                "db_value": db_col["nullable"],
                "recommendation": db_col["nullable"],
            })
        db_required = not db_col["nullable"]
        if contract_required != db_required:
            mismatches.append({
                "table": tbl,
                "column": col,
                "property": "required",
                "contract_value": contract_required,
                "db_value": db_required,
                "recommendation": db_required,
            })
        if db_raw_type in ("varchar", "nvarchar", "char", "nchar", "text"):
            if contract_length != db_col["data_length"]:
                mismatches.append({
                    "table": tbl,
                    "column": col,
                    "property": "data_length",
                    "contract_value": contract_length,
                    "db_value": db_col["data_length"],
                    "recommendation": db_col["data_length"],
                })
    return mismatches

# --- Tests ---
def test_element_filtering_validation(contract):
    errors = []
    element_filtering = contract.get('element_filtering', {})
    filter_rules = element_filtering.get('filter_rules', [])
    required_element_types = ['contact', 'address', 'employment']
    found_types = {rule.get('element_type') for rule in filter_rules}
    for elem_type in required_element_types:
        if elem_type not in found_types:
            errors.append(f"Missing required element type: {elem_type}")
    for rule in filter_rules:
        if not rule.get('element_type'):
            errors.append(f"Filter rule missing element_type")
        if not rule.get('xml_parent_path'):
            errors.append(f"Filter rule for {rule.get('element_type')} missing xml_parent_path")
        if not rule.get('xml_child_path'):
            errors.append(f"Filter rule for {rule.get('element_type')} missing xml_child_path")
        if not rule.get('required_attributes'):
            errors.append(f"Filter rule for {rule.get('element_type')} missing required_attributes")
    assert not errors, f"Element filtering validation errors: {errors}"

def test_enum_mappings_validation(contract):
    errors = []
    enum_mappings = contract.get('enum_mappings', {})
    required_enums = [
        'status_enum', 'app_source_enum', 'decision_enum', 
        'contact_type_enum', 'address_type_enum', 'employment_type_enum'
    ]
    for enum_type in required_enums:
        if enum_type not in enum_mappings:
            errors.append(f"Missing required enum mapping: {enum_type}")
    for enum_type, mappings in enum_mappings.items():
        for key, value in mappings.items():
            if not isinstance(value, int) or value < 1:
                errors.append(f"Enum {enum_type} value {value} for key '{key}' should be a positive integer")
    assert not errors, f"Enum mapping validation errors: {errors}"

def test_bit_conversions_validation(contract):
    errors = []
    bit_conversions = contract.get('bit_conversions', {})
    required_conversions = ['char_to_bit', 'boolean_to_bit']
    for conv_type in required_conversions:
        if conv_type not in bit_conversions:
            errors.append(f"Missing bit conversion type: {conv_type}")
    if 'char_to_bit' in bit_conversions:
        char_to_bit = bit_conversions['char_to_bit']
        required_chars = ['Y', 'N', '', 'null', ' ']
        for char in required_chars:
            if char not in char_to_bit:
                errors.append(f"char_to_bit missing mapping for: '{char}'")
            elif char_to_bit[char] not in [0, 1]:
                errors.append(f"char_to_bit invalid value for '{char}': {char_to_bit[char]}")
    assert not errors, f"Bit conversion validation errors: {errors}"

def test_field_mappings_validation(contract):
    errors = []
    mappings = contract.get('mappings', [])
    if not mappings:
        errors.append("No field mappings defined")
    else:
        required_fields = ['xml_path', 'target_table', 'target_column', 'data_type']
        for i, mapping in enumerate(mappings):
            for field in required_fields:
                if field not in mapping:
                    errors.append(f"Mapping {i} missing required field: {field}")
            xml_path = mapping.get('xml_path', '')
            if xml_path and not xml_path.startswith('/Provenir/Request'):
                errors.append(f"Mapping {i} XML path should start with '/Provenir/Request': {xml_path}")
            target_table = mapping.get('target_table', '')
            valid_tables = [
                'app_base', 'app_operational_cc', 'app_pricing_cc', 'app_transactional_cc', 'app_solicited_cc',
                'contact_base', 'contact_address', 'contact_employment'
            ]
            if target_table and target_table not in valid_tables:
                errors.append(f"Mapping {i} invalid target table: {target_table}")
        seen_mappings = set()
        for i, mapping in enumerate(mappings):
            key = (mapping.get('xml_path'), mapping.get('xml_attribute'), mapping.get('target_table'), mapping.get('target_column'))
            if key in seen_mappings:
                errors.append(f"Duplicate mapping found at index {i}: {key}")
            seen_mappings.add(key)
    assert not errors, f"Field mapping validation errors: {errors}"

def test_relationships_validation(contract):
    errors = []
    relationships = contract.get('relationships', [])
    for i, rel in enumerate(relationships):
        required_fields = ['parent_table', 'child_table', 'foreign_key_column', 'xml_parent_path', 'xml_child_path']
        for field in required_fields:
            if field not in rel:
                errors.append(f"Relationship {i} missing required field: {field}")
    assert not errors, f"Relationship validation errors: {errors}"

def test_contract_completeness(contract):
    required_sections = [
        'source_table', 'source_column', 'xml_root_element',
        'element_filtering', 'mappings', 'relationships'
    ]
    missing_sections = []
    for section in required_sections:
        if section not in contract:
            missing_sections.append(section)
    assert not missing_sections, f"Missing required sections: {missing_sections}"
    # Print summary for information
    print(f"\nContract Summary:")
    print(f"  - Element Filtering Rules: {len(contract.get('element_filtering', {}).get('filter_rules', []))}")
    print(f"  - Field Mappings: {len(contract.get('mappings', []))}")
    print(f"  - Enum Types: {len(contract.get('enum_mappings', {}))}")
    print(f"  - Bit Conversion Types: {len(contract.get('bit_conversions', {}))}")
    print(f"  - Relationships: {len(contract.get('relationships', []))}")

def test_contract_field_mappings_vs_db_schema(contract):
    schema = get_db_schema(contract)
    mismatches = compare_contract_to_schema(contract, schema)
    # Only export diff if there are mismatches
    if mismatches:
        with open(DIFF_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(mismatches, f, indent=2)
    assert not mismatches, f"Contract/DB schema mismatches found. See {DIFF_OUTPUT_PATH} for details."
