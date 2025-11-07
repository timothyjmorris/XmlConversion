"""
Centralized configuration management for the XML Database Extraction system.

This module provides the ConfigManager class that serves as the single source of truth
for all configuration management, including database connections, mapping contracts,
processing parameters, and environment variable handling.
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

from ..interfaces import ConfigurationManagerInterface
from ..models import MappingContract, FieldMapping, RelationshipMapping, ProcessingConfig
from ..exceptions import ConfigurationError, ValidationError


@dataclass
class DatabaseConfig:
    """Database configuration with environment variable support."""
    connection_string: str
    driver: str = "ODBC Driver 17 for SQL Server"
    server: str = "localhost\\SQLEXPRESS"
    database: str = "XmlConversionDB"
    trusted_connection: bool = True
    connection_timeout: int = 30
    command_timeout: int = 300
    mars_connection: bool = True
    charset: str = "UTF-8"
    schema_prefix: str = ""  # Optional schema prefix for table names (e.g., "sandbox", "dbo")
    connection_pooling: bool = True  # Enable connection pooling for better performance
    packet_size: int = 4096  # Network packet size (4096 is default, can be 512-32767)
    
    @classmethod
    def from_environment(cls) -> 'DatabaseConfig':
        """Create database configuration from environment variables."""
        # Primary connection string from environment
        connection_string = os.environ.get('XML_EXTRACTOR_CONNECTION_STRING')
        
        if connection_string:
            return cls(connection_string=connection_string)
        
        # Build connection string from individual components
        driver = os.environ.get('XML_EXTRACTOR_DB_DRIVER', cls.driver)
        server = os.environ.get('XML_EXTRACTOR_DB_SERVER', cls.server)
        database = os.environ.get('XML_EXTRACTOR_DB_DATABASE', cls.database)
        trusted_connection = os.environ.get('XML_EXTRACTOR_DB_TRUSTED_CONNECTION', 'true').lower() == 'true'
        connection_timeout = int(os.environ.get('XML_EXTRACTOR_DB_CONNECTION_TIMEOUT', cls.connection_timeout))
        command_timeout = int(os.environ.get('XML_EXTRACTOR_DB_COMMAND_TIMEOUT', cls.command_timeout))
        mars_connection = os.environ.get('XML_EXTRACTOR_DB_MARS_CONNECTION', 'true').lower() == 'true'
        charset = os.environ.get('XML_EXTRACTOR_DB_CHARSET', cls.charset)
        # NOTE: Schema prefix is now CONTRACT-DRIVEN via MappingContract.target_schema
        # Each mapping contract specifies its target schema (e.g., "sandbox" or "dbo")
        # Do NOT use XML_EXTRACTOR_DB_SCHEMA_PREFIX environment variable - it's deprecated
        schema_prefix = ""  # Kept empty; use MappingContract.target_schema instead
        connection_pooling = os.environ.get('XML_EXTRACTOR_DB_CONNECTION_POOLING', 'true').lower() == 'true'
        packet_size = int(os.environ.get('XML_EXTRACTOR_DB_PACKET_SIZE', cls.packet_size))
        
        # Build connection string based on authentication method
        if trusted_connection:
            connection_string = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
                f"Connection Timeout={connection_timeout};"
                f"Application Name=MAC XML Migration App;"
                f"TrustServerCertificate=yes;"
                f"Encrypt=no;"
            )
            if mars_connection:
                connection_string += "MultipleActiveResultSets=True;"
            if connection_pooling:
                connection_string += "Pooling=True;"
            if packet_size != 4096:  # Only add if different from default
                connection_string += f"Packet Size={packet_size};"
            if charset:
                connection_string += f"CharacterSet={charset};"
        else:
            username = os.environ.get('XML_EXTRACTOR_DB_USERNAME', '')
            password = os.environ.get('XML_EXTRACTOR_DB_PASSWORD', '')
            connection_string = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                f"Connection Timeout={connection_timeout};"
                f"Application Name=MAC XML Migration App;"
                f"TrustServerCertificate=yes;"
                f"Encrypt=no;"
            )
            if mars_connection:
                connection_string += "MultipleActiveResultSets=True;"
            if connection_pooling:
                connection_string += "Pooling=True;"
            if packet_size != 4096:  # Only add if different from default
                connection_string += f"Packet Size={packet_size};"
        
        return cls(
            connection_string=connection_string,
            driver=driver,
            server=server,
            database=database,
            trusted_connection=trusted_connection,
            connection_timeout=connection_timeout,
            command_timeout=command_timeout,
            mars_connection=mars_connection,
            charset=charset,
            schema_prefix=schema_prefix,
            connection_pooling=connection_pooling,
            packet_size=packet_size
        )


@dataclass
class ProcessingParameters:
    """Processing parameters with environment variable support."""
    batch_size: int = 1000
    parallel_processes: int = 4
    memory_limit_mb: int = 512
    progress_reporting_interval: int = 10000
    enable_validation: bool = True
    checkpoint_interval: int = 50000
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 5
    
    @classmethod
    def from_environment(cls) -> 'ProcessingParameters':
        """Create processing parameters from environment variables."""
        return cls(
            batch_size=int(os.environ.get('XML_EXTRACTOR_BATCH_SIZE', cls.batch_size)),
            parallel_processes=int(os.environ.get('XML_EXTRACTOR_PARALLEL_PROCESSES', cls.parallel_processes)),
            memory_limit_mb=int(os.environ.get('XML_EXTRACTOR_MEMORY_LIMIT_MB', cls.memory_limit_mb)),
            progress_reporting_interval=int(os.environ.get('XML_EXTRACTOR_PROGRESS_INTERVAL', cls.progress_reporting_interval)),
            enable_validation=os.environ.get('XML_EXTRACTOR_ENABLE_VALIDATION', 'true').lower() == 'true',
            checkpoint_interval=int(os.environ.get('XML_EXTRACTOR_CHECKPOINT_INTERVAL', cls.checkpoint_interval)),
            max_retry_attempts=int(os.environ.get('XML_EXTRACTOR_MAX_RETRY_ATTEMPTS', cls.max_retry_attempts)),
            retry_delay_seconds=int(os.environ.get('XML_EXTRACTOR_RETRY_DELAY_SECONDS', cls.retry_delay_seconds))
        )


@dataclass
class ConfigPaths:
    """Configuration file paths with environment variable support."""
    base_config_path: Path = field(default_factory=lambda: Path.cwd())
    mapping_contract_path: str = "config/mapping_contract.json"
    sql_scripts_path: str = "config/samples"
    data_model_path: str = "config/data-model.md"
    sample_xml_path: str = "config/samples"
    
    @classmethod
    def from_environment(cls, base_path: Optional[Union[str, Path]] = None) -> 'ConfigPaths':
        """Create configuration paths from environment variables."""
        if base_path:
            base_config_path = Path(base_path)
        else:
            base_config_path = Path(os.environ.get('XML_EXTRACTOR_CONFIG_PATH', Path.cwd()))
        
        return cls(
            base_config_path=base_config_path,
            mapping_contract_path=os.environ.get('XML_EXTRACTOR_MAPPING_CONTRACT_PATH', cls.mapping_contract_path),
            sql_scripts_path=os.environ.get('XML_EXTRACTOR_SQL_SCRIPTS_PATH', cls.sql_scripts_path),
            data_model_path=os.environ.get('XML_EXTRACTOR_DATA_MODEL_PATH', cls.data_model_path),
            sample_xml_path=os.environ.get('XML_EXTRACTOR_SAMPLE_XML_PATH', cls.sample_xml_path)
        )


class ConfigManager(ConfigurationManagerInterface):
    """
    Centralized configuration manager serving as single source of truth.
    
    This class consolidates all configuration management including:
    - Database connection configuration
    - Processing parameters
    - Mapping contract loading
    - File path management
    - Environment variable handling
    """
    
    def __init__(self, base_config_path: Optional[Union[str, Path]] = None):
        """
        Initialize the centralized configuration manager.
        
        Args:
            base_config_path: Base path for configuration files. If None, uses current directory.
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from environment variables
        self.paths = ConfigPaths.from_environment(base_config_path)
        self.database_config = DatabaseConfig.from_environment()
        self.processing_params = ProcessingParameters.from_environment()
        
        # Cache for loaded configurations
        self._mapping_contract_cache: Dict[str, MappingContract] = {}
        self._table_structure_cache: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._sample_xml_cache: Dict[str, List[str]] = {}
        
        self.logger.info(f"ConfigManager initialized with base path: {self.paths.base_config_path}")
        self.logger.info(f"Database server: {self.database_config.server}")
        self.logger.info(f"Processing batch size: {self.processing_params.batch_size}")
    
    def get_database_connection_string(self) -> str:
        """
        Get database connection string.
        
        Returns:
            Database connection string configured from environment variables
        """
        return self.database_config.connection_string
    
    def get_qualified_table_name(self, table_name: str) -> str:
        """
        Get fully qualified table name with schema prefix if configured.
        
        Args:
            table_name: Base table name (e.g., "app_base")
            
        Returns:
            Qualified table name (e.g., "sandbox.app_base" or "app_base")
        """
        if self.database_config.schema_prefix:
            return f"[{self.database_config.schema_prefix}].[{table_name}]"
        else:
            return f"[{table_name}]"
    
    def get_processing_config(self) -> ProcessingConfig:
        """
        Get processing configuration with all parameters.
        
        Returns:
            ProcessingConfig object with environment-configured values
        """
        return ProcessingConfig(
            batch_size=self.processing_params.batch_size,
            parallel_processes=self.processing_params.parallel_processes,
            memory_limit_mb=self.processing_params.memory_limit_mb,
            progress_reporting_interval=self.processing_params.progress_reporting_interval,
            sql_server_connection_string=self.database_config.connection_string,
            enable_validation=self.processing_params.enable_validation,
            checkpoint_interval=self.processing_params.checkpoint_interval
        )
    
    def load_mapping_contract(self, contract_path: Optional[str] = None) -> MappingContract:
        """
        Load mapping contract with caching.
        
        Args:
            contract_path: Optional path to mapping contract. If None, uses default from configuration.
            
        Returns:
            Loaded and validated mapping contract
        """
        if contract_path is None:
            contract_path = self.paths.mapping_contract_path
        
        # Return cached contract if available
        if contract_path in self._mapping_contract_cache:
            self.logger.debug(f"Returning cached mapping contract for {contract_path}")
            return self._mapping_contract_cache[contract_path]
        
        full_path = self.paths.base_config_path / contract_path
        
        if not full_path.exists():
            raise ConfigurationError(f"Mapping contract file not found: {full_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                if full_path.suffix.lower() in ['.yaml', '.yml']:
                    import yaml
                    contract_data = yaml.safe_load(file)
                elif full_path.suffix.lower() == '.json':
                    contract_data = json.load(file)
                else:
                    raise ConfigurationError(f"Unsupported file format: {full_path.suffix}")
                    
        except (json.JSONDecodeError, ImportError) as e:
            raise ConfigurationError(f"Failed to parse mapping contract file {full_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read mapping contract file {full_path}: {e}")
        
        # Parse and validate the contract
        contract = self._parse_mapping_contract(contract_data, contract_path)
        self._validate_mapping_contract(contract)
        
        # Cache the result
        self._mapping_contract_cache[contract_path] = contract
        
        self.logger.info(f"Loaded mapping contract from {contract_path}")
        return contract
    
    def load_table_structure(self, sql_script_path: Optional[str] = None, 
                           data_model_path: Optional[str] = None) -> Dict[str, Dict[str, str]]:
        """
        Load table structure with caching.
        
        Args:
            sql_script_path: Optional path to SQL scripts. If None, uses default from configuration.
            data_model_path: Optional path to data model. If None, uses default from configuration.
            
        Returns:
            Dictionary with table structure information
        """
        if sql_script_path is None:
            sql_script_path = self.paths.sql_scripts_path
        if data_model_path is None:
            data_model_path = self.paths.data_model_path
        
        # Return cached structure if available
        cache_key = f"{sql_script_path}|{data_model_path}"
        if cache_key in self._table_structure_cache:
            self.logger.debug(f"Returning cached table structure for {cache_key}")
            return self._table_structure_cache[cache_key]
        
        table_structure = {}
        
        # Load from SQL scripts
        sql_tables = self._parse_sql_scripts(sql_script_path)
        table_structure.update(sql_tables)
        
        # Load from data model documentation
        data_model_tables = self._parse_data_model(data_model_path)
        
        # Merge data model information with SQL structure
        for table_name, columns in data_model_tables.items():
            if table_name in table_structure:
                # Update existing table with additional metadata
                table_structure[table_name].update(columns)
            else:
                # Add new table from data model
                table_structure[table_name] = columns
        
        # Cache the result
        self._table_structure_cache[cache_key] = table_structure
        
        self.logger.info(f"Loaded table structure from {sql_script_path} and {data_model_path}")
        return table_structure
    
    def load_sample_xml(self, sample_path: Optional[str] = None) -> List[str]:
        """
        Load sample XML documents with caching.
        
        Args:
            sample_path: Optional path to sample XML directory. If None, uses default from configuration.
            
        Returns:
            List of sample XML content strings
        """
        if sample_path is None:
            sample_path = self.paths.sample_xml_path
        
        # Return cached samples if available
        if sample_path in self._sample_xml_cache:
            self.logger.debug(f"Returning cached sample XML for {sample_path}")
            return self._sample_xml_cache[sample_path]
        
        full_path = self.paths.base_config_path / sample_path
        
        if not full_path.exists():
            raise ConfigurationError(f"Sample XML directory not found: {full_path}")
        
        if not full_path.is_dir():
            raise ConfigurationError(f"Sample XML path is not a directory: {full_path}")
        
        xml_files = list(full_path.glob("*.xml"))
        
        if not xml_files:
            raise ConfigurationError(f"No XML files found in directory: {full_path}")
        
        sample_xml_content = []
        
        for xml_file in xml_files:
            try:
                with open(xml_file, 'r', encoding='utf-8') as file:
                    content = file.read()
                    sample_xml_content.append(content)
                    self.logger.debug(f"Loaded sample XML file: {xml_file.name}")
            except Exception as e:
                self.logger.warning(f"Failed to load sample XML file {xml_file}: {e}")
                continue
        
        if not sample_xml_content:
            raise ConfigurationError(f"Failed to load any sample XML files from {full_path}")
        
        # Cache the result
        self._sample_xml_cache[sample_path] = sample_xml_content
        
        self.logger.info(f"Loaded {len(sample_xml_content)} sample XML files from {sample_path}")
        return sample_xml_content
    
    def get_enum_mappings(self, contract_path: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """
        Get enum mappings from the mapping contract.
        
        Args:
            contract_path: Optional path to mapping contract. If None, uses default.
            
        Returns:
            Dictionary of enum mappings
        """
        if contract_path is None:
            contract_path = self.paths.mapping_contract_path
        
        contract = self.load_mapping_contract(contract_path)
        contract_data = getattr(contract, '_raw_data', {})
        return contract_data.get('enum_mappings', {})
    
    def get_bit_conversions(self, contract_path: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """
        Get bit conversion mappings from the mapping contract.
        
        Args:
            contract_path: Optional path to mapping contract. If None, uses default.
            
        Returns:
            Dictionary of bit conversion mappings
        """
        if contract_path is None:
            contract_path = self.paths.mapping_contract_path
        
        contract = self.load_mapping_contract(contract_path)
        contract_data = getattr(contract, '_raw_data', {})
        return contract_data.get('bit_conversions', {})
    
    def validate_configuration(self) -> bool:
        """
        Validate all configuration settings.
        
        Returns:
            True if all configurations are valid
            
        Raises:
            ConfigurationError: If any configuration is invalid
        """
        errors = []
        
        # Validate database configuration
        if not self.database_config.connection_string:
            errors.append("Database connection string is empty")
        
        # Validate file paths
        if not self.paths.base_config_path.exists():
            errors.append(f"Base configuration path does not exist: {self.paths.base_config_path}")
        
        mapping_contract_full_path = self.paths.base_config_path / self.paths.mapping_contract_path
        if not mapping_contract_full_path.exists():
            errors.append(f"Mapping contract file does not exist: {mapping_contract_full_path}")
        
        # Validate processing parameters
        if self.processing_params.batch_size <= 0:
            errors.append("Batch size must be greater than 0")
        
        if self.processing_params.parallel_processes <= 0:
            errors.append("Parallel processes must be greater than 0")
        
        if self.processing_params.memory_limit_mb <= 0:
            errors.append("Memory limit must be greater than 0")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
        
        self.logger.info("Configuration validation passed")
        return True
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all configuration settings.
        
        Returns:
            Dictionary containing configuration summary
        """
        return {
            'database': {
                'server': self.database_config.server,
                'database': self.database_config.database,
                'driver': self.database_config.driver,
                'trusted_connection': self.database_config.trusted_connection,
                'connection_timeout': self.database_config.connection_timeout,
                'mars_connection': self.database_config.mars_connection
            },
            'processing': {
                'batch_size': self.processing_params.batch_size,
                'parallel_processes': self.processing_params.parallel_processes,
                'memory_limit_mb': self.processing_params.memory_limit_mb,
                'progress_reporting_interval': self.processing_params.progress_reporting_interval,
                'enable_validation': self.processing_params.enable_validation,
                'checkpoint_interval': self.processing_params.checkpoint_interval
            },
            'paths': {
                'base_config_path': str(self.paths.base_config_path),
                'mapping_contract_path': self.paths.mapping_contract_path,
                'sql_scripts_path': self.paths.sql_scripts_path,
                'data_model_path': self.paths.data_model_path,
                'sample_xml_path': self.paths.sample_xml_path
            }
        }
    
    def clear_cache(self) -> None:
        """Clear all cached configurations."""
        self._mapping_contract_cache.clear()
        self._table_structure_cache.clear()
        self._sample_xml_cache.clear()
        
        self.logger.info("Configuration cache cleared")
    
    def reload_configuration(self) -> None:
        """Reload configuration from environment variables and clear cache."""
        self.database_config = DatabaseConfig.from_environment()
        self.processing_params = ProcessingParameters.from_environment()
        self.clear_cache()
        
        self.logger.info("Configuration reloaded from environment variables")
    
    def _parse_mapping_contract(self, contract_data: Dict[str, Any], 
                              contract_path: str) -> MappingContract:
        """
        Parse mapping contract data into MappingContract object.
        
        Args:
            contract_data: Raw contract data from JSON/YAML
            contract_path: Path to contract file (for error reporting)
            
        Returns:
            Parsed MappingContract object
            
        Raises:
            ValidationError: If contract structure is invalid
        """
        try:
            from ..models import ElementFiltering, FilterRule
            
            # Extract basic contract information
            source_table = contract_data.get('source_table', '')
            source_column = contract_data.get('source_column', '')
            xml_root_element = contract_data.get('xml_root_element', '')
            xml_application_path = contract_data.get('xml_application_path')
            target_schema = contract_data.get('target_schema', 'dbo')  # Contract-driven schema isolation
            
            # Parse element filtering rules
            element_filtering = None
            element_filtering_data = contract_data.get('element_filtering')
            if element_filtering_data:
                filter_rules = []
                for rule_data in element_filtering_data.get('filter_rules', []):
                    filter_rule = FilterRule(
                        element_type=rule_data.get('element_type', ''),
                        xml_parent_path=rule_data.get('xml_parent_path', ''),
                        xml_child_path=rule_data.get('xml_child_path', ''),
                        required_attributes=rule_data.get('required_attributes', {}),
                        description=rule_data.get('description')
                    )
                    filter_rules.append(filter_rule)
                
                if filter_rules:
                    element_filtering = ElementFiltering(filter_rules=filter_rules)
            
            # Parse field mappings
            mappings = []
            for mapping_data in contract_data.get('mappings', []):
                field_mapping = FieldMapping(
                    xml_path=mapping_data.get('xml_path', ''),
                    target_table=mapping_data.get('target_table', ''),
                    target_column=mapping_data.get('target_column', ''),
                    data_type=mapping_data.get('data_type', ''),
                    data_length=mapping_data.get('data_length'),
                    xml_attribute=mapping_data.get('xml_attribute'),
                    mapping_type=mapping_data.get('mapping_type'),
                    default_value=mapping_data.get('default_value'),
                    expression=mapping_data.get('expression'),
                    description=mapping_data.get('description'),
                    required=mapping_data.get('required'),
                    nullable=mapping_data.get('nullable')
                )
                mappings.append(field_mapping)
            
            # Parse relationship mappings
            relationships = []
            for rel_data in contract_data.get('relationships', []):
                relationship = RelationshipMapping(
                    parent_table=rel_data.get('parent_table', ''),
                    child_table=rel_data.get('child_table', ''),
                    foreign_key_column=rel_data.get('foreign_key_column', ''),
                    xml_parent_path=rel_data.get('xml_parent_path', ''),
                    xml_child_path=rel_data.get('xml_child_path', '')
                )
                relationships.append(relationship)
            
            contract = MappingContract(
                source_table=source_table,
                source_column=source_column,
                xml_root_element=xml_root_element,
                xml_application_path=xml_application_path,
                target_schema=target_schema,  # Contract-driven schema from JSON
                element_filtering=element_filtering,  # Parse element filtering rules
                mappings=mappings,
                relationships=relationships
            )
            
            # Store raw contract data for accessing additional configurations
            contract._raw_data = contract_data
            
            return contract
            
        except Exception as e:
            raise ValidationError(f"Failed to parse mapping contract from {contract_path}: {e}")
    
    def _validate_mapping_contract(self, contract: MappingContract) -> None:
        """
        Validate mapping contract completeness and structure.
        
        Args:
            contract: MappingContract to validate
            
        Raises:
            ValidationError: If contract is invalid or incomplete
        """
        errors = []
        
        # Validate basic contract fields
        if not contract.source_table:
            errors.append("source_table is required")
        if not contract.source_column:
            errors.append("source_column is required")
        if not contract.xml_root_element:
            errors.append("xml_root_element is required")
        
        # Validate field mappings
        if not contract.mappings:
            errors.append("At least one field mapping is required")
        
        for i, mapping in enumerate(contract.mappings):
            if not mapping.xml_path:
                errors.append(f"Field mapping {i}: xml_path is required")
            if not mapping.target_table:
                errors.append(f"Field mapping {i}: target_table is required")
            if not mapping.target_column:
                errors.append(f"Field mapping {i}: target_column is required")
            if not mapping.data_type:
                errors.append(f"Field mapping {i}: data_type is required")
        
        # Validate relationship mappings
        for i, relationship in enumerate(contract.relationships):
            if not relationship.parent_table:
                errors.append(f"Relationship mapping {i}: parent_table is required")
            if not relationship.child_table:
                errors.append(f"Relationship mapping {i}: child_table is required")
            if not relationship.foreign_key_column:
                errors.append(f"Relationship mapping {i}: foreign_key_column is required")
            if not relationship.xml_parent_path:
                errors.append(f"Relationship mapping {i}: xml_parent_path is required")
            if not relationship.xml_child_path:
                errors.append(f"Relationship mapping {i}: xml_child_path is required")
        
        # Check for duplicate target columns within the same table
        table_columns = {}
        for mapping in contract.mappings:
            table_key = mapping.target_table
            if table_key not in table_columns:
                table_columns[table_key] = set()
            
            if mapping.target_column in table_columns[table_key]:
                errors.append(f"Duplicate target column '{mapping.target_column}' in table '{mapping.target_table}'")
            else:
                table_columns[table_key].add(mapping.target_column)
        
        if errors:
            raise ValidationError(f"Mapping contract validation failed: {'; '.join(errors)}")
        
        self.logger.debug("Mapping contract validation passed")
    
    def _parse_sql_scripts(self, sql_script_path: str) -> Dict[str, Dict[str, str]]:
        """
        Parse SQL CREATE TABLE scripts to extract table structure.
        
        Args:
            sql_script_path: Path to SQL script file or directory
            
        Returns:
            Dictionary with table structure information
        """
        full_path = self.paths.base_config_path / sql_script_path
        
        if not full_path.exists():
            self.logger.warning(f"SQL script path not found: {full_path}")
            return {}
        
        sql_content = ""
        
        if full_path.is_file():
            # Single SQL file
            try:
                with open(full_path, 'r', encoding='utf-8') as file:
                    sql_content = file.read()
            except Exception as e:
                self.logger.warning(f"Failed to read SQL script file {full_path}: {e}")
                return {}
        elif full_path.is_dir():
            # Directory of SQL files
            sql_files = list(full_path.glob("*.sql"))
            for sql_file in sql_files:
                try:
                    with open(sql_file, 'r', encoding='utf-8') as file:
                        sql_content += file.read() + "\n"
                except Exception as e:
                    self.logger.warning(f"Failed to read SQL script file {sql_file}: {e}")
                    continue
        
        if not sql_content:
            self.logger.warning(f"No SQL content found in {full_path}")
            return {}
        
        return self._extract_table_structure_from_sql(sql_content)
    
    def _extract_table_structure_from_sql(self, sql_content: str) -> Dict[str, Dict[str, str]]:
        """
        Extract table structure from SQL CREATE TABLE statements.
        
        Args:
            sql_content: SQL content containing CREATE TABLE statements
            
        Returns:
            Dictionary with table structure information
        """
        tables = {}
        
        # Regex pattern to match CREATE TABLE statements
        create_table_pattern = r'CREATE\s+TABLE\s+(?:\[?(\w+)\]?\.)?(?:\[?(\w+)\]?)\s*\((.*?)\)'
        
        matches = re.finditer(create_table_pattern, sql_content, re.IGNORECASE | re.DOTALL)
        
        for match in matches:
            schema_name = match.group(1)
            table_name = match.group(2)
            columns_def = match.group(3)
            
            if not table_name:
                continue
            
            # Parse column definitions
            columns = self._parse_column_definitions(columns_def)
            
            if columns:
                full_table_name = f"{schema_name}.{table_name}" if schema_name else table_name
                tables[full_table_name] = columns
                self.logger.debug(f"Extracted table structure for {full_table_name}: {len(columns)} columns")
        
        return tables
    
    def _parse_column_definitions(self, columns_def: str) -> Dict[str, str]:
        """
        Parse column definitions from CREATE TABLE statement.
        
        Args:
            columns_def: Column definitions string from CREATE TABLE
            
        Returns:
            Dictionary mapping column names to data types
        """
        columns = {}
        
        # Split by comma, but be careful with nested parentheses
        column_lines = []
        current_line = ""
        paren_count = 0
        
        for char in columns_def:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                column_lines.append(current_line.strip())
                current_line = ""
                continue
            
            current_line += char
        
        if current_line.strip():
            column_lines.append(current_line.strip())
        
        # Parse each column definition
        for line in column_lines:
            line = line.strip()
            if not line or line.upper().startswith(('CONSTRAINT', 'PRIMARY KEY', 'FOREIGN KEY', 'INDEX', 'KEY')):
                continue
            
            # Extract column name and type
            parts = line.split()
            if len(parts) >= 2:
                column_name = parts[0].strip('[]')
                column_type = parts[1]
                
                # Handle data types with parameters like VARCHAR(50)
                if len(parts) > 2 and parts[2].startswith('('):
                    column_type += parts[2]
                
                columns[column_name] = column_type
        
        return columns
    
    def _parse_data_model(self, data_model_path: str) -> Dict[str, Dict[str, str]]:
        """
        Parse data model documentation to extract additional table information.
        
        Args:
            data_model_path: Path to data-model.md file
            
        Returns:
            Dictionary with additional table information
        """
        full_path = self.paths.base_config_path / data_model_path
        
        if not full_path.exists():
            self.logger.warning(f"Data model file not found: {full_path}")
            return {}
        
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            self.logger.warning(f"Failed to read data model file {full_path}: {e}")
            return {}
        
        # Simple parsing of markdown tables for table structure
        # This is a basic implementation - could be enhanced for more complex markdown
        tables = {}
        current_table = None
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Look for table headers (markdown style)
            if line.startswith('##') and 'table' in line.lower():
                # Extract table name from header
                table_match = re.search(r'table[:\s]+(\w+)', line, re.IGNORECASE)
                if table_match:
                    current_table = table_match.group(1)
                    tables[current_table] = {}
            
            # Look for column definitions in markdown table format
            elif current_table and '|' in line and not line.startswith('|---'):
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 2:
                    column_name = parts[0]
                    column_type = parts[1] if len(parts) > 1 else 'VARCHAR(255)'
                    tables[current_table][column_name] = column_type
        
        self.logger.debug(f"Parsed data model: {len(tables)} tables found")
        return tables


# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager(base_config_path: Optional[Union[str, Path]] = None) -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        base_config_path: Base path for configuration files. Only used on first call.
        
    Returns:
        Global ConfigManager instance
    """
    global _global_config_manager
    
    if _global_config_manager is None:
        _global_config_manager = ConfigManager(base_config_path)
    
    return _global_config_manager


def reset_config_manager() -> None:
    """Reset the global configuration manager instance."""
    global _global_config_manager
    _global_config_manager = None