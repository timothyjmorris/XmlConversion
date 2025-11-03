# Concurrent Processing Architecture Diagrams

## 1. How Resumability Works (Crash Safety)

```
NORMAL PROCESSING FLOW
═════════════════════════════════════════════════════════════════

   [dbo].[app_xml]                    [sandbox].[processing_log]
   ┌─────────────────┐               ┌──────────────────────────┐
   │ app_id | xml    │               │ app_id | status | reason │
   ├─────────────────┤               ├──────────────────────────┤
   │ 10  │ <xml1>    │               │                          │
   │ 20  │ <xml2>    │               │                          │
   │ 30  │ <xml3>    │               │                          │
   │ 40  │ <xml4>    │               │                          │
   └─────────────────┘               └──────────────────────────┘

STEP 1: get_xml_records() QUERY
───────────────────────────────
SELECT app_id, xml FROM [dbo].[app_xml]
WHERE NOT EXISTS (
    SELECT 1 FROM [sandbox].[processing_log]
    WHERE app_id = ax.app_id
)
RESULT: [10, 20, 30, 40] ✓ (no entries in processing_log)

STEP 2: ParallelCoordinator processes [10, 20, 30, 40]
─────────────────────────────────────────────────────
Worker1: app_id=10 → Parse → Map → Insert [sandbox].[app_base,contact_*] → Result: ✓ success
Worker2: app_id=20 → Parse → Map → Insert [sandbox].[app_base,contact_*] → Result: ✓ success
Worker3: app_id=30 → Parse → Map → Insert [sandbox].[app_base,contact_*] → Result: ✓ success
Worker4: app_id=40 → Parse → Map → Insert [sandbox].[app_base,contact_*] → Result: ✓ success

STEP 3: _log_processing_result() for each app [IMMEDIATELY]
──────────────────────────────────────────────────────────
INSERT INTO [sandbox].[processing_log] (app_id, status) VALUES (10, 'success')
INSERT INTO [sandbox].[processing_log] (app_id, status) VALUES (20, 'success')
INSERT INTO [sandbox].[processing_log] (app_id, status) VALUES (30, 'success')
INSERT INTO [sandbox].[processing_log] (app_id, status) VALUES (40, 'success')

   [sandbox].[processing_log] NOW CONTAINS
   ┌──────────────────────────┐
   │ app_id | status          │
   ├──────────────────────────┤
   │ 10     | 'success'      │
   │ 20     | 'success'      │
   │ 30     | 'success'      │
   │ 40     | 'success'      │
   └──────────────────────────┘

STEP 4: Next iteration
──────────────────────
get_xml_records() runs again:
SELECT app_id, xml FROM [dbo].[app_xml]
WHERE NOT EXISTS (
    SELECT 1 FROM [sandbox].[processing_log]
    WHERE app_id = ax.app_id
)
RESULT: [50, 60, 70, ...] ✓ (10,20,30,40 filtered out by processing_log check)


CRASH SCENARIO
═════════════════════════════════════════════════════════════════

CRASH AFTER INSERT, BEFORE LOGGING
───────────────────────────────────

   Worker1: app_id=10 → Parse → Map → Insert ✓ → [CRASH!]
                                        ↑
                                  Data committed to DB
                              But NO processing_log entry yet

   [sandbox].[app_base] HAS data from app_id=10
   [sandbox].[processing_log] DOES NOT have entry for app_id=10

Next Run:
─────────
get_xml_records() finds app_id=10 again (no processing_log entry)

Worker attempts to INSERT app_id=10 data again
    ├─ PRIMARY KEY constraint triggers (duplicate contact_id)
    ├─ MigrationEngine catches error
    ├─ Calls _log_processing_result(app_id=10, success=False, reason="PK violation")
    └─ INSERT INTO processing_log (10, 'failed', 'PK violation')

Next iteration:
    get_xml_records() finds app_id=10 in processing_log with status='failed'
    ├─ Filters it OUT (processing_log entry exists with 'failed' status)
    └─ Does NOT re-process

RESULT: ✅ SAFE - Duplicate blocked by DB constraints, now in processing_log


MULTI-INSTANCE SCENARIO (3 processors running simultaneously)
═════════════════════════════════════════════════════════════

T=0:00
Instance1: SELECT app_id FROM [dbo].[app_xml]
           WHERE NOT EXISTS (processing_log entry)
           ↓ RETURNS: [10, 20, 30, 40, 50, ...]

Instance2: SELECT app_id FROM [dbo].[app_xml]
           WHERE NOT EXISTS (processing_log entry)
           ↓ RETURNS: [10, 20, 30, 40, 50, ...] (same list, slightly race)

Instance3: SELECT app_id FROM [dbo].[app_xml]
           WHERE NOT EXISTS (processing_log entry)
           ↓ RETURNS: [10, 20, 30, 40, 50, ...] (same list)

T=0:10 (10 seconds later)
Instance1: Processes [10, 20, 30]
           ├─ INSERT processing_log (10, 'success')
           ├─ INSERT processing_log (20, 'success')
           └─ INSERT processing_log (30, 'success')

Instance2: Processes [10, 20, 40]
           ├─ INSERT processing_log (10, 'success') ← PK CONFLICT! (10 already inserted by Instance1)
           │  └─ Caught by constraint → Skip or retry
           ├─ INSERT processing_log (20, 'success') ← PK CONFLICT! (already by Instance1)
           │  └─ Caught by constraint → Skip or retry
           └─ INSERT processing_log (40, 'success') ← OK

Instance3: Processes [30, 50, 60]
           ├─ INSERT processing_log (30, 'success') ← PK CONFLICT! (by Instance1)
           ├─ INSERT processing_log (50, 'success') ← OK
           └─ INSERT processing_log (60, 'success') ← OK

T=0:15
Instance1: Calls get_xml_records() again
           ↓ RETURNS: [40, 50, 60, 70, ...] (10,20,30 filtered out now)

Instance2: Calls get_xml_records() again
           ↓ RETURNS: [40, 50, 60, 70, ...] (same)

Instance3: Calls get_xml_records() again
           ↓ RETURNS: [70, 80, 90, ...] (already processed others)

RESULT: ✅ SAFE - PK conflicts in processing_log are handled gracefully
        ⚠️  INEFFICIENT - Some duplicate attempts (collision inevitable with 3 instances)
        ✅ RECOVERABLE - Crashed instance doesn't interfere with others


SOLUTION: Use Partition-Based Coordination (Option 2)
═════════════════════════════════════════════════════

Instance 0: Process only WHERE (app_id % 3) == 0
            ├─ Returns: [3, 6, 9, 12, 15, 18, 21, ...]
            └─ ONLY processes these app_ids

Instance 1: Process only WHERE (app_id % 3) == 1
            ├─ Returns: [1, 4, 7, 10, 13, 16, 19, ...]
            └─ ONLY processes these app_ids

Instance 2: Process only WHERE (app_id % 3) == 2
            ├─ Returns: [2, 5, 8, 11, 14, 17, 20, ...]
            └─ ONLY processes these app_ids

RESULT: ✅ ZERO duplicate attempts across instances
        ✅ Perfect load balancing (if work evenly distributed)
        ✅ Same resumability mechanism still works
```

