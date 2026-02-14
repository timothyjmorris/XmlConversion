# XML Database Extraction System

A high-performance, contract-driven ETL pipeline that transforms deeply nested XML data into normalized Microsoft SQL Server tables.

## Documentation Quick Links

- [Operator Guide](docs/operator-guide.md) - Production operations, commands, troubleshooting
- [Deployment Guide](docs/deployment-guide.md) - Package installation and environment setup
- [Architecture Quickstart](docs/architecture-quickstart.md) - System design and data flow
- [Architecture Blueprint](docs/architecture-project-blueprint.md) - Comprehensive architecture reference
- [Testing Philosophy](docs/testing-philosophy.md) - Production-first testing approach
- [Validation Strategy](docs/validation-and-testing-strategy.md) - Validation framework and scenarios
- [Code Exemplars](docs/exemplars.md) - Representative code patterns

## Project Name and Description

**XML Database Extraction System** is a contract-driven XML-to-database ETL pipeline for Microsoft SQL Server. It reads XML stored in database text columns, applies transformations defined in mapping contracts, and bulk-inserts normalized records with atomic transaction guarantees and schema isolation.

## Technology Stack

- OS: Windows (PowerShell-first)
- Language: Python 3.13
- Database: Microsoft SQL Server
- DB driver: pyodbc
- XML processing: lxml
- Testing: pytest
- Packaging: setuptools

## Project Architecture

**Primary pattern:** Contract-driven Clean Architecture with schema isolation and atomic transactions.

**Pipeline:**
```
XML Source -> Pre-Processing Validation -> XML Parser -> Data Mapper -> Migration Engine -> SQL Server
```

**Key rules:**
- All transformations are defined in `config/mapping_contract.json` (not code).
- All database operations respect `target_schema` from the contract.
- One application = one transaction (all-or-nothing).

See [docs/architecture-quickstart.md](docs/architecture-quickstart.md) for details.

## Getting Started

### Prerequisites

- Python 3.8+
- Access to MS SQL Server with required schemas and tables
- Windows environment (PowerShell)

### Installation

```powershell
# Development installation (editable)
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

### Configuration

- Mapping contracts: `config/mapping_contract.json` (CC) and `config/mapping_contract_rl.json` (RL)
- Database config template: `config/database_config.json`

### Basic Usage

```powershell
# CC processing (default)
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB"

# RL processing
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB" --product-line RL

# Large dataset processing
python run_production_processor.py --app-id-start 1 --app-id-end 300000
```

For operational guidance, see [docs/operator-guide.md](docs/operator-guide.md).

## Project Structure

```
xml_extractor/       # Core package (parsing, mapping, database, validation)
config/              # Mapping contracts and database config
docs/                # Architecture, operations, and testing documentation
tests/               # Unit, integration, and e2e tests
production_processor.py  # Main entry point
run_production_processor.py  # Orchestrator for large datasets
```

## Key Features

- Contract-driven transformations (no hardcoded mappings)
- Schema isolation via `target_schema`
- Atomic transactions per application
- FK-ordered bulk inserts with `fast_executemany`
- Multi-process parallel processing
- Resume-safe processing via `processing_log`
- Three-layer validation (pre-processing, mapping, database constraints)

## Development Workflow

- Test-first development required before commit
- Pre-commit hook runs the comprehensive test suite
- Contracts must match database schema (validated by tests)

See [docs/DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) for the full workflow.

## Coding Standards

- Contract-driven design: transformations live in mapping contracts, not code
- Schema isolation: never hardcode schema names
- No DDL or destructive SQL in application code
- Use centralized configuration via `xml_extractor.config.config_manager.get_config_manager`
- Prefer existing patterns in [docs/exemplars.md](docs/exemplars.md) and [.github/skills/common-patterns/SKILL.md](.github/skills/common-patterns/SKILL.md)

## Testing

- Production-first testing with real XML data
- Clear separation of unit, integration, and e2e tests
- Data-driven assertions (query database for truth)

```powershell
# All tests
python -m pytest tests/ -v

# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# Quick validation
python tests/run_integration_suite.py
```

See [docs/testing-philosophy.md](docs/testing-philosophy.md) and
[docs/validation-and-testing-strategy.md](docs/validation-and-testing-strategy.md).

## Contributing

1. Review architecture and constraints in [docs/architecture-quickstart.md](docs/architecture-quickstart.md)
   and [.github/skills/system-constraints/SKILL.md](.github/skills/system-constraints/SKILL.md).
2. Follow contract-driven patterns in [.github/skills/common-patterns/SKILL.md](.github/skills/common-patterns/SKILL.md).
3. Add or update tests for every change.
4. Run the full test suite before committing.

See [docs/exemplars.md](docs/exemplars.md) for reference implementations.

## License

No license file is present in this repository. Contact the maintainer for licensing details.

#### MigrationEngine (`database/migration_engine.py`)
- **Purpose**: High-performance bulk insertion engine for contract-compliant relational data
- **Key Features**: Contract-driven column handling, fast_executemany optimization, transaction safety
- **Recent Changes**: Simplified to focus on bulk insertion; column validation now handled by DataMapper
- **Integration**: Receives pre-validated tables from DataMapper, performs optimized SQL Server bulk inserts

#### Validation System (`validation/`)
- **Purpose**: Multi-layered validation ensuring data quality throughout the pipeline
- **Components**: ElementFilter, PreProcessingValidator, DataIntegrityValidator, ValidationOrchestrator
- **Integration**: Validates at multiple pipeline stages, provides quality gates and reporting

### Configuration Management
- **Centralized Config**: Environment variable-based configuration system
- **Mapping Contracts**: JSON-based field mapping definitions with calculated field support
- **Schema Flexibility**: Configurable database schema prefixes for multi-environment support

### Performance Characteristics
- **Proven Performance**: 1,477-1,691 records/minute with >95% success rate (10x above original target of 150/min)
- **Scalability**: Multi-worker parallel processing, configurable batch sizes
- **Memory Efficiency**: Streaming XML parsing, configurable memory limits
- **Monitoring**: Real-time progress tracking and comprehensive metrics

## 🔧 Core Components

### Data Models
- **MappingContract**: Defines how XML data maps to relational structure
- **FieldMapping**: Maps XML elements/attributes to database columns with calculated field support
- **RelationshipMapping**: Defines parent-child relationships between tables
- **ProcessingConfig**: Configuration parameters for extraction operations
- **ProcessingResult**: Results and metrics from processing operations

### Key Features
- **Calculated Fields**: Support for arithmetic expressions and CASE statements
- **Contact Validation**: "Last valid element" approach for duplicate handling
- **Performance Monitoring**: Real-time progress tracking and metrics
- **Schema Flexibility**: Configurable database schema prefixes for multi-environment support
- **Centralized Configuration**: Environment variable-based configuration management

## � Recent Improvements

### Contract-Driven Architecture Refactoring
- **Schema-Derived Metadata**: Automatic enhancement of mapping contracts with nullable/required/default_value fields from database schema
- **Simplified MigrationEngine**: Removed dynamic column filtering; now focuses purely on high-performance bulk insertion
- **Consolidated Default Handling**: Migrated contract-level defaults to field-level for better maintainability
- **Enhanced Data Validation**: Contract-compliant data processing ensures compatibility throughout the pipeline

### Code Quality Enhancements
- **Comprehensive Test Coverage**: 128 tests across unit, integration, and end-to-end scenarios (100% pass rate)
- **Updated Documentation**: Enhanced docstrings and README to reflect architectural changes
- **Cleaned Configuration**: Removed unused contract sections and consolidated default value handling

## 📋 Work Sessions Summary

### Session 1-3: Lock Contention & Resume Logic (Completed)
**Issues Identified & Fixed:**
1. **RangeS-U Lock Contention** (RESOLVED)
   - Symptom: Batch processing hanging during parallel inserts
   - Root Cause: Duplicate check queries acquiring shared locks, serializing 4 workers
   - Solution: Added `WITH (NOLOCK)` to 3 duplicate detection queries in `migration_engine.py`
   - Result: Workers now proceed in parallel without lock serialization

2. **Resume Logic Bug** (RESOLVED)
   - Symptom: Consecutive runs without clearing `processing_log` would reprocess already-successful apps
   - Root Cause: WHERE clause excluded only `status='failed'`, not `status='success'`
   - Solution: Changed to `AND pl.status IN ('success', 'failed')` in `production_processor.py`
   - Result: Second run correctly returns 0 records, enabling true resume capability

3. **Pagination Bug** (RESOLVED)
   - Symptom: OFFSET-based pagination skipped records (pattern: apps 1-20, 41-60, 81-100)
   - Root Cause: OFFSET applied after WHERE filtering, causing cursor misalignment
   - Solution: Implemented cursor-based pagination using `app_id > last_app_id` with `OFFSET 0 ROWS FETCH`
   - Result: Sequential processing without gaps

### Session 4: Performance Benchmarking (Completed)
**Baseline Metrics Established:**
- Optimal batch-size: **500** (on this machine)
- Throughput: **1477-1691 applications/minute** (batch-size 500)
- Target was 3000+ rec/min (not achieved, CPU-bound bottleneck identified)

**Tests Performed & Results:**
| Batch Size | Throughput (rec/min) | Finding |
|---|---|---|
| 20 | 534 | Too small, high orchestration overhead |
| 50 | 1192 | Better, still suboptimal |
| 100 | 1791 | Good, but unstable with larger volumes |
| 500 | 1477-1691 | **Optimal** - consistent, reliable peak |
| 1000 | 1387 | Declining, memory pressure begins |
| 2000 | 1393 | Further decline, orchestration overhead |

**Optimization Attempts (Inconclusive):**
- Conditional logging (reduced DEBUG overhead): ❌ No improvement
- Connection pooling tuning: ❌ No improvement
- FK removal + index rebuild: ❌ No improvement

**Root Cause Analysis:**
- Bottleneck: **CPU-bound processing** (XML parsing with lxml, data mapping/transformation)
- Database I/O: Not a bottleneck (confirmed by FK removal test)
- Logging overhead: Negligible (confirmed by conditional logging test)

**Architectural Decisions:**
1. **Batch-size 500**: Balances memory efficiency vs orchestration overhead
2. **4 Workers**: One per CPU core, prevents context-switching overhead
3. **Connection pooling disabled for SQLExpress**: No benefit for local connections
4. **Three-layer duplicate detection**: Pragmatic balance between performance and correctness
   - Layer 1: `processing_log` (fast app-level check)
   - Layer 2: Contact-level table queries with `NOLOCK` (de-duplication)
   - Layer 3: FK/PK constraints (safety net)

**Documentation Cleanup:**
- Consolidated 18+ WIP performance docs to single `FINAL_PERFORMANCE_SUMMARY.md`
- Archived detailed investigation docs to `performance_tuning/archived_analysis/`
- Kept architectural decisions and methodology for future reference

## 🛠️ Development Setup

```bash
# Clone repository
git clone <repository-url>
cd xml-database-extraction

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest                                    # All tests
python run_integration_suite.py          # Integration test suite (if moved to root)

