import pyodbc
from lxml import etree
import json
import argparse

def get_xml_value(server, database, app_id):
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT app_XML FROM app_xml_staging_rl WHERE app_id = ?", app_id)
            row = cursor.fetchone()
            if not row:
                print(f"No XML found for {app_id}")
                return

            xml_content = row[0]
            if not xml_content:
                print("XML content is empty")
                return

            root = etree.fromstring(xml_content.encode('utf-8'))
            
            # Check PR contact
            contacts = root.xpath("/Provenir/Request/CustData/IL_application/IL_contact[@ac_role_tp_c='PR']")
            if not contacts:
                print("No PR contact found")
                return

            for i, contact in enumerate(contacts):
                bd = contact.attrib.get('birth_date')
                print(f"Contact {i} (PR): birth_date = '{bd}' (Raw Attribute Value)")
                
                # Check for whitespace or special chars
                if bd:
                    print(f"  Debug: repr() = {repr(bd)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_xml_value("mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com", "MACDEVOperational", 132808)
