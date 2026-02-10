"""
Duplicate Contact Detection - Prevents Constraint Violations

Encapsulates business logic for identifying and filtering duplicate contact records
that would violate primary key constraints. Queries database with NOLOCK hints to
prevent lock contention and maintains schema isolation via qualified table names.

DESIGN RATIONALE - Why Check Each Table Separately:

The initial intuition was to simplify this to a single query against app_contact_base.con_id
for all three tables, since app_contact_address and app_contact_employment have FK constraints
to app_contact_base. However, this approach has a critical flaw:

SCENARIO: Processing app_id 443306 (first run, database empty)
1. Insert app_contact_base: con_id=738936, con_id=738937
2. Before inserting app_contact_address with records for those con_ids:
   - If we query app_contact_base, we FIND both con_ids (just inserted in step 1)
   - We incorrectly filter ALL app_contact_address records as "duplicates"
   - Insert 0 records

The issue is that within a single transaction, we see our own uncommitted inserts.
We can't distinguish between:
- "con_id exists because WE just inserted it" (should insert children)  
- "con_id exists from a previous app" (should skip children)

CORRECT APPROACH - Check Destination Tables:
- app_contact_base: Check app_contact_base for existing con_id (prevents PK violation)
- app_contact_address: Check app_contact_address for existing (con_id, address_type_enum) pairs
- app_contact_employment: Check app_contact_employment for existing (con_id, employment_type_enum) pairs

This works because:
- First run: Destination tables empty → nothing filtered
- Subsequent runs: Only actual duplicates from previous apps are filtered

TRADE-OFF: 3 queries per app vs 1 query
- Cost: ~2 extra queries per app (typically <5ms each with NOLOCK and indexed lookups)
- Benefit: Correct handling of initial inserts + cross-app duplicate detection
- Scale: Acceptable for batch processing (processing time dominated by XML parsing/mapping)

Note: DataMapper already handles within-batch deduplication using contact type priority,
so we should never see duplicate con_ids within a single app's processing batch.
"""

import logging
import pyodbc

from typing import List, Dict, Any


