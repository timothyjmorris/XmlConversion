#!/usr/bin/env python3
"""
Step-through diagnostic: trace a SINGLE app_id through the full pipeline
and show exactly what happens to score data at each stage.

This is the equivalent of stepping through an E2E test with print statements.

Usage:
    python diagnostics/data_audit/trace_score_pipeline.py --app-id 325725 \
        --server "..." --database "MACDEVOperational"
"""
import sys
import os
import json
import argparse
import pyodbc
from pathlib import Path
from lxml import etree

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.config.config_manager import get_config_manager


RL_CONTRACT_RELPATH = "config/mapping_contract_rl.json"
RL_CONTRACT_ABSPATH = str(PROJECT_ROOT / RL_CONTRACT_RELPATH)


def get_connection_string(server: str, database: str) -> str:
    config_manager = get_config_manager()
    return config_manager.get_database_connection_string()


def pull_raw_xml(conn_str: str, app_id: int) -> str:
    """Pull raw XML text from dbo.app_xml_staging_rl for this app_id."""
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT app_XML FROM dbo.app_xml_staging_rl WHERE app_id = ?",
            app_id,
        )
        row = cursor.fetchone()
        if not row:
            print(f"[FATAL] app_id {app_id} NOT FOUND in dbo.app_xml_staging_rl")
            sys.exit(1)
        return row[0]


def inspect_xml_for_scores(xml_text: str, app_id: int):
    """Directly inspect the raw XML for score-related attributes."""
    print("\n" + "=" * 80)
    print(f"STAGE 0: RAW XML INSPECTION (app_id={app_id})")
    print("=" * 80)

    root = etree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)

    # Find IL_app_decision_info elements (where scores live per contract)
    decision_info_els = root.xpath("//IL_app_decision_info")
    print(f"\n  Found {len(decision_info_els)} <IL_app_decision_info> element(s)")

    score_attrs = [
        "experian_vantage4_score", "experian_vantage4_score2",
        "CRI_score_p", "CRI_score_s",
        "experian_Vantage_score", "experian_Vantage_score2",
        "tu_score_p", "tu_score_s",
    ]

    for i, el in enumerate(decision_info_els):
        print(f"\n  Element [{i}] attributes:")
        for attr in score_attrs:
            val = el.get(attr, "<NOT PRESENT>")
            marker = ""
            if val in ("None", "0", "", "<NOT PRESENT>"):
                marker = " ← would be skipped"
            elif val.isdigit() and int(val) > 0:
                marker = " ← SHOULD produce a score row"
            print(f"    {attr} = '{val}'{marker}")

    # Also look for any other elements that might have these attributes
    for attr in ["experian_vantage4_score", "experian_vantage4_score2"]:
        all_els = root.xpath(f"//*[@{attr}]")
        if len(all_els) != len(decision_info_els):
            print(f"\n  ⚠ {attr} found on {len(all_els)} element(s), but IL_app_decision_info has {len(decision_info_els)}")
            for el in all_els:
                print(f"    Tag: {el.tag}, path hint: {el.getparent().tag if el.getparent() is not None else 'root'}")

    return root


def trace_parser(xml_text: str, app_id: int):
    """Step 1: Run XMLParser and show what it produces."""
    print("\n" + "=" * 80)
    print(f"STAGE 1: XMLParser.parse_xml_stream + extract_elements")
    print("=" * 80)

    parser = XMLParser()
    root = parser.parse_xml_stream(xml_text)
    xml_data = parser.extract_elements(root)

    print(f"\n  parse_xml_stream: {'OK' if root is not None else 'FAILED'}")
    print(f"  extract_elements: {len(xml_data)} keys")

    # Check if the decision_info path exists in extracted data
    decision_paths = [k for k in xml_data if "IL_app_decision_info" in k]
    print(f"\n  Paths containing 'IL_app_decision_info': {len(decision_paths)}")
    for p in decision_paths:
        data = xml_data[p]
        if isinstance(data, dict) and "attributes" in data:
            attrs = data["attributes"]
            v4p = attrs.get("experian_vantage4_score", "<NOT IN DICT>")
            v4s = attrs.get("experian_vantage4_score2", "<NOT IN DICT>")
            print(f"    Path: {p}")
            print(f"      experian_vantage4_score  = '{v4p}'")
            print(f"      experian_vantage4_score2 = '{v4s}'")
            print(f"      Total attributes: {len(attrs)}")
        elif isinstance(data, list):
            print(f"    Path: {p}  (LIST of {len(data)} elements)")
            for j, item in enumerate(data):
                if isinstance(item, dict) and "attributes" in item:
                    attrs = item["attributes"]
                    v4p = attrs.get("experian_vantage4_score", "<NOT IN DICT>")
                    v4s = attrs.get("experian_vantage4_score2", "<NOT IN DICT>")
                    print(f"      [{j}] v4p='{v4p}', v4s='{v4s}'")
        else:
            print(f"    Path: {p}  type={type(data).__name__}")

    return root, xml_data


