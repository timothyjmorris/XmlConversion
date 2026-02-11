#!/usr/bin/env python3
"""
Analyze warranties and policy exceptions: XML vs DB.
Find if data is being lost in these KV tables.
"""
import pyodbc
from lxml import etree
from xml_extractor.config.config_manager import get_config_manager
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
RL_CONTRACT = PROJECT_ROOT / "config" / "mapping_contract_rl.json"

config = get_config_manager()
conn_str = config.get_database_connection_string()

# Load contract to find warranty and policy exception mappings
with open(RL_CONTRACT, "r", encoding="utf-8") as f:
    contract = json.load(f)

print("=" * 80)
print("WARRANTY MAPPINGS IN CONTRACT")
print("=" * 80)
warranty_mappings = []
policy_mappings = []
for m in contract.get("mappings", []):
    mt = m.get("mapping_type", [])
    if isinstance(mt, str):
        mt = [mt]
    if any("add_warranty" in str(t) for t in mt):
        warranty_mappings.append(m)
        print(f"  xml_path={m['xml_path']}")
        print(f"  xml_attr={m['xml_attribute']}, target_table={m['target_table']}")
        print(f"  mapping_type={m['mapping_type']}, data_type={m['data_type']}")
        print()
    if any("add_policy_exception" in str(t) for t in mt):
        policy_mappings.append(m)

print(f"\nTotal warranty mappings: {len(warranty_mappings)}")
print(f"Total policy exception mappings: {len(policy_mappings)}")

print("\n" + "=" * 80)
print("POLICY EXCEPTION MAPPINGS IN CONTRACT")
print("=" * 80)
for m in policy_mappings:
    print(f"  xml_path={m['xml_path']}")
    print(f"  xml_attr={m['xml_attribute']}, target_table={m['target_table']}")
    print(f"  mapping_type={m['mapping_type']}, data_type={m['data_type']}")
    print()

# Now check XML data for warranties
print("\n" + "=" * 80)
print("WARRANTY DATA IN XML")
print("=" * 80)

with pyodbc.connect(conn_str) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT app_id, app_XML FROM dbo.app_xml_staging_rl")

    warranty_xml_attr_name = None
    if warranty_mappings:
        warranty_xml_attr_name = warranty_mappings[0].get("xml_attribute")

    warranty_xml_counts = {}  # {app_id: count of warranty values found}
    policy_xml_counts = {}
    
    sample_warranty_values = []
    sample_policy_values = []

    for row in cursor.fetchall():
        app_id = int(row[0])
        try:
            root = etree.fromstring(row[1].encode("utf-8") if isinstance(row[1], str) else row[1])

            # Find warranty-related elements
            for wm in warranty_mappings:
                # Get XML path and attribute
                xml_path = wm["xml_path"]
                xml_attr = wm["xml_attribute"]
                
                # Try to find elements matching the path
                # Convert absolute path to XPath
                xpath = xml_path.replace("/Provenir/Request/CustData/IL_application/", "//")
                if xpath == xml_path:
                    xpath = xml_path.lstrip("/")
                    xpath = "//" + xpath.split("/")[-1]
                
                els = root.xpath(f"//{xml_path.split('/')[-1]}")
                for el in els:
                    val = el.get(xml_attr)
                    if val is not None and val.strip() not in ("", "None", "null"):
                        if app_id not in warranty_xml_counts:
                            warranty_xml_counts[app_id] = 0
                        warranty_xml_counts[app_id] += 1
                        if len(sample_warranty_values) < 10:
                            sample_warranty_values.append((app_id, xml_attr, val))

            # Find policy exception elements
            for pm in policy_mappings:
                xml_attr = pm["xml_attribute"]
                xpath_tail = pm["xml_path"].split("/")[-1]
                els = root.xpath(f"//{xpath_tail}")
                for el in els:
                    val = el.get(xml_attr)
                    if val is not None and val.strip() not in ("", "None", "null"):
                        if app_id not in policy_xml_counts:
                            policy_xml_counts[app_id] = 0
                        policy_xml_counts[app_id] += 1
                        if len(sample_policy_values) < 10:
                            sample_policy_values.append((app_id, xml_attr, val))
        except Exception as e:
            pass

    print(f"\nApps with warranty data in XML: {len(warranty_xml_counts)}")
    print(f"Total warranty values found: {sum(warranty_xml_counts.values())}")
    if sample_warranty_values:
        print("Sample warranty values:")
        for app_id, attr, val in sample_warranty_values[:10]:
            print(f"  app_id={app_id}, attr={attr}, val={val!r}")

    print(f"\nApps with policy exception data in XML: {len(policy_xml_counts)}")
    print(f"Total policy exception values found: {sum(policy_xml_counts.values())}")
    if sample_policy_values:
        print("Sample policy exception values:")
        for app_id, attr, val in sample_policy_values[:10]:
            print(f"  app_id={app_id}, attr={attr}, val={val!r}")

    # Compare with DB
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT app_id) FROM migration.app_warranties_rl")
    r = cursor.fetchone()
    print(f"\nDB app_warranties_rl: {r[0]} rows, {r[1]} distinct apps")

    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT app_id) FROM migration.app_policy_exceptions_rl")
    r = cursor.fetchone()
    print(f"DB app_policy_exceptions_rl: {r[0]} rows, {r[1]} distinct apps")

    # Also check the contact tables that errored
    print("\n" + "=" * 80)
    print("CONTACT TABLE ANALYSIS")
    print("=" * 80)
    
    # app_contact_base apps without contacts
    cursor.execute("""
        SELECT b.app_id 
        FROM migration.app_base b
        LEFT JOIN migration.app_contact_base c ON b.app_id = c.app_id
        WHERE c.app_id IS NULL
    """)
    no_contacts = cursor.fetchall()
    print(f"Apps in app_base with NO contacts: {len(no_contacts)}")
    for r in no_contacts[:5]:
        cursor.execute("SELECT status, failure_reason FROM migration.processing_log WHERE app_id = ?", int(r[0]))
        pl = cursor.fetchone()
        print(f"  app_id={r[0]}: status={pl[0] if pl else '?'}, failure={pl[1] if pl else '?'}")
