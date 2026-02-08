"""
Unit tests for warranty_field(N) mapping type.

The warranty_field mapping type creates rows in app_warranties_rl
with a composite PK of (app_id, warranty_type_enum). Each warranty type
(620–626) groups 4 columns (company_name, amount, term_months, policy_number)
plus an optional char_to_bit combo column (merrick_lienholder_flag for GAP/623).

Only creates a row when at least one non-bit field has meaningful data.

Contract entries (7 warranty types):
  - warranty_field(620) → Credit Disability   (credit_disability_*)
  - warranty_field(621) → Credit Life          (credit_life_*)
  - warranty_field(622) → Extended Warranty    (ext_warranty_*)
  - warranty_field(623) → GAP                  (gap_*) + merrick_lienholder_flag
  - warranty_field(624) → Other                (other_*)
  - warranty_field(625) → Roadside Assistance  (road_side_*)
  - warranty_field(626) → Service Contract     (service_contract_*)
"""

import pytest
from xml_extractor.mapping.data_mapper import DataMapper


class MockMapping:
    """Minimal mock for FieldMapping used by warranty_field tests."""
    def __init__(self, xml_path, xml_attribute, mapping_type, target_table="app_warranties_rl",
                 target_column="", data_type="string", data_length=None, nullable=True, required=False,
                 default_value=None):
        self.xml_path = xml_path
        self.xml_attribute = xml_attribute
        self.mapping_type = mapping_type
        self.target_table = target_table
        self.target_column = target_column
        self.data_type = data_type
        self.data_length = data_length
        self.nullable = nullable
        self.required = required
        self.default_value = default_value


WF_XML_PATH = "/Provenir/Request/CustData/IL_application/IL_backend_policies"


def _make_gap_mappings():
    """Build the 5 warranty_field(623) mappings for GAP (includes char_to_bit combo)."""
    return [
        MockMapping(WF_XML_PATH, "gap_company", ["warranty_field(623)"],
                    target_column="company_name", data_type="string", data_length=50),
        MockMapping(WF_XML_PATH, "gap_amount", ["warranty_field(623)"],
                    target_column="amount", data_type="decimal"),
        MockMapping(WF_XML_PATH, "gap_term", ["warranty_field(623)"],
                    target_column="term_months", data_type="smallint"),
        MockMapping(WF_XML_PATH, "gap_policy", ["warranty_field(623)"],
                    target_column="policy_number", data_type="string", data_length=30),
        MockMapping(WF_XML_PATH, "gap_lien", ["char_to_bit", "warranty_field(623)"],
                    target_column="merrick_lienholder_flag", data_type="bit", default_value="0"),
    ]


def _make_service_contract_mappings():
    """Build the 4 warranty_field(626) mappings for Service Contract."""
    return [
        MockMapping(WF_XML_PATH, "service_contract_company", ["warranty_field(626)"],
                    target_column="company_name", data_type="string", data_length=50),
        MockMapping(WF_XML_PATH, "service_contract_amount", ["warranty_field(626)"],
                    target_column="amount", data_type="decimal"),
        MockMapping(WF_XML_PATH, "service_contract_term", ["warranty_field(626)"],
                    target_column="term_months", data_type="smallint"),
        MockMapping(WF_XML_PATH, "service_contract_policy", ["warranty_field(626)"],
                    target_column="policy_number", data_type="string", data_length=30),
    ]


def _make_credit_life_mappings():
    """Build the 4 warranty_field(621) mappings for Credit Life."""
    return [
        MockMapping(WF_XML_PATH, "credit_life_company", ["warranty_field(621)"],
                    target_column="company_name", data_type="string", data_length=50),
        MockMapping(WF_XML_PATH, "credit_life_amount", ["warranty_field(621)"],
                    target_column="amount", data_type="decimal"),
        MockMapping(WF_XML_PATH, "credit_life_term", ["warranty_field(621)"],
                    target_column="term_months", data_type="smallint"),
        MockMapping(WF_XML_PATH, "credit_life_policy", ["warranty_field(621)"],
                    target_column="policy_number", data_type="string", data_length=30),
    ]


def _make_xml_data(**attrs):
    """Build xml_data dict with IL_backend_policies attributes."""
    return {
        WF_XML_PATH: {
            "attributes": attrs
        }
    }


