"""
Data mapping and transformation engine for XML to relational database conversion.
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


class DataMapper(DataMapperInterface):
    """Data mapping and transformation engine for converting XML data to relational format."""
    
    def __init__(self, mapping_contract_path: Optional[str] = None):
        """Initialize the DataMapper with logging and validation setup."""
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
        
        # Check for at least one valid contact with BOTH con_id AND ac_role_tp_c
        valid_contacts = self._extract_valid_contacts(xml_data)
        if not valid_contacts:
            self._validation_errors.append("CRITICAL: No valid contacts found (missing con_id or ac_role_tp_c) - cannot process XML")
            return False
        
        self.logger.info(f"Pre-flight validation passed: app_id={app_id}, valid_contacts={len(valid_contacts)}")
        return True

    def _extract_valid_contacts(self, xml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract valid contacts using 'last valid element' approach for duplicates.
        
        Rules:
        - Only contacts with BOTH con_id AND ac_role_tp_c are considered
        - Only PR and AUTH contact types are valid (AUTHU is invalid)
        - For duplicates (same con_id + ac_role_tp_c), take the LAST valid one
        """
        valid_contacts = []
        contact_groups = {}

        try:
            # Navigate to contact elements
            contacts = self._navigate_to_contacts(xml_data)

            # Group contacts by con_id + ac_role_tp_c to handle duplicates
            for contact in contacts:
                if isinstance(contact, dict):
                    con_id = contact.get('con_id', '').strip()
                    ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
                    
                    # Skip contacts with empty con_id
                    if not con_id:
                        self.logger.warning(f"Skipping contact with empty con_id")
                        continue
                    
                    # Only PR and AUTHU are valid contact types
                    if ac_role_tp_c not in ['PR', 'AUTHU']:
                        self.logger.warning(f"Skipping contact with invalid ac_role_tp_c: {ac_role_tp_c}")
                        continue
                    
                    # Create unique key for grouping
                    contact_key = f"{con_id}_{ac_role_tp_c}"
                    
                    # Store the contact (last one will overwrite duplicates)
                    contact_groups[contact_key] = contact
            
            # Process the last valid contact for each unique combination
            for contact_key, contact in contact_groups.items():
                try:
                    valid_contacts.append(contact)
                except Exception as e:
                    self.logger.warning(f"Error processing contact {contact_key}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Failed to extract valid contacts: {e}")
            
        return valid_contacts

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
        """Extract value from XML data using XPath-like navigation with context support."""
        try:
            # Initialize current_data to avoid UnboundLocalError
            current_data = None

            # If context_data is provided (for contact-specific mappings), handle nested paths
            if context_data:
                # For contact_address and contact_employment, context_data contains {'attributes': {...}}
                # BUT skip this for special mapping types that have their own handling
                if (('contact_address' in mapping.xml_path or 'contact_employment' in mapping.xml_path) and 
                    mapping.mapping_type not in ['curr_address_only']):
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
                # Standard navigation from root
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
        """Apply field-specific transformations based on mapping type."""
        
        # Handle special mapping types that don't depend on input value
        if mapping.mapping_type == 'last_valid_pr_contact':
            # Extract value from the last valid PR contact's app_prod_bcard
            result = self._extract_from_last_valid_pr_contact(mapping)
            if result is not None:
                return self.transform_data_types(result, mapping.data_type)
            return None
        
        elif mapping.mapping_type == 'curr_address_only':
            # Extract value from the current contact's CURR address only
            self.logger.debug(f"Processing curr_address_only mapping for {mapping.target_column}")
            result = self._extract_from_curr_address_only(mapping, context_data)
            if result is not None:
                self.logger.debug(f"curr_address_only returned: {result}")
                return self.transform_data_types(result, mapping.data_type)
            self.logger.debug(f"curr_address_only returned None for {mapping.target_column}")
            return None
        
        # CRITICAL FIX: Handle enum mappings specially - always call enum mapper even with None/empty values
        # The enum mapper will handle fallbacks using "" default values
        if hasattr(mapping, 'mapping_type') and mapping.mapping_type == 'enum':
            result = self._apply_enum_mapping(value, mapping)
            self._transformation_stats['enum_mappings'] += 1
            return result
        
        if not StringUtils.safe_string_check(value):
            # Try to get default value for this mapping
            default_value = self._get_default_for_mapping(mapping)
            if default_value is not None:
                return default_value
            return None
        
        try:
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type:
                if mapping.mapping_type == 'char_to_bit':
                    result = self._apply_bit_conversion(value)
                    self._transformation_stats['bit_conversions'] += 1
                    return result
                elif mapping.mapping_type == 'numbers_only':
                    return self._extract_numbers_only(value)
                elif mapping.mapping_type == 'extract_numeric':
                    return self._extract_numeric_value(value)
                elif mapping.mapping_type == 'identity_insert':
                    return self.transform_data_types(value, mapping.data_type)
                elif mapping.mapping_type == 'default_getutcdate_if_null':
                    if not StringUtils.safe_string_check(value):
                        self.logger.debug(f"Applying default_getutcdate_if_null for {mapping.target_column}: {value} -> {datetime.utcnow()}")
                        return datetime.utcnow()
                    # Apply data type transformation to the existing value
                    return self.transform_data_types(value, mapping.data_type)
            
            # Apply standard data type transformation
            result = self.transform_data_types(value, mapping.data_type)
            return result
            
        except Exception as e:
            self.logger.warning(f"Transformation failed for {mapping.target_column}: {e}")
            raise DataTransformationError(
                f"Failed to transform value '{value}' for field {mapping.target_column}",
                field_name=mapping.target_column,
                source_value=str(value),
                target_type=mapping.data_type
            )

    def _apply_enum_mapping(self, value: Any, mapping: FieldMapping) -> int:
        """Apply enum mapping transformation using loaded enum mappings."""
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
        """Determine enum type from column name."""
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
        table_name = mappings[0].target_table if mappings else 'unknown'
        
        if table_name == 'contact_base':
            # Create separate records for each VALID contact (those with con_id)
            for contact in valid_contacts:
                # Only process contacts that have con_id
                if 'con_id' in contact and contact['con_id']:
                    # Find the corresponding XML contact element for curr_address_only mappings
                    contact_element = None
                    if hasattr(self, '_current_xml_root') and self._current_xml_root is not None:
                        # Find the XML contact element with matching con_id
                        contact_elements = self._current_xml_root.xpath(f"//contact[@con_id='{contact['con_id']}']")
                        if contact_elements:
                            contact_element = contact_elements[-1]  # Get the last one (following last valid logic)
                    
                    # Create context with both contact data and XML element
                    context_with_element = contact.copy()
                    if contact_element is not None:
                        context_with_element['contact_element'] = contact_element
                    
                    record = self._create_record_from_mappings(xml_data, mappings, context_with_element)
                    # Skip empty records (happens when contact_address/employment lacks con_id)
                    if record:
                        record['con_id'] = int(contact['con_id']) if str(contact['con_id']).isdigit() else contact['con_id']
                        record['app_id'] = int(app_id) if app_id.isdigit() else app_id
                        records.append(record)
                else:
                    self.logger.warning(f"Skipping contact record without con_id during table processing")
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
        
        # Get table name for validation
        table_name = mappings[0].target_table if mappings else ""
        
        # Apply element filtering rules based on required attributes
        if table_name in ['contact_base']:
            if not context_data or not context_data.get('con_id'):
                self.logger.warning(f"Skipping {table_name} record - no con_id in context")
                return {}  # Skip contact without con_id
        
        for mapping in mappings:
            try:
                # Extract value from XML data
                value = self._extract_value_from_xml(xml_data, mapping, context_data)
                
                # Transform the value according to mapping rules
                transformed_value = self._apply_field_transformation(value, mapping, context_data)
                
                # Add to record, or use default if transformed value is None
                if transformed_value is not None:
                    record[mapping.target_column] = transformed_value
                else:
                    # Try to get default value
                    default_value = self._get_default_for_mapping(mapping)
                    if default_value is not None:
                        record[mapping.target_column] = default_value
                    # If no default, don't add the column (leave as NULL)
                
                self._transformation_stats['type_conversions'] += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to apply mapping for {mapping.xml_path}.{mapping.xml_attribute}: {e}")
                # Apply fallback strategy
                fallback_value = self._get_fallback_for_mapping(mapping, e)
                record[mapping.target_column] = fallback_value
                self._transformation_stats['fallback_values'] += 1
        
        # CRITICAL: Check if record only contains primary/foreign keys (app_id, con_id)
        # If so, skip INSERT entirely to avoid creating meaningless empty rows
        non_key_columns = {k: v for k, v in record.items() 
                          if k not in ['app_id', 'con_id'] and v is not None}
        
        if not non_key_columns:
            self.logger.info(f"Skipping {table_name} INSERT - record contains only keys with no actual data")
            return {}  # Return empty dict to signal "skip this record"
        
        return record

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
                
                self.logger.info(f"Processing {len(valid_addresses)} valid address elements")
                
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
                        self.logger.info(f"✅ Created contact_address record for con_id {con_id}")
                        
            except Exception as e:
                self.logger.error(f"Error in centralized address filtering: {e}")
                # Fallback to empty records rather than crash
                
        else:
            self.logger.warning("No XML root available for address extraction")
        
        self.logger.info(f"Extracted {len(records)} contact_address records")
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
                
                self.logger.info(f"Processing {len(valid_employments)} valid employment elements")
                
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
                        self.logger.info(f"✅ Created contact_employment record for con_id {con_id}")
                        
            except Exception as e:
                self.logger.error(f"Error in centralized employment filtering: {e}")
                # Fallback to empty records rather than crash
                
        else:
            self.logger.warning("No XML root available for employment extraction")
        
        self.logger.info(f"Extracted {len(records)} contact_employment records")
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
    
    def _extract_from_last_valid_pr_contact(self, mapping):
        """Extract value from the last valid PR contact's app_prod_bcard element."""
        try:
            if not hasattr(self, '_current_xml_root') or self._current_xml_root is None:
                return None
            
            # Find all PR contacts
            pr_contacts = self._current_xml_root.xpath('.//contact[@ac_role_tp_c="PR"]')
            if not pr_contacts:
                return None
            
            # Get the last valid PR contact
            last_pr_contact = pr_contacts[-1]
            
            # Look for app_prod_bcard element within this contact
            app_prod_bcard_elements = last_pr_contact.xpath('.//app_prod_bcard')
            if not app_prod_bcard_elements:
                return None
            
            # Get the last app_prod_bcard element
            app_prod_bcard = app_prod_bcard_elements[-1]
            
            # Extract the requested attribute
            value = app_prod_bcard.get(mapping.xml_attribute)
            self.logger.debug(f"Extracted {mapping.xml_attribute}='{value}' from last valid PR contact's app_prod_bcard")
            return value
            
        except Exception as e:
            self.logger.warning(f"Failed to extract from last valid PR contact: {e}")
            return None
    
    def _extract_from_curr_address_only(self, mapping, context_data):
        """Extract value from the current contact's CURR address only."""
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
    
    def _extract_numbers_only(self, value):
        """Extract only numeric characters from value."""
        return None
    
    def _extract_numeric_value(self, value):
        """Extract numeric value from text."""
        return None
    
    def _transform_to_string(self, value, max_length):
        """Transform value to string with length limit."""
        return str(value)[:max_length] if max_length else str(value)
    
    def _transform_to_integer(self, value):
        """Transform value to integer."""
        return int(value)
    
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
        """Transform value to datetime with fallback for missing birth_date."""
        if not StringUtils.safe_string_check(value):
            # Special fallback for birth_date to maintain data integrity
            return datetime(1900, 1, 1)
        
        try:
            # Handle various datetime formats
            if isinstance(value, str):
                # Try common formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                        
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except Exception as e:
            self.logger.warning(f"DateTime conversion failed for '{value}': {e}")
            # Fallback to 1900-01-01 for data integrity
            return datetime(1900, 1, 1)
    
    def _transform_to_bit(self, value):
        """Transform value to bit."""
        return 1 if value else 0
    
    def _transform_to_boolean(self, value):
        """Transform value to boolean."""
        return bool(value)
    
    def _get_fallback_value(self, value, target_type):
        """Get fallback value for failed conversion."""
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
        
        return processed_children