#!/usr/bin/env python3
"""
Check for con_id collisions across apps in the XML source data.
If multiple apps share the same con_ids, only the first one inserted wins.
"""
import pyodbc
from lxml import etree
from xml_extractor.config.config_manager import get_config_manager
from collections import defaultdict

config = get_config_manager()
conn_str = config.get_database_connection_string()

with pyodbc.connect(conn_str) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT app_id, app_XML FROM dbo.app_xml_staging_rl")

    con_id_to_apps = defaultdict(list)  # con_id -> [(app_id, role, name)]
    apps_with_contacts = 0
    apps_without_contacts = 0

    for row in cursor.fetchall():
        app_id = int(row[0])
        try:
            root = etree.fromstring(row[0 + 1].encode("utf-8") if isinstance(row[1], str) else row[1])
            contacts = root.xpath("//IL_contact")
            if contacts:
                apps_with_contacts += 1
            else:
                apps_without_contacts += 1
            for c in contacts:
                con_id = c.get("con_id", "")
                role = c.get("ac_role_tp_c", "")
                name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip()
                if con_id:
                    con_id_to_apps[con_id].append((app_id, role, name))
        except Exception:
            pass

    print(f"Apps with contacts in XML: {apps_with_contacts}")
    print(f"Apps without contacts in XML: {apps_without_contacts}")
    print(f"Unique con_ids in XML: {len(con_id_to_apps)}")

    # Find shared con_ids
    shared = {cid: apps for cid, apps in con_id_to_apps.items() if len(apps) > 1}
    print(f"\nCon_ids shared by multiple apps: {len(shared)}")

    if shared:
        # Count affected apps
        affected_apps = set()
        for apps in shared.values():
            for app_id, _, _ in apps:
                affected_apps.add(app_id)
        print(f"Apps affected by con_id collisions: {len(affected_apps)}")

        # Show details
        print(f"\nFirst 20 shared con_ids:")
        for i, (con_id, apps) in enumerate(sorted(shared.items())[:20]):
            print(f"\n  con_id={con_id} (shared by {len(apps)} apps):")
            for app_id, role, name in apps:
                print(f"    app_id={app_id}, role={role}, name={name}")

        # Check which of these apps have contacts in DB vs not
        print(f"\n\nDB STATUS for affected apps:")
        for con_id, apps in sorted(shared.items())[:10]:
            cursor.execute("SELECT con_id, app_id FROM migration.app_contact_base WHERE con_id = ?", int(con_id))
            db_row = cursor.fetchone()
            winner = f"app_id={db_row[1]}" if db_row else "NOT_IN_DB"
            losers = [app_id for app_id, _, _ in apps if db_row is None or app_id != int(db_row[1])]
            print(f"  con_id={con_id}: DB winner={winner}, losers={losers}")
