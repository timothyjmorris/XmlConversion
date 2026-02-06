"""
Check the actual XML structure for AUTHU contacts in app 141676
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lxml import etree
from xml_extractor.parsing.xml_parser import XMLParser
import pyodbc

# Get app 141676 XML
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com;'
    'DATABASE=MACDEVOperational;'
    'Trusted_Connection=yes;'
    'TrustServerCertificate=yes;'
    'Encrypt=no;'
)

cursor = conn.cursor()
cursor.execute('SELECT app_XML FROM migration.app_xml_staging WHERE app_id = 141676')
xml_content = cursor.fetchone()[0]
conn.close()

# Parse
parser = XMLParser()
root = parser.parse_xml_stream(xml_content)

# Find all contacts
contacts = root.xpath('.//contact')
print(f"Found {len(contacts)} contacts:")

for i, contact in enumerate(contacts):
    con_id = contact.get('con_id')
    ac_role = contact.get('ac_role_tp_c')
    first_name = contact.get('first_name')
    print(f"\n[{i}] con_id={con_id}, ac_role={ac_role}, first_name={first_name}")
    
    # Look for app_prod_bcard children
    bcard_elements = contact.xpath('.//app_prod_bcard')
    print(f"    app_prod_bcard elements: {len(bcard_elements)}")
    for j, bcard in enumerate(bcard_elements):
        issue_card_ind = bcard.get('issue_card_ind')
        print(f"      [{j}] issue_card_ind={issue_card_ind}")
    
    # Show direct children
    print(f"    Direct children: {[child.tag for child in contact]}")
