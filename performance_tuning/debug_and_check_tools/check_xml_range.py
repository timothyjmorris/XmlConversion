#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
conn_str = db.build_connection_string()
engine = MigrationEngine(conn_str)

with engine.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(app_id), MIN(app_id), COUNT(*) FROM app_xml WHERE xml IS NOT NULL')
    row = cursor.fetchone()
    print(f'Max app_id: {row[0]}, Min: {row[1]}, Total XML records: {row[2]}')
