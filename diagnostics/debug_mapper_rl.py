import json
import logging
from lxml import etree
import pyodbc
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.config.config_manager import get_config_manager

logging.basicConfig(level=logging.DEBUG)

def debug_mapper(server, database, app_id):
    # 1. Load Contract using ConfigManager
    config_manager = get_config_manager()
    contract = config_manager.load_mapping_contract("config/mapping_contract_rl.json")
    
    # Mapper takes optional config, not logger
    mapper = DataMapper()
    
    # 2. Get XML
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    # Check dbo first, then migration
    cursor.execute("SELECT app_XML FROM [dbo].[app_xml_staging_rl] WHERE app_id = ?", app_id)
    row = cursor.fetchone()
    if not row:
        # Try migration
        cursor.execute("SELECT app_XML FROM [migration].[app_xml_staging_rl] WHERE app_id = ?", app_id)
        row = cursor.fetchone()
        
    if not row:
        print("No XML found")
        return
        
    xml_str = row[0]
    xml_data = mapper.parse_xml(xml_str)
    
    # 3. Apply Mapping
    # Note: contract.target_schema might be 'migration', we can override to test mapping logic
    records = mapper.apply_mapping_contract(xml_data, contract, app_id=str(app_id))
    
    # 4. Filter for Scores
    score_records = [r for r in records if r.get('score_identifier') in ['V4P', 'V4S']]
    print(f"--- Mapped Records for App {app_id} ---")
    print(score_records)
    
    # Check all output
    print("--- All Scores ---")
    all_scores = [r for r in records if 'score' in r]
    print(all_scores)

if __name__ == "__main__":
    debug_mapper("mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com", "MACDEVOperational", 173413)
