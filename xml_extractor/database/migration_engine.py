"""
Migration Engine for SQL Server database operations.

This module provides high-performance database migration capabilities using
pyodbc with SQL Server optimizations for bulk operations and transaction management.
"""

import logging
import time
from typing import List, Dict, Any, Optional
import pyodbc
from contextlib import contextmanager

from ..interfaces import MigrationEngineInterface
from ..exceptions import DatabaseConnectionError, SchemaValidationError, XMLExtractionError
from ..config.config_manager import get_config_manager


class MigrationEngine(MigrationEngineInterface):
    """
    High-performance migration engine for SQL Server database operations.
    
    Provides bulk insert capabilities, schema management, and progress tracking
    optimized for SQL Server Express LocalDB and production SQL Server instances.
    """
    
    def __init__(self, connection_string: Optional[str] = None, batch_size: Optional[int] = None):
        """
        Initialize the migration engine.
        
        Args:
            connection_string: Optional SQL Server connection string. If None, uses centralized config.
            batch_size: Optional batch size for bulk operations. If None, uses centralized config.
        """
        self.logger = logging.getLogger(__name__)
        
        # Get centralized configuration
        self.config_manager = get_config_manager()
        processing_config = self.config_manager.get_processing_config()
        
        # Use provided values or fall back to centralized configuration
        self.connection_string = connection_string or self.config_manager.get_database_connection_string()
        self.batch_size = batch_size or processing_config.batch_size
        
        self._connection = None
        self._transaction_active = False
        
        # Progress tracking
        self._total_records = 0
        self._processed_records = 0
        self._start_time = None
        
        self.logger.info(f"MigrationEngine initialized with batch_size={self.batch_size}")
        self.logger.debug(f"Using database server: {self.config_manager.database_config.server}")
        if self.config_manager.database_config.schema_prefix:
            self.logger.info(f"Using schema prefix: {self.config_manager.database_config.schema_prefix}")
        
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
                autocommit=True,  # Use autocommit for simpler transaction handling
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
            
        except Exception as e:
            if cursor and self._transaction_active:
                try:
                    cursor.execute("ROLLBACK TRANSACTION")
                    self._transaction_active = False
                    self.logger.debug("Transaction rolled back")
                except pyodbc.Error:
                    pass  # Ignore rollback errors
            raise e
        finally:
            if cursor:
                cursor.close()
    
    def execute_bulk_insert(self, records: List[Dict[str, Any]], table_name: str, enable_identity_insert: bool = False) -> int:
        """
        Execute bulk insert operation using pyodbc fast_executemany.
        
        Args:
            records: List of record dictionaries to insert
            table_name: Target table name
            
        Returns:
            Number of records successfully inserted
            
        Raises:
            XMLExtractionError: If bulk insert operation fails
        """
        if not records:
            self.logger.warning(f"No records provided for bulk insert into {table_name}")
            return 0
        
        inserted_count = 0
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get qualified table name with schema prefix
                qualified_table_name = self.config_manager.get_qualified_table_name(table_name)
                
                # Enable IDENTITY_INSERT if needed
                if enable_identity_insert:
                    cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} ON")
                    self.logger.debug(f"Enabled IDENTITY_INSERT for {qualified_table_name}")
                
                # Enable fast_executemany for optimal performance
                cursor.fast_executemany = True
                    
                # Get all columns from the first record to maintain consistent column order
                all_columns = list(records[0].keys())
                
                # Filter out columns that are None in ALL records
                # Allow empty strings as they represent valid data that should be converted to NULL
                columns_with_data = []
                for col in all_columns:
                    has_data = any(
                        record.get(col) is not None
                        for record in records
                    )
                    if has_data:
                        columns_with_data.append(col)
                
                columns = columns_with_data
                column_list = ', '.join(f"[{col}]" for col in columns)
                placeholders = ', '.join('?' * len(columns))
                
                # Build INSERT statement with qualified table name
                sql = f"INSERT INTO {qualified_table_name} ({column_list}) VALUES ({placeholders})"
                
                # Debug logging
                self.logger.warning(f"SQL: {sql}")
                self.logger.warning(f"Columns with data: {columns}")
                self.logger.debug(f"Excluded empty columns: {set(all_columns) - set(columns)}")
                
                # Prepare data tuples in correct order, only including columns with data
                data_tuples = []
                for record in records:
                    # Only include values for columns that have data
                    # Convert empty strings to None for proper NULL handling
                    values = []
                    for col in columns:
                        val = record.get(col)
                        if val == '':
                            val = None
                        elif isinstance(val, str):
                            # Ensure string values are properly encoded as Unicode
                            try:
                                val = val.encode('utf-8').decode('utf-8')
                            except (UnicodeEncodeError, UnicodeDecodeError):
                                # If encoding fails, keep original value
                                pass
                        values.append(val)
                    data_tuples.append(tuple(values))
                    
                    # Debug ALL records for contact_base
                    if table_name == 'contact_base':
                        self.logger.warning(f"Record {len(data_tuples)}: {values}")
                        for i, (col, val) in enumerate(zip(columns, values)):
                            self.logger.warning(f"  {i}: {col} = {repr(val)} ({type(val).__name__})")
                    
                    # Debug app_operational_cc records for calculated fields
                    if table_name == 'app_operational_cc':
                        self.logger.warning(f"DEBUG: app_operational_cc Record {len(data_tuples)}: {values}")
                        for i, (col, val) in enumerate(zip(columns, values)):
                            self.logger.warning(f"DEBUG: app_operational_cc {i}: {col} = {repr(val)} ({type(val).__name__})")
                            if col in ['cb_score_factor_code_1', 'cb_score_factor_code_2']:
                                self.logger.warning(f"DEBUG: CALCULATED FIELD {col} = '{val}' (expected: cb_score_factor_code_1='AJ', cb_score_factor_code_2='')")
                
                # Try executemany first for performance, fall back to individual executes if needed
                batch_start = 0
                use_executemany = True
                
                while batch_start < len(data_tuples):
                    batch_end = min(batch_start + self.batch_size, len(data_tuples))
                    batch_data = data_tuples[batch_start:batch_end]
                    
                    self.logger.debug(f"Inserting batch {batch_start}-{batch_end} into {table_name}")
                    

                    
                    try:
                        # Force individual executes for tables with known pyodbc executemany encoding issues
                        # These specific tables have string encoding problems when using executemany with pyodbc
                        # that cause character corruption (strings become question marks in SQL Server)
                        force_individual_executes = table_name in ['contact_address', 'contact_employment', 'contact_base']
                        
                        if use_executemany and len(batch_data) > 1 and not force_individual_executes:
                            # Try executemany for better performance
                            cursor.executemany(sql, batch_data)
                            batch_inserted = len(batch_data)
                        else:
                            # Fall back to individual executes
                            batch_inserted = 0
                            for record_values in batch_data:
                                cursor.execute(sql, record_values)
                                batch_inserted += 1
                    
                    except pyodbc.Error as e:
                        if ("cast specification" in str(e) or "converting" in str(e)) and use_executemany:
                            # Fall back to individual executes for type compatibility
                            self.logger.warning(f"executemany failed with cast error, falling back to individual executes: {e}")
                            use_executemany = False
                            batch_inserted = 0
                            for record_values in batch_data:
                                cursor.execute(sql, record_values)
                                batch_inserted += 1
                        else:
                            raise e
                    
                    inserted_count += batch_inserted
                    self._processed_records += batch_inserted
                    batch_start = batch_end
                    
                # Disable IDENTITY_INSERT if it was enabled
                if enable_identity_insert:
                    cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} OFF")
                    self.logger.debug(f"Disabled IDENTITY_INSERT for {qualified_table_name}")
                
                self.logger.info(f"Successfully inserted {inserted_count} records into {table_name}")
                    
        except pyodbc.Error as e:
            # Ensure IDENTITY_INSERT is turned off even on error
            if enable_identity_insert:
                try:
                    with self.get_connection() as conn:
                        cursor = conn.cursor()
                        qualified_table_name = self.config_manager.get_qualified_table_name(table_name)
                        cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} OFF")
                        self.logger.debug(f"Disabled IDENTITY_INSERT for {qualified_table_name} after error")
                except:
                    pass  # Don't mask the original error
            
            # Categorize database errors for better error reporting
            error_str = str(e).lower()
            if 'primary key constraint' in error_str or 'duplicate key' in error_str:
                error_msg = f"Primary key violation in {table_name}: {e}"
                self.logger.error(error_msg)
                raise XMLExtractionError(error_msg, error_category="constraint_violation")
            elif 'foreign key constraint' in error_str:
                error_msg = f"Foreign key violation in {table_name}: {e}"
                self.logger.error(error_msg)
                raise XMLExtractionError(error_msg, error_category="constraint_violation")
            elif 'check constraint' in error_str:
                error_msg = f"Check constraint violation in {table_name}: {e}"
                self.logger.error(error_msg)
                raise XMLExtractionError(error_msg, error_category="constraint_violation")
            elif 'cannot insert null' in error_str or 'not null constraint' in error_str:
                error_msg = f"NULL constraint violation in {table_name}: {e}"
                self.logger.error(error_msg)
                raise XMLExtractionError(error_msg, error_category="constraint_violation")
            else:
                error_msg = f"Database error during bulk insert into {table_name}: {e}"
                self.logger.error(error_msg)
                raise XMLExtractionError(error_msg, error_category="database_error")
        except Exception as e:
            # Ensure IDENTITY_INSERT is turned off even on error
            if enable_identity_insert:
                try:
                    with self.get_connection() as conn:
                        cursor = conn.cursor()
                        qualified_table_name = self.config_manager.get_qualified_table_name(table_name)
                        cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} OFF")
                        self.logger.debug(f"Disabled IDENTITY_INSERT for {qualified_table_name} after error")
                except:
                    pass  # Don't mask the original error
            
            error_msg = f"Unexpected error during bulk insert into {table_name}: {e}"
            self.logger.error(error_msg)
            raise XMLExtractionError(error_msg, error_category="system_error")
        
        return inserted_count
    
    def create_target_tables(self, sql_scripts: List[str]) -> bool:
        """
        Validate that target tables exist (does not create them).
        
        NOTE: This project assumes tables already exist in the database.
        Table creation and enum insertion should be handled separately
        by database administrators or setup scripts.
        
        Args:
            sql_scripts: List of CREATE TABLE SQL statements (used to extract table names)
            
        Returns:
            True if all referenced tables exist
            
        Raises:
            XMLExtractionError: If required tables do not exist
        """
        if not sql_scripts:
            self.logger.warning("No SQL scripts provided for table validation")
            return True
        
        table_names = []
        
        # Extract table names from CREATE TABLE scripts
        for script in sql_scripts:
            if not script.strip():
                continue
            
            statements = [stmt.strip() for stmt in script.split('GO') if stmt.strip()]
            
            for statement in statements:
                if statement.upper().startswith('CREATE TABLE'):
                    table_name = self._extract_table_name(statement)
                    if table_name != "UNKNOWN":
                        table_names.append(table_name)
        
        if table_names:
            self.logger.info(f"Validating that required tables exist: {', '.join(table_names)}")
            return self.validate_target_schema(table_names)
        
        return True
    
    def validate_target_schema(self, table_names: List[str]) -> bool:
        """
        Validate target schema using SQL Server system views.
        
        Args:
            table_names: List of table names to validate
            
        Returns:
            True if schema is valid and compatible
            
        Raises:
            SchemaValidationError: If schema validation fails
        """
        if not table_names:
            self.logger.warning("No table names provided for schema validation")
            return True
        
        validation_results = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for table_name in table_names:
                    # Check if table exists
                    table_exists_sql = """
                        SELECT COUNT(*) 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_NAME = ? AND TABLE_TYPE = 'BASE TABLE'
                    """
                    cursor.execute(table_exists_sql, (table_name,))
                    table_exists = cursor.fetchone()[0] > 0
                    
                    if not table_exists:
                        validation_results[table_name] = {
                            'exists': False,
                            'error': f"Table {table_name} does not exist"
                        }
                        continue
                    
                    # Get table column information
                    columns_sql = """
                        SELECT 
                            COLUMN_NAME,
                            DATA_TYPE,
                            IS_NULLABLE,
                            COLUMN_DEFAULT,
                            CHARACTER_MAXIMUM_LENGTH,
                            NUMERIC_PRECISION,
                            NUMERIC_SCALE
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_NAME = ?
                        ORDER BY ORDINAL_POSITION
                    """
                    cursor.execute(columns_sql, (table_name,))
                    columns = cursor.fetchall()
                    
                    validation_results[table_name] = {
                        'exists': True,
                        'columns': [
                            {
                                'name': col[0],
                                'data_type': col[1],
                                'nullable': col[2] == 'YES',
                                'default': col[3],
                                'max_length': col[4],
                                'precision': col[5],
                                'scale': col[6]
                            }
                            for col in columns
                        ]
                    }
                    
                    self.logger.info(f"Table {table_name} validated: {len(columns)} columns")
        
        except pyodbc.Error as e:
            error_msg = f"Schema validation failed: {e}"
            self.logger.error(error_msg)
            raise SchemaValidationError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during schema validation: {e}"
            self.logger.error(error_msg)
            raise SchemaValidationError(error_msg)
        
        # Check for validation failures
        failed_tables = [name for name, result in validation_results.items() 
                        if not result.get('exists', False)]
        
        if failed_tables:
            error_msg = f"Schema validation failed for tables: {', '.join(failed_tables)}"
            self.logger.error(error_msg)
            raise SchemaValidationError(error_msg)
        
        self.logger.info(f"Schema validation successful for {len(table_names)} tables")
        return True
    
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
    
    def _extract_table_name(self, create_table_sql: str) -> str:
        """
        Extract table name from CREATE TABLE SQL statement.
        
        Args:
            create_table_sql: CREATE TABLE SQL statement
            
        Returns:
            Extracted table name
        """
        try:
            # Simple regex-free approach to extract table name
            sql_upper = create_table_sql.upper().strip()
            if not sql_upper.startswith('CREATE TABLE'):
                return "UNKNOWN"
            
            # Find the table name after CREATE TABLE
            parts = create_table_sql.split()
            for i, part in enumerate(parts):
                if part.upper() == 'TABLE' and i + 1 < len(parts):
                    table_name = parts[i + 1]
                    # Remove brackets and schema prefix if present
                    table_name = table_name.replace('[', '').replace(']', '')
                    if '.' in table_name:
                        table_name = table_name.split('.')[-1]
                    return table_name
            
            return "UNKNOWN"
        except Exception:
            return "UNKNOWN"
    
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
