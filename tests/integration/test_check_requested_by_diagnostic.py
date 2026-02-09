"""
Integration test to diagnose the actual data flow through DataMapper for check_requested_by_user.

This will help us understand where the value is being lost.
"""

import pytest
import json
from pathlib import Path
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping


@pytest.fixture
def rl_contract():
    """Load RL contract."""
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
    with open(contract_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


@pytest.fixture
def mapper():
    """Create DataMapper with RL contract."""
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
    return DataMapper(str(contract_path))


def test_check_requested_by_user_direct_transformation(rl_contract, mapper):
    """Test the _apply_field_transformation directly with the actual contract entry."""
    
    # Get the actual contract mapping for check_requested_by_user
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'check_requested_by_user'
    )
    
    field_mapping = FieldMapping(**mapping_dict)
    
    print(f"\n=== Field Mapping Details ===")
    print(f"target_column: {field_mapping.target_column}")
    print(f"xml_attribute: {field_mapping.xml_attribute}")
    print(f"mapping_type: {field_mapping.mapping_type}")
    print(f"expression: {field_mapping.expression[:100]}...")
    print(f"enum_name: {field_mapping.enum_name}")
    
    # Test with "WENDY" (name format - should match calculated_field)
    context_data = {"chk_requested_by": "WENDY"}
    
    print(f"\n=== Testing with WENDY ===")
    print(f"Context data: {context_data}")
    
    result = mapper._apply_field_transformation("WENDY", field_mapping, context_data)
    
    print(f"Result: {result}")
    print(f"Result type: {type(result)}")
    
    assert result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected WENDY email, got {result}"


def test_check_requested_by_with_full_xml_context(rl_contract, mapper):
    """Test with simulated full XML context like the real pipeline."""
    
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'check_requested_by_user'
    )
    
    field_mapping = FieldMapping(**mapping_dict)
    
    # Simulate the context data structure that comes from XMLParser.extract_elements()
    # This might include nested structures
    full_context = {
        "IL_fund_checklist": [
            {
                "attributes": {
                    "chk_requested_by": "WENDY",
                    "ct_correct_contract_state": "Y",
                    # ... other attributes
                }
            }
        ],
        # Also add flattened version
        "chk_requested_by": "WENDY"
    }
    
    print(f"\n=== Testing with Full XML Context ===")
    print(f"Context keys: {list(full_context.keys())}")
    
    result = mapper._apply_field_transformation("WENDY", field_mapping, full_context)
    
    print(f"Result: {result}")
    
    assert result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected WENDY email, got {result}"


def test_apply_calculated_field_mapping_directly(rl_contract, mapper):
    """Test _apply_calculated_field_mapping method directly."""
    
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'check_requested_by_user'
    )
    
    field_mapping = FieldMapping(**mapping_dict)
    
    context_data = {"chk_requested_by": "WENDY"}
    
    print(f"\n=== Testing _apply_calculated_field_mapping directly ===")
    print(f"Expression: {field_mapping.expression[:100]}...")
    print(f"Context: {context_data}")
    
    result = mapper._apply_calculated_field_mapping("WENDY", field_mapping, context_data)
    
    print(f"Result from calculated_field: {result}")
    print(f"Result type: {type(result)}")
    
    assert result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected email, got {result}"
