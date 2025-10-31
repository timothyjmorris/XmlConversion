#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
conn_str = db.build_connection_string()
engine = MigrationEngine(conn_str)

with engine.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM app_base WHERE app_id <= 50')
    print(f'app_base records 1-50: {cursor.fetchone()[0]}')
    cursor.execute('SELECT COUNT(*) FROM app_pricing_cc WHERE app_id <= 50')
    print(f'app_pricing_cc records 1-50: {cursor.fetchone()[0]}')
