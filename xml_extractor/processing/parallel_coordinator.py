"""
Parallel Processing Coordinator for XML extraction system.

This module provides multiprocessing capabilities to process XML records
in parallel across multiple CPU cores for improved throughput.

ARCHITECTURE & RESPONSIBILITIES
================================

The ParallelCoordinator is a WORKER POOL MANAGER, not a connection manager. Its job is:

1. MULTIPROCESSING ORCHESTRATION
   - Creates N independent worker processes (one per CPU core)
   - Each worker is COMPLETELY ISOLATED (separate Python interpreter, separate memory space)
   - Coordinates work distribution: assigns XML records to workers

2. NOT CONNECTION MANAGEMENT (important!)
   - Does NOT manage database connections directly
   - Each worker INDEPENDENTLY creates its own connections via MigrationEngine
   - Each worker has its own connection(s) to the database
   - Multiple workers = multiple independent connections to SQL Server

3. DATA FLOW
   
   ProductionProcessor (main process)
   ├─ Loads XML records from app_xml table
   ├─ Creates ParallelCoordinator (with connection string passed to workers)
   └─ Calls process_xml_batch(xml_records)
      └─ ParallelCoordinator.process_xml_batch()
         ├─ Creates mp.Pool(num_workers=4)  ← Spawns 4 independent worker processes
         ├─ For each XML record:
         │  └─ Worker process (independent interpreter):
         │     ├─ _init_worker() [runs once per worker]
         │     │  └─ Creates its own MigrationEngine(connection_string)
         │     │     └─ Each worker gets ONE connection to SQL Server
         │     │
         │     └─ _process_work_item() [runs for each assigned XML]
         │        ├─ Parse XML (in-memory)
         │        ├─ Map to database schema (in-memory)
         │        └─ Insert via own MigrationEngine connection
         │
         └─ Results aggregated back to main process

4. CONNECTION POOLING RELATIONSHIP
   
   How it works with connection pooling:
   
   WITHOUT pooling (old code):
   - Worker 1 creates connection → uses it → closes it
   - Worker 2 creates connection → uses it → closes it
   - Worker 3 creates connection → uses it → closes it
   - Worker 4 creates connection → uses it → closes it
   
   WITH pooling (new code):
   - Worker 1 creates connection from pool (or opens new if min pool not met)
   - Worker 2 requests connection → gets from pool OR creates new (up to max)
   - Worker 3 requests connection → gets from pool OR creates new (up to max)
   - Worker 4 requests connection → gets from pool OR creates new (up to max)
   
   KEY INSIGHT: Pooling is PROCESS-LEVEL, not WORKER-LEVEL
   - The ODBC driver manages the pool at the OS level
   - Separate Python processes DON'T share the same pool!
   - Each Python process (worker) gets its own independent pool
   - So with 4 workers: potentially 4 independent pools × 4 min connections = 16 min connections!

5. WHY POOLING MIGHT HURT (the regression we're seeing)
   
   a) Overhead of maintaining multiple pools
   b) ODBC connection state reset between reuses (expensive)
   c) Lock contention with multiple workers querying simultaneously
   d) SQLExpress disk I/O can't handle 4 parallel queries
   e) Pool management itself is slower than creating fresh connections for short-lived ops

6. BOTTLENECK ANALYSIS
   
   ParallelCoordinator is trying to maximize:
   - CPU utilization (by running 4 Python processes in parallel)
   - Data processing throughput (parsing + mapping happens in parallel)
   
   But ParallelCoordinator CANNOT improve:
   - SQL Server I/O performance (disk speed, query optimization, indexes)
   - Network latency (local, so not an issue)
   - Database query execution (connection pooling helps minimally)
   
   If SQL Server CPU < 10%, then:
   - SQL Server is NOT the bottleneck
   - Likely bottleneck: Disk I/O, Query execution time, Table locks
   - Solution: Query optimization, better indexes, or CHANGE THE APPROACH
   
   If Python CPU < 20% (XML parsing/mapping), then:
   - Parsing and mapping are NOT the bottleneck
   - Likely bottleneck: Database operations (inserts, queries)
   - Solution: Connection pooling (minimal help), query optimization, batch sizes

WHEN TO USE PARALLELIZATION vs OPTIMIZATION
==============================================

ParallelCoordinator is good at:
✅ Processing multiple XMLs simultaneously (parsing, mapping) while I/O waits
✅ Utilizing multiple CPU cores for CPU-intensive work
✅ Scaling on multi-core machines

ParallelCoordinator is BAD at:
❌ Making disk I/O faster
❌ Making queries execute faster
❌ Reducing lock contention (can actually increase it!)
❌ Helping if bottleneck is SQL Server CPU/disk

WHAT TO DO IF BOTTLENECK IS DATABASE
=====================================

When ParallelCoordinator hits database I/O wall:
1. Add indices to WHERE clause columns (SELECT WHERE app_id IN (...))
2. Partition tables for faster queries
3. Reduce query complexity
4. Batch inserts more efficiently (use BULK INSERT, not individual INSERTs)
5. Tune SQL Server settings
6. Use ASYNC queries (query while processing next XML)

Connection pooling is NOT a silver bullet - it helps with connection creation overhead
(usually < 5% of total time), not with actual query execution.

PERFORMANCE TUNING DOC:
For production, comment out or revert the following:
- Pass log_level and log_file to ParallelCoordinator for worker logging (see process_xml_batch)
- Enable detailed timing/logging in parallel_coordinator.py (_init_worker)
- Any timing/logging added to mapping or database insert logic
- Any debug-level logging or extra diagnostics
- Set worker logging to WARNING or CRITICAL and remove file handler for best performance
"""

