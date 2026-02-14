# GitHub Copilot Skills for XML Database Extraction System

**Status:** Complete (Foundational Skills)  
**Last Updated:** February 14, 2026  
**Purpose:** Enable AI agents to understand and extend the XML Database Extraction System.

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

### I Need to Add a New Feature/Field
→ Check **[common-patterns](common-patterns/SKILL.md)** for copy-paste examples

### I'm Unsure About an Architecture Decision
→ See **[decision-frameworks](decision-frameworks/SKILL.md)** for decision trees

### I Hit a Strange Bug or Want to Avoid Known Issues
→ Check **[system-constraints](system-constraints/SKILL.md)** for non-negotiables and gotchas

### I Need to Refactor Existing Code
→ Review **[refactor](refactor/SKILL.md)** for refactoring workflow and plan template

### I Need to Make Data-Sensitive Code Changes
→ Review **[system-constraints](system-constraints/SKILL.md)** for constraints and code review checklist

---

## Skills in This Directory

| Skill | Purpose | Audience |
|------|---------|----------|
| **[system-constraints](system-constraints/)** | Non-negotiable principles, known gotchas, code review checklist | All developers, code reviewers |
| **[decision-frameworks](decision-frameworks/)** | How to make trade-off decisions: testing vs speed, complexity vs clarity, performance tuning | Architects, senior developers |
| **[common-patterns](common-patterns/)** | Tested, reusable code patterns for parsing, mapping, validation, database ops, testing | All developers |
| **[refactor](refactor/)** | Refactoring guidance tailored to this repo (Python, JSON, SQL) | All developers |

---

## How Copilot Should Use These Skills

### When You Ask Copilot to Add a Feature

**Good prompt:**
> "Add support for healthcare providers to the mapping contract. Follow SYSTEM_CONSTRAINTS for contract-driven design and atomicity."

**Copilot will:**
1. Read [system-constraints](system-constraints/SKILL.md) to understand non-negotiables
2. Check [common-patterns](common-patterns/SKILL.md) for similar examples
3. Follow contract-driven approach (not hardcode)
4. Write tests using patterns from common-patterns
5. Use [decision-frameworks](decision-frameworks/SKILL.md) for trade-off decisions

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

See [common-patterns](common-patterns/SKILL.md) for copy-paste examples.

---

## Continuous Improvement

### How to Keep Skills Current

**After Each Product-Line Expansion:**
1. Review if agents made good decisions
2. Document any new patterns discovered
3. Add new gotchas to system-constraints/SKILL.md
4. Update common-patterns/SKILL.md with new examples

**Regular Maintenance:**
- Update "Last Updated" dates when files change
- Review decision frameworks quarterly
- Ensure code patterns match current style
- Remove outdated or inaccurate information

---

## Integration with Existing Documentation

**Relationship:**
```
copilot-instructions.md
├─ Core operating principles (use this first)
├─ Development standards
├─ Testing philosophy
└─ References .github/skills/ for detailed playbooks

.github/skills/*/SKILL.md
├─ System constraints (non-negotiables and gotchas)
├─ Decision frameworks (architecture tradeoffs)
├─ Common patterns (copy-paste examples)
└─ Refactor guidance (repo-specific refactoring)
```

**Start here:** `copilot-instructions.md` (principles)  
**Deep dive:** `.github/skills/*/SKILL.md` (specific guidance)  
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
- [System Architecture](../../docs/architecture-project-blueprint.md)
- [Copilot Instructions](../copilot-instructions.md)

**Performance Data:**
- [FINAL_PERFORMANCE_SUMMARY.md](../../performance_tuning/FINAL_PERFORMANCE_SUMMARY.md)
- [Archived Analysis](../../performance_tuning/archived_analysis/)

**Code Examples:**
- [Data Mapper](../../xml_extractor/mapping/data_mapper.py)
- [Migration Engine](../../xml_extractor/database/migration_engine.py)
- [Integration Tests](../../tests/integration/)

---

## Frequently Asked Questions

**Q: How do I know if my approach is right?**  
A: Check [decision-frameworks](decision-frameworks/SKILL.md) for decision trees

**Q: Can I copy an existing code pattern?**  
A: Yes! See [common-patterns](common-patterns/SKILL.md) for tested, reusable examples

**Q: What's off-limits or non-negotiable?**  
A: See [system-constraints](system-constraints/SKILL.md) for non-negotiables

**Q: What are common bugs to avoid?**  
A: See [system-constraints](system-constraints/SKILL.md) "Known Gotchas" section

**Q: How do I add a new product line?**  
A: Follow contract-driven design principles in [system-constraints](system-constraints/SKILL.md) and reference existing patterns in [common-patterns](common-patterns/SKILL.md)

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

*Last Updated: February 14, 2026*
