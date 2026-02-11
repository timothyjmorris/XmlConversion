#!/usr/bin/env python3
"""Full score analysis: all score types, XML vs DB, find any gaps."""
import pyodbc
from lxml import etree
from xml_extractor.config.config_manager import get_config_manager

config = get_config_manager()
conn_str = config.get_database_connection_string()

SCORE_ATTRS = {
    "V4P": "experian_vantage4_score",
    "V4S": "experian_vantage4_score2",
    "CRI_pr": "CRI_score_p",
    "CRI_sec": "CRI_score_s",
    "MRV_pr": "MRV_score_p",
    "MRV_sec": "MRV_score_s",
}

with pyodbc.connect(conn_str) as conn:
    cursor = conn.cursor()

    # Pull all XML
    cursor.execute("SELECT app_id, app_XML FROM dbo.app_xml_staging_rl")
    all_rows = cursor.fetchall()
    print(f"Total source apps: {len(all_rows)}\n")

    # Parse XML and extract score values
    xml_scores = {}  # {app_id: {identifier: raw_value}}
    for row in all_rows:
        app_id = int(row[0])
        try:
            root = etree.fromstring(row[1].encode("utf-8") if isinstance(row[1], str) else row[1])
            els = root.xpath("//IL_app_decision_info")
            for el in els:
                for ident, attr_name in SCORE_ATTRS.items():
                    val = el.get(attr_name)
                    if val is not None:
                        if app_id not in xml_scores:
                            xml_scores[app_id] = {}
                        xml_scores[app_id][ident] = val
        except Exception:
            pass

    # Pull all DB scores
    cursor.execute("SELECT app_id, score_identifier, score FROM migration.scores")
    db_scores = {}  # {app_id: {identifier: score}}
    for r in cursor.fetchall():
        app_id = int(r[0])
        if app_id not in db_scores:
            db_scores[app_id] = {}
        db_scores[app_id][r[1]] = r[2]

    # Analyze each score type
    print(f"{'Score Type':12s} | {'XML has':>8s} | {'XML>0':>6s} | {'XML=0':>6s} | {'XML empty':>10s} | {'DB has':>7s} | {'Missing':>8s} | {'Extra in DB':>12s}")
    print("-" * 100)

    for ident, attr_name in SCORE_ATTRS.items():
        xml_apps_with_attr = {}
        xml_positive = 0
        xml_zero = 0
        xml_empty = 0
        xml_other = 0

        for app_id, scores in xml_scores.items():
            if ident in scores:
                val = scores[ident]
                xml_apps_with_attr[app_id] = val
                if val.strip() == "":
                    xml_empty += 1
                elif val in ("None", "null"):
                    xml_other += 1
                else:
                    try:
                        fval = float(val)
                        if fval == 0:
                            xml_zero += 1
                        else:
                            xml_positive += 1
                    except ValueError:
                        xml_other += 1

        db_apps_with_ident = {a for a, s in db_scores.items() if ident in s}

        # "Expected" = apps where transform_data_types would produce non-None
        # For int type: '0' → 0 (stored), '' → None (skipped), 'None' → None (skipped)
        expected_in_db = set()
        for app_id, val in xml_apps_with_attr.items():
            if val.strip() == "" or val in ("None", "null"):
                continue
            try:
                float(val)
                expected_in_db.add(app_id)
            except ValueError:
                pass

        missing_from_db = expected_in_db - db_apps_with_ident
        extra_in_db = db_apps_with_ident - expected_in_db

        xml_total = len(xml_apps_with_attr)
        print(f"{ident:12s} | {xml_total:8d} | {xml_positive:6d} | {xml_zero:6d} | {xml_empty:10d} | {len(db_apps_with_ident):7d} | {len(missing_from_db):8d} | {len(extra_in_db):12d}")

        if missing_from_db:
            print(f"  ** MISSING apps for {ident}:")
            for app_id in sorted(missing_from_db)[:5]:
                xml_val = xml_apps_with_attr[app_id]
                cursor.execute("SELECT status FROM migration.processing_log WHERE app_id = ?", app_id)
                r = cursor.fetchone()
                print(f"     app_id={app_id}, XML={xml_val!r}, processed={r[0] if r else 'NO'}")

    # Overall summary
    print("\n\nOVERALL SCORE TABLE HEALTH:")
    total_db_rows = sum(len(s) for s in db_scores.values())
    total_db_apps = len(db_scores)
    print(f"  Total score rows in DB: {total_db_rows}")
    print(f"  Distinct apps with scores: {total_db_apps}")

    # How many apps SHOULD have at least one score?
    apps_with_any_xml_score = set()
    for app_id, scores in xml_scores.items():
        for ident, val in scores.items():
            if val.strip() not in ("", "None", "null"):
                try:
                    float(val)
                    apps_with_any_xml_score.add(app_id)
                except ValueError:
                    pass
    
    apps_with_db_score = set(db_scores.keys())
    missing_entirely = apps_with_any_xml_score - apps_with_db_score
    print(f"  Apps that should have >= 1 score: {len(apps_with_any_xml_score)}")
    print(f"  Apps that DO have >= 1 score: {len(apps_with_db_score)}")
    print(f"  Apps completely missing from scores: {len(missing_entirely)}")
    if missing_entirely:
        print(f"\n  COMPLETELY MISSING apps (have XML scores, no DB rows):")
        for app_id in sorted(missing_entirely)[:10]:
            xml_vals = xml_scores[app_id]
            cursor.execute("SELECT status, failure_reason FROM migration.processing_log WHERE app_id = ?", app_id)
            r = cursor.fetchone()
            print(f"    app_id={app_id}: XML scores={xml_vals}, status={r[0] if r else 'NOT_PROCESSED'}, failure={r[1] if r else 'N/A'}")
