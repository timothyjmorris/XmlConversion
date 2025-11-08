"""
Integration tests for centralized configuration with system components.

This module tests that the centralized ConfigManager properly integrates
with the MigrationEngine and DataMapper components.
"""

import os
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from xml_extractor.config.config_manager import get_config_manager, reset_config_manager
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.mapping.data_mapper import DataMapper


class TestConfigIntegration(unittest.TestCase):
    """Test integration between ConfigManager and system components."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset global config manager
        reset_config_manager()
        
        # Clear environment variables
        env_vars = [
            'XML_EXTRACTOR_BATCH_SIZE',
            'XML_EXTRACTOR_PARALLEL_PROCESSES',
            'XML_EXTRACTOR_CONNECTION_STRING'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        # Create temporary directory for test configuration
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test mapping contract file
        self.mapping_contract_path = self.temp_path / "config" / "mapping_contract.json"
        self.mapping_contract_path.parent.mkdir(parents=True, exist_ok=True)
        
        test_contract = {
            "source_table": "app_xml",
            "source_column": "xml",
            "xml_root_element": "Provenir",
            "mappings": [
                {
                    "xml_path": "/Provenir/Request",
                    "xml_attribute": "ID",
                    "target_table": "app_base",
                    "target_column": "app_id",
                    "data_type": "int"
                }
            ],
            "relationships": [],
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
            "enum_mappings": {},
            "bit_conversions": {},
            "default_values": {}
        }
        
        import json
        with open(self.mapping_contract_path, 'w') as f:
            json.dump(test_contract, f)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        reset_config_manager()
        
        # Clean up environment variables
        env_vars = [
            'XML_EXTRACTOR_BATCH_SIZE',
            'XML_EXTRACTOR_PARALLEL_PROCESSES',
            'XML_EXTRACTOR_CONNECTION_STRING'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_migration_engine_uses_centralized_config(self):
        """Test that MigrationEngine uses centralized configuration."""
        # Set environment variables
        os.environ['XML_EXTRACTOR_BATCH_SIZE'] = '2500'
        os.environ['XML_EXTRACTOR_CONNECTION_STRING'] = 'test_connection_string'
        
        # Initialize config manager with test path
        config_manager = get_config_manager(self.temp_path)
        
        # Create MigrationEngine without explicit parameters
        migration_engine = MigrationEngine()
        
        # Verify it uses centralized configuration
        self.assertEqual(migration_engine.batch_size, 2500)
        self.assertEqual(migration_engine.connection_string, 'test_connection_string')
    
    def test_migration_engine_explicit_params_override(self):
        """Test that explicit parameters override centralized configuration."""
        # Set environment variables
        os.environ['XML_EXTRACTOR_BATCH_SIZE'] = '2500'
        os.environ['XML_EXTRACTOR_CONNECTION_STRING'] = 'test_connection_string'
        
        # Initialize config manager
        config_manager = get_config_manager(self.temp_path)
        
        # Create MigrationEngine with explicit parameters
        migration_engine = MigrationEngine(
            connection_string='explicit_connection_string'
        )
        
        # Verify explicit parameter takes precedence
        # Note: batch_size is now centralized in ProcessingDefaults and not configurable per-engine
        self.assertEqual(migration_engine.connection_string, 'explicit_connection_string')
    
    def test_data_mapper_uses_centralized_config(self):
        """Test that DataMapper uses centralized configuration."""
        # Initialize config manager with test path
        config_manager = get_config_manager(self.temp_path)
        
        # Create DataMapper without explicit mapping contract path
        data_mapper = DataMapper()
        
        # Verify it uses centralized configuration
        expected_path = config_manager.paths.mapping_contract_path
        self.assertEqual(data_mapper._mapping_contract_path, expected_path)
        
        # Verify it loaded configurations from centralized manager
        self.assertIsInstance(data_mapper._enum_mappings, dict)
        self.assertIsInstance(data_mapper._bit_conversions, dict)
    
    def test_data_mapper_explicit_path_override(self):
        """Test that explicit mapping contract path overrides centralized configuration."""
        # Initialize config manager
        config_manager = get_config_manager(self.temp_path)
        
        # Create a separate contract file with explicit path
        explicit_contract_path = self.temp_path / "custom_contract.json"
        explicit_contract_path.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        with open(explicit_contract_path, 'w') as f:
            # Use the same contract structure from setUp
            test_contract = {
                "source_table": "app_xml",
                "source_column": "xml",
                "xml_root_element": "Provenir",
                "mappings": [
                    {
                        "xml_path": "/Provenir/Request",
                        "xml_attribute": "ID",
                        "target_table": "app_base",
                        "target_column": "app_id",
                        "data_type": "int"
                    }
                ],
                "relationships": [],
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
                "enum_mappings": {},
                "bit_conversions": {},
                "default_values": {}
            }
            json.dump(test_contract, f)
        
        # Create DataMapper with explicit mapping contract path
        data_mapper = DataMapper(mapping_contract_path=str(explicit_contract_path))
        
        # Verify explicit path takes precedence
        self.assertEqual(data_mapper._mapping_contract_path, str(explicit_contract_path))
    
    def test_components_share_same_config_manager(self):
        """Test that components share the same global config manager instance."""
        # Initialize config manager
        config_manager1 = get_config_manager(self.temp_path)
        
        # Create components
        migration_engine = MigrationEngine()
        data_mapper = DataMapper()
        
        # Get config manager from components (indirectly)
        config_manager2 = get_config_manager()
        
        # Verify they share the same instance
        self.assertIs(config_manager1, config_manager2)
    
    def test_environment_variable_changes_affect_new_components(self):
        """Test that environment variable changes affect newly created components."""
        # Initialize config manager
        config_manager = get_config_manager(self.temp_path)
        
        # Create component with initial settings
        migration_engine1 = MigrationEngine()
        initial_batch_size = migration_engine1.batch_size
        
        # Change environment variable
        os.environ['XML_EXTRACTOR_BATCH_SIZE'] = '5000'
        
        # Reset config manager to pick up new environment variables
        reset_config_manager()
        config_manager = get_config_manager(self.temp_path)
        
        # Create new component
        migration_engine2 = MigrationEngine()
        
        # Verify new component uses updated configuration
        self.assertNotEqual(migration_engine1.batch_size, migration_engine2.batch_size)
        self.assertEqual(migration_engine2.batch_size, 5000)
    
    def test_config_manager_integration(self):
        """Test that ConfigManager properly integrates with system components."""
        # Initialize config manager
        config_manager = get_config_manager(self.temp_path)
        
        # Create DataMapper (which uses enum mappings, bit conversions, etc.)
        data_mapper = DataMapper()
        
        # Verify DataMapper loaded configurations (even if empty due to test setup)
        self.assertIsInstance(data_mapper._enum_mappings, dict)
        self.assertIsInstance(data_mapper._bit_conversions, dict)


if __name__ == '__main__':
    unittest.main()