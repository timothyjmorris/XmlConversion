"""
Bulk Insert Strategy - Optimized Data Loading

Encapsulates the strategy for inserting records with automatic fallback from
fast_executemany to individual inserts. Handles encoding, batching, and graceful
error recovery for constraint violations.
"""

import logging
import time
import pyodbc
import os
import json
from datetime import datetime

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
            
            # Prepare container for per-batch info
            self._last_batch_info_list = []

            # Process in batches with fallback strategy
            batch_start = 0

            while batch_start < len(data_tuples):
                batch_end = min(batch_start + self.batch_size, len(data_tuples))
                batch_data = data_tuples[batch_start:batch_end]

                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Processing batch {batch_start}-{batch_end} into {table_name}")

                # Try fast path first, fallback to individual if needed
                try:
                    batch_inserted, used_fast_path, batch_elapsed = self._try_fast_insert(cursor, sql, batch_data, table_name)

                    if not used_fast_path:
                        batch_inserted, batch_elapsed = self._fallback_individual_insert(
                            cursor,
                            sql,
                            batch_data,
                            table_name,
                            qualified_table_name,
                            columns,
                        )
                except pyodbc.Error as batch_err:
                    # Dump failing SQL + sample params for diagnostics before re-raising
                    try:
                        self._dump_failure_context(sql, columns, batch_data, table_name, batch_err)
                    except Exception as dump_exc:
                        self.logger.error(f"Failed to write failure context: {dump_exc}")
                    raise

                # Record per-batch info for instrumentation consumers
                try:
                    self._last_batch_info_list.append({
                        'table': table_name,
                        'qualified_table': qualified_table_name,
                        'batch_start': batch_start,
                        'batch_end': batch_end,
                        'batch_size': len(batch_data),
                        'used_fast_path': bool(used_fast_path),
                        'elapsed_s': round(batch_elapsed, 6)
                    })
                except Exception:
                    pass

                inserted_count += batch_inserted
                batch_start = batch_end
            
            # Disable IDENTITY_INSERT if it was enabled
            if enable_identity_insert:
                cursor.execute(f"SET IDENTITY_INSERT {qualified_table_name} OFF")
                self.logger.debug(f"Disabled IDENTITY_INSERT for {qualified_table_name}")
            
            # Use DEBUG to avoid noisy INFO logs during experiments
            self.logger.debug(f"Successfully inserted {inserted_count} records into {table_name}")
            
        except pyodbc.Error as e:
            # Attempt to dump context if available
            try:
                # If sql and data_tuples exist in scope, dump a sample
                if 'sql' in locals() and 'data_tuples' in locals():
                    sample_batch = data_tuples[0: min(len(data_tuples), self.batch_size)]
                    self._dump_failure_context(sql, columns if 'columns' in locals() else None, sample_batch, table_name, e)
            except Exception:
                pass
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
        
        Uses the union of all keys across all records so that rows with
        different column sets (e.g. collateral slots where only some have
        motor_size or mileage) still produce a consistent INSERT statement.
        Missing keys default to None (NULL).
        
        Returns:
            (columns, data_tuples, sql_statement_template)
        """
        # Collect union of all keys, preserving insertion order from first
        # record, then appending any additional keys from later records.
        seen = set()
        columns: List[str] = []
        for record in records:
            for key in record:
                if key not in seen:
                    seen.add(key)
                    columns.append(key)
        
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
    
    def _try_fast_insert(self, cursor, sql: str, batch_data: List[Tuple], table_name: str) -> Tuple[int, bool, float]:
        """
        Attempt bulk insert using executemany for optimal performance.

        Returns:
            (batch_inserted, success, elapsed_seconds) where success=True if fast path worked
        """
        # Keep these tables on the individual-insert blacklist due to known issues:
        # - app_contact_base, app_pricing_cc: FK/ordering failures when batched  
        # - app_solicited_cc, app_contact_address, app_contact_employment: Character encoding corruption
        #   with fast_executemany in grouped-commit scenarios (pyodbc bug?)
        # These must use conservative per-row insertion path for data integrity.
        force_individual = table_name in ('app_contact_base', 'app_pricing_cc', 'app_solicited_cc', 
                                         'app_contact_address', 'app_contact_employment')

        if len(batch_data) <= 1 or force_individual:
            return 0, False, 0.0  # Use fallback path

        try:
            fast_flag = getattr(cursor, 'fast_executemany', None)
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"fast_executemany flag on cursor for {table_name}: {fast_flag}")

            t0 = time.time()
            cursor.executemany(sql, batch_data)
            elapsed = time.time() - t0

            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    f"executemany succeeded for {table_name} batch_size={len(batch_data)} elapsed={elapsed:.3f}s"
                )

            return len(batch_data), True, elapsed  # Success
        except pyodbc.Error as e:
            error_str = str(e).lower()
            # For key/value-style tables, duplicates should not fail processing.
            # Fall back to per-row insert/update-on-duplicate handling.
            if table_name in ('scores', 'indicators', 'app_historical_lookup', 'app_report_results_lookup') and self._is_duplicate_key_error(error_str):
                self.logger.debug(f"executemany hit duplicate key for {table_name}, falling back to individual upsert path: {e}")
                return 0, False, 0.0
            if "cast specification" in error_str or "converting" in error_str:
                self.logger.debug(f"executemany failed with type error for {table_name}, falling back: {e}")
                return 0, False, 0.0  # Signal fallback needed
            else:
                raise  # Re-raise non-type-conversion errors
    
    def _fallback_individual_insert(
        self,
        cursor,
        sql: str,
        batch_data: List[Tuple],
        table_name: str,
        qualified_table_name: str,
        columns: List[str],
    ) -> Tuple[int, float]:
        """
        Insert records individually, handling constraint violations gracefully.
        
        Returns:
            Count of successfully inserted records
        """
        batch_inserted = 0
        t0 = time.time()
        for record_values in batch_data:
            try:
                cursor.execute(sql, record_values)
                batch_inserted += 1
            except pyodbc.Error as record_error:
                error_str = str(record_error).lower()
                # Handle app_contact_base duplicate keys gracefully
                if table_name == 'app_contact_base' and (
                    'primary key constraint' in error_str or 'duplicate key' in error_str
                ):
                    con_id = record_values[0] if len(record_values) > 0 else None
                    self.logger.warning(f"Skipping duplicate app_contact_base (con_id={con_id})")
                    continue
                # Key/value tables: duplicates are expected during re-processing; update in-place.
                if table_name in ('scores', 'indicators', 'app_historical_lookup', 'app_report_results_lookup') and self._is_duplicate_key_error(error_str):
                    updated = self._try_update_on_duplicate(
                        cursor,
                        table_name,
                        qualified_table_name,
                        columns,
                        record_values,
                    )
                    if updated:
                        # Count as successfully applied (even though it was an UPDATE)
                        batch_inserted += 1
                        continue
                    # If we couldn't build a safe update, just skip the duplicate row
                    self.logger.warning(f"Skipping duplicate row for {table_name} (no safe upsert key available)")
                    continue
                else:
                    raise record_error

        elapsed = time.time() - t0
        # Record fallback duration at DEBUG to avoid noisy INFO output; can be promoted when investigating
        self.logger.debug(
            f"Fallback individual inserts for {table_name} batch_size={len(batch_data)} inserted={batch_inserted} elapsed={elapsed:.3f}s"
        )

        return batch_inserted, elapsed

    def _is_duplicate_key_error(self, error_str: str) -> bool:
        """Detect SQL Server duplicate key violations from pyodbc error text."""
        if not error_str:
            return False
        # Common SQL Server duplicate key indicators (2601 = unique index, 2627 = PK)
        return (
            'cannot insert duplicate key' in error_str
            or 'duplicate key' in error_str
            or 'primary key constraint' in error_str
            or 'unique index' in error_str
            or '2601' in error_str
            or '2627' in error_str
        )

    def _try_update_on_duplicate(
        self,
        cursor,
        table_name: str,
        qualified_table_name: str,
        columns: List[str],
        record_values: Tuple,
    ) -> bool:
        """Attempt an UPDATE for a duplicate key record for known key/value tables."""
        try:
            record = {columns[i]: (record_values[i] if i < len(record_values) else None) for i in range(len(columns))}

            if table_name == 'scores':
                key_cols = ['app_id', 'score_identifier']
                set_cols = ['score']
            elif table_name == 'indicators':
                key_cols = ['app_id', 'indicator']
                set_cols = ['value']
            elif table_name == 'app_report_results_lookup':
                key_cols = ['app_id', 'name']
                # Some schemas include source_report_key; update it when provided.
                set_cols = ['value', 'source_report_key']
            elif table_name == 'app_historical_lookup':
                # Historical lookup is typically keyed by (app_id, name, source). If source isn't present,
                # fall back to (app_id, name).
                key_cols = ['app_id', 'name', 'source'] if 'source' in record else ['app_id', 'name']
                set_cols = ['value']
            else:
                return False

            if not all(col in record for col in key_cols):
                return False

            present_set_cols = [c for c in set_cols if c in record]
            if not present_set_cols:
                return False

            set_clause = ', '.join(f"[{col}] = ?" for col in present_set_cols)
            set_params = [record[col] for col in present_set_cols]

            where_fragments: List[str] = []
            where_params: List[Any] = []
            for col in key_cols:
                val = record.get(col)
                if val is None:
                    where_fragments.append(f"[{col}] IS NULL")
                else:
                    where_fragments.append(f"[{col}] = ?")
                    where_params.append(val)

            where_clause = ' AND '.join(where_fragments)
            update_sql = f"UPDATE {qualified_table_name} SET {set_clause} WHERE {where_clause}"
            cursor.execute(update_sql, tuple(set_params + where_params))
            return True
        except Exception as e:
            self.logger.debug(f"Update-on-duplicate failed for {table_name}: {e}")
            return False
    
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

    def _dump_failure_context(self, sql: str, columns, batch_data, table_name: str, exception: Exception) -> None:
        """
        Write a diagnostic JSON file containing the failing SQL, a sample of parameter rows,
        and the original exception text to `metrics/` for offline analysis.
        """
        try:
            metrics_dir = os.path.join(os.getcwd(), 'metrics')
            if not os.path.exists(metrics_dir):
                os.makedirs(metrics_dir, exist_ok=True)

            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S%f')[:-3]
            safe_columns = columns or []

            # Build sample params (limit to first 10 rows)
            sample_params = []
            max_rows = 10
            for row in (batch_data or [])[:max_rows]:
                try:
                    if safe_columns:
                        mapped = {safe_columns[i]: (row[i] if i < len(row) else None) for i in range(len(safe_columns))}
                    else:
                        mapped = list(row)
                except Exception:
                    mapped = [str(x) for x in row]
                # Ensure JSON serializable
                mapped = {k: (v if isinstance(v, (str, int, float, bool, type(None))) else str(v)) for k, v in (mapped.items() if isinstance(mapped, dict) else enumerate(mapped))}
                sample_params.append(mapped)

            payload = {
                'timestamp_utc': timestamp,
                'table': table_name,
                'sql': sql,
                'sample_params_count': len(sample_params),
                'sample_params': sample_params,
                'error': str(exception)
            }

            fname = f"failed_insert_{table_name}_{timestamp}.json"
            path = os.path.join(metrics_dir, fname)
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(payload, fh, indent=2)

            self.logger.error(f"Wrote failing-insert diagnostic to {path}")
        except Exception as dump_exc:
            self.logger.error(f"Failed to write failing-insert diagnostic: {dump_exc}")
    
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
