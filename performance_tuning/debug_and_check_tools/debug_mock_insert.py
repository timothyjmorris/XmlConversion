#!/usr/bin/env python3
"""Debug script to test mock XML insert with better error reporting."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from env_prep.generate_mock_xml import MockXMLGenerator
from xml_extractor.database.migration_engine import MigrationEngine
from tests.integration.test_database_connection import DatabaseConnectionTester

def main():
    try:
        print("🔧 Testing mock XML insertion with detailed debugging...\n")
        
        generator = MockXMLGenerator()
        
        # Generate one XML to inspect
        print("Step 1: Generate mock XML")
        xml = generator._generate_mock_xml(app_id=998888)
        print(f"   ✅ Generated XML (length: {len(xml)} chars)")
        
        # Save to file for inspection
        debug_file = Path(__file__).parent / "debug_mock.xml"
        debug_file.write_text(xml)
        print(f"   ✅ Saved to {debug_file}")
        
        # Check XML validity
        if not xml.startswith("<Provenir"):
            print(f"   ❌ XML doesn't start with <Provenir>")
            return 1
        if not xml.endswith("</Provenir>"):
            print(f"   ❌ XML doesn't end with </Provenir>")
            return 1
        print(f"   ✅ XML structure looks valid")
        
        # Now try manual insert
        print("\nStep 2: Manual insert test")
        
        db_tester = DatabaseConnectionTester()
        success, message = db_tester.test_connection()
        if not success:
            print(f"   ❌ DB connection failed: {message}")
            return 1
        
        conn_str = db_tester.build_connection_string()
        engine = MigrationEngine(conn_str)
        
        with engine.get_connection() as conn:
            cursor = conn.cursor()
            
            # Test IDENTITY_INSERT
            print("   Testing IDENTITY_INSERT ON...")
            cursor.execute("SET IDENTITY_INSERT app_xml ON")
            print("   ✅ IDENTITY_INSERT ON succeeded")
            
            # Test INSERT
            print("   Testing INSERT...")
            try:
                cursor.execute(
                    "INSERT INTO app_xml (app_id, xml) VALUES (?, ?)",
                    (998888, xml)
                )
                print("   ✅ INSERT succeeded")
            except Exception as e:
                print(f"   ❌ INSERT failed: {e}")
                return 1
            
            # Test IDENTITY_INSERT OFF
            print("   Testing IDENTITY_INSERT OFF...")
            cursor.execute("SET IDENTITY_INSERT app_xml OFF")
            print("   ✅ IDENTITY_INSERT OFF succeeded")
            
            # Test COMMIT
            print("   Testing COMMIT...")
            try:
                conn.commit()
                print("   ✅ COMMIT succeeded")
            except Exception as e:
                print(f"   ❌ COMMIT failed: {e}")
                return 1
        
        # Verify insert
        print("\nStep 3: Verify insert")
        with engine.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM app_xml WHERE app_id = 998888")
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"   ✅ Record found in database!")
            else:
                print(f"   ❌ Record NOT found in database!")
                return 1
        
        print("\n✅ All tests passed!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
