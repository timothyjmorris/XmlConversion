"""
Core data models for the XML Database Extraction system.

This module defines the primary data structures used throughout the system
for configuration, mapping contracts, and processing parameters.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class DataType(Enum):
    """Supported data types for field mapping."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DECIMAL = "decimal"


@dataclass
class FieldMapping:
    """
    Defines how an XML element or attribute maps to a database column.
    
    Attributes:
        xml_path: XPath expression to locate the XML element
        xml_attribute: Optional attribute name if mapping an attribute
        target_table: Name of the destination database table
        target_column: Name of the destination column
        data_type: Target data type for the column
        mapping_type: Type of mapping (enum, char_to_bit, identity_insert, etc.)
        expression: Optional calculated field expression for calculated_field mapping type
    """
    xml_path: str
    target_table: str
    target_column: str
    data_type: str
    data_length: Optional[int] = None
    xml_attribute: Optional[str] = None
    mapping_type: Optional[list] = None
    default_value: Optional[str] = None
    expression: Optional[str] = None
    description: Optional[str] = None
    required: Optional[bool] = None
    nullable: Optional[bool] = None
    exclude_default_when_record_empty: Optional[bool] = None
    enum_name: Optional[str] = None

    def __post_init__(self):
        """Validate field mapping configuration and normalize mapping_type."""
        if not self.xml_path:
            raise ValueError("xml_path cannot be empty")
        if not self.target_table:
            raise ValueError("target_table cannot be empty")
        # Normalize mapping_type to always be a list
        if self.mapping_type is not None:
            if isinstance(self.mapping_type, str):
                self.mapping_type = [mt.strip() for mt in self.mapping_type.split(",")]
            elif not isinstance(self.mapping_type, list):
                self.mapping_type = [self.mapping_type]

        # target_column is required for normal column mappings, but row-creating mapping
        # types (key/value tables) intentionally leave target_column blank.
        if not self.target_column:
            row_creating_prefixes = (
                'add_score',
                'add_indicator',
                'add_history',
                'add_report_lookup',
                'policy_exceptions',
                'warranty_field',
                'add_collateral',
            )
            mapping_types = self.mapping_type or []
            allows_empty = any(
                str(mt).strip().startswith(row_creating_prefixes)
                for mt in mapping_types
            )
            if not allows_empty:
                raise ValueError("target_column cannot be empty")


@dataclass
class RelationshipMapping:
    """
    Defines parent-child relationships between tables based on XML structure.
    
    Attributes:
        parent_table: Name of the parent table
        child_table: Name of the child table
        foreign_key_column: Column name for the foreign key in child table
        xml_parent_path: XPath to the parent element in XML
        xml_child_path: XPath to the child elements in XML
    """
    parent_table: str
    child_table: str
    foreign_key_column: str
    xml_parent_path: str
    xml_child_path: str
    
    def __post_init__(self):
        """Validate relationship mapping configuration."""
        if not all([self.parent_table, self.child_table, self.foreign_key_column]):
            raise ValueError("All table and column names must be specified")
        if not all([self.xml_parent_path, self.xml_child_path]):
            raise ValueError("Both parent and child XML paths must be specified")


@dataclass
class FilterRule:
    """
    Defines an element filtering rule for validating XML elements.
    
    Attributes:
        element_type: Type of element being filtered (e.g., 'contact', 'address', 'employment')
        description: Human-readable description of the filter rule
        xml_parent_path: XPath expression to locate parent elements
        xml_child_path: XPath expression to locate child elements to filter
        required_attributes: Dict mapping attribute names to validation rules
                            - true: attribute must be present (non-empty)
                            - list: attribute value must be in this list (case-insensitive)
    """
    element_type: str
    xml_parent_path: str
    xml_child_path: str
    required_attributes: Dict[str, Any]
    description: Optional[str] = None
    
    def __post_init__(self):
        """Validate filter rule configuration."""
        if not self.element_type:
            raise ValueError("element_type cannot be empty")
        if not self.xml_parent_path:
            raise ValueError("xml_parent_path cannot be empty")
        if not self.xml_child_path:
            raise ValueError("xml_child_path cannot be empty")
        if not self.required_attributes:
            raise ValueError("required_attributes cannot be empty")


