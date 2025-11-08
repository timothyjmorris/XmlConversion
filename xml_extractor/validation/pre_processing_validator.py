"""
Pre-Processing Validation Framework

This module provides comprehensive validation of XML data and business rules before
any extraction or transformation processing begins. It serves as the initial quality
gate, ensuring that source XML meets minimum requirements for successful processing.

Key Validation Areas:
- XML Structure Integrity: Validates basic XML format and required root elements
- Business Rule Compliance: Ensures required identifiers (app_id) and relationships exist
- Contact Validation: Verifies contact elements have required attributes and valid enum values
- Data Completeness: Checks for minimum viable data to prevent wasted processing
- Graceful Degradation: Allows processing to continue with warnings for non-critical issues

Integration Points:
- Called by CLI tools and batch processors before initiating extraction
- Used by ValidationOrchestrator for comprehensive validation workflows
- Provides ValidationResult with detailed error/warning categorization
- Supports both individual file and batch validation scenarios

The framework implements a "fail fast with detailed feedback" approach, catching
issues early to prevent wasted processing time and providing actionable error messages
for data quality improvement.
"""

import logging

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from ..parsing.xml_parser import XMLParser
from ..mapping.data_mapper import DataMapper
from ..models import MappingContract


@dataclass
class ValidationResult:
    """Result of pre-processing validation."""
    is_valid: bool
    app_id: Optional[str]
    valid_contacts: List[Dict[str, Any]]
    validation_errors: List[str]
    validation_warnings: List[str]
    skipped_elements: Dict[str, List[str]]  # element_type -> list of reasons
    
    @property
    def can_process(self) -> bool:
        """Whether XML can be processed despite warnings - allows graceful degradation for missing contacts."""
        return self.is_valid and self.app_id


