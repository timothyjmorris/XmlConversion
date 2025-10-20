# Centralized Configuration Management

This document describes the centralized configuration management system for the XML Database Extraction project.

## Overview

The centralized configuration system provides a single source of truth for all configuration management, including:

- Database connection configuration
- Processing parameters (batch size, parallel processes, memory limits)
- File paths for mapping contracts, SQL scripts, and sample XML
- Environment variable support
- Configuration caching and validation

## Key Components

### ConfigManager

The main `ConfigManager` class serves as the centralized configuration hub:

```python
from xml_extractor.config.config_manager import get_config_manager

# Get the global configuration manager instance
config_manager = get_config_manager()

# Get database connection string
connection_string = config_manager.get_database_connection_string()

# Get processing configuration
processing_config = config_manager.get_processing_config()

# Load mapping contract
mapping_contract = config_manager.load_mapping_contract()
```

### Environment Variable Support

All configuration can be customized using environment variables:

#### Database Configuration
- `XML_EXTRACTOR_CONNECTION_STRING`: Complete database connection string
- `XML_EXTRACTOR_DB_DRIVER`: ODBC driver name (default: "ODBC Driver 17 for SQL Server")
- `XML_EXTRACTOR_DB_SERVER`: Database server (default: "localhost\\SQLEXPRESS")
- `XML_EXTRACTOR_DB_DATABASE`: Database name (default: "XmlConversionDB")
- `XML_EXTRACTOR_DB_TRUSTED_CONNECTION`: Use Windows authentication (default: "true")
- `XML_EXTRACTOR_DB_CONNECTION_TIMEOUT`: Connection timeout in seconds (default: 30)
- `XML_EXTRACTOR_DB_MARS_CONNECTION`: Enable MARS (default: "true")

#### Processing Parameters
- `XML_EXTRACTOR_BATCH_SIZE`: Batch size for processing (default: 1000)
- `XML_EXTRACTOR_PARALLEL_PROCESSES`: Number of parallel processes (default: 4)
- `XML_EXTRACTOR_MEMORY_LIMIT_MB`: Memory limit in MB (default: 512)
- `XML_EXTRACTOR_PROGRESS_INTERVAL`: Progress reporting interval (default: 10000)
- `XML_EXTRACTOR_ENABLE_VALIDATION`: Enable data validation (default: "true")
- `XML_EXTRACTOR_CHECKPOINT_INTERVAL`: Checkpoint interval (default: 50000)

#### File Paths
- `XML_EXTRACTOR_CONFIG_PATH`: Base configuration directory path
- `XML_EXTRACTOR_MAPPING_CONTRACT_PATH`: Mapping contract file path
- `XML_EXTRACTOR_SQL_SCRIPTS_PATH`: SQL scripts directory path
- `XML_EXTRACTOR_DATA_MODEL_PATH`: Data model documentation path
- `XML_EXTRACTOR_SAMPLE_XML_PATH`: Sample XML directory path

## Component Integration

### MigrationEngine

The `MigrationEngine` automatically uses centralized configuration:

```python
from xml_extractor.database.migration_engine import MigrationEngine

# Uses centralized configuration
migration_engine = MigrationEngine()

# Or override specific parameters
migration_engine = MigrationEngine(
    connection_string="custom_connection_string",
    batch_size=2000
)
```

### DataMapper

The `DataMapper` automatically uses centralized configuration:

```python
from xml_extractor.mapping.data_mapper import DataMapper

# Uses centralized configuration
data_mapper = DataMapper()

# Or override mapping contract path
data_mapper = DataMapper(mapping_contract_path="custom/contract.json")
```

## Configuration Examples

### Development Environment

```bash
# Set environment variables for development
export XML_EXTRACTOR_DB_SERVER="localhost\\SQLEXPRESS"
export XML_EXTRACTOR_DB_DATABASE="XmlConversionDB_Dev"
export XML_EXTRACTOR_BATCH_SIZE="500"
export XML_EXTRACTOR_PARALLEL_PROCESSES="2"
export XML_EXTRACTOR_ENABLE_VALIDATION="true"
```

### Production Environment

```bash
# Set environment variables for production
export XML_EXTRACTOR_CONNECTION_STRING="DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server;DATABASE=XmlConversionDB;UID=xmluser;PWD=secure_password;"
export XML_EXTRACTOR_BATCH_SIZE="5000"
export XML_EXTRACTOR_PARALLEL_PROCESSES="16"
export XML_EXTRACTOR_MEMORY_LIMIT_MB="4096"
export XML_EXTRACTOR_ENABLE_VALIDATION="false"
```

### Testing Environment

```python
import os
from xml_extractor.config.config_manager import reset_config_manager, get_config_manager

# Set test configuration
os.environ['XML_EXTRACTOR_DB_DATABASE'] = 'TestDB'
os.environ['XML_EXTRACTOR_BATCH_SIZE'] = '100'

# Reset to pick up new environment variables
reset_config_manager()

# Get updated configuration
config_manager = get_config_manager()
```

## Configuration Validation

The system includes built-in configuration validation:

```python
from xml_extractor.config.config_manager import get_config_manager

config_manager = get_config_manager()

try:
    is_valid = config_manager.validate_configuration()
    print(f"Configuration is {'valid' if is_valid else 'invalid'}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Caching

The configuration system includes intelligent caching:

- Mapping contracts are cached after first load
- Table structures are cached after first load
- Sample XML files are cached after first load
- Cache can be cleared manually: `config_manager.clear_cache()`
- Configuration can be reloaded: `config_manager.reload_configuration()`

## Simplified Architecture

The centralized configuration system replaces all previous configuration management:

1. **Single Source of Truth**: All configuration is managed through the `ConfigManager` class
2. **No Legacy Dependencies**: The system is built from the ground up for simplicity
3. **Override Support**: Explicit parameters still override centralized configuration when needed

## Best Practices

1. **Use Environment Variables**: Configure production systems using environment variables
2. **Validate Configuration**: Always validate configuration before processing
3. **Cache Management**: Clear cache when configuration files change
4. **Error Handling**: Handle configuration errors gracefully
5. **Documentation**: Document custom environment variables in deployment scripts

## Troubleshooting

### Common Issues

1. **Missing Configuration Files**: Ensure mapping contract and other files exist in the configured paths
2. **Environment Variable Types**: Ensure numeric environment variables contain valid numbers
3. **Connection String Format**: Verify database connection string format is correct
4. **File Permissions**: Ensure the application has read access to configuration files

### Debug Information

```python
from xml_extractor.config.config_manager import get_config_manager

config_manager = get_config_manager()

# Get configuration summary
summary = config_manager.get_configuration_summary()
print(json.dumps(summary, indent=2))

# Validate configuration
try:
    config_manager.validate_configuration()
    print("Configuration is valid")
except Exception as e:
    print(f"Configuration error: {e}")
```

## Security Considerations

1. **Connection Strings**: Store sensitive connection strings in environment variables, not in code
2. **File Permissions**: Restrict access to configuration files containing sensitive information
3. **Environment Variables**: Use secure methods to set environment variables in production
4. **Logging**: Avoid logging sensitive configuration values

## Future Enhancements

The centralized configuration system is designed to be extensible:

1. **Configuration Files**: Support for additional configuration file formats (YAML, TOML)
2. **Remote Configuration**: Support for loading configuration from remote sources
3. **Configuration Profiles**: Support for multiple configuration profiles (dev, test, prod)
4. **Dynamic Reloading**: Support for dynamic configuration reloading without restart