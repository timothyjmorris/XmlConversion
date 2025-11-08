"""
Parallel Processing Coordinator - Multiprocessing Worker Pool Manager

Orchestrates parallel XML processing across multiple CPU cores using worker pools.
Each worker independently loads MappingContract, parses XML, maps data, and inserts atomically.

KEY FEATURES:
- Multiprocessing: N independent worker processes (isolated memory/Python interpreters)
- Contract-driven: Each worker loads mapping_contract.json independently
- Atomic transactions: Single-connection per application (zero orphaned records)
- Session tracking: Tracks session_id, app_id_start/end for processing_log audit trail
- Performance: ~1,500-1,600 apps/min sustained (4 workers, batch-size=500)

ARCHITECTURE:
- NOT a connection manager: Each worker creates its own independent connections
- Worker pool approach: Assigns XML records to workers via multiprocessing.Pool
- Data flow: XML → Worker → Parser → Mapper → Engine → Database (atomic per app)

For architecture details, see ARCHITECTURE.md (schema isolation, concurrency, atomicity)
"""

import logging
import multiprocessing as mp
import time
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass

from ..validation.pre_processing_validator import PreProcessingValidator
from ..parsing.xml_parser import XMLParser
from ..mapping.data_mapper import DataMapper
from ..database.migration_engine import MigrationEngine
from ..models import ProcessingResult
from ..interfaces import BatchProcessorInterface
from ..exceptions import (XMLParsingError, DataMappingError, DataTransformationError,
                         ValidationError, DatabaseConnectionError, DatabaseConstraintError)


@dataclass
class WorkItem:
    """Work item for parallel processing queue."""
    sequence: int
    app_id: int
    xml_content: str
    record_id: str


@dataclass
class WorkResult:
    """Result from processing a work item."""
    sequence: int
    app_id: int
    success: bool
    error_stage: Optional[str] = None
    error_message: Optional[str] = None
    records_inserted: int = 0
    processing_time: float = 0.0
    tables_populated: List[str] = None
    quality_issues: List[str] = None  # Non-fatal data quality warnings (e.g., validation errors during optional field processing)


