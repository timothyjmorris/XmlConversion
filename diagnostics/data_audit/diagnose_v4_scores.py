"""
Diagnostic: Check a list of app_ids to determine:
1. Are they in migration.processing_log? (processed or not)
2. Do they have V4 scores in migration.scores?
3. What does the XML say for experian_vantage4_score?

This answers: "Did we process these apps, and if so, did we lose V4 scores?"
"""
import pyodbc
import argparse
from lxml import etree

APP_IDS = [
    132815, 170423, 173413, 311652, 311653, 311769, 311771, 312020,
    325108, 325109, 325162, 325166, 325169, 325203, 325208, 325249,
    325259, 325264, 325270, 325299, 325601, 325608, 325698, 325712,
    325713, 325714, 325718, 325719, 325721, 325722, 325723, 325724,
    325882, 325916, 325952, 325972, 325993, 325994, 326015, 326017,
    326018, 326019, 326020, 326111, 326112, 326127, 326219, 326233,
    326283, 326289,
]

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

    ids_str = ",".join(str(i) for i in APP_IDS)

    # 1. Check processing_log for these apps
    print("=" * 90)
    print("STEP 1: Check processing_log status")
    print("=" * 90)
    cursor.execute(f"""
        SELECT app_id, status, session_id
        FROM [{args.schema}].[processing_log]
        WHERE app_id IN ({ids_str})
        ORDER BY app_id
    """)
    processed = {}
    for r in cursor.fetchall():
        processed[r[0]] = {'status': r[1], 'session': r[2]}

    not_processed = [a for a in APP_IDS if a not in processed]
    processed_success = [a for a in APP_IDS if a in processed and processed[a]['status'] == 'success']
    processed_failed = [a for a in APP_IDS if a in processed and processed[a]['status'] == 'failed']

    print(f"  Total apps queried:     {len(APP_IDS)}")
    print(f"  In processing_log:      {len(processed)}")
    print(f"    - success:            {len(processed_success)}")
    print(f"    - failed:             {len(processed_failed)}")
    print(f"  NOT in processing_log:  {len(not_processed)}")
    if not_processed:
        print(f"  Not processed apps:     {not_processed[:10]}{'...' if len(not_processed) > 10 else ''}")

    # 2. Check scores table for V4P/V4S rows
    print("\n" + "=" * 90)
    print("STEP 2: Check migration.scores for V4P/V4S")
    print("=" * 90)
    cursor.execute(f"""
        SELECT app_id, score_identifier, score
        FROM [{args.schema}].[scores]
        WHERE app_id IN ({ids_str})
          AND score_identifier IN ('V4P', 'V4S')
        ORDER BY app_id, score_identifier
    """)
    db_scores = {}
    for r in cursor.fetchall():
        db_scores.setdefault(r[0], {})[r[1]] = r[2]

    has_v4p = [a for a in APP_IDS if a in db_scores and 'V4P' in db_scores[a]]
    has_v4s = [a for a in APP_IDS if a in db_scores and 'V4S' in db_scores[a]]
    missing_v4p = [a for a in APP_IDS if a not in db_scores or 'V4P' not in db_scores.get(a, {})]
    missing_v4s = [a for a in APP_IDS if a not in db_scores or 'V4S' not in db_scores.get(a, {})]

    print(f"  Have V4P in DB:         {len(has_v4p)}")
    print(f"  Have V4S in DB:         {len(has_v4s)}")
    print(f"  Missing V4P in DB:      {len(missing_v4p)}")
    print(f"  Missing V4S in DB:      {len(missing_v4s)}")

    # 3. Check XML for experian_vantage4_score values
    print("\n" + "=" * 90)
    print("STEP 3: Check XML for experian_vantage4_score values")
    print("=" * 90)
    cursor.execute(f"""
        SELECT app_id, app_XML
        FROM [{args.source_schema}].[app_xml_staging_rl]
        WHERE app_id IN ({ids_str})
    """)
    xml_rows = cursor.fetchall()
    print(f"  XML rows found:         {len(xml_rows)}")

    xml_v4_values = {}
    for app_id, xml_str in xml_rows:
        try:
            root = etree.fromstring(xml_str.encode('utf-8'))
            nodes = root.xpath('//IL_app_decision_info')
            for node in nodes:
                v4p = node.get('experian_vantage4_score')
                v4s = node.get('experian_vantage4_score2')
                xml_v4_values[app_id] = {'V4P_xml': v4p, 'V4S_xml': v4s}
        except Exception as e:
            xml_v4_values[app_id] = {'error': str(e)}

    # 4. Cross-reference: XML has value but DB doesn't
    print("\n" + "=" * 90)
    print("STEP 4: Cross-reference XML vs DB — MISSING DATA REPORT")
    print("=" * 90)

    truly_missing = []
    for app_id in sorted(APP_IDS):
        xml_vals = xml_v4_values.get(app_id, {})
        db_vals = db_scores.get(app_id, {})
        proc_status = processed.get(app_id, {}).get('status', 'NOT_PROCESSED')
        proc_session = processed.get(app_id, {}).get('session', '')

        v4p_xml = xml_vals.get('V4P_xml')
        v4s_xml = xml_vals.get('V4S_xml')
        v4p_db = db_vals.get('V4P')
        v4s_db = db_vals.get('V4S')

        v4p_expected = v4p_xml is not None and v4p_xml.strip() not in ['', 'None']
        v4s_expected = v4s_xml is not None and v4s_xml.strip() not in ['', 'None']

        v4p_missing = v4p_expected and v4p_db is None
        v4s_missing = v4s_expected and v4s_db is None

        if v4p_missing or v4s_missing:
            truly_missing.append(app_id)
            missing_ids = []
            if v4p_missing: missing_ids.append(f"V4P(xml={v4p_xml})")
            if v4s_missing: missing_ids.append(f"V4S(xml={v4s_xml})")
            print(f"  App {app_id}: MISSING {', '.join(missing_ids)} | status={proc_status} session={proc_session}")

    print(f"\n  TOTAL TRULY MISSING:     {len(truly_missing)} / {len(APP_IDS)}")
    if not truly_missing:
        print("  All V4 scores present in DB!")

    # 5. Categorize: was it processed before or after fix?
    print("\n" + "=" * 90)
    print("STEP 5: Categorize missing apps")
    print("=" * 90)
    missing_and_processed = [a for a in truly_missing if a in processed]
    missing_and_not_processed = [a for a in truly_missing if a not in processed]
    print(f"  Missing + Processed (stale data):  {len(missing_and_processed)}")
    print(f"  Missing + NOT Processed:           {len(missing_and_not_processed)}")
    if missing_and_processed:
        sessions = set()
        for a in missing_and_processed:
            sessions.add(processed[a].get('session', ''))
        print(f"  Sessions involved:                 {sessions}")

if __name__ == "__main__":
    main()
