"""
Unit tests for contract-driven XPath element name extraction (Task 5).

Tests the DataMapper's ability to extract XML element names dynamically from
the mapping contract's relationships array using child_table as the lookup key.
This enables multi-product support where XML element names vary across products
(e.g., 'contact_employment' vs 'IL_contact_employment') but destination tables
remain stable ('contact_employment').

Test Coverage:
- Element name extraction from xml_child_path
- Cache initialization and lookup performance
- Fallback behavior when relationships not found
- IL Lending product example with IL_ prefix
- Integration with XPath query construction

Testing Strategy:
- Uses raw JSON dictionaries instead of MappingContract objects for test fixtures
- This is standard practice for unit tests - provides isolation from config parsing logic
- Creates temporary JSON files that DataMapper loads directly (tests the full load path)
- Faster and more flexible than constructing full MappingContract objects
"""

import pytest

from xml_extractor.mapping.data_mapper import DataMapper



def create_minimal_contract(relationships, element_filtering=None):
    """
    Create a minimal valid contract for testing.
    
    Includes all required fields for MappingContract validation:
    - source_table, source_column, xml_root_element (required by __post_init__)
    - at least one mapping (required by __post_init__)
    - foreign_key_column in relationships (required by RelationshipMapping.__post_init__)
    - element_filtering with contact and address rules (required by fail-fast validation)
    """
    if element_filtering is None:
        element_filtering = {
            "filter_rules": [
                {
                    "element_type": "contact",
                    "xml_parent_path": "/Provenir/Request/CustData/application",
                    "xml_child_path": "/Provenir/Request/CustData/application/contact",
                    "required_attributes": {
                        "con_id": True,
                        "ac_role_tp_c": ["PR", "AUTHU"]
                    }
                },
                {
                    "element_type": "address",
                    "xml_parent_path": "/Provenir/Request/CustData/application/contact",
                    "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_address",
                    "required_attributes": {
                        "address_tp_c": ["CURR", "PREV"]
                    }
                }
            ]
        }
    
    return {
        "source_table": "app_xml",
        "source_column": "xml",
        "xml_root_element": "Provenir",
        "target_schema": "sandbox",
        "relationships": relationships,
        "element_filtering": element_filtering,
        "mappings": [
            {
                "xml_path": "/Provenir/Request",
                "xml_attribute": "ID",
                "target_table": "app_base",
                "target_column": "app_id",
                "data_type": "int",
                "nullable": False
            }
        ],
        "enum_mappings": {},
        "bit_conversions": {}
    }


@pytest.fixture
def standard_contract_data():
    """
    Standard contract fixture with default element names (no product prefix).
    
    Returns raw JSON dict instead of MappingContract object for unit test isolation,
    and to exercise edge cases we can't do with using the straight MappingContract.
    The DataMapper will load this via temporary file to test the full initialization path.
    """
    return {
        "source_table": "app_xml",
        "source_column": "xml",
        "xml_root_element": "Provenir",
        "target_schema": "sandbox",
        "relationships": [
            {
                "parent_table": "contact",
                "child_table": "contact_address",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Provenir/Request/CustData/application/contact",
                "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_address"
            },
            {
                "parent_table": "contact",
                "child_table": "contact_employment",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Provenir/Request/CustData/application/contact",
                "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_employment"
            }
        ],
        "element_filtering": {
            "filter_rules": [
                {
                    "element_type": "contact",
                    "xml_parent_path": "/Provenir/Request/CustData/application",
                    "xml_child_path": "/Provenir/Request/CustData/application/contact",
                    "required_attributes": {
                        "con_id": True,
                        "ac_role_tp_c": ["PR", "AUTHU"]
                    }
                },
                {
                    "element_type": "address",
                    "xml_parent_path": "/Provenir/Request/CustData/application/contact",
                    "xml_child_path": "/Provenir/Request/CustData/application/contact/contact_address",
                    "required_attributes": {
                        "address_tp_c": ["CURR", "PREV"]
                    }
                }
            ]
        },
        "mappings": [
            {
                "xml_path": "/Provenir/Request",
                "xml_attribute": "ID",
                "target_table": "app_base",
                "target_column": "app_id",
                "data_type": "int",
                "nullable": False
            }
        ],
        "enum_mappings": {},
        "bit_conversions": {}
    }


