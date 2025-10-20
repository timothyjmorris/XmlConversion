#!/usr/bin/env python3
"""
Debug script to check the case normalization issue
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.parsing.xml_parser import XMLParser

def debug_case_issue():
    db_tester = DatabaseConnectionTester()
    success, message = db_tester.test_connection()
    if not success:
        print(f"Connection failed: {message}")
        return

    connection_string = db_tester.build_connection_string()
    migration_engine = MigrationEngine(connection_string)
    parser = XMLParser()

    # Check app_xml_id 8 (the first failing one)
    with migration_engine.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT xml FROM app_xml WHERE app_id = 8')
        row = cursor.fetchone()
        
        if row:
            xml_content = row[0]
            
            print("=== DEBUGGING CASE NORMALIZATION ===")
            
            # Parse XML and check structure
            root = parser.parse_xml_stream(xml_content)
            xml_data = parser.extract_elements(root)
            
            print(f"Available paths: {list(xml_data.keys())[:5]}")
            
            # Check the Request element specifically
            request_path = '/Provenir/Request'
            if request_path in xml_data:
                request_element = xml_data[request_path]
                print(f"Request element type: {type(request_element)}")
                
                if isinstance(request_element, dict):
                    print(f"Request keys: {list(request_element.keys())}")
                    
                    if 'attributes' in request_element:
                        attributes = request_element['attributes']
                        print(f"Attributes count: {len(attributes)}")
                        print(f"First 10 attributes: {list(attributes.keys())[:10]}")
                        
                        # Check for ID variations
                        id_variations = ['id', 'ID', 'Id', 'iD']
                        for variation in id_variations:
                            if variation in attributes:
                                print(f"✅ Found {variation}: '{attributes[variation]}'")
                        
                        # Check if any attribute contains 'id' (case insensitive)
                        id_attrs = [k for k in attributes.keys() if 'id' in k.lower()]
                        if id_attrs:
                            print(f"Attributes containing 'id': {id_attrs}")
            else:
                print(f"❌ Request path not found")
        else:
            print("❌ No XML found for app_xml_id 8")

if __name__ == '__main__':
    debug_case_issue()