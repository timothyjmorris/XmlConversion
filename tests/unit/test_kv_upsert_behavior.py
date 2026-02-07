import pyodbc

from xml_extractor.database.bulk_insert_strategy import BulkInsertStrategy


class _FakeCursor:
    def __init__(self):
        self.fast_executemany = False
        self.calls = []
        self._insert_calls = 0

    def executemany(self, sql, batch_data):
        # Simulate a duplicate key failure on fast path
        raise pyodbc.Error("[23000] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]Violation of PRIMARY KEY constraint. Cannot insert duplicate key row (2627)")

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

        # First INSERT attempt duplicates; subsequent operations succeed
        if str(sql).lstrip().upper().startswith("INSERT INTO"):
            self._insert_calls += 1
            if self._insert_calls == 1:
                raise pyodbc.Error("Cannot insert duplicate key row in object 'scores'. (2627)")

        return None


def test_scores_duplicate_key_is_upserted_via_update():
    cursor = _FakeCursor()
    strategy = BulkInsertStrategy(batch_size=100)

    # Single record is enough to force fallback path (len <= 1) and exercise update-on-dup
    records = [{"app_id": 279971, "score_identifier": "EX_DIE", "score": 16}]

    applied = strategy.insert(cursor, records, table_name="scores", qualified_table_name="[migration].[scores]")

    assert applied == 1

    # Verify we attempted an UPDATE after the duplicate INSERT
    update_calls = [c for c in cursor.calls if str(c[0]).lstrip().upper().startswith("UPDATE")]
    assert update_calls, "Expected an UPDATE call for duplicate scores row"


def test_report_lookup_duplicate_key_is_upserted_via_update():
    cursor = _FakeCursor()
    strategy = BulkInsertStrategy(batch_size=100)

    # Ensure update logic can handle optional source_report_key
    records = [{"app_id": 279971, "name": "InstantID_Score", "value": "111", "source_report_key": "IDV"}]

    applied = strategy.insert(
        cursor,
        records,
        table_name="app_report_results_lookup",
        qualified_table_name="[migration].[app_report_results_lookup]",
    )

    assert applied == 1

    update_calls = [c for c in cursor.calls if str(c[0]).lstrip().upper().startswith("UPDATE")]
    assert update_calls, "Expected an UPDATE call for duplicate report lookup row"
