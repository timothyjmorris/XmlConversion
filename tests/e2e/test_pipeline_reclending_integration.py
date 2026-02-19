"""
Automated E2E integration test for the RL (RecLending) pipeline.

Exercises the full pipeline: Parse XML → Extract Contacts → Map Data →
Insert into Database → Verify row contents → Cleanup.

Converted from manual_test_pipeline_full_integration_rl.py to pytest
so it runs in the standard test suite.  Marked ``@pytest.mark.integration``
to allow selective execution.

Requirements:
    - Database connectivity (DEV server via config_manager)
    - RL contract: config/mapping_contract_rl.json
    - Sample XML: config/samples/xml_files/reclending/sample-source-xml--325725-e2e--rl.xml
    - Env var ``XMLCONVERSION_E2E_ALLOW_DB_DELETE=1`` to enable post-test cleanup

Usage::

    pytest tests/e2e/test_pipeline_reclending_integration.py -v
    pytest tests/e2e/test_pipeline_reclending_integration.py -v -k "scores"
"""

import os
import re
import sys
import time
import logging

import pyodbc
import pytest
from pathlib import Path

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.parsing.xml_parser import XMLParser

# ── Constants ─────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RL_CONTRACT_RELPATH = "config/mapping_contract_rl.json"
RL_SAMPLE_XML_PATH = (
    PROJECT_ROOT
    / "config"
    / "samples"
    / "xml_files"
    / "reclending"
    / "sample-source-xml--325725-e2e--rl.xml"
)

# Original con_ids in the sample XML  (rewritten per test run)
ORIGINAL_PR_CON_ID = "35655"
ORIGINAL_SEC_CON_ID = "35656"

# FK-ordered table insertion sequence
TABLE_INSERTION_ORDER = [
    "app_base",
    "app_contact_base",
    "app_operational_rl",
    "app_pricing_rl",
    "app_transactional_rl",
    "app_dealer_rl",
    "app_contact_address",
    "app_contact_employment",
    "app_collateral_rl",
    "app_warranties_rl",
    "app_policy_exceptions_rl",
    "app_funding_rl",
    "app_funding_contract_rl",
    "app_funding_checklist_rl",
    "app_historical_lookup",
    "scores",
]

IDENTITY_TABLES = {"app_base", "app_contact_base"}

logger = logging.getLogger(__name__)


# ── Fixtures ──────────────────────────────────────────────────────────


def _load_contract_schema() -> str:
    """Return target_schema from the RL mapping contract."""
    import json

    contract_path = PROJECT_ROOT / RL_CONTRACT_RELPATH
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
    # Use timestamp-based id in a range unlikely to collide (700_000+)
    return 700_000 + int(time.time()) % 100_000


