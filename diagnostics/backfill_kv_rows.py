"""\
KV Backfill (Insert-Only) - Fill missing KV rows for an app_id

Purpose
- Insert missing rows for the KV tables produced by row-creating mapping types:
  - add_score(<identifier>) -> [target_schema].[scores]
  - add_indicator(<name>)   -> [target_schema].[indicators]
  - add_history             -> [target_schema].[app_historical_lookup]
  - add_report_lookup(<key?>)-> [target_schema].[app_report_results_lookup]

Guarantees / Safety
- INSERT-ONLY.
- No DDL (no CREATE/ALTER/DROP).
- No DELETE/TRUNCATE.
- Only inserts rows that are missing in destination for the given app_id.

Usage
- Dry-run (default):
  python diagnostics/backfill_kv_rows.py --app-id 443306

- Apply inserts:
  python diagnostics/backfill_kv_rows.py --app-id 443306 --apply

- Use local XML file instead of DB source fetch:
  python diagnostics/backfill_kv_rows.py --xml-file config/samples/sample-source-xml-contact-test.xml --apply

Outputs
- Writes a JSON report to metrics/kv_backfill_<app_id>_<timestamp>.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyodbc

# Ensure workspace root is importable when running as a script
WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator

logger = logging.getLogger(__name__)


KV_TABLES = (
    "scores",
    "indicators",
    "app_historical_lookup",
    "app_report_results_lookup",
)


@dataclass
class BackfillResult:
    app_id: int
    target_schema: str
    xml_source: str
    generated_at_utc: str
    dry_run: bool

    existing_counts: Dict[str, int]
    missing_counts: Dict[str, int]
    inserted_counts: Dict[str, int]

    missing_examples: Dict[str, List[Dict[str, Any]]]


def _load_contract_json(contract_path: Path) -> Dict[str, Any]:
    return json.loads(contract_path.read_text(encoding="utf-8-sig"))


def _fetch_source_xml_from_db(conn: pyodbc.Connection, source_table: str, source_column: str, app_id: int) -> Optional[str]:
    cursor = conn.cursor()
    attempts = [f"dbo.{source_table}", source_table]
    for table in attempts:
        try:
            cursor.execute(f"SELECT {source_column} FROM {table} WITH (NOLOCK) WHERE app_id = ?", app_id)
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception:
            continue
    return None


def _query_dest_kv_keys(conn: pyodbc.Connection, target_schema: str, app_id: int) -> Dict[str, Any]:
    cursor = conn.cursor()
    qualified = lambda t: f"[{target_schema}].[{t}]"

    cursor.execute(f"SELECT score_identifier FROM {qualified('scores')} WITH (NOLOCK) WHERE app_id = ?", (app_id,))
    scores = {(r[0],) for r in cursor.fetchall()}

    cursor.execute(f"SELECT indicator FROM {qualified('indicators')} WITH (NOLOCK) WHERE app_id = ?", (app_id,))
    indicators = {(r[0],) for r in cursor.fetchall()}

    cursor.execute(
        f"SELECT name, source FROM {qualified('app_historical_lookup')} WITH (NOLOCK) WHERE app_id = ?",
        (app_id,),
    )
    history = {(r[0], r[1]) for r in cursor.fetchall()}

    cursor.execute(
        f"SELECT name FROM {qualified('app_report_results_lookup')} WITH (NOLOCK) WHERE app_id = ?",
        (app_id,),
    )
    report = {(r[0],) for r in cursor.fetchall()}

    return {
        "scores": scores,
        "indicators": indicators,
        "app_historical_lookup": history,
        "app_report_results_lookup": report,
    }


def _record_key(table: str, record: Dict[str, Any]) -> Tuple[Any, ...]:
    if table == "scores":
        return (record.get("score_identifier"),)
    if table == "indicators":
        return (record.get("indicator"),)
    if table == "app_historical_lookup":
        return (record.get("name"), record.get("source"))
    if table == "app_report_results_lookup":
        return (record.get("name"),)
    raise ValueError(f"Unsupported table for keying: {table}")


def _normalize_app_id(app_id: Any) -> int:
    if isinstance(app_id, int):
        return app_id
    s = str(app_id).strip()
    if not s.isdigit():
        raise ValueError(f"app_id must be an integer; got {app_id!r}")
    return int(s)


def _compute_mapper_kv_records(app_id: int, xml_content: str, contract_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    validator = PreProcessingValidator()
    validation = validator.validate_xml_for_processing(xml_content, source_record_id="kv_backfill")
    if not validation.is_valid or not validation.can_process:
        errors = getattr(validation, "validation_errors", None) or []
        raise RuntimeError(f"XML failed pre-processing validation: {errors}")

    parser = XMLParser()
    xml_root = parser.parse_xml_stream(xml_content)
    xml_data = parser.extract_elements(xml_root)

    mapper = DataMapper(mapping_contract_path=str(contract_path))
    mapped = mapper.map_xml_to_database(xml_data, str(app_id), validation.valid_contacts, xml_root)

    return {t: list(mapped.get(t, [])) for t in KV_TABLES}


def _insert_missing(conn: pyodbc.Connection, target_schema: str, table: str, records: List[Dict[str, Any]]) -> int:
    if not records:
        return 0

    cursor = conn.cursor()
    cursor.fast_executemany = True
    qualified = lambda t: f"[{target_schema}].[{t}]"

    if table == "scores":
        sql = f"INSERT INTO {qualified('scores')} (app_id, score_identifier, score) VALUES (?, ?, ?)"
        params = [(r["app_id"], r["score_identifier"], r["score"]) for r in records]
    elif table == "indicators":
        sql = f"INSERT INTO {qualified('indicators')} (app_id, indicator, value) VALUES (?, ?, ?)"
        params = [(r["app_id"], r["indicator"], r["value"]) for r in records]
    elif table == "app_historical_lookup":
        sql = f"INSERT INTO {qualified('app_historical_lookup')} (app_id, name, source, value) VALUES (?, ?, ?, ?)"
        params = [(r["app_id"], r["name"], r.get("source"), r["value"]) for r in records]
    elif table == "app_report_results_lookup":
        sql = f"INSERT INTO {qualified('app_report_results_lookup')} (app_id, name, value, source_report_key) VALUES (?, ?, ?, ?)"
        params = [(r["app_id"], r["name"], r["value"], r.get("source_report_key")) for r in records]
    else:
        raise ValueError(f"Unsupported KV table: {table}")

    cursor.executemany(sql, params)
    return cursor.rowcount if cursor.rowcount != -1 else len(records)


def main() -> int:
    ap = argparse.ArgumentParser(description="Insert-only backfill for KV mapping tables")
    ap.add_argument("--app-id", type=int, default=None, help="app_id to backfill (fetches XML from DB)")
    ap.add_argument("--xml-file", type=str, default=None, help="Path to XML file to backfill")
    ap.add_argument("--apply", action="store_true", help="Apply inserts (default is dry-run)")
    ap.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Optional explicit output path for the JSON report",
    )

    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    root_dir = Path(__file__).parent.parent
    contract_path = root_dir / "config" / "mapping_contract.json"
    contract_json = _load_contract_json(contract_path)

    target_schema = contract_json.get("target_schema", "dbo") or "dbo"

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

    app_id = args.app_id

    if xml_content is None:
        if app_id is None:
            raise SystemExit("Provide either --xml-file or --app-id")
        with pyodbc.connect(conn_str) as conn:
            source_table = contract_json.get("source_table", "app_xml_staging")
            source_column = contract_json.get("source_column", "app_XML")
            xml_content = _fetch_source_xml_from_db(conn, source_table, source_column, app_id)
            if not xml_content:
                raise RuntimeError(f"No source XML found for app_id={app_id} in {source_table}.{source_column}")
            xml_source = f"DB:{source_table}.{source_column}"

    if app_id is None:
        # Derive app_id from XML Request/@ID via pre-processing validator
        validator = PreProcessingValidator()
        validation = validator.validate_xml_for_processing(xml_content, source_record_id="kv_backfill")
        app_id = _normalize_app_id(validation.app_id)

    dry_run = not args.apply
    normalized_app_id = _normalize_app_id(app_id)

    mapper_records = _compute_mapper_kv_records(normalized_app_id, xml_content, contract_path)

    existing_counts: Dict[str, int] = {}
    missing_counts: Dict[str, int] = {t: 0 for t in KV_TABLES}
    inserted_counts: Dict[str, int] = {t: 0 for t in KV_TABLES}
    missing_examples: Dict[str, List[Dict[str, Any]]] = {t: [] for t in KV_TABLES}

    with pyodbc.connect(conn_str) as conn:
        conn.autocommit = False
        existing_keys = _query_dest_kv_keys(conn, target_schema=target_schema, app_id=normalized_app_id)
        existing_counts = {t: len(existing_keys[t]) for t in KV_TABLES}

        missing_by_table: Dict[str, List[Dict[str, Any]]] = {t: [] for t in KV_TABLES}

        for table in KV_TABLES:
            for record in mapper_records.get(table, []):
                # Enforce correct app_id type
                record = dict(record)
                record["app_id"] = normalized_app_id

                key = _record_key(table, record)
                if key in existing_keys[table]:
                    continue
                missing_by_table[table].append(record)

            missing_counts[table] = len(missing_by_table[table])
            missing_examples[table] = missing_by_table[table][:10]

        if dry_run:
            conn.rollback()
        else:
            try:
                for table in KV_TABLES:
                    inserted_counts[table] = _insert_missing(conn, target_schema, table, missing_by_table[table])
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    result = BackfillResult(
        app_id=normalized_app_id,
        target_schema=target_schema,
        xml_source=xml_source,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        dry_run=dry_run,
        existing_counts=existing_counts,
        missing_counts=missing_counts,
        inserted_counts=inserted_counts,
        missing_examples=missing_examples,
    )

    out_dir = root_dir / "metrics"
    out_dir.mkdir(exist_ok=True)

    if args.output_json:
        out_path = Path(args.output_json)
        if not out_path.is_absolute():
            out_path = root_dir / out_path
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        out_path = out_dir / f"kv_backfill_{normalized_app_id}_{ts}.json"

    out_path.write_text(json.dumps(result.__dict__, indent=2), encoding="utf-8")

    print("\nKV Backfill Summary")
    print("-" * 80)
    print(f"app_id:   {result.app_id}")
    print(f"schema:   {result.target_schema}")
    print(f"xml:      {result.xml_source}")
    print(f"mode:     {'DRY-RUN' if result.dry_run else 'APPLY'}")
    print(f"existing: {result.existing_counts}")
    print(f"missing:  {result.missing_counts}")
    if not result.dry_run:
        print(f"inserted: {result.inserted_counts}")
    print(f"report:   {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
