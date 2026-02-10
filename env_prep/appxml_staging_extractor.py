""""
Reconstruct and load minimal app_XML into staging table (namely avoids Reports, Journals, Audits, etc)
This is much faster than letting SQL & Python handle large XML processing
"""

import argparse
import json
import os
import time
import pyodbc

from datetime import datetime, timezone
from lxml import etree

# Configuration paths - contract and staging table are product-line driven
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.abspath(os.path.join(HERE, '..'))
CONFIG_DIR = os.path.join(PATH, 'config')
DB_CONFIG_PATH = os.path.join(CONFIG_DIR, 'database_config.json')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_connection_string(db_config):
    driver = db_config['database'].get('driver')
    server = db_config['database'].get('server')
    database = db_config['database'].get('database')
    trusted = db_config['database'].get('trusted_connection', True)
    timeout = db_config['database'].get('connection_timeout', 30)

    if trusted:
        template = db_config.get('connection_string_template_windows_auth')
        return template.format(driver=driver, server=server, database=database, connection_timeout=timeout)
    else:
        template = db_config.get('connection_string_template_sql_auth')
        username = db_config['database'].get('username')
        password = db_config['database'].get('password')
        return template.format(driver=driver, server=server, database=database, username=username, password=password, connection_timeout=timeout)


def parse_request_and_custdata(xml_text):
    """
    Parse XML and extract Request node attributes and CustData XML.
    
    Returns:
        dict with keys: app_id, process, status, priority, last_updated_by, cust_xml
        Returns None if parsing fails or required elements are missing.
    """
    try:
        root = etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
    except Exception:
        try:
            root = etree.fromstring(xml_text)
        except Exception:
            return None

    # Stop here if there's not even a Request node
    request_node = root.find('Request')
    if request_node is None:
        return None

    # Get attributes from <Request> node
    app_id = request_node.get('ID') or request_node.get('Id') or request_node.get('id')
    process = request_node.get('Process') or ''
    status = request_node.get('Status') or ''
    priority = request_node.get('Priority') or ''
    last_updated_by = request_node.get('LastUpdatedBy') or ''
    locked_by = request_node.get('LockedBy') or ''
    btcardtoken = request_node.get('btcardtoken') or ''
    btresponsecode = request_node.get('btresponsecode') or ''
    iovation_blackbox = request_node.get('iovation_blackbox') or ''
    use_alloy_service = request_node.get('useAlloyService') or ''
    trans = request_node.get('Trans') or ''

    # TODO: Extract additional attributes as needed: -------------------------------------------------
    # iovation_sessionid = request_node.get('iovation_sessionid') or ''
    # trigger_finicity = request_node.get('triggerFinicity') or ''    
    
    cust = request_node.find('CustData')
    if cust is None:
        return None

    try:
        cust_xml = etree.tostring(cust, encoding='unicode')
    except Exception:
        return None

    return {
        'app_id': app_id,
        'process': process,
        'status': status,
        'priority': priority,
        'last_updated_by': last_updated_by,
        "locked_by": locked_by,
        "btcardtoken": btcardtoken,
        "btresponsecode": btresponsecode,
        "iovation_blackbox": iovation_blackbox,
        "use_alloy_service": use_alloy_service,
        "trans": trans,
        'cust_xml': cust_xml
    }


def drop_staging_index(cursor, staging_table):
    drop_idx_sql = f"""IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_app_xml_staging_app_id' AND object_id = OBJECT_ID(N'{staging_table}'))
                        BEGIN
                            DROP INDEX IX_app_xml_staging_app_id ON {staging_table};
                        END
                    """
    cursor.execute(drop_idx_sql)
    try:
        cursor.commit()
    except Exception:
        pass


def create_staging_index(cursor, staging_table):
    create_idx_sql = f"CREATE INDEX IX_app_xml_staging_app_id ON {staging_table} (app_id) INCLUDE (app_xml);"
    cursor.execute(create_idx_sql)
    try:
        cursor.commit()
    except Exception:
        pass


