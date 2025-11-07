"""
Centralized XML Element Filtering Engine

This module provides the authoritative filtering logic for XML elements during parsing,
ensuring only valid, complete elements are processed based on element_filtering contract rules.
It serves as the first quality gate in the XML processing pipeline, preventing invalid
or incomplete data from entering the extraction process.

Key Responsibilities:
- Validates required attributes for contact elements (from contract)
- Filters elements based on valid enum values (from contract)
- Implements "last valid element" logic for duplicate contacts
- Provides filtered element collections to downstream processors
- Logs filtering decisions for audit and debugging purposes

Integration Points:
- Called by XMLParser during selective parsing to determine which elements to extract
- Used by MigrationEngine for contact_address and contact_employment record creation
- Provides filtered collections to DataMapper for relationship-aware processing
- Ensures data integrity before any transformation logic is applied

Contract-Driven:
- Element filtering rules loaded from MappingContract.element_filtering
- Element types (contact, address, employment) defined in contract
- Required attributes and valid values defined in contract (case-insensitive)
- No hard-coded constants - all configuration in contract
"""

import logging
from typing import Dict, List, Any, Optional
from xml_extractor.models import MappingContract


class ValidationError(Exception):
    """Raised when XML validation fails."""
    pass


class ElementFilter:
    """
    Authoritative XML element filtering engine using contract-driven rules.

    This class centralizes all element filtering logic to ensure consistency across the
    entire XML processing pipeline. It validates elements against required attributes
    and valid enum values defined in the MappingContract, implementing the 
    "last valid element" deduplication strategy.

    Filtering is contract-driven:
    - Rules loaded from MappingContract.element_filtering.filter_rules
    - Each rule specifies element_type, xml_path, and required_attributes
    - Required attributes can be either:
      - true: attribute must be present (non-empty)
      - list: attribute value must be in list (case-insensitive comparison)
    
    Processing Strategy:
    1. Extract and validate app_id from Request/@ID
    2. For each element type in contract rules, filter based on required_attributes
    3. Apply "last valid element" logic for contact deduplication
    4. Return filtered collections with comprehensive logging

    This ensures that only high-quality, complete data enters the transformation pipeline,
    preventing downstream issues and maintaining data integrity throughout processing.
    """
    
    def __init__(self, contract: Optional[MappingContract] = None, logger=None):
        """
        Initialize element filter with optional contract configuration.
        
        Args:
            contract: MappingContract with element_filtering rules
            logger: Logger instance (uses default if not provided)
        """
        self.contract = contract
        self.logger = logger or logging.getLogger(__name__)
    
    def filter_valid_elements(self, xml_root) -> Dict[str, Any]:
        """
        Filter XML elements based on contract-defined rules.
        
        Args:
            xml_root: lxml Element representing the XML root
            
        Returns:
            Dict containing filtered valid elements:
            {
                'app_id': str,
                'contacts': List[Element],
                'addresses': List[Element], 
                'employments': List[Element]
            }
            
        Raises:
            ValidationError: If app_id is missing, no valid contacts found, or contract missing
        """
        
        if not self.contract or not self.contract.element_filtering:
            raise ValidationError(
                "ElementFilter requires MappingContract with element_filtering rules"
            )
        
        # Extract app_id (required)
        request_elem = xml_root.find('.//Request')
        app_id = request_elem.get('ID') if request_elem is not None else None
        
        if not app_id:
            raise ValidationError("Missing required app_id (Request/@ID)")
        
        # Process each element type according to contract rules
        filtered_results = {
            'app_id': app_id,
            'contacts': [],
            'addresses': [],
            'employments': []
        }
        
        # Build map of element types to rules for easy lookup
        rules_by_type = {rule.element_type: rule for rule in self.contract.element_filtering.filter_rules}
        
        # First pass: Process contacts
        if 'contact' in rules_by_type:
            contact_rule = rules_by_type['contact']
            temp_valid_contacts = []
            
            # Find all contact elements using XPath from contract
            contact_elements = xml_root.xpath(contact_rule.xml_child_path)
            
            for contact_elem in contact_elements:
                if self._element_passes_filters(contact_elem, contact_rule):
                    temp_valid_contacts.append(contact_elem)
                else:
                    # Log filtered element with friendly identifier (first_name) and validation attributes
                    first_name = contact_elem.get('first_name', 'Unknown')
                    con_id = contact_elem.get('con_id', 'unknown')
                    
                    # Get validation attribute values from contract (grab the attribute names and their filter values)
                    attr_parts = []
                    for attr_name in sorted(contact_rule.required_attributes.keys()):
                        attr_value = contact_elem.get(attr_name, 'unknown')
                        attr_parts.append(f"{attr_name}: {attr_value}")
                    attrs_str = ", ".join(attr_parts)
                    
                    self.logger.warning(
                        f"Filtering out contact {first_name} - {attrs_str}"
                    )
            
            # Apply "last valid element" logic for duplicate contacts
            valid_contacts = self._apply_last_valid_logic(temp_valid_contacts, contact_rule)
            filtered_results['contacts'] = valid_contacts
            
            # Second pass: Process child elements (addresses, employment) from valid contacts only
            for contact_elem in valid_contacts:
                
                # ok to hard-code this: 1. it's just for logging clarity 2. attribute is the same across products
                first_name = contact_elem.get('first_name', 'Unknown')
                
                # Process addresses if rule exists
                if 'address' in rules_by_type:
                    address_rule = rules_by_type['address']
                    # Extract child element name from xml_child_path (last segment)
                    address_elem_name = address_rule.xml_child_path.split('/')[-1]
                    # Get address elements under this contact using dynamic element name
                    address_elements = contact_elem.xpath(f'./{address_elem_name}')
                    
                    for addr_elem in address_elements:
                        if self._element_passes_filters(addr_elem, address_rule):
                            filtered_results['addresses'].append(addr_elem)
                        else:
                            # Get validation attribute values from contract (grab the attribute names and their filter values)
                            attr_parts = []
                            for attr_name in sorted(address_rule.required_attributes.keys()):
                                attr_value = addr_elem.get(attr_name, 'unknown')
                                attr_parts.append(f"{attr_name}: {attr_value}")
                            attrs_str = ", ".join(attr_parts)
                            
                            self.logger.warning(
                                f"Filtering out address for contact {first_name} - {attrs_str}"
                            )
                
                # Process employments if rule exists
                if 'employment' in rules_by_type:
                    employment_rule = rules_by_type['employment']
                    # Extract child element name from xml_child_path (last segment)
                    employment_elem_name = employment_rule.xml_child_path.split('/')[-1]
                    # Get employment elements under this contact using dynamic element name
                    employment_elements = contact_elem.xpath(f'./{employment_elem_name}')
                    
                    for emp_elem in employment_elements:
                        if self._element_passes_filters(emp_elem, employment_rule):
                            filtered_results['employments'].append(emp_elem)
                        else:
                            # Get validation attribute values from contract (grab the attribute names and their filter values)
                            attr_parts = []
                            for attr_name in sorted(employment_rule.required_attributes.keys()):
                                attr_value = emp_elem.get(attr_name, 'unknown')
                                attr_parts.append(f"{attr_name}: {attr_value}")
                            attrs_str = ", ".join(attr_parts)
                            
                            self.logger.warning(
                                f"Filtering out employment for contact {first_name} - {attrs_str}"
                            )
        
        # Final validation: Must have at least one valid contact
        if not filtered_results['contacts']:
            raise ValidationError(f"Application {app_id} has no valid contacts")
        
        self.logger.info(
            f"Filtered elements for app_id {app_id}: "
            f"{len(filtered_results['contacts'])} contacts, "
            f"{len(filtered_results['addresses'])} addresses, "
            f"{len(filtered_results['employments'])} employments"
        )
        
        return filtered_results
    
    def _element_passes_filters(self, element, rule) -> bool:
        """
        Check if an element passes all required_attributes filters.
        
        Args:
            element: lxml Element to validate
            rule: FilterRule from contract
            
        Returns:
            True if element passes all filters, False otherwise
        """
        for attr_name, attr_rule in rule.required_attributes.items():
            attr_value = element.get(attr_name, "")
            
            if attr_rule is True:
                # Attribute must be present and non-empty
                if not attr_value:
                    return False
            elif isinstance(attr_rule, list):
                # Attribute value must be in list (case-insensitive)
                if not attr_value:
                    return False
                # Normalize to uppercase for case-insensitive comparison
                normalized_value = attr_value.upper()
                normalized_valid = [v.upper() for v in attr_rule]
                if normalized_value not in normalized_valid:
                    return False
        
        return True
    
    def _apply_last_valid_logic(self, contacts: List, contact_rule) -> List:
        """
        For duplicate contacts with same identifying attributes, keep only the last occurrence.
        
        This implements the "last valid contact" logic where if there are multiple
        contacts with the same values for all required_attributes, we use the last one
        in document order. The identifying attributes are contract-driven via required_attributes.
        
        Args:
            contacts: List of contact elements to deduplicate
            contact_rule: The contact FilterRule from contract (provides required_attributes)
            
        Returns:
            List of deduplicated contact elements (last occurrence kept)
        """
        contact_map = {}
        
        # Get attribute names from contract (sorted for consistent key ordering)
        attr_names = sorted(contact_rule.required_attributes.keys())
        
        for contact in contacts:
            # Build deduplication key from all required attributes
            attr_values = [str(contact.get(attr, 'None')) for attr in attr_names]
            key = "_".join(attr_values)
            
            first_name = contact.get('first_name', 'Unknown')
            
            # Last occurrence wins (overwrites previous)
            if key in contact_map:
                prev_name = contact_map[key].get('first_name', 'Unknown')
                self.logger.info(
                    f"Applying last valid logic: replacing contact {prev_name} "
                    f"with {first_name} (key: {key})"
                )
            
            contact_map[key] = contact
            
        return list(contact_map.values())