"""
Debug test to trace exactly what happens in the transformation chain.
"""
import pytest
import json
from pathlib import Path
from xml_extractor.models import FieldMapping
from xml_extractor.mapping.data_mapper import DataMapper


@pytest.fixture
def rl_contract():
    """Load the actual RL contract."""
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
    with open(contract_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


@pytest.fixture
def mapper():
    """Create a DataMapper with the RL contract."""
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
    return DataMapper(str(contract_path))


def test_transformation_chain_step_by_step(rl_contract, mapper):
    """Step through the transformation chain with detailed logging."""
    
    # Get the actual contract mapping
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'check_requested_by_user'
    )
    
    field_mapping = FieldMapping(**mapping_dict)
    
    print("\n=== MAPPING CONFIGURATION ===")
    print(f"target_column: {field_mapping.target_column}")
    print(f"xml_attribute: {field_mapping.xml_attribute}")
    print(f"mapping_type: {field_mapping.mapping_type}")
    print(f"expression: {field_mapping.expression[:100]}...")
    print(f"enum_name: {field_mapping.enum_name}")
    print(f"data_type: {field_mapping.data_type}")
    
    # Test with "WENDY"
    input_value = "WENDY"
    context_data = {"chk_requested_by": "WENDY"}
    
    print(f"\n=== INPUT ===")
    print(f"input_value: {input_value}")
    print(f"context_data: {context_data}")
    
    # Step 1: Test calculated_field directly
    print(f"\n=== STEP 1: _apply_calculated_field_mapping ===")
    result_calculated = mapper._apply_calculated_field_mapping(input_value, field_mapping, context_data)
    print(f"Result: {result_calculated}")
    print(f"Type: {type(result_calculated)}")
    
    # Step 2: Test full transformation chain
    print(f"\n=== STEP 2: _apply_field_transformation (full chain) ===")
    
    # Manually trace through the chain
    mapping_types = field_mapping.mapping_type
    current_value = input_value
    original_value = input_value
    
    print(f"Starting value: {current_value}")
    print(f"Mapping types to apply: {mapping_types}")
    
    for i, mapping_type in enumerate(mapping_types):
        print(f"\n--- Iteration {i+1}: {mapping_type} ---")
        print(f"Input to this step: {current_value} (type: {type(current_value)})")
        
        # Check for conditional enum fallback
        if (mapping_type == 'enum' and i > 0 and 
            mapping_types[i-1] == 'calculated_field' and 
            current_value is None):
            print(f"ENUM FALLBACK TRIGGERED: restoring original value '{original_value}'")
            current_value = original_value
        
        # Apply the mapping type
        print(f"About to call _apply_single_mapping_type with: value={current_value}, type={mapping_type}")
        current_value = mapper._apply_single_mapping_type(current_value, mapping_type, field_mapping, context_data)
        
        print(f"Output from this step: {current_value} (type: {type(current_value)})")
        
        # Check break conditions
        if current_value is None and mapping_type not in ['enum', 'default_getutcdate_if_null']:
            next_is_enum = (i + 1 < len(mapping_types) and mapping_types[i + 1] == 'enum')
            if not next_is_enum:
                print(f"BREAKING: None value and next is not enum")
                break
            else:
                print(f"CONTINUING: Next is enum (fallback pattern)")
    
    print(f"\n=== FINAL MANUAL RESULT ===")
    print(f"Final value: {current_value}")
    print(f"Type: {type(current_value)}")
    
    # Now test the actual method
    print(f"\n=== ACTUAL _apply_field_transformation ===")
    actual_result = mapper._apply_field_transformation(input_value, field_mapping, context_data)
    print(f"Result: {actual_result}")
    print(f"Type: {type(actual_result)}")
    
    assert actual_result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected WENDY email, got {actual_result}"
