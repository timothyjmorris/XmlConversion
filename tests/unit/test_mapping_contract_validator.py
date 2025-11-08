"""
Unit tests for MappingContractValidator class structure and orchestration.

Tests the validator framework and orchestration logic before implementing
specific validation rules in Steps 3-5.
"""

import unittest
from xml_extractor.validation.mapping_contract_validator import MappingContractValidator
from xml_extractor.models import MappingContractValidationResult


class TestMappingContractValidatorStructure(unittest.TestCase):
    """Test validator class initialization and structure."""
    
    def test_validator_initialization(self):
        """Validator accepts contract dictionary."""
        contract = {
            "target_schema": "sandbox",
            "source_table": "app_xml",
            "source_column": "xml_data",
            "xml_root_element": "/Provenir/Request/CustData/application",
            "mappings": [],
            "relationships": [],
            "element_filtering": {},
            "enum_mappings": {}
        }
        
        validator = MappingContractValidator(contract)
        
        self.assertIsNotNone(validator)
        self.assertEqual(validator.contract, contract)
        self.assertEqual(len(validator.errors), 0)
        self.assertEqual(len(validator.warnings), 0)
    
    def test_validator_initializes_with_empty_error_lists(self):
        """Validator starts with no errors or warnings."""
        contract = {"mappings": [], "relationships": []}
        validator = MappingContractValidator(contract)
        
        self.assertIsInstance(validator.errors, list)
        self.assertIsInstance(validator.warnings, list)
        self.assertEqual(len(validator.errors), 0)
        self.assertEqual(len(validator.warnings), 0)


class TestValidateContractOrchestration(unittest.TestCase):
    """Test validate_contract() orchestration method."""
    
    def test_validate_contract_returns_result(self):
        """validate_contract() returns MappingContractValidationResult."""
        contract = {
            "element_filtering": {"filter_rules": []},
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertIsInstance(result, MappingContractValidationResult)
    
    def test_validate_contract_clears_previous_results(self):
        """Multiple validate_contract() calls don't accumulate errors."""
        contract = {
            "element_filtering": {"filter_rules": []},
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        # First validation
        result1 = validator.validate_contract()
        
        # Second validation should start fresh
        result2 = validator.validate_contract()
        
        # Results should be independent
        self.assertEqual(result1.error_count, result2.error_count)
        self.assertEqual(result1.warning_count, result2.warning_count)
    
    def test_minimal_valid_contract_passes(self):
        """Contract with all required sections (empty but present) is valid."""
        contract = {
            "target_schema": "sandbox",
            "source_table": "app_xml",
            "source_column": "xml_data",
            "xml_root_element": "/Provenir/Request/CustData/application",
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "relationships": [],
            "table_insertion_order": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        # Should pass with stub validation methods (no errors added)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)


class TestValidationMethodsExist(unittest.TestCase):
    """Test that validation methods are callable (structure exists)."""
    
    def setUp(self):
        """Create validator with minimal contract."""
        self.contract = {
            "element_filtering": {},
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        self.validator = MappingContractValidator(self.contract)
    
    def test_validate_element_filtering_method_exists(self):
        """_validate_element_filtering() method is callable."""
        # Should not raise AttributeError
        self.validator._validate_element_filtering()
    
    def test_validate_relationships_method_exists(self):
        """_validate_relationships() method is callable."""
        # Should not raise AttributeError
        self.validator._validate_relationships()
    
    def test_validate_enum_mappings_method_exists(self):
        """_validate_enum_mappings() method is callable."""
        # Should not raise AttributeError
        self.validator._validate_enum_mappings()


class TestValidatorErrorAggregation(unittest.TestCase):
    """Test that validator aggregates errors from multiple validation methods."""
    
    def test_errors_list_is_mutable(self):
        """Validator can add errors to errors list."""
        from xml_extractor.models import MappingContractValidationError
        
        contract = {"element_filtering": {}, "relationships": [], "enum_mappings": {}, "mappings": []}
        validator = MappingContractValidator(contract)
        
        # Manually add an error (simulates what validation methods will do)
        error = MappingContractValidationError(
            category="test",
            message="test error",
            contract_location="test",
            fix_guidance="test fix"
        )
        validator.errors.append(error)
        
        result = validator.validate_contract()
        
        # Error should be cleared after validate_contract() (fresh start)
        self.assertEqual(result.error_count, 0)
    
    def test_warnings_list_is_mutable(self):
        """Validator can add warnings to warnings list."""
        from xml_extractor.models import MappingContractValidationWarning
        
        contract = {"element_filtering": {}, "relationships": [], "enum_mappings": {}, "mappings": []}
        validator = MappingContractValidator(contract)
        
        # Manually add a warning
        warning = MappingContractValidationWarning(
            category="test",
            message="test warning",
            contract_location="test",
            recommendation="test recommendation"
        )
        validator.warnings.append(warning)
        
        result = validator.validate_contract()
        
        # Warning should be cleared after validate_contract() (fresh start)
        self.assertEqual(result.warning_count, 0)


if __name__ == '__main__':
    unittest.main()
