"""
Tests for boolean/bit field conversions - validates char_to_bit and boolean_to_bit mappings.

These tests are designed to catch the bug where bit conversion was happening in Python
truthiness checks instead of using the actual conversion mappings from the contract.
"""

import pytest

from xml_extractor.mapping.data_mapper import DataMapper


class TestBitConversions:
    """Test suite for char_to_bit and boolean_to_bit conversion logic."""
    
    @pytest.fixture
    def data_mapper(self):
        """Fixture providing initialized DataMapper."""
        mapper = DataMapper()
        return mapper
    
    # ============================================================================
    # char_to_bit Conversion Tests (Y/N → 1/0)
    # ============================================================================
    
    def test_char_to_bit_y_converts_to_1(self, data_mapper):
        """Test that 'Y' (and 'y') converts to 1."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # Test uppercase Y
        result = data_mapper._apply_single_mapping_type("Y", "char_to_bit", mapping)
        assert result == 1, f"Expected 'Y' to convert to 1, got {result}"
        
        # Test lowercase y
        result = data_mapper._apply_single_mapping_type("y", "char_to_bit", mapping)
        assert result == 1, f"Expected 'y' to convert to 1, got {result}"
    
    def test_char_to_bit_n_converts_to_0(self, data_mapper):
        """Test that 'N' (and 'n') converts to 0."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # Test uppercase N
        result = data_mapper._apply_single_mapping_type("N", "char_to_bit", mapping)
        assert result == 0, f"Expected 'N' to convert to 0, got {result}"
        
        # Test lowercase n
        result = data_mapper._apply_single_mapping_type("n", "char_to_bit", mapping)
        assert result == 0, f"Expected 'n' to convert to 0, got {result}"
    
    # ============================================================================
    # boolean_to_bit Conversion Tests (true/false → 1/0)
    # ============================================================================
    
    def test_boolean_to_bit_true_converts_to_1(self, data_mapper):
        """Test that 'true'/'True' converts to 1."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["boolean_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # Test lowercase
        result = data_mapper._apply_single_mapping_type("true", "boolean_to_bit", mapping)
        assert result == 1, f"Expected 'true' to convert to 1, got {result}"
        
        # Test uppercase
        result = data_mapper._apply_single_mapping_type("True", "boolean_to_bit", mapping)
        assert result == 1, f"Expected 'True' to convert to 1, got {result}"
    
    def test_boolean_to_bit_false_converts_to_0(self, data_mapper):
        """Test that 'false'/'False' converts to 0."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["boolean_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # Test lowercase
        result = data_mapper._apply_single_mapping_type("false", "boolean_to_bit", mapping)
        assert result == 0, f"Expected 'false' to convert to 0, got {result}"
        
        # Test uppercase
        result = data_mapper._apply_single_mapping_type("False", "boolean_to_bit", mapping)
        assert result == 0, f"Expected 'False' to convert to 0, got {result}"
    
    # ============================================================================
    # Real-World XML Test Cases (from generate_mock_xml.py)
    # ============================================================================
    
    def test_signature_ind_n_should_be_0(self, data_mapper):
        """
        Real-world test: signature_ind="N" should become signature_flag=0.
        From generate_mock_xml.py: signature_ind="N"
        """
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application",
            xml_attribute="signature_ind",
            target_table="app_operational_cc",
            target_column="signature_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        result = data_mapper._apply_single_mapping_type("N", "char_to_bit", mapping)
        assert result == 0, f"signature_ind='N' should convert to 0, but got {result}"
    
    def test_auth_user_is_spouse_n_should_be_0(self, data_mapper):
        """
        Real-world test: auth_user_is_spouse="N" should become auth_user_spouse_flag=0.
        From generate_mock_xml.py: auth_user_is_spouse="N"
        """
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/rmts_info",
            xml_attribute="auth_user_is_spouse",
            target_table="app_operational_cc",
            target_column="auth_user_spouse_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        result = data_mapper._apply_single_mapping_type("N", "char_to_bit", mapping)
        assert result == 0, f"auth_user_is_spouse='N' should convert to 0, but got {result}"
    
    def test_esign_consent_flag_false_should_be_0(self, data_mapper):
        """
        Real-world test: esign_consent_flag="false" should become esign_consent_flag=0.
        From generate_mock_xml.py: esign_consent_flag="false"
        """
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application",
            xml_attribute="esign_consent_flag",
            target_table="app_contact_base",
            target_column="esign_consent_flag",
            data_type="bit",
            mapping_type=["boolean_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        result = data_mapper._apply_single_mapping_type("false", "boolean_to_bit", mapping)
        assert result == 0, f"esign_consent_flag='false' should convert to 0, but got {result}"
    
    def test_sms_consent_flag_false_should_be_0(self, data_mapper):
        """
        Real-world test: sms_consent_flag="false" should become sms_consent_flag=0.
        This one works correctly (as user noted), so verify it stays working.
        """
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/contact",
            xml_attribute="sms_consent_flag",
            target_table="app_contact_base",
            target_column="sms_consent_flag",
            data_type="bit",
            mapping_type=["boolean_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        result = data_mapper._apply_single_mapping_type("false", "boolean_to_bit", mapping)
        assert result == 0, f"sms_consent_flag='false' should convert to 0, but got {result}"
    
    def test_income_source_nontaxable_flag_f_should_be_0(self, data_mapper):
        """
        Real-world test: b_income_source_nontaxable="F" should become income_source_nontaxable_flag=0.
        From generate_mock_xml.py: b_income_source_nontaxable="F"
        """
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/contact/contact_employment",
            xml_attribute="b_income_source_nontaxable",
            target_table="app_contact_employment",
            target_column="income_source_nontaxable_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        result = data_mapper._apply_single_mapping_type("F", "char_to_bit", mapping)
        assert result == 0, f"b_income_source_nontaxable='F' should convert to 0, but got {result}"
    
    # ============================================================================
    # Edge Cases and Default Values
    # ============================================================================
    
    def test_missing_value_uses_default(self, data_mapper):
        """Test that missing/None values use the default_value from mapping."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # None value should use default
        result = data_mapper._apply_single_mapping_type(None, "char_to_bit", mapping)
        # Should apply default or return the default value
        assert result == 0 or result == "0", f"None value should use default 0, got {result}"
    
    def test_empty_string_uses_default(self, data_mapper):
        """Test that empty strings use the default_value from mapping."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # Empty string should use default
        result = data_mapper._apply_single_mapping_type("", "char_to_bit", mapping)
        # Should apply default or return the default value
        assert result == 0 or result == "0", f"Empty string should use default 0, got {result}"


class TestBitConversionIntegration:
    """Integration tests for bit conversions in full mapping workflow."""
    
    @pytest.fixture
    def data_mapper(self):
        """Fixture providing initialized DataMapper."""
        mapper = DataMapper()
        return mapper
    
    def test_full_field_transformation_with_char_to_bit(self, data_mapper):
        """Test full field transformation pipeline with char_to_bit."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["char_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # Test through _apply_field_transformation
        result = data_mapper._apply_field_transformation("N", mapping)
        assert result == 0, f"Full transformation: 'N' should become 0, got {result}"
        
        result = data_mapper._apply_field_transformation("Y", mapping)
        assert result == 1, f"Full transformation: 'Y' should become 1, got {result}"
    
    def test_full_field_transformation_with_boolean_to_bit(self, data_mapper):
        """Test full field transformation pipeline with boolean_to_bit."""
        from xml_extractor.models import FieldMapping
        
        mapping = FieldMapping(
            xml_path="/test",
            xml_attribute="test_flag",
            target_table="test_table",
            target_column="test_flag",
            data_type="bit",
            mapping_type=["boolean_to_bit"],
            nullable=False,
            required=True,
            default_value="0"
        )
        
        # Test through _apply_field_transformation
        result = data_mapper._apply_field_transformation("false", mapping)
        assert result == 0, f"Full transformation: 'false' should become 0, got {result}"
        
        result = data_mapper._apply_field_transformation("true", mapping)
        assert result == 1, f"Full transformation: 'true' should become 1, got {result}"
