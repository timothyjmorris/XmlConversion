import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.utils import StringUtils
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator


KV_TABLES = {
    "scores",
    "indicators",
    "app_historical_lookup",
    "app_report_results_lookup",
}


def _normalize_mapping_types(mapping_types: Any) -> List[str]:
    if mapping_types is None:
        return []
    if isinstance(mapping_types, list):
        return [str(mt).strip() for mt in mapping_types if str(mt).strip()]
    if isinstance(mapping_types, str):
        return [mt.strip() for mt in mapping_types.split(",") if mt.strip()]
    return [str(mapping_types).strip()]


def _mapping_type_name_and_param(mapping_type: str) -> Tuple[str, Optional[str]]:
    mt = (mapping_type or "").strip()
    if not mt:
        return "", None
    if "(" in mt and mt.endswith(")"):
        name = mt.split("(", 1)[0].strip()
        param = mt.split("(", 1)[1][:-1].strip()
        return name, param or None
    return mt, None


def _derive_source_from_xml_path(xml_path: str) -> str:
    trimmed = (xml_path or "").strip()
    if trimmed.endswith("/"):
        trimmed = trimmed[:-1]
    return trimmed.rsplit("/", 1)[-1] if "/" in trimmed else trimmed


def _is_meaningful_kv_value(raw_value: Any) -> bool:
    if not StringUtils.safe_string_check(raw_value):
        return False
    lowered = str(raw_value).strip().lower()
    return lowered not in {"null", "none"}


def _expected_record_from_contract_mapping(mapper: DataMapper, app_id: int, fm: Dict[str, Any], xml_raw: Any) -> Optional[Dict[str, Any]]:
    mapping_types = _normalize_mapping_types(fm.get("mapping_type"))
    data_type = (fm.get("data_type") or "").strip()
    xml_attribute = (fm.get("xml_attribute") or "").strip()
    xml_path = (fm.get("xml_path") or "").strip()

    add_score_mt = next((mt for mt in mapping_types if mt.startswith("add_score")), None)
    if add_score_mt:
        _, identifier = _mapping_type_name_and_param(add_score_mt)
        if xml_raw is None or not str(xml_raw).strip():
            return None
        coerced = mapper.transform_data_types(xml_raw, data_type)
        if coerced is None:
            return None
        return {"app_id": app_id, "score_identifier": identifier, "score": coerced}

    add_indicator_mt = next((mt for mt in mapping_types if mt.startswith("add_indicator")), None)
    if add_indicator_mt:
        if xml_raw is None:
            return None
        truthy_values = {"y", "yes", "true", "t", "1"}
        if str(xml_raw).strip().lower() not in truthy_values:
            return None
        _, indicator_name = _mapping_type_name_and_param(add_indicator_mt)
        return {"app_id": app_id, "indicator": indicator_name, "value": "1"}

    normalized_names = {_mapping_type_name_and_param(mt)[0] for mt in mapping_types}

    if "add_history" in normalized_names:
        if not _is_meaningful_kv_value(xml_raw):
            return None
        source = _derive_source_from_xml_path(xml_path)
        return {
            "app_id": app_id,
            "name": f"[{xml_attribute}]",
            "source": f"[{source}]" if source else None,
            "value": str(xml_raw).strip(),
        }

    if "add_report_lookup" in normalized_names:
        if not _is_meaningful_kv_value(xml_raw):
            return None

        report_key = None
        for mt in mapping_types:
            name, param = _mapping_type_name_and_param(mt)
            if name == "add_report_lookup" and param:
                report_key = param
                break

        record: Dict[str, Any] = {
            "app_id": app_id,
            "name": xml_attribute,
            "value": str(xml_raw).strip(),
        }
        if report_key is not None:
            record["source_report_key"] = report_key
        return record

    return None


def _mapper_has_record(table: str, expected: Dict[str, Any], rows: List[Dict[str, Any]]) -> bool:
    if table == "scores":
        return any(
            r.get("score_identifier") == expected.get("score_identifier") and r.get("score") == expected.get("score")
            for r in rows
        )
    if table == "indicators":
        return any(
            r.get("indicator") == expected.get("indicator") and r.get("value") == expected.get("value") for r in rows
        )
    if table == "app_historical_lookup":
        return any(
            r.get("name") == expected.get("name")
            and r.get("source") == expected.get("source")
            and r.get("value") == expected.get("value")
            for r in rows
        )
    if table == "app_report_results_lookup":
        return any(
            r.get("name") == expected.get("name")
            and r.get("value") == expected.get("value")
            and r.get("source_report_key") == expected.get("source_report_key")
            for r in rows
        )
    return False


class TestPostValidationKvMapperSemantics:
    def test_mapper_produces_expected_kv_records_for_cc_fixture(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        contract_path = root_dir / "config" / "mapping_contract.json"
        contract_json = json.loads(contract_path.read_text(encoding="utf-8-sig"))

        xml_path = root_dir / "config" / "samples" / "sample-source-xml-contact-test.xml"
        xml_content = xml_path.read_text(encoding="utf-8-sig")

        validator = PreProcessingValidator()
        validation = validator.validate_xml_for_processing(xml_content, source_record_id="post_validation")
        assert validation.is_valid and validation.can_process

        app_id = int(validation.app_id)

        parser = XMLParser()
        xml_root = parser.parse_xml_stream(xml_content)
        xml_data = parser.extract_elements(xml_root)

        mapper = DataMapper(mapping_contract_path=str(contract_path), log_level="ERROR")
        mapped = mapper.map_xml_to_database(xml_data, str(app_id), validation.valid_contacts, xml_root)

        # Filter to KV mappings from contract
        kv_mappings = [fm for fm in contract_json.get("mappings", []) if (fm.get("target_table") or "").strip() in KV_TABLES]
        assert kv_mappings, "Expected at least one KV mapping in contract"

        # For each KV mapping with a meaningful value, assert the mapper produced the matching record.
        checked = 0
        for fm in kv_mappings:
            target_table = (fm.get("target_table") or "").strip()

            mapping_types = _normalize_mapping_types(fm.get("mapping_type"))
            if not mapping_types:
                continue

            field_mapping = FieldMapping(
                xml_path=(fm.get("xml_path") or "").strip(),
                xml_attribute=(fm.get("xml_attribute") or "").strip(),
                target_table=target_table,
                target_column="",
                data_type=(fm.get("data_type") or "").strip(),
                mapping_type=mapping_types,
            )

            xml_raw = mapper._extract_value_from_xml(xml_data, field_mapping, context_data=None)
            expected = _expected_record_from_contract_mapping(mapper, app_id, fm, xml_raw)
            if expected is None:
                continue

            rows = list(mapped.get(target_table, []))
            assert _mapper_has_record(target_table, expected, rows), (
                f"Mapper missing expected record for {target_table}:{fm.get('xml_attribute')}. "
                f"Expected={expected}"
            )
            checked += 1

        assert checked >= 10, f"Expected to validate a meaningful number of KV mappings; checked={checked}"
