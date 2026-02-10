"""
Test meaningful data validation for addresses and employments.
Verifies that blank PREV records are filtered out and only PR contact warnings are shown.
"""
import unittest
from unittest.mock import Mock, patch
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator


class TestMeaningfulDataValidation(unittest.TestCase):
    """Test meaningful data checks for addresses, employments, and contact warnings."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mapper = DataMapper()
    
    def test_meaningful_address_with_zip(self):
        """Address with zip code should pass meaningful data check."""
        record = {'address_type_enum': 351, 'zip': '12345'}
        source_attrs = {'address_type_code': 'PREV', 'zip_code': '12345'}
        
        result = self.mapper._has_meaningful_address_data(record, source_attrs)
        self.assertTrue(result, "Address with zip should be meaningful")
    
    def test_meaningful_address_with_city(self):
        """Address with city should pass meaningful data check."""
        record = {'address_type_enum': 351, 'city': 'Springfield'}
        source_attrs = {'address_type_code': 'PREV', 'city': 'Springfield'}
        
        result = self.mapper._has_meaningful_address_data(record, source_attrs)
        self.assertTrue(result, "Address with city should be meaningful")
    
    def test_blank_prev_address_only_enum(self):
        """Blank PREV address with only enum should fail meaningful data check."""
        record = {'address_type_enum': 351}  # Only has enum, no actual data
        source_attrs = {'address_type_code': 'PREV'}  # No meaningful fields
        
        result = self.mapper._has_meaningful_address_data(record, source_attrs)
        self.assertFalse(result, "Blank PREV address should not be meaningful")
    
    def test_blank_prev_address_empty_strings(self):
        """PREV address with only empty strings should fail meaningful data check."""
        record = {
            'address_type_enum': 351,
            'zip': '',
            'city': '',
            'street_name': '',
            'state': ''
        }
        source_attrs = {
            'address_type_code': 'PREV',
            'zip_code': '',
            'city': '',
            'street_name': ''
        }
        
        result = self.mapper._has_meaningful_address_data(record, source_attrs)
        self.assertFalse(result, "PREV address with all empty fields should not be meaningful")
    
    def test_meaningful_employment_with_business_name(self):
        """Employment with business name should pass meaningful data check."""
        record = {'employment_type_enum': 351, 'business_name': 'Acme Corp'}
        source_attrs = {'employment_type_code': 'PREV', 'business_name': 'Acme Corp'}
        
        result = self.mapper._has_meaningful_employment_data(record, source_attrs)
        self.assertTrue(result, "Employment with business name should be meaningful")
    
    def test_meaningful_employment_with_salary(self):
        """Employment with monthly salary should pass meaningful data check."""
        record = {'employment_type_enum': 351, 'monthly_salary': 5000.00}
        source_attrs = {'employment_type_code': 'PREV'}
        
        result = self.mapper._has_meaningful_employment_data(record, source_attrs)
        self.assertTrue(result, "Employment with salary should be meaningful")
    
    def test_blank_prev_employment_only_enum(self):
        """Blank PREV employment with only enum should fail meaningful data check."""
        record = {'employment_type_enum': 351}  # Only has enum, no actual data
        source_attrs = {'employment_type_code': 'PREV'}  # No meaningful fields
        
        result = self.mapper._has_meaningful_employment_data(record, source_attrs)
        self.assertFalse(result, "Blank PREV employment should not be meaningful")
    
    def test_blank_prev_employment_empty_strings(self):
        """PREV employment with only empty strings should fail meaningful data check."""
        record = {
            'employment_type_enum': 351,
            'business_name': '',
            'job_title': '',
            'zip': '',
            'city': ''
        }
        source_attrs = {
            'employment_type_code': 'PREV',
            'business_name': '',
            'zip_code': '',
            'city': ''
        }
        
        result = self.mapper._has_meaningful_employment_data(record, source_attrs)
        self.assertFalse(result, "PREV employment with all empty fields should not be meaningful")
    
    def test_warning_only_for_missing_pr_contact(self):
        """Should only warn when PR contact is missing, not secondary contacts."""
        validator = PreProcessingValidator()
        
        # Mock the XML parser to return contacts without PR
        with patch.object(validator, '_navigate_to_contacts') as mock_navigate:
            # Scenario 1: Has PR contact, missing SEC - should NOT warn
            mock_navigate.return_value = [
                {'con_id': '1', 'ac_role_tp_c': 'PR', 'first_name': 'John'}
            ]
            
            warnings = []
            errors = []
            skipped = {'contacts': [], 'addresses': [], 'employments': []}
            
            result = validator._validate_and_collect_contacts(
                {}, errors, warnings, skipped, app_id='123'
            )
            
            # Should not have the "no PR" warning
            pr_warnings = [w for w in warnings if 'No PRIMARY (PR) contact' in w]
            self.assertEqual(len(pr_warnings), 0, 
                           "Should not warn when PR contact exists")
    
    def test_warning_when_pr_contact_missing(self):
        """Should warn when PR contact is missing."""
        validator = PreProcessingValidator()
        
        # Mock the XML parser to return only secondary contact
        with patch.object(validator, '_navigate_to_contacts') as mock_navigate:
            # Has SEC but no PR - should warn
            mock_navigate.return_value = [
                {'con_id': '2', 'ac_role_tp_c': 'SEC', 'first_name': 'Jane'}
            ]
            
            warnings = []
            errors = []
            skipped = {'contacts': [], 'addresses': [], 'employments': []}
            
            result = validator._validate_and_collect_contacts(
                {}, errors, warnings, skipped, app_id='456'
            )
            
            # Should have the "no PR" warning
            pr_warnings = [w for w in warnings if 'No PRIMARY (PR) contact' in w]
            self.assertEqual(len(pr_warnings), 1, 
                           "Should warn when PR contact is missing")
            self.assertIn('456', pr_warnings[0], 
                         "Warning should include app_id")


if __name__ == '__main__':
    unittest.main()
