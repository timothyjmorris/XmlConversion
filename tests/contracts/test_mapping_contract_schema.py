#!/usr/bin/env python3
"""
Test script to validate the credit card mapping contract configuration.
This script checks the JSON mapping contract for completeness and consistency.
"""

import json
import unittest
from pathlib import Path
from typing import Dict, List, Set


class TestMappingContractSchema(unittest.TestCase):
    """Test mapping contract JSON schema validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.contract_path = Path(__file__).parent.parent.parent / "config" / "credit_card_mapping_contract.json"
        if not self.contract_path.exists():
            self.skipTest(f"Mapping contract file not found: {self.contract_path}")
        
        self.contract = self.load_mapping_contract(str(self.contract_path))
    
    def load_mapping_contract(self, file_path: str) -> Dict:
        """Load the mapping contract JSON file."""
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def test_key_identifiers_validation(self):
        """Test key identifier configuration."""
        errors = []
        
        key_ids = self.contract.get('key_identifiers', {})
        
        # Check required identifiers
        required_keys = ['app_id', 'con_id_primary']
        for key in required_keys:
            if key not in key_ids:
                errors.append(f"Missing required key identifier: {key}")
            elif not key_ids[key].get('required', False):
                errors.append(f"Key identifier {key} should be marked as required")
        
        # Check XML paths
        for key, config in key_ids.items():
            if not config.get('xml_path'):
                errors.append(f"Key identifier {key} missing xml_path")
            if not config.get('xml_attribute'):
                errors.append(f"Key identifier {key} missing xml_attribute")
        
        self.assertEqual(len(errors), 0, f"Key identifier validation errors: {errors}")
    
    def test_enum_mappings_validation(self):
        """Test enum mapping configuration."""
        errors = []
        
        enum_mappings = self.contract.get('enum_mappings', {})
        
        # Check required enum types
        required_enums = [
            'status_enum', 'app_source_enum', 'decision_enum', 
            'contact_type_enum', 'address_type_enum', 'employment_type_enum'
        ]
        
        for enum_type in required_enums:
            if enum_type not in enum_mappings:
                errors.append(f"Missing required enum mapping: {enum_type}")
        
        # Validate enum value ranges are reasonable
        for enum_type, mappings in enum_mappings.items():
            for key, value in mappings.items():
                if not isinstance(value, int) or value < 1:
                    errors.append(f"Enum {enum_type} value {value} for key '{key}' should be a positive integer")
        
        self.assertEqual(len(errors), 0, f"Enum mapping validation errors: {errors}")
    
    def test_bit_conversions_validation(self):
        """Test bit conversion configuration."""
        errors = []
        
        bit_conversions = self.contract.get('bit_conversions', {})
        
        # Check required conversion types
        required_conversions = ['char_to_bit', 'boolean_to_bit']
        for conv_type in required_conversions:
            if conv_type not in bit_conversions:
                errors.append(f"Missing bit conversion type: {conv_type}")
        
        # Check char_to_bit mappings
        if 'char_to_bit' in bit_conversions:
            char_to_bit = bit_conversions['char_to_bit']
            required_chars = ['Y', 'N', '', 'null', ' ']
            for char in required_chars:
                if char not in char_to_bit:
                    errors.append(f"char_to_bit missing mapping for: '{char}'")
                elif char_to_bit[char] not in [0, 1]:
                    errors.append(f"char_to_bit invalid value for '{char}': {char_to_bit[char]}")
        
        self.assertEqual(len(errors), 0, f"Bit conversion validation errors: {errors}")
    
    def test_field_mappings_validation(self):
        """Test field mapping configuration."""
        errors = []
        
        mappings = self.contract.get('mappings', [])
        
        if not mappings:
            errors.append("No field mappings defined")
        else:
            # Check required fields
            required_fields = ['xml_path', 'target_table', 'target_column', 'data_type']
            
            for i, mapping in enumerate(mappings):
                for field in required_fields:
                    if field not in mapping:
                        errors.append(f"Mapping {i} missing required field: {field}")
                
                # Check XML path format
                xml_path = mapping.get('xml_path', '')
                if xml_path and not xml_path.startswith('/Provenir/Request'):
                    errors.append(f"Mapping {i} XML path should start with '/Provenir/Request': {xml_path}")
                
                # Check target table names
                target_table = mapping.get('target_table', '')
                valid_tables = [
                    'app_base', 'app_operational_cc', 'app_pricing_cc', 'app_transactional_cc', 'app_solicited_cc',
                    'contact_base', 'contact_address', 'contact_employment'
                ]
                if target_table and target_table not in valid_tables:
                    errors.append(f"Mapping {i} invalid target table: {target_table}")
            
            # Check for duplicate mappings
            seen_mappings = set()
            for i, mapping in enumerate(mappings):
                key = (mapping.get('xml_path'), mapping.get('xml_attribute'), mapping.get('target_table'), mapping.get('target_column'))
                if key in seen_mappings:
                    errors.append(f"Duplicate mapping found at index {i}: {key}")
                seen_mappings.add(key)
        
        self.assertEqual(len(errors), 0, f"Field mapping validation errors: {errors}")
    
    def test_relationships_validation(self):
        """Test relationship configuration."""
        errors = []
        
        relationships = self.contract.get('relationships', [])
        
        for i, rel in enumerate(relationships):
            required_fields = ['parent_table', 'child_table', 'foreign_key_column', 'xml_parent_path', 'xml_child_path']
            for field in required_fields:
                if field not in rel:
                    errors.append(f"Relationship {i} missing required field: {field}")
        
        self.assertEqual(len(errors), 0, f"Relationship validation errors: {errors}")
    
    def test_validation_rules_validation(self):
        """Test validation rules configuration."""
        errors = []
        
        validation_rules = self.contract.get('validation_rules', {})
        
        # Check required identifiers
        required_ids = validation_rules.get('required_identifiers', [])
        if 'app_id' not in required_ids:
            errors.append("app_id should be in required_identifiers")
        if 'con_id_primary' not in required_ids:
            errors.append("con_id_primary should be in required_identifiers")
        
        # Check validation ranges
        for id_type in ['app_id_validation', 'con_id_validation']:
            if id_type in validation_rules:
                validation = validation_rules[id_type]
                if 'min_value' not in validation or 'max_value' not in validation:
                    errors.append(f"{id_type} missing min_value or max_value")
                elif validation['min_value'] >= validation['max_value']:
                    errors.append(f"{id_type} min_value should be less than max_value")
        
        self.assertEqual(len(errors), 0, f"Validation rules errors: {errors}")
    
    def test_contract_completeness(self):
        """Test overall contract completeness."""
        required_sections = [
            'source_table', 'source_column', 'xml_root_element',
            'key_identifiers', 'mappings', 'relationships'
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in self.contract:
                missing_sections.append(section)
        
        self.assertEqual(len(missing_sections), 0, f"Missing required sections: {missing_sections}")
        
        # Print summary for information
        print(f"\\nContract Summary:")
        print(f"  - Key Identifiers: {len(self.contract.get('key_identifiers', {}))}")
        print(f"  - Field Mappings: {len(self.contract.get('mappings', []))}")
        print(f"  - Enum Types: {len(self.contract.get('enum_mappings', {}))}")
        print(f"  - Bit Conversion Types: {len(self.contract.get('bit_conversions', {}))}")
        print(f"  - Relationships: {len(self.contract.get('relationships', []))}")
        print(f"  - Default Values: {len(self.contract.get('default_values', {}))}")


if __name__ == '__main__':
    unittest.main()