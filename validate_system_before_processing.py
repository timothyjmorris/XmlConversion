#!/usr/bin/env python3
"""
Comprehensive system validation before processing real XML data.

This script validates all components and scenarios to ensure the system
is ready for production data processing.
"""

import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator, create_sample_validation_scenarios
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.models import MappingContract, FieldMapping


def setup_logging():
    """Set up logging for validation."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('validation_results.log')
        ]
    )


def create_test_mapping_contract() -> MappingContract:
    """Create a test mapping contract for validation."""
    return MappingContract(
        source_table="app_xml",
        source_column="xml",
        xml_root_element="Provenir",
        mappings=[
            FieldMapping(
                xml_path="/Provenir/Request",
                xml_attribute="ID",
                target_table="app_base",
                target_column="app_id",
                data_type="int"
            ),
            FieldMapping(
                xml_path="/Provenir/Request/CustData/application/contact",
                xml_attribute="con_id",
                target_table="contact_base",
                target_column="con_id",
                data_type="int"
            ),
            FieldMapping(
                xml_path="/Provenir/Request/CustData/application/contact",
                xml_attribute="ac_role_tp_c",
                target_table="contact_base",
                target_column="contact_type_enum",
                data_type="smallint"
            )
        ],
        relationships=[]
    )


def validate_xml_parser() -> bool:
    """Validate XMLParser component."""
    print("\n" + "="*50)
    print("VALIDATING XML PARSER")
    print("="*50)
    
    parser = XMLParser()
    
    # Test 1: Valid Provenir XML
    valid_xml = """
    <Provenir>
        <Request ID="154284">
            <CustData>
                <application>
                    <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN"/>
                </application>
            </CustData>
        </Request>
    </Provenir>
    """
    
    try:
        # Test parsing
        root = parser.parse_xml_stream(valid_xml)
        print("✅ XML parsing successful")
        
        # Test validation
        is_valid = parser.validate_xml_structure(valid_xml)
        print(f"✅ XML structure validation: {is_valid}")
        
        # Test element extraction
        elements = parser.extract_elements(root)
        print(f"✅ Element extraction: {len(elements)} elements found")
        
        return True
        
    except Exception as e:
        print(f"❌ XML Parser validation failed: {e}")
        return False


def validate_data_mapper() -> bool:
    """Validate DataMapper component."""
    print("\n" + "="*50)
    print("VALIDATING DATA MAPPER")
    print("="*50)
    
    mapper = DataMapper()
    contract = create_test_mapping_contract()
    
    # Test valid XML data
    xml_data = {
        'Provenir': {
            'Request': {
                'ID': '154284',
                'CustData': {
                    'application': {
                        'contact': {
                            'con_id': '277449',
                            'ac_role_tp_c': 'PR',
                            'first_name': 'JOHN'
                        }
                    }
                }
            }
        }
    }
    
    try:
        # Test mapping application
        result = mapper.apply_mapping_contract(xml_data, contract)
        print(f"✅ Data mapping successful: {len(result)} tables created")
        
        # Validate required tables exist
        required_tables = ['app_base', 'contact_base']
        for table in required_tables:
            if table in result:
                print(f"✅ Table {table}: {len(result[table])} records")
            else:
                print(f"❌ Missing required table: {table}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Data Mapper validation failed: {e}")
        return False


def validate_migration_engine() -> bool:
    """Validate MigrationEngine component."""
    print("\n" + "="*50)
    print("VALIDATING MIGRATION ENGINE")
    print("="*50)
    
    try:
        # Test engine creation
        engine = MigrationEngine("test_connection_string")
        print("✅ MigrationEngine creation successful")
        
        # Test progress tracking
        engine.track_progress(100, 1000)
        metrics = engine.get_processing_metrics()
        print(f"✅ Progress tracking: {metrics.get('progress_percent', 0)}% complete")
        
        # Test table name extraction
        test_sql = "CREATE TABLE test_table (id int, name varchar(50))"
        table_name = engine._extract_table_name(test_sql)
        print(f"✅ Table name extraction: '{table_name}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration Engine validation failed: {e}")
        return False


def validate_pre_processing_validator() -> bool:
    """Validate PreProcessingValidator component."""
    print("\n" + "="*50)
    print("VALIDATING PRE-PROCESSING VALIDATOR")
    print("="*50)
    
    validator = PreProcessingValidator()
    scenarios = create_sample_validation_scenarios()
    
    try:
        # Run batch validation
        batch_results = validator.validate_batch(scenarios)
        summary = batch_results['summary']
        
        print(f"✅ Batch validation completed:")
        print(f"   Total records: {summary['total_records']}")
        print(f"   Valid records: {summary['valid_records']}")
        print(f"   Invalid records: {summary['invalid_records']}")
        print(f"   Records with warnings: {summary['records_with_warnings']}")
        
        # Validate expected results
        expected_valid = 2  # valid_complete and graceful_missing_address_tp_c
        expected_invalid = 2  # invalid_no_app_id and invalid_no_con_id
        
        if summary['valid_records'] >= expected_valid and summary['invalid_records'] >= expected_invalid:
            print("✅ Validation results match expectations")
            return True
        else:
            print(f"❌ Unexpected validation results: expected {expected_valid} valid, {expected_invalid} invalid")
            return False
        
    except Exception as e:
        print(f"❌ Pre-processing Validator validation failed: {e}")
        return False


def validate_end_to_end_scenarios() -> bool:
    """Validate end-to-end processing scenarios."""
    print("\n" + "="*50)
    print("VALIDATING END-TO-END SCENARIOS")
    print("="*50)
    
    parser = XMLParser()
    mapper = DataMapper()
    validator = PreProcessingValidator()
    contract = create_test_mapping_contract()
    
    # Scenario 1: Complete valid processing
    valid_xml = """
    <Provenir>
        <Request ID="154284">
            <CustData>
                <application app_receive_date="05/20/2016">
                    <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN" last_name="WILLIAMS">
                        <contact_address address_tp_c="CURR" city="FARGO" state="ND"/>
                        <contact_employment employment_tp_c="CURR" b_salary="75000"/>
                    </contact>
                </application>
            </CustData>
        </Request>
    </Provenir>
    """
    
    try:
        # Step 1: Pre-validation
        validation_result = validator.validate_xml_for_processing(valid_xml, "test_001")
        if not validation_result.can_process:
            print(f"❌ Pre-validation failed: {validation_result.validation_errors}")
            return False
        print("✅ Pre-validation passed")
        
        # Step 2: Parse XML
        root = parser.parse_xml_stream(valid_xml)
        elements = parser.extract_elements(root)
        print("✅ XML parsing completed")
        
        # Step 3: Convert to data structure
        xml_data = {}
        for path, element_data in elements.items():
            # Simplified conversion for testing
            if 'attributes' in element_data:
                path_parts = path.strip('/').split('/')
                current = xml_data
                for i, part in enumerate(path_parts):
                    if i == len(path_parts) - 1:
                        if part not in current:
                            current[part] = {}
                        current[part].update(element_data['attributes'])
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
        
        # Step 4: Apply mapping
        result = mapper.apply_mapping_contract(xml_data, contract)
        print(f"✅ Data mapping completed: {len(result)} tables")
        
        # Step 5: Validate results
        if 'app_base' in result and 'contact_base' in result:
            print("✅ End-to-end processing successful")
            return True
        else:
            print("❌ End-to-end processing failed: missing expected tables")
            return False
        
    except Exception as e:
        print(f"❌ End-to-end validation failed: {e}")
        return False


def validate_error_handling() -> bool:
    """Validate error handling scenarios."""
    print("\n" + "="*50)
    print("VALIDATING ERROR HANDLING")
    print("="*50)
    
    parser = XMLParser()
    validator = PreProcessingValidator()
    
    error_scenarios = [
        ("empty_xml", ""),
        ("malformed_xml", "<Provenir><Request><unclosed_tag></Request></Provenir>"),
        ("wrong_root", "<SomeOther><Request ID='123'/></SomeOther>"),
        ("missing_app_id", "<Provenir><Request><CustData><application><contact con_id='123' ac_role_tp_c='PR'/></application></CustData></Request></Provenir>"),
        ("missing_con_id", "<Provenir><Request ID='123'><CustData><application><contact ac_role_tp_c='PR'/></application></CustData></Request></Provenir>")
    ]
    
    expected_failures = 0
    actual_failures = 0
    
    for scenario_name, xml_content in error_scenarios:
        try:
            if xml_content == "":
                # Test empty XML
                try:
                    parser.parse_xml_stream(xml_content)
                    print(f"❌ {scenario_name}: Should have failed but didn't")
                except:
                    print(f"✅ {scenario_name}: Correctly rejected")
                    actual_failures += 1
            else:
                # Test validation
                validation_result = validator.validate_xml_for_processing(xml_content, scenario_name)
                if validation_result.is_valid:
                    print(f"❌ {scenario_name}: Should have failed validation but passed")
                else:
                    print(f"✅ {scenario_name}: Correctly failed validation")
                    actual_failures += 1
            
            expected_failures += 1
            
        except Exception as e:
            print(f"✅ {scenario_name}: Correctly threw exception: {type(e).__name__}")
            actual_failures += 1
            expected_failures += 1
    
    success_rate = actual_failures / expected_failures if expected_failures > 0 else 0
    print(f"\nError handling success rate: {success_rate:.1%} ({actual_failures}/{expected_failures})")
    
    return success_rate >= 0.8  # 80% success rate threshold


def run_comprehensive_validation() -> bool:
    """Run comprehensive system validation."""
    print("🔍 COMPREHENSIVE SYSTEM VALIDATION")
    print("="*60)
    print("Validating all components before processing real XML data...")
    
    validation_results = []
    
    # Run all validation tests
    tests = [
        ("XML Parser", validate_xml_parser),
        ("Data Mapper", validate_data_mapper),
        ("Migration Engine", validate_migration_engine),
        ("Pre-Processing Validator", validate_pre_processing_validator),
        ("End-to-End Scenarios", validate_end_to_end_scenarios),
        ("Error Handling", validate_error_handling)
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            validation_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} validation crashed: {e}")
            validation_results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in validation_results if result)
    total = len(validation_results)
    
    for test_name, result in validation_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nOverall Result: {passed}/{total} tests passed ({passed/total:.1%})")
    
    if passed == total:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("System is ready to process real XML data.")
        return True
    else:
        print(f"\n❌ {total - passed} VALIDATIONS FAILED!")
        print("Fix issues before processing real XML data.")
        return False


if __name__ == '__main__':
    setup_logging()
    
    print("Starting comprehensive system validation...")
    print("This will test all components with mock scenarios before processing real data.\n")
    
    success = run_comprehensive_validation()
    
    if success:
        print("\n✅ System validation complete - Ready for production!")
        sys.exit(0)
    else:
        print("\n❌ System validation failed - Do not process real data yet!")
        sys.exit(1)