@pytest.fixture(scope="module")
def rl_pipeline_result(connection_string, test_app_id, target_schema):
    """Run the full RL pipeline once and yield results for all verification tests.

    This fixture:
    1. Loads sample XML, rewrites con_ids to avoid collisions
    2. Parses XML, extracts contacts, maps data
    3. Inserts into the database
    4. Yields (mapped_data, app_id, pr_con_id, sec_con_id, schema)
    5. Cleans up test data on teardown (if env var allows)
    """
    # ── Build unique con_ids ──────────────────────────────────────────
    pr_con_id = 900_000_000 + (test_app_id % 100_000_000)
    sec_con_id = pr_con_id + 1

    # ── Load & rewrite XML ────────────────────────────────────────────
    xml_content = RL_SAMPLE_XML_PATH.read_text(encoding="utf-8")
    xml_content = xml_content.replace(
        f'con_id="{ORIGINAL_PR_CON_ID}"', f'con_id="{pr_con_id}"'
    )
    xml_content = xml_content.replace(
        f'con_id="{ORIGINAL_SEC_CON_ID}"', f'con_id="{sec_con_id}"'
    )

    # ── Parse ─────────────────────────────────────────────────────────
    parser = XMLParser()
    root = parser.parse_xml_stream(xml_content)
    xml_data = parser.extract_elements(root)
    assert root is not None, "XML parsing must succeed"
    assert len(xml_data) > 0, "Must extract elements"

    # ── Extract contacts ──────────────────────────────────────────────
    mapper = DataMapper(
        mapping_contract_path=RL_CONTRACT_RELPATH, log_level="ERROR"
    )
    mapper._current_xml_root = root
    mapper._current_xml_tree = root
    valid_contacts = mapper._extract_valid_contacts(xml_data)
    assert len(valid_contacts) == 2, "Must find PR + SEC contacts"

    # ── Map ───────────────────────────────────────────────────────────
    app_id_str = str(test_app_id)
    mapped_data = mapper.map_xml_to_database(
        xml_data, app_id_str, valid_contacts, xml_root=root
    )
    assert mapped_data, "Mapping must produce data"

    # ── Insert ────────────────────────────────────────────────────────
    engine = MigrationEngine(
        connection_string, mapping_contract_path=RL_CONTRACT_RELPATH
    )

    for table_name in TABLE_INSERTION_ORDER:
        rows = mapped_data.get(table_name, [])
        if not rows:
            continue
        use_identity = table_name in IDENTITY_TABLES
        try:
            engine.execute_bulk_insert(rows, table_name, enable_identity_insert=use_identity)
        except Exception as exc:
            pytest.fail(f"Insert into {table_name} failed: {exc}")

    # ── Yield to tests ────────────────────────────────────────────────
    yield {
        "app_id": test_app_id,
        "pr_con_id": pr_con_id,
        "sec_con_id": sec_con_id,
        "schema": target_schema,
        "mapped_data": mapped_data,
        "connection_string": connection_string,
    }

    # ── Teardown: Cleanup ─────────────────────────────────────────────
    if os.environ.get("XMLCONVERSION_E2E_ALLOW_DB_DELETE", "").strip() != "1":
        logger.info("Skipping DB cleanup (set XMLCONVERSION_E2E_ALLOW_DB_DELETE=1)")
        return

    try:
        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            for tbl in ["scores", "processing_log"]:
                try:
                    cursor.execute(
                        f"DELETE FROM {_qualify(tbl, target_schema)} WHERE app_id = ?",
                        test_app_id,
                    )
                except Exception:
                    pass
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


# ── Helper ────────────────────────────────────────────────────────────


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
class TestRLPipelineAppBase:
    """Verify app_base row after E2E insertion."""

    def test_app_base_exists(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_base",
            ["app_id", "app_type_enum", "ip_address"],
            r["app_id"],
        )
        assert row is not None, "app_base row must exist"

    def test_app_type_enum(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_base",
            ["app_type_enum"],
            r["app_id"],
        )
        assert row["app_type_enum"] == 39, "MARINE → 39"

    def test_ip_address(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_base",
            ["ip_address"],
            r["app_id"],
        )
        assert "52.201.112.6" in str(row["ip_address"])


