#!/usr/bin/env python3
"""Detailed V4P distribution analysis: XML vs DB."""
import pyodbc
from lxml import etree
from xml_extractor.config.config_manager import get_config_manager

config = get_config_manager()
conn_str = config.get_database_connection_string()

with pyodbc.connect(conn_str) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT app_id, app_XML FROM dbo.app_xml_staging_rl")

    buckets = {"missing_attr": 0, "none_str": 0, "zero_str": 0, "empty_str": 0, "real_positive": 0, "other": 0}
    real_apps = []
    zero_apps = []
    empty_apps = []

    for row in cursor.fetchall():
        try:
            root = etree.fromstring(row[1].encode("utf-8") if isinstance(row[1], str) else row[1])
            els = root.xpath("//IL_app_decision_info")
            for el in els:
                v4p = el.get("experian_vantage4_score")
                if v4p is None:
                    buckets["missing_attr"] += 1
                elif v4p == "None":
                    buckets["none_str"] += 1
                elif v4p == "0":
                    buckets["zero_str"] += 1
                    zero_apps.append(int(row[0]))
                elif v4p.strip() == "":
                    buckets["empty_str"] += 1
                    empty_apps.append(int(row[0]))
                else:
                    try:
                        fval = float(v4p)
                        if fval > 0:
                            buckets["real_positive"] += 1
                            real_apps.append((int(row[0]), v4p))
                        else:
                            buckets["other"] += 1
                    except ValueError:
                        buckets["other"] += 1
        except Exception:
            pass

    print("V4P attribute distribution across 791 source apps:")
    for k, v in buckets.items():
        pct = v / 791 * 100
        print(f"  {k:20s}: {v:4d}  ({pct:.1f}%)")
    total_with_attr = sum(v for k, v in buckets.items() if k != "missing_attr")
    print(f"  {'TOTAL with attr':20s}: {total_with_attr:4d}")

    # Get DB V4P apps
    cursor.execute("SELECT DISTINCT app_id FROM migration.scores WHERE score_identifier = 'V4P'")
    db_v4p_apps = {int(r[0]) for r in cursor.fetchall()}
    print(f"\nApps with V4P row in migration.scores: {len(db_v4p_apps)}")

    # Cross-check: how did 96 apps get V4P if only 53 have positive values?
    real_app_ids = {a[0] for a in real_apps}
    zero_app_set = set(zero_apps)
    empty_app_set = set(empty_apps)

    db_from_real = db_v4p_apps & real_app_ids
    db_from_zero = db_v4p_apps & zero_app_set
    db_from_empty = db_v4p_apps & empty_app_set
    db_from_unknown = db_v4p_apps - real_app_ids - zero_app_set - empty_app_set

    print(f"\nDB V4P rows sourced from:")
    print(f"  real positive XML values: {len(db_from_real)}")
    print(f"  zero XML values: {len(db_from_zero)}")
    print(f"  empty XML values: {len(db_from_empty)}")
    print(f"  unknown/other source: {len(db_from_unknown)}")

    # Show what DB has for 'zero' source apps
    if db_from_zero:
        print(f"\n** V4P=0 in XML but V4P row in DB ({len(db_from_zero)} apps):")
        for app_id in sorted(db_from_zero)[:10]:
            cursor.execute(
                "SELECT score FROM migration.scores WHERE app_id = ? AND score_identifier = 'V4P'",
                app_id,
            )
            r = cursor.fetchone()
            print(f"  app_id={app_id}: DB score={r[0] if r else 'NOT FOUND'}")

    if db_from_unknown:
        print(f"\n** V4P from UNKNOWN source ({len(db_from_unknown)} apps):")
        for app_id in sorted(db_from_unknown)[:10]:
            cursor.execute(
                "SELECT score FROM migration.scores WHERE app_id = ? AND score_identifier = 'V4P'",
                app_id,
            )
            r = cursor.fetchone()
            # Check what XML actually has
            cursor.execute("SELECT app_XML FROM dbo.app_xml_staging_rl WHERE app_id = ?", app_id)
            xml_row = cursor.fetchone()
            xml_v4p = "?"
            if xml_row:
                try:
                    xroot = etree.fromstring(xml_row[0].encode("utf-8") if isinstance(xml_row[0], str) else xml_row[0])
                    xels = xroot.xpath("//IL_app_decision_info")
                    if xels:
                        xml_v4p = xels[0].get("experian_vantage4_score", "<MISSING>")
                except Exception:
                    xml_v4p = "<PARSE_ERROR>"
            print(f"  app_id={app_id}: DB score={r[0] if r else 'NOT FOUND'}, XML v4p={xml_v4p!r}")

    # Now the REAL question: apps with real V4P XML that are NOT in DB
    missing_from_db = real_app_ids - db_v4p_apps
    print(f"\n*** CRITICAL: Apps with real V4P in XML but NO V4P in DB: {len(missing_from_db)} ***")
    if missing_from_db:
        for app_id in sorted(missing_from_db)[:10]:
            v4p_val = [a[1] for a in real_apps if a[0] == app_id][0]
            cursor.execute(
                "SELECT status, failure_reason FROM migration.processing_log WHERE app_id = ?",
                app_id,
            )
            r = cursor.fetchone()
            status = r[0] if r else "NOT_IN_LOG"
            fail = r[1] if r else None
            print(f"  app_id={app_id}: V4P_xml={v4p_val!r}, status={status}, failure={fail}")
