#!/usr/bin/env python3
"""
Mock XML Data Generator for RecLending (RL) Pipeline Testing.

Generates valid mock RL XML records with unique app_ids and con_ids for
performance testing and batch processing validation.

Generated XMLs follow the same structure as production RL Provenir XML,
targeting the ``app_xml_staging_rl`` table.

Usage::

    python env_prep/generate_mock_xml_rl.py              # interactive
    python env_prep/generate_mock_xml_rl.py --count 200  # direct
"""

import argparse
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.database.migration_engine import MigrationEngine

# ── Application-type pools ────────────────────────────────────────────

APP_TYPES = ["MARINE", "RV", "MC", "HT", "OR", "UT"]
DECISION_TYPES = ["APPRV", "DECLN", "PENDING", "WITHD"]
MRV_INDICATORS = ["MRV", "Vantage", ""]
SALARY_BASES = ["MONTH", "ANNUM"]
STATES = ["FL", "TX", "AZ", "CA", "NY", "KY", "WA", "CO", "NV", "UT"]
FIRST_NAMES_PR = ["TOMMY", "RHONDA", "JAMES", "SARAH", "ALEX", "CARLA"]
LAST_NAMES_PR = ["BARKER", "WONG", "SMITH", "JOHNSON", "MORGAN", "DIAZ"]
FIRST_NAMES_SEC = ["WARD", "DREW", "LEE", "MEGAN", "KYLE", "NORA"]
LAST_NAMES_SEC = ["GILLIAN", "POPE", "CHEN", "BAKER", "HAYES", "REED"]
DEALER_NAMES = [
    "All Island Marine Corp",
    "Sunshine RV Sales",
    "Peak Motorsports",
    "Liberty Trailer Co",
    "Blue Ridge Outdoors",
    "Summit Powersports",
]
EMPLOYER_NAMES = [
    "THE BIRD CAGE",
    "ACME LOGISTICS",
    "BLUE WAVE TECH",
    "SUMMIT SERVICES",
    "GREEN VALLEY CO",
]
WARRANTY_COMPANIES = {
    "gap": ("Old Navy", "ON"),
    "service_contract": ("GOOD SAM SERVICE", "GSS"),
    "ext_warranty": ("EXPRESS SERVICE", "ES"),
    "road_side": ("Karl's Towing", "KT"),
    "credit_life": ("Life Game and Insurance", "LGI"),
    "credit_disability": ("Disability Insurance", "DI"),
    "other": ("Other Insurance Thing", "OIT"),
}


