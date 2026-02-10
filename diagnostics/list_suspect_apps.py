import pyodbc
import json
import argparse
import os

def build_connection_string(server, database):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=SuspectLister;"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

def scan_cc(conn, schema):
    print("--- Scanning CC (app_xml) ---")
    suspects = set()
    cursor = conn.cursor()
    
    # 1. Address Defaults
    try:
        query = f"""
            SELECT DISTINCT cb.app_id 
            FROM [{schema}].[app_contact_address] ca
            JOIN [{schema}].[app_contact_base] cb ON ca.con_id = cb.con_id
            WHERE (ca.city = 'MISSING' OR ca.state = 'XX' OR ca.zip = '00000')
            AND cb.app_id IN (SELECT app_id FROM app_xml)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Address Defaults: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking address: {e}")

    # 2. Contact Defaults
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_contact_base]
            WHERE (first_name = 'UNKNOWN' OR last_name = 'UNKNOWN' OR ssn = '000000000')
            AND app_id IN (SELECT app_id FROM app_xml)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Contact Defaults: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking contact: {e}")

    # 3. Date Defaults
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_contact_base]
            WHERE birth_date = '1900-01-01'
            AND app_id IN (SELECT app_id FROM app_xml)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Date Defaults: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking date: {e}")

    # 4. Marketing Defaults (CC Specific)
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_pricing_cc]
            WHERE marketing_segment = 'UNKNOWN'
            AND app_id IN (SELECT app_id FROM app_xml)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Marketing Defaults: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking marketing: {e}")

    # 5. ACH Mismatch (CC Specific)
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_operational_cc]
            WHERE sc_ach_amount > 0 AND sc_bank_account_type_enum IS NULL
            AND app_id IN (SELECT app_id FROM app_xml)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"ACH Mismatches: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking ACH: {e}")
        
    return sorted(list(suspects))

def scan_rl(conn, schema):
    print("--- Scanning RL (app_xml_staging_rl) ---")
    suspects = set()
    cursor = conn.cursor()
    source_table = "app_xml_staging_rl"
    
    # 1. Address Defaults
    try:
        query = f"""
            SELECT DISTINCT cb.app_id 
            FROM [{schema}].[app_contact_address] ca
            JOIN [{schema}].[app_contact_base] cb ON ca.con_id = cb.con_id
            WHERE (ca.city = 'MISSING' OR ca.state = 'XX' OR ca.zip = '00000')
            AND cb.app_id IN (SELECT app_id FROM {source_table})
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Address Defaults: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking address: {e}")

    # 2. Contact Defaults
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_contact_base]
            WHERE (first_name = 'UNKNOWN' OR last_name = 'UNKNOWN' OR ssn = '000000000')
            AND app_id IN (SELECT app_id FROM {source_table})
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Contact Defaults: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking contact: {e}")

    # 3. Date Defaults
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_contact_base]
            WHERE birth_date = '1900-01-01'
            AND app_id IN (SELECT app_id FROM {source_table})
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Date Defaults: {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking date: {e}")
        
    return sorted(list(suspects))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", default="localhost\\SQLEXPRESS")
    parser.add_argument("--database", default="XmlConversionDB")
    parser.add_argument("--schema", default="dbo")
    args = parser.parse_args()
    
    conn_str = build_connection_string(args.server, args.database)
    conn = pyodbc.connect(conn_str)
    
    cc_list = scan_cc(conn, args.schema)
    rl_list = scan_rl(conn, args.schema)
    
    # Save lists
    os.makedirs("docs/verification_logs", exist_ok=True)
    
    with open("docs/verification_logs/cc_suspect_apps.txt", "w") as f:
        f.write("\n".join(str(x) for x in cc_list))
    print(f"Saved {len(cc_list)} CC suspects to docs/verification_logs/cc_suspect_apps.txt")
    
    with open("docs/verification_logs/rl_suspect_apps.txt", "w") as f:
        f.write("\n".join(str(x) for x in rl_list))
    print(f"Saved {len(rl_list)} RL suspects to docs/verification_logs/rl_suspect_apps.txt")

if __name__ == "__main__":
    main()
