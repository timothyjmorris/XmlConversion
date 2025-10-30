#!/usr/bin/env python3
"""
Mock XML Data Generator for Testing

Generates valid mock XML records with unique app_ids and con_ids for testing.
Allows repeatable, clean batch size tests without running out of data.

Generated XMLs follow the same structure as production Provenir XML.
"""

import sys
import random
import string
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from xml_extractor.database.migration_engine import MigrationEngine
from tests.integration.test_database_connection import DatabaseConnectionTester


class MockXMLGenerator:
    """Generates valid mock Provenir XML for testing."""
    
    def __init__(self):
        """Initialize with database connection."""
        # Initialize database connection
        self.db_tester = DatabaseConnectionTester()
        success, message = self.db_tester.test_connection()
        if not success:
            raise RuntimeError(f"Database connection failed: {message}")
        
        self.connection_string = self.db_tester.build_connection_string()
        self.migration_engine = MigrationEngine(self.connection_string)
    
    def generate_and_insert_mock_xmls(self, count: int, start_app_id: int = 700000) -> int:
        """
        Generate and insert mock XMLs into app_xml table.
        
        Args:
            count: Number of mock XMLs to generate
            start_app_id: Starting app_id (will increment)
            
        Returns:
            Number of XMLs successfully inserted
        """
        print(f"\n🔄 Generating {count} mock XML records...")
        print(f"   Starting app_id: {start_app_id}")
        
        inserted_count = 0
        
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                
                for i in range(count):
                    app_id = start_app_id + i
                    
                    # Generate mock XML
                    xml_content = self._generate_mock_xml(app_id)
                    
                    # Insert into app_xml table
                    try:
                        cursor.execute(
                            "INSERT INTO app_xml (app_id, xml) VALUES (?, ?)",
                            (app_id, xml_content)
                        )
                        inserted_count += 1
                        
                        # Progress indicator
                        if (i + 1) % 50 == 0 or i == count - 1:
                            print(f"   Progress: {i + 1}/{count} records...")
                    
                    except Exception as e:
                        # Skip duplicates or other insert errors
                        if "PRIMARY KEY" in str(e):
                            print(f"   ⚠️  app_id {app_id} already exists, skipping")
                        else:
                            print(f"   ⚠️  Error inserting app_id {app_id}: {e}")
                        continue
                
                conn.commit()
                
        except Exception as e:
            print(f"❌ Error during insertion: {e}")
            return inserted_count
        
        print(f"✅ Inserted {inserted_count} mock XML records")
        return inserted_count
    
    def _generate_mock_xml(self, app_id: int) -> str:
        """
        Generate a valid mock Provenir XML record.
        
        Creates realistic XML with:
        - Unique app_id
        - 1-3 valid contacts with unique con_ids
        - Valid addresses and employment records
        - Required application fields
        """
        
        # Generate unique contact IDs
        con_ids = self._generate_unique_con_ids(random.randint(1, 3))
        
        # Generate contacts XML
        contacts_xml = self._generate_contacts_xml(con_ids)
        
        # Template XML structure
        xml_template = f'''<Provenir org="MOCK XML" ProductType="" Version="4.0.0" transactionID="MOCK{app_id}_12345" Org="" shred_version="3.0">
  <Request ID="{app_id}" UserID="" Workflow="W22" Timestamp="" Status="" Trans="" Readonly="0" Process="20000" Version="" Priority="" Timeout="" Trace="" LockedBy="" transactionCounter="9" _LockedBy="TEST@TEST.COM" LockedAt="">
    <CustData>
      <application app_type_code="PRODB" procs_date="2025-01-29 10:00:00.000" app_receive_date="2023-11-21 8:46:18.55" last_update_time="2023-11-3 16:26:23.729" signature_ind="Y" signed_date="" coupon_expiration_date="" suspicious_ind="" suspicious_tp_c="" name_match_flag="" address_match_flag="Y" ssn_match_flag="" opt_out_ind="" pricing_tier="59" supervisor_rev_ind="" solicitation_num="TEST{app_id}" pymnt_prot_plan_ind="N" credit_life_ind="" NAPSCI_sent_flag="" non_mon_793_sent_flag="" non_mon_699_sent_flag="" DataLink_sent_flag="" Partner_URL_ID="" telemarket_phone="" REVAM_inf_sent_flag="" non_mon_125_sent_flag="" non_mon_122_sent_flag="" non_mon_115_sent_flag="" non_mon_125_multran_sent_flag="" non_mon_216_sent_flag="" non_mon_146_multran_sent_flag="" non_mon_146_sent_flag="" app_source_ind="I" Benifit_id="" special_offer="" EODRet="WEBAPP" TUAccessCode="" existing_credit_line="" ois_app_type="STD" group_variable="" Debit_Initial_Deposit_date="" Debit_Initial_Deposit_amount="" prime_to_subprime_ind="" Debit_Funding_Source="" Debit_Refund_date="" Debit_Refund_amount="" Debit_NSF_Return_date="" existing_card_account_num="" mail_cell_pricing="" swiftpay_num="" init_open_account_flag="" non_mon_020_sent_flag="" non_mon_016_sent_flag="" non_mon_103_sent_flag="" auth_user_signed_ind="N" app_entry_date="01/29/2025" campaign_num="TEST" sec_user_signed_ind="" population_assignment="CM">
        <app_product decision_tp_c="APPRV" decision_date="2023-10-3 16:26:23.886" Risk_Model_reason1_tp_c="RISK MODEL REASON 1" Risk_Model_reason2_tp_c="RISK MODEL REASON 2" Risk_Model_reason3_tp_c="RISK MODEL REASON 3" Risk_Model_reason4_tp_c="" adverse_actn1_type_cd="AA ANYTHING-1 ANOTHER FIELD TOO LONG" adverse_actn2_type_cd="" adverse_actn3_type_cd="AA ANYTHING-3" adverse_actn4_type_cd="BLAH" adverse_actn5_type_cd="" intrnl_fraud_ssn_ind="Y" intrnl_fraud_address_ind="Y" duplicate_app_ind="Y" debt_to_income_ratio="9.18" booked_date="12/12/2024" multran_booked_date="09/09/2019" supervisor_rev_ind="Y" analyst_rev_ind="Y" pending_verif_ind="Y" csi_eligibility_ind="" monthly_debt="573.478" monthly_income="6250" precision_score="0" experian_fico_score="0" prescreen_fico_score="615" prescreen_risk_score="378" risk_model_score="" prescreen_risk_grade="E" prescreen_fico_grade="D" backend_risk_grade="U" backend_fico_grade="F" Vantage_Score_TU="" Vantage_Score_EX="" risk_model_score_JH="" risk_model_score_LP="" TU_DIE_score="" TU_TIE_score="" classic_08_score="" risk_model_score_JB="" VeridQA_Result="" InstantID_Score="50" disclosures="R" EX_FICO_08_score="610" EX_EVS_score="0" EX_TIE_score="29" EX_DIE_score="56" TU_L2C_score="0" GIACT_Response="" TU_FICO_09_Score="" fraud_rev_ind="Y" bank_debt_to_income_ratio="19.0923" regb_start_date="2023-9-21 8:46:46.046" regb_end_date="2023-12-21 8:18:18.018" complex_rev_ind="" booking_paused="Y" decision_model="EX FICO 08" decision_score="610" DIE_Plus_Score="78.14"/>
        {contacts_xml}
      </application>
    </CustData>
    <Reports />
    <Messages />
    <Rules />
    <Journals>
      <Journal Type="Script" ID="ProcStart" Timestamp="2025-01-29 10:00:00.000" Status="Start" />
      <Journal Type="Process" ID="PSHRD" Timestamp="Wed Jan 29 10:00:00 MST 2025" Status="Pass" />
    </Journals>
    <Traces />
    <Audits />
  </Request>
</Provenir>'''
        
        return xml_template
    
    def _generate_unique_con_ids(self, count: int) -> List[int]:
        """Generate unique contact IDs."""
        base_con_id = random.randint(100000, 900000)
        return [base_con_id + i for i in range(count)]
    
    def _generate_contacts_xml(self, con_ids: List[int]) -> str:
        """Generate contact XML blocks for given con_ids."""
        contacts = []
        
        for con_id in con_ids:
            contact_xml = f'''<contact con_id="{con_id}" ac_role_tp_c="PR" sms_consent_flag="true" first_name="TOM-{con_id}" initials="G" last_name="BARKER" suffix="" ssn="666883333" email="{con_id}@fake.com" birth_date="05/10/1973" mother_maiden_name="DAVIS" age="45" fraud_ind="S" banking_aba="" banking_account_number="{con_id}" banking_account_type="C">
          <app_prod_bcard card_id="{con_id}001" pd_tp_c="TEST" card_name="" requested_credit_line="1250" allocated_credit_line=2500" accnt_type_ind="" card_decision_tp_c="APPRV" signature_ind="" issue_card_ind="Y" account_number="123456789" multran_account_number="" cash_credit_line="2501" accnt_seq_no="" multran_accnt_seq_no="" sys_prin="" agent="" min_pay_due="10" />
          <contact_address address_seq_no="{con_id}100" address_tp_c="CURR" fax_no="" home_phone="5551234567" addr_1="" addr_2="" street_name="MAIN ST" street_number="505" street_prefix="" street_suffix="" street_tp_c="" unit="" po_box="" route="" rural_route="" city="DENVER" state="CO" zip="80202" ownership_tp_c="O" residence_monthly_pymnt="499" years_at_residence="1" months_at_residence="2" cell_phone="8018018001" Patriot_Act_street_number="" Patriot_Act_street_name="" Patriot_Act_unit="" Patriot_Act_city="" Patriot_Act_state="" Patriot_Act_zip="" />
          <contact_employment employment_seq_no="{con_id}200" employment_tp_c="CURR" b_name="MOCK INC {con_id}" b_job_title_tp_c="EMPL" b_years_at_job="5" b_months_at_job="6" b_self_employed_ind="" b_w2_provided_ind="" b_paystub_provided_ind="" b_1040_provided_ind="" b_addr_1="" b_addr_2="" b_street_number="" b_street_prefix="" b_street_name="" b_street_suffix="" b_street_tp_c="" b_unit="" b_po_box="" b_route="" b_rural_route="" b_city="" b_county="" b_state="" b_zip="" b_phone_no="" b_salary="50000" b_salary_basis_tp_c="YEAR" b_other_income_amt="0" b_other_income_source_tp_c="" b_othr_inc_basis_tp_c="YEAR" />
        </contact>'''
            contacts.append(contact_xml)
        
        return '\n        '.join(contacts)


