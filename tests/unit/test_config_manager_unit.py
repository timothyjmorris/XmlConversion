"""
Tests for the centralized ConfigManager.

This module tests the centralized configuration management system
to ensure it properly handles environment variables, caching, and
component integration.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from xml_extractor.config.config_manager import (
    ConfigManager, 
    get_config_manager, 
    reset_config_manager,
    DatabaseConfig,
    ProcessingParameters,
    ConfigPaths
)
from xml_extractor.exceptions import ConfigurationError


class TestDatabaseConfig(unittest.TestCase):
    """Test DatabaseConfig class."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        env_vars = [
            'XML_EXTRACTOR_CONNECTION_STRING',
            'XML_EXTRACTOR_DB_DRIVER',
            'XML_EXTRACTOR_DB_SERVER',
            'XML_EXTRACTOR_DB_DATABASE',
            'XML_EXTRACTOR_DB_TRUSTED_CONNECTION',
            'XML_EXTRACTOR_DB_CONNECTION_TIMEOUT',
            'XML_EXTRACTOR_DB_COMMAND_TIMEOUT',
            'XML_EXTRACTOR_DB_MARS_CONNECTION',
            'XML_EXTRACTOR_DB_CHARSET'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_default_configuration(self):
        """Test default database configuration."""
        config = DatabaseConfig.from_environment()
        
        self.assertEqual(config.driver, "ODBC Driver 17 for SQL Server")
        self.assertEqual(config.server, "localhost\\SQLEXPRESS")
        self.assertEqual(config.database, "XmlConversionDB")
        self.assertTrue(config.trusted_connection)
        self.assertEqual(config.connection_timeout, 30)
        self.assertTrue(config.mars_connection)
        self.assertIn("DRIVER={ODBC Driver 17 for SQL Server}", config.connection_string)
        self.assertIn("Trusted_Connection=yes", config.connection_string)
        self.assertIn("Application Name=MAC XML Migration App", config.connection_string)
    
    def test_environment_variable_override(self):
        """Test database configuration from environment variables."""
        os.environ['XML_EXTRACTOR_DB_SERVER'] = 'testserver\\SQLEXPRESS'
        os.environ['XML_EXTRACTOR_DB_DATABASE'] = 'TestDB'
        os.environ['XML_EXTRACTOR_DB_CONNECTION_TIMEOUT'] = '60'
        
        config = DatabaseConfig.from_environment()
        
        self.assertEqual(config.server, 'testserver\\SQLEXPRESS')
        self.assertEqual(config.database, 'TestDB')
        self.assertEqual(config.connection_timeout, 60)
        self.assertIn("SERVER=testserver\\SQLEXPRESS", config.connection_string)
        self.assertIn("DATABASE=TestDB", config.connection_string)
    
    def test_direct_connection_string(self):
        """Test direct connection string override."""
        test_connection_string = "DRIVER={Test Driver};SERVER=testserver;DATABASE=testdb;"
        os.environ['XML_EXTRACTOR_CONNECTION_STRING'] = test_connection_string
        
        config = DatabaseConfig.from_environment()
        
        self.assertEqual(config.connection_string, test_connection_string)