@dataclass
class ElementFiltering:
    """
    Container for element filtering rules.
    
    Attributes:
        filter_rules: List of FilterRule objects defining validation for each element type
    """
    filter_rules: List[FilterRule]
    
    def __post_init__(self):
        """Validate element filtering configuration."""
        if not self.filter_rules:
            raise ValueError("At least one filter_rule must be specified")


@dataclass
class MappingContract:
    """
    Complete mapping contract defining how XML data maps to relational structure.
    
    Attributes:
        source_table: Name of the source table containing XML data
        source_column: Column name containing the XML content
        xml_root_element: Root element name in the XML structure
        xml_application_path: Full path to application node (e.g., '/Provenir/Request/CustData/application')
        target_schema: Target database schema (e.g., 'dbo')
        table_insertion_order: Optional list specifying FK dependency order for table insertion
        element_filtering: Optional element filtering rules for XML validation
        mappings: List of field mappings for individual elements/attributes
        relationships: List of relationship mappings for nested structures
    """
    source_table: str
    source_column: str
    xml_root_element: str
    xml_application_path: Optional[str] = None
    target_schema: Optional[str] = "dbo"
    table_insertion_order: Optional[List[str]] = None
    element_filtering: Optional[ElementFiltering] = None
    mappings: List[FieldMapping] = None
    relationships: List[RelationshipMapping] = None
    enum_mappings: Optional[Dict[str, Any]] = None
    bit_conversions: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    source_application_table: Optional[str] = None
    
    def __post_init__(self):
        """Validate mapping contract configuration."""
        # Normalize nested structures when MappingContract is constructed from raw JSON.
        # Several tests (and some diagnostics) build MappingContract(**json_dict) directly.
        # In that case, element_filtering/mappings/relationships may be plain dicts.
        if self.element_filtering is not None and isinstance(self.element_filtering, dict):
            raw_rules = self.element_filtering.get('filter_rules') or []
            if isinstance(raw_rules, list) and raw_rules:
                rules: List[FilterRule] = [
                    (FilterRule(**r) if isinstance(r, dict) else r)
                    for r in raw_rules
                ]
                self.element_filtering = ElementFiltering(filter_rules=rules)
            else:
                # Treat empty/missing rules as "no filtering".
                self.element_filtering = None

        if self.mappings and any(isinstance(m, dict) for m in self.mappings):
            self.mappings = [FieldMapping(**m) if isinstance(m, dict) else m for m in self.mappings]

        if self.relationships and any(isinstance(r, dict) for r in self.relationships):
            self.relationships = [RelationshipMapping(**r) if isinstance(r, dict) else r for r in self.relationships]

        if not self.source_table:
            raise ValueError("source_table cannot be empty")
        if not self.source_column:
            raise ValueError("source_column cannot be empty")
        if not self.xml_root_element:
            raise ValueError("xml_root_element cannot be empty")
        if not self.mappings:
            raise ValueError("At least one field mapping must be specified")


