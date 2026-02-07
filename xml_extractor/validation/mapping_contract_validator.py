"""
Mapping Contract Validator - Pre-flight validation for mapping contracts.

Validates mapping contract structure and business rules BEFORE processing begins.
Catches configuration issues at startup, not after 1000 records.

Purpose:
    - Ensure mapping contract provides all required sections for processing
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
    
    def __init__(self, contract):
        """
        Initialize validator with mapping contract.
        
        Args:
            contract: Mapping contract (dict, dataclass, or MappingContract object)
        """
        # If it's a dataclass/object with attributes, we can work with it directly
        # No conversion needed - just access attributes when needed
        self.contract = contract
        self.errors: List[MappingContractValidationError] = []
        self.warnings: List[MappingContractValidationWarning] = []
    
    def _get_attr(self, obj, key: str, default=None):
        """
        Get attribute from object or dict, handling both formats.
        
        Args:
            obj: Object or dict to get attribute from
            key: Attribute/key name
            default: Default value if not found
        
        Returns:
            Attribute value or default
        """
        # Try as dict first
        if isinstance(obj, dict):
            return obj.get(key, default)
        # Try as object attribute
        return getattr(obj, key, default)
    
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
        element_filtering = self._get_attr(self.contract, "element_filtering")
        if element_filtering is None:
            self.errors.append(MappingContractValidationError(
                category="element_filtering",
                message="Missing required 'element_filtering' section in contract",
                contract_location="root",
                fix_guidance="Add 'element_filtering' section with 'filter_rules' array containing 'contact' and 'address' rules",
                example_fix='{\n  "element_filtering": {\n    "filter_rules": [\n      {"element_type": "contact", "required_attributes": {...}},\n      {"element_type": "address", "required_attributes": {...}}\n    ]\n  }\n}'
            ))
            return
        
        # Check if filter_rules key exists
        filter_rules = self._get_attr(element_filtering, "filter_rules")
        if filter_rules is None:
            self.errors.append(MappingContractValidationError(
                category="element_filtering",
                message="Missing 'filter_rules' key in element_filtering section",
                contract_location="element_filtering",
                fix_guidance="Add 'filter_rules' array with 'contact' and 'address' filter rule entries",
                example_fix='"filter_rules": [\n  {"element_type": "contact", ...},\n  {"element_type": "address", ...}\n]'
            ))
            return
        
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
            element_type = self._get_attr(rule, "element_type")
            if element_type:
                element_types.add(element_type)
        
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
            2. All relationship child tables exist in table_insertion_order
            3. All non-root, non-metadata tables in table_insertion_order exist in relationships,
               EXCEPT for key/value (row-creating) tables produced by mapping types like
               add_score/add_indicator/add_history/add_report_lookup.
        
        Rationale:
        - relationships primarily describes XML structure for extracting nested/related tables.
        - table_insertion_order describes FK dependency order for database inserts.
        Some destination tables are app-scoped key/value tables that are derived from
        other XML sections and do not have a fixed parent/child XML path; those tables
        should still be insert-ordered but do not require a relationships entry.
        
        Adds errors to self.errors list for integrity violations.
        """
        # Get table_insertion_order
        table_insertion_order = self._get_attr(self.contract, "table_insertion_order")
        if table_insertion_order is None:
            self.errors.append(MappingContractValidationError(
                category="relationships",
                message="Missing required 'table_insertion_order' section in contract",
                contract_location="root",
                fix_guidance="Add 'table_insertion_order' array listing all destination tables in FK dependency order",
                example_fix='{\n  "table_insertion_order": [\n    "app_base",\n    "app_contact_base",\n    "app_contact_address",\n    "processing_log"\n  ]\n}'
            ))
            return
        
        # Get relationships
        relationships = self._get_attr(self.contract, "relationships")
        if relationships is None:
            self.errors.append(MappingContractValidationError(
                category="relationships",
                message="Missing required 'relationships' section in contract",
                contract_location="root",
                fix_guidance="Add 'relationships' array defining parent-child table relationships",
                example_fix='{\n  "relationships": [\n    {"parent_table": "app_base", "child_table": "app_contact_base", "foreign_key_column": "app_id"}\n  ]\n}'
            ))
            return

        def _is_kv_row_creating_table(table_name: str) -> bool:
            """Return True if all mappings to table_name are row-creating KV mappings."""
            mappings = self._get_attr(self.contract, "mappings", []) or []
            table_mappings = [
                m for m in mappings
                if self._get_attr(m, "target_table") == table_name
            ]
            if not table_mappings:
                return False

            row_creating_prefixes = (
                "add_score",
                "add_indicator",
                "add_history",
                "add_report_lookup",
            )

            def _is_row_creating_mapping(mapping: Any) -> bool:
                mapping_type = self._get_attr(mapping, "mapping_type", [])
                if mapping_type is None:
                    mapping_type = []
                elif isinstance(mapping_type, str):
                    mapping_type = [mapping_type]

                return any(
                    str(mt).strip().startswith(row_creating_prefixes)
                    for mt in (mapping_type or [])
                )

            return all(_is_row_creating_mapping(m) for m in table_mappings)
        
        # Extract all child_table values from relationships (using helper for dict/object compatibility)
        child_tables = set()
        for idx, rel in enumerate(relationships):
            # Get child_table (works for both dict and dataclass)
            child_table = self._get_attr(rel, "child_table")
            if child_table is None:
                self.errors.append(MappingContractValidationError(
                    category="relationships",
                    message=f"Relationship at index {idx} missing required 'child_table' field",
                    contract_location=f"relationships[{idx}]",
                    fix_guidance="Add 'child_table' field specifying the child table name",
                    example_fix='{"parent_table": "app_base", "child_table": "app_contact_base", "foreign_key_column": "app_id"}'
                ))
                continue
            
            child_tables.add(child_table)
            
            # Validate relationship has foreign_key_column
            foreign_key_column = self._get_attr(rel, "foreign_key_column")
            if foreign_key_column is None:
                self.errors.append(MappingContractValidationError(
                    category="relationships",
                    message=f"Relationship for table '{child_table}' missing required 'foreign_key_column' field",
                    contract_location=f"relationships[{idx}] (child_table='{child_table}')",
                    fix_guidance="Add 'foreign_key_column' field specifying the FK column name",
                    example_fix=f'{{"parent_table": "...", "child_table": "{child_table}", "foreign_key_column": "app_id"}}'
                ))
        
        # Cross-reference: ensure every relationship child table appears in table_insertion_order
        for child_table in child_tables:
            if child_table not in table_insertion_order:
                self.errors.append(MappingContractValidationError(
                    category="relationships",
                    message=f"Relationship child_table '{child_table}' not found in table_insertion_order",
                    contract_location="relationships / table_insertion_order",
                    fix_guidance=f"Add '{child_table}' to table_insertion_order (in FK dependency order)",
                    example_fix=f'"table_insertion_order": ["...", "{child_table}", "..."]'
                ))

        # Cross-reference: check all tables in table_insertion_order exist in relationships
        # Exclude 'processing_log' (metadata table, not part of relationships)
        # Exclude 'app_base' (root table, appears as parent not child)
        excluded_tables = {"processing_log", "app_base"}
        
        for table in table_insertion_order:
            if table in excluded_tables:
                continue
            
            if table not in child_tables:
                if _is_kv_row_creating_table(table):
                    continue
                self.errors.append(MappingContractValidationError(
                    category="relationships",
                    message=f"Table '{table}' appears in table_insertion_order but not in relationships",
                    contract_location="table_insertion_order / relationships",
                    fix_guidance=(
                        f"Either add a relationships entry with child_table='{table}', or ensure "
                        f"'{table}' is a key/value (row-creating) table produced only by add_score/" 
                        f"add_indicator/add_history/add_report_lookup mappings."
                    ),
                    example_fix=f'{{"parent_table": "...", "child_table": "{table}", "foreign_key_column": "...", "xml_parent_path": "...", "xml_child_path": "..."}}'
                ))
    
    def _validate_enum_mappings(self) -> None:
        """
        Validate enum_mappings section and cross-reference with mappings.
        
        Checks that every mapping with mapping_type=["enum"] has its target_column
        defined in the enum_mappings section. This ensures enum transformations
        won't silently fail at runtime due to missing configuration.
        
        Design: Simple one-way check - mappings → enum_mappings.
        - Unused enum_mappings are allowed (no warnings)
        - Column naming conventions not enforced (allow flexibility)
        - Just verify: if mapping uses enum, the enum definition must exist
        
        Adds errors to self.errors list for:
        - Missing enum_mappings section when enum mappings exist
        - Missing enum definition for any mapping with mapping_type=["enum"]
        """
        # Get enum_mappings section
        enum_mappings = self._get_attr(self.contract, "enum_mappings")
        
        # Get all mappings
        mappings = self._get_attr(self.contract, "mappings", [])
        if not mappings:
            return  # No mappings to validate
        
        # Find all mappings that use enum transformation
        enum_mapped_columns = []
        for mapping in mappings:
            mapping_type = self._get_attr(mapping, "mapping_type", [])
            
            # Handle None, string, and list formats
            if mapping_type is None:
                mapping_type = []
            elif isinstance(mapping_type, str):
                mapping_type = [mapping_type]
            
            # Check if "enum" is in the mapping_type list
            if "enum" in mapping_type:
                target_column = self._get_attr(mapping, "target_column")
                target_table = self._get_attr(mapping, "target_table")
                enum_name = self._get_attr(mapping, "enum_name")
                if target_column:
                    enum_mapped_columns.append({
                        "column": target_column,
                        "table": target_table,
                        "enum_name": enum_name
                    })
        
        # If no enum mappings used, no validation needed
        if not enum_mapped_columns:
            return
        
        # Check if enum_mappings section exists
        if enum_mappings is None:
            self.errors.append(MappingContractValidationError(
                category="enum_mappings",
                message="Missing enum_mappings section but mappings use mapping_type=['enum']",
                contract_location="enum_mappings",
                fix_guidance="Add enum_mappings section with definitions for all enum columns",
                example_fix='{"enum_mappings": {"app_source_enum": {"VALUE1": 1, "VALUE2": 2}}}'
            ))
            return
        
        # Validate each enum-mapped column has definition in enum_mappings
        # Columns may specify an explicit enum_name to share a definition with other columns
        for enum_col in enum_mapped_columns:
            column_name = enum_col["column"]
            table_name = enum_col["table"]
            enum_name = enum_col.get("enum_name")
            
            # Resolution order: explicit enum_name > column_name match
            resolved = enum_name if enum_name and enum_name in enum_mappings else (
                column_name if column_name in enum_mappings else None
            )
            
            if resolved is None:
                hint = f" (enum_name='{enum_name}' also not found)" if enum_name else ""
                self.errors.append(MappingContractValidationError(
                    category="enum_mappings",
                    message=f"Column '{column_name}' uses mapping_type=['enum'] but not defined in enum_mappings{hint}",
                    contract_location=f"mappings (target_table='{table_name}', target_column='{column_name}') / enum_mappings",
                    fix_guidance=f"Add enum definition for '{enum_name or column_name}' to enum_mappings section, or set enum_name on the mapping",
                    example_fix=f'"{enum_name or column_name}": {{"VALUE1": 1, "VALUE2": 2}}'
                ))
