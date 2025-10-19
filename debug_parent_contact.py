#!/usr/bin/env python3
"""Debug parent contact element."""

from xml_extractor.parsing.xml_parser import XMLParser
from pathlib import Path

# Load sample XML
sample_path = Path('config/samples/sample-source-xml-contact-test.xml')
with open(sample_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

# Parse XML
parser = XMLParser()
root = parser.parse_xml_stream(xml_content)
xml_data = parser.extract_elements(root)

# Check the parent contact element
parent_path = '/Provenir/Request/CustData/application/contact'
parent_element = xml_data.get(parent_path)

print(f'Parent element found: {parent_element is not None}')
if parent_element:
    print(f'Parent element type: {type(parent_element)}')
    if isinstance(parent_element, dict):
        print(f'Parent element keys: {list(parent_element.keys())}')
        if 'attributes' in parent_element:
            attrs = parent_element['attributes']
            print(f'Parent attributes: {attrs}')
            print(f'con_id in attributes: {"con_id" in attrs}')
            if 'con_id' in attrs:
                print(f'con_id value: {attrs["con_id"]}')

# Also check all contact paths
print('\nAll contact-related paths:')
for path in sorted(xml_data.keys()):
    if '/contact' in path:
        element = xml_data[path]
        if isinstance(element, dict) and 'attributes' in element:
            attrs = element['attributes']
            con_id = attrs.get('con_id')
            print(f'{path}: con_id={con_id}')