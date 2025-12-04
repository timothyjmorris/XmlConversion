
import unittest
import sys
import os
import json
import tempfile

from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.exceptions import ConfigurationError

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)


class TestExtractValidContacts(unittest.TestCase):
    def test_no_valid_contacts(self):
        # All contacts missing required fields, should return empty list
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '', 'ac_role_tp_c': 'PR', 'first_name': 'NoId'},
                {'con_id': '2', 'ac_role_tp_c': '', 'first_name': 'NoType'},
                {'con_id': '3', 'first_name': 'NoRole'},
                {},
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        self.assertEqual(len(contacts), 0)
    
    def test_pr_and_authu_same_con_id(self):
        # PR and AUTHU with same con_id, PR should be chosen -- and also return the non-duplicate AUTHU
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser', 'contact_type_enum': 1},
                {'con_id': '1', 'ac_role_tp_c': 'AUTHU', 'first_name': 'AuthUser', 'contact_type_enum': 2},
                {'con_id': '2', 'ac_role_tp_c': 'AUTHU', 'first_name': 'OtherAuth', 'contact_type_enum': 2},
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        self.assertEqual(len(contacts), 2)
        self.assertTrue(any(c['first_name'] == 'PrimaryUser' and c['con_id'] == '1' for c in contacts))
        self.assertTrue(any(c['first_name'] == 'OtherAuth' and c['con_id'] == '2' for c in contacts))

    def test_missing_required_fields(self):
        # Contact missing contact_type_enum should be excluded
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': '', 'first_name': 'PrimaryUser'},  # Missing contact_type_enum
                {'con_id': '2', 'ac_role_tp_c': 'AUTHU', 'first_name': 'OtherAuth', 'contact_type_enum': 2},
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        # Only contact with all required fields should be present
        self.assertEqual(len(contacts), 1)
        self.assertTrue(all('contact_type_enum' in c for c in contacts))
        self.assertTrue(any(c['first_name'] == 'OtherAuth' and c['con_id'] == '2' for c in contacts))

    def test_multiple_contacts_same_con_id(self):
        # Multiple contacts with same con_id, PR should be chosen
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'AUTHU', 'first_name': 'AuthUser', 'contact_type_enum': 2},
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser', 'contact_type_enum': 1},
                {'con_id': '1', 'ac_role_tp_c': 'AUTHU', 'first_name': 'AuthUser2', 'contact_type_enum': 2},
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        self.assertEqual(len(contacts), 1)
        self.assertTrue(any(c['first_name'] == 'PrimaryUser' and c['con_id'] == '1' for c in contacts))

    def test_only_one_contact(self):
        # Only one contact present
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser', 'contact_type_enum': 1},
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        self.assertEqual(len(contacts), 1)
        self.assertTrue(any(c['first_name'] == 'PrimaryUser' and c['con_id'] == '1' for c in contacts))
        self.assertTrue(all('contact_type_enum' in c for c in contacts))
    
    def test_priority_pr_over_authu(self):
        # PR and AUTHU with same con_id, PR should be chosen
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'AUTHU', 'first_name': 'AuthUser'},
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser'},  # Should be selected
                {'con_id': '2', 'ac_role_tp_c': 'AUTHU', 'first_name': 'OtherAuth'},
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        # Only PR for con_id=1, AUTHU for con_id=2
        self.assertEqual(len(contacts), 2)
        self.assertTrue(any(c['first_name'] == 'PrimaryUser' and c['con_id'] == '1' for c in contacts))
        self.assertTrue(any(c['first_name'] == 'OtherAuth' and c['con_id'] == '2' for c in contacts))
    
    def test_dedupe_across_types(self):
        # PR and AUTHU with same con_id, only last contact (PR) should be returned
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser'},  # Should be selected (last for con_id=1)
                {'con_id': '1', 'ac_role_tp_c': 'AUTHU', 'first_name': 'AuthUser'},                
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        # Only last contact for con_id=1 (PR) and con_id=2 (AUTHU)
        self.assertEqual(len(contacts), 1)
        self.assertTrue(any(c['first_name'] == 'PrimaryUser' and c['con_id'] == '1' for c in contacts))

    def setUp(self):
        self.mapper = DataMapper()

    def test_last_contact_per_con_id(self):
        # Simulate XML data with multiple PR and AUTHU contacts
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Alice'},
                {'con_id': '2', 'ac_role_tp_c': 'AUTHU', 'first_name': 'Bob'},
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Carol'},   # Should NOT be selected (not last)
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Dave'},    # Should be selected (last for con_id=1)
                {'con_id': '2', 'ac_role_tp_c': 'AUTHU', 'first_name': 'Eve'},  # Should be selected (last for con_id=2)
                {'con_id': '', 'ac_role_tp_c': 'PR', 'first_name': 'Frank'},    # Should NOT be selected (no con_id)
            ]
        }
        # Patch _navigate_to_contacts to return our test contacts
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        # Should only have last for con_id=1 and con_id=2
        self.assertEqual(len(contacts), 2)
        self.assertTrue(any(c['first_name'] == 'Dave' and c['con_id'] == '1' for c in contacts))
        self.assertTrue(any(c['first_name'] == 'Eve' and c['con_id'] == '2' for c in contacts))


