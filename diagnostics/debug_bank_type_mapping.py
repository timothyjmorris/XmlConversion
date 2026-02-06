"""
Debug why sc_bank_account_type_enum is not being populated.
"""
from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.mapping.data_mapper import DataMapper
import pyodbc
from lxml import etree
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

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

    # Get an app_id with banking_account_type
    cursor.execute('SELECT TOP 1 app_id FROM dbo.app_operational_cc WHERE sc_ach_amount > 0')
    app_id = cursor.fetchone()[0]
    print(f'\n=== Testing app_id {app_id} ===\n')
    
    # Get the XML
    cursor.execute('SELECT app_XML FROM dbo.app_XML WHERE app_id = ?', (app_id,))
    xml = cursor.fetchone()[0]
    tree = etree.fromstring(xml.encode() if isinstance(xml, str) else xml)
    
    # Show what's in the XML for the PR contact
    for contact in tree.xpath('.//contact[@ac_role_tp_c="PR"]'):
        print(f'PR Contact con_id={contact.get("con_id")}:')
        print(f'  banking_account_type = "{contact.get("banking_account_type")}"')
        print(f'  secure_ach_amount = "{contact.get("secure_ach_amount")}"')
        print(f'  banking_aba_number = "{contact.get("banking_aba_number")}"')
        print(f'  banking_account_number = "{contact.get("banking_account_number")}"')
    
    # Now run through DataMapper and see what it extracts
    print('\n=== Running DataMapper ===\n')
    mapper = DataMapper(log_level='DEBUG')
    result = mapper.map_application(tree, str(app_id))
    
    # Check the app_operational_cc record
    if 'app_operational_cc' in result and result['app_operational_cc']:
        rec = result['app_operational_cc'][0]
        print('\n=== Mapped app_operational_cc record ===')
        for key in ['app_id', 'sc_bank_account_type_enum', 'sc_ach_amount', 'sc_bank_aba', 'sc_bank_account_num']:
            print(f'  {key}: {rec.get(key, "NOT IN RECORD")}')
    else:
        print('No app_operational_cc record generated!')

if __name__ == "__main__":
    main()
