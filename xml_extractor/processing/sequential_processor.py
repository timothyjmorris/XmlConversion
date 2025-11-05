"""
Sequential XML Processor - Single-threaded processing for testing and debugging.

Implements the same BatchProcessorInterface as ParallelCoordinator but processes
records sequentially in the main process. Useful for:
- Unit testing (easier to debug)
- Integration testing (no multiprocessing complexity)
- Development and troubleshooting
- Comparing sequential vs parallel performance
"""

import logging
import time
from typing import List, Tuple, Optional

from ..validation.pre_processing_validator import PreProcessingValidator
from ..parsing.xml_parser import XMLParser
from ..mapping.data_mapper import DataMapper
from ..database.migration_engine import MigrationEngine
from ..models import ProcessingResult
from ..interfaces import BatchProcessorInterface


class SequentialProcessor(BatchProcessorInterface):
    """
    Single-threaded XML processor for sequential record processing.
    
    Processes XML records one at a time in the main process. Useful for:
    - Testing (no multiprocessing complexity)
    - Debugging (easier stack traces)
    - Development (faster iteration)
    - Performance comparison (baseline for parallelization gains)
    
    Features:
    - Single database connection for all records
    - Same processing pipeline as workers in ParallelCoordinator
    - Same error handling and validation
    - Easier debugging and testing
    """
    
    def __init__(self, 
                 connection_string: str, 
                 mapping_contract_path: str, 
                 batch_size: int = 1000, 
                 log_level: str = "INFO",
                 session_id: Optional[str] = None, 
                 app_id_start: Optional[int] = None, 
                 app_id_end: Optional[int] = None):
        """
        Initialize the sequential processor.
        
        Args:
            connection_string: Database connection string
            mapping_contract_path: Path to mapping contract JSON file
            batch_size: Batch size for database operations
            log_level: Logging level
            session_id: Session identifier for processing_log tracking
            app_id_start: Starting app_id for range processing
            app_id_end: Ending app_id for range processing
        """
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string
        self.mapping_contract_path = mapping_contract_path
        self.batch_size = batch_size
        self.log_level = log_level
        self.session_id = session_id
        self.app_id_start = app_id_start
        self.app_id_end = app_id_end
        
        # Initialize components
        self.validator = PreProcessingValidator()
        self.parser = XMLParser()
        self.mapper = DataMapper(mapping_contract_path=mapping_contract_path)
        self.migration_engine = MigrationEngine(
            connection_string=connection_string,
            log_level=log_level
        )
        
        self.logger.info("SequentialProcessor initialized (single-threaded)")
    
    def process_xml_batch(self, 
                         xml_records: List[Tuple[int, str]], 
                         batch_number: int = 1) -> ProcessingResult:
        """
        Process a batch of XML records sequentially.
        
        Args:
            xml_records: List of (app_id, xml_content) tuples
            batch_number: Batch sequence number (for logging)
            
        Returns:
            ProcessingResult with metrics and results
        """
        if not xml_records:
            return ProcessingResult()
        
        start_time = time.time()
        self.logger.info(f"Batch {batch_number}: Starting sequential processing of {len(xml_records)} XML records")
        
        result = ProcessingResult()
        result.batch_number = batch_number
        result.total_records = len(xml_records)
        result.start_time = start_time
        
        successful_records = 0
        failed_records = 0
        tables_populated = set()
        
        for sequence, (app_id, xml_content) in enumerate(xml_records, 1):
            try:
                # Validate XML structure
                validation_result = self.validator.validate_xml_structure(xml_content)
                if not validation_result.is_valid:
                    self.logger.warning(f"Sequence {sequence}, App {app_id}: XML validation failed: {validation_result.errors}")
                    result.failed_items.append({
                        'app_id': app_id,
                        'error_stage': 'validation',
                        'error': str(validation_result.errors)
                    })
                    failed_records += 1
                    continue
                
                # Parse XML
                xml_element = self.parser.parse_xml_stream(xml_content)
                if xml_element is None:
                    self.logger.warning(f"Sequence {sequence}, App {app_id}: XML parsing returned None")
                    result.failed_items.append({
                        'app_id': app_id,
                        'error_stage': 'parsing',
                        'error': 'Parse returned None'
                    })
                    failed_records += 1
                    continue
                
                # Apply mapping contract
                extracted_data = self.mapper.apply_mapping_contract(xml_element, app_id)
                if not extracted_data:
                    self.logger.warning(f"Sequence {sequence}, App {app_id}: Mapping returned no data")
                    result.failed_items.append({
                        'app_id': app_id,
                        'error_stage': 'mapping',
                        'error': 'Mapping returned no data'
                    })
                    failed_records += 1
                    continue
                
                # Insert to database
                tables_in_batch = set()
                with self.migration_engine.get_connection() as conn:
                    for table_name, records in extracted_data.items():
                        if records:
                            count = self.migration_engine.execute_bulk_insert(
                                records=records,
                                table_name=table_name,
                                enable_identity_insert=(table_name == 'contact_base'),
                                connection=conn
                            )
                            tables_in_batch.add(table_name)
                            self.logger.debug(f"Sequence {sequence}, App {app_id}: Inserted {count} records into {table_name}")
                    
                    conn.commit()
                
                tables_populated.update(tables_in_batch)
                successful_records += 1
                self.logger.info(f"Sequence {sequence}, App {app_id}: Successfully processed ({len(tables_in_batch)} tables)")
                
            except Exception as e:
                self.logger.error(f"Sequence {sequence}, App {app_id}: Processing failed: {str(e)}")
                result.failed_items.append({
                    'app_id': app_id,
                    'error_stage': 'processing',
                    'error': str(e)
                })
                failed_records += 1
        
        # Update result
        result.successful_items = successful_records
        result.failed_items_count = failed_records
        result.end_time = time.time()
        result.processing_time = result.end_time - start_time
        
        self.logger.info(
            f"Batch {batch_number}: Sequential processing complete - "
            f"Success: {successful_records}, Failed: {failed_records}, "
            f"Time: {result.processing_time:.2f}s"
        )
        
        return result
