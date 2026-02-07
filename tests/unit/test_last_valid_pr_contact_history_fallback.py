import pytest
from lxml import etree

from xml_extractor.mapping.data_mapper import DataMapper
from xml_extractor.models import FieldMapping


class TestLastValidPrContactHistoryFallback:
    @pytest.fixture
    def mapper(self):
        return DataMapper(log_level="ERROR")

    def test_history_mapping_falls_back_to_earlier_primary_contact_with_value(self, mapper):
        xml = """
        <Provenir>
            <Request ID="12345">
                <CustData>
                    <application app_id="12345">
                        <contact con_id="1001" ac_role_tp_c="PR" CPS_Spouse_Address1="111 FIRST ST" />
                        <contact con_id="1002" ac_role_tp_c="PR" />
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """.strip()

        tree = etree.fromstring(xml.encode("utf-8"))
        mapper._current_xml_root = tree

        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/contact",
            xml_attribute="CPS_Spouse_Address1",
            target_table="app_historical_lookup",
            target_column="",
            data_type="string",
            mapping_type=["last_valid_pr_contact", "add_history"],
        )

        value = mapper._extract_from_last_valid_pr_contact(mapping)
        assert value == "111 FIRST ST"

    def test_history_mapping_prefers_last_primary_contact_when_populated(self, mapper):
        xml = """
        <Provenir>
            <Request ID="12345">
                <CustData>
                    <application app_id="12345">
                        <contact con_id="1001" ac_role_tp_c="PR" CPS_Spouse_Address1="111 FIRST ST" />
                        <contact con_id="1002" ac_role_tp_c="PR" CPS_Spouse_Address1="222 SECOND ST" />
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """.strip()

        tree = etree.fromstring(xml.encode("utf-8"))
        mapper._current_xml_root = tree

        mapping = FieldMapping(
            xml_path="/Provenir/Request/CustData/application/contact",
            xml_attribute="CPS_Spouse_Address1",
            target_table="app_historical_lookup",
            target_column="",
            data_type="string",
            mapping_type=["last_valid_pr_contact", "add_history"],
        )

        value = mapper._extract_from_last_valid_pr_contact(mapping)
        assert value == "222 SECOND ST"