class DatasetManager:
    """Manages test datasets for batch size and performance testing."""
    
    def __init__(self):
        """Initialize with database connection."""
        self.db_tester = DatabaseConnectionTester()
        success, message = self.db_tester.test_connection()
        if not success:
            raise RuntimeError(f"Database connection failed: {message}")
        
        self.connection_string = self.db_tester.build_connection_string()
        self.migration_engine = MigrationEngine(self.connection_string)
    
    def get_app_xml_count(self) -> int:
        """Get count of app_xml records."""
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM app_xml WHERE xml IS NOT NULL")
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting app_xml count: {e}")
            return 0
    
    def get_next_available_app_id(self) -> int:
        """Get next available app_id for mock data."""
        try:
            with self.migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(app_id) FROM app_xml")
                max_id = cursor.fetchone()[0]
                return (max_id or 0) + 1
        except Exception as e:
            print(f"Error getting max app_id: {e}")
            return 100000


def main():
    """Main entry point for mock data generation."""
    print("\n" + "="*80)
    print("📋 MOCK XML DATA GENERATOR")
    print("="*80)
    
    try:
        # Initialize manager
        manager = DatasetManager()
        
        # Check current data
        current_count = manager.get_app_xml_count()
        print(f"\n📊 Current app_xml records: {current_count}")
        
        # Generate mock data
        generator = MockXMLGenerator()
        
        # Generate different dataset sizes
        print("\n🔧 Available dataset sizes:")
        print("   1. Small (50 records) - Quick testing")
        print("   2. Medium (200 records) - Batch size testing")
        print("   3. Large (500 records) - Phase II benchmarking")
        print("   4. Custom size")
        
        choice = input("\nSelect dataset size (1-4): ").strip()
        
        if choice == "1":
            count = 50
        elif choice == "2":
            count = 200
        elif choice == "3":
            count = 500
        elif choice == "4":
            count_input = input("Enter number of records to generate: ").strip()
            try:
                count = int(count_input)
            except ValueError:
                print("Invalid number!")
                return 1
        else:
            print("Invalid choice!")
            return 1
        
        # Generate and insert
        start_app_id = manager.get_next_available_app_id()
        inserted = generator.generate_and_insert_mock_xmls(count, start_app_id)
        
        # Verify
        new_count = manager.get_app_xml_count()
        print(f"\n✅ Generation complete!")
        print(f"   Previous count: {current_count}")
        print(f"   New count: {new_count}")
        print(f"   Added: {new_count - current_count} records")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
