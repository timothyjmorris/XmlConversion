#!/usr/bin/env python3
"""Quick test to verify mock XML generation and insertion."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from env_prep.generate_mock_xml import MockXMLGenerator

try:
    print("🔧 Testing mock XML generation...\n")
    
    generator = MockXMLGenerator()
    
    # Generate just one mock XML to inspect
    print("Generating single mock XML...")
    xml = generator._generate_mock_xml(app_id=999999)
    
    print(f"\n📄 Generated XML (first 1000 chars):")
    print(xml[:1000])
    print("\n...")
    print(f"\n📄 Generated XML (last 500 chars):")
    print(xml[-500:])
    
    # Check if it looks valid
    if xml.startswith("<Provenir"):
        print("\n✅ XML starts correctly with <Provenir>")
    else:
        print("\n❌ XML doesn't start with <Provenir>")
    
    if xml.endswith("</Provenir>"):
        print("✅ XML ends correctly with </Provenir>")
    else:
        print("❌ XML doesn't end with </Provenir>")
    
    # Try to insert one
    print("\n🔄 Attempting to insert one mock XML...")
    result = generator.generate_and_insert_mock_xmls(count=1, start_app_id=999999)
    print(f"Inserted: {result} records")
    
    if result > 0:
        print("✅ Insertion successful!")
    else:
        print("❌ Insertion failed!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
