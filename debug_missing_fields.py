#!/usr/bin/env python3
"""
Debug script to investigate why specific fields are missing from the mapping
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.parsing.xml_parser import XMLParser

def debug_missing_fields():
    # Get connection
    db_tester = DatabaseConnectionTester()
    success, message = db_tester.test_connection()
    if not success:
        print(f"Connection failed: {message}")
        return

    connection_string = db_tester.build_connection_string()
    migration_engine = MigrationEngine(connection_string)
    parser = XMLParser()

    # Check app_id 8 (which contains 207748)
    app_xml_id = 8

    with migration_engine.get_connection() as conn:
        cursor = conn.cursor()
        
        print(f"=== DEBUGGING MISSING FIELDS FOR APP_XML_ID {app_xml_id} ===")
        cursor.execute('SELECT xml FROM app_xml WHERE app_id = ?', (app_xml_id,))
        row = cursor.fetchone()
        
        if row:
            xml_content = row[0]
            
            # Parse XML and extract elements
            root = parser.parse_xml_stream(xml_content)
            xml_data = parser.extract_elements(root)
            
            # Get the actual app_id from XML
            request_path = '/Provenir/Request'
            if request_path in xml_data:
                request_element = xml_data[request_path]
                if isinstance(request_element, dict) and 'attributes' in request_element:
                    xml_app_id = request_element['attributes'].get('ID', 'Unknown')
                    print(f"XML contains app_id: {xml_app_id}")
            
            # Check specific missing fields
            missing_fields = [
                {
                    'name': 'auth_user_is_spouse',
                    'path': '/Provenir/Request/CustData/application/rmts_info',
                    'attribute': 'auth_user_is_spouse'
                },
                {
                    'name': 'ip_address', 
                    'path': '/Provenir/Request/CustData/application',
                    'attribute': 'ip_address'
                },
                {
                    'name': 'secure_ach_amount',
                    'path': '/Provenir/Request/CustData/application', 
                    'attribute': 'secure_ach_amount'
                },
                {
                    'name': 'allocated_credit_line',
                    'path': '/Provenir/Request/CustData/application/contact/app_prod_bcard',
                    'attribute': 'allocated_credit_line'
                },
                {
                    'name': 'credit_line2',
                    'path': '/Provenir/Request/CustData/application/contact/app_prod_bcard', 
                    'attribute': 'credit_line2'
                }
            ]
            
            for field in missing_fields:
                print(f"\n--- Checking {field['name']} ---")
                path = field['path']
                attr = field['attribute']
                
                if path in xml_data:
                    element = xml_data[path]
                    print(f"✅ Found path: {path}")
                    
                    if isinstance(element, dict) and 'attributes' in element:
                        attributes = element['attributes']
                        if attr in attributes:
                            value = attributes[attr]
                            print(f"✅ Found attribute {attr}: '{value}' (type: {type(value)})")
                        else:
                            print(f"❌ Attribute {attr} NOT FOUND in path")
                            print(f"Available attributes: {list(attributes.keys())[:10]}")
                    else:
                        print(f"❌ Unexpected element structure: {type(element)}")
                else:
                    print(f"❌ Path {path} NOT FOUND")
                    # Show similar paths
                    similar_paths = [p for p in xml_data.keys() if path.split('/')[-1] in p]
                    if similar_paths:
                        print(f"Similar paths found: {similar_paths[:5]}")
            
            # Also check if we can find these values by searching the raw XML
            print(f"\n--- Raw XML Search ---")
            for field in missing_fields:
                attr = field['attribute']
                if f'{attr}=' in xml_content:
                    # Extract the value
                    import re
                    pattern = f'{attr}="([^"]*)"'
                    match = re.search(pattern, xml_content)
                    if match:
                        value = match.group(1)
                        print(f"✅ Found {attr} in raw XML: '{value}'")
                    else:
                        print(f"⚠️ Found {attr} in raw XML but couldn't extract value")
                else:
                    print(f"❌ {attr} not found in raw XML")
        else:
            print(f"❌ No XML found for app_xml_id {app_xml_id}")

if __name__ == '__main__':
    debug_missing_fields()