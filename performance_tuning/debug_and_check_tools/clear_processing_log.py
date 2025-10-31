#!/usr/bin/env python3
from xml_extractor.database.migration_engine import MigrationEngine
from tests.integration.test_database_connection import DatabaseConnectionTester

db = DatabaseConnectionTester()
engine = MigrationEngine(db.build_connection_string())

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Check current count
    cursor.execute('SELECT COUNT(*) FROM processing_log WHERE app_id BETWEEN 1 AND 50')
    print(f"Before DELETE: {cursor.fetchone()[0]}")
    
    # Delete
    cursor.execute('DELETE FROM processing_log')
    conn.commit()
    
    # Check after DELETE
    cursor.execute('SELECT COUNT(*) FROM processing_log WHERE app_id BETWEEN 1 AND 50')
    print(f"After DELETE: {cursor.fetchone()[0]}")
