# Copilot Skills Strategy for Product-Line Expansion

**Date:** January 22, 2026  
**Purpose:** Enable AI agents to understand the XML Conversion System's architecture, constraints, and decision frameworks for expanding to new product lines.

---

## 1. Current State & Knowledge Transfer Challenge

### What Makes This System Special

Your XML conversion system has three critical characteristics that **must be preserved** in expansions:

1. **Contract-Driven Architecture**
   - All transformations defined in `mapping_contract.json` (not code)
   - Schema isolation pattern (sandbox/dbo) enables safe parallel development
   - Data mapping is *declarative*, not imperative

2. **Data Integrity as Non-Negotiable**
   - Atomic transactions per application (all-or-nothing)
   - Foreign key ordering strategy prevents orphaned records
   - Resume capability with duplicate detection
   - Lock contention fixes (WITH NOLOCK hints)

3. **Performance as Functional Requirement**
   - Target: 3,500 records/min (current: ~2,000 apps/min)
   - Batch-size 1000 proven optimal for current stack
   - Memory degradation over long runs addressed by chunked processing
   - No hypothetical optimizations—only data-driven tuning

**The Problem:** AI agents (including Copilot) will default to:
- Creating imperative code instead of contracts
- Skipping atomicity for "simplicity"
- Adding premature optimizations
- Ignoring schema isolation patterns

---

## 2. Recommended Skill File Structure

Create this directory structure:

```
.github/skills/
├── SYSTEM_CONSTRAINTS.md          [Non-negotiables & guardrails]
├── DECISION_FRAMEWORKS.md          [How to think about tradeoffs]
├── PRODUCT_LINE_EXPANSION.md       [Playbook for new data sources]
├── CONTRACT_DRIVEN_DESIGN.md       [How to extend mapping contracts]
├── TESTING_DATA_INTEGRITY.md       [Validation approach for new features]
├── PERFORMANCE_PROFILING.md        [How to measure, not guess]
└── COMMON_PATTERNS.md              [Reusable code & architecture patterns]
```

---

## 3. Critical Skill Files to Create

### A. `SYSTEM_CONSTRAINTS.md`
**Purpose:** Define what MUST NOT change, and why.

Key sections:
- **Non-Negotiable Principles**
  - All transformations are contract-driven (never hardcode mappings)
  - All table operations must respect target_schema from contract
  - Every data insertion must be atomic (all-or-nothing per app_id)
  - No reintroduction of lock contention patterns (see ARCHITECTURE.md for WITH NOLOCK usage)
  
