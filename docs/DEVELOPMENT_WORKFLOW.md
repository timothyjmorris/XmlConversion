# Development Workflow: Test-First Requirement

## Philosophy

All code changes require tests to pass **before committing**. This ensures:
- ✅ Tests catch regressions immediately
- ✅ No ambiguity about whether the code or test is wrong
- ✅ Commits to the repository are always passing
- ✅ Confidence in production deployments

## Workflow

### 1. Make Code Changes
```powershell
# Edit code files
notepad xml_extractor/mapping/data_mapper.py
```

### 2. Run Tests Immediately
```powershell
# Run all tests before committing
python tests/run_comprehensive_suite.py

# Or run specific test category
python -m pytest tests/unit -v
python -m pytest tests/contracts -v
python -m pytest tests/integration -v
```

### 3. Fix Any Failures
- **Code issue**: Fix the implementation
- **Test issue**: Update the test to match new behavior (with good reason)
- **Contract issue**: Update `config/mapping_contract.json` to match database schema

### 4. Commit (Pre-commit Hook Validates)
```powershell
git add .
git commit -m "Feature description"
```

The **pre-commit hook automatically runs** the comprehensive test suite. If tests fail, the commit is blocked.

## Pre-Commit Hook

**Location**: `.git/hooks/pre-commit`

**When it runs**: Before every `git commit`

**What it does**:
1. Runs `tests/run_comprehensive_suite.py`
2. Checks all test categories (contracts, unit, integration, e2e)
3. Blocks commit if any tests fail
4. Prints clear error messages showing which tests failed

**To bypass** (NOT RECOMMENDED):
```powershell
git commit --no-verify
```

Only use `--no-verify` in emergencies and document why.

## Test Categories

| Category | Tests | Command | Purpose |
|----------|-------|---------|---------|
| Contracts | 19 | `pytest tests/contracts -v` | Validate mapping contract + database schema alignment |
| Unit | 170 | `pytest tests/unit -v` | Core logic + transformations |
| Integration | 25 | `pytest tests/integration -v` | Real database operations |
| E2E | 0 (future) | `pytest tests/e2e -v` | Full pipeline end-to-end |

## Contract/Database Schema Validation

When contract tests fail due to schema mismatches:

1. **Read the error output** - Now shows detailed mismatch report with recommendations
2. **Check the diff file** - `tests/contracts/mapping_contract_schema_diff.json`
3. **Update the contract** - Edit `config/mapping_contract.json` to match database
4. **Re-run tests** - Verify the fix resolves the issue

Example: `use_alloy_service_flag` was marked as `nullable: true` in contract but is `NOT NULL` in database → Fix: set `nullable: false, required: true`

## Quality Gates

All of these must pass before commit:
- ✅ All contracts tests pass (19/19)
- ✅ All unit tests pass (170/170)  
- ✅ All integration tests pass (25/25)
- ✅ Contract/database schema perfectly aligned

**Total**: 214 tests must pass

## Common Issues & Fixes

### Issue: "Contract/DB schema mismatches found"
**Cause**: Mapping contract doesn't match actual database column definitions  
**Fix**: Update contract to match database (recommendations provided in test output)  
**Example**: nullable/required mismatch, data type mismatch, length mismatch

### Issue: Test passes in isolation but fails in suite
**Cause**: Test depends on state from previous tests or database state  
**Fix**: Ensure tests are isolated; use fixtures to reset state; check test order

### Issue: "Mapping types not exercised by sample XML"
**Cause**: A mapping type is defined in contract but never tested  
**Fix**: Add sample XML data that exercises that mapping type (see `config/samples/`)

## Responsibilities

- **Developer**: Run tests before committing, fix failures
- **Pre-commit hook**: Automatic enforcement - blocks bad commits
- **CI/CD** (future): Additional checks on PR/merge
- **Code review**: Verify tests match implementation intent

## References

- Test suite: [tests/run_comprehensive_suite.py](../../tests/run_comprehensive_suite.py)
- Contract validator: [tests/contracts/test_mapping_contract_schema.py](../contracts/test_mapping_contract_schema.py)
- Mapping contract: [config/mapping_contract.json](../../config/mapping_contract.json)
- Sample XML files: [config/samples/](../../config/samples/)
