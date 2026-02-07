"""\
KV Mapping Reconciliation - Contract ↔ XML ↔ Mapper ↔ Destination Tables

Purpose
- Enumerate all contract mappings that use the new row-creating mapping types:
  - add_score(<identifier>) -> [target_schema].[scores]
  - add_indicator(<name>)   -> [target_schema].[indicators]
  - add_history             -> [target_schema].[app_historical_lookup]
  - add_report_lookup       -> [target_schema].[app_report_results_lookup]
- For each mapping, reconcile:
  1) Source XML attribute value
  2) Mapper-produced record (DataMapper.map_xml_to_database)
  3) Destination table row(s)

Usage examples
- Use local XML fixture (recommended for CC manual E2E fixture):
  python diagnostics/reconcile_kv_mappings.py --xml-file config/samples/sample-source-xml-contact-test.xml

- Use an app_id and fetch XML from the configured source_table/source_column:
  python diagnostics/reconcile_kv_mappings.py --app-id 443306

- Override app_id (if the XML itself has a different Request/@ID):
  python diagnostics/reconcile_kv_mappings.py --xml-file <path> --app-id 123

Outputs
- Writes a JSON report to metrics/kv_reconcile_<app_id>_<timestamp>.json
- Prints a concise console summary + top mismatches

Notes
- This script does SELECT-only reads from SQL Server.
- No DDL, DELETE, TRUNCATE, or other destructive operations.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import difflib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyodbc
from lxml import etree

# Ensure workspace root is importable when running as a script
WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping, MappingContract, RelationshipMapping
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.utils import StringUtils
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator


logger = logging.getLogger(__name__)


KV_TABLES = {
    "scores",
    "indicators",
    "app_historical_lookup",
    "app_report_results_lookup",
}


@dataclass
class MappingSpec:
    xml_path: str
    xml_attribute: str
    target_table: str
    data_type: str
    mapping_types: List[str]


@dataclass
class MappingReconcileRow:
    mapping: MappingSpec
    mapping_type_normalized: str

    xml_raw_value: Optional[str] = None
    xml_has_value: bool = False

    expected_record: Optional[Dict[str, Any]] = None
    mapper_produced: bool = False

    dest_record: Optional[Dict[str, Any]] = None
    dest_has_row: bool = False

    status: str = "UNKNOWN"  # PASS | FAIL | WARN
    issues: List[str] = field(default_factory=list)
    smells: List[str] = field(default_factory=list)


@dataclass
class ReconcileReport:
    app_id: int
    target_schema: str
    xml_source: str
    generated_at_utc: str

    contract_kv_mapping_count: int
    rows: List[MappingReconcileRow]

    summary: Dict[str, int]
    contract_issues: List[str]


def _load_contract(contract_path: Path) -> Dict[str, Any]:
    with open(contract_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _parse_contract(contract_json: Dict[str, Any]) -> MappingContract:
    contract_json = dict(contract_json)
    contract_json["mappings"] = [FieldMapping(**fm) for fm in contract_json.get("mappings", [])]
    if contract_json.get("relationships"):
        contract_json["relationships"] = [RelationshipMapping(**rm) for rm in contract_json["relationships"]]
    return MappingContract(**contract_json)


def _normalize_mapping_types(mapping_types: Any) -> List[str]:
    if mapping_types is None:
        return []
    if isinstance(mapping_types, list):
        return [str(mt).strip() for mt in mapping_types if str(mt).strip()]
    if isinstance(mapping_types, str):
        # Contract sometimes uses a string; keep it resilient
        return [mt.strip() for mt in mapping_types.split(",") if mt.strip()]
    return [str(mapping_types).strip()]


def _mapping_type_name_and_param(mapping_type: str) -> Tuple[str, Optional[str]]:
    mt = (mapping_type or "").strip()
    if not mt:
        return "", None
    # Function-like: add_score(TU_TIE)
    if "(" in mt and mt.endswith(")"):
        name = mt.split("(", 1)[0].strip()
        param = mt.split("(", 1)[1][:-1].strip()
        return name, param or None
    return mt, None


def _is_meaningful_kv_value(raw_value: Any) -> bool:
    if not StringUtils.safe_string_check(raw_value):
        return False
    lowered = str(raw_value).strip().lower()
    return lowered not in {"null", "none"}


def _derive_source_from_xml_path(xml_path: str) -> str:
    trimmed = (xml_path or "").strip()
    if trimmed.endswith("/"):
        trimmed = trimmed[:-1]
    return trimmed.rsplit("/", 1)[-1] if "/" in trimmed else trimmed


def _get_xml_attribute(root: etree._Element, xml_path: str, xml_attribute: str) -> Optional[str]:
    if root is None:
        return None
    try:
        elements = root.xpath(xml_path)
        if not elements:
            return None
        val = elements[0].attrib.get(xml_attribute)
        return val
    except Exception as e:
        logger.warning("XPath/attribute extract failed for %s/@%s: %s", xml_path, xml_attribute, e)
        return None


def _fetch_source_xml_from_db(conn: pyodbc.Connection, source_table: str, source_column: str, app_id: int) -> Optional[str]:
    cursor = conn.cursor()

    # Source tables are always in dbo in this project (by design); try dbo first.
    attempts = [f"dbo.{source_table}", source_table]
    for table in attempts:
        try:
            cursor.execute(f"SELECT {source_column} FROM {table} WITH (NOLOCK) WHERE app_id = ?", app_id)
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception:
            continue
    return None


def _query_dest_kv_tables(conn: pyodbc.Connection, target_schema: str, app_id: int) -> Dict[str, Any]:
    cursor = conn.cursor()

    def q(sql: str, params: Tuple[Any, ...]) -> List[Tuple[Any, ...]]:
        cursor.execute(sql, params)
        return cursor.fetchall()

    qualified = lambda t: f"[{target_schema}].[{t}]"

    scores_rows = q(
        f"SELECT score_identifier, score FROM {qualified('scores')} WITH (NOLOCK) WHERE app_id = ?",
        (app_id,),
    )
    indicators_rows = q(
        f"SELECT indicator, value FROM {qualified('indicators')} WITH (NOLOCK) WHERE app_id = ?",
        (app_id,),
    )
    history_rows = q(
        f"SELECT name, source, value FROM {qualified('app_historical_lookup')} WITH (NOLOCK) WHERE app_id = ?",
        (app_id,),
    )
    report_rows = q(
        f"SELECT name, value, source_report_key FROM {qualified('app_report_results_lookup')} WITH (NOLOCK) WHERE app_id = ?",
        (app_id,),
    )

    return {
        "scores": {(r[0],): {"score_identifier": r[0], "score": r[1]} for r in scores_rows},
        "indicators": {(r[0],): {"indicator": r[0], "value": r[1]} for r in indicators_rows},
        "app_historical_lookup": {
            (r[0], r[1]): {"name": r[0], "source": r[1], "value": r[2]} for r in history_rows
        },
        "app_report_results_lookup": {(r[0],): {"name": r[0], "value": r[1], "source_report_key": r[2]} for r in report_rows},
    }


def _contract_kv_specs(contract_json: Dict[str, Any]) -> List[MappingSpec]:
    specs: List[MappingSpec] = []
    for fm in contract_json.get("mappings", []):
        target_table = (fm.get("target_table") or "").strip()
        if target_table not in KV_TABLES:
            continue
        xml_path = (fm.get("xml_path") or "").strip()
        xml_attribute = (fm.get("xml_attribute") or "").strip()
        data_type = (fm.get("data_type") or "").strip()
        mapping_types = _normalize_mapping_types(fm.get("mapping_type"))
        specs.append(
            MappingSpec(
                xml_path=xml_path,
                xml_attribute=xml_attribute,
                target_table=target_table,
                data_type=data_type,
                mapping_types=mapping_types,
            )
        )
    return specs


def _detect_contract_issues(specs: List[MappingSpec]) -> List[str]:
    issues: List[str] = []

    for s in specs:
        normalized = {_mapping_type_name_and_param(mt)[0] for mt in s.mapping_types}
        if s.target_table == "scores" and not any(mt.startswith("add_score") for mt in s.mapping_types):
            issues.append(f"Contract: scores mapping without add_score(): {s.xml_attribute} ({s.mapping_types})")
        if s.target_table == "indicators" and not any(mt.startswith("add_indicator") for mt in s.mapping_types):
            issues.append(f"Contract: indicators mapping without add_indicator(): {s.xml_attribute} ({s.mapping_types})")
        if s.target_table == "app_historical_lookup" and "add_history" not in normalized:
            issues.append(f"Contract: history mapping without add_history: {s.xml_attribute} ({s.mapping_types})")
        if s.target_table == "app_report_results_lookup" and "add_report_lookup" not in normalized:
            issues.append(f"Contract: report lookup mapping without add_report_lookup: {s.xml_attribute} ({s.mapping_types})")

        # Smell: score-like attributes mapped to history
        if s.target_table == "app_historical_lookup" and s.xml_attribute.lower().endswith("_score"):
            issues.append(
                f"Contract smell: {s.xml_attribute} endswith _score but mapped to app_historical_lookup (add_history)"
            )

    return issues


def _expected_record_from_mapping(
    mapper: DataMapper,
    app_id: int,
    spec: MappingSpec,
    xml_raw: Optional[str],
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Compute the expected KV record using the same semantics as DataMapper."""
    smells: List[str] = []

    mapping_types = spec.mapping_types
    add_score_mt = next((mt for mt in mapping_types if mt.startswith("add_score")), None)
    add_indicator_mt = next((mt for mt in mapping_types if mt.startswith("add_indicator")), None)
    name, param = _mapping_type_name_and_param(add_score_mt) if add_score_mt else ("", None)

    if add_score_mt:
        if xml_raw is None or not str(xml_raw).strip():
            return None, smells
        coerced = mapper.transform_data_types(xml_raw, spec.data_type)
        if coerced is None:
            return None, smells
        return {
            "app_id": app_id,
            "score_identifier": param,
            "score": coerced,
        }, smells

    if add_indicator_mt:
        if xml_raw is None:
            return None, smells
        truthy_values = {"y", "yes", "true", "t", "1"}
        if str(xml_raw).strip().lower() not in truthy_values:
            return None, smells
        _, indicator_name = _mapping_type_name_and_param(add_indicator_mt)
        return {
            "app_id": app_id,
            "indicator": indicator_name,
            "value": "1",
        }, smells

    normalized_names = {_mapping_type_name_and_param(mt)[0] for mt in mapping_types}

    if "add_history" in normalized_names:
        if not _is_meaningful_kv_value(xml_raw):
            return None, smells
        source = _derive_source_from_xml_path(spec.xml_path)
        val = str(xml_raw).strip() if xml_raw is not None else None
        if val in {"0", "0.0", "0.00"} and (spec.xml_attribute or "").lower().endswith("_score"):
            smells.append(f"History value for score-like field is zero: {spec.xml_attribute}={val}")
        return {
            "app_id": app_id,
            "name": f"[{spec.xml_attribute}]",
            "source": f"[{source}]" if source else None,
            "value": val,
        }, smells

    if "add_report_lookup" in normalized_names:
        if not _is_meaningful_kv_value(xml_raw):
            return None, smells
        val = str(xml_raw).strip() if xml_raw is not None else None

        # Support optional parameter: add_report_lookup(IDV) -> source_report_key='IDV'
        report_key: Optional[str] = None
        for mt in mapping_types:
            name, param = _mapping_type_name_and_param(mt)
            if name == "add_report_lookup" and param:
                report_key = param
                break

        record: Dict[str, Any] = {
            "app_id": app_id,
            "name": spec.xml_attribute,
            "value": val,
        }
        if report_key is not None:
            record["source_report_key"] = report_key
        return record, smells

    return None, smells


