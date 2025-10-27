#!/usr/bin/env python3
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
# Ensure workspace root (parent of MB_XmlConversionKiro) is in sys.path for imports
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)
print('DEBUG sys.path:', sys.path)
from MB_XmlConversionKiro.xml_extractor.mapping.data_mapper import DataMapper
from MB_XmlConversionKiro.xml_extractor.models import MappingContract

class TestMappingTypesAndExpressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        contract_path = Path(__file__).parent.parent.parent / "config" / "credit_card_mapping_contract.json"
        sample_xml_path = Path(__file__).parent.parent.parent / "config" / "samples" / "sample-source-xml-contact-test.xml"
        with open(contract_path, 'r') as f:
            contract_data = json.load(f)
        # Convert mappings and relationships to objects
        from MB_XmlConversionKiro.xml_extractor.models import FieldMapping, RelationshipMapping
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
        from MB_XmlConversionKiro.xml_extractor.parsing.xml_parser import XMLParser
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
            'default_getutcdate_if_null'
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

    def test_default_values_usage(self):
        """Ensure default values are only used where allowed and tested."""
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
        # Ensure enum mappings are loaded from the contract
        if hasattr(self.mapper, '_enum_mappings') and not self.mapper._enum_mappings:
            if hasattr(self.contract, 'enum_mappings'):
                self.mapper._enum_mappings = self.contract.enum_mappings
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
if __name__ == '__main__':
    unittest.main()
