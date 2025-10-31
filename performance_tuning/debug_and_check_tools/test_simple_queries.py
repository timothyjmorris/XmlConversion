#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
engine = MigrationEngine(db.build_connection_string())

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Test 1: Very simple - just select from app_xml
    cursor.execute("SELECT COUNT(*) FROM app_xml")
    print(f"Total in app_xml: {cursor.fetchone()[0]}")
    
    # Test 2: With LEFT JOIN to app_base
    cursor.execute("SELECT COUNT(*) FROM app_xml ax LEFT JOIN app_base ab ON ax.app_id = ab.app_id")
    print(f"With LEFT JOIN: {cursor.fetchone()[0]}")
    
    # Test 3: With WHERE xml IS NOT NULL
    cursor.execute("SELECT COUNT(*) FROM app_xml ax LEFT JOIN app_base ab ON ax.app_id = ab.app_id WHERE ax.xml IS NOT NULL")
    print(f"With WHERE xml IS NOT NULL: {cursor.fetchone()[0]}")
    
    # Test 4: Full condition but no OFFSET
    query = """
        SELECT COUNT(*) FROM app_xml ax 
        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
        WHERE ax.xml IS NOT NULL 
        AND DATALENGTH(ax.xml) > 100
        AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
        AND NOT EXISTS (SELECT 1 FROM processing_log pl WHERE pl.app_id = ax.app_id AND pl.status = 'failed')
    """
    try:
        cursor.execute(query)
        print(f"Full query without OFFSET: {cursor.fetchone()[0]}")
    except Exception as e:
        print(f"Error: {e}")
