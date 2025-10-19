#!/usr/bin/env python3
"""
Minimal test to check database insertion with simple data using direct pyodbc.
"""

import sys
import os
import pyodbc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_minimal_insert():
    """Test inserting minimal data using direct pyodbc like the working tests."""
    
    print("🔧 Starting minimal insert test with direct pyodbc...")
    
    # Use the same connection string as the working tests
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;"
    print(f"📡 Connection string: {connection_string}")
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            print("✅ Database connection successful")
    
            # Test 1: Simple app_base record with minimal data
            print("\n🧪 Test 1: Minimal app_base record")
            
            # Clean up first
            cursor.execute("DELETE FROM contact_base WHERE app_id = 999999")
            cursor.execute("DELETE FROM app_base WHERE app_id = 999999")
            
            # Insert app_base record using the exact same approach as your manual SQL
            cursor.execute("SET IDENTITY_INSERT app_base ON")
            cursor.execute("""
                INSERT INTO [app_base]([app_id], [receive_date], [app_source_enum], [product_line_enum])
                VALUES(?, ?, ?, ?)
            """, (999999, '2023-01-01', 1, 600))
            cursor.execute("SET IDENTITY_INSERT app_base OFF")
            print("✅ app_base insertion succeeded")
            
            # Test 2: Simple contact_base record with minimal data
            print("\n🧪 Test 2: Minimal contact_base record")
            
            cursor.execute("SET IDENTITY_INSERT contact_base ON")
            cursor.execute("""
                INSERT INTO [contact_base]([con_id], [first_name], [last_name], [ssn], [birth_date], [contact_type_enum], [middle_initial], [mother_maiden_name], [suffix], [email], [home_phone], [cell_phone], [app_id])
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (999999, 'TEST', 'USER', '123456789', '1990-01-01', 281, '', '', '', '', '', '', 999999))
            cursor.execute("SET IDENTITY_INSERT contact_base OFF")
            print("✅ contact_base insertion succeeded")
            
            # Verify the data was inserted
            cursor.execute("SELECT COUNT(*) FROM app_base WHERE app_id = 999999")
            app_count = cursor.fetchone()[0]
            print(f"📊 app_base records: {app_count}")
            
            cursor.execute("SELECT COUNT(*) FROM contact_base WHERE app_id = 999999")
            contact_count = cursor.fetchone()[0]
            print(f"📊 contact_base records: {contact_count}")
            
            # Cleanup
            print("\n🧹 Cleaning up test data")
            cursor.execute("DELETE FROM contact_base WHERE app_id = 999999")
            cursor.execute("DELETE FROM app_base WHERE app_id = 999999")
            conn.commit()
            print("✅ Cleanup completed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_minimal_insert()