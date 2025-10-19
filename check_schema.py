#!/usr/bin/env python3
"""
Check the actual database schema to understand column types.
"""

import pyodbc

def check_schema():
    """Check the database schema for app_base and contact_base tables."""
    
    connection_string = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;"
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            # Check app_base schema
            print("📋 app_base table schema:")
            cursor.execute("""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'app_base'
                ORDER BY ORDINAL_POSITION
            """)
            
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]}, max_len: {row[4]})")
            
            # Check contact_base schema
            print("\n📋 contact_base table schema:")
            cursor.execute("""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'contact_base'
                ORDER BY ORDINAL_POSITION
            """)
            
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]}, max_len: {row[4]})")
                
    except Exception as e:
        print(f"❌ Schema check failed: {e}")

if __name__ == "__main__":
    check_schema()