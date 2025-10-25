# XML Database Extraction System

A high-performance, configurable data migration tool that processes XML content stored in database text columns and transforms it into normalized relational structures.

## 🚀 Quick Start

### Installation Methods

#### Method 1: Package Installation (Recommended)
```bash
# Development installation (editable)
pip install -e .

# Production installation  
pip install .

# With optional dependencies
pip install -e ".[dev]"      # Include development tools (pytest, black, etc.)
pip install -e ".[optional]" # Include optional features
```

#### Method 2: Manual Installation (Legacy)
```bash
pip install -r requirements.txt
```

### CLI Usage

After package installation, use the `xml-extractor` command:

```bash
# Display system information and configuration
xml-extractor

# The CLI shows:
# - Database connection settings
# - Processing configuration  
# - Environment variables
# - Available components
```

**Note**: The `xml-extractor` CLI currently displays system status and configuration. For production processing, continue using `production_processor.py` with full command-line options.

### Production Processing

The production processor remains the primary tool for batch processing:

```bash
# High-performance production processing
python production_processor.py \
  --server "prod-sql-server" \
  --database "ProductionDB" \
  --workers 4 \
  --batch-size 100 \
  --log-level ERROR

# Development/testing
python production_processor.py \
  --server "dev-server" \
  --database "TestDB" \
  --workers 2 \
  --batch-size 25 \
  --limit 1000 \
  --log-level INFO
```

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
├── credit_card_mapping_contract.json       # CRITICAL project contract for field mapping definitions
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
├── bulk-insert-architecture.md             # Bulk insert design and optimization
├── data-intake-and-preparation.md          # Data intake processes
├── mapping-principles.md                   # Mapping system principles
├── testing-philosophy.md                   # Testing approach and strategy
├── validation-and-testing-strategy.md      # Validation framework
└── xml-hierarchy-corrections.md            # XML structure corrections

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

### Core Components Integration

#### XMLParser (`parsing/xml_parser.py`)
- **Purpose**: Memory-efficient XML parsing with selective element extraction
- **Key Features**: Selective parsing, contact deduplication, flattened data structures
- **Integration**: Provides data to DataMapper and validation components

#### DataMapper (`mapping/data_mapper.py`) 
- **Purpose**: Core data transformation engine orchestrating XML-to-database conversion
- **Key Features**: Complex mapping types, calculated field evaluation, enum handling
- **Integration**: Receives flattened XML from XMLParser, supplies tables to MigrationEngine

#### CalculatedFieldEngine (`mapping/calculated_field_engine.py`)
- **Purpose**: Safe evaluation of calculated field expressions with cross-element references
- **Key Features**: SQL-like expression language, safety features, performance optimization
- **Integration**: Called by DataMapper for complex field calculations

#### MigrationEngine (`database/migration_engine.py`)
- **Purpose**: High-performance database operations with SQL Server optimizations
- **Key Features**: Bulk insert operations, transaction management, progress tracking
- **Integration**: Receives extracted tables from DataMapper, validates schema compatibility

#### Validation System (`validation/`)
- **Purpose**: Multi-layered validation ensuring data quality throughout the pipeline
- **Components**: ElementFilter, PreProcessingValidator, DataIntegrityValidator, ValidationOrchestrator
- **Integration**: Validates at multiple pipeline stages, provides quality gates and reporting

### Configuration Management
- **Centralized Config**: Environment variable-based configuration system
- **Mapping Contracts**: JSON-based field mapping definitions with calculated field support
- **Schema Flexibility**: Configurable database schema prefixes for multi-environment support

### Performance Characteristics
- **Target Performance**: >150 records/minute with >90% success rate
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

### Environment Variables
```bash
# Database connection
export XML_EXTRACTOR_DB_SERVER="your-sql-server"
export XML_EXTRACTOR_DB_DATABASE="YourDatabase"
export XML_EXTRACTOR_CONNECTION_STRING="Driver={ODBC Driver 17 for SQL Server};Server=...;"

# Processing configuration
export XML_EXTRACTOR_BATCH_SIZE=100
export XML_EXTRACTOR_PARALLEL_PROCESSES=4
export XML_EXTRACTOR_MEMORY_LIMIT_MB=512

# Schema configuration (for multi-environment support)
export XML_EXTRACTOR_DB_SCHEMA_PREFIX=sandbox    # Optional: for non-production schemas
```

### Configuration Validation
```bash
# Check configuration status
xml-extractor

# Test database connectivity
python production_processor.py --server "server" --database "db" --limit 1 --log-level DEBUG
```

## 🚀 Production Deployment

See [docs/production-deployment.md](docs/production-deployment.md) for comprehensive production deployment guide including:

- Performance optimization
- Monitoring and alerting
- Database configuration
- Operational procedures
- Troubleshooting

### Quick Production Setup
```bash
# 1. Install package
pip install .

# 2. Test connectivity
python production_processor.py --server "prod-server" --database "DB" --limit 1

# 3. Run production batch
python production_processor.py \
  --server "prod-server" \
  --database "ProductionDB" \
  --workers 4 \
  --batch-size 100 \
  --log-level ERROR
```

## 📈 Performance

- **Target**: >150 records/minute with >90% success rate
- **Parallel Processing**: Multi-worker support for high throughput
- **Memory Efficient**: Configurable batch sizes and memory limits
- **Real-time Monitoring**: Progress tracking and performance metrics

## Requirements

- Python 3.8+
- lxml for high-performance XML processing
- pyodbc for SQL Server connectivity
- Additional dependencies listed in requirements.txt