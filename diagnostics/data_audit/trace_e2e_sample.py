#!/usr/bin/env python3
"""
Trace the E2E sample XML through the mapper to see
where V4P/V4S values end up.
"""
import sys
import json
from pathlib import Path
from lxml import etree

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper

RL_CONTRACT_RELPATH = "config/mapping_contract_rl.json"
SAMPLE_XML = PROJECT_ROOT / "config" / "samples" / "xml_files" / "reclending" / "sample-source-xml--325725-e2e--rl.xml"

# Load and parse sample XML
with open(SAMPLE_XML, "r", encoding="utf-8-sig") as f:
    xml_text = f.read()

parser = XMLParser()
root = parser.parse_xml_stream(xml_text)
xml_data = parser.extract_elements(root)

print(f"Sample XML parsed: {len(xml_data)} keys")

# Check raw V4 values in parsed data
decision_info_path = "/Provenir/Request/CustData/IL_application/IL_app_decision_info"
if decision_info_path in xml_data:
    attrs = xml_data[decision_info_path].get("attributes", {})
    print(f"\nRaw XML values:")
    print(f"  experian_vantage4_score = {attrs.get('experian_vantage4_score', 'MISSING')!r}")
    print(f"  experian_vantage4_score2 = {attrs.get('experian_vantage4_score2', 'MISSING')!r}")
    print(f"  CRI_score_p = {attrs.get('CRI_score_p', 'MISSING')!r}")

# Run through DataMapper
mapper = DataMapper(mapping_contract_path=RL_CONTRACT_RELPATH)
mapper._current_xml_root = root
mapper._current_xml_tree = root

valid_contacts = mapper._extract_valid_contacts(xml_data)
print(f"\nValid contacts: {len(valid_contacts)}")

mapped_data = mapper.map_xml_to_database(xml_data, "325725", valid_contacts, root)

# Show what ended up in each table
print(f"\n{'='*60}")
print("TABLE OUTPUT SUMMARY")
print(f"{'='*60}")

for table_name in sorted(mapped_data.keys()):
    records = mapped_data[table_name]
    print(f"\n  {table_name}: {len(records)} records")
    if table_name == "scores":
        for r in records:
            print(f"    → {r}")
    elif table_name == "app_historical_lookup":
        for r in records:
            # Check if any history records look like scores
            name = r.get("name", "")
            if "V4" in str(name) or "CRI" in str(name) or "MRV" in str(name) or "score" in str(name).lower():
                print(f"    → SCORE-LIKE: {r}")

# Explicit check
print(f"\n{'='*60}")
print("KEY FINDINGS")
print(f"{'='*60}")
scores = mapped_data.get("scores", [])
history = mapped_data.get("app_historical_lookup", [])

v4p_in_scores = [r for r in scores if r.get("score_identifier") == "V4P"]
v4s_in_scores = [r for r in scores if r.get("score_identifier") == "V4S"]
v4p_in_history = [r for r in history if "V4P" in str(r.get("name", "")) or "vantage4_score" in str(r.get("name", "")).lower()]
v4s_in_history = [r for r in history if "V4S" in str(r.get("name", "")) or "vantage4_score2" in str(r.get("name", "")).lower()]

print(f"\n  V4P in scores table: {len(v4p_in_scores)}")
for r in v4p_in_scores:
    print(f"    {r}")

print(f"  V4S in scores table: {len(v4s_in_scores)}")
for r in v4s_in_scores:
    print(f"    {r}")

print(f"  V4P-like in app_historical_lookup: {len(v4p_in_history)}")
for r in v4p_in_history:
    print(f"    {r}")

print(f"  V4S-like in app_historical_lookup: {len(v4s_in_history)}")
for r in v4s_in_history:
    print(f"    {r}")

# Check ALL history records
print(f"\n  ALL app_historical_lookup records:")
for r in history:
    print(f"    {r}")
