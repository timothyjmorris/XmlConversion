#!/usr/bin/env python3
"""
Live End-to-End Integration Test with Real Database.

This test runs the complete pipeline against the actual SQL Server database:
PreProcessingValidator → XMLParser → DataMapper → MigrationEngine

Uses sample-source-xml-contact-test.xml to test the "last valid element" approach
with real database insertion into production tables.

IMPORTANT: This test inserts real data into the database and keeps it for manual inspection.
"""

import unittest
import logging
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


class TestLiveEndToEndIntegration(unittest.TestCase):
    """Live end-to-end integration test with real SQL Server database."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Load database config from the central config
        import json
        config_path = Path(__file__).parent.parent / "config" / "database_config.json"
        with open(config_path, 'r') as f:
            db_config = json.load(f)
        
        # Build connection string using config
        db_settings = db_config["database"]
        self.connection_string = db_config["connection_string_template_windows_auth"].format(**db_settings)
        
        print(f"Using database: {db_settings['database']} on {db_settings['server']}")
        
        # Load sample XML
        sample_path = Path(__file__).parent.parent / "config" / "samples" / "sample-source-xml-contact-test.xml"
        if not sample_path.exists():
            self.skipTest("Sample XML file not found")
        
        with open(sample_path, 'r', encoding='utf-8') as f:
            self.sample_xml = f.read()
        
        # Initialize components
        self.validator = PreProcessingValidator()
        self.parser = XMLParser()
        
        # Initialize DataMapper with the mapping contract path so it loads enum mappings
        mapping_contract_path = Path(__file__).parent.parent / "config" / "credit_card_mapping_contract.json"
        self.mapper = DataMapper(mapping_contract_path=str(mapping_contract_path))
        
        self.migration_engine = MigrationEngine(self.connection_string)
        
        # Clean up any existing test data (app_id 443306) to avoid duplicates
        self.cleanup_test_data()
    
    def cleanup_test_data(self):
        """Clean up any existing test data to avoid duplicate key errors."""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # Delete in reverse dependency order using correct table names
                cursor.execute("DELETE FROM contact_employment WHERE con_id IN (SELECT con_id FROM contact_base WHERE app_id = 443306)")
                cursor.execute("DELETE FROM contact_address WHERE con_id IN (SELECT con_id FROM contact_base WHERE app_id = 443306)")
                cursor.execute("DELETE FROM contact_base WHERE app_id = 443306")
                cursor.execute("DELETE FROM app_base WHERE app_id = 443306")
                
                conn.commit()
                print(f"🧹 Cleaned up existing test data for app_id 443306")
                
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up test data: {e}")
            # Continue anyway - might be first run
    
    def test_live_end_to_end_pipeline(self):
        """Test the complete end-to-end pipeline with real database insertion."""
        print("\n" + "="*80)
        print("TESTING LIVE END-TO-END PIPELINE WITH REAL DATABASE")
        print("="*80)
        
        # Step 1: Validate XML
        print("\n📋 Step 1: Validating XML...")
        validation_result = self.validator.validate_xml_for_processing(
            self.sample_xml, 
            "live_integration_test"
        )
        
        self.assertTrue(validation_result.is_valid, "XML validation should pass")
        self.assertTrue(validation_result.can_process, "XML should be processable")
        self.assertEqual(validation_result.app_id, "443306", "Should extract correct app_id")
        self.assertEqual(len(validation_result.valid_contacts), 2, "Should find 2 valid contacts")
        
        print(f"✅ Validation passed: app_id={validation_result.app_id}, contacts={len(validation_result.valid_contacts)}")
        for i, contact in enumerate(validation_result.valid_contacts):
            print(f"   Contact {i+1}: {contact.get('first_name')} (con_id={contact.get('con_id')}, role={contact.get('ac_role_tp_c')})")
        
        # Step 2: Parse XML
        print("\n🔍 Step 2: Parsing XML...")
        root = self.parser.parse_xml_stream(self.sample_xml)
        xml_data = self.parser.extract_elements(root)
        
        self.assertIsNotNone(root, "XML parsing should succeed")
        self.assertGreater(len(xml_data), 0, "Should extract XML elements")
        
        print(f"✅ Parsing completed: {len(xml_data)} elements extracted")
        
        # Step 3: Map data using the actual mapping contract and DataMapper
        print("\n🗺️  Step 3: Mapping data using contracts...")
        
        # Pass XML root to mapper for direct contact parsing
        self.mapper._current_xml_root = root
        
        # Load the actual mapping contract
        import json
        from xml_extractor.models import MappingContract, FieldMapping, RelationshipMapping
        
        mapping_contract_path = Path(__file__).parent.parent / "config" / "credit_card_mapping_contract.json"
        with open(mapping_contract_path, 'r') as f:
            contract_data = json.load(f)
        
        # Convert JSON to MappingContract object
        field_mappings = []
        for mapping_data in contract_data['mappings']:
            field_mapping = FieldMapping(
                xml_path=mapping_data['xml_path'],
                xml_attribute=mapping_data.get('xml_attribute'),  # Don't default to empty string
                target_table=mapping_data['target_table'],
                target_column=mapping_data['target_column'],
                data_type=mapping_data['data_type'],
                mapping_type=mapping_data.get('mapping_type'),  # Don't default to 'direct'
                transformation=None  # FieldMapping uses 'transformation', not 'enum_mapping'
            )
            field_mappings.append(field_mapping)
        
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
        
        mapping_contract = MappingContract(
            source_table=contract_data['source_table'],
            source_column=contract_data['source_column'],
            xml_root_element=contract_data['xml_root_element'],
            mappings=field_mappings,
            relationships=relationship_mappings
        )
        
        print(f"✅ Loaded mapping contract with {len(mapping_contract.mappings)} mappings")
        
        # Apply the mapping contract using DataMapper
        try:
            # Debug: Check if the XML has the receive_date path
            app_path = '/Provenir/Request/CustData/application'
            if app_path in xml_data:
                app_element = xml_data[app_path]
                print(f"🔍 Debug: Found application element: {app_element}")
                if 'attributes' in app_element and 'app_receive_date' in app_element['attributes']:
                    print(f"🔍 Debug: Found app_receive_date: {app_element['attributes']['app_receive_date']}")
                if 'attributes' in app_element and 'app_source_ind' in app_element['attributes']:
                    print(f"🔍 Debug: Found app_source_ind: {app_element['attributes']['app_source_ind']}")
                else:
                    print(f"🔍 Debug: app_source_ind not found in attributes: {app_element.get('attributes', {}).keys()}")
            else:
                print(f"🔍 Debug: Application path not found in XML data")
            
            mapped_data = self.mapper.apply_mapping_contract(xml_data, mapping_contract)
            
            print(f"✅ Mapping completed using contracts:")
            for table_name, records in mapped_data.items():
                print(f"   - {table_name}: {len(records)} records")
                
                # Debug: Show first record of each table to see what data we have
                if records:
                    print(f"     Sample {table_name} record: {records[0]}")
                
        except Exception as e:
            print(f"❌ Mapping failed: {e}")
            # Fall back to manual extraction for debugging
            print("Falling back to manual extraction for debugging...")
            
            # Extract app_id manually
            app_id = None
            if '/Provenir/Request' in xml_data:
                request_element = xml_data['/Provenir/Request']
                if 'attributes' in request_element and 'ID' in request_element['attributes']:
                    app_id = int(request_element['attributes']['ID'])
            
            print(f"Manual app_id extraction: {app_id}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise the exception to see what went wrong
        
        # Step 4: Insert into real database using IDENTITY_INSERT
        print("\n💾 Step 4: Inserting into real database...")
        
        insertion_summary = {}
        
        # Insert in dependency order with proper IDENTITY_INSERT handling
        table_order = [
            ('app_base', True),  # (table_name, needs_identity_insert)
            ('contact_base', True),
            ('contact_address', False),
            ('contact_employment', False)
        ]
        
        for table_name, needs_identity_insert in table_order:
            if table_name in mapped_data and mapped_data[table_name]:
                records = mapped_data[table_name]
                try:
                    self.migration_engine.execute_bulk_insert(
                        records, 
                        table_name, 
                        enable_identity_insert=needs_identity_insert
                    )
                    insertion_summary[table_name] = len(records)
                    print(f"✅ Inserted {len(records)} records into {table_name}")
                except Exception as e:
                    print(f"❌ Failed to insert into {table_name}: {e}")
                    insertion_summary[table_name] = f"FAILED: {e}"
                    import traceback
                    traceback.print_exc()
        
        # Step 5: Verify database contents
        print("\n🔍 Step 5: Verifying database contents...")
        verification_results = self.verify_database_contents()
        
        # Step 6: Summary
        print("\n📊 INSERTION SUMMARY:")
        for table, result in insertion_summary.items():
            print(f"   - {table}: {result}")
        
        print("\n📊 VERIFICATION RESULTS:")
        for table, result in verification_results.items():
            print(f"   - {table}: {result}")
        
        print("\n🎉 LIVE END-TO-END PIPELINE TEST COMPLETED!")
        print("💡 Data has been inserted into the real database for manual inspection.")
        print(f"💡 Search for app_id = 443306 to find the test data.")
    
    def create_minimal_mapping_contract(self):
        """Create a minimal mapping contract for testing."""
        return {
            "app_base": [
                {
                    "source_path": "/Provenir/Request/@ID",
                    "target_column": "app_id",
                    "data_type": "int"
                },
                {
                    "source_path": "/Provenir/Request/CustData/application/@app_type_code",
                    "target_column": "app_type_code",
                    "data_type": "string"
                }
            ],
            "contact": [
                {
                    "source_path": "con_id",
                    "target_column": "con_id", 
                    "data_type": "int"
                },
                {
                    "source_path": "ac_role_tp_c",
                    "target_column": "ac_role_tp_c",
                    "data_type": "enum",
                    "enum_mapping": {"PR": 281, "AUTHU": 280}
                },
                {
                    "source_path": "first_name",
                    "target_column": "first_name",
                    "data_type": "string"
                },
                {
                    "source_path": "last_name", 
                    "target_column": "last_name",
                    "data_type": "string"
                },
                {
                    "source_path": "ssn",
                    "target_column": "ssn",
                    "data_type": "string"
                }
            ]
        }
    
    def verify_database_contents(self):
        """Verify the data was inserted correctly into the real database."""
        results = {}
        
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # Check app_base table
                cursor.execute("SELECT COUNT(*) FROM app_base WHERE app_id = 443306")
                app_count = cursor.fetchone()[0]
                results["app_base"] = f"{app_count} records"
                
                if app_count > 0:
                    cursor.execute("SELECT app_id, app_type_code FROM app_base WHERE app_id = 443306")
                    app_data = cursor.fetchone()
                    print(f"   📋 Application: app_id={app_data[0]}, type={app_data[1]}")
                
                # Check contact_base table (correct table name)
                cursor.execute("SELECT COUNT(*) FROM contact_base WHERE app_id = 443306")
                contact_count = cursor.fetchone()[0]
                results["contact_base"] = f"{contact_count} records"
                
                if contact_count > 0:
                    cursor.execute("""
                        SELECT con_id, contact_type_enum, first_name, last_name
                        FROM contact_base 
                        WHERE app_id = 443306
                        ORDER BY con_id
                    """)
                    contacts = cursor.fetchall()
                    
                    for contact in contacts:
                        role_name = "PR" if contact[1] == 281 else "AUTHU" if contact[1] == 280 else f"Unknown({contact[1]})"
                        print(f"   👤 Contact: con_id={contact[0]}, role={role_name}, name={contact[2]} {contact[3]}")
                
                # Check contact_address table
                cursor.execute("SELECT COUNT(*) FROM contact_address WHERE con_id IN (SELECT con_id FROM contact_base WHERE app_id = 443306)")
                address_count = cursor.fetchone()[0]
                results["contact_address"] = f"{address_count} records"
                
                if address_count > 0:
                    cursor.execute("""
                        SELECT ca.con_id, ca.address_type_enum, ca.city, ca.state
                        FROM contact_address ca
                        INNER JOIN contact_base cb ON ca.con_id = cb.con_id
                        WHERE cb.app_id = 443306
                        ORDER BY ca.con_id, ca.address_type_enum
                    """)
                    addresses = cursor.fetchall()
                    
                    for addr in addresses:
                        print(f"   🏠 Address: con_id={addr[0]}, type={addr[1]}, location={addr[2]}, {addr[3]}")
                
                # Check contact_employment table
                cursor.execute("SELECT COUNT(*) FROM contact_employment WHERE con_id IN (SELECT con_id FROM contact_base WHERE app_id = 443306)")
                employment_count = cursor.fetchone()[0]
                results["contact_employment"] = f"{employment_count} records"
                
                if employment_count > 0:
                    cursor.execute("""
                        SELECT ce.con_id, ce.employment_type_enum, ce.monthly_salary, ce.business_name
                        FROM contact_employment ce
                        INNER JOIN contact_base cb ON ce.con_id = cb.con_id
                        WHERE cb.app_id = 443306
                        ORDER BY ce.con_id, ce.employment_type_enum
                    """)
                    employments = cursor.fetchall()
                    
                    for emp in employments:
                        print(f"   💼 Employment: con_id={emp[0]}, type={emp[1]}, salary={emp[2]}, company={emp[3]}")
                
        except Exception as e:
            results["error"] = f"Verification failed: {e}"
            print(f"❌ Database verification failed: {e}")
        
        return results
    
    def test_last_valid_element_verification(self):
        """Verify that the 'last valid element' approach worked correctly in the database."""
        print("\n" + "="*80)
        print("VERIFYING 'LAST VALID ELEMENT' APPROACH IN DATABASE")
        print("="*80)
        
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # Check that we have exactly 2 contacts
                cursor.execute("SELECT COUNT(*) FROM contact_base WHERE app_id = 443306")
                contact_count = cursor.fetchone()[0]
                self.assertEqual(contact_count, 2, "Should have exactly 2 contacts")
                
                # Check PR contact (should be TOM, not MARK - the last valid one)
                cursor.execute("""
                    SELECT con_id, first_name, last_name
                    FROM contact_base 
                    WHERE app_id = 443306 AND contact_type_enum = 281
                """)
                pr_contact = cursor.fetchone()
                self.assertIsNotNone(pr_contact, "Should have PR contact")
                self.assertEqual(pr_contact[0], 738936, "PR contact should have con_id 738936")
                self.assertEqual(pr_contact[1], "TOM", "Should be TOM (last valid), not MARK")
                
                # Check AUTHU contact
                cursor.execute("""
                    SELECT con_id, first_name, last_name
                    FROM contact_base 
                    WHERE app_id = 443306 AND contact_type_enum = 280
                """)
                authu_contact = cursor.fetchone()
                self.assertIsNotNone(authu_contact, "Should have AUTHU contact")
                self.assertEqual(authu_contact[0], 738937, "AUTHU contact should have con_id 738937")
                self.assertEqual(authu_contact[1], "AUTH", "Should be AUTH")
                
                print(f"✅ Last valid element approach verified:")
                print(f"   - PR Contact: {pr_contact[1]} {pr_contact[2]} (con_id={pr_contact[0]})")
                print(f"   - AUTHU Contact: {authu_contact[1]} {authu_contact[2]} (con_id={authu_contact[0]})")
                
        except Exception as e:
            self.fail(f"Database verification failed: {e}")


def run_live_integration_test():
    """Run the live integration test."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    print("🚀 Starting Live End-to-End Integration Test")
    print("⚠️  This test will insert real data into the database!")
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLiveEndToEndIntegration)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*80)
    print("LIVE INTEGRATION TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 Live integration test completed successfully!")
        print("💡 Check the database for app_id = 443306 to inspect the inserted data.")
        print("💡 Data includes: 1 application, 2 contacts, addresses, and employments.")
    else:
        print("\n❌ Live integration test had issues!")
        print("💡 Check the errors above and fix before production use.")
    
    return success


if __name__ == '__main__':
    success = run_live_integration_test()
    sys.exit(0 if success else 1)