---
name: system-constraints
description: Non-negotiable architectural principles that protect data integrity in the XML Database Extraction System. Defines contract-driven architecture, schema isolation, atomic transactions, FK ordering, Windows-first requirements, and known gotchas to avoid. Use when reviewing code, making architecture decisions, or preventing bugs.
metadata:
  last-updated: "2026-02-14"
  project: xml-database-extraction
---

# System Constraints & Non-Negotiable Principles

---

## 1. Non-Negotiable Design Principles

### 1.1 Contract-Driven Architecture
**Constraint:** All data transformations are defined in `config/mapping_contract.json`, NOT in code.

**Why This Matters:**
- Enables config-driven variations per product line
- Separates domain logic from transformation logic
- Allows operational changes without code deployment
- Makes contracts self-documenting

**What This Means:**
- ❌ NEVER hardcode field mappings in DataMapper
- ❌ NEVER create conditional code for "special cases" (use contract enum_mappings instead)
- ✅ Always extend mapping_contract.json for new fields/rules
- ✅ Use DataMapper.apply_calculated_fields() for complex logic tied to the contract
- ✅ Each product line uses its own contract file (`mapping_contract.json` for CC, `mapping_contract_rl.json` for RL)
- ✅ `MigrationEngine` must receive `mapping_contract_path` to derive schema metadata from the correct contract

**Example - WRONG:**
```python
# DON'T DO THIS
if source == "type_A":
    mapped_value = transform_a(value)
elif source == "type_B":
    mapped_value = transform_b(value)
```

**Example - RIGHT:**
```python
# Do this instead - define in contract
"enum_mappings": {
    "type_A": "mapped_a",
    "type_B": "mapped_b"
}
# DataMapper applies it automatically
```

---

### 1.2 Schema Isolation Pattern
**Constraint:** All database operations respect `target_schema` from the mapping contract.

**Why This Matters:**
- Enables sandbox/dbo/product-prod schema isolation
- Allows parallel development (different teams on different schemas)
- Provides safe testing without production data
- Supports isolated testing (different schemas for different product lines)

**What This Means:**
- ❌ NEVER hardcode schema names in code (e.g., `[dbo].table_name`)
- ❌ NEVER use `sys.tables` to discover schemas dynamically
- ❌ NEVER execute DDL (CREATE SCHEMA, DROP SCHEMA) in application code
- ❌ NEVER call `MigrationEngine()` without `mapping_contract_path` for non-default product lines
- ✅ Always read target_schema from contract config
- ✅ Pass schema through database operations (MigrationEngine, Validator)
- ✅ Manage schemas outside application (by you, via SQL scripts or operations)
- ✅ Pass `mapping_contract_path` to `MigrationEngine` (it derives schema metadata from the contract)

**Example - WRONG:**
```python
query = f"SELECT * FROM [dbo].[app_base]"  # Hardcoded!
cursor.execute("DROP SCHEMA [test_schema]")  # Never in app code!
```

**Example - RIGHT:**
```python
query = f"SELECT * FROM [{target_schema}].[app_base]"
# target_schema comes from mapping_contract.json
```

---

### 1.3 Atomic Transaction Guarantee
**Constraint:** Every application record must succeed or fail as a complete unit (all-or-nothing).

**Why This Matters:**
- Prevents orphaned records (child without parent)
- Enables safe resume capability (retry without duplicates)
- Guarantees consistency on crashes
- Makes debugging deterministic

**What This Means:**
- ❌ NEVER insert one table at a time across connections
- ❌ NEVER commit after each table (violates atomicity)
- ✅ Use MigrationEngine which handles atomicity
- ✅ All tables for one app_id share one transaction

**Example - WRONG:**
```python
# DON'T DO THIS
insert_app_base(app_data)  # Connection A, auto-commit
conn.commit()  # First commit
insert_contact_base(app_data)  # Connection B, if this fails, app_base orphaned
```

**Example - RIGHT:**
```python
# MigrationEngine does this
with engine.get_connection(app_id) as conn:
    insert_app_base(app_data, conn)
    insert_contact_base(app_data, conn)
    insert_contact_address(app_data, conn)
    insert_processing_log(app_data, conn)
    conn.commit()  # All succeed or all fail
```