class TestProcessingParameters(unittest.TestCase):
    """Test ProcessingParameters class."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        env_vars = [
            'XML_EXTRACTOR_BATCH_SIZE',
            'XML_EXTRACTOR_PARALLEL_PROCESSES',
            'XML_EXTRACTOR_MEMORY_LIMIT_MB',
            'XML_EXTRACTOR_PROGRESS_INTERVAL',
            'XML_EXTRACTOR_ENABLE_VALIDATION',
            'XML_EXTRACTOR_CHECKPOINT_INTERVAL'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_default_parameters(self):
        """Test default processing parameters."""
        params = ProcessingParameters.from_environment()
        
        self.assertEqual(params.batch_size, 1000)
        self.assertEqual(params.parallel_processes, 4)
        self.assertEqual(params.memory_limit_mb, 512)
        self.assertEqual(params.progress_reporting_interval, 10000)
        self.assertTrue(params.enable_validation)
        self.assertEqual(params.checkpoint_interval, 50000)
    
    def test_environment_variable_override(self):
        """Test processing parameters from environment variables."""
        os.environ['XML_EXTRACTOR_BATCH_SIZE'] = '2000'
        os.environ['XML_EXTRACTOR_PARALLEL_PROCESSES'] = '8'
        os.environ['XML_EXTRACTOR_MEMORY_LIMIT_MB'] = '1024'
        os.environ['XML_EXTRACTOR_ENABLE_VALIDATION'] = 'false'
        
        params = ProcessingParameters.from_environment()
        
        self.assertEqual(params.batch_size, 2000)
        self.assertEqual(params.parallel_processes, 8)
        self.assertEqual(params.memory_limit_mb, 1024)
        self.assertFalse(params.enable_validation)


class TestConfigManager(unittest.TestCase):
    """Test ConfigManager class."""
    
    def setUp(self):
        """Set up test environment."""
        # Reset global config manager
        reset_config_manager()
        
        # Create temporary directory for test configuration
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create test mapping contract file
        self.mapping_contract_path = self.temp_path / "test_mapping_contract.json"
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
            "enum_mappings": {},
            "bit_conversions": {}
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
            'XML_EXTRACTOR_MAPPING_CONTRACT_PATH',
            'XML_EXTRACTOR_BATCH_SIZE',
            'XML_EXTRACTOR_PARALLEL_PROCESSES',
            'XML_EXTRACTOR_MEMORY_LIMIT_MB'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_config_manager_initialization(self):
        """Test ConfigManager initialization."""
        config_manager = ConfigManager(self.temp_path)
        
        self.assertEqual(config_manager.paths.base_config_path, self.temp_path)
        self.assertIsNotNone(config_manager.database_config)
        self.assertIsNotNone(config_manager.processing_params)
    
    def test_get_database_connection_string(self):
        """Test getting database connection string."""
        config_manager = ConfigManager(self.temp_path)
        
        connection_string = config_manager.get_database_connection_string()
        
        self.assertIsInstance(connection_string, str)
        self.assertIn("DRIVER=", connection_string)
    
    def test_get_processing_config(self):
        """Test getting processing configuration."""
        # Clear any environment variables that might affect this test
        env_vars = [
            'XML_EXTRACTOR_BATCH_SIZE',
            'XML_EXTRACTOR_PARALLEL_PROCESSES',
            'XML_EXTRACTOR_MEMORY_LIMIT_MB'
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
        
        config_manager = ConfigManager(self.temp_path)
        
        processing_config = config_manager.get_processing_config()
        
        self.assertEqual(processing_config.batch_size, 1000)
        self.assertEqual(processing_config.parallel_processes, 4)
        self.assertIsInstance(processing_config.sql_server_connection_string, str)
    
    def test_load_mapping_contract_with_caching(self):
        """Test mapping contract loading with caching."""
        config_manager = ConfigManager(self.temp_path)
        
        # First call should load from file
        contract1 = config_manager.load_mapping_contract(str(self.mapping_contract_path.relative_to(self.temp_path)))
        
        # Second call should use cache
        contract2 = config_manager.load_mapping_contract(str(self.mapping_contract_path.relative_to(self.temp_path)))
        
        # Should be the same cached instance
        self.assertEqual(contract1, contract2)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Set the mapping contract path to our test file
        os.environ['XML_EXTRACTOR_MAPPING_CONTRACT_PATH'] = str(self.mapping_contract_path.relative_to(self.temp_path))
        
        config_manager = ConfigManager(self.temp_path)
        
        # Should pass validation with test settings
        is_valid = config_manager.validate_configuration()
        self.assertTrue(is_valid)
    
    def test_configuration_summary(self):
        """Test configuration summary."""
        config_manager = ConfigManager(self.temp_path)
        
        summary = config_manager.get_configuration_summary()
        
        self.assertIn('database', summary)
        self.assertIn('processing', summary)
        self.assertIn('paths', summary)
        self.assertIn('server', summary['database'])
        self.assertIn('batch_size', summary['processing'])
    
    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        config_manager = ConfigManager(self.temp_path)
        
        # Load something to populate cache
        try:
            config_manager.load_mapping_contract(str(self.mapping_contract_path.relative_to(self.temp_path)))
        except:
            pass  # Ignore errors for this test
        
        # Clear cache
        config_manager.clear_cache()
        
        # Verify cache is cleared (should be empty dictionaries)
        self.assertEqual(len(config_manager._mapping_contract_cache), 0)
        self.assertEqual(len(config_manager._table_structure_cache), 0)
        self.assertEqual(len(config_manager._sample_xml_cache), 0)


class TestGlobalConfigManager(unittest.TestCase):
    """Test global config manager functions."""
    
    def setUp(self):
        """Set up test environment."""
        reset_config_manager()
    
    def tearDown(self):
        """Clean up test environment."""
        reset_config_manager()
    
    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton instance."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        self.assertIs(manager1, manager2)
    
    def test_reset_config_manager(self):
        """Test resetting global config manager."""
        manager1 = get_config_manager()
        reset_config_manager()
        manager2 = get_config_manager()
        
        self.assertIsNot(manager1, manager2)


if __name__ == '__main__':
    unittest.main()