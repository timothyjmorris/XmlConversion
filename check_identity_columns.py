#!/usr/bin/env python3
"""
Check which columns are identity columns.
"""

import json
import pyodbc
from pathlib import Path

def check_identity_columns():
    """Check identity columns in relevant tables."""
    # Load database config
    config_path = Path("config/database_config.json")
    with open(config_path, 'r') as f:
        db_config = json.load(f)
    
    # Build connection string
    db_settings = db_config["database"]
    connection_string = db_config["connection_string_template_windows_auth"].format(**db_settings)
    
    print("🔍 Checking Identity Columns")
    print("="*50)
    
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        
        # Check identity columns in relevant tables
        tables = ['app_base', 'contact_base', 'contact_address', 'contact_employment']
        
        for table in tables:
            print(f"\n📊 Identity columns in {table}:")
            cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA+'.'+TABLE_NAME), COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = '{table}' AND COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA+'.'+TABLE_NAME), COLUMN_NAME, 'IsIdentity') = 1
                ORDER BY ORDINAL_POSITION
            """)
            
            identity_cols = cursor.fetchall()
            if identity_cols:
                for col in identity_cols:
                    print(f"    {col[0]} ({col[1]}) - IDENTITY")
            else:
                print("    No identity columns")

if __name__ == '__main__':
    check_identity_columns()