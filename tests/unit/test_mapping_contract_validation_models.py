"""
Unit tests for MappingContractValidation result models.

Tests the data structures used to report contract validation errors and warnings,
ensuring they provide clear, actionable feedback for configuration issues.
"""

import unittest
from xml_extractor.models import (
    MappingContractValidationError,
    MappingContractValidationWarning,
    MappingContractValidationResult
)


class TestMappingContractValidationError(unittest.TestCase):
    """Test MappingContractValidationError model."""
    
    def test_error_creation_with_all_fields(self):
        """Create error with all fields populated."""
        error = MappingContractValidationError(
            category="element_filtering",
            message="Missing required filter rule for 'address'",
            contract_location="element_filtering.filter_rules",
            fix_guidance="Add an address filter rule to element_filtering.filter_rules array",
            example_fix='{"element_type": "address", "required_attributes": {"address_tp_c": ["CURR"]}}'
        )
        
        self.assertEqual(error.category, "element_filtering")
        self.assertEqual(error.message, "Missing required filter rule for 'address'")
        self.assertEqual(error.contract_location, "element_filtering.filter_rules")
        self.assertIsNotNone(error.fix_guidance)
        self.assertIsNotNone(error.example_fix)
    
    def test_error_creation_without_example(self):
        """Create error without example fix (optional field)."""
        error = MappingContractValidationError(
            category="relationships",
            message="Missing foreign_key_column",
            contract_location="relationships[2]",
            fix_guidance="Add foreign_key_column field"
        )
        
        self.assertEqual(error.category, "relationships")
        self.assertIsNone(error.example_fix)
    
    def test_format_error_with_example(self):
        """Format error message includes all fields when example provided."""
        error = MappingContractValidationError(
            category="enum_mappings",
            message="Undefined enum type 'contact_type_enum'",
            contract_location="mappings[15].mapping_type",
            fix_guidance="Add 'contact_type_enum' to enum_mappings section",
            example_fix='"contact_type_enum": {"PR": 1, "AUTHU": 2}'
        )
        
        formatted = error.format_error()
        
        # Check all components present
        self.assertIn("X:", formatted)
        self.assertIn("[enum_mappings]", formatted)
        self.assertIn("Undefined enum type", formatted)
        self.assertIn("Location: mappings[15].mapping_type", formatted)
        self.assertIn("Fix:", formatted)
        self.assertIn("Example:", formatted)
        self.assertIn('"contact_type_enum"', formatted)
    
    def test_format_error_without_example(self):
        """Format error message without example fix."""
        error = MappingContractValidationError(
            category="relationships",
            message="Missing foreign_key_column",
            contract_location="relationships[2]",
            fix_guidance="Add foreign_key_column field to relationship"
        )
        
        formatted = error.format_error()
        
        # Check required components present
        self.assertIn("X:", formatted)
        self.assertIn("[relationships]", formatted)
        self.assertIn("Missing foreign_key_column", formatted)
        self.assertIn("Location:", formatted)
        self.assertIn("Fix:", formatted)
        # Example should not be present
        self.assertNotIn("Example:", formatted)


class TestMappingContractValidationWarning(unittest.TestCase):
    """Test MappingContractValidationWarning model."""
    
    def test_warning_creation(self):
        """Create warning with all required fields."""
        warning = MappingContractValidationWarning(
            category="performance",
            message="Large number of mappings detected",
            contract_location="mappings (count: 500)",
            recommendation="Consider splitting into multiple smaller contracts or using calculated fields"
        )
        
        self.assertEqual(warning.category, "performance")
        self.assertEqual(warning.message, "Large number of mappings detected")
        self.assertIsNotNone(warning.recommendation)
    
    def test_format_warning(self):
        """Format warning message includes all fields."""
        warning = MappingContractValidationWarning(
            category="consistency",
            message="Inconsistent naming pattern in target_column values",
            contract_location="mappings",
            recommendation="Use consistent naming convention (e.g., snake_case) for all target_column values"
        )
        
        formatted = warning.format_warning()
        
        # Check all components present
        self.assertIn("!:", formatted)
        self.assertIn("[consistency]", formatted)
        self.assertIn("Inconsistent naming pattern", formatted)
        self.assertIn("Location:", formatted)
        self.assertIn("Recommendation:", formatted)


