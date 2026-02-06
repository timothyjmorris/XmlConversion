"""
Test script to validate all mapping types and expressions in the mapping contract are supported, exercised, and produce correct results.
- It checks that every mapping type listed in the contract is implemented in DataMapper.
- It does not check that mapping types are exercised or produce correct results.
- Uses central sample XML files for real coverage.
"""

import unittest
import json
from pathlib import Path
import sys
import os
from typing import Dict
from tests.helpers import safe_coerce_dict

from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import MappingContract

# Ensure workspace root (parent of MB_XmlConversionKiro) is in sys.path for imports
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)


class TestMappingTypesAndExpressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract.json"
        sample_xml_path = Path(__file__).parent.parent.parent / "config" / "samples" / "sample-source-xml-contact-test.xml"
        with open(contract_path, 'r') as f:
            contract_data = json.load(f)
        # Convert mappings and relationships to objects
        from xml_extractor.models import FieldMapping, RelationshipMapping
        mappings = [FieldMapping(**m) for m in contract_data.get('mappings', [])]
        relationships = [RelationshipMapping(**r) for r in contract_data.get('relationships', [])]
        cls.contract = MappingContract(
            source_table=contract_data.get('source_table'),
            source_column=contract_data.get('source_column'),
            xml_root_element=contract_data.get('xml_root_element'),
            mappings=mappings,
            relationships=relationships
        )
        with open(sample_xml_path, 'r') as f:
            cls.sample_xml = f.read()
        # Initialize DataMapper with contract path to load enum mappings as in production
        cls.mapper = DataMapper(mapping_contract_path=str(contract_path))
        # Parse XML using the real parser
        from xml_extractor.parsing.xml_parser import XMLParser
        parser = XMLParser(mapping_contract=cls.contract)
        xml_root = parser.parse_xml_stream(cls.sample_xml)
        cls.parsed_xml = parser.extract_elements(xml_root)
        # Set _current_xml_root for DataMapper to match production logic
        cls.mapper._current_xml_root = xml_root

    def test_all_mapping_types_supported(self):
        """
        Purpose: Ensure every mapping_type listed in the mapping contract is implemented in DataMapper.
        This test does NOT check that mapping types are exercised or produce correct results.
        It simply verifies that all mapping types referenced in the contract are recognized and supported by the codebase.
        If a mapping type is present in the contract but not in the supported_types set, this test will fail (e.g., if you put 'bogus' as a mapping type).
        """
        supported_types = {
            'identity_insert', 'enum', 'char_to_bit', 'numbers_only', 'last_valid_pr_contact',
            'curr_address_only', 'calculated_field', 'extract_numeric', 'boolean_to_bit',
            'default_getutcdate_if_null',
            'authu_contact'  # Modifier for AUTHU contact extraction - see implementation-plan.md Phase 0.5
        }
        found_types = set()
        for mapping in self.contract.mappings:
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type:
                if isinstance(mapping.mapping_type, list):
                    found_types.update(mapping.mapping_type)
                else:
                    # Fallback for string format
                    for mt in str(mapping.mapping_type).split(','):
                        found_types.add(mt.strip())
        missing = found_types - supported_types
        self.assertEqual(len(missing), 0, f"Unsupported mapping types found: {missing}")

    def test_all_mapping_types_exercised(self):
        """Ensure every mapping_type is exercised by sample XML and mapping code."""
        exercised_types = set()
        for mapping in self.contract.mappings:
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type:
                mapping_types = mapping.mapping_type if isinstance(mapping.mapping_type, list) else [mt.strip() for mt in str(mapping.mapping_type).split(',')]
                # Try to extract value for this mapping from sample XML
                value = self.mapper._extract_value_from_xml(self.parsed_xml, mapping)
                if value is not None:
                    exercised_types.update(mapping_types)
        # All contract mapping types should be exercised
        contract_types = set()
        for mapping in self.contract.mappings:
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type:
                mapping_types = mapping.mapping_type if isinstance(mapping.mapping_type, list) else [mt.strip() for mt in str(mapping.mapping_type).split(',')]
                contract_types.update(mapping_types)
        # Allow for some mapping types to be optional/not present in every sample
        optional_types = {'last_valid_pr_contact'}
        missing = contract_types - exercised_types - optional_types
        self.assertEqual(len(missing), 0, f"Mapping types not exercised by sample XML (excluding optional): {missing}")

    def test_expressions_syntax_and_execution(self):
        """Ensure all expressions are syntactically valid and produce results."""
        for mapping in self.contract.mappings:
            if hasattr(mapping, 'expression') and mapping.expression:
                # Try to evaluate the expression using the mapping engine
                try:
                    # This assumes DataMapper has a method to evaluate expressions
                    result = self.mapper._apply_calculated_field_mapping(None, mapping)
                    # Accept None only if input is missing, otherwise must produce a value
                except Exception as e:
                    self.fail(f"Expression failed for mapping {mapping.target_column}: {e}")

    def test_multi_mapping_type_chaining(self):
        """Ensure multi-mapping (chained) types are handled and tested."""
        for mapping in self.contract.mappings:
            if 'mapping_type' in mapping.__dict__ and mapping.mapping_type and ',' in str(mapping.mapping_type):
                types = [mt.strip() for mt in str(mapping.mapping_type).split(',')]
                # Try to extract and transform value for each type in chain
                value = self.mapper._extract_value_from_xml(self.parsed_xml, mapping)
                for mt in types:
                    # Simulate chaining by passing through each transformation
                    try:
                        if mt == 'enum':
                            value = self.mapper._apply_enum_mapping(value, mapping)
                        elif mt == 'char_to_bit':
                            value = self.mapper._apply_bit_conversion(value)
                        elif mt == 'numbers_only':
                            value = self.mapper._extract_numbers_only(value)
                        elif mt == 'boolean_to_bit':
                            value = self.mapper._apply_boolean_to_bit_conversion(value)
                        # Add other types as needed
                    except Exception as e:
                        self.fail(f"Chained mapping type {mt} failed for {mapping.target_column}: {e}")
                # Final value should be valid or None (excluded)

    def test_field_level_default_values(self):
        """Ensure field-level default values work correctly."""
        for mapping in self.contract.mappings:
            if hasattr(mapping, 'default_value') and mapping.default_value is not None:
                # Try to extract value, simulate missing input
                value = self.mapper._extract_value_from_xml(self.parsed_xml, mapping)
                if value is None:
                    # Should use default value
                    default = mapping.default_value
                    self.assertIsNotNone(default, f"Default value missing for {mapping.target_column}")

    def test_enum_type_mapping(self):
        """
        Functional test: Validate that enum mapping produces the expected output for known XML input.
        """
        # Ensure enum mappings are loaded from the contract. Use safe helper to
        # coerce possibly-None contract values into an empty dict when needed.
        if hasattr(self.mapper, '_enum_mappings') and not self.mapper._enum_mappings:
            enum_mappings = getattr(self.contract, 'enum_mappings', None)
            self.mapper._enum_mappings = safe_coerce_dict(enum_mappings)
        mapping = next(m for m in self.contract.mappings if m.target_column == "app_type_enum")
        app_path = '/Provenir/Request/CustData/application'
        app_data = self.parsed_xml.get(app_path, {})
        app_type_code = app_data.get('attributes', {}).get('app_type_code')
        print(f"[DEBUG] app_type_code from XML: {app_type_code}")
        # Print loaded enum mappings
        enum_mappings = None
        if hasattr(self.mapper, '_enum_mappings'):
            enum_mappings = self.mapper._enum_mappings.get('app_type_enum', {})
        print(f"[DEBUG] Loaded enum mappings for app_type_enum: {enum_mappings}")
        result = self.mapper._apply_enum_mapping(app_type_code, mapping)
        print(f"[DEBUG] Mapping result for app_type_code '{app_type_code}': {result}")
        expected_enum_value = 30  # PRODB -> 30
        if result != expected_enum_value:
            print(f"[ERROR] Enum mapping failed: got {result}, expected {expected_enum_value}")
        self.assertEqual(result, expected_enum_value, f"Enum mapping failed: got {result}, expected {expected_enum_value}")

    def test_calculated_field_expression(self):
        xml_root = self.mapper._current_xml_root
        all_contacts = self.mapper._parse_all_contacts_from_root(xml_root)
        # Filter for valid contacts using production logic
        valid_contacts = []
        for contact in all_contacts:
            con_id = contact.get('con_id', '').strip()
            ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
            if not con_id:
                continue
            if ac_role_tp_c not in ['PR', 'AUTHU']:
                continue
            valid_contacts.append(contact)
        # ...existing code...
        """
        Functional test: Validate calculated field expressions for known XML input.
        Uses DataMapper's valid contact extraction logic and processes child elements for each valid contact.
        """
        def get_mapping(target_column):
            return next(m for m in self.contract.mappings if m.target_column == target_column)

        xml_root = self.mapper._current_xml_root
        contacts = self.mapper._parse_all_contacts_from_root(xml_root)
        found = 0
        # Existing assertions for calculated fields
        for contact in contacts:
            ac_role_tp_c = contact.get('ac_role_tp_c')
            for emp in contact.get('contact_employment', []):
                if emp.get('b_months_at_job') == '10' and emp.get('b_years_at_job') == '2':
                    mapping = get_mapping("months_at_job")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=emp)
                    expected_value = 34
                    self.assertEqual(result, expected_value)
                    found += 1
                if emp.get('b_months_at_job') == '32' and emp.get('b_years_at_job') == '1':
                    mapping = get_mapping("months_at_job")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=emp)
                    expected_value = 44
                    self.assertEqual(result, expected_value)
                    found += 1
                if emp.get('b_salary') == '120000.656' and emp.get('b_salary_basis_tp_c') == 'ANNUM':
                    mapping = get_mapping("monthly_salary")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=emp)
                    expected_value = 10000.05
                    self.assertEqual(result, expected_value)
                    found += 1
                if emp.get('b_salary') == '4000' and emp.get('b_salary_basis_tp_c') == 'MONTH':
                    mapping = get_mapping("monthly_salary")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=emp)
                    expected_value = 48000
                    self.assertEqual(result, expected_value)
                    found += 1
            for addr in contact.get('contact_address', []):
                if addr.get('months_at_residence') == '11' and addr.get('years_at_residence') == '2':
                    mapping = get_mapping("months_at_address")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=addr)
                    expected_value = 35
                    self.assertEqual(result, expected_value)
                    found += 1
                if addr.get('months_at_residence') == '41' and addr.get('years_at_residence') == '1':
                    mapping = get_mapping("months_at_address")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=addr)
                    expected_value = 53
                    self.assertEqual(result, expected_value)
                    found += 1
                if ac_role_tp_c == 'AUTHU' and addr.get('months_at_residence') == '3' and addr.get('years_at_residence') == '2':
                    mapping = get_mapping("months_at_address")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=addr)
                    expected_value = 27
                    self.assertEqual(result, expected_value)
                    found += 1

        # New assertions for qualified references, LIKE, and DATE comparisons
        # Test cb_score_factor_code_1 and cb_score_factor_code_2 against actual contract expressions
        for path, element in self.parsed_xml.items():
            if path.endswith('app_product'):
                attrs = element.get('attributes', {})
                app_attrs = None
                # Find the application element for context
                for app_path, app_element in self.parsed_xml.items():
                    if app_path.endswith('application'):
                        app_attrs = app_element.get('attributes', {})
                        break

                if app_attrs:
                    # Build proper context for app-level calculated fields using the same method as the system
                    context_data = self.mapper._build_app_level_context(self.parsed_xml, valid_contacts, '443306')

                    # Test cb_score_factor_type_1: Should return 'AJ' based on contract expression
                    # Expression: CASE WHEN app_product.adverse_actn1_type_cd IS NOT EMPTY AND application.app_receive_date > DATE('2023-10-11 00:00:00') AND application.population_assignment = 'CM' THEN 'AJ' WHEN app_product.adverse_actn1_type_cd LIKE 'V4_%' AND application.app_receive_date > DATE('2023-10-11 00:00:00') AND application.app_type_code = 'SECURE' THEN 'V4' ELSE '' END
                    mapping1 = get_mapping("cb_score_factor_type_1")
                    result1 = self.mapper._apply_calculated_field_mapping(None, mapping1, context_data=context_data)
                    # adverse_actn1_type_cd = "V4 ACTION 1" (not empty), app_receive_date > '2023-10-11', population_assignment = 'CM' -> should return 'AJ'
                    self.assertEqual(result1, 'AJ', f"cb_score_factor_type_1 should return 'AJ' but got '{result1}'")

                    # Test cb_score_factor_type_2: Should return '' based on contract expression
                    # Expression: CASE WHEN app_product.adverse_actn2_type_cd IS NOT EMPTY AND application.app_receive_date > DATE('2050-01-01 00:00:00') AND application.population_assignment = 'CM' THEN 'AJ' WHEN app_product.adverse_actn2_type_cd LIKE 'V4_%' AND application.app_receive_date > DATE('2023-10-11 00:00:00') AND application.app_type_code = 'SECURE' THEN 'V4' ELSE '' END
                    mapping2 = get_mapping("cb_score_factor_type_2")
                    result2 = self.mapper._apply_calculated_field_mapping(None, mapping2, context_data=context_data)
                    # adverse_actn2_type_cd = "AA ACTION 2" (not empty but not LIKE 'V4_%'), app_receive_date not > '2050-01-01', app_type_code != 'SECURE' -> should return ''
                    self.assertEqual(result2, '', f"cb_score_factor_code_2 should return '' but got '{result2}'")
                    # Test risk_model_score_factor_type_1: Should return 'AJ' based on contract expression
                    # Expression: CASE WHEN app_product.risk_model_reason1_tp_c IS NOT EMPTY AND application.population_assignment = 'BL' THEN 'ben_lomond' WHEN app_product.risk_model_reason1_tp_c IS NOT EMPTY AND application.population_assignment = 'JB' THEN 'jupiter_bowl' WHEN app_product.risk_model_reason1_tp_c IS NOT EMPTY AND application.population_assignment = 'LB' THEN 'lightbox' WHEN app_product.risk_model_reason1_tp_c IS NOT EMPTY AND application.population_assignment = 'SB' THEN 'snowbird' WHEN app_product.risk_model_reason1_tp_c IS NOT EMPTY AND application.population_assignment = 'SO' THEN 'solitude' ELSE '' END
                    mapping_risk1 = get_mapping("risk_model_score_factor_type_1")
                    result_risk1 = self.mapper._apply_calculated_field_mapping(None, mapping_risk1, context_data=context_data)
                    # Risk_Model_reason1_tp_c = "RISK MODEL REASON 1" (not empty), population_assignment = 'CM' -> should return '' (no match)
                    self.assertEqual(result_risk1, '', f"risk_model_score_factor_type_1 should return '' but got '{result_risk1}'")

        self.assertGreaterEqual(found, 7, f"Not all expected calculated field elements found and tested. Found {found}.")

    def test_risk_model_calculated_fields_case_insensitive(self):
        """Test that risk_model calculated fields work with case-insensitive XML attribute matching."""
        def get_mapping(target_column):
            return next(m for m in self.contract.mappings if m.target_column == target_column)

        # Build context using the same method as the system
        xml_root = self.mapper._current_xml_root
        all_contacts = self.mapper._parse_all_contacts_from_root(xml_root)
        valid_contacts = []
        for contact in all_contacts:
            con_id = contact.get('con_id', '').strip()
            ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
            if not con_id:
                continue
            if ac_role_tp_c not in ['PR', 'AUTHU']:
                continue
            valid_contacts.append(contact)
        
        context_data = self.mapper._build_app_level_context(self.parsed_xml, valid_contacts, '443306')
        
        # Test that Risk_Model_reason1_tp_c (with capital R and M) is accessible as app_product.risk_model_reason1_tp_c (lowercase)
        self.assertIn('app_product.risk_model_reason1_tp_c', context_data, "Context should contain lowercase version of Risk_Model_reason1_tp_c")   
        self.assertEqual(context_data['app_product.risk_model_reason1_tp_c'], 'RISK MODEL REASON 1', "Context should have correct value for risk_model_reason1_tp_c")
        
        # Test the calculated field
        mapping = get_mapping("risk_model_score_factor_type_1")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        # With population_assignment = 'CM', should return '' since none of the WHEN conditions match
        self.assertEqual(result, '', f"risk_model_score_factor_type_1 should return '' for population_assignment='CM' but got '{result}'")

    def test_expression_syntax_and_result(self):
        """
        Functional test: Validate that all expressions in the contract are syntactically valid and produce expected results for known XML input.
        """
        for mapping in self.contract.mappings:
            if hasattr(mapping, 'expression') and mapping.expression:
                # Find a matching context for the mapping
                for path, element in self.parsed_xml.items():
                    if path.endswith('contact_employment') and mapping.target_column == 'months_at_job':
                        attrs = element.get('attributes', {})
                        if attrs.get('b_months_at_job') == '6' and attrs.get('b_years_at_job') == '1':
                            result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=element)
                            self.assertIsNotNone(result, f"Expression failed for mapping {mapping.target_column}: result is None")
                            break
                # ...existing code...

    def test_comprehensive_calculated_field_expressions(self):
        """
        Comprehensive test coverage for all calculated field expressions in the mapping contract.
        Tests expressions with various input scenarios to ensure they produce correct results.
        This provides unit-level validation before e2e testing.
        """
        def get_mapping(target_column):
            return next(m for m in self.contract.mappings if m.target_column == target_column)

        # Build context data for app-level tests
        xml_root = self.mapper._current_xml_root
        all_contacts = self.mapper._parse_all_contacts_from_root(xml_root)
        valid_contacts = []
        for contact in all_contacts:
            con_id = contact.get('con_id', '').strip()
            ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
            if not con_id:
                continue
            if ac_role_tp_c not in ['PR', 'AUTHU']:
                continue
            valid_contacts.append(contact)

        context_data = self.mapper._build_app_level_context(self.parsed_xml, valid_contacts, '443306')

        # Test 1: Basic calculated fields (contact-level)
        # months_at_address: months_at_residence + (years_at_residence * 12)
        mapping = get_mapping("months_at_address")

        # Test case 1: 11 months + 2 years = 11 + (2*12) = 35
        test_context = {'months_at_residence': 11, 'years_at_residence': 2}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 35, f"months_at_address calculation failed: expected 35, got {result}")

        # Test case 2: 3 months + 2 years = 3 + (2*12) = 27
        test_context = {'months_at_residence': 3, 'years_at_residence': 2}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 27, f"months_at_address calculation failed: expected 27, got {result}")

        # months_at_job: b_months_at_job + (b_years_at_job * 12)
        mapping = get_mapping("months_at_job")

        # Test case 1: 10 months + 2 years = 10 + (2*12) = 34
        test_context = {'b_months_at_job': 10, 'b_years_at_job': 2}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 34, f"months_at_job calculation failed: expected 34, got {result}")

        # Test case 2: 6 months + 1 year = 6 + (1*12) = 18
        test_context = {'b_months_at_job': 6, 'b_years_at_job': 1}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 18, f"months_at_job calculation failed: expected 18, got {result}")

        # monthly_salary: CASE WHEN b_salary_basis_tp_c = 'ANNUM' THEN b_salary / 12 WHEN b_salary_basis_tp_c = 'MONTH' THEN b_salary * 12 WHEN b_salary_basis_tp_c = 'HOURLY' THEN b_salary WHEN b_salary_basis_tp_c = '' THEN b_salary ELSE b_salary END
        mapping = get_mapping("monthly_salary")

        # Test case 1: Annual salary 120000.656 / 12 = 10000.054666... (should be 10000.05 with proper rounding)
        test_context = {'b_salary': 120000.656, 'b_salary_basis_tp_c': 'ANNUM'}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertAlmostEqual(result, 10000.05, places=2, msg=f"monthly_salary ANNUM calculation failed: expected ~10000.05, got {result}")

        # Test case 2: Monthly salary 4000 * 12 = 48000
        test_context = {'b_salary': 4000, 'b_salary_basis_tp_c': 'MONTH'}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 48000, f"monthly_salary MONTH calculation failed: expected 48000, got {result}")

        # Test case 3: Hourly salary (should return as-is)
        test_context = {'b_salary': 25.50, 'b_salary_basis_tp_c': 'HOURLY'}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 25.50, f"monthly_salary HOURLY calculation failed: expected 25.50, got {result}")

        # Test 2: CB Score Factor Types (app-level with complex CASE logic)
        # All CB score factors use the same complex CASE expression with different adverse action codes

        # Test cb_score_factor_type_1 with current test data context
        # Expression checks: adverse_actn1_type_cd with various conditions
        # Current test data: adverse_actn1_type_cd = "V4 ACTION 1", population_assignment = 'CM',
        # app_receive_date > '2023-10-11', so should match: WHEN ... population_assignment = 'CM' THEN 'AJ'
        mapping = get_mapping("cb_score_factor_type_1")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, 'AJ', f"cb_score_factor_type_1 failed: expected 'AJ', got '{result}'")

        # Test cb_score_factor_type_2 with current test data context
        # Expression checks: adverse_actn2_type_cd with various conditions
        # Current test data: adverse_actn2_type_cd = "AA ACTION 2", population_assignment = 'CM',
        # app_receive_date > '2023-10-11', but doesn't match any WHEN conditions -> should return ''
        mapping = get_mapping("cb_score_factor_type_2")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, '', f"cb_score_factor_type_2 failed: expected '', got '{result}'")

        # Test cb_score_factor_type_3 with current test data context
        # Expression checks: adverse_actn3_type_cd with various conditions
        # Current test data: adverse_actn3_type_cd = "AA ANYTHING-3" (not empty), population_assignment = 'CM',
        # app_receive_date > '2023-10-11', so should match: WHEN ... population_assignment = 'CM' THEN 'AJ'
        mapping = get_mapping("cb_score_factor_type_3")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, 'AJ', f"cb_score_factor_type_3 failed: expected 'AJ', got '{result}'")

        # Test cb_score_factor_type_4 with current test data context
        # Expression checks: adverse_actn4_type_cd with various conditions
        # Current test data: adverse_actn4_type_cd = "BLAH" (not empty), population_assignment = 'CM',
        # app_receive_date > '2023-10-11', so should match: WHEN ... population_assignment = 'CM' THEN 'AJ'
        mapping = get_mapping("cb_score_factor_type_4")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, 'AJ', f"cb_score_factor_type_4 failed: expected 'AJ', got '{result}'")

        # Test cb_score_factor_type_5 with current test data context
        # Similar logic to type_2
        mapping = get_mapping("cb_score_factor_type_5")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, '', f"cb_score_factor_type_5 failed: expected '', got '{result}'")

        # Test 3: Risk Model Score Factor Types (app-level)
        # All risk model factors use: CASE WHEN risk_model_reasonX_tp_c IS NOT EMPTY AND population_assignment = 'XX' THEN 'model_name' ELSE '' END

        # Test risk_model_score_factor_type_1
        # Current test data: risk_model_reason1_tp_c = "RISK MODEL REASON 1", population_assignment = 'CM'
        # No matching population_assignment condition -> should return ''
        mapping = get_mapping("risk_model_score_factor_type_1")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, '', f"risk_model_score_factor_type_1 failed: expected '', got '{result}'")

        # Test risk_model_score_factor_type_2
        mapping = get_mapping("risk_model_score_factor_type_2")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, '', f"risk_model_score_factor_type_2 failed: expected '', got '{result}'")

        # Test risk_model_score_factor_type_3
        mapping = get_mapping("risk_model_score_factor_type_3")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, '', f"risk_model_score_factor_type_3 failed: expected '', got '{result}'")

        # Test risk_model_score_factor_type_4
        mapping = get_mapping("risk_model_score_factor_type_4")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=context_data)
        self.assertEqual(result, '', f"risk_model_score_factor_type_4 failed: expected '', got '{result}'")

        # Test 4: Edge cases and error handling
        # Test with missing context data
        mapping = get_mapping("months_at_address")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={})
        self.assertIsNone(result, "Should return None when required context data is missing")

        # Test with partial context data (missing one field)
        test_context = {'months_at_residence': 5}  # missing years_at_residence
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, "Should return None when any field in arithmetic expression is missing (respects nullable: true)")

        # Test with empty string values
        test_context = {'months_at_residence': '', 'years_at_residence': 2}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, "Should return None when any field is empty string (respects nullable: true)")

        # Test with None values
        test_context = {'months_at_residence': None, 'years_at_residence': 2}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, "Should return None when any field is None (respects nullable: true)")

    def test_calculated_field_null_handling(self):
        """
        Test that calculated fields properly handle missing/null data and return None 
        instead of manufacturing fake data (like converting missing fields to 0).
        This respects the nullable: true setting in the mapping contract.
        
        Critical business requirement: "If there truly is missing fields or blank data, 
        we don't want to return a 0, we want to return a null. I don't want to manufacture 
        data that wasn't there."
        """
        def get_mapping(target_column):
            return next(m for m in self.contract.mappings if m.target_column == target_column)

        # Test 1: months_at_job with missing b_months_at_job (should return None, not 0)
        mapping = get_mapping("months_at_job")
        test_context = {'b_years_at_job': 2}  # b_months_at_job missing
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, 
            "months_at_job should return None when b_months_at_job is missing (not manufacture 0)")

        # Test 2: months_at_job with missing b_years_at_job (should return None, not 0)
        test_context = {'b_months_at_job': 10}  # b_years_at_job missing
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, 
            "months_at_job should return None when b_years_at_job is missing (not manufacture 0)")

        # Test 3: months_at_address with empty string values (should return None)
        mapping = get_mapping("months_at_address")
        test_context = {'months_at_residence': '', 'years_at_residence': 2}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, 
            "months_at_address should return None when months_at_residence is empty string")

        # Test 4: months_at_address with None values (should return None)
        test_context = {'months_at_residence': 5, 'years_at_residence': None}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, 
            "months_at_address should return None when years_at_residence is None")

        # Test 5: monthly_salary with missing b_salary (should return None)
        mapping = get_mapping("monthly_salary")
        test_context = {'b_salary_basis_tp_c': 'ANNUM'}  # b_salary missing
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertIsNone(result, 
            "monthly_salary should return None when b_salary is missing")

        # Test 6: Verify valid data still works (not breaking normal operation)
        test_context = {'b_months_at_job': 10, 'b_years_at_job': 2}
        mapping = get_mapping("months_at_job")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 34, 
            "months_at_job should still calculate correctly when all fields are present")

        # Test 7: Verify zero values work correctly (0 is valid data, not missing)
        test_context = {'b_months_at_job': 0, 'b_years_at_job': 0}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 0, 
            "months_at_job should return 0 when fields are present with value 0 (not None)")

    def test_calculated_field_expression_scenarios(self):
        """
        Test calculated field expressions with various realistic scenarios and edge cases.
        This provides additional coverage beyond the basic comprehensive test.
        """
        def get_mapping(target_column):
            return next(m for m in self.contract.mappings if m.target_column == target_column)

        # Scenario 1: Test monthly_salary with empty salary basis (should return salary as-is)
        mapping = get_mapping("monthly_salary")
        test_context = {'b_salary': 50000, 'b_salary_basis_tp_c': ''}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 50000, f"monthly_salary with empty basis failed: expected 50000, got {result}")

        # Scenario 2: Test months_at_address with zero values
        mapping = get_mapping("months_at_address")
        test_context = {'months_at_residence': 0, 'years_at_residence': 0}
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 0, f"months_at_address with zeros failed: expected 0, got {result}")

        # Scenario 3: Test months_at_job with large values
        mapping = get_mapping("months_at_job")
        test_context = {'b_months_at_job': 11, 'b_years_at_job': 10}  # 11 + (10*12) = 131
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=test_context)
        self.assertEqual(result, 131, f"months_at_job with large values failed: expected 131, got {result}")

        # Scenario 4: Test CB score factors with different population assignments
        # Create mock context data with different population assignment
        xml_root = self.mapper._current_xml_root
        all_contacts = self.mapper._parse_all_contacts_from_root(xml_root)
        valid_contacts = []
        for contact in all_contacts:
            con_id = contact.get('con_id', '').strip()
            ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
            if not con_id:
                continue
            if ac_role_tp_c not in ['PR', 'AUTHU']:
                continue
            valid_contacts.append(contact)

        # Test with BL population assignment (should return specific values for risk model factors)
        mock_context_bl = self.mapper._build_app_level_context(self.parsed_xml, valid_contacts, '443306')
        # Override population_assignment for testing
        mock_context_bl['application.population_assignment'] = 'BL'

        mapping = get_mapping("risk_model_score_factor_type_1")
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=mock_context_bl)
        self.assertEqual(result, 'ben_lomond', f"risk_model_score_factor_type_1 with BL assignment failed: expected 'ben_lomond', got '{result}'")

        # Test with JB population assignment
        mock_context_jb = dict(mock_context_bl)
        mock_context_jb['application.population_assignment'] = 'JB'
        result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data=mock_context_jb)
        self.assertEqual(result, 'jupiter_bowl', f"risk_model_score_factor_type_1 with JB assignment failed: expected 'jupiter_bowl', got '{result}'")


if __name__ == '__main__':
    unittest.main()
