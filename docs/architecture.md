# XML Database Extraction System - Architecture

**Date:** November 6, 2025  
**Status:** Ready to Baseline in DEV

---

## Quick Reference

- **Schema Isolation:** Target schema from MappingContract (sandbox/dbo)
- **Data Flow:** XML → Parser → Mapper → Engine → DB (atomic transaction per app)
- **FK Ordering:** app_base → contact_base → child tables → processing_log
- **Concurrency:** App ID ranges prevent overlap; processing_log prevents reprocessing
- **Performance:** 1,500-1,600 apps/min sustained (4 workers, batch-size=500)

---

## 1. Schema Isolation (Contract-Driven)

**Core Principle:** All database operations respect `target_schema` from MappingContract, enabling safe schema-isolated development/testing/production pipelines.

### Schema Boundaries

| Component | Schema | Read/Write | Purpose |
|-----------|--------|-----------|---------|
| Source XML (`app_xml`) | `[dbo]` | Read-only | Raw XML storage (never modified) |
| Target tables (app_base, contact_base, etc.) | `[target_schema]` | Write | Normalized data output |
| Audit log (`processing_log`) | `[target_schema]` | Write | Processing audit trail |

---

## 2. Data Flow Architecture

### Processing Pipeline

```
    XML Input
        ↓
    [1] XML PARSER (lxml)
        • Selective element extraction
        • Memory-efficient streaming
        • Validates XML structure
        ↓
    [2] DATA MAPPER (Contract-Driven)
        • Extracts fields per MappingContract
        • Applies enum mappings
        • Calculates derived fields
        • Validates data types
        ↓
    [3] DATA VALIDATION
        • Required field checks
        • Enum value verification
        • FK dependency validation
        • Duplicate detection
        ↓
    [4] MIGRATION ENGINE (Atomic Transactions)
        • Single connection per application
        • Bulk insert with FK ordering
        • processing_log entry included
        • Explicit commit/rollback
        ↓
    Database Output (Normalized Tables)
```

### Key Stages

**Parser → Mapper → Engine** is the critical path:
- Parser extracts raw XML → dict
- Mapper transforms dict per contract → table-keyed dict
- Engine batches and inserts → database (atomic)

**Every stage validates its output:**
- Parser: XML well-formed?
- Mapper: All required fields present?
- Engine: FK constraints satisfied?

---

## 3. Foreign Key Ordering Strategy

**Critical:** Tables must be inserted in FK dependency order to prevent constraint violations.

### Table Insertion Order

```
    1. app_base
        ↓ (all app_*_cc tables FK to this)

    2. contact_base
        ↓ (contact_address/contact_employment FK to this)
        ↓ (also has FK to app_base)

    3. app_operational_cc   (child of app_base)
    4. app_pricing_cc       (child of app_base)
    5. app_transactional_cc (child of app_base)
    6. app_solicited_cc     (child of app_base)

    7. contact_address      (child of contact_base)
    8. contact_employment   (child of contact_base)

    9. processing_log       (audit log, FK to app_base)
```

### Why This Order Works

1. **Parent-First Rule:** All parents inserted before children
   - app_base must exist before app_operational_cc inserts
   - contact_base must exist before contact_address inserts

2. **Multiple Parents:** contact_base depends on both app_base AND contact_base
   - Insert app_base first (parent of contact_base)
   - Then insert contact_base (parent of child tables)

3. **Audit Trail Last:** processing_log references app_base via FK
   - Must insert after app_base succeeds
   - Atomic transaction ensures both succeed or both fail

---

## 4. Transaction Atomicity

**Guarantee:** Either ALL tables for an application succeed, or NONE do (zero orphaned records).

### Atomic Scope: Single Application

```python
    # One connection per application for atomic transaction
    with migration_engine.get_connection() as conn:
        # All inserts share this connection (no autocommit)
        
        INSERT INTO app_base (...)                    # Connection A
        INSERT INTO contact_base (...)                # Connection A
        INSERT INTO app_operational_cc (...)          # Connection A
        INSERT INTO processing_log (...)              # Connection A (audit)
        
        conn.commit()  # All succeed, or rollback on first error
```

