#!/usr/bin/env python3
"""
Current State Performance Benchmark

This script benchmarks the current state of the XML extraction system
to evaluate viability and performance characteristics before running out of trial credits.

Goals:
- Gauge performance using test data from [app_xml] table
- Run as a batch to get metrics for the whole batch and individual applications
- Provide comprehensive performance analysis for decision making
- Use existing test framework for speed and reliability

Requirements addressed: 4.3, 4.5 (Performance and throughput targets)
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from xml_extractor.monitoring.performance_monitor import PerformanceMonitor
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine
from tests.integration.test_database_connection import DatabaseConnectionTester


class CurrentStateBenchmark:
    """
    Performance benchmark for current XML extraction system state.
    
    Uses existing production test infrastructure for reliability while
    focusing on performance metrics and throughput analysis.
    """
    
    def __init__(self):
        """Initialize benchmark with existing components."""
        # Set up logging for performance analysis - MINIMAL for performance testing
        logging.basicConfig(
            level=logging.ERROR,  # Only show errors to minimize logging overhead
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize performance monitor
        self.performance_monitor = PerformanceMonitor()
        
        # Initialize components using existing patterns from production test
        self.db_tester = DatabaseConnectionTester()
        
        # Test database connection
        success, message = self.db_tester.test_connection()
        if not success:
            raise RuntimeError(f"Database connection failed: {message}")
        
        self.connection_string = self.db_tester.build_connection_string()
        
        # Initialize processing components
        self.validator = PreProcessingValidator()
        self.parser = XMLParser()
        
        # Initialize DataMapper with mapping contract
        mapping_contract_path = project_root / "config" / "credit_card_mapping_contract.json"
        self.mapper = DataMapper(mapping_contract_path=str(mapping_contract_path))
        
        self.migration_engine = MigrationEngine(self.connection_string)
        
        # Benchmark results
        self.individual_results = []
        self.batch_summary = {}
    
    def run_benchmark(self) -> Dict[str, Any]:
        """
        Run the complete performance benchmark.
        
        Returns:
            Comprehensive benchmark results
        """
        print("🚀 CURRENT STATE PERFORMANCE BENCHMARK")
        print("="*80)
        print("Goal: Evaluate system viability and performance characteristics")
        print("Scope: Process 25 records from [app_xml] table for batch throughput analysis")
        print("Focus: Test performance impact of reduced logging (ERROR level only)")
        print()
        
        # Start overall performance monitoring
        self.performance_monitor.start_monitoring()
        
        try:
            # Step 1: Extract test data from app_xml table
            print("📊 Step 1: Extracting test data from app_xml table...")
            xml_records = self._extract_test_data()
            
            if not xml_records:
                raise RuntimeError("No XML records found for benchmarking")
            
            print(f"   Found {len(xml_records)} XML records for benchmarking")
            print()
            
            # Step 2: Process each XML with detailed performance tracking
            print("⚡ Step 2: Processing XML records with performance tracking...")
            self._process_xml_batch(xml_records)
            
            # Step 3: Stop monitoring and get results
            print("\n📈 Step 3: Analyzing performance results...")
            processing_result = self.performance_monitor.stop_monitoring()
            
            # Step 4: Generate comprehensive analysis
            benchmark_results = self._generate_benchmark_analysis(processing_result)
            
            # Step 5: Print detailed performance report
            self.performance_monitor.print_performance_report()
            
            # Step 6: Print benchmark conclusions
            self._print_benchmark_conclusions(benchmark_results)
            
            return benchmark_results
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            # Still try to get partial results
            try:
                processing_result = self.performance_monitor.stop_monitoring()
                return self._generate_benchmark_analysis(processing_result)
            except:
                return {'error': str(e), 'partial_results': self.individual_results}
    
    def _extract_test_data(self) -> List[Tuple[int, str]]:
        """Extract XML test data from app_xml table."""
        xml_records = []
        
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                
                # Extract a larger set for benchmarking (first 25 records for better throughput analysis)
                # This provides more meaningful performance analysis for batch processing
                cursor.execute("""
                    SELECT TOP 25 app_id, xml 
                    FROM app_xml 
                    WHERE xml IS NOT NULL 
                    AND DATALENGTH(xml) > 100
                    ORDER BY app_id
                """)
                
                rows = cursor.fetchall()
                
                for row in rows:
                    app_id = row[0]
                    xml_content = row[1]
                    
                    if xml_content and len(xml_content.strip()) > 0:
                        xml_records.append((app_id, xml_content))
                        
                        # Record XML size for analysis
                        xml_size_kb = len(xml_content) / 1024
                        self.performance_monitor.record_metric(f'xml_size_kb_app_{app_id}', xml_size_kb)
        
        except Exception as e:
            print(f"❌ Failed to extract test data: {e}")
            raise
        
        return xml_records
    
    def _process_xml_batch(self, xml_records: List[Tuple[int, str]]) -> None:
        """Process XML batch with detailed performance tracking."""
        
        for i, (app_id, xml_content) in enumerate(xml_records, 1):
            print(f"   Processing XML {i:2d}/{len(xml_records)} (app_id: {app_id})... ", end="", flush=True)
            
            # Track individual record performance
            record_start_time = time.time()
            success = False
            
            try:
                # Stage 1: Validation
                self.performance_monitor.start_stage('validation')
                validation_result = self.validator.validate_xml_for_processing(
                    xml_content, 
                    f"benchmark_{i}"
                )
                validation_time = self.performance_monitor.end_stage('validation')
                
                if not validation_result.is_valid or not validation_result.can_process:
                    print(f"❌ Validation failed")
                    continue
                
                # Clean up existing data
                self._cleanup_existing_data(validation_result.app_id)
                
                # Stage 2: Parsing
                self.performance_monitor.start_stage('parsing')
                root = self.parser.parse_xml_stream(xml_content)
                xml_data = self.parser.extract_elements(root)
                parsing_time = self.performance_monitor.end_stage('parsing')
                
                if root is None or not xml_data:
                    print(f"❌ Parsing failed")
                    continue
                
                # Stage 3: Mapping
                self.performance_monitor.start_stage('mapping')
                mapped_data = self.mapper.map_xml_to_database(
                    xml_data, 
                    validation_result.app_id, 
                    validation_result.valid_contacts, 
                    root
                )
                mapping_time = self.performance_monitor.end_stage('mapping')
                
                if not mapped_data:
                    print(f"❌ Mapping failed")
                    continue
                
                # Stage 4: Database Insertion
                self.performance_monitor.start_stage('insertion')
                insertion_results = self._insert_mapped_data(mapped_data)
                insertion_time = self.performance_monitor.end_stage('insertion')
                
                total_inserted = sum(insertion_results.values())
                if total_inserted == 0:
                    print(f"❌ Insertion failed")
                    continue
                
                success = True
                print(f"✅ Success ({total_inserted} records)")
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}...")
            
            finally:
                # Record individual performance metrics
                record_time = time.time() - record_start_time
                self.performance_monitor.record_processing_result(success)
                
                # Store individual result for detailed analysis
                individual_result = {
                    'app_id': app_id,
                    'sequence': i,
                    'success': success,
                    'processing_time': record_time,
                    'xml_size_kb': len(xml_content) / 1024,
                }
                
                if success:
                    individual_result.update({
                        'validation_time': validation_time,
                        'parsing_time': parsing_time,
                        'mapping_time': mapping_time,
                        'insertion_time': insertion_time,
                        'records_inserted': total_inserted if 'total_inserted' in locals() else 0,
                        'tables_populated': len(mapped_data) if 'mapped_data' in locals() else 0
                    })
                
                self.individual_results.append(individual_result)
    
    def _cleanup_existing_data(self, app_id: int) -> None:
        """Clean up existing data for app_id."""
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                # Use centralized configuration for schema-aware table name
                qualified_table_name = self.migration_engine.config_manager.get_qualified_table_name("app_base")
                cursor.execute(f"DELETE FROM {qualified_table_name} WHERE app_id = ?", (app_id,))
                conn.commit()
        except Exception:
            pass  # Ignore cleanup errors
    
    def _insert_mapped_data(self, mapped_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
        """Insert mapped data using existing patterns."""
        insertion_results = {}
        
        # Use proven table order from existing tests
        table_order = ["app_base", "app_operational_cc", "app_pricing_cc", 
                      "app_transactional_cc", "app_solicited_cc", 
                      "contact_base", "contact_address", "contact_employment"]
        
        for table_name in table_order:
            records = mapped_data.get(table_name, [])
            if records:
                enable_identity = table_name in ["app_base", "contact_base"]
                inserted_count = self.migration_engine.execute_bulk_insert(
                    records, 
                    table_name, 
                    enable_identity_insert=enable_identity
                )
                insertion_results[table_name] = inserted_count
        
        return insertion_results
    
    def _generate_benchmark_analysis(self, processing_result) -> Dict[str, Any]:
        """Generate comprehensive benchmark analysis."""
        
        # Calculate individual record statistics
        successful_records = [r for r in self.individual_results if r['success']]
        failed_records = [r for r in self.individual_results if not r['success']]
        
        individual_stats = {}
        if successful_records:
            processing_times = [r['processing_time'] for r in successful_records]
            xml_sizes = [r['xml_size_kb'] for r in successful_records]
            
            individual_stats = {
                'avg_processing_time': sum(processing_times) / len(processing_times),
                'min_processing_time': min(processing_times),
                'max_processing_time': max(processing_times),
                'avg_xml_size_kb': sum(xml_sizes) / len(xml_sizes),
                'min_xml_size_kb': min(xml_sizes),
                'max_xml_size_kb': max(xml_sizes),
                'avg_records_per_xml': sum(r.get('records_inserted', 0) for r in successful_records) / len(successful_records),
                'avg_tables_per_xml': sum(r.get('tables_populated', 0) for r in successful_records) / len(successful_records)
            }
        
        # Performance assessment against requirements
        performance_assessment = {
            'meets_throughput_target': processing_result.performance_metrics.get('records_per_minute', 0) >= 1000,
            'memory_efficient': processing_result.performance_metrics.get('resource_usage', {}).get('peak_memory_mb', 0) < 1000,
            'high_success_rate': processing_result.success_rate >= 90.0,
            'processing_stable': len(failed_records) == 0
        }
        
        return {
            'benchmark_timestamp': datetime.now().isoformat(),
            'processing_result': processing_result.__dict__,
            'individual_stats': individual_stats,
            'performance_assessment': performance_assessment,
            'successful_records': len(successful_records),
            'failed_records': len(failed_records),
            'individual_results': self.individual_results
        }
    
    def _print_benchmark_conclusions(self, results: Dict[str, Any]) -> None:
        """Print benchmark conclusions and recommendations."""
        
        print("\n" + "="*80)
        print("🎯 BENCHMARK CONCLUSIONS & RECOMMENDATIONS")
        print("="*80)
        
        assessment = results['performance_assessment']
        processing_result = results['processing_result']
        
        # Overall viability assessment
        viable_criteria = [
            assessment['meets_throughput_target'],
            assessment['memory_efficient'], 
            assessment['high_success_rate']
        ]
        
        overall_viable = sum(viable_criteria) >= 2  # At least 2 out of 3 criteria
        
        print(f"📊 System Viability: {'✅ VIABLE' if overall_viable else '⚠️ NEEDS WORK'}")
        print()
        
        # Detailed assessment
        print(f"🔍 Detailed Assessment:")
        throughput = processing_result.get('performance_metrics', {}).get('records_per_minute', 0)
        print(f"   Throughput Target (≥1000 rec/min): {throughput:.1f} rec/min {'✅' if assessment['meets_throughput_target'] else '❌'}")
        
        memory_mb = processing_result.get('performance_metrics', {}).get('resource_usage', {}).get('peak_memory_mb', 0)
        print(f"   Memory Efficiency (<1GB): {memory_mb:.1f} MB {'✅' if assessment['memory_efficient'] else '❌'}")
        
        success_rate = processing_result.get('success_rate', 0)
        print(f"   Success Rate (≥90%): {success_rate:.1f}% {'✅' if assessment['high_success_rate'] else '❌'}")
        
        print(f"   Processing Stability: {'✅' if assessment['processing_stable'] else '❌'}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if overall_viable:
            print(f"   ✅ System is viable for production deployment")
            print(f"   ✅ Current performance meets basic requirements")
            print(f"   🚀 Consider implementing parallel processing (task 5.2) for scale")
        else:
            print(f"   ⚠️ System needs optimization before production")
            
            if not assessment['meets_throughput_target']:
                print(f"   🔧 Implement parallel processing to improve throughput")
                print(f"   🔧 Optimize database bulk insert operations")
            
            if not assessment['memory_efficient']:
                print(f"   🔧 Implement streaming XML processing")
                print(f"   🔧 Add memory management and garbage collection")
            
            if not assessment['high_success_rate']:
                print(f"   🔧 Review and fix data mapping issues")
                print(f"   🔧 Improve error handling and validation")
        
        # Next steps
        print(f"\n🎯 Next Steps:")
        if overall_viable:
            print(f"   1. Proceed with remaining tasks (5.2 parallel processing)")
            print(f"   2. Implement monitoring and logging (task 6)")
            print(f"   3. Create production deployment plan")
        else:
            print(f"   1. Address performance bottlenecks identified above")
            print(f"   2. Re-run benchmark to validate improvements")
            print(f"   3. Consider alternative optimization strategies")
        
        print(f"\n💰 Trial Credits Status:")
        print(f"   Current benchmark used minimal credits (focused test set)")
        print(f"   Recommend {'proceeding with development' if overall_viable else 'optimization before further testing'}")


def main():
    """Run the current state performance benchmark."""
    
    try:
        # Create and run benchmark
        benchmark = CurrentStateBenchmark()
        results = benchmark.run_benchmark()
        
        # Return success based on viability
        viable = results.get('performance_assessment', {}).get('meets_throughput_target', False)
        return 0 if viable else 1
        
    except Exception as e:
        print(f"\n❌ Benchmark failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)