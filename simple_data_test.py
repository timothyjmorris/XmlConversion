#!/usr/bin/env python3
"""
Simple test to verify the data transformations are working correctly
without database insertion.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import MappingContract
import json

def test_data_transformations():
    """Test that data transformations are working correctly."""
    
    # Load test XML
    xml_file = "config/samples/sample-source-xml-1.xml"
    parser = XMLParser()
    with open(xml_file, 'r') as f:
        xml_content = f.read()
    xml_data = parser.parse_xml_stream(xml_content)
    
    # Load mapping contract
    contract_file = "config/credit_card_mapping_contract.json"
    with open(contract_file, 'r') as f:
        contract_data = json.load(f)
    
    # Create MappingContract from the loaded data
    from xml_extractor.models import FieldMapping, RelationshipMapping
    
    # Convert mappings to FieldMapping objects
    field_mappings = []
    for mapping_data in contract_data.get('mappings', []):
        field_mapping = FieldMapping(
            xml_path=mapping_data['xml_path'],
            xml_attribute=mapping_data['xml_attribute'],
            target_table=mapping_data['target_table'],
            target_column=mapping_data['target_column'],
            data_type=mapping_data['data_type'],
            mapping_type=mapping_data.get('mapping_type')
        )
        field_mappings.append(field_mapping)
    
    # Convert relationships to RelationshipMapping objects
    relationship_mappings = []
    for rel_data in contract_data.get('relationships', []):
        rel_mapping = RelationshipMapping(
            parent_table=rel_data['parent_table'],
            child_table=rel_data['child_table'],
            foreign_key_column=rel_data['foreign_key_column'],
            xml_parent_path=rel_data['xml_parent_path'],
            xml_child_path=rel_data['xml_child_path']
        )
        relationship_mappings.append(rel_mapping)
    
    contract = MappingContract(
        source_table=contract_data['source_table'],
        source_column=contract_data['source_column'],
        xml_root_element=contract_data['xml_root_element'],
        mappings=field_mappings,
        relationships=relationship_mappings
    )
    
    # Apply mapping
    mapper = DataMapper(contract_file)
    result = mapper.apply_mapping_contract(xml_data, contract)
    
    print("🎯 TRANSFORMATION RESULTS:")
    print("=" * 50)
    
    for table_name, records in result.items():
        print(f"\n📋 {table_name}: {len(records)} records")
        if records:
            sample_record = records[0]
            for field, value in sample_record.items():
                print(f"  {field}: {repr(value)} ({type(value).__name__})")
    
    # Check specific transformations
    print("\n🔍 VALIDATION CHECKS:")
    print("=" * 50)
    
    if 'app_base' in result and result['app_base']:
        app_record = result['app_base'][0]
        
        # Check app_source_enum transformation
        if app_record.get('app_source_enum') == 1:
            print("✅ app_source_enum: 'I' -> 1 (correct)")
        else:
            print(f"❌ app_source_enum: expected 1, got {app_record.get('app_source_enum')}")
        
        # Check receive_date transformation
        receive_date = app_record.get('receive_date')
        if isinstance(receive_date, str) and '2023-09-21' in receive_date:
            print("✅ receive_date: datetime string format (correct)")
        else:
            print(f"❌ receive_date: expected datetime string, got {repr(receive_date)}")
    
    if 'contact_base' in result and result['contact_base']:
        contact_record = result['contact_base'][0]
        
        # Check contact_type_enum transformation
        if contact_record.get('contact_type_enum') == 281:
            print("✅ contact_type_enum: 'PR' -> 281 (correct)")
        else:
            print(f"❌ contact_type_enum: expected 281, got {contact_record.get('contact_type_enum')}")
        
        # Check birth_date transformation
        birth_date = contact_record.get('birth_date')
        if isinstance(birth_date, str) and '1973-05-10' in birth_date:
            print("✅ birth_date: datetime string format (correct)")
        else:
            print(f"❌ birth_date: expected datetime string, got {repr(birth_date)}")

if __name__ == "__main__":
    test_data_transformations()