### Safety Guarantees

| Scenario | Result |
|----------|--------|
| All inserts succeed | COMMIT: All data in DB, log entry exists |
| Error in app_base | ROLLBACK: Nothing in DB, no orphans |
| Error in processing_log | ROLLBACK: Everything rolled back (no partial data) |
| Crash mid-transaction | ROLLBACK: DB recovered on restart, no orphans |

### Resume Capability

```sql
    -- processing_log tracks completion
    SELECT * FROM processing_log WHERE app_id = 12345 AND status='success'

    -- Already processed? Skip it on resume
    -- Not logged? Retry it
    -- Failed? Can retry or investigate
```

---

## 5. Concurrency & Lock Prevention

**Strategy:** Non-overlapping app_id ranges prevent lock contention between instances.

### Concurrent Processing Pattern

```powershell
    # Terminal 1: Process app_ids 1-60,000
    python production_processor.py --app-id-start 1 --app-id-end 60000

    # Terminal 2: Process app_ids 60,001-120,000
    python production_processor.py --app-id-start 60001 --app-id-end 120000

    # Terminal 3: Process app_ids 120,001-180,000
    python production_processor.py --app-id-start 120001 --app-id-end 180000
```

### How Ranges Prevent Contention

1. **Different app_ids:** Each instance processes different applications
2. **No overlap:** No two instances insert into same processing_log rows
3. **Independent destinations:** No lock conflicts on destination tables
4. **Resume-safe:** processing_log prevents reprocessing regardless of ranges

### Query Optimization

```sql
    -- Fast batch query with TOP + range filter (no OFFSET scan penalty)
    SELECT TOP (500) ax.app_id, ax.xml 
    FROM [dbo].[app_xml] AS ax
    WHERE ax.app_id > @last_app_id          -- Cursor pagination
    AND ax.app_id <= (@last_app_id + 500)   -- Upper bound (focused search)
    AND ax.xml IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM [sandbox].[processing_log] AS pl
        WHERE pl.app_id = ax.app_id        -- Already processed?
    )
    ORDER BY ax.app_id
```

---

## 6. Performance Characteristics

### Throughput

**Baseline:** 1,500-1,600 applications/minute
- 4 parallel workers
- batch-size=1000 (App XMLs per SQL fetch)
- 4-core Windows machine with SQLExpress

**Scaling:**
- Per additional worker: ~400 apps/min (diminishing returns after 6 workers)
- Per remote SQL Server: Higher throughput (SQLExpress has I/O limits)

### Batch Processing

- Batch size: 1000 App XMLs fetched per SQL query (pagination size)
- Processing: Parallel across 4 workers
- Insert: Bulk operation with fast_executemany (each application expands to multiple normalized database records)
- Memory: ~125MB stable (no degradation)

### Chunked Processing (Long Production Runs)

For >100k applications, use `run_production_processor.py`:
- Chunk size: 10k app_ids per chunk (default) - each chunk is a separate process
- Batch size: 500-1000 App XMLs per SQL query within each chunk
- Lifecycle: Fresh Python process per chunk
- Benefits: Prevents performance degradation on long runs, natural checkpoints
- Performance: Same throughput, better stability over extended processing

---

## 7. Error Recovery

### Processing Log States

```
    status = 'success'   → Application processed successfully, all data inserted
    status = 'failed'    → Application failed, rolled back, no data inserted
    <not in log>         → Application not yet attempted (will retry on resume)
```

### Resume After Failure

```powershell
    # Same command as before (resume-safe):
    python production_processor.py --app-id-start 1 --app-id-end 180000

    # Automatically:
    # 1. Reads processing_log to find last-processed app_id
    # 2. Skips already-logged entries (success or failed)
    # 3. Continues from where it left off
    # 4. No PK violations, no orphaned data
```

