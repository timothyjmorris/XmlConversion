---
name: refactor
description: Surgical refactoring for the XML Database Extraction System (Python ETL). Improve maintainability without changing behavior by extracting functions, simplifying logic, adding typing, and reducing code smells while preserving data integrity and contract-driven behavior.
license: MIT
metadata:
  last-updated: "2026-02-14"
  project: xml-database-extraction
---

# Refactor

## Overview

Improve code structure and readability without changing external behavior. Refactoring is gradual evolution, not a rewrite. Use this skill for focused, low-risk improvements in existing code.

## When to Use

- Code is hard to understand or maintain
- Functions or modules are too large
- Code smells block feature work
- Tests exist or can be added first
- The user asks to clean up, refactor, or simplify code

## Repository Context (Non-Negotiables)

- Contract-driven mapping lives in config files (no hardcoded mappings)
- Schema isolation is required; read `target_schema` from contracts
- Never execute DDL or data deletion in application code
- Windows-first: use PowerShell and pyodbc
- Data integrity beats speed

See the system constraints skill for details: ../system-constraints/SKILL.md

## Style Guides (Use in This Repo)

### Python (PEP 8)

- 4 spaces for indentation, no tabs
- Keep lines readable; prefer implied line continuation with parentheses
- Use explicit imports; avoid wildcard imports
- Keep naming consistent: `snake_case` for functions/variables, `CapWords` for classes
- Consistency within this project beats generic guidance

Reference: https://peps.python.org/pep-0008/

### JSON (Google JSON Style Guide)

- Use double quotes for strings
- No comments in JSON files
- Use meaningful property names; arrays should use plural names
- Prefer strings for enum-like values
- Avoid nulls unless required by a contract

Reference: https://google.github.io/styleguide/jsoncstyleguide.xml

### SQL (SQL Style Guide)

- Uppercase SQL keywords (`SELECT`, `FROM`, `WHERE`)
- Use consistent indentation and alignment
- Prefer `snake_case` identifiers and avoid quoted identifiers
- Use `AS` for aliases
- Avoid vendor-specific features unless required

Reference: https://www.sqlstyle.guide/

## Refactor Plan Template

```markdown
## Refactor Plan: [title]

### Current State
[Brief description of how things work now]

### Target State
[Brief description of how things will work after]

### Affected Files
| File | Change Type | Dependencies |
|------|-------------|--------------|
| path | modify/create/delete | blocks X, blocked by Y |

### Execution Plan

#### Phase 1: Types and Interfaces
- [ ] Step 1.1: [action] in `file.py`
- [ ] Verify: [how to check it worked]

#### Phase 2: Implementation
- [ ] Step 2.1: [action] in `file.py`
- [ ] Verify: [how to check]

#### Phase 3: Tests
- [ ] Step 3.1: Update tests in `tests/...`
- [ ] Verify: Run `python -m pytest tests/ -v`

#### Phase 4: Cleanup
- [ ] Remove deprecated code
- [ ] Update documentation

### Rollback Plan
If something fails:
1. [Step to undo]
2. [Step to undo]

### Risks
- [Potential issue and mitigation]
```

## Refactoring Workflow

1. Prepare: confirm tests, baseline behavior, and scope
2. Isolate: make one small change at a time
3. Verify: run relevant tests after each step
4. Document: update comments or docs only when needed

## Exemplar-Driven Refactoring

Use exemplar code in this repo to guide refactors instead of generic patterns. Start by locating a similar implementation and align changes with it.

Suggested exemplar sources (paths relative to repo root):

- XML parsing: ../../../xml_extractor/parsing/xml_parser.py
- Data mapping: ../../../xml_extractor/mapping/data_mapper.py
- Database writes: ../../../xml_extractor/database/migration_engine.py
- Validation: ../../../xml_extractor/validation/validator.py
- Contracts: ../../../config/mapping_contract.json
- RL contract: ../../../config/mapping_contract_rl.json
- Integration tests: ../../../tests/integration/

If you need to extract more exemplars, use the blueprint prompt:

- ../../../.github/prompts/code-exemplars-blueprint-generator.prompt.md

## Python-Focused Refactor Examples (Repo-Style)

### Extract Function

```python
# Before: long function with mixed concerns
def process_app(xml_text, mapper, engine):
    parsed = parse_xml(xml_text)
    mapped = mapper.map_record(parsed)
    validate_mapping(mapped)
    engine.migrate(mapped)
    log_success(parsed.get("app_id"))

# After: smaller, focused helpers
def process_app(xml_text, mapper, engine):
    parsed = parse_xml(xml_text)
    mapped = map_and_validate(parsed, mapper)
    engine.migrate(mapped)
    log_success(parsed.get("app_id"))

def map_and_validate(parsed, mapper):
    mapped = mapper.map_record(parsed)
    validate_mapping(mapped)
    return mapped
```

### Guard Clauses

```python
# Before
def load_contract(path):
    if path is not None:
        if os.path.exists(path):
            return read_contract(path)
        else:
            raise FileNotFoundError(path)
    else:
        raise ValueError("Missing path")

# After
def load_contract(path):
    if path is None:
        raise ValueError("Missing path")
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return read_contract(path)
```

### Replace Stringly-Typed Values

```python
from enum import Enum

class Status(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"

def is_terminal(status: Status) -> bool:
    return status in {Status.SUCCESS, Status.FAILED}
```

### Use Dataclasses for Structured Records

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class MappingResult:
    app_id: int
    target_table: str
    status: str
    error: Optional[str] = None
```

### Consolidate Mapping Validation

```python
# Before: mapping + validation spread across call sites
mapped = mapper.map_record(parsed)
if not validator.validate_mapping(mapped).is_valid:
    return fail(app_id, "mapping")
engine.migrate(mapped)

# After: centralize and return consistent results
def map_with_validation(parsed, mapper, validator):
    mapped = mapper.map_record(parsed)
    result = validator.validate_mapping(mapped)
    if not result.is_valid:
        return None, result
    return mapped, result
```

### Preserve Contract-Driven Behavior

```python
# Before: hardcoded mapping
record["status_code"] = STATUS_MAP.get(raw_status)

# After: rely on contract enum mappings
mapped = mapper.apply_enum_mappings(record, mapping_contract)
```

## SQL and JSON Refactor Tips (Repo-Style)

### SQL

- Keep queries formatted and aligned for readability
- Use parameterized queries with pyodbc placeholders (`?`)
- Preserve required `WITH (NOLOCK)` usage in duplicate detection
- Do not add DDL or data deletion logic in application code

```sql
-- Preferred formatting
SELECT app_id,
             status
    FROM [sandbox].[processing_log] WITH (NOLOCK)
 WHERE app_id = ?
     AND status IN ('success', 'failed');
```

### JSON

- Keep configuration files valid JSON (no comments)
- Use stable, descriptive keys that match contracts
- Avoid reformatting keys unless the contract requires it

```json
{
    "product_line": "cc",
    "target_schema": "sandbox",
    "mappings": {
        "app_base": [
            {
                "column": "app_id",
                "source_path": "application/id",
                "type": "int",
                "nullable": false
            }
        ]
    }
}
```

## Testing and Verification

- Unit tests: `pytest tests/unit/`
- Integration tests: `pytest tests/integration/`
- Quick validation: `python tests/run_integration_suite.py`

## References

- PEP 8: https://peps.python.org/pep-0008/
- Google JSON Style Guide: https://google.github.io/styleguide/jsoncstyleguide.xml
- SQL Style Guide: https://www.sqlstyle.guide/
- System constraints skill: ../system-constraints/SKILL.md
- Code exemplars: ../../../docs/exemplars.md