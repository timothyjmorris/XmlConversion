---
name: decision-frameworks
description: Decision-making frameworks for architecture trade-offs in the XML Database Extraction System. Covers testing vs speed, complexity vs clarity, performance optimization, scope management, and configuration decisions. Use when evaluating implementation approaches, optimizing performance, or choosing between design alternatives.
metadata:
  last-updated: "2026-02-14"
  project: xml-database-extraction
---

# Decision Frameworks & How We Make Trade-offs

---

## 1. Testing vs. Speed: The Data Integrity Priority

### Core Philosophy
**We prioritize evidence over assertion.** Never assume something worksâ€”prove it with tests.

### Decision Framework

**Question:** "Should we skip this test to ship faster?"

**Decision Tree:**
```
Does the change affect data integrity?
â”œâ”€ YES
â”‚  â””â”€ MUST have: unit test + integration test + data-driven assertions
â”‚     Example: Changing FK ordering â†’ test with intentional FK violations
â”‚
â”œâ”€ NO (cosmetic/perf optimization only)
â”‚  â””â”€ Unit test sufficient (verify the optimization works)
â”‚     Example: Adding index â†’ test query plan improvement
â”‚
â””â”€ UNCERTAIN
   â””â”€ Assume YES (data-first mindset)
      Write the test, then optimize if needed
```

### Testing Philosophy

**What We Test For:**
- âœ… **Robustness:** Can the system handle edge cases, failures, retries?
- âœ… **Correctness:** Does output match contract expectations?
- âœ… **Consistency:** Do parallel runs produce same results?
- âœ… **Atomicity:** Do failures rollback cleanly?

**What We Don't Test For:**
- âŒ Line-by-line code coverage (testing the implementation, not behavior)
- âŒ Happy path only (tests must prove robustness)
- âŒ Mocked dependencies (data-driven assertions use real database)

### Test Classification

| Test Type | Speed | Data Verified | Use When |
|-----------|-------|----------------|----------|
| **Unit** | <100ms | Function behavior | Isolated logic (enum mapping, calculations) |
| **Integration** | 1-5s | Database state | Cross-module interactions (Parserâ†’Mapperâ†’Engine) |
| **End-to-End** | 5-60s | Full pipeline | Entire product line (XMLâ†’DB with metrics) |

**Rule:** For data-affecting changes, require both unit + integration tests.

### Data-Driven Assertions

**Example - WRONG:**
```python
# Testing the code, not the behavior
result = mapper.map_record(input_data)
assert result is not None  # Meaningless assertion
assert isinstance(result, dict)  # Testing Python types, not domain logic
```

**Example - RIGHT:**
```python
# Testing domain behavior with data
cursor.execute(f"SELECT COUNT(*) FROM [{target_schema}].app_base WHERE app_id = ?", (app_id,))
count = cursor.fetchone()[0]
assert count == 1, f"Expected 1 app_base row, found {count}"  # Proves insertion worked

cursor.execute(f"SELECT status FROM [{target_schema}].processing_log WHERE app_id = ? AND target_table = ?", 
               (app_id, 'app_base'))
status = cursor.fetchone()[0]
assert status == 'success', f"Expected success, got {status}"  # Proves atomicity
```

---

## 2. Complexity vs. Clarity: The Simplicity-First Principle

### Core Philosophy
**Explicit over implicit. Simple over clever. Prove necessity before implementing.**

### Decision Framework

**Question:** "Should we add this abstraction/helper/utility?"

**Decision Tree:**
```
Will this abstraction be used in more than one place?
â”œâ”€ YES (2+ places use it)
â”‚  â””â”€ CREATE the abstraction
â”‚     Reduces duplication, improves maintainability
â”‚
â”œâ”€ NO (only used once)
â”‚  â””â”€ KEEP IT INLINE
â”‚     Simplicity > abstraction overhead
â”‚     Exception: Calculation-heavy logic (still inline, but documented)
â”‚
â””â”€ MAYBE/FUTURE (hypothetical reuse)
   â””â”€ DON'T CREATE (YAGNI principle)
      You Ain't Gonna Need It
      Wait for proven need (second actual use case)
```

