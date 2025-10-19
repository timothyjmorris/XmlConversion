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
        
        # Load enum mappings and validation rules from contract
        self._enum_mappings = {}
        self._bit_conversions = {}
        self._default_values = {}
        self._validation_rules = {}
        
        if mapping_contract_path:
            self._load_contract_configurations(mapping_contract_path)
            self._mapping_contract_path = mapping_contract_path
        else:
            self._mapping_contract_path = None
    
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
                    raise DataMappingError("Could not extract app_id from XML data")
            
            if not valid_contacts:
                # PRE-FLIGHT VALIDATION: Must have app_id and at least one con_id or don't process
                if not self._pre_flight_validation(xml_data):
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
                    self.logger.error(f"Failed to process table {table_name}: {e}")
                    self._validation_errors.append(f"Table processing error for {table_name}: {e}")
                    continue
            
            # Handle relationships and foreign keys
            result_tables = self._apply_relationships(result_tables, contract, xml_data, app_id, valid_contacts)
            
            # NO DEFAULT VALUES APPLIED - only use data from XML mapping
            
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
        if not self._mapping_contract_path:
            raise DataMappingError("No mapping contract path provided during initialization")
        
        # Set the XML root for contact extraction
        if xml_root is not None:
            self._current_xml_root = xml_root
        
        # Load the mapping contract from JSON
        import json
        from ..models import MappingContract, FieldMapping, RelationshipMapping
        
        with open(self._mapping_contract_path, 'r') as f:
            contract_data = json.load(f)
        
        # Create FieldMapping objects
        field_mappings = []
        for mapping in contract_data['mappings']:
            field_mapping = FieldMapping(
                xml_path=mapping['xml_path'],
                target_table=mapping['target_table'],
                target_column=mapping['target_column'],
                data_type=mapping['data_type'],
                xml_attribute=mapping.get('xml_attribute'),
                mapping_type=mapping.get('mapping_type'),
                transformation=mapping.get('transformation')
            )
            field_mappings.append(field_mapping)
        
        # Create RelationshipMapping objects
        relationship_mappings = []
        for relationship in contract_data['relationships']:
            rel_mapping = RelationshipMapping(
                parent_table=relationship['parent_table'],
                child_table=relationship['child_table'],
                foreign_key_column=relationship['foreign_key_column'],
                xml_parent_path=relationship['xml_parent_path'],
                xml_child_path=relationship['xml_child_path']
            )
            relationship_mappings.append(rel_mapping)
        
        mapping_contract = MappingContract(
            source_table=contract_data['source_table'],
            source_column=contract_data['source_column'],
            xml_root_element=contract_data['xml_root_element'],
            mappings=field_mappings,
            relationships=relationship_mappings
        )
        
        # Apply the mapping contract with pre-validated data
        return self.apply_mapping_contract(xml_data, mapping_contract, app_id, valid_contacts)
    
    def apply_mapping_contract_with_validation(self, xml_data: Dict[str, Any], 
                                             contract: MappingContract,
                                             enable_comprehensive_validation: bool = True) -> Dict[str, Any]:
        """
        Apply mapping contract with comprehensive validation integration.
        
        Args:
            xml_data: Parsed XML data
            contract: Mapping contract defining transformations
            enable_comprehensive_validation: Whether to run full validation suite
            
        Returns:
            Dictionary containing extracted tables and validation results
        """
        from ..validation.data_integrity_validator import DataIntegrityValidator
        from ..validation.validation_models import ValidationConfig
        
        # Apply standard mapping
        result_tables = self.apply_mapping_contract(xml_data, contract)
        
        # Perform comprehensive validation if enabled
        validation_result = None
        if enable_comprehensive_validation:
            try:
                validator = DataIntegrityValidator(ValidationConfig())
                validation_result = validator.validate_extraction_results(
                    source_xml_data=xml_data,
                    extracted_tables=result_tables,
                    mapping_contract=contract,
                    source_record_id=self._extract_app_id(xml_data)
                )
                
                # Log validation summary
                if validation_result.validation_passed:
                    self.logger.info(f"Validation passed: {validation_result.total_records_validated} records validated")
                else:
                    self.logger.warning(
                        f"Validation issues found: {validation_result.total_errors} errors, "
                        f"{validation_result.total_warnings} warnings"
                    )
                    
            except Exception as e:
                self.logger.error(f"Comprehensive validation failed: {e}")
        
        return {
            'extracted_tables': result_tables,
            'validation_result': validation_result,
            'transformation_stats': self.get_transformation_stats(),
            'validation_errors': self.get_validation_errors()
        }
    
    def transform_data_types(self, value: Any, target_type: str) -> Any:
        """Transform value to target data type with comprehensive fallback handling."""
        if not StringUtils.safe_string_check(value):
            return None  # Return None to exclude from INSERT - no default values injected
        
        try:
            # Handle string types with length specifications
            if target_type.startswith('varchar') or target_type.startswith('char'):
                return self._transform_to_string(value, target_type)
            
            # Handle numeric types
            elif target_type in ['int', 'smallint', 'bigint']:
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
            return self._get_fallback_value(value, target_type)
    
    def handle_nested_elements(self, parent_id: str, 
                             child_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                
                # Add sequence number for ordering (only if needed by the table)
                # child_record['sequence_number'] = i + 1
                
                # Don't add audit fields automatically - only add fields defined in mapping contract
                
                processed_children.append(child_record)
                
            except Exception as e:
                self.logger.warning(f"Failed to process nested element {i}: {e}")
                # Only create fallback if we have required identifiers
                if 'contact' not in str(child_element) or child_element.get('con_id'):
                    fallback_record = {
                        'app_id': int(parent_id) if parent_id.isdigit() else parent_id
                    }
                    if child_element.get('con_id'):
                        fallback_record['con_id'] = child_element['con_id']
                    processed_children.append(fallback_record)
                continue
        
        return processed_children
    
    # Helper methods
    def _load_contract_configurations(self, contract_path: str) -> None:
        """Load enum mappings and validation rules from mapping contract file."""
        try:
            with open(contract_path, 'r') as f:
                contract_data = json.load(f)
            
            self._enum_mappings = contract_data.get('enum_mappings', {})
            self._bit_conversions = contract_data.get('bit_conversions', {})
            self._default_values = contract_data.get('default_values', {})
            self._validation_rules = contract_data.get('validation_rules', {})
            
            self.logger.info(f"Loaded contract configurations from {contract_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to load contract configurations: {e}")
    
    def _extract_app_id(self, xml_data: Dict[str, Any]) -> Optional[str]:
        """Extract app_id from XML data (compatible with XMLParser flat structure)."""
        try:
            # Try XMLParser flat structure first: /Provenir/Request with attributes
            request_path = '/Provenir/Request'
            if request_path in xml_data:
                request_element = xml_data[request_path]
                if isinstance(request_element, dict) and 'attributes' in request_element:
                    attributes = request_element['attributes']
                    if 'ID' in attributes:
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
        - For contact_address: take last 2 valid elements with address_type_enum
        - For contact_employment: take last 2 valid elements with employment_type_enum
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
                    # Apply "last valid element" approach to child elements
                    processed_contact = self._process_contact_with_last_valid_children(contact)
                    valid_contacts.append(processed_contact)
                    
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
    
    def _process_contact_with_last_valid_children(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process contact and apply 'last valid element' approach to child elements.
        
        For contact_address and contact_employment, only keep the last 2 valid elements
        that have the required type attributes (address_tp_c, employment_tp_c).
        """
        processed_contact = contact.copy()
        
        # Process contact_address elements - keep last 2 valid with address_tp_c
        if 'contact_address' in contact:
            addresses = contact['contact_address']
            if isinstance(addresses, dict):
                addresses = [addresses]
            elif not isinstance(addresses, list):
                addresses = []
            
            # Filter for valid addresses with address_tp_c
            valid_addresses = []
            for addr in addresses:
                if isinstance(addr, dict) and addr.get('address_tp_c'):
                    valid_addresses.append(addr)
            
            # Keep only the last 2 valid addresses
            processed_contact['contact_address'] = valid_addresses[-2:] if valid_addresses else []
            
            if len(addresses) > len(valid_addresses):
                self.logger.warning(f"Filtered {len(addresses) - len(valid_addresses)} invalid addresses for contact {contact.get('con_id')}")
        
        # Process contact_employment elements - keep last 2 valid with employment_tp_c
        if 'contact_employment' in contact:
            employments = contact['contact_employment']
            if isinstance(employments, dict):
                employments = [employments]
            elif not isinstance(employments, list):
                employments = []
            
            # Filter for valid employments with employment_tp_c
            valid_employments = []
            for emp in employments:
                if isinstance(emp, dict) and emp.get('employment_tp_c'):
                    valid_employments.append(emp)
            
            # Keep only the last 2 valid employments
            processed_contact['contact_employment'] = valid_employments[-2:] if valid_employments else []
            
            if len(employments) > len(valid_employments):
                self.logger.warning(f"Filtered {len(employments) - len(valid_employments)} invalid employments for contact {contact.get('con_id')}")
        
        return processed_contact
    
    def _validate_address_element(self, context_data: Optional[Dict[str, Any]]) -> bool:
        """
        Validate contact_address element has required attributes.
        
        Rules:
        - Must have con_id (cascaded from parent contact)
        - Must have address_tp_c attribute
        
        Args:
            context_data: Contact context containing address data
            
        Returns:
            True if address element should be processed
        """
        if not context_data:
            return False
        
        # Check for cascaded con_id from parent contact
        con_id = context_data.get('con_id')
        if not con_id:
            self.logger.warning("Skipping contact_address - no con_id cascaded from parent contact")
            return False
        
        # Check for required address_tp_c attribute in address elements
        address_elements = context_data.get('contact_address', [])
        if isinstance(address_elements, dict):
            address_elements = [address_elements]
        
        # At least one address element must have address_tp_c
        valid_addresses = [addr for addr in address_elements 
                          if isinstance(addr, dict) and addr.get('address_tp_c')]
        
        if not valid_addresses:
            self.logger.warning(f"Skipping contact_address for con_id {con_id} - no address_tp_c attribute found")
            return False
        
        return True
    
    def _validate_employment_element(self, context_data: Optional[Dict[str, Any]]) -> bool:
        """
        Validate contact_employment element has required attributes.
        
        Rules:
        - Must have con_id (cascaded from parent contact)
        - Must have employment_tp_c attribute
        
        Args:
            context_data: Contact context containing employment data
            
        Returns:
            True if employment element should be processed
        """
        if not context_data:
            return False
        
        # Check for cascaded con_id from parent contact
        con_id = context_data.get('con_id')
        if not con_id:
            self.logger.warning("Skipping contact_employment - no con_id cascaded from parent contact")
            return False
        
        # Check for required employment_tp_c attribute in employment elements
        employment_elements = context_data.get('contact_employment', [])
        if isinstance(employment_elements, dict):
            employment_elements = [employment_elements]
        
        # At least one employment element must have employment_tp_c
        valid_employments = [emp for emp in employment_elements 
                           if isinstance(emp, dict) and emp.get('employment_tp_c')]
        
        if not valid_employments:
            self.logger.warning(f"Skipping contact_employment for con_id {con_id} - no employment_tp_c attribute found")
            return False
        
        return True
    
    def _extract_contact_address_records(self, xml_data: Dict[str, Any], mappings: List[FieldMapping], 
                                       app_id: str, valid_contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract contact_address records using centralized element filtering."""
        records = []
        
        # Use centralized element filtering
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
                    # Ensure proper encoding for string attributes
                    attributes = {}
                    for key, value in addr_elem.attrib.items():
                        if isinstance(value, str):
                            # Ensure proper UTF-8 encoding
                            try:
                                attributes[key] = value.encode('utf-8').decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                attributes[key] = value
                        else:
                            attributes[key] = value
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
        
        # Use centralized element filtering
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
                    # Ensure proper encoding for string attributes
                    attributes = {}
                    for key, value in emp_elem.attrib.items():
                        if isinstance(value, str):
                            # Ensure proper UTF-8 encoding
                            try:
                                attributes[key] = value.encode('utf-8').decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                attributes[key] = value
                        else:
                            attributes[key] = value
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
        if table_name == 'contact_address':
            if not self._validate_address_element(context_data):
                return {}  # Skip this address element
        elif table_name == 'contact_employment':
            if not self._validate_employment_element(context_data):
                return {}  # Skip this employment element
        elif table_name in ['contact_base']:
            if not context_data or not context_data.get('con_id'):
                self.logger.warning(f"Skipping {table_name} record - no con_id in context")
                return {}  # Skip contact without con_id
        
        for mapping in mappings:
            try:
                # Extract value from XML data
                value = self._extract_value_from_xml(xml_data, mapping, context_data)
                
                # Transform the value according to mapping rules
                transformed_value = self._apply_field_transformation(value, mapping, context_data)
                
                # Add to record
                record[mapping.target_column] = transformed_value
                
                self._transformation_stats['type_conversions'] += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to apply mapping for {mapping.xml_path}.{mapping.xml_attribute}: {e}")
                # Apply fallback strategy
                fallback_value = self._get_fallback_for_mapping(mapping, e)
                record[mapping.target_column] = fallback_value
                self._transformation_stats['fallback_values'] += 1
        
        return record
    
    def _validate_required_identifiers(self, xml_data: Dict[str, Any], 
                                     contract: MappingContract, app_id: str, 
                                     valid_contacts: List[Dict[str, Any]]) -> bool:
        """
        Validate that required identifiers exist in XML data.
        This is now redundant since pre-flight validation handles this,
        but kept for additional validation rules.
        """
        # Validate app_id range if specified
        if app_id and 'app_id_validation' in self._validation_rules:
            app_id_rules = self._validation_rules['app_id_validation']
            try:
                app_id_int = int(app_id)
                if app_id_int < app_id_rules.get('min_value', 1) or app_id_int > app_id_rules.get('max_value', 999999999):
                    self._validation_errors.append(f"app_id {app_id} is outside valid range")
                    return False
            except ValueError:
                self._validation_errors.append(f"app_id {app_id} is not a valid integer")
                return False
        
        # Validate con_id ranges if specified
        if valid_contacts and 'con_id_validation' in self._validation_rules:
            con_id_rules = self._validation_rules['con_id_validation']
            for contact in valid_contacts:
                con_id = contact.get('con_id')
                if con_id:
                    try:
                        con_id_int = int(con_id)
                        if con_id_int < con_id_rules.get('min_value', 1) or con_id_int > con_id_rules.get('max_value', 999999999):
                            self._validation_errors.append(f"con_id {con_id} is outside valid range")
                            return False
                    except ValueError:
                        self._validation_errors.append(f"con_id {con_id} is not a valid integer")
                        return False
        
        return True
    
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
                        if mapping.xml_attribute in attributes:
                            return attributes[mapping.xml_attribute]
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
                        # Extract attribute if specified
                        if mapping.xml_attribute and isinstance(current_data, dict):
                            if mapping.xml_attribute in current_data:
                                return current_data[mapping.xml_attribute]
                            elif 'attributes' in current_data and mapping.xml_attribute in current_data['attributes']:
                                return current_data['attributes'][mapping.xml_attribute]
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
            
            # Extract attribute if specified
            if mapping.xml_attribute and current_data is not None:
                if isinstance(current_data, dict):
                    # First try direct attribute access
                    if mapping.xml_attribute in current_data:
                        return current_data[mapping.xml_attribute]
                    # Then try attributes dictionary (XMLParser structure)
                    elif 'attributes' in current_data and mapping.xml_attribute in current_data['attributes']:
                        return current_data['attributes'][mapping.xml_attribute]
                elif isinstance(current_data, list):
                    for item in current_data:
                        if isinstance(item, dict):
                            if mapping.xml_attribute in item:
                                return item[mapping.xml_attribute]
                            elif 'attributes' in item and mapping.xml_attribute in item['attributes']:
                                return item['attributes'][mapping.xml_attribute]
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
        
        elif mapping.mapping_type == 'last_valid_pr_contact_address':
            # Extract value from the last valid PR contact's contact_address elements
            result = self._extract_from_last_valid_pr_contact_address(mapping)
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
        
        if not StringUtils.safe_string_check(value):
            return self._get_default_for_mapping(mapping)
        
        try:
            if hasattr(mapping, 'mapping_type') and mapping.mapping_type:
                if mapping.mapping_type == 'enum':
                    result = self._apply_enum_mapping(value, mapping)
                    self._transformation_stats['enum_mappings'] += 1
                    return result
                elif mapping.mapping_type == 'char_to_bit':
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
        str_value = str(value).strip() if value is not None else ''

        
        # Determine enum type from target column name
        enum_type = self._determine_enum_type(mapping.target_column)
        
        # Debug logging
        self.logger.debug(f"Enum mapping: value='{str_value}', column={mapping.target_column}, enum_type={enum_type}")
        self.logger.debug(f"Available enum types: {list(self._enum_mappings.keys())}")
        
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
        
        # No valid enum mapping found - return None to exclude column from INSERT
        self.logger.warning(f"No enum mapping found for value '{str_value}' in column {mapping.target_column}, enum_type={enum_type} - excluding column")

        return None
    
    def _extract_from_last_valid_pr_contact(self, mapping: FieldMapping) -> Any:
        """Extract value from the last valid PR contact's app_prod_bcard element."""
        if not hasattr(self, '_current_xml_root') or self._current_xml_root is None:
            self.logger.warning(f"No XML root available for last_valid_pr_contact mapping: {mapping.target_column}")
            return None
        
        try:
            # Find all PR contacts
            pr_contacts = self._current_xml_root.xpath("//contact[@ac_role_tp_c='PR']")
            
            if not pr_contacts:
                self.logger.warning(f"No PR contacts found for last_valid_pr_contact mapping: {mapping.target_column}")
                return None
            
            # Get the last valid PR contact (following the same logic as validation)
            last_valid_pr_contact = None
            for contact in pr_contacts:
                con_id = contact.get('con_id')
                if con_id and con_id.strip():  # Valid contact has non-empty con_id
                    last_valid_pr_contact = contact
            
            if last_valid_pr_contact is None:
                self.logger.warning(f"No valid PR contact found for last_valid_pr_contact mapping: {mapping.target_column}")
                return None
            
            # Find the app_prod_bcard element within this contact
            app_prod_bcard = last_valid_pr_contact.find('app_prod_bcard')
            if app_prod_bcard is None:
                self.logger.warning(f"No app_prod_bcard found in last valid PR contact for: {mapping.target_column}")
                return None
            
            # Extract the specific attribute
            # The xml_attribute should be just the attribute name (e.g., "residence_monthly_pymnt")
            attribute_name = mapping.xml_attribute
            value = app_prod_bcard.get(attribute_name)
            
            if StringUtils.safe_string_check(value):
                self.logger.debug(f"Extracted from last valid PR contact app_prod_bcard: {attribute_name} = {value}")
                return value
            else:
                self.logger.debug(f"Empty value from last valid PR contact app_prod_bcard: {attribute_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting from last valid PR contact for {mapping.target_column}: {e}")
            return None
    
    def _extract_from_last_valid_pr_contact_address(self, mapping: FieldMapping) -> Any:
        """Extract value from the last valid PR contact's contact_address elements."""
        try:
            if not hasattr(self, '_current_xml_root') or self._current_xml_root is None:
                self.logger.warning(f"No XML root available for last_valid_pr_contact_address mapping: {mapping.target_column}")
                return None
            
            # Find all PR contacts
            pr_contacts = self._current_xml_root.xpath("//contact[@ac_role_tp_c='PR']")
            
            if not pr_contacts:
                self.logger.warning(f"No PR contacts found for last_valid_pr_contact_address mapping: {mapping.target_column}")
                return None
            
            # Get the last valid PR contact (following the same logic as validation)
            last_valid_pr_contact = None
            for contact in pr_contacts:
                con_id = contact.get('con_id')
                if con_id and con_id.strip():  # Valid contact has non-empty con_id
                    last_valid_pr_contact = contact
            
            if last_valid_pr_contact is None:
                self.logger.warning(f"No valid PR contact found for last_valid_pr_contact_address mapping: {mapping.target_column}")
                return None
            
            # Find all contact_address elements within this contact
            contact_addresses = last_valid_pr_contact.findall('contact_address')
            if not contact_addresses:
                self.logger.warning(f"No contact_address found in last valid PR contact for: {mapping.target_column}")
                return None
            
            # Look for the attribute in all address elements, return first non-empty value
            attribute_name = mapping.xml_attribute
            for address in contact_addresses:
                value = address.get(attribute_name)
                if StringUtils.safe_string_check(value):
                    self.logger.debug(f"Extracted from last valid PR contact address: {attribute_name} = {value}")
                    return value
            
            self.logger.debug(f"No value found in any address for attribute: {attribute_name}")
            return None
                
        except Exception as e:
            self.logger.error(f"Error extracting from last valid PR contact address for {mapping.target_column}: {e}")
            return None
    
    def _extract_from_curr_address_only(self, mapping: FieldMapping, context_data: Dict[str, Any]) -> Any:
        """Extract value from the current contact's CURR address only."""
        try:
            # We need to get the current contact from context_data
            if not context_data or 'contact_element' not in context_data:
                self.logger.warning(f"No contact element in context for curr_address_only mapping: {mapping.target_column}")
                return None
            
            contact_element = context_data['contact_element']
            
            # Find all contact_address elements within this contact
            contact_addresses = contact_element.findall('contact_address')
            if not contact_addresses:
                self.logger.debug(f"No contact_address found in contact for: {mapping.target_column}")
                return None
            
            # Look for the CURR address specifically
            attribute_name = mapping.xml_attribute
            for address in contact_addresses:
                address_type = address.get('address_tp_c')
                if address_type == 'CURR':
                    value = address.get(attribute_name)
                    if StringUtils.safe_string_check(value):
                        self.logger.debug(f"Extracted from CURR address: {attribute_name} = {value}")
                        return value
            
            self.logger.debug(f"No CURR address found or no value for attribute: {attribute_name}")
            return None
                
        except Exception as e:
            self.logger.error(f"Error extracting from CURR address for {mapping.target_column}: {e}")
            return None

                
        except Exception as e:
            self.logger.error(f"Error extracting from CURR address for {mapping.target_column}: {e}")
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
    
    def _apply_bit_conversion(self, value: Any) -> int:
        """Apply bit conversion transformation using loaded bit conversion mappings."""
        if value is None:
            return None  # Return None to exclude from INSERT - no default values
        
        str_value = str(value).strip() if value is not None else ''
        
        # Use loaded bit conversion mappings
        char_to_bit = self._bit_conversions.get('char_to_bit', {})
        boolean_to_bit = self._bit_conversions.get('boolean_to_bit', {})
        
        # Try char_to_bit mapping first
        if str_value in char_to_bit:
            return char_to_bit[str_value]
        
        # Try boolean_to_bit mapping
        if str_value.lower() in boolean_to_bit:
            return boolean_to_bit[str_value.lower()]
        
        # Fallback to standard bit conversion logic
        if isinstance(value, bool):
            return 1 if value else 0
        
        str_value_upper = str_value.upper()
        if str_value_upper in ['1', 'TRUE', 'YES', 'Y', 'ON']:
            return 1
        elif str_value_upper in ['0', 'FALSE', 'NO', 'N', 'OFF']:
            return 0
        elif str_value_upper == '':
            return None  # Return None for empty strings to exclude from INSERT
        else:
            self.logger.warning(f"Unknown bit conversion value: '{str_value}', excluding from INSERT")
            return None  # Return None to exclude from INSERT - no default values
    
    def _extract_numbers_only(self, value: Any) -> str:
        """Extract only numeric characters from value."""
        return StringUtils.extract_numbers_only(value)
    
    def _extract_numeric_value(self, value: Any) -> int:
        """Extract numeric value from text like 'Up to $40' -> 40."""
        return StringUtils.extract_numeric_value(value)
    
    def _find_or_create_record(self, table_records: List[Dict[str, Any]], 
                              mapping: FieldMapping, xml_data: Dict[str, Any]) -> Dict[str, Any]:
        """Find existing record or create new one for the target table."""
        record = {}
        table_records.append(record)
        return record
    
    def _apply_relationships(self, result_tables: Dict[str, List[Dict[str, Any]]], 
                           contract: MappingContract, xml_data: Dict[str, Any],
                           app_id: str, valid_contacts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Apply relationship mappings to establish foreign key relationships."""
        for relationship in contract.relationships:
            try:
                parent_table = relationship.parent_table
                child_table = relationship.child_table
                fk_column = relationship.foreign_key_column
                
                if parent_table in result_tables and child_table in result_tables:
                    parent_records = result_tables[parent_table]
                    child_records = result_tables[child_table]
                    
                    # Handle app_base -> other tables relationships
                    if parent_table == 'app_base':
                        for child_record in child_records:
                            if fk_column not in child_record and app_id:
                                child_record[fk_column] = int(app_id) if app_id.isdigit() else app_id
                    
                    # Handle contact_base -> contact_* tables relationships
                    elif parent_table == 'contact_base':
                        for child_record in child_records:
                            if fk_column not in child_record:
                                # Match child records to contact records by con_id
                                if 'con_id' in child_record:
                                    child_record[fk_column] = child_record['con_id']
                                else:
                                    self.logger.warning(f"Child record in {child_table} missing con_id for relationship")
                    
                    # Generic relationship handling
                    else:
                        for parent_record in parent_records:
                            parent_id = self._get_primary_key_value(parent_record, parent_table)
                            
                            for child_record in child_records:
                                if fk_column not in child_record and parent_id:
                                    child_record[fk_column] = parent_id
                                    
            except Exception as e:
                self.logger.warning(f"Failed to apply relationship {relationship.parent_table}->{relationship.child_table}: {e}")
                continue
        
        return result_tables
    
    def _apply_calculated_fields(self, result_tables: Dict[str, List[Dict[str, Any]]], 
                               contract: MappingContract, xml_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Apply calculated field transformations."""
        # NO DEFAULT VALUES INJECTED - only use data from XML mapping contract
        # Don't add audit timestamps - these columns don't exist in the target database schema
        # Only add fields that are explicitly defined in the mapping contract
        pass
        
        return result_tables
    
    # REMOVED: _apply_default_values method - no default values injected
    
    def _validate_data_integrity(self, result_tables: Dict[str, List[Dict[str, Any]]], 
                               contract: MappingContract) -> None:
        """Validate data integrity and quality with detailed error reporting."""
        try:
            # Validate required fields are present
            for table_name, records in result_tables.items():
                for i, record in enumerate(records):
                    # Check for required primary keys
                    if table_name == 'app_base' and 'app_id' not in record:
                        self._validation_errors.append(f"Missing app_id in {table_name} record {i}")
                    elif table_name == 'contact_base' and 'con_id' not in record:
                        self._validation_errors.append(f"Missing con_id in {table_name} record {i}")
                    
                    # Validate SSN format if present
                    if 'ssn' in record and record['ssn']:
                        if not self._validate_ssn(record['ssn']):
                            self._validation_errors.append(f"Invalid SSN format in {table_name} record {i}: {record['ssn']}")
                    
                    # Validate foreign key relationships
                    if table_name != 'app_base' and 'app_id' in record and not record['app_id']:
                        self._validation_errors.append(f"Missing app_id foreign key in {table_name} record {i}")
            
            # Validate referential integrity
            self._validate_referential_integrity(result_tables)
            
            # Log validation summary
            if self._validation_errors:
                self.logger.warning(f"Data integrity validation found {len(self._validation_errors)} issues")
            else:
                self.logger.info("Data integrity validation passed")
                
        except Exception as e:
            self.logger.error(f"Data integrity validation failed: {e}")
            self._validation_errors.append(f"Validation process error: {e}")
    
    def _validate_ssn(self, ssn: str) -> bool:
        """Validate SSN format and exclude invalid patterns."""
        if not ssn or len(ssn) != 9:
            return False
        
        if not ssn.isdigit():
            return False
        
        # Check against excluded values from validation rules
        excluded_ssns = self._validation_rules.get('ssn_validation', {}).get('exclude_values', [])
        if ssn in excluded_ssns:
            return False
        
        return True
    
    def _validate_referential_integrity(self, result_tables: Dict[str, List[Dict[str, Any]]]) -> None:
        """Validate foreign key relationships between tables."""
        try:
            # Get all app_ids from app_base
            app_ids = set()
            if 'app_base' in result_tables:
                app_ids = {record.get('app_id') for record in result_tables['app_base'] if record.get('app_id')}
            
            # Get all con_ids from contact_base
            con_ids = set()
            if 'contact_base' in result_tables:
                con_ids = {record.get('con_id') for record in result_tables['contact_base'] if record.get('con_id')}
            
            # Validate app_id foreign keys
            for table_name, records in result_tables.items():
                if table_name != 'app_base':
                    for i, record in enumerate(records):
                        if 'app_id' in record and record['app_id'] not in app_ids:
                            self._validation_errors.append(f"Invalid app_id foreign key in {table_name} record {i}: {record['app_id']}")
            
            # Validate con_id foreign keys
            contact_tables = ['contact_address', 'contact_employment']
            for table_name in contact_tables:
                if table_name in result_tables:
                    for i, record in enumerate(result_tables[table_name]):
                        if 'con_id' in record and record['con_id'] not in con_ids:
                            self._validation_errors.append(f"Invalid con_id foreign key in {table_name} record {i}: {record['con_id']}")
                            
        except Exception as e:
            self.logger.warning(f"Referential integrity validation failed: {e}")
            self._validation_errors.append(f"Referential integrity check error: {e}")
    
    def _get_primary_key_value(self, record: Dict[str, Any], table_name: str) -> Any:
        """Get the primary key value for a record."""
        if table_name == 'app_base':
            return record.get('app_id')
        elif table_name == 'contact_base':
            return record.get('con_id')
        else:
            for key in record.keys():
                if 'id' in key.lower():
                    return record[key]
        return None
    
    def _get_default_for_type(self, target_type: str, column_name: str = None) -> Any:
        """Get default value for a data type."""
        # For enum columns, return None to exclude from INSERT if no valid mapping
        if column_name and column_name.endswith('_enum'):

            return None
        
        # NO DEFAULT VALUES - always return None to exclude from INSERT
        return None
    
    def _get_default_for_mapping(self, mapping: FieldMapping) -> Any:
        """Get default value for a specific mapping."""
        # NO DEFAULT VALUES - return None to exclude from INSERT
        
        # Check for enum defaults
        enum_type = self._determine_enum_type(mapping.target_column)
        if enum_type and enum_type in self._enum_mappings and '' in self._enum_mappings[enum_type]:
            return self._enum_mappings[enum_type]['']
        
        # Return None to exclude from INSERT - no default values injected
        return None
    
    def _get_fallback_for_mapping(self, mapping: FieldMapping, error: Exception) -> Any:
        """Get fallback value when mapping fails."""
        self.logger.warning(f"Using fallback value for {mapping.target_column} due to error: {error}")
        
        # Use default value as fallback
        fallback = self._get_default_for_mapping(mapping)
        
        # Log the fallback strategy used
        self.logger.info(f"Applied fallback value {fallback} for {mapping.target_column}")
        
        return fallback
    
    def _get_fallback_value(self, original_value: Any, target_type: str) -> Any:
        """Get fallback value when type conversion fails."""
        self.logger.warning(f"Conversion failed, excluding from INSERT: {original_value} -> {target_type}")
        return None  # Return None to exclude from INSERT - no default values injected
    
    def _transform_to_string(self, value: Any, target_type: str) -> str:
        """Transform value to string with length constraints."""
        str_value = str(value) if value is not None else ''
        
        if '(' in target_type:
            length_str = target_type.split('(')[1].split(')')[0]
            try:
                max_length = int(length_str)
                return str_value[:max_length]
            except ValueError:
                pass
        
        return str_value
    
    def _transform_to_integer(self, value: Any) -> int:
        """Transform value to integer."""
        result = ValidationUtils.safe_int_conversion(value)
        if result is not None:
            return result
        raise ValueError(f"Cannot convert '{value}' to integer")
    
    def _transform_to_decimal(self, value: Any, target_type: str) -> float:
        """Transform value to float for SQL Server compatibility (no Python Decimal objects)."""
        result = ValidationUtils.safe_float_conversion(value)
        if result is not None:
            return result
        raise ValueError(f"Cannot convert '{value}' to decimal")
    
    def _transform_to_datetime(self, value: Any, target_type: str) -> str:
        """Transform value to datetime string format for SQL Server compatibility."""
        if isinstance(value, datetime):
            # Convert datetime object to SQL Server compatible string format
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, date):
            # Convert date object to SQL Server compatible string format
            return value.strftime('%Y-%m-%d')
        
        str_value = str(value).strip()
        
        # Try to parse using dateutil for flexible parsing
        try:
            from dateutil import parser
            parsed_dt = parser.parse(str_value)
            return parsed_dt.strftime('%Y-%m-%d %H:%M:%S')
        except ImportError:
            # Fallback to manual parsing if dateutil is not available
            pass
        except Exception:
            # Continue to manual parsing if dateutil fails
            pass
        
        # Manual parsing with various formats
        formats = [
            '%Y-%m-%d %H:%M:%S.%f',  # 2023-09-21 08:46:18.164
            '%Y-%m-%d %H:%M:%S',     # 2023-09-21 08:46:18
            '%Y-%m-%d',              # 2023-09-21
            '%m/%d/%Y',              # 09/21/2023
            '%m/%d/%Y %H:%M:%S',     # 09/21/2023 08:46:18
            '%Y-%m-%dT%H:%M:%S',     # 2023-09-21T08:46:18
            '%Y-%m-%dT%H:%M:%SZ',    # 2023-09-21T08:46:18Z
        ]
        
        for fmt in formats:
            try:
                parsed_dt = datetime.strptime(str_value, fmt)
                return parsed_dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        
        # Try to handle flexible formats manually
        try:
            # Handle formats like "2023-9-21 8:46:18.55"
            import re
            # Match pattern: YYYY-M-D H:M:S.f or YYYY-MM-DD HH:MM:SS.fff
            pattern = r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})(?:\.(\d+))?'
            match = re.match(pattern, str_value)
            if match:
                year, month, day, hour, minute, second, microsecond = match.groups()
                microsecond = int((microsecond or '0').ljust(6, '0')[:6])  # Pad or truncate to 6 digits
                parsed_dt = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), microsecond)
                return parsed_dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass
        
        raise ValueError(f"Cannot convert '{value}' to datetime")
    
    def _transform_to_bit(self, value: Any) -> int:
        """Transform value to bit (0 or 1)."""
        if isinstance(value, bool):
            return 1 if value else 0
        
        str_value = str(value).strip().upper()
        
        if str_value in ['1', 'TRUE', 'YES', 'Y', 'ON']:
            return 1
        elif str_value in ['0', 'FALSE', 'NO', 'N', 'OFF']:
            return 0
        elif str_value == '':
            return None  # Return None for empty strings to exclude from INSERT
        else:
            return None  # Return None for unknown values to exclude from INSERT
    
    def _transform_to_boolean(self, value: Any) -> bool:
        """Transform value to boolean."""
        if isinstance(value, bool):
            return value
        
        str_value = str(value).strip().upper()
        return str_value in ['1', 'TRUE', 'YES', 'Y', 'ON']
    

    
    def get_transformation_stats(self) -> Dict[str, int]:
        """Get current transformation statistics."""
        return self._transformation_stats.copy()
    
    def get_validation_errors(self) -> List[str]:
        """Get current validation errors."""
        return self._validation_errors.copy()
    
    def reset_stats(self) -> None:
        """Reset transformation statistics."""
        self._transformation_stats = {
            'records_processed': 0,
            'records_successful': 0,
            'records_failed': 0,
            'type_conversions': 0,
            'enum_mappings': 0,
            'bit_conversions': 0
        }
        self._validation_errors.clear()
    
    def validate_mapping_contract(self, contract: MappingContract) -> List[str]:
        """Validate mapping contract completeness and correctness."""
        validation_errors = []
        
        try:
            # Check required fields
            if not contract.source_table:
                validation_errors.append("Missing source_table in mapping contract")
            if not contract.source_column:
                validation_errors.append("Missing source_column in mapping contract")
            if not contract.mappings:
                validation_errors.append("No field mappings defined in contract")
            
            # Validate each mapping
            for i, mapping in enumerate(contract.mappings):
                if not mapping.xml_path:
                    validation_errors.append(f"Missing xml_path in mapping {i}")
                if not mapping.target_table:
                    validation_errors.append(f"Missing target_table in mapping {i}")
                if not mapping.target_column:
                    validation_errors.append(f"Missing target_column in mapping {i}")
                if not mapping.data_type:
                    validation_errors.append(f"Missing data_type in mapping {i}")
            
            # Validate relationships
            for i, relationship in enumerate(contract.relationships):
                if not all([relationship.parent_table, relationship.child_table, relationship.foreign_key_column]):
                    validation_errors.append(f"Incomplete relationship definition {i}")
            
            self.logger.info(f"Mapping contract validation completed with {len(validation_errors)} errors")
            
        except Exception as e:
            validation_errors.append(f"Contract validation error: {e}")
        
        return validation_errors
    

    def apply_quality_checks(self, result_tables: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Apply comprehensive data quality checks and return quality report."""
        quality_report = {
            'total_records': 0,
            'tables_processed': len(result_tables),
            'quality_issues': [],
            'completeness_score': 0.0,
            'accuracy_score': 0.0
        }
        
        try:
            total_fields = 0
            complete_fields = 0
            
            for table_name, records in result_tables.items():
                quality_report['total_records'] += len(records)
                
                for i, record in enumerate(records):
                    # Check field completeness
                    for field_name, field_value in record.items():
                        total_fields += 1
                        if field_value is not None and field_value != '':
                            complete_fields += 1
                        else:
                            quality_report['quality_issues'].append(
                                f"Empty field {field_name} in {table_name} record {i}"
                            )
                    
                    # Check data type consistency
                    self._check_data_type_consistency(record, table_name, i, quality_report)
            
            # Calculate quality scores
            if total_fields > 0:
                quality_report['completeness_score'] = (complete_fields / total_fields) * 100
            
            # Accuracy score based on validation errors
            total_checks = total_fields + len(self._validation_errors)
            if total_checks > 0:
                quality_report['accuracy_score'] = ((total_checks - len(self._validation_errors)) / total_checks) * 100
            
            self.logger.info(f"Quality check completed: {quality_report['completeness_score']:.1f}% complete, "
                           f"{quality_report['accuracy_score']:.1f}% accurate")
            
        except Exception as e:
            quality_report['quality_issues'].append(f"Quality check error: {e}")
            self.logger.error(f"Quality check failed: {e}")
        
        return quality_report
    
    def _check_data_type_consistency(self, record: Dict[str, Any], table_name: str, 
                                   record_index: int, quality_report: Dict[str, Any]) -> None:
        """Check data type consistency for record fields."""
        try:
            # Check integer fields
            int_fields = ['app_id', 'con_id', 'months_at_address', 'months_at_job']
            for field in int_fields:
                if field in record and record[field] is not None:
                    if not isinstance(record[field], int):
                        try:
                            int(record[field])
                        except (ValueError, TypeError):
                            quality_report['quality_issues'].append(
                                f"Invalid integer value in {table_name}.{field} record {record_index}: {record[field]}"
                            )
            
            # Check date fields
            date_fields = ['receive_date', 'birth_date', 'last_updated_date', 'created_date']
            for field in date_fields:
                if field in record and record[field] is not None:
                    if not isinstance(record[field], (datetime, date)):
                        quality_report['quality_issues'].append(
                            f"Invalid date value in {table_name}.{field} record {record_index}: {record[field]}"
                        )
            
            # Check enum fields (should be integers)
            enum_fields = [f for f in record.keys() if f.endswith('_enum')]
            for field in enum_fields:
                if field in record and record[field] is not None:
                    if not isinstance(record[field], int):
                        quality_report['quality_issues'].append(
                            f"Invalid enum value in {table_name}.{field} record {record_index}: {record[field]}"
                        )
                        
        except Exception as e:
            quality_report['quality_issues'].append(f"Data type check error for {table_name} record {record_index}: {e}")
    
