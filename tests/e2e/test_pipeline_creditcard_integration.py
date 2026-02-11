"""
Automated E2E integration test for the CC (CreditCard) pipeline.

Exercises the full pipeline: Validate → Parse XML → Extract Contacts →
Map Data → Insert into Database → Verify row contents → Cleanup.

Converted from manual_test_pipeline_full_integration_cc.py to pytest
so it runs in the standard test suite.  Marked ``@pytest.mark.integration``
to allow selective execution.

Requirements:
    - Database connectivity (DEV server via config_manager)
    - CC contract: config/mapping_contract.json
    - Sample XML: config/samples/sample-source-xml-contact-test.xml
    - Env var ``XMLCONVERSION_E2E_ALLOW_DB_DELETE=1`` to enable post-test cleanup

Usage::

    pytest tests/e2e/test_pipeline_creditcard_integration.py -v
    pytest tests/e2e/test_pipeline_creditcard_integration.py -v -k "scores"
"""

import os
import sys
import time
import logging

import pyodbc
import pytest
from lxml import etree
from pathlib import Path

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser
from xml_extractor.validation.pre_processing_validator import PreProcessingValidator

# ── Constants ─────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CC_CONTRACT_RELPATH = "config/mapping_contract.json"
CC_SAMPLE_XML_PATH = (
    PROJECT_ROOT / "config" / "samples" / "sample-source-xml-contact-test.xml"
)

# Original con_ids in the sample XML (rewritten per test run)
ORIGINAL_PR_CON_ID = "738936"
ORIGINAL_AUTHU_CON_ID = "738937"

# FK-ordered table insertion sequence for CC
TABLE_INSERTION_ORDER = [
    "app_base",
    "app_contact_base",
    "app_operational_cc",
    "app_pricing_cc",
    "app_transactional_cc",
    "app_solicited_cc",
    "app_contact_address",
    "app_contact_employment",
    "app_report_results_lookup",
    "app_historical_lookup",
    "scores",
    "indicators",
]

IDENTITY_TABLES = {"app_base", "app_contact_base"}

logger = logging.getLogger(__name__)


# ── Fixtures ──────────────────────────────────────────────────────────


def _load_contract_schema() -> str:
    """Return target_schema from the CC mapping contract."""
    import json

    contract_path = PROJECT_ROOT / CC_CONTRACT_RELPATH
    with open(contract_path) as f:
        contract = json.load(f)
    return contract.get("target_schema", "migration")


def _qualify(table: str, schema: str) -> str:
    return f"{schema}.{table}"


@pytest.fixture(scope="module")
def target_schema():
    return _load_contract_schema()


@pytest.fixture(scope="module")
def connection_string():
    config = get_config_manager()
    return config.get_database_connection_string()


@pytest.fixture(scope="module")
def test_app_id():
    """Generate a unique test app_id from the current timestamp.

    Can be overridden with env var ``XMLCONVERSION_E2E_APP_ID``.
    """
    env_id = os.environ.get("XMLCONVERSION_E2E_APP_ID")
    if env_id:
        return int(env_id)
    # Use timestamp-based id in a range unlikely to collide (800_000+)
    return 800_000 + int(time.time()) % 100_000


