#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
engine = MigrationEngine(db.build_connection_string())

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Check processing_log
    cursor.execute("SELECT COUNT(*) FROM processing_log")
    print(f"processing_log records: {cursor.fetchone()[0]}")
    
    # Check what's in processing_log
    cursor.execute("SELECT TOP 10 app_id, status FROM processing_log")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"  app_id={row[0]}, status={row[1]}")
    else:
        print("  (empty)")
