#!/usr/bin/env python3
"""
Test case for DQ3 - Required Enum Validation

This test validates that required (NOT NULL) enum fields properly fail
when no valid mapping exists and no default is provided, implementing
the critical fix identified in CODE_REVIEW_AND_ACTION_PLAN.md.
"""

import pytest
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping
from xml_extractor.exceptions import DataMappingError


class TestRequiredEnumValidation:
    """Test required enum field validation (DQ3 fix)."""
    
    def test_required_enum_fails_without_mapping_or_default(self):
        """
        Test that required enum fields fail fast when no valid mapping exists.
        
        This implements the DQ3 fix where required enum fields should raise
        DataMappingError instead of silently returning None.
        """
        # Create a DataMapper instance
        mapper = DataMapper()
        
        # Create a required (NOT NULL) enum field mapping without default_value
        required_enum_mapping = FieldMapping(
            xml_path="/test/path",
            target_table="test_table", 
            target_column="required_enum_field",
            data_type="int",
            mapping_type=["enum"],
            nullable=False,  # This makes it required
            # No default_value defined
        )
        
        # Test that invalid enum value raises DataMappingError for required field
        with pytest.raises(DataMappingError, match="Required enum field 'required_enum_field' has no valid mapping"):
            mapper._apply_enum_mapping("INVALID_VALUE", required_enum_mapping)
    
    def test_nullable_enum_returns_none_without_mapping(self):
        """
        Test that nullable enum fields return None when no valid mapping exists.
        
        This verifies the existing behavior is preserved for nullable fields.
        """
        # Create a DataMapper instance
        mapper = DataMapper()
        
        # Create a nullable enum field mapping
        nullable_enum_mapping = FieldMapping(
            xml_path="/test/path",
            target_table="test_table",
            target_column="nullable_enum_field", 
            data_type="int",
            mapping_type=["enum"],
            nullable=True,  # This makes it optional
        )
        
        # Test that invalid enum value returns None for nullable field
        result = mapper._apply_enum_mapping("INVALID_VALUE", nullable_enum_mapping)
        assert result is None
    
    def test_required_enum_uses_default_when_no_mapping(self):
        """
        Test that required enum fields use default_value when no mapping exists.
        
        This tests the fallback behavior for required fields with defaults.
        """
        # Create a DataMapper instance  
        mapper = DataMapper()
        
        # Create a required enum field mapping WITH default_value
        required_enum_with_default = FieldMapping(
            xml_path="/test/path",
            target_table="test_table",
            target_column="required_enum_with_default",
            data_type="int", 
            mapping_type=["enum"],
            nullable=False,  # Required
            default_value=999  # Has default
        )
        
        # Test that invalid enum value uses default for required field with default
        result = mapper._apply_enum_mapping("INVALID_VALUE", required_enum_with_default)
        assert result == 999