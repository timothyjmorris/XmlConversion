"""
Configuration management implementation for the XML Database Extraction system.

This module provides the ConfigurationManager class that handles loading and
validation of mapping contracts, table structures, sample XML documents,
and processing configurations.
"""

import json
import yaml
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from ..interfaces import ConfigurationManagerInterface
from ..models import MappingContract, FieldMapping, RelationshipMapping, ProcessingConfig
from ..exceptions import ConfigurationError, ValidationError


logger = logging.getLogger(__name__)


class ConfigurationManager(ConfigurationManagerInterface):
    """
    Concrete implementation of configuration management for XML extraction system.
    
    This class handles loading and validation of all configuration artifacts
    including mapping contracts, table structures, sample XML documents,
    and processing parameters.
    """
    
    def __init__(self, base_config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            base_config_path: Base path for configuration files. If None, uses current directory.
        """
        self.base_config_path = Path(base_config_path) if base_config_path else Path.cwd()
        self._cached_contracts: Dict[str, MappingContract] = {}
        self._cached_table_structures: Dict[str, Dict[str, Dict[str, str]]] = {}
        self._cached_sample_xml: Dict[str, List[str]] = {}
        
    def load_mapping_contract(self, contract_path: str) -> MappingContract:
        """
        Load mapping contract from JSON or YAML file.
        
        Args:
            contract_path: Path to mapping contract file (relative to base_config_path)
            
        Returns:
            Loaded and validated mapping contract
            
        Raises:
            ConfigurationError: If file cannot be loaded or parsed
            ValidationError: If contract structure is invalid
        """
        # Check cache first
        if contract_path in self._cached_contracts:
            logger.debug(f"Returning cached mapping contract for {contract_path}")
            return self._cached_contracts[contract_path]
        
        full_path = self.base_config_path / contract_path
        
        if not full_path.exists():
            raise ConfigurationError(f"Mapping contract file not found: {full_path}")
        
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                if full_path.suffix.lower() in ['.yaml', '.yml']:
                    contract_data = yaml.safe_load(file)
                elif full_path.suffix.lower() == '.json':
                    contract_data = json.load(file)
                else:
                    raise ConfigurationError(f"Unsupported file format: {full_path.suffix}")
                    
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ConfigurationError(f"Failed to parse mapping contract file {full_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read mapping contract file {full_path}: {e}")
        
        # Parse and validate the contract
        contract = self._parse_mapping_contract(contract_data, contract_path)
        self._validate_mapping_contract(contract)
        
        # Cache the result
        self._cached_contracts[contract_path] = contract
        logger.info(f"Successfully loaded mapping contract from {contract_path}")
        
        return contract
    
    def load_table_structure(self, sql_script_path: str, 
                           data_model_path: str) -> Dict[str, Dict[str, str]]:
        """
        Load table structure from SQL CREATE TABLE scripts and data-model.md.
        
        Args:
            sql_script_path: Path to SQL CREATE TABLE scripts (relative to base_config_path)
            data_model_path: Path to data-model.md file (relative to base_config_path)
            
        Returns:
            Dictionary with table names as keys and column definitions as values
            Format: {table_name: {column_name: column_type, ...}, ...}
            
        Raises:
            ConfigurationError: If files cannot be loaded or parsed
        """
        cache_key = f"{sql_script_path}|{data_model_path}"
        
        # Check cache first
        if cache_key in self._cached_table_structures:
            logger.debug(f"Returning cached table structure for {cache_key}")
            return self._cached_table_structures[cache_key]
        
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
        self._cached_table_structures[cache_key] = table_structure
        logger.info(f"Successfully loaded table structure from {sql_script_path} and {data_model_path}")
        
        return table_structure
    
    def load_sample_xml(self, sample_path: str) -> List[str]:
        """
        Load sample XML documents from directory.
        
        Args:
            sample_path: Path to directory containing sample XML files (relative to base_config_path)
            
        Returns:
            List of sample XML content strings
            
        Raises:
            ConfigurationError: If directory cannot be accessed or no XML files found
        """
        # Check cache first
        if sample_path in self._cached_sample_xml:
            logger.debug(f"Returning cached sample XML for {sample_path}")
            return self._cached_sample_xml[sample_path]
        
        full_path = self.base_config_path / sample_path
        
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
                    logger.debug(f"Loaded sample XML file: {xml_file.name}")
            except Exception as e:
                logger.warning(f"Failed to load sample XML file {xml_file}: {e}")
                continue
        
        if not sample_xml_content:
            raise ConfigurationError(f"Failed to load any sample XML files from {full_path}")
        
        # Cache the result
        self._cached_sample_xml[sample_path] = sample_xml_content
        logger.info(f"Successfully loaded {len(sample_xml_content)} sample XML files from {sample_path}")
        
        return sample_xml_content
    
    def get_processing_config(self) -> ProcessingConfig:
        """
        Get processing configuration with default values.
        
        Returns:
            ProcessingConfig object with default or environment-specific values
        """
        # Default SQL Server Express LocalDB connection string
        default_connection_string = (
            "Driver={ODBC Driver 17 for SQL Server};"
            "Server=(localdb)\\MSSQLLocalDB;"
            "Database=XMLExtraction;"
            "Trusted_Connection=yes;"
        )
        
        # Check for environment variables to override defaults
        batch_size = int(os.environ.get('XML_EXTRACTOR_BATCH_SIZE', 1000))
        parallel_processes = int(os.environ.get('XML_EXTRACTOR_PARALLEL_PROCESSES', 4))
        memory_limit_mb = int(os.environ.get('XML_EXTRACTOR_MEMORY_LIMIT_MB', 512))
        progress_reporting_interval = int(os.environ.get('XML_EXTRACTOR_PROGRESS_INTERVAL', 10000))
        connection_string = os.environ.get('XML_EXTRACTOR_CONNECTION_STRING', default_connection_string)
        enable_validation = os.environ.get('XML_EXTRACTOR_ENABLE_VALIDATION', 'true').lower() == 'true'
        checkpoint_interval = int(os.environ.get('XML_EXTRACTOR_CHECKPOINT_INTERVAL', 50000))
        
        config = ProcessingConfig(
            batch_size=batch_size,
            parallel_processes=parallel_processes,
            memory_limit_mb=memory_limit_mb,
            progress_reporting_interval=progress_reporting_interval,
            sql_server_connection_string=connection_string,
            enable_validation=enable_validation,
            checkpoint_interval=checkpoint_interval
        )
        
        logger.info(f"Generated processing config: batch_size={config.batch_size}, "
                   f"parallel_processes={config.parallel_processes}, "
                   f"memory_limit_mb={config.memory_limit_mb}")
        
        return config
    
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
            # Extract basic contract information
            source_table = contract_data.get('source_table', '')
            source_column = contract_data.get('source_column', '')
            xml_root_element = contract_data.get('xml_root_element', '')
            
            # Parse field mappings
            mappings = []
            for mapping_data in contract_data.get('mappings', []):
                field_mapping = FieldMapping(
                    xml_path=mapping_data.get('xml_path', ''),
                    target_table=mapping_data.get('target_table', ''),
                    target_column=mapping_data.get('target_column', ''),
                    data_type=mapping_data.get('data_type', ''),
                    xml_attribute=mapping_data.get('xml_attribute'),
                    mapping_type=mapping_data.get('mapping_type'),
                    transformation=mapping_data.get('transformation')
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
        
        logger.debug("Mapping contract validation passed")
    
    def validate_key_identifiers(self, xml_content: str, contract: MappingContract) -> bool:
        """
        Validate that required key identifiers (app_id and con_id) can be extracted from XML.
        
        Args:
            xml_content: Raw XML content to validate
            contract: Mapping contract containing key identifier definitions
            
        Returns:
            True if required identifiers are present, False otherwise
        """
        try:
            from xml.etree import ElementTree as ET
            
            # Parse XML content
            root = ET.fromstring(xml_content)
            
            # Check if contract has key_identifiers section
            contract_data = getattr(contract, '_raw_data', {})
            key_identifiers = contract_data.get('key_identifiers', {})
            
            if not key_identifiers:
                logger.warning("No key identifiers defined in mapping contract")
                return True  # Skip validation if not configured
            
            # Validate each required key identifier
            for key_name, key_config in key_identifiers.items():
                if key_config.get('required', False):
                    xml_path = key_config.get('xml_path', '')
                    xml_attribute = key_config.get('xml_attribute', '')
                    
                    # Find element using XPath-like syntax (simplified)
                    element = self._find_xml_element(root, xml_path)
                    
                    if element is None:
                        logger.error(f"Required key identifier '{key_name}' element not found at path: {xml_path}")
                        return False
                    
                    if xml_attribute:
                        if xml_attribute not in element.attrib:
                            logger.error(f"Required key identifier '{key_name}' attribute '{xml_attribute}' not found")
                            return False
                        
                        value = element.attrib[xml_attribute]
                        if not value or value.strip() == '':
                            logger.error(f"Required key identifier '{key_name}' has empty value")
                            return False
            
            logger.debug("Key identifier validation passed")
            return True
            
        except ET.ParseError as e:
            logger.error(f"XML parsing error during key identifier validation: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during key identifier validation: {e}")
            return False
    
    def get_enum_mappings(self, contract_path: str) -> Dict[str, Dict[str, int]]:
        """
        Get enum mappings from the mapping contract.
        
        Args:
            contract_path: Path to mapping contract file
            
        Returns:
            Dictionary of enum mappings
        """
        if contract_path not in self._cached_contracts:
            self.load_mapping_contract(contract_path)
        
        contract = self._cached_contracts[contract_path]
        contract_data = getattr(contract, '_raw_data', {})
        return contract_data.get('enum_mappings', {})
    
    def get_bit_conversions(self, contract_path: str) -> Dict[str, Dict[str, int]]:
        """
        Get bit conversion mappings from the mapping contract.
        
        Args:
            contract_path: Path to mapping contract file
            
        Returns:
            Dictionary of bit conversion mappings
        """
        if contract_path not in self._cached_contracts:
            self.load_mapping_contract(contract_path)
        
        contract = self._cached_contracts[contract_path]
        contract_data = getattr(contract, '_raw_data', {})
        return contract_data.get('bit_conversions', {})
    
    def get_default_values(self, contract_path: str) -> Dict[str, Any]:
        """
        Get default values from the mapping contract.
        
        Args:
            contract_path: Path to mapping contract file
            
        Returns:
            Dictionary of default values
        """
        if contract_path not in self._cached_contracts:
            self.load_mapping_contract(contract_path)
        
        contract = self._cached_contracts[contract_path]
        contract_data = getattr(contract, '_raw_data', {})
        return contract_data.get('default_values', {})
    
    def _find_xml_element(self, root: Any, xpath: str) -> Optional[Any]:
        """
        Find XML element using simplified XPath syntax.
        
        Args:
            root: XML root element
            xpath: Simplified XPath expression
            
        Returns:
            Found element or None
        """
        try:
            # Handle simple XPath expressions like /Provenir/Request
            if xpath.startswith('/'):
                xpath = xpath[1:]  # Remove leading slash
            
            parts = xpath.split('/')
            current = root
            
            for part in parts:
                if not part:
                    continue
                
                # Handle attribute filters like contact[@ac_role_tp_c='PR']
                if '[' in part and ']' in part:
                    element_name = part.split('[')[0]
                    filter_expr = part.split('[')[1].split(']')[0]
                    
                    # Parse attribute filter like @ac_role_tp_c='PR'
                    if '@' in filter_expr and '=' in filter_expr:
                        attr_name = filter_expr.split('=')[0].strip('@').strip()
                        attr_value = filter_expr.split('=')[1].strip("'\"")
                        
                        # Find child element with matching attribute
                        found = False
                        for child in current.findall(element_name):
                            if child.attrib.get(attr_name) == attr_value:
                                current = child
                                found = True
                                break
                        
                        if not found:
                            return None
                    else:
                        # Simple element name with filter (not supported yet)
                        child = current.find(element_name)
                        if child is None:
                            return None
                        current = child
                else:
                    # Simple element name
                    child = current.find(part)
                    if child is None:
                        return None
                    current = child
            
            return current
            
        except Exception as e:
            logger.warning(f"Error parsing XPath '{xpath}': {e}")
            return None
    
    def _parse_sql_scripts(self, sql_script_path: str) -> Dict[str, Dict[str, str]]:
        """
        Parse SQL CREATE TABLE scripts to extract table structure.
        
        Args:
            sql_script_path: Path to SQL script file or directory
            
        Returns:
            Dictionary with table structure information
        """
        full_path = self.base_config_path / sql_script_path
        
        if not full_path.exists():
            logger.warning(f"SQL script path not found: {full_path}")
            return {}
        
        sql_content = ""
        
        if full_path.is_file():
            # Single SQL file
            try:
                with open(full_path, 'r', encoding='utf-8') as file:
                    sql_content = file.read()
            except Exception as e:
                logger.warning(f"Failed to read SQL script file {full_path}: {e}")
                return {}
        elif full_path.is_dir():
            # Directory of SQL files
            sql_files = list(full_path.glob("*.sql"))
            for sql_file in sql_files:
                try:
                    with open(sql_file, 'r', encoding='utf-8') as file:
                        sql_content += file.read() + "\n"
                except Exception as e:
                    logger.warning(f"Failed to read SQL script file {sql_file}: {e}")
                    continue
        
        if not sql_content:
            logger.warning(f"No SQL content found in {full_path}")
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
                logger.debug(f"Extracted table structure for {full_table_name}: {len(columns)} columns")
        
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
        full_path = self.base_config_path / data_model_path
        
        if not full_path.exists():
            logger.warning(f"Data model file not found: {full_path}")
            return {}
        
        try:
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            logger.warning(f"Failed to read data model file {full_path}: {e}")
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
        
        logger.debug(f"Parsed data model: {len(tables)} tables found")
        return tables