"""
Bulk Insert Strategy - Optimized Data Loading

Encapsulates the strategy for inserting records with automatic fallback from
fast_executemany to individual inserts. Handles encoding, batching, and graceful
error recovery for constraint violations.
"""

import logging
import pyodbc

from typing import List, Dict, Any, Tuple

from ..exceptions import XMLExtractionError, DatabaseConstraintError


class BulkInsertStrategy:
    """
    Strategy for bulk inserting records into database tables.
    
    Implements two-tier insertion strategy:
    1. Fast path: executemany for optimal performance
    2. Fallback path: individual executes for robustness
    
    Automatically switches between strategies based on error type.
    """
    
    def __init__(self, batch_size: int = 500, logger: logging.Logger = None):
        """
        Initialize bulk insert strategy.
        
        Args:
            batch_size: Records per batch for memory-efficient processing
            logger: Optional logger instance
        """
        self.batch_size = batch_size
        self.logger = logger or logging.getLogger(__name__)
    
    def insert(
        self,
        cursor,
        records: List[Dict[str, Any]],
        table_name: str,
        qualified_table_name: str,
        enable_identity_insert: bool = False
    ) -> int:
        """
        Insert records using optimized strategy with automatic fallback.
        
        Args:
            cursor: Active database cursor
            records: List of records to insert
            table_name: Unqualified table name (for error messages)
            qualified_table_name: Schema-qualified table name ([schema].[table])
            enable_identity_insert: Whether to enable IDENTITY_INSERT
            
        Returns:
            Number of records successfully inserted
            
        Raises:
            XMLExtractionError: On database or data errors
        """
        if not records:
            return 0
        
        inserted_count = 0
        
        try:
            # Prepare data and SQL
            columns, data_tuples, sql_template = self._prepare_data_tuples(records)
            sql = sql_template.replace("{table}", qualified_table_name)
            
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"SQL: {sql}")
                # Also log a sample parameter mapping for the first record to aid debugging
                if data_tuples:
                    try:
                        first_tuple = data_tuples[0]
                        sample_map = {col: first_tuple[i] for i, col in enumerate(columns)}
                        self.logger.debug(f"Sample params (first record): {sample_map}")
                    except Exception as e:
                        self.logger.debug(f"Failed to build sample params debug info: {e}")
