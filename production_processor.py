"""
Production XML Processing Script

Contract-driven ETL processor for transforming XML records into normalized SQL Server tables.
Supports atomic transactions, parallel processing, and resume-safe operations.

QUICK START:
    python production_processor.py --server "localhost\\SQLEXPRESS" --database "XmlConversionDB"

For detailed documentation, see:
    - ARCHITECTURE.md (design decisions, data flow, FK ordering, atomicity)
    - OPERATOR_GUIDE.md (usage patterns, troubleshooting, monitoring)
    - run_production_processor.py (for large datasets >100k, use this orchestrator)

USAGE MODES:
    Defaults:  batch-size=500, limit=10000, workers=4, log-level=WARNING
    Range:     --app-id-start N --app-id-end M (concurrent-safe, recommended)
    Limit:     --limit N (process up to N records, testing/safety)

KEY FEATURES:
    • Atomic transactions: zero orphaned records, +14% throughput
    • Resume-safe: processing_log prevents reprocessing
    • Concurrent instances: non-overlapping app_id ranges prevent locks
    • Schema isolation: target_schema from MappingContract
    • Performance: 1,500-1,600 apps/min sustained (4 workers)
"""

import argparse
import sys
import time
import json
import logging
import statistics

from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

from xml_extractor.config.processing_defaults import ProcessingDefaults
from xml_extractor.processing.parallel_coordinator import ParallelCoordinator
from xml_extractor.database.migration_engine import MigrationEngine
from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.interfaces import MappingContract, BatchProcessorInterface
from xml_extractor.validation.mapping_contract_validator import MappingContractValidator


# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class ProductionProcessor:
    """
    Production-optimized XML processor with contract-driven schema isolation.
    
    ARCHITECTURE - Contract-Driven Schema Isolation:
    
        The ProductionProcessor implements a contract-driven schema isolation pattern where
        all database operations respect the target_schema specified in MappingContract:
        
        1. Source Access (Read-Only - Always [dbo]):
           - app_xml table (source XML data): [dbo].[app_xml] (hardcoded schema)
           - Used to extract XML documents for processing
           - Never written to by processor; read-only access
        
        2. Target Output (Schema-Isolated - Uses target_schema):
           - All output tables (app_base, contact_base, etc.): [{target_schema}].[table_name]
           - Example: target_schema="sandbox" → [sandbox].[app_base], [sandbox].[contact_base]
           - Example: target_schema="dbo" → [dbo].[app_base], [dbo].[contact_base]
           - Controlled by MappingContract.target_schema from mapping_contract.json
        
        3. Metadata Logging (Schema-Isolated - Uses target_schema):
           - Processing log: [{target_schema}].[processing_log]
           - Tracks success/failure of each application processed
           - Enables resume capability and duplicate prevention
           - Schema matches target tables for consistency
        
    Benefits of Contract-Driven Design:
        - Multiple processing pipelines can coexist (dev, staging, production)
        - Each pipeline can isolate data in separate schemas
        - No environment variables or configuration pollution
        - Clear, auditable data lineage through schema and processing_log
        - Supports blue/green deployments and schema versioning
    
    Key Responsibilities:
        1. Load MappingContract (via ConfigManager) at initialization
        2. Extract XML from [dbo].[app_xml] (hardcoded source schema)
        3. Coordinate parallel processing via ParallelCoordinator
        4. Log results to [{target_schema}].[processing_log]
        5. Report metrics and performance tracking
        6. Support resume capability via processing_log queries
    
    Integration with MigrationEngine:
        The MigrationEngine (final insertion stage) also implements contract-driven
        schema isolation:
        - Receives target_schema from same MappingContract
        - All INSERT operations qualified with [{target_schema}].[table_name]
        - Ensures data consistency across components
        - See: xml_extractor.database.migration_engine.MigrationEngine
    """
    
    def __init__(self, server: str, database: str, username: str = None, password: str = None,
                 workers: int = 4, batch_size: int = 1000, log_level: str = "INFO",
                 enable_pooling: bool = False, min_pool_size: int = 4, max_pool_size: int = 20,
                 enable_mars: bool = True, connection_timeout: int = 30,
                 app_id_start: int = None, app_id_end: int = None,
                 batch_processor: BatchProcessorInterface = None):
        """
        Initialize production processor.
        
        Args:
            server: SQL Server instance (e.g., "localhost\\SQLEXPRESS" or "prod-server")
            database: Database name
            username: SQL Server username (optional, uses Windows auth if not provided)
            password: SQL Server password (optional)
            workers: Number of parallel workers
            batch_size: Number of application XMLs to fetch from database per SQL query (pagination size)
            log_level: Logging level (CRITICAL, ERROR, WARNING, INFO, DEBUG)
            enable_pooling: Enable connection pooling (default: False for SQLExpress, True for SQL Server/Prod)
            min_pool_size: Minimum connection pool size (default: 4, only used if enable_pooling=True)
            max_pool_size: Maximum connection pool size (default: 20, only used if enable_pooling=True)
            enable_mars: Enable Multiple Active Result Sets (default: True)
            connection_timeout: Connection timeout in seconds (default: 30)
            app_id_start: Starting app_id for range processing (optional, for non-overlapping instances)
            app_id_end: Ending app_id for range processing (optional, for non-overlapping instances)
            batch_processor: BatchProcessorInterface implementation (optional). If None, ParallelCoordinator
                          used for production. Can also use MockProcessor for unit tests.
        """
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.workers = workers
        self.batch_size = batch_size
        self.enable_pooling = enable_pooling
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.enable_mars = enable_mars
        self.connection_timeout = connection_timeout
        self.app_id_start = app_id_start
        self.app_id_end = app_id_end
        self.batch_processor = batch_processor  # Store injected processor
        
        # Validate app_id range configuration
        if self.app_id_start is not None and self.app_id_end is not None:
            if self.app_id_start >= self.app_id_end:
                raise ValueError(f"Invalid app_id range: app_id_start ({self.app_id_start}) must be < app_id_end ({self.app_id_end})")
            if self.app_id_start < 1:
                raise ValueError(f"app_id_start must be >= 1, got {self.app_id_start}")
        elif (self.app_id_start is None) != (self.app_id_end is None):
            raise ValueError("Both app_id_start and app_id_end must be specified together, or neither")
        
        # Build connection string with performance optimizations
        self.connection_string = self._build_connection_string_with_pooling()
        
        # Performance tracking (must be before logging setup)
        self.session_start = datetime.now()
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        
        # Set up production logging
        self._setup_logging(log_level)
        
        # Initialize components
        self.mapping_contract_path = str(project_root / "config" / "mapping_contract.json")
        
        # Load mapping contract using config_manager (contract-driven schema isolation)
        self.config_manager = get_config_manager()
        self.mapping_contract = self.config_manager.load_mapping_contract()
        
        # Validate mapping contract structure (fail-fast on config errors)
        self._validate_contract()
        
        # Extract target schema from contract (with dbo default)
        self.target_schema = self.mapping_contract.target_schema if self.mapping_contract else 'dbo'
        
        self.logger.info(f"ProductionProcessor initialized:")
        self.logger.info(f"  Server: {server}")
        self.logger.info(f"  Database: {database}")
        self.logger.info(f"  Target Schema: {self.target_schema}")
        self.logger.info(f"  Workers: {workers}")
        self.logger.info(f"  Processing Batch Size: {batch_size}")
        if self.app_id_start is not None and self.app_id_end is not None:
            self.logger.info(f"  App ID Range: {self.app_id_start} to {self.app_id_end} (range-based processing)")
        else:
            self.logger.info(f"  App ID Range: ALL (full table processing)")
        if self.enable_pooling:
            self.logger.info(f"  Connection Pooling: ENABLED ({min_pool_size}-{max_pool_size})")
        else:
            self.logger.info(f"  Connection Pooling: DISABLED")
        self.logger.info(f"  MARS Enabled: {enable_mars}")
        self.logger.info(f"  Session ID: {self.session_id}")
        self.logger.debug(f"  Connection String: {self.connection_string}")

    def _build_connection_string_with_pooling(self) -> str:
        """
        Build SQL Server connection string with optional connection pooling.
        
        Includes:
        - Connection pooling (optional, controlled by enable_pooling parameter)
        - Multiple Active Result Sets (MARS)
        - Connection timeouts
        - UTF-8 encoding
        
        Note on Connection Pooling:
        - SQLExpress (local): Pooling disabled by default (adds I/O overhead)
        - SQL Server/Dev: Enable pooling (network latency makes it valuable)
        - Production: Enable pooling with larger pool sizes
        """
        # Handle server name formatting (replace double backslash with single)
        server_name = self.server.replace('\\\\', '\\')
        
        # Base connection string
        if self.username and self.password:
            # SQL Server authentication
            conn_string = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                          f"SERVER={server_name};"
                          f"DATABASE={self.database};"
                          f"UID={self.username};"
                          f"PWD={self.password};"
                          f"Connection Timeout={self.connection_timeout};"
                          f"Application Name=MAC XML Migration App;"
                          f"TrustServerCertificate=yes;"
                          f"Encrypt=no;")
        else:
            # Windows authentication
            conn_string = (f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                          f"SERVER={server_name};"
                          f"DATABASE={self.database};"
                          f"Connection Timeout={self.connection_timeout};"
                          f"Application Name=MAC XML Migration App;"
                          f"Trusted_Connection=yes;"
                          f"TrustServerCertificate=yes;"
                          f"Encrypt=no;")
        
        # Add MARS if enabled
        if self.enable_mars:
            conn_string += "MultipleActiveResultSets=True;"
        
        # Add connection pooling only if enabled
        if self.enable_pooling:
            conn_string += (f"Pooling=True;"
                           f"Min Pool Size={self.min_pool_size};"
                           f"Max Pool Size={self.max_pool_size};")
        else:
            conn_string += "Pooling=False;"
        
        return conn_string
    
    def _validate_contract(self):
        """
        Validate mapping contract structure before processing begins.
        
        Fail-fast on configuration errors to catch issues at startup,
        not after processing 1000 records.
        
        Raises:
            SystemExit: If contract validation fails (exit code 1)
        """
        
        # Validate contract structure (validator handles dataclass directly)
        validator = MappingContractValidator(self.mapping_contract)
        result = validator.validate_contract()
        
        if not result.is_valid:
            # Print validation errors to console
            print("\n" + "="*80)
            print(" MAPPING CONTRACT VALIDATION FAILED")
            print("="*80)
            print(result.format_summary())
            print("="*80)
            print("\n  Processing cannot continue with invalid contract configuration.")
            print("  Please fix the contract errors above and try again.\n")
            sys.exit(1)
        
        # Log warnings if present (non-blocking)
        if result.has_warnings:
            self.logger.warning("Mapping contract validation warnings:")
            for warning in result.warnings:
                self.logger.warning(warning.format_warning())
    
    def _setup_logging(self, log_level: str):
        """Set up production-optimized logging."""
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Configure logging with app_id range suffix for range-based processing
        range_suffix = f"_range_{self.app_id_start}_{self.app_id_end}" if self.app_id_start is not None and self.app_id_end is not None else ""
        log_file = logs_dir / f"production_{self.session_id}{range_suffix}.log"
        
        # Set root logger level to suppress all other module noise
        logging.getLogger().setLevel(logging.WARNING)
        
        # Configure our specific logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove any existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatters
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File handler (logs everything at our configured level)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(formatter)
        
        # Console handler (only shows INFO and above for our logger)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Add handlers to our logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Suppress all other loggers (xml_extractor modules, etc.)
        logging.getLogger('xml_extractor').setLevel(logging.WARNING)
        logging.getLogger('lxml').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

        # Enable migration engine logging based on log level (controlled by --log-level flag)
        logging.getLogger('xml_extractor.database.migration_engine').setLevel(getattr(logging, log_level.upper()))
        
        self.logger.info(f"Logging initialized: {log_file}")
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            migration_engine = MigrationEngine(self.connection_string)
            with migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()[0]
                self.logger.info(f"Database connection successful: {version}")
                return True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
    
    def get_xml_records(self, limit: Optional[int] = None, last_app_id: int = 0, exclude_failed: bool = True) -> List[Tuple[int, str]]:
        """
        Extract XML records from app_xml table with optional app_id range filtering.
        
        Range Processing Strategy:
            When app_id_start and app_id_end are specified, only processes records in that range:
            - app_id >= app_id_start AND app_id <= app_id_end
            
            This enables non-overlapping parallel processing across multiple instances,
            eliminating lock contention during duplicate detection queries.
        
        Args:
            limit: Maximum number of App XMLs to retrieve in this fetch (controls SQL TOP clause)
                  Used for batch-size pagination - fetches up to 'limit' application XMLs per query.
                  NOT the same as total application limit passed to run_full_processing().
            last_app_id: Only fetch App XMLs with app_id > last_app_id (cursor-based pagination)
            exclude_failed: Whether to exclude applications that have failed processing before
            
        Returns:
            List of (app_id, xml_content) tuples, ordered by app_id
        """
        self.logger.info(f"Extracting XML records (limit={limit}, last_app_id={last_app_id}, exclude_failed={exclude_failed})")
        if self.app_id_start is not None and self.app_id_end is not None:
            self.logger.info(f"  Range Filter: app_id {self.app_id_start} to {self.app_id_end}")
        else:
            self.logger.info(f"  Range Filter: ALL applications")
        
        xml_records = []
        
        try:
            # Load mapping contract to get the source table/column names (contract-driven)
            config_manager = get_config_manager()
            mapping_contract = config_manager.load_mapping_contract()
            source_table = mapping_contract.source_table
            source_column = mapping_contract.source_column

            migration_engine = MigrationEngine(self.connection_string)
            with migration_engine.get_connection() as conn:
                cursor = conn.cursor()

                # Build query for XML record extraction using TOP + range filter (avoids OFFSET scan)
                # ====================================================================================
                # Uses TOP for fast sequential access, cursor pagination for resumability

                # Build WHERE clause (use contract-driven source column)
                # Ensure column is properly quoted in case of mixed-case or special names
                where_conditions = [f"ax.[{source_column}] IS NOT NULL"]
                
                # Cursor pagination: only fetch records after the last processed app_id
                # This enables resuming mid-range if needed
                if last_app_id > 0:
                    where_conditions.append(f"ax.app_id > {last_app_id}")
                
                # Add app_id range filtering (optional, for non-overlapping instances)
                if self.app_id_start is not None:
                    where_conditions.append(f"ax.app_id >= {self.app_id_start}")
                if self.app_id_end is not None:
                    where_conditions.append(f"ax.app_id <= {self.app_id_end}")
                
                # Exclude already-processed records using NOT EXISTS
                if exclude_failed:
                    where_conditions.append(f"""NOT EXISTS (
                        SELECT 1 
                        FROM [{self.target_schema}].[processing_log] AS pl 
                        WHERE pl.app_id = ax.app_id
                    )""")
                
                where_clause = "WHERE " + " AND ".join(where_conditions)
                
                # Build final SQL query with TOP (faster than OFFSET for sequential access)
                top_clause = f"TOP ({limit})" if limit else ""
                # Use contract-driven source table and column for extraction
                query = f"""
                    SELECT {top_clause} ax.app_id, ax.[{source_column}]
                    FROM [dbo].[{source_table}] AS ax
                    {where_clause}
                    ORDER BY ax.app_id
                """
                
                # Log the actual SQL query for debugging
                self.logger.debug(f"Executing SQL query:\n{query}")
                
                # TIME THE QUERY EXECUTION
                query_start = time.time()
                cursor.execute(query)
                rows = cursor.fetchall()
                query_duration = time.time() - query_start
                
                seen_app_ids = set()
                for row in rows:
                    app_id = row[0]
                    xml_content = row[1]
                    
                    if xml_content and len(xml_content.strip()) > 0:
                        # Check for duplicate app_ids in the same batch
                        if app_id in seen_app_ids:
                            self.logger.warning(f"Duplicate app_id {app_id} found in app_xml table - skipping duplicate")
                            continue
                        seen_app_ids.add(app_id)
                        xml_records.append((app_id, xml_content))
                
                self.logger.info(f"Extracted {len(xml_records)} XML records (excluding already processed and failed)")
                
                # Log if we found any duplicates
                if len(seen_app_ids) < len(rows):
                    duplicates_found = len(rows) - len(seen_app_ids)
                    self.logger.warning(f"Found {duplicates_found} duplicate app_ids in app_xml table")
                
        except Exception as e:
            self.logger.error(f"Failed to extract XML records: {e}")
            raise
        
        return xml_records
    
    def process_batch(self, xml_records: List[Tuple[int, str]], batch_number: int = 1) -> dict:
        """
        Process a batch of XML applications with full monitoring.
        
        Success Rate Definition:
            success_rate = (applications_successful / applications_processed) * 100
            
            - applications_successful: XML applications completely processed with data inserted into database
            - applications_processed: Total XML applications attempted 
            - applications_failed: XML applications that failed at any stage (parsing, mapping, or insertion)
            
        Args:
            xml_records: List of (app_id, xml_content) tuples to process
            batch_number: Batch sequence number (for logging/tracking)
            
        Returns:
            Dictionary containing processing metrics including failed_apps list with failure details
        """
        if not xml_records:
            self.logger.warning("No XML records to process")
            return {}
        
        self.logger.info(f"Starting batch processing of {len(xml_records)} records")
        
        # Use injected batch processor, or create ParallelCoordinator for production
        if self.batch_processor is None:
            self.batch_processor = ParallelCoordinator(
                connection_string=self.connection_string,
                mapping_contract_path=self.mapping_contract_path,
                num_workers=self.workers,
                batch_size=self.batch_size,
                session_id=self.session_id,
                app_id_start=self.app_id_start,
                app_id_end=self.app_id_end
            )
        
        # Process batch
        start_time = time.time()
        processing_result = self.batch_processor.process_xml_batch(xml_records, batch_number=batch_number)
        end_time = time.time()
        
        # Extract failed app details from individual results
        # NOTE: processing_log entries are now created atomically with data insertion in workers
        # No need for separate logging here - log entries already exist in database
        individual_results = processing_result.performance_metrics.get('individual_results', [])
        failed_apps = []
        quality_issue_apps = []  # Apps that succeeded but had data quality warnings
        for result in individual_results:
            success = result.get('success', True)
            app_id = result.get('app_id')
            error_stage = result.get('error_stage', 'unknown')
            error_message = result.get('error_message', 'No error message available')
            quality_issues = result.get('quality_issues', [])
            
            # Special case: PK violations on app_base are NOT failures
            # They mean the data already exists in the database, which is the desired end state
            # Treat as success to prevent re-processing the same record
            if not success and error_stage == 'constraint_violation' and 'PK_app_base' in str(error_message):
                self.logger.info(f"App {app_id}: PK violation on app_base (data already exists) - treating as success")
                # No need to log - already logged atomically with data insertion
                success = True
            
            if not success:
                # Only track failures for reporting
                failure_reason = f"{error_stage}: {error_message}"
                failed_app = {
                    'app_id': app_id,
                    'error_stage': error_stage,
                    'error_message': error_message,
                    'processing_time': result.get('processing_time', 0)
                }
                failed_apps.append(failed_app)
            elif quality_issues:
                # Track successful apps with data quality warnings
                quality_issue_app = {
                    'app_id': app_id,
                    'quality_issues': quality_issues,
                    'processing_time': result.get('processing_time', 0)
                }
                quality_issue_apps.append(quality_issue_app)
        
        # Categorize failures by stage
        failure_summary = {
            'validation_failures': len([f for f in failed_apps if f['error_stage'] == 'validation']),
            'parsing_failures': len([f for f in failed_apps if f['error_stage'] == 'parsing']),
            'mapping_failures': len([f for f in failed_apps if f['error_stage'] == 'mapping']),
            'insertion_failures': len([f for f in failed_apps if f['error_stage'] == 'insertion']),
            'constraint_violations': len([f for f in failed_apps if f['error_stage'] == 'constraint_violation']),
            'database_errors': len([f for f in failed_apps if f['error_stage'] == 'database_error']),
            'system_errors': len([f for f in failed_apps if f['error_stage'] == 'system_error']),
            'unknown_failures': len([f for f in failed_apps if f['error_stage'] == 'unknown'])
        }
        
        # Calculate metrics
        metrics = {
            'session_id': self.session_id,
            'batch_start_time': datetime.fromtimestamp(start_time).isoformat(),
            'batch_end_time': datetime.fromtimestamp(end_time).isoformat(),
            'total_processing_time': end_time - start_time,
            'records_processed': processing_result.records_processed,
            'records_successful': processing_result.records_successful,
            'records_failed': processing_result.records_failed,
            'success_rate': processing_result.success_rate,
            'records_per_minute': processing_result.performance_metrics.get('records_per_minute', 0),
            'records_per_second': processing_result.performance_metrics.get('records_per_second', 0),
            'total_records_inserted': processing_result.performance_metrics.get('total_records_inserted', 0),
            'parallel_efficiency': processing_result.performance_metrics.get('parallel_efficiency', 0),
            'worker_count': self.workers,
            'server': self.server,
            'database': self.database,
            'failed_apps': failed_apps,
            'failure_summary': failure_summary,
            'quality_issue_apps': quality_issue_apps,
            'quality_issue_count': len(quality_issue_apps)
        }
        
        # Log summary
        self.logger.info("="*60)
        self.logger.info("BATCH PROCESSING COMPLETE")
        self.logger.info("="*60)
        self.logger.info(f"Applications Processed: {metrics['records_processed']}")
        self.logger.info(f"Success Rate: {metrics['success_rate']:.1f}%")
        self.logger.info(f"Throughput: {metrics['records_per_minute']:.1f} applications/minute")
        self.logger.info(f"Total Time: {metrics['total_processing_time']:.2f} seconds")
        self.logger.info(f"Database Records Inserted: {metrics['total_records_inserted']}")
        self.logger.info(f"Parallel Efficiency: {metrics['parallel_efficiency']*100:.1f}%")
        
        # Log failure details if any
        if metrics['records_failed'] > 0:
            self.logger.warning(f"Failed Applications: {metrics['records_failed']}")
            
            # Log failure breakdown
            failure_summary = metrics['failure_summary']
            if failure_summary.get('validation_failures', 0) > 0:
                self.logger.warning(f"  Validation Failures: {failure_summary['validation_failures']} (XML validation issues)")
            if failure_summary['parsing_failures'] > 0:
                self.logger.warning(f"  Parsing Failures: {failure_summary['parsing_failures']} (XML structure/format issues)")
            if failure_summary['mapping_failures'] > 0:
                self.logger.warning(f"  Mapping Failures: {failure_summary['mapping_failures']} (Data transformation issues)")
            if failure_summary['insertion_failures'] > 0:
                self.logger.warning(f"  Insertion Failures: {failure_summary['insertion_failures']} (General database insertion issues)")
            if failure_summary['constraint_violations'] > 0:
                self.logger.warning(f"  Constraint Violations: {failure_summary['constraint_violations']} (Primary key, foreign key, null constraints)")
            if failure_summary['database_errors'] > 0:
                self.logger.warning(f"  Database Errors: {failure_summary['database_errors']} (Connection, timeout, SQL errors)")
            if failure_summary['system_errors'] > 0:
                self.logger.warning(f"  System Errors: {failure_summary['system_errors']} (Unexpected system issues)")
            if failure_summary['unknown_failures'] > 0:
                self.logger.warning(f"  Unknown Failures: {failure_summary['unknown_failures']} (Unclassified errors)")
            
            # Log failed app_ids (keep it concise)
            failed_app_ids = [str(f['app_id']) for f in metrics['failed_apps'] if f.get('app_id') is not None]
            if len(failed_app_ids) <= 10:
                self.logger.warning(f"  Failed App IDs: {', '.join(failed_app_ids)}")
            else:
                self.logger.warning(f"  Failed App IDs: {', '.join(failed_app_ids[:10])} ... and {len(failed_app_ids)-10} more")
            
            # Log detailed errors at DEBUG level
            for failed_app in metrics['failed_apps']:
                self.logger.debug(f"  App {failed_app['app_id']}: {failed_app['error_stage']} - {failed_app['error_message']}")
        else:
            self.logger.info("All records processed successfully!")
        
        # Log quality issues if any (successful apps with data quality warnings)
        if metrics['quality_issue_count'] > 0:
            self.logger.warning(f"Data Quality Warnings: {metrics['quality_issue_count']} applications had non-fatal data quality issues")
            quality_app_ids = [str(app['app_id']) for app in metrics['quality_issue_apps']]
            if len(quality_app_ids) <= 10:
                self.logger.warning(f"  Apps with Quality Issues: {', '.join(quality_app_ids)}")
            else:
                self.logger.warning(f"  Apps with Quality Issues: {', '.join(quality_app_ids[:10])} ... and {len(quality_app_ids)-10} more")
            
            # Log detailed quality issues at INFO level
            for quality_app in metrics['quality_issue_apps']:
                for issue in quality_app['quality_issues']:
                    self.logger.info(f"  App {quality_app['app_id']}: {issue}")
        
        return metrics
    
    def _save_metrics(self, metrics: dict):
        """
        Save consolidated performance metrics to JSON file.
        
        Includes:
        - Connection/processing configuration
        - Overall run statistics
        - Failure analysis
        - Per-batch detailed breakdown
        """
        metrics_dir = Path("metrics")
        metrics_dir.mkdir(exist_ok=True)
        
        # Add app_id range suffix for range-based processing
        range_suffix = f"_range_{self.app_id_start}_{self.app_id_end}" if self.app_id_start is not None and self.app_id_end is not None else ""
        metrics_file = metrics_dir / f"metrics_{self.session_id}{range_suffix}.json"
        
        try:
            # Build consolidated metrics structure
            consolidated_metrics = {
                'run_timestamp': datetime.now().isoformat(),
                'app_id_start': self.app_id_start,
                'app_id_end': self.app_id_end,
                'server': self.server,
                'database': self.database,
                'target_schema': self.target_schema,
                'pooling': self.enable_pooling,
                'workers': self.workers,
                'batch_size': self.batch_size,
                'limit': metrics.get('limit'),
                'total_applications_processed': metrics.get('total_processed', 0),
                'total_applications_successful': metrics.get('total_successful', 0),
                'total_applications_failed': metrics.get('total_failed', 0),
                'success_rate': metrics.get('overall_success_rate', 0),
                'total_duration_seconds': metrics.get('overall_time_minutes', 0) * 60,
                'applications_per_minute': metrics.get('overall_rate_per_minute', 0),
                'total_database_inserts': metrics.get('total_database_inserts', 0),
                'parallel_efficiency': metrics.get('parallel_efficiency', 0),
                'failure_summary': metrics.get('failure_summary', {}),
                'failed_apps': metrics.get('failed_apps', []),
                'quality_issue_apps': metrics.get('quality_issue_apps', []),
                'quality_issue_count': metrics.get('quality_issue_count', 0),
                'batch_details': metrics.get('batch_details', [])
            }
            
            # JSON serializer helper to handle Decimal and datetime objects gracefully
            from decimal import Decimal
            def _json_default(o):
                if isinstance(o, Decimal):
                    return float(o)
                # datetime -> ISO string
                try:
                    import datetime as _dt
                    if isinstance(o, _dt.datetime):
                        return o.isoformat()
                except Exception:
                    pass
                return str(o)

            with open(metrics_file, 'w') as f:
                json.dump(consolidated_metrics, f, indent=2, default=_json_default)
            self.logger.info(f"Metrics saved to: {metrics_file}")
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")
    
    def run_full_processing(self, limit: Optional[int] = None):
        """
        Run full processing with batching and monitoring.
        
        Args:
            limit: Maximum total number of applications to process before stopping (safety cap).
                  NOT the same as batch_size - this limits total applications across all batches.
                  Applications are fetched in batches of self.batch_size until limit is reached.
                  Example: limit=10000, batch_size=500 → process up to 10,000 applications, fetching 500 App XMLs at a time.
        """
        self.logger.info("Starting full processing run")
        
        # Display processing scope in console
        print("\n" + "=" * 82)
        if self.app_id_start is not None and self.app_id_end is not None:
           print(f" PROCESSING [app_id] RANGE: {self.app_id_start} - {self.app_id_end}")
        elif limit:
            print(f" PROCESSING UP TO {limit:,} APPLICATIONS")
        else:
            print(f" PROCESSING ALL APPLICATIONS (NO LIMIT)")
        print("=" * 82)
        
        # Test connection first
        if not self.test_connection():
            raise RuntimeError("Database connection test failed")
        
        # Get total record count for progress tracking (use contract-driven source table/column)
        try:
            config_manager = get_config_manager()
            mapping_contract = config_manager.load_mapping_contract()
            source_table = mapping_contract.source_table
            source_column = mapping_contract.source_column

            migration_engine = MigrationEngine(self.connection_string)
            with migration_engine.get_connection() as conn:
                cursor = conn.cursor()
                # Source table always in [dbo] schema (read-only access)
                cursor.execute(f"SELECT COUNT(*) FROM [dbo].[{source_table}] WHERE [{source_column}] IS NOT NULL")
                total_records = cursor.fetchone()[0]
                
                if limit:
                    total_records = min(total_records, limit)
                
                self.logger.info(f"Total records to process: {total_records}")
        except Exception as e:
            self.logger.error(f"Failed to get record count: {e}")
            total_records = 0
        
        # Process in batches
        last_app_id = 0  # Cursor-based pagination: track last app_id processed
        total_processed = 0
        total_successful = 0
        total_failed = 0
        all_failed_apps = []
        all_quality_issue_apps = []  # Collect quality warnings across batches
        batch_details = []  # Collect per-batch metrics
        overall_failure_summary = {
            'validation_failures': 0,
            'parsing_failures': 0,
            'mapping_failures': 0,
            'insertion_failures': 0,
            'constraint_violations': 0,
            'database_errors': 0,
            'system_errors': 0,
            'unknown_failures': 0
        }
        overall_start = time.time()
        
        while True:
            # Calculate remaining records to fetch based on total limit
            remaining_limit = None
            if limit:
                remaining_limit = limit - total_processed
                if remaining_limit <= 0:
                    break
            
            # Get next batch using cursor-based pagination (app_id > last_app_id)
            # Fetch min(batch_size, remaining_limit) records
            fetch_limit = self.batch_size
            if remaining_limit:
                fetch_limit = min(self.batch_size, remaining_limit)
            
            batch_records = self.get_xml_records(limit=fetch_limit, last_app_id=last_app_id)
            
            if not batch_records:
                break
            
            # Process batch
            batch_number = len(batch_details) + 1
            app_ids = [rec[0] for rec in batch_records]
            self.logger.info(f"Processing batch {batch_number}: app_ids {min(app_ids)}-{max(app_ids)}" if app_ids else f"Processing batch {batch_number}: empty batch")
            batch_start_time = time.time()
            metrics = self.process_batch(batch_records, batch_number=batch_number)
            batch_duration = time.time() - batch_start_time
            
            # Collect batch metrics for later reporting
            batch_detail = {
                'batch_number': batch_number,
                'total_applications_processed': metrics.get('records_processed', 0),
                'duration_seconds': float(batch_duration),
                'applications_per_minute': float((metrics.get('records_processed', 0) / batch_duration * 60) if batch_duration > 0 else 0),
                'database_inserts': metrics.get('total_records_inserted', 0),
                'application_failures': metrics.get('records_failed', 0)
            }
            batch_details.append(batch_detail)
            
            # Update totals
            total_processed += metrics.get('records_processed', 0)
            total_successful += metrics.get('records_successful', 0)
            total_failed += metrics.get('records_failed', 0)
            
            # Accumulate failed apps and failure summary
            all_failed_apps.extend(metrics.get('failed_apps', []))
            batch_failure_summary = metrics.get('failure_summary', {})
            for key in overall_failure_summary:
                overall_failure_summary[key] += batch_failure_summary.get(key, 0)
            
            # Accumulate quality issue apps
            all_quality_issue_apps.extend(metrics.get('quality_issue_apps', []))
            
            # Update cursor to last app_id in batch for next iteration
            if batch_records:
                last_app_id = max(rec[0] for rec in batch_records)
            
            # Check if we've reached the limit
            if limit and total_processed >= limit:
                break
        
        # Final summary
        overall_time = time.time() - overall_start
        overall_rate = total_processed / (overall_time / 60) if overall_time > 0 else 0
        overall_success_rate = (total_successful/total_processed*100) if total_processed > 0 else 0
        
        self.logger.info("="*82)
        self.logger.info(" FULL PROCESSING COMPLETE")
        self.logger.info("="*82)
        self.logger.info(f"  Total Applications Processed: {total_processed}")
        self.logger.info(f"  Total Successful: {total_successful}")
        self.logger.info(f"  Total Failed: {total_failed}")
        self.logger.info(f"  Overall Success Rate: {overall_success_rate:.1f}%")
        self.logger.info(f"  Overall Time: {overall_time/60:.1f} minutes")
        self.logger.info(f"  Overall Rate: {overall_rate:.1f} applications/minute")
        self.logger.info(f"  Total Database Records Inserted: {sum(b.get('database_inserts', 0) for b in batch_details)}")
        
        # Log overall failure summary if there were failures
        if total_failed > 0:
            self.logger.warning("="*82)
            self.logger.warning(" FAILURE ANALYSIS")
            self.logger.warning("="*82)

            if overall_failure_summary.get('validation_failures', 0) > 0:
                self.logger.warning(f" Validation Failures: {overall_failure_summary['validation_failures']} (XML validation issues)")
            if overall_failure_summary['parsing_failures'] > 0:
                self.logger.warning(f" Parsing Failures: {overall_failure_summary['parsing_failures']} (XML structure/format issues)")
            if overall_failure_summary['mapping_failures'] > 0:
                self.logger.warning(f" Mapping Failures: {overall_failure_summary['mapping_failures']} (Data transformation issues)")
            if overall_failure_summary['insertion_failures'] > 0:
                self.logger.warning(f" Insertion Failures: {overall_failure_summary['insertion_failures']} (General database insertion issues)")
            if overall_failure_summary['constraint_violations'] > 0:
                self.logger.warning(f" Constraint Violations: {overall_failure_summary['constraint_violations']} (Primary key, foreign key, null constraints)")
            if overall_failure_summary['database_errors'] > 0:
                self.logger.warning(f" Database Errors: {overall_failure_summary['database_errors']} (Connection, timeout, SQL errors)")
            if overall_failure_summary['system_errors'] > 0:
                self.logger.warning(f" System Errors: {overall_failure_summary['system_errors']} (Unexpected system issues)")
            if overall_failure_summary['unknown_failures'] > 0:
                self.logger.warning(f" Unknown Failures: {overall_failure_summary['unknown_failures']} (Unclassified errors)")

            # Log sample of failed app_ids for investigation
            failed_app_ids = [str(f['app_id']) for f in all_failed_apps if f.get('app_id') is not None]
            unique_failed_ids = list(dict.fromkeys(failed_app_ids))  # Remove duplicates while preserving order
            
            if len(unique_failed_ids) <= 20:
                self.logger.warning(f" Failed App IDs: {', '.join(unique_failed_ids)}")
            else:
                self.logger.warning(f" Failed App IDs (first 20): {', '.join(unique_failed_ids[:20])}")
                self.logger.warning(f" Total unique failed apps: {len(unique_failed_ids)}")
        
        final_metrics = {
            'app_id_start': self.app_id_start,
            'app_id_end': self.app_id_end,
            'total_processed': total_processed,
            'total_successful': total_successful,
            'total_failed': total_failed,
            'overall_success_rate': overall_success_rate,
            'overall_time_minutes': overall_time / 60,
            'overall_rate_per_minute': overall_rate,
            'failed_apps': all_failed_apps,
            'failure_summary': overall_failure_summary,
            'quality_issue_apps': all_quality_issue_apps,
            'quality_issue_count': len(all_quality_issue_apps),
            'batch_details': batch_details,
            'limit': limit,
            'total_database_inserts': sum(b.get('database_inserts', 0) for b in batch_details),
            'parallel_efficiency': statistics.mean([b.get('applications_per_minute', 0) / overall_rate for b in batch_details]) if batch_details and overall_rate > 0 else 0
        }
        
        # Save consolidated metrics file once at end of run
        self._save_metrics(final_metrics)
        
        return final_metrics


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description="Production XML Processing")
    
    # Required arguments
    parser.add_argument("--server", required=True, help="SQL Server instance (e.g., 'localhost\\SQLEXPRESS')")
    parser.add_argument("--database", required=True, help="Database name")
    
    # Optional arguments
    parser.add_argument("--username", help="SQL Server username (uses Windows auth if not provided)")
    parser.add_argument("--password", help="SQL Server password")
    parser.add_argument("--workers", type=int, default=ProcessingDefaults.WORKERS, 
                       help=f"Number of parallel workers (default: {ProcessingDefaults.WORKERS})")
    parser.add_argument("--batch-size", type=int, default=ProcessingDefaults.BATCH_SIZE, 
                       help=f"Application XMLs to fetch per SQL query (pagination size, default: {ProcessingDefaults.BATCH_SIZE})")
    parser.add_argument("--limit", type=int, 
                       help=f"Total applications to process before stopping (safety cap). In RANGE mode (--app-id-start/--app-id-end), this parameter is ignored. Default when not in range mode: {ProcessingDefaults.LIMIT}")
    parser.add_argument("--log-level", default=ProcessingDefaults.LOG_LEVEL, 
                       choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
                       help=f"Logging level (default: {ProcessingDefaults.LOG_LEVEL})")
    
    # App ID range processing (eliminates lock contention between instances)
    parser.add_argument("--app-id-start", type=int, 
                       help="Starting app_id for processing range (inclusive)")
    parser.add_argument("--app-id-end", type=int,
                       help="Ending app_id for processing range (inclusive)")
    
    # Connection pooling optimization arguments
    parser.add_argument("--enable-pooling", action="store_true", default=ProcessingDefaults.ENABLE_POOLING,
                       help=f"Enable connection pooling (default: {ProcessingDefaults.ENABLE_POOLING})")
    parser.add_argument("--min-pool-size", type=int, default=ProcessingDefaults.CONNECTION_POOL_MIN, 
                       help=f"Minimum connection pool size (default: {ProcessingDefaults.CONNECTION_POOL_MIN})")
    parser.add_argument("--max-pool-size", type=int, default=ProcessingDefaults.CONNECTION_POOL_MAX, 
                       help=f"Maximum connection pool size (default: {ProcessingDefaults.CONNECTION_POOL_MAX})")
    parser.add_argument("--disable-mars", action="store_true", default=not ProcessingDefaults.MARS_ENABLED,
                       help=f"Disable Multiple Active Result Sets (default: MARS {'enabled' if ProcessingDefaults.MARS_ENABLED else 'disabled'})")
    parser.add_argument("--connection-timeout", type=int, default=ProcessingDefaults.CONNECTION_TIMEOUT,
                       help=f"Connection timeout in seconds (default: {ProcessingDefaults.CONNECTION_TIMEOUT})")
    
    args = parser.parse_args()
    
    # Handle limit defaults and range mode interaction
    # ================================================
    # When in RANGE mode (--app-id-start/--app-id-end), ignore --limit entirely
    # When NOT in range mode and no --limit provided, apply safety default
    in_range_mode = args.app_id_start is not None and args.app_id_end is not None
    
    if in_range_mode:
        # Range mode: process entire range, ignore limit
        processing_limit = None
        if args.limit is not None:
            print(f" WARNING: --limit={args.limit} ignored in RANGE mode (--app-id-start/--app-id-end specified)")
    else:
        # Not in range mode: apply limit or default
        if args.limit is None:
            processing_limit = ProcessingDefaults.LIMIT
            print(f" INFO: No --limit specified, applying safety default: {ProcessingDefaults.LIMIT}")
        else:
            processing_limit = args.limit
    
    try:
        # Create processor with connection pooling optimizations
        processor = ProductionProcessor(
            server=args.server,
            database=args.database,
            username=args.username,
            password=args.password,
            workers=args.workers,
            batch_size=args.batch_size,
            log_level=args.log_level,
            enable_pooling=args.enable_pooling,
            min_pool_size=args.min_pool_size,
            max_pool_size=args.max_pool_size,
            enable_mars=not args.disable_mars,  # Invert: MARS enabled by default
            connection_timeout=args.connection_timeout,
            app_id_start=args.app_id_start,
            app_id_end=args.app_id_end
        )
        
        # Run processing with calculated limit
        results = processor.run_full_processing(limit=processing_limit)
        
        print("\n" + "="*82)
        print(" PRODUCTION PROCESSING COMPLETED SUCCESSFULLY")
        print("="*82)
        print(f" Check logs/ and metrics/ directories for detailed results")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n Processing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)