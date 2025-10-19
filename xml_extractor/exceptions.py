"""
Custom exceptions for the XML Database Extraction system.

This module defines specific exception types for different error conditions
that can occur during XML processing and data extraction.
"""


class XMLExtractionError(Exception):
    """Base exception for all XML extraction related errors."""
    
    def __init__(self, message: str, source_record_id: str = None):
        """
        Initialize XML extraction error.
        
        Args:
            message: Error description
            source_record_id: Optional identifier of the source record that caused the error
        """
        super().__init__(message)
        self.source_record_id = source_record_id


class XMLParsingError(XMLExtractionError):
    """Exception raised when XML parsing fails."""
    
    def __init__(self, message: str, xml_content: str = None, source_record_id: str = None):
        """
        Initialize XML parsing error.
        
        Args:
            message: Error description
            xml_content: Optional XML content that failed to parse (truncated for logging)
            source_record_id: Optional identifier of the source record
        """
        super().__init__(message, source_record_id)
        # Store truncated XML content for debugging (first 500 chars)
        self.xml_content = xml_content[:500] + "..." if xml_content and len(xml_content) > 500 else xml_content


class MappingContractError(XMLExtractionError):
    """Exception raised when mapping contract is invalid or cannot be applied."""
    pass


class DataTransformationError(XMLExtractionError):
    """Exception raised when data transformation fails."""
    
    def __init__(self, message: str, field_name: str = None, source_value: str = None, 
                 target_type: str = None, source_record_id: str = None):
        """
        Initialize data transformation error.
        
        Args:
            message: Error description
            field_name: Name of the field that failed transformation
            source_value: Original value that failed transformation
            target_type: Target data type for transformation
            source_record_id: Optional identifier of the source record
        """
        super().__init__(message, source_record_id)
        self.field_name = field_name
        self.source_value = source_value
        self.target_type = target_type


class DatabaseConnectionError(XMLExtractionError):
    """Exception raised when database connection fails."""
    pass


class SchemaValidationError(XMLExtractionError):
    """Exception raised when target schema validation fails."""
    pass


class ConfigurationError(XMLExtractionError):
    """Exception raised when configuration is invalid or missing."""
    pass


class ValidationError(XMLExtractionError):
    """Exception raised when data or configuration validation fails."""
    pass


class DataMappingError(XMLExtractionError):
    """Exception raised when data mapping operations fail."""
    pass


class PerformanceError(XMLExtractionError):
    """Exception raised when performance thresholds are exceeded."""
    
    def __init__(self, message: str, metric_name: str = None, 
                 current_value: float = None, threshold_value: float = None):
        """
        Initialize performance error.
        
        Args:
            message: Error description
            metric_name: Name of the performance metric that exceeded threshold
            current_value: Current value of the metric
            threshold_value: Threshold value that was exceeded
        """
        super().__init__(message)
        self.metric_name = metric_name
        self.current_value = current_value
        self.threshold_value = threshold_value