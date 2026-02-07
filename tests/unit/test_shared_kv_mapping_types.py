import json
import os
import sys
from pathlib import Path

import pytest

from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.models import MappingContract, FieldMapping, RelationshipMapping


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def load_fixture_279971():
    sample_path = Path(__file__).parent.parent.parent / "config" / "samples" / "xml_files" / "sample-source-xml--279971.xml"
    with open(sample_path, "r", encoding="utf-8") as f:
        sample_xml = f.read()

    contract_path = Path(__file__).parent.parent.parent / "config" / "mapping_contract.json"
    with open(contract_path, "r", encoding="utf-8-sig") as f:
        contract_json = json.load(f)

    contract_json["mappings"] = [FieldMapping(**fm) for fm in contract_json["mappings"]]
    if "relationships" in contract_json and contract_json["relationships"]:
        contract_json["relationships"] = [RelationshipMapping(**rm) for rm in contract_json["relationships"]]

    contract = MappingContract(**contract_json)
    mapper = DataMapper(mapping_contract_path=str(contract_path))
    parser = XMLParser()

    return {
        "sample_xml": sample_xml,
        "mapper": mapper,
        "parser": parser,
        "contract": contract,
    }


class TestSharedKeyValueMappingTypes:
    @pytest.fixture(scope="class")
    def fixture(self):
        return load_fixture_279971()

    def test_add_score_creates_score_rows(self, fixture):
        xml_root = fixture["parser"].parse_xml_stream(fixture["sample_xml"])
        xml_data = fixture["parser"].extract_elements(xml_root)

        mapped_tables = fixture["mapper"].apply_mapping_contract(xml_data, fixture["contract"], xml_root=xml_root)
        scores = mapped_tables.get("scores", [])

        assert scores, "Expected at least one scores record"

        by_id = {rec.get("score_identifier"): rec.get("score") for rec in scores}

        assert by_id.get("EX_DIE") == 16
        assert by_id.get("EX_TIE") == 36
        assert by_id.get("AJ") == 503
        assert by_id.get("prescreen_fico_score") == 597
        assert by_id.get("prescreen_risk_score") == 302
        assert by_id.get("V4") == 777
        assert by_id.get("00V60") == 606
        assert by_id.get("TU_TIE") == 777
        assert by_id.get("TU_DIE") == 444
        assert by_id.get("00W83") == 555
        assert by_id.get("DIEPLUS") == 546

    def test_add_indicator_creates_indicator_rows(self, fixture):
        xml_root = fixture["parser"].parse_xml_stream(fixture["sample_xml"])
        xml_data = fixture["parser"].extract_elements(xml_root)

        mapped_tables = fixture["mapper"].apply_mapping_contract(xml_data, fixture["contract"], xml_root=xml_root)
        indicators = mapped_tables.get("indicators", [])

        assert indicators, "Expected at least one indicators record"

        by_name = {rec.get("indicator"): rec.get("value") for rec in indicators}
        assert by_name.get("internal_fraud_address_ind") == "1"
        assert by_name.get("internal_fraud_ssn_ind") == "1"

    def test_add_history_creates_historical_rows(self, fixture):
        xml_root = fixture["parser"].parse_xml_stream(fixture["sample_xml"])
        xml_data = fixture["parser"].extract_elements(xml_root)

        mapped_tables = fixture["mapper"].apply_mapping_contract(xml_data, fixture["contract"], xml_root=xml_root)
        history = mapped_tables.get("app_historical_lookup", [])

        assert history, "Expected at least one app_historical_lookup record"

        # Look for a couple of known fields from sample XML
        history_pairs = {(rec.get("name"), rec.get("value")) for rec in history}
        assert ("[risk_model_score_JH]", "222") in history_pairs
        assert ("[supervisor_rev_ind]", "Y") in history_pairs

        # Verify source derived from xml_path rightmost segment
        any_source = next((rec.get("source") for rec in history if rec.get("name") == "[risk_model_score_JH]"), None)
        assert any_source == "[app_product]"

    def test_add_report_lookup_creates_report_rows(self, fixture):
        xml_root = fixture["parser"].parse_xml_stream(fixture["sample_xml"])
        xml_data = fixture["parser"].extract_elements(xml_root)

        mapped_tables = fixture["mapper"].apply_mapping_contract(xml_data, fixture["contract"], xml_root=xml_root)
        report = mapped_tables.get("app_report_results_lookup", [])

        assert report, "Expected at least one app_report_results_lookup record"

        by_name = {rec.get("name"): rec for rec in report}

        assert by_name["GIACT_Response"]["value"] == "some response saved to report results"
        assert by_name["GIACT_Response"].get("source_report_key") == "GIACT"

        assert by_name["InstantID_Score"]["value"] == "another response saved to report results"
        assert by_name["InstantID_Score"]["source_report_key"] == "IDV"

        assert by_name["VeridQA_Result"]["value"] == "a third result saved to report results"
        assert by_name["VeridQA_Result"].get("source_report_key") == "VERID"