def main(product_line, batch_size, limit, start_after, mod=None, rem=None, drop_index=False, recreate_index=False, metrics_path=None, source_table_override=None, source_column_override=None, force_source_ok=False):
    """
    Main staging extractor - product-line aware.
    
    Args:
        product_line: 'CC' or 'RL' - determines contract, staging table, and source application table
    """
    # Load product-line specific configuration
    db_config = load_json(DB_CONFIG_PATH)
    
    contract_filename = f'mapping_contract_{product_line.lower()}.json' if product_line == 'RL' else 'mapping_contract.json'
    contract_path = os.path.join(CONFIG_DIR, contract_filename)
    
    if not os.path.exists(contract_path):
        raise RuntimeError(f"Contract not found: {contract_path}")
    
    mapping = load_json(contract_path)
    
    # Extract contract-driven configuration
    target_schema = mapping.get('target_schema', 'migration')
    staging_table_name = mapping.get('source_table', f'app_xml_staging_{product_line.lower()}')
    source_application_table = mapping.get('source_application_table')  # 'application' or 'IL_application'
    
    if not source_application_table:
        raise RuntimeError(f"Contract {contract_filename} missing 'source_application_table' field")
    
    # Build fully qualified staging table name from contract
    staging_table = f'[{target_schema}].[{staging_table_name}]'
    
    # Source XML always comes from dbo.app_xml (not the staging table)
    source_table = source_table_override or 'app_xml'
    source_column = source_column_override or 'app_XML'
    
    # Safety: prevent reading from staging tables
    normalized_source = source_table.lower().replace('[', '').replace(']', '').replace('dbo.', '').strip()
    if 'staging' in normalized_source and not force_source_ok:
        raise RuntimeError(f"Refusing to read from staging table '{source_table}'. Use --source-table to point to original source (e.g. app_xml) or pass --force-source-ok to override.")

    conn_str = build_connection_string(db_config)
    
    print("="*80)
    print(f"XML STAGING EXTRACTOR - Product Line: {product_line}")
    print("="*80)
    print(f"Contract:              {contract_filename}")
    print(f"Source table:          [dbo].[{source_table}]")
    print(f"Source column:         {source_column}")
    print(f"Source app table:      [dbo].[{source_application_table}]")
    print(f"Staging table:         {staging_table}")
    print(f"Target schema:         {target_schema}")
    print(f"Connection:            {conn_str.split(';')[1]} (server info hidden)")
    print("="*80)

    connection = pyodbc.connect(conn_str, autocommit=False)
    cursor = connection.cursor()
    try:
        cursor.fast_executemany = True
    except Exception:
        pass
    
    # don't allow table creation in python outside of DEV, just bomb out bro
    # ensure_staging_table(cursor)

    if drop_index:
        print("Dropping staging nonclustered index before load (if present)")
        drop_staging_index(cursor, staging_table)

    processed_count = 0
    last_app_id = start_after or 0
    start_time = time.time()

    while True:
        select_clause = f"TOP ({batch_size})"
        where_parts = []
        if last_app_id:
            where_parts.append(f"s.app_id > {last_app_id}")

        if mod is not None:
            where_parts.append(f"(s.app_id % {mod}) = {rem}")

        # Product-line specific: Only include records with corresponding application in the correct table
        # CC uses [application], RL uses [IL_application] - this ensures distinct staging per product line
        where_parts.append(f"EXISTS (SELECT 1 FROM [dbo].[{source_application_table}] a WITH (NOLOCK) WHERE a.app_id = s.app_id)")

        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
        select_sql = f"SELECT {select_clause} s.app_id, s.[{source_column}] FROM [dbo].[{source_table}] s {where_clause} ORDER BY s.app_id"

        # print(f"SQL {select_sql}")

        now = time.time()
        cursor.execute(select_sql)
        rows = cursor.fetchall()
        if not rows:
            print("No more rows to process; exiting")
            break

        parsed_rows = []
        for app_id, xml_text in rows:
            parsed = parse_request_and_custdata(xml_text)
            
            # Skip rows where parsing failed or CustData is missing
            if parsed is None:
                continue

            # Extract values from dictionary
            app_id_attr = str(parsed['app_id']) if parsed['app_id'] is not None else ''
            process_attr = str(parsed['process'])
            status_attr = str(parsed['status'])
            priority_attr = str(parsed['priority'])
            last_updated_by_attr = str(parsed['last_updated_by'])
            locked_by_attr = str(parsed['locked_by'])
            btcardtoken_attr = str(parsed['btcardtoken'])
            btresponsecode_attr = str(parsed['btresponsecode'])
            iovation_blackbox_attr = str(parsed['iovation_blackbox'])
            use_alloy_service_attr = str(parsed['use_alloy_service'])
            trans_attr = str(parsed['trans'])


            minimal_xml = f"<Provenir><Request ID=\"{app_id_attr}\" Process=\"{process_attr}\" Status=\"{status_attr}\" Priority=\"{priority_attr}\" LastUpdatedBy=\"{last_updated_by_attr}\" LockedBy=\"{locked_by_attr}\" btcardtoken=\"{btcardtoken_attr}\" btresponsecode=\"{btresponsecode_attr}\" iovation_blackbox=\"{iovation_blackbox_attr}\" useAlloyService=\"{use_alloy_service_attr}\" Trans=\"{trans_attr}\">{parsed['cust_xml']}</Request></Provenir>"
            parsed_rows.append((parsed['app_id'], minimal_xml))
            last_app_id = parsed['app_id']
            processed_count += 1
            if limit and processed_count >= limit:
                break

        if parsed_rows:
            insert_sql = f"INSERT INTO {staging_table} (app_id, app_XML) VALUES (?, ?)"
            
            try:
                cursor.executemany(insert_sql, parsed_rows)
                connection.commit()
                print(f"Inserted {len(parsed_rows)} rows into staging (last_app_id={last_app_id})")
            except Exception as e:
                connection.rollback()
                print(f"Insert failed: {e}")
                raise

        batch_time = time.time() - now
        rate = len(parsed_rows) / batch_time if batch_time > 0 else 0
        print(f"XML Staging batch: fetched={len(rows)} inserted={len(parsed_rows)} batch_time={batch_time:.3f}s rate={rate:.1f} rows/sec")

        if limit and processed_count >= limit:
            print(f"Reached limit of {limit} processed rows; exiting")
            break

    total_duration = time.time() - start_time
    summary = {
        'processed': processed_count,
        'duration_seconds': total_duration,
        'rows_per_second': (processed_count / total_duration) if total_duration > 0 else 0,
        'finished_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    }
    print(f"Completed. Total # processed: {processed_count} rows in {total_duration:.1f}s ({summary['rows_per_second']:.1f} rows/sec)")

    if metrics_path:
        try:
            os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
            with open(metrics_path, 'w', encoding='utf-8') as mf:
                json.dump(summary, mf, indent=2)
            print(f"Wrote metrics to {metrics_path}")
        except Exception as e:
            print(f"Failed to write metrics: {e}")

    if recreate_index:
        print("Recreating staging index after load")
        try:
            create_staging_index(cursor, staging_table)
        except Exception as e:
            print(f"Failed to recreate index: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Product-line aware XML staging extractor - populates staging tables with minimal XML')
    parser.add_argument('--product-line', type=str, required=True,
                       choices=['CC', 'RL'],
                       help="Product line to process: 'CC' (Credit Card) or 'RL' (Rec Lending) - REQUIRED")
    parser.add_argument('--batch', type=int, default=1000, help='batch size to fetch from source table')
    parser.add_argument('--limit', type=int, default=0, help='maximum number of reduced rows to insert (0 = unlimited)')
    parser.add_argument('--start-after', type=int, default=0, help='start after this app_id (useful to resume)')
    parser.add_argument('--mod', type=int, default=0, help='partition modulus for worker (e.g., 8)')
    parser.add_argument('--rem', type=int, default=0, help='partition remainder for this worker (0..mod-1)')
    parser.add_argument('--drop-index', action='store_true', help='drop nonclustered staging index before load')
    parser.add_argument('--recreate-index', action='store_true', help='recreate staging index after load')
    parser.add_argument('--metrics', type=str, default='', help='path to write metrics JSON (e.g., metrics/appxml_1.json)')
    parser.add_argument('--source-table', type=str, default='', help='override source table (defaults to dbo.app_xml)')
    parser.add_argument('--source-column', type=str, default='', help='override source column (defaults to app_XML)')
    parser.add_argument('--force-source-ok', action='store_true', help='allow using the staging table as a source (dangerous)')

    args = parser.parse_args()
    mod = args.mod if args.mod and args.mod > 0 else None
    rem = args.rem if mod is not None else None
    metrics_path = args.metrics if args.metrics else None
    source_table = args.source_table if args.source_table else None
    source_column = args.source_column if args.source_column else None
    main(product_line=args.product_line, batch_size=args.batch, limit=args.limit or None, start_after=(args.start_after or 0), mod=mod, rem=rem, drop_index=args.drop_index, recreate_index=args.recreate_index, metrics_path=metrics_path, source_table_override=source_table, source_column_override=source_column, force_source_ok=args.force_source_ok)
