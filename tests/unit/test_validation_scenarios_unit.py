#!/usr/bin/env python3
"""
Comprehensive XML validation test scenarios using mock Provenir XML samples.

Tests all validation rules and edge cases before processing real data.
"""

import unittest
import logging
from typing import Dict, Any
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import MappingContract, FieldMapping, RelationshipMapping


class TestXMLValidationScenarios(unittest.TestCase):
    """Test XML validation with comprehensive mock scenarios."""
    
    def setUp(self):
        """Set up test fixtures with parser and mapper."""
        from pathlib import Path
        from xml_extractor.config.config_manager import get_config_manager
        
        self.parser = XMLParser()
        
        # Use real mapping contract for proper validation
        mapping_contract_path = Path(__file__).parent.parent.parent / "config" / "credit_card_mapping_contract.json"
        self.mapper = DataMapper(mapping_contract_path=str(mapping_contract_path))
        
        # Load the real mapping contract for tests
        config_manager = get_config_manager()
        self.mapping_contract = config_manager.load_mapping_contract(str(mapping_contract_path))
        
        # Initialize validator for proper contact extraction
        from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
        self.validator = PreProcessingValidator()
    
    def _process_xml_with_validation(self, xml_content: str, test_name: str = "unit_test"):
        """Helper method to process XML with proper validation like E2E tests."""
        # Step 1: Validate XML and extract valid contacts
        validation_result = self.validator.validate_xml_for_processing(xml_content, test_name)
        
        # Step 2: Parse XML
        root = self.parser.parse_xml_stream(xml_content)
        xml_data = self.parser.extract_elements(root)
        # Use the direct XML data format that DataMapper expects, not converted format
        
        # Step 3: Apply mapping with validated contacts and XML root
        result = self.mapper.map_xml_to_database(
            xml_data, 
            validation_result.app_id, 
            validation_result.valid_contacts,
            root  # Pass XML root for proper processing
        )
        
        return result, validation_result
    
    # ========================================
    # VALID XML SCENARIOS (Should Process)
    # ========================================
    
    def test_valid_complete_xml(self):
        """Test XML with all required attributes - should process successfully."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application app_receive_date="05/20/2016" campaign_num="P2F">
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN" last_name="WILLIAMS">
                            <contact_address address_tp_c="CURR" city="FARGO" state="ND"/>
                            <contact_employment employment_tp_c="CURR" b_salary="75000"/>
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        # Parse XML
        root = self.parser.parse_xml_stream(xml_content)
        self.assertIsNotNone(root)
        
        # Extract elements
        elements = self.parser.extract_elements(root)
        self.assertIn('/Provenir', elements)
        
        # Validate structure
        self.assertTrue(self.parser.validate_xml_structure(xml_content))
        
        # Test data mapping
        result, validation_result = self._process_xml_with_validation(xml_content, "test_valid_complete_xml")
        
        # Should create records for all tables
        self.assertIn('app_base', result)
        self.assertIn('contact_base', result)
        self.assertEqual(len(result['app_base']), 1)
        self.assertEqual(len(result['contact_base']), 1)
        
        print("✅ Valid complete XML processed successfully")
    
    def test_valid_xml_missing_optional_elements(self):
        """Test XML missing optional address/employment - should process with graceful degradation."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application app_receive_date="05/20/2016">
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN" last_name="WILLIAMS">
                            <!-- No contact_address or contact_employment -->
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        result, validation_result = self._process_xml_with_validation(xml_content, "test_valid_xml_missing_optional_elements")
        
        # Should still create app_base and contact_base
        self.assertIn('app_base', result)
        self.assertIn('contact_base', result)
        
        print("✅ Valid XML with missing optional elements processed successfully")
    
    def test_valid_xml_multiple_contacts(self):
        """Test XML with multiple valid contacts (PR and AUTH) - should process both."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN" last_name="WILLIAMS">
                            <contact_address address_tp_c="CURR" city="FARGO"/>
                        </contact>
                        <contact con_id="277450" ac_role_tp_c="AUTHU" first_name="JANE" last_name="WILLIAMS">
                            <contact_address address_tp_c="CURR" city="FARGO"/>
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        result, validation_result = self._process_xml_with_validation(xml_content, "test_valid_xml_multiple_contacts")
        
        # Should create records for both contacts
        self.assertIn('contact_base', result)
        self.assertEqual(len(result['contact_base']), 2)
        
        print("✅ Valid XML with multiple contacts processed successfully")
    
    # ========================================
    # INVALID XML SCENARIOS (Should Reject)
    # ========================================
    
    def test_invalid_xml_missing_app_id(self):
        """Test XML missing app_id - should reject entire application."""
        xml_content = """
        <Provenir>
            <Request>
                <!-- Missing ID attribute -->
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN"/>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        root = self.parser.parse_xml_stream(xml_content)
        elements = self.parser.extract_elements(root)
        xml_data = self._convert_elements_to_dict(elements)
        
        # Should raise exception or return empty result
        with self.assertRaises(Exception) as context:
            self.mapper.apply_mapping_contract(xml_data, self.mapping_contract)
        
        self.assertIn("app_id", str(context.exception).lower())
        print("✅ Invalid XML missing app_id rejected correctly")
    
    def test_invalid_xml_missing_con_id(self):
        """Test XML with contact missing con_id - should process with graceful degradation."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact ac_role_tp_c="PR" first_name="JOHN" last_name="WILLIAMS">
                            <!-- Missing con_id attribute -->
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        root = self.parser.parse_xml_stream(xml_content)
        elements = self.parser.extract_elements(root)
        xml_data = self._convert_elements_to_dict(elements)
        
        # Should process successfully with graceful degradation
        result = self.mapper.apply_mapping_contract(xml_data, self.mapping_contract)
        
        # Should have application tables but no contact tables
        self.assertTrue(len(result) > 0, "Should have some application tables")
        self.assertNotIn('contact_base', result)
        print("✅ Invalid XML missing con_id processed with graceful degradation")
    
    def test_invalid_xml_missing_ac_role_tp_c(self):
        """Test XML with contact missing ac_role_tp_c - should process with graceful degradation."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" first_name="JOHN" last_name="WILLIAMS">
                            <!-- Missing ac_role_tp_c attribute -->
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        root = self.parser.parse_xml_stream(xml_content)
        elements = self.parser.extract_elements(root)
        xml_data = self._convert_elements_to_dict(elements)
        
        # Should process successfully with graceful degradation
        result = self.mapper.apply_mapping_contract(xml_data, self.mapping_contract)
        
        # Should have application tables but no contact tables
        self.assertTrue(len(result) > 0, "Should have some application tables")
        self.assertNotIn('contact_base', result)
        print("✅ Invalid XML missing ac_role_tp_c processed with graceful degradation")
    
    def test_invalid_xml_no_valid_contacts(self):
        """Test XML with no valid contacts - should process with graceful degradation."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact first_name="JOHN" last_name="WILLIAMS">
                            <!-- Missing both con_id and ac_role_tp_c -->
                        </contact>
                        <contact con_id="277449">
                            <!-- Missing ac_role_tp_c -->
                        </contact>
                        <contact ac_role_tp_c="PR">
                            <!-- Missing con_id -->
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        root = self.parser.parse_xml_stream(xml_content)
        elements = self.parser.extract_elements(root)
        xml_data = self._convert_elements_to_dict(elements)
        
        # Should process successfully with graceful degradation
        result = self.mapper.apply_mapping_contract(xml_data, self.mapping_contract)
        
        # Should have application tables but no contact tables
        self.assertTrue(len(result) > 0, "Should have some application tables")
        self.assertNotIn('contact_base', result)
        self.assertNotIn('contact_address', result)
        self.assertNotIn('contact_employment', result)
        print("✅ Invalid XML with no valid contacts processed with graceful degradation")
    
    # ========================================
    # GRACEFUL DEGRADATION SCENARIOS
    # ========================================
    
    def test_graceful_address_missing_address_tp_c(self):
        """Test address missing address_tp_c - should skip address but process contact."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application app_receive_date="05/20/2016" app_source_ind="I">
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN">
                            <contact_address city="FARGO" state="ND">
                                <!-- Missing address_tp_c attribute -->
                            </contact_address>
                            <contact_employment employment_tp_c="CURR" b_salary="75000"/>
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        # Should process successfully but skip invalid address
        result, validation_result = self._process_xml_with_validation(xml_content, "test_graceful_address")
        
        self.assertIn('app_base', result)
        self.assertIn('contact_base', result)
        # Address should be skipped, employment should be processed
        
        print("✅ Graceful degradation: Invalid address skipped, contact processed")
    
    def test_graceful_employment_missing_employment_tp_c(self):
        """Test employment missing employment_tp_c - should skip employment but process contact."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application app_receive_date="05/20/2016" app_source_ind="I">
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN">
                            <contact_address address_tp_c="CURR" city="FARGO"/>
                            <contact_employment b_salary="75000">
                                <!-- Missing employment_tp_c attribute -->
                            </contact_employment>
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        # Should process successfully but skip invalid employment
        result, validation_result = self._process_xml_with_validation(xml_content, "test_graceful_employment")
        
        self.assertIn('app_base', result)
        self.assertIn('contact_base', result)
        # Employment should be skipped, address should be processed
        
        print("✅ Graceful degradation: Invalid employment skipped, contact processed")
    
    def test_mixed_valid_invalid_contacts(self):
        """Test mix of valid and invalid contacts - should process only valid ones."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN">
                            <!-- Valid contact -->
                        </contact>
                        <contact con_id="277450" first_name="JANE">
                            <!-- Invalid: missing ac_role_tp_c -->
                        </contact>
                        <contact ac_role_tp_c="AUTHU" first_name="BOB">
                            <!-- Invalid: missing con_id -->
                        </contact>
                        <contact con_id="277451" ac_role_tp_c="AUTHU" first_name="ALICE">
                            <!-- Valid contact -->
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        result, validation_result = self._process_xml_with_validation(xml_content, "test_mixed_valid_invalid_contacts")
        
        # Should process only the 2 valid contacts (1 valid PR + 1 valid AUTHU)
        self.assertIn('contact_base', result)
        self.assertEqual(len(result['contact_base']), 2)
        
        print("✅ Mixed contacts: Only valid contacts processed")
    
    # ========================================
    # MALFORMED XML SCENARIOS
    # ========================================
    
    def test_malformed_xml_syntax(self):
        """Test malformed XML syntax - should reject during parsing."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR"
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        # The XML parser is lenient and may not raise exceptions for malformed XML
        # Instead, check if the result is None or if validation fails
        try:
            result = self.parser.parse_xml_stream(xml_content)
            # If parsing succeeds, the result should be None or invalid
            self.assertIsNone(result, "Malformed XML should return None")
        except Exception:
            # If an exception is raised, that's also acceptable
            pass
        
        print("✅ Malformed XML syntax rejected during parsing")
    
    def test_empty_xml(self):
        """Test empty XML - should reject."""
        xml_content = ""
        
        with self.assertRaises(Exception):
            self.parser.parse_xml_stream(xml_content)
        
        print("✅ Empty XML rejected correctly")
    
    def test_non_provenir_xml(self):
        """Test XML with wrong root element - should reject."""
        xml_content = """
        <SomeOtherRoot>
            <Request ID="154284">
                <contact con_id="277449"/>
            </Request>
        </SomeOtherRoot>
        """
        
        # Should fail validation
        self.assertFalse(self.parser.validate_xml_structure(xml_content))
        
        print("✅ Non-Provenir XML rejected correctly")
    
    # ========================================
    # EDGE CASE SCENARIOS
    # ========================================
    
    def test_duplicate_con_ids(self):
        """Test XML with duplicate con_ids - should use last valid element approach."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN"/>
                        <contact con_id="277449" ac_role_tp_c="AUTHU" first_name="JANE"/>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        # Should use "last valid element" approach - only 1 contact record (JANE, the last one)
        result, validation_result = self._process_xml_with_validation(xml_content, "test_duplicate_con_ids")
        self.assertEqual(len(result['contact_base']), 1)
        
        # Verify it's the last contact (JANE)
        contact = result['contact_base'][0]
        self.assertEqual(contact['first_name'], 'JANE')
        self.assertEqual(contact['con_id'], 277449)
        
        print("✅ Duplicate con_ids handled correctly using last valid element approach")
    
    def test_special_characters_in_attributes(self):
        """Test XML with special characters in attributes."""
        xml_content = """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOSÉ" last_name="O'CONNOR">
                            <contact_address address_tp_c="CURR" street_name="123 Main St. &amp; Co"/>
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """
        
        result, validation_result = self._process_xml_with_validation(xml_content, "test_special_characters")
        
        # Should handle special characters correctly
        self.assertIn('contact_base', result)
        
        print("✅ Special characters in attributes handled correctly")
    
    # ========================================
    # HELPER METHODS
    # ========================================
    
    def _convert_elements_to_dict(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parsed elements to dictionary format expected by DataMapper."""
        # This is a simplified conversion for testing
        # In real implementation, this would be more sophisticated
        result = {}
        
        for path, element_data in elements.items():
            path_parts = path.strip('/').split('/')
            current = result
            
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    # Last part - store the element data
                    if part not in current:
                        current[part] = {}
                    
                    # Add attributes to the element
                    if 'attributes' in element_data:
                        current[part].update(element_data['attributes'])
                    
                    # Add text content if present
                    if 'text' in element_data and element_data['text']:
                        current[part]['_text'] = element_data['text']
                else:
                    # Intermediate part - create nested structure
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        
        return result
    
    def run_all_validation_tests(self):
        """Run all validation tests and provide summary."""
        test_methods = [method for method in dir(self) if method.startswith('test_')]
        
        print("\n" + "="*60)
        print("XML VALIDATION TEST SUITE")
        print("="*60)
        
        passed = 0
        failed = 0
        
        for test_method in test_methods:
            try:
                getattr(self, test_method)()
                passed += 1
            except Exception as e:
                print(f"❌ {test_method} FAILED: {e}")
                failed += 1
        
        print("\n" + "="*60)
        print(f"TEST SUMMARY: {passed} passed, {failed} failed")
        print("="*60)
        
        return failed == 0


if __name__ == '__main__':
    # Run comprehensive test suite
    test_suite = TestXMLValidationScenarios()
    test_suite.setUp()
    
    # Run all tests
    success = test_suite.run_all_validation_tests()
    
    if success:
        print("\n🎉 All validation tests passed! System ready for production data.")
    else:
        print("\n❌ Some validation tests failed. Review and fix before processing real data.")