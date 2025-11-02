"""
Tests for extract_numeric mapping type - validates numeric extraction from formatted strings.

These tests verify that the extract_numeric mapping type correctly:
1. Extracts numeric values from strings with non-numeric characters
2. Handles edge cases (empty strings, null values, multiple numbers)
3. Applies proper type conversion after extraction
"""

import pytest
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping


class TestExtractNumeric:
    """Test suite for extract_numeric mapping type logic."""
    
    @pytest.fixture
    def data_mapper(self):
        """Fixture providing initialized DataMapper."""
        mapper = DataMapper()
        return mapper
    
    # ============================================================================
    # Basic Numeric Extraction Tests
    # ============================================================================
    
    def test_extract_numeric_from_currency_format(self, data_mapper):
        """Test extracting numeric value from currency format: 'Up to $40' → 40."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="fee",
            target_table="test_table",
            target_column="fee_amount",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("Up to $40", "extract_numeric", mapping)
        assert result == 40, f"Expected 'Up to $40' to extract to 40, got {result}"
    
    def test_extract_numeric_from_percentage_format(self, data_mapper):
        """Test extracting numeric value from percentage format: '15% APR' → 15."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="rate",
            target_table="test_table",
            target_column="interest_rate",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("15% APR", "extract_numeric", mapping)
        assert result == 15, f"Expected '15% APR' to extract to 15, got {result}"
    
    def test_extract_numeric_from_hyphenated_format(self, data_mapper):
        """Test extracting numeric value from hyphenated format: '$100-$500' → 100500 (all digits)."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="range",
            target_table="test_table",
            target_column="amount",
            data_type="smallint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("$100-$500", "extract_numeric", mapping)
        assert result == 100500, f"Expected '$100-$500' to extract to 100500 (all digits), got {result}"
    
    def test_extract_numeric_from_plain_number(self, data_mapper):
        """Test extracting from plain number string: '42' → 42."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="count",
            target_table="test_table",
            target_column="count_value",
            data_type="int",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("42", "extract_numeric", mapping)
        assert result == 42, f"Expected '42' to remain 42, got {result}"
    
    def test_extract_numeric_from_integer(self, data_mapper):
        """Test extracting from integer value: 40 → 40."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="fee",
            target_table="test_table",
            target_column="fee_amount",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type(40, "extract_numeric", mapping)
        assert result == 40, f"Expected integer 40 to remain 40, got {result}"
    
    # ============================================================================
    # Edge Cases and Empty Values
    # ============================================================================
    
    def test_extract_numeric_from_null_returns_none(self, data_mapper):
        """Test that null/None returns None."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="fee",
            target_table="test_table",
            target_column="fee_amount",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type(None, "extract_numeric", mapping)
        assert result is None, f"Expected None to return None, got {result}"
    
    def test_extract_numeric_from_empty_string_returns_none(self, data_mapper):
        """Test that empty string returns None."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="fee",
            target_table="test_table",
            target_column="fee_amount",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("", "extract_numeric", mapping)
        assert result is None, f"Expected empty string to return None, got {result}"
    
    def test_extract_numeric_from_no_numbers_returns_none(self, data_mapper):
        """Test that string with no numeric characters returns None."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="text",
            target_table="test_table",
            target_column="text_field",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("No numbers here", "extract_numeric", mapping)
        assert result is None, f"Expected string with no numbers to return None, got {result}"
    
    # ============================================================================
    # Different Target Data Types
    # ============================================================================
    
    def test_extract_numeric_to_int(self, data_mapper):
        """Test extract_numeric with int target type."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="value",
            target_table="test_table",
            target_column="int_field",
            data_type="int",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("Amount: 12345", "extract_numeric", mapping)
        assert result == 12345, f"Expected 12345 as int, got {result}"
    
    def test_extract_numeric_to_smallint(self, data_mapper):
        """Test extract_numeric with smallint target type."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="value",
            target_table="test_table",
            target_column="smallint_field",
            data_type="smallint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("Rate: 5%", "extract_numeric", mapping)
        assert result == 5, f"Expected 5 as smallint, got {result}"
    
    def test_extract_numeric_to_bigint(self, data_mapper):
        """Test extract_numeric with bigint target type."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="value",
            target_table="test_table",
            target_column="bigint_field",
            data_type="bigint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("ID: 9223372036854775807", "extract_numeric", mapping)
        assert result == 9223372036854775807, f"Expected large number as bigint, got {result}"
    
    # ============================================================================
    # Real-World Scenarios
    # ============================================================================
    
    def test_extract_numeric_late_payment_fee_real_world(self, data_mapper):
        """
        Real-world test case: late_payment_fee from credit card XML.
        
        Example from actual mapping: 'Up to $40' should extract to 40
        This was the original bug report.
        """
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/rmts_info",
            xml_attribute="late_payment_fee",
            target_table="app_pricing_cc",
            target_column="card_late_payment_fee",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("Up to $40", "extract_numeric", mapping)
        assert result == 40, (
            f"Real-world scenario FAILED: late_payment_fee='Up to $40' should extract to 40, got {result}"
        )
    
    def test_extract_numeric_annual_fee(self, data_mapper):
        """Real-world scenario: annual_fee with currency formatting."""
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/card_info",
            xml_attribute="annual_fee",
            target_table="app_card_features",
            target_column="annual_fee_amount",
            data_type="smallint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("$95 per year", "extract_numeric", mapping)
        assert result == 95, f"Expected annual fee $95 to extract to 95, got {result}"
    
    def test_extract_numeric_cashback_rate(self, data_mapper):
        """Real-world scenario: cashback_rate with percentage formatting."""
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/rewards_info",
            xml_attribute="cashback_rate",
            target_table="app_rewards",
            target_column="cashback_percentage",
            data_type="tinyint",
            mapping_type=["extract_numeric"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("2.5% cashback", "extract_numeric", mapping)
        # Extracts all digits: "2" and "5" -> "25" -> 25
        assert result == 25, f"Expected cashback rate to extract all digits (25), got {result}"


class TestNumbersOnlyAlias:
    """Test that 'numbers_only' mapping type is an alias for 'extract_numeric'."""
    
    @pytest.fixture
    def data_mapper(self):
        """Fixture providing initialized DataMapper."""
        mapper = DataMapper()
        return mapper
    
    def test_numbers_only_alias_works_like_extract_numeric(self, data_mapper):
        """Test that 'numbers_only' mapping type behaves identically to 'extract_numeric'."""
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="fee",
            target_table="test_table",
            target_column="fee_amount",
            data_type="tinyint",
            mapping_type=["numbers_only"],
            nullable=True,
            required=False
        )
        
        result = data_mapper._apply_single_mapping_type("Up to $40", "numbers_only", mapping)
        assert result == 40, f"Expected 'numbers_only' alias to extract to 40, got {result}"