### No Backward-Compatibility Shims

**Principle:** When changing code, change all callers. Don't create compatibility wrappers.

**Example - WRONG:**
```python
# Old function (deprecated but kept for compatibility)
def old_validation(record):
    # This is slower and maintains two code paths
    return new_validation(record)

# In 5 years, someone still doesn't know which to use
```

**Example - RIGHT:**
```python
# Replace all callers at once (code refactoring)
# Search for old_validation() â†’ update 3 files â†’ delete function (from codebase)
# Clean, explicit, no hidden coupling
# Note: Deleting code from repo is OK; deleting data is never OK without approval
```

### No Premature Optimization

**Rule:** Only optimize when:
1. Baseline measurement shows it's slow
2. Profiling identifies the bottleneck
3. Change is data-proven to improve it

**Example - WRONG:**
```python
# Premature optimization (no data showing this is slow)
# Adds complexity for hypothetical gains
async def optimized_parser_with_parallel_xml_processing():
    tasks = [asyncio.create_task(parse_element(e)) for e in elements]
    return await asyncio.gather(*tasks)
```

**Example - RIGHT:**
```python
# Measure first
# Current: 2000 apps/min on 4 workers, 85% CPU, 60% memory
# Target: 3500 apps/min
# Profiling: batch-size tuning yields biggest gain (measure it)

parser.batch_size = 1000  # Data-driven tuning
# Remeasure: 3100 apps/min
```

### Reuse Before New

