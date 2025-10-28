#!/usr/bin/env python3
"""
Parallel Processing Performance Benchmark

This script benchmarks the parallel processing implementation to measure
the performance improvement from multiprocessing coordination.

Compares single-threaded vs parallel processing performance.
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from xml_extractor.processing.parallel_coordinator import ParallelCoordinator
from xml_extractor.monitoring.performance_monitor import PerformanceMonitor
from tests.integration.test_database_connection import DatabaseConnectionTester


class ParallelBenchmark:
    """
    Benchmark parallel processing performance vs single-threaded processing.
    """
    
    def __init__(self):
        """Initialize benchmark with database connection and components."""
        # Set up minimal logging for performance
        logging.basicConfig(
            level=logging.ERROR,  # ERROR level for maximum performance
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize database connection
        self.db_tester = DatabaseConnectionTester()
        success, message = self.db_tester.test_connection()
        if not success:
            raise RuntimeError(f"Database connection failed: {message}")
        
        self.connection_string = self.db_tester.build_connection_string()
        
        # Initialize mapping contract path
        self.mapping_contract_path = str(project_root / "config" / "mapping_contract.json")
        
        # Performance monitor
        self.performance_monitor = PerformanceMonitor()
    
    def run_benchmark(self, num_workers_list: List[int] = None) -> None:
        """
        Run parallel processing benchmark with different worker counts.
        
        Args:
            num_workers_list: List of worker counts to test (defaults to [1, 2, 4, 8])
        """
        if num_workers_list is None:
            num_workers_list = [1, 2, 4, 8]
        
        print("🚀 PARALLEL PROCESSING PERFORMANCE BENCHMARK")
        print("="*80)
        print("Goal: Measure parallel processing performance improvements")
        print("Scope: Test different worker counts with 50-record dataset for better parallel efficiency")
        print()
        
        # Extract test data
        xml_records = self._extract_test_data()
        if not xml_records:
            raise RuntimeError("No XML records found for benchmarking")
        
        print(f"Testing with {len(xml_records)} XML records")
        print()
        
        results = {}
        
        # Test each worker configuration
        for num_workers in num_workers_list:
            print(f"🔄 Testing with {num_workers} worker{'s' if num_workers > 1 else ''}...")
            
            try:
                # Create parallel coordinator
                coordinator = ParallelCoordinator(
                    connection_string=self.connection_string,
                    mapping_contract_path=self.mapping_contract_path,
                    num_workers=num_workers
                )
                
                # Run benchmark
                start_time = time.time()
                processing_result = coordinator.process_xml_batch(xml_records)
                end_time = time.time()
                
                # Store results
                results[num_workers] = {
                    'processing_result': processing_result,
                    'total_time': end_time - start_time,
                    'records_per_minute': processing_result.performance_metrics.get('records_per_minute', 0),
                    'success_rate': processing_result.success_rate,
                    'parallel_efficiency': processing_result.performance_metrics.get('parallel_efficiency', 0)
                }
                
                print(f"   ✅ Completed: {processing_result.records_successful}/{processing_result.records_processed} successful")
                print(f"   ⚡ Throughput: {results[num_workers]['records_per_minute']:.1f} records/minute")
                print(f"   🎯 Efficiency: {results[num_workers]['parallel_efficiency']*100:.1f}%")
                print()
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                results[num_workers] = {'error': str(e)}
                print()
        
        # Generate comparison report
        self._generate_comparison_report(results, len(xml_records))
    
    def _extract_test_data(self) -> List[Tuple[int, str]]:
        """Extract the same test data used in previous benchmarks."""
        xml_records = []
        
        try:
            from xml_extractor.database.migration_engine import MigrationEngine
            migration_engine = MigrationEngine(self.connection_string)
            
            with migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                
                # Use 50 records for better parallel efficiency testing
                cursor.execute("""
                    SELECT TOP 50 app_id, xml 
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
        
        except Exception as e:
            print(f"❌ Failed to extract test data: {e}")
            raise
        
        return xml_records
    
    def _generate_comparison_report(self, results: dict, num_records: int) -> None:
        """Generate comprehensive comparison report."""
        
        print("="*80)
        print("📊 PARALLEL PROCESSING COMPARISON REPORT")
        print("="*80)
        
        # Filter successful results
        successful_results = {k: v for k, v in results.items() if 'error' not in v}
        
        if not successful_results:
            print("❌ No successful benchmark results to compare")
            return
        
        # Performance comparison table
        print(f"{'Workers':<8} {'Time (s)':<10} {'Rec/Min':<10} {'Success %':<10} {'Efficiency %':<12} {'Speedup':<8}")
        print("-" * 70)
        
        baseline_time = None
        baseline_throughput = None
        
        for num_workers in sorted(successful_results.keys()):
            result = successful_results[num_workers]
            
            time_taken = result['total_time']
            throughput = result['records_per_minute']
            success_rate = result['success_rate']
            efficiency = result['parallel_efficiency'] * 100
            
            # Calculate speedup
            if baseline_time is None:
                baseline_time = time_taken
                baseline_throughput = throughput
                speedup = 1.0
            else:
                speedup = baseline_time / time_taken
            
            print(f"{num_workers:<8} {time_taken:<10.2f} {throughput:<10.1f} {success_rate:<10.1f} {efficiency:<12.1f} {speedup:<8.2f}x")
        
        # Find best configuration
        best_workers = max(successful_results.keys(), 
                          key=lambda k: successful_results[k]['records_per_minute'])
        best_result = successful_results[best_workers]
        
        print(f"\n🏆 Best Configuration: {best_workers} workers")
        print(f"   Throughput: {best_result['records_per_minute']:.1f} records/minute")
        print(f"   Speedup: {baseline_time / best_result['total_time']:.2f}x faster than single-threaded")
        
        # 11M record projection
        best_throughput = best_result['records_per_minute']
        minutes_for_11m = 11_000_000 / best_throughput
        hours_for_11m = minutes_for_11m / 60
        days_for_11m = hours_for_11m / 24
        
        print(f"\n🎯 11 Million Record Projection (Best Configuration):")
        print(f"   Time Required: {days_for_11m:.1f} days ({hours_for_11m:.1f} hours)")
        print(f"   Target Achievement: {'✅ MEETS TARGET' if best_throughput >= 1000 else '⚠️ BELOW TARGET'} (≥1000 rec/min)")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        if best_throughput >= 1000:
            print(f"   ✅ System ready for production with {best_workers} workers")
            print(f"   ✅ Parallel processing successfully achieves throughput targets")
        else:
            print(f"   🔧 Consider additional optimizations:")
            print(f"   🔧 - Database connection pooling")
            print(f"   🔧 - Batch size optimization")
            print(f"   🔧 - Further logging reduction")
        
        # Efficiency analysis
        if len(successful_results) > 1:
            print(f"\n📈 Efficiency Analysis:")
            for num_workers in sorted(successful_results.keys()):
                if num_workers == 1:
                    continue
                result = successful_results[num_workers]
                theoretical_speedup = num_workers
                actual_speedup = baseline_time / result['total_time']
                efficiency_percent = (actual_speedup / theoretical_speedup) * 100
                
                print(f"   {num_workers} workers: {efficiency_percent:.1f}% efficiency "
                      f"({actual_speedup:.2f}x actual vs {theoretical_speedup}x theoretical)")


def main():
    """Run the parallel processing benchmark."""
    
    try:
        benchmark = ParallelBenchmark()
        
        # Test with different worker counts
        # Start conservative to avoid overwhelming the system
        worker_counts = [1, 2, 4]  # Can extend to [1, 2, 4, 8] if system handles it well
        
        benchmark.run_benchmark(worker_counts)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)