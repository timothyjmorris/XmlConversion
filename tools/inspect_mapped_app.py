"""
Diagnostic helper: fetch a single app XML, run parser+mapper, and check campaign lookup rows.

Usage (PowerShell):
  python tools\inspect_mapped_app.py --server <server> --database <db> --app-id 311202

This script prints the mapped `app_pricing_cc` records for the app and queries
the target `campaign_cc` table to see whether referenced `campaign_num` values
exist in the target schema from the mapping contract (usually `sandbox`).
"""
import argparse
import json
import sys
import logging
from typing import List

import pyodbc

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.database.migration_engine import MigrationEngine


def build_conn_string(server: str, database: str, username: str = None, password: str = None, trusted: bool = True) -> str:
    server_name = server.replace('\\\\', '\\')
    if username and password:
        conn = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_name};DATABASE={database};"
            f"UID={username};PWD={password};Connection Timeout=30;Application Name=InspectMappedApp;"
            f"TrustServerCertificate=yes;Encrypt=no;MultipleActiveResultSets=True;Pooling=False;"
        )
    else:
        conn = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_name};DATABASE={database};"
            f"Trusted_Connection=yes;Connection Timeout=30;Application Name=InspectMappedApp;"
            f"TrustServerCertificate=yes;Encrypt=no;MultipleActiveResultSets=True;Pooling=False;"
        )
    return conn


def fetch_xml(conn, source_table: str, source_column: str, app_id: int) -> str:
    cursor = conn.cursor()
    sql = f"SELECT ax.[{source_column}] FROM [dbo].[{source_table}] AS ax WHERE ax.app_id = ?"
    cursor.execute(sql, app_id)
    row = cursor.fetchone()
    return row[0] if row else None


def check_campaigns_exist(conn, target_schema: str, campaign_nums: List[str]) -> List[str]:
    if not campaign_nums:
        return []
    cursor = conn.cursor()
    placeholders = ','.join('?' for _ in campaign_nums)
    sql = f"SELECT campaign_num FROM [{target_schema}].[campaign_cc] WHERE campaign_num IN ({placeholders})"
    cursor.execute(sql, *campaign_nums)
    rows = cursor.fetchall()
    return [r[0] for r in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--app-id', type=int, required=True)
    parser.add_argument('--username')
    parser.add_argument('--password')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    cfg = get_config_manager()
    mapping_contract = cfg.load_mapping_contract()
    source_table = mapping_contract.source_table
    source_column = mapping_contract.source_column
    target_schema = mapping_contract.target_schema or 'sandbox'

    conn_str = build_conn_string(args.server, args.database, args.username, args.password, trusted=not args.username)

    print(f"Using source: [dbo].[{source_table}].[{source_column}]  target schema: {target_schema}")

    try:
        mig = MigrationEngine(conn_str)
        with mig.get_connection() as conn:
            xml_content = fetch_xml(conn, source_table, source_column, args.app_id)
            if not xml_content:
                print(f"No XML found for app_id={args.app_id} in [dbo].[{source_table}]")
                return

            parser = XMLParser(mapping_contract=mapping_contract)
            xml_root = parser.parse_xml_stream(xml_content)
            xml_data = parser.extract_elements(xml_root)

            mapper = DataMapper(log_level='DEBUG')
            # Load the contract via config manager for passing to mapper
            contract = cfg.load_mapping_contract()
            mapped = mapper.apply_mapping_contract(xml_data, contract, xml_root=xml_root)

            app_pricing = mapped.get('app_pricing_cc', [])
            print(f"Mapped app_pricing_cc records for app_id={args.app_id}: \n{json.dumps(app_pricing, indent=2)}")

            # Extract campaign_num values (unique)
            campaign_nums = sorted({str(r.get('campaign_num')) for r in app_pricing if r.get('campaign_num') is not None})
            print(f"Referenced campaign_num values: {campaign_nums}")

            existing = check_campaigns_exist(conn, target_schema, campaign_nums)
            print(f"campaign_num rows present in [{target_schema}].campaign_cc: {existing}")

    except Exception as e:
        print(f"Error during inspection: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
