"""
Verify the sc_bank_account_type_enum mapping fix.

Tests that ["last_valid_pr_contact", "enum"] chain correctly extracts 
banking_account_type ("C" or "S") and maps it to enum values (70 or 71).
"""
from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
import pyodbc
from lxml import etree
import logging

# Only show INFO and above (not DEBUG)
logging.basicConfig(level=logging.INFO)

def main():
    config = get_config_manager()
    db_config = config.database_config

    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={db_config.server};'
        f'DATABASE={db_config.database};'
        f'Trusted_Connection=yes;'
        f'TrustServerCertificate=yes;'
        f'Encrypt=no'
    )
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Get 5 app_ids with banking_account_type in XML
    cursor.execute('''
        SELECT TOP 5 x.app_id
        FROM dbo.app_XML x
        INNER JOIN dbo.app_operational_cc o ON x.app_id = o.app_id
        WHERE o.sc_ach_amount > 0
    ''')
    
    print("Testing sc_bank_account_type_enum mapping fix")
    print("=" * 60)
    
    success_count = 0
    failure_count = 0
    
    for row in cursor.fetchall():
        app_id = row[0]
        
        # Get the XML
        cursor.execute('SELECT app_XML FROM dbo.app_XML WHERE app_id = ?', (app_id,))
        xml = cursor.fetchone()[0]
        tree = etree.fromstring(xml.encode() if isinstance(xml, str) else xml)
        
        # Get source value from XML
        pr_contacts = tree.xpath('.//contact[@ac_role_tp_c="PR"]')
        source_value = None
        if pr_contacts:
            # Get last valid PR contact's banking_account_type
            for contact in reversed(pr_contacts):
                if contact.get('con_id') and contact.get('ac_role_tp_c'):
                    source_value = contact.get('banking_account_type')
                    break
        
        # Run DataMapper
        mapper = DataMapper(log_level='WARNING')
        parser = XMLParser()
        xml_data = parser.extract_elements(tree)
        valid_contacts = mapper._extract_valid_contacts(xml_data)
        
        # Store XML root for extraction
        mapper._current_xml_root = tree
        
        # Get mapping contract
        contract = config.load_mapping_contract()
        
        # Apply mapping
        result = mapper.apply_mapping_contract(xml_data, contract, str(app_id), valid_contacts, xml_root=tree)
        
        # Check result
        mapped_value = None
        if 'app_operational_cc' in result and result['app_operational_cc']:
            mapped_value = result['app_operational_cc'][0].get('sc_bank_account_type_enum')
        
        # Determine expected enum value
        expected_value = None
        if source_value == 'C':
            expected_value = 70
        elif source_value == 'S':
            expected_value = 71
        
        status = "✓ PASS" if mapped_value == expected_value else "✗ FAIL"
        if mapped_value == expected_value:
            success_count += 1
        else:
            failure_count += 1
        
        print(f"app_id={app_id}: source='{source_value}' → mapped={mapped_value} (expected={expected_value}) {status}")
    
    print("=" * 60)
    print(f"Results: {success_count} passed, {failure_count} failed")
    
    conn.close()

if __name__ == "__main__":
    main()
