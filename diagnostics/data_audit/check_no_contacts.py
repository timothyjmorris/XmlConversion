#!/usr/bin/env python3
"""Check apps with no contacts in DB."""
import pyodbc
from lxml import etree
from xml_extractor.config.config_manager import get_config_manager

config = get_config_manager()
conn_str = config.get_database_connection_string()

with pyodbc.connect(conn_str) as conn:
    cursor = conn.cursor()
    
    # Find apps with no contacts
    cursor.execute("""
        SELECT b.app_id FROM migration.app_base b
        LEFT JOIN migration.app_contact_base c ON b.app_id = c.app_id
        WHERE c.app_id IS NULL
    """)
    no_contact_apps = [int(r[0]) for r in cursor.fetchall()]
    print(f"Apps with no contacts in DB: {len(no_contact_apps)}")
    
    for app_id in no_contact_apps:
        cursor.execute("SELECT app_XML FROM dbo.app_xml_staging_rl WHERE app_id = ?", app_id)
        row = cursor.fetchone()
        if row:
            root = etree.fromstring(row[0].encode("utf-8") if isinstance(row[0], str) else row[0])
            contacts = root.xpath("//IL_contact")
            il_app = root.xpath("//IL_application")
            app_type = il_app[0].get("application_type", "?") if il_app else "?"
            print(f"\n  app_id={app_id}: {len(contacts)} IL_contact elements, app_type={app_type}")
            for c in contacts:
                con_id = c.get("con_id", "?")
                role = c.get("ac_role_tp_c", "?")
                fname = c.get("first_name", "?")
                lname = c.get("last_name", "?")
                print(f"    con_id={con_id}, role={role}, name={fname} {lname}")
