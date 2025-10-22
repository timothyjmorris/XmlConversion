import pyodbc
import xml.etree.ElementTree as ET

# Get XML for app_id 8 (207748)
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=XmlConversionDB;Trusted_Connection=yes;')
cursor = conn.cursor()
cursor.execute('SELECT xml FROM app_xml WHERE app_id = 8')
xml_content = cursor.fetchone()[0]
conn.close()

# Parse and check birth_date
root = ET.fromstring(xml_content)
contacts = root.findall('.//contact')

print(f"Found {len(contacts)} contacts in app_id 8 (207748):")
for i, contact in enumerate(contacts):
    con_id = contact.get('con_id')
    birth_date = contact.get('birth_date')
    print(f"  Contact {i+1} (con_id={con_id}): birth_date='{birth_date}'")
    print(f"    birth_date is empty: {birth_date == '' or birth_date is None}")