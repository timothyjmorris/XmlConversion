# Network Latency Test to RDS
# Measures connection establishment and query response time

import pyodbc
import time
import statistics

server = "mbc-dev-npci-use1-db.cofvo8gypwe9.us-east-1.rds.amazonaws.com"
database = "MACDEVOperational"

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"Trusted_Connection=yes;"
    f"Connection Timeout=30;"
)

print(f"Testing network latency to: {server}")
print(f"Database: {database}\n")

# Test 1: Connection establishment time
print("=" * 80)
print("TEST 1: Connection Establishment Time")
print("=" * 80)

connection_times = []
for i in range(10):
    start = time.perf_counter()
    try:
        conn = pyodbc.connect(conn_str)
        conn.close()
        elapsed = (time.perf_counter() - start) * 1000  # Convert to milliseconds
        connection_times.append(elapsed)
        print(f"  Attempt {i+1}: {elapsed:.2f} ms")
    except Exception as e:
        print(f"  Attempt {i+1}: FAILED - {e}")

if connection_times:
    print(f"\nConnection Time Statistics:")
    print(f"  Average: {statistics.mean(connection_times):.2f} ms")
    print(f"  Median:  {statistics.median(connection_times):.2f} ms")
    print(f"  Min:     {min(connection_times):.2f} ms")
    print(f"  Max:     {max(connection_times):.2f} ms")
    print(f"  StdDev:  {statistics.stdev(connection_times) if len(connection_times) > 1 else 0:.2f} ms")

# Test 2: Query response time (reusing connection)
print("\n" + "=" * 80)
print("TEST 2: Simple Query Response Time (Single Connection)")
print("=" * 80)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    query_times = []
    for i in range(20):
        start = time.perf_counter()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        elapsed = (time.perf_counter() - start) * 1000
        query_times.append(elapsed)
        print(f"  Query {i+1}: {elapsed:.2f} ms")
    
    conn.close()
    
    print(f"\nQuery Time Statistics:")
    print(f"  Average: {statistics.mean(query_times):.2f} ms")
    print(f"  Median:  {statistics.median(query_times):.2f} ms")
    print(f"  Min:     {min(query_times):.2f} ms")
    print(f"  Max:     {max(query_times):.2f} ms")
    print(f"  StdDev:  {statistics.stdev(query_times):.2f} ms")
    
except Exception as e:
    print(f"Query test failed: {e}")

# Test 3: Query response time (new connection each time)
print("\n" + "=" * 80)
print("TEST 3: Simple Query Response Time (New Connection Each Query)")
print("=" * 80)

query_with_connect_times = []
for i in range(10):
    start = time.perf_counter()
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        elapsed = (time.perf_counter() - start) * 1000
        query_with_connect_times.append(elapsed)
        print(f"  Attempt {i+1}: {elapsed:.2f} ms (connect + query + close)")
    except Exception as e:
        print(f"  Attempt {i+1}: FAILED - {e}")

if query_with_connect_times:
    print(f"\nConnect+Query+Close Time Statistics:")
    print(f"  Average: {statistics.mean(query_with_connect_times):.2f} ms")
    print(f"  Median:  {statistics.median(query_with_connect_times):.2f} ms")
    print(f"  Min:     {min(query_with_connect_times):.2f} ms")
    print(f"  Max:     {max(query_with_connect_times):.2f} ms")
    print(f"  StdDev:  {statistics.stdev(query_with_connect_times) if len(query_with_connect_times) > 1 else 0:.2f} ms")

# Analysis
print("\n" + "=" * 80)
print("ANALYSIS & IMPACT")
print("=" * 80)

if connection_times and query_times:
    avg_connect = statistics.mean(connection_times)
    avg_query = statistics.mean(query_times)
    
    print(f"\nPer-Operation Latency:")
    print(f"  Connection establishment: {avg_connect:.1f} ms")
    print(f"  Simple query (reuse conn): {avg_query:.1f} ms")
    
    print(f"\nImpact with 16 workers processing 2000 apps:")
    
    # Scenario 1: If each worker creates new connection per app
    apps_per_worker = 2000 / 16
    total_connect_time = apps_per_worker * avg_connect / 1000  # Convert to seconds
    print(f"\n  Scenario 1: New connection per app")
    print(f"    Each worker: {apps_per_worker:.0f} apps × {avg_connect:.1f}ms = {total_connect_time:.1f}s wasted on connections")
    print(f"    All 16 workers: {16 * total_connect_time:.1f}s total wasted time")
    
    # Scenario 2: Workers reuse connections but have query latency
    if avg_query > 5:
        # Assume each app does ~50 queries (lookups, inserts, etc.)
        queries_per_app = 50
        total_query_time = apps_per_worker * queries_per_app * avg_query / 1000
        print(f"\n  Scenario 2: Reused connections, {queries_per_app} queries per app")
        print(f"    Each worker: {apps_per_worker:.0f} apps × {queries_per_app} queries × {avg_query:.1f}ms")
        print(f"    Each worker: {total_query_time:.1f}s spent waiting for query responses")
        print(f"    All 16 workers: {16 * total_query_time:.1f}s total wait time")
    
    print(f"\n  Performance Impact:")
    if avg_query > 20:
        print(f"    ⚠️  HIGH LATENCY DETECTED ({avg_query:.1f}ms per query)")
        print(f"    This is a MAJOR contributor to worker idle time")
        print(f"    Workers spend more time waiting for network than processing")
    elif avg_query > 10:
        print(f"    ⚠️  MODERATE LATENCY ({avg_query:.1f}ms per query)")
        print(f"    This is contributing to reduced throughput")
        print(f"    Consider EC2 instance in same VPC/AZ as RDS")
    else:
        print(f"    ✓  Low latency ({avg_query:.1f}ms per query)")
        print(f"    Network is not the primary bottleneck")

print("\n" + "=" * 80)
