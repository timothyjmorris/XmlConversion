#!/usr/bin/env python3
"""
End-to-end integration test with real database insertion.

This test runs the complete pipeline:
PreProcessingValidator → XMLParser → DataMapper → MigrationEngine

Uses sample-source-xml-contact-test.xml to test the "last valid element" approach
with actual database insertion and validation.
    - parse xml
    - map fields + transform
    - insert into db
"""

import unittest
import logging
import tempfile
import sys
import pyodbc
import json

from pathlib import Path
from datetime import datetime

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.models import ProcessingConfig

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration test with real database insertion."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database and tables."""
        cls.test_db_path = None
        cls.connection_string = None
        # Load mapping contract to get the target schema for qualified table names
        root = Path(__file__).parent.parent.parent
        mapping_contract_path = root / "config" / "mapping_contract.json"
        try:
            with open(mapping_contract_path, 'r', encoding='utf-8') as f:
                contract = json.load(f)
                cls.target_schema = contract.get('target_schema', 'dbo') or 'dbo'
        except Exception:
            # Fallback to dbo if contract cannot be read
            cls.target_schema = 'dbo'

        @classmethod
        def _qualify_table(inner_cls, table_name: str) -> str:
            return f"[{inner_cls.target_schema}].[{table_name}]"

        # Attach helper to class so instance methods can call self._qualify_table(...)
        cls._qualify_table = _qualify_table

        cls.setup_test_database()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database."""
        # Comment out cleanup to leave test data for inspection
        print("Test data left in database for inspection (app_id=443306)")
        # if cls.test_db_path and cls.test_db_path.exists():
        #     try:
        #         cls.test_db_path.unlink()
        #         print(f"Cleaned up test database: {cls.test_db_path}")
        #     except Exception as e:
        #         print(f"Warning: Could not clean up test database: {e}")
    
    @classmethod
    def setup_test_database(cls):
        """Set up real database connection for testing."""
        # Use centralized configuration for database connection
        from xml_extractor.config.config_manager import get_config_manager
        config_manager = get_config_manager()
        cls.connection_string = config_manager.get_database_connection_string()
        
        # Clean up any existing test data once at the beginning
        # Note: cleanup will be done in individual test methods
    
    @classmethod
    def create_test_tables(cls):
        """Create test tables based on our schema (mock implementation)."""
        # Mock implementation - tables are represented as lists in memory
        pass
    
    def setUp(self):
        """Set up test fixtures."""
        # Note: Cleanup moved to setUpClass to preserve data after tests
        
        # Load sample XML
        sample_path = Path(__file__).parent.parent.parent / "config" / "samples" / "sample-source-xml-contact-test.xml"
        if not sample_path.exists():
            self.skipTest("Sample XML file not found")
        
        with open(sample_path, 'r', encoding='utf-8-sig') as f:
            self.sample_xml = f.read()
        
        # Initialize components with real mapping contract
        self.validator = PreProcessingValidator()
        self.parser = XMLParser()
        
        # Initialize DataMapper with the mapping contract path so it loads enum mappings
        mapping_contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract.json"
        self.mapper = DataMapper(mapping_contract_path=str(mapping_contract_path))
        
        self.migration_engine = MigrationEngine(self.connection_string)
    
    def cleanup_test_data(self):
        """Clean up any existing test data to avoid duplicate key errors."""
        try:
            with pyodbc.connect(self.connection_string) as conn:
                cursor = conn.cursor()
                
                # Clean up test app (FK cascade delete)
                cursor.execute(f"DELETE FROM {self._qualify_table('app_base')} WHERE app_id = 443306")
                
                conn.commit()
                print("[CLEANUP] Cleaned up existing test data for app_id 443306")
        except Exception as e:
            print(f"[WARNING] Cleanup warning: {e}")
    
    def test_end_to_end_pipeline(self):
        """Test the complete end-to-end pipeline with database insertion."""
        print("\n" + "="*80)
        print("TESTING END-TO-END PIPELINE WITH DATABASE INSERTION")
        print("="*80)

        # Clean up any existing test data first
        self.cleanup_test_data()

        # Step 1: Validate XML
        print("\n[STEP 1] Validating XML...")
        validation_result = self.validator.validate_xml_for_processing(
            self.sample_xml,
            "integration_test"
        )
        self.assertTrue(validation_result.is_valid, "XML validation should pass")
        self.assertTrue(validation_result.can_process, "XML should be processable")
        self.assertEqual(validation_result.app_id, "443306", "Should extract correct app_id")
        self.assertEqual(len(validation_result.valid_contacts), 2, "Should find 2 valid contacts")
        print(f"[OK] Validation passed: app_id={validation_result.app_id}, contacts={len(validation_result.valid_contacts)}")

        # Step 2: Parse XML
        print("\n[STEP 2] Parsing XML...")
        root = self.parser.parse_xml_stream(self.sample_xml)
        xml_data = self.parser.extract_elements(root)
        self.assertIsNotNone(root, "XML parsing should succeed")
        self.assertGreater(len(xml_data), 0, "Should extract XML elements")
        print(f"[OK] Parsing completed: {len(xml_data)} elements extracted")

        # Step 3: Map data using real contracts
        print("\n[STEP 3] Mapping data using contracts...")
        mapped_data = self.mapper.map_xml_to_database(
            xml_data,
            validation_result.app_id,
            validation_result.valid_contacts,
            root
        )
        self.assertIn("app_base", mapped_data, "Should map app_base data")
        self.assertIn("contact_base", mapped_data, "Should map contact_base data")
        print(f"[OK] Mapping completed: {len(mapped_data)} tables mapped")
        for table_name, records in mapped_data.items():
            print(f"   - {table_name}: {len(records)} records")

        # Step 4: Insert into database
        print("\n[STEP 4] Inserting into database...")
        table_order = [
            "app_base", "app_operational_cc", "app_pricing_cc", "app_transactional_cc", "app_solicited_cc",
            "contact_base", "contact_address", "contact_employment"
        ]
        for table_name in table_order:
            records = mapped_data.get(table_name, [])
            if records:
                enable_identity = table_name in ["app_base", "contact_base"]
                result = self.migration_engine.execute_bulk_insert(records, table_name, enable_identity_insert=enable_identity)
                print(f"[OK] Inserted {result} records into {table_name}")

        # Step 5: Verify database contents
        print("\n[STEP 5] Verifying database contents...")
        self.verify_database_contents()
        print("\n[COMPLETE] END-TO-END PIPELINE TEST COMPLETED SUCCESSFULLY!")
    
    def verify_database_contents(self):
        """Verify the data was inserted correctly using actual table names from contract."""
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            
            # Check app_base table (not "application")
            cursor.execute(f"SELECT COUNT(*) FROM {self._qualify_table('app_base')} WHERE app_id = 443306")
            app_count = cursor.fetchone()[0]
            self.assertEqual(app_count, 1, "Should have 1 app_base record")
            
            cursor.execute(f"SELECT app_id, receive_date FROM {self._qualify_table('app_base')} WHERE app_id = 443306")
            app_record = cursor.fetchone()
            self.assertEqual(app_record[0], 443306, "Should have correct app_id")
            
            print(f"[OK] app_base verified: {app_count} record, app_id={app_record[0]}")
            
            # Check contact_base table (not "contact")
            cursor.execute(f"SELECT COUNT(*) FROM {self._qualify_table('contact_base')} WHERE app_id = 443306")
            contact_count = cursor.fetchone()[0]
            self.assertEqual(contact_count, 2, "Should have 2 contact records")
            
            cursor.execute(f"""
                SELECT con_id, contact_type_enum, first_name 
                FROM {self._qualify_table('contact_base')} 
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
            
            print(f"[OK] Contacts verified: {contact_count} records")
            print(f"   - PR Contact: con_id={pr_contact[0]}, name={pr_contact[2]}")
            print(f"   - AUTHU Contact: con_id={authu_contact[0]}, name={pr_contact[2]}")
            
            # Verify curr_address_only mapping for home_phone and cell_phone on PR contact
            cursor.execute(f"""
                SELECT home_phone, cell_phone 
                FROM {self._qualify_table('contact_base')} 
                WHERE con_id = 738936
            """)
            phone_record = cursor.fetchone()
            home_phone = phone_record[0]
            cell_phone = phone_record[1]
            
            print(f"[OK] Phone fields verified: home_phone='{home_phone}', cell_phone='{cell_phone}'")
            
            # Verify curr_address_only extracts from CURR address
            self.assertIsNotNone(home_phone, "home_phone should not be null")
            self.assertEqual(home_phone.strip(), '5051002300', f"home_phone should be '5051002300' but got '{home_phone}'")
            
            self.assertIsNotNone(cell_phone, "cell_phone should not be null") 
            self.assertEqual(cell_phone.strip(), '5555555555', f"cell_phone should be '5555555555' but got '{cell_phone}'")
            
            # Check app_operational_cc table for calculated fields
            cursor.execute(f"SELECT cb_score_factor_type_1, cb_score_factor_type_2, assigned_to, backend_fico_grade, cb_score_factor_code_1, meta_url, priority_enum, housing_monthly_payment FROM {self._qualify_table('app_operational_cc')} WHERE app_id = 443306")
            operational_record = cursor.fetchone()
            self.assertIsNotNone(operational_record, "Should have app_operational_cc record")
            
            cb_score_factor_type_1 = operational_record[0]
            cb_score_factor_type_2 = operational_record[1]
            assigned_to = operational_record[2]
            backend_fico_grade = operational_record[3]
            cb_score_factor_code_1 = operational_record[4]
            meta_url = operational_record[5]
            priority_enum = operational_record[6]
            housing_monthly_payment = operational_record[7]
            
            print(f"[OK] app_operational_cc verified: cb_score_factor_type_1='{cb_score_factor_type_1}', cb_score_factor_type_2='{cb_score_factor_type_2}'")
            print(f"   - assigned_to='{assigned_to}', backend_fico_grade='{backend_fico_grade}', cb_score_factor_code_1='{cb_score_factor_code_1}'")
            print(f"   - meta_url='{meta_url}', priority_enum={priority_enum}, housing_monthly_payment={housing_monthly_payment}")
            
            # Verify calculated field values based on contract expressions
            # cb_score_factor_type_1 should return 'AJ' based on the complex CASE WHEN logic
            # (adverse_actn1_type_cd is not empty, population_assignment = 'CM', app_receive_date > 2023-10-11)
            self.assertEqual(cb_score_factor_type_1, 'AJ', f"cb_score_factor_type_1 should be 'AJ' but got '{cb_score_factor_type_1}'")
            
            # cb_score_factor_type_2 should return None (NULL in database) when falling through to ELSE
            # The CASE WHEN expression returns '' which gets converted to NULL in the database
            self.assertIsNone(cb_score_factor_type_2, f"cb_score_factor_type_2 should be None (NULL) but got '{cb_score_factor_type_2}'")
            
            # Verify other fields are not null when calculated fields are used
            self.assertIsNotNone(assigned_to, "assigned_to should not be null")
            self.assertEqual(assigned_to, 'test-tacular@testy.com', f"assigned_to should be 'test-tacular@testy.com' but got '{assigned_to}'")
            
            self.assertIsNotNone(backend_fico_grade, "backend_fico_grade should not be null")
            self.assertEqual(backend_fico_grade, 'F', f"backend_fico_grade should be 'F' but got '{backend_fico_grade}'")
            
            self.assertIsNotNone(cb_score_factor_code_1, "cb_score_factor_code_1 should not be null")
            self.assertEqual(cb_score_factor_code_1, 'AA ANYTHIN', f"cb_score_factor_code_1 should be 'AA ANYTHIN' but got '{cb_score_factor_code_1}'")
            
            self.assertIsNotNone(meta_url, "meta_url should not be null")
            self.assertEqual(meta_url, 'meta-bro-url.com', f"meta_url should be 'meta-bro-url.com' but got '{meta_url}'")
            
            self.assertIsNotNone(priority_enum, "priority_enum should not be null")
            self.assertEqual(priority_enum, 80, f"priority_enum should be 80 but got {priority_enum}")
            
            # Verify housing_monthly_payment from last valid PR contact
            self.assertIsNotNone(housing_monthly_payment, "housing_monthly_payment should not be null")
            self.assertEqual(float(housing_monthly_payment), 893.55, f"housing_monthly_payment should be 893.55 but got {housing_monthly_payment}")
            
            # Verify calculated fields in contact_address table
            cursor.execute(f"""
                SELECT ca.con_id, ca.city, ca.months_at_address 
                FROM {self._qualify_table('contact_address')} ca
                INNER JOIN {self._qualify_table('contact_base')} cb ON ca.con_id = cb.con_id
                WHERE cb.app_id = 443306 
                ORDER BY ca.con_id, ca.months_at_address
            """)
            address_records = cursor.fetchall()
            self.assertEqual(len(address_records), 3, "Should have 3 address records")
            
            # Check calculated months_at_address values
            # Expected: months_at_residence + (years_at_residence * 12)
            # Address 1: 11 + (2 * 12) = 35
            # Address 2: 41 + (1 * 12) = 53  
            # Address 3: 3 + (2 * 12) = 27
            expected_months = [35, 53, 27]
            actual_months = [int(record[2]) for record in address_records]
            self.assertEqual(actual_months, expected_months, 
                           f"months_at_address values should be {expected_months} but got {actual_months}")
            
            print(f"[OK] contact_address calculated fields verified: {len(address_records)} records with months_at_address={actual_months}")
            
            # Verify calculated fields in contact_employment table
            cursor.execute(f"""
                SELECT ce.con_id, ce.business_name, ce.monthly_salary, ce.months_at_job 
                FROM {self._qualify_table('contact_employment')} ce
                INNER JOIN {self._qualify_table('contact_base')} cb ON ce.con_id = cb.con_id
                WHERE cb.app_id = 443306 
                ORDER BY ce.con_id
            """)
            employment_records = cursor.fetchall()
            self.assertEqual(len(employment_records), 2, "Should have 2 employment records")
            
            # Check calculated monthly_salary and months_at_job values
            for record in employment_records:
                con_id, business_name, monthly_salary, months_at_job = record
                
                # Verify monthly_salary is not null (CASE WHEN logic based on salary_basis)
                self.assertIsNotNone(monthly_salary, f"monthly_salary should not be null for con_id {con_id}")
                
                # Verify months_at_job is not null (b_months_at_job + b_years_at_job * 12)
                self.assertIsNotNone(months_at_job, f"months_at_job should not be null for con_id {con_id}")
                
                # Check specific expected values based on XML data
                if business_name == 'HOME-STYLE JIVE':
                    # b_salary=120000.656, b_salary_basis_tp_c=ANNUM -> 120000.656 / 12 = 10000.05
                    self.assertAlmostEqual(float(monthly_salary), 10000.05, places=2,
                                         msg=f"monthly_salary for HOME-STYLE JIVE should be ~10000.05 but got {monthly_salary}")
                    # b_months_at_job=6, b_years_at_job=1 -> 6 + (1 * 12) = 18
                    self.assertEqual(int(months_at_job), 18,
                                   f"months_at_job for HOME-STYLE JIVE should be 18 but got {months_at_job}")
                elif business_name == 'LIL BUDDY':
                    # b_salary=4000, b_salary_basis_tp_c=MONTH -> 4000 * 12 = 48000
                    self.assertEqual(float(monthly_salary), 48000.0,
                                   f"monthly_salary for LIL BUDDY should be 48000 but got {monthly_salary}")
                    # b_months_at_job=32, b_years_at_job=1 -> 32 + (1 * 12) = 44
                    self.assertEqual(int(months_at_job), 44,
                                   f"months_at_job for LIL BUDDY should be 44 but got {months_at_job}")
            
            print(f"[OK] contact_employment calculated fields verified: {len(employment_records)} records")
            for record in employment_records:
                print(f"   - {record[1]}: monthly_salary={record[2]}, months_at_job={record[3]}")
    
    def test_curr_address_filtering_logic(self):
        """Test that CURR address filtering works correctly for housing_monthly_payment."""
        print("\n" + "="*80)
        print("TESTING CURR ADDRESS FILTERING LOGIC")
        print("="*80)
        
        # Parse the XML to get the root element
        root = self.parser.parse_xml_stream(self.sample_xml)
        
        # Set the _current_xml_root on the mapper (required for the method to work)
        self.mapper._current_xml_root = root
        
        # Test the _extract_from_last_valid_pr_contact method directly
        from xml_extractor.mapping.data_mapper import FieldMapping
        
        # Create a mapping for housing_monthly_payment
        housing_mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/contact/contact_address",
            xml_attribute="residence_monthly_pymnt",
            target_table="app_operational_cc",
            target_column="housing_monthly_payment",
            data_type="decimal",
            data_length=2,
            mapping_type="last_valid_pr_contact"
        )
        
        # Extract the value using the mapper
        result = self.mapper._extract_from_last_valid_pr_contact(housing_mapping)
        
        # Verify it extracts the CURR address value (893.55), not the PREV address value (empty)
        self.assertIsNotNone(result, "housing_monthly_payment should be extracted")
        self.assertEqual(float(result), 893.55, f"Should extract CURR address value 893.55, got {result}")
        
        # Test with a field that doesn't exist in CURR addresses to verify fallback logic
        # Create a mapping for a non-existent attribute
        nonexistent_mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/contact/contact_address",
            xml_attribute="nonexistent_attribute",
            target_table="app_operational_cc",
            target_column="test_field",
            data_type="string",
            data_length=50,
            mapping_type="last_valid_pr_contact"
        )
        
        nonexistent_result = self.mapper._extract_from_last_valid_pr_contact(nonexistent_mapping)
        self.assertIsNone(nonexistent_result, "Non-existent attribute should return None")
        
        # Test that banking fields (which don't use address filtering) still work
        banking_mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/contact",
            xml_attribute="banking_aba",
            target_table="app_operational_cc",
            target_column="sc_bank_aba",
            data_type="string",
            data_length=9,
            mapping_type="last_valid_pr_contact"
        )

        value = self.mapper._extract_from_last_valid_pr_contact(banking_mapping)
        banking_result = self.mapper._apply_field_transformation(value, banking_mapping)
        self.assertIsNotNone(banking_result, "Banking field should be extracted")
        self.assertEqual(banking_result, "192019207", f"Should extract banking ABA 192019207, got {banking_result}")
    
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
        print("\n[OK] All integration tests passed!")
        print("End-to-end pipeline working correctly with real database insertion.")
    else:
        print("\n[FAIL] Some integration tests failed!")
        print("Review and fix pipeline issues before production use.")
    
    return success


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)