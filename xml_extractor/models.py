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
        transformation: Optional transformation rule to apply
        expression: Optional calculated field expression for calculated_field mapping type
    """
    xml_path: str
    target_table: str
    target_column: str
    data_type: str
    data_length: Optional[int] = None
    xml_attribute: Optional[str] = None
    mapping_type: Optional[list] = None
    transformation: Optional[str] = None
    default_value: Optional[str] = None
    expression: Optional[str] = None
    description: Optional[str] = None
    required: Optional[bool] = None
    nullable: Optional[bool] = None
    exclude_default_when_record_empty: Optional[bool] = None

    def __post_init__(self):
        """Validate field mapping configuration and normalize mapping_type."""
        if not self.xml_path:
            raise ValueError("xml_path cannot be empty")
        if not self.target_table:
            raise ValueError("target_table cannot be empty")
        if not self.target_column:
            raise ValueError("target_column cannot be empty")
        # Normalize mapping_type to always be a list
        if self.mapping_type is not None:
            if isinstance(self.mapping_type, str):
                self.mapping_type = [mt.strip() for mt in self.mapping_type.split(",")]
            elif not isinstance(self.mapping_type, list):
                self.mapping_type = [self.mapping_type]


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

@dataclass
class MappingContract:
    """
    Complete mapping contract defining how XML data maps to relational structure.
    
    Attributes:
        source_table: Name of the source table containing XML data
        source_column: Column name containing the XML content
        xml_root_element: Root element name in the XML structure
        key_identifiers: Optional dictionary of key identifiers
        mappings: List of field mappings for individual elements/attributes
        relationships: List of relationship mappings for nested structures
    """
    source_table: str
    source_column: str
    xml_root_element: str
    key_identifiers: Optional[Dict[str, Any]] = None
    mappings: List[FieldMapping] = None
    relationships: List[RelationshipMapping] = None
    enum_mappings: Optional[Dict[str, Any]] = None
    bit_conversions: Optional[Dict[str, Any]] = None
    default_values: Optional[Dict[str, Any]] = None
    validation_rules: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate mapping contract configuration."""
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