#            else:
#                # If DEBUG logging is suppressed, print SQL and a sample param mapping to stdout
#                try:
#                    print("[BULK INSERT SQL]:", sql)
#                    if data_tuples:
#                        first_tuple = data_tuples[0]
#                        sample_map = {col: first_tuple[i] for i, col in enumerate(columns)}
#                        print("[BULK INSERT SAMPLE PARAMS]:", sample_map)
#                except Exception as e:
#                    # Avoid raising; fallback to logger
#                    self.logger.info(f"Could not print sample params: {e}")
            
            # Enable IDENTITY_INSERT if needed
            if enable_identity_insert:
                cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} ON")
                self.logger.debug(f"Enabled IDENTITY_INSERT for {qualified_table_name}")
            
            # Enable fast_executemany for performance
            cursor.fast_executemany = True
            
            # Process in batches with fallback strategy
            batch_start = 0
            
            while batch_start < len(data_tuples):
                batch_end = min(batch_start + self.batch_size, len(data_tuples))
                batch_data = data_tuples[batch_start:batch_end]
                
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Processing batch {batch_start}-{batch_end} into {table_name}")
                
                # Try fast path first, fallback to individual if needed
                batch_inserted, used_fast_path = self._try_fast_insert(cursor, sql, batch_data, table_name)
                
                if not used_fast_path:
                    batch_inserted = self._fallback_individual_insert(cursor, sql, batch_data, table_name)
                
                inserted_count += batch_inserted
                batch_start = batch_end
            
            # Disable IDENTITY_INSERT if it was enabled
            if enable_identity_insert:
                cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} OFF")
                self.logger.debug(f"Disabled IDENTITY_INSERT for {qualified_table_name}")
            
            self.logger.info(f"Successfully inserted {inserted_count} records into {table_name}")
            
        except pyodbc.Error as e:
            self._cleanup_identity_insert_safely(cursor, qualified_table_name, enable_identity_insert)
            self._handle_database_error(e, table_name)
        except Exception as e:
            self._cleanup_identity_insert_safely(cursor, qualified_table_name, enable_identity_insert)
            error_msg = f"Error during bulk insert into {table_name}: {e}"
            self.logger.error(error_msg)
            raise XMLExtractionError(error_msg, error_category="system_error")
        
        return inserted_count
    
    def _prepare_data_tuples(self, records: List[Dict[str, Any]]) -> Tuple[List[str], List[Tuple], str]:
        """
        Prepare data tuples from records, handling encoding and null conversions.
        
        Returns:
            (columns, data_tuples, sql_statement_template)
        """
        columns = list(records[0].keys())
        column_list = ', '.join(f"[{col}]" for col in columns)
        placeholders = ', '.join('?' * len(columns))
        
        # Build INSERT statement template
        sql = f"INSERT INTO {{table}} ({column_list}) VALUES ({placeholders})"
        
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Columns: {columns}")
        
        # Prepare data tuples with encoding handling
        data_tuples = []
        for record in records:
            values = []
            for col in columns:
                val = record.get(col)
                # Convert empty string to None
                if val == '':
                    val = None
                # Handle string encoding
                elif isinstance(val, str):
                    try:
                        val = val.encode('utf-8').decode('utf-8')
                    except (UnicodeEncodeError, UnicodeDecodeError):
                        pass
                values.append(val)
            data_tuples.append(tuple(values))
        
        return columns, data_tuples, sql
    
    def _try_fast_insert(self, cursor, sql: str, batch_data: List[Tuple], table_name: str) -> Tuple[int, bool]:
        """
        Attempt bulk insert using executemany for optimal performance.
        
        Returns:
            (batch_inserted, success) where success=True if fast path worked
        """
        # Force individual executes for tables with known pyodbc executemany encoding issues
        force_individual = table_name in ['contact_address', 'contact_employment', 'contact_base']
        
        if len(batch_data) <= 1 or force_individual:
            return 0, False  # Use fallback path
        
        try:
            cursor.executemany(sql, batch_data)
            return len(batch_data), True  # Success
        except pyodbc.Error as e:
            error_str = str(e).lower()
            if "cast specification" in error_str or "converting" in error_str:
                self.logger.debug(f"executemany failed with type error, using individual inserts: {e}")
                return 0, False  # Signal fallback needed
            else:
                raise  # Re-raise non-type-conversion errors
    
    def _fallback_individual_insert(self, cursor, sql: str, batch_data: List[Tuple], table_name: str) -> int:
        """
        Insert records individually, handling constraint violations gracefully.
        
        Returns:
            Count of successfully inserted records
        """
        batch_inserted = 0
        for record_values in batch_data:
            try:
                cursor.execute(sql, record_values)
                batch_inserted += 1
            except pyodbc.Error as record_error:
                error_str = str(record_error).lower()
                # Handle contact_base duplicate keys gracefully
                if table_name == 'contact_base' and (
                    'primary key constraint' in error_str or 'duplicate key' in error_str
                ):
                    con_id = record_values[0] if len(record_values) > 0 else None
                    self.logger.warning(f"Skipping duplicate contact_base (con_id={con_id})")
                    continue
                else:
                    raise record_error
        
        return batch_inserted
    
    def _handle_database_error(self, e: Exception, table_name: str) -> None:
        """
        Categorize and re-raise database errors with proper exception types.
        
        Constraint violations raise DatabaseConstraintError (specific type).
        Other database errors raise XMLExtractionError with database_error category.
        
        Raises:
            DatabaseConstraintError: For PK, FK, CHECK, NOT NULL violations
            XMLExtractionError: For other database errors
        """
        error_str = str(e).lower()
        
        if 'primary key constraint' in error_str or 'duplicate key' in error_str:
            error_msg = f"Primary key violation in {table_name}: {e}"
            self.logger.error(error_msg)
            raise DatabaseConstraintError(error_msg, error_category="primary_key_violation")
        elif 'foreign key constraint' in error_str:
            error_msg = f"Foreign key violation in {table_name}: {e}"
            self.logger.error(error_msg)
            raise DatabaseConstraintError(error_msg, error_category="foreign_key_violation")
        elif 'check constraint' in error_str:
            error_msg = f"Check constraint violation in {table_name}: {e}"
            self.logger.error(error_msg)
            raise DatabaseConstraintError(error_msg, error_category="check_constraint_violation")
        elif 'cannot insert null' in error_str or 'not null constraint' in error_str:
            error_msg = f"NULL constraint violation in {table_name}: {e}"
            self.logger.error(error_msg)
            raise DatabaseConstraintError(error_msg, error_category="not_null_violation")
        else:
            error_msg = f"Database error during bulk insert into {table_name}: {e}"
            self.logger.error(error_msg)
            raise XMLExtractionError(error_msg, error_category="database_error")
    
    def _cleanup_identity_insert_safely(self, cursor, qualified_table_name: str, enable_identity_insert: bool) -> None:
        """
        Safely disable IDENTITY_INSERT on error without masking original exception.
        
        Attempts cleanup but doesn't raise if it fails.
        """
        if enable_identity_insert:
            try:
                cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} OFF")
                self.logger.debug(f"Disabled IDENTITY_INSERT for {qualified_table_name} after error")
            except:
                pass  # Don't mask the original error
