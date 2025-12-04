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
        
        # Use valid contract to avoid validation errors
        contract = {
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
        
        # Use valid contract to avoid validation errors
        contract = {
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


class TestElementFilteringValidation(unittest.TestCase):
    """Test _validate_element_filtering() method - structure validation only."""
    
    def test_valid_element_filtering_with_contact_and_address(self):
        """Contract with contact and address filter rules passes."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact", "required_attributes": {"con_id": True}},
                    {"element_type": "address", "required_attributes": {"address_tp_c": ["CURR"]}}
                ]
            },
            "relationships": [],
            "table_insertion_order": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
    
    def test_valid_with_extra_filter_rules(self):
        """Contract with contact, address, and additional filter rules passes."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact", "required_attributes": {}},
                    {"element_type": "address", "required_attributes": {}},
                    {"element_type": "employment", "required_attributes": {}}
                ]
            },
            "relationships": [],
            "table_insertion_order": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
    
    def test_missing_element_filtering_section(self):
        """Contract without element_filtering section fails."""
        contract = {
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.error_count, 0)
        # Check error details
        error = result.errors[0]
        self.assertEqual(error.category, "element_filtering")
        self.assertIn("element_filtering", error.message.lower())
    
    def test_missing_filter_rules_key(self):
        """Contract with element_filtering but no filter_rules key fails."""
        contract = {
            "element_filtering": {},
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.error_count, 0)
    
    def test_empty_filter_rules_array(self):
        """Contract with empty filter_rules array fails."""
        contract = {
            "element_filtering": {"filter_rules": []},
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.error_count, 0)
    
    def test_missing_contact_filter_rule(self):
        """Contract with address but no contact filter rule fails."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "address", "required_attributes": {}}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        # Check error specifics
        error = result.errors[0]
        self.assertEqual(error.category, "element_filtering")
        self.assertIn("contact", error.message.lower())
        self.assertIn("element_filtering.filter_rules", error.contract_location)
        self.assertIsNotNone(error.fix_guidance)
    
    def test_missing_address_filter_rule(self):
        """Contract with contact but no address filter rule fails."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact", "required_attributes": {}}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        # Check error specifics
        error = result.errors[0]
        self.assertEqual(error.category, "element_filtering")
        self.assertIn("address", error.message.lower())
        self.assertIn("element_filtering.filter_rules", error.contract_location)
        self.assertIsNotNone(error.fix_guidance)
    
    def test_missing_both_contact_and_address_rules(self):
        """Contract missing both contact and address rules reports both errors."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "employment", "required_attributes": {}}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 2)
        # Both errors should be present
        error_messages = [e.message.lower() for e in result.errors]
        self.assertTrue(any("contact" in msg for msg in error_messages))
        self.assertTrue(any("address" in msg for msg in error_messages))
    
    def test_filter_values_not_validated(self):
        """Validator does NOT check filter attribute values (structure only)."""
        # Even with nonsensical filter values, structure validation passes
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact", "required_attributes": {"nonsense": ["bad", "values"]}},
                    {"element_type": "address", "required_attributes": {"invalid": "data"}}
                ]
            },
            "relationships": [],
            "table_insertion_order": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        # Should pass - we only validate structure (contact + address rules exist)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)


class TestRelationshipsValidation(unittest.TestCase):
    """Test _validate_relationships() method - cross-reference with table_insertion_order."""
    
    def test_valid_relationships_with_all_tables_present(self):
        """Contract with all tables from insertion order in relationships passes."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": [
                "app_base",
                "app_contact_base",
                "app_contact_address",
                "processing_log"
            ],
            "relationships": [
                {"parent_table": "app_base", "child_table": "app_contact_base", "foreign_key_column": "app_id"},
                {"parent_table": "app_contact_base", "child_table": "app_contact_address", "foreign_key_column": "con_id"}
            ],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
    
    def test_processing_log_excluded_from_validation(self):
        """processing_log in table_insertion_order does not require relationship."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": [
                "app_base",
                "processing_log"  # No relationship needed
            ],
            "relationships": [
                # No relationship for processing_log - should be fine
            ],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
    
    def test_missing_table_insertion_order_section(self):
        """Contract without table_insertion_order fails."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "relationships": [],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.error_count, 0)
        error = result.errors[0]
        self.assertEqual(error.category, "relationships")
        self.assertIn("table_insertion_order", error.message.lower())
    
    def test_missing_relationships_section(self):
        """Contract without relationships section fails."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "app_contact_base"],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.error_count, 0)
    
    def test_orphaned_table_in_insertion_order(self):
        """Table in insertion_order but not in relationships fails."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": [
                "app_base",
                "app_contact_base",
                "app_contact_address",  # Missing from relationships
                "processing_log"
            ],
            "relationships": [
                {"parent_table": "app_base", "child_table": "app_contact_base", "foreign_key_column": "app_id"}
                # app_contact_address is missing!
            ],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        error = result.errors[0]
        self.assertEqual(error.category, "relationships")
        self.assertIn("app_contact_address", error.message)
        self.assertIn("table_insertion_order", error.message.lower())
    
    def test_multiple_orphaned_tables(self):
        """Multiple tables missing from relationships reported."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": [
                "app_base",
                "app_contact_base",
                "app_contact_address",
                "app_contact_employment",
                "processing_log"
            ],
            "relationships": [
                {"parent_table": "app_base", "child_table": "app_contact_base", "foreign_key_column": "app_id"}
                # app_contact_address and app_contact_employment missing!
            ],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 2)
        error_messages = [e.message for e in result.errors]
        self.assertTrue(any("app_contact_address" in msg for msg in error_messages))
        self.assertTrue(any("app_contact_employment" in msg for msg in error_messages))
    
    def test_relationship_missing_foreign_key_column(self):
        """Relationship without foreign_key_column field fails."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": [
                "app_base",
                "app_contact_base",
                "processing_log"
            ],
            "relationships": [
                {"parent_table": "app_base", "child_table": "app_contact_base"}  # Missing foreign_key_column!
            ],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertGreater(result.error_count, 0)
        error = result.errors[0]
        self.assertEqual(error.category, "relationships")
        self.assertIn("foreign_key_column", error.message.lower())
        self.assertIn("app_contact_base", error.message)
    
    def test_app_base_not_required_in_relationships(self):
        """app_base as root table doesn't need to appear as child_table."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": [
                "app_base",  # Root table - no relationship as child
                "app_contact_base",
                "processing_log"
            ],
            "relationships": [
                {"parent_table": "app_base", "child_table": "app_contact_base", "foreign_key_column": "app_id"}
                # app_base doesn't appear as child_table - should be OK
            ],
            "enum_mappings": {},
            "mappings": []
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)


class TestEnumMappingsValidation(unittest.TestCase):
    """Test _validate_enum_mappings() - Step 5."""
    
    def test_valid_enum_mappings_all_defined(self):
        """All enum mappings referenced in mappings are defined in enum_mappings."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {
                "app_source_enum": {"WEB": 1, "MOBILE": 2},
                "status_enum": {"ACTIVE": 1, "INACTIVE": 2}
            },
            "mappings": [
                {
                    "target_table": "app_base",
                    "target_column": "app_source_enum",
                    "mapping_type": ["enum"]
                },
                {
                    "target_table": "app_base",
                    "target_column": "status_enum",
                    "mapping_type": ["enum"]
                },
                {
                    "target_table": "app_base",
                    "target_column": "app_id",
                    "mapping_type": []  # Not an enum
                }
            ]
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
    
    def test_missing_enum_mappings_section(self):
        """Error when enum_mappings section is missing entirely."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            # enum_mappings missing entirely
            "mappings": [
                {
                    "target_table": "app_base",
                    "target_column": "app_source_enum",
                    "mapping_type": ["enum"]
                }
            ]
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        error = result.errors[0]
        self.assertEqual(error.category, "enum_mappings")
        self.assertIn("missing", error.message.lower())
    
    def test_enum_mapping_not_defined(self):
        """Error when mapping uses enum but target_column not in enum_mappings."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {
                "status_enum": {"ACTIVE": 1}
            },
            "mappings": [
                {
                    "target_table": "app_base",
                    "target_column": "app_source_enum",  # Not in enum_mappings!
                    "mapping_type": ["enum"]
                }
            ]
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        error = result.errors[0]
        self.assertEqual(error.category, "enum_mappings")
        self.assertIn("app_source_enum", error.message)
        self.assertIn("not defined", error.message.lower())
    
    def test_multiple_missing_enum_mappings(self):
        """Errors for each missing enum mapping."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {},
            "mappings": [
                {
                    "target_table": "app_base",
                    "target_column": "app_source_enum",
                    "mapping_type": ["enum"]
                },
                {
                    "target_table": "app_base",
                    "target_column": "status_enum",
                    "mapping_type": ["enum"]
                },
                {
                    "target_table": "app_base",
                    "target_column": "decision_enum",
                    "mapping_type": ["enum"]
                }
            ]
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 3)
        # Check all three are reported
        error_messages = " ".join([e.message for e in result.errors])
        self.assertIn("app_source_enum", error_messages)
        self.assertIn("status_enum", error_messages)
        self.assertIn("decision_enum", error_messages)
    
    def test_chained_mapping_type_with_enum(self):
        """Enum validation works when enum is part of chained mapping_type."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {
                "contact_type_enum": {"PR": 1, "AUTHU": 2}
            },
            "mappings": [
                {
                    "target_table": "app_contact_base",
                    "target_column": "contact_type_enum",
                    "mapping_type": ["last_valid_pr_contact", "enum"]  # Chained
                }
            ]
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)
    
    def test_empty_enum_mappings_section_with_enum_usage(self):
        """Error when enum_mappings exists but is empty and enums are used."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {},  # Empty
            "mappings": [
                {
                    "target_table": "app_base",
                    "target_column": "app_source_enum",
                    "mapping_type": ["enum"]
                }
            ]
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_count, 1)
        self.assertIn("app_source_enum", result.errors[0].message)
    
    def test_unused_enum_mappings_allowed(self):
        """Unused enum_mappings (not referenced in mappings) are allowed."""
        contract = {
            "element_filtering": {
                "filter_rules": [
                    {"element_type": "contact"},
                    {"element_type": "address"}
                ]
            },
            "table_insertion_order": ["app_base", "processing_log"],
            "relationships": [],
            "enum_mappings": {
                "app_source_enum": {"WEB": 1},
                "unused_enum": {"VALUE": 99},  # Not referenced - OK
                "another_unused": {"X": 1}      # Also not referenced - OK
            },
            "mappings": [
                {
                    "target_table": "app_base",
                    "target_column": "app_source_enum",
                    "mapping_type": ["enum"]
                }
            ]
        }
        validator = MappingContractValidator(contract)
        
        result = validator.validate_contract()
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.error_count, 0)


if __name__ == '__main__':
    unittest.main()
