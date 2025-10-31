#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
engine = MigrationEngine(db.build_connection_string())

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Get foreign keys
    cursor.execute("""
        SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_NAME = 'processing_log' AND REFERENCED_TABLE_NAME IS NOT NULL
    """)
    
    print("Foreign keys in processing_log:")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"  {row}")
    else:
        print("  (none)")