class PreProcessingValidator:
    """
    Comprehensive pre-processing validator that ensures XML data meets minimum requirements for extraction.

    This validator performs thorough checks on XML structure and business rules before any
    transformation processing begins. It implements a multi-layered validation approach that
    catches issues early, preventing wasted processing time and providing detailed feedback
    for data quality improvement.

    Validation Layers:
    1. XML Structure: Validates basic XML format, encoding, and required root elements
    2. Business Rules: Ensures required identifiers (app_id) and minimum data requirements
    3. Contact Validation: Verifies contact elements have required attributes and valid values
    4. Relationship Checks: Validates parent-child relationships and data consistency
    5. Graceful Degradation: Allows processing with warnings for non-critical issues

    Key Validation Rules:
    - Must have valid app_id from /Provenir/Request/@ID
    - Must have at least one valid contact with both con_id and ac_role_tp_c
    - Contacts must have valid ac_role_tp_c values (PR, AUTHU)
    - Child elements (addresses, employment) must belong to valid contacts
    - XML must be well-formed and parseable

    Processing Strategy:
    - Fail fast for critical errors (missing app_id, malformed XML)
    - Allow graceful degradation for missing contacts (logs warnings, continues with app-level data)
    - Provide detailed error categorization for debugging and data quality improvement
    - Support both individual file and batch validation scenarios

    Integration Points:
    - Called by CLI tools before initiating extraction workflows
    - Used by ValidationOrchestrator for comprehensive validation pipelines
    - Provides ValidationResult with actionable error and warning details
    - Enables early rejection of invalid data to optimize processing efficiency
    """
    
    def __init__(self, mapping_contract: Optional[MappingContract] = None):
        """Initialize validator with optional mapping contract."""
        self.logger = logging.getLogger(__name__)
        self.parser = XMLParser()
        self.mapper = DataMapper()
        self.mapping_contract = mapping_contract
        
    def validate_xml_for_processing(self, xml_content: str, 
                                  source_record_id: Optional[str] = None) -> ValidationResult:
        """
        Comprehensive validation of XML before processing.
        
        Args:
            xml_content: Raw XML content to validate
            source_record_id: Optional identifier for logging
            
        Returns:
            ValidationResult with detailed validation information
        """
        errors = []
        warnings = []
        skipped_elements = {
            'contacts': [],
            'addresses': [],
            'employments': []
        }
        
        try:
            # Step 1: Basic XML structure validation
            if not self._validate_basic_xml_structure(xml_content):
                return ValidationResult(
                    is_valid=False,
                    app_id=None,
                    valid_contacts=[],
                    validation_errors=["Invalid XML structure or format"],
                    validation_warnings=[],
                    skipped_elements=skipped_elements
                )
            
            # Step 2: Parse XML (use cleaned content)
            try:
                cleaned_content = self._clean_xml_content(xml_content)
                root = self.parser.parse_xml_stream(cleaned_content)
                elements = self.parser.extract_elements(root)
                
                # Store the parsed root for contact extraction
                self._current_xml_root = root
            except Exception as e:
                return ValidationResult(
                    is_valid=False,
                    app_id=None,
                    valid_contacts=[],
                    validation_errors=[f"XML parsing failed: {e}"],
                    validation_warnings=[],
                    skipped_elements=skipped_elements
                )
            
            # Step 3: Convert to data structure
            xml_data = self._convert_elements_to_data_structure(elements)

            # Step 3.5: Defensive schema and product line validation
            app_id = self._extract_and_validate_app_id(xml_data, errors)
            # Check for Rec Lending in nested structure
            has_rec_lending_app = False
            try:
                has_rec_lending_app = (
                    'Provenir' in xml_data and
                    'Request' in xml_data['Provenir'] and
                    'CustData' in xml_data['Provenir']['Request'] and
                    'IL_application' in xml_data['Provenir']['Request']['CustData']
                )
            except Exception:
                pass
            if has_rec_lending_app:
                errors.append(
                    "Unsupported application type: Rec Lending (product_line_enum 601) detected. "
                    "Current version only supports Credit Card (product_line_enum 600). "
                    "Rec Lending and other types will require future enhancements."
                )
            # Check for Credit Card application in nested structure
            has_credit_card_app = False
            try:
                has_credit_card_app = (
                    'Provenir' in xml_data and
                    'Request' in xml_data['Provenir'] and
                    'CustData' in xml_data['Provenir']['Request'] and
                    'application' in xml_data['Provenir']['Request']['CustData']
                )
            except Exception:
                pass
            if not has_credit_card_app:
                errors.append(
                    "Missing required Credit Card application element: /Provenir/Request/CustData/application. "
                    "Current version only supports Credit Card (product_line_enum 600). "
                    "Rec Lending and other types will require future enhancements."
                )
            # Defensive: If app_id is missing or invalid, error is already appended by _extract_and_validate_app_id

            # Step 5: Validate contacts and collect valid ones
            valid_contacts = self._validate_and_collect_contacts(
                xml_data, errors, warnings, skipped_elements
            )
            
            # Step 6: Validate child elements (addresses, employment)
            self._validate_child_elements(
                xml_data, valid_contacts, warnings, skipped_elements
            )
            
            # Step 7: Business rule validation
            self._validate_business_rules(
                xml_data, app_id, valid_contacts, errors, warnings
            )
            
            # Determine if validation passed - allow graceful degradation for missing contacts
            is_valid = len(errors) == 0 and app_id is not None
            
            # Log validation summary
            self._log_validation_summary(
                source_record_id, is_valid, app_id, valid_contacts, 
                errors, warnings, skipped_elements
            )
            
            return ValidationResult(
                is_valid=is_valid,
                app_id=app_id,
                valid_contacts=valid_contacts,
                validation_errors=errors,
                validation_warnings=warnings,
                skipped_elements=skipped_elements
            )
            
        except Exception as e:
            self.logger.error(f"Validation process failed: {e}")
            return ValidationResult(
                is_valid=False,
                app_id=None,
                valid_contacts=[],
                validation_errors=[f"Validation process error: {e}"],
                validation_warnings=[],
                skipped_elements=skipped_elements
            )
    
    def _validate_basic_xml_structure(self, xml_content: str) -> bool:
        """Validate basic XML structure and Provenir format."""
        try:
            # Clean the XML content first to handle hidden characters
            cleaned_content = self._clean_xml_content(xml_content)
            return self.parser.validate_xml_structure(cleaned_content)
        except Exception as e:
            self.logger.error(f"Basic XML structure validation failed: {e}")
            return False
    
    def _clean_xml_content(self, xml_content: str) -> str:
        """Clean XML content to handle hidden characters and normalize format."""
        if not xml_content:
            return xml_content
        
        # Remove BOM and hidden characters
        content = xml_content
        
        # Remove UTF-8 BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]
            self.logger.debug("Removed UTF-8 BOM from XML content")
        
        # Remove UTF-16 BOMs
        elif content.startswith('\xff\xfe') or content.startswith('\xfe\xff'):
            content = content[2:]
            self.logger.debug("Removed UTF-16 BOM from XML content")
        
        # Remove other common hidden characters at the beginning
        while content and ord(content[0]) < 32 and content[0] not in '\t\n\r':
            content = content[1:]
            self.logger.debug("Removed hidden leading character")
        
        # Normalize line endings and strip whitespace
        content = content.replace('\r\n', '\n').replace('\r', '\n').strip()
        
        return content
    
    def _extract_and_validate_app_id(self, xml_data: Dict[str, Any], 
                                   errors: List[str]) -> Optional[str]:
        """Extract and validate app_id from XML data."""
        try:
            # Navigate to /Provenir/Request/@ID using XMLParser flat structure
            request_path = '/Provenir/Request'
            app_id = None
            
            if request_path in xml_data:
                request_element = xml_data[request_path]
                if isinstance(request_element, dict) and 'attributes' in request_element:
                    attributes = request_element['attributes']
                    # Check for lowercase 'id' due to case normalization in XML parser
                    app_id = attributes.get('id') or attributes.get('ID')
            
            # Fallback to nested structure for backward compatibility
            if not app_id:
                request_data = xml_data.get('Provenir', {}).get('Request', {})
                if isinstance(request_data, list) and len(request_data) > 0:
                    request_data = request_data[0]
                app_id = request_data.get('ID') if isinstance(request_data, dict) else None
            
            if not app_id:
                errors.append("CRITICAL: Missing app_id (/Provenir/Request/@ID)")
                return None
            
            # Validate app_id format
            app_id_str = str(app_id).strip()
            if not app_id_str:
                errors.append("CRITICAL: Empty app_id value")
                return None
            
            # Validate app_id is numeric (business rule)
            try:
                app_id_int = int(app_id_str)
                if app_id_int <= 0:
                    errors.append(f"CRITICAL: Invalid app_id value: {app_id_str} (must be positive integer)")
                    return None
            except ValueError:
                errors.append(f"CRITICAL: Invalid app_id format: {app_id_str} (must be integer)")
                return None
            
            return app_id_str
            
        except Exception as e:
            errors.append(f"CRITICAL: Failed to extract app_id: {e}")
            return None
    
    def _validate_and_collect_contacts(self, xml_data: Dict[str, Any], 
                                     errors: List[str], warnings: List[str],
                                     skipped_elements: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """
        Validate contacts and collect valid ones using 'last valid element' approach.
        
        Uses DataMapper's improved logic for handling duplicates and invalid contacts.
        """
        try:
            # Use DataMapper's improved contact extraction logic
            from xml_extractor.mapping.data_mapper import DataMapper
            mapper = DataMapper()
            
            # Pass the XML root to the mapper for direct parsing
            if hasattr(self, '_current_xml_root'):
                mapper._current_xml_root = self._current_xml_root
            
            # Extract valid contacts using "last valid element" approach
            valid_contacts = mapper._extract_valid_contacts(xml_data)
            
            # Navigate to all contacts for validation reporting
            all_contacts = self._navigate_to_contacts(xml_data)
            
            if not all_contacts:
                warnings.append("DATA QUALITY: No contact elements found in XML - will process application only")
                return []
            
            # Track validation issues for reporting
            contact_groups = {}
            duplicate_con_ids = set()
            
            for i, contact in enumerate(all_contacts):
                if not isinstance(contact, dict):
                    skipped_elements['contacts'].append(f"Contact {i}: Not a valid contact object")
                    continue
                
                con_id = contact.get('con_id', '').strip()
                ac_role_tp_c = contact.get('ac_role_tp_c', '').strip()
                
                # Track validation issues
                missing_attrs = []
                if not con_id:
                    missing_attrs.append('con_id')
                if not ac_role_tp_c:
                    missing_attrs.append('ac_role_tp_c')
                
                if missing_attrs:
                    reason = f"Contact {i+1}: Missing required attributes: {', '.join(missing_attrs)}"
                    skipped_elements['contacts'].append(reason)
                    warnings.append(f"Skipping contact - {reason}")
                    continue
                
                # Validate ac_role_tp_c values
                valid_roles = ['PR', 'AUTHU']
                if ac_role_tp_c not in valid_roles:
                    reason = f"Contact {i+1}: Invalid ac_role_tp_c value: {ac_role_tp_c} (must be PR or AUTHU)"
                    skipped_elements['contacts'].append(reason)
                    warnings.append(f"Skipping contact - {reason}")
                    continue
                
                # Track duplicates for reporting
                contact_key = f"{con_id}_{ac_role_tp_c}"
                if contact_key in contact_groups:
                    duplicate_con_ids.add(con_id)
                contact_groups[contact_key] = contact
            
            # Report business rule warnings
            if len(valid_contacts) > 1:
                pr_contacts = [c for c in valid_contacts if c.get('ac_role_tp_c') == 'PR']
                if len(pr_contacts) > 1:
                    warnings.append(f"Multiple primary contacts found ({len(pr_contacts)}), will process all")
            
            if duplicate_con_ids:
                warnings.append(f"Duplicate con_ids found: {sorted(list(duplicate_con_ids))}")
            
            # Check if we have at least one valid contact
            if not valid_contacts:
                warnings.append("DATA QUALITY: No valid contacts found (all missing con_id or ac_role_tp_c) - will process with graceful degradation")
            
            return valid_contacts
            
        except Exception as e:
            errors.append(f"CRITICAL: Failed to validate contacts: {e}")
            return []
    
    def _validate_child_elements(self, xml_data: Dict[str, Any], 
                               valid_contacts: List[Dict[str, Any]],
                               warnings: List[str], 
                               skipped_elements: Dict[str, List[str]]) -> None:
        """Validate child elements (addresses, employment) for each valid contact."""
        
        for contact in valid_contacts:
            con_id = contact.get('con_id')
            
            # Validate addresses
            addresses = contact.get('contact_address', [])
            if isinstance(addresses, dict):
                addresses = [addresses]
            
            valid_address_count = 0
            for i, address in enumerate(addresses):
                if not isinstance(address, dict):
                    continue
                
                address_tp_c = address.get('address_tp_c')
                if not address_tp_c:
                    reason = f"Address {i} for con_id {con_id}: Missing address_tp_c"
                    skipped_elements['addresses'].append(reason)
                    warnings.append(f"Skipping address - {reason}")
                else:
                    valid_address_count += 1
            
            # Validate employment
            employments = contact.get('contact_employment', [])
            if isinstance(employments, dict):
                employments = [employments]
            
            valid_employment_count = 0
            for i, employment in enumerate(employments):
                if not isinstance(employment, dict):
                    continue
                
                employment_tp_c = employment.get('employment_tp_c')
                if not employment_tp_c:
                    reason = f"Employment {i} for con_id {con_id}: Missing employment_tp_c"
                    skipped_elements['employments'].append(reason)
                    warnings.append(f"Skipping employment - {reason}")
                else:
                    valid_employment_count += 1
            
            # Log summary for this contact
            self.logger.debug(
                f"Contact {con_id}: {valid_address_count} valid addresses, "
                f"{valid_employment_count} valid employments"
            )
    
    def _validate_business_rules(self, xml_data: Dict[str, Any], app_id: Optional[str],
                               valid_contacts: List[Dict[str, Any]], 
                               errors: List[str], warnings: List[str]) -> None:
        """Validate business-specific rules."""
        
        # Rule: Must have exactly one PR contact
        pr_contacts = [c for c in valid_contacts if c.get('ac_role_tp_c') == 'PR']
        if len(pr_contacts) == 0 and valid_contacts:  # Only warn if we have contacts but no PR
            warnings.append("DATA QUALITY: No primary contact (ac_role_tp_c='PR') found - some fields requiring 'last_valid_pr_contact' will be skipped")
        elif len(pr_contacts) > 1:
            warnings.append(f"Multiple primary contacts found ({len(pr_contacts)}), will process all")
        
        # Rule: AUTHU contacts are optional
        authu_contacts = [c for c in valid_contacts if c.get('ac_role_tp_c') == 'AUTHU']
        if len(authu_contacts) > 0:
            self.logger.info(f"Found {len(authu_contacts)} authorized user contacts")
        
        # Rule: Check for duplicate con_ids
        con_ids = [c.get('con_id') for c in valid_contacts]
        duplicate_con_ids = [cid for cid in set(con_ids) if con_ids.count(cid) > 1]
        if duplicate_con_ids:
            warnings.append(f"Duplicate con_ids found: {duplicate_con_ids}")
        
        # Rule: Validate required fields for PR contact
        for contact in pr_contacts:
            required_fields = ['first_name', 'last_name']
            missing_fields = [field for field in required_fields 
                            if not contact.get(field)]
            if missing_fields:
                warnings.append(
                    f"PR contact {contact.get('con_id')} missing recommended fields: "
                    f"{', '.join(missing_fields)}"
                )
    
    def _navigate_to_contacts(self, xml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Navigate to contact elements in XML structure."""
        try:
            # The XMLParser has a limitation where multiple elements with the same path
            # overwrite each other. For contacts, we need to parse the XML directly
            # to find all contact elements.
            return self._extract_all_contacts_from_xml()
                
        except Exception as e:
            self.logger.error(f"Failed to navigate to contacts: {e}")
            return []
    
    def _extract_all_contacts_from_xml(self) -> List[Dict[str, Any]]:
        """
        Extract all contact elements directly from XML to handle multiple contacts.
        
        This is a workaround for the XMLParser limitation where multiple elements
        with the same path overwrite each other.
        """
        contacts = []
        
        try:
            # We need to store the parsed root for this method to work
            if hasattr(self, '_current_xml_root') and self._current_xml_root is not None:
                contacts = self._find_all_contacts_in_element(self._current_xml_root)
            
            return contacts
            
        except Exception as e:
            self.logger.error(f"Failed to extract contacts from XML: {e}")
            return []
    
    def _find_all_contacts_in_element(self, element) -> List[Dict[str, Any]]:
        """Recursively find all contact elements in XML tree."""
        contacts = []
        
        try:
            # Check if this is a contact element
            if element.tag == 'contact':
                contact_data = dict(element.attrib)
                contacts.append(contact_data)
            
            # Recurse into children
            for child in element:
                contacts.extend(self._find_all_contacts_in_element(child))
            
            return contacts
            
        except Exception as e:
            self.logger.error(f"Error finding contacts in element: {e}")
            return []
    
    def _clean_xml_content(self, xml_content: str) -> str:
        """Clean XML content (delegate to XMLParser)."""
        return self.parser._clean_xml_content(xml_content)
    
    def _convert_elements_to_data_structure(self, elements: Dict[str, Any]) -> Dict[str, Any]:
        """Convert parsed elements to nested data structure."""
        result = {}
        
        for path, element_data in elements.items():
            if not isinstance(element_data, dict):
                continue
            
            path_parts = path.strip('/').split('/')
            current = result
            
            # Navigate/create nested structure
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    # Last part - store element data
                    if part not in current:
                        current[part] = {}
                    elif not isinstance(current[part], dict):
                        # If it's not a dict (e.g., a string), convert it to dict
                        current[part] = {}
                    
                    # Merge attributes
                    if 'attributes' in element_data:
                        current[part].update(element_data['attributes'])
                    
                    # Add text content
                    if 'text' in element_data and element_data['text']:
                        current[part]['_text'] = element_data['text']
                else:
                    # Intermediate part
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        
        return result
    
    def _log_validation_summary(self, source_record_id: Optional[str], 
                              is_valid: bool, app_id: Optional[str],
                              valid_contacts: List[Dict[str, Any]], 
                              errors: List[str], warnings: List[str],
                              skipped_elements: Dict[str, List[str]]) -> None:
        """Log comprehensive validation summary."""
        
        record_info = f" (Record: {source_record_id})" if source_record_id else ""
        
        if is_valid:
            self.logger.info(
                f"Validation PASSED{record_info}: app_id={app_id}, "
                f"valid_contacts={len(valid_contacts)}, warnings={len(warnings)}"
            )
        else:
            self.logger.error(
                f"Validation FAILED{record_info}: {len(errors)} errors, "
                f"{len(warnings)} warnings"
            )
        
        # Log errors
        for error in errors:
            self.logger.error(f"  ERROR: {error}")
        
        # Log warnings
        for warning in warnings:
            self.logger.warning(f"  WARNING: {warning}")
        
        # Log skipped elements summary
        total_skipped = sum(len(items) for items in skipped_elements.values())
        if total_skipped > 0:
            self.logger.info(f"  SKIPPED: {total_skipped} elements total")
            for element_type, items in skipped_elements.items():
                if items:
                    self.logger.debug(f"    {element_type}: {len(items)} skipped")
    
    def validate_batch(self, xml_records: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Validate a batch of XML records.
        
        Args:
            xml_records: List of (record_id, xml_content) tuples
            
        Returns:
            Dictionary with validation summary and results
        """
        results = []
        summary = {
            'total_records': len(xml_records),
            'valid_records': 0,
            'invalid_records': 0,
            'records_with_warnings': 0,
            'total_errors': 0,
            'total_warnings': 0,
            'total_skipped_elements': 0
        }
        
        for record_id, xml_content in xml_records:
            result = self.validate_xml_for_processing(xml_content, record_id)
            results.append((record_id, result))
            
            if result.is_valid:
                summary['valid_records'] += 1
            else:
                summary['invalid_records'] += 1
            
            if result.validation_warnings:
                summary['records_with_warnings'] += 1
            
            summary['total_errors'] += len(result.validation_errors)
            summary['total_warnings'] += len(result.validation_warnings)
            summary['total_skipped_elements'] += sum(
                len(items) for items in result.skipped_elements.values()
            )
        
        # Log batch summary
        self.logger.info(
            f"Batch validation complete: {summary['valid_records']}/{summary['total_records']} "
            f"valid ({summary['valid_records']/summary['total_records']*100:.1f}%)"
        )
        
        return {
            'summary': summary,
            'results': results
        }


def create_sample_validation_scenarios() -> List[Tuple[str, str]]:
    """Create sample XML scenarios for testing validation using real sample data."""
    
    scenarios = []
    
    # Load real sample XML with edge cases
    try:
        with open('config/samples/sample-source-xml-contact-test.xml', 'r') as f:
            real_sample_xml = f.read()
        scenarios.append(("real_sample_with_edge_cases", real_sample_xml))
    except FileNotFoundError:
        # Fallback to mock scenarios if sample file not found
        pass
    
    # Add specific test scenarios
    scenarios.extend([
        # Valid scenarios
        ("valid_complete", """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN">
                            <contact_address address_tp_c="CURR" city="FARGO"/>
                            <contact_employment employment_tp_c="CURR" b_salary="75000"/>
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """),
        
        # Invalid scenarios
        ("invalid_no_app_id", """
        <Provenir>
            <Request>
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN"/>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """),
        
        ("invalid_no_con_id", """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact ac_role_tp_c="PR" first_name="JOHN"/>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """),
        
        # Graceful degradation scenarios
        ("graceful_missing_address_tp_c", """
        <Provenir>
            <Request ID="154284">
                <CustData>
                    <application>
                        <contact con_id="277449" ac_role_tp_c="PR" first_name="JOHN">
                            <contact_address city="FARGO"/>
                            <contact_employment employment_tp_c="CURR" b_salary="75000"/>
                        </contact>
                    </application>
                </CustData>
            </Request>
        </Provenir>
        """)
    ])
    
    return scenarios


if __name__ == '__main__':
    # Run validation on sample scenarios
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    validator = PreProcessingValidator()
    scenarios = create_sample_validation_scenarios()
    
    print("Running pre-processing validation on sample scenarios...")
    batch_results = validator.validate_batch(scenarios)
    
    print(f"\nValidation Summary:")
    for key, value in batch_results['summary'].items():
        print(f"  {key}: {value}")
    
    print(f"\nReady to process {batch_results['summary']['valid_records']} valid records.")