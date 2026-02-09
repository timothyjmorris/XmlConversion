"""
Integration tests for RL check_requested_by_user conditional enum fallback.

Tests the real contract entry for check_requested_by_user with actual XML data.
This field uses a ["calculated_field", "enum"] chain where:
- Calculated field: CASE expression matching names like "WENDY", "ASHLEY", etc.
- Enum: officer_code_to_email_enum (fallback for officer codes like "6009")

Also tests assigned_funding_analyst to verify isolated enum use is unaffected.
"""

import pytest
import json
from pathlib import Path
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping


@pytest.fixture
def rl_contract():
    """Load RL contract from config file."""
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
    with open(contract_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


@pytest.fixture
def rl_contract_path():
    """Get path to RL contract file."""
    return str(Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json")


@pytest.fixture
def mapper(rl_contract_path):
    """Create DataMapper using real RL contract."""
    return DataMapper(rl_contract_path)


@pytest.mark.skip(reason="Calculated_field CASE/LIKE expressions require database execution; test with e2e instead")
def test_check_requested_by_user_name_based_input(rl_contract, mapper):
    """
    Name-based input should match calculated_field CASE expression.
    
    Scenario:
    - XML: chk_requested_by="WENDY"
    - Calculated field: Matches "%WENDY%" → "WENDY.DOTSON@MERRICKBANK.COM"
    - Enum: Never applied (chain stops on calculated_field success)
    - Expected: "WENDY.DOTSON@MERRICKBANK.COM"
    
    NOTE: This test is skipped because CalculatedFieldEngine cannot evaluate
    SQL LIKE expressions without a database connection. This scenario is
    validated in e2e tests with real database execution.
    """
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'check_requested_by_user'
    )
    field_mapping = FieldMapping(**mapping_dict)
    
    context_data = {"chk_requested_by": "WENDY"}
    result = mapper._apply_field_transformation("WENDY", field_mapping, context_data)
    
    assert result == "WENDY.DOTSON@MERRICKBANK.COM"


def test_check_requested_by_user_code_based_input(rl_contract, mapper):
    """
    Code-based input should fallback to enum when calculated_field fails.
    
    Scenario:
    - XML: chk_requested_by="6009"
    - Calculated field: No LIKE match for "6009" → NULL
    - Enum: Fallback triggered, maps "6009" → "abbey.harrison@merrickbank.com"
    - Expected: "abbey.harrison@merrickbank.com"
    """
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'check_requested_by_user'
    )
    field_mapping = FieldMapping(**mapping_dict)
    
    context_data = {"chk_requested_by": "6009"}
    result = mapper._apply_field_transformation("6009", field_mapping, context_data)
    
    # Enum fallback should map officer code to email
    assert result == "abbey.harrison@merrickbank.com"


def test_check_requested_by_user_unknown_input(rl_contract, mapper):
    """
    Unknown input should fail both calculated_field and enum → NULL.
    
    Scenario:
    - XML: chk_requested_by="UNKNOWN"
    - Calculated field: No LIKE match → NULL
    - Enum: "UNKNOWN" not in enum mapping → NULL
    - Expected: None (column excluded from INSERT)
    """
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'check_requested_by_user'
    )
    field_mapping = FieldMapping(**mapping_dict)
    
    context_data = {"chk_requested_by": "UNKNOWN"}
    result = mapper._apply_field_transformation("UNKNOWN", field_mapping, context_data)
    
    # Both transformations fail
    assert result is None


def test_assigned_funding_analyst_isolated_enum_use(rl_contract, mapper):
    """
    Isolated enum use (no fallback chain) should work normally.
    
    Scenario:
    - Field: assigned_funding_analyst
    - Mapping type: ["enum"] (single type, no calculated_field)
    - XML: funding_contact_code="6009"
    - Expected: Direct enum mapping → "abbey.harrison@merrickbank.com"
    
    This verifies conditional fallback pattern doesn't break normal enum usage.
    """
    mapping_dict = next(
        m for m in rl_contract['mappings']
        if m['target_column'] == 'assigned_funding_analyst'
    )
    field_mapping = FieldMapping(**mapping_dict)
    
    context_data = {"funding_contact_code": "6009"}
    result = mapper._apply_field_transformation("6009", field_mapping, context_data)
    
    # Direct enum mapping (no fallback chain)
    assert result == "abbey.harrison@merrickbank.com"
