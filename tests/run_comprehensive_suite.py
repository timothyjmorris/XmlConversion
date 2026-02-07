"""
Comprehensive Test Suite Runner

This script runs tests across all categories with appropriate execution strategies:
- Unit Tests: Fast, isolated component testing
- Integration Tests: Component interaction testing
- End-to-End Tests: Full pipeline testing
- Contract Tests: Schema and configuration validation
"""

import os
import sys
import subprocess
import time
import argparse

from pathlib import Path
from typing import Dict, List, Tuple


class TestSuiteRunner:
    """Comprehensive test suite runner with category-based execution."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.results = {
            'unit': {'passed': 0, 'failed': 0, 'time': 0, 'details': []},
            'integration': {'passed': 0, 'failed': 0, 'time': 0, 'details': []},
            'e2e': {'passed': 0, 'failed': 0, 'time': 0, 'details': []},
            'contracts': {'passed': 0, 'failed': 0, 'time': 0, 'details': []}
        }
    
    def run_category(self, category: str, timeout: int = 300) -> bool:
        """Run tests for a specific category."""
        print(f"{'='*80}")
        print(f"RUNNING {category.upper()} TESTS")
        print(f"{'='*80}")
        
        workspace_root = Path(__file__).resolve().parent.parent
        test_path = workspace_root / "tests" / category
        if not test_path.exists():
            print(f"WARNING: No tests found in {test_path}")
            return True

        test_files = list(test_path.glob("test_*.py"))
        if not test_files:
            print(f"WARNING: No test files found in {test_path}")
            # E2E tests in this repo are often "manual_*" scripts, not pytest-collected tests.
            # If no pytest-style tests exist, treat this category as a SKIP (not a failure).
            if category == 'e2e':
                self.results[category]['time'] = 0
                self.results[category]['passed'] = 0
                self.results[category]['failed'] = 0
                self.results[category]['details'] = {
                    'success': True,
                    'skipped': True,
                    'reason': 'No pytest test_*.py files found under tests/e2e'
                }
                print(f"SKIPPING {category.upper()} TESTS (no pytest-collected tests found)")
                return True
        else:
            print(f"Found {len(test_files)} test file(s) in {test_path}")

        start_time = time.time()

        try:
            # Run pytest for the category from workspace root
            cmd = [
                sys.executable, '-m', 'pytest',
                str(test_path.relative_to(workspace_root)),
                '-v',
                '--tb=short',
                '--capture=no'
            ]
            if category == 'unit':
                cmd.extend(['--maxfail=5'])
            elif category == 'e2e':
                cmd.extend(['--maxfail=1'])

            print(f" Executing: {' '.join(cmd)}")

            env = dict(os.environ)
            env['PYTHONPATH'] = str(workspace_root) + os.pathsep + env.get('PYTHONPATH', '')
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=str(workspace_root)
            )
            
            execution_time = time.time() - start_time
            self.results[category]['time'] = execution_time
            
            # Parse pytest output for results
            success = result.returncode == 0
            output_lines = result.stdout.split('\n')

            # Extract test results from pytest output (always show summary)
            passed, failed = self._parse_pytest_output(output_lines)
            self.results[category]['passed'] = passed
            self.results[category]['failed'] = failed

            print(f"   {category.upper()} TESTS {'PASSED' if success else 'FAILED'}")
            print(f"   Tests: {passed} passed, {failed} failed")
            print(f"   Time: {execution_time:.1f}s")

            if not success:
                # Show failure details
                if result.stderr:
                    print(f"Error Output:")
                    print(result.stderr[:1000])  # Limit error output
                # Show relevant stdout
                failure_lines = [line for line in output_lines if 'FAILED' in line or 'ERROR' in line]
                if failure_lines:
                    print(f"Failed Tests:")
                    for line in failure_lines[:10]:  # Show first 10 failures
                        print(f"   {line}")

            self.results[category]['details'] = {
                'success': success,
                'skipped': False,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

            return success
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            self.results[category]['time'] = execution_time
            print(f"{category.upper()} TESTS TIMED OUT after {timeout}s")
            return False
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.results[category]['time'] = execution_time
            print(f"{category.upper()} TESTS ERROR: {e}")
            return False
    
    def _parse_pytest_output(self, output_lines: List[str]) -> Tuple[int, int]:
        """Parse pytest output to extract pass/fail counts from the pytest summary line for any category."""
        import re
        passed = 0
        failed = 0
        # Look for pytest summary line (e.g. '== 5 failed, 42 passed in 0.93s ==')
        summary_line = None
        for line in reversed(output_lines):
            # Match lines like '== ... 65 passed ... ==', with or without commas
            if re.search(r'\d+\s+passed', line) or re.search(r'\d+\s+failed', line):
                summary_line = line
                break
        if summary_line:
            # Remove ANSI color codes
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', summary_line)
            # Use regex to extract all 'N passed', 'N failed', etc. regardless of comma/space
            matches = re.findall(r'(\d+)\s+passed|(\d+)\s+failed', clean_line)
            for m in matches:
                if m[0]:
                    passed += int(m[0])
                if m[1]:
                    failed += int(m[1])
        return passed, failed
    
    def run_all_categories(self, categories: List[str] = None) -> bool:
        """Run all test categories."""
        if categories is None:
            categories = ['contracts', 'unit', 'integration', 'e2e']
        
        print(f"RUNNING COMPREHENSIVE TEST SUITE")
        print(f"Categories: {', '.join(categories)}")
        
        overall_success = True
        critical_success = True  # Track only critical categories
        category_timeouts = {
            'unit': 60,        # 1 minute for unit tests
            'integration': 180, # 3 minutes for integration tests
            'e2e': 600,        # 10 minutes for E2E tests
            'contracts': 30    # 30 seconds for contract tests
        }
        
        # Critical categories that must pass
        critical_categories = ['unit', 'contracts', 'integration']
        
        for category in categories:
            timeout = category_timeouts.get(category, 300)
            success = self.run_category(category, timeout)
            if not success:
                overall_success = False
                
                # Track failures in critical categories
                if category in critical_categories:
                    critical_success = False
                
                # For critical categories, consider stopping
                if category in ['unit', 'contracts']:
                    print(f"CRITICAL CATEGORY {category.upper()} FAILED")
                    print(f"   Consider fixing {category} tests before proceeding")
        
        # Return success based on critical categories only (unit, contracts, integration)
        # E2E is optional/future and should not block commits
        return critical_success
    
    def generate_summary_report(self) -> None:
        """Generate comprehensive summary report."""
        print(f"{'='*80}")
        print(f"COMPREHENSIVE TEST SUITE SUMMARY")
        print(f"{'='*80}")
        
        total_passed = sum(r['passed'] for r in self.results.values())
        total_failed = sum(r['failed'] for r in self.results.values())
        total_time = sum(r['time'] for r in self.results.values())
        total_tests = total_passed + total_failed
        
        print(f"Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {total_passed}")
        print(f"   Failed: {total_failed}")
        print(f"   Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "   Success Rate: N/A")
        print(f"   Total Time: {total_time:.1f}s")
        
        print(f"Category Breakdown:")
        for category, results in self.results.items():
            total_cat = results['passed'] + results['failed']
            if total_cat > 0 or (results['passed'] == 0 and results['failed'] == 0):
                # Always show summary, even if zero
                details = results.get('details') if isinstance(results.get('details'), dict) else {}
                is_skipped = bool(details.get('skipped'))
                success_rate = (results['passed'] / total_cat) * 100 if total_cat > 0 else 0.0
                status = "SKIP" if is_skipped else ("OK" if results['failed'] == 0 else "BAD")
                print(f"   {status} {category.upper():12} {results['passed']:3}P {results['failed']:3}F {success_rate:5.1f}% {results['time']:6.1f}s")
            else:
                print(f"   {category.upper():12} No tests found")
                print(f"        WARNING: No tests were discovered for {category}. Check test file names and test function definitions.")
        
        # Performance analysis
        print(f"Performance Analysis:")
        for category, results in self.results.items():
            total_cat = results['passed'] + results['failed']
            if total_cat > 0 and results['time'] > 0:
                tests_per_second = total_cat / results['time']
                print(f"   {category.upper():12} {tests_per_second:.1f} tests/second")
        
        # Quality gates
        print(f"Quality Gates:")
        
        # Unit tests should be fast and reliable
        unit_results = self.results['unit']
        unit_total = unit_results['passed'] + unit_results['failed']
        if unit_total > 0:
            unit_success = unit_results['failed'] == 0
            unit_fast = unit_results['time'] < 60
            print(f"   Unit Tests:        {'OK' if unit_success else 'BAD'} 100% Pass Rate {'OK' if unit_fast else 'BAD'} <60s Execution")
        
        # Integration tests should be reliable
        int_results = self.results['integration']
        int_total = int_results['passed'] + int_results['failed']
        if int_total > 0:
            int_success = int_results['failed'] == 0
            int_reasonable = int_results['time'] < 180
            print(f"   Integration Tests: {'OK' if int_success else 'BAD'} 100% Pass Rate {'OK' if int_reasonable else 'BAD'} <180s Execution")
        
        # E2E tests can have some tolerance
        e2e_results = self.results['e2e']
        e2e_total = e2e_results['passed'] + e2e_results['failed']
        if e2e_total > 0:
            e2e_success_rate = (e2e_results['passed'] / e2e_total) * 100
            e2e_acceptable = e2e_success_rate >= 90
            e2e_reasonable = e2e_results['time'] < 600
            print(f"   E2E Tests:         {'OK' if e2e_acceptable else 'BAD'} ≥90% Pass Rate {'OK' if e2e_reasonable else 'BAD'} <600s Execution")
        
        # Contract tests should be perfect
        contract_results = self.results['contracts']
        contract_total = contract_results['passed'] + contract_results['failed']
        if contract_total > 0:
            contract_success = contract_results['failed'] == 0
            contract_fast = contract_results['time'] < 30
            print(f"   Contract Tests:    {'OK' if contract_success else 'BAD'} 100% Pass Rate {'OK' if contract_fast else 'BAD'} <30s Execution")
        
        # Overall assessment
        critical_failures = (
            self.results['unit']['failed'] > 0 or
            self.results['contracts']['failed'] > 0
        )
        
        if critical_failures:
            print(f"BRO: CRITICAL ISSUES DETECTED")
            print(f"   Unit or Contract tests failed - system may not be ready for production")
        elif total_failed > 0:
            print(f"BRO: SOME ISSUES DETECTED")
            print(f"   Non-critical tests failed - review before production deployment")
        else:
            print(f"BRO! ALL TESTS PASSED")
            print(f"   System is ready for production deployment")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run comprehensive test suite')
    parser.add_argument(
        '--categories',
        nargs='+',
        choices=['unit', 'integration', 'e2e', 'contracts'],
        default=['contracts', 'unit', 'integration', 'e2e'],
        help='Test categories to run (default: all)'
    )
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Run only fast tests (unit + contracts)'
    )
    parser.add_argument(
        '--critical',
        action='store_true',
        help='Run only critical tests (unit + integration)'
    )
    
    args = parser.parse_args()
    
    # Determine categories to run
    if args.fast:
        categories = ['contracts', 'unit']
    elif args.critical:
        categories = ['contracts', 'unit', 'integration']
    else:
        categories = args.categories
    
    # Run tests
    runner = TestSuiteRunner()
    success = runner.run_all_categories(categories)
    runner.generate_summary_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()