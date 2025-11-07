"""
XML Database Extraction System

A configurable, contract-driven, high-performance tool for extracting XML data from database text columns
and transforming it into normalized relational structures.
"""

__version__ = "2.1.0"
__author__ = "Timothy J. Morris"

# Import core models and interfaces for easy access
from .models import (
    MappingContract,
    FieldMapping, 
    RelationshipMapping,
    ElementFiltering,
    FilterRule,
    ProcessingConfig,
    ProcessingResult,
    DataType
)

from .interfaces import (
    XMLParserInterface,
    DataMapperInterface,
    MigrationEngineInterface,
    ConfigurationManagerInterface,
    PerformanceMonitorInterface
)

from .exceptions import (
    XMLExtractionError,
    XMLParsingError,
    MappingContractError,
    DataTransformationError,
    DatabaseConnectionError,
    SchemaValidationError,
    ConfigurationError,
    PerformanceError
)

__all__ = [
    # Core models
    "MappingContract",
    "FieldMapping",
    "RelationshipMapping", 
    "ProcessingConfig",
    "ProcessingResult",
    "DataType",
    
    # Interfaces
    "XMLParserInterface",
    "DataMapperInterface", 
    "MigrationEngineInterface",
    "ConfigurationManagerInterface",
    "PerformanceMonitorInterface",
    
    # Exceptions
    "XMLExtractionError",
    "XMLParsingError",
    "MappingContractError",
    "DataTransformationError",
    "DatabaseConnectionError", 
    "SchemaValidationError",
    "ConfigurationError",
    "PerformanceError"
]