def _find_mapper_record(mapped_data: Dict[str, List[Dict[str, Any]]], table: str, expected: Dict[str, Any]) -> bool:
    rows = mapped_data.get(table, [])
    if not rows:
        return False

    if table == "scores":
        return any(
            (r.get("score_identifier") == expected.get("score_identifier") and r.get("score") == expected.get("score"))
            for r in rows
        )
    if table == "indicators":
        return any(
            (r.get("indicator") == expected.get("indicator") and r.get("value") == expected.get("value"))
            for r in rows
        )
    if table == "app_historical_lookup":
        return any(
            (r.get("name") == expected.get("name") and r.get("source") == expected.get("source") and r.get("value") == expected.get("value"))
            for r in rows
        )
    if table == "app_report_results_lookup":
        return any(
            (r.get("name") == expected.get("name") and r.get("value") == expected.get("value") and r.get("source_report_key") == expected.get("source_report_key"))
            for r in rows
        )

    return False


def _dest_lookup(dest_index: Dict[str, Any], table: str, expected: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if table == "scores":
        return dest_index[table].get((expected.get("score_identifier"),))
    if table == "indicators":
        return dest_index[table].get((expected.get("indicator"),))
    if table == "app_report_results_lookup":
        return dest_index[table].get((expected.get("name"),))
    if table == "app_historical_lookup":
        return dest_index[table].get((expected.get("name"), expected.get("source")))
    return None


def reconcile(app_id: int, xml_content: str, xml_source: str) -> ReconcileReport:
    root_dir = Path(__file__).parent.parent
    contract_path = root_dir / "config" / "mapping_contract.json"

    contract_json = _load_contract(contract_path)
    target_schema = contract_json.get("target_schema", "dbo") or "dbo"

    specs = _contract_kv_specs(contract_json)
    contract_issues = _detect_contract_issues(specs)

    validator = PreProcessingValidator()
    validation = validator.validate_xml_for_processing(xml_content, source_record_id="kv_reconcile")
    if not validation.is_valid or not validation.can_process:
        errors = getattr(validation, "validation_errors", None) or []
        raise RuntimeError(f"XML failed pre-processing validation: {errors}")

    # Prefer explicit app_id argument, but allow the XML-derived one as a fallback.
    xml_app_id = int(validation.app_id) if str(validation.app_id).isdigit() else None
    if xml_app_id is not None and xml_app_id != app_id:
        logger.warning("XML app_id=%s does not match requested app_id=%s; using requested app_id", xml_app_id, app_id)

    parser = XMLParser()
    xml_root = parser.parse_xml_stream(xml_content)
    xml_data = parser.extract_elements(xml_root)

    mapper = DataMapper(mapping_contract_path=str(contract_path))
    mapped_data = mapper.map_xml_to_database(xml_data, str(app_id), validation.valid_contacts, xml_root)

    config = get_config_manager()
    conn_str = config.get_database_connection_string()

    with pyodbc.connect(conn_str) as conn:
        dest_index = _query_dest_kv_tables(conn, target_schema=target_schema, app_id=app_id)

    rows: List[MappingReconcileRow] = []

    # Parse XML into lxml tree for raw attribute extraction
    xml_etree_root = etree.fromstring(xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content)

    # Track expected keys to detect destination extras
    expected_keys: Dict[str, set] = {
        "scores": set(),
        "indicators": set(),
        "app_historical_lookup": set(),
        "app_report_results_lookup": set(),
    }

    for spec in specs:
        mapping_types = spec.mapping_types
        normalized_mt_names = {_mapping_type_name_and_param(mt)[0] for mt in mapping_types}

        mt_display = "|".join(mapping_types) if mapping_types else ""
        normalized = (
            "add_score"
            if any(mt.startswith("add_score") for mt in mapping_types)
            else "add_indicator"
            if any(mt.startswith("add_indicator") for mt in mapping_types)
            else "add_history"
            if "add_history" in normalized_mt_names
            else "add_report_lookup"
            if "add_report_lookup" in normalized_mt_names
            else mt_display
        )

        row = MappingReconcileRow(
            mapping=spec,
            mapping_type_normalized=normalized,
        )

        # Use DataMapper's extraction semantics (XMLParser flattens/dedupes contacts).
        # This keeps reconciliation aligned with what the mapper actually sees.
        try:
            fm = FieldMapping(
                xml_path=spec.xml_path,
                xml_attribute=spec.xml_attribute,
                target_table=spec.target_table,
                target_column="",
                data_type=spec.data_type,
                mapping_type=spec.mapping_types,
            )
            xml_raw_val = mapper._extract_value_from_xml(xml_data, fm, context_data=None)
            xml_raw = None if xml_raw_val is None else str(xml_raw_val)
        except Exception:
            xml_raw = None

        # Fallback to direct etree attribute extraction when mapper-based extraction yields nothing.
        if xml_raw is None:
            xml_raw = _get_xml_attribute(xml_etree_root, spec.xml_path, spec.xml_attribute)
        row.xml_raw_value = xml_raw
        row.xml_has_value = bool(xml_raw is not None and str(xml_raw).strip() != "")

        # If the element exists but the attribute is missing, suggest close matches.
        if xml_raw is None:
            try:
                elements = xml_etree_root.xpath(spec.xml_path)
                if elements:
                    attr_keys = list(getattr(elements[0], "attrib", {}).keys())
                    if attr_keys and spec.xml_attribute:
                        matches = difflib.get_close_matches(spec.xml_attribute, attr_keys, n=3, cutoff=0.78)
                        if matches:
                            row.status = "WARN"
                            row.issues.append(
                                f"XML attribute not found; close matches: {matches}"
                            )
            except Exception:
                pass

        expected, smells = _expected_record_from_mapping(mapper, app_id, spec, xml_raw)
        row.expected_record = expected
        row.smells.extend(smells)

        if expected is None:
            # If no expected record due to empty/non-meaningful input, that is usually PASS.
            # But we still want visibility into "you thought it had a value" situations.
            if row.xml_has_value:
                row.status = "WARN"
                row.issues.append("XML has value but no expected record produced (check mapping type / coercion)")
            else:
                row.status = "PASS"
            rows.append(row)
            continue

        # Record expected key for extra-row detection
        if spec.target_table == "scores":
            expected_keys["scores"].add((expected.get("score_identifier"),))
        elif spec.target_table == "indicators":
            expected_keys["indicators"].add((expected.get("indicator"),))
        elif spec.target_table == "app_report_results_lookup":
            expected_keys["app_report_results_lookup"].add((expected.get("name"),))
        elif spec.target_table == "app_historical_lookup":
            expected_keys["app_historical_lookup"].add((expected.get("name"), expected.get("source")))

        row.mapper_produced = _find_mapper_record(mapped_data, spec.target_table, expected)
        if not row.mapper_produced:
            row.issues.append("Mapper did not produce expected KV record")

        dest = _dest_lookup(dest_index, spec.target_table, expected)
        row.dest_record = dest
        row.dest_has_row = dest is not None

        if not row.dest_has_row:
            row.status = "FAIL"
            row.issues.append("Destination row missing")
            rows.append(row)
            continue

        # Compare value fields
        if spec.target_table == "scores":
            exp_val = expected.get("score")
            act_val = dest.get("score") if dest else None
            if exp_val != act_val:
                row.status = "FAIL"
                row.issues.append(f"Score mismatch: expected={exp_val!r} actual={act_val!r}")
            else:
                row.status = "PASS"
        elif spec.target_table == "indicators":
            exp_val = expected.get("value")
            act_val = dest.get("value") if dest else None
            if str(exp_val) != str(act_val):
                row.status = "FAIL"
                row.issues.append(f"Indicator mismatch: expected={exp_val!r} actual={act_val!r}")
            else:
                row.status = "PASS"
        elif spec.target_table == "app_historical_lookup":
            exp_val = expected.get("value")
            act_val = dest.get("value") if dest else None
            if str(exp_val) != str(act_val):
                row.status = "FAIL"
                row.issues.append(f"History mismatch: expected={exp_val!r} actual={act_val!r}")
            else:
                row.status = "PASS"
        elif spec.target_table == "app_report_results_lookup":
            exp_val = expected.get("value")
            act_val = dest.get("value") if dest else None
            if str(exp_val) != str(act_val):
                row.status = "FAIL"
                row.issues.append(f"Report value mismatch: expected={exp_val!r} actual={act_val!r}")
            else:
                # Also verify source_report_key when expected includes it
                exp_key = expected.get("source_report_key")
                if exp_key is not None:
                    act_key = dest.get("source_report_key")
                    if str(exp_key) != str(act_key):
                        row.status = "FAIL"
                        row.issues.append(f"source_report_key mismatch: expected={exp_key!r} actual={act_key!r}")
                    else:
                        row.status = "PASS"
                else:
                    row.status = "PASS"
        else:
            row.status = "WARN"
            row.issues.append("Unhandled target_table comparison")

        rows.append(row)

    summary = {
        "PASS": sum(1 for r in rows if r.status == "PASS"),
        "WARN": sum(1 for r in rows if r.status == "WARN"),
        "FAIL": sum(1 for r in rows if r.status == "FAIL"),
        "TOTAL": len(rows),
    }

    # Detect destination extras (rows present in DB but not expected for this XML+contract)
    for table in ("scores", "indicators", "app_historical_lookup", "app_report_results_lookup"):
        dest_keys = set(dest_index.get(table, {}).keys())
        extras = dest_keys - expected_keys.get(table, set())
        if extras:
            # Add a single summarized WARN row per table.
            dummy = MappingSpec(
                xml_path="",
                xml_attribute="",
                target_table=table,
                data_type="",
                mapping_types=[],
            )
            extra_row = MappingReconcileRow(
                mapping=dummy,
                mapping_type_normalized="EXTRA_DEST_ROWS",
                status="WARN",
                issues=[f"Destination has {len(extras)} extra row(s) not expected by contract+XML"],
                smells=[],
            )
            # Include up to 5 examples for quick inspection
            examples = list(extras)[:5]
            extra_row.dest_has_row = True
            extra_row.dest_record = {"example_keys": examples}
            rows.append(extra_row)

    # Recompute summary with extra rows included
    summary = {
        "PASS": sum(1 for r in rows if r.status == "PASS"),
        "WARN": sum(1 for r in rows if r.status == "WARN"),
        "FAIL": sum(1 for r in rows if r.status == "FAIL"),
        "TOTAL": len(rows),
    }

    return ReconcileReport(
        app_id=app_id,
        target_schema=target_schema,
        xml_source=xml_source,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        contract_kv_mapping_count=len(specs),
        rows=rows,
        summary=summary,
        contract_issues=contract_issues,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile KV (add_*) mappings end-to-end")
    parser.add_argument("--app-id", type=int, default=None, help="app_id to reconcile")
    parser.add_argument("--xml-file", type=str, default=None, help="Path to source XML file")
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional explicit output path for the JSON report",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    root_dir = Path(__file__).parent.parent
    contract_path = root_dir / "config" / "mapping_contract.json"
    contract_json = _load_contract(contract_path)

    config = get_config_manager()
    conn_str = config.get_database_connection_string()

    xml_content: Optional[str] = None
    xml_source = ""

    if args.xml_file:
        xml_path = Path(args.xml_file)
        if not xml_path.is_absolute():
            xml_path = root_dir / xml_path
        if not xml_path.exists():
            raise FileNotFoundError(f"XML file not found: {xml_path}")
        xml_source = str(xml_path)
        xml_content = xml_path.read_text(encoding="utf-8-sig")

    if xml_content is None:
        if args.app_id is None:
            raise SystemExit("Provide either --xml-file or --app-id")
        with pyodbc.connect(conn_str) as conn:
            source_table = contract_json.get("source_table", "app_xml_staging")
            source_column = contract_json.get("source_column", "app_XML")
            xml_content = _fetch_source_xml_from_db(conn, source_table, source_column, args.app_id)
            if not xml_content:
                raise RuntimeError(f"No source XML found for app_id={args.app_id} in {source_table}.{source_column}")
            xml_source = f"DB:{source_table}.{source_column}"

    # Determine app_id
    app_id = args.app_id
    if app_id is None:
        # Derive from XML Request/@ID
        try:
            root = etree.fromstring(xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content)
            req = root.xpath("/Provenir/Request")
            if not req:
                raise RuntimeError("Could not locate /Provenir/Request in XML")
            app_id = int(req[0].attrib.get("ID"))
        except Exception as e:
            raise RuntimeError(f"Unable to derive app_id from XML; pass --app-id. Error: {e}")

    report = reconcile(app_id=app_id, xml_content=xml_content, xml_source=xml_source)

    out_dir = root_dir / "metrics"
    out_dir.mkdir(exist_ok=True)

    if args.output_json:
        out_path = Path(args.output_json)
        if not out_path.is_absolute():
            out_path = root_dir / out_path
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        out_path = out_dir / f"kv_reconcile_{app_id}_{ts}.json"

    # Serialize dataclasses
    json_obj = {
        "app_id": report.app_id,
        "target_schema": report.target_schema,
        "xml_source": report.xml_source,
        "generated_at_utc": report.generated_at_utc,
        "contract_kv_mapping_count": report.contract_kv_mapping_count,
        "summary": report.summary,
        "contract_issues": report.contract_issues,
        "rows": [
            {
                **asdict(r),
                # Flatten mapping spec for easier consumption
                "mapping": asdict(r.mapping),
            }
            for r in report.rows
        ],
    }

    out_path.write_text(json.dumps(json_obj, indent=2), encoding="utf-8")

    # Console summary
    print("\nKV Reconcile Summary")
    print("-" * 80)
    print(f"app_id: {report.app_id}")
    print(f"schema: {report.target_schema}")
    print(f"xml:    {report.xml_source}")
    print(f"mappings: {report.contract_kv_mapping_count}")
    print(f"PASS={report.summary['PASS']} WARN={report.summary['WARN']} FAIL={report.summary['FAIL']} TOTAL={report.summary['TOTAL']}")
    print(f"report: {out_path}")

    if report.contract_issues:
        print("\nContract issues/smells (top 10):")
        for msg in report.contract_issues[:10]:
            print(f"- {msg}")

    fails = [r for r in report.rows if r.status == "FAIL"]
    if fails:
        print("\nTop mismatches (first 15):")
        for r in fails[:15]:
            mt = r.mapping_type_normalized
            print(f"- {r.mapping.target_table}:{mt} {r.mapping.xml_attribute} -> issues={'; '.join(r.issues)}")
            print(f"  xml_raw={r.xml_raw_value!r}")
            print(f"  expected={r.expected_record}")
            print(f"  dest={r.dest_record}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
