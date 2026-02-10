import pyodbc
import json
import argparse
import os

def build_connection_string(server, database):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;Application Name=SuspectGenerator;"
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

    # 4. Marketing Defaults
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_pricing_cc]
            WHERE marketing_segment = 'UNKNOWN'
            AND app_id IN (SELECT app_id FROM app_xml)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Marketing Defaults ('UNKNOWN'): {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking marketing: {e}")

    # 5. Population Assignment Defaults (229)
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_pricing_cc]
            WHERE population_assignment_enum = 229
            AND app_id IN (SELECT app_id FROM app_xml)
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Population Assignment Defaults (229): {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking population: {e}")

    # 6. ACH Mismatch
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
    
    # 1. Address
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

    # 2. Contact
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

    # 3. Date
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
        
    # 4. Collateral Type Defaults (423)
    try:
        query = f"""
            SELECT DISTINCT app_id 
            FROM [{schema}].[app_collateral_rl]
            WHERE collateral_type_enum = 423
            AND app_id IN (SELECT app_id FROM {source_table})
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Collateral Defaults (423): {len(rows)}")
        suspects.update(row[0] for row in rows)
    except Exception as e:
        print(f"Error checking collateral: {e}")
        
    return sorted(list(suspects))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="dbo")
    args = parser.parse_args()
    
    conn_str = build_connection_string(args.server, args.database)
    conn = pyodbc.connect(conn_str)
    
    cc_list = scan_cc(conn, args.schema)
    rl_list = scan_rl(conn, args.schema)
    
    # Save lists
    out_dir = "diagnostics/data_audit/logs"
    os.makedirs(out_dir, exist_ok=True)
    
    with open(f"{out_dir}/cc_suspect_apps.txt", "w") as f:
        f.write("\n".join(str(x) for x in cc_list))
    print(f"Saved {len(cc_list)} CC suspects to {out_dir}/cc_suspect_apps.txt")
    
    with open(f"{out_dir}/rl_suspect_apps.txt", "w") as f:
        f.write("\n".join(str(x) for x in rl_list))
    print(f"Saved {len(rl_list)} RL suspects to {out_dir}/rl_suspect_apps.txt")

if __name__ == "__main__":
    main()