---

### 1.4 Foreign Key Ordering Strategy
**Constraint:** Tables must be inserted in FK dependency order (documented in architecture-project-blueprint.mdoject-blueprint.md).

**Required Order:**
```
1. app_base                    (root, no parents)
2. contact_base                (parent of contact_*, child of app_base)
3. app_operational_cc          (child of app_base)
4. app_pricing_cc              (child of app_base)
5. app_transactional_cc        (child of app_base)
6. app_solicited_cc            (child of app_base)
7. contact_address             (child of contact_base)
8. contact_employment          (child of contact_base)
9. processing_log              (audit, child of app_base)
```

**Why This Matters:**
- Parent rows must exist before child rows
- Prevents "Violation of PRIMARY KEY constraint" errors
- Makes transaction rollback deterministic
- Enables resume without duplicate constraints

**What This Means:**
- ❌ NEVER change insert order without updating FK dependencies in contract
- ✅ Document FK dependencies in mapping_contract.json under "foreign_keys"
- ✅ Use MigrationEngine which respects this order
- ✅ Test new tables in isolation with correct FK ordering

---

## 2. Windows-First Environment Requirements

### 2.1 Shell & Filesystem
**Constraint:** Always use PowerShell, never bash or Linux paths.

**What This Means:**
- ❌ NEVER use bash-isms: `/path/to/file`, `&&`, `|`, `$()` constructs
- ✅ Use PowerShell: `Join-Path`, semicolons `;`, pipe `|`, `@()` arrays
- ✅ Use Windows paths: `C:\path\to\file` or `Path.Combine()`

**Example:**
```python
# WRONG - bash style
import subprocess
subprocess.run("ls -la /path/to/file && echo done")

# RIGHT - PowerShell
import subprocess
result = subprocess.run(["powershell", "-Command", 
    "Get-ChildItem C:\\path\\to\\file; 'done'"])
```

---

### 2.2 Database Connectivity
**Constraint:** Use pyodbc with Windows Authentication, never SQLAlchemy.

**Why This Matters:**
- pyodbc has native Windows Auth support (no username/password required)
- SQLAlchemy adds abstraction layer (performance penalty for this throughput)
- Simpler connection pooling management
- Works offline with integrated security

**What This Means:**
- ❌ NEVER use SQLAlchemy ORM
- ❌ NEVER use pandas.read_sql (unless for analysis, not production)
- ✅ Use pyodbc directly for all CRUD operations
- ✅ Use `connection_string = f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};Trusted_Connection=yes;"`

---

## 3. Untouchable Code Patterns

### 3.1 Processing Log Resume Logic
**Constraint:** Processing must exclude BOTH `status='success'` AND `status='failed'` records.

**Current Implementation:**
```sql
-- CORRECT resume query
SELECT app_id FROM processing_log 
WHERE target_table = 'app_base' 
  AND status NOT IN ('success', 'failed')
ORDER BY app_id ASC
```

**Why This Matters:**
- Failed records must be retried (user may fix source data)
- Successful records must be skipped (prevent duplicates)
- Partial success (one table failed) must not reprocess entire app

**What This Means:**
- ❌ NEVER change resume logic without understanding atomicity implications
- ✅ Test resume with intentional failures (delete one table, retry app_id)
- ✅ Verify processing_log shows correct final status

---

### 3.2 Cursor-Based Pagination
**Constraint:** Use cursor-based pagination (app_id > last_app_id), never OFFSET.

**Current Implementation:**
```sql
-- CORRECT cursor-based pagination
SELECT TOP @batch_size app_id, xml_content 
FROM [dbo].[app_xml]
WHERE app_id > @last_app_id
ORDER BY app_id ASC
```

**Why This Matters:**
- OFFSET is O(n) - performance degrades with dataset size
- Cursor-based is O(1) - consistent regardless of dataset size
- Prevents "missing records" between chunks

**What This Means:**
- ❌ NEVER use `OFFSET @skip ROWS FETCH NEXT @batch_size`
- ✅ Always use `app_id > @last_app_id`
- ✅ Track last_app_id between batches

---

### 3.3 Lock Contention Prevention
**Constraint:** All duplicate detection queries use `WITH (NOLOCK)` hint.

