
import sys
import os
import pytest
import json

from pathlib import Path

from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.models import MappingContract, FieldMapping, RelationshipMapping

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)


@pytest.fixture(scope="module")
def fixture():
    sample_path = Path(__file__).parent.parent.parent / "config" / "samples" / "sample-source-xml-contact-test.xml"
    with open(sample_path, 'r', encoding='utf-8-sig') as f:
        sample_xml = f.read()
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract.json"
    with open(contract_path, 'r', encoding='utf-8-sig') as f:
        contract_json = json.load(f)
    contract_json["mappings"] = [FieldMapping(**fm) for fm in contract_json["mappings"]]
    if "relationships" in contract_json and contract_json["relationships"]:
        contract_json["relationships"] = [RelationshipMapping(**rm) for rm in contract_json["relationships"]]
    contract = MappingContract(**contract_json)
    mapper = DataMapper(mapping_contract_path=str(contract_path))
    parser = XMLParser()
    return {
        "sample_xml": sample_xml,
        "mapper": mapper,
        "parser": parser,
        "contract": contract,
    }

def test_contract_driven_truncation(fixture):
    xml_root = fixture["parser"].parse_xml_stream(fixture["sample_xml"])
    xml_data = fixture["parser"].extract_elements(xml_root)
    mapped_tables = fixture["mapper"].apply_mapping_contract(xml_data, fixture["contract"], xml_root=xml_root)
    contract = fixture["contract"]
    # Collect all failures and successes
    failures = []
    successes = []
    for mapping in contract.mappings:
        table = mapping.target_table
        column = mapping.target_column
        data_length = mapping.data_length
        if not data_length:
            continue  # Only check fields with explicit truncation
        records = mapped_tables.get(table, [])
        for rec in records:
            val = rec.get(column)
            if val is not None:
                # Only check string truncation for string fields
                if mapping.data_type == 'string' and isinstance(val, str):
                    if len(val) > data_length:
                        failures.append(f"{table}.{column} value '{val}' exceeds contract data_length {data_length}")
                    else:
                        successes.append(f"{table}.{column} value '{val}' PASSED (len={len(val)}, max={data_length})")
                elif mapping.data_type == 'string':
                    # If it's supposed to be string but is not, that's a failure
                    failures.append(f"{table}.{column} expected string but got {type(val)}: {val}")
                # For non-string types (like decimal), truncation doesn't apply in the same way
    # Print results for diagnosis
    if failures:
        print("\nFAILED truncation checks:")
        for fail in failures:
            print(fail)
    else:
        print("\nAll truncation checks passed!")
    print("\nSuccessful truncation checks:")
    for succ in successes:
        print(succ)
    
    # Debug: Print all mapped fields
    print("\nAll mapped fields:")
    for mapping in contract.mappings:
        table = mapping.target_table
        column = mapping.target_column
        records = mapped_tables.get(table, [])
        for rec in records:
            val = rec.get(column)
            print(f"{table}.{column}: {repr(val)}")
    
    assert not failures, f"Truncation failures found: {len(failures)}. See output above."

def test_decimal_precision_rounding(fixture):
    """Test that decimal values are rounded correctly according to contract precision."""
    mapper = fixture["mapper"]
    
    # Test the _transform_to_decimal_with_precision method directly
    test_cases = [
        ("2003.2003", 2, 2003.20),  # Should round to 2 decimal places
        ("893.55444444444", 2, 893.55),  # Should round to 2 decimal places
        ("120000.656", 2, 120000.66),  # Should round to 2 decimal places
        ("1.00444", 2, 1.00),  # Should round to 2 decimal places
        ("199.190001", 2, 199.19),  # Should round to 2 decimal places
        ("315.315", 2, 315.32),  # Should round to 2 decimal places
        ("0.1432197654", 5, 0.14322),  # Should round to 5 decimal places
        ("1.000666", 5, 1.00067),  # Should round to 5 decimal places
    ]
    
    for input_value, precision, expected in test_cases:
        result = mapper._transform_to_decimal_with_precision(input_value, precision)
        assert result == expected, f"Expected {expected} for {input_value} with precision {precision}, got {result}"
        print(f"OK {input_value} -> {result} (expected {expected})")