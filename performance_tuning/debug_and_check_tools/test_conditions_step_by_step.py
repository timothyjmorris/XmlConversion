#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
engine = MigrationEngine(db.build_connection_string())

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    queries = [
        ("Base", "SELECT COUNT(*) FROM app_xml ax LEFT JOIN app_base ab ON ax.app_id = ab.app_id WHERE ax.xml IS NOT NULL"),
        ("+ DATALENGTH", "SELECT COUNT(*) FROM app_xml ax LEFT JOIN app_base ab ON ax.app_id = ab.app_id WHERE ax.xml IS NOT NULL AND DATALENGTH(ax.xml) > 100"),
        ("+ app_base condition", "SELECT COUNT(*) FROM app_xml ax LEFT JOIN app_base ab ON ax.app_id = ab.app_id WHERE ax.xml IS NOT NULL AND DATALENGTH(ax.xml) > 100 AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))"),
        ("+ processing_log condition", """
            SELECT COUNT(*) FROM app_xml ax 
            LEFT JOIN app_base ab ON ax.app_id = ab.app_id
            WHERE ax.xml IS NOT NULL 
            AND DATALENGTH(ax.xml) > 100
            AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
            AND NOT EXISTS (SELECT 1 FROM processing_log pl WHERE pl.app_id = ax.app_id AND pl.status = 'failed')
        """),
    ]
    
    for desc, query in queries:
        try:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"{desc}: {count}")
        except Exception as e:
            print(f"{desc}: ERROR - {e}")
