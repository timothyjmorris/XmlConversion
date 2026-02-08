"""
Unit tests for policy_exceptions(N) mapping type.

The policy_exceptions mapping type creates rows in app_policy_exceptions_rl
with a composite PK of (app_id, policy_exception_type_enum). Each enum-parameterized
entry extracts a reason_code from an XML attribute, and the empty-param entry
provides shared notes across all created rows.

Contract entries:
  - policy_exceptions(630) → override_capacity   → reason_code, enum=630 (Capacity)
  - policy_exceptions(631) → override_collateral_program → reason_code, enum=631 (Collateral/Program)
  - policy_exceptions(632) → override_credit      → reason_code, enum=632 (Credit)
  - policy_exceptions()    → override_type_code_notes → notes (shared)
"""

import pytest
from xml_extractor.mapping.data_mapper import DataMapper


class MockMapping:
    """Minimal mock for FieldMapping used by policy_exceptions tests."""
    def __init__(self, xml_path, xml_attribute, mapping_type, target_table="app_policy_exceptions_rl",
                 target_column="", data_type="string", data_length=None, nullable=True, required=False):
        self.xml_path = xml_path
        self.xml_attribute = xml_attribute
        self.mapping_type = mapping_type
        self.target_table = target_table
        self.target_column = target_column
        self.data_type = data_type
        self.data_length = data_length
        self.nullable = nullable
        self.required = required


PE_XML_PATH = "/Provenir/Request/CustData/IL_application/IL_app_decision_info"


def _make_mappings():
    """Build the 4 standard policy_exceptions mappings matching the RL contract."""
    return [
        MockMapping(PE_XML_PATH, "override_capacity", ["policy_exceptions(630)"]),
        MockMapping(PE_XML_PATH, "override_collateral_program", ["policy_exceptions(631)"]),
        MockMapping(PE_XML_PATH, "override_credit", ["policy_exceptions(632)"]),
        MockMapping(PE_XML_PATH, "override_type_code_notes", ["policy_exceptions()"]),
    ]


def _make_xml_data(**attrs):
    """Build xml_data dict with IL_app_decision_info attributes."""
    return {
        PE_XML_PATH: {
            "attributes": attrs
        }
    }


class TestPolicyExceptionsMapping:
    """Test suite for policy_exceptions(N) mapping type extraction."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper()

    def test_creates_rows_for_each_populated_enum(self, data_mapper):
        """Each enum entry with a non-empty reason_code creates exactly one row."""
        xml_data = _make_xml_data(
            override_capacity="EXDTIIR",
            override_collateral_program="",
            override_credit="MFSCORE",
            override_type_code_notes="Some notes here",
        )
        records = data_mapper._extract_policy_exception_records(xml_data, _make_mappings(), "100001")

        assert len(records) == 2
        enums = {r['policy_exception_type_enum'] for r in records}
        assert enums == {630, 632}

    def test_reason_code_values(self, data_mapper):
        """reason_code comes from the xml_attribute value for each enum entry."""
        xml_data = _make_xml_data(
            override_capacity="EXDTIIR",
            override_collateral_program="LTLGT1K",
            override_credit="",
            override_type_code_notes="",
        )
        records = data_mapper._extract_policy_exception_records(xml_data, _make_mappings(), "100001")

        by_enum = {r['policy_exception_type_enum']: r for r in records}
        assert by_enum[630]['reason_code'] == "EXDTIIR"
        assert by_enum[631]['reason_code'] == "LTLGT1K"

    def test_shared_notes_attached_to_all_rows(self, data_mapper):
        """The policy_exceptions() entry provides notes shared across all created rows."""
        xml_data = _make_xml_data(
            override_capacity="EXDTIIR",
            override_collateral_program="LTLGT1K",
            override_credit="MFSCORE",
            override_type_code_notes="DTI at Experian 45%, okay based on reserves",
        )
        records = data_mapper._extract_policy_exception_records(xml_data, _make_mappings(), "100001")

        assert len(records) == 3
        for r in records:
            assert r['notes'] == "DTI at Experian 45%, okay based on reserves"

    def test_notes_none_when_no_shared_notes(self, data_mapper):
        """When override_type_code_notes is empty, notes is None on each row."""
        xml_data = _make_xml_data(
            override_capacity="MDPGT1M",
            override_collateral_program="",
            override_credit="",
            override_type_code_notes="",
        )
        records = data_mapper._extract_policy_exception_records(xml_data, _make_mappings(), "100001")

        assert len(records) == 1
        assert records[0]['notes'] is None

    def test_no_rows_when_no_reason_codes(self, data_mapper):
        """No rows created when all reason_code attributes are empty."""
        xml_data = _make_xml_data(
            override_capacity="",
            override_collateral_program="",
            override_credit="",
            override_type_code_notes="Some orphaned notes",
        )
        records = data_mapper._extract_policy_exception_records(xml_data, _make_mappings(), "100001")
        assert records == []

    def test_app_id_normalized_to_int(self, data_mapper):
        """app_id is normalized to int when numeric."""
        xml_data = _make_xml_data(
            override_capacity="CODE1",
            override_collateral_program="",
            override_credit="",
            override_type_code_notes="",
        )
        records = data_mapper._extract_policy_exception_records(xml_data, _make_mappings(), "325725")

        assert records[0]['app_id'] == 325725
        assert isinstance(records[0]['app_id'], int)

    def test_row_structure_has_all_keys(self, data_mapper):
        """Each row has exactly the 4 expected keys."""
        xml_data = _make_xml_data(
            override_capacity="CODE1",
            override_collateral_program="",
            override_credit="",
            override_type_code_notes="Note text",
        )
        records = data_mapper._extract_policy_exception_records(xml_data, _make_mappings(), "100001")

        assert len(records) == 1
        assert set(records[0].keys()) == {'app_id', 'policy_exception_type_enum', 'reason_code', 'notes'}
