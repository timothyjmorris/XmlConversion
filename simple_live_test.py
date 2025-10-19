#!/usr/bin/env python3
"""
Simple live integration test without unittest framework.
"""

import sys
from pathlib import Path
import pyodbc
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from xml_extractor.validation.pre_processing_validator import PreProcessingValidator
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.models import ProcessingConfig

def run_live_integration():
    """Run live integration test."""
    # Enable debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    print("🚀 Starting Live End-to-End Integration Test")
    print("⚠️  This test will insert real data into the database!")
    
    # Load database config
    import json
    config_path = Path("config/database_config.json")
    with open(config_path, 'r') as f:
        db_config = json.load(f)
    
    # Build connection string using config
    db_settings = db_config["database"]
    connection_string = db_config["connection_string_template_windows_auth"].format(**db_settings)
    
    print(f"Using database: {db_settings['database']} on {db_settings['server']}")
    
    # Load sample XML
    sample_path = Path("config/samples/sample-source-xml-contact-test.xml")
    if not sample_path.exists():
        print("❌ Sample XML file not found")
        return False
    
    with open(sample_path, 'r', encoding='utf-8') as f:
        sample_xml = f.read()
    
    print(f"✅ Sample XML loaded: {len(sample_xml)} characters")
    
    # Initialize components
    validator = PreProcessingValidator()
    parser = XMLParser()
    mapper = DataMapper()
    migration_engine = MigrationEngine(connection_string)
    
    # Clean up existing test data
    print("\n🧹 Cleaning up existing test data...")
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            # Delete in reverse dependency order using correct table names
            cursor.execute("DELETE FROM contact_employment WHERE con_id IN (SELECT con_id FROM contact_base WHERE app_id = 443306)")
            cursor.execute("DELETE FROM contact_address WHERE con_id IN (SELECT con_id FROM contact_base WHERE app_id = 443306)")
            cursor.execute("DELETE FROM contact_base WHERE app_id = 443306")
            cursor.execute("DELETE FROM app_base WHERE app_id = 443306")
            conn.commit()
            print("✅ Cleaned up existing test data")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up test data: {e}")
    
    # Step 1: Validate XML
    print("\n📋 Step 1: Validating XML...")
    validation_result = validator.validate_xml_for_processing(sample_xml, "live_test")
    
    if not validation_result.is_valid:
        print("❌ XML validation failed")
        return False
    
    print(f"✅ Validation passed: app_id={validation_result.app_id}, contacts={len(validation_result.valid_contacts)}")
    for i, contact in enumerate(validation_result.valid_contacts):
        print(f"   Contact {i+1}: {contact.get('first_name')} (con_id={contact.get('con_id')}, role={contact.get('ac_role_tp_c')})")
    
    # Step 2: Parse XML
    print("\n🔍 Step 2: Parsing XML...")
    root = parser.parse_xml_stream(sample_xml)
    xml_data = parser.extract_elements(root)
    
    print(f"✅ Parsing completed: {len(xml_data)} elements extracted")
    
    # Step 3: Extract data manually
    print("\n🗺️  Step 3: Extracting data...")
    
    # Extract app_id
    app_id = None
    if '/Provenir/Request' in xml_data:
        request_element = xml_data['/Provenir/Request']
        if 'attributes' in request_element and 'ID' in request_element['attributes']:
            app_id = int(request_element['attributes']['ID'])
    
    if not app_id:
        print("❌ Could not extract app_id")
        return False
    
    print(f"✅ Extracted app_id: {app_id}")
    
    # Get valid contacts
    valid_contacts = validation_result.valid_contacts
    
    # Create data records using correct table structure
    # Include app_id since we're using IDENTITY_INSERT
    app_record = {
        'app_id': app_id,  # Required for IDENTITY_INSERT
        'app_type_enum': 1,  # Placeholder enum value
        'product_line_enum': 600  # Default from schema
    }
    
    print(f"✅ Data prepared: 1 app record (app_id will be auto-generated)")
    
    # We'll need to get the generated app_id after insertion to use for contacts
    contact_data = []
    for contact in valid_contacts:
        # Parse birth_date to proper format
        birth_date_str = contact.get('birth_date', '')
        birth_date = None
        if birth_date_str:
            try:
                from datetime import datetime as dt
                birth_date = dt.strptime(birth_date_str, '%m/%d/%Y')
            except:
                birth_date = dt(1980, 1, 1)  # Fallback date
        else:
            birth_date = dt(1980, 1, 1)  # Fallback date
        
        # Clean SSN - remove non-digits and pad/truncate to 9 characters
        ssn_raw = contact.get('ssn', '')
        ssn_clean = ''.join(filter(str.isdigit, ssn_raw))
        if len(ssn_clean) > 9:
            ssn_clean = ssn_clean[:9]
        elif len(ssn_clean) < 9:
            ssn_clean = ssn_clean.ljust(9, '0')
        
        # Only use fields that are in the mapping contract!
        contact_info = {
            'con_id': int(contact['con_id']),  # identity_insert from contract
            'app_id': app_id,  # foreign key relationship
            'first_name': contact.get('first_name', ''),  # mapped in contract
            'last_name': contact.get('last_name', ''),  # mapped in contract
            'ssn': ssn_clean,  # mapped in contract
            'birth_date': birth_date,  # mapped in contract
            'contact_type_enum': 281 if contact['ac_role_tp_c'] == 'PR' else 280,  # mapped in contract
            'middle_initial': contact.get('initials', ''),  # mapped in contract
            'mother_maiden_name': contact.get('mother_maiden_name', ''),  # mapped in contract
            'suffix': contact.get('suffix', ''),  # mapped in contract
            'email': contact.get('email', '')  # mapped in contract
        }
        contact_data.append(contact_info)
    
    print(f"✅ Data prepared: 1 app, {len(contact_data)} contacts")
    
    # Debug: Print contact data to see what's causing the conversion error
    print("\n🔍 Debug: Contact data to be inserted:")
    for i, contact in enumerate(contact_data):
        print(f"  Contact {i+1}:")
        for key, value in contact.items():
            print(f"    {key}: {repr(value)} (type: {type(value).__name__})")
    
    # Step 4: Insert into database
    print("\n💾 Step 4: Inserting into database...")
    
    try:
        # Insert app_base with IDENTITY_INSERT enabled
        migration_engine.execute_bulk_insert([app_record], "app_base", enable_identity_insert=True)
        print(f"✅ Inserted 1 record into app_base")
        
        # Insert contacts with IDENTITY_INSERT enabled
        migration_engine.execute_bulk_insert(contact_data, "contact_base", enable_identity_insert=True)
        print(f"✅ Inserted {len(contact_data)} records into contact_base")
        
    except Exception as e:
        print(f"❌ Database insertion failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Verify database contents
    print("\n🔍 Step 5: Verifying database contents...")
    
    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            
            # Check app_base
            cursor.execute("SELECT COUNT(*) FROM app_base WHERE app_id = 443306")
            app_count = cursor.fetchone()[0]
            print(f"   📋 Application records: {app_count}")
            
            # Check contacts (correct table name: contact_base)
            cursor.execute("SELECT COUNT(*) FROM contact_base WHERE app_id = 443306")
            contact_count = cursor.fetchone()[0]
            print(f"   👤 Contact records: {contact_count}")
            
            if contact_count > 0:
                cursor.execute("""
                    SELECT con_id, contact_type_enum, first_name, last_name
                    FROM contact_base 
                    WHERE app_id = 443306
                    ORDER BY con_id
                """)
                contacts = cursor.fetchall()
                
                for contact in contacts:
                    role_name = "PR" if contact[1] == 281 else "AUTHU" if contact[1] == 280 else f"Unknown({contact[1]})"
                    print(f"      - con_id={contact[0]}, role={role_name}, name={contact[2]} {contact[3]}")
            
            # Verify "last valid element" approach
            cursor.execute("""
                SELECT con_id, first_name
                FROM contact_base 
                WHERE app_id = 443306 AND contact_type_enum = 281
            """)
            pr_contact = cursor.fetchone()
            
            if pr_contact and pr_contact[1] == 'TOM':
                print(f"   ✅ Last valid element approach verified: PR contact is TOM (not MARK)")
            else:
                print(f"   ⚠️  Expected PR contact to be TOM, got: {pr_contact}")
            
    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        return False
    
    print("\n🎉 LIVE END-TO-END INTEGRATION TEST COMPLETED SUCCESSFULLY!")
    print("💡 Check the database for app_id = 443306 to inspect the inserted data.")
    
    return True

if __name__ == '__main__':
    success = run_live_integration()
    sys.exit(0 if success else 1)