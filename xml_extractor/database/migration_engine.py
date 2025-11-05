"""
Migration Engine - High-Performance Bulk Insert with Atomic Transactions

Final stage of XML extraction pipeline. Receives contract-compliant relational data
from DataMapper and performs optimized bulk insertion with single-connection atomicity.

KEY FEATURES:
- Atomic transactions: Single connection per application (zero orphaned records)
- Performance: fast_executemany with intelligent fallback to individual inserts
- Schema isolation: Target schema from MappingContract (sandbox/dbo)
- FK ordering: Respects table_insertion_order for constraint safety
- Error recovery: Automatic rollback on failure, proper IDENTITY_INSERT cleanup

For architecture details, see ARCHITECTURE.md (schema isolation, atomicity, FK ordering)
"""

import logging
import time
from typing import List, Dict, Any, Optional
import pyodbc
from contextlib import contextmanager

from ..interfaces import MigrationEngineInterface
from ..exceptions import (
    DatabaseConnectionError, 
    SchemaValidationError, 
    XMLExtractionError,
    TransactionAtomicityError,
    DatabaseConstraintError
)
from ..config.config_manager import get_config_manager
from .duplicate_contact_detector import DuplicateContactDetector
from .bulk_insert_strategy import BulkInsertStrategy


class MigrationEngine(MigrationEngineInterface):
    """
    High-Performance Database Migration Engine for Contract-Driven Data Pipeline.

    The MigrationEngine serves as the final execution stage of the XML Database Extraction System,
    receiving pre-processed relational data from the DataMapper and performing optimized bulk
    insert operations into SQL Server. This engine embodies the "contract-first" architecture
    where data compatibility is guaranteed by upstream components.

    SCHEMA ISOLATION & TARGET_SCHEMA:
        All database operations use the target_schema from MappingContract:
        - Inserts: INSERT INTO [{target_schema}].[table_name] (...)
        - Queries: SELECT FROM [{target_schema}].[table_name] WHERE ...
        - Deletes: DELETE FROM [{target_schema}].[table_name]
        - Exception: Source table (app_xml) always queries from [dbo].[app_xml]
        
        This contract-driven approach allows:
        - Sandbox schema for testing/staging
        - Production schema for live data
        - Complete isolation between environments
        - No environment variable pollution

    Pipeline Position:
    1. Receives contract-compliant record sets from DataMapper.apply_mapping_contract()
    2. Extracts target_schema from MappingContract (e.g., "sandbox" or "dbo")
    3. Performs bulk insertion with SQL Server optimizations using schema-qualified names
    4. Reports progress and metrics to CLI/batch processors
    5. Ensures transaction safety and error recovery

    Key Architectural Principles:
    - Contract-Driven: Schema, columns, and validation all from MappingContract
    - Performance-Focused: Optimized for high-throughput bulk operations
    - Schema-Isolated: Each contract controls its target schema independently
    - Transaction-Safe: Comprehensive error handling with automatic rollback
    - Progress-Aware: Real-time metrics for monitoring and batch processing

    Recent Refactoring Changes:
    - Simplified column handling: DataMapper provides exact column sets per contract rules
    - Removed dynamic filtering: Contract-driven approach eliminates need for runtime column validation
    - Enhanced bulk insertion: Intelligent fast_executemany with automatic fallback strategies
    - Schema Isolation Implementation: All operations now use target_schema from contract
    - Streamlined schema validation: Focus on table existence (columns pre-validated upstream)

    Performance Optimizations:
    - Batch processing with configurable batch sizes (default: 1000 records)
    - Fast executemany for homogeneous data (significant performance boost)
    - Automatic fallback to individual executes for heterogeneous data
    - Connection reuse and prepared statement caching
    - Memory-efficient processing of large datasets

    Integration Points:
    - DataMapper: Receives processed tables with contract-compliant column sets
    - MappingContract: Source of truth for target_schema and data mappings
    - CLI Tools: Provides progress tracking and error reporting
    - Batch Processors: Supports high-volume production processing
    - Configuration System: Uses centralized database and processing configuration

    Error Recovery Strategies:
    - Type conversion errors trigger fallback to individual executes
    - Constraint violations logged with detailed context and record identification
    - Connection issues trigger automatic retry with exponential backoff
    - Transaction rollback ensures database consistency on failures
    - Comprehensive error categorization for downstream processing decisions
    """
    
    def __init__(self, connection_string: Optional[str] = None, log_level: str = "ERROR"):
        """
        Initialize the migration engine with injected dependencies.
        
        Args:
            connection_string: Optional SQL Server connection string. If None, uses centralized config.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                      Defaults to ERROR for production use to minimize overhead.
        """
        self.logger = logging.getLogger(__name__)
        # Attach root logger handlers for consistent logging across processes
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            self.logger.addHandler(handler)
        
        # PRODUCTION FIX: Set log level explicitly (default to ERROR for production)
        log_level_value = getattr(logging, log_level.upper(), logging.ERROR)
        self.logger.setLevel(log_level_value)
        
        # Get centralized configuration
        self.config_manager = get_config_manager()
        processing_config = self.config_manager.get_processing_config()
        
        # Use provided values or fall back to centralized configuration
        self.connection_string = connection_string or self.config_manager.get_database_connection_string()
        # Batch size is informational only; determined by fast_executemany performance
        self.batch_size = processing_config.batch_size
        
        # Load target_schema from MappingContract (contract-driven schema isolation)
        self.target_schema = self._load_target_schema_from_contract()
        
        self._connection = None
        self._transaction_active = False
        
        # Inject extracted dependencies (Strategy pattern & Dependency Injection)
        self.duplicate_detector = DuplicateContactDetector(self.get_connection, self.logger)
        self.insert_strategy = BulkInsertStrategy(self.batch_size, self.logger)
        
        # Progress tracking
        self._total_records = 0
        self._processed_records = 0
        self._start_time = None
        
        self.logger.info(f"MigrationEngine initialized with batch_size={self.batch_size}")
        self.logger.debug(f"Using database server: {self.config_manager.database_config.server}")
        self.logger.info(f"Contract-driven target_schema: {self.target_schema}")
    
    def _load_target_schema_from_contract(self) -> str:
        """
        Load target schema from MappingContract.
        
        Contract-Driven Architecture:
        - Reads target_schema from mapping_contract.json via ConfigManager
        - Falls back to 'dbo' if contract cannot be loaded
        - Enables schema isolation for different processing environments
        
        Returns:
            Target schema name (e.g., "sandbox", "dbo")
        """
        try:
            mapping_contract = self.config_manager.load_mapping_contract()
            target_schema = mapping_contract.target_schema if mapping_contract else None
            return target_schema or 'dbo'
        except Exception as e:
            self.logger.warning(f"Failed to load target_schema from contract, defaulting to 'dbo': {e}")
            return 'dbo'
    
    def _get_qualified_table_name(self, table_name: str) -> str:
        """
        Get schema-qualified table name for contract-driven SQL operations.
        
        Contract-Driven Schema Isolation:
        - All target table names are qualified with target_schema from MappingContract
        - Format: [target_schema].[table_name]
        - Example: [sandbox].[app_base] or [dbo].[contact_base]
        - Source table (app_xml) always remains in [dbo].[app_xml]
        
        Args:
            table_name: Unqualified table name (e.g., "app_base")
            
        Returns:
            Schema-qualified table name (e.g., "[sandbox].[app_base]")
        """
        # Source table always stays in dbo regardless of target_schema
        if table_name == 'app_xml':
            return '[dbo].[app_xml]'
        
        return f'[{self.target_schema}].[{table_name}]'
        
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections with automatic cleanup.
        
        Yields:
            pyodbc.Connection: Active database connection
            
        Raises:
            DatabaseConnectionError: If connection cannot be established
        """
        connection = None
        try:
            connection = pyodbc.connect(
                self.connection_string,
                autocommit=False,  # Explicit transaction control for atomic operations
                timeout=30
            )
            # Enable fast_executemany for bulk operations
            connection.setdecoding(pyodbc.SQL_CHAR, encoding='utf-8')
            connection.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-8')
            connection.setencoding(encoding='utf-8')
            
            yield connection
            
        except pyodbc.Error as e:
            error_str = str(e).lower()
            # Only re-raise as DatabaseConnectionError if it's actually a connection issue
            if any(conn_error in error_str for conn_error in [
                'connection', 'login', 'server', 'network', 'timeout', 'cannot open database'
            ]) and not any(data_error in error_str for data_error in [
                'primary key', 'foreign key', 'check constraint', 'duplicate key', 
                'cast specification', 'converting', 'null constraint'
            ]):
                self.logger.error(f"Database connection failed: {e}")
                raise DatabaseConnectionError(f"Failed to connect to database: {e}")
            else:
                # Let data/constraint errors bubble up to be handled by bulk insert error handling
                raise
        finally:
            if connection:
                try:
                    connection.close()
                except pyodbc.Error:
                    pass  # Ignore errors during cleanup
    
    @contextmanager
    def transaction(self, connection: pyodbc.Connection):
        """
        Context manager for explicit transaction management.
        
        Args:
            connection: Active database connection
            
        Yields:
            pyodbc.Connection: Connection within transaction context
            
        Raises:
            TransactionAtomicityError: If transaction cannot be rolled back on failure
            XMLExtractionError: If transaction fails (other errors)
        """
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute("BEGIN TRANSACTION")
            self._transaction_active = True
            self.logger.debug("Transaction started")
            
            yield connection
            
            cursor.execute("COMMIT TRANSACTION")
            self._transaction_active = False
            self.logger.debug("Transaction committed")
            
        except pyodbc.Error as e:
            # Database-specific error during transaction
            if cursor and self._transaction_active:
                try:
                    cursor.execute("ROLLBACK TRANSACTION")
                    self._transaction_active = False
                    self.logger.error(f"Transaction rolled back due to database error: {str(e)[:200]}")
                except pyodbc.Error as rollback_error:
                    # Critical failure: cannot rollback
                    self.logger.critical(f"ROLLBACK FAILED - Database may be in inconsistent state: {rollback_error}")
                    raise TransactionAtomicityError(
                        f"Failed to rollback transaction after error: {rollback_error}",
                        error_category="transaction_atomicity"
                    )
            raise XMLExtractionError(f"Database error during transaction: {e}", error_category="database_error")
        except XMLExtractionError:
            # Already an extraction error, re-raise
            if cursor and self._transaction_active:
                try:
                    cursor.execute("ROLLBACK TRANSACTION")
                    self._transaction_active = False
                except pyodbc.Error as rollback_error:
                    self.logger.critical(f"ROLLBACK FAILED: {rollback_error}")
            raise
        except Exception as e:
            # Unexpected error during transaction
            if cursor and self._transaction_active:
                try:
                    cursor.execute("ROLLBACK TRANSACTION")
                    self._transaction_active = False
                    self.logger.error(f"Transaction rolled back due to error: {str(e)[:200]}")
                except pyodbc.Error as rollback_error:
                    self.logger.critical(f"ROLLBACK FAILED - Database may be in inconsistent state: {rollback_error}")
                    raise TransactionAtomicityError(
                        f"Failed to rollback transaction: {rollback_error}",
                        error_category="transaction_atomicity"
                    )
            raise XMLExtractionError(f"Unexpected error during transaction: {e}", error_category="system_error")
        finally:
            if cursor:
                cursor.close()
    
    def execute_bulk_insert(self, records: List[Dict[str, Any]], table_name: str, enable_identity_insert: bool = False, connection=None) -> int:
        """
        Execute optimized bulk insert operation for contract-compliant relational data.

        Orchestrates bulk insertion by delegating to injected dependencies:
        1. DuplicateContactDetector: Filters records that would violate constraints
        2. BulkInsertStrategy: Executes insert with fast/fallback strategy
        
        This thin orchestration method maintains transaction context and error handling
        while delegating all specific logic to extracted classes.

        Args:
            records: List of contract-compliant record dictionaries from DataMapper
            table_name: Target table name (schema-qualified automatically)
            enable_identity_insert: Whether to enable IDENTITY_INSERT for auto-increment columns
            connection: Optional existing connection (if provided, caller manages transaction)

        Returns:
            Number of records successfully inserted

        Raises:
            XMLExtractionError: If bulk insert operation fails catastrophically
        """
        # Get schema-qualified table name
        qualified_table_name = self._get_qualified_table_name(table_name)
        
        # Step 1: Filter duplicate records using injected detector
        records = self.duplicate_detector.filter_duplicates(records, table_name, qualified_table_name)
        if not records:
            self.logger.warning(f"No records remain for bulk insert into {table_name} after filtering.")
            return 0
        
        # Step 2: Use provided connection or create new one
        if connection is not None:
            # Caller is managing the transaction - just do the insert
            cursor = connection.cursor()
            return self.insert_strategy.insert(
                cursor, records, table_name, qualified_table_name, enable_identity_insert
            )
        else:
            # We manage the connection and transaction
            with self.get_connection() as conn:
                cursor = conn.cursor()
                result = self.insert_strategy.insert(
                    cursor, records, table_name, qualified_table_name, enable_identity_insert
                )
                conn.commit()  # Commit after successful insert
                return result
    
    def track_progress(self, processed_count: int, total_count: int) -> None:
        """
        Track and report processing progress with performance metrics.
        
        Args:
            processed_count: Number of records processed so far
            total_count: Total number of records to process
        """
        self._processed_records = processed_count
        self._total_records = total_count
        
        if self._start_time is None:
            self._start_time = time.time()
        
        # Calculate progress metrics
        progress_percent = (processed_count / total_count * 100) if total_count > 0 else 0
        elapsed_time = time.time() - self._start_time
        
        # Calculate processing rate
        records_per_second = processed_count / elapsed_time if elapsed_time > 0 else 0
        records_per_minute = records_per_second * 60
        
        # Estimate remaining time
        remaining_records = total_count - processed_count
        estimated_remaining_seconds = (remaining_records / records_per_second) if records_per_second > 0 else 0
        
        # Log progress at appropriate intervals
        if processed_count % 10000 == 0 or processed_count == total_count:
            self.logger.info(
                f"Progress: {processed_count:,}/{total_count:,} ({progress_percent:.1f}%) - "
                f"Rate: {records_per_minute:.0f} records/min - "
                f"ETA: {estimated_remaining_seconds/60:.1f} minutes"
            )
        
        # Log detailed metrics for debugging
        self.logger.debug(
            f"Processing metrics - Elapsed: {elapsed_time:.1f}s, "
            f"Rate: {records_per_second:.1f} rec/sec, "
            f"Remaining: {remaining_records:,} records"
        )

    def get_processing_metrics(self) -> Dict[str, Any]:
        """
        Get current processing metrics.
        
        Returns:
            Dictionary containing processing metrics
        """
        if self._start_time is None:
            return {}
        
        elapsed_time = time.time() - self._start_time
        records_per_second = self._processed_records / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'total_records': self._total_records,
            'processed_records': self._processed_records,
            'elapsed_time_seconds': elapsed_time,
            'records_per_second': records_per_second,
            'records_per_minute': records_per_second * 60,
            'progress_percent': (self._processed_records / self._total_records * 100) if self._total_records > 0 else 0
        }
    
    def reset_progress_tracking(self) -> None:
        """Reset progress tracking counters."""
        self._total_records = 0
        self._processed_records = 0
        self._start_time = None
        self.logger.debug("Progress tracking reset")
