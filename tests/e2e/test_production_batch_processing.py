#!/usr/bin/env python3
"""
Production XML Batch Processing Test

This test extracts real XML files from the app_xml table and processes them
through the complete pipeline to discover problems and refine the program.

The goal is to prove the system works on production data by:
1. Extracting XML from app_xml table (production-like data)
2. Processing each XML through: validate → parse → map → insert
3. Inspecting outcomes and identifying issues
4. Iterating improvements until confident batch processing

This test acts as a pure orchestrator - it does NOT implement new functionality,
only exercises existing components to discover issues.
"""

import unittest
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine
# Import DatabaseConnectionTester from integration tests
from tests.integration.test_database_connection import DatabaseConnectionTester


class TestProductionXMLBatch(unittest.TestCase):
    """Production XML batch processing test for system hardening."""
    
    @classmethod
    def setUpClass(cls):
        """Set up database connection and components using existing configuration."""
        # Use existing DatabaseConnectionTester to get proper connection
        cls.db_tester = DatabaseConnectionTester()
        
        # Test connection and get connection string
        success, message = cls.db_tester.test_connection()
        if not success:
            raise RuntimeError(f"Database connection failed: {message}")
        
        cls.connection_string = cls.db_tester.build_connection_string()
        
        # Initialize components using existing patterns
        cls.validator = PreProcessingValidator()
        cls.parser = XMLParser()
        
        # Initialize DataMapper with mapping contract (existing pattern)
        mapping_contract_path = project_root / "config" / "credit_card_mapping_contract.json"
        cls.mapper = DataMapper(mapping_contract_path=str(mapping_contract_path))
        
        cls.migration_engine = MigrationEngine(cls.connection_string)
        
        # Test results tracking
        cls.batch_results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'validation_failures': 0,
            'parsing_failures': 0,
            'mapping_failures': 0,
            'insertion_failures': 0,
            'detailed_results': [],
            'data_quality_issues': {
                'incomplete_applications': 0,
                'missing_contacts': 0,
                'missing_primary_contacts': 0,
                'skipped_contact_tables': 0
            }
        }
    
    def setUp(self):
        """Set up for each test."""
        # Configure logging for detailed output
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def test_production_xml_batch_processing(self):
        """
        Main test: Extract and process production XML files from app_xml table.
        
        This is the ultimate litmus test to prove the complete plumbing works.
        """
        print("\n" + "="*100)
        print("🚀 PRODUCTION XML BATCH PROCESSING TEST - COMPLETE VALIDATION")
        print("="*100)
        print("Goal: Complete validation of all production data with latest improvements")
        print("System Status: Testing chained mapping types and phone truncation fixes")
        print("Processing: Apps 17-24 for performance benchmarking")
        print()
        
        # Step 1: Extract XML files from app_xml table
        xml_records = self.extract_production_xml_files()
        
        if not xml_records:
            self.skipTest("No XML records found in app_xml table")
        
        print(f"Processing {len(xml_records)} XML records...")
        print()
        
        # Step 2: Process each XML through the complete pipeline
        for i, (app_id, xml_content) in enumerate(xml_records, 1):
            print(f"App {i:2d} (ID: {app_id:6d}): ", end="", flush=True)
            result = self.process_single_xml(app_id, xml_content, i)
            self.batch_results['detailed_results'].append(result)
            self.batch_results['total_processed'] += 1
            
            if result['success']:
                self.batch_results['successful'] += 1
                print(f"✅ SUCCESS")
            else:
                self.batch_results['failed'] += 1
                print(f"❌ FAILED ({result['error_stage']})")
                if 'error' in result:
                    print(f"    Error: {result['error'][:100]}...")  # Truncate long errors
                
                # Track failure types
                if result['error_stage'] == 'validation':
                    self.batch_results['validation_failures'] += 1
                elif result['error_stage'] == 'parsing':
                    self.batch_results['parsing_failures'] += 1
                elif result['error_stage'] == 'mapping':
                    self.batch_results['mapping_failures'] += 1
                elif result['error_stage'] == 'insertion':
                    self.batch_results['insertion_failures'] += 1
        
        # Step 3: Analyze results and generate report
        print(f"\n📊 Step 3: Analyzing batch processing results...")
        self.analyze_batch_results()
        
        # Step 4: Validate overall success criteria
        self.validate_batch_success_criteria()
        
        print(f"\n🎉 PRODUCTION XML BATCH PROCESSING COMPLETED!")
    
    def extract_production_xml_files(self) -> List[Tuple[int, str]]:
        """
        Extract XML files from app_xml table for testing.
        
        Uses existing database connection patterns from migration engine.
        
        Returns:
            List of tuples (app_id, xml_content)
        """
        xml_records = []
        
        try:
            # Use existing database connection pattern from migration engine
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                
                # COMPLETE VALIDATION: Process ALL XML records (1-16)
                # Testing latest improvements: chained mapping types + phone truncation fixes
                cursor.execute("""
                    SELECT app_id, xml 
                    FROM app_xml 
                    WHERE xml IS NOT NULL 
                    AND DATALENGTH(xml) > 100
                    AND app_id BETWEEN 1 AND 24  -- Complete benchmark 1-24
                    ORDER BY app_id
                """)
                
                rows = cursor.fetchall()
                
                for row in rows:
                    app_id = row[0]
                    xml_content = row[1]
                    
                    if xml_content and len(xml_content.strip()) > 0:
                        xml_records.append((app_id, xml_content))
                

                
        except Exception as e:
            print(f"❌ Failed to extract XML from database: {e}")
            raise
        
        return xml_records
    
    def process_single_xml(self, app_id: int, xml_content: str, sequence: int) -> Dict[str, Any]:
        """
        Process a single XML through the complete pipeline.
        
        Args:
            app_id: Application ID from database
            xml_content: Raw XML content
            sequence: Sequence number for tracking
            
        Returns:
            Dictionary with processing results
        """
        result = {
            'app_id': app_id,
            'sequence': sequence,
            'success': False,
            'error_stage': None,
            'error': None,
            'validation_result': None,
            'mapped_tables': None,
            'inserted_records': {},
            'processing_time': None
        }
        
        start_time = datetime.now()
        
        try:
            # Stage 1: Validation (to get the actual app_id from XML)
            validation_result = self.validator.validate_xml_for_processing(
                xml_content, 
                f"production_batch_{sequence}"
            )
            
            result['validation_result'] = {
                'is_valid': validation_result.is_valid,
                'can_process': validation_result.can_process,
                'extracted_app_id': validation_result.app_id,
                'valid_contacts': len(validation_result.valid_contacts) if validation_result.valid_contacts else 0,
                'validation_errors': validation_result.validation_errors,
                'validation_warnings': validation_result.validation_warnings
            }
            
            # Track data quality issues
            self._track_data_quality_issues(validation_result)
            
            if not validation_result.is_valid or not validation_result.can_process:
                result['error_stage'] = 'validation'
                result['error'] = f"Validation failed: {validation_result.validation_errors}"
                return result
            
            # Clean up any existing test data for the actual app_id from XML
            try:
                self.cleanup_existing_data(validation_result.app_id)
            except Exception as cleanup_error:
                print(f"    ⚠️ Cleanup failed for app_id {validation_result.app_id}: {cleanup_error}")
            
            # Stage 2: Parsing
            root = self.parser.parse_xml_stream(xml_content)
            xml_data = self.parser.extract_elements(root)
            
            if root is None or not xml_data:
                result['error_stage'] = 'parsing'
                result['error'] = "Failed to parse XML or extract elements"
                return result
            
            # Stage 3: Mapping
            mapped_data = self.mapper.map_xml_to_database(
                xml_data, 
                validation_result.app_id, 
                validation_result.valid_contacts, 
                root
            )
            
            if not mapped_data:
                result['error_stage'] = 'mapping'
                result['error'] = "No data mapped from XML"
                return result
            
            result['mapped_tables'] = list(mapped_data.keys())
            
            # Stage 4: Database Insertion
            try:
                insertion_results = self.insert_mapped_data(mapped_data)
                result['inserted_records'] = insertion_results
                
                # Check if all insertions were successful
                total_inserted = sum(insertion_results.values())
                if total_inserted == 0:
                    result['error_stage'] = 'insertion'
                    result['error'] = "No records were inserted into database"
                    return result
                
                # Success!
                result['success'] = True
                
            except Exception as insertion_error:
                result['error_stage'] = 'insertion'
                result['error'] = str(insertion_error)
                result['traceback'] = traceback.format_exc()
                return result
            
        except Exception as e:
            # Determine error stage based on what we've completed so far
            if result['validation_result'] is None:
                result['error_stage'] = 'validation'
            elif 'mapped_tables' not in result or result['mapped_tables'] is None:
                result['error_stage'] = 'mapping'
            else:
                result['error_stage'] = 'unknown'
            
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
        
        finally:
            end_time = datetime.now()
            result['processing_time'] = (end_time - start_time).total_seconds()
        
        return result
    
    def cleanup_existing_data(self, app_id: int):
        """Clean up any existing data for the app_id to avoid conflicts."""
        # Use existing database connection pattern from migration engine
        with self.migration_engine.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if record exists first
            cursor.execute("SELECT COUNT(*) FROM app_base WHERE app_id = ?", (app_id,))
            count_before = cursor.fetchone()[0]
            
            if count_before > 0:
                # Delete from app_base (cascade will handle all related tables)
                cursor.execute("DELETE FROM app_base WHERE app_id = ?", (app_id,))
                rows_deleted = cursor.rowcount
                
                # Commit the transaction to ensure cleanup is applied
                conn.commit()
                
                # Cleanup completed - will be reported in main output
                pass
            else:
                # No cleanup needed - will be reported in main output  
                pass
    
    def insert_mapped_data(self, mapped_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """
        Insert mapped data using existing insertion logic from end-to-end test.
        
        This follows the exact same pattern as test_end_to_end_integration.py
        to ensure consistency and avoid reimplementing functionality.
        
        Returns:
            Dictionary with table names and record counts inserted
        """
        insertion_results = {}
        
        # Use the same table order as existing end-to-end test
        # This is the proven working order from test_end_to_end_integration.py
        table_order = ["app_base", "app_operational_cc", "app_pricing_cc", "app_transactional_cc", "app_solicited_cc", "contact_base", "contact_address", "contact_employment"]
        
        for table_name in table_order:
            records = mapped_data.get(table_name, [])
            if records:
                try:
                    # Use same identity insert logic as existing test
                    enable_identity = table_name in ["app_base", "contact_base"]
                    
                    inserted_count = self.migration_engine.execute_bulk_insert(
                        records, 
                        table_name, 
                        enable_identity_insert=enable_identity
                    )
                    
                    insertion_results[table_name] = inserted_count
                    
                except Exception as e:
                    insertion_results[table_name] = 0
                    raise  # Re-raise to mark this XML as failed
        
        return insertion_results
    
    def _track_data_quality_issues(self, validation_result):
        """Track data quality issues from validation results."""
        warnings = validation_result.validation_warnings
        
        for warning in warnings:
            if "No valid contacts found" in warning:
                self.batch_results['data_quality_issues']['missing_contacts'] += 1
                self.batch_results['data_quality_issues']['incomplete_applications'] += 1
            elif "No primary contact" in warning:
                self.batch_results['data_quality_issues']['missing_primary_contacts'] += 1
            elif "Skipping contact" in warning:
                # Individual contact issues don't count as incomplete applications
                pass
        
        # Track if this application had no valid contacts (will skip contact tables)
        if len(validation_result.valid_contacts) == 0:
            self.batch_results['data_quality_issues']['skipped_contact_tables'] += 3  # contact_base, contact_address, contact_employment

    def analyze_batch_results(self):
        """Analyze and report on batch processing results."""
        results = self.batch_results
        
        print("\n" + "="*80)
        print("📊 BATCH PROCESSING ANALYSIS")
        print("="*80)
        
        # Overall statistics
        print(f"📈 Overall Statistics:")
        print(f"   Total XMLs Processed: {results['total_processed']}")
        print(f"   Successful: {results['successful']} ({(results['successful']/results['total_processed']*100):.1f}%)")
        print(f"   Failed: {results['failed']} ({(results['failed']/results['total_processed']*100):.1f}%)")
        
        # Failure breakdown
        if results['failed'] > 0:
            print(f"\n❌ Failure Breakdown:")
            print(f"   Validation Failures: {results['validation_failures']}")
            print(f"   Parsing Failures: {results['parsing_failures']}")
            print(f"   Mapping Failures: {results['mapping_failures']}")
            print(f"   Insertion Failures: {results['insertion_failures']}")
        
        # Detailed failure analysis
        failed_results = [r for r in results['detailed_results'] if not r['success']]
        if failed_results:
            print(f"\n🔍 Detailed Failure Analysis:")
            for result in failed_results[:5]:  # Show first 5 failures
                print(f"   App ID {result['app_id']}: {result['error_stage']} - {result['error']}")
        
        # Success patterns
        successful_results = [r for r in results['detailed_results'] if r['success']]
        if successful_results:
            print(f"\n✅ Success Patterns:")
            
            # Average processing time
            avg_time = sum(r['processing_time'] for r in successful_results) / len(successful_results)
            print(f"   Average Processing Time: {avg_time:.2f} seconds")
            
            # Table mapping statistics
            all_tables = set()
            for result in successful_results:
                if result['mapped_tables']:
                    all_tables.update(result['mapped_tables'])
            
            print(f"   Tables Successfully Mapped: {', '.join(sorted(all_tables))}")
            
            # Record insertion statistics
            total_records_inserted = {}
            for result in successful_results:
                for table, count in result['inserted_records'].items():
                    total_records_inserted[table] = total_records_inserted.get(table, 0) + count
            
            print(f"   Total Records Inserted:")
            for table, count in sorted(total_records_inserted.items()):
                print(f"     {table}: {count} records")
        
        # Data quality analysis
        dq_issues = results['data_quality_issues']
        if any(dq_issues.values()):
            print(f"\n⚠️ Data Quality Issues:")
            if dq_issues['incomplete_applications'] > 0:
                print(f"   Incomplete Applications: {dq_issues['incomplete_applications']} ({(dq_issues['incomplete_applications']/results['total_processed']*100):.1f}%)")
            if dq_issues['missing_contacts'] > 0:
                print(f"   Missing Contacts: {dq_issues['missing_contacts']} applications processed with graceful degradation")
            if dq_issues['missing_primary_contacts'] > 0:
                print(f"   Missing Primary Contacts: {dq_issues['missing_primary_contacts']} applications missing PR contact")
            if dq_issues['skipped_contact_tables'] > 0:
                print(f"   Skipped Contact Tables: {dq_issues['skipped_contact_tables']} table insertions skipped due to missing contacts")
        else:
            print(f"\n✅ Data Quality: No data quality issues detected - all applications had complete contact information")
    
    def validate_batch_success_criteria(self):
        """Validate that batch processing meets success criteria."""
        results = self.batch_results
        
        print(f"\n🎯 Validating Success Criteria:")
        
        # Criterion 1: At least 90% success rate
        success_rate = (results['successful'] / results['total_processed']) * 100
        criterion_1 = success_rate >= 90.0
        print(f"   ✅ Success Rate ≥ 90%: {success_rate:.1f}% {'✓' if criterion_1 else '✗'}")
        
        # Criterion 2: No parsing failures (indicates robust XML handling)
        criterion_2 = results['parsing_failures'] == 0
        print(f"   ✅ Zero Parsing Failures: {results['parsing_failures']} {'✓' if criterion_2 else '✗'}")
        
        # Criterion 3: Minimal insertion failures (indicates good data mapping)
        insertion_failure_rate = (results['insertion_failures'] / results['total_processed']) * 100
        criterion_3 = insertion_failure_rate <= 10.0
        print(f"   ✅ Insertion Failure Rate ≤ 10%: {insertion_failure_rate:.1f}% {'✓' if criterion_3 else '✗'}")
        
        # Overall assessment
        all_criteria_met = criterion_1 and criterion_2 and criterion_3
        
        print(f"\n🏆 Overall Assessment: {'PASS' if all_criteria_met else 'NEEDS IMPROVEMENT'}")
        
        if not all_criteria_met:
            print(f"\n🔧 Recommended Actions:")
            if not criterion_1:
                print(f"   - Investigate validation and mapping failures")
                print(f"   - Review mapping contract for edge cases")
            if not criterion_2:
                print(f"   - Improve XML parsing robustness")
                print(f"   - Handle malformed XML gracefully")
            if not criterion_3:
                print(f"   - Review database constraints and data types")
                print(f"   - Improve data transformation logic")
        
        # Assert for test framework - fail if any criteria not met
        self.assertTrue(all_criteria_met, 
                       f"Production batch processing failed criteria: Success Rate: {success_rate:.1f}% (need ≥90%), "
                       f"Parsing Failures: {results['parsing_failures']} (need 0), "
                       f"Insertion Failure Rate: {insertion_failure_rate:.1f}% (need ≤10%)")


def run_production_batch_test():
    """Run the production XML batch processing test."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProductionXMLBatch)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*100)
    print("🎯 PRODUCTION XML BATCH TEST SUMMARY")
    print("="*100)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}")
            print(f"    {traceback}")
    
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 Production XML batch test completed successfully!")
        print("The system is ready for confident batch processing of production data.")
    else:
        print("\n⚠️ Production XML batch test revealed issues!")
        print("Review and fix the identified problems before production deployment.")
    
    return success


if __name__ == '__main__':
    success = run_production_batch_test()
    sys.exit(0 if success else 1)