import logging
import multiprocessing as mp
import time
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from queue import Empty

from ..validation.pre_processing_validator import PreProcessingValidator
from ..parsing.xml_parser import XMLParser
from ..mapping.data_mapper import DataMapper
from ..database.migration_engine import MigrationEngine
from ..models import ProcessingResult


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


class ParallelCoordinator:
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
    
    # PRODUCTION: uncomment this in exchange for the other signature
    # def __init__(self, connection_string: str, mapping_contract_path: str, num_workers: Optional[int] = None, batch_size: int = 1000):
    def __init__(self, connection_string: str, mapping_contract_path: str, num_workers: Optional[int] = None, batch_size: int = 1000, log_level: str = "INFO", log_file: str = None):
        """
        Initialize the parallel coordinator.
        
        Args:
            connection_string: Database connection string
            mapping_contract_path: Path to mapping contract JSON file
            num_workers: Number of worker processes (defaults to CPU count)
            batch_size: Batch size for database operations
        """
        self.logger = logging.getLogger(__name__)
        self.connection_string = connection_string
        self.mapping_contract_path = mapping_contract_path
        self.num_workers = num_workers or mp.cpu_count()
        self.batch_size = batch_size
        
        # PRODUCTION: comment this out to remove performance logging
        self.log_level = log_level
        self.log_file = log_file
        # -----------------------------------------------------------
        
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
    
    def process_xml_batch(self, xml_records: List[Tuple[int, str]]) -> ProcessingResult:
        """
        Process a batch of XML records in parallel.
        
        Args:
            xml_records: List of (app_id, xml_content) tuples
            
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
        
        self.logger.info(f"Starting parallel processing of {len(xml_records)} XML records with {self.num_workers} workers")
        
        
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
                initargs=(self.connection_string, self.mapping_contract_path, self.progress_dict)
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
                        'error_message': r.error_message
                    }
                    for r in results
                ]
            }
        )
        
        self.logger.info(f"Parallel processing completed: {len(successful_results)}/{len(results)} successful "
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
        """Calculate parallel processing efficiency."""
        if not results or total_time <= 0:
            return 0.0
        
        # Sum of individual processing times
        total_individual_time = sum(r.processing_time for r in results)
        
        # Theoretical single-threaded time
        theoretical_time = total_individual_time
        
        # Efficiency = theoretical_time / (actual_time * num_workers)
        efficiency = theoretical_time / (total_time * self.num_workers) if total_time > 0 else 0.0
        
        return min(efficiency, 1.0)  # Cap at 100%


# Global worker state (initialized once per worker process)
_worker_validator = None
_worker_parser = None
_worker_mapper = None
_worker_migration_engine = None
_worker_progress_dict = None


def _init_worker(connection_string: str, mapping_contract_path: str, progress_dict):
    """
    Initialize worker process with required components.
    PERFORMANCE TUNING: Worker logging disabled for maximum performance.
    Only ERROR+ level logging is active in workers.
    """
    global _worker_validator, _worker_parser, _worker_mapper, _worker_migration_engine, _worker_progress_dict
    
    # PERFORMANCE: Disable all DEBUG/INFO logging in worker processes
    # Workers should only log critical errors, not debug/trace information
    import logging
    logging.basicConfig(level=logging.ERROR)
        
    try:
        _worker_validator = PreProcessingValidator()
        _worker_parser = XMLParser()
        _worker_mapper = DataMapper(mapping_contract_path=mapping_contract_path)
        _worker_migration_engine = MigrationEngine(connection_string)
        _worker_progress_dict = progress_dict
        
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
        
        # Clean up existing data -- local development only
        
        try:
            with _worker_migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM app_base WHERE app_id = ?", (validation_result.app_id,))
                conn.commit()
        except Exception:
            pass  # Ignore cleanup errors
        
        
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
        _worker_mapper.logger.info(f"PERF Timing: Mapping logic for app_id {work_item.app_id} took {mapping_duration:.4f} seconds")

        if not mapped_data:
            return WorkResult(
                sequence=work_item.sequence,
                app_id=work_item.app_id,
                success=False,
                error_stage='mapping',
                error_message="No data mapped from XML",
                processing_time=time.time() - start_time
            )

        # Stage 4: Database Insertion
        db_insert_start = time.time()
        insertion_results = _insert_mapped_data(mapped_data)
        db_insert_end = time.time()
        db_insert_duration = db_insert_end - db_insert_start
        _worker_mapper.logger.info(f"PERF Timing: DB insert for app_id {work_item.app_id} took {db_insert_duration:.4f} seconds")
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
            tables_populated=list(mapped_data.keys())
        )
        
    except Exception as e:
        # Update worker stats
        if worker_id in _worker_progress_dict['worker_stats']:
            _worker_progress_dict['worker_stats'][worker_id]['processed'] += 1
            _worker_progress_dict['worker_stats'][worker_id]['failed'] += 1
        
        # Determine error stage from exception type and category
        error_stage = 'unknown'
        if hasattr(e, 'error_category'):
            if e.error_category == 'constraint_violation':
                error_stage = 'constraint_violation'
            elif e.error_category == 'database_error':
                error_stage = 'database_error'
            elif e.error_category == 'system_error':
                error_stage = 'system_error'
        
        return WorkResult(
            sequence=work_item.sequence,
            app_id=work_item.app_id,
            success=False,
            error_stage=error_stage,
            error_message=str(e),
            processing_time=time.time() - start_time
        )


def _insert_mapped_data(mapped_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, int]:
    """Insert mapped data using proven table order."""
    global _worker_migration_engine
    
    insertion_results = {}
    
    # Use proven table order from benchmarks
    table_order = ["app_base", "app_operational_cc", "app_pricing_cc", 
                  "app_transactional_cc", "app_solicited_cc", 
                  "contact_base", "contact_address", "contact_employment"]
    
    for table_name in table_order:
        records = mapped_data.get(table_name, [])
        if records:
            enable_identity = table_name in ["app_base", "contact_base"]
            inserted_count = _worker_migration_engine.execute_bulk_insert(
                records, 
                table_name, 
                enable_identity_insert=enable_identity
            )
            insertion_results[table_name] = inserted_count
    
    return insertion_results