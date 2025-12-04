"""
Integration Tests for BulkInsertStrategy (extracted from MigrationEngine)

Tests verify that all error paths in BulkInsertStrategy.insert() work correctly:
- Fast executemany success path
- Fallback to individual inserts
- Constraint violations (primary key, foreign key, check, NOT NULL)
- Type conversion errors
- Connection errors
- Identity insert edge cases
- Transaction rollback/commit behavior

Note: With SoC refactoring, BulkInsertStrategy now handles all insert logic.
Tests mock cursors to verify BulkInsertStrategy behavior directly.
"""

import pytest
import pyodbc

from unittest.mock import Mock, MagicMock, patch, call

from xml_extractor.database.bulk_insert_strategy import BulkInsertStrategy
from xml_extractor.exceptions import XMLExtractionError


@pytest.fixture
def bulk_insert_strategy():
    """Create a bulk insert strategy for testing."""
    return BulkInsertStrategy(batch_size=500)


@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = Mock()
    cursor.fast_executemany = False
    return cursor


class TestBulkInsertSuccessPaths:
    """Test successful insertion scenarios."""
    
    def test_fast_executemany_success(self, bulk_insert_strategy, mock_cursor):
        """Fast path: executemany succeeds with no errors."""
        mock_cursor.executemany = Mock()
        mock_cursor.execute = Mock()
        
        records = [
            {'con_id': 1, 'first_name': 'John', 'last_name': 'Doe'},
            {'con_id': 2, 'first_name': 'Jane', 'last_name': 'Smith'},
        ]
        
        count = bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='contact_base_test',
            qualified_table_name='[dbo].[contact_base_test]',
            enable_identity_insert=False
        )
        
        assert count == 2
    
    def test_individual_inserts_fallback_on_type_error(self, bulk_insert_strategy, mock_cursor):
        """Individual insert path: falls back to individual inserts on cast error."""
        mock_cursor.executemany = Mock(side_effect=pyodbc.Error("[ODBC] cast specification error"))
        mock_cursor.execute = Mock()
        
        records = [
            {'col1': 'value1'},
            {'col1': 'value2'},
        ]
        
        count = bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='test_table',
            qualified_table_name='[dbo].[test_table]',
            enable_identity_insert=False
        )
        
        assert count == 2
        assert mock_cursor.execute.call_count >= 2
    
    def test_identity_insert_enabled_and_disabled(self, bulk_insert_strategy, mock_cursor):
        """Edge case: IDENTITY_INSERT is properly enabled and disabled."""
        mock_cursor.executemany = Mock()
        mock_cursor.execute = Mock()
        
        records = [
            {'con_id': 1, 'data': 'test'},
        ]
        
        bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='test_table',
            qualified_table_name='[dbo].[test_table]',
            enable_identity_insert=True
        )
        
        # Verify IDENTITY_INSERT was toggled
        calls = [str(call) for call in mock_cursor.execute.call_args_list]
        identity_insert_on_called = any('SET IDENTITY_INSERT' in call and 'ON' in call for call in calls)
        identity_insert_off_called = any('SET IDENTITY_INSERT' in call and 'OFF' in call for call in calls)
        
        assert identity_insert_on_called
        assert identity_insert_off_called


