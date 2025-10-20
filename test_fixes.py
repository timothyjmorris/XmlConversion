#!/usr/bin/env python3
"""
Quick test to verify the mapping fixes work
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator

def test_fixes():
    print("Testing mapping fixes...")
    
    # Get connection
    db_tester = DatabaseConnectionTester()
    success, message = db_tester.test_connection()
    if not success:
        print(f"Connection failed: {message}")
        return False

    connection_string = db_tester.build_connection_string()
    migration_engine = MigrationEngine(connection_string)
    
    # Test with app_xml table ID 8 (the one that failed with birth_date)
    with migration_engine.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT xml FROM app_xml WHERE app_id = 8')
        row = cursor.fetchone()
        
        if not row:
            print("No XML found for app_id 8")
            return False
        
        xml_content = row[0]
        
        # Initialize components
        validator = PreProcessingValidator()
        parser = XMLParser()
        mapper = DataMapper('config/credit_card_mapping_contract.json')
        
        print("1. Validating XML...")
        validation_result = validator.validate_xml_for_processing(xml_content, "test_fixes")
        if not validation_result.is_valid:
            print(f"Validation failed: {validation_result.validation_errors}")
            return False
        
        print(f"✅ Validation passed: app_id={validation_result.app_id}")
        
        print("2. Parsing XML...")
        root = parser.parse_xml_stream(xml_content)
        xml_data = parser.extract_elements(root)
        
        print("3. Mapping data...")
        mapped_data = mapper.map_xml_to_database(xml_data, validation_result.app_id, validation_result.valid_contacts, root)
        
        print("4. Checking contact_base data...")
        if 'contact_base' in mapped_data:
            for contact in mapped_data['contact_base']:
                birth_date = contact.get('birth_date')
                print(f"Contact {contact.get('con_id')}: birth_date = {birth_date}")
                if birth_date is None:
                    print("❌ birth_date is still None!")
                    return False
        
        print("5. Testing insertion...")
        # Clean up first
        cursor.execute("DELETE FROM app_base WHERE app_id = ?", (validation_result.app_id,))
        conn.commit()
        
        # Insert in proper order
        table_order = ["app_base", "app_operational_cc", "app_pricing_cc", "app_transactional_cc", "app_solicited_cc", "contact_base", "contact_address", "contact_employment"]
        
        for table_name in table_order:
            records = mapped_data.get(table_name, [])
            if records:
                try:
                    enable_identity = table_name in ["app_base", "contact_base"]
                    result = migration_engine.execute_bulk_insert(records, table_name, enable_identity_insert=enable_identity)
                    print(f"✅ Inserted {result} records into {table_name}")
                except Exception as e:
                    print(f"❌ Failed to insert into {table_name}: {e}")
                    return False
        
        print("✅ All fixes working correctly!")
        return True

if __name__ == '__main__':
    success = test_fixes()
    sys.exit(0 if success else 1)