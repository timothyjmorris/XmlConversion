"""
Data Mapping Module - Contract-Driven XML to Database Transformation Engine

This module implements the core data transformation engine for converting XML credit application
data into relational database records using a contract-driven architecture. The DataMapper serves
as the central orchestration component in the XML-to-database pipeline, ensuring data integrity
through schema-derived validation and transformation rules.

SCHEMA ISOLATION (Contract-Driven):
    The MappingContract specifies target_schema (e.g., "sandbox" or "dbo"), which drives
    all downstream database operations in MigrationEngine:
    - The DataMapper extracts and provides target_schema to MigrationEngine
    - MigrationEngine uses target_schema for all SQL operations: INSERT, SELECT, DELETE
    - Exception: Source table (app_xml) always remains in [dbo] schema
    - This enables safe isolation between development, testing, and production environments

Key Architectural Components:
- Contract-Driven Validation: Uses schema-derived metadata (nullable/required/default_value) from mapping contracts
- Schema-Aware Output: Provides target_schema from contract to MigrationEngine for qualified table names
- Multi-Stage Transformation: Handles complex mapping types with proper precedence and chaining
- Context-Aware Processing: Builds flattened XML context for calculated field evaluation
- Contact Deduplication: Implements 'last valid element' approach for contact data extraction
- Type-Safe Conversions: Database-specific NULL handling with no default value injection
- Relationship Management: Handles foreign key relationships and data dependencies

Integration Points:
- ConfigManager: Centralized configuration and contract loading
- MappingContract: Source of target_schema and all data mapping rules
- CalculatedFieldEngine: Expression evaluation for derived data
- MigrationEngine: Receives transformed data with target_schema for bulk insertion
- XMLParser: Flattened XML structure processing
- Validation Framework: Pre-flight and post-transformation data integrity checks

The module ensures that only explicitly mapped, validated data reaches the database,
preventing silent data corruption through strict contract compliance and comprehensive
error handling throughout the transformation pipeline.

Mapping Types Supported:
- calculated_field: Evaluates SQL-like expressions with cross-element references
- last_valid_pr_contact: Extracts from the most recent valid PR (Primary Responsible) contact
- curr_address_only: Filters to current (CURR) addresses only, excluding PREV/MAIL addresses
- enum: Maps string values to integer codes using configurable enum mappings
- char_to_bit: Converts Y/N or boolean values to database bit fields
- direct: Simple field extraction with type conversion
- char_to_bit/boolean_to_bit: Converts Y/N or boolean values to 0/1 bit fields
- extract_numeric/numbers_only: Extracts numeric values from formatted strings
- default_getutcdate_if_null: Provides current timestamp for missing datetime fields
- identity_insert: Handles auto-increment fields during bulk inserts

The engine processes XML data through a multi-stage pipeline:
1. Pre-flight validation (app_id and contact requirements)
2. Contract loading with target_schema extraction
3. Contact extraction and deduplication (last valid element approach)
4. Field mapping application with context building for calculated fields
5. Data type transformation with database-specific handling
6. Record creation with intelligent NULL vs default value decisions
7. Prepared output for MigrationEngine with target_schema forwarding
"""

import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from ..interfaces import DataMapperInterface
from ..models import MappingContract, FieldMapping
from ..exceptions import DataMappingError, DataTransformationError
from ..validation.element_filter import ElementFilter
from ..utils import StringUtils
from ..config.config_manager import get_config_manager
from .calculated_field_engine import CalculatedFieldEngine


