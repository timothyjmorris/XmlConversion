"""
Centralized XML Element Filtering Engine

This module provides the authoritative filtering logic for XML elements during parsing,
ensuring only valid, complete elements are processed based on strict data-model.md rules.
It serves as the first quality gate in the XML processing pipeline, preventing invalid
or incomplete data from entering the extraction process.

Key Responsibilities:
- Validates required attributes (con_id, ac_role_tp_c) for contact elements
- Filters elements based on valid enum values from data-model.md
- Implements "last valid element" logic for duplicate contacts
- Provides filtered element collections to downstream processors
- Logs filtering decisions for audit and debugging purposes

Integration Points:
- Called by XMLParser during selective parsing to determine which elements to extract
- Used by MigrationEngine for contact_address and contact_employment record creation
- Provides filtered collections to DataMapper for relationship-aware processing
- Ensures data integrity before any transformation logic is applied
"""

import logging
from typing import Dict, List, Any


class ValidationError(Exception):
    """Raised when XML validation fails."""
    pass


class ElementFilter:
    """
    Authoritative XML element filtering engine implementing data-model.md validation rules.

    This class centralizes all element filtering logic to ensure consistency across the
    entire XML processing pipeline. It validates elements against required attributes
    and valid enum values, implementing the "last valid element" deduplication strategy.

    Filtering Rules Applied:
    - Contacts: Must have both con_id AND ac_role_tp_c (PR or AUTHU only)
    - Addresses: Must have valid address_tp_c (CURR, PREV, PATR)
    - Employment: Must have valid employment_tp_c (CURR, PREV)
    - Duplicates: For contacts with same con_id + ac_role_tp_c, keep last occurrence

    Valid Enum Values (from data-model.md):
    - ac_role_tp_c: {"PR", "AUTHU"} (Primary Responsible, Authorized User)
    - address_tp_c: {"CURR", "PREV", "PATR"} (Current, Previous, Parent)
    - employment_tp_c: {"CURR", "PREV"} (Current, Previous)

    Processing Strategy:
    1. Extract and validate app_id from Request/@ID
    2. Filter contacts based on required attributes and valid enum values
    3. Apply "last valid element" logic for contact deduplication
    4. Filter child elements (addresses, employment) from valid contacts only
    5. Return filtered collections with comprehensive logging

    This ensures that only high-quality, complete data enters the transformation pipeline,
    preventing downstream issues and maintaining data integrity throughout processing.
    """
    
    # Valid enum values from data-model.md
    VALID_AC_ROLE_TP_C = {"PR", "AUTHU"}
    VALID_ADDRESS_TP_C = {"CURR", "PREV", "PATR"}  
    VALID_EMPLOYMENT_TP_C = {"CURR", "PREV"}
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def filter_valid_elements(self, xml_root) -> Dict[str, Any]:
        """
        Filter XML elements based on required attributes and valid values.
        
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
            ValidationError: If app_id is missing or no valid contacts found
        """
        
        # Extract app_id (required)
        request_elem = xml_root.find('.//Request')
        app_id = request_elem.get('ID') if request_elem is not None else None
        
        if not app_id:
            raise ValidationError("Missing required app_id (Request/@ID)")
        
        valid_contacts = []
        valid_addresses = []
        valid_employments = []
        
        # First pass: collect all valid contacts
        temp_valid_contacts = []
        for contact_elem in xml_root.findall('.//contact'):
            con_id = contact_elem.get('con_id')
            ac_role_tp_c = contact_elem.get('ac_role_tp_c')
            first_name = contact_elem.get('first_name', 'Unknown')
            
            # Filter: Must have both con_id AND valid ac_role_tp_c
            if not con_id or ac_role_tp_c not in self.VALID_AC_ROLE_TP_C:
                self.logger.warning(
                    f"Filtering out contact {first_name} - con_id: {con_id}, "
                    f"ac_role_tp_c: {ac_role_tp_c} (must be PR or AUTHU)"
                )
                continue
                
            temp_valid_contacts.append(contact_elem)
        
        # Apply "last valid contact" logic for duplicates FIRST
        valid_contacts = self._apply_last_valid_logic(temp_valid_contacts)
        
        # Second pass: collect addresses and employments ONLY from the final valid contacts
        for contact_elem in valid_contacts:
            first_name = contact_elem.get('first_name', 'Unknown')
            
            # Process child addresses with valid enum values
            for addr_elem in contact_elem.findall('contact_address'):
                address_tp_c = addr_elem.get('address_tp_c')
                if address_tp_c in self.VALID_ADDRESS_TP_C:
                    valid_addresses.append(addr_elem)
                else:
                    self.logger.warning(
                        f"Filtering out address for contact {first_name} - "
                        f"address_tp_c: {address_tp_c} (must be CURR, PREV, or PATR)"
                    )
            
            # Process child employments with valid enum values  
            for emp_elem in contact_elem.findall('contact_employment'):
                employment_tp_c = emp_elem.get('employment_tp_c')
                if employment_tp_c in self.VALID_EMPLOYMENT_TP_C:
                    valid_employments.append(emp_elem)
                else:
                    self.logger.warning(
                        f"Filtering out employment for contact {first_name} - "
                        f"employment_tp_c: {employment_tp_c} (must be CURR or PREV)"
                    )
        
        # Final validation: Must have at least one valid contact
        if not valid_contacts:
            raise ValidationError(f"Application {app_id} has no valid contacts")
        
        self.logger.info(
            f"Filtered elements for app_id {app_id}: "
            f"{len(valid_contacts)} contacts, {len(valid_addresses)} addresses, "
            f"{len(valid_employments)} employments"
        )
        
        return {
            'app_id': app_id,
            'contacts': valid_contacts,
            'addresses': valid_addresses, 
            'employments': valid_employments
        }
    
    def _apply_last_valid_logic(self, contacts: List) -> List:
        """
        For duplicate con_id + ac_role_tp_c, keep only the last occurrence.
        
        This implements the "last valid contact" logic where if there are multiple
        contacts with the same con_id and ac_role_tp_c combination, we use the
        last one in document order.
        """
        contact_map = {}
        
        for contact in contacts:
            con_id = contact.get('con_id')
            ac_role_tp_c = contact.get('ac_role_tp_c')
            first_name = contact.get('first_name', 'Unknown')
            key = f"{con_id}_{ac_role_tp_c}"
            
            # Last occurrence wins (overwrites previous)
            if key in contact_map:
                prev_name = contact_map[key].get('first_name', 'Unknown')
                self.logger.info(
                    f"Applying last valid logic: replacing contact {prev_name} "
                    f"with {first_name} for {key}"
                )
            
            contact_map[key] = contact
            
        return list(contact_map.values())