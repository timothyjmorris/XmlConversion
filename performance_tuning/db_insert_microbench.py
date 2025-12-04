#!/usr/bin/env python3
import sys
import pathlib
import time
import pyodbc
import os

# Ensure repo root (one level above this file) is on sys.path so
# `from xml_extractor...` works when the script is run from any cwd.
repo_root = pathlib.Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from xml_extractor.config.config_manager import get_config_manager

cfg = get_config_manager()
conn_str = cfg.get_database_connection_string()

# Simple synthetic table - change schema/table as needed for safe testing
table = "dbo.__bench_insert"  
create_sql = f"""
IF OBJECT_ID('{table}', 'U') IS NULL
CREATE TABLE {table} (
  id INT IDENTITY(1,1) PRIMARY KEY,
  v1 VARCHAR(100),
  v2 INT
)
"""
n = 1000  # number of rows to test with; increase if needed

def run_test(fast_flag):
    conn = pyodbc.connect(conn_str, autocommit=False, timeout=30)
    cursor = conn.cursor()
    try:
        # small cleanup / create
        cursor.execute(create_sql)
        conn.commit()

        # prepare data
        rows = [("text-%04d" % i, i) for i in range(n)]
        sql = f"INSERT INTO {table} (v1, v2) VALUES (?, ?)"

        cursor.fast_executemany = fast_flag

        t0 = time.time()
        cursor.executemany(sql, rows)
        conn.commit()
        elapsed = time.time() - t0
        print(f"fast_executemany={fast_flag} elapsed={elapsed:.3f}s")
    finally:
        # cleanup small sample rows so test is repeatable
        try:
            cursor.execute(f"DELETE FROM {table}")
            conn.commit()
        except Exception:
            pass
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("Running microbench with fast_executemany=True")
    run_test(True)
    print("Running microbench with fast_executemany=False")
    run_test(False)