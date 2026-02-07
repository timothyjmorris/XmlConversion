"""
Unit tests for last_valid_sec_contact mapping type.

The last_valid_sec_contact mapping type extracts values from the last valid
secondary contact (e.g., SEC) instead of the primary (PR) contact. This mirrors
last_valid_pr_contact but selects valid_contact_types[1] from the contract.

Used by RL contract for fields like:
  - app_funding_rl.loanpro_customer_id_sec (contact-level attribute)
  - app_operational_rl.housing_monthly_payment_sec (address child element)
"""

import pytest
from lxml import etree
from xml_extractor.mapping.data_mapper import DataMapper


class TestLastValidSecContactMapping:
    """Test suite for last_valid_sec_contact mapping type extraction."""

    @pytest.fixture
    def sample_xml_pr_and_sec(self):
        """XML with both PR and SEC contacts."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <application app_id="325725">
            <contact con_id="1001" ac_role_tp_c="PR" first_name="John"
                     loanpro_customer_id="5001">
                <contact_address address_type_code="CURR" 
                    residence_monthly_pymnt="1500" city="Denver"/>
            </contact>
            <contact con_id="1002" ac_role_tp_c="SEC" first_name="Jane"
                     loanpro_customer_id="5002">
                <contact_address address_type_code="CURR" 
                    residence_monthly_pymnt="900" city="Boulder"/>
            </contact>
        </application>
        """

    @pytest.fixture
    def sample_xml_no_sec(self):
        """XML with only PR contact, no SEC."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <application app_id="325725">
            <contact con_id="1001" ac_role_tp_c="PR" first_name="John"
                     loanpro_customer_id="5001">
            </contact>
        </application>
        """

    @pytest.fixture
    def sample_xml_multiple_sec(self):
        """XML with multiple SEC contacts - should use the last valid one."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <application app_id="325725">
            <contact con_id="1001" ac_role_tp_c="PR" first_name="John"
                     loanpro_customer_id="5001"/>
            <contact con_id="1002" ac_role_tp_c="SEC" first_name="Jane"
                     loanpro_customer_id="5002"/>
            <contact con_id="1003" ac_role_tp_c="SEC" first_name="Bob"
                     loanpro_customer_id="5003"/>
        </application>
        """

    @pytest.fixture
    def sample_xml_sec_invalid_con_id(self):
        """XML where first SEC has empty con_id - should skip to next valid SEC."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <application app_id="325725">
            <contact con_id="1001" ac_role_tp_c="PR" first_name="John"
                     loanpro_customer_id="5001"/>
            <contact con_id="" ac_role_tp_c="SEC" first_name="Invalid"
                     loanpro_customer_id="9999"/>
            <contact con_id="1003" ac_role_tp_c="SEC" first_name="Valid"
                     loanpro_customer_id="5003"/>
        </application>
        """

    @pytest.fixture
    def data_mapper(self):
        """DataMapper instance configured for SEC contact testing.
        
        Default contract uses ["PR", "AUTHU"]. Override _valid_contact_type_config
        to ["PR", "SEC"] to match RL contract configuration.
        """
        mapper = DataMapper()
        mapper._valid_contact_type_config = ('ac_role_tp_c', ['PR', 'SEC'])
        return mapper

    def _set_xml(self, data_mapper, xml_string):
        """Parse XML string and set it on the data mapper for extraction."""
        tree = etree.fromstring(xml_string.encode())
        data_mapper._current_xml_root = tree
        data_mapper._current_xml_tree = tree

    class MockMapping:
        """Minimal mock for FieldMapping with only the fields needed."""
        def __init__(self, target_column, xml_path, xml_attribute,
                     target_table="app_funding_rl", data_type="int",
                     data_length=None, mapping_type=None):
            self.target_column = target_column
            self.xml_path = xml_path
            self.xml_attribute = xml_attribute
            self.target_table = target_table
            self.data_type = data_type
            self.data_length = data_length
            self.mapping_type = mapping_type or ["last_valid_sec_contact"]

    # --- Contact-level attribute extraction ---

    def test_extracts_from_sec_not_pr(self, data_mapper, sample_xml_pr_and_sec):
        """Verify last_valid_sec_contact extracts from SEC contact, not PR."""
        self._set_xml(data_mapper, sample_xml_pr_and_sec)
        mapping = self.MockMapping(
            target_column="loanpro_customer_id_sec",
            xml_path="/Provenir/Request/CustData/IL_application/IL_contact",
            xml_attribute="loanpro_customer_id",
        )
        result = data_mapper._extract_from_last_valid_sec_contact(mapping)
        assert result == "5002", f"Expected '5002' from SEC contact, got '{result}'"

    def test_returns_none_when_no_sec_contact(self, data_mapper, sample_xml_no_sec):
        """Verify returns None when no SEC contact exists."""
        self._set_xml(data_mapper, sample_xml_no_sec)
        mapping = self.MockMapping(
            target_column="loanpro_customer_id_sec",
            xml_path="/Provenir/Request/CustData/IL_application/IL_contact",
            xml_attribute="loanpro_customer_id",
        )
        result = data_mapper._extract_from_last_valid_sec_contact(mapping)
        assert result is None

    def test_uses_last_valid_sec_contact(self, data_mapper, sample_xml_multiple_sec):
        """With multiple SEC contacts, uses the last valid one."""
        self._set_xml(data_mapper, sample_xml_multiple_sec)
        mapping = self.MockMapping(
            target_column="loanpro_customer_id_sec",
            xml_path="/Provenir/Request/CustData/IL_application/IL_contact",
            xml_attribute="loanpro_customer_id",
        )
        result = data_mapper._extract_from_last_valid_sec_contact(mapping)
        assert result == "5003", f"Expected '5003' from last SEC, got '{result}'"

    def test_skips_invalid_sec_contacts(self, data_mapper, sample_xml_sec_invalid_con_id):
        """SEC contacts with empty con_id should be skipped."""
        self._set_xml(data_mapper, sample_xml_sec_invalid_con_id)
        mapping = self.MockMapping(
            target_column="loanpro_customer_id_sec",
            xml_path="/Provenir/Request/CustData/IL_application/IL_contact",
            xml_attribute="loanpro_customer_id",
        )
        result = data_mapper._extract_from_last_valid_sec_contact(mapping)
        assert result == "5003", f"Expected '5003' (valid SEC), got '{result}'"

    # --- Address child element extraction ---

    def test_extracts_address_attribute_from_sec(self, data_mapper, sample_xml_pr_and_sec):
        """Verify extraction of address child element attribute from SEC contact."""
        self._set_xml(data_mapper, sample_xml_pr_and_sec)
        mapping = self.MockMapping(
            target_column="housing_monthly_payment_sec",
            xml_path="/Provenir/Request/CustData/application/contact/contact_address",
            xml_attribute="residence_monthly_pymnt",
            target_table="app_operational_rl",
        )
        result = data_mapper._extract_from_last_valid_sec_contact(mapping)
        assert result == "900", f"Expected '900' from SEC address, got '{result}'"

    def test_returns_none_no_xml_root(self, data_mapper):
        """Returns None when no XML root is set."""
        data_mapper._current_xml_root = None
        mapping = self.MockMapping(
            target_column="loanpro_customer_id_sec",
            xml_path="/Provenir/Request/CustData/IL_application/IL_contact",
            xml_attribute="loanpro_customer_id",
        )
        result = data_mapper._extract_from_last_valid_sec_contact(mapping)
        assert result is None
