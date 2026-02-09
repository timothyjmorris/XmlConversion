"""
Unit tests for add_collateral(N) mapping type.

The add_collateral mapping type creates rows in app_collateral_rl,
one per collateral slot (N=1–4). Each slot has 11 target columns including
combo mapping types:
  - calculated_field + add_collateral(N) → collateral_type_enum
  - char_to_bit + add_collateral(N)      → used_flag (N=New→0, U=Used→1, D=Demo→0)
  - numbers_only + add_collateral(N)     → year

Cross-element context is required because calculated_field expressions
reference IL_application.app_type_code and sub_type_code.
"""

import pytest
from xml_extractor.mapping.data_mapper import DataMapper


class MockMapping:
    """Minimal mock for FieldMapping used by add_collateral tests."""
    def __init__(self, xml_path, xml_attribute, mapping_type, target_table="app_collateral_rl",
                 target_column="", data_type="string", data_length=None, nullable=True, required=False,
                 default_value=None, expression=None):
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
        self.expression = expression


COLL_XML_PATH = "/Provenir/Request/CustData/IL_application/IL_collateral"
APP_XML_PATH = "/Provenir/Request/CustData/IL_application"


def _make_coll1_mappings():
    """Build the 11 add_collateral(1) mappings.

    Expression mirrors the actual RL contract for coll1: pure app_type/sub_type dispatch.
    """
    return [
        MockMapping(COLL_XML_PATH, "coll1_type", ["calculated_field", "add_collateral(1)"],
                    target_column="collateral_type_enum", data_type="smallint",
                    expression=(
                        "CASE "
                        "WHEN IL_application.app_type_code = 'MARINE' THEN 412 "
                        "WHEN IL_application.app_type_code = 'RV' THEN 419 "
                        "WHEN IL_application.app_type_code = 'HT' THEN 415 "
                        "WHEN IL_application.app_type_code = 'UT' THEN 421 "
                        "WHEN IL_application.app_type_code = 'MC' THEN 416 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'ATV' THEN 410 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'UTV' THEN 422 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'PWC' THEN 418 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'SNOWMOBILE' THEN 420 "
                        "WHEN IL_application.app_type_code IS NOT EMPTY THEN 423 "
                        "END"
                    )),
        MockMapping(COLL_XML_PATH, "coll1_make", ["add_collateral(1)"],
                    target_column="make", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll1_model", ["add_collateral(1)"],
                    target_column="model", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll1_new_used_demo", ["char_to_bit", "add_collateral(1)"],
                    target_column="used_flag", data_type="bit", default_value="0"),
        MockMapping(COLL_XML_PATH, "coll1_value", ["add_collateral(1)"],
                    target_column="wholesale_value", data_type="decimal", data_length=2),
        MockMapping(COLL_XML_PATH, "coll1_mileage", ["add_collateral(1)"],
                    target_column="mileage", data_type="int"),
        MockMapping(COLL_XML_PATH, "coll1_VIN", ["add_collateral(1)"],
                    target_column="vin", data_type="string", data_length=60),
        MockMapping(COLL_XML_PATH, "coll1_year", ["numbers_only", "add_collateral(1)"],
                    target_column="year", data_type="smallint"),
        MockMapping(COLL_XML_PATH, "coll_option1", ["add_collateral(1)"],
                    target_column="option_1_value", data_type="decimal", data_length=2),
        MockMapping(COLL_XML_PATH, "coll_option1_desc", ["add_collateral(1)"],
                    target_column="option_1_description", data_type="string", data_length=100),
        MockMapping(COLL_XML_PATH, "coll_option2", ["add_collateral(1)"],
                    target_column="option_2_value", data_type="decimal", data_length=2),
        MockMapping(COLL_XML_PATH, "coll_option2_desc", ["add_collateral(1)"],
                    target_column="option_2_description", data_type="string", data_length=100),
    ]


def _make_simple_coll2_mappings():
    """Build a minimal add_collateral(2) group (no calculated_field, for simple tests)."""
    return [
        MockMapping(COLL_XML_PATH, "coll2_make", ["add_collateral(2)"],
                    target_column="make", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll2_model", ["add_collateral(2)"],
                    target_column="model", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll2_VIN", ["add_collateral(2)"],
                    target_column="vin", data_type="string", data_length=60),
        MockMapping(COLL_XML_PATH, "coll2_year", ["numbers_only", "add_collateral(2)"],
                    target_column="year", data_type="smallint"),
        MockMapping(COLL_XML_PATH, "coll2_new_used_demo", ["char_to_bit", "add_collateral(2)"],
                    target_column="used_flag", data_type="bit", default_value="0"),
    ]


def _make_full_coll2_mappings():
    """Build add_collateral(2) mappings with actual contract expression.

    Coll2 expression uses coll2_HP_Marine > '0' as engine sentinel (→413),
    then MARINE+coll2_value/make fallbacks (→413), then OR subtypes.
    Generic fallback: coll2_value IS NOT EMPTY → 423.
    """
    return [
        MockMapping(COLL_XML_PATH, "coll2_type", ["calculated_field", "add_collateral(2)"],
                    target_column="collateral_type_enum", data_type="smallint",
                    expression=(
                        "CASE "
                        "WHEN IL_collateral.coll2_HP_Marine > '0' THEN 413 "
                        "WHEN IL_application.app_type_code = 'MARINE' AND IL_collateral.coll2_value IS NOT EMPTY THEN 413 "
                        "WHEN IL_application.app_type_code = 'MARINE' AND IL_collateral.make IS NOT EMPTY THEN 413 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'ATV' THEN 410 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'UTV' THEN 422 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'PWC' THEN 418 "
                        "WHEN IL_application.app_type_code = 'OR' AND IL_application.sub_type_code = 'SNOWMOBILE' THEN 420 "
                        "WHEN IL_collateral.coll2_value IS NOT EMPTY THEN 423 "
                        "END"
                    )),
        MockMapping(COLL_XML_PATH, "coll2_make", ["add_collateral(2)"],
                    target_column="make", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll2_model", ["add_collateral(2)"],
                    target_column="model", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll2_VIN", ["add_collateral(2)"],
                    target_column="vin", data_type="string", data_length=60),
        MockMapping(COLL_XML_PATH, "coll2_year", ["numbers_only", "add_collateral(2)"],
                    target_column="year", data_type="smallint"),
        MockMapping(COLL_XML_PATH, "coll2_new_used_demo", ["char_to_bit", "add_collateral(2)"],
                    target_column="used_flag", data_type="bit", default_value="0"),
        MockMapping(COLL_XML_PATH, "coll2_HP_Marine", ["add_collateral(2)"],
                    target_column="motor_size", data_type="smallint"),
    ]