@pytest.fixture(scope="module")
def cc_pipeline_result(connection_string, test_app_id, target_schema):
    """Run the full CC pipeline once and yield results for all verification tests.

    This fixture:
    1. Loads sample XML, rewrites con_ids to avoid collisions
    2. Validates, parses XML, extracts contacts, maps data
    3. Inserts into the database
    4. Yields result dict for verification tests
    5. Cleans up test data on teardown (if env var allows)
    """
    # ── Build unique con_ids ──────────────────────────────────────────
    pr_con_id = 900_000_000 + (test_app_id % 100_000_000)
    authu_con_id = pr_con_id + 1

    # ── Load & rewrite XML ────────────────────────────────────────────
    xml_content = CC_SAMPLE_XML_PATH.read_text(encoding="utf-8-sig")
    # Use lxml to reliably rewrite con_ids (XML may have multiple elements
    # with the same con_id)
    xml_root = etree.fromstring(xml_content.encode("utf-8"))
    for el in xml_root.xpath(f"//*[@con_id='{ORIGINAL_PR_CON_ID}']"):
        el.attrib["con_id"] = str(pr_con_id)
    for el in xml_root.xpath(f"//*[@con_id='{ORIGINAL_AUTHU_CON_ID}']"):
        el.attrib["con_id"] = str(authu_con_id)
    rewritten_xml = etree.tostring(xml_root, encoding="utf-8").decode("utf-8")

    # ── Validate ──────────────────────────────────────────────────────
    validator = PreProcessingValidator()
    validation = validator.validate_xml_for_processing(
        rewritten_xml, "cc_e2e_test"
    )
    assert validation.is_valid, f"Validation failed: {validation.validation_errors}"
    assert validation.can_process, "XML should be processable"
    assert len(validation.valid_contacts) == 2, "Must find PR + AUTHU contacts"

    # ── Parse ─────────────────────────────────────────────────────────
    parser = XMLParser()
    root = parser.parse_xml_stream(rewritten_xml)
    xml_data = parser.extract_elements(root)
    assert root is not None, "XML parsing must succeed"
    assert len(xml_data) > 0, "Must extract elements"

    # ── Map ───────────────────────────────────────────────────────────
    mapper = DataMapper(
        mapping_contract_path=CC_CONTRACT_RELPATH, log_level="ERROR"
    )
    app_id_str = str(test_app_id)
    mapped_data = mapper.map_xml_to_database(
        xml_data, app_id_str, validation.valid_contacts, root
    )
    assert mapped_data, "Mapping must produce data"

    # ── Insert ────────────────────────────────────────────────────────
    engine = MigrationEngine(
        connection_string, mapping_contract_path=CC_CONTRACT_RELPATH
    )

    for table_name in TABLE_INSERTION_ORDER:
        rows = mapped_data.get(table_name, [])
        if not rows:
            continue
        use_identity = table_name in IDENTITY_TABLES
        try:
            engine.execute_bulk_insert(
                rows, table_name, enable_identity_insert=use_identity
            )
        except Exception as exc:
            pytest.fail(f"Insert into {table_name} failed: {exc}")

    # ── Yield to tests ────────────────────────────────────────────────
    yield {
        "app_id": test_app_id,
        "pr_con_id": pr_con_id,
        "authu_con_id": authu_con_id,
        "schema": target_schema,
        "mapped_data": mapped_data,
        "connection_string": connection_string,
    }

    # ── Teardown: Cleanup ─────────────────────────────────────────────
    if os.environ.get("XMLCONVERSION_E2E_ALLOW_DB_DELETE", "").strip() != "1":
        logger.info(
            "Skipping DB cleanup (set XMLCONVERSION_E2E_ALLOW_DB_DELETE=1)"
        )
        return

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            # Clean KV tables first (no FK cascade from app_base)
            for tbl in [
                "scores",
                "indicators",
                "app_report_results_lookup",
                "app_historical_lookup",
                "processing_log",
            ]:
                try:
                    cursor.execute(
                        f"DELETE FROM {_qualify(tbl, target_schema)} WHERE app_id = ?",
                        test_app_id,
                    )
                except Exception:
                    pass
            # app_base cascade deletes remaining child tables
            try:
                cursor.execute(
                    f"DELETE FROM {_qualify('app_base', target_schema)} WHERE app_id = ?",
                    test_app_id,
                )
            except Exception:
                pass
            conn.commit()
            logger.info(f"Cleaned up test data for app_id {test_app_id}")
    except Exception as exc:
        logger.warning(f"Cleanup warning: {exc}")


# ── Helpers ───────────────────────────────────────────────────────────


def _query_one(conn_str, schema, table, columns, app_id):
    """Return a single row dict from *table* WHERE app_id = ?."""
    cols = ", ".join(columns)
    sql = f"SELECT {cols} FROM {_qualify(table, schema)} WHERE app_id = ?"
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, app_id)
        row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))


