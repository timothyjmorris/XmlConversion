"""
Test that chained mapping types like ["last_valid_pr_contact", "enum"] work correctly.

This test verifies the fix for the bug where last_valid_pr_contact was prematurely
applying data type transformation BEFORE passing the value to subsequent mapping types.

Bug: sc_bank_account_type_enum was always NULL because:
1. last_valid_pr_contact extracted "S" from XML
2. last_valid_pr_contact called transform_data_types("S", "smallint") 
3. transform_data_types couldn't convert "S" to int, returned None
4. enum mapping received None, returned None

Fix: last_valid_pr_contact no longer applies data type transformation.
Final transformation is applied after all mapping types complete.
"""
import pytest
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
from lxml import etree


class TestMappingTypeChainFix:
    """Tests for chained mapping type behavior."""
    
    @pytest.fixture
    def mapper(self):
        """Create a DataMapper instance."""
        return DataMapper(log_level='ERROR')
    
    @pytest.fixture
    def xml_with_banking_account_type_S(self):
        """XML with banking_account_type="S" (Savings)."""
        return """
        <Provenir>
            <Request ID="12345">
                <CustData>
                    <application app_id="12345">
                        <contact con_id="1001" ac_role_tp_c="PR" banking_account_type="S">
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """.strip()
    
    @pytest.fixture
    def xml_with_banking_account_type_C(self):
        """XML with banking_account_type="C" (Checking)."""
        return """
        <Provenir>
            <Request ID="12345">
                <CustData>
                    <application app_id="12345">
                        <contact con_id="1001" ac_role_tp_c="PR" banking_account_type="C">
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """.strip()
    
    @pytest.fixture
    def xml_without_banking_account_type(self):
        """XML without banking_account_type attribute."""
        return """
        <Provenir>
            <Request ID="12345">
                <CustData>
                    <application app_id="12345">
                        <contact con_id="1001" ac_role_tp_c="PR">
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """.strip()

    def test_last_valid_pr_contact_enum_chain_extracts_S_correctly(self, mapper, xml_with_banking_account_type_S):
        """Verify that banking_account_type="S" is correctly mapped to enum value 71."""
        tree = etree.fromstring(xml_with_banking_account_type_S.encode())
        parser = XMLParser()
        xml_data = parser.extract_elements(tree)
        
        mapper._current_xml_root = tree
        valid_contacts = mapper._extract_valid_contacts(xml_data)
        
        from xml_extractor.config.config_manager import get_config_manager
        config = get_config_manager()
        contract = config.load_mapping_contract()
        
        result = mapper.apply_mapping_contract(xml_data, contract, "12345", valid_contacts, xml_root=tree)
        
        assert 'app_operational_cc' in result
        assert len(result['app_operational_cc']) > 0
        
        mapped_value = result['app_operational_cc'][0].get('sc_bank_account_type_enum')
        assert mapped_value == 71, f"Expected 71 for 'S', got {mapped_value}"
    
    def test_last_valid_pr_contact_enum_chain_extracts_C_correctly(self, mapper, xml_with_banking_account_type_C):
        """Verify that banking_account_type="C" is correctly mapped to enum value 70."""
        tree = etree.fromstring(xml_with_banking_account_type_C.encode())
        parser = XMLParser()
        xml_data = parser.extract_elements(tree)
        
        mapper._current_xml_root = tree
        valid_contacts = mapper._extract_valid_contacts(xml_data)
        
        from xml_extractor.config.config_manager import get_config_manager
        config = get_config_manager()
        contract = config.load_mapping_contract()
        
        result = mapper.apply_mapping_contract(xml_data, contract, "12345", valid_contacts, xml_root=tree)
        
        assert 'app_operational_cc' in result
        assert len(result['app_operational_cc']) > 0
        
        mapped_value = result['app_operational_cc'][0].get('sc_bank_account_type_enum')
        assert mapped_value == 70, f"Expected 70 for 'C', got {mapped_value}"
    
    def test_last_valid_pr_contact_enum_chain_handles_missing_value(self, mapper, xml_without_banking_account_type):
        """Verify that missing banking_account_type correctly results in None (NULL in DB)."""
        tree = etree.fromstring(xml_without_banking_account_type.encode())
        parser = XMLParser()
        xml_data = parser.extract_elements(tree)
        
        mapper._current_xml_root = tree
        valid_contacts = mapper._extract_valid_contacts(xml_data)
        
        from xml_extractor.config.config_manager import get_config_manager
        config = get_config_manager()
        contract = config.load_mapping_contract()
        
        result = mapper.apply_mapping_contract(xml_data, contract, "12345", valid_contacts, xml_root=tree)
        
        assert 'app_operational_cc' in result
        assert len(result['app_operational_cc']) > 0
        
        # sc_bank_account_type_enum should either be None or not present (both mean NULL in DB)
        record = result['app_operational_cc'][0]
        mapped_value = record.get('sc_bank_account_type_enum')
        assert mapped_value is None, f"Expected None for missing banking_account_type, got {mapped_value}"
