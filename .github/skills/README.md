# GitHub Copilot Skills for XML Database Extraction System

**Status:** Phase 1 Complete (Foundational Skills)  
**Date:** January 22, 2026  
**Purpose:** Enable AI agents to understand and extend the XML Database Extraction System for new product lines.

---

## Overview

This directory contains structured knowledge that enables GitHub Copilot and other AI agents to:

✅ **Understand system architecture** - Why design decisions were made  
✅ **Avoid reintroducing bugs** - Known gotchas and how to prevent them  
✅ **Make consistent decisions** - Decision frameworks for architecture/performance/scope  
✅ **Reuse proven patterns** - Copy-paste-ready code examples  
✅ **Extend safely** - Contract-driven design enables product-line expansion  

---

## Documentation Principles

- **Organized and purposeful:** Every document has a clear, stable purpose and audience.
- **Accuracy is critical:** Incorrect or outdated docs are dangerous; keep docs aligned with code.
- **Qualified content:** Documentation has value and cost; we continuously qualify and prune.
- **Minimize overlap:** Reduce duplicate content across docs to ease updates and discovery.
- **WIP isolation:** Temporary or work-in-progress content belongs in a separate `wip/` folder, not mixed with canonical docs.
- **No temporal summaries in repo:** Status reports or audit summaries live in chat/PR comments, not as persistent files.

Where to place docs:
- Canonical references → `docs/` or root README(s) where appropriate
- Agent skills → `.github/skills/`
- Operational guides → `OPERATOR_GUIDE.md`, `DEPLOYMENT_GUIDE.md`
- Temporary/WIP → `wip/` (can be organized but not treated as canonical)

---

## Quick Reference: Which Skill to Read?

### I'm Adding a New Product Line
→ Start with **[PRODUCT_LINE_EXPANSION.md](PRODUCT_LINE_EXPANSION.md)** (once it exists)

### I Need to Add a New Feature/Field
→ Check **[COMMON_PATTERNS.md](COMMON_PATTERNS.md)** for copy-paste examples

### I'm Unsure About an Architecture Decision
→ See **[DECISION_FRAMEWORKS.md](DECISION_FRAMEWORKS.md)** for decision trees

### I Hit a Strange Bug
→ Check **[SYSTEM_CONSTRAINTS.md](SYSTEM_CONSTRAINTS.md)** for known gotchas

### I Need to Make Code Changes
→ Review **[SYSTEM_CONSTRAINTS.md](SYSTEM_CONSTRAINTS.md)** - "Code Review Checklist"

---

## Files in This Directory

### Phase 1: Foundational Skills ✅ COMPLETE

| File | Purpose | Audience |
|------|---------|----------|
| **[SYSTEM_CONSTRAINTS.md](SYSTEM_CONSTRAINTS.md)** | Non-negotiable principles, known gotchas, code review checklist | All developers, code reviewers |
| **[DECISION_FRAMEWORKS.md](DECISION_FRAMEWORKS.md)** | How to make trade-off decisions: testing vs speed, complexity vs clarity, performance tuning | Architects, senior developers |
| **[COMMON_PATTERNS.md](COMMON_PATTERNS.md)** | Tested, reusable code patterns for parsing, mapping, validation, database ops, testing | All developers |

### Phase 2: Product-Line Expansion Tools (TODO)

| File | Purpose | Status |
|------|---------|--------|
| **[PRODUCT_LINE_EXPANSION.md](PRODUCT_LINE_EXPANSION.md)** | Step-by-step playbook for adding new product lines | Not yet created |
| **[CONTRACT_DRIVEN_DESIGN.md](CONTRACT_DRIVEN_DESIGN.md)** | Deep dive into mapping contract philosophy and extension patterns | Not yet created |

### Phase 3: Testing & Performance (TODO)

