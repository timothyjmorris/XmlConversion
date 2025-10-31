#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
engine = MigrationEngine(db.build_connection_string())

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Check distinct status values
    cursor.execute("SELECT DISTINCT status FROM processing_log")
    print("Distinct status values:")
    for row in cursor.fetchall():
        print(f"  '{row[0]}'")
    
    # Check for status='failed'
    cursor.execute("SELECT COUNT(*) FROM processing_log WHERE status = 'failed'")
    print(f"\nStatus='failed': {cursor.fetchone()[0]}")
    
    # Check if app_ids 1-50 are in processing_log at all
    cursor.execute("SELECT COUNT(*) FROM processing_log WHERE app_id >= 1 AND app_id <= 50")
    print(f"processing_log with app_id 1-50: {cursor.fetchone()[0]}")