def _query_all(conn_str, schema, sql, params):
    """Return all rows as list of tuples."""
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return cursor.fetchall()


# ══════════════════════════════════════════════════════════════════════
# Verification Tests
# ══════════════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestCCPipelineAppBase:
    """Verify app_base row after E2E insertion."""

    def test_app_base_exists(self, cc_pipeline_result):
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_base",
            ["app_id", "app_type_enum", "decision_enum"],
            r["app_id"],
        )
        assert row is not None, "app_base row must exist"

    def test_decision_enum(self, cc_pipeline_result):
        """APPRV → decision_enum = 50 (CC contract mapping)."""
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_base",
            ["decision_enum"],
            r["app_id"],
        )
        assert row["decision_enum"] == 50

    def test_receive_date(self, cc_pipeline_result):
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_base",
            ["receive_date"],
            r["app_id"],
        )
        assert row["receive_date"] is not None


@pytest.mark.integration
class TestCCPipelineContacts:
    """Verify app_contact_base rows (PR + AUTHU)."""

    def test_two_contacts(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT con_id, contact_type_enum, first_name, last_name "
            f"FROM {_qualify('app_contact_base', r['schema'])} "
            f"WHERE app_id = ? ORDER BY contact_type_enum"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 2

    def test_pr_contact_is_last_valid(self, cc_pipeline_result):
        """PR contact should be TOM BARKER (last valid), not MARK WOODFIELD."""
        r = cc_pipeline_result
        sql = (
            f"SELECT first_name, last_name, contact_type_enum "
            f"FROM {_qualify('app_contact_base', r['schema'])} "
            f"WHERE app_id = ? AND con_id = ?"
        )
        rows = _query_all(
            r["connection_string"],
            r["schema"],
            sql,
            (r["app_id"], r["pr_con_id"]),
        )
        assert len(rows) == 1
        assert rows[0][0] == "TOM"
        assert rows[0][1] == "BARKER"
        assert rows[0][2] == 281  # PR enum

    def test_authu_contact(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT first_name, last_name, contact_type_enum "
            f"FROM {_qualify('app_contact_base', r['schema'])} "
            f"WHERE app_id = ? AND con_id = ?"
        )
        rows = _query_all(
            r["connection_string"],
            r["schema"],
            sql,
            (r["app_id"], r["authu_con_id"]),
        )
        assert len(rows) == 1
        assert rows[0][0] == "AUTH"
        assert rows[0][1] == "USER"
        assert rows[0][2] == 280  # AUTHU enum

    def test_pr_phone_fields(self, cc_pipeline_result):
        """home_phone and cell_phone from CURR address of last valid PR contact."""
        r = cc_pipeline_result
        sql = (
            f"SELECT home_phone, cell_phone "
            f"FROM {_qualify('app_contact_base', r['schema'])} "
            f"WHERE app_id = ? AND con_id = ?"
        )
        rows = _query_all(
            r["connection_string"],
            r["schema"],
            sql,
            (r["app_id"], r["pr_con_id"]),
        )
        assert len(rows) == 1
        home_phone = str(rows[0][0]).strip() if rows[0][0] else None
        cell_phone = str(rows[0][1]).strip() if rows[0][1] else None
        assert home_phone == "5051002300"
        assert cell_phone == "5555555555"


@pytest.mark.integration
class TestCCPipelineOperational:
    """Verify app_operational_cc row with calculated fields."""

    def test_cb_score_factor_type_1(self, cc_pipeline_result):
        """Complex CASE WHEN → 'AJ' (population_assignment=CM, date > 2023-10-11)."""
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["cb_score_factor_type_1"],
            r["app_id"],
        )
        assert row is not None
        assert row["cb_score_factor_type_1"] == "AJ"

    def test_cb_score_factor_type_2_null(self, cc_pipeline_result):
        """Falls through to ELSE '' → NULL in DB."""
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["cb_score_factor_type_2"],
            r["app_id"],
        )
        assert row["cb_score_factor_type_2"] is None

    def test_assigned_to(self, cc_pipeline_result):
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["assigned_to"],
            r["app_id"],
        )
        assert row["assigned_to"] == "test-tacular@testy.com"

    def test_backend_fico_grade(self, cc_pipeline_result):
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["backend_fico_grade"],
            r["app_id"],
        )
        assert row["backend_fico_grade"] == "F"

    def test_cb_score_factor_code_1(self, cc_pipeline_result):
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["cb_score_factor_code_1"],
            r["app_id"],
        )
        assert row["cb_score_factor_code_1"] == "AA ANYTHIN"

    def test_meta_url(self, cc_pipeline_result):
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["meta_url"],
            r["app_id"],
        )
        assert row["meta_url"] == "meta-bro-url.com"

    def test_priority_enum(self, cc_pipeline_result):
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["priority_enum"],
            r["app_id"],
        )
        assert row["priority_enum"] == 80

    def test_housing_monthly_payment(self, cc_pipeline_result):
        """From last_valid_pr_contact CURR address residence_monthly_pymnt=893.55."""
        r = cc_pipeline_result
        row = _query_one(
            r["connection_string"],
            r["schema"],
            "app_operational_cc",
            ["housing_monthly_payment"],
            r["app_id"],
        )
        assert abs(float(row["housing_monthly_payment"]) - 893.55) < 0.01