def trace_mapper(xml_data, app_id, root):
    """Step 2: Run DataMapper and show EXACTLY what happens to scores."""
    print("\n" + "=" * 80)
    print(f"STAGE 2: DataMapper — contract loading, grouping, score extraction")
    print("=" * 80)

    mapper = DataMapper(mapping_contract_path=RL_CONTRACT_RELPATH)

    # Load contract to inspect mappings
    with open(RL_CONTRACT_ABSPATH, "r", encoding="utf-8") as f:
        contract_json = json.load(f)

    # Find all score mappings in the contract
    score_mappings_in_contract = []
    for m in contract_json.get("mappings", []):
        mt = m.get("mapping_type", [])
        if isinstance(mt, str):
            mt = [mt]
        if any("add_score" in str(t) for t in mt):
            score_mappings_in_contract.append(m)

    print(f"\n  Score mappings in contract: {len(score_mappings_in_contract)}")
    for sm in score_mappings_in_contract:
        print(f"    target_table={sm['target_table']}, xml_attr={sm['xml_attribute']}, "
              f"mapping_type={sm['mapping_type']}, data_type={sm['data_type']}")

    # Now trace through _group_mappings_by_table
    contract = mapper._config_manager.load_mapping_contract(mapper._mapping_contract_path)
    table_mappings = mapper._group_mappings_by_table(contract.mappings)

    print(f"\n  Tables after grouping: {sorted(table_mappings.keys())}")
    if "scores" in table_mappings:
        scores_mappings = table_mappings["scores"]
        print(f"  Mappings grouped under 'scores': {len(scores_mappings)}")
        for sm in scores_mappings:
            mt = sm.mapping_type if sm.mapping_type else []
            print(f"    xml_attr={sm.xml_attribute}, mapping_type={mt}, target_table={sm.target_table}")
    else:
        print("  ⚠ NO 'scores' key in table_mappings!")
        # Check where score mappings ended up
        for tname, tmaps in table_mappings.items():
            for m in tmaps:
                mt = m.mapping_type if m.mapping_type else []
                if any("add_score" in str(t) for t in mt):
                    print(f"  ⚠ add_score mapping found under table '{tname}' instead of 'scores'!")

    # Now manually call _extract_score_records with scores mappings
    print(f"\n  --- Manually calling _extract_score_records ---")
    if "scores" in table_mappings:
        # Set up mapper state (same as map_xml_to_database does)
        mapper._current_xml_root = root
        mapper._current_xml_tree = root

        score_records = mapper._extract_score_records(xml_data, table_mappings["scores"], str(app_id))
        print(f"  Score records returned: {len(score_records)}")
        for sr in score_records:
            print(f"    {sr}")

        # Now trace EACH mapping individually
        print(f"\n  --- Tracing each score mapping individually ---")
        for mapping in table_mappings["scores"]:
            mt = mapping.mapping_type if mapping.mapping_type else []
            add_score_types = [t for t in mt if str(t).strip().startswith("add_score")]
            if not add_score_types:
                print(f"    {mapping.xml_attribute}: NO add_score in mapping_type {mt} → SKIPPED")
                continue

            name, identifier = mapper._parse_mapping_type_function(add_score_types[0])
            if name != "add_score" or not identifier:
                print(f"    {mapping.xml_attribute}: parse returned name={name}, id={identifier} → SKIPPED")
                continue

            raw_value = mapper._extract_value_from_xml(xml_data, mapping, context_data=None)
            print(f"    {mapping.xml_attribute} [{identifier}]:")
            print(f"      raw_value = {repr(raw_value)} (type={type(raw_value).__name__})")

            if raw_value is None:
                print(f"      → SKIPPED (raw_value is None)")
                continue

            score_value = mapper.transform_data_types(raw_value, mapping.data_type)
            print(f"      transform_data_types('{raw_value}', '{mapping.data_type}') = {repr(score_value)}")

            if score_value is None:
                print(f"      → SKIPPED (transform returned None)")
            else:
                print(f"      → WOULD CREATE: app_id={app_id}, score_identifier={identifier}, score={score_value}")

    return mapper


def trace_full_map(mapper, xml_data, app_id, root):
    """Step 3: Run full map_xml_to_database and check scores output."""
    print("\n" + "=" * 80)
    print(f"STAGE 3: Full map_xml_to_database output")
    print("=" * 80)

    mapper._current_xml_root = root
    mapper._current_xml_tree = root
    valid_contacts = mapper._extract_valid_contacts(xml_data)
    print(f"\n  Valid contacts: {len(valid_contacts)}")

    mapped_data = mapper.map_xml_to_database(xml_data, str(app_id), valid_contacts, root)

    print(f"\n  Tables in mapped output: {sorted(mapped_data.keys())}")
    for tname, records in sorted(mapped_data.items()):
        print(f"    {tname}: {len(records)} records")

    if "scores" in mapped_data:
        print(f"\n  Score records from full mapping:")
        for sr in mapped_data["scores"]:
            print(f"    {sr}")
    else:
        print(f"\n  ⚠ 'scores' NOT in mapped_data keys!")

    return mapped_data


def main():
    parser = argparse.ArgumentParser(description="Trace score pipeline for a single app_id")
    parser.add_argument("--app-id", type=int, required=True)
    parser.add_argument("--server", required=True)
    parser.add_argument("--database", required=True)
    args = parser.parse_args()

    conn_str = get_connection_string(args.server, args.database)

    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║  SCORE PIPELINE TRACE — app_id {args.app_id:<28} ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")

    # Pull raw XML
    xml_text = pull_raw_xml(conn_str, args.app_id)
    print(f"\n  Raw XML length: {len(xml_text)} chars")

    # Stage 0: Raw XML inspection
    xml_root = inspect_xml_for_scores(xml_text, args.app_id)

    # Stage 1: XMLParser
    root, xml_data = trace_parser(xml_text, args.app_id)

    # Stage 2: DataMapper score extraction (isolated)
    mapper = trace_mapper(xml_data, args.app_id, root)

    # Stage 3: Full map_xml_to_database
    mapped_data = trace_full_map(mapper, xml_data, args.app_id, root)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    score_count = len(mapped_data.get("scores", []))
    print(f"  Scores produced by pipeline: {score_count}")
    if score_count == 0:
        print("  ⚠ ZERO scores — the pipeline is dropping them before DB insertion")
    else:
        for sr in mapped_data["scores"]:
            print(f"    → {sr['score_identifier']} = {sr['score']}")


if __name__ == "__main__":
    main()
