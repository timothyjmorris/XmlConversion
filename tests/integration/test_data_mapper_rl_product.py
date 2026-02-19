"""
Integration tests for DataMapper with the RL (RecLending) mapping contract.

These tests exercise the full DataMapper transformation pipeline using
the real RL contract and sample XML — no database connection required.
They verify that XML is correctly parsed, contacts extracted, and data
mapped to the expected table structures with correct values.

Sample: app_id 325725 (MARINE, PR=RHONDA WONG, SEC=WARD GILLIAN)
Contract: config/mapping_contract_rl.json
"""

import json
import os
import sys
import unittest
from pathlib import Path

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


class TestRLDataMapperContactExtraction(unittest.TestCase):
    """Test contact extraction from RL XML via DataMapper."""

    @classmethod
    def setUpClass(cls):
        cls.mapper = DataMapper(
            mapping_contract_path=RL_CONTRACT_RELPATH, log_level="ERROR"
        )
        cls.parser = XMLParser()

        xml_content = RL_SAMPLE_XML_PATH.read_text(encoding="utf-8")
        root = cls.parser.parse_xml_stream(xml_content)
        cls.xml_data = cls.parser.extract_elements(root)
        # DataMapper needs the XML root set for contact navigation
        cls.mapper._current_xml_root = root
        cls.mapper._current_xml_tree = root

    def test_extracts_two_contacts(self):
        """PR + SEC contacts present; AUTHU / PATR should not appear."""
        contacts = self.mapper._extract_valid_contacts(self.xml_data)
        self.assertEqual(len(contacts), 2, "Sample XML has exactly 2 valid contacts (PR + SEC)")

    def test_pr_contact_attributes(self):
        contacts = self.mapper._extract_valid_contacts(self.xml_data)
        pr = next((c for c in contacts if c.get("ac_role_tp_c") == "PR"), None)
        self.assertIsNotNone(pr, "PR contact must be extracted")
        self.assertEqual(pr["con_id"], "35655")
        self.assertEqual(pr["first_name"], "RHONDA")
        self.assertEqual(pr["last_name"], "WONG")

    def test_sec_contact_attributes(self):
        contacts = self.mapper._extract_valid_contacts(self.xml_data)
        sec = next((c for c in contacts if c.get("ac_role_tp_c") == "SEC"), None)
        self.assertIsNotNone(sec, "SEC contact must be extracted")
        self.assertEqual(sec["con_id"], "35656")
        self.assertEqual(sec["first_name"], "WARD")
        self.assertEqual(sec["last_name"], "GILLIAN")