class ParallelCoordinator(BatchProcessorInterface):
    """
    Multiprocessing Pool Manager for parallel XML record processing.
    
    CRITICAL: This is a WORKER POOL, NOT a CONNECTION POOL.
    
    Responsibilities:
    - Creates N independent worker processes (one per CPU core)
    - Distributes XML records to workers for parallel processing
    - Each worker independently manages its own database connections
    - Coordinates results aggregation and progress tracking
    
    Worker Lifecycle:
    1. ParallelCoordinator creates mp.Pool(num_workers=4)
    2. Each worker process runs _init_worker() once
       - Loads mapping contract
       - Creates its own MigrationEngine with connection string
       - Each worker gets its own database connection(s)
    3. For each XML record, a worker runs _process_work_item()
       - Parses XML (in-memory, fast)
       - Maps to database schema (in-memory, fast)
       - Inserts via its own MigrationEngine connection
    4. Workers complete, results returned to main process
    
    Connection Management (IMPORTANT):
    - ParallelCoordinator does NOT manage connections
    - Each worker independently creates connections via MigrationEngine
    - With N workers: N independent connections to SQL Server
    - If connection string includes "Pooling=True":
      - Each worker's ODBC driver manages its own pool
      - Potentially N pools, not 1 shared pool!
      - This can INCREASE overhead instead of reducing it
    
    Performance Characteristics:
    - Best when: CPU-intensive processing (XML parsing/mapping) overlaps with I/O waits
    - Worst when: Database I/O is bottleneck (< 10% SQL Server CPU suggests this)
    - Scaling: Improves up to CPU core count, then plateaus or regresses
    
    Diagnostic:
    - If SQL Server CPU < 10%: Database I/O is bottleneck (not a parallelization problem)
    - If Python process CPU < 20%: Parsing/mapping not bottleneck (database is)
    - If high I/O wait: Adding more workers makes it WORSE due to lock contention
    """
    
    def __init__(self, connection_string: str, mapping_contract_path: str, num_workers: Optional[int] = None, batch_size: int = 1000, log_level: str = "INFO", log_file: str = None, session_id: str = None, app_id_start: int = None, app_id_end: int = None):
        """
        Initialize the parallel coordinator.
        
        Args:
            connection_string: Database connection string
            mapping_contract_path: Path to mapping contract JSON file
            num_workers: Number of worker processes (defaults to CPU count)
            batch_size: Batch size for database operations
            log_level: Logging level for workers
            log_file: Log file path for workers
            session_id: Session identifier for processing_log tracking
            app_id_start: Starting app_id for range processing (for processing_log)
            app_id_end: Ending app_id for range processing (for processing_log)
        """
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string
        self.mapping_contract_path = mapping_contract_path
        self.num_workers = num_workers or mp.cpu_count()
        self.batch_size = batch_size
        
        # Performance logging configuration
        self.log_level = log_level
        self.log_file = log_file
        
        # Session metadata for processing_log
        self.session_id = session_id
        self.app_id_start = app_id_start
        self.app_id_end = app_id_end
        
        # Shared progress tracking
        self.manager = mp.Manager()
        self.progress_dict = self.manager.dict({
            'total_items': 0,
            'completed_items': 0,
            'successful_items': 0,
            'failed_items': 0,
            'start_time': None,
            'worker_stats': self.manager.dict()
        })
        
        self.logger.info(f"ParallelCoordinator initialized with {self.num_workers} workers")
    
    def process_xml_batch(self, xml_records: List[Tuple[int, str]], batch_number: int = 1) -> ProcessingResult:
        """
        Process a batch of XML records in parallel using multiprocessing.Pool.
        
        Architecture:
        1. Spawns N worker processes (one per CPU core)
        2. Each worker independently processes assigned XML records
        3. Workers perform parsing, mapping, and database insertion
        4. Results aggregated and returned to main process
        
        Each worker:
        - Creates its own MigrationEngine with database connection
        - Validates, parses, maps, and inserts XML data
        - Respects FK dependency ordering to prevent constraint violations
        - Returns result with success/failure status and record count
        
        Args:
            xml_records: List of (app_id, xml_content) tuples
            batch_number: Batch sequence number (default: 1)
            
        Returns:
            ProcessingResult with comprehensive metrics
        """
        if not xml_records:
            return ProcessingResult()
        
        start_time = time.time()
        self.progress_dict['total_items'] = len(xml_records)
        self.progress_dict['completed_items'] = 0
        self.progress_dict['successful_items'] = 0
        self.progress_dict['failed_items'] = 0
        self.progress_dict['start_time'] = start_time
        
        self.logger.info(f"Batch {batch_number}: Starting parallel processing of {len(xml_records)} XML records with {self.num_workers} workers")
        
        # Create work items
        work_items = [
            WorkItem(
                sequence=i,
                app_id=app_id,
                xml_content=xml_content,
                record_id=f"parallel_batch_{i}"
            )
            for i, (app_id, xml_content) in enumerate(xml_records, 1)
        ]
        
        # Process in parallel using multiprocessing.Pool
        results = []
        try:
            with mp.Pool(
                processes=self.num_workers,
                initializer=_init_worker,
                initargs=(self.connection_string, self.mapping_contract_path, self.progress_dict, self.session_id, self.app_id_start, self.app_id_end)
            ) as pool:
                
                # Submit all work items
                async_results = [
                    pool.apply_async(_process_work_item, (work_item,))
                    for work_item in work_items
                ]
                
                # Collect results with progress tracking
                for async_result in async_results:
                    try:
                        result = async_result.get(timeout=300)  # 5 minute timeout per item
                        results.append(result)
                        
                        # Update progress
                        self.progress_dict['completed_items'] += 1
                        if result.success:
                            self.progress_dict['successful_items'] += 1
                        else:
                            self.progress_dict['failed_items'] += 1
                        
                        # Log progress periodically
                        if len(results) % 5 == 0 or len(results) == len(work_items):
                            self._log_progress()
                            
                    except Exception as e:
                        self.logger.error(f"Worker process failed: {e}")
                        # Create failed result
                        failed_result = WorkResult(
                            sequence=len(results) + 1,
                            app_id=0,
                            success=False,
                            error_stage='worker_process',
                            error_message=str(e)
                        )
                        results.append(failed_result)
                        self.progress_dict['completed_items'] += 1
                        self.progress_dict['failed_items'] += 1
        
        except Exception as e:
            self.logger.error(f"Parallel processing failed: {e}")
            raise
        
        # Calculate final metrics
        end_time = time.time()
        processing_time = end_time - start_time
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        total_records_inserted = sum(r.records_inserted for r in successful_results)
        
        # Create processing result
        processing_result = ProcessingResult(
            records_processed=len(results),
            records_successful=len(successful_results),
            records_failed=len(failed_results),
            processing_time_seconds=processing_time,
            performance_metrics={
                'records_per_second': len(results) / processing_time if processing_time > 0 else 0,
                'records_per_minute': (len(results) / processing_time * 60) if processing_time > 0 else 0,
                'total_records_inserted': total_records_inserted,
                'avg_processing_time_per_record': processing_time / len(results) if results else 0,
                'parallel_efficiency': self._calculate_parallel_efficiency(results, processing_time),
                'worker_count': self.num_workers,
                'individual_results': [
                    {
                        'sequence': r.sequence,
                        'app_id': r.app_id,
                        'success': r.success,
                        'processing_time': r.processing_time,
                        'records_inserted': r.records_inserted,
                        'error_stage': r.error_stage,
                        'error_message': r.error_message,
                        'quality_issues': r.quality_issues
                    }
                    for r in results
                ]
            }
        )
        
        self.logger.info(f"  - Batch {batch_number}: Parallel processing completed: {len(successful_results)}/{len(results)} successful "
                        f"in {processing_time:.2f}s ({processing_result.performance_metrics['records_per_minute']:.1f} rec/min)")
        
        # OUTPUT to console with batch number
        print(f"  - Batch {batch_number} completed: {len(successful_results)}/{len(results)} successful "
                        f"in {processing_time:.2f}s ({processing_result.performance_metrics['records_per_minute']:.1f} rec/min)")
        
        return processing_result
    
    def _log_progress(self):
        """Log current progress with throughput metrics."""
        progress = dict(self.progress_dict)
        
        if progress['start_time']:
            elapsed_time = time.time() - progress['start_time']
            if elapsed_time > 0:
                current_rate = progress['completed_items'] / elapsed_time * 60  # per minute
                eta_minutes = (progress['total_items'] - progress['completed_items']) / (current_rate / 60) if current_rate > 0 else 0
                
                self.logger.info(
                    f"Progress: {progress['completed_items']}/{progress['total_items']} "
                    f"({progress['completed_items']/progress['total_items']*100:.1f}%) - "
                    f"Rate: {current_rate:.1f} rec/min - "
                    f"ETA: {eta_minutes:.1f} min - "
                    f"Success: {progress['successful_items']}, Failed: {progress['failed_items']}"
                )
    
    def _calculate_parallel_efficiency(self, results: List[WorkResult], total_time: float) -> float:
        """
        Calculate parallel processing efficiency as a ratio of actual vs. theoretical speedup.
        
        Efficiency Formula:
        - Sequential time = sum of all individual worker processing times
        - Actual speedup = sequential_time / total_parallel_time
        - Theoretical ideal speedup = num_workers (perfect parallelization)
        - Efficiency = actual_speedup / ideal_speedup
        
        Returns:
            Efficiency ratio (0.0 to 1.0):
            - 1.0 = perfect parallelization (achieved theoretical maximum speedup)
            - 0.5 = 50% efficiency (half the theoretical speedup achieved)
            - Near 0.0 = poor parallelization or high overhead
            
        Example:
            - 4 workers, sequential_time=1000ms, total_time=300ms
            - Actual speedup = 1000/300 = 3.33x
            - Ideal speedup = 4.0x
            - Efficiency = 3.33/4 = 0.83 (83% efficiency)
        """
        if not results or total_time <= 0:
            return 0.0
        
        # Sum of individual processing times (sequential equivalent)
        sequential_time = sum(r.processing_time for r in results)
        
        # Actual speedup: how much faster did we run in parallel vs sequentially?
        actual_speedup = sequential_time / total_time if total_time > 0 else 0.0
        
        # Ideal speedup with N workers (theoretical maximum)
        ideal_speedup = self.num_workers
        
        # Efficiency: ratio of actual to ideal speedup (0.0 to 1.0)
        efficiency = actual_speedup / ideal_speedup if ideal_speedup > 0 else 0.0
        
        return min(efficiency, 1.0)  # Cap at 100%


