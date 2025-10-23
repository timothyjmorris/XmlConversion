"""
Test module for the comprehensive data integrity validation system.

This module provides test cases and validation scenarios to ensure
the validation system works correctly with various data conditions.
"""

import unittest
import json
import logging
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from xml_extractor.validation.data_integrity_validator import DataIntegrityValidator
    from xml_extractor.validation.validation_models import ValidationConfig, ValidationSeverity, ValidationType
    from xml_extractor.validation.validation_integration import ValidationOrchestrator, ValidationReporter
    from xml_extractor.models import MappingContract, FieldMapping, RelationshipMapping
except ImportError as e:
    print(f"Import error: {e}")
    print("This test requires the xml_extractor package to be installed or available in the Python path")
    sys.exit(1)


class TestValidationSystem(unittest.TestCase):
    """
    Test harness for the data integrity validation system.
    
    Provides test scenarios and validation of the validation system itself.
    """
    
    def setUp(self):
        """Initialize the test harness."""
        self.logger = logging.getLogger(__name__)
        
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """
        Run comprehensive tests of the validation system.
        
        Returns:
            Test results summary
        """
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_details': []
        }
        
        # Test scenarios
        test_scenarios = [
            ('test_valid_data_validation', self._run_valid_data_validation),
            ('test_missing_app_id_validation', self._test_missing_app_id_validation),
            ('test_missing_contact_id_validation', self._test_missing_contact_id_validation),
            ('test_referential_integrity_validation', self._test_referential_integrity_validation),
            ('test_constraint_compliance_validation', self._test_constraint_compliance_validation),
            ('test_data_quality_metrics', self._test_data_quality_metrics),
            ('test_validation_orchestrator', self._test_validation_orchestrator),
            ('test_validation_reporter', self._test_validation_reporter)
        ]
        
        for test_name, test_func in test_scenarios:
            try:
                self.logger.info(f"Running test: {test_name}")
                test_result = test_func()
                test_results['tests_run'] += 1
                
                if test_result.get('passed', False):
                    test_results['tests_passed'] += 1
                    self.logger.info(f"Test {test_name} PASSED")
                else:
                    test_results['tests_failed'] += 1
                    self.logger.error(f"Test {test_name} FAILED: {test_result.get('error', 'Unknown error')}")
                
                test_results['test_details'].append({
                    'test_name': test_name,
                    'passed': test_result.get('passed', False),
                    'error': test_result.get('error'),
                    'details': test_result.get('details', {})
                })
                
            except Exception as e:
                test_results['tests_run'] += 1
                test_results['tests_failed'] += 1
                error_msg = f"Test {test_name} threw exception: {e}"
                self.logger.error(error_msg)
                
                test_results['test_details'].append({
                    'test_name': test_name,
                    'passed': False,
                    'error': error_msg,
                    'details': {}
                })
        
        # Calculate success rate
        if test_results['tests_run'] > 0:
            success_rate = (test_results['tests_passed'] / test_results['tests_run']) * 100
            test_results['success_rate'] = success_rate
        else:
            test_results['success_rate'] = 0
        
        self.logger.info(
            f"Test suite completed: {test_results['tests_passed']}/{test_results['tests_run']} passed "
            f"({test_results['success_rate']:.1f}%)"
        )
        
        return test_results
    
    def test_valid_data_validation(self):
        """Test validation with valid data."""
        # Create test data
        source_xml_data = self._create_valid_xml_data()
        extracted_tables = self._create_valid_extracted_tables()
        mapping_contract = self._create_test_mapping_contract()
        
        # Run validation
        validator = DataIntegrityValidator(ValidationConfig())
        result = validator.validate_extraction_results(
            source_xml_data=source_xml_data,
            extracted_tables=extracted_tables,
            mapping_contract=mapping_contract,
            source_record_id="123456"  # Match the app_id from test data
        )
        
        # Validate results
        self.assertTrue(result.validation_passed, "Valid data should pass validation")
        self.assertEqual(result.total_errors, 0, "Valid data should have no errors")
    
    def test_missing_app_id_validation(self):
        """Test validation with missing app_id."""
        result = self._test_missing_app_id_validation()
        self.assertTrue(result['passed'], result.get('error', 'Test failed'))
    
    def test_missing_contact_id_validation(self):
        """Test validation with missing contact IDs."""
        result = self._test_missing_contact_id_validation()
        self.assertTrue(result['passed'], result.get('error', 'Test failed'))
    
    def test_referential_integrity_validation(self):
        """Test referential integrity validation."""
        result = self._test_referential_integrity_validation()
        self.assertTrue(result['passed'], result.get('error', 'Test failed'))
    
    def test_constraint_compliance_validation(self):
        """Test constraint compliance validation."""
        result = self._test_constraint_compliance_validation()
        self.assertTrue(result['passed'], result.get('error', 'Test failed'))
    
    def test_data_quality_metrics(self):
        """Test data quality metrics calculation."""
        result = self._test_data_quality_metrics()
        self.assertTrue(result['passed'], result.get('error', 'Test failed'))
    
    def test_validation_orchestrator(self):
        """Test validation orchestrator functionality."""
        result = self._test_validation_orchestrator()
        self.assertTrue(result['passed'], result.get('error', 'Test failed'))
    
    def test_validation_reporter(self):
        """Test validation reporter functionality."""
        result = self._test_validation_reporter()
        self.assertTrue(result['passed'], result.get('error', 'Test failed'))
    
    def _run_valid_data_validation(self) -> Dict[str, Any]:
        """Run valid data validation test and return result."""
        try:
            # Create test data
            source_xml_data = self._create_valid_xml_data()
            extracted_tables = self._create_valid_extracted_tables()
            mapping_contract = self._create_test_mapping_contract()
            
            # Run validation
            validator = DataIntegrityValidator(ValidationConfig())
            result = validator.validate_extraction_results(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract,
                source_record_id="123456"  # Match the app_id from test data
            )
            
            # Check results
            if result.validation_passed and result.total_errors == 0:
                return {'passed': True, 'details': {'records_validated': result.total_records_validated}}
            else:
                return {'passed': False, 'error': f'Validation failed: {result.total_errors} errors'}
                
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _test_missing_app_id_validation(self) -> Dict[str, Any]:
        """Test validation with missing app_id."""
        try:
            # Create test data without app_id
            source_xml_data = {'Provenir': {'Request': {}}}  # Missing ID attribute
            extracted_tables = self._create_valid_extracted_tables()
            mapping_contract = self._create_test_mapping_contract()
            
            # Run validation
            validator = DataIntegrityValidator(ValidationConfig())
            result = validator.validate_extraction_results(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract
            )
            
            # Should fail validation
            if not result.validation_passed and result.total_errors > 0:
                # Check for specific error about missing app_id
                has_app_id_error = any('app_id' in str(error).lower() for error in result.errors)
                if has_app_id_error:
                    return {'passed': True, 'details': {'errors_found': result.total_errors}}
                else:
                    return {'passed': False, 'error': 'Missing app_id error not detected'}
            else:
                return {'passed': False, 'error': 'Validation should have failed for missing app_id'}
                
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _test_missing_contact_id_validation(self) -> Dict[str, Any]:
        """Test validation with missing contact IDs."""
        try:
            # Create test data without contact IDs
            source_xml_data = {
                'Provenir': {
                    'Request': {
                        'ID': '123456',
                        'CustData': {
                            'application': {
                                'contact': [
                                    {'name': 'John Doe'},  # Missing con_id
                                    {'name': 'Jane Doe'}   # Missing con_id
                                ]
                            }
                        }
                    }
                }
            }
            extracted_tables = self._create_valid_extracted_tables()
            mapping_contract = self._create_test_mapping_contract()
            
            # Run validation
            validator = DataIntegrityValidator(ValidationConfig())
            result = validator.validate_extraction_results(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract
            )
            
            # Should fail validation
            if not result.validation_passed and result.total_errors > 0:
                return {'passed': True, 'details': {'errors_found': result.total_errors}}
            else:
                return {'passed': False, 'error': 'Validation should have failed for missing contact IDs'}
                
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _test_referential_integrity_validation(self) -> Dict[str, Any]:
        """Test referential integrity validation."""
        try:
            # Create test data with referential integrity issues
            source_xml_data = self._create_valid_xml_data()
            extracted_tables = {
                'app_base': [{'app_id': 123456}],
                'contact_base': [{'con_id': 789, 'app_id': 123456}],
                'contact_address': [
                    {'con_id': 999, 'app_id': 123456},  # Invalid con_id reference
                    {'con_id': 789, 'app_id': 999999}   # Invalid app_id reference
                ]
            }
            mapping_contract = self._create_test_mapping_contract()
            
            # Run validation
            validator = DataIntegrityValidator(ValidationConfig())
            result = validator.validate_extraction_results(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract
            )
            
            # Should detect referential integrity errors
            referential_errors = result.get_errors_by_type(ValidationType.REFERENTIAL_INTEGRITY)
            if len(referential_errors) >= 2:  # Should find both invalid references
                return {'passed': True, 'details': {'referential_errors': len(referential_errors)}}
            else:
                return {
                    'passed': False,
                    'error': f'Expected 2+ referential integrity errors, found {len(referential_errors)}'
                }
                
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _test_constraint_compliance_validation(self) -> Dict[str, Any]:
        """Test constraint compliance validation."""
        try:
            # Create test data with constraint violations
            source_xml_data = self._create_valid_xml_data()
            extracted_tables = {
                'app_base': [
                    {'app_id': None},  # Required field violation
                    {'app_id': 123456, 'ssn': '123456789'}  # Valid record
                ],
                'contact_base': [
                    {'con_id': 789, 'app_id': 123456, 'ssn': '000000000'}  # Invalid SSN
                ]
            }
            mapping_contract = self._create_test_mapping_contract()
            
            # Run validation
            validator = DataIntegrityValidator(ValidationConfig())
            result = validator.validate_extraction_results(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract
            )
            
            # Should detect constraint violations
            constraint_errors = result.get_errors_by_type(ValidationType.CONSTRAINT_COMPLIANCE)
            if len(constraint_errors) >= 2:  # Should find null app_id and invalid SSN
                return {'passed': True, 'details': {'constraint_errors': len(constraint_errors)}}
            else:
                return {
                    'passed': False,
                    'error': f'Expected 2+ constraint errors, found {len(constraint_errors)}'
                }
                
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _test_data_quality_metrics(self) -> Dict[str, Any]:
        """Test data quality metrics calculation."""
        try:
            # Create test data with quality issues
            source_xml_data = self._create_valid_xml_data()
            extracted_tables = {
                'app_base': [
                    {'app_id': 123456, 'name': 'John Doe', 'email': 'john@example.com'},
                    {'app_id': 789012, 'name': '', 'email': None}  # Missing data
                ],
                'contact_base': [
                    {'con_id': 789, 'app_id': 123456, 'name': 'Jane Doe'},
                    {'con_id': 101112, 'app_id': 789012, 'name': None}  # Missing data
                ]
            }
            mapping_contract = self._create_test_mapping_contract()
            
            # Run validation
            validator = DataIntegrityValidator(ValidationConfig())
            result = validator.validate_extraction_results(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract
            )
            
            # Check data quality metrics
            if result.data_quality_metrics:
                completeness = result.data_quality_metrics.get('completeness_percentage', 0)
                if 0 <= completeness <= 100:
                    return {
                        'passed': True,
                        'details': {
                            'completeness': completeness,
                            'total_fields': result.data_quality_metrics.get('total_fields', 0)
                        }
                    }
                else:
                    return {'passed': False, 'error': f'Invalid completeness percentage: {completeness}'}
            else:
                return {'passed': False, 'error': 'No data quality metrics calculated'}
                
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _test_validation_orchestrator(self) -> Dict[str, Any]:
        """Test validation orchestrator functionality."""
        try:
            # Create test data
            source_xml_data = self._create_valid_xml_data()
            extracted_tables = self._create_valid_extracted_tables()
            mapping_contract = self._create_test_mapping_contract()
            
            # Test orchestrator
            orchestrator = ValidationOrchestrator()
            result = orchestrator.validate_complete_extraction(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract,
                source_record_id="test_orchestrator"
            )
            
            # Check orchestrator functionality
            if result and hasattr(result, 'validation_id'):
                stats = orchestrator.get_validation_statistics()
                if stats.get('total_validations', 0) > 0:
                    return {'passed': True, 'details': {'stats': stats}}
                else:
                    return {'passed': False, 'error': 'Orchestrator statistics not updated'}
            else:
                return {'passed': False, 'error': 'Orchestrator did not return valid result'}
                
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    def _test_validation_reporter(self) -> Dict[str, Any]:
        """Test validation reporter functionality."""
        try:
            # Create test validation results
            source_xml_data = self._create_valid_xml_data()
            extracted_tables = self._create_valid_extracted_tables()
            mapping_contract = self._create_test_mapping_contract()
            
            validator = DataIntegrityValidator(ValidationConfig())
            validation_results = [
                validator.validate_extraction_results(
                    source_xml_data=source_xml_data,
                    extracted_tables=extracted_tables,
                    mapping_contract=mapping_contract,
                    source_record_id=f"test_{i}"
                )
                for i in range(3)
            ]
            
            # Test reporter
            reporter = ValidationReporter()
            
            # Test CSV report
            csv_report = reporter.generate_csv_report(validation_results)
            if not csv_report or 'validation_id' not in csv_report:
                return {'passed': False, 'error': 'CSV report generation failed'}
            
            # Test JSON report
            json_report = reporter.generate_json_report(validation_results)
            if not json_report or 'summary' not in json_report:
                return {'passed': False, 'error': 'JSON report generation failed'}
            
            return {
                'passed': True,
                'details': {
                    'csv_lines': len(csv_report.split('\n')),
                    'json_validations': len(json_report.get('validations', []))
                }
            }
            
        except Exception as e:
            return {'passed': False, 'error': str(e)}
    
    # Helper methods for creating test data
    def _create_valid_xml_data(self) -> Dict[str, Any]:
        """Create valid XML data for testing."""
        return {
            'Provenir': {
                'Request': {
                    'ID': '123456',
                    'CustData': {
                        'application': {
                            'contact': [
                                {'con_id': '789', 'name': 'John Doe', 'email': 'john@example.com'},
                                {'con_id': '101112', 'name': 'Jane Doe', 'email': 'jane@example.com'}
                            ]
                        }
                    }
                }
            }
        }
    
    def _create_valid_extracted_tables(self) -> Dict[str, List[Dict[str, Any]]]:
        """Create valid extracted tables for testing."""
        return {
            'app_base': [
                {'app_id': 123456, 'name': 'Test Application', 'created_date': datetime.now()}
            ],
            'contact_base': [
                {'con_id': 789, 'app_id': 123456, 'name': 'John Doe', 'created_date': datetime.now()},
                {'con_id': 101112, 'app_id': 123456, 'name': 'Jane Doe', 'created_date': datetime.now()}
            ],
            'contact_address': [
                {'con_id': 789, 'app_id': 123456, 'address_line1': '123 Main St', 'created_date': datetime.now()}
            ]
        }
    
    def _create_test_mapping_contract(self) -> MappingContract:
        """Create a test mapping contract."""
        mappings = [
            FieldMapping(
                xml_path='/Provenir/Request',
                xml_attribute='ID',
                target_table='app_base',
                target_column='app_id',
                data_type='int'
            ),
            FieldMapping(
                xml_path='/Provenir/Request/CustData/application/contact',
                xml_attribute='con_id',
                target_table='contact_base',
                target_column='con_id',
                data_type='int'
            )
        ]
        
        relationships = [
            RelationshipMapping(
                parent_table='app_base',
                child_table='contact_base',
                foreign_key_column='app_id',
                xml_parent_path='/Provenir/Request',
                xml_child_path='/Provenir/Request/CustData/application/contact'
            )
        ]
        
        return MappingContract(
            source_table='app_xml',
            source_column='xml',
            xml_root_element='Provenir',
            mappings=mappings,
            relationships=relationships
        )