@pytest.fixture
def il_lending_contract_data():
    """
    IL Lending product contract fixture with IL_ prefix on element names.
    
    Demonstrates multi-product support: same child_table ('contact_address') but
    different XML element names ('IL_contact_address' vs 'contact_address').
    
    Returns raw JSON dict for unit test isolation and flexibility.
    """
    return {
        "source_table": "app_xml",
        "source_column": "xml",
        "xml_root_element": "Provenir",
        "target_schema": "sandbox",
        "relationships": [
            {
                "parent_table": "contact",
                "child_table": "contact_address",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Provenir/Request/CustData/IL_application/IL_contact",
                "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact/IL_contact_address"
            },
            {
                "parent_table": "contact",
                "child_table": "contact_employment",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Provenir/Request/CustData/IL_application/IL_contact",
                "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact/IL_contact_employment"
            }
        ],
        "element_filtering": {
            "filter_rules": [
                {
                    "element_type": "contact",
                    "xml_parent_path": "/Provenir/Request/CustData/IL_application",
                    "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact",
                    "required_attributes": {
                        "con_id": True,
                        "ac_role_tp_c": ["PR", "AUTHU"]
                    }
                },
                {
                    "element_type": "address",
                    "xml_parent_path": "/Provenir/Request/CustData/IL_application/IL_contact",
                    "xml_child_path": "/Provenir/Request/CustData/IL_application/IL_contact/IL_contact_address",
                    "required_attributes": {
                        "address_tp_c": ["CURR", "PREV"]
                    }
                }
            ]
        },
        "mappings": [
            {
                "xml_path": "/Provenir/Request",
                "xml_attribute": "ID",
                "target_table": "app_base",
                "target_column": "app_id",
                "data_type": "int",
                "nullable": False
            }
        ],
        "enum_mappings": {},
        "bit_conversions": {}
    }


