#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
engine = MigrationEngine(db.build_connection_string())

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Test 1: Without OFFSET
    query1 = """
        SELECT COUNT(*) FROM app_xml ax 
        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
        WHERE ax.xml IS NOT NULL 
        AND DATALENGTH(ax.xml) > 100
        AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
        AND NOT EXISTS (SELECT 1 FROM processing_log pl WHERE pl.app_id = ax.app_id AND pl.status = 'failed')
    """
    cursor.execute(query1)
    print(f"Without OFFSET: {cursor.fetchone()[0]} records")
    
    # Test 2: With OFFSET 0 ROWS FETCH NEXT
    query2 = """
        SELECT COUNT(*) FROM app_xml ax 
        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
        WHERE ax.xml IS NOT NULL 
        AND DATALENGTH(ax.xml) > 100
        AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
        AND NOT EXISTS (SELECT 1 FROM processing_log pl WHERE pl.app_id = ax.app_id AND pl.status = 'failed')
        OFFSET 0 ROWS
        FETCH NEXT 1000 ROWS ONLY
    """
    cursor.execute(query2)
    print(f"With OFFSET 0: {cursor.fetchone()[0]} records")
    
    # Test 3: Select actual records with OFFSET
    query3 = """
        SELECT app_id FROM app_xml ax 
        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
        WHERE ax.xml IS NOT NULL 
        AND DATALENGTH(ax.xml) > 100
        AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
        AND NOT EXISTS (SELECT 1 FROM processing_log pl WHERE pl.app_id = ax.app_id AND pl.status = 'failed')
        ORDER BY app_id
        OFFSET 0 ROWS
        FETCH NEXT 1000 ROWS ONLY
    """
    cursor.execute(query3)
    rows = cursor.fetchall()
    print(f"Actual SELECT with OFFSET: {len(rows)} records")
    for row in rows[:5]:
        print(f"  {row[0]}")