class TestContractDrivenContactTypes(unittest.TestCase):
    """Test that contact type validation is fully contract-driven."""
    
    def setUp(self):
        """Create a temporary contract with custom contact types."""
        self.temp_contract = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        # Custom contract with different contact type attribute and values
        contract_data = {
            "xml_root_element": "Provenir",
            "xml_application_path": "/Provenir/Request/CustData/application",
            "source_table": "app_xml",
            "source_column": "xml",
            "target_schema": "sandbox",
            "table_insertion_order": ["app_base", "app_contact_base"],
            "element_filtering": {
                "filter_rules": [
                    {
                        "element_type": "contact",
                        "description": "Custom contact types for testing",
                        "xml_parent_path": "/Provenir/Request/CustData/application",
                        "xml_child_path": "/Provenir/Request/CustData/application/contact",
                        "required_attributes": {
                            "con_id": True,
                            "borrower_type": ["PRIMARY", "SECONDARY", "COSIGNER"]
                        }
                    },
                    {
                        "element_type": "address",
                        "xml_parent_path": "/Provenir/Request/CustData/application/contact",
                        "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_address",
                        "required_attributes": {
                            "address_tp_c": ["CURR", "PREV", "PATR"]
                        }
                    }
                ]
            },
            "enum_mappings": {
                "contact_type_enum": {
                    "PRIMARY": 1,
                    "SECONDARY": 2,
                    "COSIGNER": 3
                }
            },
            "bit_conversions": {},
            "mappings": [
                {
                    "xml_path": "/Provenir/Request",
                    "xml_attribute": "ID",
                    "target_table": "app_base",
                    "target_column": "app_id",
                    "data_type": "int",
                    "nullable": False
                }
            ]
        }
        json.dump(contract_data, self.temp_contract)
        self.temp_contract.close()
        
        # Initialize mapper with custom contract and DEBUG logging
        self.mapper = DataMapper(mapping_contract_path=self.temp_contract.name, log_level="DEBUG")
    
    def tearDown(self):
        """Clean up temporary contract file."""
        os.unlink(self.temp_contract.name)
    
    def test_custom_contact_type_attribute_name(self):
        """Verify that custom contact type attribute name is recognized."""
        contact_type_attr, valid_types = self.mapper._valid_contact_type_config
        self.assertEqual(contact_type_attr, "borrower_type")
        self.assertEqual(set(valid_types), {"PRIMARY", "SECONDARY", "COSIGNER"})
    
    def test_extract_contacts_with_custom_types(self):
        """Verify contact extraction works with custom contact type values."""
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'borrower_type': 'PRIMARY', 'first_name': 'John'},
                {'con_id': '2', 'borrower_type': 'SECONDARY', 'first_name': 'Jane'},
                {'con_id': '3', 'borrower_type': 'COSIGNER', 'first_name': 'Bob'},
                {'con_id': '4', 'borrower_type': 'INVALID_TYPE', 'first_name': 'Invalid'},  # Should be filtered
                {'con_id': '5', 'ac_role_tp_c': 'PR', 'first_name': 'OldAttribute'},  # Wrong attribute name
            ]
        }
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        
        # Should only extract contacts with valid borrower_type values
        self.assertEqual(len(contacts), 3)
        contact_names = {c['first_name'] for c in contacts}
        self.assertEqual(contact_names, {'John', 'Jane', 'Bob'})
        
        # Verify the INVALID_TYPE and wrong attribute contacts were filtered out
        self.assertNotIn('Invalid', contact_names)
        self.assertNotIn('OldAttribute', contact_names)
    
    def test_fallback_to_defaults_when_contract_missing(self):
        """Verify fallback to default values when contract is missing filter rules."""
        # Create mapper with default contract (no custom path)
        default_mapper = DataMapper()
        contact_type_attr, valid_types = default_mapper._valid_contact_type_config
        
        # Should fall back to standard ac_role_tp_c with PR/AUTHU
        self.assertEqual(contact_type_attr, "ac_role_tp_c")
        self.assertIn("PR", valid_types)
        self.assertIn("AUTHU", valid_types)