@dataclass
class ProcessingConfig:
    """
    Configuration parameters for the extraction and processing operations.
    
    Attributes:
        batch_size: Number of records to process in each batch
        parallel_processes: Number of parallel processes to use
        memory_limit_mb: Maximum memory usage limit in megabytes
        progress_reporting_interval: Interval for progress reporting (in records)
        sql_server_connection_string: Connection string for SQL Server database
        enable_validation: Whether to enable data validation during processing
        checkpoint_interval: Interval for creating processing checkpoints
    """
    batch_size: int = 1000
    parallel_processes: int = 4
    memory_limit_mb: int = 512
    progress_reporting_interval: int = 10000
    sql_server_connection_string: str = ""
    enable_validation: bool = True
    checkpoint_interval: int = 50000
    
    def __post_init__(self):
        """Validate processing configuration."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.parallel_processes <= 0:
            raise ValueError("parallel_processes must be positive")
        if self.memory_limit_mb <= 0:
            raise ValueError("memory_limit_mb must be positive")


@dataclass
class ProcessingResult:
    """
    Results from a processing operation.
    
    Attributes:
        records_processed: Total number of records processed
        records_successful: Number of successfully processed records
        records_failed: Number of failed records
        processing_time_seconds: Total processing time
        errors: List of error messages encountered
        performance_metrics: Dictionary of performance metrics
    """
    records_processed: int = 0
    records_successful: int = 0
    records_failed: int = 0
    processing_time_seconds: float = 0.0
    errors: List[str] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.errors is None:
            self.errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.records_processed == 0:
            return 0.0
        return (self.records_successful / self.records_processed) * 100.0


@dataclass
class MappingContractValidationError:
    """
    Represents a specific validation error in a mapping contract.
    
    Provides detailed, actionable information about what's wrong and how to fix it.
    These are CRITICAL errors that must be fixed before processing can begin.
    
    Attributes:
        category: High-level error category (e.g., "element_filtering", "relationships", "enum_mappings")
        message: Human-readable description of what's wrong
        contract_location: Where in the contract the issue exists (JSONPath-style: "element_filtering.filter_rules[0]")
        fix_guidance: Specific instructions on how to fix the issue
        example_fix: Optional code example showing correct structure
    """
    category: str
    message: str
    contract_location: str
    fix_guidance: str
    example_fix: Optional[str] = None
    
    def format_error(self) -> str:
        """Format error for display with all details."""
        lines = [
            f"X: [{self.category}] {self.message}",
            f"  Location: {self.contract_location}",
            f"  Fix: {self.fix_guidance}"
        ]
        if self.example_fix:
            lines.append(f"  Example:\n{self.example_fix}")
        return "\n".join(lines)


@dataclass
class MappingContractValidationWarning:
    """
    Represents a non-critical issue in a mapping contract.
    
    Warnings indicate suspicious patterns or sub-optimal configurations that
    won't block processing but should be reviewed.
    
    Attributes:
        category: High-level warning category (e.g., "performance", "consistency", "best_practices")
        message: Human-readable description of the concern
        contract_location: Where in the contract the issue exists
        recommendation: Suggested improvement
    """
    category: str
    message: str
    contract_location: str
    recommendation: str
    
    def format_warning(self) -> str:
        """Format warning for display."""
        return (
            f"!: [{self.category}] {self.message}\n"
            f"  Location: {self.contract_location}\n"
            f"  Recommendation: {self.recommendation}"
        )


@dataclass
class MappingContractValidationResult:
    """
    Result of validating a mapping contract against business rules.
    
    Contains all validation errors (blocking) and warnings (non-blocking) discovered
    during pre-flight contract validation.
    
    Attributes:
        is_valid: True if no critical errors (warnings are OK)
        errors: List of critical errors that must be fixed
        warnings: List of non-critical issues that should be reviewed
    """
    is_valid: bool
    errors: List[MappingContractValidationError]
    warnings: List[MappingContractValidationWarning]
    
    def __post_init__(self):
        """Ensure is_valid matches error count."""
        if self.errors and self.is_valid:
            raise ValueError("MappingContractValidationResult cannot be valid with errors present")
        if not self.errors and not self.is_valid:
            raise ValueError("MappingContractValidationResult must be valid if no errors present")
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation result has warnings."""
        return len(self.warnings) > 0
    
    @property
    def error_count(self) -> int:
        """Count of critical errors."""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return len(self.warnings)
    
    def format_summary(self) -> str:
        """Format a summary of validation results."""
        if self.is_valid and not self.has_warnings:
            return "> Mapping contract validation passed (no errors, no warnings)"
        
        lines = []
        if not self.is_valid:
            lines.append(f"X: Mapping contract validation FAILED ({self.error_count} error(s)):")
            for error in self.errors:
                lines.append("")
                lines.append(error.format_error())
        
        if self.has_warnings:
            lines.append("")
            lines.append(f"!: Mapping contract validation has {self.warning_count} warning(s):")
            for warning in self.warnings:
                lines.append("")
                lines.append(warning.format_warning())
        
        return "\n".join(lines)