# Global worker state (initialized once per worker process)
_worker_validator = None
_worker_parser = None
_worker_mapper = None
_worker_migration_engine = None
_worker_progress_dict = None
_worker_session_id = None
_worker_app_id_start = None
_worker_app_id_end = None


def _init_worker(connection_string: str, mapping_contract_path: str, progress_dict, session_id: str = None, app_id_start: int = None, app_id_end: int = None):
    """
    Initialize worker process with required components.
    
    This function runs ONCE per worker process at startup. Each worker process gets its own
    isolated Python interpreter, memory space, and database connection.
    
    Args:
        connection_string: Database connection string
        mapping_contract_path: Path to mapping contract JSON
        progress_dict: Shared dict for progress tracking
        session_id: Session identifier for processing_log tracking
        app_id_start: Starting app_id for range processing (for processing_log)
        app_id_end: Ending app_id for range processing (for processing_log)
    
    PERFORMANCE TUNING: Worker logging disabled for maximum performance.
    Only ERROR+ level logging is active in workers.
    """
    global _worker_validator, _worker_parser, _worker_mapper, _worker_migration_engine, _worker_progress_dict
    global _worker_session_id, _worker_app_id_start, _worker_app_id_end
    
    # Initialize worker processes with minimal logging (ERROR level only)
    import logging
    logging.basicConfig(level=logging.ERROR)
        
    try:
        _worker_validator = PreProcessingValidator()
        _worker_parser = XMLParser()
        _worker_mapper = DataMapper(mapping_contract_path=mapping_contract_path)
        _worker_migration_engine = MigrationEngine(connection_string)
        _worker_progress_dict = progress_dict
        
        # Store session metadata for processing_log
        _worker_session_id = session_id
        _worker_app_id_start = app_id_start
        _worker_app_id_end = app_id_end
        
        # Initialize worker stats
        worker_id = mp.current_process().pid
        _worker_progress_dict['worker_stats'][worker_id] = {
            'processed': 0,
            'successful': 0,
            'failed': 0
        }
        
    except Exception as e:
        logging.error(f"Worker initialization failed: {e}")
        raise


