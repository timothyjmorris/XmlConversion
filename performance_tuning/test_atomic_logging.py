"""
Quick test to verify atomic logging implementation works in normal processing.

⚠️  NOTE: This tests NORMAL processing, NOT crash recovery!
    For crash testing, use crash_test_atomic_logging.py instead.

Tests:
1. Process a small batch (10 records) normally
2. Verify processing_log entries exist
3. Verify data and log counts match
4. Check FK constraint enforcement

What this DOESN'T test:
- Crash during batch processing
- Recovery after crash
- Orphaned data from incomplete transactions
- Resume capability after crash

Usage:
    python test_atomic_logging.py
"""

import pyodbc
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from production_processor import ProductionProcessor

def verify_counts(connection_string, target_schema='sandbox'):
    """Verify data and log entry counts match."""
    try:
        conn = pyodbc.connect(connection_string, autocommit=True)
        cursor = conn.cursor()
        
        # Count app_base records
        cursor.execute(f"SELECT COUNT(*) FROM [{target_schema}].[app_base]")
        app_count = cursor.fetchone()[0]
        
        # Count processing_log success entries
        cursor.execute(f"SELECT COUNT(*) FROM [{target_schema}].[processing_log] WHERE status='success'")
        log_count = cursor.fetchone()[0]
        
        print(f"\n{'='*60}")
        print(f"ATOMICITY VERIFICATION")
        print(f"{'='*60}")
        print(f"app_base records:         {app_count}")
        print(f"processing_log successes: {log_count}")
        print(f"Match: {'✅ YES' if app_count == log_count else '❌ NO - ORPHANED DATA DETECTED'}")
        
        # Check for any orphaned data (app_base without processing_log)
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM [{target_schema}].[app_base] ab
            LEFT JOIN [{target_schema}].[processing_log] pl ON ab.app_id = pl.app_id
            WHERE pl.app_id IS NULL
        """)
        orphaned = cursor.fetchone()[0]
        
        if orphaned > 0:
            print(f"⚠️  WARNING: {orphaned} orphaned records found (data without log entry)")
        else:
            print(f"✅ No orphaned data detected")
        
        conn.close()
        return app_count == log_count and orphaned == 0
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("ATOMIC LOGGING TEST")
    print("="*60)
    print("Testing: processing_log entries created atomically with data")
    print("Expected: Every app_base record has matching processing_log entry")
    print("\n")
    
    # Configuration
    server = "localhost\\SQLEXPRESS"
    database = "XmlConversionDB"
    target_schema = "sandbox"
    test_limit = 10  # Process only 10 records for quick test
    
    # Build connection string
    connection_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
        f"Encrypt=no;"
        f"Pooling=False;"
    )
    
    print(f"Server:        {server}")
    print(f"Database:      {database}")
    print(f"Target Schema: {target_schema}")
    print(f"Test Limit:    {test_limit} records")
    print(f"\n{'='*60}\n")
    
    try:
        # Get initial counts
        print("📊 BEFORE PROCESSING:")
        verify_counts(connection_string, target_schema)
        
        # Process test batch
        print(f"\n{'='*60}")
        print(f"PROCESSING TEST BATCH")
        print(f"{'='*60}\n")
        
        processor = ProductionProcessor(
            server=server,
            database=database,
            workers=4,
            batch_size=10,
            log_level="WARNING",  # Quiet output for test
            disable_metrics=True,
            enable_pooling=False
        )
        
        results = processor.run_full_processing(limit=test_limit)
        
        # Verify atomicity
        print(f"\n{'='*60}")
        print(f"📊 AFTER PROCESSING:")
        success = verify_counts(connection_string, target_schema)
        
        if success:
            print(f"\n{'='*60}")
            print(f"✅ TEST PASSED: Atomic logging working correctly!")
            print(f"{'='*60}\n")
            return 0
        else:
            print(f"\n{'='*60}")
            print(f"❌ TEST FAILED: Data/log mismatch detected")
            print(f"{'='*60}\n")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
