"""
Demonstration script for the comprehensive data integrity validation system.

This script shows how to use the validation system with sample data
and demonstrates the key validation capabilities.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from xml_extractor.validation.data_integrity_validator import DataIntegrityValidator
from xml_extractor.validation.validation_models import ValidationConfig, ValidationSeverity, ValidationType
from xml_extractor.validation.validation_integration import ValidationOrchestrator, ValidationReporter
from xml_extractor.models import MappingContract, FieldMapping, RelationshipMapping


def create_sample_data() -> tuple:
    """Create sample XML data and extracted tables for demonstration."""
    
    # Sample XML data (as it would be parsed from XML)
    source_xml_data = {
        'Provenir': {
            'Request': {
                'ID': '123456789',
                'CustData': {
                    'application': {
                        'receive_date': '2024-01-15',
                        'contact': [
                            {
                                'con_id': '987654321',
                                'contact_type': 'PR',
                                'first_name': 'John',
                                'last_name': 'Doe',
                                'ssn': '123456789',
                                'birth_date': '1985-03-15',
                                'email': 'john.doe@example.com'
                            },
                            {
                                'con_id': '987654322',
                                'contact_type': 'AUTH',
                                'first_name': 'Jane',
                                'last_name': 'Doe',
                                'ssn': '987654321',
                                'birth_date': '1987-07-22',
                                'email': 'jane.doe@example.com'
                            }
                        ]
                    }
                }
            }
        }
    }
    
    # Sample extracted relational data
    extracted_tables = {
        'app_base': [
            {
                'app_id': 123456789,
                'receive_date': datetime(2024, 1, 15),
                'product_line_enum': 600,
                'created_date': datetime.utcnow(),
                'last_updated_date': datetime.utcnow()
            }
        ],
        'contact_base': [
            {
                'con_id': 987654321,
                'app_id': 123456789,
                'contact_type_enum': 1,  # PR
                'first_name': 'John',
                'last_name': 'Doe',
                'ssn': '123456789',
                'birth_date': datetime(1985, 3, 15),
                'email': 'john.doe@example.com',
                'created_date': datetime.utcnow(),
                'last_updated_date': datetime.utcnow()
            },
            {
                'con_id': 987654322,
                'app_id': 123456789,
                'contact_type_enum': 2,  # AUTH
                'first_name': 'Jane',
                'last_name': 'Doe',
                'ssn': '987654321',
                'birth_date': datetime(1987, 7, 22),
                'email': 'jane.doe@example.com',
                'created_date': datetime.utcnow(),
                'last_updated_date': datetime.utcnow()
            }
        ],
        'contact_address': [
            {
                'con_id': 987654321,
                'app_id': 123456789,
                'address_line1': '123 Main Street',
                'city': 'Anytown',
                'state': 'CA',
                'zip_code': '12345',
                'created_date': datetime.utcnow(),
                'last_updated_date': datetime.utcnow()
            }
        ]
    }
    
    # Sample mapping contract
    mappings = [
        FieldMapping(
            xml_path='/Provenir/Request',
            xml_attribute='ID',
            target_table='app_base',
            target_column='app_id',
            data_type='int'
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application',
            xml_attribute='receive_date',
            target_table='app_base',
            target_column='receive_date',
            data_type='datetime'
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application/contact',
            xml_attribute='con_id',
            target_table='contact_base',
            target_column='con_id',
            data_type='int'
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application/contact',
            xml_attribute='first_name',
            target_table='contact_base',
            target_column='first_name',
            data_type='varchar(50)'
        ),
        FieldMapping(
            xml_path='/Provenir/Request/CustData/application/contact',
            xml_attribute='ssn',
            target_table='contact_base',
            target_column='ssn',
            data_type='char(9)'
        )
    ]
    
    relationships = [
        RelationshipMapping(
            parent_table='app_base',
            child_table='contact_base',
            foreign_key_column='app_id',
            xml_parent_path='/Provenir/Request',
            xml_child_path='/Provenir/Request/CustData/application/contact'
        ),
        RelationshipMapping(
            parent_table='contact_base',
            child_table='contact_address',
            foreign_key_column='con_id',
            xml_parent_path='/Provenir/Request/CustData/application/contact',
            xml_child_path='/Provenir/Request/CustData/application/contact/address'
        )
    ]
    
    mapping_contract = MappingContract(
        source_table='app_xml',
        source_column='xml',
        xml_root_element='Provenir',
        mappings=mappings,
        relationships=relationships
    )
    
    return source_xml_data, extracted_tables, mapping_contract


def demonstrate_basic_validation():
    """Demonstrate basic validation functionality."""
    print("\n" + "="*60)
    print("BASIC VALIDATION DEMONSTRATION")
    print("="*60)
    
    # Create sample data
    source_xml_data, extracted_tables, mapping_contract = create_sample_data()
    
    # Configure validation
    config = ValidationConfig(
        enable_end_to_end_validation=True,
        enable_referential_integrity=True,
        enable_constraint_compliance=True,
        enable_data_quality_checks=True
    )
    
    # Create validator and run validation
    validator = DataIntegrityValidator(config)
    result = validator.validate_extraction_results(
        source_xml_data=source_xml_data,
        extracted_tables=extracted_tables,
        mapping_contract=mapping_contract,
        source_record_id="demo_123456789"
    )
    
    # Display results
    print(f"Validation ID: {result.validation_id}")
    print(f"Validation Passed: {'YES' if result.validation_passed else 'NO'}")
    print(f"Records Validated: {result.total_records_validated}")
    print(f"Total Errors: {result.total_errors}")
    print(f"Total Warnings: {result.total_warnings}")
    print(f"Execution Time: {result.execution_time_ms:.2f}ms")
    
    # Show integrity checks
    if result.integrity_checks:
        print("\nIntegrity Checks:")
        for check in result.integrity_checks:
            status = "PASSED" if check.passed else "FAILED"
            print(f"  - {check.check_name}: {status}")
            print(f"    Records Checked: {check.records_checked}")
            print(f"    Errors: {check.errors_found}, Warnings: {check.warnings_found}")
    
    # Show data quality metrics
    if result.data_quality_metrics:
        print("\nData Quality Metrics:")
        metrics = result.data_quality_metrics
        print(f"  - Completeness: {metrics.get('completeness_percentage', 0):.2f}%")
        print(f"  - Validity: {metrics.get('validity_percentage', 0):.2f}%")
        print(f"  - Accuracy: {metrics.get('accuracy_percentage', 0):.2f}%")
        print(f"  - Total Fields: {metrics.get('total_fields', 0)}")
    
    # Show errors if any
    if result.errors:
        print(f"\nFirst {min(3, len(result.errors))} Errors/Warnings:")
        for i, error in enumerate(result.errors[:3]):
            print(f"  {i+1}. [{error.severity.value.upper()}] {error.message}")
            if error.table_name:
                print(f"     Table: {error.table_name}")
            if error.field_name:
                print(f"     Field: {error.field_name}")
    
    return result


def demonstrate_validation_with_errors():
    """Demonstrate validation with intentional errors."""
    print("\n" + "="*60)
    print("VALIDATION WITH ERRORS DEMONSTRATION")
    print("="*60)
    
    # Create sample data with errors
    source_xml_data, extracted_tables, mapping_contract = create_sample_data()
    
    # Introduce errors
    # 1. Missing app_id in one record
    extracted_tables['contact_base'][0]['app_id'] = None
    
    # 2. Invalid foreign key reference
    extracted_tables['contact_address'][0]['con_id'] = 999999999  # Non-existent con_id
    
    # 3. Invalid SSN
    extracted_tables['contact_base'][1]['ssn'] = '000000000'  # Invalid SSN pattern
    
    # 4. Missing required field
    del extracted_tables['contact_base'][1]['con_id']
    
    # Run validation
    validator = DataIntegrityValidator(ValidationConfig())
    result = validator.validate_extraction_results(
        source_xml_data=source_xml_data,
        extracted_tables=extracted_tables,
        mapping_contract=mapping_contract,
        source_record_id="demo_with_errors"
    )
    
    # Display results
    print(f"Validation Passed: {'YES' if result.validation_passed else 'NO'}")
    print(f"Total Errors: {result.total_errors}")
    print(f"Total Warnings: {result.total_warnings}")
    
    # Group errors by type
    error_types = {}
    for error in result.errors:
        error_type = error.error_type.value
        if error_type not in error_types:
            error_types[error_type] = []
        error_types[error_type].append(error)
    
    print("\nErrors by Type:")
    for error_type, errors in error_types.items():
        print(f"  {error_type.upper()}: {len(errors)} errors")
        for error in errors[:2]:  # Show first 2 errors of each type
            print(f"    - {error.message}")
    
    return result


def demonstrate_validation_orchestrator():
    """Demonstrate validation orchestrator functionality."""
    print("\n" + "="*60)
    print("VALIDATION ORCHESTRATOR DEMONSTRATION")
    print("="*60)
    
    # Create sample data
    source_xml_data, extracted_tables, mapping_contract = create_sample_data()
    
    # Create orchestrator
    orchestrator = ValidationOrchestrator()
    
    # Validate single extraction
    result = orchestrator.validate_complete_extraction(
        source_xml_data=source_xml_data,
        extracted_tables=extracted_tables,
        mapping_contract=mapping_contract,
        source_record_id="orchestrator_demo"
    )
    
    print(f"Single Validation Result: {'PASSED' if result.validation_passed else 'FAILED'}")
    
    # Simulate batch validation
    batch_results = []
    for i in range(3):
        batch_results.append({
            'source_xml_data': source_xml_data,
            'extracted_tables': extracted_tables,
            'source_record_id': f"batch_record_{i}"
        })
    
    batch_summary = orchestrator.validate_batch_extraction(batch_results, mapping_contract)
    
    print(f"\nBatch Validation Summary:")
    print(f"  Total Records: {batch_summary['total_records']}")
    print(f"  Overall Passed: {'YES' if batch_summary['overall_passed'] else 'NO'}")
    print(f"  Total Errors: {batch_summary['total_errors']}")
    print(f"  Total Warnings: {batch_summary['total_warnings']}")
    print(f"  Execution Time: {batch_summary['execution_time_ms']:.2f}ms")
    
    # Get orchestrator statistics
    stats = orchestrator.get_validation_statistics()
    print(f"\nOrchestrator Statistics:")
    print(f"  Total Validations: {stats['total_validations']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print(f"  Average Execution Time: {stats['average_execution_time_ms']:.2f}ms")
    
    return batch_summary


def demonstrate_validation_reporting():
    """Demonstrate validation reporting functionality."""
    print("\n" + "="*60)
    print("VALIDATION REPORTING DEMONSTRATION")
    print("="*60)
    
    # Create sample validation results
    source_xml_data, extracted_tables, mapping_contract = create_sample_data()
    validator = DataIntegrityValidator(ValidationConfig())
    
    validation_results = []
    for i in range(2):
        result = validator.validate_extraction_results(
            source_xml_data=source_xml_data,
            extracted_tables=extracted_tables,
            mapping_contract=mapping_contract,
            source_record_id=f"report_demo_{i}"
        )
        validation_results.append(result)
    
    # Create reporter
    reporter = ValidationReporter()
    
    # Generate text report
    orchestrator = ValidationOrchestrator()
    text_report = orchestrator.generate_validation_report(validation_results, include_details=True)
    
    print("Text Report Preview (first 500 characters):")
    print("-" * 40)
    print(text_report[:500] + "..." if len(text_report) > 500 else text_report)
    
    # Generate CSV report
    csv_report = reporter.generate_csv_report(validation_results)
    print(f"\nCSV Report Generated: {len(csv_report.split(chr(10)))} lines")
    
    # Generate JSON report
    json_report = reporter.generate_json_report(validation_results)
    print(f"JSON Report Generated: {len(json_report['validations'])} validation records")
    
    return text_report, csv_report, json_report


def main():
    """Run all validation demonstrations."""
    # Configure logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise for demo
    
    print("COMPREHENSIVE DATA INTEGRITY VALIDATION SYSTEM DEMONSTRATION")
    print("=" * 80)
    print("This demonstration shows the key capabilities of the validation system:")
    print("- End-to-end validation comparing source XML with extracted data")
    print("- Referential integrity checking for foreign key relationships")
    print("- Constraint compliance validation for target tables")
    print("- Data quality reporting with detailed error information")
    
    try:
        # Run demonstrations
        result1 = demonstrate_basic_validation()
        result2 = demonstrate_validation_with_errors()
        result3 = demonstrate_validation_orchestrator()
        result4 = demonstrate_validation_reporting()
        
        print("\n" + "="*80)
        print("DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*80)
        print("The validation system is working correctly and ready for use.")
        print("Key features demonstrated:")
        print("✓ Basic validation with clean data")
        print("✓ Error detection and reporting")
        print("✓ Batch validation orchestration")
        print("✓ Comprehensive reporting capabilities")
        
    except Exception as e:
        print(f"\nDemonstration failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()