
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



def load_fixture():
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

class TestMappingTypeChain:
    @pytest.fixture(scope="class")
    def fixture(self):
        return load_fixture()

    def test_mapping_type_chain_cell_phone(self, fixture):
        xml_root = fixture["parser"].parse_xml_stream(fixture["sample_xml"])
        xml_data = fixture["parser"].extract_elements(xml_root)
        mapped_tables = fixture["mapper"].apply_mapping_contract(xml_data, fixture["contract"], xml_root=xml_root)
        app_contact_base = mapped_tables.get("app_contact_base", [])
        cell_phones = [rec.get("cell_phone") for rec in app_contact_base if rec.get("cell_phone")]
        assert cell_phones and cell_phones[0] == "5555555555"
