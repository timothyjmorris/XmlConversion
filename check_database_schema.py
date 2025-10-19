#!/usr/bin/env python3
"""
Check the actual database schema to understand table structure.
"""

import json
import pyodbc
from pathlib import Path

def check_schema():
    """Check database schema."""
    # Load database config
    config_path = Path("config/database_config.json")
    with open(config_path, 'r') as f:
        db_config = json.load(f)
    
    # Build connection string
    db_settings = db_config["database"]
    connection_string = db_config["connection_string_template_windows_auth"].format(**db_settings)
    
    print("🔍 Checking Database Schema")
    print("="*50)
    
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📋 Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        
        # Check for tables that might be related to our data
        relevant_tables = [t for t in tables if any(keyword in t.lower() for keyword in ['app', 'contact', 'address', 'employment'])]
        
        print(f"\n🎯 Relevant tables for our test:")
        for table in relevant_tables:
            print(f"  - {table}")
        
        # Get column info for relevant tables
        for table in relevant_tables:
            print(f"\n📊 Columns in {table}:")
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table}'
                ORDER BY ORDINAL_POSITION
            """)
            
            columns = cursor.fetchall()
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"    {col[0]} ({col[1]}) {nullable}{default}")

if __name__ == '__main__':
    check_schema()