def run_validation_system_tests() -> Dict[str, Any]:
    """
    Run comprehensive tests of the validation system.
    
    Returns:
        Test results summary
    """
    tester = TestValidationSystem()
    tester.setUp()
    return tester.run_comprehensive_tests()


def run_custom_test_harness():
    """Run the custom test harness for standalone execution."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n🧪 VALIDATION SYSTEM UNIT TESTS")
    print("=" * 80)
    
    # Run tests using the custom harness
    results = run_validation_system_tests()
    
    # Print results in a nice format
    print(f"📋 Tests Run: {results['tests_run']}")
    print(f"✅ Tests Passed: {results['tests_passed']}")
    print(f"❌ Tests Failed: {results['tests_failed']}")
    print(f"📊 Success Rate: {results['success_rate']:.1f}%")
    
    if results['test_details']:
        print("\n📋 Test Details:")
        for test in results['test_details']:
            status = "✅ PASS" if test['passed'] else "❌ FAIL"
            print(f"  {test['test_name']}: {status}")
            if not test['passed'] and test.get('error'):
                print(f"    Error: {test['error']}")
    
    if results['tests_failed'] == 0:
        print("\n🎉 ALL VALIDATION SYSTEM TESTS PASSED!")
        print("   System validation components are working correctly")
    else:
        print(f"\n⚠️  {results['tests_failed']} tests failed - check errors above")
    
    print("=" * 80)
    return results['tests_failed'] == 0


if __name__ == "__main__":
    success = run_custom_test_harness()
    sys.exit(0 if success else 1)