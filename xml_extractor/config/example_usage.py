"""
Example usage of the centralized ConfigManager.

This script demonstrates how to use the new centralized configuration system
for the XML Database Extraction system.
"""

import os
import logging
from pathlib import Path

from .config_manager import ConfigManager, get_config_manager, reset_config_manager


def demonstrate_basic_usage():
    """Demonstrate basic ConfigManager usage."""
    print("=== Basic ConfigManager Usage ===")
    
    # Get the global configuration manager instance
    config_manager = get_config_manager()
    
    # Get database connection string
    connection_string = config_manager.get_database_connection_string()
    print(f"Database Connection: {connection_string[:50]}...")
    
    # Get processing configuration
    processing_config = config_manager.get_processing_config()
    print(f"Batch Size: {processing_config.batch_size}")
    print(f"Parallel Processes: {processing_config.parallel_processes}")
    print(f"Memory Limit: {processing_config.memory_limit_mb}MB")
    
    # Load mapping contract
    try:
        mapping_contract = config_manager.load_mapping_contract()
        print(f"Mapping Contract: {len(mapping_contract.mappings)} mappings loaded")
    except Exception as e:
        print(f"Could not load mapping contract: {e}")
    
    # Get configuration summary
    summary = config_manager.get_configuration_summary()
    print(f"Configuration Summary: {len(summary)} sections")


def demonstrate_environment_variables():
    """Demonstrate configuration with environment variables."""
    print("\n=== Environment Variable Configuration ===")
    
    # Set some environment variables
    os.environ['XML_EXTRACTOR_BATCH_SIZE'] = '2000'
    os.environ['XML_EXTRACTOR_PARALLEL_PROCESSES'] = '8'
    os.environ['XML_EXTRACTOR_MEMORY_LIMIT_MB'] = '1024'
    os.environ['XML_EXTRACTOR_DB_SERVER'] = 'localhost\\SQLEXPRESS'
    os.environ['XML_EXTRACTOR_DB_DATABASE'] = 'TestDB'
    
    # Reset the global config manager to pick up new environment variables
    reset_config_manager()
    
    # Get new configuration
    config_manager = get_config_manager()
    processing_config = config_manager.get_processing_config()
    
    print(f"Updated Batch Size: {processing_config.batch_size}")
    print(f"Updated Parallel Processes: {processing_config.parallel_processes}")
    print(f"Updated Memory Limit: {processing_config.memory_limit_mb}MB")
    print(f"Updated Database Server: {config_manager.database_config.server}")
    print(f"Updated Database Name: {config_manager.database_config.database}")


def demonstrate_component_integration():
    """Demonstrate how components use the centralized configuration."""
    print("\n=== Component Integration ===")
    
    # Import components that use centralized configuration
    from ..database.migration_engine import MigrationEngine
    from ..mapping.data_mapper import DataMapper
    
    # Create components without explicit configuration - they'll use centralized config
    try:
        migration_engine = MigrationEngine()
        print(f"MigrationEngine created with batch_size: {migration_engine.batch_size}")
        
        data_mapper = DataMapper()
        print(f"DataMapper created with mapping contract: {data_mapper._mapping_contract_path}")
        
    except Exception as e:
        print(f"Component creation failed: {e}")


def demonstrate_validation():
    """Demonstrate configuration validation."""
    print("\n=== Configuration Validation ===")
    
    config_manager = get_config_manager()
    
    try:
        is_valid = config_manager.validate_configuration()
        print(f"Configuration validation: {'PASSED' if is_valid else 'FAILED'}")
    except Exception as e:
        print(f"Configuration validation failed: {e}")


def demonstrate_caching():
    """Demonstrate configuration caching."""
    print("\n=== Configuration Caching ===")
    
    config_manager = get_config_manager()
    
    # Load mapping contract multiple times - should use cache
    try:
        print("Loading mapping contract (first time)...")
        contract1 = config_manager.load_mapping_contract()
        
        print("Loading mapping contract (second time - should use cache)...")
        contract2 = config_manager.load_mapping_contract()
        
        print(f"Same contract instance: {contract1 is contract2}")
        
        # Clear cache and reload
        config_manager.clear_cache()
        print("Cache cleared")
        
        print("Loading mapping contract (after cache clear)...")
        contract3 = config_manager.load_mapping_contract()
        
        print(f"Different contract instance after cache clear: {contract1 is not contract3}")
        
    except Exception as e:
        print(f"Caching demonstration failed: {e}")


def demonstrate_direct_configuration_access():
    """Demonstrate direct access to configuration components."""
    print("\n=== Direct Configuration Access ===")
    
    config_manager = get_config_manager()
    
    # Access database configuration directly
    db_config = config_manager.database_config
    print(f"Database Driver: {db_config.driver}")
    print(f"Connection Timeout: {db_config.connection_timeout}")
    print(f"MARS Connection: {db_config.mars_connection}")
    
    # Access processing parameters directly
    proc_params = config_manager.processing_params
    print(f"Max Retry Attempts: {proc_params.max_retry_attempts}")
    print(f"Retry Delay: {proc_params.retry_delay_seconds}s")
    
    # Access file paths directly
    paths = config_manager.paths
    print(f"Base Config Path: {paths.base_config_path}")
    print(f"SQL Scripts Path: {paths.sql_scripts_path}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run demonstrations
    demonstrate_basic_usage()
    demonstrate_environment_variables()
    demonstrate_component_integration()
    demonstrate_validation()
    demonstrate_caching()
    demonstrate_direct_configuration_access()
    
    print("\n=== ConfigManager Demonstration Complete ===")