"""
Unit Tests for DuplicateContactDetector (extracted from MigrationEngine)

Tests verify duplicate detection logic for contact records with different key structures:
- contact_base: Single primary key (con_id)
- contact_address: Composite key (con_id + address_type_enum)
- contact_employment: Composite key (con_id + employment_type_enum)
"""

import unittest

from unittest.mock import Mock
from xml_extractor.database.duplicate_contact_detector import DuplicateContactDetector


class DummyConn:
    """Mock connection context manager for testing."""
    def __init__(self, existing):
        self.existing = existing
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def cursor(self):
        return DummyCursor(self.existing)


class DummyCursor:
    """Mock cursor for testing."""
    def __init__(self, existing):
        self.existing = existing
    
    def execute(self, query, params=None):
        self.query = query
        self.params = params
    
    def fetchall(self):
        if not self.existing:
            return []
        if isinstance(self.existing[0], tuple):
            return self.existing
        return [(x,) for x in self.existing]


class TestDuplicateDetection(unittest.TestCase):
    """Test duplicate contact detection logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.detector = DuplicateContactDetector(connection_provider=lambda: None)
    
    def test_contact_base_duplicate(self):
        """Test filtering of duplicate contact_base records."""
        # Simulate existing con_id in DB
        batch = [
            {'con_id': 100, 'app_id': 1},
            {'con_id': 101, 'app_id': 2}
        ]
        
        # Mock the connection provider
        def mock_conn_provider():
            return DummyConn([100])  # con_id 100 exists
        
        detector = DuplicateContactDetector(connection_provider=mock_conn_provider)
        filtered = detector.filter_duplicates(batch, 'contact_base', '[dbo].[contact_base]')
        
        # Should only have con_id 101 (100 is duplicate)
        assert len(filtered) == 1
        assert filtered[0]['con_id'] == 101
    
    def test_contact_address_duplicate(self):
        """Test filtering of duplicate contact_address records."""
        batch = [
            {'con_id': 200, 'address_type_enum': 1},
            {'con_id': 200, 'address_type_enum': 2},
            {'con_id': 201, 'address_type_enum': 1}
        ]
        
        # Mock the connection provider with existing composite key (200, 1)
        def mock_conn_provider():
            return DummyConn([(200, 1)])
        
        detector = DuplicateContactDetector(connection_provider=mock_conn_provider)
        filtered = detector.filter_duplicates(batch, 'contact_address', '[dbo].[contact_address]')
        
        # Should have 2 records (skip (200, 1))
        assert len(filtered) == 2
        assert {'con_id': 200, 'address_type_enum': 2} in filtered
        assert {'con_id': 201, 'address_type_enum': 1} in filtered
    
    def test_contact_employment_duplicate(self):
        """Test filtering of duplicate contact_employment records."""
        batch = [
            {'con_id': 300, 'employment_type_enum': 1},
            {'con_id': 300, 'employment_type_enum': 2},
            {'con_id': 301, 'employment_type_enum': 1}
        ]
        
        # Mock the connection provider with existing composite key (300, 2)
        def mock_conn_provider():
            return DummyConn([(300, 2)])
        
        detector = DuplicateContactDetector(connection_provider=mock_conn_provider)
        filtered = detector.filter_duplicates(batch, 'contact_employment', '[dbo].[contact_employment]')
        
        # Should have 2 records (skip (300, 2))
        assert len(filtered) == 2
        assert {'con_id': 300, 'employment_type_enum': 1} in filtered
        assert {'con_id': 301, 'employment_type_enum': 1} in filtered
    
    def test_non_contact_table_passed_through(self):
        """Test that non-contact tables are passed through unchanged."""
        batch = [
            {'app_id': 1, 'name': 'app1'},
            {'app_id': 2, 'name': 'app2'}
        ]
        
        def mock_conn_provider():
            return DummyConn([])
        
        detector = DuplicateContactDetector(connection_provider=mock_conn_provider)
        filtered = detector.filter_duplicates(batch, 'app_base', '[dbo].[app_base]')
        
        # Should return unchanged
        assert filtered == batch
    
    def test_empty_batch_passed_through(self):
        """Test that empty batches are passed through unchanged."""
        batch = []
        
        def mock_conn_provider():
            return DummyConn([])
        
        detector = DuplicateContactDetector(connection_provider=mock_conn_provider)
        filtered = detector.filter_duplicates(batch, 'contact_base', '[dbo].[contact_base]')
        
        assert filtered == []


if __name__ == '__main__':
    unittest.main()
