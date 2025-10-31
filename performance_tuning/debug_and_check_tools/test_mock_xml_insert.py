#!/usr/bin/env python3
"""Quick test to see if mock XML inserts successfully."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from env_prep.generate_mock_xml import MockXMLGenerator

def main():
    try:
        generator = MockXMLGenerator()
        
        # Try to generate and insert just 1 mock XML
        print("Attempting to insert 1 mock XML record...")
        result = generator.generate_and_insert_mock_xmls(1, start_app_id=900000)
        
        if result > 0:
            print(f"✅ Success! Inserted {result} record(s)")
            
            # Now check if we can query it back
            from xml_extractor.database.migration_engine import MigrationEngine
            from tests.integration.test_database_connection import DatabaseConnectionTester
            
            db_tester = DatabaseConnectionTester()
            success, message = db_tester.test_connection()
            conn_str = db_tester.build_connection_string()
            engine = MigrationEngine(conn_str)
            
            with engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM app_xml WHERE app_id >= 900000")
                count = cursor.fetchone()[0]
                print(f"✅ Query verification: Found {count} record(s) with app_id >= 900000")
                
                # Get the XML
                cursor.execute("SELECT app_id, LEN(xml) as xml_length FROM app_xml WHERE app_id >= 900000")
                for row in cursor.fetchall():
                    print(f"   app_id={row[0]}, xml_length={row[1]}")
        else:
            print("❌ Insert failed - returned 0")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
