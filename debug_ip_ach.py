#!/usr/bin/env python3
"""
Debug script specifically for ip_address and sc_ach_amount issues
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.parsing.xml_parser import XMLParser

def debug_ip_and_ach():
    db_tester = DatabaseConnectionTester()
    success, message = db_tester.test_connection()
    if not success:
        print(f"Connection failed: {message}")
        return

    connection_string = db_tester.build_connection_string()
    migration_engine = MigrationEngine(connection_string)
    parser = XMLParser()

    # Check app_xml_id 8 (contains app_id 207748)
    with migration_engine.get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT xml FROM app_xml WHERE app_id = 8')
        row = cursor.fetchone()
        
        if row:
            xml_content = row[0]
            
            print("=== RAW XML SEARCH ===")
            # Check for IP_address vs ip_address (case sensitivity)
            if 'IP_address=' in xml_content:
                import re
                match = re.search(r'IP_address="([^"]*)"', xml_content)
                if match:
                    print(f"✅ Found IP_address (uppercase): '{match.group(1)}'")
            
            if 'ip_address=' in xml_content:
                import re
                match = re.search(r'ip_address="([^"]*)"', xml_content)
                if match:
                    print(f"✅ Found ip_address (lowercase): '{match.group(1)}'")
            
            # Check for secure_ach_amount
            if 'secure_ach_amount=' in xml_content:
                import re
                match = re.search(r'secure_ach_amount="([^"]*)"', xml_content)
                if match:
                    print(f"✅ Found secure_ach_amount: '{match.group(1)}'")
            else:
                print("❌ secure_ach_amount not found in XML (should be NULL)")
            
            print("\n=== PARSED XML STRUCTURE ===")
            root = parser.parse_xml_stream(xml_content)
            xml_data = parser.extract_elements(root)
            
            # Check application path
            app_path = '/Provenir/Request/CustData/application'
            if app_path in xml_data:
                app_element = xml_data[app_path]
                if isinstance(app_element, dict) and 'attributes' in app_element:
                    attributes = app_element['attributes']
                    print(f"Application attributes count: {len(attributes)}")
                    
                    # Check both case variations
                    for attr_name in ['ip_address', 'IP_address']:
                        if attr_name in attributes:
                            print(f"✅ Found {attr_name}: '{attributes[attr_name]}'")
                    
                    # Check secure_ach_amount
                    if 'secure_ach_amount' in attributes:
                        print(f"✅ Found secure_ach_amount: '{attributes['secure_ach_amount']}'")
                    else:
                        print("❌ secure_ach_amount not in parsed attributes")
                        
                    # Show some attributes for context
                    print(f"Sample attributes: {list(attributes.keys())[:10]}")
        else:
            print("❌ No XML found for app_xml_id 8")

if __name__ == '__main__':
    debug_ip_and_ach()