| File | Purpose | Status |
|------|---------|--------|
| **[TESTING_DATA_INTEGRITY.md](TESTING_DATA_INTEGRITY.md)** | How to prove new features work correctly | Not yet created |
| **[PERFORMANCE_PROFILING.md](PERFORMANCE_PROFILING.md)** | How to measure, baseline, and optimize performance | Not yet created |

---

## How Copilot Should Use These Skills

### When You Ask Copilot to Add a Feature

**Good prompt:**
> "Add support for healthcare providers to the mapping contract. Use the CONTRACT_DRIVEN_DESIGN pattern and follow SYSTEM_CONSTRAINTS for atomicity."

**Copilot will:**
1. Read [SYSTEM_CONSTRAINTS.md](SYSTEM_CONSTRAINTS.md) to understand non-negotiables
2. Check [COMMON_PATTERNS.md](COMMON_PATTERNS.md) for similar examples
3. Follow contract-driven approach (not hardcode)
4. Write tests using patterns from COMMON_PATTERNS
5. Measure performance (if applicable)

**Copilot will avoid:**
- ❌ Hardcoding field mappings in code
- ❌ Removing atomicity "for simplicity"
- ❌ Assuming optimizations work (will measure first)
- ❌ Reintroducing known gotchas (lock contention, OFFSET pagination, etc.)

---

## System Constraints Summary

### 1. Contract-Driven Architecture
All transformations defined in `config/mapping_contract.json` (not code).

### 2. Schema Isolation Pattern
All database operations respect `target_schema` from contract (enables sandbox/dbo/prod separation).

### 3. Atomic Transactions
Every application succeeds or fails as a complete unit (prevents orphaned records).

### 4. Foreign Key Ordering
Tables inserted in dependency order (app_base → contact_base → children → processing_log).

### 5. Windows-First Environment
PowerShell commands, pyodbc connections, Windows paths (not bash/SQLAlchemy/Linux paths).

### 6. Data Integrity > Speed
Never sacrifice correctness for performance. Measure before optimizing.

---

## Decision Frameworks Summary

### Testing vs. Speed
- Always test-first for data-affecting changes
- Use data-driven assertions (query database for truth)
- Test robustness, not happy path

### Complexity vs. Clarity
- Reuse before creating new abstractions
- No backward-compatibility shims
- No premature optimizations (measure first)

### Performance Decisions
- Establish baseline before optimizing
- Measure impact (must be >20% improvement for code complexity cost)
- Target is 3,500 records/min, not "maximum speed"

### Scope Management
- Thin vertical slices (end-to-end, one feature at a time)
- Contract extends existing structure
- Schema isolation per product line for testing

---

## Common Patterns Summary

**Parsing:** Selective element extraction, streaming for large files  
**Mapping:** Contract-driven (standard), calculated fields, product-line dispatch  
**Validation:** Three-layer validation (XML structure → contract compliance → DB constraints)  
**Database:** Atomic transactions, bulk insert with batching, resume with duplicate detection  
**Testing:** Unit tests (isolated logic), integration tests (full pipeline), schema-isolated fixtures  

See [COMMON_PATTERNS.md](COMMON_PATTERNS.md) for copy-paste examples.

---

## Roadmap

### Phase 1: Foundation (COMPLETE ✅)
- ✅ SYSTEM_CONSTRAINTS.md - Non-negotiable principles
- ✅ DECISION_FRAMEWORKS.md - How we think about tradeoffs
- ✅ COMMON_PATTERNS.md - Reusable code examples

### Phase 2: Expansion (NEXT)
- [ ] PRODUCT_LINE_EXPANSION.md - Playbook for new product lines
- [ ] CONTRACT_DRIVEN_DESIGN.md - Philosophy + examples

### Phase 3: Verification (AFTER PHASE 2)
- [ ] TESTING_DATA_INTEGRITY.md - Test patterns for new features
- [ ] PERFORMANCE_PROFILING.md - Measurement tools + decision trees