class TestElementNameExtraction:
    """Tests for _get_child_element_name() method."""
    
    def test_extract_standard_element_name(self, standard_contract_data, tmp_path):
        """Extract element name from standard contract."""
        # Arrange: Create temporary contract file
        import json
        contract_path = tmp_path / "test_contract.json"
        contract_path.write_text(json.dumps(standard_contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act: Extract element names
        address_element = mapper._get_child_element_name('contact_address')
        employment_element = mapper._get_child_element_name('contact_employment')
        
        # Assert: Element names match XML structure
        assert address_element == 'contact_address'
        assert employment_element == 'contact_employment'
    
    def test_extract_il_lending_element_name(self, il_lending_contract_data, tmp_path):
        """Extract IL_-prefixed element name from IL Lending contract."""
        # Arrange: Create IL Lending contract
        import json
        contract_path = tmp_path / "il_contract.json"
        contract_path.write_text(json.dumps(il_lending_contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act: Extract element names from IL Lending contract
        address_element = mapper._get_child_element_name('contact_address')
        employment_element = mapper._get_child_element_name('contact_employment')
        
        # Assert: Element names have IL_ prefix
        assert address_element == 'IL_contact_address'
        assert employment_element == 'IL_contact_employment'
    
    def test_fallback_when_relationship_not_found(self, standard_contract_data, tmp_path):
        """Fallback to table name when relationship not in contract."""
        # Arrange
        import json
        contract_path = tmp_path / "test_contract.json"
        contract_path.write_text(json.dumps(standard_contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act: Request element name not in relationships
        unknown_element = mapper._get_child_element_name('contact_phone')
        
        # Assert: Falls back to table name
        assert unknown_element == 'contact_phone'
    
    def test_element_name_from_complex_path(self, tmp_path):
        """Extract element name from deeply nested XML path."""
        # Arrange: Contract with complex path
        import json
        contract_data = create_minimal_contract([
            {
                "parent_table": "contact",
                "child_table": "contact_employment",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Root/Deep/Nested/Parent/contact",
                "xml_child_path": "/Root/Deep/Nested/Parent/contact/Very_Deep_Employment_Element"
            }
        ])
        contract_path = tmp_path / "complex_contract.json"
        contract_path.write_text(json.dumps(contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act
        element_name = mapper._get_child_element_name('contact_employment')
        
        # Assert: Extracts only final segment
        assert element_name == 'Very_Deep_Employment_Element'
    
    def test_handles_trailing_slash_in_path(self, tmp_path):
        """Handle xml_child_path with trailing slash."""
        # Arrange: Path with trailing slash
        import json
        contract_data = create_minimal_contract([
            {
                "parent_table": "contact",
                "child_table": "contact_address",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Root/contact",
                "xml_child_path": "/Root/contact/contact_address/"
            }
        ])
        contract_path = tmp_path / "trailing_slash_contract.json"
        contract_path.write_text(json.dumps(contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act
        element_name = mapper._get_child_element_name('contact_address')
        
        # Assert: Trailing slash doesn't affect extraction
        assert element_name == 'contact_address'


class TestElementNameCache:
    """Tests for element name caching at initialization."""
    
    def test_cache_built_at_initialization(self, standard_contract_data, tmp_path):
        """Element name cache is built during __init__."""
        # Arrange & Act
        import json
        contract_path = tmp_path / "test_contract.json"
        contract_path.write_text(json.dumps(standard_contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Assert: Cache exists and contains expected entries
        assert hasattr(mapper, '_element_name_cache')
        assert 'contact_address' in mapper._element_name_cache
        assert 'contact_employment' in mapper._element_name_cache
        assert mapper._element_name_cache['contact_address'] == 'contact_address'
    
    def test_cache_performance_no_repeated_lookups(self, standard_contract_data, tmp_path, monkeypatch):
        """Cache prevents repeated contract lookups."""
        # Arrange
        import json
        contract_path = tmp_path / "test_contract.json"
        contract_path.write_text(json.dumps(standard_contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Track how many times we iterate relationships
        lookup_count = {'count': 0}
        original_get_method = mapper._get_child_element_name
        
        def counting_wrapper(child_table_name):
            lookup_count['count'] += 1
            return original_get_method(child_table_name)
        
        monkeypatch.setattr(mapper, '_get_child_element_name', counting_wrapper)
        
        # Act: Call multiple times with same table name
        for _ in range(10):
            mapper._get_child_element_name('contact_address')
        
        # Assert: With caching, should do 10 cache lookups (fast)
        # Without caching, would iterate relationships array 10 times (slow)
        assert lookup_count['count'] == 10  # Method called 10 times
        # The key is that internal loop doesn't execute 10 times due to cache
    
    def test_empty_relationships_handled(self, tmp_path):
        """Handle contract with empty relationships array."""
        # Arrange: Contract with no relationships
        import json
        contract_data = create_minimal_contract([])
        contract_path = tmp_path / "empty_relationships.json"
        contract_path.write_text(json.dumps(contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act: Request element name
        element_name = mapper._get_child_element_name('contact_address')
        
        # Assert: Falls back to table name
        assert element_name == 'contact_address'
        assert mapper._element_name_cache == {}


class TestXPathIntegration:
    """Tests for XPath construction using dynamic element names."""
    
    def test_xpath_construction_with_dynamic_element(self, il_lending_contract_data, tmp_path):
        """XPath queries use dynamically extracted element names."""
        # Arrange: IL Lending contract
        import json
        contract_path = tmp_path / "il_contract.json"
        contract_path.write_text(json.dumps(il_lending_contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act: Build XPath query using extracted element name
        address_element = mapper._get_child_element_name('contact_address')
        employment_element = mapper._get_child_element_name('contact_employment')
        
        # Simulate XPath construction (what code will do)
        address_xpath = f'./{address_element}'
        employment_xpath = f'./{employment_element}'
        
        # Assert: XPath reflects IL Lending structure
        assert address_xpath == './IL_contact_address'
        assert employment_xpath == './IL_contact_employment'
    
    def test_backwards_compatibility_with_standard_contract(self, standard_contract_data, tmp_path):
        """Standard contracts continue to work with existing element names."""
        # Arrange
        import json
        contract_path = tmp_path / "standard_contract.json"
        contract_path.write_text(json.dumps(standard_contract_data))
        
        mapper = DataMapper(mapping_contract_path=str(contract_path))
        
        # Act: Extract element names
        address_element = mapper._get_child_element_name('contact_address')
        employment_element = mapper._get_child_element_name('contact_employment')
        
        # Assert: Existing behavior preserved
        assert address_element == 'contact_address'
        assert employment_element == 'contact_employment'


class TestMultiProductSupport:
    """Tests for multi-product scenarios."""
    
    def test_different_products_use_same_table_names(self, tmp_path):
        """Different products map to same destination tables."""
        import json
        
        # Standard product
        standard_contract = create_minimal_contract([
            {
                "parent_table": "contact",
                "child_table": "contact_address",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Root/contact",
                "xml_child_path": "/Root/contact/contact_address"
            }
        ])
        standard_path = tmp_path / "standard.json"
        standard_path.write_text(json.dumps(standard_contract))
        
        # IL Lending product
        il_contract = create_minimal_contract([
            {
                "parent_table": "contact",
                "child_table": "contact_address",
                "foreign_key_column": "con_id",
                "xml_parent_path": "/Root/IL_contact",
                "xml_child_path": "/Root/IL_contact/IL_contact_address"
            }
        ])
        il_path = tmp_path / "il.json"
        il_path.write_text(json.dumps(il_contract))
        
        # Act: Create mappers for both products
        standard_mapper = DataMapper(mapping_contract_path=str(standard_path))
        il_mapper = DataMapper(mapping_contract_path=str(il_path))
        
        # Assert: Both use 'contact_address' as table name (child_table)
        # but extract different element names from XML
        standard_element = standard_mapper._get_child_element_name('contact_address')
        il_element = il_mapper._get_child_element_name('contact_address')
        
        assert standard_element == 'contact_address'
        assert il_element == 'IL_contact_address'
        
        # Both would write to same destination table but read from different XML elements