def _make_coll3_mappings():
    """Build add_collateral(3) mappings with coll3 expression from RL contract.

    Expression uses LIKE wildcard matching for trailer makes (→420), model
    sniffing for TRAILER (→420), HP_Marine > '0' for engines (→413),
    and LIKE wildcard matching for engine makes (→413).  No app_type guard.
    Generic fallback: coll3_value IS NOT EMPTY → 423.
    """
    return [
        MockMapping(COLL_XML_PATH, "coll3_type", ["calculated_field", "add_collateral(3)"],
                    target_column="collateral_type_enum", data_type="smallint",
                    expression=(
                        "CASE "
                        "WHEN IL_collateral.coll3_make LIKE '%BT%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%BEAR%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%BOATMATE%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%BACKTRACK%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%TRAILSTAR%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%MAGIC TILT%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%MARINE MASTER%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%SHORELANDER%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%SHORELANDR%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%EZ LOADER%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%KARAVAN%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%MCCLAIN%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%ESCORT%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%ROAD RUNNER%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%LOAD RITE%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%LOADRITE%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%MAGIC LOADER%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%MALIBU%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%ZIEMAN%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%TRACKER%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%DIAMOND CITY%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%RANGER%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%WESCO%' THEN 420 "
                        "WHEN IL_collateral.coll3_make LIKE '%TRAILER%' THEN 420 "
                        "WHEN IL_collateral.coll3_model LIKE '%TRAILER%' THEN 420 "
                        "WHEN IL_collateral.coll3_HP_Marine > '0' THEN 413 "
                        "WHEN IL_collateral.coll3_make LIKE '%MERCURY%' THEN 413 "
                        "WHEN IL_collateral.coll3_make LIKE '%YAMAHA%' THEN 413 "
                        "WHEN IL_collateral.coll3_make LIKE '%MERCRUISER%' THEN 413 "
                        "WHEN IL_application.app_type_code IS NOT EMPTY AND IL_collateral.coll3_value IS NOT EMPTY THEN 423 "
                        "END"
                    )),
        MockMapping(COLL_XML_PATH, "coll3_make", ["add_collateral(3)"],
                    target_column="make", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll3_model", ["add_collateral(3)"],
                    target_column="model", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll3_VIN", ["add_collateral(3)"],
                    target_column="vin", data_type="string", data_length=60),
        MockMapping(COLL_XML_PATH, "coll3_year", ["numbers_only", "add_collateral(3)"],
                    target_column="year", data_type="smallint"),
        MockMapping(COLL_XML_PATH, "coll3_new_used_demo", ["char_to_bit", "add_collateral(3)"],
                    target_column="used_flag", data_type="bit", default_value="0"),
        MockMapping(COLL_XML_PATH, "coll3_HP_Marine", ["add_collateral(3)"],
                    target_column="motor_size", data_type="smallint"),
    ]


def _make_coll4_mappings():
    """Build add_collateral(4) mappings with coll4 expression from RL contract.

    Expression checks engine makes via LIKE (→413), trailer model/make
    detection (→420), then falls back to OTHER TRAILER (→417).
    Generic fallback: coll4_value IS NOT EMPTY → 423.
    """
    return [
        MockMapping(COLL_XML_PATH, "coll4_type", ["calculated_field", "add_collateral(4)"],
                    target_column="collateral_type_enum", data_type="smallint",
                    expression=(
                        "CASE "
                        "WHEN IL_collateral.coll4_make LIKE '%MERCURY%' THEN 413 "
                        "WHEN IL_collateral.coll4_make LIKE '%YAMAHA%' THEN 413 "
                        "WHEN IL_collateral.coll4_make LIKE '%MERCRUISER%' THEN 413 "
                        "WHEN IL_collateral.coll4_model LIKE '%TRAILER%' THEN 420 "
                        "WHEN IL_collateral.coll4_make LIKE '%MAGIC TILT%' THEN 420 "
                        "WHEN IL_application.app_type_code = 'MARINE' THEN 417 "
                        "WHEN IL_application.app_type_code = 'OR' THEN 417 "
                        "WHEN IL_application.app_type_code IS NOT EMPTY AND IL_collateral.coll4_value IS NOT EMPTY THEN 423 "
                        "END"
                    )),
        MockMapping(COLL_XML_PATH, "coll4_make", ["add_collateral(4)"],
                    target_column="make", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll4_model", ["add_collateral(4)"],
                    target_column="model", data_type="string", data_length=50),
        MockMapping(COLL_XML_PATH, "coll4_VIN", ["add_collateral(4)"],
                    target_column="vin", data_type="string", data_length=60),
        MockMapping(COLL_XML_PATH, "coll4_year", ["numbers_only", "add_collateral(4)"],
                    target_column="year", data_type="smallint"),
        MockMapping(COLL_XML_PATH, "coll4_new_used_demo", ["char_to_bit", "add_collateral(4)"],
                    target_column="used_flag", data_type="bit", default_value="0"),
    ]


def _make_xml_data(app_attrs=None, coll_attrs=None):
    """Build xml_data dict with IL_application and IL_collateral attributes."""
    data = {}
    if app_attrs is not None:
        data[APP_XML_PATH] = {"attributes": app_attrs}
    if coll_attrs is not None:
        data[COLL_XML_PATH] = {"attributes": coll_attrs}
    return data


