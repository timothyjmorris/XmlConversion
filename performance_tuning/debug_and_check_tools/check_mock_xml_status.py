#!/usr/bin/env python3
"""Check if mock XMLs are being filtered out."""

from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
conn_str = db.build_connection_string()
engine = MigrationEngine(conn_str)

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM app_base WHERE app_id >= 1000000')
    app_base_count = cursor.fetchone()[0]
    print(f'app_base records >= 1000000: {app_base_count}')
    
    cursor.execute('SELECT COUNT(*) FROM app_xml WHERE app_id >= 1000000')
    app_xml_count = cursor.fetchone()[0]
    print(f'app_xml records >= 1000000: {app_xml_count}')
    
    cursor.execute('SELECT COUNT(*) FROM app_xml WHERE app_id >= 1000000 AND DATALENGTH(xml) > 100')
    valid_xml_count = cursor.fetchone()[0]
    print(f'app_xml valid XML >= 1000000: {valid_xml_count}')
    
    # Check if they're in app_pricing_cc
    cursor.execute('SELECT COUNT(*) FROM app_pricing_cc WHERE app_id >= 1000000')
    pricing_count = cursor.fetchone()[0]
    print(f'app_pricing_cc records >= 1000000: {pricing_count}')
    
    # Check processing_log
    cursor.execute('SELECT COUNT(*) FROM processing_log WHERE app_id >= 1000000')
    log_count = cursor.fetchone()[0]
    print(f'processing_log records >= 1000000: {log_count}')