@pytest.mark.integration
class TestCCPipelineContactAddress:
    """Verify app_contact_address rows with calculated months_at_address."""

    def test_three_address_records(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT ca.con_id, ca.city, ca.months_at_address "
            f"FROM {_qualify('app_contact_address', r['schema'])} ca "
            f"INNER JOIN {_qualify('app_contact_base', r['schema'])} cb "
            f"ON ca.con_id = cb.con_id "
            f"WHERE cb.app_id = ? ORDER BY ca.con_id, ca.months_at_address"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 3

    def test_calculated_months_at_address(self, cc_pipeline_result):
        """months + (years * 12): expect [35, 53, 27] sorted."""
        r = cc_pipeline_result
        sql = (
            f"SELECT ca.months_at_address "
            f"FROM {_qualify('app_contact_address', r['schema'])} ca "
            f"INNER JOIN {_qualify('app_contact_base', r['schema'])} cb "
            f"ON ca.con_id = cb.con_id "
            f"WHERE cb.app_id = ? ORDER BY ca.con_id, ca.months_at_address"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        actual = [int(row[0]) for row in rows]
        assert actual == [35, 53, 27], f"Expected [35, 53, 27] but got {actual}"


@pytest.mark.integration
class TestCCPipelineContactEmployment:
    """Verify app_contact_employment rows with calculated fields."""

    def test_two_employment_records(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT ce.con_id, ce.business_name, ce.monthly_salary, ce.months_at_job "
            f"FROM {_qualify('app_contact_employment', r['schema'])} ce "
            f"INNER JOIN {_qualify('app_contact_base', r['schema'])} cb "
            f"ON ce.con_id = cb.con_id "
            f"WHERE cb.app_id = ? ORDER BY ce.con_id"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 2

    def test_home_style_jive_salary(self, cc_pipeline_result):
        """ANNUM salary 120000.656 / 12 ≈ 10000.05."""
        r = cc_pipeline_result
        sql = (
            f"SELECT monthly_salary, months_at_job "
            f"FROM {_qualify('app_contact_employment', r['schema'])} ce "
            f"INNER JOIN {_qualify('app_contact_base', r['schema'])} cb "
            f"ON ce.con_id = cb.con_id "
            f"WHERE cb.app_id = ? AND ce.business_name = 'HOME-STYLE JIVE'"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert abs(float(rows[0][0]) - 10000.05) < 0.01
        assert int(rows[0][1]) == 18  # 6 + (1 * 12)

    def test_prev_employment_salary(self, cc_pipeline_result):
        """PREV employment: MONTH salary 4000 * 12 = 48000, months = 32+(1*12)=44.

        Note: XML has b_name='' for this record so business_name is NULL in DB.
        Match by employment_type_enum=351 (PREV).
        """
        r = cc_pipeline_result
        sql = (
            f"SELECT ce.monthly_salary, ce.months_at_job "
            f"FROM {_qualify('app_contact_employment', r['schema'])} ce "
            f"INNER JOIN {_qualify('app_contact_base', r['schema'])} cb "
            f"ON ce.con_id = cb.con_id "
            f"WHERE cb.app_id = ? AND ce.employment_type_enum = 351"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert float(rows[0][0]) == 48000.0
        assert int(rows[0][1]) == 44  # 32 + (1 * 12)


@pytest.mark.integration
class TestCCPipelineScores:
    """Verify scores rows from add_score mappings."""

    def test_key_scores(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT score_identifier, score "
            f"FROM {_qualify('scores', r['schema'])} "
            f"WHERE app_id = ?"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) >= 8

        by_id = {row[0]: row[1] for row in rows}

        assert by_id["EX_DIE"] == 956
        assert by_id["EX_TIE"] == 929
        assert by_id["AJ"] == 910  # EX_FICO_08
        assert by_id["prescreen_fico_score"] == 915
        assert by_id["prescreen_risk_score"] == 978
        assert by_id["DIEPLUS"] == 978  # 978.14 rounded to int
        assert by_id["V4"] == 911  # Vantage_Score_EX
        assert by_id["00V60"] == 988  # Vantage_Score_TU


@pytest.mark.integration
class TestCCPipelineIndicators:
    """Verify indicators rows from add_indicator mappings."""

    def test_fraud_indicators(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT indicator, value "
            f"FROM {_qualify('indicators', r['schema'])} "
            f"WHERE app_id = ?"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) > 0

        by_name = {row[0]: row[1] for row in rows}
        assert by_name.get("internal_fraud_address_ind") == "1"
        assert by_name.get("internal_fraud_ssn_ind") == "1"


@pytest.mark.integration
class TestCCPipelineHistoricalLookup:
    """Verify app_historical_lookup rows from add_history mappings."""

    def test_supervisor_rev_ind(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT name, source, value "
            f"FROM {_qualify('app_historical_lookup', r['schema'])} "
            f"WHERE app_id = ? AND name = '[supervisor_rev_ind]'"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert rows[0][2] == "Y"
        assert rows[0][1] == "[app_product]"

    def test_vantage_scores_in_history(self, cc_pipeline_result):
        """Vantage scores should exist in BOTH scores AND historical_lookup."""
        r = cc_pipeline_result
        sql = (
            f"SELECT name, value "
            f"FROM {_qualify('app_historical_lookup', r['schema'])} "
            f"WHERE app_id = ? AND name IN ('[Vantage_Score_EX]', '[Vantage_Score_TU]')"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        by_name = {row[0]: row[1] for row in rows}
        assert by_name.get("[Vantage_Score_EX]") == "911"
        assert by_name.get("[Vantage_Score_TU]") == "988"


@pytest.mark.integration
class TestCCPipelineReportResultsLookup:
    """Verify app_report_results_lookup rows from add_report_lookup mappings."""

    def test_instantid_score(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT name, value, source_report_key "
            f"FROM {_qualify('app_report_results_lookup', r['schema'])} "
            f"WHERE app_id = ? AND name = 'InstantID_Score'"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert rows[0][1] == "950"
        assert rows[0][2] == "IDV"

    def test_giact_response(self, cc_pipeline_result):
        r = cc_pipeline_result
        sql = (
            f"SELECT name, value, source_report_key "
            f"FROM {_qualify('app_report_results_lookup', r['schema'])} "
            f"WHERE app_id = ? AND name = 'GIACT_Response'"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert rows[0][1] == "9 save me!"
        assert rows[0][2] == "GIACT"