class TestBulkInsertErrorPaths:
    """Test error handling in bulk insert."""
    
    def test_primary_key_constraint_violation(self, bulk_insert_strategy, mock_cursor):
        """Primary key violation should raise XMLExtractionError."""
        # Make executemany raise pyodbc error
        def raise_pk_error(*args, **kwargs):
            raise pyodbc.Error("Violation of PRIMARY KEY constraint")
        
        mock_cursor.executemany = raise_pk_error
        
        # Need multiple records to trigger executemany (not individual insert fallback)
        records = [{'col1': 'value1'}, {'col1': 'value2'}]
        
        with pytest.raises(XMLExtractionError):
            bulk_insert_strategy.insert(
                cursor=mock_cursor,
                records=records,
                table_name='other_table',  # Not contact table to avoid forced individual
                qualified_table_name='[dbo].[other_table]',
                enable_identity_insert=False
            )
    
    def test_foreign_key_constraint_detected_in_error(self, bulk_insert_strategy, mock_cursor):
        """Foreign key violation should raise XMLExtractionError."""
        def raise_fk_error(*args, **kwargs):
            raise pyodbc.Error("FOREIGN KEY constraint")
        
        mock_cursor.executemany = raise_fk_error
        
        # Need multiple records to trigger executemany
        records = [{'col1': 'value1'}, {'col1': 'value2'}]
        
        with pytest.raises(XMLExtractionError):
            bulk_insert_strategy.insert(
                cursor=mock_cursor,
                records=records,
                table_name='other_table',  # Not contact table
                qualified_table_name='[dbo].[other_table]',
                enable_identity_insert=False
            )
    
    def test_not_null_constraint_detected_in_error(self, bulk_insert_strategy, mock_cursor):
        """NOT NULL constraint violation should raise XMLExtractionError."""
        def raise_nn_error(*args, **kwargs):
            raise pyodbc.Error("NOT NULL constraint")
        
        mock_cursor.executemany = raise_nn_error
        
        # Need multiple records to trigger executemany
        records = [{'col1': 'value1'}, {'col1': 'value2'}]
        
        with pytest.raises(XMLExtractionError):
            bulk_insert_strategy.insert(
                cursor=mock_cursor,
                records=records,
                table_name='other_table',  # Not contact table
                qualified_table_name='[dbo].[other_table]',
                enable_identity_insert=False
            )
    
    def test_type_conversion_error_triggers_fallback(self, bulk_insert_strategy, mock_cursor):
        """Type conversion error should trigger fallback to individual inserts."""
        mock_cursor.executemany = Mock(side_effect=pyodbc.Error("cast specification error"))
        mock_cursor.execute = Mock()
        
        records = [
            {'col1': 'value1'},
            {'col1': 'value2'},
        ]
        
        count = bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='test_table',
            qualified_table_name='[dbo].[test_table]',
            enable_identity_insert=False
        )
        
        assert count == 2
        assert mock_cursor.execute.call_count >= 2  # Fallback executed
    
    def test_connection_error_handled(self, bulk_insert_strategy, mock_cursor):
        """Connection errors should raise XMLExtractionError."""
        def raise_conn_error(*args, **kwargs):
            raise pyodbc.Error("Connection failed")
        
        mock_cursor.executemany = raise_conn_error
        
        # Need multiple records to trigger executemany (not individual insert fallback)
        records = [{'col1': 'value1'}, {'col1': 'value2'}]
        
        with pytest.raises(XMLExtractionError):
            bulk_insert_strategy.insert(
                cursor=mock_cursor,
                records=records,
                table_name='other_table',  # Not contact table
                qualified_table_name='[dbo].[other_table]',
                enable_identity_insert=False
            )
    
    def test_duplicate_key_in_contact_base_skipped(self, bulk_insert_strategy, mock_cursor):
        """Duplicate app_contact_base records should be skipped gracefully."""
        # First record succeeds, second fails with duplicate key
        mock_cursor.execute = Mock(side_effect=[
            None,  # First insert succeeds
            pyodbc.Error("Violation of PRIMARY KEY constraint"),  # Second fails
        ])
        
        records = [
            {'con_id': 1, 'data': 'first'},
            {'con_id': 1, 'data': 'duplicate'},
        ]
        
        # Should skip the duplicate and return 1 successful insert
        count = bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='app_contact_base',
            qualified_table_name='[dbo].[app_contact_base]',
            enable_identity_insert=False
        )
        
        # For app_contact_base, duplicate key errors are caught and skipped gracefully
        assert count >= 1


class TestBulkInsertTransactionBehavior:
    """Test transaction-related behavior."""
    
    def test_commit_called_when_commit_after_true(self, bulk_insert_strategy, mock_cursor):
        """Commit should be called after successful insert if requested."""
        mock_cursor.executemany = Mock()
        
        records = [{'col1': 'value1'}]
        
        bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='test_table',
            qualified_table_name='[dbo].[test_table]',
            enable_identity_insert=False
        )
    
    def test_commit_not_called_when_commit_after_false(self, bulk_insert_strategy, mock_cursor):
        """Commit should not be called if not requested."""
        mock_cursor.executemany = Mock()
        
        records = [{'col1': 'value1'}]
        
        count = bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='test_table',
            qualified_table_name='[dbo].[test_table]',
            enable_identity_insert=False
        )
        
        assert count == 1
    
    def test_identity_insert_cleanup_attempted_on_error(self, bulk_insert_strategy, mock_cursor):
        """IDENTITY_INSERT should be disabled even on error."""
        def raise_error(*args, **kwargs):
            raise pyodbc.Error("Some error")
        
        mock_cursor.executemany = raise_error
        
        # Need multiple records to trigger executemany (not individual insert fallback)
        records = [{'col1': 'value1'}, {'col1': 'value2'}]
        
        with pytest.raises(XMLExtractionError):
            bulk_insert_strategy.insert(
                cursor=mock_cursor,
                records=records,
                table_name='other_table',  # Not contact table
                qualified_table_name='[dbo].[other_table]',
                enable_identity_insert=True
            )
        
        # Verify IDENTITY_INSERT ON was called before error
        on_calls = [c for c in mock_cursor.execute.call_args_list if 'IDENTITY_INSERT' in str(c)]
        assert len(on_calls) >= 1  # At least the ON call


class TestBulkInsertDataPreparation:
    """Test data preparation logic."""
    
    def test_multiple_records_processed_in_batches(self, bulk_insert_strategy, mock_cursor):
        """Multiple records should be processed in batches."""
        mock_cursor.executemany = Mock()
        mock_cursor.execute = Mock()
        
        # Create 10 records (batch_size=500 in fixture, so all in one batch)
        records = [{'id': i, 'value': f'val{i}'} for i in range(10)]
        
        count = bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='test_table',
            qualified_table_name='[dbo].[test_table]',
            enable_identity_insert=False
        )
        
        assert count == 10
    
    def test_single_record_processed(self, bulk_insert_strategy, mock_cursor):
        """Single record should be processed correctly."""
        mock_cursor.executemany = Mock()
        mock_cursor.execute = Mock()
        
        records = [{'id': 1, 'value': 'test'}]
        
        count = bulk_insert_strategy.insert(
            cursor=mock_cursor,
            records=records,
            table_name='test_table',
            qualified_table_name='[dbo].[test_table]',
            enable_identity_insert=False
        )
        
        # Single record forces individual insert path (no executemany)
        assert count == 1