class DataMapper(DataMapperInterface):
    """
    Core data mapping engine that orchestrates the transformation of XML credit application data
    into relational database records using contract-driven validation and transformation rules.

    This class serves as the central orchestration component in the XML-to-database pipeline,
    implementing a contract-driven architecture where schema-derived metadata ensures data
    integrity throughout the transformation process. It handles the complex orchestration of:

    SCHEMA ISOLATION & TARGET_SCHEMA:
        Each MappingContract specifies target_schema (e.g., "sandbox" or "dbo"):
        - Loaded during initialization from mapping_contract.json
        - Provided to MigrationEngine for all SQL operations
        - Enables complete schema isolation between environments
        - Source table (app_xml) always queries from [dbo]
        - Target tables use [{target_schema}].[table_name] format downstream
        
        This contract-driven approach means:
        - No environment variable pollution
        - Each pipeline is self-contained
        - Testing, staging, and production can coexist safely

    Core Responsibilities:
    - Loading and applying mapping contracts with schema-derived validation rules
    - Extracting target_schema from contract and passing to MigrationEngine
    - Building flattened XML context data for calculated field evaluation
    - Applying multiple mapping types with proper precedence and chaining
    - Contact-specific data extraction with deduplication logic ('last valid element' approach)
    - Type-safe transformations with database-specific NULL handling (no default injection)
    - Progress tracking and error reporting for large-scale data migrations

    The mapper separates concerns between application-level and contact-level data,
    ensuring calculated fields can reference data across the entire XML structure while
    contact fields are properly scoped to their respective contact contexts.

    Contract-Driven Architecture:
    - Uses nullable/required/default_value metadata from schema-derived contracts
    - Validates data integrity against contract specifications before transformation
    - Prevents silent data corruption by excluding unmapped or invalid data
    - Ensures database constraints are respected through pre-flight validation

    Key Design Decisions:
    - Calculated fields use sentinel values to trigger expression evaluation
    - Context data is built once per record to avoid redundant XML parsing
    - Enum mappings return None (excluded from INSERT) when no valid mapping exists,
      preserving data integrity by not fabricating default values
    - Contact extraction uses 'last valid element' approach for duplicate handling
    - Address filtering prioritizes CURR (current) addresses over PREV/MAIL types
    - No default values are injected - only explicitly mapped data is processed
    """
    
    def __init__(self, mapping_contract_path: Optional[str] = None, log_level: str = "ERROR"):
        """
        Initialize the DataMapper with centralized configuration and mapping contract loading.

        Loads enum mappings, bit conversions, and default values from the mapping contract
        JSON file. These configurations enable the various mapping types (enum, char_to_bit,
        calculated_field, etc.) to function properly.

        Args:
            mapping_contract_path: Optional path to mapping contract JSON file.
                                If None, uses path from centralized configuration.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                      Defaults to ERROR for production use to minimize overhead.

        Configuration Loaded:
        - _enum_mappings: Dict mapping enum_type names to value->integer mappings
        - _bit_conversions: Dict for Y/N -> 0/1 and boolean -> bit transformations
        - _validation_rules: Dict of validation constraints (currently unused)

        The initialization is designed to be fault-tolerant - if the mapping contract
        cannot be loaded, empty dictionaries are used as fallbacks.
        """
        self.logger = logging.getLogger(__name__)
        
        # PRODUCTION FIX: Set log level explicitly (default to ERROR for production)
        log_level_value = getattr(logging, log_level.upper(), logging.ERROR)
        self.logger.setLevel(log_level_value)
        
        self._validation_errors = []
        self._transformation_stats = {
            'records_processed': 0,
            'records_successful': 0,
            'records_failed': 0,
            'type_conversions': 0,
            'enum_mappings': 0,
            'bit_conversions': 0,
            'calculated_fields': 0,
            'fallback_values': 0
        }
        
        # Get centralized configuration
        self._config_manager = get_config_manager()
        
        # Use provided path or get from centralized configuration
        if mapping_contract_path:
            self._mapping_contract_path = mapping_contract_path
        else:
            self._mapping_contract_path = self._config_manager.paths.mapping_contract_path
        
        # Load enum mappings and validation rules from contract using centralized config
        # Handle cases where the mapping contract file might not exist during initialization
        try:
            self._enum_mappings = self._config_manager.get_enum_mappings(self._mapping_contract_path)
            self._bit_conversions = self._config_manager.get_bit_conversions(self._mapping_contract_path)
            self.logger.info(f"DataMapper initialized with mapping contract: {self._mapping_contract_path}")
            self.logger.debug(f"Loaded {len(self._enum_mappings)} enum mappings, {len(self._bit_conversions)} bit conversions")
        except Exception as e:
            self.logger.warning(f"Could not load mapping contract configurations during initialization: {e}")
            self._enum_mappings = {}
            self._bit_conversions = {}
        
        self._validation_rules = {}
        
        # Pre-compile regex for datetime correction
        # Note: The 'numbers_only' regex is already cached in StringUtils._regex_cache,
        # so we only need to cache the datetime pattern here
        self._regex_invalid_datetime_seconds = re.compile(r'(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:)(\d{2})(\.\d+)?')
        
        # Build enum_type cache at initialization
        # Pre-compute all column name -> enum_type mappings to avoid repeated pattern matching
        self._enum_type_cache = self._build_enum_type_cache()
        
        # Build contact type configuration cache at initialization
        # Extract valid contact type attribute name and values from contract
        self._valid_contact_type_config = self._get_contact_type_config_from_contract()
    
    def _build_enum_type_cache(self) -> Dict[str, Optional[str]]:
        """
        Pre-build cache of column name -> enum_type mappings.
        
        PERFORMANCE TUNING (Phase 1):
        Instead of calling _determine_enum_type() for every field transformation
        (which does pattern matching on every call), we pre-compute all enum types
        at initialization and cache them.
        
        Returns:
            Dictionary mapping column names to their enum_type identifiers
        """
        cache = {}
        
        # Pattern mappings for enum type detection
        enum_patterns = {
            'status': 'status_enum',
            'process': 'process_enum',
            'app_source': 'app_source_enum',
            'contact_type': 'contact_type_enum',
            'address_type': 'address_type_enum',
            'ownership_type': 'ownership_type_enum',
            'employment_type': 'employment_type_enum',
            'income_type': 'income_type_enum',
            'other_income_type': 'other_income_type_enum',
            'population_assignment': 'population_assignment_enum',
            'decision': 'decision_enum'
        }
        
        # Build cache for all known enum mappings from contract
        for enum_type in self._enum_mappings.keys():
            cache[enum_type] = enum_type
        
        # Pre-populate cache for common column patterns
        common_columns = [
            'app_status', 'process_status', 'contact_type_enum', 'address_type_enum',
            'priority_enum', 'population_assignment_enum', 'decision_enum'
        ]
        
        for column_name in common_columns:
            if column_name not in cache:
                # Apply pattern matching logic to populate cache
                if column_name.endswith('_enum'):
                    cache[column_name] = column_name
                else:
                    for pattern, enum_type in enum_patterns.items():
                        if pattern in column_name:
                            cache[column_name] = enum_type
                            break
        
        self.logger.debug(f"Built enum_type cache with {len(cache)} entries")
        return cache
    
    def _find_filter_rule_by_element_type(self, element_type: str):
        """
        Find filter rule by element_type from contract's element_filtering configuration.
        
        Follows the pattern from element_filter.py for contract-driven rule discovery.
        
        Args:
            element_type: The element type to find (e.g., 'contact', 'address', 'employment')
            
        Returns:
            FilterRule object if found, None otherwise
        """
        try:
            # Load the full mapping contract to access element_filtering rules
            contract = self._config_manager.load_mapping_contract(self._mapping_contract_path)
            if not contract or not hasattr(contract, 'element_filtering') or not contract.element_filtering:
                return None
            
            # Find the filter rule matching the element_type
            for rule in contract.element_filtering.filter_rules:
                if rule.element_type == element_type:
                    return rule
            
            return None
        except Exception as e:
            self.logger.warning(f"Could not load filter rule for element_type '{element_type}': {e}")
            return None
    
    def _get_contact_type_config_from_contract(self) -> tuple:
        """
        Extract contact type configuration from contract's element_filtering rules.
        
        Returns tuple of (attribute_name, valid_values_list) for contact type validation.
        This enables fully product-agnostic contact filtering where both the attribute
        name (e.g., 'ac_role_tp_c' vs 'borrower_type') and valid values can differ.
        
        Pattern mirrors element_filter.py approach: discover attribute names dynamically
        from contract rather than hard-coding them.
        
        Returns:
            Tuple of (attribute_name, valid_values_list)
            Example: ('ac_role_tp_c', ['PR', 'AUTHU'])
            Fallback: ('ac_role_tp_c', ['PR', 'AUTHU']) if not found in contract
        """
        try:
            contact_rule = self._find_filter_rule_by_element_type('contact')
            if not contact_rule:
                self.logger.warning("Contact filter rule not found in contract - using fallback ('ac_role_tp_c', ['PR', 'AUTHU'])")
                return ('ac_role_tp_c', ['PR', 'AUTHU'])
            
            if not hasattr(contact_rule, 'required_attributes'):
                self.logger.warning("Contact filter rule has no required_attributes - using fallback")
                return ('ac_role_tp_c', ['PR', 'AUTHU'])
            
            self.logger.debug(f"Contact rule required_attributes: {contact_rule.required_attributes}")
            
            # Find the attribute that has an array of values (that's the type attribute)
            # In the contract: "ac_role_tp_c": ["PR", "AUTHU"]
            for attr_name, attr_config in contact_rule.required_attributes.items():
                self.logger.debug(f"Checking attribute {attr_name}: {attr_config} (type: {type(attr_config)})")
                if isinstance(attr_config, list) and len(attr_config) > 0:
                    self.logger.debug(f"Extracted contact type config from contract: attribute='{attr_name}', valid_values={attr_config}")
                    return (attr_name, attr_config)
            
            # If no array-valued attribute found, fall back
            self.logger.warning("No contact type attribute with array values found in contract - using fallback")
            return ('ac_role_tp_c', ['PR', 'AUTHU'])
            
        except Exception as e:
            self.logger.warning(f"Error extracting contact type config from contract: {e} - using fallback")
            return ('ac_role_tp_c', ['PR', 'AUTHU'])
    
    def apply_mapping_contract(self, xml_data: Dict[str, Any], 
                             contract: MappingContract,
                             app_id: Optional[str] = None,
                             valid_contacts: Optional[List[Dict[str, Any]]] = None,
                             xml_root=None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Apply mapping contract to transform XML data into relational database records.

        This is the core orchestration method that implements the contract-driven architecture,
        transforming flattened XML data into properly structured database records. The method
        enforces data integrity through schema-derived validation rules and ensures database
        constraints are respected.

        Args:
            xml_data: Flattened XML data dictionary from XMLParser
            contract: MappingContract with schema-derived nullable/required/default_value metadata
            app_id: Application ID (extracted if not provided)
            valid_contacts: Pre-validated contact list (extracted if not provided)
            xml_root: Original XML root for contact/address extraction

        Returns:
            Dictionary mapping table names to lists of record dictionaries ready for bulk insertion

        Contract-Driven Validation Process:
        1. Pre-flight validation: Ensures required app_id and contact identifiers exist
        2. Contact extraction: Applies 'last valid element' deduplication logic
        3. Table grouping: Organizes mappings by target table for efficient processing
        4. Field mapping: Applies contract rules (nullable/required/default_value) per field
        5. Relationship application: Handles foreign key relationships between tables
        6. Calculated field evaluation: Processes expressions using flattened XML context
        7. Data integrity validation: Ensures all records conform to contract specifications

        Key Design Principles:
        - Schema-derived defaults: Uses database schema metadata for field validation
        - No default injection: Only explicitly mapped data is processed (preserves NULL semantics)
        - Contact deduplication: 'Last valid element' approach for duplicate contact handling
        - Type safety: Contract-driven data type transformations with proper NULL handling
        - Relationship integrity: Foreign key constraints validated before insertion
        """
        try:
            self._validation_errors.clear()
            result_tables = {}

            # Extract key identifiers if not provided
            if not app_id:
                app_id = self._extract_app_id(xml_data)
                if not app_id:
                    # If app_id is missing, do not process this XML record
                    # This enforces business rules for required identifiers
                    raise DataMappingError("Could not extract app_id from XML data")

            # Set XML root for contact extraction and CURR address extraction
            if xml_root is not None:
                self._current_xml_root = xml_root
            
            # Store contract for use in element filtering
            self._current_contract = contract

            if valid_contacts is None:
                # PRE-FLIGHT VALIDATION: Must have app_id and at least one con_id or don't process
                if not self._pre_flight_validation(xml_data):
                    # If validation fails, do not process this XML record
                    raise DataMappingError(f"Pre-flight validation failed: {self._validation_errors}")
                # Extract valid contacts using 'last valid element' approach
                valid_contacts = self._extract_valid_contacts(xml_data)
            
            # Group mappings by target table for efficient processing
            table_mappings = self._group_mappings_by_table(contract.mappings)
            self.logger.debug(f"Found {len(table_mappings)} tables to process: {list(table_mappings.keys())}")
            
            # Process each table's mappings
            for table_name, mappings in table_mappings.items():
                try:
                    table_records = self._process_table_mappings(xml_data, mappings, app_id, valid_contacts)
                    if table_records:
                            result_tables[table_name] = table_records
                except Exception as e:
                    # Log and continue processing other tables
                    self.logger.error(f"Failed to process table {table_name}: {e}")
                    self._validation_errors.append(f"Table processing error for {table_name}: {e}")
                    continue
            

            # Handle relationships and foreign keys
            result_tables = self._apply_relationships(result_tables, contract, xml_data, app_id, valid_contacts)


            # NO DEFAULT VALUES APPLIED - only use data from XML mapping
            # This ensures that only explicitly mapped data is inserted, avoiding silent data corruption.

            # Apply calculated fields
            result_tables = self._apply_calculated_fields(result_tables, contract, xml_data)

            # Validate final data integrity
            self._validate_data_integrity(result_tables, contract)

            self._transformation_stats['records_processed'] += 1
            self._transformation_stats['records_successful'] += 1

            return result_tables
            
        except Exception as e:
            self._transformation_stats['records_failed'] += 1
            self.logger.error(f"Failed to apply mapping contract: {e}")
            raise DataMappingError(f"Mapping contract application failed: {e}")
    
    def map_xml_to_database(self, xml_data: Dict[str, Any], app_id: str, valid_contacts: List[Dict[str, Any]], xml_root=None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Map XML data to database format using the loaded mapping contract.

        This method provides a simplified interface for XML-to-database transformation when
        app_id and valid_contacts are already known. It loads the mapping contract using
        centralized configuration and delegates to apply_mapping_contract for the actual
        transformation logic.

        Args:
            xml_data: Flattened XML data dictionary from XMLParser
            app_id: Pre-validated application identifier
            valid_contacts: Pre-validated contact list with deduplication applied
            xml_root: Original XML root for contact/address extraction

        Returns:
            Dictionary mapping table names to lists of record dictionaries for bulk insertion

        Note:
            This method assumes pre-validation of app_id and contacts. For full validation
            including contact extraction and deduplication, use apply_mapping_contract directly.
        """
        # Set the XML root for contact extraction
        if xml_root is not None:
            self._current_xml_root = xml_root
        
        # Load the mapping contract using centralized configuration
        mapping_contract = self._config_manager.load_mapping_contract(self._mapping_contract_path)
        
        # Apply the mapping contract with pre-validated data
        return self.apply_mapping_contract(xml_data, mapping_contract, app_id, valid_contacts)    

    def transform_data_types(self, value: Any, target_type: str) -> Any:
        """Transform value to target data type with comprehensive fallback handling."""
        if not StringUtils.safe_string_check(value):
            return None  # Return None to exclude from INSERT - no default values injected
        
        try:
            # Handle string types
            if target_type == 'string':
                return str(value)
            
            # Handle numeric types
            elif target_type in ['int', 'smallint', 'bigint', 'tinyint']:
                return self._transform_to_integer(value)
            
            elif target_type == 'decimal':
                return self._transform_to_decimal(value, target_type)
            
            elif target_type == 'float':
                return float(value)
            
            # Handle date/time types
            elif target_type in ['datetime', 'smalldatetime', 'date']:
                return self._transform_to_datetime(value, target_type)
            
            # Handle bit type
            elif target_type == 'bit':
                return self._transform_to_bit(value)
            
            # Handle boolean
            elif target_type == 'boolean':
                return self._transform_to_boolean(value)
            
            else:
                # Default to string conversion
                return str(value)
                
        except Exception as e:
            self.logger.warning(f"Type conversion failed for value '{value}' to type '{target_type}': {e}")
            # Use fallback value (None) to exclude from INSERT
            return self._get_fallback_value(value, target_type)

    def _extract_app_id(self, xml_data: Dict[str, Any]) -> Optional[str]:
        """Extract app_id from XML data (compatible with XMLParser flat structure)."""
        try:
            # Extract app_id from both flat and nested XML structures for compatibility
            # Try XMLParser flat structure first: /Provenir/Request with attributes
            request_path = '/Provenir/Request'
            if request_path in xml_data:
                request_element = xml_data[request_path]
                if isinstance(request_element, dict) and 'attributes' in request_element:
                    attributes = request_element['attributes']
                    # Check for lowercase 'id' due to case normalization in XML parser
                    if 'id' in attributes:
                        return str(attributes['id'])
                    # Fallback to uppercase for backward compatibility
                    elif 'ID' in attributes:
                        return str(attributes['ID'])
            
            # Fallback to nested dictionary structure for backward compatibility
            if 'Provenir' in xml_data and 'Request' in xml_data['Provenir']:
                request = xml_data['Provenir']['Request']
                if isinstance(request, dict) and 'ID' in request:
                    return str(request['ID'])
                elif isinstance(request, list) and len(request) > 0 and 'ID' in request[0]:
                    return str(request[0]['ID'])
            
            return None
        except Exception as e:
            self.logger.warning(f"Failed to extract app_id: {e}")
            return None

    def _pre_flight_validation(self, xml_data: Dict[str, Any]) -> bool:
        """
        Pre-flight validation: Must have app_id and at least one valid contact.
        
        Requirements:
        - Must have /Provenir/Request/@ID (app_id)
        - Must have at least one contact with BOTH con_id AND ac_role_tp_c
        
        If these don't exist, don't process the XML at all.
        """
        # Check for required app_id at /Provenir/Request/@ID
        app_id = self._extract_app_id(xml_data)
        if not app_id:
            self._validation_errors.append("CRITICAL: Missing /Provenir/Request/@ID - cannot process XML")
            return False
        
        # Check for valid contacts - if none found, use graceful degradation
        valid_contacts = self._extract_valid_contacts(xml_data)
        if not valid_contacts:
            self.logger.warning(f"DATA QUALITY WARNING: No valid contacts found for app_id {app_id} - processing with graceful degradation (contact tables will be skipped)")
            # Continue processing - don't return False
        
        contact_status = f"{len(valid_contacts)} valid contacts" if valid_contacts else "graceful degradation (no contacts)"
        self.logger.info(f"Pre-flight validation passed: app_id={app_id}, {contact_status}")
        return True

    def _extract_valid_contacts(self, xml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract valid contacts using 'last valid element' logic:
        - Only contacts with BOTH con_id AND contact_type_attribute are considered
        - Contact types are validated against contract's element_filtering rules (contract-driven)
        - Max of one contact per con_id is returned (last valid element wins)
        - This function also deduplicates contacts by con_id across types (to prevent SQL errors)
        Returns a list of contacts which can safely be inserted.
        """
        try:
            # Get contact type configuration from contract (cached at init)
            contact_type_attr, valid_contact_types = self._valid_contact_type_config
            
            contacts = self._navigate_to_contacts(xml_data)
            self.logger.info(f"Contacts found: {[(c.get('con_id', '').strip(), c.get('first_name', ''), c.get(contact_type_attr, '')) for c in contacts if isinstance(c, dict)]}")

            # Only consider contacts with required fields: con_id and contact_type_attribute
            # Note: Using dynamic contact_type_attr from contract instead of hard-coded 'ac_role_tp_c'
            filtered_contacts = []
            for contact in contacts:
                if not isinstance(contact, dict):
                    continue
                con_id = contact.get('con_id', '').strip()
                contact_type_value = contact.get(contact_type_attr, '').strip()
                if not con_id or not contact_type_value:
                    continue
                # CONTRACT-DRIVEN: Validate against valid types from element_filtering rules
                if contact_type_value not in valid_contact_types:
                    continue
                filtered_contacts.append(contact)

            # For each con_id, prefer PR contact over AUTHU (business rule: PR takes precedence)
            # NOTE: This precedence logic will be made contract-driven in Task 2
            con_id_map = {}
            for contact in filtered_contacts:
                con_id = contact.get('con_id', '').strip()
                contact_type_value = contact.get(contact_type_attr, '').strip()
                if con_id not in con_id_map:
                    con_id_map[con_id] = contact
                else:
                    # TEMPORARY: Hard-coded PR precedence - will be contract-driven in Task 2
                    # If current contact is PR, always prefer it over existing
                    if contact_type_value == 'PR':
                        con_id_map[con_id] = contact
                    # If existing is not PR and current is AUTHU, keep the latest AUTHU
                    elif con_id_map[con_id].get(contact_type_attr, '').strip() != 'PR':
                        con_id_map[con_id] = contact
                    # If existing is PR, keep it (don't overwrite with AUTHU)

            valid_contacts = list(con_id_map.values())
            return valid_contacts
        except Exception as e:
            self.logger.warning(f"Failed to extract valid contacts: {e}")
            return []

    def _navigate_to_contacts(self, xml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Navigate to contact elements in XML structure.
        
        Since the XMLParser only returns the last element for each path, we need to
        parse contacts directly from the XML root if available.
        """
        contacts = []
        
        try:
            # First, try to get contacts from the XMLParser structure
            for path, element in xml_data.items():
                # Find contact elements (not child elements like contact_address)
                if (path.endswith('/contact') and 
                    isinstance(element, dict) and 
                    element.get('tag') == 'contact' and
                    'attributes' in element):
                    
                    # Convert XMLParser format to expected format
                    contact_dict = element['attributes'].copy()
                    contacts.append(contact_dict)
            
            # If we have the XML root available, parse all contacts directly
            if hasattr(self, '_current_xml_root') and self._current_xml_root is not None:
                contacts = self._parse_all_contacts_from_root(self._current_xml_root)
            
            return contacts
            
        except Exception as e:
            self.logger.warning(f"Error navigating to contacts: {e}")
            return []

    def _parse_all_contacts_from_root(self, xml_root) -> List[Dict[str, Any]]:
        """
        Parse all contact elements directly from XML root using XPath.
        
        This bypasses the XMLParser's limitation of only keeping the last element
        for each path, allowing us to get all contacts.
        """
        contacts = []
        try:
            # Use XPath to find all contact elements
            contact_elements = xml_root.xpath('.//contact[@ac_role_tp_c]')
            for contact_elem in contact_elements:
                # Extract all attributes as a dictionary
                contact_dict = dict(contact_elem.attrib)

                # Extract child employment elements
                employment_elems = contact_elem.xpath('./contact_employment')
                contact_dict['contact_employment'] = [dict(emp.attrib) for emp in employment_elems]

                # Extract child address elements
                address_elems = contact_elem.xpath('./contact_address')
                contact_dict['contact_address'] = [dict(addr.attrib) for addr in address_elems]

                contacts.append(contact_dict)

            self.logger.debug(f"Parsed {len(contacts)} contacts directly from XML root")
            return contacts
        except Exception as e:
            self.logger.warning(f"Error parsing contacts from XML root: {e}")
            return []
    def _get_attribute_case_insensitive(self, attributes: Dict[str, Any], target_attr: str) -> Any:
        """
        Get attribute value using case-insensitive lookup.
        
        PERFORMANCE TUNING (Phase 1):
        Optimized from O(n) iteration to O(1) lookup by creating a lowercase-to-original
        mapping. For typical XML attributes (< 50), the iteration is negligible, but in
        hot loops with 10,000+ field transformations, this adds up.
        
        For further optimization, consider caching this mapping at the record level.
        
        Args:
            attributes: Dictionary of attributes
            target_attr: Target attribute name (from mapping contract)
            
        Returns:
            Attribute value if found, None otherwise
        """
        # Try direct lookup first (most common case - attribute names match exactly)
        if target_attr in attributes:
            return attributes[target_attr]
        
        # Fallback to case-insensitive lookup (only needed for mismatched cases)
        target_lower = target_attr.lower()
        for attr_key, attr_value in attributes.items():
            if attr_key.lower() == target_lower:
                return attr_value
        return None

    def _extract_value_from_xml(self, xml_data: Dict[str, Any], 
                               mapping: FieldMapping, context_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Extract value from XML data using XPath-like navigation with context-aware field resolution.

        This method handles the complex logic of extracting values from the flattened XML structure,
        with special handling for different mapping types and context scenarios. The XML data is
        pre-flattened by the XMLParser into a dictionary structure where keys are XPath-like paths.

        Special Cases Handled:
        - calculated_field: Returns sentinel value to trigger expression evaluation instead of XML extraction
        - last_valid_pr_contact: Delegates to specialized contact extraction method
        - contact_base application attributes: When context_data is available, extracts app-level data
          for threading into contact records (e.g., app_id, application dates)
        - Contact-specific mappings: When context_data provided, navigates within contact scope
          instead of global XML structure

        Context Data Usage:
        - For contact-level mappings: context_data contains the specific contact's data
            # Example pattern (contact type attribute is contract-driven):
            contact_type_attr, valid_types = self._valid_contact_type_config
            seen_con_ids = set()
            for contact in reversed(contacts):
                if isinstance(contact, dict):
                    con_id = contact.get('con_id', '').strip()
                    contact_type = contact.get(contact_type_attr, '').strip()
                    if contact_type in valid_types and con_id and con_id not in seen_con_ids:
                        valid_contacts.insert(0, contact)
                        seen_con_ids.add(con_id)

        Returns:
            Extracted value or None if not found. For calculated fields, returns sentinel string.
        """
        try:
            # Handle special mapping types that require custom extraction logic
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type == 'last_valid_pr_contact':
                return self._extract_from_last_valid_pr_contact(mapping)
            
            # For calculated fields, skip XML extraction entirely - return sentinel value to trigger expression evaluation
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type and 'calculated_field' in mapping.mapping_type:
                return "__CALCULATED_FIELD_SENTINEL__"
            
            # Handle application-level attributes that need to be threaded to contact_base
            if (mapping.target_table == 'contact_base' and 
                mapping.xml_path == '/Provenir/Request/CustData/application' and
                context_data is not None):
                # Extract from application level, not contact level
                app_path = '/Provenir/Request/CustData/application'
                if app_path in xml_data and isinstance(xml_data[app_path], dict):
                    app_element = xml_data[app_path]
                    if 'attributes' in app_element and mapping.xml_attribute in app_element['attributes']:
                        return app_element['attributes'][mapping.xml_attribute]
                return None
            
            # Initialize current_data to avoid UnboundLocalError
            current_data = None

            # Handle contact-specific mappings with context_data when available
            if context_data and ('contact' in mapping.xml_path or 
                               'contact_address' in mapping.xml_path or 
                               'contact_employment' in mapping.xml_path):
                # For contact_address and contact_employment, context_data contains {'attributes': {...}}
                # BUT skip this for special mapping types that have their own handling
                if (('contact_address' in mapping.xml_path or 'contact_employment' in mapping.xml_path) and 
                    mapping.mapping_type not in ['curr_address_only', 'last_valid_pr_contact']):
                    # Extract directly from context attributes
                    if mapping.xml_attribute and 'attributes' in context_data:
                        attributes = context_data['attributes']
                        value = self._get_attribute_case_insensitive(attributes, mapping.xml_attribute)
                        if value is not None:
                            return value
                    return None
                elif 'contact' in mapping.xml_path:
                    # Direct contact attributes can use context_data
                    current_data = context_data
                    # Skip to the part after 'contact' in the path
                    path_parts = mapping.xml_path.strip('/').split('/')
                    contact_index = -1
                    for i, part in enumerate(path_parts):
                        if 'contact' in part:
                            contact_index = i
                            break
                    
                    if contact_index >= 0 and contact_index < len(path_parts) - 1:
                        # Navigate from contact element onwards
                        remaining_parts = path_parts[contact_index + 1:]
                        for part in remaining_parts:
                            if isinstance(current_data, dict) and part in current_data:
                                current_data = current_data[part]
                            else:
                                current_data = None
                                break
                    
                    # If we successfully navigated using context, return early
                    if current_data is not None:
                        # Extract attribute if specified (case-insensitive)
                        if mapping.xml_attribute and isinstance(current_data, dict):
                            value = self._get_attribute_case_insensitive(current_data, mapping.xml_attribute)
                            if value is not None:
                                return value
                            elif 'attributes' in current_data:
                                value = self._get_attribute_case_insensitive(current_data['attributes'], mapping.xml_attribute)
                                if value is not None:
                                    return value
                            # Attribute not found in contact - return None instead of entire contact object
                            return None
                        return current_data
            else:
                # Standard navigation from root for non-contact mappings (or when context_data is not available)
                # First try direct path lookup (for flat XML structure)
                full_path = mapping.xml_path
                if full_path in xml_data:
                    current_data = xml_data[full_path]
                else:
                    # Fallback to nested navigation
                    current_data = xml_data
                    path_parts = mapping.xml_path.strip('/').split('/')
                    
                    for i, part in enumerate(path_parts):
                        if isinstance(current_data, dict):
                            if part in current_data:
                                current_data = current_data[part]
                            else:
                                current_data = None
                                break
                        elif isinstance(current_data, list) and len(current_data) > 0:
                            # Handle list elements - take first matching item
                            found = False
                            for item in current_data:
                                if isinstance(item, dict) and part in item:
                                    current_data = item[part]
                                    found = True
                                    break
                            if not found:
                                current_data = None
                                break
                        else:
                            current_data = None
                            break
            
            # Extract attribute if specified (case-insensitive)
            if mapping.xml_attribute and current_data is not None:
                if isinstance(current_data, dict):
                    # First try direct attribute access (case-insensitive)
                    value = self._get_attribute_case_insensitive(current_data, mapping.xml_attribute)
                    if value is not None:
                        return value
                    # Then try attributes dictionary (XMLParser structure)
                    elif 'attributes' in current_data:
                        value = self._get_attribute_case_insensitive(current_data['attributes'], mapping.xml_attribute)
                        if value is not None:
                            return value
                elif isinstance(current_data, list):
                    for item in current_data:
                        if isinstance(item, dict):
                            value = self._get_attribute_case_insensitive(item, mapping.xml_attribute)
                            if value is not None:
                                return value
                            elif 'attributes' in item:
                                value = self._get_attribute_case_insensitive(item['attributes'], mapping.xml_attribute)
                                if value is not None:
                                    return value
                return None
            
            return current_data
            
        except Exception as e:
            self.logger.warning(f"Failed to extract value from XML path {mapping.xml_path}: {e}")
            return None

    def _apply_field_transformation(self, value: Any, mapping: FieldMapping, context_data: Optional[Dict[str, Any]] = None) -> Any:
        """Apply field-specific transformations with support for chained mapping types."""
        
        # PERFORMANCE TUNING (Phase 1): Use pre-parsed mapping_type list directly
        # FieldMapping.__post_init__() already normalizes mapping_type to a list,
        # so we avoid redundant string parsing here
        mapping_types = mapping.mapping_type if mapping.mapping_type else []
        
        if mapping_types:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Applying {len(mapping_types)} mapping type(s) for {mapping.target_column}: {mapping_types}")
        else:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"No mapping_type for {mapping.target_column}")

        current_value = value

        # Apply mapping types if present
        if mapping_types:
            for i, mapping_type in enumerate(mapping_types):
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Applying mapping type {i+1}/{len(mapping_types)}: '{mapping_type}' to value: {current_value}")
                try:
                    current_value = self._apply_single_mapping_type(current_value, mapping_type, mapping, context_data)
                    if self.logger.isEnabledFor(logging.DEBUG):
                        self.logger.debug(f"Result after '{mapping_type}': {current_value}")
                    if current_value is None and mapping_type not in ['enum', 'default_getutcdate_if_null']:
                        if self.logger.isEnabledFor(logging.DEBUG):
                            self.logger.debug(f"Breaking transformation chain at '{mapping_type}' due to None value")
                        break
                except Exception as e:
                    self.logger.warning(f"Transformation failed at step '{mapping_type}' for {mapping.target_column}: {e}")
                    raise DataTransformationError(
                        f"Failed to transform value '{current_value}' using mapping type '{mapping_type}' for field {mapping.target_column}",
                        field_name=mapping.target_column,
                        source_value=str(current_value),
                        target_type=mapping.data_type
                    )
        else:
            # If no mapping types, apply standard data type transformation
            if not StringUtils.safe_string_check(current_value):
                default_value = self._get_default_for_mapping(mapping)
                if default_value is not None:
                    current_value = default_value
                else:
                    # Handle decimal transformation with contract-driven precision
                    if mapping.data_type == 'decimal' and mapping.data_length is not None:
                        current_value = self._transform_to_decimal_with_precision(current_value, mapping.data_length)
                    else:
                        current_value = self.transform_data_types(current_value, mapping.data_type)
            else:
                # Auto-apply extract_numeric for integer types if value contains non-numeric characters
                if (mapping.data_type in ['int', 'smallint', 'bigint', 'tinyint'] and 
                    isinstance(current_value, str) and 
                    not current_value.strip().isdigit()):
                    # Try to extract numeric value automatically for integer fields
                    # Use decimal-preserving extraction so "36.50" stays as 36.5 (then rounds to 36)
                    extracted = self._extract_numeric_value_preserving_decimals(current_value)
                    if extracted is not None:
                        self.logger.debug(f"Auto-extracted numeric value for {mapping.target_column}: '{current_value}' -> {extracted}")
                        current_value = extracted
                
                # Handle decimal transformation with contract-driven precision
                if mapping.data_type == 'decimal' and mapping.data_length is not None:
                    current_value = self._transform_to_decimal_with_precision(current_value, mapping.data_length)
                else:
                    current_value = self.transform_data_types(current_value, mapping.data_type)

        # ENFORCE contract-driven truncation for ALL string fields, regardless of mapping type chain
        if current_value is not None and isinstance(current_value, str):
            # Apply numbers_only if specified (guaranteed after all mapping types)
            if 'numbers_only' in mapping_types:
                # PERFORMANCE TUNING (Phase 1): Use cached regex from StringUtils
                current_value = StringUtils.extract_numbers_only(current_value)
            current_value = current_value.strip()
            max_length = getattr(mapping, 'data_length', None)
            if max_length is not None:
                if isinstance(max_length, str):
                    try:
                        max_length = int(max_length)
                    except Exception:
                        self.logger.debug(f"Invalid data_length for {mapping.target_column}: {max_length}")
                        max_length = None
                if max_length is not None and len(current_value) > max_length:
                    original_value = current_value
                    current_value = current_value[:max_length]
                    self.logger.debug(f"Truncated value for {mapping.target_column}: '{original_value}' -> '{current_value}' (max_length={max_length})")
            current_value = current_value.strip()
        return current_value

    def _apply_single_mapping_type(self, value: Any, mapping_type: str, mapping: FieldMapping, context_data: Optional[Dict[str, Any]] = None) -> Any:
        """
        Apply a single mapping type transformation with contract-driven validation.

        This method implements the core transformation logic for individual mapping types,
        handling special cases like contact-specific extractions, enum mappings, and
        schema-derived defaults. It ensures data integrity by respecting contract
        specifications for nullable/required fields.

        Args:
            value: Input value to transform
            mapping_type: Type of transformation to apply (enum, char_to_bit, calculated_field, etc.)
            mapping: FieldMapping with contract metadata (nullable/required/default_value)
            context_data: XML context for calculated fields and contact-specific extractions

        Returns:
            Transformed value or None (excluded from INSERT to preserve NULL semantics)

        Mapping Type Handling:
        - last_valid_pr_contact: Extracts from last valid primary contact
        - curr_address_only: Filters to current address only
        - enum: Maps string values to integer codes (None if no mapping exists)
        - char_to_bit: Converts Y/N to 0/1
        - calculated_field: Evaluates expressions using XML context
        - default_getutcdate_if_null: Provides current timestamp for missing dates
        - extract_numeric: Extracts numeric values from strings
        - Schema-derived defaults: Applied only when explicitly defined in contract

        Contract-Driven Design:
        - No default injection for missing data (preserves NULL semantics)
        - Type-safe transformations with proper error handling
        - Context-aware processing for calculated and contact-specific fields
        """
        
        # Handle special mapping types that don't depend on input value
        if mapping_type == 'last_valid_pr_contact':
            # Extract value from the last valid PR contact
            self.logger.info(f"Processing last_valid_pr_contact mapping for {mapping.target_column}")
            result = self._extract_from_last_valid_pr_contact(mapping)
            if result is not None:
                self.logger.info(f"last_valid_pr_contact returned: {result} for {mapping.target_column}")
                # Apply data type transformation to the extracted value
                return self.transform_data_types(result, mapping.data_type)
            self.logger.info(f"last_valid_pr_contact returned None for {mapping.target_column}")
            return None
        
        elif mapping_type == 'curr_address_only':
            self.logger.debug(f"Processing curr_address_only mapping for {mapping.target_column}")
            # If context_data is provided, use XML extraction logic
            if context_data is not None:
                result = self._extract_from_curr_address_only(mapping, context_data)
            else:
                # If called with a raw value, treat as direct transformation
                result = value
            if result is not None:
                self.logger.debug(f"curr_address_only returned: {result}")
                return result
            self.logger.debug(f"curr_address_only returned None for {mapping.target_column}")
            return None
        
        # Handle calculated fields with sentinel value - always evaluate expression
        elif mapping_type == 'calculated_field' and value == "__CALCULATED_FIELD_SENTINEL__":
            return self._apply_calculated_field_mapping(None, mapping, context_data)
        
        # Handle enum mappings specially - always call enum mapper even with None/empty values
        elif mapping_type == 'enum':
            result = self._apply_enum_mapping(value, mapping)
            self._transformation_stats['enum_mappings'] += 1
            return result
        
        # Handle default_getutcdate_if_null specially - it provides defaults for empty/null values
        elif mapping_type == 'default_getutcdate_if_null':
            if not StringUtils.safe_string_check(value):
                import datetime
                utc_now = datetime.datetime.now(datetime.UTC)
                self.logger.debug(f"Applying default_getutcdate_if_null for {mapping.target_column}: {value} -> {utc_now}")
                return utc_now
            # Apply data type transformation to the existing value
            return self.transform_data_types(value, mapping.data_type)
        
        # CRITICAL FIX: Handle char_to_bit and boolean_to_bit BEFORE the empty value check
        # These need to process empty/null values using the bit conversion mappings
        elif mapping_type == 'char_to_bit':
            return self._apply_bit_conversion(value)
        elif mapping_type == 'boolean_to_bit':
            return self._apply_boolean_to_bit_conversion(value)
        
        # Handle other mapping types that require a valid input value
        elif not StringUtils.safe_string_check(value):
            # Try to get default value for this mapping
            default_value = self._get_default_for_mapping(mapping)
            if default_value is not None:
                return default_value
            return None
        elif mapping_type == 'calculated_field':
            return self._apply_calculated_field_mapping(value, mapping, context_data)
        elif mapping_type in ['extract_numeric', 'numbers_only']:
            # Extract numeric values from strings BEFORE type transformation
            extracted_value = self._extract_numeric_value(value)
            return self.transform_data_types(extracted_value, mapping.data_type)
        else:
            # Unknown mapping type - apply standard data type transformation
            self.logger.debug(f"Unknown mapping type '{mapping_type}' for {mapping.target_column}, applying standard data type transformation")
            return self.transform_data_types(value, mapping.data_type)

    def _apply_enum_mapping(self, value: Any, mapping: FieldMapping) -> int:
        """
        Apply enum mapping transformation, converting string values to integer codes.

        This method implements a deliberate design choice in the contract-driven architecture:
        when no valid enum mapping exists for a value, it returns None instead of a fabricated
        default. This causes the column to be excluded from the INSERT statement, leaving the
        database column NULL and preserving data integrity.

        Contract-Driven Design Rationale:
        - Schema-derived validation: Uses contract metadata for enum type determination
        - NULL preservation: No default injection maintains distinction between missing data and defaults
        - Data integrity: Prevents silent corruption by excluding unmapped enum values
        - Database constraints: Respects nullable/required field specifications from schema

        The mapping process:
        1. Convert input value to string and strip whitespace
        2. Determine enum_type from column name using pattern matching
        3. Look up the enum_type in _enum_mappings (loaded from contract configuration)
        4. Try exact match first, then case-insensitive match
        5. Use default value from enum map if available (key='')
        6. Return None if no valid mapping found (column excluded from INSERT)

        Args:
            value: Input value to be mapped (typically string from XML)
            mapping: Field mapping containing target_column and contract metadata

        Returns:
            Integer enum value if mapping found, None otherwise (excludes column from INSERT)
        """
        # CRITICAL FIX: Check if a contact object is being passed instead of a simple value
        if isinstance(value, dict) and 'con_id' in value and 'ac_role_tp_c' in value:
            self.logger.warning(f"Contact object passed to enum mapping for {mapping.target_column} - returning None to exclude column")
            return None
        
        str_value = str(value).strip() if value is not None else ''

        # Determine enum type from target column name
        enum_type = self._determine_enum_type(mapping.target_column)
        
        # Debug logging
        self.logger.debug(f"Enum mapping: value='{str_value}', column={mapping.target_column}, enum_type={enum_type}")
        self.logger.debug(f"Available enum types: {list(self._enum_mappings.keys())}")
        
        # Only apply enum mapping if a valid enum_type is detected for this column
        if enum_type and enum_type in self._enum_mappings:
            enum_map = self._enum_mappings[enum_type]
            self.logger.debug(f"Enum map for {enum_type}: {enum_map}")
            # Try exact match first
            if str_value in enum_map:
                result = enum_map[str_value]
                self.logger.debug(f"Enum mapping success: '{str_value}' -> {result}")
                return result
            
            # Try case-insensitive match
            for key, enum_value in enum_map.items():
                if key.upper() == str_value.upper():
                    self.logger.debug(f"Enum mapping success (case-insensitive): '{str_value}' -> {enum_value}")
                    return enum_value
            
            # Use default value if available
            if '' in enum_map:
                self.logger.warning(f"Using default enum value for unmapped '{str_value}' in {enum_type}")
                return enum_map['']
        
        # CRITICAL FIX (DQ3): Check if this is a required (NOT NULL) enum field
        is_required = not getattr(mapping, 'nullable', True)
        
        if is_required:
            # Required enum with no valid mapping - this is an error
            if hasattr(mapping, 'default_value') and mapping.default_value is not None:
                self.logger.warning(f"Using contract default for required enum {mapping.target_column}: {mapping.default_value}")
                return mapping.default_value
            else:
                # FAIL FAST: Required enum field with no valid mapping and no default
                raise DataMappingError(
                    f"Required enum field '{mapping.target_column}' has no valid "
                    f"mapping for value '{str_value}' (enum_type: {enum_type}) and no default_value defined. "
                    f"Cannot proceed with NULL for NOT NULL enum column."
                )
        else:
            # Nullable enum - returning None is correct (database sets NULL)
            # This preserves data integrity by distinguishing between missing data and defaults
            self.logger.info(f"No enum mapping found for value '{str_value}' in column {mapping.target_column}, enum_type={enum_type} - excluding column (nullable)")
            return None

    def _determine_enum_type(self, column_name: str) -> Optional[str]:
        """
        Determine the enum type name for a given column based on naming patterns.

        PERFORMANCE TUNING (Phase 1):
        This method now uses a pre-built cache (_enum_type_cache) to avoid repeated
        pattern matching on every field transformation. Cache is built once at
        initialization and used for O(1) lookups during data mapping.

        This method maps database column names to enum type identifiers that are used
        as keys in the _enum_mappings dictionary. The mapping uses common patterns
        found in credit application data:

        Direct Mappings (column_name matches enum_type):
        - Columns ending in '_enum' use the column name directly

        Pattern-Based Mappings:
        - 'status' → 'status_enum' (app_status, process_status, etc.)
        - 'process' → 'process_enum'
        - 'app_source' → 'app_source_enum'
        - 'contact_type' → 'contact_type_enum'
        - 'address_type' → 'address_type_enum'
        - etc.

        This indirection allows the same enum mapping to be reused across multiple
        columns that represent the same conceptual type (e.g., multiple status columns
        can all use the 'status_enum' mapping).

        Args:
            column_name: Database column name to map to enum type

        Returns:
            Enum type name (key in _enum_mappings) or None if no pattern matches
        """
        # PERFORMANCE: Check cache first (O(1) lookup)
        if hasattr(self, '_enum_type_cache') and column_name in self._enum_type_cache:
            return self._enum_type_cache[column_name]
        
        # Fallback to direct pattern matching if cache miss (for dynamically-added columns)
        if column_name.endswith('_enum'):
            return column_name
        
        # Map common column patterns to enum types
        enum_mappings = {
            'status': 'status_enum',
            'process': 'process_enum',
            'app_source': 'app_source_enum',
            'contact_type': 'contact_type_enum',
            'address_type': 'address_type_enum',
            'ownership_type': 'ownership_type_enum',
            'employment_type': 'employment_type_enum',
            'income_type': 'income_type_enum',
            'other_income_type': 'other_income_type_enum',
            'population_assignment': 'population_assignment_enum',
            'decision': 'decision_enum'
        }
        
        for pattern, enum_type in enum_mappings.items():
            if pattern in column_name:
                # Cache this result for future lookups
                if hasattr(self, '_enum_type_cache'):
                    self._enum_type_cache[column_name] = enum_type
                return enum_type
        
        # Not found - cache the miss for future lookups
        if hasattr(self, '_enum_type_cache'):
            self._enum_type_cache[column_name] = None
        return None
        
        return None 
    
    def _apply_calculated_field_mapping(self, value: Any, mapping: FieldMapping, context_data: Optional[Dict[str, Any]] = None) -> Any:
        """Apply calculated field mapping using expressions."""
        try:
            # Get the expression from the mapping
            expression = mapping.expression
            if not expression:
                self.logger.warning(f"No expression found for calculated field: {mapping.target_column}")
                return None
            
            # Initialize calculated field engine if not already done
            if not hasattr(self, '_calculated_field_engine'):
                self._calculated_field_engine = CalculatedFieldEngine()
            
            # Get the element data from context_data
            # For calculated fields, always use the full context_data since they need cross-element references
            element_data = context_data if context_data else {}
            
            # For address/employment records, the attributes are nested under 'attributes' key
            # Flatten them to the top level for calculated field evaluation
            if 'attributes' in element_data:
                # Create a flattened version with attributes at top level
                flattened_data = dict(element_data)  # Copy the context_data
                flattened_data.update(element_data['attributes'])  # Add attributes at top level
                element_data = flattened_data
            
            # Evaluate the expression using the element data
            result = self._calculated_field_engine.evaluate_expression(expression, element_data, mapping.target_column)
            
            # Debug logging for specific calculated fields
            if mapping.target_column in ['cb_score_factor_code_1', 'cb_score_factor_code_2']:
                self.logger.debug(f"DEBUG: Calculated field '{mapping.target_column}' expression evaluation completed with result: {repr(result)}")
                self.logger.debug(f"DEBUG: Context data keys: {list(element_data.keys()) if element_data else 'None'}")
                if 'adverse_actn1_type_cd' in element_data:
                    self.logger.debug(f"DEBUG: adverse_actn1_type_cd = '{element_data.get('adverse_actn1_type_cd')}'")
                if 'adverse_actn2_type_cd' in element_data:
                    self.logger.debug(f"DEBUG: adverse_actn2_type_cd = '{element_data.get('adverse_actn2_type_cd')}'")
                if 'app_receive_date' in element_data:
                    self.logger.debug(f"DEBUG: app_receive_date = '{element_data.get('app_receive_date')}'")
                if 'population_assignment' in element_data:
                    self.logger.debug(f"DEBUG: population_assignment = '{element_data.get('population_assignment')}'")
                                
            self.logger.debug(f"Calculated field expression '{expression}' evaluated to: {result}")
            self._transformation_stats['calculated_fields'] += 1
            
            # Apply data type transformation to the result
            if result is not None:
                # Special handling for empty strings in calculated fields - preserve them for string types
                if result == '' and mapping.data_type and mapping.data_type == 'string':
                    return result
                return self.transform_data_types(result, mapping.data_type)
            return None
            
        except Exception as e:
            self.logger.error(f"Error evaluating calculated field expression for '{mapping.target_column}': {e}")
            return None
    
    def _group_mappings_by_table(self, mappings: List[FieldMapping]) -> Dict[str, List[FieldMapping]]:
        """Group field mappings by target table."""
        table_mappings = {}
        for mapping in mappings:
            table_name = mapping.target_table
            if table_name not in table_mappings:
                table_mappings[table_name] = []
            table_mappings[table_name].append(mapping)
        
        return table_mappings

    def _process_table_mappings(self, xml_data: Dict[str, Any], mappings: List[FieldMapping], 
                               app_id: str, valid_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all mappings for a specific table."""
        records = []
        
        # Determine if this is a contact-related table (only actual contact tables, not app tables)
        # Get table name from the first mapping
        table_name = mappings[0].target_table if mappings else ""
        
        if table_name == 'contact_base':
            # valid_contacts is already deduped by con_id
            for contact in valid_contacts:
                record = self._create_record_from_mappings(xml_data, mappings, contact)
                if record:
                    record['con_id'] = int(contact['con_id']) if str(contact['con_id']).isdigit() else contact['con_id']
                    record['app_id'] = int(app_id) if app_id.isdigit() else app_id
                    records.append(record)
                    self.logger.debug(f"Created contact_base record for con_id={contact['con_id']}")
                else:
                    self.logger.debug(f"Skipping empty contact_base record for con_id={contact['con_id']}")
        elif table_name == 'contact_address':
            # Extract contact_address elements directly from XML data
            self.logger.debug(f"Extracting contact_address with {len(mappings)} mappings")
            records = self._extract_contact_address_records(xml_data, mappings, app_id, valid_contacts)
        elif table_name == 'contact_employment':
            # Extract contact_employment elements directly from XML data
            self.logger.debug(f"Extracting contact_employment with {len(mappings)} mappings")
            records = self._extract_contact_employment_records(xml_data, mappings, app_id, valid_contacts)
        else:
            # Create single record for app-level tables
            # Check if this table has calculated field mappings that need enhanced context
            has_calculated_fields = any(hasattr(m, 'mapping_type') and m.mapping_type and 'calculated_field' in m.mapping_type for m in mappings)
            if has_calculated_fields:
                # Build enhanced context for calculated fields that may reference cross-element data
                context_data = self._build_app_level_context(xml_data, valid_contacts, app_id)
                record = self._create_record_from_mappings(xml_data, mappings, context_data)
            else:
                # Use original xml_data for regular field mappings
                record = self._create_record_from_mappings(xml_data, mappings)
            # Only add app_id and append if record has actual data (not empty)
            if record:  # Check if record is not empty
                if app_id:
                    record['app_id'] = int(app_id) if app_id.isdigit() else app_id
                records.append(record)
        
        return records

    def _create_record_from_mappings(self, xml_data: Dict[str, Any], mappings: List[FieldMapping], context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a record by applying all mappings for a table.
        Apply cascading ID validation and element filtering rules.
        """
        record = {}
        applied_defaults = set()  # Track columns that received default values
        conditional_defaults = set()  # Track columns with conditional defaults that may be excluded
        
        # Get table name for validation
        table_name = mappings[0].target_table if mappings else ""
        
        # Apply element filtering rules based on required attributes  
        # REMOVED: This validation was preventing contact_base records from being created
        # The con_id validation is already handled in the calling code        
        for mapping in mappings:
            try:
                # Extract value from XML data
                value = self._extract_value_from_xml(xml_data, mapping, context_data)
                
                # DEBUG: Log calculated field processing
                if hasattr(mapping, 'mapping_type') and mapping.mapping_type and 'calculated_field' in mapping.mapping_type:
                    self.logger.debug(f"DEBUG: Processing calculated field mapping: {mapping.target_column}, xml_path={mapping.xml_path}, xml_attribute={mapping.xml_attribute}, extracted_value={value}")
                
                # Log extraction for birth_date fields (debug level)
                if mapping.target_column == 'birth_date':
                    self.logger.debug(f"Extracted birth_date: table={table_name}, value={value}")
                
                # Transform the value according to mapping rules
                transformed_value = self._apply_field_transformation(value, mapping, context_data)
                
                # Check if transformation applied a default (e.g., datetime 1900-01-01 for missing birth_date)
                is_transformation_default = self._is_transformation_default(value, transformed_value, mapping)
                
                # ENHANCED: Use contract-driven column inclusion logic
                if transformed_value is not None:
                    # Value successfully extracted and transformed - include column
                    record[mapping.target_column] = transformed_value
                    if is_transformation_default:
                        applied_defaults.add(mapping.target_column)  # Track transformation default
                    # Log birth_date transformation (debug level)
                    if mapping.target_column == 'birth_date':
                        self.logger.debug(f"Transformed birth_date: {transformed_value} (default: {is_transformation_default})")
                else:
                    # No value available - use contract-driven logic for column inclusion
                    if getattr(mapping, 'nullable', True):
                        # Column is nullable - exclude it entirely (don't add to record)
                        # This allows the database default or NULL to be used
                        self.logger.debug(f"Excluding nullable column {mapping.target_column} from {table_name} (no value available)")
                    else:
                        # Column is NOT nullable (required) - must provide a value
                        default_value = getattr(mapping, 'default_value', None)
                        if default_value is not None:
                            # Use contract default value
                            record[mapping.target_column] = default_value
                            applied_defaults.add(mapping.target_column)
                            self.logger.debug(f"Using contract default for required column {mapping.target_column}: {default_value}")
                        else:
                            # CRITICAL FIX: No contract default for required field - FAIL FAST
                            # This prevents silent data corruption and batch failures at database level
                            raise DataMappingError(
                                f"Required column '{mapping.target_column}' in table '{table_name}' "
                                f"has no value and no default_value defined in contract. "
                                f"Cannot proceed with NULL for NOT NULL column. "
                                f"Source XML path: {mapping.xml_path}{f'/@{mapping.xml_attribute}' if mapping.xml_attribute else ''}"
                            )
                
                self._transformation_stats['type_conversions'] += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to apply mapping for {mapping.xml_path}.{mapping.xml_attribute}: {e}")
                # Apply fallback strategy
                fallback_value = self._get_fallback_for_mapping(mapping, e)
                if fallback_value is not None:
                    record[mapping.target_column] = fallback_value
                    applied_defaults.add(mapping.target_column)  # Track fallback as applied default
                self._transformation_stats['fallback_values'] += 1
        
        # ENHANCED: Check if record only contains keys and applied defaults
        # If so, skip INSERT entirely to avoid creating meaningless empty rows
        # For conditional defaults, remove them when record would be skipped
        should_skip = self._should_skip_record(record, table_name, applied_defaults, conditional_defaults)
        if should_skip:
            return {}  # Return empty dict to signal "skip this record"
        
        # If record will be kept but has conditional defaults, check if we should exclude them
        if conditional_defaults and self._should_exclude_conditional_defaults(record, table_name, applied_defaults, conditional_defaults):
            for col in conditional_defaults:
                if col in record:
                    del record[col]
                    self.logger.debug(f"Excluded conditional default {col} from {table_name} record")
        
        return record

    def _should_skip_record(self, record: Dict[str, Any], table_name: str, applied_defaults: set, conditional_defaults: set) -> bool:
        """
        Determine if record should be skipped because it only contains keys and applied defaults.

        For app_base: Only app_id is required to keep the record (even if all other fields are defaults or missing).
        For other tables: Keep applied defaults if there's ANY meaningful data in the record.
        Only skip if record has ONLY keys and applied defaults with no real data.

        Args:
            record: The record dictionary
            table_name: Name of the target table
            applied_defaults: Set of column names that received default values

        Returns:
            True if record should be skipped, False otherwise
        """
        key_columns = {'app_id', 'con_id'}

        # Special case: app_base only requires app_id to keep the record
        if table_name == 'app_base':
            return False  # Never skip app_base records

        # For other tables: Check if record has only keys and applied defaults
        meaningful_columns = set(record.keys()) - key_columns - applied_defaults

        # If there are meaningful (non-default, non-key) columns, keep the record
        if meaningful_columns:
            return False

        # Record has only keys and/or applied defaults - should be skipped
        # Exception: contact_base should be kept even with minimal data for relationship integrity
        if table_name == 'contact_base':
            return False

        return True

    def _should_exclude_conditional_defaults(self, record: Dict[str, Any], table_name: str, applied_defaults: set, conditional_defaults: set) -> bool:
        """
        Determine if conditional defaults should be excluded from a record that will be kept.

        Conditional defaults (like birth_date) should be excluded when the record has minimal
        meaningful data - i.e., mostly just keys and other defaults.

        Args:
            record: The record dictionary
            table_name: Name of the target table
            applied_defaults: Set of columns with regular applied defaults
            conditional_defaults: Set of columns with conditional defaults

        Returns:
            True if conditional defaults should be excluded, False otherwise
        """
        key_columns = {'app_id', 'con_id'}

        # Calculate meaningful columns (non-key, non-default data)
        all_defaults = applied_defaults | conditional_defaults
        meaningful_columns = set(record.keys()) - key_columns - all_defaults

        # If record has substantial meaningful data, keep conditional defaults
        if len(meaningful_columns) >= 2:  # At least 2 meaningful columns
            return False

        # Record has minimal meaningful data - exclude conditional defaults
        return True
        """
        Check if a transformation applied a default value due to missing/invalid source data.
        
        Args:
            original_value: The original value from XML
            transformed_value: The transformed value
            mapping: The field mapping
            
        Returns:
            True if transformation applied a default, False otherwise
        """
        # If original value was missing/empty and we got a known default value, it's a transformation default
        if not StringUtils.safe_string_check(original_value):
            # Known transformation defaults
            transformation_defaults = {
                datetime(1900, 1, 1),  # birth_date default from _transform_to_datetime
            }
            return transformed_value in transformation_defaults
        
        return False

    def _extract_contact_address_records(self, xml_data: Dict[str, Any], mappings: List[FieldMapping], 
                                       app_id: str, valid_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract contact_address records using centralized element filtering."""
        records = []
        
        # Create set of valid con_ids for efficient lookup
        valid_con_ids = {contact.get('con_id', '').strip() for contact in valid_contacts if isinstance(contact, dict)}
        
        # Use centralized element filtering for robust extraction of address records
        if hasattr(self, '_current_xml_root') and self._current_xml_root is not None:
            element_filter = ElementFilter(contract=self._current_contract, logger=self.logger)
            try:
                filtered_elements = element_filter.filter_valid_elements(self._current_xml_root)
                valid_addresses = filtered_elements['addresses']
                
                self.logger.debug(f"Processing {len(valid_addresses)} valid address elements")
                
                for addr_elem in valid_addresses:
                    # Get parent contact info
                    parent_contact = addr_elem.getparent()
                    con_id = parent_contact.get('con_id')
                    
                    # Only process addresses for valid contacts
                    if con_id not in valid_con_ids:
                        self.logger.debug(f"Skipping address for invalid contact con_id {con_id}")
                        continue
                    
                    # Convert element attributes to the format expected by _create_record_from_mappings
                    attributes = dict(addr_elem.attrib)
                    context_data = {
                        'attributes': attributes,
                        'con_id': con_id,
                        'contact_address': [attributes]
                    }
                    
                    # Create record from mappings
                    record = self._create_record_from_mappings(xml_data, mappings, context_data)
                    if record:
                        record['con_id'] = int(con_id) if str(con_id).isdigit() else con_id
                        records.append(record)
                        self.logger.debug(f"Created contact_address record for con_id {con_id}")
                        
            except Exception as e:
                self.logger.error(f"Error in centralized address filtering: {e}")
                # Fallback to empty records rather than crash
                
        else:
            self.logger.warning("No XML root available for address extraction")
        
        self.logger.debug(f"Extracted {len(records)} contact_address records")
        return records

    def _extract_contact_employment_records(self, xml_data: Dict[str, Any], mappings: List[FieldMapping], 
                                          app_id: str, valid_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract contact_employment records using centralized element filtering."""
        records = []
        
        # Create set of valid con_ids for efficient lookup
        valid_con_ids = {contact.get('con_id', '').strip() for contact in valid_contacts if isinstance(contact, dict)}
        
        # Use centralized element filtering for robust extraction of employment records
        if hasattr(self, '_current_xml_root') and self._current_xml_root is not None:
            element_filter = ElementFilter(contract=self._current_contract, logger=self.logger)
            try:
                filtered_elements = element_filter.filter_valid_elements(self._current_xml_root)
                valid_employments = filtered_elements['employments']
                
                self.logger.debug(f"Processing {len(valid_employments)} valid employment elements")
                
                for emp_elem in valid_employments:
                    # Get parent contact info
                    parent_contact = emp_elem.getparent()
                    con_id = parent_contact.get('con_id')
                    
                    # Only process employments for valid contacts
                    if con_id not in valid_con_ids:
                        self.logger.debug(f"Skipping employment for invalid contact con_id {con_id}")
                        continue
                    
                    # Convert element attributes to the format expected by _create_record_from_mappings
                    attributes = dict(emp_elem.attrib)
                    context_data = {
                        'attributes': attributes,
                        'con_id': con_id,
                        'contact_employment': [attributes]
                    }
                    
                    # Create record from mappings
                    record = self._create_record_from_mappings(xml_data, mappings, context_data)
                    if record:
                        record['con_id'] = int(con_id) if str(con_id).isdigit() else con_id
                        records.append(record)
                        self.logger.debug(f"Created contact_employment record for con_id {con_id}")
                        
            except Exception as e:
                self.logger.error(f"Error in centralized employment filtering: {e}")
                # Fallback to empty records rather than crash
                
        else:
            self.logger.warning("No XML root available for employment extraction")
        
        self.logger.debug(f"Extracted {len(records)} contact_employment records")
        return records

    # Placeholder methods for missing functionality
    def _apply_relationships(self, result_tables, contract, xml_data, app_id, valid_contacts):
        """Apply relationship mappings to establish foreign key relationships."""
        return result_tables
    
    def _apply_calculated_fields(self, result_tables, contract, xml_data):
        """Apply calculated field transformations."""
        return result_tables
    
    def _validate_data_integrity(self, result_tables, contract):
        """Validate data integrity and quality with detailed error reporting."""
        pass
    
    def _get_default_for_mapping(self, mapping):
        """
        Get schema-derived default value for a field mapping.

        Retrieves the default_value from the mapping contract (derived from database schema)
        and applies appropriate data type transformation. This implements the contract-driven
        approach where defaults are explicitly defined in the schema rather than injected
        by the application.

        Args:
            mapping: FieldMapping object with schema-derived metadata

        Returns:
            Transformed default value in correct data type, or None if no default exists

        Contract-Driven Design:
        - Uses database schema defaults instead of application-level defaults
        - Applies type transformation to ensure data type consistency
        - Returns None for fields without explicit schema defaults
        - Preserves NULL semantics for optional fields
        """
        # Check if mapping has a default_value
        if hasattr(mapping, 'default_value') and mapping.default_value:
            return self.transform_data_types(mapping.default_value, mapping.data_type)
        
        return None
    
    def _get_fallback_for_mapping(self, mapping, error):
        """Get fallback value for mapping."""
        return None
    

    
    def _extract_from_curr_address_only(self, mapping, context_data):
        """Extract value from the current contact's CURR address only."""
        if not context_data or not hasattr(self, '_current_xml_root') or self._current_xml_root is None:
            return None
        
        # Get the contact ID from context
        con_id = context_data.get('con_id')
        if not con_id:
            return None
        
        try:
            # Find the contact element with this con_id
            contact_elements = self._current_xml_root.xpath(f"//contact[@con_id='{con_id}']")
            if not contact_elements:
                return None
            
            # Use the last contact element (following "last valid" logic)
            contact_element = contact_elements[-1]
            
            # Find the CURR address within this contact
            curr_address_elements = contact_element.xpath("contact_address[@address_tp_c='CURR']")
            if not curr_address_elements:
                return None
            
            # Use the last CURR address element
            curr_address_element = curr_address_elements[-1]
            
            # Extract the requested attribute
            value = curr_address_element.get(mapping.xml_attribute)
            self.logger.debug(f"Extracted {mapping.xml_attribute}='{value}' from CURR address for con_id {con_id}")
            
            return value
            
        except Exception as e:
            self.logger.warning(f"Error extracting from curr_address_only for {mapping.xml_attribute}: {e}")
            return None
    
    def _apply_bit_conversion(self, value):
        """Apply bit conversion transformation using loaded bit conversions."""
        str_value = str(value).strip() if value is not None else ''
        
        # Use char_to_bit conversion from loaded configuration
        if 'char_to_bit' in self._bit_conversions:
            bit_map = self._bit_conversions['char_to_bit']
            
            # Try exact match first
            if str_value in bit_map:
                result = bit_map[str_value]
                self.logger.debug(f"Bit conversion: '{str_value}' -> {result}")
                return result
            
            # Try case-insensitive match (uppercase)
            upper_value = str_value.upper()
            if upper_value in bit_map:
                result = bit_map[upper_value]
                self.logger.debug(f"Bit conversion (case-insensitive): '{str_value}' -> {result}")
                return result
        
        # If no match and empty/null value, return the mapped default (which is 0 in char_to_bit)
        if str_value in ['', 'null', 'None']:
            self.logger.debug(f"Bit conversion: '{str_value}' (empty/null) -> 0 (default)")
            return 0
        
        # Default fallback
        self.logger.warning(f"No bit conversion found for value '{str_value}' - using default 0")
        return 0
    
    def _apply_boolean_to_bit_conversion(self, value):
        """Apply boolean to bit conversion transformation using loaded bit conversions."""
        str_value = str(value).strip().lower() if value is not None else ''
        
        # Use boolean_to_bit conversion from loaded configuration
        if 'boolean_to_bit' in self._bit_conversions:
            bit_map = self._bit_conversions['boolean_to_bit']
            if str_value in bit_map:
                result = bit_map[str_value]
                self.logger.debug(f"Boolean-to-bit conversion: '{value}' -> {result}")
                return result
            
            # If empty/null value, return the mapped default (which is 0 in boolean_to_bit)
            if str_value in ['', 'null', 'none']:
                self.logger.debug(f"Boolean-to-bit conversion: '{value}' (empty/null) -> 0 (default)")
                return 0
        
        # Default fallback
        self.logger.warning(f"No boolean_to_bit conversion found for value '{str_value}' - using default 0")
        return 0
    
    def _apply_bit_conversion_with_default_tracking(self, value):
        """Apply bit conversion with tracking of applied defaults."""
        str_value = str(value).strip() if value is not None else ''
        
        # Use char_to_bit conversion from loaded configuration
        if 'char_to_bit' in self._bit_conversions:
            bit_map = self._bit_conversions['char_to_bit']
            if str_value in bit_map:
                result = bit_map[str_value]
                self.logger.debug(f"Bit conversion: '{str_value}' -> {result}")
                
                # Check if this is a default mapping for missing/empty values
                is_default = str_value in ['', 'null', ' ']  # These are default mappings
                return result, is_default
        
        # Default fallback - this is always a default
        self.logger.warning(f"No bit conversion found for value '{str_value}' - using default 0")
        return 0, True
    
    def _extract_numbers_only(self, value):
        """Extract only numeric characters from value."""
        if not StringUtils.safe_string_check(value):
            return None
        
        numbers_only = StringUtils.extract_numbers_only(value)
        
        # Return None if no numbers found (will be excluded from INSERT)
        if not numbers_only:
            return None
            
        return numbers_only
    
    def _extract_numeric_value(self, value):
        """Extract numeric value from text."""
        if not StringUtils.safe_string_check(value):
            return None
            
        return StringUtils.extract_numeric_value(value)
    
    def _extract_numeric_value_preserving_decimals(self, value):
        """
        Extract numeric value from text while preserving decimal structure.
        Used for auto-extraction when no mapping_type is specified.
        Converts to float first (preserves decimals), then transform_data_types handles the final type conversion.
        """
        if not StringUtils.safe_string_check(value):
            return None
            
        return StringUtils.extract_numeric_value_preserving_decimals(value)
    
    def _transform_to_string(self, value, max_length):
        """Transform value to string with length limit."""
        return str(value)[:max_length] if max_length else str(value)
    
    def _transform_to_integer(self, value):
        """Transform value to integer."""
        if value is None:
            return None
        try:
            # Handle string values that might be numeric
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                # Check if the string contains only digits (optionally with leading minus)
                if not value.isdigit() and not (value.startswith('-') and value[1:].isdigit()):
                    self.logger.warning(f"Invalid integer value '{value}' - contains non-numeric characters")
                    return None
            # Use decimal for proper rounding (round half up)
            val = Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            return int(val)
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Failed to convert '{value}' to integer: {e}")
            return None
    
    def _transform_to_decimal(self, value, target_type, precision=None):
        """Transform value to decimal with proper NULL handling."""
        if not StringUtils.safe_string_check(value):
            return None  # Return None for missing values - don't default to 0.00
        
        try:
            # Handle empty strings as NULL
            if str(value).strip() == '':
                return None
            # Use provided precision or default to 2
            if precision is None:
                precision = 2
            # Use decimal.Decimal for proper rounding (round half up, not banker's rounding)
            val = Decimal(str(value)).quantize(Decimal('0.' + '0' * precision), rounding=ROUND_HALF_UP)
            return float(val)
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Decimal conversion failed for '{value}': {e}")
            return None  # Return None instead of 0.00 for invalid values
    
    def _transform_to_decimal_with_precision(self, value, precision):
        """Transform value to decimal with specified precision."""
        if not StringUtils.safe_string_check(value):
            return None  # Return None for missing values - don't default to 0.00
        
        try:
            # Handle empty strings as NULL
            if str(value).strip() == '':
                return None
            # Use decimal.Decimal for proper rounding (round half up, not banker's rounding)
            val = Decimal(str(value)).quantize(Decimal('0.' + '0' * precision), rounding=ROUND_HALF_UP)
            return float(val)
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Decimal conversion failed for '{value}' with precision {precision}: {e}")
            return None  # Return None instead of 0.00 for invalid values
    
    def _transform_to_datetime(self, value, target_type):
        """Transform value to datetime - return None for missing values to let default system handle it."""
        if not StringUtils.safe_string_check(value):
            # Return None - let the mapping contract default system handle missing values
            return None
        
        try:
            # Handle various datetime formats
            if isinstance(value, str):
                # Clean up invalid datetime components first
                cleaned_value = self._clean_datetime_string(value)
                if not cleaned_value:
                    return None
                
                # Try common formats including the specific format from the XML
                formats_to_try = [
                    '%Y-%m-%d %H:%M:%S.%f',  # 2023-10-3 16:26:23.886
                    '%Y-%m-%d %H:%M:%S',     # 2023-10-3 16:26:23
                    '%Y-%m-%d',              # 2023-10-3
                    '%m/%d/%Y',              # 10/3/2023
                    '%m/%d/%Y %H:%M:%S',     # 10/3/2023 16:26:23
                    '%m/%d/%Y %I:%M:%S %p',  # 4/2/2020 5:53:20 AM
                ]
                
                for fmt in formats_to_try:
                    try:
                        return datetime.strptime(cleaned_value, fmt)
                    except ValueError:
                        continue
                        
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception as e:
            self.logger.warning(f"DateTime conversion failed for '{value}': {e}")
            # Return None for invalid values - let default system handle it
            return None
    
    def _clean_datetime_string(self, datetime_str):
        """Clean datetime string to fix common invalid patterns."""
        if not datetime_str:
            return None
        
        try:
            # Handle invalid seconds (like 88 seconds)
            # PERFORMANCE TUNING (Phase 1): Use pre-compiled regex
            match = self._regex_invalid_datetime_seconds.match(datetime_str)
            
            if match:
                prefix = match.group(1)  # "2024-8-8 8:08:"
                seconds = int(match.group(2))  # 88
                milliseconds = match.group(3) or ""  # ".008"
                
                # Fix invalid seconds (clamp to 59)
                if seconds > 59:
                    seconds = 59
                    self.logger.debug(f"Fixed invalid seconds in datetime: {datetime_str}")
                
                return f"{prefix}{seconds:02d}{milliseconds}"
            
            return datetime_str
            
        except Exception as e:
            self.logger.warning(f"Error cleaning datetime string '{datetime_str}': {e}")
            return None
    
    def _transform_to_bit(self, value):
        """Transform value to bit."""
        return 1 if value else 0
    
    def _transform_to_boolean(self, value):
        """Transform value to boolean."""
        return bool(value)
    
    def _get_fallback_value(self, value, target_type):
        """Get fallback value for failed conversion."""
        return None
    
    def _extract_from_last_valid_pr_contact(self, mapping, context_data=None):
        """Extract value from the last valid PR contact with enhanced debugging."""
        self.logger.debug(f"ENTERING _extract_from_last_valid_pr_contact for field {mapping.target_column}")
        try:
            if not hasattr(self, '_current_xml_root') or self._current_xml_root is None:
                self.logger.debug("No XML root available for last_valid_pr_contact extraction")
                return None
            
            # Find all PR contacts
            pr_contacts = self._current_xml_root.xpath('.//contact[@ac_role_tp_c="PR"]')
            self.logger.debug(f"Found {len(pr_contacts)} PR contacts via xpath")
            if not pr_contacts:
                self.logger.debug("No PR contacts found in XML")
                return None
            
            # Find the last VALID PR contact (one with non-empty con_id AND non-empty ac_role_tp_c)
            last_valid_pr_contact = None
            for contact in reversed(pr_contacts):  # Start from the end
                con_id = contact.get('con_id', '').strip()
                ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
                if con_id and ac_role_tp_c:  # Both must be non-empty
                    last_valid_pr_contact = contact
                    break
            
            if last_valid_pr_contact is None:
                self.logger.debug("No valid PR contacts found (all have empty con_id or ac_role_tp_c)")
                return None
            
            selected_con_id = last_valid_pr_contact.get('con_id', 'UNKNOWN')
            self.logger.debug(f"Selected last VALID PR contact: con_id={selected_con_id}")
            
            # Extract the requested attribute directly from the contact or its child elements
            if 'contact_address' in mapping.xml_path:
                # Look for contact_address elements within this contact
                address_elements = last_valid_pr_contact.xpath('.//contact_address')
                # Filter to only CURR (current) addresses - these have the most relevant data
                curr_address_elements = [addr for addr in address_elements if addr.get('address_tp_c') == 'CURR']
                # Use CURR addresses if available, otherwise fall back to all addresses
                target_addresses = curr_address_elements if curr_address_elements else address_elements
                if target_addresses:
                    # Find the first address that has the required attribute
                    selected_address = None
                    for addr in target_addresses:
                        if addr.get(mapping.xml_attribute):
                            selected_address = addr
                            break
                    if selected_address is None:
                        # If no address has the attribute, fall back to the last one
                        selected_address = target_addresses[-1]
                    address_element = selected_address
                    value = address_element.get(mapping.xml_attribute)
                    # If the field is a decimal, apply rounding/truncation using contract data_length
                    if value is not None and mapping.data_type and mapping.data_type == 'decimal' and mapping.data_length is not None:
                        try:
                            # Use decimal for proper rounding (round half up, not banker's rounding)
                            val = Decimal(str(value)).quantize(Decimal('0.' + '0' * mapping.data_length), rounding=ROUND_HALF_UP)
                            return float(val)
                        except Exception:
                            return value
                    return value
            elif 'app_prod_bcard' in mapping.xml_path:
                # Look for app_prod_bcard element within this contact
                app_prod_bcard_elements = last_valid_pr_contact.xpath('.//app_prod_bcard')
                self.logger.debug(f"Found {len(app_prod_bcard_elements)} app_prod_bcard elements for con_id {selected_con_id}")
                if app_prod_bcard_elements:
                    # Get the last app_prod_bcard element
                    app_prod_bcard = app_prod_bcard_elements[-1]
                    
                    # Debug: Log all attributes in the app_prod_bcard element
                    all_attrs = dict(app_prod_bcard.attrib)
                    self.logger.debug(f"app_prod_bcard attributes for con_id {selected_con_id}: {all_attrs}")
                    
                    value = app_prod_bcard.get(mapping.xml_attribute)
                    self.logger.debug(f"Extracted {mapping.xml_attribute}='{value}' from app_prod_bcard for con_id {selected_con_id}")
                    return value
                else:
                    self.logger.debug(f"No app_prod_bcard elements found for con_id {selected_con_id}")
            
            # Always try to extract directly from the contact element first
            # This handles banking attributes and other contact-level attributes
            value = last_valid_pr_contact.get(mapping.xml_attribute)
            self.logger.debug(f"Extracted {mapping.xml_attribute}='{value}' directly from contact con_id {selected_con_id}")
            # Enforce string truncation for all string fields
            # Enforce string truncation using contract data_length
            max_length = getattr(mapping, 'data_length', None)
            if max_length and value is not None and mapping.data_type and mapping.data_type == 'string':
                value = str(value)[:max_length]
            return value
            
        except Exception as e:
            self.logger.debug(f"Failed to extract from last valid PR contact: {e}")
            return None
    
    def get_transformation_stats(self):
        """Get transformation statistics."""
        return self._transformation_stats
    
    def get_validation_errors(self):
        """Get validation errors."""
        return self._validation_errors 
    
    def handle_nested_elements(self, parent_id: str, child_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Handle nested XML elements for parent-child relationship detection and foreign key generation.
        CRITICAL: Only process child elements that have required identifiers (con_id for contacts).
        Never generate app_id or con_id - they must exist in the XML.
        """
        processed_children = []
        
        for i, child_element in enumerate(child_elements):
            try:
                # SKIP elements without required identifiers
                if 'contact' in str(child_element) and ('con_id' not in child_element or not child_element.get('con_id')):
                    self.logger.warning(f"Skipping nested contact element {i} - missing con_id")
                    continue
                
                # Add parent foreign key to child record
                child_record = child_element.copy()
                
                # Determine the foreign key column name based on parent type
                if 'app_' in parent_id or (parent_id.isdigit() and len(parent_id) <= 9):
                    child_record['app_id'] = int(parent_id) if parent_id.isdigit() else parent_id
                elif 'con_' in parent_id or (parent_id.isdigit() and len(parent_id) <= 9):
                    child_record['con_id'] = int(parent_id) if parent_id.isdigit() else parent_id
                
                processed_children.append(child_record)
                
            except Exception as e:
                self.logger.warning(f"Failed to process nested element {i}: {e}")
                continue
    
    def _build_app_level_context(self, xml_data: Dict[str, Any], valid_contacts: List[Dict[str, Any]], app_id: str) -> Dict[str, Any]:
        """
        Build enhanced context for app-level calculated fields that may reference cross-element data.
        
        This provides access to contact, address, and employment data for expressions like:
        - contact.field_name (references primary contact data)
        - address.field_name (references address data)
        - employment.field_name (references employment data)
        - app_product.field_name (references app_product data)
        - application.field_name (references application data)
        """
        context = {}
        
        # Flatten all contact data for easy access
        if valid_contacts:
            # Primary contact (first PR contact or first contact)
            pr_contacts = [c for c in valid_contacts if c.get('ac_role_tp_c') == 'PR']
            primary_contact = pr_contacts[0] if pr_contacts else valid_contacts[0]
            
            # Add contact fields with 'contact.' prefix for cross-element references
            for key, value in primary_contact.items():
                if key and value is not None:
                    context[f'contact.{key}'] = value
            
            # Add all contacts data
            context['contacts'] = valid_contacts
            
            # Add primary contact data without prefix for backward compatibility
            context.update(primary_contact)
        
        # Add app_id for reference
        if app_id:
            context['app_id'] = app_id
        
        # Add application and app_product data with dotted prefixes for cross-element references
        for path, element in xml_data.items():
            if isinstance(element, dict) and 'attributes' in element:
                attrs = element['attributes']
                if path.endswith('/application'):
                    # Add application fields with 'application.' prefix
                    for key, value in attrs.items():
                        if key and value is not None:
                            context[f'application.{key.lower()}'] = value
                    # Also add without prefix for direct access
                    context.update(attrs)
                elif path.endswith('/app_product'):
                    # Add app_product fields with 'app_product.' prefix
                    for key, value in attrs.items():
                        if key and value is not None:
                            context[f'app_product.{key.lower()}'] = value
                    # Also add without prefix for direct access
                    context.update(attrs)
        
        self.logger.debug(f"Built app-level context with {len(context)} keys")
        for key in sorted(context.keys())[:10]:  # Log first 10 keys
            self.logger.debug(f"Context key: {key} = {context[key]}")
        
        return context

    def _is_transformation_default(self, original_value: Any, transformed_value: Any, mapping: FieldMapping) -> bool:
        """Check if the transformation resulted in applying a default value."""
        # If original value was None or empty and we got a transformed value, it might be a default
        if original_value is None or (isinstance(original_value, str) and not original_value.strip()):
            # Check if the transformed value matches known defaults
            default_value = self._get_default_for_mapping(mapping)
            if default_value is not None and transformed_value == default_value:
                return True
        return False