class TestContactTypePriority(unittest.TestCase):
    """Test that contact type priority is determined by array order."""
    
    def test_default_priority_order_pr_over_authu(self):
        """Verify default priority: PR (index 0) beats AUTHU (index 1)."""
        mapper = DataMapper()
        
        # Default contract has ["PR", "AUTHU"] order
        priority_map = mapper._contact_type_priority_map
        self.assertEqual(priority_map['PR'], 0)
        self.assertEqual(priority_map['AUTHU'], 1)
        
        # Test deduplication - PR should win
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'AUTHU', 'first_name': 'AuthUser'},
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser'},  # Should win
            ]
        }
        mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = mapper._extract_valid_contacts(xml_data)
        
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['first_name'], 'PrimaryUser')
    
    def test_reversed_priority_order(self):
        """Verify reversed priority: AUTHU wins when it comes first in array."""
        temp_contract = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        contract_data = {
            "xml_root_element": "Provenir",
            "xml_application_path": "/Provenir/Request/CustData/application",
            "source_table": "app_xml",
            "source_column": "xml",
            "target_schema": "sandbox",
            "table_insertion_order": ["app_base", "app_contact_base"],
            "element_filtering": {
                "filter_rules": [
                    {
                        "element_type": "contact",
                        "description": "Reversed priority - AUTHU first",
                        "xml_parent_path": "/Provenir/Request/CustData/application",
                        "xml_child_path": "/Provenir/Request/CustData/application/contact",
                        "required_attributes": {
                            "con_id": True,
                            "ac_role_tp_c": ["AUTHU", "PR"]  # AUTHU first!
                        }
                    },
                    {
                        "element_type": "address",
                        "xml_parent_path": "/Provenir/Request/CustData/application/contact",
                        "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_address",
                        "required_attributes": {
                            "address_tp_c": ["CURR", "PREV"]
                        }
                    }
                ]
            },
            "enum_mappings": {"contact_type_enum": {"PR": 1, "AUTHU": 2}},
            "bit_conversions": {},
            "mappings": [{"xml_path": "/Provenir/Request", "xml_attribute": "ID", "target_table": "app_base", "target_column": "app_id", "data_type": "int", "nullable": False}]
        }
        json.dump(contract_data, temp_contract)
        temp_contract.close()
        
        try:
            mapper = DataMapper(mapping_contract_path=temp_contract.name, log_level="DEBUG")
            
            # Priority map should be reversed
            priority_map = mapper._contact_type_priority_map
            self.assertEqual(priority_map['AUTHU'], 0)  # AUTHU is now highest priority
            self.assertEqual(priority_map['PR'], 1)
            
            # Test deduplication - AUTHU should win
            xml_data = {
                '/Provenir/Request/contact': [
                    {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser'},
                    {'con_id': '1', 'ac_role_tp_c': 'AUTHU', 'first_name': 'AuthUser'},  # Should win now!
                ]
            }
            mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
            contacts = mapper._extract_valid_contacts(xml_data)
            
            self.assertEqual(len(contacts), 1)
            self.assertEqual(contacts[0]['first_name'], 'AuthUser')
        finally:
            os.unlink(temp_contract.name)
    
    def test_equal_priority_last_wins(self):
        """Verify that when priorities are equal, last element wins."""
        mapper = DataMapper()
        
        # All contacts have same priority
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'First'},
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Second'},
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Last'},  # Should win
            ]
        }
        mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = mapper._extract_valid_contacts(xml_data)
        
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['first_name'], 'Last')
    
    def test_unknown_type_lowest_priority(self):
        """Verify unknown contact types get lowest priority."""
        temp_contract = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        contract_data = {
            "xml_root_element": "Provenir",
            "xml_application_path": "/Provenir/Request/CustData/application",
            "source_table": "app_xml",
            "source_column": "xml",
            "target_schema": "sandbox",
            "table_insertion_order": ["app_base", "app_contact_base"],
            "element_filtering": {
                "filter_rules": [
                    {
                        "element_type": "contact",
                        "xml_parent_path": "/Provenir/Request/CustData/application",
                        "xml_child_path": "/Provenir/Request/CustData/application/contact",
                        "required_attributes": {
                            "con_id": True,
                            "ac_role_tp_c": ["PR", "AUTHU", "UNKNOWN"]  # Allow UNKNOWN type
                        }
                    },
                    {
                        "element_type": "address",
                        "xml_parent_path": "/Provenir/Request/CustData/application/contact",
                        "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_address",
                        "required_attributes": {
                            "address_tp_c": ["CURR", "PREV"]
                        }
                    }
                ]
            },
            "enum_mappings": {"contact_type_enum": {"PR": 1, "AUTHU": 2, "UNKNOWN": 3}},
            "bit_conversions": {},
            "mappings": [{"xml_path": "/Provenir/Request", "xml_attribute": "ID", "target_table": "app_base", "target_column": "app_id", "data_type": "int", "nullable": False}]
        }
        json.dump(contract_data, temp_contract)
        temp_contract.close()
        
        try:
            mapper = DataMapper(mapping_contract_path=temp_contract.name, log_level="DEBUG")
            
            # UNKNOWN has higher index (lower priority)
            priority_map = mapper._contact_type_priority_map
            self.assertEqual(priority_map['UNKNOWN'], 2)  # Index 2 = lowest priority
            
            # PR should win over UNKNOWN
            xml_data = {
                '/Provenir/Request/contact': [
                    {'con_id': '1', 'ac_role_tp_c': 'UNKNOWN', 'first_name': 'UnknownContact'},
                    {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'PrimaryUser'},  # Should win
                ]
            }
            mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
            contacts = mapper._extract_valid_contacts(xml_data)
            
            self.assertEqual(len(contacts), 1)
            self.assertEqual(contacts[0]['first_name'], 'PrimaryUser')
        finally:
            os.unlink(temp_contract.name)


