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
        con_id = random.randint(1000, 900000) + app_id
        
        # Generate contacts XML
        contacts_xml = self._generate_contacts_xml(con_id)
        
        # Template XML structure
        xml_template = f'''<Provenir TestType="MOCK_APP_{app_id}_12345">
            <Request ID="{app_id}" Process="20000" Priority="" LockedBy="" _LockedBy="MOCK_APP_{app_id}@TEST.COM" LockedAt="">
                <CustData>
                    <application app_type_code="PRODB" app_receive_date="2023-11-21 8:46:18.{app_id}" last_update_time="2024-11-3 16:26:23.{app_id}" signature_ind="N" name_match_flag="Y" address_match_flag="N" ssn_match_flag="R" pricing_tier="59" solicitation_num="MOCK_{app_id}T" pymnt_prot_plan_ind="Y" credit_life_ind="Y" campaign_num="T{app_id}" swiftpay_num="1313131313" mail_cell_pricing="XJEFH8E171" Partner_URL_ID="mock-test-app_id-{app_id}@bro.com" app_source_ind="I" Debit_Refund_Failed="Y" Debit_Initial_Deposit_date="10/11/2024" Debit_Initial_Deposit_amount="129.46" Debit_NSF_Return_date="10/12/2024" Debit_Refund_amount="31.53" Debit_Refund_date="2024-8-8 8:08:48.008" Debit_Funding_Source="ACH" special_offer="3" population_assignment="CM" verification_source="TLO" secure_ach_amount="199.19" IP_address="10.20.138.103" EXPinNumber="{app_id}" assignedTo="test-{app_id}@testy.com" esign_consent_flag="false" paperless_flag="true" sms_consent_flag="true" secure_ach_sent_flag="Y">
                        <app_product decision_tp_c="APPRV" decision_date="2023-10-30 16:26:23.886" Risk_Model_reason1_tp_c="RISK_{app_id}" Risk_Model_reason2_tp_c="RISK_{app_id}" Risk_Model_reason3_tp_c="RISK_{app_id}" Risk_Model_reason4_tp_c="" adverse_actn1_type_cd="AA_{app_id}" adverse_actn2_type_cd="" adverse_actn3_type_cd="AA_{app_id}" adverse_actn4_type_cd="" adverse_actn5_type_cd="" debt_to_income_ratio="9.18" booked_date="12/12/2024" multran_booked_date="09/09/2019" supervisor_rev_ind="N" analyst_rev_ind="Y" pending_verif_ind="Y" monthly_debt="573.478" monthly_income="6250" precision_score="0" experian_fico_score="0" prescreen_fico_score="615" prescreen_risk_score="378" risk_model_score="" prescreen_risk_grade="E" prescreen_fico_grade="D" backend_risk_grade="U" backend_fico_grade="F" Vantage_Score_TU="" Vantage_Score_EX="" risk_model_score_JH="" risk_model_score_LP="" TU_DIE_score="" TU_TIE_score="" classic_08_score="" risk_model_score_JB="" VeridQA_Result="" InstantID_Score="50" disclosures="R" EX_FICO_08_score="610" EX_EVS_score="0" EX_TIE_score="29" EX_DIE_score="56" TU_L2C_score="0" GIACT_Response="" TU_FICO_09_Score="" fraud_rev_ind="Y" bank_debt_to_income_ratio="19.0923" regb_start_date="2023-9-21 8:46:46.{app_id}" regb_end_date="2023-12-21 8:18:18.{app_id}" booking_paused="N" decision_model="EX FICO 08" decision_score="610" DIE_Plus_Score="78.{app_id}" />
                        <rmts_info campaign_number="X4J" name_match_flag="N" ssn_match_flag="N" address_match_flag="Y" primary_first_name="MARKY-MOCK-{app_id}" primary_middle_name="G" primary_last_name="WOODFIELD" primary_suffix="" primary_ssn="{app_id}" pri_cur_street_num="{app_id}" pri_cur_street_name="S {app_id} HWY" pri_apt_number="{app_id}" pri_rural_rt_num="21" pri_po_box_num="12" pri_city="HORSE CAVE - {app_id}" pri_state="KY" pri_zip_code="{app_id}" special_flag_5="A" special_flag_6="G" special_flag_7="A" special_flag_8="Z" aaa_misc_field_4="Wah" CB_prescreen_birth_date="05/10/1978" auth_user_is_spouse="Y" minimum_interest_charge="1.00444" account_setup_fee="99" additional_card_fee="12" late_payment_fee="Up to $40" over_limit_fee="103.3" returned_payment_fee="40" apr="0.2{app_id}" annual_fee="072.00" cash_advance_apr="0.347" foreign_percent="{app_id}.04" cash_advance_fee="36.24" cash_advance_percent="9.{app_id}" cash_apr_margin="7.7" intro_cash_advance_apr="{app_id}.1432197654" intro_purchase_apr="1.000666" min_payment_percent="4.{app_id}" purchase_apr_margin="3.3" seg_plan_version="BIG" min_payment_fee="{app_id}" />
                        {contacts_xml}
                    </application>
                </CustData>
            </Request>
        </Provenir>'''
        
        return xml_template
    
    def _generate_unique_con_ids(self, count: int) -> List[int]:
        """Generate unique contact IDs."""
        base_con_id = random.randint(100000, 900000)
        return [base_con_id + i for i in range(count)]
    
    def _generate_contacts_xml(self, con_id: int) -> str:
        """Generate single primary contact XML block."""
        contact_xml = f'''<contact con_id="{con_id}"  ac_role_tp_c="PR" sms_consent_flag="false" first_name="TOMMY-{con_id}" initials="G" last_name="BARKER" suffix="" ssn="666883333" email="tommy-{con_id}@mock.com" birth_date="05/10/1973" mother_maiden_name="DAVIS" fraud_ind="S" banking_aba="19201920" banking_account_number="900890089008" banking_account_type="C" >
          <app_prod_bcard card_decision_tp_c="APPRV" pd_tp_c="X4J" requested_credit_line="{con_id}" allocated_credit_line="2003" accnt_type_ind="" account_number="{con_id}" multran_account_number="{con_id}" min_pay_due="315.31" credit_line2="620" max_line="1666"/>
          <contact_address address_tp_c="CURR" residence_monthly_pymnt="893.55" city="MOCK CITY - {con_id}" rural_route="RR#1" state="KY" po_box="{con_id}" street_name="JACKSON HWY" street_number="{con_id} S" unit="12" home_phone="801{con_id}" cell_phone="401{con_id}" address_line_1="LOTS" zip="{con_id}" months_at_residence="11" years_at_residence="2" ownership_tp_c="O" />
          <contact_employment employment_tp_c="CURR" b_phone_no="101{con_id}" b_addr_1="LINE ONE - {con_id}" b_unit="#c-30" b_zip="10{con_id}" b_state="WA" b_street_name="SNAME" b_street_number="{con_id} W" b_city="THE BIG CITY" b_other_income_amt="888" b_other_income_source_detail="other source detail" b_name="MOCK-STYLE {con_id}" b_job_title_tp_c="BIG GUY" b_income_source_nontaxable="Y" b_self_employed_ind="Y" b_months_at_job="6" b_years_at_job="1" b_primary_income_source_tp_c="INVEST" b_salary="{con_id}" b_salary_basis_tp_c="ANNUM" b_othr_inc_basis_tp_c="WEEK" b_other_income_source_tp_c="BONUS" />
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