### Phase 4: Continuous Improvement
- [ ] Review skills after each product-line expansion
- [ ] Add new gotchas to SYSTEM_CONSTRAINTS
- [ ] Update decision frameworks based on outcomes

---

## Integration with Existing Documentation

**Relationship:**
```
copilot-instructions.md
├─ Core operating principles (use this first)
├─ Development standards
├─ Testing philosophy
└─ References .github/skills/ for detailed playbooks

.github/skills/*.md
├─ Specific playbooks (product-line expansion)
├─ Decision frameworks (architecture tradeoffs)
├─ Code patterns (copy-paste examples)
└─ Gotchas (what to avoid)
```

**Start here:** `copilot-instructions.md` (principles)  
**Deep dive:** `.github/skills/*.md` (specific guidance)  
**Reference code:** `xml_extractor/` (working examples)

---

## How to Keep These Skills Current

### After Each Product-Line Expansion
1. Did Copilot make good decisions?
2. Did it avoid the known gotchas?
3. Are there new patterns to document?
4. Any new constraints discovered?

### Quarterly Review
1. Are decision frameworks still accurate?
2. Have we changed how we approach problems?
3. Do the code patterns match current style?
4. Should we consolidate or split any files?

### Tag Each File with "Last Updated"
```markdown
**Last Updated:** January 22, 2026
```

This helps identify stale information.

---

## Success Metrics

You'll know these skills are working when Copilot:

✅ **Avoids architectural anti-patterns**
- Doesn't hardcode mappings
- Preserves schema isolation
- Maintains atomicity

✅ **Makes consistent decisions**
- Proposes contract extensions (not code branching)
- Measures before optimizing
- Uses existing patterns

✅ **Prevents known bugs**
- Includes WITH (NOLOCK) on duplicate detection
- Uses cursor-based pagination (not OFFSET)
- Tests resume logic with intentional failures

✅ **Speeds up development**
- Finds copy-paste patterns from COMMON_PATTERNS
- Uses decision frameworks to settle debates
- References constraints to rule out bad ideas

---

## Quick Links

**Core References:**
- [XML Database Extraction System README](../../README.md)
- [System Architecture](../../ARCHITECTURE.md)
- [Copilot Instructions](../copilot-instructions.md)

**Performance Data:**
- [FINAL_PERFORMANCE_SUMMARY.md](../../performance_tuning/FINAL_PERFORMANCE_SUMMARY.md)
- [Archived Analysis](../../performance_tuning/archived_analysis/)

**Code Examples:**
- [Data Mapper](../../xml_extractor/mapping/data_mapper.py)
- [Migration Engine](../../xml_extractor/database/migration_engine.py)
- [Integration Tests](../../tests/integration/)

---

## Questions?

If you're unsure which skill to read:

**Q: How do I add a new product line?**  
A: See PRODUCT_LINE_EXPANSION.md (will be created in Phase 2)

**Q: How do I know if my approach is right?**  
A: Check DECISION_FRAMEWORKS.md for decision trees

**Q: Can I copy this code pattern?**  
A: See COMMON_PATTERNS.md for tested examples

**Q: What's off-limits?**  
A: See SYSTEM_CONSTRAINTS.md for non-negotiables

**Q: What went wrong last time?**  
A: See SYSTEM_CONSTRAINTS.md "Known Gotchas" section

---

## Contributing to Skills

When you discover a new pattern or gotcha:

1. **Document it** - Add to relevant skill file
2. **Add example** - Include code sample
3. **Explain rationale** - Why does this matter?
4. **Reference it** - Link from other files
5. **Update checklist** - Add to code review items if applicable

Format:
```markdown
### [New Pattern/Gotcha Name]
**When to use:** ...
**Why this matters:** ...
**Example:** ...
**Prevention:** ...
```

---

*Last Updated: January 22, 2026*  
*Next Review: After first product-line expansion*
