#!/usr/bin/env python3
"""
Direct runner for live integration test.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_live_end_to_end_integration import TestLiveEndToEndIntegration

def run_test():
    """Run the live integration test directly."""
    print("🚀 Starting Live End-to-End Integration Test")
    print("⚠️  This test will insert real data into the database!")
    
    try:
        # Create test instance
        test_instance = TestLiveEndToEndIntegration()
        test_instance.setUp()
        
        # Run the main test
        test_instance.test_live_end_to_end_pipeline()
        
        print("\n🎉 Live integration test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Live integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = run_test()
    sys.exit(0 if success else 1)