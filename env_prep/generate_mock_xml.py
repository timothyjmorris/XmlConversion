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
project_root = Path(__file__).parent.parent
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
                
                # Enable IDENTITY_INSERT for app_xml table
                try:
                    cursor.execute("SET IDENTITY_INSERT app_xml ON")
                    print(f"   ✅ IDENTITY_INSERT ON set successfully")
                except Exception as e:
                    print(f"   ❌ Failed to set IDENTITY_INSERT ON: {e}")
                    return 0
                
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
                            print(f"   Progress: {i + 1}/{count} records inserted...")
                    
                    except Exception as e:
                        # Skip duplicates or other insert errors
                        error_str = str(e)
                        if "PRIMARY KEY" in error_str or "Duplicate" in error_str:
                            print(f"   ⚠️  app_id {app_id} already exists, skipping")
                        else:
                            print(f"   ❌ Error inserting app_id {app_id}: {error_str}")
                            if i == 0:  # Print details for first error
                                print(f"      XML length: {len(xml_content)}")
                                print(f"      First 200 chars: {xml_content[:200]}")
                        continue
                
                # Disable IDENTITY_INSERT when done
                try:
                    cursor.execute("SET IDENTITY_INSERT app_xml OFF")
                    print(f"   ✅ IDENTITY_INSERT OFF set successfully")
                except Exception as e:
                    print(f"   ⚠️  Warning setting IDENTITY_INSERT OFF: {e}")
                
                # Commit transaction
                try:
                    conn.commit()
                    print(f"   ✅ Transaction committed successfully")
                except Exception as e:
                    print(f"   ❌ Failed to commit transaction: {e}")
                    return inserted_count
                
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
        - One primary contact (ac_role_tp_c="PR")
        - Valid addresses and employment records
        - Required application fields
        """
        
        # Generate unique contact ID
        con_id = random.randint(100000, 900000)
        
        # Generate contacts XML
        contacts_xml = self._generate_contacts_xml(con_id)
        
        # Template XML structure
        xml_template = f'''<Provenir org="" ProductType="" Version="4.0.0" transactionID="MOCK{app_id}_12345" Org="" shred_version="3.0">
  <Request ID="{app_id}" UserID="" Workflow="W22" Timestamp="" Status="" Trans="" Readonly="0" Process="99000" Version="" Priority="" Timeout="" Trace="" LockedBy="" transactionCounter="9" _LockedBy="TEST@TEST.COM" LockedAt="">
    <CustData>
      <application app_type_code="FPP" procs_date="2025-01-29 10:00:00.000" app_receive_date="01/29/2025" last_update_time="" signature_ind="Y" signed_date="" coupon_expiration_date="" suspicious_ind="" suspicious_tp_c="" name_match_flag="" address_match_flag="" ssn_match_flag="" opt_out_ind="" pricing_tier="" supervisor_rev_ind="" solicitation_num="TEST{app_id}" pymnt_prot_plan_ind="N" credit_life_ind="" NAPSCI_sent_flag="" non_mon_793_sent_flag="" non_mon_699_sent_flag="" DataLink_sent_flag="" Partner_URL_ID="" telemarket_phone="" REVAM_inf_sent_flag="" non_mon_125_sent_flag="" non_mon_122_sent_flag="" non_mon_115_sent_flag="" non_mon_125_multran_sent_flag="" non_mon_216_sent_flag="" non_mon_146_multran_sent_flag="" non_mon_146_sent_flag="" app_source_ind="I" Benifit_id="" special_offer="" EODRet="WEBAPP" TUAccessCode="" existing_credit_line="" ois_app_type="STD" group_variable="" Debit_Initial_Deposit_date="" Debit_Initial_Deposit_amount="" prime_to_subprime_ind="" Debit_Funding_Source="" Debit_Refund_date="" Debit_Refund_amount="" Debit_NSF_Return_date="" existing_card_account_num="" mail_cell_pricing="" swiftpay_num="" init_open_account_flag="" non_mon_020_sent_flag="" non_mon_016_sent_flag="" non_mon_103_sent_flag="" auth_user_signed_ind="N" app_entry_date="01/29/2025" campaign_num="TEST" sec_user_signed_ind="" population_assignment="">
        <app_product pd_seq_no="" req_prod_tp_c="VCRDU" pd_tp_c="" prmy_pd_ind="" req_plastics_qt="1" decision_tp_c="APPRV" scorecard="" score="" control_accnt_desired_ind="" bus_card_name="" decision_date="2025-01-29 10:00:00.000" dec_reason_c_1="" dec_reason_c_2="" dec_reason_c_3="" dec_reason_c_4="" Risk_Model_reason1_tp_c="" Risk_Model_reason2_tp_c="" cash_advance_ind="" annual_fee_tp_c="" autopay_ind="" overdraft_ind="" aba_number="" policy_override_employee_code="" override_tp_c="" control_accnt_number="" control_accnt_seq_no="" neuristics_edge_score="" adverse_actn1_type_cd="" adverse_actn2_type_cd="" adverse_actn3_type_cd="" adverse_actn4_type_cd="" intrnl_fraud_ssn_ind="" intrnl_fraud_address_ind="" existing_cardholder_ind="" duplicate_app_ind="N" debt_to_income_ratio="" booked_date="2025-01-29 10:00:00.000" supervisor_rev_ind="N" analyst_rev_ind="N" filed_bankruptcy_ind="" dismissed_bankruptcy_ind="" discharged_bankruptcy_ind="" thirty_day_delinq_num="" sixty_day_delinq_num="" ninety_day_delinq_num="" sixty_ninety_day_delinq_num="" one_twenty_day_delinq_num="" aggregate_balance="" merrick_tradelines_num="" prev_merrick_inq_num="" empirica_score="" delphi_score="" regbcloseddays_num="0" regbcloseddays2_num="" regbnewinfostartdate="" cendant_add_date="" ics_sent_date="" pending_verif_ind="N" letter_requested_ind="" csi_eligibility_ind="" csi_sent_date="" monthly_debt="" monthly_income="" bankruptcy_score="" pinnacle_score="" precision_score="" horizon_score="" experian_fico_score="" prescreen_risk_score="" risk_model_score="" lscampaign_num="" prescreen_fico_score="" multran_booked_date="" mars_model_score="" TU_DIE_score="0" />
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
    
    def _generate_contacts_xml(self, con_id: int) -> str:
        """Generate single primary contact XML block."""
        contact_xml = f'''<contact home_phone="5551234567" checking_accnt_ind="" checking_accnt_bank_name="" mother_maiden_name="" num_dependents="" fax_no="" ac_role_tp_c="PR" drivers_license="" drivers_license_state="" savings_accnt_ind="" savings_accnt_bank_name="" manual_pull_bureau="" initials="T" last_name="TEST" suffix="" con_id="{con_id}" title="" first_name="MOCK" birth_date="01/15/1980" sex_type_code="" fraud_ind="" ssn="111223333" ssn_last_4="3333" email="test@example.com" email_option_ind="" CPS_Spouse_Name="" CPS_Spouse_Address1="" CPS_Spouse_City="" CPS_Spouse_State="" CPS_Spouse_Zipcode="">
          <app_prod_bcard card_id="{con_id}001" pd_tp_c="TEST" card_name="" requested_credit_line="" allocated_credit_line="" accnt_type_ind="" card_decision_tp_c="APPRV" signature_ind="" issue_card_ind="Y" account_number="" multran_account_number="" cash_credit_line="" accnt_seq_no="" multran_accnt_seq_no="" sys_prin="" agent="" min_pay_due="10" />
          <contact_address address_seq_no="{con_id}100" address_tp_c="CURR" fax_no="" home_phone="5551234567" addr_1="" addr_2="" street_name="123 MAIN ST APT 500" street_number="" street_prefix="" street_suffix="" street_tp_c="" unit="" po_box="" route="" rural_route="" city="DENVER" state="CO" zip="80202" ownership_tp_c="" residence_monthly_pymnt="0" years_at_residence="" months_at_residence="" cell_phone="" Patriot_Act_street_number="" Patriot_Act_street_name="" Patriot_Act_unit="" Patriot_Act_city="" Patriot_Act_state="" Patriot_Act_zip="" />
          <contact_employment employment_seq_no="{con_id}200" employment_tp_c="CURR" b_name="MOCK INC" b_job_title_tp_c="EMPL" b_years_at_job="5" b_months_at_job="6" b_self_employed_ind="" b_w2_provided_ind="" b_paystub_provided_ind="" b_1040_provided_ind="" b_addr_1="" b_addr_2="" b_street_number="" b_street_prefix="" b_street_name="" b_street_suffix="" b_street_tp_c="" b_unit="" b_po_box="" b_route="" b_rural_route="" b_city="" b_county="" b_state="" b_zip="" b_phone_no="" b_salary="50000" b_salary_basis_tp_c="YEAR" b_other_income_amt="0" b_other_income_source_tp_c="" b_othr_inc_basis_tp_c="YEAR" />
        </contact>'''
        return contact_xml


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
