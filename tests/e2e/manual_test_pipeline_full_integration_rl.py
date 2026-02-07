#!/usr/bin/env python3
"""Manual end-to-end-ish DB validation for RecLending work.

Purpose
- Practical, repeatable proof that key/value tables (scores/indicators/history/report lookups)
  handle duplicates gracefully by updating existing rows ("upsert on duplicate")

Notes
- This is intentionally NOT part of automated pytest runs.
- Per repo policy, this test does not DELETE from the database.
- It operates on a single app_id (default 443306) that is expected to already exist in
  the target schema (from any prior CC manual pipeline run).

How to run
- `C:/Users/tmorris/Repos_local/XmlConversion/.venv/Scripts/python.exe tests/e2e/manual_test_pipeline_full_integration_rl.py`

Optional env vars
- `XMLCONVERSION_E2E_APP_ID` : app_id to use (default 443306)
"""

import os
import sys
import json
import unittest
import logging

from pathlib import Path

# Ensure repo root is importable before importing xml_extractor
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pyodbc

from xml_extractor.config.config_manager import get_config_manager
from xml_extractor.database.migration_engine import MigrationEngine


class TestRecLendingUpsertBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_manager = get_config_manager()
        cls.connection_string = config_manager.get_database_connection_string()

        mapping_contract_path = PROJECT_ROOT / "config" / "mapping_contract.json"
        try:
            with open(mapping_contract_path, "r", encoding="utf-8") as f:
                contract = json.load(f)
                cls.target_schema = contract.get("target_schema", "dbo") or "dbo"
        except Exception:
            cls.target_schema = "dbo"

        cls.migration_engine = MigrationEngine(cls.connection_string)

        def _qualify_table(table_name: str) -> str:
            return f"[{cls.target_schema}].[{table_name}]"

        cls._qualify_table = staticmethod(_qualify_table)

    def setUp(self):
        logging.basicConfig(level=logging.INFO)

    def _app_exists(self, app_id: int) -> bool:
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self._qualify_table('app_base')} WHERE app_id = ?", app_id)
            return int(cursor.fetchone()[0]) > 0

    def _get_score_value(self, app_id: int, score_identifier: str):
        with pyodbc.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT score FROM {self._qualify_table('scores')} WHERE app_id = ? AND score_identifier = ?",
                app_id,
                score_identifier,
            )
            row = cursor.fetchone()
            return None if row is None else row[0]

    def test_scores_insert_then_update(self):
        """First write creates the score row; second write updates it."""
        app_id = int(os.environ.get("XMLCONVERSION_E2E_APP_ID", "443306"))
        if not self._app_exists(app_id):
            self.skipTest(
                f"app_id {app_id} not found in {self._qualify_table('app_base')}; "
                "run the CC manual pipeline once, or set XMLCONVERSION_E2E_APP_ID to an existing app_id"
            )

        score_identifier = "E2E_UPSERT_TEST"

        print("\n" + "=" * 80)
        print("TESTING SCORES UPSERT (INSERT THEN UPDATE)")
        print("=" * 80)
        print(f"Target: app_id={app_id}, score_identifier='{score_identifier}'")

        insert_records = [{"app_id": app_id, "score_identifier": score_identifier, "score": 1}]
        applied_1 = self.migration_engine.execute_bulk_insert(insert_records, "scores")
        print(f"[OK] Applied {applied_1} record(s) to scores")

        value_after_1 = self._get_score_value(app_id, score_identifier)
        self.assertEqual(value_after_1, 1, f"Expected score to be 1 after first apply, got {value_after_1!r}")

        update_records = [{"app_id": app_id, "score_identifier": score_identifier, "score": 2}]
        applied_2 = self.migration_engine.execute_bulk_insert(update_records, "scores")
        print(f"[OK] Applied {applied_2} record(s) to scores (duplicate key should update)")

        value_after_2 = self._get_score_value(app_id, score_identifier)
        self.assertEqual(value_after_2, 2, f"Expected score to be updated to 2, got {value_after_2!r}")


def run_tests() -> bool:
    logging.basicConfig(level=logging.INFO)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRecLendingUpsertBehavior)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
