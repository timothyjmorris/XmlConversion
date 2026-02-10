import pyodbc
from lxml import etree

def inspect_ach_data(app_id):
    server = "mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com"
    database = "MACDEVOperational"
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            
            # Get Dest Data
            print(f"--- Destination Data (app_operational_cc) for {app_id} ---")
            cursor.execute("SELECT sc_ach_amount, sc_bank_aba, sc_bank_account_num FROM app_operational_cc WHERE app_id = ?", app_id)
            row = cursor.fetchone()
            if row:
                print(f"sc_ach_amount: {row.sc_ach_amount}")
                print(f"sc_bank_aba: {row.sc_bank_aba}")
                print(f"sc_bank_account_num: {row.sc_bank_account_num}")
            else:
                print("No destination data found.")

            # Get Source Data
            print(f"\n--- Source XML Inspection ---")
            cursor.execute("SELECT app_XML FROM app_xml WHERE app_id = ?", app_id)
            xml_row = cursor.fetchone()
            if not xml_row or not xml_row[0]:
                print("No source XML found.")
                return

            root = etree.fromstring(xml_row[0].encode('utf-8'))
            
            # Check Savings Acct
            # Note: use .// to search from root if needed, but path usually starts at /Provenir
            xpath = "//savings_acct[@acct_type='ACH']"
            nodes = root.xpath(xpath)
            
            if not nodes:
                print(f"No nodes found for xpath: {xpath}")
                # Try relaxed search
                all_savings = root.xpath("//savings_acct")
                if not all_savings:
                    print("No //savings_acct nodes found anywhere.")
                for s in all_savings:
                   print(f"Found savings_acct with acct_type='{s.attrib.get('acct_type')}'")
            else:
                for node in nodes:
                    print("Found ACH Node:")
                    print(f"  bank_aba: {node.attrib.get('bank_aba')}")
                    print(f"  account_num: {node.attrib.get('account_num')}")
                    print(f"  bank_name: {node.attrib.get('bank_name')}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_ach_data(325775)
