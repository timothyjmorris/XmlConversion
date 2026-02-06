"""
Unit tests for authu_contact mapping type.

The authu_contact mapping type extracts values from AUTHU (Authorized User) contacts
instead of PR (Primary) contacts. This is used for fields like auth_user_issue_card_flag.
"""

import pytest
from lxml import etree
from xml_extractor.mapping.data_mapper import DataMapper


class TestAuthuContactMapping:
    """Test suite for authu_contact mapping type extraction."""
    
    @pytest.fixture
    def sample_xml_with_authu(self):
        """XML with both PR and AUTHU contacts having app_prod_bcard elements."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <application app_id="12345">
            <contact con_id="1001" ac_role_tp_c="PR" first_name="John">
                <app_prod_bcard issue_card_ind="Y" card_type="VISA"/>
            </contact>
            <contact con_id="1002" ac_role_tp_c="AUTHU" first_name="Jane">
                <app_prod_bcard issue_card_ind="N" card_type="MC"/>
            </contact>
        </application>
        """
    
    @pytest.fixture
    def sample_xml_no_authu(self):
        """XML with only PR contact, no AUTHU."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <application app_id="12345">
            <contact con_id="1001" ac_role_tp_c="PR" first_name="John">
                <app_prod_bcard issue_card_ind="Y" card_type="VISA"/>
            </contact>
        </application>
        """
    
    @pytest.fixture
    def sample_xml_multiple_authu(self):
        """XML with multiple AUTHU contacts - should use the last one."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <application app_id="12345">
            <contact con_id="1001" ac_role_tp_c="PR" first_name="John">
                <app_prod_bcard issue_card_ind="Y" card_type="VISA"/>
            </contact>
            <contact con_id="1002" ac_role_tp_c="AUTHU" first_name="Jane">
                <app_prod_bcard issue_card_ind="N" card_type="MC"/>
            </contact>
            <contact con_id="1003" ac_role_tp_c="AUTHU" first_name="Bob">
                <app_prod_bcard issue_card_ind="Y" card_type="AMEX"/>
            </contact>
        </application>
        """
    
    @pytest.fixture
    def data_mapper(self):
        """DataMapper instance with default contract (uses production contract)."""
        return DataMapper()
    
    def test_authu_contact_extracts_from_authu_not_pr(self, data_mapper, sample_xml_with_authu):
        """Verify authu_contact extracts from AUTHU contact, not PR contact."""
        # Parse XML and set it on the data mapper
        tree = etree.fromstring(sample_xml_with_authu.encode())
        data_mapper._current_xml_tree = tree
        
        # Create a mock mapping for issue_card_ind from app_prod_bcard
        class MockMapping:
            target_column = "auth_user_issue_card_flag"
            xml_path = "contact/app_prod_bcard"
            xml_attribute = "issue_card_ind"
            data_type = "string"
            data_length = 1
        
        mapping = MockMapping()
        
        # Extract using authu_contact
        result = data_mapper._extract_from_authu_contact(mapping)
        
        # Should get 'N' from AUTHU contact (con_id=1002), not 'Y' from PR contact (con_id=1001)
        assert result == "N", f"Expected 'N' from AUTHU contact, got '{result}'"
    
    def test_authu_contact_returns_none_when_no_authu(self, data_mapper, sample_xml_no_authu):
        """Verify authu_contact returns None when no AUTHU contact exists."""
        tree = etree.fromstring(sample_xml_no_authu.encode())
        data_mapper._current_xml_tree = tree
        
        class MockMapping:
            target_column = "auth_user_issue_card_flag"
            xml_path = "contact/app_prod_bcard"
            xml_attribute = "issue_card_ind"
            data_type = "string"
            data_length = 1
        
        mapping = MockMapping()
        result = data_mapper._extract_from_authu_contact(mapping)
        
        # Should return None when no AUTHU contact exists
        assert result is None, f"Expected None when no AUTHU contact, got '{result}'"
    
    def test_authu_contact_uses_last_authu_when_multiple(self, data_mapper, sample_xml_multiple_authu):
        """Verify authu_contact uses the last AUTHU contact when multiple exist."""
        tree = etree.fromstring(sample_xml_multiple_authu.encode())
        data_mapper._current_xml_tree = tree
        
        class MockMapping:
            target_column = "auth_user_issue_card_flag"
            xml_path = "contact/app_prod_bcard"
            xml_attribute = "issue_card_ind"
            data_type = "string"
            data_length = 1
        
        mapping = MockMapping()
        result = data_mapper._extract_from_authu_contact(mapping)
        
        # Should get 'Y' from last AUTHU contact (con_id=1003), not 'N' from first AUTHU (con_id=1002)
        assert result == "Y", f"Expected 'Y' from last AUTHU contact, got '{result}'"
    
    def test_authu_contact_extracts_direct_attribute(self, data_mapper, sample_xml_with_authu):
        """Verify authu_contact can extract attributes directly from contact element."""
        tree = etree.fromstring(sample_xml_with_authu.encode())
        data_mapper._current_xml_tree = tree
        
        class MockMapping:
            target_column = "auth_user_first_name"
            xml_path = "contact"
            xml_attribute = "first_name"
            data_type = "string"
            data_length = 50
        
        mapping = MockMapping()
        result = data_mapper._extract_from_authu_contact(mapping)
        
        # Should get 'Jane' from AUTHU contact, not 'John' from PR contact
        assert result == "Jane", f"Expected 'Jane' from AUTHU contact, got '{result}'"


