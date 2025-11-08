"""
Mapping Contract Validator - Pre-flight validation for mapping contracts.

Validates contract structure and business rules BEFORE processing begins.
Catches configuration issues at startup, not after 1000 records.

Purpose:
    - Ensure contract provides all required sections for processing
    - Validate cross-references within contract (relationships ↔ table_insertion_order)
    - Verify enum mappings exist for all enum-type fields
    - Catch structural issues that would require fallback code

Scope:
    - VALIDATES: Contract structure, required sections, internal consistency
    - DOES NOT VALIDATE: Filter effectiveness, data values, XML content
    - Bad filter values = logged data quality issue, not startup failure
"""

from typing import Dict, Any, List, Set
from ..models import (
    MappingContractValidationError,
    MappingContractValidationWarning,
    MappingContractValidationResult
)


class MappingContractValidator:
    """
    Validates mapping contract structure and business rules.
    
    Performs comprehensive pre-flight validation to catch configuration issues
    before processing begins. Returns detailed results with actionable error messages.
    
    Validation Categories:
        1. Element Filtering: Required filter rules exist (contact, address)
        2. Relationships: Cross-reference with table_insertion_order
        3. Enum Mappings: All enum-type fields have corresponding enum definitions
    
    Usage:
        validator = MappingContractValidator(contract_dict)
        result = validator.validate_contract()
        if not result.is_valid:
            print(result.format_summary())
            sys.exit(1)
    """
    
    def __init__(self, contract: Dict[str, Any]):
        """
        Initialize validator with mapping contract.
        
        Args:
            contract: Parsed mapping contract dictionary (from JSON)
        """
        self.contract = contract
        self.errors: List[MappingContractValidationError] = []
        self.warnings: List[MappingContractValidationWarning] = []
    
    def validate_contract(self) -> MappingContractValidationResult:
        """
        Perform full contract validation.
        
        Orchestrates all validation checks and returns aggregated result.
        Validation continues even after errors to report all issues at once.
        
        Returns:
            MappingContractValidationResult with all errors and warnings
        """
        # Clear previous results
        self.errors.clear()
        self.warnings.clear()
        
        # Run all validation checks
        self._validate_element_filtering()
        self._validate_relationships()
        self._validate_enum_mappings()
        
        # Return aggregated result
        return MappingContractValidationResult(
            is_valid=len(self.errors) == 0,
            errors=self.errors.copy(),
            warnings=self.warnings.copy()
        )
    
    def _validate_element_filtering(self) -> None:
        """
        Validate element_filtering section structure.
        
        Ensures required filter rules exist:
            - 'contact' filter rule (required for contact processing)
            - 'address' filter rule (required for address processing)
        
        Does NOT validate filter effectiveness (e.g., whether contact_role_type
        values will actually match data). Bad filter values = data quality issue.
        
        Adds errors to self.errors list for missing required sections.
        """
        # Check if element_filtering section exists
        if "element_filtering" not in self.contract:
            self.errors.append(MappingContractValidationError(
                category="element_filtering",
                message="Missing required 'element_filtering' section in contract",
                contract_location="root",
                fix_guidance="Add 'element_filtering' section with 'filter_rules' array containing 'contact' and 'address' rules",
                example_fix='{\n  "element_filtering": {\n    "filter_rules": [\n      {"element_type": "contact", "required_attributes": {...}},\n      {"element_type": "address", "required_attributes": {...}}\n    ]\n  }\n}'
            ))
            return
        
        element_filtering = self.contract["element_filtering"]
        
        # Check if filter_rules key exists
        if "filter_rules" not in element_filtering:
            self.errors.append(MappingContractValidationError(
                category="element_filtering",
                message="Missing 'filter_rules' key in element_filtering section",
                contract_location="element_filtering",
                fix_guidance="Add 'filter_rules' array with 'contact' and 'address' filter rule entries",
                example_fix='"filter_rules": [\n  {"element_type": "contact", ...},\n  {"element_type": "address", ...}\n]'
            ))
            return
        
        filter_rules = element_filtering["filter_rules"]
        
        # Check if filter_rules is empty
        if not filter_rules or len(filter_rules) == 0:
            self.errors.append(MappingContractValidationError(
                category="element_filtering",
                message="Empty 'filter_rules' array - must contain at least 'contact' and 'address' rules",
                contract_location="element_filtering.filter_rules",
                fix_guidance="Add filter rule entries for 'contact' and 'address' element types",
                example_fix='[\n  {"element_type": "contact", "required_attributes": {"con_id": true, "ac_role_tp_c": ["PR", "AUTHU"]}},\n  {"element_type": "address", "required_attributes": {"address_tp_c": ["CURR"]}}\n]'
            ))
            return
        
        # Extract all element_type values from filter_rules
        element_types = set()
        for rule in filter_rules:
            if isinstance(rule, dict) and "element_type" in rule:
                element_types.add(rule["element_type"])
        
        # Check for required 'contact' filter rule
        if "contact" not in element_types:
            self.errors.append(MappingContractValidationError(
                category="element_filtering",
                message="Missing required filter rule with element_type='contact'",
                contract_location="element_filtering.filter_rules",
                fix_guidance="Add a filter rule entry for 'contact' element type to filter_rules array",
                example_fix='{"element_type": "contact", "required_attributes": {"con_id": true, "ac_role_tp_c": ["PR", "AUTHU"]}}'
            ))
        
        # Check for required 'address' filter rule
        if "address" not in element_types:
            self.errors.append(MappingContractValidationError(
                category="element_filtering",
                message="Missing required filter rule with element_type='address'",
                contract_location="element_filtering.filter_rules",
                fix_guidance="Add a filter rule entry for 'address' element type to filter_rules array",
                example_fix='{"element_type": "address", "required_attributes": {"address_tp_c": ["CURR", "PREV"]}}'
            ))
    
    def _validate_relationships(self) -> None:
        """
        Validate relationships section and cross-reference with table_insertion_order.
        
        Checks:
            1. All relationships have required fields (child_table, foreign_key_column)
            2. All tables in table_insertion_order (except processing_log) exist in relationships
            3. No orphaned table references
        
        Rationale: table_insertion_order lists all destination tables. If a table is
        in insertion order but not in relationships, processing will fail.
        
        Adds errors to self.errors list for integrity violations.
        """
        # TODO: Implement relationships validation
        pass
    
    def _validate_enum_mappings(self) -> None:
        """
        Validate enum_mappings section and cross-reference with mappings.
        
        Checks:
            1. All mappings with mapping_type=["enum"] have corresponding enum definitions
            2. Enum name extracted from target_column (e.g., "app_source_enum" key required
               for mapping with target_column="app_source_enum")
            3. No unused enum definitions (warning only)
        
        Pattern: Scan mappings for `"mapping_type": ["enum"]`, extract target_column,
        verify key exists in enum_mappings section.
        
        Adds errors to self.errors list for missing enum definitions.
        Adds warnings to self.warnings list for unused enum definitions.
        """
        # TODO: Implement enum mappings validation
        pass