class TestWarrantyFieldMapping:
    """Test suite for warranty_field(N) mapping type extraction."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper()

    def test_creates_single_warranty_row(self, data_mapper):
        """A single warranty type with populated data creates exactly one row."""
        xml_data = _make_xml_data(
            service_contract_company="GOOD SAM SERVICE",
            service_contract_amount="141",
            service_contract_term="72",
            service_contract_policy="GSS-X1VGHTYY",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_service_contract_mappings(), "100001"
        )

        assert len(records) == 1
        assert records[0]['warranty_type_enum'] == 626

    def test_row_contains_all_mapped_columns(self, data_mapper):
        """Each row should contain app_id, warranty_type_enum, mapped columns, and merrick_lienholder_flag default."""
        xml_data = _make_xml_data(
            service_contract_company="GOOD SAM SERVICE",
            service_contract_amount="141",
            service_contract_term="72",
            service_contract_policy="GSS-X1VGHTYY",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_service_contract_mappings(), "100001"
        )

        row = records[0]
        assert row['app_id'] == 100001
        assert row['warranty_type_enum'] == 626
        assert row['company_name'] == "GOOD SAM SERVICE"
        assert row['amount'] == "141"
        assert row['term_months'] == "72"
        assert row['policy_number'] == "GSS-X1VGHTYY"
        # merrick_lienholder_flag always present (DB NOT NULL), defaults to 0
        assert row['merrick_lienholder_flag'] == 0

    def test_multiple_warranty_types_create_multiple_rows(self, data_mapper):
        """Multiple warranty types with data create one row per type."""
        xml_data = _make_xml_data(
            service_contract_company="GOOD SAM SERVICE",
            service_contract_amount="141",
            service_contract_term="72",
            service_contract_policy="GSS-X1VGHTYY",
            credit_life_company="Life Game and Insurance",
            credit_life_amount="67",
            credit_life_term="120",
            credit_life_policy="LGI-67120",
        )
        mappings = _make_service_contract_mappings() + _make_credit_life_mappings()
        records = data_mapper._extract_warranty_records(xml_data, mappings, "100001")

        assert len(records) == 2
        enums = {r['warranty_type_enum'] for r in records}
        assert enums == {621, 626}

    def test_skips_empty_warranty_types(self, data_mapper):
        """Warranty types with no meaningful data are skipped."""
        xml_data = _make_xml_data(
            service_contract_company="",
            service_contract_amount="",
            service_contract_term="",
            service_contract_policy="",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_service_contract_mappings(), "100001"
        )

        assert records == []

    def test_creates_row_with_partial_data(self, data_mapper):
        """A warranty type creates a row even if only some fields are populated."""
        xml_data = _make_xml_data(
            service_contract_company="ACME Insurance",
            service_contract_amount="",
            service_contract_term="",
            service_contract_policy="",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_service_contract_mappings(), "100001"
        )

        assert len(records) == 1
        assert records[0]['company_name'] == "ACME Insurance"
        # Empty fields are not included in the row dict
        assert 'amount' not in records[0]
        assert 'term_months' not in records[0]
        assert 'policy_number' not in records[0]

    def test_gap_includes_char_to_bit_merrick_flag(self, data_mapper):
        """GAP (623) warranty includes merrick_lienholder_flag via char_to_bit combo."""
        xml_data = _make_xml_data(
            gap_company="Old Navy",
            gap_amount="100",
            gap_term="48",
            gap_policy="ON-65487",
            gap_lien="N",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_gap_mappings(), "325725"
        )

        assert len(records) == 1
        row = records[0]
        assert row['warranty_type_enum'] == 623
        assert row['company_name'] == "Old Navy"
        assert row['merrick_lienholder_flag'] == 0  # N → 0 via char_to_bit

    def test_gap_merrick_flag_yes(self, data_mapper):
        """GAP merrick_lienholder_flag: Y → 1 via char_to_bit."""
        xml_data = _make_xml_data(
            gap_company="Some Provider",
            gap_amount="200",
            gap_term="36",
            gap_policy="SP-999",
            gap_lien="Y",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_gap_mappings(), "100001"
        )

        assert len(records) == 1
        assert records[0]['merrick_lienholder_flag'] == 1  # Y → 1 via char_to_bit

    def test_gap_empty_lien_does_not_create_row_alone(self, data_mapper):
        """An empty gap_lien with no other gap data does not create a warranty row.

        char_to_bit fields always produce a value (0 or 1), but they don't
        count as meaningful data on their own.
        """
        xml_data = _make_xml_data(
            gap_company="",
            gap_amount="",
            gap_term="",
            gap_policy="",
            gap_lien="",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_gap_mappings(), "100001"
        )

        assert records == []

    def test_app_id_normalized_to_int(self, data_mapper):
        """app_id is normalized to int when numeric."""
        xml_data = _make_xml_data(
            service_contract_company="ACME",
            service_contract_amount="50",
            service_contract_term="12",
            service_contract_policy="A-1",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_service_contract_mappings(), "325725"
        )

        assert records[0]['app_id'] == 325725
        assert isinstance(records[0]['app_id'], int)

    def test_null_literal_values_are_not_meaningful(self, data_mapper):
        """Values like 'Null' or 'None' are not considered meaningful."""
        xml_data = _make_xml_data(
            service_contract_company="Null",
            service_contract_amount="None",
            service_contract_term="",
            service_contract_policy="",
        )
        records = data_mapper._extract_warranty_records(
            xml_data, _make_service_contract_mappings(), "100001"
        )

        assert records == []
