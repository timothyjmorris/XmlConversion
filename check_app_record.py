#!/usr/bin/env python3
"""
Check if the app_base record exists.
"""

import pyodbc

def check_app_record():
    """Check if app_base record 999998 exists."""
    
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;"
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM app_base WHERE app_id = 999998")
            count = cursor.fetchone()[0]
            print(f"📊 app_base records with app_id 999998: {count}")
            
            if count > 0:
                cursor.execute("SELECT app_id, receive_date, app_source_enum, product_line_enum FROM app_base WHERE app_id = 999998")
                record = cursor.fetchone()
                print(f"📋 Record: app_id={record[0]}, receive_date={record[1]}, app_source_enum={record[2]}, product_line_enum={record[3]}")
            
    except Exception as e:
        print(f"❌ Check failed: {e}")

if __name__ == "__main__":
    check_app_record()