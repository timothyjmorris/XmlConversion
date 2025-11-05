"""
Abstract interfaces and base classes for the XML Database Extraction system.

This module defines the contracts that all system components must implement
to ensure consistent behavior and enable dependency injection.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator, Tuple
from xml.etree.ElementTree import Element

from .models import MappingContract, ProcessingConfig, ProcessingResult


class XMLParserInterface(ABC):
    """Abstract interface for XML parsing components."""
    
    @abstractmethod
    def parse_xml_stream(self, xml_content: str) -> Element:
        """
        Parse XML content using streaming approach for memory efficiency.
        
        Args:
            xml_content: Raw XML content as string
            
        Returns:
            Parsed XML element tree root
            
        Raises:
            XMLParsingError: If XML is malformed or cannot be parsed
        """
        pass
    
    @abstractmethod
    def validate_xml_structure(self, xml_content: str) -> bool:
        """
        Validate XML structure before processing.
        
        Args:
            xml_content: Raw XML content to validate
            
        Returns:
            True if XML is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def extract_elements(self, xml_node: Element) -> Dict[str, Any]:
        """
        Extract elements from XML node recursively.
        
        Args:
            xml_node: XML element to extract data from
            
        Returns:
            Dictionary containing extracted element data
        """
        pass 
    @abstractmethod
    def extract_attributes(self, xml_node: Element) -> Dict[str, str]:
        """
        Extract attributes from XML node.
        
        Args:
            xml_node: XML element to extract attributes from
            
        Returns:
            Dictionary containing attribute name-value pairs
        """
        pass


class DataMapperInterface(ABC):
    """Abstract interface for data mapping components."""
    
    @abstractmethod
    def apply_mapping_contract(self, xml_data: Dict[str, Any], 
                             contract: MappingContract) -> Dict[str, List[Dict[str, Any]]]:
        """
        Apply mapping contract to transform XML data to relational format.
        
        Args:
            xml_data: Parsed XML data
            contract: Mapping contract defining transformations
            
        Returns:
            Dictionary with table names as keys and list of records as values
        """
        pass
    
    @abstractmethod
    def transform_data_types(self, value: Any, target_type: str) -> Any:
        """
        Transform value to target data type.
        
        Args:
            value: Source value to transform
            target_type: Target data type name
            
        Returns:
            Transformed value in target type
        """
        pass
    
    @abstractmethod
    def handle_nested_elements(self, parent_id: str, 
                             child_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Handle nested XML elements for relationship mapping.
        
        Args:
            parent_id: Identifier of the parent record
            child_elements: List of child element data
            
        Returns:
            List of child records with foreign key relationships
        """
        pass

class MigrationEngineInterface(ABC):
    """Abstract interface for database migration components."""
    
    @abstractmethod
    def execute_bulk_insert(self, records: List[Dict[str, Any]], table_name: str) -> int:
        """
        Execute bulk insert operation for records.
        
        Args:
            records: List of record dictionaries to insert
            table_name: Target table name
            
        Returns:
            Number of records successfully inserted
        """
        pass
    
    @abstractmethod
    def track_progress(self, processed_count: int, total_count: int) -> None:
        """
        Track and report processing progress.
        
        Args:
            processed_count: Number of records processed so far
            total_count: Total number of records to process
        """
        pass


class ConfigurationManagerInterface(ABC):
    """Abstract interface for configuration management components."""
    
    @abstractmethod
    def load_mapping_contract(self, contract_path: str) -> MappingContract:
        """
        Load mapping contract from file.
        
        Args:
            contract_path: Path to mapping contract file
            
        Returns:
            Loaded mapping contract
        """
        pass 
    @abstractmethod
    def load_table_structure(self, sql_script_path: str, 
                           data_model_path: str) -> Dict[str, Dict[str, str]]:
        """
        Load table structure from SQL scripts and data model documentation.
        
        Args:
            sql_script_path: Path to SQL CREATE TABLE scripts
            data_model_path: Path to data-model.md file
            
        Returns:
            Dictionary with table definitions
        """
        pass
    
    @abstractmethod
    def load_sample_xml(self, sample_path: str) -> List[str]:
        """
        Load sample XML documents for validation.
        
        Args:
            sample_path: Path to sample XML files directory
            
        Returns:
            List of sample XML content strings
        """
        pass
    
    @abstractmethod
    def get_processing_config(self) -> ProcessingConfig:
        """
        Get processing configuration parameters.
        
        Returns:
            Processing configuration object
        """
        pass


class PerformanceMonitorInterface(ABC):
    """Abstract interface for performance monitoring components."""
    
    @abstractmethod
    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> ProcessingResult:
        """
        Stop monitoring and return results.
        
        Returns:
            Processing results with performance metrics
        """
        pass
    
    @abstractmethod
    def record_metric(self, metric_name: str, value: Any) -> None:
        """
        Record a performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        pass
    
    @abstractmethod
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Dictionary of current metric values
        """
        pass


class DataIntegrityValidatorInterface(ABC):
    """Abstract interface for data integrity validation components."""
    
    @abstractmethod
    def validate_extraction_results(self, source_xml_data: Dict[str, Any], 
                                  extracted_tables: Dict[str, List[Dict[str, Any]]], 
                                  mapping_contract: MappingContract,
                                  source_record_id: Optional[str] = None) -> Any:
        """
        Perform comprehensive validation of extraction results.
        
        Args:
            source_xml_data: Original parsed XML data
            extracted_tables: Extracted relational data organized by table
            mapping_contract: Mapping contract used for extraction
            source_record_id: Optional identifier for the source record
            
        Returns:
            ValidationResult containing all validation findings
        """
        pass


class BatchProcessorInterface(ABC):
    """
    Abstract interface for batch XML processing strategies.
    
    Enables dependency injection to decouple ProductionProcessor from specific
    processing implementations (parallel vs sequential).
    
    Allows:
    - Parallel processing via ParallelCoordinator (production)
    - Sequential processing for testing and debugging
    - Mock processors for unit testing
    """
    
    @abstractmethod
    def process_xml_batch(self, 
                         xml_records: List[Tuple[int, str]], 
                         batch_number: int = 1) -> ProcessingResult:
        """
        Process a batch of XML records using the implementation's strategy.
        
        Args:
            xml_records: List of (app_id, xml_content) tuples to process
            batch_number: Batch sequence number (for logging/tracking)
            
        Returns:
            ProcessingResult with metrics and results
        """
        pass