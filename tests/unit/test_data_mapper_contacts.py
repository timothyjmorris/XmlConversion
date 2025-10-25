import unittest
import sys
import os
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
from xml_extractor.mapping.data_mapper import DataMapper

class TestExtractValidContacts(unittest.TestCase):
    def setUp(self):
        self.mapper = DataMapper()

    def test_last_valid_pr_and_authu_contacts(self):
        # Simulate XML data with multiple PR and AUTHU contacts
        xml_data = {
            '/Provenir/Request/contact': [
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Alice'},
                {'con_id': '2', 'ac_role_tp_c': 'AUTHU', 'first_name': 'Bob'},
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Carol'},   # Should NOT be selected (first PR)
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'Dave'},    # Should be selected (last "valid" PR)
                {'con_id': '2', 'ac_role_tp_c': 'AUTHU', 'first_name': 'Eve'},  # Should be selected (last AUTHU)
                {'con_id': '', 'ac_role_tp_c': 'PR', 'first_name': 'Frank'},    # Should NOT be selected (no con_id)
            ]
        }
        # Patch _navigate_to_contacts to return our test contacts
        self.mapper._navigate_to_contacts = lambda x: xml_data['/Provenir/Request/contact']
        contacts = self.mapper._extract_valid_contacts(xml_data)
        pr_contacts = [c for c in contacts if c['ac_role_tp_c'] == 'PR']
        authu_contacts = [c for c in contacts if c['ac_role_tp_c'] == 'AUTHU']
        # Only last PR contact (Frank)
        self.assertEqual(len(pr_contacts), 1)
        self.assertEqual(pr_contacts[0]['first_name'], 'Dave')
        # Only last AUTHU contact (Eve)
        self.assertEqual(len(authu_contacts), 1)
        self.assertEqual(authu_contacts[0]['first_name'], 'Eve')

if __name__ == '__main__':
    unittest.main()