- **Windows-First Requirements**
  - PowerShell for shell commands, never bash
  - Use `Path.Combine()` or `\` for file paths
  - pyodbc over SQLAlchemy (Windows Auth native support)
  
- **Untouchable Code Patterns**
  - Processing_log resume logic (excludes both success AND failed status)
  - Cursor-based pagination (NOT OFFSET)
  - FK ordering sequence (document the dependency graph)
  - Three-layer validation architecture
  
- **Known Gotchas (Do Not Reintroduce)**
  - Lock contention on duplicate detection (fixed with WITH NOLOCK)
  - Enum mappings returning None (columns excluded from INSERT)
  - Memory degradation in long runs (solved by chunked processing)

---

### B. `DECISION_FRAMEWORKS.md`
**Purpose:** Help agents understand *how* you make tradeoffs.

Key sections:
- **Testing vs. Speed**
  - Always test-first (TDD/BDD)
  - Evidence-based assertions (not narrative reasoning)
  - Test coverage must prove *robustness*, not just passing tests
  - Data-driven fixtures, not hard-coded values

- **Complexity vs. Clarity**
  - Prefer explicit over implicit (but not over-engineered)
  - No premature optimizations without data
  - No backward-compatibility shims
  - Reuse existing modules before creating new abstractions
  - No hypothetical requirements

- **Performance Decisions**
  - Measure before optimizing (get baseline metrics)
  - Target-driven (3,500 records/min), not theoretical
  - Trade memory for throughput (chunked processing for >100k records)
  - No changes without before/after metrics

- **Scope Management for Expansions**
  - Thin vertical slices (end-to-end per product line feature)
  - Contract extends existing structure (not parallel systems)
  - Schema isolation per product line (sandbox/[product]-prod)
  - Test product line in isolation before integration

---

### C. `PRODUCT_LINE_EXPANSION.md`
**Purpose:** Step-by-step playbook for adding new product lines.

Key sections:
- **Pre-Expansion Checklist**
  - [ ] New product line's XML schema documented (structure, nesting, cardinality)
  - [ ] Target database schema designed (table names, columns, FKs)
  - [ ] Business rules identified (field mappings, enum values, calculations)
  - [ ] Performance baseline for volume and concurrency
  - [ ] Testing strategy (unit, integration, end-to-end)

- **Extension Points (in order)**
  1. Create new mapping contract section in `config/mapping_contract.json`
  2. Add new database schema objects (tables, indexes) to target DB
  3. Create product-line-specific parsing rules (if XML differs significantly)
  4. Extend `DataMapper` with product-line-specific calculated fields
  5. Add product-line-specific validation rules
  6. Create product-line test fixtures and integration tests
  7. Document product-line-specific gotchas

- **Schema Isolation Strategy**
  - Keep source XML in `dbo.app_xml` (shared)
  - Target tables in `[sandbox]` or `[product-line-prod]`
  - Separate mapping contracts per environment
  - Use configuration to swap contracts by product line

- **Contract Structure Template**
  ```json
  {
    "product_line": "new_product",
    "source_table": "dbo.app_xml",  
    "target_schema": "sandbox",
    "mappings": {
      "target_table": [
        {
          "column": "field_name",
          "source_path": "xpath/to/element",
          "type": "string|int|datetime|enum",
          "nullable": true|false,
          "default_value": null,
          "enum_mappings": { "source_val": "target_val" }
        }
      ]
    },
    "calculated_fields": {
      "target_table": {
        "column_name": "transformation_logic"
      }
    },
    "foreign_keys": {
      "table_name": ["parent_table.parent_id"]
    }
  }
  ```

---

### D. `CONTRACT_DRIVEN_DESIGN.md`
**Purpose:** Deep dive into mapping contract philosophy & extension patterns.

Key sections:
- **Why Contracts > Code**
  - Transformation logic is data, not code (enables config-driven variations)
  - Contracts are queryable and self-documenting
  - Changes don't require code deployment (safer for operations)
  - Schema metadata auto-derives from database (DRY principle)

- **Contract Extension Patterns**
  - Adding new source paths (enrich existing mapping)
  - Adding enum mappings (support new business rules)
  - Adding calculated fields (derive values from inputs)
  - Adding validation rules (apply domain constraints)

- **Common Extensions**
  ```python
  # Pattern 1: Conditional field mapping (based on parent state)
  # Implement in DataMapper.map_record() with product-line dispatch
  
  # Pattern 2: Cross-field dependencies
  # Document in contract under "validation_rules"
  
  # Pattern 3: Rollup/aggregation fields
  # Implement as calculated_fields with group-by logic
  ```

- **Data Derivation Patterns**
  - Enum mapping + fallback (None = exclude from INSERT)
  - String concatenation (combine multiple sources)
  - Parsing/extraction (substring, split, regex)
  - Calculation (math, date arithmetic)
  - Conditional (IF/CASE logic based on other fields)

---

### E. `TESTING_DATA_INTEGRITY.md`
**Purpose:** How to prove new product lines work correctly.

Key sections:
- **Three-Layer Validation Strategy**
  1. **Pre-Processing:** XML structure, required elements present
  2. **Data Mapping:** All contract-defined fields extractable, type conversions valid
  3. **Database Constraints:** FK relationships satisfied, unique constraints preserved

- **Test Fixtures for New Product Lines**
  - Valid minimum case (one of each table type)
  - Edge case with NULL optional fields
  - Enum boundary cases (valid/invalid/missing values)
  - FK dependency cases (parent missing, orphaned child)
  - Duplicate detection cases (retry same app_id)
  - Resume cases (partial success, gap-filling)

- **Integration Test Patterns**
  ```python
  # Pattern: Roundtrip validation
  def test_product_line_roundtrip():
      # 1. Insert via normal pipeline
      # 2. Query results from DB
      # 3. Assert all fields match contract expectations
      # 4. Verify FK relationships intact
      # 5. Check atomicity (all-or-nothing)
  ```

- **Data-Driven Assertions**
  - Use database queries for truth (not in-memory objects)
  - Verify row counts per table
  - Check FK referential integrity
  - Validate calculated fields with SQL
  - Audit trail verification (processing_log entries)

---

### F. `PERFORMANCE_PROFILING.md`
**Purpose:** How to measure & establish baselines for new product lines.

Key sections:
- **Measurement Checklist**
  - [ ] Baseline throughput (records/min) on target hardware
  - [ ] Memory usage over 1 hour run
  - [ ] Database connection count
  - [ ] Lock wait times (if applicable)
  - [ ] Batch-size impact (20, 50, 100, 500, 1000, 2000)
  - [ ] Worker concurrency impact (1, 2, 4, 8)

- **Tooling**
  ```
  diagnostics/
  ├── resource_profiler.py      # CPU, memory, I/O
  ├── test_network_latency.py   # DB connection overhead
  ├── inspect_mapped_app.py     # Single record tracing
  └── check_metrics.py          # Aggregate performance stats
  ```

- **Decision Points**
  - If throughput < 3,500 records/min:
    - Measure batch-size sensitivity first
    - Then measure worker count sensitivity
    - Then profile database query plans
  - If memory degrades in long runs:
    - Use chunked processor (run_production_processor.py)
  - If lock contention occurs:
    - Add WITH (NOLOCK) to read queries (see ARCHITECTURE.md)

---

### G. `COMMON_PATTERNS.md`
**Purpose:** Reusable code patterns & templates for product-line extensions.

Key sections:
- **XML Parsing Patterns**
  ```python
  # Pattern: Selective element extraction
  from xml_extractor.parsing.xml_parser import XMLParser
  
  parser = XMLParser(select_elements=['app', 'contact'])
  records = parser.parse(xml_content)
  ```

- **Data Mapping Patterns**
  ```python
  # Pattern: Product-line-specific calculated field
  from xml_extractor.mapping.data_mapper import DataMapper
  
  # Implement in contract under calculated_fields
  # Or override DataMapper.apply_calculated_field() for complex logic
  ```

- **Validation Patterns**
  ```python
  # Pattern: Custom validation rule
  from xml_extractor.validation.validator import Validator
  
  def validate_product_line_rule(record, contract):
      # Return ValidationResult(is_valid, errors)
  ```

- **Database Patterns**
  ```python
  # Pattern: Atomic transaction with FK ordering
  # MigrationEngine handles this automatically
  # Just ensure FK ordering in contract's foreign_keys section
  ```

- **Testing Patterns**
  ```python
  # Pattern: Fixture-based integration test
  @pytest.mark.integration
  def test_product_line_with_fixture(fixture_app_id):
      # Uses fixture for repeatable, schema-isolated testing
  ```

---

## 4. How Agents Should Use These Skills

### For Architecture Questions
Agent should:
1. Check `SYSTEM_CONSTRAINTS.md` first (what's non-negotiable?)
2. Reference `DECISION_FRAMEWORKS.md` (how do we think about this?)
3. Propose using existing patterns from `COMMON_PATTERNS.md`

### For Feature Development
Agent should:
1. Follow `PRODUCT_LINE_EXPANSION.md` checklist
2. Extend `mapping_contract.json` using `CONTRACT_DRIVEN_DESIGN.md` patterns
3. Create tests using `TESTING_DATA_INTEGRITY.md` approach
4. Measure impact using `PERFORMANCE_PROFILING.md` tools

### For Problem-Solving
Agent should:
1. Check `SYSTEM_CONSTRAINTS.md` for known gotchas
2. Reference `DECISION_FRAMEWORKS.md` for decision criteria
3. Propose data-driven validation (never assume)
4. Suggest measurement before optimization

---

## 5. Integration with Existing copilot-instructions.md

Your current `copilot-instructions.md` is excellent and should remain the **primary reference**. These skills are **supplementary:**

- `copilot-instructions.md` = Core operating principles, development philosophy, critical files
- `.github/skills/*.md` = Specific playbooks & decision frameworks for product expansion

**Recommendation:** Add to `copilot-instructions.md`:
```markdown
### For Product-Line Expansion
See `.github/skills/` directory:
- PRODUCT_LINE_EXPANSION.md - Step-by-step playbook
- CONTRACT_DRIVEN_DESIGN.md - How to extend mapping contracts
- TESTING_DATA_INTEGRITY.md - Validation approach for new features
- PERFORMANCE_PROFILING.md - How to measure, not guess
```

---

## 6. Implementation Roadmap

### Phase 1: Foundational Skills (Week 1)
1. Create `SYSTEM_CONSTRAINTS.md` (copy from ARCHITECTURE.md + new gotchas)
2. Create `DECISION_FRAMEWORKS.md` (extract from copilot-instructions.md)
3. Create `COMMON_PATTERNS.md` (code examples from xml_extractor/)

### Phase 2: Product-Line Tools (Week 2)
4. Create `PRODUCT_LINE_EXPANSION.md` (playbook + checklist)
5. Create `CONTRACT_DRIVEN_DESIGN.md` (philosophy + examples)

### Phase 3: Testing & Performance (Week 3)
6. Create `TESTING_DATA_INTEGRITY.md` (test patterns + fixtures)
7. Create `PERFORMANCE_PROFILING.md` (measurement tools & decision trees)

### Phase 4: Continuous Improvement
8. Review skills after each product-line expansion
9. Document new gotchas & patterns as they emerge
10. Update decision frameworks based on outcomes

---

## 7. Making Copilot Skills Work Effectively

### Best Practices

1. **Keep Files Focused**
   - One skill = one decision domain
   - Use cross-references (not duplication)
   - Max 300-400 lines per skill

2. **Use Concrete Examples**
   - Code samples from actual codebase
   - Real decision scenarios & outcomes
   - Before/after comparisons for patterns

3. **Make Checklist-Driven**
   - Playbooks should be executable (not aspirational)
   - Decision frameworks should have decision trees
   - Each skill should be actionable in 30 minutes

4. **Maintain Currency**
   - Tag skills with "Last updated: YYYY-MM-DD"
   - Document when constraints change
   - Mark deprecated patterns as such

### Testing Your Skills

When you create a new product-line feature:
1. **Without skills:** How much context did the agent need?
2. **With skills:** Did the agent avoid the common traps?
3. **Iterate:** Add gotchas to `SYSTEM_CONSTRAINTS.md`

---

## 8. Advanced Considerations for Product-Line Scalability

### Multi-Tenant Considerations
- Each product line uses schema isolation (`[product-sandbox]` vs `[product-prod]`)
- Separate mapping contracts per product line
- Shared XML parser + validator, product-specific DataMapper extensions
- Unified metrics/monitoring (cross-product throughput dashboard)

### Evolutionary Architecture Pattern
```
Generation 1 (Current): Single product line, single mapping contract
                         ↓
Generation 2 (Expansion): Multiple product lines, schema isolation
                         Shared parsing/validation, product-specific mapping
                         ↓
Generation 3 (Platform): Configuration-driven product registration
                         Plugin architecture for custom DataMapper extensions
                         Unified performance monitoring & auto-tuning
```

Your **current skills should support Generation 2 easily**. Generation 3 would require new skills.

---

## Summary

By creating these 7 skill files in `.github/skills/`, you enable Copilot to:

✅ Understand non-negotiable system constraints  
✅ Apply decision frameworks consistently  
✅ Follow proven patterns for product-line expansion  
✅ Build data integrity into new features from day 1  
✅ Measure performance instead of guessing  
✅ Avoid reintroducing known gotchas  
✅ Stay aligned with contract-driven architecture  

This transforms Copilot from a "code generator" into a **domain-aware coding partner** that understands your system's philosophy, constraints, and best practices.

**Next Step:** Start with Phase 1 (create the foundational 3 skills), then iterate as you build your first new product line.