### Crash Recovery

```
    Crash after COMMIT:        → Data safely in DB
    Crash during transaction:  → Rolled back on restart
    Crash during XML parse:    → No data inserted (parse stage)
    Crash during mapping:      → No data inserted (pre-insert)
```

---

## 8. Configuration Points

### Mapping Contract (config/mapping_contract.json)

```json
    {
    "target_schema": "sandbox",           // or "dbo" for production
    "table_insertion_order": [...],       // FK dependency order
    "mappings": [...],                    // Field extraction rules
    "enum_mappings": {...},               // Value transformations
    "bit_conversions": {...}              // Boolean handling
    }
```

### Runtime Parameters

```powershell
    # LIMIT Mode: Sequential with total cap (safety limit)
    --limit 10000                           # Process up to 10k applications

    # RANGE Mode: Explicit range (concurrent-safe for multiple instances)
    --app-id-start 1 --app-id-end 180000   # Process only applications in this app_id range

    # Performance tuning
    --workers 4                             # Parallel processes per instance (default: 4)
    --batch-size 1000                       # App XMLs per SQL fetch (pagination, default: 500)
    --enable-pooling                        # Connection pooling (for remote SQL Server)
```

---

## 9. Design Decisions

### Why Single Connection per Application?

**Atomic Transactions:**
- Decoupling data INSERT from audit logging caused orphaned records
- Solution: Include processing_log as part of same transaction
- Result: All-or-nothing semantics, zero orphans, +14% throughput

### Why TOP + Range Instead of OFFSET?

**Query Performance:**
- OFFSET scans all prior rows (expensive as table grows)
- TOP seeks directly with index (constant time)
- Upper bound limit focuses search space
- Result: 2+ seconds → <500ms per batch

### Why Chunked Orchestrator?

**Memory Degradation Prevention:**
- Python internal state accumulates over 60k+ records (-60% throughput)
- Solution: Fresh process every 10k records
- Result: Sustained 1,500+ apps/min vs 350 apps/min at end

### Why App ID Ranges?

**Concurrency Safety:**
- Concurrent instances can collide on processing_log (lock contention)
- Solution: Explicit non-overlapping ranges per instance
- Result: 3 concurrent instances = 3x throughput (with proper ranges)

---

## 10. Reference: Contract-Driven Pattern

**Definition:** MappingContract defines the entire ETL transformation:
- What fields to extract (mappings)
- How to transform values (enum_mappings, bit_conversions)
- Where to store output (target_schema)
- What order to insert (table_insertion_order)

**Benefits:**
- Separation of concerns (code doesn't hardcode transformation logic)
- Easy to support multiple contracts/products
- Audit trail: know exactly how data was transformed
- Version control: contracts track schema changes

**Implementation:**
- ConfigManager loads contract from JSON
- DataMapper applies mappings to each record
- MigrationEngine respects target_schema for all operations
- processing_log tracks which contract was used

---

## Quick Links

- **Setup:** See `config/samples/create_destination_tables.sql`
- **Operator Guide:** See `OPERATOR_GUIDE.md`
- **Performance Analysis:** See `performance_tuning/FINAL_PERFORMANCE_SUMMARY.md`
- **Testing:** See `performance_tuning/TESTING_STRATEGY_ATOMIC_LOGGING.md`
- **Investigation Archive:** See `performance_tuning/DEGRADATION_INVESTIGATION_LOG.md`

---

## Summary

| Concern | Design Decision | Rationale |
|---------|-----------------|-----------|
| Data Isolation | Schema per environment | Prevent cross-env contamination |
| Transaction Safety | Atomic per application | Zero orphaned records |
| Query Performance | TOP + range filters | Sub-second batch queries |
| Concurrency | App ID ranges | Lock contention prevention |
| Long Runs | Chunked orchestrator | Memory degradation prevention |
| Resume Capability | processing_log tracking | Crash recovery without PK violations |
| Configuration | Contract-driven | Separation of concerns, easy updates |

