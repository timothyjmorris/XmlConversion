#!/usr/bin/env python3
"""
Test script to validate the credit card mapping contract configuration.
This script checks the JSON mapping contract for completeness and consistency.
"""

import json
from pathlib import Path
from typing import Dict, List, Set

def load_mapping_contract(file_path: str) -> Dict:
    """Load the mapping contract JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def validate_key_identifiers(contract: Dict) -> List[str]:
    """Validate key identifier configuration."""
    errors = []
    
    key_ids = contract.get('key_identifiers', {})
    
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
    
    return errors

def validate_enum_mappings(contract: Dict) -> List[str]:
    """Validate enum mapping configuration."""
    errors = []
    
    enum_mappings = contract.get('enum_mappings', {})
    
    # Check required enum types
    required_enums = [
        'status_enum', 'app_source_enum', 'decision_enum', 
        'contact_type_enum', 'address_type_enum', 'employment_type_enum'
    ]
    
    for enum_type in required_enums:
        if enum_type not in enum_mappings:
            errors.append(f"Missing required enum mapping: {enum_type}")
    
    # Check that population_assignment_enum has empty string default (required field)
    if 'population_assignment_enum' in enum_mappings:
        if '' not in enum_mappings['population_assignment_enum']:
            errors.append("population_assignment_enum missing empty string default value (required for NOT NULL column)")
    
    # Check that critical enum types do NOT have empty string defaults (should skip insert if missing)
    critical_enums = ['contact_type_enum', 'address_type_enum', 'employment_type_enum']
    for enum_type in critical_enums:
        if enum_type in enum_mappings and '' in enum_mappings[enum_type]:
            errors.append(f"Critical enum {enum_type} should NOT have empty string default - missing values should skip record insert")
    
    # Validate enum value ranges are reasonable (not enforcing strict ranges since you have custom values)
    for enum_type, mappings in enum_mappings.items():
        for key, value in mappings.items():
            if not isinstance(value, int) or value < 1:
                errors.append(f"Enum {enum_type} value {value} for key '{key}' should be a positive integer")
    
    return errors

def validate_bit_conversions(contract: Dict) -> List[str]:
    """Validate bit conversion configuration."""
    errors = []
    
    bit_conversions = contract.get('bit_conversions', {})
    
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
    
    return errors

def validate_field_mappings(contract: Dict) -> List[str]:
    """Validate field mapping configuration."""
    errors = []
    
    mappings = contract.get('mappings', [])
    
    if not mappings:
        errors.append("No field mappings defined")
        return errors
    
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
    
    return errors

def validate_relationships(contract: Dict) -> List[str]:
    """Validate relationship configuration."""
    errors = []
    
    relationships = contract.get('relationships', [])
    
    for i, rel in enumerate(relationships):
        required_fields = ['parent_table', 'child_table', 'foreign_key_column', 'xml_parent_path', 'xml_child_path']
        for field in required_fields:
            if field not in rel:
                errors.append(f"Relationship {i} missing required field: {field}")
    
    return errors

def validate_validation_rules(contract: Dict) -> List[str]:
    """Validate validation rules configuration."""
    errors = []
    
    validation_rules = contract.get('validation_rules', {})
    
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
    
    return errors

def main():
    """Main validation function."""
    script_dir = Path(__file__).parent
    config_file = script_dir / '..' / 'credit_card_mapping_contract.json'
    
    if not config_file.exists():
        print(f"ERROR: Configuration file not found: {config_file}")
        return 1
    
    try:
        contract = load_mapping_contract(config_file)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in configuration file: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: Failed to load configuration file: {e}")
        return 1
    
    print("Validating credit card mapping contract configuration...")
    print("=" * 60)
    
    all_errors = []
    
    # Run all validations
    validations = [
        ("Key Identifiers", validate_key_identifiers),
        ("Enum Mappings", validate_enum_mappings),
        ("Bit Conversions", validate_bit_conversions),
        ("Field Mappings", validate_field_mappings),
        ("Relationships", validate_relationships),
        ("Validation Rules", validate_validation_rules)
    ]
    
    for section_name, validation_func in validations:
        print(f"\nValidating {section_name}...")
        errors = validation_func(contract)
        if errors:
            print(f"  ❌ Found {len(errors)} error(s):")
            for error in errors:
                print(f"    - {error}")
            all_errors.extend(errors)
        else:
            print(f"  ✅ {section_name} validation passed")
    
    print("\n" + "=" * 60)
    if all_errors:
        print(f"❌ Validation FAILED with {len(all_errors)} total error(s)")
        return 1
    else:
        print("✅ All validations PASSED - Configuration is valid!")
        
        # Print summary statistics
        print(f"\nConfiguration Summary:")
        print(f"  - Key Identifiers: {len(contract.get('key_identifiers', {}))}")
        print(f"  - Field Mappings: {len(contract.get('mappings', []))}")
        print(f"  - Enum Types: {len(contract.get('enum_mappings', {}))}")
        print(f"  - Bit Conversion Types: {len(contract.get('bit_conversions', {}))}")
        print(f"  - Relationships: {len(contract.get('relationships', []))}")
        print(f"  - Default Values: {len(contract.get('default_values', {}))}")
        
        return 0

if __name__ == "__main__":
    exit(main())