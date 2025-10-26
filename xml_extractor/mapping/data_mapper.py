"""
Data Mapping and Transformation Engine

This module provides the core data transformation pipeline for converting complex XML credit application
data into relational database format. It handles multiple mapping types including calculated fields,
enum mappings, contact-specific extractions, and cross-element references.

Key Features:
- Complex calculated field expressions with CASE/WHEN logic and cross-element references
- Enum mapping with configurable value transformations (string → integer)
- Contact-specific data extraction (last valid PR contact, current address filtering)
- Type-safe data transformations with proper NULL handling for database compatibility
- Context-aware field extraction that separates application vs contact-level data
- Comprehensive error handling and transformation statistics tracking

Mapping Types Supported:
- calculated_field: Evaluates SQL-like expressions with cross-element references
- last_valid_pr_contact: Extracts from the most recent valid PR (Primary Responsible) contact
- curr_address_only: Filters to current (CURR) addresses only, excluding PREV/MAIL addresses
- enum: Maps string values to integer codes using configurable enum mappings
- char_to_bit/boolean_to_bit: Converts Y/N or boolean values to 0/1 bit fields
- extract_numeric/numbers_only: Extracts numeric values from formatted strings
- default_getutcdate_if_null: Provides current timestamp for missing datetime fields
- identity_insert: Handles auto-increment fields during bulk inserts

The engine processes XML data through a multi-stage pipeline:
1. Pre-flight validation (app_id and contact requirements)
2. Contact extraction and deduplication (last valid element approach)
3. Field mapping application with context building for calculated fields
4. Data type transformation with database-specific handling
5. Record creation with intelligent NULL vs default value decisions
"""

import re
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, date
# Removed Decimal import - using float for SQL Server compatibility

from ..interfaces import DataMapperInterface
from ..models import MappingContract, FieldMapping, RelationshipMapping
from ..exceptions import DataMappingError, ValidationError, DataTransformationError
from ..validation.element_filter import ElementFilter
from ..utils import StringUtils, ValidationUtils
from ..config.config_manager import get_config_manager
from .calculated_field_engine import CalculatedFieldEngine