**When extending system:**
1. Check existing modules first (see [common-patterns](../common-patterns/SKILL.md))
2. Extend existing abstractions (don't create parallel ones)
3. Only create new modules when existing ones don't fit

**Example - WRONG:**
```python
# Created new validation module instead of extending existing
xml_extractor/
â”œâ”€â”€ validation/validator.py      (original, 400 lines)
â”œâ”€â”€ validation/custom_validator.py  (new, parallel, 300 lines)
```

**Example - RIGHT:**
```python
# Extended existing module
xml_extractor/
â”œâ”€â”€ validation/validator.py      (now 600 lines, handles all cases)
â”‚   â”œâ”€â”€ three_layer_validation()      (original)
â”‚   â”œâ”€â”€ custom_rules_validation()     (new method)
```

---

## 3. Performance: Measurement-Driven, Not Theoretical

### Core Philosophy
**Only optimize what you've measured. Target-driven performance, not maximum speed.**

### Decision Framework

**Question:** "Should we implement this performance optimization?"

**Decision Tree:**
```
Do we have a baseline measurement?
â”œâ”€ NO
â”‚  â””â”€ MEASURE FIRST
â”‚     Get baseline (throughput, memory, latency)
â”‚     Document current state
â”‚
â”œâ”€ YES
â”‚  â””â”€ Does optimization achieve target improvement?
â”‚     â”œâ”€ TARGET NOT MET
â”‚     â”‚  â””â”€ Measure impact: +10%? +50%? +500%?
â”‚     â”‚     If >20% gain with <10% complexity cost â†’ IMPLEMENT
â”‚     â”‚
â”‚     â”œâ”€ TARGET ALREADY MET
â”‚     â”‚  â””â”€ DO NOT OPTIMIZE (target already achieved)
â”‚     â”‚     Simplicity wins
â”‚     â”‚
â”‚     â””â”€ TARGET EXCEEDED
â”‚        â””â”€ DONE (no optimization needed)
```

### Performance Baselines

**For new product lines, establish:**
- Throughput (records/min) on target hardware
- Memory usage over 1-hour run
- Database connection count
- Lock contention (if any)
- Batch-size sensitivity (test 20, 50, 100, 500, 1000)
- Worker concurrency sensitivity (test 1, 2, 4, 8)

**Target for expansion:** â‰¥ 3,500 records/min

### Trade-Off Decision Matrix

When optimization requires trade-offs:

| Trade-Off | Decision | Example |
|-----------|----------|---------|
| Speed vs. Memory | **Trade memory for speed** | Chunked processing: fresh process per chunk (use more memory/processes, get better throughput) |
| Speed vs. Simplicity | **Measure first, then choose** | Batch-size tuning yields 50% gain with no complexity â†’ DO IT. Async parsing adds 20% gain with 200 lines complexity â†’ DON'T |
| Speed vs. Correctness | **NEVER sacrifice correctness** | Lock-free validation? No. Use WITH (NOLOCK) instead. |
| Speed vs. Maintainability | **Choose based on code lifetime** | If feature is one-time â†’ simplicity wins. If feature is core â†’ maintainability wins. |

---

## 4. Scope Management: Thin Vertical Slices

### Core Philosophy
**Small, testable, end-to-end increments. Not big bang, not layers.**

### Decision Framework

**Question:** "How do I approach a new product-line expansion?"

**Decision Tree:**
```
Define vertical slice (one feature, end-to-end):
â”œâ”€ 1. Contract extension (mapping_contract.json)
â”œâ”€ 2. Schema extension (new tables + FKs)
â”œâ”€ 3. Parser/Mapper extension (product-specific logic)
â”œâ”€ 4. Validation rules (three-layer validation)
â”œâ”€ 5. Integration tests (prove correctness)
â”œâ”€ 6. Performance baseline (measure throughput)
â”œâ”€ 7. Merge to main
â”‚
â””â”€ Repeat for next feature
```

**Why This Works:**
- Each slice is <1 day of work
- Errors isolated to single slice
- Easy to rollback
- Easy to merge and deploy
- No integration surprises

### Feature Ordering for Product-Line Expansion

**Phase 1: Foundation (Week 1)**
```
Slice 1: Create mapping contract for product line
Slice 2: Add schema (tables, indexes, FKs)
Slice 3: Extend parser (handle new XML structure)
Slice 4: Create basic tests (prove XMLâ†’DB works)
```

**Phase 2: Enhancement (Week 2)**
```
Slice 5: Add enum mappings
Slice 6: Add calculated fields
Slice 7: Add validation rules
```

**Phase 3: Integration (Week 3)**
```
Slice 8: Performance testing
Slice 9: Parallel processing (if needed)
Slice 10: Monitoring/metrics
```

---

## 5. Correctness as Non-Negotiable

### Core Philosophy
**Data integrity > Speed. Always.**

### When to Sacrifice Performance

**You should slow down (or skip optimization) when:**
- Change affects atomicity (must commit all-or-nothing)
- Change affects FK ordering
- Change affects resume capability
- Change affects duplicate detection
- Optimization creates lock contention

**Example - WRONG:**
```python
# "Optimization": Remove WITH (NOLOCK) for "stronger consistency"
# Result: Lock contention, timeouts, data loss
cursor.execute("SELECT * FROM app_base WHERE app_id = ?")  # No NOLOCK
```

**Example - RIGHT:**
```python
# Keep WITH (NOLOCK) for duplicate detection
# Dirty reads acceptable, correctness preserved, throughput optimized
cursor.execute("SELECT COUNT(*) FROM app_base WITH (NOLOCK) WHERE app_id = ?")
```

### Validation Layers as Non-Negotiable

All three layers must always be present:
1. **Pre-Processing:** XML structure valid
2. **Data Mapping:** Contract requirements met
3. **Database:** FK/unique constraints satisfied

**Example - WRONG:**
```python
# Skip Layer 1 "for speed"
# Result: Parser crashes on malformed XML, no recovery
parsed = parser.parse(raw_xml)  # No validation
mapper.map(parsed)
```

**Example - RIGHT:**
```python
# All three layers active
result = validator.validate_preprocessing(raw_xml)
if not result.is_valid:
    return result  # Fail fast with clear error

parsed = parser.parse(raw_xml)
result = validator.validate_mapping(parsed)
if not result.is_valid:
    return result

engine.migrate(parsed)
result = validator.validate_database_state(app_id)
if not result.is_valid:
    rollback()  # Atomic guarantee
```

---

## 6. Configuration & Flexibility

### Core Philosophy
**Contract-driven configuration enables variations without code changes.**

### When to Extend Config vs. Code

**Decision Framework:**

| Need | Solution | Why |
|------|----------|-----|
| New field mapping | Extend mapping_contract.json | Product lines differ, config enables that |
| Enum value translation | Add enum_mappings to contract | Business rules vary, config-driven is safer |
| Calculated field | Add to contract calculated_fields | Logic tied to domain, should be visible |
| Product-specific parsing | Extend DataMapper class | Rare, only if XML structure fundamentally differs |
| Data validation rule | Add validation_rules to contract | Domain-specific, should be discoverable |
| Custom error handling | Code (with contract dispatch) | Cross-cutting concern, not contract-driven |

### Schema Isolation Configuration

**Per environment:**
```json
{
  "mapping_contract": "config/mapping_contract.json",
  "target_schema": "sandbox",  // or "dbo" or "product-prod"
  "source_table": "dbo.app_xml",
  "source_schema": "dbo"
}
```

**Enables:**
- Dev team uses `[sandbox]` schema
- QA team uses `[qa]` schema
- Prod uses `[dbo]` schema
- Same code, different databases, zero configuration in code

---

## 7. Common Decision Scenarios

### Scenario 1: New Field from Different XML Path

**Decision:** Contract-driven (10 min vs. 2 hours for code change)

```json
{
  "target_table": "app_base",
  "mappings": [
    {
      "column": "region_name",
      "source_path": "application/location/region",  // New path
      "type": "string",
      "nullable": true
    }
  ]
}
```

### Scenario 2: New Product Line with Different Table Structure

**Decision:** Extend contract + schema + minimal code

```json
{
  "product_line": "healthcare_provider",
  "target_schema": "healthcare_sandbox",
  "mappings": {
    "provider_base": [...],
    "provider_credentials": [...],
    "provider_specialties": [...]
  }
}
```

### Scenario 3: Enum Values Need Translation

**Decision:** Contract enum_mappings (centralized, discoverable)

```json
{
  "column": "credential_status",
  "enum_mappings": {
    "ACTIVE": "A",
    "INACTIVE": "I",
    "SUSPENDED": "S"
  }
}
```

### Scenario 4: Throughput Below 3,500 Records/Min

**Decision:** Measure â†’ profile â†’ optimize (in this order)

```
1. Measure current state (1800 records/min, 80% CPU, 40% memory)
2. Profile: What's the bottleneck?
   - Batch-size: Test 20, 50, 100, 500, 1000, 2000
   - Workers: Test 1, 2, 4, 8
   - Query plans: Any full scans?
3. Implement biggest-gain optimization (usually batch-size tuning)
4. Remeasure: Verify improvement
5. Iterate until target reached
```

### Scenario 5: Should We Support Multiple XML Versions?

**Decision:** Add to contract, not code

```json
{
  "versions": [
    {
      "version": "1.0",
      "source_path_mapping": {
        "app/name": "appName"  // v1.0 path
      }
    },
    {
      "version": "2.0", 
      "source_path_mapping": {
        "application/applicationName": "appName"  // v2.0 path
      }
    }
  ]
}
```

DataMapper dispatches based on detected version, contract defines both paths.

---

## 8. Review Checklist: Decision Quality

When reviewing code or design proposals, ask:

**For Architecture Decisions:**
- [ ] Is this contract-driven or hardcoded?
- [ ] Could configuration replace code?
- [ ] Does it respect schema isolation?
- [ ] Does it preserve atomicity?
- [ ] Was it measured against baseline?

**For Performance Decisions:**
- [ ] What was the baseline? (throughput, memory, latency)
- [ ] What's the target? (3,500 records/min?)
- [ ] What was the bottleneck? (profiled or guessed?)
- [ ] What's the improvement? (+10%? +50%?)
- [ ] What's the complexity cost? (lines of code, maintainability impact)
- [ ] Is the ROI positive? (improvement > complexity cost)

**For Feature Decisions:**
- [ ] Is this end-to-end? (contract through tests)
- [ ] Are all three validation layers present?
- [ ] Are tests data-driven? (query database for truth)
- [ ] Was existing code reused?
- [ ] Is it schema-isolated testable?

---

## References
- [system-constraints](../system-constraints/SKILL.md) - Non-negotiable principles
- [copilot-instructions.md](../../copilot-instructions.md) - Core operating principles
- [docs/architecture.md](../../../docs/architecture.md) - Design rationale

