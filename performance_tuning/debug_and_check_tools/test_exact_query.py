#!/usr/bin/env python3
from tests.integration.test_database_connection import DatabaseConnectionTester
from xml_extractor.database.migration_engine import MigrationEngine

db = DatabaseConnectionTester()
conn_str = db.build_connection_string()
engine = MigrationEngine(conn_str)

with engine.get_connection() as conn:
    cursor = conn.cursor()
    
    # Run EXACTLY as production_processor does it
    limit = 1000
    offset = 0
    
    base_conditions = """
        WHERE ax.xml IS NOT NULL 
        AND DATALENGTH(ax.xml) > 100
        AND (ab.app_id IS NULL OR NOT EXISTS (SELECT 1 FROM app_pricing_cc apc WHERE apc.app_id = ax.app_id))
    """
    
    base_conditions += """
        AND NOT EXISTS (
            SELECT 1 FROM processing_log pl 
            WHERE pl.app_id = ax.app_id 
            AND pl.status = 'failed'
        )
    """
    
    query = f"""
        SELECT ax.app_id, ax.xml 
        FROM app_xml ax
        LEFT JOIN app_base ab ON ax.app_id = ab.app_id
        {base_conditions}
        ORDER BY ax.app_id
        OFFSET {offset} ROWS
        FETCH NEXT {limit} ROWS ONLY
    """
    
    print("Query:")
    print(query)
    print("\nExecuting...")
    
    cursor.execute(query)
    rows = cursor.fetchall()
    print(f"Result: {len(rows)} records")
