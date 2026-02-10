"""
Test collateral default value application for NOT NULL columns.

This test verifies that when a collateral record is created with meaningful data
(e.g., make, model, year), but some NOT NULL columns are missing (e.g., collateral_type_enum
returns None from calculated field), the default values are correctly applied.
"""
import pytest
from xml_extractor.mapping.data_mapper import DataMapper


class MockMapping:
    """Minimal mock for FieldMapping used by collateral default tests."""
    def __init__(self, xml_path, xml_attribute, mapping_type, target_table="app_collateral_rl",
                 target_column="", data_type="string", data_length=None, nullable=True, required=False,
                 default_value=None, exclude_default_when_record_empty=False, expression=None):
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
        self.exclude_default_when_record_empty = exclude_default_when_record_empty
        self.expression = expression


COLL_XML_PATH = "/Provenir/Request/CustData/IL_application/IL_collateral"
APP_XML_PATH = "/Provenir/Request/CustData/IL_application"


class TestCollateralDefaultValues:
    """Test that collateral extraction applies default values correctly."""

    @pytest.fixture
    def data_mapper(self):
        return DataMapper()

    def test_collateral_type_enum_default_applied_when_calculated_field_returns_none(self, data_mapper):
        """
        Test that when calculated_field returns None for collateral_type_enum,
        the default value 423 is applied.
        """
        # Create mappings for a minimal collateral record
        mappings = [
            # Collateral type - calculated field that might return None
            MockMapping(
                COLL_XML_PATH, "coll1_type", ["calculated_field", "add_collateral(1)"],
                target_column="collateral_type_enum",
                data_type="smallint",
                expression="CASE WHEN IL_application.app_type_code = 'MARINE' THEN 412 ELSE 423 END",
                nullable=False,
                required=False,
                default_value="423",
                exclude_default_when_record_empty=True
            ),
            # Make - has data, triggers meaningful_data=True
            MockMapping(
                COLL_XML_PATH, "coll1_make", ["add_collateral(1)"],
                target_column="make",
                data_type="string",
                data_length=50,
                nullable=False,
                required=False,
                default_value="MISSING",
                exclude_default_when_record_empty=True
            ),
            # Year - missing from XML, should get default
            MockMapping(
                COLL_XML_PATH, "coll1_year", ["numbers_only", "add_collateral(1)"],
                target_column="year",
                data_type="smallint",
                nullable=False,
                required=False,
                default_value="9999",
                exclude_default_when_record_empty=True
            ),
            # Used flag - char to bit, always produces value
            MockMapping(
                COLL_XML_PATH, "coll1_new_used_demo", ["char_to_bit", "add_collateral(1)"],
                target_column="used_flag",
                data_type="bit",
                nullable=False,
                required=False,
                default_value="0",
                exclude_default_when_record_empty=True
            ),
        ]

        # Create XML data - has make but missing year
        # app_type_code is present, so calculated field SHOULD return 423 (ELSE clause)
        xml_data = {
            APP_XML_PATH: {
                "attributes": {
                    "app_type_code": "UNKNOWN_TYPE"  # Not MARINE, will trigger ELSE
                }
            },
            COLL_XML_PATH: {
                "attributes": {
                    "coll1_make": "YAMAHA",
                    "coll1_new_used_demo": "U"
                    # coll1_year is MISSING - should get default 9999
                }
            }
        }

        # Extract collateral records
        records = data_mapper._extract_collateral_records(xml_data, mappings, "12345", [])

        # Verify results
        assert len(records) == 1, "Should create 1 collateral record"
        
        record = records[0]
        
        # Verify default values were applied
        assert "collateral_type_enum" in record, "collateral_type_enum should be in record"
        assert record["collateral_type_enum"] == 423, \
            "collateral_type_enum should have value 423 from ELSE clause"
        
        assert "make" in record, "make should be in record"
        assert record["make"] == "YAMAHA", "make should have XML value"
        
        assert "year" in record, "year should be in record"
        assert record["year"] == 9999, \
            "year should have default value 9999 when missing from XML"
        
        assert "used_flag" in record, "used_flag should be in record"
        assert record["used_flag"] == 1, "used_flag should be 1 for 'U'"

    def test_collateral_make_default_applied_when_missing(self, data_mapper):
        """
        Test that when make is missing from XML, default value "MISSING" is applied.
        """
        mappings = [
            MockMapping(
                COLL_XML_PATH, "coll1_type", ["calculated_field", "add_collateral(1)"],
                target_column="collateral_type_enum",
                data_type="smallint",
                expression="CASE WHEN IL_application.app_type_code = 'MARINE' THEN 412 ELSE 423 END",
                nullable=False,
                required=False,
                default_value="423",
                exclude_default_when_record_empty=True
            ),
            MockMapping(
                COLL_XML_PATH, "coll1_make", ["add_collateral(1)"],
                target_column="make",
                data_type="string",
                data_length=50,
                nullable=False,
                required=False,
                default_value="MISSING",
                exclude_default_when_record_empty=True
            ),
            MockMapping(
                COLL_XML_PATH, "coll1_year", ["numbers_only", "add_collateral(1)"],
                target_column="year",
                data_type="smallint",
                nullable=False,
                required=False,
                default_value="9999",
                exclude_default_when_record_empty=True
            ),
        ]

        # XML data with year but no make - year triggers meaningful_data=True
        xml_data = {
            APP_XML_PATH: {
                "attributes": {
                    "app_type_code": "MARINE"
                }
            },
            COLL_XML_PATH: {
                "attributes": {
                    "coll1_year": "2015"
                    # coll1_make is MISSING - should get default "MISSING"
                }
            }
        }

        records = data_mapper._extract_collateral_records(xml_data, mappings, "12345", [])

        assert len(records) == 1
        record = records[0]
        
        # Verify defaults applied
        assert record["collateral_type_enum"] == 412, "Should evaluate to 412 for MARINE"
        assert record["make"] == "MISSING", \
            "make should have default value 'MISSING' when absent"
        assert record["year"] == 2015, "year should have XML value 2015"

    def test_no_record_created_when_no_meaningful_data(self, data_mapper):
        """
        Test that when a collateral slot has no meaningful data,
        no record is created (and thus defaults are not applied).
        
        This verifies exclude_default_when_record_empty logic:
        If there's no meaningful data, no row should be created at all.
        """
        mappings = [
            MockMapping(
                COLL_XML_PATH, "coll1_make", ["add_collateral(1)"],
                target_column="make",
                data_type="string",
                data_length=50,
                nullable=False,
                required=False,
                default_value="MISSING",
                exclude_default_when_record_empty=True
            ),
        ]

        # Empty XML - no collateral data
        xml_data = {}

        records = data_mapper._extract_collateral_records(xml_data, mappings, "12345", [])

        assert len(records) == 0, \
            "Should not create record when no meaningful data exists (exclude_default_when_record_empty=True)"
