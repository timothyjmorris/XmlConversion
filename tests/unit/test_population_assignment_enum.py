import sys
import os
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
import pytest
from pathlib import Path
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.models import MappingContract, FieldMapping, RelationshipMapping
import json

@pytest.fixture(scope="module")
def fixture():
    sample_path = Path(__file__).parent.parent.parent / "config" / "samples" / "xml_files" / "sample-source-xml-old--4696.xml"
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

def test_population_assignment_enum_extraction_and_mapping(fixture):
    xml_root = fixture["parser"].parse_xml_stream(fixture["sample_xml"])
    xml_data = fixture["parser"].extract_elements(xml_root)
    mapped_tables = fixture["mapper"].apply_mapping_contract(xml_data, fixture["contract"], xml_root=xml_root)
    contract = fixture["contract"]
    found = False
    debug_vals = []
    for mapping in contract.mappings:
        if mapping.target_table == "app_pricing_cc" and mapping.target_column == "population_assignment_enum":
            records = mapped_tables.get("app_pricing_cc", [])
            for rec in records:
                val = rec.get("population_assignment_enum")
                debug_vals.append(val)
                if val == 242:
                    found = True
    print(f"Extracted population_assignment_enum values: {debug_vals}")
    assert found, "population_assignment_enum should be mapped to 242 for 'HU' in sample XML"
