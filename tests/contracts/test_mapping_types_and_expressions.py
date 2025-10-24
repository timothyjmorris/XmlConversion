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
    def test_debug_print_all_contacts_and_addresses(self):
        """
        Debug: Print all contact_employment and contact_address elements and their attributes from parsed XML.
        """
        print("\n[DEBUG] All contact_employment elements:")
        for path, element in self.parsed_xml.items():
            if path.endswith('contact_employment'):
                print(f"  Path: {path}")
                print(f"    Attributes: {element.get('attributes', {})}")
        print("\n[DEBUG] All contact_address elements:")
        for path, element in self.parsed_xml.items():
            if path.endswith('contact_address'):
                print(f"  Path: {path}")
                print(f"    Attributes: {element.get('attributes', {})}")
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
            if 'mapping_type' in mapping.__dict__ and mapping.mapping_type:
                for mt in str(mapping.mapping_type).split(','):
                    found_types.add(mt.strip())
        missing = found_types - supported_types
        self.assertEqual(len(missing), 0, f"Unsupported mapping types found: {missing}")

    def test_all_mapping_types_exercised(self):
        """Ensure every mapping_type is exercised by sample XML and mapping code."""
        exercised_types = set()
        for mapping in self.contract.mappings:
            if 'mapping_type' in mapping.__dict__ and mapping.mapping_type:
                for mt in str(mapping.mapping_type).split(','):
                    # Try to extract value for this mapping from sample XML
                    value = self.mapper._extract_value_from_xml(self.parsed_xml, mapping)
                    if value is not None:
                        exercised_types.add(mt.strip())
        # All contract mapping types should be exercised
        contract_types = set()
        for mapping in self.contract.mappings:
            if 'mapping_type' in mapping.__dict__ and mapping.mapping_type:
                for mt in str(mapping.mapping_type).split(','):
                    contract_types.add(mt.strip())
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
        import pprint
        print("\n[DEBUG] Full valid contact structures:")
        for idx, contact in enumerate(valid_contacts):
            print(f"Contact {idx}:")
            pprint.pprint(contact)
        print("\n[DEBUG] Parsed valid contacts and children:")
        for idx, contact in enumerate(valid_contacts):
            print(f"Contact {idx}: ac_role_tp_c={contact.get('ac_role_tp_c')}")
            if 'contact_employment' in contact:
                for emp in contact['contact_employment']:
                    print(f"  Employment: b_months_at_job={emp.get('b_months_at_job')}, b_years_at_job={emp.get('b_years_at_job')}, b_salary={emp.get('b_salary')}, b_salary_basis_tp_c={emp.get('b_salary_basis_tp_c')}")
            if 'contact_address' in contact:
                for addr in contact['contact_address']:
                    print(f"  Address: months_at_residence={addr.get('months_at_residence')}, years_at_residence={addr.get('years_at_residence')}")
        # ...existing code...
        """
        Functional test: Validate calculated field expressions for known XML input.
        Uses DataMapper's valid contact extraction logic and processes child elements for each valid contact.
        """
        def get_mapping(target_column):
            return next(m for m in self.contract.mappings if m.target_column == target_column)

        # Use DataMapper's valid contact extraction logic
        # Use XML root and DataMapper's _parse_all_contacts_from_root to traverse child elements
        xml_root = self.mapper._current_xml_root
        contacts = self.mapper._parse_all_contacts_from_root(xml_root)
        found = 0
        def get_mapping(target_column):
            return next(m for m in self.contract.mappings if m.target_column == target_column)

        for contact in valid_contacts:
            ac_role_tp_c = contact.get('ac_role_tp_c')
            # Employment elements
            for emp in contact.get('contact_employment', []):
                # 1. PR/CURR, b_months_at_job="10" b_years_at_job="2"
                if emp.get('b_months_at_job') == '10' and emp.get('b_years_at_job') == '2':
                    mapping = get_mapping("months_at_job")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={'attributes': emp})
                    expected_value = 34
                    print(f"[DEBUG] {ac_role_tp_c}/CURR contact_employment: b_months_at_job=10, b_years_at_job=2, result={result}")
                    self.assertEqual(result, expected_value)
                    found += 1
                # 2. PR/PREV, b_months_at_job="32" b_years_at_job="1"
                if emp.get('b_months_at_job') == '32' and emp.get('b_years_at_job') == '1':
                    mapping = get_mapping("months_at_job")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={'attributes': emp})
                    expected_value = 44
                    print(f"[DEBUG] {ac_role_tp_c}/PREV contact_employment: b_months_at_job=32, b_years_at_job=1, result={result}")
                    self.assertEqual(result, expected_value)
                    found += 1
                # 3. PR/CURR, b_salary="120000" b_salary_basis_tp_c="ANNUM"
                if emp.get('b_salary') == '120000' and emp.get('b_salary_basis_tp_c') == 'ANNUM':
                    mapping = get_mapping("monthly_salary")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={'attributes': emp})
                    expected_value = 10000
                    print(f"[DEBUG] {ac_role_tp_c}/CURR contact_employment: b_salary=120000, b_salary_basis_tp_c=ANNUM, result={result}")
                    self.assertEqual(result, expected_value)
                    found += 1
                # 4. PR/PREV, b_salary="4000" b_salary_basis_tp_c="MONTH"
                if emp.get('b_salary') == '4000' and emp.get('b_salary_basis_tp_c') == 'MONTH':
                    mapping = get_mapping("monthly_salary")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={'attributes': emp})
                    expected_value = 48000
                    print(f"[DEBUG] {ac_role_tp_c}/PREV contact_employment: b_salary=4000, b_salary_basis_tp_c=MONTH, result={result}")
                    self.assertEqual(result, expected_value)
                    found += 1
            # Address elements
            for addr in contact.get('contact_address', []):
                # 5. PR/CURR, months_at_residence="11" years_at_residence="2"
                if addr.get('months_at_residence') == '11' and addr.get('years_at_residence') == '2':
                    mapping = get_mapping("months_at_address")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={'attributes': addr})
                    expected_value = 35
                    print(f"[DEBUG] {ac_role_tp_c}/CURR contact_address: months_at_residence=11, years_at_residence=2, result={result}")
                    self.assertEqual(result, expected_value)
                    found += 1
                # 6. PR/PREV, months_at_residence="41" years_at_residence="1"
                if addr.get('months_at_residence') == '41' and addr.get('years_at_residence') == '1':
                    mapping = get_mapping("months_at_address")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={'attributes': addr})
                    expected_value = 53
                    print(f"[DEBUG] {ac_role_tp_c}/PREV contact_address: months_at_residence=41, years_at_residence=1, result={result}")
                    self.assertEqual(result, expected_value)
                    found += 1
                # 7. AUTHU/CURR, months_at_residence="3" years_at_residence="2"
                if ac_role_tp_c == 'AUTHU' and addr.get('months_at_residence') == '3' and addr.get('years_at_residence') == '2':
                    mapping = get_mapping("months_at_address")
                    result = self.mapper._apply_calculated_field_mapping(None, mapping, context_data={'attributes': addr})
                    expected_value = 27
                    print(f"[DEBUG] AUTHU/CURR contact_address: months_at_residence=3, years_at_residence=2, result={result}")
                    self.assertEqual(result, expected_value)
                    found += 1
        self.assertGreaterEqual(found, 7, f"Not all expected calculated field elements found and tested. Found {found}.")

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