class TestRLDataMapperFullMapping(unittest.TestCase):
    """Test the complete map_xml_to_database output for RL sample 325725."""

    @classmethod
    def setUpClass(cls):
        cls.mapper = DataMapper(
            mapping_contract_path=RL_CONTRACT_RELPATH, log_level="ERROR"
        )
        cls.parser = XMLParser()

        xml_content = RL_SAMPLE_XML_PATH.read_text(encoding="utf-8")
        root = cls.parser.parse_xml_stream(xml_content)
        cls.xml_data = cls.parser.extract_elements(root)
        cls.contacts = cls.mapper._extract_valid_contacts(cls.xml_data)

        cls.mapped = cls.mapper.map_xml_to_database(
            cls.xml_data, "325725", cls.contacts, xml_root=root
        )

    # ── Table presence ────────────────────────────────────────────────

    def test_expected_tables_present(self):
        """All RL target tables must appear in mapped output."""
        expected = {
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
        }
        missing = expected - set(self.mapped.keys())
        self.assertFalse(missing, f"Missing tables: {missing}")

    # ── app_base ──────────────────────────────────────────────────────

    def test_app_base_single_row(self):
        rows = self.mapped["app_base"]
        self.assertEqual(len(rows), 1, "Exactly 1 app_base row expected")

    def test_app_base_app_type_enum(self):
        """MARINE → app_type_enum = 39."""
        row = self.mapped["app_base"][0]
        self.assertEqual(row.get("app_type_enum"), 39)

    def test_app_base_decision_enum(self):
        """APPRV → decision_enum = 610."""
        row = self.mapped["app_base"][0]
        self.assertEqual(row.get("decision_enum"), 610)

    def test_app_base_product_line_enum(self):
        """RL product_line_enum = 602."""
        row = self.mapped["app_base"][0]
        self.assertEqual(row.get("product_line_enum"), 602)

    def test_app_base_ip_address(self):
        row = self.mapped["app_base"][0]
        self.assertIn("52.201.112.6", str(row.get("ip_address", "")))

    # ── app_contact_base ──────────────────────────────────────────────

    def test_contact_base_two_rows(self):
        rows = self.mapped["app_contact_base"]
        self.assertEqual(len(rows), 2, "PR + SEC = 2 contact rows")

    def test_contact_base_pr_enum(self):
        rows = self.mapped["app_contact_base"]
        pr = next((r for r in rows if r.get("contact_type_enum") == 281), None)
        self.assertIsNotNone(pr, "PR contact_type_enum=281 must exist")
        self.assertEqual(pr["first_name"], "RHONDA")

    def test_contact_base_sec_enum(self):
        rows = self.mapped["app_contact_base"]
        sec = next((r for r in rows if r.get("contact_type_enum") == 282), None)
        self.assertIsNotNone(sec, "SEC contact_type_enum=282 must exist")
        self.assertEqual(sec["first_name"], "WARD")

    # ── app_operational_rl ────────────────────────────────────────────

    def test_operational_single_row(self):
        self.assertEqual(len(self.mapped["app_operational_rl"]), 1)

    def test_operational_assigned_credit_analyst(self):
        row = self.mapped["app_operational_rl"][0]
        self.assertEqual(
            row.get("assigned_credit_analyst"), "joshua.ramsey@merrickbank.com"
        )

    def test_operational_mrv_lead_indicator_pr_enum(self):
        """MRV_lead_indicator_p='MRV' → calculated_field → 640."""
        row = self.mapped["app_operational_rl"][0]
        self.assertEqual(row.get("mrv_lead_indicator_pr_enum"), 640)

    def test_operational_housing_monthly_payment_pr(self):
        """PR CURR address residence_monthly_pymnt=525."""
        row = self.mapped["app_operational_rl"][0]
        self.assertAlmostEqual(
            float(row.get("housing_monthly_payment_pr", 0)), 525.0, places=0
        )

    def test_operational_housing_monthly_payment_sec(self):
        """SEC CURR address residence_monthly_pymnt=616."""
        row = self.mapped["app_operational_rl"][0]
        self.assertAlmostEqual(
            float(row.get("housing_monthly_payment_sec", 0)), 616.0, places=0
        )

    def test_operational_joint_app_flag(self):
        """individual_joint_app_ind='J' → bit → True/1."""
        row = self.mapped["app_operational_rl"][0]
        self.assertIn(row.get("joint_app_flag"), [True, 1])

    def test_operational_cb_score_factor_code_pr_1(self):
        """First decline code from Vantage4 → 'V4_68'."""
        row = self.mapped["app_operational_rl"][0]
        self.assertEqual(row.get("cb_score_factor_code_pr_1"), "V4_68")

    # ── app_pricing_rl ────────────────────────────────────────────────

    def test_pricing_loan_amount(self):
        row = self.mapped["app_pricing_rl"][0]
        self.assertAlmostEqual(float(row.get("loan_amount", 0)), 26000.00, places=2)

    def test_pricing_selling_price(self):
        row = self.mapped["app_pricing_rl"][0]
        self.assertAlmostEqual(
            float(row.get("selling_price", 0)), 28000.00, places=2
        )

    def test_pricing_loan_term_months(self):
        row = self.mapped["app_pricing_rl"][0]
        self.assertEqual(int(row.get("loan_term_months", 0)), 144)

    # ── app_dealer_rl ─────────────────────────────────────────────────

    def test_dealer_name(self):
        row = self.mapped["app_dealer_rl"][0]
        self.assertEqual(row.get("dealer_name"), "All Island Marine Corp")

    # ── app_contact_address ───────────────────────────────────────────

    def test_address_record_count(self):
        """At least 2 addresses: PR CURR + SEC CURR.  PR PREV possible."""
        rows = self.mapped["app_contact_address"]
        self.assertGreaterEqual(len(rows), 2)

    def test_address_pr_curr_city(self):
        rows = self.mapped["app_contact_address"]
        pr_curr = [
            r
            for r in rows
            if r.get("address_type_enum") == 320
            and str(r.get("con_id")) == "35655"
        ]
        self.assertTrue(pr_curr, "PR CURR address must exist")
        self.assertEqual(pr_curr[0]["city"], "WINTER PARK")

    def test_address_months_at_address_calculated(self):
        """PR CURR: months=0, years=3 → 36."""
        rows = self.mapped["app_contact_address"]
        pr_curr = [
            r
            for r in rows
            if r.get("address_type_enum") == 320
            and str(r.get("con_id")) == "35655"
        ]
        if pr_curr and "months_at_address" in pr_curr[0]:
            self.assertEqual(int(pr_curr[0]["months_at_address"]), 36)

    def test_address_sec_curr_city(self):
        rows = self.mapped["app_contact_address"]
        sec_curr = [
            r
            for r in rows
            if r.get("address_type_enum") == 320
            and str(r.get("con_id")) == "35656"
        ]
        self.assertTrue(sec_curr, "SEC CURR address must exist")
        self.assertEqual(sec_curr[0]["city"], "SHORES")

    # ── app_contact_employment ────────────────────────────────────────

    def test_employment_record_count(self):
        """At least 2: PR CURR + SEC CURR.  PR PREV possible."""
        rows = self.mapped["app_contact_employment"]
        self.assertGreaterEqual(len(rows), 2)

    def test_employment_pr_curr_business(self):
        rows = self.mapped["app_contact_employment"]
        pr_curr = [
            r
            for r in rows
            if r.get("employment_type_enum") == 350
            and str(r.get("con_id")) == "35655"
        ]
        self.assertTrue(pr_curr, "PR CURR employment must exist")
        self.assertEqual(pr_curr[0]["business_name"], "THE BIRD CAGE")

    def test_employment_pr_monthly_salary(self):
        """basis=MONTH, salary=3858.00 → monthly_salary=3858.00."""
        rows = self.mapped["app_contact_employment"]
        pr_curr = [
            r
            for r in rows
            if r.get("employment_type_enum") == 350
            and str(r.get("con_id")) == "35655"
        ]
        if pr_curr and "monthly_salary" in pr_curr[0]:
            self.assertAlmostEqual(
                float(pr_curr[0]["monthly_salary"]), 3858.00, places=2
            )

    def test_employment_pr_months_at_job(self):
        """months=2, years=3 → 38."""
        rows = self.mapped["app_contact_employment"]
        pr_curr = [
            r
            for r in rows
            if r.get("employment_type_enum") == 350
            and str(r.get("con_id")) == "35655"
        ]
        if pr_curr and "months_at_job" in pr_curr[0]:
            self.assertEqual(int(pr_curr[0]["months_at_job"]), 38)

    def test_employment_sec_monthly_salary_annum(self):
        """basis=ANNUM, salary=125125.50 → monthly_salary=125125.50/12≈10427.13."""
        rows = self.mapped["app_contact_employment"]
        sec_curr = [
            r
            for r in rows
            if r.get("employment_type_enum") == 350
            and str(r.get("con_id")) == "35656"
        ]
        if sec_curr and "monthly_salary" in sec_curr[0]:
            self.assertAlmostEqual(
                float(sec_curr[0]["monthly_salary"]), 10427.13, places=2
            )

    def test_employment_sec_months_at_job(self):
        """months=5, years=5 → 65."""
        rows = self.mapped["app_contact_employment"]
        sec_curr = [
            r
            for r in rows
            if r.get("employment_type_enum") == 350
            and str(r.get("con_id")) == "35656"
        ]
        if sec_curr and "months_at_job" in sec_curr[0]:
            self.assertEqual(int(sec_curr[0]["months_at_job"]), 65)

    # ── app_collateral_rl ─────────────────────────────────────────────

    def test_collateral_four_rows(self):
        self.assertEqual(len(self.mapped["app_collateral_rl"]), 4)

    def test_collateral_slot1_boat(self):
        """Coll1: MARINE → collateral_type_enum=412, make=ALL WATER."""
        rows = self.mapped["app_collateral_rl"]
        slot1 = next((r for r in rows if r.get("sort_order") == 1), None)
        self.assertIsNotNone(slot1, "Slot 1 collateral row must exist")
        self.assertEqual(slot1["collateral_type_enum"], 412)
        self.assertEqual(slot1["make"], "ALL WATER")
        self.assertEqual(slot1["model"], "LONG BOY")
        self.assertEqual(slot1["vin"], "4b5et6egt69")
        self.assertEqual(slot1["year"], 2025)
        # U → used_flag = True/1
        self.assertIn(slot1.get("used_flag"), [True, 1])

    def test_collateral_slot1_mileage(self):
        rows = self.mapped["app_collateral_rl"]
        slot1 = next((r for r in rows if r.get("sort_order") == 1), None)
        self.assertEqual(int(slot1["mileage"]), 836)

    def test_collateral_slot1_wholesale_value(self):
        rows = self.mapped["app_collateral_rl"]
        slot1 = next((r for r in rows if r.get("sort_order") == 1), None)
        self.assertAlmostEqual(float(slot1["wholesale_value"]), 22500.00, places=2)

    def test_collateral_slot2_engine(self):
        """Coll2: HP_Marine=115 → collateral_type_enum=413, motor_size=115."""
        rows = self.mapped["app_collateral_rl"]
        slot2 = next((r for r in rows if r.get("sort_order") == 2), None)
        self.assertIsNotNone(slot2)
        self.assertEqual(slot2["collateral_type_enum"], 413)
        self.assertEqual(slot2["make"], "Coll2 Make")
        self.assertEqual(int(slot2["motor_size"]), 115)
        self.assertAlmostEqual(float(slot2["wholesale_value"]), 2500.50, places=2)

    def test_collateral_slot3_engine_mercury(self):
        """Coll3: make=MERCURY → collateral_type_enum=413 via OR expression."""
        rows = self.mapped["app_collateral_rl"]
        slot3 = next((r for r in rows if r.get("sort_order") == 3), None)
        self.assertIsNotNone(slot3)
        self.assertEqual(slot3["collateral_type_enum"], 413)
        self.assertEqual(slot3["make"], "MERCURY")
        self.assertAlmostEqual(float(slot3["wholesale_value"]), 750.25, places=2)

    def test_collateral_slot4_other_trailer(self):
        """Coll4: → collateral_type_enum=417 (OTHER TRAILER)."""
        rows = self.mapped["app_collateral_rl"]
        slot4 = next((r for r in rows if r.get("sort_order") == 4), None)
        self.assertIsNotNone(slot4)
        self.assertEqual(slot4["collateral_type_enum"], 417)
        self.assertAlmostEqual(float(slot4["wholesale_value"]), 250.00, places=2)

    # ── app_warranties_rl ─────────────────────────────────────────────

    def test_warranties_seven_rows(self):
        self.assertEqual(len(self.mapped["app_warranties_rl"]), 7)

    def test_warranty_gap(self):
        """GAP (623): Old Navy, $100, 48mo."""
        rows = self.mapped["app_warranties_rl"]
        gap = next((r for r in rows if r.get("warranty_type_enum") == 623), None)
        self.assertIsNotNone(gap, "GAP warranty must exist")
        self.assertEqual(gap["company_name"], "Old Navy")
        self.assertEqual(int(gap["amount"]), 100)
        self.assertEqual(int(gap["term_months"]), 48)
        self.assertEqual(gap["policy_number"], "ON-65487")

    def test_warranty_extended(self):
        """Extended Warranty (622): EXPRESS SERVICE, $80, 60mo."""
        rows = self.mapped["app_warranties_rl"]
        ew = next((r for r in rows if r.get("warranty_type_enum") == 622), None)
        self.assertIsNotNone(ew)
        self.assertEqual(ew["company_name"], "EXPRESS SERVICE")

    def test_warranty_credit_life(self):
        """Credit Life (621): Life Game and Insurance, $67, 120mo."""
        rows = self.mapped["app_warranties_rl"]
        cl = next((r for r in rows if r.get("warranty_type_enum") == 621), None)
        self.assertIsNotNone(cl)
        self.assertEqual(cl["company_name"], "Life Game and Insurance")
        self.assertEqual(int(cl["amount"]), 67)

    def test_warranty_service_contract(self):
        """Service Contract (626): GOOD SAM SERVICE, $141, 72mo."""
        rows = self.mapped["app_warranties_rl"]
        sc = next((r for r in rows if r.get("warranty_type_enum") == 626), None)
        self.assertIsNotNone(sc)
        self.assertEqual(sc["company_name"], "GOOD SAM SERVICE")
        self.assertEqual(sc["policy_number"], "GSS-X1VGHTYY")

    # ── app_policy_exceptions_rl ──────────────────────────────────────

    def test_policy_exceptions_three_rows(self):
        self.assertEqual(len(self.mapped["app_policy_exceptions_rl"]), 3)

    def test_policy_exception_credit(self):
        """override_credit → type_enum=632, reason='override tag 1'."""
        rows = self.mapped["app_policy_exceptions_rl"]
        credit = next(
            (r for r in rows if r.get("policy_exception_type_enum") == 632), None
        )
        self.assertIsNotNone(credit)
        self.assertEqual(credit["reason_code"], "override tag 1")

    def test_policy_exception_shared_notes(self):
        """All 3 exceptions share the same notes string."""
        rows = self.mapped["app_policy_exceptions_rl"]
        shared = "these are the general notes that will apply to all policies tagged"
        for row in rows:
            self.assertEqual(row.get("notes"), shared)

    # ── scores (add_score mappings) ───────────────────────────────────

    def test_scores_at_least_four(self):
        """V4P, V4S, CRI_pr, MRV_pr expected from sample XML."""
        rows = self.mapped["scores"]
        self.assertGreaterEqual(len(rows), 4)

    def test_score_v4p(self):
        rows = self.mapped["scores"]
        v4p = next(
            (r for r in rows if r.get("score_identifier") == "V4_pr"), None
        )
        self.assertIsNotNone(v4p, "V4P score must be present (target_table=scores)")
        self.assertEqual(int(v4p["score"]), 771)

    def test_score_v4s(self):
        rows = self.mapped["scores"]
        v4s = next(
            (r for r in rows if r.get("score_identifier") == "V4_sec"), None
        )
        self.assertIsNotNone(v4s, "V4S score must be present (target_table=scores)")
        self.assertEqual(int(v4s["score"]), 772)

    def test_score_cri_pr(self):
        rows = self.mapped["scores"]
        cri = next(
            (r for r in rows if r.get("score_identifier") == "CRI_pr"), None
        )
        self.assertIsNotNone(cri)
        self.assertEqual(int(cri["score"]), 746)

    def test_score_mrv_pr(self):
        rows = self.mapped["scores"]
        mrv = next(
            (r for r in rows if r.get("score_identifier") == "MRV_pr"), None
        )
        self.assertIsNotNone(mrv)
        self.assertEqual(int(mrv["score"]), 697)

    # ── app_historical_lookup ─────────────────────────────────────────

    def test_historical_lookup_has_records(self):
        rows = self.mapped["app_historical_lookup"]
        self.assertGreater(len(rows), 0)

    def test_historical_lookup_v4_not_present(self):
        """V4P/V4S now go to scores table, not app_historical_lookup."""
        rows = self.mapped["app_historical_lookup"]
        names = {r.get("name") for r in rows}
        self.assertNotIn("V4_pr", names, "V4P targets scores, not historical_lookup")
        self.assertNotIn("V4_sec", names, "V4S targets scores, not historical_lookup")

    def test_historical_lookup_supervisor_rev_ind(self):
        rows = self.mapped["app_historical_lookup"]
        sup = next(
            (r for r in rows if r.get("name") == "[supervisor_rev_ind]"), None
        )
        if sup:
            self.assertEqual(sup["value"], "C")

    # ── app_funding_rl ────────────────────────────────────────────────

    def test_funding_loanpro_customer_ids(self):
        """last_valid_pr_contact → 7007, last_valid_sec_contact → 7008."""
        row = self.mapped["app_funding_rl"][0]
        self.assertEqual(int(row.get("loanpro_customer_id_pr", 0)), 7007)
        self.assertEqual(int(row.get("loanpro_customer_id_sec", 0)), 7008)

    # ── app_funding_checklist_rl ──────────────────────────────────────

    def test_funding_checklist_motor_ucc_vin(self):
        """Y → y_n_d_enum → 660."""
        row = self.mapped["app_funding_checklist_rl"][0]
        self.assertEqual(row.get("motor_ucc_vin_confirmed_enum"), 660)

    def test_funding_checklist_check_requested_by(self):
        """chk_requested_by='6010' → enum → 'wendy.dotson@merrickbank.com'."""
        row = self.mapped["app_funding_checklist_rl"][0]
        self.assertEqual(
            row.get("check_requested_by_user"),
            "wendy.dotson@merrickbank.com",
        )


if __name__ == "__main__":
    unittest.main()
