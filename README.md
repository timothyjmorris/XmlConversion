# XML Database Extraction System

A high-performance, configurable data migration tool that processes XML content stored in database text columns and transforms it into normalized relational structures.

## Project Structure

```
xml_extractor/
├── __init__.py              # Main package with core exports
├── models.py                # Core data classes and models
├── interfaces.py            # Abstract interfaces and base classes
├── exceptions.py            # Custom exception classes
├── cli.py                   # Command-line interface
├── config/                  # Configuration management components
│   └── __init__.py
├── parsing/                 # XML parsing components  
│   └── __init__.py
├── mapping/                 # Data mapping and transformation
│   └── __init__.py
└── database/                # Database connection and migration
    └── __init__.py
```

## Core Data Models

- **MappingContract**: Defines how XML data maps to relational structure
- **FieldMapping**: Maps XML elements/attributes to database columns
- **RelationshipMapping**: Defines parent-child relationships between tables
- **ProcessingConfig**: Configuration parameters for extraction operations
- **ProcessingResult**: Results and metrics from processing operations

## Abstract Interfaces

- **XMLParserInterface**: Contract for XML parsing components
- **DataMapperInterface**: Contract for data mapping components  
- **MigrationEngineInterface**: Contract for database migration components
- **ConfigurationManagerInterface**: Contract for configuration management
- **PerformanceMonitorInterface**: Contract for performance monitoring

## Installation

```bash
pip install -r requirements.txt
```

## Development Setup

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black xml_extractor/

# Type checking
mypy xml_extractor/
```

## Usage

The system is designed to be implemented through the task-based workflow defined in the specification. Each component will be implemented incrementally according to the implementation plan.

## Requirements

- Python 3.8+
- lxml for high-performance XML processing
- pyodbc for SQL Server connectivity
- Additional dependencies listed in requirements.txt