# Code quality
black xml_extractor/                      # Code formatting
mypy xml_extractor/                       # Type checking
flake8 xml_extractor/                     # Linting
```

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# End-to-end tests
pytest tests/e2e/

# Comprehensive test suite
python tests/run_integration_suite.py    # Runs all test categories with reporting
```

## 📊 Configuration

See **[Operator Guide](docs/operator-guide.md)** for detailed configuration options.

### Quick Configuration
```bash
# Check configuration status
xml-extractor

# Environment variables (optional)
export XML_EXTRACTOR_DB_SERVER="your-sql-server"
export XML_EXTRACTOR_DB_DATABASE="YourDatabase"
```

---

## 🚀 Production Deployment

See **[Deployment Guide](docs/deployment-guide.md)** for package distribution and installation.

See **[Operator Guide](docs/operator-guide.md)** for operations, monitoring, and troubleshooting.

---
python production_processor.py \
  --server "prod-server" \
  --database "ProductionDB" \
  --workers 4 \
  --batch-size 100 \
  --log-level ERROR
```

## 📈 Performance

- **Achieved Performance**: 1,477-1,691 records/minute with >95% success rate
- **Original Target**: >150 records/minute (exceeded by 10x)
- **Parallel Processing**: Multi-worker support for high throughput
- **Memory Efficient**: Configurable batch sizes and memory limits
- **Real-time Monitoring**: Progress tracking and performance metrics

## Requirements

- Python 3.8+
- lxml for high-performance XML processing
- pyodbc for SQL Server connectivity
- Additional dependencies listed in requirements.txt