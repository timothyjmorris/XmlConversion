"""
Test validation using the real sample XML with ghost nodes and edge cases.

This test uses the actual `sample-source-xml-contact-test.xml` file to validate
our system handles real-world edge cases correctly
"""

import unittest
import logging
import sys

from pathlib import Path
# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper


class TestRealSampleXMLValidation(unittest.TestCase):
    """Test validation using real sample XML with edge cases."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clean up any existing test data first (app_id 443306) to avoid conflicts
        self.cleanup_test_data()
        
        self.validator = PreProcessingValidator()
        self.parser = XMLParser()
        self.mapper = DataMapper()
        
        # Load real sample XML with proper UTF-8 encoding to handle BOM correctly
        sample_path = Path(__file__).parent.parent.parent / "config" / "samples" / "sample-source-xml-contact-test.xml"
        if sample_path.exists():
            with open(sample_path, 'r', encoding='utf-8') as f:
                self.real_sample_xml = f.read()
        else:
            self.skipTest("Real sample XML file not found")
    
    def cleanup_test_data(self):
        """Clean up any existing test data to avoid conflicts."""
        try:
            # Use centralized configuration for database connection
            from xml_extractor.config.config_manager import get_config_manager
            config_manager = get_config_manager()
            connection_string = config_manager.get_database_connection_string()
            
            import pyodbc
            with pyodbc.connect(connection_string) as conn:
                cursor = conn.cursor()
                
                # Only delete from app_base - cascade will handle the rest
                cursor.execute("DELETE FROM app_base WHERE app_id = 443306")
                
                conn.commit()
                print("INFO: Cleaned up existing test data for app_id 443306")
        except Exception as e:
            print(f"  Cleanup warning: {e}")
    
    def test_real_sample_xml_validation(self):
        """Test validation of real sample XML with edge cases."""
        print("\n" + "="*60)
        print("TESTING REAL SAMPLE XML VALIDATION")
        print("="*60)
        
        # Validate the real sample XML
        result = self.validator.validate_xml_for_processing(
            self.real_sample_xml, 
            "sample-source-xml-contact-test"
        )
        
        # Print validation results
        print(f"\nValidation Results:")
        print(f"  Is Valid: {result.is_valid}")
        print(f"  Can Process: {result.can_process}")
        print(f"  App ID: {result.app_id}")
        print(f"  Valid Contacts: {len(result.valid_contacts)}")
        print(f"  Validation Errors: {len(result.validation_errors)}")
        print(f"  Validation Warnings: {len(result.validation_warnings)}")
        
        # Print errors
        if result.validation_errors:
            print(f"\nValidation Errors:")
            for error in result.validation_errors:
                print(f"  - {error}")
        
        # Print warnings
        if result.validation_warnings:
            print(f"\nValidation Warnings:")
            for warning in result.validation_warnings[:10]:  # Show first 10
                print(f"  - {warning}")
            if len(result.validation_warnings) > 10:
                print(f"  ... and {len(result.validation_warnings) - 10} more warnings")
        
        # Print skipped elements
        total_skipped = sum(len(items) for items in result.skipped_elements.values())
        if total_skipped > 0:
            print(f"\nSkipped Elements ({total_skipped} total):")
            for element_type, items in result.skipped_elements.items():
                if items:
                    print(f"  {element_type}: {len(items)} skipped")
                    for item in items[:3]:  # Show first 3
                        print(f"    - {item}")
                    if len(items) > 3:
                        print(f"    ... and {len(items) - 3} more")
        
        # Analyze valid contacts
        if result.valid_contacts:
            print(f"\nValid Contacts Found:")
            for i, contact in enumerate(result.valid_contacts):
                con_id = contact.get('con_id')
                role = contact.get('ac_role_tp_c')
                first_name = contact.get('first_name', 'N/A')
                print(f"  {i+1}. con_id={con_id}, role={role}, name={first_name}")
        
        # Expected results based on manual analysis of the XML
        self.assertIsNotNone(result.app_id, "Should extract app_id from Request/@ID")
        self.assertEqual(result.app_id, "443306", "Should extract correct app_id")
        
        # Should have valid contacts (at least the PR contact with con_id="738936")
        self.assertGreater(len(result.valid_contacts), 0, "Should find at least one valid contact")
        
        # Should be able to process despite warnings
        self.assertTrue(result.can_process, "Should be able to process despite edge cases")
        
        print(f"\nReal sample XML validation completed successfully!")
    
    def test_expected_edge_cases_in_sample(self):
        """Test that we correctly identify expected edge cases in the sample XML."""
        print("\n" + "="*60)
        print("TESTING EXPECTED EDGE CASES")
        print("="*60)
        
        result = self.validator.validate_xml_for_processing(
            self.real_sample_xml, 
            "edge_case_analysis"
        )
        
        # Expected edge cases based on manual XML analysis:
        expected_issues = [
            "ghost contact with empty con_id",
            "contact with invalid ac_role_tp_c='WEIRD'", 
            "contact with ac_role_tp_c='AUTHU' (invalid)",
            "address missing address_tp_c",
            "employment missing employment_tp_c"
        ]
        
        # Check that we have warnings (indicating edge cases were caught)
        self.assertGreater(len(result.validation_warnings), 0, 
                          "Should have warnings for edge cases")
        
        # Check that we have skipped elements
        total_skipped = sum(len(items) for items in result.skipped_elements.values())
        self.assertGreater(total_skipped, 0, 
                          "Should have skipped some invalid elements")
        
        # Verify specific edge cases are handled
        warnings_text = " ".join(result.validation_warnings).lower()
        
        # Should warn about contacts with issues
        contact_warnings = [w for w in result.validation_warnings if 'contact' in w.lower()]
        self.assertGreater(len(contact_warnings), 0, 
                          "Should have warnings about problematic contacts")
        
        # Should warn about invalid contact roles
        role_warnings = [w for w in result.validation_warnings if 'ac_role_tp_c' in w.lower()]
        self.assertGreater(len(role_warnings), 0,
                          "Should have warnings about invalid ac_role_tp_c values")
        
        # Should warn about missing con_id
        con_id_warnings = [w for w in result.validation_warnings if 'con_id' in w.lower()]
        self.assertGreater(len(con_id_warnings), 0,
                          "Should have warnings about missing con_id attributes")
        
        print(f"  Edge case detection working correctly!")
        print(f"   - Contact warnings: {len(contact_warnings)}")
        print(f"   - Role warnings: {len(role_warnings)}")
        print(f"   - Con_id warnings: {len(con_id_warnings)}")
    
    def test_graceful_degradation_behavior(self):
        """Test that graceful degradation works correctly with real sample."""
        print("\n" + "="*60)
        print("TESTING GRACEFUL DEGRADATION")
        print("="*60)
        
        result = self.validator.validate_xml_for_processing(
            self.real_sample_xml,
            "graceful_degradation_test"
        )
        
        # Key test: Should be able to process despite having invalid elements
        self.assertTrue(result.can_process, 
                       "Should be able to process despite invalid child elements")
        
        # Should have valid contacts even with some invalid ones
        self.assertGreater(len(result.valid_contacts), 0,
                          "Should have at least one valid contact")
        
        # Should have warnings but not errors (graceful degradation)
        self.assertGreater(len(result.validation_warnings), 0,
                          "Should have warnings about skipped elements")
        
        # Should not have critical errors that prevent processing
        critical_errors = [e for e in result.validation_errors if 'CRITICAL' in e]
        self.assertEqual(len(critical_errors), 0,
                        "Should not have critical errors with valid app_id and contacts")
        
        print(f"   Graceful degradation working correctly!")
        print(f"   - Can process: {result.can_process}")
        print(f"   - Valid contacts: {len(result.valid_contacts)}")
        print(f"   - Warnings: {len(result.validation_warnings)}")
        print(f"   - Critical errors: {len(critical_errors)}")
    
    def test_performance_with_large_xml(self):
        """Test validation performance with the large real sample XML."""
        import time
        
        print("\n" + "="*60)
        print("TESTING VALIDATION PERFORMANCE")
        print("="*60)
        
        # Measure validation time
        start_time = time.time()
        result = self.validator.validate_xml_for_processing(
            self.real_sample_xml,
            "performance_test"
        )
        validation_time = time.time() - start_time
        
        # Performance expectations
        max_validation_time = 5.0  # 5 seconds max for validation
        
        self.assertLess(validation_time, max_validation_time,
                       f"Validation should complete in under {max_validation_time}s")
        
        print(f"  Performance test passed!")
        print(f"   - Validation time: {validation_time:.3f} seconds")
        print(f"   - XML size: {len(self.real_sample_xml):,} characters")
        print(f"   - Processing rate: {len(self.real_sample_xml)/validation_time:,.0f} chars/sec")


def run_real_sample_tests():
    """Run all real sample XML tests."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRealSampleXMLValidation)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*60)
    print("REAL SAMPLE XML TEST SUMMARY")
    print("="*60)
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
        print("\nAll real sample XML tests passed!")
        print("System correctly handles real-world edge cases and ghost nodes.")
    else:
        print("\nSome real sample XML tests failed!")
        print("Review and fix validation logic before processing production data.")
    
    return success


if __name__ == '__main__':
    success = run_real_sample_tests()
    sys.exit(0 if success else 1)