class MockXMLGeneratorRL:
    """Generates valid mock RL Provenir XML for performance testing."""

    def __init__(self):
        """Initialize with database connection via config_manager."""
        config = get_config_manager()
        self.connection_string = config.get_database_connection_string()
        self.migration_engine = MigrationEngine(
            self.connection_string,
            mapping_contract_path="config/mapping_contract_rl.json",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_and_insert(
        self, count: int, start_app_id: int = 700000
    ) -> int:
        """Generate *count* mock RL XMLs and insert into app_xml_staging_rl.

        Returns:
            Number of records successfully inserted.
        """
        print(f"\n🔄 Generating {count} mock RL XML records …")
        print(f"   Starting app_id: {start_app_id}")

        inserted = 0
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()

                for i in range(count):
                    app_id = start_app_id + i
                    xml = self._generate_mock_xml(app_id)

                    try:
                        cursor.execute(
                            "INSERT INTO dbo.app_xml_staging_rl (app_id, app_XML) VALUES (?, ?)",
                            (app_id, xml),
                        )
                        inserted += 1

                        if (i + 1) % 100 == 0 or i == count - 1:
                            print(f"   Progress: {i + 1}/{count} inserted …")

                    except Exception as exc:
                        err = str(exc)
                        if "PRIMARY KEY" in err or "Duplicate" in err:
                            pass  # skip existing
                        else:
                            print(f"   ❌ app_id {app_id}: {err}")
                        continue

                conn.commit()
                print(f"   ✅ Committed {inserted} rows")

        except Exception as exc:
            print(f"❌ Error: {exc}")

        return inserted

    # ------------------------------------------------------------------
    # XML Generation
    # ------------------------------------------------------------------

    def _generate_mock_xml(self, app_id: int) -> str:
        pr_con_id = app_id * 2
        sec_con_id = pr_con_id + 1

        app_type = random.choice(APP_TYPES)
        decision = random.choice(DECISION_TYPES)
        mrv_ind = random.choice(MRV_INDICATORS)
        state = random.choice(STATES)
        dealer = random.choice(DEALER_NAMES)

        loan_amount = random.randint(8000, 80000)
        sale_price = loan_amount + random.randint(500, 5000)
        term = random.choice([36, 48, 60, 72, 84, 96, 120, 144, 180])
        down_payment = random.randint(500, 10000)
        entry_date = (
            datetime.now() - timedelta(days=random.randint(1, 365))
        ).strftime("%Y-%m-%d %H:%M:%S.000")
        decision_date = (
            datetime.now() - timedelta(days=random.randint(0, 30))
        ).strftime("%Y-%m-%d %H:%M:%S.000")

        # Scores
        fico_10t = random.randint(550, 850)
        v4_score = random.randint(550, 850)
        v4_score2 = random.randint(550, 850)
        mrv_score = round(random.uniform(500, 800), 1)
        cri_score = round(random.uniform(500, 800), 1)
        monthly_income = round(random.uniform(3000, 15000), 2)
        dti = round(random.uniform(5, 50), 2)
        monthly_debt = round(monthly_income * dti / 100, 2)

        # Collateral
        coll1_year = random.randint(2015, 2025)
        coll1_value = round(random.uniform(5000, 50000), 2)
        coll2_year = random.randint(2015, 2025)
        coll2_value = round(random.uniform(500, 5000), 2)
        coll2_hp = round(random.uniform(50, 350), 2)

        contacts_xml = self._generate_contacts_xml(
            pr_con_id, sec_con_id, app_id
        )
        warranty_xml = self._generate_warranty_xml()

        xml = f'''<Provenir status="" ipaddress="10.20.{random.randint(1,254)}.{random.randint(1,254)}" product="rl" app_source="API" Org="MBC" shred_version="MOCK" resetRegB="false" error="" fundingErrorMessage="">
  <Request ID="{app_id}" orgID="MBC-MOCK" Process="20800" LockedBy="" UserID="" Priority="" Status="" Workflow="RecLending" Trans="" Readonly="" _LockedBy="MOCK@TEST.COM" LastUpdatedBy="MOCK-{app_id}" LockedAt="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}">
    <CustData>
      <IL_application loanpro_loan_id="{app_id + 1000000}" individual_joint_app_ind="J" app_receive_date="{entry_date}" app_source_ind="D" app_type_code="{app_type}" sub_type_code="" dlr_name="{dealer}" dealer_number="{random.randint(100000,999999)}" dlr_address_line1="{random.randint(100,9999)} MOCK ST" dlr_city="MOCK CITY" dlr_state="{state}" dlr_zipcode="{random.randint(10000,99999)}" dlr_email="dealer-{app_id}@mock.com" dlr_phone="801{random.randint(1000000,9999999)}" parent_dealer_number="{random.randint(100000,999999)}" esign_eligible="Y" dlr_broker="N" dlr_num_marine="{random.randint(100000,999999)}" dlr_fax="" fsp_name="" fsp_phone="" requested_term_months="{term}" app_cash_down_payment="{down_payment}" app_sale_price="{sale_price}" trade_net_tradein_amount="0" app_invoice_amount="0" loan_amount_requested="{loan_amount}" client_id="{app_id}" app_entry_date="{entry_date}" campaign_num="MOCK-{app_id}" opt_out_ind="N" tied_app_id="" tied_app_indicator="" add_TTL_to_amt_fin="N" dealer_count="1" app_counted="Y" assigned_analyst="mock-{app_id}@merrickbank.com" duplicate_app_ind="N" last_update_time="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}" EODRet="" duplicate_fund_ind="N" application_eligible="" dlr_num_ht="" dlr_num_mc="" dlr_num_or="" dlr_num_rv="" dlr_num_trailer="" supervisor_rev_ind="C" trade_allowance="{round(random.uniform(0,5000),2)}">
        <IL_fund_dlr_ach dlr_name="{dealer}" dlr_num="{random.randint(100000,999999)}" dlr_aba="" dlr_account_num="" pre_note_date="" dlr_check_or_sav="" dlr_ach_ind="N" dlr_active_dormant="" dlr_agree_completed="" dlr_bank_name="" dlr_bank_phone="" dlr_fsp_yn="N" dlr_fsp_num="" dlr_proceeds_amount="" />
        <IL_app_decision_info manual_adj_monthly_income="" experian_fico_score_10t="0{fico_10t}" experian_vantage4_score="0{v4_score}" experian_vantage4_score2="0{v4_score2}" vantage_score_used="{v4_score}" experian_fico_score_f9="" Vantage4P_decline_code1="V4_{random.randint(10,99)}" Vantage4P_decline_code2="" Vantage4P_decline_code3="" Vantage4P_decline_code4="" Vantage4P_decline_code5="" MRVReasons="" MRV_lead_indicator_p="{mrv_ind}" MRV_score_p="{mrv_score}" MRV_score_s="" CRI_score_p="{cri_score}" CRI_score_s="" MRVP_decline_code1="rmc_{random.randint(1,9)}_pr" MRVP_decline_code2="" MRVP_decline_code3="" MRVP_decline_code4="" monthly_income="{monthly_income}" regular_pymt_amount1="0" manual_adj_monthly_debt="" monthly_debt="{monthly_debt}" debt_to_income_ratio="{dti}" manual_adj_DTI_ratio="" credit_exception_notes="" pending_verif_ind="" decision_type_code="{decision}" decision_date="{decision_date}" regb_closed_days_num="30" max_DTI="{dti + 5}" override_credit="override tag 1" override_capacity="override tag 2" override_collateral_program="override tag 3" override_type_code_notes="general override notes for mock {app_id}" MRVP_Decline_Code_1="rmc_1_pr" MRVP_Decline_Code_2="" MRVS_Decline_Code_1="rmc_1_sec" MRV_Grade_P="A" />
        <IL_collateral coll1_year="{coll1_year}" coll1_make="MOCK MARINE CO" coll1_model="MODEL-{app_id}" coll1_VIN="VIN{app_id:09d}" coll1_mileage="{random.randint(0,5000)}" coll1_new_used_demo="U" coll_is_motorhome="" net_invoice="0" coll_option_total_value="{round(random.uniform(0,2000),2)}" coll1_value="{coll1_value}" coll2_year="{coll2_year}" coll2_make="ENGINE CO" coll2_model="ENG-{app_id}" coll2_VIN="EVIN{app_id:08d}" coll2_HP_Marine="{coll2_hp}" coll2_value="{coll2_value}" coll3_year="" coll3_make="" coll3_model="" coll3_VIN="" coll3_value="" coll4_year="" coll4_make="" coll4_model="" coll4_VIN="" coll4_value="" coll_option1="{round(random.uniform(0,1000),2)}" coll_option2_desc="Mock option" engine_size_CC="{random.randint(100,1500)}" coll1_invoice_wholesale_ind="" />
        <IL_application_verification v_employ_name="" v_employ_hiredate="" v_employ_phone="" v_employ_salary="" v_employ_spokewith="" v_verifier_name="" v_coapp_employ_name="" v_coapp_employ_hiredate="" v_coapp_employ_phone="" v_coapp_employ_salary="" v_coapp_employ_spokewith="" v_coapp_verifier_name="" />
        <IL_fund_checklist ct_rate_over_split="{round(random.uniform(5,20),2)}" ct_sale_price="{sale_price}" total_amount_financed="{loan_amount}" total_of_payments="{round(loan_amount * 1.5, 2)}" finance_charge="{round(loan_amount * 0.5, 2)}" ct_loan_to_value_percentage="{round(loan_amount / sale_price * 100, 2)}" ct_note_date="{datetime.now().strftime('%m/%d/%Y')}" ct_contract_state="{state}" ct_titled_in_state="{state}" funding_contact_code="6029" chk_requested_by="6010" motor_ucc_vin_confirmed="Y" title_transfer_received="N" insurance_confirmed="Y" ins_company_name="MOCK INS" ins_policy_number="POL-{app_id}" ins_agent_name="Agent {app_id}" ins_agent_phone="801{random.randint(1000000,9999999)}" ins_expiration_date="{(datetime.now() + timedelta(days=365)).strftime('%m/%d/%Y')}" proof_of_insurance_recd="" dealer_agreement_received="" odometer_received="" void_check_received="" stips_completed="" stips_list="" pay_by_check="" />
        <IL_rule_flags DELAT="" DELIL="" DELRV="" CCJTH="" INSILH="" INSSLR="" NLABD="" REVDT="" TOJOB="" ILDTI="" />
        {warranty_xml}
{contacts_xml}
        <IL_Incomes>
          <IL_Income id="1" sourceApplicant="primary" baseMonthlyIncome="{round(monthly_income, 2)}" ytdMonthlyIncome="0" ytdAmount="0" frequency="monthly" dtiIncomeType="employment" type="salary" baseRate="" unitsPerPeriod="" periodEndDate="" payDate="" grossUpIncome="" notes="" />
        </IL_Incomes>
        <IL_Indicators>
          <IL_Indicator ID="CreditBureauPulledP" value="True" />
          <IL_Indicator ID="ValidCreditScoreP" value="True" />
        </IL_Indicators>
        <WorkItems>
          <WorkItem name="decision" status="pass" />
        </WorkItems>
        <IL_Adjustments />
        <IL_ITI_control funding_date="" account_number="" boarding_date="" boarding_datetime="" />
        <IL_ITI_note payment_date="" product_number="" />
      </IL_application>
    </CustData>
    <Reports>
      <EX report_time="{datetime.now().strftime('%Y-%m-%d %H:%M:%S.000')}" />
      <TLO report_time="{datetime.now().strftime('%Y-%m-%d %H:%M:%S.000')}" />
      <MLA report_time="{datetime.now().strftime('%Y-%m-%d %H:%M:%S.000')}" />
    </Reports>
    <Documents />
    <Audits />
    <Rules />
    <Journals />
    <Messages />
  </Request>
  <queues>
    <queue name="T All Applications" id="45" />
  </queues>
</Provenir>'''
        return xml

    def _generate_contacts_xml(
        self, pr_con_id: int, sec_con_id: int, app_id: int
    ) -> str:
        """Generate PR + SEC contact blocks with addresses and employment."""
        pr_first = random.choice(FIRST_NAMES_PR)
        pr_last = random.choice(LAST_NAMES_PR)
        sec_first = random.choice(FIRST_NAMES_SEC)
        sec_last = random.choice(LAST_NAMES_SEC)
        pr_salary = round(random.uniform(2000, 8000), 2)
        sec_salary = round(random.uniform(30000, 150000), 2)
        pr_emp = random.choice(EMPLOYER_NAMES)
        sec_emp = random.choice(EMPLOYER_NAMES)
        pr_pymnt = random.randint(200, 2000)
        sec_pymnt = random.randint(200, 2000)
        pr_state = random.choice(STATES)
        sec_state = random.choice(STATES)

        return f'''        <IL_contact loanpro_customer_id="{pr_con_id}" ac_role_tp_c="PR" con_id="{pr_con_id}" email="{pr_first.lower()}-{app_id}@mock.com" first_name="{pr_first}" middle_initial="M" last_name="{pr_last}" ssn="{random.randint(100000000,999999999)}" cell_phone="801{random.randint(1000000,9999999)}" home_phone="801{random.randint(1000000,9999999)}" drivers_license="DL{pr_con_id}" drivers_license_state="{pr_state}" birth_date="05/10/1978" suffix="">
          <IL_contact_address address_seq_no="1" address_type_code="CURR" years_at_residence="{random.randint(0,15)}" months_at_residence="{random.randint(0,11)}" residence_monthly_pymnt="{pr_pymnt}" city="MOCK CITY" state="{pr_state}" zip_code="{random.randint(10000,99999)}" street_number="{random.randint(100,9999)}" street_name="MAIN ST" apartment_unit_number="" po_box="" rural_route="" ownership_type_code="330" />
          <IL_contact_address address_seq_no="2" address_type_code="PREV" years_at_residence="1" months_at_residence="6" residence_monthly_pymnt="0" city="" state="" zip_code="" street_number="" street_name="" apartment_unit_number="" po_box="" rural_route="" ownership_type_code="" />
          <IL_contact_employment employment_seq_no="1" employment_type_code="CURR" salary="{pr_salary}" salary_basis_type_code="MONTH" business_name="{pr_emp}" business_phone="801{random.randint(1000000,9999999)}" years_at_job="{random.randint(0,10)}" months_at_job="{random.randint(0,11)}" address_line1="" city="" state="" zip_code="" other_income_source_type_code="" self_employed_ind="N" other_income_basis_type_code="" other_income_amt="0" />
        </IL_contact>
        <IL_contact loanpro_customer_id="{sec_con_id}" ac_role_tp_c="SEC" con_id="{sec_con_id}" email="{sec_first.lower()}-{app_id}@mock.com" first_name="{sec_first}" middle_initial="" last_name="{sec_last}" ssn="{random.randint(100000000,999999999)}" cell_phone="801{random.randint(1000000,9999999)}" home_phone="" drivers_license="" drivers_license_state="" birth_date="11/06/1973" suffix="">
          <IL_contact_address address_seq_no="1" address_type_code="CURR" years_at_residence="{random.randint(0,10)}" months_at_residence="{random.randint(0,11)}" residence_monthly_pymnt="{sec_pymnt}" city="SEC CITY" state="{sec_state}" zip_code="{random.randint(10000,99999)}" street_number="{random.randint(100,9999)}" street_name="OAK AVE" apartment_unit_number="" po_box="" rural_route="" ownership_type_code="332" />
          <IL_contact_employment employment_seq_no="1" employment_type_code="CURR" salary="{sec_salary}" salary_basis_type_code="ANNUM" business_name="{sec_emp}" business_phone="" years_at_job="{random.randint(0,10)}" months_at_job="{random.randint(0,11)}" address_line1="" city="" state="" zip_code="" other_income_source_type_code="" self_employed_ind="Y" other_income_basis_type_code="" other_income_amt="0" />
        </IL_contact>'''

    def _generate_warranty_xml(self) -> str:
        """Generate IL_backend_policies element with 7 warranty groups."""
        attrs = []
        for key, (company, prefix) in WARRANTY_COMPANIES.items():
            amt = random.randint(20, 200)
            term = random.choice([36, 48, 60, 72, 84, 91, 120])
            policy = f"{prefix}-{random.randint(10000,99999)}"
            attrs.append(f'{key}_company="{company}"')
            attrs.append(f'{key}_amount="{amt}"')
            attrs.append(f'{key}_term="{term}"')
            attrs.append(f'{key}_policy="{policy}"')
            if key == "gap":
                attrs.append(f'{key}_lien="Y"')
        return f'        <IL_backend_policies {" ".join(attrs)} />'


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════


def _get_next_app_id(conn_str: str) -> int:
    """Query max(app_id) from app_xml_staging_rl + 1."""
    import pyodbc

    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(app_id) FROM dbo.app_xml_staging_rl")
            row = cursor.fetchone()
            return (row[0] or 0) + 1
    except Exception:
        return 800000


def _get_current_count(conn_str: str) -> int:
    import pyodbc

    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM dbo.app_xml_staging_rl WHERE app_XML IS NOT NULL"
            )
            return cursor.fetchone()[0]
    except Exception:
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate mock RL XML records for performance testing."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="Number of records to generate (interactive if omitted)",
    )
    parser.add_argument(
        "--start-app-id",
        type=int,
        default=None,
        help="Starting app_id (auto-detect if omitted)",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("📋 MOCK RL XML DATA GENERATOR")
    print("=" * 60)

    gen = MockXMLGeneratorRL()
    current = _get_current_count(gen.connection_string)
    print(f"\n📊 Current app_xml_staging_rl rows: {current}")

    if args.count is not None:
        count = args.count
    else:
        print("\n🔧 Dataset sizes:")
        print("   1. Small  (50)")
        print("   2. Medium (200)")
        print("   3. Large  (500)")
        print("   4. Custom")
        choice = input("\nSelect (1-4): ").strip()
        count = {"1": 50, "2": 200, "3": 500}.get(choice)
        if count is None:
            try:
                count = int(input("Enter record count: ").strip())
            except ValueError:
                print("Invalid number!")
                return 1

    start_id = args.start_app_id or _get_next_app_id(gen.connection_string)
    inserted = gen.generate_and_insert(count, start_id)

    new_total = _get_current_count(gen.connection_string)
    print(f"\n✅ Done — previous: {current}, new: {new_total}, added: {inserted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