def _process_work_item(work_item: WorkItem) -> WorkResult:
    """Process a single work item in a worker process."""
    global _worker_validator, _worker_parser, _worker_mapper, _worker_migration_engine, _worker_progress_dict
    global _worker_session_id, _worker_app_id_start, _worker_app_id_end
    
    start_time = time.time()
    worker_id = mp.current_process().pid
    
    try:
        # Stage 1: Validation
        validation_result = _worker_validator.validate_xml_for_processing(
            work_item.xml_content,
            work_item.record_id
        )
        
        if not validation_result.is_valid or not validation_result.can_process:
            return WorkResult(
                sequence=work_item.sequence,
                app_id=work_item.app_id,
                success=False,
                error_stage='validation',
                error_message=f"Validation failed: {validation_result.validation_errors}",
                processing_time=time.time() - start_time
            )
        
        # Stage 2: Parsing
        root = _worker_parser.parse_xml_stream(work_item.xml_content)
        xml_data = _worker_parser.extract_elements(root)
        
        if root is None or not xml_data:
            return WorkResult(
                sequence=work_item.sequence,
                app_id=work_item.app_id,
                success=False,
                error_stage='parsing',
                error_message="Failed to parse XML or extract elements",
                processing_time=time.time() - start_time
            )
        
        # Stage 3: Mapping
        mapping_start = time.time()
        mapped_data = _worker_mapper.map_xml_to_database(
            xml_data,
            validation_result.app_id,
            validation_result.valid_contacts,
            root
        )
        mapping_end = time.time()
        mapping_duration = mapping_end - mapping_start
        if _worker_mapper.logger.isEnabledFor(logging.DEBUG):
            _worker_mapper.logger.debug(f"PERF Timing: Mapping logic for app_id {work_item.app_id} took {mapping_duration:.4f} seconds")

        if not mapped_data:
            return WorkResult(
                sequence=work_item.sequence,
                app_id=work_item.app_id,
                success=False,
                error_stage='mapping',
                error_message="No data mapped from XML",
                processing_time=time.time() - start_time
            )
        
        # Capture data quality issues from mapper (non-fatal warnings)
        quality_issues = _worker_mapper.get_validation_errors() if hasattr(_worker_mapper, 'get_validation_errors') else []
        
        # Add processing_log entry to mapped_data (atomically coupled with data insertion)
        # This ensures log entry only exists if data insertion succeeds (single transaction)
        # processing_log has FK constraint on app_id → app_base.app_id, so it must come after app_base in insertion order
        mapped_data['processing_log'] = [{
            'app_id': work_item.app_id,
            'status': 'success',
            'failure_reason': None,
            'processing_time': datetime.utcnow(),
            'session_id': _worker_session_id,
            'app_id_start': _worker_app_id_start,
            'app_id_end': _worker_app_id_end
        }]

        # Stage 4: Database Insertion
        # Direct blocking inserts with FK dependency ordering to prevent constraint violations
        db_insert_start = time.time()
        insertion_results = _insert_mapped_data_with_fk_order(mapped_data)
        db_insert_duration = time.time() - db_insert_start
        
        total_inserted = sum(insertion_results.values())
        
        if total_inserted == 0:
            return WorkResult(
                sequence=work_item.sequence,
                app_id=work_item.app_id,
                success=False,
                error_stage='insertion',
                error_message="No records were inserted into database",
                processing_time=time.time() - start_time
            )
        
        # Update worker stats
        if worker_id in _worker_progress_dict['worker_stats']:
            _worker_progress_dict['worker_stats'][worker_id]['processed'] += 1
            _worker_progress_dict['worker_stats'][worker_id]['successful'] += 1
        
        return WorkResult(
            sequence=work_item.sequence,
            app_id=work_item.app_id,
            success=True,
            records_inserted=total_inserted,
            processing_time=time.time() - start_time,
            tables_populated=list(mapped_data.keys()),
            quality_issues=quality_issues if quality_issues else None
        )
        
    except Exception as e:
        # Update worker stats
        if worker_id in _worker_progress_dict['worker_stats']:
            _worker_progress_dict['worker_stats'][worker_id]['processed'] += 1
            _worker_progress_dict['worker_stats'][worker_id]['failed'] += 1
        
        # Determine error stage from exception type
        if isinstance(e, XMLParsingError):
            error_stage = 'parsing'
        elif isinstance(e, ValidationError):
            error_stage = 'validation'
        elif isinstance(e, (DataMappingError, DataTransformationError)):
            error_stage = 'mapping'
        elif isinstance(e, DatabaseConstraintError):
            error_stage = 'constraint_violation'
        elif isinstance(e, DatabaseConnectionError):
            error_stage = 'database'
        else:
            error_stage = 'unknown'
        
        # Log the failure to processing_log so we don't retry this app_id
        # This prevents repeatedly attempting to process failed applications
        try:
            failure_message = f"{error_stage}: {str(e)}"
            _worker_migration_engine.execute_bulk_insert(
                records=[{
                    'app_id': work_item.app_id,
                    'status': 'failed',
                    'failure_reason': failure_message[:500],  # Truncate to column size
                    'processing_time': datetime.utcnow(),
                    'session_id': _worker_session_id,
                    'app_id_start': _worker_app_id_start,
                    'app_id_end': _worker_app_id_end
                }],
                table_name='processing_log',
                enable_identity_insert=False
            )
        except Exception as log_error:
            # If logging fails, at least log to Python logs (logging already imported at module level)
            logging.error(f"Failed to log failure for app_id {work_item.app_id}: {log_error}")
        
        return WorkResult(
            sequence=work_item.sequence,
            app_id=work_item.app_id,
            success=False,
            error_stage=error_stage,
            error_message=str(e),
            processing_time=time.time() - start_time
        )