---

## 2. Concurrent Processing: 3 Instances Competing for CPU

```
SINGLE PROCESSOR (Current)
═══════════════════════════════════════════════════════════════

CPU (4 cores)
┌─────────────────────────────────────────┐
│ ProductionProcessor instance 1          │
│ ├─ Worker 1 (XML parsing & mapping)    │  4 parallel
│ ├─ Worker 2 (XML parsing & mapping)    │  workers = 
│ ├─ Worker 3 (XML parsing & mapping)    │  4x speedup
│ └─ Worker 4 (XML parsing & mapping)    │
└─────────────────────────────────────────┘

Throughput: 100 apps/min (example)


3 PROCESSORS UNCOORDINATED (Option 1)
═════════════════════════════════════════════════════════════════

CPU (4 cores) - OVERSUBSCRIBED
┌─────────────────────────────────────────────────────────────────┐
│ Instance 1    │ Instance 2    │ Instance 3    │ (Context switching)
│ ├─ W1  ├─ W2  │ ├─ W1  ├─ W2  │ ├─ W1  ├─ W2  │ ↓ wasted CPU
│ ├─ W3  ├─ W4  │ ├─ W3  ├─ W4  │ └─ W1         │
└─────────────────────────────────────────────────────────────────┘
       12 workers fighting for 4 CPU cores

Context Switching Overhead: ~20-30% wasted on context switches
Effective Speedup: ~2-2.5x (instead of 3x)
Expected Throughput: 200-250 apps/min

Pros:
  + Simple (just run 3 terminals)
  + Natural resumability
  + Automatic load balancing (fast instance picks up more work)

Cons:
  - Context switching waste
  - Occasional duplicate attempts (PK conflicts in processing_log)
  - OS scheduler makes no guarantees about parallelism


3 PROCESSORS WITH PARTITIONING (Option 2)
═════════════════════════════════════════════════════════════════

CPU (4 cores) - BALANCED
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Instance 1     │ │ Instance 2     │ │ Instance 3     │
│ WHERE app_id   │ │ WHERE app_id   │ │ WHERE app_id   │
│ % 3 == 0       │ │ % 3 == 1       │ │ % 3 == 2       │
│                │ │                │ │                │
│ ├─ W1    ├─ W2 │ │ ├─ W1    ├─ W2 │ │ ├─ W1    ├─ W2 │ 
│ ├─ W3    ├─ W4 │ │ ├─ W3    ├─ W4 │ │ ├─ W3    └─ W4 │
│ [4 workers]    │ │ [4 workers]    │ │ [4 workers]    │
└────────────────┘ └────────────────┘ └────────────────┘
      ↓                   ↓                    ↓
  [3, 6, 9, ...]    [1, 4, 7, ...]     [2, 5, 8, ...]
  (no collision)     (no collision)     (no collision)

Pros:
  ✓ Zero context switching waste (each instance is independent process)
  ✓ Zero duplicate attempts (different partitions)
  ✓ Each instance can use full 4 workers efficiently
  ✓ Load balanced (if apps evenly distributed by app_id)

Cons:
  - Small code change needed (~20 lines)
  - Uneven distribution if app_ids clustered (e.g., recent apps all odd)
  - Requires knowing instance count upfront


COMPARISON TABLE
═════════════════════════════════════════════════════════════════

                     Single Proc  Option 1      Option 2
                                 (3x Uncoord)  (3x Partitioned)
─────────────────────────────────────────────────────────────────
CPU Cores Used       4            4 (actual)    ~6-8 (effective)
Workers Per Inst     4            4             4
Total Workers        4            12            12

Context Switch       None         High (~20%)   None
Overhead

Expected Speedup     1x           2-2.5x        2.8-3x
vs Single

Duplicate            No           Rare (PK)     Zero
Attempts

Code Changes         -            0 lines       ~20 lines

Setup Complexity     Low          Very Low      Low

Production Ready     Yes          Yes           Better

Recommended For      Dev/Test     Initial       Production
                                  Testing       Runs
```