class DuplicateContactDetector:
    """
    Detects and filters duplicate contact records to prevent constraint violations.
    
    Handles three types of contact records with different key structures:
    - app_contact_base: Single primary key (con_id)
    - app_contact_address: Composite key (con_id + address_type_enum)
    - app_contact_employment: Composite key (con_id + employment_type_enum)
    
    Uses NOLOCK hints to prevent lock contention on duplicate queries.
    """
    
    def __init__(self, connection_provider, logger: logging.Logger = None):
        """
        Initialize duplicate detector.
        
        Args:
            connection_provider: Callable that returns pyodbc connections
            logger: Optional logger instance (creates new if not provided)
        """
        self.connection_provider = connection_provider
        self.logger = logger or logging.getLogger(__name__)
    
    def filter_duplicates(
        self,
        records: List[Dict[str, Any]],
        table_name: str,
        qualified_table_name: str,
        connection: Any = None
    ) -> List[Dict[str, Any]]:
        """
        Filter out duplicate contact records from batch.
        
        Strategy:
        1. For app_contact_base: Check con_id existence
        2. For app_contact_address: Check (con_id, address_type_enum) composite key
        3. For app_contact_employment: Check (con_id, employment_type_enum) composite key
        
        Args:
            records: List of records to filter
            table_name: Table name (app_contact_base, app_contact_address, app_contact_employment)
            qualified_table_name: Schema-qualified table name ([schema].[table])
            
        Returns:
            Filtered list of records with duplicates removed
        """
        # Only filter for contact tables; pass through others
        if table_name not in ['app_contact_base', 'app_contact_address', 'app_contact_employment'] or not records:
            return records
        
        try:
            if table_name == 'app_contact_base':
                return self._filter_contact_base_duplicates(records, qualified_table_name, connection=connection)
            elif table_name == 'app_contact_address':
                return self._filter_contact_address_duplicates(records, qualified_table_name, connection=connection)
            elif table_name == 'app_contact_employment':
                return self._filter_contact_employment_duplicates(records, qualified_table_name, connection=connection)
        
        except pyodbc.Error as e:
            self.logger.warning(f"Failed to check for duplicates in {table_name}, proceeding with all records: {e}")
        
        return records
    
    def _filter_contact_base_duplicates(
        self,
        records: List[Dict[str, Any]],
        qualified_table_name: str,
        connection: Any = None
    ) -> List[Dict[str, Any]]:
        """Filter duplicate app_contact_base records by con_id."""
        # Prefer using provided connection to avoid creating a new connection per check
        conn_ctx = None
        if connection is not None:
            conn = connection
            cursor = conn.cursor()
        else:
            conn_ctx = self.connection_provider()
            conn = conn_ctx.__enter__()
            cursor = conn.cursor()
        
        # Extract con_id values from records
        con_ids = [record.get('con_id') for record in records if record.get('con_id')]
        if not con_ids:
            return records
        
        # Query database for existing con_ids
        placeholders = ','.join('?' for _ in con_ids)
        query = f"SELECT con_id FROM {qualified_table_name} WITH (NOLOCK) WHERE con_id IN ({placeholders})"
        cursor.execute(query, con_ids)
        existing_con_ids = {row[0] for row in cursor.fetchall()}
        
        # Filter and track
        filtered_records = []
        skipped_count = 0
        for record in records:
            con_id = record.get('con_id')
            if con_id in existing_con_ids:
                self.logger.warning(f"Skipping duplicate app_contact_base record (con_id={con_id})")
                skipped_count += 1
            else:
                filtered_records.append(record)
        
        if skipped_count > 0:
            self.logger.info(f"Filtered {skipped_count} duplicate app_contact_base records")

        # Cleanup created connection context if we opened it
        if conn_ctx is not None:
            try:
                conn_ctx.__exit__(None, None, None)
            except Exception:
                pass

        return filtered_records
    
    def _filter_contact_address_duplicates(
        self,
        records: List[Dict[str, Any]],
        qualified_table_name: str,
        connection: Any = None
    ) -> List[Dict[str, Any]]:
        """Filter duplicate app_contact_address records by (con_id, address_type_enum) composite key."""
        conn_ctx = None
        if connection is not None:
            conn = connection
            cursor = conn.cursor()
        else:
            conn_ctx = self.connection_provider()
            conn = conn_ctx.__enter__()
            cursor = conn.cursor()
        
        # Extract composite keys
        key_pairs = [
            (record.get('con_id'), record.get('address_type_enum'))
            for record in records
            if record.get('con_id') and record.get('address_type_enum')
        ]
        
        if not key_pairs:
            return records
        
        # Build parameterized query for composite keys
        conditions = []
        params = []
        for con_id, addr_type in key_pairs:
            conditions.append("(con_id = ? AND address_type_enum = ?)")
            params.extend([con_id, addr_type])
        
        query = f"SELECT con_id, address_type_enum FROM {qualified_table_name} WITH (NOLOCK) WHERE {' OR '.join(conditions)}"
        cursor.execute(query, params)
        existing_keys = {(row[0], row[1]) for row in cursor.fetchall()}
        
        # Filter against database AND in-batch duplicates
        filtered_records = []
        seen_in_batch = set()
        db_skipped = 0
        batch_skipped = 0
        
        for record in records:
            con_id = record.get('con_id')
            addr_type = record.get('address_type_enum')
            key = (con_id, addr_type)
            
            # Check if already in database
            if key in existing_keys:
                self.logger.warning(f"Skipping duplicate app_contact_address (con_id={con_id}, address_type_enum={addr_type}) - already in database")
                db_skipped += 1
            # Check if duplicate within current batch
            elif key in seen_in_batch:
                self.logger.warning(f"Skipping duplicate app_contact_address (con_id={con_id}, address_type_enum={addr_type}) - duplicate within batch")
                batch_skipped += 1
            else:
                filtered_records.append(record)
                seen_in_batch.add(key)
        
        if db_skipped > 0 or batch_skipped > 0:
            self.logger.info(f"Filtered {db_skipped + batch_skipped} duplicate app_contact_address records ({db_skipped} from DB, {batch_skipped} in-batch)")

        if conn_ctx is not None:
            try:
                conn_ctx.__exit__(None, None, None)
            except Exception:
                pass

        return filtered_records
    
    def _filter_contact_employment_duplicates(
        self,
        records: List[Dict[str, Any]],
        qualified_table_name: str,
        connection: Any = None
    ) -> List[Dict[str, Any]]:
        """Filter duplicate app_contact_employment records by (con_id, employment_type_enum) composite key."""
        conn_ctx = None
        if connection is not None:
            conn = connection
            cursor = conn.cursor()
        else:
            conn_ctx = self.connection_provider()
            conn = conn_ctx.__enter__()
            cursor = conn.cursor()
        
        # Extract composite keys
        key_pairs = [
            (record.get('con_id'), record.get('employment_type_enum'))
            for record in records
            if record.get('con_id') and record.get('employment_type_enum')
        ]
        
        if not key_pairs:
            return records
        
        # Build parameterized query for composite keys
        conditions = []
        params = []
        for con_id, emp_type in key_pairs:
            conditions.append("(con_id = ? AND employment_type_enum = ?)")
            params.extend([con_id, emp_type])
        
        query = f"SELECT con_id, employment_type_enum FROM {qualified_table_name} WITH (NOLOCK) WHERE {' OR '.join(conditions)}"
        cursor.execute(query, params)
        existing_keys = {(row[0], row[1]) for row in cursor.fetchall()}
        
        # Filter against database AND in-batch duplicates
        filtered_records = []
        seen_in_batch = set()
        db_skipped = 0
        batch_skipped = 0
        
        for record in records:
            con_id = record.get('con_id')
            emp_type = record.get('employment_type_enum')
            key = (con_id, emp_type)
            
            # Check if already in database
            if key in existing_keys:
                self.logger.warning(f"Skipping duplicate app_contact_employment (con_id={con_id}, employment_type_enum={emp_type}) - already in database")
                db_skipped += 1
            # Check if duplicate within current batch
            elif key in seen_in_batch:
                self.logger.warning(f"Skipping duplicate app_contact_employment (con_id={con_id}, employment_type_enum={emp_type}) - duplicate within batch")
                batch_skipped += 1
            else:
                filtered_records.append(record)
                seen_in_batch.add(key)
        
        if db_skipped > 0 or batch_skipped > 0:
            self.logger.info(f"Filtered {db_skipped + batch_skipped} duplicate app_contact_employment records ({db_skipped} from DB, {batch_skipped} in-batch)")

        if conn_ctx is not None:
            try:
                conn_ctx.__exit__(None, None, None)
            except Exception:
                pass

        return filtered_records
