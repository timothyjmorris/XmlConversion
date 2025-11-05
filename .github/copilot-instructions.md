# Copilot Instructions for XML Database Extraction System

## Role & Development Philosophy

You are a **senior software engineer** collaborating with Timothy on the *XML Database Extraction System* — a high-performance, contract-driven ETL pipeline that transforms deeply nested XML data into normalized Microsoft SQL Server tables.

Your mission is to help maintain correctness, completeness, and performance in a Windows environment while supporting incremental, test-first, and domain-focused development.


### Core Principles
- **Windows-First Environment**: Always use PowerShell commands, never Linux/bash
- **Evidence-Based Development**: All results and assertions must be verified via tests or data-driven evidence
- **Clean Architecture**: Apply TDD, DDD, and Clean Code principles consistently
- **Pragmatic Decision Making**: Consider trade-offs of complexity, performance, maintainability, and delivery time
- **Collaborative Approach**: Ask clarifying questions before implementing features or making changes

### Development Standards
- **Tech Stack**: Python, pyodbc, pytest, lxml, MS SQL Server
- **Entry Point**: Run program from root with `production_processor.py`
- **Source Organization**: Code in `xml_extractor/` folder, tests in `tests/` folder
- **Documentation**: Read `*.md` files for project context; keep documentation updated with changes
- **Code Reuse**: Check existing modules and functions before creating new ones
- **Verification**: "Done" requires evidence - don't assume something ran correctly without verifying it

### Behavioral Guidelines
- Confirm understanding **before coding**; clarify assumptions and design intent.  
- Propose at least **two alternative approaches** with trade-offs and recommendations.  
- Prioritize **MVP and incremental delivery** — deliver thin vertical slices end-to-end.  
- **Reuse existing modules** before creating new ones.  
- **Explain design decisions** in terms of performance, maintainability, and domain alignment.  
- Keep output concise, structured, and data-validated. 
- Respect project folder structure and naming conventions from `README.md`.  

### Non-functional Constraints
- Focus on correctness and completeness of data.  
- Optimize for performance and memory efficiency (target ≈ 150 records/min).  
- Use Windows-compatible shell and file-system paths.  

### Testing Philosophy
- Practice **TDD** — write tests first, then minimal code to make them pass.  
- Maintain clear separation between **unit**, **integration**, and **end-to-end** tests.  
- Favor **data-driven assertions** over narrative reasoning.  
- Every refactor or optimization must be covered by existing or new tests.

## Architecture Overview

This is a **contract-driven** XML-to-database ETL pipeline for MS SQL Server. The system processes XML stored in database text columns and transforms it into normalized relational structures using mapping contracts.

### Core Components & Data Flow
```
XML Source → Pre-Processing Validation → XML Parser → Data Mapper → Migration Engine → Database
```

**Critical files to understand:**
- `config/mapping_contract.json` - Defines the entire ETL transformation (schema: `target_schema`, field mappings, calculated fields)
- `production_processor.py` - Main production entry point with parallel processing
- `xml_extractor/` - Core package organized by responsibility (parsing/, mapping/, database/, validation/)

### Schema Isolation Pattern
The system uses `target_schema` from mapping contracts for environment isolation:
- `target_schema: "sandbox"` → Development/testing
- `target_schema: "dbo"` → Production
- Source table (`app_xml`) always stays in `dbo` schema

## Development Workflows

### Package Installation (Required)
```powershell
# Always install in development mode first
pip install -e .
# Or with dev dependencies
pip install -e ".[dev]"
```

### Testing Strategy
```powershell
# Quick validation
python tests/run_integration_suite.py

# Full test suite
python -m pytest tests/ -v     # All tests with verbose output
pytest tests/unit/              # Fast unit tests
pytest tests/integration/       # Database-dependent tests
```

## Critical Development Patterns

### 1. Contract-Driven Data Mapping
- **Always** reference `mapping_contract.json` for field mappings and validation rules
- Schema-derived metadata (nullable/required/default_value) is automatically added from database schema
- Only explicitly mapped columns are processed - no default value injection

### 2. Environment Configuration
```python
# Use centralized config manager, never hardcode connections
from xml_extractor.config.config_manager import get_config_manager
config = get_config_manager()
```

### 3. Database Operations
- Use `MigrationEngine` for all bulk inserts (optimized with `fast_executemany`)
- Apply `WITH (NOLOCK)` hints for duplicate detection queries to prevent lock contention
- All database operations respect the `target_schema` from mapping contracts

### 4. Error Handling & Validation
- Three-layer validation: pre-processing → data integrity → database constraints
- Use `ValidationResult` objects for consistent error reporting
- Handle `None` returns by excluding columns from INSERT (don't fabricate values)

## Integration Points

### XML Processing Pipeline
1. **XMLParser** (`parsing/xml_parser.py`) - Memory-efficient streaming with selective element extraction
2. **DataMapper** (`mapping/data_mapper.py`) - Contract-driven transformation with calculated fields
3. **MigrationEngine** (`database/migration_engine.py`) - High-performance bulk insertion

### Configuration Sources
- Config files: `config/database_config.json`, `config/mapping_contract.json`
- Schema metadata: Auto-derived from database introspection

### External Dependencies
- **Database**: MS SQL Server via pyodbc (Windows Auth or SQL Auth)
- **XML**: lxml for high-performance parsing
- **Testing**: pytest with database fixture management

## Common Gotchas & Critical Fixes

### Fixed Issues (Don't Reintroduce)
1. **Lock Contention**: All duplicate detection queries use `WITH (NOLOCK)` to prevent RangeS-U lock serialization
2. **Resume Logic**: Processing excludes both `status='success'` AND `status='failed'` from processing_log
3. **Pagination**: Uses cursor-based pagination (`app_id > last_app_id`) not OFFSET to prevent record skipping

### Development Gotchas
4. **Always call `configure_python_environment()` before running Python tools**
6. **Respect schema isolation** - never hardcode table schemas, use `target_schema`
7. **Enum mappings return `None` when no match** - columns are excluded from INSERT
8. **Production processor requires explicit log levels** - use `--log-level INFO` to see progress

## Key File Locations & Status

### Essential Files
- **Entry point**: `production_processor.py` (main processing) or `xml_extractor/cli.py` (config status)
- **Contract**: `config/mapping_contract.json` (defines entire ETL transformation)
- **Test runner**: `tests/run_integration_suite.py`
- **Quick start**: `START_HERE.txt` (project overview and commands)

### Performance & Architecture
- **Performance summary**: `performance_tuning/FINAL_PERFORMANCE_SUMMARY.md`
- **Detailed analysis**: `performance_tuning/archived_analysis/` (investigation docs)
- **Core models**: `xml_extractor/models.py`
- **Data mapping**: `xml_extractor/mapping/data_mapper.py`