---

## 3. Processing Pipeline with Schema Isolation

```
XML SOURCE (always [dbo])
═════════════════════════════════════════════════════════════════

[dbo].[app_xml] table
┌──────────────────────────────────────────┐
│ app_id | session_id | xml                │
├──────────────────────────────────────────┤
│ 1      | NULL       | <application>...   │
│ 2      | NULL       | <application>...   │
│ 3      | NULL       | <application>...   │
└──────────────────────────────────────────┘
         ↑
    Source data
  (read-only, never modified)


TARGET DATA (uses target_schema from contract)
═════════════════════════════════════════════════════════════════

MappingContract.target_schema = "sandbox"

[sandbox].[app_base]
┌──────────────────────────────────────────┐
│ app_id | app_status | created_date | ... │
├──────────────────────────────────────────┤
│ 1      | 'A'        | 2024-01-01   | ... │
│ 2      | 'A'        | 2024-01-02   | ... │
│ 3      | 'I'        | 2024-01-03   | ... │
└──────────────────────────────────────────┘

[sandbox].[contact_base]
[sandbox].[contact_address]
[sandbox].[contact_employment]
...other target tables...


PROCESSING LOG (tracks what was processed)
═════════════════════════════════════════════════════════════════

[sandbox].[processing_log]
┌──────────────────────────────────────────────────────┐
│ app_id | status      | failure_reason | session_id   │
├──────────────────────────────────────────────────────┤
│ 1      | 'success'   | NULL           | '20251101_*' │
│ 2      | 'success'   | NULL           | '20251101_*' │
│ 3      | 'failed'    | 'XML parse...' | '20251101_*' │
│ 4      | 'success'   | NULL           | '20251101_*' │
└──────────────────────────────────────────────────────┘
         ↑
    Resumability anchor
  (tracks which apps already processed)


MULTI-INSTANCE COORDINATION
═════════════════════════════════════════════════════════════════

Instance 1: session_id='20251101_143022'    Instance 2: session_id='20251101_143025'
    ↓                                             ↓
[dbo].[app_xml] ← read (no lock needed)  [dbo].[app_xml] ← read (no lock)
    ↓ SELECT WHERE NOT IN processing_log          ↓
    ├─ Gets [1, 2, 3, 4, ...]                    ├─ Gets [1, 2, 3, 4, ...] 
    ↓                                             ↓
   Process [1, 2] atomically             Process [1, 3] atomically
    ├─ INSERT [sandbox].[app_base] for 1         ├─ INSERT [sandbox].[app_base] for 1
    ├─ INSERT [sandbox].[contact_*] for 1        ├─ INSERT [sandbox].[contact_*] for 1
    ├─ INSERT [sandbox].[app_base] for 2         ├─ INSERT [sandbox].[app_base] for 3
    ├─ INSERT [sandbox].[contact_*] for 2        └─ INSERT [sandbox].[contact_*] for 3
    ↓                                             ↓
   Log: INSERT processing_log (1, 'success')  Log: INSERT processing_log (1, 'success')
   Log: INSERT processing_log (2, 'success')       ↑ PK conflict (1 already inserted by Instance1)
                                                    └─ Handled gracefully (skipped or error)
                                            Log: INSERT processing_log (3, 'success')

Result:
  [sandbox].[app_base] has: app_id 1,2,3 with correct data
  [sandbox].[processing_log] has: app_id 1,2,3 with session_ids tracking
  Next iteration: get_xml_records() returns only app_id 4+ (1,2,3 filtered by processing_log)


CRASH RECOVERY
═════════════════════════════════════════════════════════════════

If Instance 1 crashes during processing of app_id 5:
  ├─ app_id 5 data inserted to [sandbox].[app_base,contact_*]
  ├─ processing_log entry for app_id 5 NOT created yet
  ├─ Instance 1 terminates

When Instance 1 (or any instance) restarts:
  ├─ get_xml_records() finds app_id 5 (no processing_log entry)
  ├─ Attempts to re-process app_id 5
  ├─ PRIMARY KEY constraint on [sandbox].[contact_base] triggers
  ├─ Error caught, logged as status='failed' in processing_log
  └─ Next iteration: app_id 5 filtered out (has processing_log entry)

Result: ✅ No data loss, no duplicates (DB constraints + processing_log)
```