def _insert_mapped_data_with_fk_order(mapped_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
    """
    Insert mapped data respecting FK dependency order with atomic transaction per application.
    
    CRITICAL ATOMICITY: All table inserts for a single application occur within a single
    database transaction. If any insert fails, the entire transaction is rolled back,
    preventing orphaned records and ensuring data consistency.
    
    CRITICAL FK ORDERING: This order prevents FK constraint violations by ensuring parent records
    are inserted before child records. The insertion order is defined in the mapping
    contract's table_insertion_order field, which should specify the FK dependency order.
    
    Fallback behavior (Option A):
    - Tables in table_insertion_order are processed in that order
    - Any tables in mapped_data NOT in table_insertion_order are appended at the end
    - This allows new product lines to add tables without updating the contract order
    - If a child table is added without updating the order, it may encounter FK errors
      (this should be caught during contract definition for the new product line)
    
    Args:
        mapped_data: Dict of {table_name: [records]} from mapper
        
    Returns:
        Dict of {table_name: inserted_count} for each table processed
        
    Raises:
        XMLExtractionError: If any table insert fails (triggers rollback)
    """
    global _worker_migration_engine, _worker_mapper
    
    insertion_results = {}
    
    # Create single connection for atomic transaction spanning all tables
    # Use the context manager properly - it handles connection lifecycle
    with _worker_migration_engine.get_connection() as conn:
        try:
            # Get table insertion order from contract, or use fallback hardcoded order
            # The fallback ensures backward compatibility if contract doesn't specify order
            try:
                from ..config.config_manager import get_config_manager
                config_manager = get_config_manager()
                mapping_contract = config_manager.load_mapping_contract()
                table_order = mapping_contract.table_insertion_order if mapping_contract and mapping_contract.table_insertion_order else None
            except Exception:
                table_order = None
            
            # Fallback to hardcoded order if contract doesn't specify
            if not table_order:
                table_order = [
                    "app_base",              # Parent: all app_*_cc tables FK to this
                    "contact_base",          # Parent: contact_address/employment FK to this + FK to app_base
                    "app_operational_cc",    # Child of app_base
                    "app_pricing_cc",        # Child of app_base
                    "app_transactional_cc",  # Child of app_base
                    "app_solicited_cc",      # Child of app_base
                    "contact_address",       # Child of contact_base
                    "contact_employment",    # Child of contact_base
                ]
                _worker_mapper.logger.debug("Using fallback hardcoded table_insertion_order (contract order not available)")
            
            # Process tables in order using shared connection for atomic transaction
            processed_tables = set()
            for table_name in table_order:
                records = mapped_data.get(table_name, [])
                if records:
                    enable_identity = table_name in ["app_base", "contact_base"]
                    inserted_count = _worker_migration_engine.execute_bulk_insert(
                        records, 
                        table_name, 
                        enable_identity_insert=enable_identity,
                        connection=conn  # Pass shared connection
                    )
                    insertion_results[table_name] = inserted_count
                    processed_tables.add(table_name)
            
            # Option A: Append any tables not in the insertion order (for new product lines)
            # Log warning if unmapped tables are found (helps with contract debugging)
            unmapped_tables = set(mapped_data.keys()) - processed_tables
            if unmapped_tables:
                _worker_mapper.logger.warning(
                    f"Tables in mapped_data not in table_insertion_order (appending to end): {', '.join(sorted(unmapped_tables))}. "
                    f"If these are child tables with FK dependencies, update table_insertion_order in contract."
                )
                # Append unmapped tables at the end (risky but allows flexibility for new product lines)
                for table_name in sorted(unmapped_tables):
                    records = mapped_data[table_name]
                    if records:
                        enable_identity = table_name in ["app_base", "contact_base"]
                        inserted_count = _worker_migration_engine.execute_bulk_insert(
                            records, 
                            table_name, 
                            enable_identity_insert=enable_identity,
                            connection=conn  # Pass shared connection
                        )
                        insertion_results[table_name] = inserted_count
            
            # Commit transaction - all tables inserted successfully
            conn.commit()
            _worker_mapper.logger.debug(f"Committed transaction for application with {len(insertion_results)} tables")
            
        except Exception as e:
            # Rollback on any error
            try:
                conn.rollback()
                _worker_mapper.logger.error(f"Rolled back transaction due to error: {e}")
            except:
                pass
            raise
    
    return insertion_results
