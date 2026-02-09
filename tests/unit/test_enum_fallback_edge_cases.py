"""
Unit tests for edge cases in conditional enum fallback pattern.

Tests safeguards against:
- Missing attributes in context_data
- Nested structure handling (attributes key)
- Type mismatches (numeric vs string)
- Whitespace handling
- Empty string vs None distinction
"""

import pytest
from pathlib import Path
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping


class MockMapping:
    """Minimal mock for Field Mapping to test transformation logic."""
    def __init__(self, mapping_type, expression=None, enum_name=None, data_type="string", 
                 xml_attribute="test_field"):
        self.xml_path = "/Provenir/Request/CustData/test_element"
        self.xml_attribute = xml_attribute
        self.target_table = "test_table"
        self.target_column = "test_column"
        self.mapping_type = mapping_type
        self.expression = expression
        self.enum_name = enum_name
        self.data_type = data_type
        self.nullable = True
        self.required = False
        self.default_value = None


@pytest.fixture
def mapper():
    """Create DataMapper using real RL contract with DEBUG logging to capture warnings."""
    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract_rl.json"
    return DataMapper(str(contract_path), log_level='DEBUG')


def test_context_data_missing_attribute(mapper):
    """
    SAFEGUARD: Warn when attribute not found in context_data.
    
    Scenario:
    - calculated_field returns NULL
    - context_data doesn't have the attribute
    - Should log warning and return None (column excluded)
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN test_field LIKE '%MATCH%' THEN 'result' END",
        enum_name="officer_code_to_email_enum",
        xml_attribute="missing_attribute"
    )
    
    # Context has other keys but not the one we need
    context_data = {"other_key": "value", "another_key": "value2"}
    
    # This should log a warning and return None
    result = mapper._apply_field_transformation("__CALCULATED_FIELD_SENTINEL__", mapping, context_data)
    assert result is None, "Should return None when attribute not in context"


def test_nested_structure_with_attributes_key(mapper):
    """
    SAFEGUARD: Handle nested structures with 'attributes' key.
    
    Scenario:
    - context_data = {"attributes": {"test_field": "6010"}}
    - Should check attributes subkey when not found at top level
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN test_field LIKE '%NOMATCH%' THEN 'result' END",
        enum_name="officer_code_to_email_enum",
        xml_attribute="chk_requested_by"
    )
    
    # Nested structure like contact/address/employment tables
    context_data = {
        "attributes": {
            "chk_requested_by": "6010"
        },
        "other_data": "value"
    }
    
    result = mapper._apply_field_transformation("__CALCULATED_FIELD_SENTINEL__", mapping, context_data)
    # Should find "6010" in attributes and map it via enum
    assert result == "wendy.dotson@merrickbank.com"


def test_type_conversion_numeric_to_string(mapper):
    """
    SAFEGUARD: Type conversion handles numeric values.
    
    Scenario:
    - XML value extracted as integer 6010 (not string "6010")
    - Enum expects string keys
    - Calculated field doesn't match (expression looks for 9999)
    - Should convert to string and match via enum fallback
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN chk_requested_by = 9999 THEN 'result' END",  # Won't match 6010
        enum_name="officer_code_to_email_enum",
        xml_attribute="chk_requested_by"
    )
    
    # Numeric value in context (as if extracted from XML as number)
    context_data = {"chk_requested_by": 6010}  # int, not string
    
    result = mapper._apply_field_transformation("__CALCULATED_FIELD_SENTINEL__", mapping, context_data)
    # Calculated field returns None (6010 != 9999), enum fallback converts 6010 -> "6010" and maps
    assert result == "wendy.dotson@merrickbank.com"


def test_whitespace_trimming(mapper):
    """
    SAFEGUARD: Whitespace trimming for enum lookup.
    
    Scenario:
    - XML value has leading/trailing spaces: " 6010 "
    - Should strip spaces and match enum key "6010"
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN test_field LIKE '%NOMATCH%' THEN 'result' END",
        enum_name="officer_code_to_email_enum",
        xml_attribute="chk_requested_by"
    )
    
    # Value with whitespace
    context_data = {"chk_requested_by": "  6010  "}
    
    result = mapper._apply_field_transformation("__CALCULATED_FIELD_SENTINEL__", mapping, context_data)
    # Should trim and match
    assert result == "wendy.dotson@merrickbank.com"


def test_empty_string_becomes_none_triggers_fallback(mapper):
    """
    SAFEGUARD: Empty string after strip becomes None.
    
    Scenario:
    - XML has "   " (only whitespace)
    - After strip becomes ""
    - Should treat as None and trigger enum fallback
    - But enum also can't map empty string, so final result is None
    """
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN test_field LIKE '%NOMATCH%' THEN 'result' END",
        enum_name="officer_code_to_email_enum",
        xml_attribute="chk_requested_by"
    )
    
    # Value is only whitespace
    context_data = {"chk_requested_by": "    "}
    
    result = mapper._apply_field_transformation("__CALCULATED_FIELD_SENTINEL__", mapping, context_data)
    # Empty string after strip -> None, enum can't map it
    assert result is None


def test_both_failures_logged(mapper, caplog):
    """
    SAFEGUARD: Log warning when both calculated_field and enum fail.
    
    Scenario:
    - Calculated field returns NULL
    - Attribute not in context (extraction fails)
    - Should log TWO warnings: one for missing attr, one for double failure
    """
    import logging
    caplog.set_level(logging.WARNING)
    
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN test_field LIKE '%NOMATCH%' THEN 'result' END",
        enum_name="officer_code_to_email_enum",
        xml_attribute="nonexistent_field"
    )
    
    context_data = {"other_key": "value"}
    
    result = mapper._apply_field_transformation("__CALCULATED_FIELD_SENTINEL__", mapping, context_data)
    
    assert result is None
    # Should have warnings about missing attribute and double failure
    assert any("Could not extract" in record.message for record in caplog.records)
    assert any("Both calculated_field and original XML extraction" in record.message for record in caplog.records)


def test_enum_lookup_failure_logged(mapper, caplog):
    """
    SAFEGUARD: Log INFO when enum lookup fails for valid code.
    
    Scenario:
    - Calculated field returns NULL
    - Original value is "9999" (not in enum)
    - Should log INFO about enum lookup failure
    """
    import logging
    caplog.set_level(logging.INFO)
    
    mapping = MockMapping(
        mapping_type=["calculated_field", "enum"],
        expression="CASE WHEN test_field LIKE '%NOMATCH%' THEN 'result' END",
        enum_name="officer_code_to_email_enum",
        xml_attribute="chk_requested_by"
    )
    
    context_data = {"chk_requested_by": "9999"}  # Invalid code
    
    result = mapper._apply_field_transformation("__CALCULATED_FIELD_SENTINEL__", mapping, context_data)
    
    assert result is None
    # Should log that enum lookup failed
    assert any("Enum mapping returned None" in record.message for record in caplog.records)
