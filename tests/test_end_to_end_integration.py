#!/usr/bin/env python3
"""
End-to-end integration test with real database insertion.

This test runs the complete pipeline:
PreProcessingValidator → XMLParser → DataMapper → MigrationEngine

Uses sample-source-xml-contact-test.xml to test the "last valid element" approach
with actual database insertion and validation.
"""

import unittest
import logging
import tempfile
import os
from pathlib import Path
import sys
import pyodbc
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.models import ProcessingConfig


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration test with real database insertion."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database and tables."""
        cls.test_db_path = None
        cls.connection_string = None
        cls.setup_test_database()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        # Comment out cleanup to leave test data for inspection
        print("🔍 Test data left in database for inspection (app_id=443306)")
        # if cls.test_db_path and os.path.exists(cls.test_db_path):
        #     try:
        #         os.remove(cls.test_db_path)
        #         print(f"Cleaned up test database: {cls.test_db_path}")
        #     except Exception as e:
        #         print(f"Warning: Could not clean up test database: {e}")
    
    @classmethod
    def setup_test_database(cls):
        """Set up real database connection for testing."""
        # Use the real database connection string
        cls.connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;Mars_Connection=yes;CharacterSet=UTF-8;"
        print(f"✅ Using real database: XmlConversionDB on localhost\\SQLEXPRESS")
    
    @classmethod
    def create_test_tables(cls):
        """Create test tables based on our schema (mock implementation)."""
        # Mock implementation - tables are represented as lists in memory
        pass
    
    def setUp(self):
        """Set up test fixtures."""
        # Clean up any existing test data (app_id 443306) to avoid duplicates
        self.cleanup_test_data()
        
        # Load sample XML
        sample_path = Path(__file__).parent.parent / "config" / "samples" / "sample-source-xml-contact-test.xml"
        if not sample_path.exists():
            self.skipTest("Sample XML file not found")
        
        with open(sample_path, 'r', encoding='utf-8-sig') as f:
            self.sample_xml = f.read()
        
        # Initialize components with real mapping contract
        self.validator = PreProcessingValidator()
        self.parser = XMLParser()
        
        # Initialize DataMapper with the mapping contract path so it loads enum mappings
        mapping_contract_path = Path(__file__).parent.parent / "config" / "credit_card_mapping_contract.json"
        self.mapper = DataMapper(mapping_contract_path=str(mapping_contract_path))
        
        self.migration_engine = MigrationEngine(self.connection_string)
    
    def cleanup_test_data(self):
        """Clean up any existing test data to avoid duplicate key errors."""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # Only delete from app_base - cascade will handle the rest
                cursor.execute("DELETE FROM app_base WHERE app_id = 443306")
                
                conn.commit()
                print("🧹 Cleaned up existing test data for app_id 443306")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
    
    def test_end_to_end_pipeline(self):
        """Test the complete end-to-end pipeline with database insertion."""
        print("\n" + "="*80)
        print("TESTING END-TO-END PIPELINE WITH DATABASE INSERTION")
        print("="*80)
        
        # Step 1: Validate XML
        print("\n📋 Step 1: Validating XML...")
        validation_result = self.validator.validate_xml_for_processing(
            self.sample_xml, 
            "integration_test"
        )
        
        self.assertTrue(validation_result.is_valid, "XML validation should pass")
        self.assertTrue(validation_result.can_process, "XML should be processable")
        self.assertEqual(validation_result.app_id, "443306", "Should extract correct app_id")
        self.assertEqual(len(validation_result.valid_contacts), 2, "Should find 2 valid contacts")
        
        print(f"✅ Validation passed: app_id={validation_result.app_id}, contacts={len(validation_result.valid_contacts)}")
        
        # Step 2: Parse XML
        print("\n🔍 Step 2: Parsing XML...")
        root = self.parser.parse_xml_stream(self.sample_xml)
        xml_data = self.parser.extract_elements(root)
        
        self.assertIsNotNone(root, "XML parsing should succeed")
        self.assertGreater(len(xml_data), 0, "Should extract XML elements")
        
        print(f"✅ Parsing completed: {len(xml_data)} elements extracted")
        
        # Step 3: Map data using real contracts
        print("\n🗺️  Step 3: Mapping data using contracts...")
        
        # Use the DataMapper's built-in contract loading functionality
        mapped_data = self.mapper.map_xml_to_database(xml_data, validation_result.app_id, validation_result.valid_contacts, root)
        
        self.assertIn("app_base", mapped_data, "Should map app_base data")
        self.assertIn("contact_base", mapped_data, "Should map contact_base data")
        
        print(f"✅ Mapping completed: {len(mapped_data)} tables mapped")
        for table_name, records in mapped_data.items():
            print(f"   - {table_name}: {len(records)} records")
        
        # Step 4: Insert into database
        print("\n💾 Step 4: Inserting into database...")
        
        # Insert in dependency order: app_base first, then related tables
        table_order = ["app_base", "app_operational_cc", "app_pricing_cc", "app_transactional_cc", "app_solicited_cc", "contact_base", "contact_address", "contact_employment"]
        
        for table_name in table_order:
            records = mapped_data.get(table_name, [])
            if records:
                enable_identity = table_name in ["app_base", "contact_base"]  # Tables with identity columns
                result = self.migration_engine.execute_bulk_insert(records, table_name, enable_identity_insert=enable_identity)
                print(f"✅ Inserted {result} records into {table_name}")
        
        # Step 5: Verify database contents
        print("\n🔍 Step 5: Verifying database contents...")
        self.verify_database_contents()
        
        print("\n🎉 END-TO-END PIPELINE TEST COMPLETED SUCCESSFULLY!")
    
    def verify_database_contents(self):
        """Verify the data was inserted correctly using actual table names from contract."""
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            
            # Check app_base table (not "application")
            cursor.execute("SELECT COUNT(*) FROM app_base WHERE app_id = 443306")
            app_count = cursor.fetchone()[0]
            self.assertEqual(app_count, 1, "Should have 1 app_base record")
            
            cursor.execute("SELECT app_id, receive_date FROM app_base WHERE app_id = 443306")
            app_record = cursor.fetchone()
            self.assertEqual(app_record[0], 443306, "Should have correct app_id")
            
            print(f"✅ app_base verified: {app_count} record, app_id={app_record[0]}")
            
            # Check contact_base table (not "contact")
            cursor.execute("SELECT COUNT(*) FROM contact_base WHERE app_id = 443306")
            contact_count = cursor.fetchone()[0]
            self.assertEqual(contact_count, 2, "Should have 2 contact records")
            
            cursor.execute("""
                SELECT con_id, contact_type_enum, first_name 
                FROM contact_base 
                WHERE app_id = 443306
                ORDER BY con_id
            """)
            contacts = cursor.fetchall()
            
            # Verify PR contact (should be TOM - the last valid one)
            pr_contact = [c for c in contacts if c[1] == 281][0]  # 281 = PR
            self.assertEqual(pr_contact[0], 738936, "PR contact should have con_id 738936")
            self.assertEqual(pr_contact[2], "TOM", "PR contact should be TOM (last valid)")
            
            # Verify AUTHU contact
            authu_contact = [c for c in contacts if c[1] == 280][0]  # 280 = AUTHU
            self.assertEqual(authu_contact[0], 738937, "AUTHU contact should have con_id 738937")
            self.assertEqual(authu_contact[2], "AUTH", "AUTHU contact should be AUTH")
            
            print(f"✅ Contacts verified: {contact_count} records")
            print(f"   - PR Contact: con_id={pr_contact[0]}, name={pr_contact[2]}")
            print(f"   - AUTHU Contact: con_id={authu_contact[0]}, name={pr_contact[2]}")
    
    def test_last_valid_element_approach(self):
        """Test that the 'last valid element' approach works correctly."""
        print("\n" + "="*80)
        print("TESTING 'LAST VALID ELEMENT' APPROACH")
        print("="*80)
        
        # Parse and validate
        validation_result = self.validator.validate_xml_for_processing(
            self.sample_xml, 
            "last_valid_test"
        )
        
        # Check that we get the expected contacts
        valid_contacts = validation_result.valid_contacts
        self.assertEqual(len(valid_contacts), 2, "Should have 2 valid contacts")
        
        # Find PR and AUTHU contacts
        pr_contacts = [c for c in valid_contacts if c.get('ac_role_tp_c') == 'PR']
        authu_contacts = [c for c in valid_contacts if c.get('ac_role_tp_c') == 'AUTHU']
        
        self.assertEqual(len(pr_contacts), 1, "Should have 1 PR contact (last valid)")
        self.assertEqual(len(authu_contacts), 1, "Should have 1 AUTHU contact")
        
        # Verify it's the LAST valid PR contact (TOM, not MARK)
        pr_contact = pr_contacts[0]
        self.assertEqual(pr_contact['con_id'], '738936', "PR contact should have con_id 738936")
        self.assertEqual(pr_contact['first_name'], 'TOM', "Should be TOM (last valid), not MARK")
        
        # Verify AUTHU contact
        authu_contact = authu_contacts[0]
        self.assertEqual(authu_contact['con_id'], '738937', "AUTHU contact should have con_id 738937")
        self.assertEqual(authu_contact['first_name'], 'AUTH', "Should be AUTH")
        
        print(f"✅ Last valid element approach working correctly:")
        print(f"   - PR Contact: {pr_contact['first_name']} (con_id={pr_contact['con_id']})")
        print(f"   - AUTHU Contact: {authu_contact['first_name']} (con_id={authu_contact['con_id']})")


def run_integration_tests():
    """Run all integration tests."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestEndToEndIntegration)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 All integration tests passed!")
        print("End-to-end pipeline working correctly with real database insertion.")
    else:
        print("\n❌ Some integration tests failed!")
        print("Review and fix pipeline issues before production use.")
    
    return success


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)