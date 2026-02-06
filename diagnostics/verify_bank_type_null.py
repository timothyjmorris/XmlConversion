"""
Verify NULL handling for sc_bank_account_type_enum when source has no banking_account_type.
"""
from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
import pyodbc
from lxml import etree

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

# Get app_ids WITHOUT banking_account_type (no ACH activity)
cursor.execute('''
    SELECT TOP 3 x.app_id
    FROM dbo.app_XML x
    WHERE NOT EXISTS (
        SELECT 1 FROM dbo.app_operational_cc o WHERE o.app_id = x.app_id AND o.sc_ach_amount > 0
    )
''')

print('Testing NULL handling (no banking_account_type in source):')
for row in cursor.fetchall():
    app_id = row[0]
    cursor.execute('SELECT app_XML FROM dbo.app_XML WHERE app_id = ?', (app_id,))
    xml = cursor.fetchone()[0]
    tree = etree.fromstring(xml.encode() if isinstance(xml, str) else xml)
    
    pr_contacts = tree.xpath('.//contact[@ac_role_tp_c="PR"]')
    source_value = None
    if pr_contacts:
        for contact in reversed(pr_contacts):
            if contact.get('con_id') and contact.get('ac_role_tp_c'):
                source_value = contact.get('banking_account_type')
                break
    
    mapper = DataMapper(log_level='ERROR')
    parser = XMLParser()
    xml_data = parser.extract_elements(tree)
    valid_contacts = mapper._extract_valid_contacts(xml_data)
    mapper._current_xml_root = tree
    contract = config.load_mapping_contract()
    result = mapper.apply_mapping_contract(xml_data, contract, str(app_id), valid_contacts, xml_root=tree)
    
    mapped_value = None
    if 'app_operational_cc' in result and result['app_operational_cc']:
        mapped_value = result['app_operational_cc'][0].get('sc_bank_account_type_enum')
    
    print(f'  app_id={app_id}: source={repr(source_value)} -> mapped={mapped_value}')

conn.close()
