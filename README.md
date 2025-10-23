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
├── __init__.py              # Main package with core exports
├── models.py                # Core data classes and models
├── interfaces.py            # Abstract interfaces and base classes
├── exceptions.py            # Custom exception classes
├── cli.py                   # Command-line interface (xml-extractor command)
├── config/                  # Configuration management components
│   ├── config_manager.py    # Centralized configuration system
│   └── __init__.py
├── parsing/                 # XML parsing components  
│   ├── xml_parser.py        # High-performance XML parser
│   └── __init__.py
├── mapping/                 # Data mapping and transformation
│   ├── data_mapper.py       # XML to database mapping engine
│   ├── calculated_field_engine.py  # Calculated field expressions
│   └── __init__.py
├── database/                # Database connection and migration
│   ├── migration_engine.py  # Database operations and bulk insert
│   └── __init__.py
└── validation/              # Data validation and quality checks
    ├── pre_processing_validator.py  # XML validation and contact extraction
    └── __init__.py

# Production Scripts
production_processor.py      # Main production processing script

# Configuration
config/
├── credit_card_mapping_contract.json  # Field mapping definitions
└── samples/                 # Sample XML files for testing

# Documentation  
docs/
├── production-deployment.md # Production deployment guide
└── *.md                    # Additional documentation
```

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