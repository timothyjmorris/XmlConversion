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

# Hard-coded mapping_contract & app_xml_staging table, that's ok
HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.abspath(os.path.join(HERE, '..'))
CONFIG_DIR = os.path.join(PATH, 'config')
DB_CONFIG_PATH = os.path.join(CONFIG_DIR, 'database_config.json')
MAPPING_CONTRACT_PATH = os.path.join(CONFIG_DIR, 'mapping_contract.json')
STAGING_TABLE = '[dbo].[app_xml_staging]'


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
    try:
        root = etree.fromstring(xml_text.encode('utf-8') if isinstance(xml_text, str) else xml_text)
    except Exception:
        try:
            root = etree.fromstring(xml_text)
        except Exception:
            return None, None

    req = root.find('Request')
    if req is None:
        return None, None

    """
    Also need to extract attributes from <Request>
        Process
        Status
        Priority
        LastUpdatedBy
    
    Check
        iovation_sessionid
        triggerFinicity
        triggerNova
        btcardtoken
        btresponsecode

    # UH-OH, do we need to map and capture <Provenir> attributes for applications still processing?
        a1_date
    """


    req_id = req.get('ID') or req.get('Id') or req.get('id')
    cust = req.find('CustData')
    if cust is None:
        return req_id, None

    try:
        cust_xml = etree.tostring(cust, encoding='unicode')
    except Exception:
        cust_xml = None

    return req_id, cust_xml


def drop_staging_index(cursor):
    drop_sql = f"""IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_app_xml_staging_app_id' AND object_id = OBJECT_ID(N'{STAGING_TABLE}'))
                    BEGIN
                        DROP INDEX IX_app_xml_staging_app_id ON {STAGING_TABLE};
                    END
                    """
    cursor.execute(drop_sql)
    try:
        cursor.commit()
    except Exception:
        pass


def create_staging_index(cursor):
    create_sql = f"CREATE INDEX IX_app_xml_staging_app_id ON {STAGING_TABLE} (app_id) INCLUDE (app_xml);"
    cursor.execute(create_sql)
    try:
        cursor.commit()
    except Exception:
        pass


def main(batch_size, limit, start_after, mod=None, rem=None, drop_index=False, recreate_index=False, metrics_path=None, source_table_override=None, source_column_override=None, force_source_ok=False):
    db_config = load_json(DB_CONFIG_PATH)
    mapping = load_json(MAPPING_CONTRACT_PATH)

    source_table = source_table_override or mapping.get('source_table', 'app_xml')
    source_column = source_column_override or mapping.get('source_column', 'app_XML')

    # Safety: avoid reading from the staging table and inserting back into it accidentally.
    normalized_source = source_table.lower().replace('[', '').replace(']', '').replace('dbo.', '').strip()
    if normalized_source == 'app_xml_staging' and not force_source_ok:
        raise RuntimeError("Refusing to read from 'app_xml_staging' as source. Use --source-table to point to original source (e.g. app_xml) or pass --force-source-ok to override.")

    conn_str = build_connection_string(db_config)
    print(f"Using connection: {conn_str.split(';')[1]} (server info hidden)")

    connection = pyodbc.connect(conn_str, autocommit=False)
    cursor = connection.cursor()
    try:
        cursor.fast_executemany = True
    except Exception:
        pass
    
    # don't allow table creation, just bomb out bro
    # ensure_staging_table(cursor)

    if drop_index:
        print("Dropping staging nonclustered index before load (if present)")
        drop_staging_index(cursor)

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

        # Exclude orphaned XML - make sure it has a corresponding application using EXISTS (uses indexes and avoids UNION scans)
        where_parts.append("(EXISTS (SELECT 1 FROM [application] a WITH (NOLOCK) WHERE a.app_id = s.app_id) OR EXISTS (SELECT 1 FROM IL_application ia WITH (NOLOCK) WHERE ia.app_id = s.app_id))")

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
            req_id, cust_xml = parse_request_and_custdata(xml_text)
            if cust_xml is None:
                continue

            req_id_attr = str(req_id) if req_id is not None else ''
            minimal_xml = f"<Provenir><Request ID=\"{req_id_attr}\">{cust_xml}</Request></Provenir>"
            parsed_rows.append((app_id, minimal_xml))
            last_app_id = app_id
            processed_count += 1
            if limit and processed_count >= limit:
                break

        if parsed_rows:
            insert_sql = f"INSERT INTO {STAGING_TABLE} (app_id, app_XML) VALUES (?, ?)"
            
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
            create_staging_index(cursor)
        except Exception as e:
            print(f"Failed to recreate index: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Stage app_XML extractor to populate app_xml_staging')
    parser.add_argument('--batch', type=int, default=1000, help='batch size to fetch from source table')
    parser.add_argument('--limit', type=int, default=0, help='maximum number of reduced rows to insert (0 = unlimited)')
    parser.add_argument('--start-after', type=int, default=0, help='start after this app_id (useful to resume)')
    parser.add_argument('--mod', type=int, default=0, help='partition modulus for worker (e.g., 8)')
    parser.add_argument('--rem', type=int, default=0, help='partition remainder for this worker (0..mod-1)')
    parser.add_argument('--drop-index', action='store_true', help='drop nonclustered staging index before load')
    parser.add_argument('--recreate-index', action='store_true', help='recreate staging index after load')
    parser.add_argument('--metrics', type=str, default='', help='path to write metrics JSON (e.g., metrics/appxml_1.json)')
    parser.add_argument('--source-table', type=str, default='', help='override source table (defaults to mapping_contract source_table)')
    parser.add_argument('--source-column', type=str, default='', help='override source column (defaults to mapping_contract source_column)')
    parser.add_argument('--force-source-ok', action='store_true', help='allow using the staging table as a source (dangerous)')

    args = parser.parse_args()
    mod = args.mod if args.mod and args.mod > 0 else None
    rem = args.rem if mod is not None else None
    metrics_path = args.metrics if args.metrics else None
    source_table = args.source_table if args.source_table else None
    source_column = args.source_column if args.source_column else None
    main(batch_size=args.batch, limit=args.limit or None, start_after=(args.start_after or 0), mod=mod, rem=rem, drop_index=args.drop_index, recreate_index=args.recreate_index, metrics_path=metrics_path, source_table_override=source_table, source_column_override=source_column, force_source_ok=args.force_source_ok)
