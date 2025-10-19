"""
XML Database Extraction System

A high-performance tool for extracting XML data from database text columns
and transforming it into normalized relational structures.
"""

__version__ = "1.0.0"
__author__ = "XML Extractor Team"

# Import core models and interfaces for easy access
from .models import (
    MappingContract,
    FieldMapping, 
    RelationshipMapping,
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