class DataMapper(DataMapperInterface):
    """
    Core data mapping engine that orchestrates the transformation of XML credit application data
    into relational database records.

    This class handles the complex orchestration of:
    - Loading and applying mapping contracts from configuration
    - Building context data for calculated field evaluation (flattens XML structure)
    - Applying multiple mapping types with proper precedence and chaining
    - Contact-specific data extraction with deduplication logic
    - Type-safe transformations with database-specific NULL handling
    - Progress tracking and error reporting for large-scale data migrations

    The mapper separates concerns between application-level and contact-level data,
    ensuring calculated fields can reference data across the entire XML structure while
    contact fields are properly scoped to their respective contact contexts.

    Key Design Decisions:
    - Calculated fields use sentinel values to trigger expression evaluation
    - Context data is built once per record to avoid redundant XML parsing
    - Enum mappings return None (excluded from INSERT) when no valid mapping exists,
      preserving data integrity by not fabricating default values
    - Contact extraction uses 'last valid element' approach for duplicate handling
    - Address filtering prioritizes CURR (current) addresses over PREV/MAIL types
    """
    
    def __init__(self, mapping_contract_path: Optional[str] = None):
        """
        Initialize the DataMapper with centralized configuration and mapping contract loading.

        Loads enum mappings, bit conversions, and default values from the mapping contract
        JSON file. These configurations enable the various mapping types (enum, char_to_bit,
        calculated_field, etc.) to function properly.

        Args:
            mapping_contract_path: Optional path to mapping contract JSON file.
                                If None, uses path from centralized configuration.

        Configuration Loaded:
        - _enum_mappings: Dict mapping enum_type names to value→integer mappings
        - _bit_conversions: Dict for Y/N → 0/1 and boolean → bit transformations
        - _default_values: Dict of fallback values for specific column mappings
        - _validation_rules: Dict of validation constraints (currently unused)

        The initialization is designed to be fault-tolerant - if the mapping contract
        cannot be loaded, empty dictionaries are used as fallbacks.
        """
        self.logger = logging.getLogger(__name__)
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
            self._default_values = self._config_manager.get_default_values(self._mapping_contract_path)
            self.logger.info(f"DataMapper initialized with mapping contract: {self._mapping_contract_path}")
            self.logger.debug(f"Loaded {len(self._enum_mappings)} enum mappings, {len(self._bit_conversions)} bit conversions")
        except Exception as e:
            self.logger.warning(f"Could not load mapping contract configurations during initialization: {e}")
            self._enum_mappings = {}
            self._bit_conversions = {}
            self._default_values = {}
        
        self._validation_rules = {}
    
    def apply_mapping_contract(self, xml_data: Dict[str, Any], 
                             contract: MappingContract,
                             app_id: Optional[str] = None,
                             valid_contacts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Apply mapping contract to transform XML data to relational format."""
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
            
            if not valid_contacts:
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
        """Map XML data to database format using the loaded mapping contract."""
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
            # Handle string types with length specifications
            if target_type.startswith('varchar') or target_type.startswith('char'):
                # Extract max length from type specification like 'varchar(50)'
                import re
                match = re.search(r'\((\d+)\)', target_type)
                max_length = int(match.group(1)) if match else None
                return self._transform_to_string(value, max_length)
            
            # Handle numeric types
            elif target_type in ['int', 'smallint', 'bigint', 'tinyint']:
                return self._transform_to_integer(value)
            
            elif target_type.startswith('decimal'):
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
        - Only contacts with BOTH con_id AND ac_role_tp_c are considered
        - Only PR and AUTHU contact types are valid (future TODO: use "contact_type_enum" from mapping contract to future-proof types)
        - Max of one contact per type is returned (last PR, last AUTHU)
        - This function also deduplicates contacts by con_id across types (to prevent SQL errors)
        - In the case of duplicates by con_id across types, the PR contact is preferred over AUTHU
        Returns a list of contacts which can safely be inserted.
        """
        try:
            contacts = self._navigate_to_contacts(xml_data)
            self.logger.info(f"Contacts found: {[(c.get('con_id', '').strip(), c.get('first_name', ''), c.get('ac_role_tp_c', '')) for c in contacts if isinstance(c, dict)]}")

            # Only consider contacts with required fields: con_id and ac_role_tp_c
            filtered_contacts = []
            for contact in contacts:
                if not isinstance(contact, dict):
                    continue
                con_id = contact.get('con_id', '').strip()
                ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
                if not con_id or not ac_role_tp_c:
                    continue
                if ac_role_tp_c not in ('PR', 'AUTHU'):
                    continue
                filtered_contacts.append(contact)

            # For each con_id, keep only the last PR if present, else last AUTHU
            con_id_map = {}
            for contact in filtered_contacts:
                con_id = contact.get('con_id', '').strip()
                ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
                # Always overwrite with latest contact
                if con_id not in con_id_map:
                    con_id_map[con_id] = contact
                else:
                    # If current is PR, always prefer it
                    if ac_role_tp_c == 'PR':
                        con_id_map[con_id] = contact
                    # If existing is not PR, overwrite with latest AUTHU
                    elif con_id_map[con_id].get('ac_role_tp_c', '') != 'PR':
                        con_id_map[con_id] = contact

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
        
        Args:
            attributes: Dictionary of attributes
            target_attr: Target attribute name (from mapping contract)
            
        Returns:
            Attribute value if found, None otherwise
        """
        # Create case-insensitive lookup
        for attr_key, attr_value in attributes.items():
            if attr_key.lower() == target_attr.lower():
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
            seen_con_ids_authu = set()
            for contact in reversed(contacts):
                if isinstance(contact, dict):
                    con_id = contact.get('con_id', '').strip()
                    ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
                    if ac_role_tp_c == 'AUTHU' and con_id and con_id not in seen_con_ids_authu:
                        authu_contacts.insert(0, contact)
                        seen_con_ids_authu.add(con_id)

        Returns:
            Extracted value or None if not found. For calculated fields, returns sentinel string.
        """
        try:
            # Handle special mapping types that require custom extraction logic
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type == 'last_valid_pr_contact':
                return self._extract_from_last_valid_pr_contact(mapping)
            
            # For calculated fields, skip XML extraction entirely - return sentinel value to trigger expression evaluation
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type == 'calculated_field':
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
        
        # Parse chained mapping types (comma-separated)
        mapping_types = []
        if hasattr(mapping, 'mapping_type') and mapping.mapping_type:
            mapping_types = [mt.strip() for mt in mapping.mapping_type.split(',')]
            self.logger.debug(f"Parsed mapping_types for {mapping.target_column}: {mapping_types}")
        else:
            self.logger.debug(f"No mapping_type for {mapping.target_column}")
        
        # If no mapping types specified, apply standard data type transformation
        if not mapping_types:
            # Check for default value if input is empty
            if not StringUtils.safe_string_check(value):
                default_value = self._get_default_for_mapping(mapping)
                if default_value is not None:
                    return default_value
            return self.transform_data_types(value, mapping.data_type)
        
        current_value = value
        
        # Apply each mapping type in sequence
        for i, mapping_type in enumerate(mapping_types):
            self.logger.debug(f"Applying mapping type {i+1}/{len(mapping_types)}: '{mapping_type}' to value: {current_value}")
            
            try:
                current_value = self._apply_single_mapping_type(current_value, mapping_type, mapping, context_data)
                self.logger.debug(f"Result after '{mapping_type}': {current_value}")
                
                # Allow certain mapping types to handle None values (don't break the chain)
                if current_value is None and mapping_type not in ['enum', 'default_getutcdate_if_null']:
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
        
        # For string fields, apply mapping_type first (if any), then trim, truncate, trim again
        if current_value is not None and isinstance(current_value, str):
            # Apply mapping_type transformation if present and not already applied
            mapping_types = []
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type:
                mapping_types = [mt.strip() for mt in mapping.mapping_type.split(',')]
            # Only apply numbers_only if not already applied in chain
            if 'numbers_only' in mapping_types:
                import re
                current_value = re.sub(r'[^0-9]', '', current_value)
            # First trim
            current_value = current_value.strip()
            # Truncate
            max_length = None
            if mapping.data_type and (mapping.data_type.startswith('varchar') or mapping.data_type.startswith('char')):
                import re
                match = re.search(r'\((\d+)\)', mapping.data_type)
                if match:
                    max_length = int(match.group(1))
            if max_length:
                current_value = current_value[:max_length]
            # Final trim
            current_value = current_value.strip()
            return current_value
        return current_value

    def _apply_single_mapping_type(self, value: Any, mapping_type: str, mapping: FieldMapping, context_data: Optional[Dict[str, Any]] = None) -> Any:
        """Apply a single mapping type transformation."""
        
        # Handle special mapping types that don't depend on input value
        if mapping_type == 'last_valid_pr_contact':
            # Extract value from the last valid PR contact
            self.logger.info(f"Processing last_valid_pr_contact mapping for {mapping.target_column}")
            result = self._extract_from_last_valid_pr_contact(mapping)
            if result is not None:
                self.logger.info(f"last_valid_pr_contact returned: {result} for {mapping.target_column}")
                return result  # Don't apply data type transformation here - let it be chained
            self.logger.info(f"last_valid_pr_contact returned None for {mapping.target_column}")
            return None
        
        elif mapping_type == 'curr_address_only':
            # Extract value from the current contact's CURR address only
            self.logger.debug(f"Processing curr_address_only mapping for {mapping.target_column}")
            result = self._extract_from_curr_address_only(mapping, context_data)
            if result is not None:
                self.logger.debug(f"curr_address_only returned: {result}")
                # Clean phone numbers to extract only digits
                if 'phone' in mapping.target_column.lower():
                    result = StringUtils.extract_numbers_only(result)
                    if not result:  # If no numbers found, return None
                        return None
                # Apply data type transformation to handle truncation for phone numbers
                return self.transform_data_types(result, mapping.data_type)
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
        
        # Handle other mapping types that require a valid input value
        elif not StringUtils.safe_string_check(value):
            # Try to get default value for this mapping
            default_value = self._get_default_for_mapping(mapping)
            if default_value is not None:
                return default_value
            return None
        
        # Apply specific mapping type transformations
        if mapping_type == 'char_to_bit':
            result = self._apply_bit_conversion(value)
            self._transformation_stats['bit_conversions'] += 1
            return result
        elif mapping_type == 'boolean_to_bit':
            result = self._apply_boolean_to_bit_conversion(value)
            self._transformation_stats['bit_conversions'] += 1
            return result
        elif mapping_type == 'numbers_only':
            result = self._extract_numbers_only(value)
            if result is not None:
                # Apply data type transformation to handle truncation
                return self.transform_data_types(result, mapping.data_type)
            return None
        elif mapping_type == 'extract_numeric':
            return self._extract_numeric_value(value)
        elif mapping_type == 'identity_insert':
            return self.transform_data_types(value, mapping.data_type)
        elif mapping_type == 'default_getutcdate_if_null':
            if not StringUtils.safe_string_check(value):
                self.logger.debug(f"Applying default_getutcdate_if_null for {mapping.target_column}: {value} -> {datetime.utcnow()}")
                return datetime.utcnow()
            # Apply data type transformation to the existing value
            return self.transform_data_types(value, mapping.data_type)
        elif mapping_type == 'calculated_field':
            return self._apply_calculated_field_mapping(value, mapping, context_data)
        else:
            # Unknown mapping type - apply standard data type transformation
            self.logger.warning(f"Unknown mapping type '{mapping_type}' for {mapping.target_column}, applying standard data type transformation")
            return self.transform_data_types(value, mapping.data_type)

    def _apply_enum_mapping(self, value: Any, mapping: FieldMapping) -> int:
        """
        Apply enum mapping transformation, converting string values to integer codes.

        This method implements a deliberate design choice: when no valid enum mapping exists
        for a value, it returns None instead of a fabricated default. This causes the column
        to be excluded from the INSERT statement, leaving the database column NULL.

        Design Rationale:
        - NULL indicates "no source data available" vs. "explicitly set to default"
        - Preserves data integrity by not inventing values
        - Allows applications to distinguish between missing XML data and default assignments
        - Follows database best practices for optional enumerated fields

        The mapping process:
        1. Convert input value to string and strip whitespace
        2. Determine enum_type from column name using pattern matching
        3. Look up the enum_type in _enum_mappings (loaded from config)
        4. Try exact match first, then case-insensitive match
        5. Use default value from enum map if available (key='')
        6. Return None if no valid mapping found (column excluded from INSERT)

        Args:
            value: Input value to be mapped (typically string from XML)
            mapping: Field mapping containing target_column and other metadata

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
        
        # INTENTIONAL DESIGN: No valid enum mapping found - return None to exclude column from INSERT
        # This is BY DESIGN: When XML attribute is missing/empty and no default enum mapping exists,
        # we intentionally exclude the column from INSERT so the database column remains NULL.
        # NULL indicates "no source data available" vs. fabricating a default value.
        # This preserves data integrity and allows applications to distinguish between
        # "missing in source XML" vs. "explicitly set to default value".
        self.logger.info(f"No enum mapping found for value '{str_value}' in column {mapping.target_column}, enum_type={enum_type} - excluding column")
        return None

    def _determine_enum_type(self, column_name: str) -> Optional[str]:
        """
        Determine the enum type name for a given column based on naming patterns.

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
                return enum_type
        
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
            # For contact-level mappings, use context_data['attributes'] if available
            # For app-level mappings, use the entire context_data (which contains flattened cross-element references)
            element_data = {}
            if context_data:
                if 'attributes' in context_data:
                    # Contact-level mapping (employment, address)
                    element_data = context_data['attributes']
                else:
                    # App-level mapping with cross-element context
                    element_data = context_data
            
            # Evaluate the expression using the element data
            result = self._calculated_field_engine.evaluate_expression(expression, element_data, mapping.target_column)
            
            # Debug logging for specific calculated fields
            if mapping.target_column in ['cb_score_factor_code_1', 'cb_score_factor_code_2']:
                self.logger.warning(f"DEBUG: Calculated field '{mapping.target_column}' expression evaluation completed with result: {repr(result)}")
                self.logger.warning(f"DEBUG: Context data keys: {list(element_data.keys()) if element_data else 'None'}")
                if 'adverse_actn1_type_cd' in element_data:
                    self.logger.warning(f"DEBUG: adverse_actn1_type_cd = '{element_data.get('adverse_actn1_type_cd')}'")
                if 'adverse_actn2_type_cd' in element_data:
                    self.logger.warning(f"DEBUG: adverse_actn2_type_cd = '{element_data.get('adverse_actn2_type_cd')}'")
                if 'app_receive_date' in element_data:
                    self.logger.warning(f"DEBUG: app_receive_date = '{element_data.get('app_receive_date')}'")
                if 'population_assignment' in element_data:
                    self.logger.warning(f"DEBUG: population_assignment = '{element_data.get('population_assignment')}'")
            
            self.logger.debug(f"Calculated field expression '{expression}' evaluated to: {result}")
            self._transformation_stats['calculated_fields'] += 1
            
            # Apply data type transformation to the result
            if result is not None:
                # Special handling for empty strings in calculated fields - preserve them for string types
                if result == '' and (mapping.data_type.startswith('varchar') or mapping.data_type.startswith('char')):
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
        
        # DEBUG: Log mappings for app_operational_cc
        # if 'app_operational_cc' in table_mappings:
        #     print(f"DEBUG: Found {len(table_mappings['app_operational_cc'])} mappings for app_operational_cc")
        #     for mapping in table_mappings['app_operational_cc']:
        #         print(f"  Mapping: {mapping.target_column} -> {mapping.xml_path}.{mapping.xml_attribute}, type={mapping.mapping_type}")
        
        return table_mappings

    def _process_table_mappings(self, xml_data: Dict[str, Any], mappings: List[FieldMapping], 
                               app_id: str, valid_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process all mappings for a specific table."""
        records = []
        
        # Determine if this is a contact-related table (only actual contact tables, not app tables)
        # Get table name from the first mapping
        table_name = mappings[0].target_table if mappings else ""
        
        # DEBUG: Log mappings for app_operational_cc
        # if table_name == 'app_operational_cc':
        #     print(f"DEBUG: Processing {len(mappings)} mappings for app_operational_cc")
        #     for mapping in mappings:
        #         print(f"  Mapping: {mapping.target_column} -> {mapping.xml_path}.{mapping.xml_attribute}, type={mapping.mapping_type}")
        
        # Determine if this is a contact-related table (only actual contact tables, not app tables)
        table_name = mappings[0].target_table if mappings else 'unknown'
        
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
            has_calculated_fields = any(m.mapping_type == 'calculated_field' for m in mappings)
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

    def _create_record_from_mappings(self, xml_data: Dict[str, Any], mappings: List[FieldMapping], 
                                   context_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a record by applying all mappings for a table.
        Apply cascading ID validation and element filtering rules.
        """
        record = {}
        applied_defaults = set()  # Track columns that received default values
        
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
                if mapping.mapping_type == 'calculated_field':
                    self.logger.warning(f"DEBUG: Processing calculated field mapping: {mapping.target_column}, xml_path={mapping.xml_path}, xml_attribute={mapping.xml_attribute}, extracted_value={value}")
                
                # Log extraction for birth_date fields (debug level)
                if mapping.target_column == 'birth_date':
                    self.logger.debug(f"Extracted birth_date: table={table_name}, value={value}")
                
                # Transform the value according to mapping rules
                transformed_value = self._apply_field_transformation(value, mapping, context_data)
                
                # Check if transformation applied a default (e.g., datetime 1900-01-01 for missing birth_date)
                is_transformation_default = self._is_transformation_default(value, transformed_value, mapping)
                
                # Add to record, or use default if transformed value is None
                if transformed_value is not None:
                    record[mapping.target_column] = transformed_value
                    if is_transformation_default:
                        applied_defaults.add(mapping.target_column)  # Track transformation default
                    # Log birth_date transformation (debug level)
                    if mapping.target_column == 'birth_date':
                        self.logger.debug(f"Transformed birth_date: {transformed_value} (default: {is_transformation_default})")
                else:
                    # Try to get default value
                    default_value = self._get_default_for_mapping(mapping)
                    if default_value is not None:
                        record[mapping.target_column] = default_value
                        applied_defaults.add(mapping.target_column)  # Track applied default
                                # Log birth_date default (debug level)
                        if mapping.target_column == 'birth_date':
                            self.logger.debug(f"Using birth_date default: {default_value}")
                    else:
                        # Log missing birth_date (debug level)
                        if mapping.target_column == 'birth_date':
                            self.logger.debug(f"No birth_date default - will be NULL")
                    # If no default, don't add the column (leave as NULL)
                
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
        if self._should_skip_record(record, table_name, applied_defaults):
            return {}  # Return empty dict to signal "skip this record"
        
        return record

    def _should_skip_record(self, record: Dict[str, Any], table_name: str, applied_defaults: set) -> bool:
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

        # Special case: app_base only requires app_id to be kept
        if table_name == 'app_base':
            if 'app_id' in record:
                self.logger.debug(f"Keeping app_base record with app_id (special case)")
                return False
            else:
                self.logger.debug(f"Skipping app_base record - missing app_id")
                return True

        # Find meaningful data: not keys, not None, and not applied defaults
        meaningful_data = {k: v for k, v in record.items() 
                          if k not in key_columns 
                          and v is not None 
                          and k not in applied_defaults}

        # Log record evaluation summary
        self.logger.debug(f"Record evaluation for {table_name}: {len(meaningful_data)} meaningful fields, {len(applied_defaults)} defaults")

        # Disallow app_pricing_cc inserts if required fields are missing or empty
        if table_name == 'app_pricing_cc':
            required_fields = ['campaign_num']
            for field in required_fields:
                if field not in record or not StringUtils.safe_string_check(record[field]):
                    self.logger.debug(f"Skipping app_pricing_cc record - missing or empty required field: {field}")
                    return True
        # Disallow app_operational_cc inserts if required fields are missing or empty
        if table_name == 'app_operational_cc':
            required_fields = ['sc_bank_aba']
            for field in required_fields:
                if field not in record or not StringUtils.safe_string_check(record[field]):
                    self.logger.debug(f"Skipping app_operational_cc record - missing or empty required field: {field}")
                    return True
        # Skip records if they only have keys and applied defaults (no meaningful data)
        if not meaningful_data:
            tables_with_required_defaults = {
                'contact_base', 'app_pricing_cc', 'app_solicited_cc', 
                'app_transactional_cc', 'app_operational_cc'
            }
            if table_name in tables_with_required_defaults and applied_defaults:
                self.logger.debug(f"Keeping {table_name} record with applied defaults")
                return False
            self.logger.debug(f"Skipping {table_name} INSERT - only keys and defaults")
            return True
            
        # Keep records with meaningful data (applied defaults will be included automatically)
        self.logger.debug(f"Keeping {table_name} record - has meaningful data")
        return False

    def _is_transformation_default(self, original_value: Any, transformed_value: Any, mapping: FieldMapping) -> bool:
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
        # Use centralized element filtering for robust extraction of address records
        if hasattr(self, '_current_xml_root') and self._current_xml_root is not None:
            element_filter = ElementFilter(self.logger)
            try:
                filtered_elements = element_filter.filter_valid_elements(self._current_xml_root)
                valid_addresses = filtered_elements['addresses']
                
                self.logger.debug(f"Processing {len(valid_addresses)} valid address elements")
                
                for addr_elem in valid_addresses:
                    # Get parent contact info
                    parent_contact = addr_elem.getparent()
                    con_id = parent_contact.get('con_id')
                    
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
        # Use centralized element filtering for robust extraction of employment records
        if hasattr(self, '_current_xml_root') and self._current_xml_root is not None:
            element_filter = ElementFilter(self.logger)
            try:
                filtered_elements = element_filter.filter_valid_elements(self._current_xml_root)
                valid_employments = filtered_elements['employments']
                
                self.logger.debug(f"Processing {len(valid_employments)} valid employment elements")
                
                for emp_elem in valid_employments:
                    # Get parent contact info
                    parent_contact = emp_elem.getparent()
                    con_id = parent_contact.get('con_id')
                    
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
        """Get default value for mapping."""
        # TARGETED SUPPRESSION: Only suppress defaults for specific problematic mappings
        # where applying defaults creates meaningless data
        suppress_defaults_for = {
            # Don't apply birth_date default for rmts_info when CB_prescreen_birth_date is missing
            ('/Provenir/Request/CustData/application/rmts_info', 'CB_prescreen_birth_date', 'app_solicited_cc', 'birth_date'),
        }
        
        mapping_key = (mapping.xml_path, mapping.xml_attribute, mapping.target_table, mapping.target_column)
        if mapping_key in suppress_defaults_for:
            self.logger.debug(f"Suppressing default for {mapping.target_table}.{mapping.target_column} when {mapping.xml_attribute} is missing")
            return None
        
        # Check if mapping has a default_value
        if hasattr(mapping, 'default_value') and mapping.default_value:
            return self.transform_data_types(mapping.default_value, mapping.data_type)
        
        # Check default_values configuration
        if mapping.target_column in self._default_values:
            default_val = self._default_values[mapping.target_column]
            return self.transform_data_types(default_val, mapping.data_type)
        
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
            if str_value in bit_map:
                result = bit_map[str_value]
                self.logger.debug(f"Bit conversion: '{str_value}' -> {result}")
                return result
        
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
                return bit_map[str_value]
        
        # Default fallback for common boolean values
        if str_value in ['true', '1', 'yes', 'y']:
            return 1
        elif str_value in ['false', '0', 'no', 'n', '']:
            return 0
        
        # Default to 0 for unknown values
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
            return round(float(value))  # Use round() for proper rounding instead of truncation
        except (ValueError, TypeError):
            return None
    
    def _transform_to_decimal(self, value, target_type):
        """Transform value to decimal with proper NULL handling."""
        if not StringUtils.safe_string_check(value):
            return None  # Return None for missing values - don't default to 0.00
        
        try:
            # Handle empty strings as NULL
            if str(value).strip() == '':
                return None
                
            return float(value)
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Decimal conversion failed for '{value}': {e}")
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
            import re
            # Pattern to match datetime with invalid seconds
            pattern = r'(\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:)(\d{2})(\.\d+)?'
            match = re.match(pattern, datetime_str)
            
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
            
            # Debug: Log all PR contacts found with their key attributes
            self.logger.debug(f"Found {len(pr_contacts)} PR contacts")
            for i, contact in enumerate(pr_contacts):
                con_id = contact.get('con_id', 'UNKNOWN')
                # Check for banking attributes in each contact
                banking_aba = contact.get('banking_aba', 'MISSING')
                banking_account = contact.get('banking_account_number', 'MISSING')
                self.logger.debug(f"PR contact {i}: con_id={con_id}, banking_aba={banking_aba}, banking_account={banking_account}")
            
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
            
            # If the value is empty/None, check if the attribute exists with a different name
            if not value:
                # Check for common attribute name variations
                attribute_variations = [
                    mapping.xml_attribute,
                    mapping.xml_attribute.lower(),
                    mapping.xml_attribute.upper(),
                    mapping.xml_attribute.replace('_', ''),
                    mapping.xml_attribute.replace('sc_bank_', 'banking_'),
                    mapping.xml_attribute.replace('sc_bank_', ''),
                ]
                
                for attr_variant in attribute_variations:
                    variant_value = last_valid_pr_contact.get(attr_variant)
                    if variant_value:
                        self.logger.debug(f"Found value using attribute variant '{attr_variant}': {variant_value}")
                        return variant_value
                
                self.logger.debug(f"No value found for {mapping.xml_attribute} or its variants in contact {selected_con_id}")
            
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
                            context[f'application.{key}'] = value
                    # Also add without prefix for direct access
                    context.update(attrs)
                elif path.endswith('/app_product'):
                    # Add app_product fields with 'app_product.' prefix
                    for key, value in attrs.items():
                        if key and value is not None:
                            context[f'app_product.{key}'] = value
                    # Also add without prefix for direct access
                    context.update(attrs)
        
        self.logger.debug(f"Built app-level context with {len(context)} keys")
        for key in sorted(context.keys())[:10]:  # Log first 10 keys
            self.logger.debug(f"Context key: {key} = {context[key]}")
        
        return context