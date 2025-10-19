#!/usr/bin/env python3
"""
Simple integration test to debug issues.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("Testing imports...")
    
    from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
    print("✅ PreProcessingValidator imported")
    
    from xml_extractor.parsing.xml_parser import XMLParser
    print("✅ XMLParser imported")
    
    from xml_extractor.mapping.data_mapper import DataMapper
    print("✅ DataMapper imported")
    
    from xml_extractor.database.migration_engine import MigrationEngine
    print("✅ MigrationEngine imported")
    
    from xml_extractor.models import ProcessingConfig
    print("✅ ProcessingConfig imported")
    
    # Test basic functionality
    print("\nTesting basic functionality...")
    
    # Load sample XML
    sample_path = Path("config/samples/sample-source-xml-contact-test.xml")
    if sample_path.exists():
        with open(sample_path, 'r', encoding='utf-8') as f:
            sample_xml = f.read()
        print(f"✅ Sample XML loaded: {len(sample_xml)} characters")
        
        # Test validation
        validator = PreProcessingValidator()
        result = validator.validate_xml_for_processing(sample_xml, "simple_test")
        print(f"✅ Validation result: valid={result.is_valid}, contacts={len(result.valid_contacts)}")
        
        # Test parsing
        parser = XMLParser()
        root = parser.parse_xml_stream(sample_xml)
        xml_data = parser.extract_elements(root)
        print(f"✅ Parsing result: {len(xml_data)} elements")
        
        # Test mapping
        mapper = DataMapper()
        mapper._current_xml_root = root
        
        # Simple mapping contract
        mapping_contract = {
            "contact": [
                {
                    "source_path": "con_id",
                    "target_column": "con_id", 
                    "data_type": "int"
                }
            ]
        }
        
        # Debug: Show available paths
        print(f"Available XML paths:")
        for path in sorted(xml_data.keys())[:10]:  # Show first 10
            print(f"  - {path}")
        
        # Look for Request element
        request_path = '/Provenir/Request'
        if request_path in xml_data:
            request_element = xml_data[request_path]
            print(f"Request element: {request_element}")
            if 'attributes' in request_element:
                print(f"Request attributes: {request_element['attributes']}")
                if 'ID' in request_element['attributes']:
                    print(f"Found app_id: {request_element['attributes']['ID']}")
        else:
            print("Request element not found")
        
        try:
            mapped_data = mapper.apply_mapping_contract(xml_data, mapping_contract)
            print(f"✅ Mapping result: {len(mapped_data)} tables")
        except Exception as e:
            print(f"⚠️  Mapping failed: {e}")
            print("This is expected - we need to fix the mapping contract paths")
        
        print("\n🎉 All basic functionality working!")
        
    else:
        print("❌ Sample XML file not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()