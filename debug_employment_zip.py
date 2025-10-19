#!/usr/bin/env python3
"""Debug employment zip field."""

import xml.etree.ElementTree as ET
from pathlib import Path

# Load sample XML
sample_path = Path('config/samples/sample-source-xml-contact-test.xml')
with open(sample_path, 'r', encoding='utf-8') as f:
    xml_content = f.read()

root = ET.fromstring(xml_content)

# Find the TOM contact and check its employment elements
tom_contact = None
for contact in root.findall('.//contact'):
    if contact.get('con_id') == '738936' and contact.get('first_name') == 'TOM':
        tom_contact = contact
        break

if tom_contact:
    employments = tom_contact.findall('contact_employment')
    print(f'TOM has {len(employments)} employment elements:')
    for i, emp in enumerate(employments):
        attrs = dict(emp.attrib)
        print(f'  Employment {i+1}:')
        for key, value in attrs.items():
            if 'zip' in key.lower():
                print(f'    {key} = {value}')
        b_zip = attrs.get('b_zip', 'NOT FOUND')
        print(f'    b_zip = {b_zip}')
        print()