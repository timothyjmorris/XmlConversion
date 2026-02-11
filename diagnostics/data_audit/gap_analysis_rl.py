"""
Comprehensive gap analysis: What's in source XML vs what's been processed?
Shows the full population that SHOULD be processed but hasn't been.
"""
import pyodbc
import argparse

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

    print("=" * 90)
    print("POPULATION ANALYSIS")
    print("=" * 90)

    # Total XML source population
    cursor.execute(f"SELECT COUNT(*) FROM [{args.source_schema}].[app_xml_staging_rl]")
    total_source = cursor.fetchone()[0]
    print(f"  Total XML source rows (app_xml_staging_rl):  {total_source}")

    # Total processed in migration
    cursor.execute(f"SELECT COUNT(*) FROM [{args.schema}].[processing_log]")
    total_processed = cursor.fetchone()[0]
    print(f"  Total in processing_log:                     {total_processed}")

    cursor.execute(f"SELECT COUNT(*) FROM [{args.schema}].[processing_log] WHERE status='success'")
    total_success = cursor.fetchone()[0]
    print(f"    - success:                                 {total_success}")

    cursor.execute(f"SELECT COUNT(*) FROM [{args.schema}].[processing_log] WHERE status='failed'")
    total_failed = cursor.fetchone()[0]
    print(f"    - failed:                                  {total_failed}")

    gap = total_source - total_processed
    print(f"  NOT PROCESSED (gap):                         {gap}")
    if total_source > 0:
        print(f"  Coverage:                                    {total_processed/total_source*100:.1f}%")

    # App_id ranges
    print("\n" + "=" * 90)
    print("APP_ID RANGES")
    print("=" * 90)
    cursor.execute(f"SELECT MIN(app_id), MAX(app_id) FROM [{args.source_schema}].[app_xml_staging_rl]")
    src_min, src_max = cursor.fetchone()
    print(f"  Source range:     {src_min} - {src_max}")

    cursor.execute(f"SELECT MIN(app_id), MAX(app_id) FROM [{args.schema}].[processing_log] WHERE status='success'")
    row = cursor.fetchone()
    if row[0]:
        print(f"  Processed range:  {row[0]} - {row[1]}")
    else:
        print(f"  Processed range:  (none)")

    # Session breakdown
    print("\n" + "=" * 90)
    print("SESSION BREAKDOWN")
    print("=" * 90)
    cursor.execute(f"""
        SELECT session_id, COUNT(*) as cnt, 
               MIN(app_id) as min_app, MAX(app_id) as max_app,
               SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as ok,
               SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as fail
        FROM [{args.schema}].[processing_log]
        GROUP BY session_id
        ORDER BY session_id
    """)
    for r in cursor.fetchall():
        print(f"  Session {r[0]}: {r[1]} apps (range {r[2]}-{r[3]}, ok={r[4]}, fail={r[5]})")

    # Scores table stats
    print("\n" + "=" * 90)
    print("SCORES TABLE STATS")
    print("=" * 90)
    cursor.execute(f"SELECT COUNT(DISTINCT app_id) FROM [{args.schema}].[scores]")
    score_apps = cursor.fetchone()[0]
    print(f"  Distinct app_ids in scores:  {score_apps}")

    cursor.execute(f"""
        SELECT score_identifier, COUNT(*) 
        FROM [{args.schema}].[scores]
        GROUP BY score_identifier
        ORDER BY score_identifier
    """)
    for r in cursor.fetchall():
        print(f"    {r[0]}: {r[1]} rows")

    # Cross-check: processed apps WITH scores vs WITHOUT
    print("\n" + "=" * 90)
    print("PROCESSED APPS: SCORES COVERAGE")
    print("=" * 90)
    cursor.execute(f"""
        SELECT COUNT(DISTINCT pl.app_id)
        FROM [{args.schema}].[processing_log] pl
        WHERE pl.status = 'success'
          AND EXISTS (SELECT 1 FROM [{args.schema}].[scores] s WHERE s.app_id = pl.app_id)
    """)
    with_scores = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT COUNT(DISTINCT pl.app_id)
        FROM [{args.schema}].[processing_log] pl
        WHERE pl.status = 'success'
          AND NOT EXISTS (SELECT 1 FROM [{args.schema}].[scores] s WHERE s.app_id = pl.app_id)
    """)
    without_scores = cursor.fetchone()[0]
    print(f"  Processed apps WITH scores:    {with_scores}")
    print(f"  Processed apps WITHOUT scores: {without_scores}")

    # Cross-check: processed apps that have V4 XML but no V4P in scores
    print("\n" + "=" * 90)
    print("CRITICAL: Processed apps with V4 XML but NO V4P score row")
    print("=" * 90)
    cursor.execute(f"""
        SELECT pl.app_id
        FROM [{args.schema}].[processing_log] pl
        INNER JOIN [{args.source_schema}].[app_xml_staging_rl] src ON pl.app_id = src.app_id
        WHERE pl.status = 'success'
          AND NOT EXISTS (
            SELECT 1 FROM [{args.schema}].[scores] s 
            WHERE s.app_id = pl.app_id AND s.score_identifier = 'V4P'
          )
    """)
    no_v4p_rows = cursor.fetchall()
    print(f"  Count: {len(no_v4p_rows)}")
    if no_v4p_rows:
        sample = [r[0] for r in no_v4p_rows[:10]]
        print(f"  Sample: {sample}")

    conn.close()

if __name__ == "__main__":
    main()
