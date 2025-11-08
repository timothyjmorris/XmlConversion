"""
Performance Test Runner for DataMapper Regression Testing

This script provides a convenient way to run performance tests and track
results over time. Integrates with CI/CD pipelines and provides detailed
reporting for refactoring validation.
"""

import pytest
import sys
import json
import time
import os
import argparse

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add project root to Python path for imports
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class PerformanceTestRunner:
    """Manages performance test execution and result tracking."""
    
    def __init__(self, results_dir: str = "performance_results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        self.baseline_file = self.results_dir / "performance_baseline.json"
        self.history_file = self.results_dir / "performance_history.json"
    
    def run_performance_tests(self, test_file: str = None, save_baseline: bool = False) -> Dict[str, Any]:
        """
        Run performance tests and collect results.
        
        Args:
            test_file: Specific test file to run (default: all performance tests)
            save_baseline: Whether to save results as new baseline
            
        Returns:
            Dictionary with test results and performance metrics
        """
        print("🚀 Starting Performance Test Suite")
        print("=" * 60)
        
        # Determine test files to run
        if test_file:
            test_files = [test_file]
        else:
            test_files = [
                "tests/performance/test_datamapper_performance_regression.py"
            ]
        
        # Prepare pytest arguments
        pytest_args = [
            "-v",  # Verbose output
            "-s",  # Don't capture stdout (show print statements)
            "--tb=short",  # Short traceback format
        ] + test_files
        
        # Capture start time
        start_time = time.time()
        
        # Run tests and capture exit code
        print(f"Running: pytest {' '.join(pytest_args)}")
        exit_code = pytest.main(pytest_args)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Collect results
        results = {
            "timestamp": datetime.now().isoformat(),
            "execution_time_seconds": execution_time,
            "exit_code": exit_code,
            "success": exit_code == 0,
            "test_files": test_files
        }
        
        # Save results to history
        self._save_to_history(results)
        
        # Save as baseline if requested
        if save_baseline and results["success"]:
            self._save_baseline(results)
            print(f"✅ Baseline saved to {self.baseline_file}")
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def compare_with_baseline(self) -> Dict[str, Any]:
        """
        Compare latest performance results with saved baseline.
        
        Returns:
            Dictionary with comparison results and recommendations
        """
        if not self.baseline_file.exists():
            return {
                "status": "no_baseline",
                "message": "No baseline found. Run with --save-baseline to establish baseline."
            }
        
        # Load baseline
        with open(self.baseline_file, 'r') as f:
            baseline = json.load(f)
        
        # Load latest results
        history = self._load_history()
        if not history:
            return {
                "status": "no_results", 
                "message": "No performance test results found."
            }
        
        latest = history[-1]
        
        # Compare key metrics (would be enhanced with actual performance data)
        comparison = {
            "baseline_timestamp": baseline["timestamp"],
            "latest_timestamp": latest["timestamp"],
            "baseline_success": baseline["success"],
            "latest_success": latest["success"],
            "execution_time_change": latest["execution_time_seconds"] - baseline["execution_time_seconds"]
        }
        
        # Determine if regression occurred
        if latest["success"] and baseline["success"]:
            if comparison["execution_time_change"] > 10:  # 10 second increase threshold
                comparison["status"] = "regression"
                comparison["message"] = f"Performance regression detected: {comparison['execution_time_change']:.1f}s slower"
            else:
                comparison["status"] = "pass"
                comparison["message"] = "Performance within acceptable range"
        else:
            comparison["status"] = "failure"
            comparison["message"] = "Test failures detected"
        
        return comparison
    
    def _save_baseline(self, results: Dict[str, Any]):
        """Save results as performance baseline."""
        with open(self.baseline_file, 'w') as f:
            json.dump(results, f, indent=2)
    
    def _save_to_history(self, results: Dict[str, Any]):
        """Add results to performance history."""
        history = self._load_history()
        history.append(results)
        
        # Keep only last 100 results
        history = history[-100:]
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """Load performance test history."""
        if not self.history_file.exists():
            return []
        
        with open(self.history_file, 'r') as f:
            return json.load(f)
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print test execution summary."""
        print("\n" + "=" * 60)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        
        status_icon = "✅" if results["success"] else "❌"
        print(f"{status_icon} Status: {'PASSED' if results['success'] else 'FAILED'}")
        print(f"⏱️  Execution Time: {results['execution_time_seconds']:.1f} seconds")
        print(f"📅 Timestamp: {results['timestamp']}")
        print(f"📁 Test Files: {', '.join(results['test_files'])}")
        
        # Compare with baseline if available
        if self.baseline_file.exists():
            comparison = self.compare_with_baseline()
            print(f"📊 Baseline Comparison: {comparison.get('message', 'N/A')}")


def main():
    """Command-line interface for performance testing."""
    parser = argparse.ArgumentParser(description="DataMapper Performance Test Runner")
    parser.add_argument(
        "--test-file", 
        help="Specific test file to run (default: all performance tests)"
    )
    parser.add_argument(
        "--save-baseline", 
        action="store_true",
        help="Save results as new performance baseline"
    )
    parser.add_argument(
        "--compare-only",
        action="store_true", 
        help="Only compare with baseline, don't run tests"
    )
    parser.add_argument(
        "--results-dir",
        default="performance_results",
        help="Directory to store performance results (default: performance_results)"
    )
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = PerformanceTestRunner(results_dir=args.results_dir)
    
    if args.compare_only:
        # Just compare with baseline
        comparison = runner.compare_with_baseline()
        print(f"Comparison Result: {comparison}")
        sys.exit(0 if comparison.get("status") == "pass" else 1)
    
    # Run performance tests
    results = runner.run_performance_tests(
        test_file=args.test_file,
        save_baseline=args.save_baseline
    )
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()