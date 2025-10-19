#!/usr/bin/env python3
"""Debug contact_address and contact_employment extraction."""

import logging
logging.basicConfig(level=logging.INFO)

from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from pathlib import Path

# Load sample XML
sample_path = Path('config/samples/sample-source-xml-contact-test.xml')
with open(sample_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Parse XML
parser = XMLParser()
root = parser.parse_xml_stream(xml_content)
xml_data = parser.extract_elements(root)

# Initialize DataMapper
mapping_contract_path = Path('config/credit_card_mapping_contract.json')
mapper = DataMapper(mapping_contract_path=str(mapping_contract_path))

# Test mapping
valid_contacts = [
    {'con_id': '738936', 'ac_role_tp_c': 'PR'},
    {'con_id': '738937', 'ac_role_tp_c': 'AUTHU'}
]

print('Testing contact_address extraction:')
print(f'Valid contacts from test: {valid_contacts}')

# Let's also test the PreProcessingValidator to see what it returns
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
validator = PreProcessingValidator()
validation_result = validator.validate_xml_for_processing(xml_content, "debug_test")
print(f'Valid contacts from validator: {validation_result.valid_contacts}')

mapped_data = mapper.map_xml_to_database(xml_data, '443306', validation_result.valid_contacts, root)
print(f'Final result: {len(mapped_data)} tables: {list(mapped_data.keys())}')

# Check if contact_address and contact_employment are in the results
if 'contact_address' in mapped_data:
    print(f'✅ contact_address: {len(mapped_data["contact_address"])} records')
else:
    print('❌ contact_address: NOT FOUND')

if 'contact_employment' in mapped_data:
    print(f'✅ contact_employment: {len(mapped_data["contact_employment"])} records')
else:
    print('❌ contact_employment: NOT FOUND')