class TestMappingContractValidationResult(unittest.TestCase):
    """Test MappingContractValidationResult model."""
    
    def test_valid_result_with_no_errors_or_warnings(self):
        """Create valid result with no errors or warnings."""
        result = MappingContractValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.warning_count, 0)
        self.assertFalse(result.has_warnings)
    
    def test_valid_result_with_warnings_only(self):
        """Valid result can have warnings (non-blocking)."""
        warning = MappingContractValidationWarning(
            category="best_practices",
            message="Consider adding description field",
            contract_location="mappings[10]",
            recommendation="Add description for maintainability"
        )
        
        result = MappingContractValidationResult(
            is_valid=True,
            errors=[],
            warnings=[warning]
        )
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
        self.assertEqual(result.warning_count, 1)
        self.assertTrue(result.has_warnings)
    
    def test_invalid_result_with_errors(self):
        """Invalid result with errors."""
        error = MappingContractValidationError(
            category="element_filtering",
            message="Missing required filter rule",
            contract_location="element_filtering.filter_rules",
            fix_guidance="Add filter rule"
        )
        
        result = MappingContractValidationResult(
            is_valid=False,
            errors=[error],
            warnings=[]
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        self.assertEqual(result.warning_count, 0)
    
    def test_invalid_result_with_errors_and_warnings(self):
        """Invalid result can have both errors and warnings."""
        error = MappingContractValidationError(
            category="enum_mappings",
            message="Missing enum",
            contract_location="enum_mappings",
            fix_guidance="Add enum"
        )
        
        warning = MappingContractValidationWarning(
            category="performance",
            message="Too many mappings",
            contract_location="mappings",
            recommendation="Reduce count"
        )
        
        result = MappingContractValidationResult(
            is_valid=False,
            errors=[error],
            warnings=[warning]
        )
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        self.assertEqual(result.warning_count, 1)
        self.assertTrue(result.has_warnings)
    
    def test_post_init_validation_errors_with_valid_flag(self):
        """Cannot create result with errors but is_valid=True."""
        error = MappingContractValidationError(
            category="test",
            message="test error",
            contract_location="test",
            fix_guidance="fix it"
        )
        
        with self.assertRaises(ValueError) as context:
            MappingContractValidationResult(
                is_valid=True,
                errors=[error],
                warnings=[]
            )
        
        self.assertIn("cannot be valid with errors present", str(context.exception))
    
    def test_post_init_validation_no_errors_but_invalid_flag(self):
        """Cannot create result without errors but is_valid=False."""
        with self.assertRaises(ValueError) as context:
            MappingContractValidationResult(
                is_valid=False,
                errors=[],
                warnings=[]
            )
        
        self.assertIn("must be valid if no errors present", str(context.exception))
    
    def test_format_summary_valid_no_warnings(self):
        """Format summary for completely valid result."""
        result = MappingContractValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        summary = result.format_summary()
        
        self.assertIn(">", summary)
        self.assertIn("passed", summary)
        self.assertIn("no errors, no warnings", summary)
    
    def test_format_summary_valid_with_warnings(self):
        """Format summary for valid result with warnings."""
        warning = MappingContractValidationWarning(
            category="performance",
            message="Many mappings",
            contract_location="mappings",
            recommendation="Optimize"
        )
        
        result = MappingContractValidationResult(
            is_valid=True,
            errors=[],
            warnings=[warning]
        )
        
        summary = result.format_summary()
        
        self.assertIn("!:", summary)
        self.assertIn("1 warning(s)", summary)
        self.assertIn("[performance]", summary)
        self.assertIn("Many mappings", summary)
    
    def test_format_summary_invalid_with_errors(self):
        """Format summary for invalid result with errors."""
        error = MappingContractValidationError(
            category="element_filtering",
            message="Missing filter rule",
            contract_location="element_filtering.filter_rules",
            fix_guidance="Add it",
            example_fix='{"example": "here"}'
        )
        
        result = MappingContractValidationResult(
            is_valid=False,
            errors=[error],
            warnings=[]
        )
        
        summary = result.format_summary()
        
        self.assertIn("X:", summary)
        self.assertIn("FAILED", summary)
        self.assertIn("1 error(s)", summary)
        self.assertIn("[element_filtering]", summary)
        self.assertIn("Missing filter rule", summary)
        self.assertIn("Location:", summary)
        self.assertIn("Fix:", summary)
        self.assertIn("Example:", summary)
    
    def test_format_summary_multiple_errors_and_warnings(self):
        """Format summary with multiple errors and warnings."""
        error1 = MappingContractValidationError(
            category="element_filtering",
            message="Missing contact rule",
            contract_location="element_filtering.filter_rules",
            fix_guidance="Add contact rule"
        )
        
        error2 = MappingContractValidationError(
            category="relationships",
            message="Missing foreign key",
            contract_location="relationships[0]",
            fix_guidance="Add foreign_key_column"
        )
        
        warning = MappingContractValidationWarning(
            category="performance",
            message="Large contract",
            contract_location="mappings",
            recommendation="Consider splitting"
        )
        
        result = MappingContractValidationResult(
            is_valid=False,
            errors=[error1, error2],
            warnings=[warning]
        )
        
        summary = result.format_summary()
        
        # Check errors section
        self.assertIn("X:", summary)
        self.assertIn("2 error(s)", summary)
        self.assertIn("Missing contact rule", summary)
        self.assertIn("Missing foreign key", summary)
        
        # Check warnings section
        self.assertIn("!:", summary)
        self.assertIn("1 warning(s)", summary)
        self.assertIn("Large contract", summary)


if __name__ == '__main__':
    unittest.main()
