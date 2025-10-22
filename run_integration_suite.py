#!/usr/bin/env python3
"""
Integration Test Suite Runner

This script runs the core integration tests that should be executed frequently
when making changes to ensure the system still works end-to-end.

Test Categories:
1. Validation Tests - Test validation logic and edge cases
2. Integration Tests - Test full pipeline with database operations  
3. Production Tests - Test with real production data
"""

import sys
import subprocess
from pathlib import Path
import time

def run_test_suite():
    """Run the complete integration test suite."""
    print("🚀 RUNNING INTEGRATION TEST SUITE")
    print("=" * 80)
    
    # Test suite configuration - organized by category
    tests = [
        # Unit Tests (Fast, isolated)
        {
            'name': 'Configuration Management Tests (Unit)',
            'file': 'tests/unit/test_config_manager_unit.py',
            'description': 'Tests centralized configuration system',
            'critical': True,
            'category': 'unit'
        },
        {
            'name': 'Validation Scenarios Tests (Unit)',
            'file': 'tests/unit/test_validation_scenarios_unit.py',
            'description': 'Tests validation logic with mock XML scenarios',
            'critical': True,
            'category': 'unit'
        },
        {
            'name': 'Validation System Tests (Unit)',
            'file': 'tests/unit/test_validation_system_unit.py',
            'description': 'Tests data integrity validation system',
            'critical': True,
            'category': 'unit'
        },
        # Contract Tests (Fast, schema validation)
        {
            'name': 'Mapping Contract Schema Tests (Contract)',
            'file': 'tests/contracts/test_mapping_contract_schema.py',
            'description': 'Tests mapping contract JSON schema validation',
            'critical': True,
            'category': 'contract'
        },
        # Integration Tests (Medium speed, component interaction)
        {
            'name': 'Configuration Integration Tests',
            'file': 'tests/integration/test_config_integration.py',
            'description': 'Tests ConfigManager integration with components',
            'critical': True,
            'category': 'integration'
        },
        {
            'name': 'Real Sample Validation Tests (Integration)', 
            'file': 'tests/integration/test_validation_real_sample.py',
            'description': 'Tests validation logic with real sample XML and edge cases',
            'critical': True,
            'category': 'integration'
        },
        # E2E Tests (Slow, full pipeline)
        {
            'name': 'Pipeline Integration Tests (E2E)',
            'file': 'tests/e2e/test_pipeline_full_integration.py', 
            'description': 'Tests complete pipeline with database insertion',
            'critical': True,
            'category': 'e2e'
        },
        {
            'name': 'Production Batch Tests (E2E)',
            'file': 'tests/e2e/test_production_batch_processing.py',
            'description': 'Tests with real production XML data from database',
            'critical': False,  # Optional since it requires production data
            'category': 'e2e'
        }
    ]
    
    results = []
    start_time = time.time()
    
    for i, test in enumerate(tests, 1):
        print(f"\n📋 {i}/{len(tests)}: {test['name']}")
        print(f"   {test['description']}")
        print(f"   File: {test['file']}")
        
        try:
            # Check if test file exists
            if not Path(test['file']).exists():
                print(f"   ⚠️ SKIPPED - Test file not found")
                results.append({
                    'name': test['name'],
                    'success': None,  # Skipped
                    'critical': test['critical'],
                    'output': '',
                    'error': 'Test file not found'
                })
                continue
            
            # Run the test
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                test['file'], 
                '-v', '-x'  # Stop on first failure
            ], capture_output=True, text=True, timeout=300)
            
            success = result.returncode == 0
            results.append({
                'name': test['name'],
                'success': success,
                'critical': test['critical'],
                'output': result.stdout,
                'error': result.stderr
            })
            
            if success:
                print(f"   ✅ PASSED")
            else:
                print(f"   ❌ FAILED")
                if test['critical']:
                    print(f"   🚨 CRITICAL TEST FAILED - This may indicate a serious issue")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ TIMEOUT - Test took longer than 5 minutes")
            results.append({
                'name': test['name'],
                'success': False,
                'critical': test['critical'],
                'output': '',
                'error': 'Test timeout after 5 minutes'
            })
        except Exception as e:
            print(f"   💥 ERROR - {e}")
            results.append({
                'name': test['name'],
                'success': False,
                'critical': test['critical'],
                'output': '',
                'error': str(e)
            })
    
    # Generate summary report
    total_time = time.time() - start_time
    print(f"\n" + "=" * 80)
    print("📊 INTEGRATION TEST SUITE SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r['success'] == True)
    failed = sum(1 for r in results if r['success'] == False)
    skipped = sum(1 for r in results if r['success'] is None)
    critical_failed = sum(1 for r in results if r['success'] == False and r['critical'])
    
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    print(f"Critical Failures: {critical_failed}")
    print(f"Total Time: {total_time:.1f} seconds")
    
    # Show detailed results
    if failed > 0:
        print(f"\n❌ Failed Tests:")
        for result in results:
            if result['success'] == False:
                critical_marker = "🚨 CRITICAL" if result['critical'] else ""
                print(f"   - {result['name']} {critical_marker}")
                if result['error']:
                    print(f"     Error: {result['error'][:200]}...")
    
    if skipped > 0:
        print(f"\n⚠️ Skipped Tests:")
        for result in results:
            if result['success'] is None:
                print(f"   - {result['name']}")
                print(f"     Reason: {result['error']}")
    
    if passed > 0:
        print(f"\n✅ Passed Tests:")
        for result in results:
            if result['success'] == True:
                print(f"   - {result['name']}")
    
    # Overall assessment
    if critical_failed > 0:
        print(f"\n🚨 CRITICAL ISSUES DETECTED")
        print(f"   {critical_failed} critical test(s) failed")
        print(f"   System may not be ready for production use")
        return False
    elif failed > 0:
        print(f"\n⚠️ SOME ISSUES DETECTED") 
        print(f"   {failed} non-critical test(s) failed")
        print(f"   Core functionality appears to work")
        return True
    else:
        print(f"\n🎉 ALL TESTS PASSED")
        print(f"   System is working correctly")
        return True

if __name__ == '__main__':
    success = run_test_suite()
    sys.exit(0 if success else 1)