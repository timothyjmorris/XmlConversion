"""
Check source XML to see if banking_account_type has data that should be mapping.
"""
from xml_extractor.config.config_manager import get_config_manager
import pyodbc
from lxml import etree

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

    # Get some app_ids where sc_ach_amount > 0
    cursor.execute('SELECT TOP 10 app_id FROM dbo.app_operational_cc WHERE sc_ach_amount > 0')
    app_ids = [r[0] for r in cursor.fetchall()]
    print(f'Checking app_ids with sc_ach_amount > 0: {app_ids}\n')

    found_with_data = 0
    found_empty = 0
    
    for app_id in app_ids:
        cursor.execute('SELECT app_XML FROM dbo.app_XML WHERE app_id = ?', (app_id,))
        row = cursor.fetchone()
        if row:
            xml = row[0]
            tree = etree.fromstring(xml.encode() if isinstance(xml, str) else xml)
            
            # Find banking_account_type in the XML
            for contact in tree.xpath('.//contact'):
                con_id = contact.get('con_id', '?')
                ac_role = contact.get('ac_role_tp_c', '?')
                bank_type = contact.get('banking_account_type')
                ach_amt = contact.get('secure_ach_amount')
                
                if bank_type is not None or ach_amt is not None:
                    has_data = bank_type and bank_type.strip()
                    if has_data:
                        found_with_data += 1
                    else:
                        found_empty += 1
                    print(f'app_id={app_id}, con_id={con_id}, ac_role={ac_role}:')
                    print(f'  banking_account_type="{bank_type}"')  
                    print(f'  secure_ach_amount="{ach_amt}"')
                    print()

    print(f'\n=== Summary ===')
    print(f'Contacts with non-empty banking_account_type: {found_with_data}')
    print(f'Contacts with empty/null banking_account_type: {found_empty}')
    
    # Now let's check across ALL records with ach_amount > 0
    print(f'\n=== Broader check: All apps with sc_ach_amount > 0 ===')
    cursor.execute('''
        SELECT TOP 100 o.app_id, o.sc_ach_amount 
        FROM dbo.app_operational_cc o 
        WHERE o.sc_ach_amount > 0
    ''')
    apps_to_check = cursor.fetchall()
    
    has_bank_type = 0
    no_bank_type = 0
    
    for app_id, ach_amt in apps_to_check:
        cursor.execute('SELECT app_XML FROM dbo.app_XML WHERE app_id = ?', (app_id,))
        row = cursor.fetchone()
        if row:
            xml = row[0]
            tree = etree.fromstring(xml.encode() if isinstance(xml, str) else xml)
            
            # Check all contacts for banking_account_type
            for contact in tree.xpath('.//contact[@ac_role_tp_c="PR"]'):
                bank_type = contact.get('banking_account_type', '')
                if bank_type and bank_type.strip():
                    has_bank_type += 1
                else:
                    no_bank_type += 1
                break  # Just check PR contact
    
    print(f'PR contacts WITH banking_account_type: {has_bank_type}')
    print(f'PR contacts WITHOUT banking_account_type: {no_bank_type}')

if __name__ == "__main__":
    main()