class TestAddressTypeFiltering(unittest.TestCase):
    """Test that preferred address type is determined by array order in contract."""
    
    def test_default_preferred_address_curr(self):
        """Verify default contract uses CURR as preferred address type (first in array)."""
        mapper = DataMapper(log_level="DEBUG")
        
        # Default contract has ["CURR", "PREV", "PATR"] - CURR should be preferred (index 0)
        address_type_attr, preferred_address_type = mapper._preferred_address_type_config
        
        self.assertEqual(address_type_attr, 'address_tp_c')
        self.assertEqual(preferred_address_type, 'CURR')
    
    def test_custom_preferred_address_type(self):
        """Verify custom contract can define different preferred address (first in array)."""
        # Load the default contract file and modify it
        config_dir = os.path.join(os.path.dirname(__file__), '../../config')
        with open(os.path.join(config_dir, 'mapping_contract.json'), 'r') as f:
            custom_contract = json.load(f)
        
        # Modify address filter rule to use custom types
        for rule in custom_contract['element_filtering']['filter_rules']:
            if rule['element_type'] == 'address':
                rule['required_attributes']['location_type'] = ["HOME", "WORK", "MAIL"]
                del rule['required_attributes']['address_tp_c']
                break
        
        # Write custom contract to temp file
        temp_contract = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(custom_contract, temp_contract)
        temp_contract.close()
        
        try:
            mapper = DataMapper(mapping_contract_path=temp_contract.name, log_level="DEBUG")
            
            # Should extract attribute name and preferred type from custom contract
            address_type_attr, preferred_address_type = mapper._preferred_address_type_config
            
            self.assertEqual(address_type_attr, 'location_type')
            self.assertEqual(preferred_address_type, 'HOME')  # First in array
        finally:
            os.unlink(temp_contract.name)
    
    def test_reversed_address_priority_prev_over_curr(self):
        """Verify reversed address order: PREV preferred when it comes first in array."""
        # Load the default contract file and modify it
        config_dir = os.path.join(os.path.dirname(__file__), '../../config')
        with open(os.path.join(config_dir, 'mapping_contract.json'), 'r') as f:
            custom_contract = json.load(f)
        
        # Modify address filter rule to reverse order
        for rule in custom_contract['element_filtering']['filter_rules']:
            if rule['element_type'] == 'address':
                # Reverse order: PREV first, then CURR
                rule['required_attributes']['address_tp_c'] = ["PREV", "CURR", "PATR"]
                break
        
        # Write custom contract to temp file
        temp_contract = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(custom_contract, temp_contract)
        temp_contract.close()
        
        try:
            mapper = DataMapper(mapping_contract_path=temp_contract.name, log_level="DEBUG")
            
            # Should prefer PREV (first in array)
            address_type_attr, preferred_address_type = mapper._preferred_address_type_config
            
            self.assertEqual(address_type_attr, 'address_tp_c')
            self.assertEqual(preferred_address_type, 'PREV')  # First in reversed array
        finally:
            os.unlink(temp_contract.name)
    
    def test_fallback_when_contract_incomplete(self):
        """Verify fail-fast ConfigurationError when address filter rule missing."""
        # Load the default contract file and modify it
        config_dir = os.path.join(os.path.dirname(__file__), '../../config')
        with open(os.path.join(config_dir, 'mapping_contract.json'), 'r') as f:
            custom_contract = json.load(f)
        
        # Remove address filter rule
        custom_contract['element_filtering']['filter_rules'] = [
            rule for rule in custom_contract['element_filtering']['filter_rules']
            if rule['element_type'] != 'address'
        ]
        
        # Write custom contract to temp file
        temp_contract = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        json.dump(custom_contract, temp_contract)
        temp_contract.close()
        
        try:
            # Should raise ConfigurationError, not fall back to defaults
            with self.assertRaises(ConfigurationError) as context:
                DataMapper(mapping_contract_path=temp_contract.name, log_level="DEBUG")
            
            # Verify error message is actionable
            self.assertIn("Missing element_filtering rule for 'address'", str(context.exception))
            self.assertIn("element_filtering.filter_rules", str(context.exception))
        finally:
            os.unlink(temp_contract.name)


if __name__ == '__main__':
    unittest.main()
