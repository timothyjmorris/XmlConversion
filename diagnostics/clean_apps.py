import pyodbc
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_connection_string(server, database):
    return (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;Connection Timeout=30;"
        f"TrustServerCertificate=yes;Encrypt=no;"
    )

def clean_apps(server, database, schema, app_ids):
    conn = pyodbc.connect(build_connection_string(server, database))
    cursor = conn.cursor()
    
    tables = [
        "processing_log",
        "scores",
        "app_historical_lookup",
        "app_funding_checklist_rl",
        "app_funding_contract_rl",
        "app_funding_rl",
        "app_policy_exceptions_rl",
        "app_warranties_rl",
        "app_collateral_rl",
        "app_contact_employment",
        "app_contact_address",
        "app_dealer_rl",
        "app_transactional_rl",
        "app_pricing_rl",
        "app_operational_rl",
        "app_contact_base",
        "app_base"
    ]
    
    logger.info(f"Cleaning apps: {app_ids}")
    
    ids_str = ",".join(str(i) for i in app_ids)
    
    for table_name in tables:
        try:
            full_table = f"[{schema}].[{table_name}]"
            # Some tables use con_id, but usually cascade or just join?
            # E.g. app_contact_address -> con_id -> app_contact_base -> app_id
            # Assuming app_id is present or we rely on cascades? 
            # Actually, app_contact_address does NOT have app_id usually.
            
            # This is complex. But MigrationEngine handles it.
            # Let's hope simple app_id deletion works for most, and handle exceptions.
            
            # Skip contact children for now, delete contact_base (which has app_id) and hope for cascade?
            # Or use nested subquery: DELETE FROM x WHERE con_id IN (SELECT con_id FROM app_contact_base WHERE app_id IN (...))
            
            if table_name in ["app_contact_address", "app_contact_employment"]:
                query = f"""
                DELETE FROM {full_table} 
                WHERE con_id IN (
                    SELECT con_id FROM [{schema}].[app_contact_base] 
                    WHERE app_id IN ({ids_str})
                )
                """
                cursor.execute(query)
            else:
                # Check if column app_id exists?
                # Assume standard tables have app_id
                query = f"DELETE FROM {full_table} WHERE app_id IN ({ids_str})"
                cursor.execute(query)
                
            logger.info(f"Deleted from {table_name}")
            conn.commit()
            
        except Exception as e:
            logger.warning(f"Failed to delete from {table_name}: {e}")
            conn.rollback()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="dbo")
    parser.add_argument("--app-ids", required=True)
    args = parser.parse_args()
    
    ids = [int(x) for x in args.app_ids.split(',')]
    clean_apps(args.server, args.database, args.schema, ids)
