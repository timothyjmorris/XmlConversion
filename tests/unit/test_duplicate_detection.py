import unittest
from xml_extractor.database.migration_engine import MigrationEngine

class TestDuplicateDetection(unittest.TestCase):
    def setUp(self):
        self.engine = MigrationEngine()

    def test_contact_base_duplicate(self):
        # Simulate existing con_id in DB
        existing = [{'con_id': 100, 'app_id': 1}]
        # Simulate batch with duplicate
        batch = [{'con_id': 100, 'app_id': 2}, {'con_id': 101, 'app_id': 2}]
        # Patch get_connection to simulate DB response
        self.engine.get_connection = lambda: DummyConn([100])
        filtered = self.engine._filter_duplicate_contacts(batch, 'contact_base')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['con_id'], 101)

    def test_contact_address_duplicate(self):
        batch = [
            {'con_id': 200, 'address_type_enum': 1},
            {'con_id': 200, 'address_type_enum': 2},
            {'con_id': 201, 'address_type_enum': 1}
        ]
        self.engine.get_connection = lambda: DummyConn([(200, 1)])
        filtered = self.engine._filter_duplicate_contacts(batch, 'contact_address')
        self.assertEqual(len(filtered), 2)
        self.assertTrue({'con_id': 200, 'address_type_enum': 2} in filtered)
        self.assertTrue({'con_id': 201, 'address_type_enum': 1} in filtered)

    def test_contact_employment_duplicate(self):
        batch = [
            {'con_id': 300, 'employment_type_enum': 1},
            {'con_id': 300, 'employment_type_enum': 2},
            {'con_id': 301, 'employment_type_enum': 1}
        ]
        self.engine.get_connection = lambda: DummyConn([(300, 2)])
        filtered = self.engine._filter_duplicate_contacts(batch, 'contact_employment')
        self.assertEqual(len(filtered), 2)
        self.assertTrue({'con_id': 300, 'employment_type_enum': 1} in filtered)
        self.assertTrue({'con_id': 301, 'employment_type_enum': 1} in filtered)

class DummyConn:
    def __init__(self, existing):
        self.existing = existing
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    def cursor(self):
        return DummyCursor(self.existing)
class DummyCursor:
    def __init__(self, existing):
        self.existing = existing
    def execute(self, query, params):
        self.query = query
        self.params = params
    def fetchall(self):
        if isinstance(self.existing[0], tuple):
            return self.existing
        return [(x,) for x in self.existing]
