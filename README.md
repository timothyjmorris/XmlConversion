# XML Database Extraction System

A high-performance, contract-driven ETL pipeline that transforms deeply nested XML data into normalized Microsoft SQL Server relational structures.

## 📖 Documentation Quick Links

- **[Operator Guide](docs/operator-guide.md)** - Production operations, commands, troubleshooting
- **[Deployment Guide](docs/deployment-guide.md)** - Package installation and environment setup
- **[Architecture Guide](ARCHITECTURE.md)** - System design and technical details
- **[Bug Fixes](docs/decisions/bug-fixes.md)** - Critical bugs resolved
- **[Performance Findings](docs/decisions/performance-findings.md)** - Configuration and optimization decisions

---

## Tech Stack
- **OS:** Windows | **Shell:** PowerShell | **Database:** MS SQL Server  
- **Language:** Python | **DB Driver:** pyodbc | **Testing:** pytest | **XML:** lxml

---

## 🚀 Quick Start

### Installation

```bash
# Development installation (editable)
pip install -e .

# Production installation  
pip install .

# With development dependencies
pip install -e ".[dev]"
```

See **[Deployment Guide](docs/deployment-guide.md)** for detailed installation options.

---

### Basic Usage

```bash
# Test run (10k records)
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB"

# Gap filling
python production_processor.py --server "server" --database "db" --limit 50000

# Large dataset processing
python run_production_processor.py --app-id-start 1 --app-id-end 300000
```

For complete operational guidance, see **[Operator Guide](docs/operator-guide.md)**.

---

## 📁 Project Structure

```
xml_extractor/
├── __init__.py                        # Main package with core exports
├── cli.py                             # Command-line interface (xml-extractor command)
├── models.py                          # Core data classes and models
├── interfaces.py                      # Abstract interfaces and base classes
├── exceptions.py                      # Custom exception classes
├── utils.py                           # Utility functions and helpers
├── config/                            # Configuration management
│   └── manager.py                      # Centralized configuration system
├── database/                          # Database operations and migration
│   ├── connection_test.py              # Database connectivity testing
│   └── migration_engine.py             # High-performance bulk insert operations
├── mapping/                           # Data transformation and mapping
│   ├── data_mapper.py                  # Core XML-to-database mapping engine
│   ├── reverse_mapper.py               # Reverse mapping utilities
│   └── calculated_field_engine.py      # Calculated field expression evaluation
├── parsing/                           # XML parsing and processing
│   └── xml_parser.py                   # Memory-efficient XML parser
└── validation/                        # Multi-layered data validation system
    ├── data_integrity_validator.py     # End-to-end validation engine
    ├── element_filter.py               # XML element filtering and validation
    ├── pre_processing_validator.py     # Pre-extraction validation
    ├── validation_integration.py       # Validation orchestration
    ├── validation_models.py            # Validation data structures
    ├── test_validation_system.py       # Validation system tests
    └── README.md                       # Validation system documentation

# Production Scripts
production_processor.py                     # Main production processing script

# Configuration & Samples
config/
├── mapping_contract.json       # CRITICAL project contract for field mapping definitions
├── data-model.md                           # Data model specifications
├── database_config.json                    # Database configuration
└── samples/                                # Sample files and documentation
    ├── configuration_summary.md
    ├── create_destination_tables.sql
    ├── enum_handling_guide.md
    ├── insert_enum_values.sql
    ├── migrate_table_logic.sql
    ├── new_datamodel_queries.sql
    ├── README.md
    ├── sample-source-xml-contact-test.xml  # Key source file used in tests to validate complex mappings
    ├── test_mapping_contract.py    
    └── validate_mapping_contract.sql

# Documentation
docs/
├── decisions/                              # Architecture decisions and learnings
│   ├── bug-fixes.md                        # Critical bugs resolved
│   └── performance-findings.md             # Configuration and optimization decisions
├── deployment-guide.md                     # Package installation and setup
├── operator-guide.md                       # Operations, commands, troubleshooting
├── mapping/                                # Mapping and contract docs
│   ├── mapping-principles.md               # Mapping system principles
│   ├── datamapper-functions.md             # DataMapper function reference
│   └── [IL/RL docs]                        # RecLending product line mapping
├── onboard_reclending/                     # RecLending onboarding materials
├── operations/
│   └── production-deployment.md            # Production deployment specifics
└── [other technical docs]                  # Architecture, testing, validation

# Tests
tests/
├── test_end_to_end_integration.py          # End-to-end integration tests
├── test_production_xml_batch.py            # Production batch processing tests
├── test_real_sample_xml_validation.py      # Real XML validation tests
└── test_xml_validation_scenarios.py        # XML validation scenarios


# Build & Dependencies
setup.py                                    # Package setup configuration
requirements.txt                            # Python dependencies
README.md                                   # This file
```

