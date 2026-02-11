"""
Deep check: For ALL 55 processed apps in migration, check XML for V4 values
and compare with what's in migration.scores. 
This tells us if the 47 apps with no V4P score genuinely lack V4 XML data
or if we're still losing data.
"""
import pyodbc
import argparse
from lxml import etree

def build_conn(server, database):
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};"
        f"Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=no;"
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--schema", default="migration")
    parser.add_argument("--source-schema", default="dbo")
    args = parser.parse_args()

    conn = build_conn(args.server, args.database)
    cursor = conn.cursor()

    # Get all successfully processed app_ids
    cursor.execute(f"""
        SELECT app_id FROM [{args.schema}].[processing_log] 
        WHERE status='success'
        ORDER BY app_id
    """)
    processed_ids = [r[0] for r in cursor.fetchall()]
    ids_str = ",".join(str(i) for i in processed_ids)

    # Get scores for these
    cursor.execute(f"""
        SELECT app_id, score_identifier, score
        FROM [{args.schema}].[scores]
        WHERE app_id IN ({ids_str})
    """)
    db_scores = {}
    for r in cursor.fetchall():
        db_scores.setdefault(r[0], {})[r[1]] = r[2]

    # Get XML for these
    cursor.execute(f"""
        SELECT app_id, app_XML
        FROM [{args.source_schema}].[app_xml_staging_rl]
        WHERE app_id IN ({ids_str})
    """)
    xml_rows = {r[0]: r[1] for r in cursor.fetchall()}

    # Analyze each
    has_v4_xml_no_db = []
    has_v4_xml_and_db = []
    no_v4_xml = []

    for app_id in processed_ids:
        xml_str = xml_rows.get(app_id)
        if not xml_str:
            continue

        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
            nodes = root.xpath('//IL_app_decision_info')
            v4p_xml = None
            v4s_xml = None
            for node in nodes:
                v4p_xml = node.get('experian_vantage4_score')
                v4s_xml = node.get('experian_vantage4_score2')
        except:
            continue

        v4p_meaningful = v4p_xml is not None and v4p_xml.strip() not in ['', 'None']
        v4p_in_db = 'V4P' in db_scores.get(app_id, {})

        if v4p_meaningful and not v4p_in_db:
            has_v4_xml_no_db.append((app_id, v4p_xml, v4s_xml))
        elif v4p_meaningful and v4p_in_db:
            has_v4_xml_and_db.append(app_id)
        else:
            no_v4_xml.append((app_id, v4p_xml))

    print("=" * 90)
    print("DEEP CHECK: All 55 processed apps — V4 Score Analysis")
    print("=" * 90)
    print(f"\n  Total processed:                     {len(processed_ids)}")
    print(f"  Have V4 XML + V4P in DB (OK):        {len(has_v4_xml_and_db)}")
    print(f"  Have V4 XML + NO V4P in DB (BUG):    {len(has_v4_xml_no_db)}")
    print(f"  No V4 XML value (legitimately none):  {len(no_v4_xml)}")

    if has_v4_xml_no_db:
        print(f"\n  *** DATA LOSS: {len(has_v4_xml_no_db)} apps have V4 in XML but NOT in DB ***")
        for app_id, v4p, v4s in has_v4_xml_no_db:
            print(f"    App {app_id}: V4P={v4p}, V4S={v4s}")

    if no_v4_xml:
        print(f"\n  Apps with no V4 XML (legitimate):")
        for app_id, v4p in no_v4_xml[:10]:
            print(f"    App {app_id}: V4P_raw='{v4p}'")
        if len(no_v4_xml) > 10:
            print(f"    ... and {len(no_v4_xml) - 10} more")

    conn.close()

if __name__ == "__main__":
    main()