**Why This Matters:**
- Default READ locks cause RangeS-U (range shared-update) lock serialization
- Causes lock timeouts on high-concurrency runs
- WITH (NOLOCK) allows dirty reads (acceptable for duplicate detection)

**Current Implementation:**
```sql
-- CORRECT with lock hint
SELECT COUNT(*) FROM [sandbox].[app_base] WITH (NOLOCK)
WHERE app_id = @app_id
```

**What This Means:**
- ❌ NEVER remove WITH (NOLOCK) from duplicate detection
- ✅ Apply WITH (NOLOCK) to all SELECT statements in validation layer
- ✅ Monitor lock_wait_time_ms in metrics if timeouts occur

---

### 3.4 Three-Layer Validation
**Constraint:** Validation must occur in three distinct layers.

**Layers:**
```
Layer 1: Pre-Processing Validation
├── XML structure valid (well-formed)
├── Required elements present
└── XPath expressions match expected cardinality

Layer 2: Data Mapping Validation  
├── All contract-required fields extractable
├── Type conversions succeed (string→int, etc.)
├── Enum values mapped (or excluded if missing)
└── Calculated fields compute without errors

Layer 3: Database Constraint Validation
├── FK dependencies satisfied
├── Unique constraints not violated
├── NOT NULL columns have values
└── Domain constraints (e.g., date ranges) satisfied
```

**What This Means:**
- ❌ NEVER skip a layer (each catches different errors)
- ✅ Create custom validation rules using three-layer pattern
- ✅ Report which layer failed (helps debugging)

---

## 4. Known Gotchas (Do Not Reintroduce)

### Gotcha 1: Lock Contention on Duplicate Detection (FIXED)
**What Was Wrong:**
- Default READ locks caused RangeS-U lock serialization
- High-concurrency runs (8+ workers) experienced lock timeouts
- Duplicate detection queries blocked each other