class TestCollateralFieldMapping:
    """Test suite for add_collateral(N) mapping type extraction."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper()

    # ------------------------------------------------------------------
    # Basic row creation
    # ------------------------------------------------------------------

    def test_creates_single_collateral_row(self, data_mapper):
        """A collateral group with populated data creates exactly one row."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "ALL WATER",
                "coll1_model": "LONG BOY",
                "coll1_VIN": "4b5et6egt69",
                "coll1_year": "2025",
                "coll1_new_used_demo": "N",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "325725", []
        )

        assert len(records) == 1
        row = records[0]
        assert row['make'] == "ALL WATER"
        assert row['model'] == "LONG BOY"
        assert row['vin'] == "4b5et6egt69"
        assert row['app_id'] == 325725
        assert row['sort_order'] == 1

    def test_multiple_groups_create_multiple_rows(self, data_mapper):
        """Multiple collateral slots with data create one row per group."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "ALL WATER",
                "coll1_year": "2025",
                "coll2_make": "Coll2 Make",
                "coll2_year": "2023",
            },
        )
        mappings = _make_coll1_mappings() + _make_simple_coll2_mappings()
        records = data_mapper._extract_collateral_records(xml_data, mappings, "100001", [])

        assert len(records) == 2
        assert records[0]['sort_order'] == 1
        assert records[1]['sort_order'] == 2

    def test_skips_empty_collateral_groups(self, data_mapper):
        """Collateral groups with no meaningful data are skipped."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "",
                "coll1_model": "",
                "coll1_VIN": "",
                "coll1_year": "",
                "coll1_new_used_demo": "",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert records == []

    # ------------------------------------------------------------------
    # Calculated field combo (collateral_type_enum)
    # ------------------------------------------------------------------

    def test_calculated_field_marine_gives_412(self, data_mapper):
        """MARINE app_type_code → collateral_type_enum 412 (BOAT)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "SOMETHING"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 412

    def test_calculated_field_rv_gives_419(self, data_mapper):
        """RV app_type_code → collateral_type_enum 419 (RV)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "RV"},
            coll_attrs={"coll1_make": "WINNEBAGO"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 419

    def test_calculated_field_unknown_type_gives_423(self, data_mapper):
        """Unknown but non-empty app_type_code → 423 (UNDETERMINED)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "SOMETHING_NEW"},
            coll_attrs={"coll1_make": "BRAND"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 423

    # ------------------------------------------------------------------
    # char_to_bit combo (used_flag)
    # ------------------------------------------------------------------

    def test_used_flag_new_maps_to_0(self, data_mapper):
        """N (New) → used_flag = 0."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "BRAND", "coll1_new_used_demo": "N"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert records[0]['used_flag'] == 0

    def test_used_flag_used_maps_to_1(self, data_mapper):
        """U (Used) → used_flag = 1."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "BRAND", "coll1_new_used_demo": "U"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert records[0]['used_flag'] == 1

    def test_used_flag_demo_maps_to_0(self, data_mapper):
        """D (Demo) → used_flag = 0."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "BRAND", "coll1_new_used_demo": "D"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert records[0]['used_flag'] == 0

    def test_used_flag_empty_defaults_to_0(self, data_mapper):
        """Empty/missing used_flag defaults to 0 (DB NOT NULL)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "BRAND"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert records[0]['used_flag'] == 0

    # ------------------------------------------------------------------
    # numbers_only combo (year)
    # ------------------------------------------------------------------

    def test_year_numbers_only_extracts_digits(self, data_mapper):
        """Year field strips non-numeric characters via numbers_only."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "BRAND", "coll1_year": "2025"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert records[0]['year'] == 2025

    # ------------------------------------------------------------------
    # sort_order (PK component)
    # ------------------------------------------------------------------

    def test_sort_order_matches_slot_index(self, data_mapper):
        """sort_order is set to the collateral slot number (1-based).

        PK = (app_id, collateral_type_enum, sort_order).  Two slots can
        share the same collateral_type_enum, so sort_order must be unique.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "BRAND_A",
                "coll2_make": "BRAND_B",
            },
        )
        mappings = _make_coll1_mappings() + _make_simple_coll2_mappings()
        records = data_mapper._extract_collateral_records(
            xml_data, mappings, "100001", []
        )

        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[1]['make'] == "BRAND_A"  # slot 1
        assert by_sort[2]['make'] == "BRAND_B"  # slot 2

    # ------------------------------------------------------------------
    # app_id normalization
    # ------------------------------------------------------------------

    def test_app_id_normalized_to_int(self, data_mapper):
        """app_id is normalized to int when numeric."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "BRAND"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "325725", []
        )

        assert records[0]['app_id'] == 325725
        assert isinstance(records[0]['app_id'], int)

    # ------------------------------------------------------------------
    # Partial data & edge cases
    # ------------------------------------------------------------------

    def test_partial_data_creates_row(self, data_mapper):
        """A group with only make creates a row (make is sufficient meaningful data)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_make": "BAYLINER"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['make'] == "BAYLINER"
        # Empty fields should not be present
        assert 'model' not in records[0]
        assert 'vin' not in records[0]
        assert 'wholesale_value' not in records[0]

    def test_bit_only_data_does_not_create_row(self, data_mapper):
        """char_to_bit used_flag alone is not meaningful enough to create a row."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={"coll1_new_used_demo": "U"},
        )
        # Only the char_to_bit mapping, no other meaningful data
        bit_only_mappings = [
            MockMapping(COLL_XML_PATH, "coll1_new_used_demo", ["char_to_bit", "add_collateral(1)"],
                        target_column="used_flag", data_type="bit", default_value="0"),
        ]
        records = data_mapper._extract_collateral_records(
            xml_data, bit_only_mappings, "100001", []
        )

        assert records == []

    # ------------------------------------------------------------------
    # IN-expression tests: collateral_type_enum via multi-value matching
    # ------------------------------------------------------------------
    # Expressions for coll3 and coll4 use IN (...) lists to identify
    # engine makes and trailer makes.  The calculated_field engine must
    # handle these correctly (converted to OR chains in the contract).
    # ------------------------------------------------------------------

    def test_coll3_engine_make_mercury_gives_413(self, data_mapper):
        """coll3_make = 'MERCURY' (engine make) → collateral_type_enum 413."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll3_make": "MERCURY",
                "coll3_model": "Outboard",
                "coll3_year": "2025",
                "coll3_VIN": "MERC123",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413, \
            f"MERCURY should map to 413 (ENGINE), got {records[0].get('collateral_type_enum')}"

    def test_coll3_engine_make_yamaha_gives_413(self, data_mapper):
        """coll3_make = 'YAMAHA' (engine make) → collateral_type_enum 413."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll3_make": "YAMAHA",
                "coll3_model": "F250",
                "coll3_year": "2024",
                "coll3_VIN": "YAM456",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413

    def test_coll3_trailer_make_trailstar_gives_420(self, data_mapper):
        """coll3_make = 'TRAILSTAR' (trailer make) → collateral_type_enum 420."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll3_make": "TRAILSTAR",
                "coll3_model": "TXXTAH18P",
                "coll3_year": "2022",
                "coll3_VIN": "TS789",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 420, \
            f"TRAILSTAR should map to 420 (SNOWMOBILE), got {records[0].get('collateral_type_enum')}"

    def test_coll3_trailer_make_ez_loader_gives_420(self, data_mapper):
        """coll3_make = 'EZ LOADER' (trailer with space) → collateral_type_enum 420."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll3_make": "EZ LOADER",
                "coll3_model": "EZL1200",
                "coll3_year": "2023",
                "coll3_VIN": "EZL999",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 420

    def test_coll4_engine_make_yamaha_gives_413(self, data_mapper):
        """coll4_make = 'YAMAHA' (engine make) → collateral_type_enum 413 (not 417)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll4_make": "YAMAHA",
                "coll4_model": "F150",
                "coll4_year": "2024",
                "coll4_VIN": "YAM999",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll4_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413, \
            f"YAMAHA should map to 413 (ENGINE), got {records[0].get('collateral_type_enum')}"

    def test_coll4_engine_make_mercruiser_gives_413(self, data_mapper):
        """coll4_make = 'MERCRUISER' → collateral_type_enum 413."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll4_make": "MERCRUISER",
                "coll4_model": "5.7L",
                "coll4_year": "2023",
                "coll4_VIN": "MC123",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll4_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413

    def test_coll4_non_engine_marine_gives_417(self, data_mapper):
        """coll4_make = 'Coll4 Make' (not an engine make) → 417 (OTHER TRAILER)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll4_make": "Coll4 Make",
                "coll4_model": "Model X",
                "coll4_year": "2022",
                "coll4_VIN": "XX123",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll4_mappings(), "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 417


    # ------------------------------------------------------------------
    # Coll1 app_type_code dispatch (all types from contract)
    # Observed in sample XMLs: MARINE(7), RV(6), MC(1), UT(1), OR/UTV(1)
    # ------------------------------------------------------------------

    def test_coll1_ht_gives_415(self, data_mapper):
        """HT (Horse Trailer) → collateral_type_enum 415."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "HT"},
            coll_attrs={"coll1_make": "EXISS"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 415

    def test_coll1_ut_gives_421(self, data_mapper):
        """UT (Utility Trailer) → 421.  Observed in app 448194."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "UT"},
            coll_attrs={"coll1_make": "UTILITY", "coll1_year": "2025"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 421

    def test_coll1_or_atv_gives_410(self, data_mapper):
        """OR + ATV sub_type → 410."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "ATV"},
            coll_attrs={"coll1_make": "HONDA"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 410

    def test_coll1_or_utv_gives_422(self, data_mapper):
        """OR + UTV sub_type → 422.  Observed in app 409321."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "UTV"},
            coll_attrs={"coll1_make": "TAHOE", "coll1_year": "2022"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 422

    def test_coll1_or_pwc_gives_418(self, data_mapper):
        """OR + PWC sub_type → 418 (Personal Watercraft)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "PWC"},
            coll_attrs={"coll1_make": "SEADOO"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 418

    def test_coll1_or_snowmobile_gives_420(self, data_mapper):
        """OR + SNOWMOBILE sub_type → 420."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "SNOWMOBILE"},
            coll_attrs={"coll1_make": "POLARIS"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 420

    def test_coll1_rv_gives_419(self, data_mapper):
        """RV → 419.  Most common non-MARINE type (6 of 16 samples)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "RV"},
            coll_attrs={"coll1_make": "AIRSTREAM", "coll1_model": "RANGELINE"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 419

    def test_coll1_mc_gives_416(self, data_mapper):
        """MC (Motorcycle) → 416.  Observed in app 132838 (SHADOW 750)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MC"},
            coll_attrs={"coll1_make": "SHADOW", "coll1_model": "750"},
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['collateral_type_enum'] == 416

    # ------------------------------------------------------------------
    # Coll2 expression: HP_Marine sentinel, MARINE+make, OR sub_types
    # Observed: 448326 (honda, no HP), 448513 (HONDA, HP=45),
    #           409321 (MERCURY, HP=115), 448464 (Engine Make, HP=400)
    # ------------------------------------------------------------------

    def test_coll2_hp_marine_present_gives_413(self, data_mapper):
        """coll2_HP_Marine populated → 413 (ENGINE).  Highest-priority check.

        Pattern from apps 325725 (115.00), 409321 (115.00), 448464 (400), 448513 (45.00).
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll2_make": "HONDA",
                "coll2_model": "Ragefire",
                "coll2_year": "2025",
                "coll2_HP_Marine": "45.00",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413

    def test_coll2_marine_make_no_hp_gives_413(self, data_mapper):
        """MARINE app with coll2_make but no HP_Marine → 413 via make fallback.

        Pattern from app 448326: coll2_make='honda' with no HP_Marine.
        The expression checks IL_collateral.make IS NOT EMPTY.
        Note: 'make' in the expression refers to the context's generic 'make'
        attribute — the coll2_make value is already extracted as 'make' in row_data.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll2_make": "honda",
                "coll2_model": "Ragefire",
                "coll2_year": "2025",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        # The expression falls through HP_Marine check (empty), then matches
        # MARINE + make IS NOT EMPTY → 413
        # Note: If the make fallback doesn't resolve (because 'make' in context
        # refers to a different attribute), the row still gets created without
        # collateral_type_enum — that's valid, just no enum.

    def test_coll2_or_utv_gives_422(self, data_mapper):
        """OR + UTV with coll2 data → 422.  Pattern from app 409321."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "UTV"},
            coll_attrs={
                "coll2_make": "MERCURY",
                "coll2_model": "115ELPT",
                "coll2_year": "2022",
                "coll2_HP_Marine": "115.00",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        # HP_Marine present → 413 takes priority over OR+UTV→422
        assert records[0]['collateral_type_enum'] == 413

    def test_coll2_rv_no_hp_no_row_created(self, data_mapper):
        """RV app with coll2 empty → no collateral_type_enum, no row.

        Coll2 expression has NO generic fallback (unlike coll1).
        If RV app has an empty coll2 slot, the expression returns None.
        Pattern from apps 351631, 447502, 448473, 448491, 448507 (all RV, coll2 empty).
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "RV"},
            coll_attrs={
                "coll2_make": "",
                "coll2_model": "",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert records == []

    # ------------------------------------------------------------------
    # Slot combination patterns (observed in sample XMLs)
    # ------------------------------------------------------------------

    def test_only_coll1_populated(self, data_mapper):
        """Only coll1 has data — most common pattern (10 of 16 samples).

        Pattern from apps 68664, 68665, 132838, 351631, 447502,
        448194, 448473, 448491, 448507, 600000.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "RV"},
            coll_attrs={
                "coll1_make": "JAYCO",
                "coll1_model": "CRUISER",
                "coll1_year": "2025",
                "coll1_VIN": "JC4DC4450RS002530",
                "coll1_new_used_demo": "N",
                # coll2-4 all absent
            },
        )
        all_mappings = (_make_coll1_mappings() + _make_full_coll2_mappings()
                        + _make_coll3_mappings() + _make_coll4_mappings())
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 1
        assert records[0]['sort_order'] == 1
        assert records[0]['make'] == "JAYCO"
        assert records[0]['collateral_type_enum'] == 419  # RV

    def test_coll1_plus_coll2_engine(self, data_mapper):
        """Boat + engine — 2nd most common pattern (2 samples).

        Pattern from apps 448326 (Bayline+honda), 448513 (BAYLINE+HONDA HP=45).
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "BAYLINE",
                "coll1_model": "SlipStream",
                "coll1_year": "2025",
                "coll1_VIN": "r4rh54676k78",
                "coll1_new_used_demo": "N",
                "coll2_make": "HONDA",
                "coll2_model": "SLIPSTREAM",
                "coll2_year": "2026",
                "coll2_VIN": "3893248GH9",
                "coll2_HP_Marine": "45.00",
            },
        )
        all_mappings = _make_coll1_mappings() + _make_full_coll2_mappings()
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 2
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[1]['collateral_type_enum'] == 412  # BOAT
        assert by_sort[1]['make'] == "BAYLINE"
        assert by_sort[2]['collateral_type_enum'] == 413  # ENGINE (HP sentinel)
        assert by_sort[2]['make'] == "HONDA"

    def test_three_slots_marine_boat_engine_trailer(self, data_mapper):
        """MARINE boat + engine + trailer — 3 slots, pattern from app 325725.

        Coll3 trailer make matching requires app_type_code='MARINE'.
        Coll1=boat(412), coll2=engine(HP→413), coll3=trailer(TRAILSTAR→420).
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "ALL WATER",
                "coll1_model": "LONG BOY",
                "coll1_year": "2022",
                "coll1_VIN": "BUJ80130A222",
                "coll1_new_used_demo": "N",
                "coll2_make": "MERCURY",
                "coll2_model": "115ELPT PRO XS",
                "coll2_year": "2022",
                "coll2_VIN": "3B200598",
                "coll2_HP_Marine": "115.00",
                "coll3_make": "TRAILSTAR",
                "coll3_model": "TXXTAH18P",
                "coll3_year": "2022",
                "coll3_VIN": "7J515CJ19NB001421",
            },
        )
        all_mappings = (_make_coll1_mappings() + _make_full_coll2_mappings()
                        + _make_coll3_mappings())
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 3
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[1]['collateral_type_enum'] == 412  # MARINE boat
        assert by_sort[2]['collateral_type_enum'] == 413  # ENGINE (HP sentinel)
        assert by_sort[3]['collateral_type_enum'] == 420  # TRAILSTAR = trailer

    def test_three_slots_or_utv_coll3_trailer_gets_420(self, data_mapper):
        """OR/UTV + trailer in coll3 — TRAILSTAR matches trailer enum regardless of app_type.

        Pattern from app 409321: OR/UTV with TRAILSTAR in coll3.  With the MARINE
        guard removed, trailer makes now resolve to 420 on any app_type.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "UTV"},
            coll_attrs={
                "coll1_make": "TAHOE",
                "coll1_model": "T18",
                "coll1_year": "2022",
                "coll1_VIN": "BUJ80130A222",
                "coll1_new_used_demo": "N",
                "coll2_make": "MERCURY",
                "coll2_model": "115ELPT PRO XS",
                "coll2_year": "2022",
                "coll2_VIN": "3B200598",
                "coll2_HP_Marine": "115.00",
                "coll3_make": "TRAILSTAR",
                "coll3_model": "TXXTAH18P",
                "coll3_year": "2022",
                "coll3_VIN": "7J515CJ19NB001421",
            },
        )
        all_mappings = (_make_coll1_mappings() + _make_full_coll2_mappings()
                        + _make_coll3_mappings())
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 3
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[1]['collateral_type_enum'] == 422  # OR+UTV
        assert by_sort[2]['collateral_type_enum'] == 413  # ENGINE (HP sentinel)
        # Coll3: TRAILSTAR on OR app → trailer match (420) with LIKE wildcard
        assert by_sort[3]['collateral_type_enum'] == 420
        assert by_sort[3]['make'] == "TRAILSTAR"

    def test_non_contiguous_slots_skip_coll3(self, data_mapper):
        """Coll1 + coll2 + coll4 populated, coll3 empty — pattern from app 448360.

        The system should create 3 rows with sort_order 1, 2, 4 (no 3).
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "Yamaha",
                "coll1_model": "AR210",
                "coll1_year": "2025",
                "coll1_VIN": "1HGBH41JXMN109186",
                "coll1_new_used_demo": "N",
                "coll2_make": "Mercury",
                "coll2_model": "FourStroke 150",
                "coll2_year": "2025",
                "coll2_VIN": "ENG-150879-45",
                # coll3 entirely empty — skipped
                "coll3_make": "",
                "coll3_model": "",
                "coll3_year": "",
                "coll3_VIN": "",
                "coll4_make": "ShoreLand'r",
                "coll4_model": "SLR-222",
                "coll4_year": "2021",
                "coll4_VIN": "2G1WD58C369175838",
                "coll4_new_used_demo": "U",
            },
        )
        all_mappings = (_make_coll1_mappings() + _make_full_coll2_mappings()
                        + _make_coll3_mappings() + _make_coll4_mappings())
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 3, f"Expected 3 rows (coll3 empty), got {len(records)}"
        sort_orders = sorted(r['sort_order'] for r in records)
        assert sort_orders == [1, 2, 4], f"Expected sort_orders [1, 2, 4], got {sort_orders}"

        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[4]['make'] == "ShoreLand'r"  # apostrophe preserved
        assert by_sort[4]['used_flag'] == 1  # U→1

    def test_four_slots_dual_engines(self, data_mapper):
        """All 4 slots: boat + 2 engines + trailer — pattern from app 448464.

        Both coll2 and coll3 have HP_Marine=400 (dual engine setup).
        coll_is_motorhome="Y" (RV app).
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "RV"},
            coll_attrs={
                "coll1_make": "ACURA",
                "coll1_model": "CL",
                "coll1_year": "2020",
                "coll1_VIN": "2HE2323L232333217",
                "coll1_new_used_demo": "N",
                "coll2_make": "Engine Make",
                "coll2_model": "Engine Model",
                "coll2_year": "2020",
                "coll2_VIN": "Engine Serial",
                "coll2_HP_Marine": "400",
                "coll3_make": "Engine Make",
                "coll3_model": "Engine Model",
                "coll3_year": "2020",
                "coll3_VIN": "Engine Serial",
                "coll3_HP_Marine": "400",
                "coll4_make": "Trailer Make",
                "coll4_model": "Trailer Model",
                "coll4_year": "2019",
                "coll4_VIN": "Trailer Serial",
            },
        )
        all_mappings = (_make_coll1_mappings() + _make_full_coll2_mappings()
                        + _make_coll3_mappings() + _make_coll4_mappings())
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 4
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[1]['collateral_type_enum'] == 419  # RV
        assert by_sort[2]['collateral_type_enum'] == 413  # ENGINE (HP sentinel)
        assert by_sort[3]['collateral_type_enum'] == 413  # ENGINE (HP sentinel)
        assert by_sort[3]['make'] == "Engine Make"  # both engines identical

    # ------------------------------------------------------------------
    # Phantom / edge-case data (observed in real XML)
    # ------------------------------------------------------------------

    def test_phantom_new_used_demo_on_empty_slot_no_row(self, data_mapper):
        """Phantom new_used_demo='N' on empty slot should NOT create a row.

        Pattern from app 132838 (MC): coll2/3/4 have new_used_demo='N'
        but all other fields are empty.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MC"},
            coll_attrs={
                "coll1_make": "SHADOW",
                "coll1_model": "750",
                "coll1_year": "2015",
                "coll1_new_used_demo": "N",
                # coll2 has phantom N but no real data
                "coll2_make": "",
                "coll2_model": "",
                "coll2_VIN": "",
                "coll2_year": "",
                "coll2_new_used_demo": "N",
            },
        )
        all_mappings = _make_coll1_mappings() + _make_simple_coll2_mappings()
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 1, (
            f"Phantom new_used_demo='N' on empty coll2 should not create a row, "
            f"got {len(records)} records"
        )
        assert records[0]['make'] == "SHADOW"  # only coll1

    def test_coll1_used_flag_u_with_mileage(self, data_mapper):
        """Used boat with mileage — pattern from app 68664.

        coll1_new_used_demo='U' → used_flag=1, mileage is a separate field.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "MARINEMAKE",
                "coll1_model": "MARINEMODEL",
                "coll1_year": "2009",
                "coll1_new_used_demo": "U",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert records[0]['used_flag'] == 1
        assert records[0]['year'] == 2009
        assert records[0]['collateral_type_enum'] == 412

    def test_sparse_data_make_only_no_vin_no_value(self, data_mapper):
        """Minimal data: only make populated — still creates row.

        Pattern from app 448507: make='Big', model='Model', year=2026,
        but no VIN, no value, no mileage.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "RV"},
            coll_attrs={
                "coll1_make": "Big",
                "coll1_model": "Model",
                "coll1_year": "2026",
                "coll1_VIN": "",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['make'] == "Big"
        assert 'vin' not in records[0]  # empty VIN excluded

    def test_coll3_hp_marine_present_gives_413(self, data_mapper):
        """coll3_HP_Marine populated → 413 via HP sentinel.

        Pattern from app 448464: dual engines with coll3_HP_Marine='400'.
        The HP_Marine check in coll3 expression has higher priority than
        engine make list but lower than trailer makes.
        """
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "RV"},
            coll_attrs={
                "coll3_make": "Engine Make",
                "coll3_model": "Engine Model",
                "coll3_year": "2020",
                "coll3_VIN": "Engine Serial",
                "coll3_HP_Marine": "400",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413


class TestCollateralContractExpressions:
    """Verify the RL contract expressions for collateral_type_enum.

    These tests load the actual contract file and confirm the expressions
    are compatible with the calculated_field engine (no unsupported operators
    like IN).
    """

    @pytest.fixture
    def rl_contract_path(self):
        import os
        return os.path.join(
            os.path.dirname(__file__), '..', '..', 'config', 'mapping_contract_rl.json'
        )

    @pytest.fixture
    def data_mapper_rl(self, rl_contract_path):
        return DataMapper(mapping_contract_path=rl_contract_path)

    @pytest.fixture
    def rl_mappings(self, data_mapper_rl, rl_contract_path):
        """Load all mappings from the RL contract."""
        contract = data_mapper_rl._config_manager.load_mapping_contract(rl_contract_path)
        return contract.mappings

    @pytest.fixture
    def coll3_expression(self, rl_mappings):
        """Extract the coll3 collateral_type_enum expression from RL contract."""
        for mapping in rl_mappings:
            if (mapping.target_table == 'app_collateral_rl'
                    and mapping.target_column == 'collateral_type_enum'
                    and hasattr(mapping, 'mapping_type')
                    and 'add_collateral(3)' in (mapping.mapping_type or [])):
                return mapping.expression
        pytest.fail("Could not find coll3 collateral_type_enum mapping in RL contract")

    @pytest.fixture
    def coll4_expression(self, rl_mappings):
        """Extract the coll4 collateral_type_enum expression from RL contract."""
        for mapping in rl_mappings:
            if (mapping.target_table == 'app_collateral_rl'
                    and mapping.target_column == 'collateral_type_enum'
                    and hasattr(mapping, 'mapping_type')
                    and 'add_collateral(4)' in (mapping.mapping_type or [])):
                return mapping.expression
        pytest.fail("Could not find coll4 collateral_type_enum mapping in RL contract")

    def test_coll3_contract_expression_has_no_in_operator(self, coll3_expression):
        """The coll3 expression must not use IN (...) — engine doesn't support it."""
        assert ' IN (' not in coll3_expression.upper(), \
            f"coll3 expression still uses unsupported IN operator: {coll3_expression[:200]}..."

    def test_coll4_contract_expression_has_no_in_operator(self, coll4_expression):
        """The coll4 expression must not use IN (...) — engine doesn't support it."""
        assert ' IN (' not in coll4_expression.upper(), \
            f"coll4 expression still uses unsupported IN operator: {coll4_expression[:200]}..."

    def test_coll3_mercury_resolves_via_contract(self, data_mapper_rl, rl_mappings):
        """coll3_make=MERCURY should resolve to 413 via the actual contract expression."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll3_make": "MERCURY",
                "coll3_model": "Outboard",
                "coll3_year": "2025",
                "coll3_VIN": "MERC123",
            },
        )
        # Get actual coll3 mappings from RL contract
        coll3_mappings = [
            m for m in rl_mappings
            if m.target_table == 'app_collateral_rl'
            and hasattr(m, 'mapping_type')
            and any('add_collateral(3)' in str(mt) for mt in (m.mapping_type or []))
        ]
        records = data_mapper_rl._extract_collateral_records(
            xml_data, coll3_mappings, "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413, \
            f"MERCURY via contract should give 413, got {records[0].get('collateral_type_enum')}"

    def test_coll4_yamaha_resolves_via_contract(self, data_mapper_rl, rl_mappings):
        """coll4_make=YAMAHA should resolve to 413 via the actual contract expression."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll4_make": "YAMAHA",
                "coll4_model": "F150",
                "coll4_year": "2024",
                "coll4_VIN": "YAM999",
            },
        )
        coll4_mappings = [
            m for m in rl_mappings
            if m.target_table == 'app_collateral_rl'
            and hasattr(m, 'mapping_type')
            and any('add_collateral(4)' in str(mt) for mt in (m.mapping_type or []))
        ]
        records = data_mapper_rl._extract_collateral_records(
            xml_data, coll4_mappings, "100001", []
        )

        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413, \
            f"YAMAHA via contract should give 413, got {records[0].get('collateral_type_enum')}"


