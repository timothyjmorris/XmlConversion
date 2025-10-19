#!/usr/bin/env python3
"""
Test the fixed bulk insert method.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from xml_extractor.database.migration_engine import MigrationEngine

def test_app_base_only():
    """Test only app_base bulk insert."""
    
    print("🔧 Testing app_base bulk insert only...")
    
    # Use the same connection string as the working tests
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;"
    migration_engine = MigrationEngine(connection_string)
    
    # Clean up first
    import pyodbc
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contact_base WHERE app_id = 999997")
        cursor.execute("DELETE FROM app_base WHERE app_id = 999997")
        conn.commit()
    
    # Test: Simple app_base record with minimal data
    print("\n🧪 Testing app_base bulk insert")
    app_record = {
        'app_id': 999997,  # Use a different unique ID
        'receive_date': '2023-01-01',  # YYYY-MM-DD format
        'app_source_enum': 1,
        'product_line_enum': 600
    }
    
    try:
        result = migration_engine.execute_bulk_insert([app_record], 'app_base', enable_identity_insert=True)
        print(f"✅ app_base bulk insert succeeded: {result} records")
    except Exception as e:
        print(f"❌ app_base bulk insert failed: {e}")
        return
    
    # Verify the data was inserted using direct pyodbc
    print("\n🔍 Verifying inserted data...")
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM app_base WHERE app_id = 999997")
            app_count = cursor.fetchone()[0]
            print(f"📊 app_base records: {app_count}")
            
            if app_count > 0:
                cursor.execute("SELECT app_id, receive_date FROM app_base WHERE app_id = 999997")
                record = cursor.fetchone()
                print(f"📋 Found record: app_id={record[0]}, receive_date={record[1]}")
            
            # Cleanup
            print("\n🧹 Cleaning up test data")
            cursor.execute("DELETE FROM app_base WHERE app_id = 999997")
            conn.commit()
            print("✅ Cleanup completed")
            
    except Exception as e:
        print(f"❌ Verification failed: {e}")

def test_fixed_bulk_insert():
    """Test the fixed bulk insert method."""
    test_app_base_only()

if __name__ == "__main__":
    test_fixed_bulk_insert()