@pytest.mark.integration
class TestRLPipelineContacts:
    """Verify app_contact_base rows."""

    def test_two_contacts(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT con_id, contact_type_enum, first_name, last_name "
            f"FROM {_qualify('app_contact_base', r['schema'])} WHERE app_id = ? "
            f"ORDER BY contact_type_enum"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 2

    def test_pr_contact(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT first_name, last_name, contact_type_enum "
            f"FROM {_qualify('app_contact_base', r['schema'])} "
            f"WHERE app_id = ? AND con_id = ?"
        )
        rows = _query_all(
            r["connection_string"], r["schema"], sql,
            (r["app_id"], r["pr_con_id"]),
        )
        assert len(rows) == 1
        assert rows[0][0] == "RHONDA"
        assert rows[0][1] == "WONG"
        assert rows[0][2] == 281  # PR enum

    def test_sec_contact(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT first_name, last_name, contact_type_enum "
            f"FROM {_qualify('app_contact_base', r['schema'])} "
            f"WHERE app_id = ? AND con_id = ?"
        )
        rows = _query_all(
            r["connection_string"], r["schema"], sql,
            (r["app_id"], r["sec_con_id"]),
        )
        assert len(rows) == 1
        assert rows[0][0] == "WARD"
        assert rows[0][1] == "GILLIAN"
        assert rows[0][2] == 282  # SEC enum


@pytest.mark.integration
class TestRLPipelineOperational:
    """Verify app_operational_rl row."""

    def test_assigned_credit_analyst(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_operational_rl",
            ["assigned_credit_analyst"],
            r["app_id"],
        )
        assert row is not None
        assert row["assigned_credit_analyst"] == "joshua.ramsey@merrickbank.com"

    def test_mrv_lead_indicator_pr_enum(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_operational_rl",
            ["mrv_lead_indicator_pr_enum"],
            r["app_id"],
        )
        assert row["mrv_lead_indicator_pr_enum"] == 640

    def test_housing_monthly_payments(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_operational_rl",
            ["housing_monthly_payment_pr", "housing_monthly_payment_sec"],
            r["app_id"],
        )
        assert abs(float(row["housing_monthly_payment_pr"]) - 525.0) < 1
        assert abs(float(row["housing_monthly_payment_sec"]) - 616.0) < 1

    def test_joint_app_flag(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_operational_rl",
            ["joint_app_flag"],
            r["app_id"],
        )
        assert row["joint_app_flag"] in (True, 1)

    def test_cb_score_factor_code_pr_1(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_operational_rl",
            ["cb_score_factor_code_pr_1"],
            r["app_id"],
        )
        assert row["cb_score_factor_code_pr_1"] == "V4_68"


@pytest.mark.integration
class TestRLPipelinePricing:
    """Verify app_pricing_rl row."""

    def test_pricing_values(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_pricing_rl",
            ["loan_amount", "selling_price", "loan_term_months"],
            r["app_id"],
        )
        assert row is not None
        assert abs(float(row["loan_amount"]) - 26000.00) < 0.01
        assert abs(float(row["selling_price"]) - 28000.00) < 0.01
        assert int(row["loan_term_months"]) == 144


@pytest.mark.integration
class TestRLPipelineDealer:
    """Verify app_dealer_rl row."""

    def test_dealer_name(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_dealer_rl",
            ["dealer_name"],
            r["app_id"],
        )
        assert row is not None
        assert row["dealer_name"] == "All Island Marine Corp"


@pytest.mark.integration
class TestRLPipelineContactAddress:
    """Verify app_contact_address rows."""

    def test_at_least_two_addresses(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT ca.con_id, ca.address_type_enum, ca.city, ca.months_at_address "
            f"FROM {_qualify('app_contact_address', r['schema'])} ca "
            f"INNER JOIN {_qualify('app_contact_base', r['schema'])} cb "
            f"ON ca.con_id = cb.con_id "
            f"WHERE cb.app_id = ? ORDER BY ca.con_id, ca.address_type_enum"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) >= 2

    def test_pr_curr_city(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT city, months_at_address "
            f"FROM {_qualify('app_contact_address', r['schema'])} "
            f"WHERE con_id = ? AND address_type_enum = 320"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["pr_con_id"])
        assert len(rows) >= 1
        assert rows[0][0] == "WINTER PARK"
        assert int(rows[0][1]) == 36  # 0 + (3*12) = 36

    def test_sec_curr_city(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT city FROM {_qualify('app_contact_address', r['schema'])} "
            f"WHERE con_id = ? AND address_type_enum = 320"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["sec_con_id"])
        assert len(rows) >= 1
        assert rows[0][0] == "SHORES"


@pytest.mark.integration
class TestRLPipelineContactEmployment:
    """Verify app_contact_employment rows."""

    def test_at_least_two_records(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT ce.con_id, ce.business_name, ce.monthly_salary, ce.months_at_job "
            f"FROM {_qualify('app_contact_employment', r['schema'])} ce "
            f"INNER JOIN {_qualify('app_contact_base', r['schema'])} cb "
            f"ON ce.con_id = cb.con_id "
            f"WHERE cb.app_id = ? ORDER BY ce.con_id, ce.employment_type_enum"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) >= 2

    def test_pr_curr_employment(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT business_name, monthly_salary, months_at_job "
            f"FROM {_qualify('app_contact_employment', r['schema'])} "
            f"WHERE con_id = ? AND employment_type_enum = 350"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["pr_con_id"])
        assert len(rows) >= 1
        assert rows[0][0] == "THE BIRD CAGE"
        assert abs(float(rows[0][1]) - 3858.00) < 0.01
        assert int(rows[0][2]) == 38  # 2 + (3*12) = 38

    def test_sec_curr_employment(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT business_name, monthly_salary, months_at_job "
            f"FROM {_qualify('app_contact_employment', r['schema'])} "
            f"WHERE con_id = ? AND employment_type_enum = 350"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["sec_con_id"])
        assert len(rows) >= 1
        assert rows[0][0] == "THE RAT CAGE"
        assert abs(float(rows[0][1]) - 10427.13) < 0.01  # ANNUM / 12
        assert int(rows[0][2]) == 65  # 5 + (5*12) = 65


@pytest.mark.integration
class TestRLPipelinePolicyExceptions:
    """Verify app_policy_exceptions_rl rows."""

    def test_three_exceptions(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT policy_exception_type_enum, reason_code, notes "
            f"FROM {_qualify('app_policy_exceptions_rl', r['schema'])} "
            f"WHERE app_id = ? ORDER BY policy_exception_type_enum"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 3

        by_type = {r[0]: {"reason_code": r[1], "notes": r[2]} for r in rows}
        shared = "these are the general notes that will apply to all policies tagged"

        # 630 = Capacity
        assert by_type[630]["reason_code"] == "override tag 2"
        assert by_type[630]["notes"] == shared

        # 631 = Collateral/Program
        assert by_type[631]["reason_code"] == "override tag 3"
        assert by_type[631]["notes"] == shared

        # 632 = Credit
        assert by_type[632]["reason_code"] == "override tag 1"
        assert by_type[632]["notes"] == shared


@pytest.mark.integration
class TestRLPipelineCollateral:
    """Verify app_collateral_rl rows (4 units)."""

    def test_four_collateral_rows(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT collateral_type_enum, make, model, vin, year, used_flag, "
            f"sort_order, mileage, motor_size, wholesale_value "
            f"FROM {_qualify('app_collateral_rl', r['schema'])} "
            f"WHERE app_id = ? ORDER BY sort_order"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 4

    def test_slot1_boat(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT collateral_type_enum, make, model, vin, year, used_flag, "
            f"mileage, motor_size, wholesale_value "
            f"FROM {_qualify('app_collateral_rl', r['schema'])} "
            f"WHERE app_id = ? AND sort_order = 1"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == 412  # BOAT
        assert row[1] == "ALL WATER"
        assert row[2] == "LONG BOY"
        assert row[3] == "4b5et6egt69"
        assert row[4] == 2025
        assert row[5] in (True, 1)  # U → used
        assert int(row[6]) == 836  # mileage
        assert row[7] is None  # no HP_Marine → motor_size NULL
        assert abs(float(row[8]) - 22500.00) < 0.01

    def test_slot2_engine(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT collateral_type_enum, make, motor_size, wholesale_value "
            f"FROM {_qualify('app_collateral_rl', r['schema'])} "
            f"WHERE app_id = ? AND sort_order = 2"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert rows[0][0] == 413  # ENGINE
        assert rows[0][1] == "Coll2 Make"
        assert int(rows[0][2]) == 115
        assert abs(float(rows[0][3]) - 2500.50) < 0.01

    def test_slot3_engine_mercury(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT collateral_type_enum, make, wholesale_value "
            f"FROM {_qualify('app_collateral_rl', r['schema'])} "
            f"WHERE app_id = ? AND sort_order = 3"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert rows[0][0] == 413  # ENGINE (OR expression)
        assert rows[0][1] == "MERCURY"
        assert abs(float(rows[0][2]) - 750.25) < 0.01

    def test_slot4_other_trailer(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT collateral_type_enum, wholesale_value "
            f"FROM {_qualify('app_collateral_rl', r['schema'])} "
            f"WHERE app_id = ? AND sort_order = 4"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 1
        assert rows[0][0] == 417  # OTHER TRAILER
        assert abs(float(rows[0][1]) - 250.00) < 0.01


@pytest.mark.integration
class TestRLPipelineWarranties:
    """Verify app_warranties_rl rows (7 warranty types)."""

    def test_seven_warranties(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT warranty_type_enum, company_name, amount, term_months, "
            f"policy_number, merrick_lienholder_flag "
            f"FROM {_qualify('app_warranties_rl', r['schema'])} "
            f"WHERE app_id = ? ORDER BY warranty_type_enum"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) == 7

        by_type = {r[0]: r for r in rows}

        # 620 - Credit Disability
        assert by_type[620][1] == "Disability Insurance"
        assert by_type[620][2] == 31
        assert by_type[620][3] == 91

        # 621 - Credit Life
        assert by_type[621][1] == "Life Game and Insurance"
        assert by_type[621][2] == 67
        assert by_type[621][3] == 120

        # 622 - Extended Warranty
        assert by_type[622][1] == "EXPRESS SERVICE"
        assert by_type[622][2] == 80

        # 623 - GAP
        assert by_type[623][1] == "Old Navy"
        assert by_type[623][2] == 100
        assert by_type[623][4] == "ON-65487"
        assert by_type[623][5] in (True, 1)  # merrick_lienholder Y→1

        # 624 - Other
        assert by_type[624][1] == "Other Insurance Thing"

        # 625 - Roadside
        assert by_type[625][1] == "Karl's Towing"
        assert by_type[625][4] == "KT-35954"

        # 626 - Service Contract
        assert by_type[626][1] == "GOOD SAM SERVICE"
        assert by_type[626][4] == "GSS-X1VGHTYY"


@pytest.mark.integration
class TestRLPipelineFunding:
    """Verify app_funding_rl and app_funding_checklist_rl rows."""

    def test_funding_loanpro_ids(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_funding_rl",
            ["loanpro_customer_id_pr", "loanpro_customer_id_sec"],
            r["app_id"],
        )
        assert row is not None
        assert row["loanpro_customer_id_pr"] == 7007
        assert row["loanpro_customer_id_sec"] == 7008

    def test_funding_checklist_motor_ucc(self, rl_pipeline_result):
        r = rl_pipeline_result
        row = _query_one(
            r["connection_string"], r["schema"], "app_funding_checklist_rl",
            ["motor_ucc_vin_confirmed_enum", "check_requested_by_user"],
            r["app_id"],
        )
        assert row is not None
        assert row["motor_ucc_vin_confirmed_enum"] == 660  # Y → 660
        assert row["check_requested_by_user"] == "wendy.dotson@merrickbank.com"


@pytest.mark.integration
class TestRLPipelineScores:
    """Verify scores rows (add_score mappings)."""

    def test_four_scores(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT score_identifier, score "
            f"FROM {_qualify('scores', r['schema'])} "
            f"WHERE app_id = ?"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) >= 4

        by_id = {row[0]: row[1] for row in rows}

        assert by_id["CRI_pr"] == 746
        assert by_id["MRV_pr"] == 697
        assert by_id["V4_pr"] == 771
        assert by_id["V4_sec"] == 772


@pytest.mark.integration
class TestRLPipelineHistoricalLookup:
    """Verify app_historical_lookup rows."""

    def test_has_records(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT name, source, value "
            f"FROM {_qualify('app_historical_lookup', r['schema'])} "
            f"WHERE app_id = ?"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        assert len(rows) > 0

    def test_v4_not_in_historical(self, rl_pipeline_result):
        """V4P/V4S target scores table, not historical_lookup."""
        r = rl_pipeline_result
        sql = (
            f"SELECT name FROM {_qualify('app_historical_lookup', r['schema'])} "
            f"WHERE app_id = ?"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        names = {row[0] for row in rows}
        assert "V4P" not in names
        assert "V4S" not in names

    def test_supervisor_rev_ind(self, rl_pipeline_result):
        r = rl_pipeline_result
        sql = (
            f"SELECT value FROM {_qualify('app_historical_lookup', r['schema'])} "
            f"WHERE app_id = ? AND name = '[supervisor_rev_ind]'"
        )
        rows = _query_all(r["connection_string"], r["schema"], sql, r["app_id"])
        if rows:
            assert rows[0][0] == "C"