---

## 4. Decision Tree: Which Option to Use?

```
START
  │
  └─→ Are you in DEVELOPMENT/TESTING?
      ├─ YES → Use Option 1 (Uncoordinated)
      │        "Just run 3 terminals, simple and works"
      │
      └─ NO → Are you expecting frequent crashes?
              ├─ YES → Use Option 2 (Partitioned)
              │        "Guaranteed zero collisions + resumability"
              │
              └─ NO → Use Option 1 initially
                      "Monitor for PK collisions in processing_log"
                      "Upgrade to Option 2 if collisions become problem"
```

---

## 5. Quick Reference: Throughput Expectations

```
BASELINE (Single ProductionProcessor, 4 workers)
CPU bound (XML parsing/mapping)
DB: SQLExpress, local network
Typical Throughput: 50-150 apps/min

Sample Timings:
  Small XML (5 contacts):  0.5 sec per app
  Medium XML (20 contacts): 2.0 sec per app
  Large XML (100 contacts): 10+ sec per app

Parallelism (4 workers):
  4 small XMLs processed in parallel: ~2 sec total (vs 2 sec serial = 2x speedup)
  4 medium XMLs: ~8 sec total (vs 8 sec serial = 1x, limited by largest)
  4 large XMLs: ~40+ sec total (very CPU bound)

WITH 3 PROCESSORS
─────────────────

Uncoordinated (Option 1):
  ├─ 12 workers competing
  ├─ Context switch overhead ~20-30%
  └─ Expected: 2-2.5x speedup = 100-375 apps/min

Partitioned (Option 2):
  ├─ 12 workers, no collision
  ├─ Zero context switch overhead
  ├─ Load balanced (no idle waiting)
  └─ Expected: 2.8-3x speedup = 140-450 apps/min

Actual Speedup Depends On:
  ├─ XML complexity distribution
  ├─ CPU core utilization pattern
  ├─ Database I/O (usually negligible with partitioning)
  └─ OS process scheduling efficiency
```
