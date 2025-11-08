"""
Quick Test Runner for Development

This script runs only the fast tests (unit + contracts) for quick feedback during development.
Perfect for running after code changes to ensure nothing is broken.
"""

import sys
import subprocess
import time

from pathlib import Path


def run_quick_tests():
    """Run quick tests for fast development feedback."""
    print("RUNNING QUICK TESTS (Unit + Contract)")
    print("=" * 60)
    
    # Quick test categories
    test_categories = [
        {
            'name': 'Contract Tests',
            'path': 'tests/contracts',
            'timeout': 30,
            'description': 'Schema and configuration validation'
        },
        {
            'name': 'Unit Tests', 
            'path': 'tests/unit',
            'timeout': 60,
            'description': 'Fast isolated component tests'
        }
    ]
    
    results = []
    total_start_time = time.time()
    
    for category in test_categories:
        print(f"\\n🧪 Running {category['name']}")
        print(f"   {category['description']}")
        
        test_path = Path(category['path'])
        if not test_path.exists():
            print(f"   ⚠️ No tests found in {test_path}")
            continue
        
        test_files = list(test_path.glob("test_*.py"))
        if not test_files:
            print(f"   ⚠️ No test files found in {test_path}")
            continue
        
        print(f"   📁 Found {len(test_files)} test file(s)")
        
        start_time = time.time()
        
        try:
            # Run pytest for the category
            result = subprocess.run([
                sys.executable, '-m', 'pytest',
                str(test_path),
                '-v',
                '--tb=short',
                '--maxfail=5'  # Stop after 5 failures
            ], capture_output=True, text=True, timeout=category['timeout'])
            
            execution_time = time.time() - start_time
            success = result.returncode == 0
            
            # Parse test counts from output
            passed, failed = parse_pytest_output(result.stdout)
            
            results.append({
                'category': category['name'],
                'success': success,
                'passed': passed,
                'failed': failed,
                'time': execution_time,
                'output': result.stdout,
                'error': result.stderr
            })
            
            if success:
                print(f"   ✅ PASSED ({passed} tests, {execution_time:.1f}s)")
            else:
                print(f"   ❌ FAILED ({passed} passed, {failed} failed, {execution_time:.1f}s)")
                
                # Show first few failures
                failure_lines = [line for line in result.stdout.split('\\n') if 'FAILED' in line]
                for line in failure_lines[:3]:
                    print(f"      {line}")
                if len(failure_lines) > 3:
                    print(f"      ... and {len(failure_lines) - 3} more failures")
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            print(f"   ⏰ TIMEOUT after {category['timeout']}s")
            results.append({
                'category': category['name'],
                'success': False,
                'passed': 0,
                'failed': 1,
                'time': execution_time,
                'output': '',
                'error': f"Timeout after {category['timeout']}s"
            })
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"   💥 ERROR: {e}")
            results.append({
                'category': category['name'],
                'success': False,
                'passed': 0,
                'failed': 1,
                'time': execution_time,
                'output': '',
                'error': str(e)
            })
    
    # Generate summary
    total_time = time.time() - total_start_time
    total_passed = sum(r['passed'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    all_success = all(r['success'] for r in results)
    
    print(f"\\n" + "=" * 60)
    print("📊 QUICK TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {total_passed + total_failed}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print(f"Total Time: {total_time:.1f}s")
    
    if total_passed + total_failed > 0:
        success_rate = (total_passed / (total_passed + total_failed)) * 100
        print(f"Success Rate: {success_rate:.1f}%")
    
    # Performance analysis
    if total_time > 0:
        tests_per_second = (total_passed + total_failed) / total_time
        print(f"Speed: {tests_per_second:.1f} tests/second")
    
    # Category breakdown
    print(f"\\nCategory Results:")
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"   {status} {result['category']:15} {result['passed']:3}P {result['failed']:3}F {result['time']:5.1f}s")
    
    # Overall assessment
    if all_success:
        print(f"\\n🎉 ALL QUICK TESTS PASSED!")
        print(f"   Ready to continue development")
    else:
        print(f"\\n⚠️ SOME QUICK TESTS FAILED")
        print(f"   Fix issues before committing")
    
    return all_success


def parse_pytest_output(output: str) -> tuple:
    """Parse pytest output to extract pass/fail counts."""
    passed = 0
    failed = 0
    
    for line in output.split('\\n'):
        if ' passed' in line and ' failed' in line:
            # Line like: "5 passed, 2 failed in 10.5s"
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'passed' and i > 0:
                    try:
                        passed = int(parts[i-1])
                    except ValueError:
                        pass
                elif part == 'failed' and i > 0:
                    try:
                        failed = int(parts[i-1])
                    except ValueError:
                        pass
        elif ' passed' in line and 'failed' not in line:
            # Line like: "5 passed in 10.5s"
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'passed' and i > 0:
                    try:
                        passed = int(parts[i-1])
                    except ValueError:
                        pass
    
    return passed, failed


if __name__ == '__main__':
    success = run_quick_tests()
    sys.exit(0 if success else 1)