#!/usr/bin/env python3
"""
Clean up test data from database.
"""

import pyodbc

def cleanup_test_data():
    """Clean up test data for app_id 443306."""
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;"
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            print("🧹 Cleaning up test data for app_id = 443306...")
            
            # Use cascade delete - just delete from app_base and let foreign keys cascade
            cursor.execute("DELETE FROM app_base WHERE app_id = 443306")
            
            conn.commit()
            print("✅ Cleanup completed successfully")
            
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")

if __name__ == "__main__":
    cleanup_test_data()