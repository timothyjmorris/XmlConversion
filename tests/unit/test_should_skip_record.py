
import unittest
import sys
import os
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
from xml_extractor.mapping.data_mapper import DataMapper

class TestShouldSkipRecord(unittest.TestCase):
    def setUp(self):
        self.mapper = DataMapper()

    def test_keep_app_base_only_app_id(self):
        # Only app_id, no meaningful data, no defaults
        record = {'app_id': 500000}
        applied_defaults = set()
        should_skip = self.mapper._should_skip_record(record, 'app_base', applied_defaults)
        self.assertFalse(should_skip, "Should NOT skip app_base with only app_id (special case)")

    def test_keep_app_base_with_defaults(self):
        # app_id and a default value
        record = {'app_id': 500001, 'some_column': 'default_value'}
        applied_defaults = {'some_column'}
        should_skip = self.mapper._should_skip_record(record, 'app_base', applied_defaults)
        self.assertFalse(should_skip, "Should NOT skip app_base with app_id and applied defaults (special case)")

    def test_keep_app_base_with_meaningful_data(self):
        # app_id and a real value
        record = {'app_id': 500002, 'real_column': 'real_value'}
        applied_defaults = set()
        should_skip = self.mapper._should_skip_record(record, 'app_base', applied_defaults)
        self.assertFalse(should_skip, "Should NOT skip app_base with meaningful data (special case)")

    def test_keep_app_base_keys_and_defaults_only(self):
        # Only app_id and defaults, no meaningful data
        record = {'app_id': 500003, 'default_col': 'default_value'}
        applied_defaults = {'default_col'}
        should_skip = self.mapper._should_skip_record(record, 'app_base', applied_defaults)
        self.assertFalse(should_skip, "Should NOT skip app_base with only keys and defaults (special case)")

if __name__ == '__main__':
    unittest.main()