## 🏗️ System Architecture

### Complete XML-to-Database Processing Pipeline

The XML Database Extraction System operates as a comprehensive pipeline that transforms XML content stored in database text columns into normalized relational structures:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   XML Source    │──▶│ Pre-Processing   │───▶│   Extraction    │──▶│  Data Integrity │
│                 │    │   Validation     │    │   Pipeline      │    │   Validation    │
│ • Raw XML file  │    │ • ElementFilter  │    │ • XMLParser     │    │ • End-to-End    │
│ • Provenir data │    │ • Business rules │    │ • DataMapper    │    │ • Referential   │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
                              │                        │                        │
                              ▼                        ▼                        ▼
                       ┌──────────────────┐    ┌───────────────────┐    ┌───────────────────┐
                       │ ValidationResult │    │ Extracted Tables  │    │ ValidationResult  │
                       │ • Can process?   │    │ • Relational data │    │ • Quality OK?     │
                       │ • Early errors   │    │ • Ready for DB    │    │ • Detailed errors │
                       └──────────────────┘    └───────────────────┘    └───────────────────┘
```

### Processing Stages

1. **XML Source (Database)** → Raw Provenir XML data from database text columns
2. **Pre-Processing Validation** → ElementFilter + PreProcessingValidator quality gate
3. **Extraction Pipeline** → XMLParser + DataMapper transformation engine
4. **Data Integrity Validation** → DataIntegrityValidator quality assurance
5. **Database Migration** → MigrationEngine bulk insert operations

### Quality Gates

- **Gate 1**: Pre-processing validation (can we process this XML?)
- **Gate 2**: Data integrity validation (is extracted data quality acceptable?)
- **Gate 3**: Migration success (were records successfully loaded?)

### Contract-Driven Architecture

The system uses a **contract-first approach** where mapping contracts define the exact data structure and validation rules:

- **Mapping Contracts**: JSON specifications defining XML-to-database transformations
- **Schema-Derived Metadata**: Automatic addition of nullable/required/default_value fields
- **DataMapper Validation**: Ensures only contract-compliant columns are processed
- **MigrationEngine Optimization**: Focuses on high-performance bulk insertion of validated data

### Core Components Integration

#### XMLParser (`parsing/xml_parser.py`)
- **Purpose**: Memory-efficient XML parsing with selective element extraction
- **Key Features**: Selective parsing, contact deduplication, flattened data structures
- **Integration**: Provides data to DataMapper and validation components

#### DataMapper (`mapping/data_mapper.py`) 
- **Purpose**: Core data transformation engine orchestrating XML-to-database conversion
- **Key Features**: Contract-driven column selection, calculated field evaluation, enum handling
- **Recent Changes**: Now handles schema-derived nullable/required/default_value validation
- **Integration**: Receives flattened XML from XMLParser, produces contract-compliant tables for MigrationEngine

#### CalculatedFieldEngine (`mapping/calculated_field_engine.py`)
- **Purpose**: Safe evaluation of calculated field expressions with cross-element references
- **Key Features**: SQL-like expression language, safety features, performance optimization
- **Integration**: Called by DataMapper for complex field calculations

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