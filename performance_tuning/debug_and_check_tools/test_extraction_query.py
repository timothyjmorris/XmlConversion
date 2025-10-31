#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
conn_str = db.build_connection_string()
engine = MigrationEngine(conn_str)

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Run the exact query from production_processor.py
    query = """
        SELECT ax.app_id, DATALENGTH(ax.xml) as xml_length
        FROM app_xml ax
        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
        WHERE ax.xml IS NOT NULL 
        AND DATALENGTH(ax.xml) > 100
        AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
        AND NOT EXISTS (
            SELECT 1 FROM processing_log pl 
            WHERE pl.app_id = ax.app_id 
            AND pl.status = 'failed'
        )
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    print(f"Query returned {len(rows)} records")
    for row in rows[:10]:
        print(f"  app_id={row[0]}, xml_length={row[1]}")
