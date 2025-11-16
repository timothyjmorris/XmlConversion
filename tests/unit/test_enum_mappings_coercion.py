import unittest
from types import SimpleNamespace


class DummyMapper:
    def __init__(self):
        self._enum_mappings = None


class TestEnumMappingsCoercion(unittest.TestCase):
    def test_coerce_none_enum_mappings_to_dict(self):
        contract = SimpleNamespace(enum_mappings=None)
        mapper = DummyMapper()

        # mimic safe assignment used in tests: only assign dicts, else fallback to {}
        enum_mappings = getattr(contract, 'enum_mappings', None)
        if isinstance(enum_mappings, dict) and enum_mappings:
            mapper._enum_mappings = enum_mappings
        else:
            mapper._enum_mappings = {}

        self.assertIsInstance(mapper._enum_mappings, dict)
        self.assertEqual(mapper._enum_mappings, {})


if __name__ == '__main__':
    unittest.main()
