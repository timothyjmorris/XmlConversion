"""
Unit tests for conditional enum fallback chaining in DataMapper.

Tests the RL Phase 4 pattern where ["calculated_field", "enum"] chains together.
When calculated_field returns NULL, enum should operate on the original XML value
as a fallback mechanism.

Key Behaviors Tested:
- Enum fallback triggered when calculated_field returns None
- Enum fallback triggered when calculated_field returns empty string
- Enum NOT applied when calculated_field returns a valid value
- Enum fallback uses original XML value, not None
- Both transformations fail → column excluded (None returned)
- Isolated enum use (no fallback) works normally
"""

import pytest
from pathlib import Path
import json
from xml_extractor.mapping.data_mapper import DataMapper


class MockMapping:
    """Minimal mock for Field Mapping to test transformation logic."""
    def __init__(self, mapping_type, expression=None, enum_name=None, data_type="string", 
                 data_length=None, nullable=True, xml_attribute="chk_requested_by"):
        self.xml_path = "/Provenir/Request/CustData/IL_application/IL_fund_checklist"
        self.xml_attribute = xml_attribute
        self.target_table = "app_funding_checklist_rl"
        self.target_column = "check_requested_by_user"
        self.mapping_type = mapping_type
        self.expression = expression
        self.enum_name = enum_name
        self.data_type = data_type
        self.data_length = data_length
        self.nullable = nullable
        self.required = False
        self.default_value = None


@pytest.fixture
def mapper():
    """Create DataMapper using real RL contract (which has officer_code_to_email_enum)."""
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
    return DataMapper(str(contract_path))


def test_enum_fallback_when_calculated_field_returns_null(mapper):
    """
    When calculated_field returns NULL, enum should try mapping original value.
    
    Scenario:
    - Original XML value: "6009" (officer code)
    - Calculated field: CASE expression that doesn't match → returns NULL
    - Expected: Enum fallback maps "6009" → "abbey.harrison@merrickbank.com"
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN chk_requested_by LIKE '%WENDY%' THEN 'wendy.dotson@merrickbank.com' END",
        enum_name="officer_code_to_email_enum"
    )
    
    context_data = {"chk_requested_by": "6009"}  # Officer code input
    result = mapper._apply_field_transformation("6009", mapping, context_data)
    assert result == "abbey.harrison@merrickbank.com"


def test_enum_fallback_when_calculated_field_returns_empty(mapper):
    """
    When calculated_field returns empty string (treated as None), enum should try mapping.
    
    Scenario:
    - Original XML value: "6019" (valid officer code for Alyssa)
    - Calculated field: Returns "" (empty string, treated as NULL by chain)
    - Expected: Enum fallback maps "6019" → "alyssa.rapotez@merrickbank.com"
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN chk_requested_by LIKE '%NONEXISTENT%' THEN '' END",
        enum_name="officer_code_to_email_enum"
    )
    
    context_data = {"chk_requested_by": "6019"}
    result = mapper._apply_field_transformation("6019", mapping, context_data)
    # Empty string from calculated_field is None after strip, triggers enum fallback
    assert result == "alyssa.rapotez@merrickbank.com"


def test_enum_not_applied_when_calculated_field_returns_value(mapper):
    """
    When calculated_field returns a valid value, enum should NOT be applied.
    
    Scenario:
    - Original XML value: "WENDY"
    - Calculated field: Matches "WENDY" → returns "wendy.dotson@merrickbank.com"
    - Expected: Calculated value used, enum skipped (chain stops on success)
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN chk_requested_by LIKE '%WENDY%' THEN 'wendy.dotson@merrickbank.com' END",
        enum_name="officer_code_to_email_enum"
    )
    
    context_data = {"chk_requested_by": "WENDY"}
    result = mapper._apply_field_transformation("WENDY", mapping, context_data)
    # Calculated field succeeds, enum never applied
    assert result == "wendy.dotson@merrickbank.com"


def test_enum_fallback_uses_original_value(mapper):
    """
    Enum fallback must use original XML value, not the NULL from calculated_field.
    
    Scenario:
    - Original XML value: "6010" (valid officer code for Wendy)
    - Calculated field: Returns NULL (current_value becomes None)
    - Expected: Enum operates on "6010" (original), not None
    - Result: "wendy.dotson@merrickbank.com"
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN chk_requested_by = 'NOMATCH' THEN 'result' END",
        enum_name="officer_code_to_email_enum"
    )
    
    context_data = {"chk_requested_by": "6010"}
    result = mapper._apply_field_transformation("6010", mapping, context_data)
    # Verifies original value "6010" was used, not None
    assert result == "wendy.dotson@merrickbank.com"


def test_both_fail_column_excluded(mapper):
    """
    When both calculated_field and enum fail, column should be excluded (None).
    
    Scenario:
    - Original XML value: "UNKNOWN"
    - Calculated field: No match → NULL
    - Enum: "UNKNOWN" not in enum mapping → NULL
    - Expected: None (column excluded from INSERT)
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN chk_requested_by LIKE '%WENDY%' THEN 'wendy.dotson@merrickbank.com' END",
        enum_name="officer_code_to_email_enum"
    )
    
    context_data = {"chk_requested_by": "UNKNOWN"}
    result = mapper._apply_field_transformation("UNKNOWN", mapping, context_data)
    assert result is None


def test_isolated_enum_without_fallback(mapper):
    """
    Enum used in isolation (not as fallback) should work normally.
    
    Scenario:
    - Field: assigned_funding_analyst
    - Mapping type: ["enum"] (single type, no calculated_field)
    - Original XML value: "6009"
    - Expected: Direct enum mapping → "abbey.harrison@merrickbank.com"
    
    This verifies the fallback pattern doesn't break normal enum usage.
    """
    mapping = MockMapping(
        mapping_type=["enum"],
        enum_name="officer_code_to_email_enum"
    )
    
    result = mapper._apply_field_transformation("6009", mapping, None)
    assert result == "abbey.harrison@merrickbank.com"
