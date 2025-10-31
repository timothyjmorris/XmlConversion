#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
conn_str = db.build_connection_string()
engine = MigrationEngine(conn_str)

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    print("Test 1: Simple XML check")
    cursor.execute("SELECT COUNT(*) FROM app_xml WHERE xml IS NOT NULL")
    print(f"  XML IS NOT NULL: {cursor.fetchone()[0]}")
    
    print("\nTest 2: XML length check")
    cursor.execute("SELECT COUNT(*) FROM app_xml WHERE xml IS NOT NULL AND DATALENGTH(xml) > 100")
    print(f"  DATALENGTH > 100: {cursor.fetchone()[0]}")
    
    print("\nTest 3: app_base join")
    cursor.execute("SELECT COUNT(*) FROM app_xml ax LEFT JOIN app_base ab ON ax.app_id = ab.app_id WHERE ax.xml IS NOT NULL AND DATALENGTH(ax.xml) > 100")
    print(f"  With join: {cursor.fetchone()[0]}")
    
    print("\nTest 4: With app_base condition")
    cursor.execute("SELECT COUNT(*) FROM app_xml ax LEFT JOIN app_base ab ON ax.app_id = ab.app_id WHERE ax.xml IS NOT NULL AND DATALENGTH(ax.xml) > 100 AND ab.app_id IS NULL")
    print(f"  Where ab.app_id IS NULL: {cursor.fetchone()[0]}")
    
    print("\nTest 5: With app_base OR pricing_cc condition")
    cursor.execute("""
        SELECT COUNT(*) FROM app_xml ax 
        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
        WHERE ax.xml IS NOT NULL 
        AND DATALENGTH(ax.xml) > 100
        AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
    """)
    print(f"  With OR condition: {cursor.fetchone()[0]}")
    
    print("\nTest 6: Sample app_xml records")
    cursor.execute("SELECT TOP 5 app_id, DATALENGTH(xml) as len FROM app_xml")
    for row in cursor.fetchall():
        print(f"  app_id={row[0]}, len={row[1]}")