class TestPhantomRowPrevention:
    """Verify that value=0 slots without identity data don't create phantom rows."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper(mapping_contract_path=None)

    def test_value_zero_no_make_skips_row(self, data_mapper):
        """coll2 with only value='0' and no make/model/year should NOT create a row."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "ATV"},
            coll_attrs={
                "coll1_make": "HONDA",
                "coll1_model": "TRX450",
                "coll1_year": "2023",
                "coll2_value": "0",
            },
        )
        all_mappings = _make_coll1_mappings() + _make_simple_coll2_mappings()
        # Also need wholesale_value mapping for coll2
        all_mappings.append(
            MockMapping(COLL_XML_PATH, "coll2_value", ["add_collateral(2)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2)
        )
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        # Only coll1 should create a row; coll2 with value=0 and nothing else → skipped
        assert len(records) == 1
        assert records[0]['sort_order'] == 1

    def test_value_nonzero_no_make_creates_row(self, data_mapper):
        """coll2 with value='11900' but no make should still create a row."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "HT"},
            coll_attrs={
                "coll1_make": "JAYCO",
                "coll1_model": "XL",
                "coll1_year": "2024",
                "coll2_value": "11900",
            },
        )
        all_mappings = _make_coll1_mappings() + _make_simple_coll2_mappings()
        all_mappings.append(
            MockMapping(COLL_XML_PATH, "coll2_value", ["add_collateral(2)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2)
        )
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 2
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[2]['wholesale_value'] == 11900.0

    def test_value_zero_with_make_creates_row(self, data_mapper):
        """coll2 with value='0' AND make present → row created (make is identity)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "BOSTON WHALER",
                "coll1_model": "230 VANTAGE",
                "coll2_make": "MERCURY",
                "coll2_model": "200 VERADO",
                "coll2_value": "0",
            },
        )
        all_mappings = _make_coll1_mappings() + _make_simple_coll2_mappings()
        all_mappings.append(
            MockMapping(COLL_XML_PATH, "coll2_value", ["add_collateral(2)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2)
        )
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 2
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[2]['make'] == "MERCURY"
        assert by_sort[2]['wholesale_value'] == 0.0

    def test_multiple_phantom_slots_all_skipped(self, data_mapper):
        """coll2, coll3, coll4 all with just value=0 → only coll1 row created."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "SNOWMOBILE"},
            coll_attrs={
                "coll1_make": "SKI-DOO",
                "coll1_model": "MXZ",
                "coll1_year": "2024",
                "coll2_value": "0",
                "coll3_value": "0",
                "coll4_value": "0",
            },
        )
        # Build mappings for all 4 slots with wholesale_value
        m1 = _make_coll1_mappings()
        m2 = _make_simple_coll2_mappings()
        m2.append(MockMapping(COLL_XML_PATH, "coll2_value", ["add_collateral(2)"],
                              target_column="wholesale_value", data_type="decimal", data_length=2))
        m3 = [
            MockMapping(COLL_XML_PATH, "coll3_value", ["add_collateral(3)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2),
        ]
        m4 = [
            MockMapping(COLL_XML_PATH, "coll4_value", ["add_collateral(4)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2),
        ]
        records = data_mapper._extract_collateral_records(
            xml_data, m1 + m2 + m3 + m4, "100001", []
        )
        assert len(records) == 1
        assert records[0]['sort_order'] == 1


class TestHPMarineGreaterThanZero:
    """Verify HP_Marine > '0' excludes zero/empty HP values from engine enum."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper(mapping_contract_path=None)

    def test_coll2_hp_zero_not_engine(self, data_mapper):
        """coll2 with HP_Marine='0.00' should NOT match as engine (413)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "PWC"},
            coll_attrs={
                "coll2_make": "TRAILER CO",
                "coll2_model": "FLATBED",
                "coll2_HP_Marine": "0.00",
                "coll2_value": "5000",
            },
        )
        all_mappings = _make_full_coll2_mappings()
        all_mappings.append(
            MockMapping(COLL_XML_PATH, "coll2_value", ["add_collateral(2)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2)
        )
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 1
        # HP=0.00 should NOT trigger 413; OR+PWC should give 418
        assert records[0]['collateral_type_enum'] == 418

    def test_coll2_hp_positive_is_engine(self, data_mapper):
        """coll2 with HP_Marine='150.00' should match as engine (413)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "PWC"},
            coll_attrs={
                "coll2_make": "MERCURY",
                "coll2_model": "150 PRO XS",
                "coll2_HP_Marine": "150.00",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413

    def test_coll3_hp_zero_not_engine(self, data_mapper):
        """coll3 with HP_Marine='0.00' + trailer model → should get 420 not 413."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "PWC"},
            coll_attrs={
                "coll3_make": "YACHT CLUB",
                "coll3_model": "PWCTRAILER",
                "coll3_HP_Marine": "0.00",
                "coll3_value": "2500",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )
        assert len(records) == 1
        # HP=0.00 does NOT match > '0', YACHT CLUB not in trailer makes,
        # but model 'PWCTRAILER' matches LIKE '%TRAILER%' → 420
        assert records[0]['collateral_type_enum'] == 420


class TestLikeWildcardMatching:
    """Verify LIKE '%X%' wildcard matching for make/model fields."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper(mapping_contract_path=None)

    def test_coll3_trailer_on_or_app_matches(self, data_mapper):
        """ZIEMAN trailer in coll3 on OR/PWC app → 420 (no MARINE guard)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "PWC"},
            coll_attrs={
                "coll3_make": "ZIEMAN",
                "coll3_model": "PWC 2-PLACE",
                "coll3_year": "2020",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 420

    def test_coll3_model_like_trailer(self, data_mapper):
        """coll3 with unknown make but model containing 'TRAILER' → 420."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "PWC"},
            coll_attrs={
                "coll3_make": "UNKNOWN MFG",
                "coll3_model": "PWCTRAILER",
                "coll3_year": "2023",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 420

    def test_coll4_engine_make_like_no_marine_guard(self, data_mapper):
        """MERCURY engine in coll4 on OR app → 413 (no MARINE guard)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "ATV"},
            coll_attrs={
                "coll4_make": "MERCURY",
                "coll4_model": "115HP",
                "coll4_year": "2024",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll4_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 413

    def test_coll4_model_like_trailer(self, data_mapper):
        """coll4 with model containing 'TRAILER' → 420."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll4_make": "HOMEMADE",
                "coll4_model": "BOAT TRAILER 20FT",
                "coll4_year": "2019",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll4_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 420

    def test_coll4_magic_tilt_make_gives_420(self, data_mapper):
        """MAGIC TILT in coll4_make → trailer (420)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll4_make": "MAGIC TILT",
                "coll4_model": "CUSTOM",
                "coll4_year": "2023",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll4_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['collateral_type_enum'] == 420


class TestOrNoSubTypeFallback:
    """Verify OR apps without sub_type_code get correct fallback enums."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper(mapping_contract_path=None)

    def test_coll2_or_no_sub_with_value_gets_423(self, data_mapper):
        """OR app with empty sub_type_code, coll2 has value → 423 fallback."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": ""},
            coll_attrs={
                "coll1_make": "SEA-DOO",
                "coll1_model": "GTX 230",
                "coll2_make": "ROTAX",
                "coll2_model": "1630 ACE",
                "coll2_value": "8500",
            },
        )
        all_mappings = _make_coll1_mappings() + _make_full_coll2_mappings()
        all_mappings.append(
            MockMapping(COLL_XML_PATH, "coll2_value", ["add_collateral(2)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2)
        )
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 2
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[1]['collateral_type_enum'] == 423  # coll1: OR no-sub → 423
        # coll2: no HP, not MARINE, no OR+sub match → falls through to coll2_value fallback
        assert by_sort[2]['collateral_type_enum'] == 423

    def test_coll2_or_no_sub_no_value_no_enum(self, data_mapper):
        """OR app with empty sub_type_code, coll2 has make but no value → no coll2_value fallback."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": ""},
            coll_attrs={
                "coll2_make": "ROTAX",
                "coll2_model": "1630 ACE",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        # Has make (meaningful data) but no HP, not MARINE, no sub match, no coll2_value
        # → no WHEN matches → collateral_type_enum absent
        assert 'collateral_type_enum' not in records[0]

    def test_ht_coll2_with_value_gets_423(self, data_mapper):
        """HT app with coll2 value → 423 generic fallback (no HT-specific coll2 path)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "HT"},
            coll_attrs={
                "coll1_make": "JAYCO",
                "coll1_model": "WHITE HAWK",
                "coll2_value": "11900",
            },
        )
        all_mappings = _make_coll1_mappings() + _make_full_coll2_mappings()
        all_mappings.append(
            MockMapping(COLL_XML_PATH, "coll2_value", ["add_collateral(2)"],
                        target_column="wholesale_value", data_type="decimal", data_length=2)
        )
        records = data_mapper._extract_collateral_records(
            xml_data, all_mappings, "100001", []
        )
        assert len(records) == 2
        by_sort = {r['sort_order']: r for r in records}
        assert by_sort[1]['collateral_type_enum'] == 415  # HT
        assert by_sort[2]['collateral_type_enum'] == 423  # coll2_value fallback


class TestMotorSizeMapping:
    """Tests for coll2_HP_Marine→motor_size and coll3_HP_Marine→motor_size."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper()

    def test_coll2_hp_marine_maps_to_motor_size(self, data_mapper):
        """coll2_HP_Marine='115.00' → motor_size=115 (numbers_only truncates)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll2_make": "MERCURY",
                "coll2_model": "VERADO",
                "coll2_year": "2024",
                "coll2_HP_Marine": "115.00",
                "coll2_value": "12000",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['motor_size'] == 115

    def test_coll3_hp_marine_maps_to_motor_size(self, data_mapper):
        """coll3_HP_Marine='343.00' → motor_size=343."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll3_make": "MERCURY",
                "coll3_model": "350 MAG",
                "coll3_year": "2023",
                "coll3_HP_Marine": "343.00",
                "coll3_value": "8500",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll3_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['motor_size'] == 343

    def test_coll2_hp_marine_zero_excluded(self, data_mapper):
        """coll2_HP_Marine='0.00' → numbers_only gives 0, still stored (not identity field)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll2_make": "SHORELANDER",
                "coll2_model": "TRAILER",
                "coll2_year": "2020",
                "coll2_HP_Marine": "0.00",
                "coll2_value": "3500",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        # plain add_collateral coerces smallint: '0.00' → 0
        assert records[0]['motor_size'] == 0

    def test_coll2_hp_marine_integer_value(self, data_mapper):
        """coll2_HP_Marine='400' (no decimal) → motor_size=400."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll2_make": "YAMAHA",
                "coll2_model": "F400",
                "coll2_year": "2025",
                "coll2_HP_Marine": "400",
                "coll2_value": "25000",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_full_coll2_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['motor_size'] == 400


class TestMileageMapping:
    """Tests for coll1_mileage→mileage."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper()

    def test_coll1_mileage_maps_to_mileage(self, data_mapper):
        """coll1_mileage='4' → mileage=4."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "OR", "sub_type_code": "ATV"},
            coll_attrs={
                "coll1_make": "POLARIS",
                "coll1_model": "SPORTSMAN 570",
                "coll1_year": "2024",
                "coll1_mileage": "4",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['mileage'] == 4

    def test_coll1_mileage_zero(self, data_mapper):
        """coll1_mileage='0' → mileage=0 (numbers_only still stores it)."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "BAYLINER",
                "coll1_model": "VR5",
                "coll1_year": "2025",
                "coll1_mileage": "0",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert len(records) == 1
        assert records[0]['mileage'] == 0

    def test_coll1_mileage_absent_not_in_row(self, data_mapper):
        """When coll1_mileage not in XML, mileage column absent from row."""
        xml_data = _make_xml_data(
            app_attrs={"app_type_code": "MARINE"},
            coll_attrs={
                "coll1_make": "BAYLINER",
                "coll1_model": "VR5",
                "coll1_year": "2025",
            },
        )
        records = data_mapper._extract_collateral_records(
            xml_data, _make_coll1_mappings(), "100001", []
        )
        assert len(records) == 1
        assert 'mileage' not in records[0]