**How It Was Fixed:**
- Added `WITH (NOLOCK)` to all duplicate detection queries
- Allows dirty reads (acceptable since we're just checking existence)
- No blocking between parallel workers

**Prevention:**
- ✅ Apply WITH (NOLOCK) to validation SELECT queries
- ✅ Monitor lock_wait_time_ms in metrics
- ❌ NEVER remove NOLOCK "for safety" (dirty reads are fine for this use case)

---

### Gotcha 2: Resume Logic Including 'Failed' Status (FIXED)
**What Was Wrong:**
- Resume query only excluded `status='success'`
- Failed records were reprocessed on retry, causing duplicates
- If first attempt had 50% failure rate, second attempt created 50% duplicates

**How It Was Fixed:**
- Changed resume logic to exclude BOTH success and failed
- Failed records remain for manual investigation
- Partial success (one table failed) correctly retried entire app

**Prevention:**
- ✅ Test resume logic with intentional failures
- ✅ Verify processing_log shows both success and failed
- ❌ NEVER reprocess records with status='failed'

---

### Gotcha 3: OFFSET-Based Pagination (FIXED)
**What Was Wrong:**
- Large app_id ranges with OFFSET skipped records between chunks
- OFFSET performance degraded with dataset size
- Resume capability unreliable with OFFSET

**How It Was Fixed:**
- Switched to cursor-based pagination (app_id > last_app_id)
- Consistent O(1) performance regardless of dataset size
- No skipped records between chunks

**Prevention:**
- ✅ Use cursor-based pagination (app_id > @last_app_id)
- ❌ NEVER use OFFSET for large datasets
- ✅ Document pagination strategy in code comments

---

### Gotcha 4: Enum Mappings Returning None (EXPECTED BEHAVIOR)
**What Happens:**
- Contract specifies enum mappings
- If source value doesn't match any mapping, DataMapper returns None
- Column is excluded from INSERT (doesn't inject NULL)

**Why This Is Correct:**
- Missing enum value indicates data quality issue
- Better to skip column than inject wrong value
- processing_log captures which fields were excluded

**Prevention:**
- ✅ Test enum mappings with boundary values
- ✅ Check processing_log for excluded columns
- ❌ NEVER fabricate enum values as fallback
- ✅ Add missing mappings to contract if needed

---

### Gotcha 5: Memory Degradation in Long Runs (FIXED)
**What Was Wrong:**
- Single process run on 300k+ records caused memory pressure
- GC pauses increased, throughput degraded over time
- Eventually caused crashes or swap thrashing

**How It Was Fixed:**
- Created chunked orchestrator (run_production_processor.py)
- Spawns fresh process per chunk (garbage collection per process)
- Enables 1M+ record runs without memory issues

**Prevention:**
- ✅ Use run_production_processor.py for >100k records
- ✅ Use production_processor.py for <100k records
- ✅ Monitor memory usage over 1-hour runs
- ❌ NEVER run single process on 500k+ records

---

### Gotcha 6: Contract `target_table` Mismatch for Scores (FIXED Feb 2026)
**What Was Wrong:**
- RL contract (`mapping_contract_rl.json`) had V4P/V4S score mappings with `target_table: "app_historical_lookup"` instead of `"scores"`
- Vantage 4 scores were silently dropped because they mapped to the wrong table
- Other score types (e.g., V3P/V3S, KV-based) worked because their `target_table` was correct

**How It Was Fixed:**
- Changed `target_table` from `"app_historical_lookup"` to `"scores"` for V4P and V4S mappings in the RL contract
- All 96 V4P scores across 791 apps now correctly appear in the scores table

**Prevention:**
- ✅ Validate all `target_table` values in contract against actual database table names
- ✅ Run source-first reconciliation (`validate_source_to_dest_rl.py`) after contract changes
- ❌ NEVER assume a mapping is correct without verifying data appears in the target table

---

### Gotcha 7: MigrationEngine Default Contract Routing (FIXED Feb 2026)
**What Was Wrong:**
- `MigrationEngine.__init__()` called `config_manager.load_mapping_contract()` without a path
- This always loaded the default CC contract (`mapping_contract.json`), ignoring the RL contract
- Schema metadata (column names, types, source table) was derived from the wrong contract
- RL processing silently used CC column definitions, causing subtle data mismatches

**How It Was Fixed:**
- Added `mapping_contract_path` parameter to `MigrationEngine.__init__()`
- Passed through from `production_processor.py` and `parallel_coordinator.py`
- `MigrationEngine` now loads the correct contract for schema introspection

**Prevention:**
- ✅ Always pass `mapping_contract_path` when creating `MigrationEngine` for non-CC product lines
- ✅ Test with both CC and RL contracts to verify correct routing
- ❌ NEVER rely on default contract loading when processing non-default product lines

---

## 5. Code Review Checklist

**When reviewing new features or product-line expansions, verify:**

- [ ] All field mappings defined in mapping_contract.json (not hardcoded)
- [ ] target_schema read from contract (not hardcoded)
- [ ] MigrationEngine receives `mapping_contract_path` for non-default product lines
- [ ] Atomic transactions used (all-or-nothing per app_id)
- [ ] FK ordering respected in insertion sequence
- [ ] Processing log resume logic tested with failures
- [ ] Cursor-based pagination used (not OFFSET)
- [ ] Duplicate detection has WITH (NOLOCK)
- [ ] Three-layer validation present
- [ ] Windows-specific code uses PowerShell/pyodbc (not bash/SQLAlchemy)
- [ ] Tests verify data integrity (not just happy path)
- [ ] Performance measured before and after changes
- [ ] New gotchas documented if discovered

---

## 6. Adding New Constraints

When you encounter a new issue that becomes a system constraint:

1. **Document the gotcha** (what went wrong, how it was fixed)
2. **Add prevention strategies** (how to avoid reintroducing it)
3. **Add to code review checklist** (make it visible)
4. **Update architecture-project-blueprint.md** if it affects design decisions

Example format:
```markdown
### Gotcha N: [Problem Name]
**What Was Wrong:** [Describe the issue and symptoms]
**How It Was Fixed:** [Explain the solution]
**Prevention:** [Checklist items for code review]
```

---

## References
- [docs/architecture-project-blueprint](../../../docs/architecture-project-blueprint.md) - Detailed design rationale
- [copilot-instructions.md](../../copilot-instructions.md) - Core operating principles
- [config/mapping_contract.json](../../../config/mapping_contract.json) - Contract schema definition
