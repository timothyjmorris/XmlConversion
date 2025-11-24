#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase II Baseline Establishment - Production Processor Performance

This script establishes the performance baseline for Phase II optimizations.

It runs production_processor.py multiple times with a clean database between runs,
measuring the actual production throughput that we'll use as our baseline.

Key features:
- Clears app_base table between runs (cascade deletes via FK)
- Measures actual production throughput
- Records median + standard deviation
- No interference from accumulated data
"""

import sys
import time
import logging
import subprocess
from datetime import datetime
import statistics
from pathlib import Path
from typing import List, Tuple
import io

# Set UTF-8 encoding for stdout/stderr (fixes PowerShell emoji issues)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path (establish_baseline.py is in env_prep/, parent is project root)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from xml_extractor.database.migration_engine import MigrationEngine
from tests.integration.test_database_connection import DatabaseConnectionTester


class BaselineEstablisher:
    """Establishes Phase II optimization baseline."""
    
    def __init__(self):
        """Initialize with database connection."""
        # Set up minimal logging
        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize database connection
        self.db_tester = DatabaseConnectionTester()
        success, message = self.db_tester.test_connection()
        if not success:
            raise RuntimeError(f"Database connection failed: {message}")
        
        self.connection_string = self.db_tester.build_connection_string()
        self.migration_engine = MigrationEngine(self.connection_string)
    
    def clear_app_base(self) -> None:
        """
        Clear app_base table and processing_log to start fresh.
        
        Note: Cascade delete will automatically delete from dependent tables:
        - app_operational_cc
        - app_pricing_cc
        - app_transactional_cc
        - app_solicited_cc
        - contact_base (and its children contact_address, contact_employment)
        
        Also clears processing_log so XMLs can be re-processed.
        """
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clear processing log first (no FK constraints)
                cursor.execute("DELETE FROM processing_log")
                
                # Truncate or delete based on production requirements
                # Using DELETE to respect constraints; TRUNCATE would fail without turning off FK
                cursor.execute("DELETE FROM app_base")
                
                # Get count to verify
                cursor.execute("SELECT COUNT(*) FROM app_base")
                count = cursor.fetchone()[0]
                
                conn.commit()
                
                if count == 0:
                    print("Database cleared (app_base, dependent tables, and processing_log)")
                    return True
                else:
                    print(f"Database may not be fully cleared ({count} records remain)")
                    return False
                    
        except Exception as e:
            print(f"Failed to clear database: {e}")
            return False
    
    def count_app_xml_records(self) -> int:
        """Count available app_xml records for processing."""
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM app_xml WHERE app_XML IS NOT NULL")
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            print(f"Failed to count app_xml records: {e}")
            return 0
    
    def run_baseline_benchmark(self, num_runs: int = 10) -> dict:
        """
        Run production_processor.py multiple times to establish baseline.
        
        Args:
            num_runs: Number of runs to perform (default 10)
            
        Returns:
            Dictionary with baseline metrics
        """
        print("\n" + "="*80)
        print("PHASE II BASELINE ESTABLISHMENT")
        print("="*80)
        
        # Check available data
        app_xml_count = self.count_app_xml_records()
        print(f"\nAvailable app_xml records: {app_xml_count}")
        
        if app_xml_count == 0:
            print("No app_xml records found for benchmarking!")
            print("   Please load test data first.")
            return {}
        
        print(f"Running {num_runs} production_processor.py iterations...")
        print(f"   - Each run will clear app_base and re-process data")
        print(f"   - Measuring actual production throughput")
        print()
        
        # Run multiple times
        throughputs = []
        times_taken = []
        
        for run_num in range(1, num_runs + 1):
            print(f"Run {run_num}/{num_runs}...", end=" ", flush=True)
            
            # Clear database before each run
            if not self.clear_app_base():
                print(f"Failed to clear database, aborting run {run_num}")
                continue
            
            # Run production_processor.py and capture metrics
            try:
                result = self._run_production_processor()
                
                if result:
                    throughput = result['throughput']
                    time_taken = result['time_seconds']
                    
                    throughputs.append(throughput)
                    times_taken.append(time_taken)
                    
                    print(f"{throughput:.1f} rec/min ({time_taken:.1f}s)")
                else:
                    print("Failed to parse results")
                    
            except Exception as e:
                print(f"Error: {e}")
                continue
        
        # Calculate statistics
        if not throughputs:
            print("\nNo successful runs completed!")
            return {}
        
        median_throughput = statistics.median(throughputs)
        mean_throughput = statistics.mean(throughputs)
        stdev_throughput = statistics.stdev(throughputs) if len(throughputs) > 1 else 0
        min_throughput = min(throughputs)
        max_throughput = max(throughputs)
        
        print("\n" + "="*80)
        print("BASELINE RESULTS")
        print("="*80)
        print(f"\nThroughput Statistics (records/minute):")
        print(f"  Median:     {median_throughput:.1f}")
        print(f"  Mean:       {mean_throughput:.1f}")
        print(f"  Std Dev:    {stdev_throughput:.1f}")
        print(f"  Min:        {min_throughput:.1f}")
        print(f"  Max:        {max_throughput:.1f}")
        print(f"  Range:      {min_throughput:.1f} - {max_throughput:.1f}")
        
        # Time statistics
        median_time = statistics.median(times_taken)
        stdev_time = statistics.stdev(times_taken) if len(times_taken) > 1 else 0
        
        print(f"\nTime Statistics (seconds):")
        print(f"  Median:     {median_time:.1f}s")
        print(f"  Std Dev:    {stdev_time:.1f}s")
        
        # Confidence assessment
        confidence = self._assess_confidence(stdev_throughput, mean_throughput)
        
        print(f"\nBaseline Measurement Confidence: {confidence}")
        if confidence == "High":
            print(f"   Measurements are stable (std dev < 5%)")
        elif confidence == "Medium":
            print(f"   Measurements show moderate variance (5-10%)")
        else:
            print(f"   Measurements show high variance (> 10%)")
        
        # Recommendations
        print(f"\nRecommendations for Phase II:")
        if median_throughput < 300:
            print(f"   • Current baseline is LOW ({median_throughput:.1f} rec/min)")
            print(f"   • Significant optimization opportunities exist")
            print(f"   • Target: 400-600 rec/min after Phase II optimizations")
        elif median_throughput < 400:
            print(f"   • Current baseline is MODERATE ({median_throughput:.1f} rec/min)")
            print(f"   • Room for 20-50% improvement with Phase II")
            print(f"   • Target: 450-600 rec/min")
        else:
            print(f"   • Current baseline is GOOD ({median_throughput:.1f} rec/min)")
            print(f"   • Room for 10-30% improvement with Phase II")
            print(f"   • Target: {int(median_throughput * 1.3)}-{int(median_throughput * 1.6)} rec/min")
        
        # Return metrics
        return {
            'median_rec_per_min': median_throughput,
            'mean_rec_per_min': mean_throughput,
            'stdev_rec_per_min': stdev_throughput,
            'min_rec_per_min': min_throughput,
            'max_rec_per_min': max_throughput,
            'median_time_seconds': median_time,
            'stdev_time_seconds': stdev_time,
            'num_runs': len(throughputs),
            'confidence': confidence,
            'throughputs': throughputs,
            'times': times_taken
        }
    
    def _run_production_processor(self) -> dict:
        """
        Run production_processor.py and extract metrics.
        
        Returns:
            Dictionary with 'throughput' and 'time_seconds', or None if failed
        """
        print(f"     [DEBUG] Starting _run_production_processor", flush=True)
        try:
            # Run production_processor.py
            # Adjust script name/path as needed for your setup
            script_path = project_root / "production_processor.py"
            
            # Basic invocation - adjust parameters as needed
            cmd = [
                sys.executable,
                str(script_path),
                "--server", "localhost\\SQLEXPRESS",
                "--database", "XmlConversionDB",
                "--workers", "4",
                "--batch-size", "1000",
                "--log-level", "INFO"
                # Note: Connection pooling disabled by default for SQLExpress
                # To enable: add "--enable-pooling"
            ]
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            elapsed_time = time.time() - start_time
            
            # Parse output for metrics
            # Looking for pattern like "Processed X records in Y seconds"
            output = result.stdout + result.stderr
            print(f"     [DEBUG] Output captured - length: {len(output)} chars, return code: {result.returncode}", flush=True)
            
            # Try to extract throughput from output
            # Adjust parsing based on actual production_processor.py output format
            throughput = self._parse_throughput_from_output(output, elapsed_time)
            
            if throughput is None:
                print(f"  Could not parse metrics from output")
                print(f"\n--- DEBUG: Raw Output (last 500 chars) ---")
                print(output[-500:] if len(output) > 500 else output)
                print(f"--- END DEBUG ---\n")
                # Save full output to file for inspection
                with open("baseline_output_debug.txt", "a") as f:
                    f.write(f"\n{'='*80}\nRun at {datetime.now()}\n{'='*80}\n")
                    f.write(output)
                    f.write(f"\n{'='*80}\n")
                return None
            
            return {
                'throughput': throughput,
                'time_seconds': elapsed_time,
                'output': output
            }
            
        except subprocess.TimeoutExpired:
            print("Timeout (5 min limit exceeded)")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def _parse_throughput_from_output(self, output: str, elapsed_time: float) -> float:
        """
        Parse throughput from production_processor.py output.
        
        Looks for patterns like:
        - "Overall Rate: 325.4 applications/minute"
        - Or calculates from record count if time is given
        """
        # Try to find explicit throughput in output
        import re
        
        # Pattern 1: Explicit applications/minute mention (primary pattern from production_processor.py)
        match = re.search(r'Overall Rate:\s*(\d+\.?\d*)\s*applications/minute', output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        # Pattern 2: Fallback - rec/min mention
        match = re.search(r'(\d+\.?\d*)\s*rec/min', output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        # Pattern 3: Records and time mentioned
        records_match = re.search(r'Processed\s+(\d+)\s+records', output, re.IGNORECASE)
        if records_match:
            records = int(records_match.group(1))
            if records > 0:
                return (records / elapsed_time * 60)
        
        # Fallback: Try to find any numeric summary
        # This is a guess - adjust based on actual output
        import re
        numbers = re.findall(r'\d+', output)
        if numbers and len(numbers) >= 2:
            # Assume: first number is records processed, use elapsed_time
            try:
                records = int(numbers[0])
                if 50 < records < 500:  # Sanity check
                    return (records / elapsed_time * 60)
            except:
                pass
        
        return None
    
    def _assess_confidence(self, stdev: float, mean: float) -> str:
        """Assess measurement confidence based on variance."""
        if mean == 0:
            return "Low"
        
        cv = (stdev / mean) * 100  # Coefficient of variation
        
        if cv < 5:
            return "High"
        elif cv < 10:
            return "Medium"
        else:
            return "Low"


def main():
    """Run the baseline establishment."""
    try:
        establisher = BaselineEstablisher()
        
        # Run baseline benchmark
        baseline_metrics = establisher.run_baseline_benchmark(num_runs=10)
        
        if baseline_metrics:
            # Save metrics for later comparison
            import json
            metrics_file = project_root / "baseline_metrics.json"
            with open(metrics_file, 'w') as f:
                # Convert non-serializable values
                save_metrics = {k: v for k, v in baseline_metrics.items() 
                               if k not in ['throughputs', 'times']}
                json.dump(save_metrics, f, indent=2)
            
            print(f"\nMetrics saved to: {metrics_file}")
            print("\nBaseline establishment complete!")
            print("   Ready to begin Phase II.1 (Batch Size Optimization)")
            return 0
        else:
            print("\nBaseline establishment failed!")
            return 1
            
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
