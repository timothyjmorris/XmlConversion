# Project Architecture Blueprint
# XML Database Extraction System

**Generated:** February 14, 2026  
**Version:** 2.1.0  
**Status:** Production (CC + RL pipelines active)  
**Blueprint Type:** Implementation-Ready  

---

## Table of Contents

1. [Architecture Detection and Analysis](#1-architecture-detection-and-analysis)
2. [Architectural Overview](#2-architectural-overview)
3. [Architecture Visualization](#3-architecture-visualization)
4. [Core Architectural Components](#4-core-architectural-components)
5. [Architectural Layers and Dependencies](#5-architectural-layers-and-dependencies)
6. [Data Architecture](#6-data-architecture)
7. [Cross-Cutting Concerns Implementation](#7-cross-cutting-concerns-implementation)
8. [Service Communication Patterns](#8-service-communication-patterns)
9. [Python Architectural Patterns](#9-python-architectural-patterns)
10. [Implementation Patterns](#10-implementation-patterns)
11. [Testing Architecture](#11-testing-architecture)
12. [Deployment Architecture](#12-deployment-architecture)
13. [Extension and Evolution Patterns](#13-extension-and-evolution-patterns)
14. [Architectural Pattern Examples](#14-architectural-pattern-examples)
15. [Architectural Decision Records](#15-architectural-decision-records)
16. [Architecture Governance](#16-architecture-governance)
17. [Blueprint for New Development](#17-blueprint-for-new-development)

---

## 1. Architecture Detection and Analysis

### 1.1 Technology Stack Detection

**Primary Technology:** Python 3.x  
**Runtime Environment:** Windows (PowerShell-first)  
**Database:** Microsoft SQL Server  
**Database Driver:** pyodbc (Windows Authentication + SQL Authentication)  
**XML Processing:** lxml (high-performance streaming)  
**Testing Framework:** pytest  
**Packaging:** setuptools (editable installation)  

**Framework-Specific Patterns Detected:**
- **Data Classes:** Extensive use of `@dataclass` for domain models
- **Abstract Base Classes:** Interface-driven architecture using `abc.ABC` and `@abstractmethod`
- **Type Hints:** Strong typing throughout codebase (`typing` module)
- **Context Managers:** Resource management with `with` statements
- **Multiprocessing:** Parallel processing with `multiprocessing.Pool`

### 1.2 Architectural Pattern Detection

**Primary Pattern:** **Contract-Driven Clean Architecture**

**Evidence:**
1. **Contract-Driven Design:** All data transformations defined in `config/mapping_contract.json`, not code
2. **Dependency Inversion:** Abstract interfaces (`interfaces.py`) with concrete implementations
3. **Layer Separation:** Clear separation between parsing, mapping, database, validation layers
4. **Domain-Centric:** Core business logic in `models.py`, `mapping/`, `validation/`
5. **Infrastructure Isolation:** Database and external dependencies abstracted behind interfaces

**Secondary Patterns:**
- **Pipeline Architecture:** Sequential data transformation stages (Parse → Map → Validate → Insert)
- **Adapter Pattern:** Schema metadata adapters, contract loaders
- **Strategy Pattern:** Multiple mapping types (enum, calculated_field, char_to_bit, etc.)
- **Repository Pattern:** `MigrationEngine` abstracts database operations
- **Observer Pattern:** `PerformanceMonitor` tracks processing metrics

**Folder Organization Analysis:**

```
xml_extractor/               # Core domain package
├── models.py                # Domain models (Clean Architecture core)
├── interfaces.py            # Abstract contracts (Dependency Inversion)
├── exceptions.py            # Domain-specific exceptions
├── parsing/                 # Input boundary layer
├── mapping/                 # Domain transformation layer
├── database/                # Output boundary layer (infrastructure)
├── validation/              # Domain/cross-cutting validation layer
├── processing/              # Orchestration/application layer
├── config/                  # Configuration management
└── monitoring/              # Observability infrastructure
```

**Dependency Flow (adheres to Clean Architecture):**
- `database/` → `interfaces.py` ← `models.py` (infrastructure depends on abstractions)
- `parsing/` → `interfaces.py` ← `models.py` (infrastructure depends on abstractions)
- `mapping/` → `models.py` (domain layer, no infrastructure dependencies)
- `processing/` → `interfaces.py` (orchestration layer coordinates via interfaces)

### 1.3 Hybrid Architectural Adaptations

**Contract-Driven Architecture:**
- Standard Clean Architecture places business rules in code
- This system externalizes business rules to `mapping_contract.json`
- Enables runtime configuration without code changes
- Supports multiple product lines with different contracts (CC vs. RL)

**Schema Isolation Pattern:**
- Traditional systems hardcode database schemas
- This system derives all schema references from `MappingContract.target_schema`
- Enables parallel development environments (sandbox, migration, dbo)
- Supports blue/green deployments and schema versioning

---

## 2. Architectural Overview

### 2.1 System Purpose

The XML Database Extraction System is a **high-performance, contract-driven ETL pipeline** that transforms deeply nested XML data (stored in database text columns) into normalized Microsoft SQL Server relational structures.

**Core Mission:**
- Extract XML from database source tables
- Transform XML to relational format via declarative contracts
- Load data into target schema with atomic transaction guarantees
- Support multiple product lines with isolated configurations

### 2.2 Guiding Architectural Principles

#### Principle 1: Contract-Driven Transformation
**"All data transformations are defined in configuration, not code."**

- Mapping contracts (`mapping_contract.json`) define every XML→database transformation
- Enum mappings, calculated fields, validation rules externalized
- Code implements generic transformation engine; contracts provide specifics
- Enables operational changes without code deployment

#### Principle 2: Schema Isolation
**"Every database operation respects `target_schema` from the mapping contract."**

- Development, staging, production use different schemas (sandbox, migration, dbo)
- Single codebase supports all environments via contract configuration
- No environment variables or hardcoded schema names

#### Principle 3: Atomic Transaction Guarantees
**"Every application record succeeds or fails as a complete unit (all-or-nothing)."**

- One transaction per application (all tables + processing_log)
- Prevents orphaned records (child without parent)
- Enables safe resume capability and deterministic debugging

#### Principle 4: Foreign Key Ordering
**"Tables must be inserted in dependency order to prevent constraint violations."**

- Parent tables inserted before child tables
- `table_insertion_order` in contract defines FK dependency sequence
- MigrationEngine enforces ordering automatically

#### Principle 5: Evidence-Based Development
**"All results and assertions must be verified via tests or data-driven evidence."**

- Test-first development (BDD, TDD, ATDD)
- Production-first testing with real XML data
- No hypothetical requirements or speculative code

#### Principle 6: Windows-First Environment
**"All operations, commands, and tooling optimized for Windows/PowerShell."**

- PowerShell scripts (never bash)
- Windows paths (`\` separators)
- Native Windows Authentication for SQL Server

### 2.3 Architectural Boundaries

**Input Boundary:**
- XML content from database source tables (`dbo.app_xml`, `dbo.app_xml_staging_rl`)
- Mapping contracts from JSON files (`config/mapping_contract.json`)
- Database connection strings (Windows Auth or SQL Auth)

**Output Boundary:**
- Normalized relational tables in `target_schema`
- Processing audit log (`processing_log`) in `target_schema`
- Performance metrics and logging

**Enforced Boundaries:**
- No DDL statements (CREATE/ALTER/DROP TABLE/SCHEMA)
- No DELETE/TRUNCATE operations (except test fixture cleanup)
- No environment-specific hardcoding
- Database schema changes managed outside application

### 2.4 Boundary Enforcement Mechanisms

1. **Interface Segregation:** Abstract interfaces prevent direct infrastructure access
2. **Contract Validation:** `MappingContractValidator` enforces contract schema
3. **Schema Metadata Derivation:** All schema info derived from contracts, not code
4. **Type Safety:** Strong typing with `@dataclass` and type hints
5. **Exception Hierarchy:** Domain-specific exceptions prevent leaky abstractions

---

## 3. Architecture Visualization

### 3.1 High-Level System Architecture (C4 Context)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    XML Database Extraction System                         │
│                         (Contract-Driven ETL)                             │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↑
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
         ┌──────────▼──────────┐       ┌───────────▼──────────┐
         │   Database          │       │  Configuration       │
         │   (MS SQL Server)   │       │  Files (JSON)        │
         │                     │       │                      │
         │  - Source XML       │       │  - mapping_contract  │
         │  - Target Tables    │       │  - enum_mappings     │
         │  - processing_log   │       │  - validation_rules  │
         └─────────────────────┘       └──────────────────────┘
```

### 3.2 Component Architecture (C4 Container)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Production Processor                                │
│                    (Entry Point & Orchestration)                            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
    ┌───────────▼──────┐  ┌────▼─────────┐  ┌─▼────────────────┐
    │ Parallel         │  │ Config       │  │ Performance      │
    │ Coordinator      │  │ Manager      │  │ Monitor          │
    │                  │  │              │  │                  │
    │ - Work Queue     │  │ - Contract   │  │ - Metrics        │
    │ - Worker Pool    │  │   Loading    │  │ - Tracking       │
    │ - Progress Track │  │ - Validation │  │ - Reporting      │
    └──────────────────┘  └──────────────┘  └──────────────────┘
                │
    ┌───────────┴────────────────────────────┐
    │        Worker Process Pipeline         │
    │                                        │
    │  ┌──────────────────────────────────┐ │
    │  │  1. Validation Layer             │ │
    │  │     - PreProcessingValidator     │ │
    │  │     - ElementFilter              │ │
    │  └──────────────────────────────────┘ │
    │                 ↓                      │
    │  ┌──────────────────────────────────┐ │
    │  │  2. Parsing Layer                │ │
    │  │     - XMLParser (lxml)           │ │
    │  │     - Element Extraction         │ │
    │  └──────────────────────────────────┘ │
    │                 ↓                      │
    │  ┌──────────────────────────────────┐ │
    │  │  3. Mapping Layer                │ │
    │  │     - DataMapper                 │ │
    │  │     - CalculatedFieldEngine      │ │
    │  │     - Enum Transformation        │ │
    │  └──────────────────────────────────┘ │
    │                 ↓                      │
    │  ┌──────────────────────────────────┐ │
    │  │  4. Database Layer               │ │
    │  │     - MigrationEngine            │ │
    │  │     - BulkInsertStrategy         │ │
    │  │     - DuplicateContactDetector   │ │
    │  └──────────────────────────────────┘ │
    └────────────────────────────────────────┘
                                │
                ┌───────────────┴────────────────┐
                │                                │
    ┌───────────▼───────────┐       ┌───────────▼───────────┐
    │  SQL Server           │       │  Processing Log       │
    │  Target Schema        │       │  (Audit/Resume)       │
    │                       │       │                       │
    │  - app_base           │       │  - app_id             │
    │  - contact_base       │       │  - status             │
    │  - operational_cc     │       │  - error_details      │
    │  - pricing_cc, etc.   │       │  - timestamp          │
    └───────────────────────┘       └───────────────────────┘
```

### 3.3 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Data Flow Pipeline                             │
└─────────────────────────────────────────────────────────────────────────┘

    [Source XML in Database]
              │
              │ 1. Extract XML (READ ONLY)
              ↓
    ┌─────────────────────┐
    │  Raw XML String     │
    │  (text column)      │
    └─────────────────────┘
              │
              │ 2. Pre-Processing Validation
              ↓
    ┌─────────────────────┐    FAIL → [Log Error & Skip]
    │  Validation Result  │───────────────────┐
    │  - Well-formed?     │                   │
    │  - Has root?        │                   ↓
    │  - Has app path?    │           [processing_log]
    └─────────────────────┘           status='validation_failed'
              │ PASS
              │ 3. XML Parsing (lxml streaming)
              ↓
    ┌─────────────────────┐
    │  Element Tree       │
    │  (lxml.etree)       │
    └─────────────────────┘
              │
              │ 4. Element Filtering (contract-driven)
              ↓
    ┌─────────────────────┐
    │  Filtered Elements  │
    │  - Valid contacts   │  Filter Rules:
    │  - Valid addresses  │  - con_id present
    │  - Valid employment │  - ac_role_tp_c in ['PR','AUTHU']
    └─────────────────────┘  - address_tp_c in ['CURR','PREV']
              │
              │ 5. Data Mapping (contract-driven)
              ↓
    ┌─────────────────────────────────┐
    │  Table-Keyed Dict               │
    │  {                              │
    │    'app_base': [                │
    │      {app_id: 123, name: ...}   │
    │    ],                           │
    │    'contact_base': [            │
    │      {contact_id: 1, ...}       │  Transformations:
    │    ],                           │  - Enum mappings
    │    'app_operational_cc': [...], │  - Calculated fields
    │    ...                          │  - Type conversions
    │  }                              │  - Default values
    └─────────────────────────────────┘
              │
              │ 6. Data Integrity Validation
              ↓
    ┌─────────────────────┐    FAIL → [Log Error & Rollback]
    │  Validation Result  │───────────────────┐
    │  - Required fields? │                   │
    │  - FK constraints?  │                   ↓
    │  - Enum valid?      │           [processing_log]
    └─────────────────────┘           status='mapping_failed'
              │ PASS
              │ 7. Bulk Insert (FK-ordered, atomic)
              ↓
    ┌─────────────────────────────────┐
    │  BEGIN TRANSACTION              │
    │                                 │
    │  1. INSERT app_base             │ ← Parent
    │  2. INSERT contact_base         │ ← Child of app_base
    │  3. INSERT operational_cc       │ ← Child of app_base
    │  4. INSERT pricing_cc           │ ← Child of app_base
    │  5. INSERT contact_address      │ ← Child of contact_base
    │  6. INSERT contact_employment   │ ← Child of contact_base
    │  7. INSERT processing_log       │ ← Audit trail
    │                                 │
    │  COMMIT (all succeed)           │
    │  or ROLLBACK (any fail)         │
    └─────────────────────────────────┘
              │
              ↓
    ┌─────────────────────────────────┐
    │   Normalized Tables             │
    │   + Processing Log              │
    │                                 │
    │   [target_schema].[app_base]    │
    │   [target_schema].[contact_*]   │
    │   [target_schema].[processing_  │
    │     log]                        │
    └─────────────────────────────────┘
```

### 3.4 Dependency Graph (Component Relationships)

```
┌──────────────────────────────────────────────────────────────────┐
│                      Dependency Architecture                     │
│                  (arrows point from dependent to dependency)     │
└──────────────────────────────────────────────────────────────────┘

                    ┌─────────────────┐
                    │   models.py     │  ← Core Domain (no dependencies)
                    │                 │
                    │ - MappingContract
                    │ - FieldMapping  │
                    │ - DataType      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │  interfaces.py  │  ← Abstractions
                    │                 │
                    │ - XMLParserInterface
                    │ - DataMapperInterface
                    │ - MigrationEngineInterface
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌────────▼────────┐   ┌──────▼─────────┐
│ parsing/      │   │  mapping/       │   │  database/     │
│ xml_parser.py │   │  data_mapper.py │   │  migration_    │
│               │   │                 │   │    engine.py   │
│ Implements:   │   │ Implements:     │   │                │
│ XMLParser     │   │ DataMapper      │   │ Implements:    │
│ Interface     │   │ Interface       │   │ MigrationEngine│
│               │   │                 │   │   Interface    │
└───────┬───────┘   └────────┬────────┘   └────────┬───────┘
        │                    │                     │
        │                    │                     │
        └────────────────────┼─────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  validation/    │
                    │                 │
                    │ - PreProcessing │
                    │   Validator     │
                    │ - DataIntegrity │
                    │   Validator     │
                    │ - ElementFilter │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  processing/    │
                    │  parallel_      │
                    │  coordinator.py │
                    │                 │
                    │ - Orchestrates  │
                    │   all components│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ production_     │
                    │ processor.py    │
                    │                 │
                    │ Main Entry Point│
                    └─────────────────┘
```

---

## 4. Core Architectural Components

### 4.1 Component: XMLParser (`xml_extractor/parsing/xml_parser.py`)

**Purpose:** Transform raw XML strings into structured element trees for mapping.

**Responsibilities:**
- Parse XML using lxml for high performance and memory efficiency
- Validate XML well-formedness before processing
- Extract elements and attributes from XML nodes
- Handle malformed XML gracefully with detailed error messages

**Internal Structure:**
```python
class XMLParser(XMLParserInterface):
    """Memory-efficient XML parser using lxml streaming."""
    
    def parse_xml_stream(xml_content: str) -> Element
    def validate_xml_structure(xml_content: str) -> bool
    def extract_elements(xml_node: Element) -> Dict[str, Any]
    def extract_attributes(xml_node: Element) -> Dict[str, str]
```

**Key Design Patterns:**
- **Interface Implementation:** Implements `XMLParserInterface` for testability
- **Streaming Processing:** Uses lxml's iterparse for memory efficiency
- **Exception Translation:** Converts lxml errors to domain `XMLParsingError`

**Interaction Patterns:**
- **Input:** Raw XML string from database
- **Output:** lxml Element tree
- **Dependencies:** lxml library, `models.py` for exceptions
- **Consumers:** `DataMapper`, `PreProcessingValidator`

**Evolution Patterns:**
- **Extension Point 1:** Add custom element selectors for specific product lines
- **Extension Point 2:** Implement true streaming mode for multi-GB XML files
- **Configuration:** Currently minimal; could accept parsing options via contract

### 4.2 Component: DataMapper (`xml_extractor/mapping/data_mapper.py`)

**Purpose:** Transform XML element trees into normalized relational records per mapping contract.

**Responsibilities:**
- Apply field mappings from `MappingContract`
- Execute enum transformations (e.g., "ACTIVE" → 1)
- Calculate derived fields using `CalculatedFieldEngine`
- Apply character-to-bit conversions (e.g., "Y" → 1, "N" → 0)
- Handle special mapping types (key/value tables, identity insert, etc.)
- Return table-keyed dictionary of records

**Internal Structure:**
```python
class DataMapper(DataMapperInterface):
    """Contract-driven XML-to-relational transformer."""
    
    def __init__(mapping_contract_path: str):
        self.contract = load_contract(mapping_contract_path)
        self.calculated_field_engine = CalculatedFieldEngine()
    
    def apply_mapping_contract(xml_data: Dict, contract: MappingContract) 
        -> Dict[str, List[Dict[str, Any]]]
    
    def transform_data_types(value: Any, target_type: str) -> Any
    def handle_nested_elements(parent_id: str, child_elements: List) 
        -> List[Dict]
    def apply_enum_mapping(value: str, enum_name: str) -> Optional[int]
    def apply_calculated_field(expression: str, context: Dict) -> Any
```

**Key Design Patterns:**
- **Strategy Pattern:** Different mapping strategies per `mapping_type` (enum, calculated_field, char_to_bit, etc.)
- **Interpreter Pattern:** `CalculatedFieldEngine` evaluates expressions from contract
- **Null Object Pattern:** Returns `None` for unmapped enums (columns excluded from INSERT)

**Interaction Patterns:**
- **Input:** Element tree from `XMLParser`, `MappingContract` from config
- **Output:** `Dict[table_name, List[record_dict]]`
- **Dependencies:** `CalculatedFieldEngine`, `models.MappingContract`, `exceptions.DataMappingError`
- **Consumers:** `MigrationEngine`

**Evolution Patterns:**
- **Extension Point 1:** Add new `mapping_type` handlers without changing core logic
- **Extension Point 2:** Extend `CalculatedFieldEngine` with custom functions
- **Configuration:** Entirely driven by `MappingContract.mappings`

**Critical Implementation Notes:**
- If enum mapping returns `None`, column is **excluded** from INSERT (not set to NULL)
- Calculated fields have access to entire XML context via expression variables
- Mapping types can be combined (e.g., `["enum", "nullable"]`)

### 4.3 Component: MigrationEngine (`xml_extractor/database/migration_engine.py`)

**Purpose:** Execute high-performance bulk inserts with FK ordering and transaction atomicity.

**Responsibilities:**
- Derive schema metadata from `MappingContract` and database introspection
- Insert records in FK dependency order (`table_insertion_order` from contract)
- Execute bulk inserts using `fast_executemany` for performance
- Manage atomic transactions (all tables + processing_log succeed or all fail)
- Detect duplicate contacts to prevent constraint violations
- Log processing results to `processing_log` table

**Internal Structure:**
```python
class MigrationEngine(MigrationEngineInterface):
    """High-performance bulk insert engine with atomicity guarantees."""
    
    def __init__(connection_string: str, mapping_contract_path: str):
        self.connection_string = connection_string
        self.contract = load_contract(mapping_contract_path)
        self.schema_metadata = self._derive_schema_metadata()
        self.bulk_insert_strategy = BulkInsertStrategy()
        self.duplicate_detector = DuplicateContactDetector()
    
    def execute_bulk_insert(records: List[Dict], table_name: str) -> int
    def migrate_application(app_id: int, mapped_data: Dict, 
                          xml_content: str) -> ProcessingResult
    def get_connection() -> pyodbc.Connection
    def transaction(conn: pyodbc.Connection) -> ContextManager
    def log_processing_result(app_id: int, status: str, error: str) -> None
```

**Key Design Patterns:**
- **Repository Pattern:** Abstracts database operations behind interface
- **Unit of Work Pattern:** Atomic transaction spans all tables for one application
- **Strategy Pattern:** `BulkInsertStrategy` encapsulates insert algorithm
- **Template Method:** `migrate_application()` orchestrates standard insert flow

**Interaction Patterns:**
- **Input:** Mapped data from `DataMapper`, connection string, mapping contract
- **Output:** `ProcessingResult` with success/failure status
- **Dependencies:** pyodbc, `BulkInsertStrategy`, `DuplicateContactDetector`, schema metadata
- **Consumers:** `ParallelCoordinator`, `ProductionProcessor`

**Critical Performance Optimizations:**
1. **`fast_executemany = True`:** Uses SQL Server's native bulk protocol (100x faster)
2. **Batch Processing:** Inserts 500-1000 records per `executemany()` call
3. **Connection Reuse:** Single connection per application (not per table)
4. **Prepared Statements:** SQL compiled once, executed many times
5. **WITH (NOLOCK) hints:** Duplicate detection uses `NOLOCK` to prevent RangeS-U lock serialization

**Evolution Patterns:**
- **Extension Point 1:** Override `BulkInsertStrategy` for different databases
- **Extension Point 2:** Add custom duplicate detection strategies
- **Configuration:** Batch size configurable, FK ordering from contract

**Atomic Transaction Guarantees:**

```python
# Single transaction per application
with self.get_connection() as conn:
    with self.transaction(conn):  # BEGIN TRANSACTION
        for table_name in self.contract.table_insertion_order:
            self.execute_bulk_insert(records[table_name], table_name)
        self.log_processing_result(app_id, 'success', None)
    # Auto-COMMIT on success, ROLLBACK on exception
```

### 4.4 Component: ParallelCoordinator (`xml_extractor/processing/parallel_coordinator.py`)

**Purpose:** Orchestrate parallel processing across multiple worker processes for high throughput.

**Responsibilities:**
- Manage worker process pool using `multiprocessing.Pool`
- Distribute XML records to workers via process-safe queue
- Track progress across workers using shared memory
- Collect and aggregate processing results
- Handle worker failures and recovery
- Report performance metrics

**Internal Structure:**
```python
class ParallelCoordinator(BatchProcessorInterface):
    """Multi-process orchestration for high-throughput ETL."""
    
    def __init__(connection_string: str, mapping_contract_path: str,
                 num_workers: int = 4, batch_size: int = 1000):
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.contract_path = mapping_contract_path
        self.progress_tracker = Manager().dict()
    
    def process_batch(work_items: List[WorkItem]) -> List[WorkResult]
    def _init_worker(conn_str: str, contract_path: str, progress: Dict)
    def _process_work_item(work_item: WorkItem) -> WorkResult
```

**Key Design Patterns:**
- **Process Pool Pattern:** `multiprocessing.Pool` for CPU-bound parallelism
- **Work Queue Pattern:** Distributes work items to available workers
- **Shared State Pattern:** `Manager().dict()` for cross-process progress tracking
- **Facade Pattern:** Presents simple interface to complex multiprocessing

**Interaction Patterns:**
- **Input:** List of `WorkItem` (app_id + XML content), configuration
- **Output:** List of `WorkResult` (success/failure per work item)
- **Dependencies:** `XMLParser`, `DataMapper`, `MigrationEngine` (in each worker)
- **Consumers:** `ProductionProcessor`, `run_production_processor.py`

**Worker Isolation:**
- Each worker has independent database connection (no connection sharing)
- Each worker has its own instances of Parser, Mapper, MigrationEngine
- Worker failures don't affect other workers (exception isolation)

**Evolution Patterns:**
- **Extension Point 1:** Implement distributed processing (Celery, RabbitMQ)
- **Extension Point 2:** Add work prioritization strategies
- **Configuration:** Worker count, batch size configurable via CLI args

### 4.5 Component: Validation Layer (`xml_extractor/validation/`)

**Purpose:** Multi-stage validation to ensure data quality and integrity before database operations.

**Responsibilities:**
- **Pre-Processing Validation:** XML well-formedness, required elements present
- **Element Filtering:** Apply filter rules from contract (valid contacts, addresses, etc.)
- **Data Integrity Validation:** Required fields, FK constraints, enum validity
- **Mapping Contract Validation:** Contract schema compliance

**Internal Structure:**

```
validation/
├── pre_processing_validator.py     # Stage 1: XML structure validation
├── element_filter.py               # Stage 2: Element filtering per contract
├── data_integrity_validator.py     # Stage 3: Mapped data validation
├── mapping_contract_validator.py   # Contract schema validation
├── validation_models.py            # ValidationResult, FieldValidation
└── validation_integration.py       # Orchestrates all validators
```

**Key Classes:**

```python
class PreProcessingValidator:
    """Validates XML before parsing."""
    def validate_xml_for_processing(xml_content: str, app_id: str) 
        -> ValidationResult

class ElementFilter:
    """Filters elements per contract filter_rules."""
    def apply_filter_rules(xml_tree: Element, contract: MappingContract) 
        -> Element

class DataIntegrityValidator:
    """Validates mapped data before insertion."""
    def validate_mapped_data(mapped_data: Dict, contract: MappingContract) 
        -> ValidationResult
```

**Key Design Patterns:**
- **Chain of Responsibility:** Validators execute in sequence, early exit on failure
- **Strategy Pattern:** Different validation strategies per stage
- **Result Object Pattern:** `ValidationResult` encapsulates validation outcome

**Interaction Patterns:**
- **Stage 1:** ProductionProcessor → PreProcessingValidator (validates raw XML)
- **Stage 2:** XMLParser → ElementFilter (filters elements before mapping)
- **Stage 3:** DataMapper → DataIntegrityValidator (validates mapped data)

**Evolution Patterns:**
- **Extension Point 1:** Add custom validation rules without changing validators
- **Extension Point 2:** Implement async validation for performance
- **Configuration:** Filter rules and validation rules from `MappingContract`

### 4.6 Component: ConfigManager (`xml_extractor/config/config_manager.py`)

**Purpose:** Centralized configuration loading and validation.

**Responsibilities:**
- Load `MappingContract` from JSON files
- Load database configuration
- Validate contract schema using `MappingContractValidator`
- Cache loaded contracts for performance
- Provide singleton access via `get_config_manager()`

**Internal Structure:**
```python
class ConfigManager(ConfigurationManagerInterface):
    """Singleton configuration manager."""
    
    def get_mapping_contract(contract_path: str = DEFAULT_CONTRACT) 
        -> MappingContract
    def get_database_config() -> Dict
    def validate_contract(contract: MappingContract) -> ValidationResult
    def get_target_schema(contract_path: str) -> str
    def get_source_table(contract_path: str) -> str

def get_config_manager() -> ConfigManager:
    """Get singleton instance."""
```

**Key Design Patterns:**
- **Singleton Pattern:** Single instance via `get_config_manager()`
- **Factory Pattern:** Creates and validates `MappingContract` objects
- **Cache Pattern:** Caches loaded contracts to avoid re-parsing JSON

**Evolution Patterns:**
- **Extension Point 1:** Support additional config sources (YAML, environment vars)
- **Extension Point 2:** Implement hot-reloading of contracts
- **Configuration:** Contract file paths configurable

---

## 5. Architectural Layers and Dependencies

### 5.1 Layer Structure

The system implements **Clean Architecture** with contract-driven adaptations:

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: DOMAIN                          │
│                  (No External Dependencies)                 │
│                                                             │
│  • models.py (MappingContract, FieldMapping, DataType)      │
│  • exceptions.py (Domain-specific exceptions)               │
│                                                             │
│  Dependencies: None (pure Python, stdlib only)              │
└─────────────────────────────────────────────────────────────┘
                             ↑
                             │ depends on
┌─────────────────────────────────────────────────────────────┐
│                 LAYER 2: INTERFACES                         │
│              (Abstract Contracts/Ports)                     │
│                                                             │
│  • interfaces.py (XMLParserInterface, DataMapperInterface,  │
│                   MigrationEngineInterface, etc.)           │
│                                                             │
│  Dependencies: models.py only                               │
└─────────────────────────────────────────────────────────────┘
                             ↑
                             │ depends on
┌─────────────────────────────────────────────────────────────┐
│              LAYER 3: APPLICATION LOGIC                     │
│           (Business Rules & Transformations)                │
│                                                             │
│  • mapping/data_mapper.py (transformation logic)            │
│  • mapping/calculated_field_engine.py (expression eval)     │
│  • validation/* (business validation rules)                 │
│                                                             │
│  Dependencies: interfaces.py, models.py                     │
└─────────────────────────────────────────────────────────────┘
                             ↑
                             │ depends on
┌─────────────────────────────────────────────────────────────┐
│             LAYER 4: INFRASTRUCTURE                         │
│         (External Systems & I/O Adapters)                   │
│                                                             │
│  • parsing/xml_parser.py (lxml adapter)                     │
│  • database/migration_engine.py (pyodbc adapter)            │
│  • config/config_manager.py (JSON file adapter)             │
│  • monitoring/performance_monitor.py (observability)        │
│                                                             │
│  Dependencies: interfaces.py, models.py, third-party libs   │
└─────────────────────────────────────────────────────────────┘
                             ↑
                             │ depends on
┌─────────────────────────────────────────────────────────────┐
│            LAYER 5: ORCHESTRATION                           │
│          (Coordination & Entry Points)                      │
│                                                             │
│  • processing/parallel_coordinator.py (multi-process coord) │
│  • production_processor.py (main entry point)               │
│  • cli.py (command-line interface)                          │
│                                                             │
│  Dependencies: All lower layers via interfaces              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Dependency Rules

**Rule 1: Dependencies Point Inward**
- Infrastructure depends on interfaces (not vice versa)
- Application logic depends on domain models
- Orchestration depends on interfaces (uses dependency injection)

**Rule 2: Domain Layer Has Zero Dependencies**
- `models.py` uses only Python stdlib (dataclasses, typing, enum)
- No third-party libraries in domain layer
- No infrastructure leakage (no database, XML, file I/O concerns)

**Rule 3: Abstractions Isolate Infrastructure**
- `XMLParserInterface` isolates lxml dependency
- `MigrationEngineInterface` isolates pyodbc dependency
- `ConfigurationManagerInterface` isolates file I/O

**Rule 4: Contract-Driven Configuration**
- Business rules externalized to `MappingContract`
- Application logic implements generic transformation engine
- Specific transformations defined in JSON configuration

### 5.3 Abstraction Mechanisms

**Interface Segregation:**
```python
# interfaces.py defines contracts
class XMLParserInterface(ABC):
    @abstractmethod
    def parse_xml_stream(self, xml_content: str) -> Element: pass

# Implementation in infrastructure layer
class XMLParser(XMLParserInterface):
    def parse_xml_stream(self, xml_content: str) -> Element:
        return lxml.etree.fromstring(xml_content)
```

**Dependency Injection:**
```python
# Orchestration layer injects dependencies
class ProductionProcessor:
    def __init__(self, 
                 validator: PreProcessingValidator,
                 parser: XMLParserInterface,
                 mapper: DataMapperInterface,
                 engine: MigrationEngineInterface):
        self.validator = validator
        self.parser = parser
        self.mapper = mapper
        self.engine = engine
```

**Contract-Driven Separation:**
```python
# Domain models define contract structure
@dataclass
class FieldMapping:
    xml_path: str
    target_table: str
    target_column: str
    mapping_type: Optional[List[str]] = None

# Application logic reads contract, executes transformation
class DataMapper:
    def apply_mapping_contract(self, xml_data, contract):
        for field_mapping in contract.mappings:
            # Generic transformation based on mapping_type
```

### 5.4 Circular Dependency Prevention

**No Circular Dependencies Detected:**
- All dependencies flow inward (domain ← interfaces ← application ← infrastructure ← orchestration)
- Infrastructure never depends on orchestration
- Application logic never depends on infrastructure
- Domain never depends on anything outside stdlib

**Dependency Verification:**
```bash
# No circular imports
python -c "import xml_extractor; print('No circular dependencies')"
```

### 5.5 Layer Violation Detection

**Automated Checks:**
- Type checking via mypy (ensures interface compliance)
- Import analysis (no infrastructure imports in domain layer)
- Contract validation tests (ensure contracts don't reference implementation details)

**Manual Review Guidelines:**
- Domain models should never import from `parsing/`, `database/`, `processing/`
- Interfaces should only import from `models.py`
- Application logic can import interfaces and models, but not infrastructure implementations

---

## 6. Data Architecture

### 6.1 Domain Model Structure

**Core Domain Entities:**

```python
# Primary domain model
@dataclass
class MappingContract:
    """Defines entire ETL pipeline configuration."""
    source_table: str                        # Source XML table
    source_column: str                       # XML column name
    xml_root_element: str                    # Root element name
    xml_application_path: str                # XPath to application node
    target_schema: str                       # Target schema (sandbox/dbo)
    table_insertion_order: List[str]         # FK dependency order
    element_filtering: ElementFiltering      # Filter rules
    mappings: List[FieldMapping]             # Field transformations
    relationships: List[RelationshipMapping]  # Parent-child relationships
    enum_mappings: Dict[str, Any]            # Enum value mappings
    bit_conversions: Dict[str, Any]          # Char-to-bit conversions
```

```python
# Field mapping (transformation rule)
@dataclass
class FieldMapping:
    """Single field transformation rule."""
    xml_path: str                    # XPath to source element
    xml_attribute: str               # Attribute name (if applicable)
    target_table: str                # Destination table
    target_column: str               # Destination column
    data_type: str                   # Target data type
    mapping_type: List[str]          # Transformation types
    expression: str                  # Calculated field expression
    enum_name: str                   # Enum mapping reference
    default_value: Any               # Default if missing
    required: bool                   # Validation flag
    nullable: bool                   # Validation flag
```

```python
# Element filtering (data quality)
@dataclass
class FilterRule:
    """Validation rule for XML elements."""
    element_type: str                  # contact, address, employment
    xml_parent_path: str               # Parent element XPath
    xml_child_path: str                # Child element XPath
    required_attributes: Dict[str, Any]  # Validation rules
    description: str                   # Human-readable explanation
```

**Domain Value Objects:**

```python
class DataType(Enum):
    """Supported data types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DECIMAL = "decimal"
```

**Processing Results:**

```python
@dataclass
class ProcessingResult:
    """Result of processing one application."""
    app_id: int
    success: bool
    error_stage: Optional[str]       # validation/parsing/mapping/insertion
    error_message: Optional[str]
    records_inserted: int
    processing_time: float
```

### 6.2 Entity Relationships and Aggregation Patterns

**XML Hierarchy → Relational Aggregate:**

```
Application (Root Aggregate)
    │
    ├─→ app_base (1:1)              # Application details
    ├─→ app_operational_cc (1:1)    # Operational data
    ├─→ app_pricing_cc (1:1)        # Pricing data
    ├─→ app_transactional_cc (1:1)  # Transaction data
    ├─→ app_solicited_cc (1:1)      # Solicitation data
    │
    └─→ Contact (1:M) [contact_base]
            │
            ├─→ contact_address (1:M)
            └─→ contact_employment (1:M)
```

**Aggregate Root:** `app_base`
- All child tables reference `app_id` (FK to `app_base`)
- Contact is a child aggregate with its own children

**Aggregate Boundaries:**
- One application = one transaction (atomic unit)
- All tables for one `app_id` succeed or fail together

### 6.3 Data Access Patterns

**Repository Pattern (MigrationEngine):**

```python
class MigrationEngine:
    """Repository for application data."""
    
    def migrate_application(app_id: int, mapped_data: Dict) 
        -> ProcessingResult:
        """Save complete application aggregate."""
        
    def find_processed_application(app_id: int) -> Optional[Dict]:
        """Check if app_id already processed."""
        
    def get_unprocessed_applications(limit: int) -> List[int]:
        """Fetch app_ids needing processing."""
```

**Read Patterns:**
- `WITH (NOLOCK)` hints for duplicate detection (prevents lock serialization)
- Cursor-based pagination for large datasets (avoids OFFSET issues)
- Single-record reads for validation (check if app exists)

**Write Patterns:**
- Bulk insert with `fast_executemany` (batch 500-1000 records)
- FK-ordered insertion (parent before children)
- Atomic transactions (all tables + processing_log)

### 6.4 Data Transformation and Mapping Approaches

**Transformation Pipeline:**

```
XML Element → Extract → Transform → Load
    ↓           ↓          ↓         ↓
 <app_id>    "12345"     12345    INSERT INTO app_base
```

**Transformation Strategies:**

1. **Direct Mapping:**
   ```json
   {"xml_path": "/application", "xml_attribute": "app_id", 
    "target_column": "app_id", "data_type": "int"}
   ```

2. **Enum Mapping:**
   ```json
   {"mapping_type": ["enum"], "enum_name": "app_source_enum"}
   // "ONLINE" → 1, "BRANCH" → 2, "PHONE" → 3
   ```

3. **Calculated Field:**
   ```json
   {"mapping_type": ["calculated_field"], 
    "expression": "first_name + ' ' + last_name"}
   ```

4. **Character-to-Bit Conversion:**
   ```json
   {"mapping_type": ["char_to_bit"]}
   // "Y" → 1, "N" → 0, "" → 0
   ```

5. **Key/Value Table Mapping:**
   ```json
   {"mapping_type": ["add_score"]}
   // Creates rows in scores table from multiple XML elements
   ```

**Mapper Implementation:**

```python
class DataMapper:
    def apply_mapping_contract(self, xml_data, contract):
        result = {}
        for field_mapping in contract.mappings:
            value = self._extract_value(xml_data, field_mapping.xml_path)
            
            if 'enum' in field_mapping.mapping_type:
                value = self._apply_enum(value, field_mapping.enum_name)
            
            if 'calculated_field' in field_mapping.mapping_type:
                value = self._calculate_field(field_mapping.expression)
            
            if 'char_to_bit' in field_mapping.mapping_type:
                value = self._char_to_bit(value)
            
            result[field_mapping.target_table].append({
                field_mapping.target_column: value
            })
        
        return result
```

### 6.5 Caching Strategies

**Contract Caching:**
```python
class ConfigManager:
    _contract_cache = {}  # In-memory cache
    
    def get_mapping_contract(self, path):
        if path not in self._contract_cache:
            self._contract_cache[path] = self._load_contract(path)
        return self._contract_cache[path]
```

**Schema Metadata Caching:**
```python
class MigrationEngine:
    def __init__(self):
        self.schema_metadata = self._derive_schema_metadata()
        # Cached for lifetime of engine instance
```

**No Database Query Caching:**
- No caching of query results (data changes frequently)
- Each worker process has independent state (no shared cache)

### 6.6 Data Validation Patterns

**Three-Layer Validation:**

**Layer 1: Pre-Processing (Structure)**
```python
class PreProcessingValidator:
    def validate_xml_for_processing(self, xml_content: str):
        # 1. XML well-formed?
        # 2. Has required root element?
        # 3. Has application path?
        return ValidationResult(valid=True/False, errors=[...])
```

**Layer 2: Mapping (Business Rules)**
```python
class ElementFilter:
    def apply_filter_rules(self, xml_tree: Element, contract: MappingContract):
        # 1. Contact has con_id?
        # 2. Contact type in ['PR', 'AUTHU']?
        # 3. Address type in ['CURR', 'PREV']?
        return filtered_tree
```

**Layer 3: Integrity (Constraints)**
```python
class DataIntegrityValidator:
    def validate_mapped_data(self, mapped_data: Dict, contract: MappingContract):
        # 1. Required fields present?
        # 2. FK relationships valid?
        # 3. Enum values in allowed set?
        # 4. Data types correct?
        return ValidationResult(valid=True/False, errors=[...])
```

**Database Constraint Enforcement:**
- Final validation layer: SQL Server FK constraints, NOT NULL constraints
- If constraints violated, transaction rolls back atomically

---

## 7. Cross-Cutting Concerns Implementation

### 7.1 Error Handling & Resilience

**Exception Hierarchy:**

```python
XMLExtractionError (base)
    ├── XMLParsingError
    ├── MappingContractError
    ├── DataTransformationError
    ├── DatabaseConnectionError
    ├── SchemaValidationError
    ├── ConfigurationError
    ├── ValidationError
    ├── DataMappingError
    └── PerformanceError
```

**Error Handling Strategy:**

```python
# Staged error handling with specific exceptions
try:
    # Stage 1: Validation
    validation_result = validator.validate_xml_for_processing(xml)
    if not validation_result.valid:
        raise ValidationError(validation_result.errors)
    
    # Stage 2: Parsing
    xml_tree = parser.parse_xml_stream(xml)
except XMLParsingError as e:
    return ProcessingResult(success=False, error_stage='parsing', 
                          error_message=str(e))
except ValidationError as e:
    return ProcessingResult(success=False, error_stage='validation',
                          error_message=str(e))
```

**Resilience Patterns:**

1. **Transaction Rollback:**
   ```python
   with self.transaction(conn):
       try:
           # All inserts
           conn.commit()
       except Exception:
           conn.rollback()  # Atomic rollback
   ```

2. **Worker Isolation:**
   - Each worker process independent
   - Worker failure doesn't affect other workers
   - Failed work items logged to `processing_log`

3. **Resume Capability:**
   ```python
   # Skip already-processed applications
   WHERE app_id NOT IN (
       SELECT app_id FROM processing_log 
       WHERE status IN ('success', 'failed')
   )
   ```

4. **Graceful Degradation:**
   - If enum mapping fails, return `None` (column excluded from INSERT)
   - If calculated field fails, log warning and use default
   - If duplicate contact detected, deduplicate automatically

**Error Reporting:**

```python
# Detailed error context in processing_log
{
    "app_id": 12345,
    "status": "failed",
    "error_stage": "mapping",
    "error_message": "Enum mapping failed for field 'app_source_enum': value 'INVALID' not in enum map",
    "error_category": "data_transformation",
    "timestamp": "2026-02-14T10:30:00"
}
```

### 7.2 Logging & Monitoring

**Logging Strategy:**

```python
# Structured logging with levels
import logging

logger = logging.getLogger(__name__)

# DEBUG: Detailed diagnostic info
logger.debug(f"Parsing XML for app_id={app_id}")

# INFO: Key processing milestones
logger.info(f"Processed app_id={app_id} successfully ({records_inserted} records)")

# WARNING: Recoverable issues
logger.warning(f"Enum mapping returned None for field={field_name}")

# ERROR: Processing failures
logger.error(f"Failed to process app_id={app_id}: {error_message}")
```

**Performance Monitoring:**

```python
class PerformanceMonitor:
    """Track processing metrics in real-time."""
    
    def track_processing_time(self, app_id: int, duration: float):
        self.metrics['processing_times'].append(duration)
    
    def track_throughput(self, records_per_minute: float):
        self.metrics['throughput'].append(records_per_minute)
    
    def report_summary(self):
        return {
            'total_processed': self.metrics['total'],
            'success_rate': self.metrics['success'] / self.metrics['total'],
            'avg_time': statistics.mean(self.metrics['processing_times']),
            'throughput': self.metrics['throughput'][-1]
        }
```

**Observability Instrumentation:**

```python
# Production processor reports progress
print(f"Progress: {processed}/{total} ({progress_pct:.1f}%) | "
      f"Success: {success_count} | Failed: {fail_count} | "
      f"Rate: {rate:.0f} apps/min | "
      f"Est. remaining: {est_remaining_time}")
```

### 7.3 Validation

**Validation Responsibility Distribution:**

| Layer | Validator | Responsibility |
|-------|-----------|----------------|
| Pre-Processing | `PreProcessingValidator` | XML structure, required elements |
| Parsing | `ElementFilter` | Element filtering per contract rules |
| Mapping | `DataMapper` | Data type conversions, enum validity |
| Database | `DataIntegrityValidator` | FK constraints, required fields |
| Database | SQL Server Constraints | NOT NULL, FK, CHECK constraints |

**Validation Flow:**

```python
# 1. Pre-Processing Validation (before parsing)
validation_result = pre_validator.validate_xml_for_processing(xml_content, app_id)
if not validation_result.valid:
    return ProcessingResult(error_stage='validation')

# 2. Element Filtering (during parsing)
filtered_tree = element_filter.apply_filter_rules(xml_tree, contract)

# 3. Data Mapping (with type validation)
mapped_data = data_mapper.apply_mapping_contract(filtered_tree, contract)

# 4. Data Integrity Validation (before insertion)
integrity_result = integrity_validator.validate_mapped_data(mapped_data, contract)
if not integrity_result.valid:
    return ProcessingResult(error_stage='integrity_validation')

# 5. Database Constraint Validation (during insertion)
# SQL Server enforces FK, NOT NULL, CHECK constraints
```

**Error Reporting Patterns:**

```python
@dataclass
class ValidationResult:
    """Standardized validation result."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    field_validations: Dict[str, FieldValidation]
```

### 7.4 Configuration Management

**Configuration Sources:**

1. **Mapping Contracts:** `config/mapping_contract.json`, `config/mapping_contract_rl.json`
2. **Database Config:** `config/database_config.json`
3. **CLI Arguments:** Connection string, app ID ranges, workers, batch size
4. **Processing Defaults:** `xml_extractor/config/processing_defaults.py`

**Configuration Loading Pattern:**

```python
class ConfigManager:
    """Singleton configuration manager."""
    
    def get_mapping_contract(self, path: str = DEFAULT_CONTRACT):
        # 1. Load JSON from file
        # 2. Validate schema
        # 3. Convert to MappingContract dataclass
        # 4. Cache for reuse
        return mapping_contract
```

**Environment-Specific Configuration:**

```json
{
  "target_schema": "sandbox",    // Development
  "target_schema": "migration",  // Staging
  "target_schema": "dbo"         // Production
}
```

**Secret Management:**
- Database connection strings via CLI args (not files)
- Windows Authentication preferred (no credentials in code)
- SQL Authentication supported for cross-platform testing

**Feature Flag Implementation:**
- Element filtering enabled/disabled per contract (`element_filtering`)
- Mapping types enable/disable features (`mapping_type: ["enum", "nullable"]`)

---

## 8. Service Communication Patterns

### 8.1 Service Boundary Definitions

**Internal Service Boundaries:**

```
Production Processor (Orchestrator)
    ↕ (function call)
ParallelCoordinator (Multi-process Coordinator)
    ↕ (multiprocessing.Queue)
Worker Processes (ETL Pipeline)
    ↕ (pyodbc connection)
SQL Server Database (Data Store)
```

**No External Services:**
- Entire system runs locally on Windows
- No HTTP APIs, message queues, or external integrations
- All communication via function calls or multiprocessing

### 8.2 Communication Protocols

**Intra-Process Communication:**
- Direct function calls via interfaces
- Dependency injection pattern

**Inter-Process Communication:**
- `multiprocessing.Queue` for work distribution
- `multiprocessing.Manager().dict()` for shared progress tracking
- Process pool with worker initialization

**Database Communication:**
- pyodbc (ODBC protocol) for SQL Server
- Connection pooling at worker level (one connection per worker process)
- Atomic transactions with explicit commit/rollback

### 8.3 Synchronous vs. Asynchronous

**All Communication is Synchronous:**
- No async/await usage
- No message queues or event buses
- Blocking database operations

**Parallel Processing (not async):**
- Uses `multiprocessing` for CPU-bound parallelism
- Each worker synchronously processes work items
- Results collected synchronously by coordinator

**Rationale:**
- ETL workload is CPU/I/O-bound, not latency-bound
- Simpler error handling and debugging with synchronous code
- Database operations inherently synchronous

---

## 9. Python Architectural Patterns

### 9.1 Module Organization

**Package Structure:**
```
xml_extractor/                  # Main package
├── __init__.py                 # Public API exports
├── models.py                   # Domain models (dataclasses)
├── interfaces.py               # Abstract interfaces (ABC)
├── exceptions.py               # Custom exceptions
├── utils.py                    # Utility functions
├── cli.py                      # CLI entry point
├── config/                     # Configuration management
├── parsing/                    # XML parsing adapters
├── mapping/                    # Data transformation logic
├── database/                   # Database adapters
├── validation/                 # Multi-stage validation
├── processing/                 # Orchestration layer
└── monitoring/                 # Observability
```

**Import Organization:**
```python
# Standard library
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Third-party
import pyodbc
from lxml import etree

# Local (absolute imports)
from xml_extractor.models import MappingContract
from xml_extractor.interfaces import XMLParserInterface
from xml_extractor.exceptions import XMLParsingError
```

### 9.2 Dependency Management

**Package Installation:**
```bash
# Editable development installation
pip install -e .

# Production installation
pip install .

# With dev dependencies
pip install -e ".[dev]"
```

**requirements.txt:**
```
pyodbc>=4.0.0
lxml>=4.9.0
pytest>=7.0.0
```

**setup.py:**
```python
setup(
    name="xml-extractor",
    version="2.1.0",
    packages=find_packages(),
    install_requires=[
        "pyodbc>=4.0.0",
        "lxml>=4.9.0"
    ],
    extras_require={
        "dev": ["pytest>=7.0.0", "mypy>=0.990"]
    }
)
```

### 9.3 OOP vs. Functional Programming

**Predominantly Object-Oriented:**
- Classes for components (XMLParser, DataMapper, MigrationEngine)
- Interface-based design with ABC
- Encapsulation of state and behavior

**Functional Elements:**
- Data classes (`@dataclass`) for immutable data
- Pure functions for transformations
- Utility functions in `utils.py`

**Example - OOP:**
```python
class DataMapper(DataMapperInterface):
    def __init__(self, mapping_contract_path: str):
        self.contract = load_contract(mapping_contract_path)
    
    def apply_mapping_contract(self, xml_data: Dict) -> Dict:
        # Stateful transformation using self.contract
```

**Example - Functional:**
```python
def extract_attribute(element: Element, attr_name: str) -> Optional[str]:
    """Pure function: element + attr_name → value."""
    return element.get(attr_name)
```

### 9.4 Framework Integration Patterns (N/A)

**No Web Framework:**
- Command-line application, not web service
- No Flask, Django, FastAPI usage

**Testing Framework (pytest):**
```python
# Fixtures for dependency injection
@pytest.fixture
def mapping_contract():
    return load_contract('config/mapping_contract.json')

# Parametrized tests
@pytest.mark.parametrize("xml_input,expected", test_cases)
def test_parser(xml_input, expected):
    result = XMLParser().parse_xml_stream(xml_input)
    assert result == expected
```

### 9.5 Asynchronous Programming (Not Used)

**No async/await:**
- Synchronous codebase
- Uses multiprocessing for parallelism, not asyncio

**Rationale:**
- Database operations are synchronous (pyodbc)
- XML parsing is CPU-bound (not I/O-bound)
- Multiprocessing provides true parallelism (not concurrency)

---

## 10. Implementation Patterns

### 10.1 Interface Design Patterns

**Interface Segregation:**

```python
# Small, focused interfaces
class XMLParserInterface(ABC):
    @abstractmethod
    def parse_xml_stream(self, xml_content: str) -> Element: pass
    
    @abstractmethod
    def validate_xml_structure(self, xml_content: str) -> bool: pass

class DataMapperInterface(ABC):
    @abstractmethod
    def apply_mapping_contract(self, xml_data: Dict, contract: MappingContract) 
        -> Dict[str, List[Dict]]: pass
```

**Abstraction Levels:**
- **High-level:** `BatchProcessorInterface` (orchestration)
- **Mid-level:** `DataMapperInterface`, `MigrationEngineInterface` (components)
- **Low-level:** `XMLParserInterface` (adapters)

**Generic vs. Specific:**
```python
# Generic interface
class MigrationEngineInterface(ABC):
    @abstractmethod
    def execute_bulk_insert(self, records: List[Dict], table_name: str) -> int:
        """Generic bulk insert - works for any table."""

# Specific implementation
class MigrationEngine(MigrationEngineInterface):
    def execute_bulk_insert(self, records: List[Dict], table_name: str) -> int:
        # SQL Server-specific implementation with fast_executemany
```

### 10.2 Service Implementation Patterns

**Service Lifetime Management:**

```python
# Singleton pattern for configuration
_config_manager_instance = None

def get_config_manager() -> ConfigManager:
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance
```

```python
# Worker-local instances (one per worker process)
# Global worker state initialized once per process
_worker_parser = None
_worker_mapper = None
_worker_engine = None

def _init_worker(conn_string, contract_path, progress_dict):
    global _worker_parser, _worker_mapper, _worker_engine
    _worker_parser = XMLParser()
    _worker_mapper = DataMapper(contract_path)
    _worker_engine = MigrationEngine(conn_string, contract_path)
```

**Service Composition:**

```python
class ProductionProcessor:
    """Composes services via dependency injection."""
    
    def __init__(self, 
                 validator: PreProcessingValidator,
                 parser: XMLParserInterface,
                 mapper: DataMapperInterface,
                 engine: MigrationEngineInterface,
                 monitor: PerformanceMonitor):
        self.validator = validator
        self.parser = parser
        self.mapper = mapper
        self.engine = engine
        self.monitor = monitor
```

**Error Handling Within Services:**

```python
class DataMapper:
    def apply_mapping_contract(self, xml_data, contract):
        try:
            # Transformation logic
            mapped_data = self._transform(xml_data, contract)
        except KeyError as e:
            raise DataMappingError(f"Missing required field: {e}")
        except ValueError as e:
            raise DataTransformationError(f"Type conversion failed: {e}")
        return mapped_data
```

### 10.3 Repository Implementation Patterns

**Repository Pattern:**

```python
class MigrationEngine(MigrationEngineInterface):
    """Repository for application data."""
    
    # Query patterns
    def find_processed_application(self, app_id: int) -> Optional[Dict]:
        """Check if app already processed."""
        query = """
            SELECT app_id, status, processed_at 
            FROM [{schema}].[processing_log] 
            WHERE app_id = ?
        """.format(schema=self.target_schema)
        return self._execute_query(query, (app_id,))
    
    def get_unprocessed_applications(self, limit: int) -> List[int]:
        """Fetch app_ids needing processing."""
        query = """
            SELECT TOP (?) app_id 
            FROM [dbo].[app_xml]
            WHERE app_id NOT IN (
                SELECT app_id FROM [{schema}].[processing_log]
                WHERE status IN ('success', 'failed')
            )
            ORDER BY app_id
        """.format(schema=self.target_schema)
        return self._execute_query(query, (limit,))
    
    # Transaction management
    @contextmanager
    def transaction(self, conn):
        """Manage atomic transactions."""
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    # Concurrency handling
    def _execute_duplicate_check(self, query: str):
        """Use NOLOCK to prevent RangeS-U lock serialization."""
        query_with_nolock = query.replace(
            f"[{self.target_schema}].[contact_base]",
            f"[{self.target_schema}].[contact_base] WITH (NOLOCK)"
        )
        return self._execute_query(query_with_nolock)
    
    # Bulk operation patterns
    def execute_bulk_insert(self, records: List[Dict], table_name: str) -> int:
        """High-performance bulk insert."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.fast_executemany = True  # SQL Server optimization
            
            # Dynamic SQL generation
            columns = list(records[0].keys())
            placeholders = ', '.join(['?'] * len(columns))
            sql = f"INSERT INTO [{self.target_schema}].[{table_name}] " \
                  f"({', '.join(f'[{c}]' for c in columns)}) " \
                  f"VALUES ({placeholders})"
            
            # Batch processing
            data_tuples = [tuple(r[c] for c in columns) for r in records]
            cursor.executemany(sql, data_tuples)
            
            return cursor.rowcount
```

### 10.4 Domain Model Implementation

**Entity Pattern:**

```python
@dataclass
class MappingContract:
    """Entity with identity (contract file path)."""
    source_table: str
    source_column: str
    target_schema: str
    mappings: List[FieldMapping]
    
    def get_target_table_names(self) -> List[str]:
        """Business logic on entity."""
        return list(set(m.target_table for m in self.mappings))
    
    def get_mappings_for_table(self, table_name: str) -> List[FieldMapping]:
        """Query methods on entity."""
        return [m for m in self.mappings if m.target_table == table_name]
```

**Value Object Pattern:**

```python
@dataclass(frozen=True)
class FieldMapping:
    """Immutable value object."""
    xml_path: str
    target_table: str
    target_column: str
    data_type: str
    # No identity - equality based on values
```

**Domain Event Pattern (Implicit):**

```python
# Processing log entry = domain event
{
    "app_id": 12345,
    "status": "success",
    "records_inserted": 15,
    "timestamp": "2026-02-14T10:30:00"
}
# Enables event sourcing / audit trail
```

---

## 11. Testing Architecture

### 11.1 Testing Strategies

**Production-First Testing Philosophy:**
> "Test with real production data to discover problems and refine the program until you can run the whole batch confidently."

**Testing Pyramid:**

```
        /\
       /  \  E2E Tests (integration/e2e/)
      /────\  - Real database, real XML
     /      \  - Complete pipeline validation
    /────────\  Integration Tests (integration/)
   /          \  - Component integration
  /────────────\  - Database operations
 /──────────────\ Unit Tests (unit/)
 ‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾ - Pure functions, isolated components
```

### 11.2 Test Organization

**Test Structure:**

```
tests/
├── conftest.py                    # Shared fixtures
├── helpers.py                     # Test utilities
├── unit/                          # Fast, isolated tests
│   ├── test_xml_parser.py
│   ├── test_data_mapper.py
│   ├── test_models.py
│   └── test_calculated_field_engine.py
├── integration/                   # Database-dependent tests
│   ├── test_migration_engine.py
│   ├── test_duplicate_detection.py
│   ├── test_validation_integration.py
│   └── test_batch_processing.py
├── e2e/                          # End-to-end tests
│   ├── test_production_pipeline.py
│   └── test_parallel_processing.py
├── contracts/                    # Contract validation tests
│   ├── test_mapping_contract.py
│   └── test_contract_compliance.py
├── performance/                  # Performance benchmarks
│   └── test_throughput.py
└── harness/                      # Test infrastructure
    ├── fixtures/
    └── mock_data/
```

### 11.3 Test Boundary Patterns

**Unit Test Boundaries:**
```python
# Test pure functions and isolated components
def test_enum_mapping():
    mapper = DataMapper('config/mapping_contract.json')
    result = mapper.apply_enum_mapping('ACTIVE', 'app_status_enum')
    assert result == 1  # No database, no external I/O
```

**Integration Test Boundaries:**
```python
# Test component integration with database
def test_migration_engine_insert(test_database):
    engine = MigrationEngine(test_database.connection_string)
    records = [{'app_id': 123, 'name': 'Test'}]
    count = engine.execute_bulk_insert(records, 'app_base')
    assert count == 1
    # Verify data in database
    assert test_database.fetch_one('SELECT * FROM app_base WHERE app_id=123')
```

**E2E Test Boundaries:**
```python
# Test complete pipeline with real data
def test_complete_pipeline(test_database, sample_xml):
    processor = ProductionProcessor(test_database.connection_string)
    result = processor.process_application(app_id=123, xml_source='database')
    assert result.success == True
    # Verify all tables populated
    assert test_database.count('app_base') > 0
    assert test_database.count('contact_base') > 0
    assert test_database.count('processing_log') == 1
```

### 11.4 Test Doubles and Mocking

**Minimal Mocking Philosophy:**
- Prefer real implementations over mocks
- Use mocks only for external dependencies (database in unit tests)
- Integration tests use real database (sandbox schema)

**Mock Examples:**

```python
# Mock database connection for unit tests
class MockConnection:
    def cursor(self):
        return MockCursor()
    
    def commit(self): pass
    def rollback(self): pass

# Use real implementations for everything else
```

**Test Fixtures:**

```python
# conftest.py - Shared fixtures
@pytest.fixture
def mapping_contract():
    """Load real mapping contract."""
    return get_config_manager().get_mapping_contract()

@pytest.fixture
def sample_xml():
    """Load real sample XML from config/samples/."""
    with open('config/samples/sample-source-xml.xml') as f:
        return f.read()

@pytest.fixture
def test_database():
    """Provide test database with cleanup."""
    db = create_test_database(schema='test_sandbox')
    yield db
    db.cleanup()  # Remove test data
```

### 11.5 Test Data Strategies

**Real Production Data:**
```python
# Extract sample XMLs from production database
python env_prep/appxml_staging_extractor.py --limit 100

# Test with production XMLs
def test_production_xml_batch():
    xmls = load_production_sample_xmls()
    for xml in xmls:
        result = processor.process_xml(xml)
        # Track success/failure patterns
```

**Synthetic Test Data:**
```python
# Generate mock XML for edge cases
python env_prep/generate_mock_xml.py

# Test edge cases
def test_missing_optional_fields():
    xml = generate_xml(exclude_fields=['middle_name', 'suffix'])
    result = processor.process_xml(xml)
    assert result.success == True
```

**Fixture Data:**
```
tests/harness/fixtures/
├── valid_application.xml
├── missing_required_field.xml
├── invalid_enum_value.xml
└── malformed_xml.xml
```

### 11.6 Testing Tools Integration

**pytest Configuration:**

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests (no database)
    integration: Integration tests (require database)
    e2e: End-to-end tests (full pipeline)
    performance: Performance benchmarks
```

**Running Tests:**

```powershell
# All tests
pytest tests/ -v

# Unit tests only (fast)
pytest tests/unit/ -m unit

# Integration tests (require database)
pytest tests/integration/ -m integration

# Quick validation
python tests/run_integration_suite.py

# Comprehensive suite
python tests/run_comprehensive_suite.py
```

---

## 12. Deployment Architecture

### 12.1 Deployment Topology

**Single-Machine Deployment:**
```
Windows Server / Workstation
    │
    ├─→ Python Runtime (3.9+)
    ├─→ xml_extractor package (pip installed)
    ├─→ Configuration Files (config/)
    │
    └─→ Network Connection
            │
            └─→ SQL Server (local or remote)
                    ├─→ Database: XmlConversionDB
                    ├─→ Source schema: [dbo]
                    └─→ Target schema: [sandbox/migration/dbo]
```

**Multi-Process Deployment (Parallel Processing):**
```
Main Process (production_processor.py)
    │
    ├─→ Worker Process 1 → SQL Connection 1
    ├─→ Worker Process 2 → SQL Connection 2
    ├─→ Worker Process 3 → SQL Connection 3
    └─→ Worker Process 4 → SQL Connection 4
            │
            └─→ All connect to same SQL Server database
```

### 12.2 Environment-Specific Adaptations

**Development Environment:**
```json
{
  "target_schema": "sandbox",
  "source_table": "app_xml_staging",
  "table_insertion_order": [...]
}
```
```powershell
python production_processor.py --server "localhost\SQLEXPRESS" --database "XmlConversionDB_Dev" --limit 100
```

**Staging Environment:**
```json
{
  "target_schema": "migration",
  "source_table": "app_xml_staging",
  "table_insertion_order": [...]
}
```
```powershell
python production_processor.py --server "staging-server" --database "XmlConversionDB" --limit 10000
```

**Production Environment:**
```json
{
  "target_schema": "dbo",
  "source_table": "app_xml",
  "table_insertion_order": [...]
}
```
```powershell
python run_production_processor.py --app-id-start 1 --app-id-end 500000
```

### 12.3 Configuration Management Across Environments

**Single Codebase, Multiple Contracts:**
- Dev: Uses `mapping_contract.json` with `target_schema: "sandbox"`
- Staging: Uses `mapping_contract.json` with `target_schema: "migration"`
- Prod: Uses `mapping_contract.json` with `target_schema: "dbo"`

**No Environment Variables:**
- Schema isolation via contract configuration
- Connection string via CLI args
- No `.env` files or environment-specific hardcoding

### 12.4 Containerization (Not Used)

**No Docker/Containers:**
- Windows-native deployment
- Direct Python installation via pip
- No containerization required

**Rationale:**
- Windows-only application
- SQL Server requires Windows Authentication (container complexity)
- Simpler deployment without Docker layer

### 12.5 Cloud Service Integration (Not Used)

**On-Premise Deployment:**
- No cloud services (AWS, Azure, GCP)
- Direct connection to on-premise SQL Server
- No S3, blob storage, or cloud databases

---

## 13. Extension and Evolution Patterns

### 13.1 Feature Addition Patterns

**Adding New Product Line:**

1. **Create New Mapping Contract:**
   ```powershell
   # Copy existing contract
   cp config/mapping_contract.json config/mapping_contract_new_product.json
   
   # Edit source table, target schema, mappings
   ```

2. **Update Entry Point:**
   ```python
   # production_processor.py
   parser.add_argument('--contract', default='config/mapping_contract.json',
                     help='Path to mapping contract')
   ```

3. **No Code Changes Required:**
   - Mapping contract defines all transformations
   - DataMapper, MigrationEngine work generically

**Adding New Mapping Type:**

1. **Extend DataMapper:**
   ```python
   class DataMapper:
       def apply_mapping_contract(self, xml_data, contract):
           for field_mapping in contract.mappings:
               if 'new_mapping_type' in field_mapping.mapping_type:
                   value = self._apply_new_mapping_type(value, field_mapping)
       
       def _apply_new_mapping_type(self, value, field_mapping):
           # Implementation of new transformation
   ```

2. **Update Contract:**
   ```json
   {"mapping_type": ["new_mapping_type"], "config": {...}}
   ```

3. **Add Tests:**
   ```python
   def test_new_mapping_type():
       mapper = DataMapper()
       result = mapper._apply_new_mapping_type('input', mock_field_mapping)
       assert result == 'expected'
   ```

**Adding New Table:**

1. **Create Database Table (Outside Application):**
   ```sql
   CREATE TABLE [sandbox].[new_table] (...)
   ```

2. **Update Mapping Contract:**
   ```json
   {
     "table_insertion_order": [..., "new_table"],
     "mappings": [
       {"target_table": "new_table", ...}
     ]
   }
   ```

3. **No Code Changes Required:**
   - MigrationEngine derives schema metadata automatically
   - Bulk insert works for any table structure

### 13.2 Modification Patterns

**Modifying Existing Component:**

1. **Update Tests First (TDD):**
   ```python
   def test_new_behavior():
       # Write test for new behavior
       assert component.new_method() == expected_result
   ```

2. **Implement Change:**
   ```python
   class ComponentName:
       def new_method(self):
           # Implementation
   ```

3. **Verify No Regressions:**
   ```powershell
   pytest tests/unit/test_component.py -v
   ```

**Maintaining Backward Compatibility:**

```python
# Old contract format
mappings: List[FieldMapping]

# New contract format (backward compatible)
mappings: List[FieldMapping] = None  # Optional with default

def __post_init__(self):
    # Normalize old format to new format
    if self.mappings is None:
        self.mappings = []
```

**Deprecation Pattern:**

```python
# Mark as deprecated
def old_method(self):
    warnings.warn("old_method() is deprecated, use new_method()", 
                  DeprecationWarning)
    return self.new_method()

def new_method(self):
    # New implementation
```

### 13.3 Integration Patterns

**Integrating New External System:**

1. **Define Interface:**
   ```python
   class ExternalSystemInterface(ABC):
       @abstractmethod
       def fetch_data(self, id: str) -> Dict: pass
   ```

2. **Implement Adapter:**
   ```python
   class ExternalSystemAdapter(ExternalSystemInterface):
       def fetch_data(self, id: str) -> Dict:
           # Call external system API
   ```

3. **Inject Dependency:**
   ```python
   class ProductionProcessor:
       def __init__(self, external_system: ExternalSystemInterface):
           self.external_system = external_system
   ```

**Anti-Corruption Layer Pattern:**

```python
class ExternalSystemAdapter:
    """Translates external data format to internal domain model."""
    
    def fetch_application(self, external_id: str) -> ApplicationData:
        # Fetch from external system
        external_data = self._call_external_api(external_id)
        
        # Translate to internal format
        return self._translate_to_domain_model(external_data)
    
    def _translate_to_domain_model(self, external_data):
        # Isolate external format from domain
```

**Service Facade Pattern:**

```python
class ApplicationDataFacade:
    """Unified interface for multiple data sources."""
    
    def __init__(self, database: DatabaseAdapter, 
                 external_system: ExternalSystemAdapter):
        self.database = database
        self.external_system = external_system
    
    def get_application(self, app_id: str) -> ApplicationData:
        # Try database first
        data = self.database.get_application(app_id)
        if data is None:
            # Fallback to external system
            data = self.external_system.fetch_application(app_id)
        return data
```

---

## 14. Architectural Pattern Examples

### 14.1 Layer Separation Examples

**Interface Definition and Implementation Separation:**

```python
# interfaces.py (Application Layer)
from abc import ABC, abstractmethod

class DataMapperInterface(ABC):
    """Abstract contract for data mapping."""
    
    @abstractmethod
    def apply_mapping_contract(self, xml_data: Dict, contract: MappingContract) 
        -> Dict[str, List[Dict]]:
        """Transform XML to relational format per contract."""
        pass

# mapping/data_mapper.py (Infrastructure Layer)
class DataMapper(DataMapperInterface):
    """Concrete implementation using contract-driven transformation."""
    
    def apply_mapping_contract(self, xml_data: Dict, contract: MappingContract) 
        -> Dict[str, List[Dict]]:
        # Concrete implementation
        mapped_data = {}
        for field_mapping in contract.mappings:
            table_name = field_mapping.target_table
            if table_name not in mapped_data:
                mapped_data[table_name] = []
            # ... transformation logic
        return mapped_data
```

**Cross-Layer Communication:**

```python
# production_processor.py (Orchestration Layer)
class ProductionProcessor:
    def __init__(self, 
                 parser: XMLParserInterface,        # Interface, not implementation
                 mapper: DataMapperInterface,       # Interface, not implementation
                 engine: MigrationEngineInterface): # Interface, not implementation
        self.parser = parser
        self.mapper = mapper
        self.engine = engine
    
    def process_application(self, xml_content: str):
        # Use interfaces, not concrete classes
        xml_tree = self.parser.parse_xml_stream(xml_content)
        mapped_data = self.mapper.apply_mapping_contract(xml_tree, self.contract)
        result = self.engine.migrate_application(mapped_data)
        return result
```

**Dependency Injection:**

```python
# Main entry point injects dependencies
def main():
    # Create concrete implementations
    parser = XMLParser()
    mapper = DataMapper('config/mapping_contract.json')
    engine = MigrationEngine(connection_string)
    
    # Inject via constructor (dependency inversion)
    processor = ProductionProcessor(
        parser=parser,
        mapper=mapper,
        engine=engine
    )
    
    # Run processing
    processor.run()
```

### 14.2 Component Communication Examples

**Service Invocation Pattern:**

```python
# Coordinated service invocation
class ProductionProcessor:
    def process_single_application(self, app_id: int) -> ProcessingResult:
        # 1. Fetch XML from database
        xml_content = self.engine.fetch_xml(app_id)
        
        # 2. Validate XML structure
        validation_result = self.validator.validate_xml_for_processing(xml_content, app_id)
        if not validation_result.valid:
            return ProcessingResult(success=False, error_stage='validation')
        
        # 3. Parse XML
        xml_tree = self.parser.parse_xml_stream(xml_content)
        
        # 4. Apply mapping contract
        mapped_data = self.mapper.apply_mapping_contract(xml_tree, self.contract)
        
        # 5. Migrate to database
        result = self.engine.migrate_application(app_id, mapped_data, xml_content)
        
        return result
```

**Event Publication and Handling (Implicit):**

```python
# Processing log acts as event store
class MigrationEngine:
    def migrate_application(self, app_id: int, mapped_data: Dict) -> ProcessingResult:
        try:
            # Execute migration
            self._insert_all_tables(mapped_data)
            
            # Publish success event (via processing_log)
            self.log_processing_result(app_id, status='success', error=None)
            
            return ProcessingResult(success=True)
        except Exception as e:
            # Publish failure event (via processing_log)
            self.log_processing_result(app_id, status='failed', error=str(e))
            
            return ProcessingResult(success=False, error_message=str(e))
```

**Message Passing (Multiprocessing):**

```python
# Worker coordinator passes work items via queue
class ParallelCoordinator:
    def process_batch(self, work_items: List[WorkItem]) -> List[WorkResult]:
        # Create process pool
        with Pool(processes=self.num_workers, 
                 initializer=self._init_worker,
                 initargs=(self.connection_string, self.contract_path, self.progress_tracker)
                 ) as pool:
            # Map work items to workers (message passing)
            results = pool.map(self._process_work_item, work_items)
        
        return results
    
    @staticmethod
    def _process_work_item(work_item: WorkItem) -> WorkResult:
        # Worker receives message, processes, returns result
        try:
            # Use worker-local instances
            validation_result = _worker_validator.validate_xml_for_processing(work_item.xml_content)
            xml_tree = _worker_parser.parse_xml_stream(work_item.xml_content)
            mapped_data = _worker_mapper.apply_mapping_contract(xml_tree)
            result = _worker_engine.migrate_application(work_item.app_id, mapped_data)
            
            return WorkResult(success=True, app_id=work_item.app_id)
        except Exception as e:
            return WorkResult(success=False, app_id=work_item.app_id, error=str(e))
```

### 14.3 Extension Point Examples

**Plugin Registration (Mapping Types):**

```python
class DataMapper:
    """Extensible mapper with plugin architecture."""
    
    def __init__(self):
        # Registry of mapping type handlers
        self.mapping_handlers = {
            'enum': self._apply_enum_mapping,
            'calculated_field': self._apply_calculated_field,
            'char_to_bit': self._apply_char_to_bit,
            # Extension point: register new handlers
        }
    
    def register_mapping_handler(self, mapping_type: str, handler: Callable):
        """Plugin registration for custom mapping types."""
        self.mapping_handlers[mapping_type] = handler
    
    def apply_mapping_contract(self, xml_data, contract):
        for field_mapping in contract.mappings:
            for mapping_type in field_mapping.mapping_type:
                # Lookup and execute handler
                handler = self.mapping_handlers.get(mapping_type)
                if handler:
                    value = handler(value, field_mapping)
```

**Configuration-Driven Extension:**

```json
{
  "mappings": [
    {
      "target_column": "full_name",
      "mapping_type": ["calculated_field"],
      "expression": "first_name + ' ' + last_name"
    }
  ]
}
```

```python
# CalculatedFieldEngine executes expression from contract
class CalculatedFieldEngine:
    def evaluate(self, expression: str, context: Dict) -> Any:
        """Execute expression with context variables."""
        # Safe eval with restricted scope
        return eval(expression, {"__builtins__": {}}, context)
```

---

## 15. Architectural Decision Records

### 15.1 Architectural Style Decisions

**Decision: Contract-Driven Clean Architecture**

**Context:**
- Multiple product lines (CC, RL) with different XML structures
- Need to support schema isolation (sandbox, migration, dbo)
- Operational changes should not require code deployment
- Business rules must be auditable and version-controlled

**Alternatives Considered:**
1. **Hardcoded Mapping Logic:** Fast to implement initially, but inflexible
2. **Database-Driven Config:** Runtime changes, but harder to version control
3. **Code Generation:** Type-safe, but requires regeneration on contract changes
4. **Contract-Driven (Chosen):** JSON-defined contracts, generic transformation engine

**Decision:**
Implement Contract-Driven Clean Architecture where:
- All transformations defined in `mapping_contract.json`
- Code implements generic transformation engine
- Schema isolation via `target_schema` in contract
- Interface-based design for testability and dependency inversion

**Consequences:**
- ✅ **Positive:** Product lines configurable without code changes
- ✅ **Positive:** Schema isolation enables parallel development
- ✅ **Positive:** Contracts are version-controlled and auditable
- ❌ **Negative:** Contract validation adds complexity
- ❌ **Negative:** Runtime errors if contract misconfigured (not compile-time)

### 15.2 Technology Selection Decisions

**Decision: lxml for XML Parsing**

**Context:**
- Need to parse large XML documents (10-100 KB per record)
- XML stored in database text columns (not files)
- Performance critical (target: 2,500+ records/min)

**Alternatives:**
1. **xml.etree.ElementTree (stdlib):** Built-in, but slower
2. **lxml (Chosen):** C-based, high performance, XPath support
3. **BeautifulSoup:** Robust for malformed XML, but slower

**Decision:** Use lxml for performance and XPath support

**Consequences:**
- ✅ **Positive:** 5-10x faster than stdlib ElementTree
- ✅ **Positive:** Native XPath support simplifies element extraction
- ❌ **Negative:** External dependency (not stdlib)
- ❌ **Negative:** C extension requires compiler for installation

---

**Decision: pyodbc for Database Access**

**Context:**
- Target database: Microsoft SQL Server
- Windows environment with Windows Authentication
- Need bulk insert performance for high throughput

**Alternatives:**
1. **ODBC (pyodbc) (Chosen):** Native SQL Server protocol, fast_executemany support
2. **SQLAlchemy:** ORM abstraction, but ORM overhead unneeded
3. **pymssql:** Pure Python, but slower and less SQL Server optimization

**Decision:** Use pyodbc with `fast_executemany=True` for bulk inserts

**Consequences:**
- ✅ **Positive:** Native SQL Server bulk protocol (100x faster than row-by-row)
- ✅ **Positive:** Windows Authentication support (no credentials in code)
- ✅ **Positive:** Direct SQL control (no ORM overhead)
- ❌ **Negative:** Windows-only (ODBC driver requirement)

---

**Decision: Multiprocessing (not Threading or Async)**

**Context:**
- CPU-bound workload (XML parsing, data transformation)
- Need parallelism to saturate multi-core CPUs
- Python GIL prevents true threading parallelism

**Alternatives:**
1. **Threading:** GIL prevents parallel execution for CPU-bound tasks
2. **Asyncio:** Not suitable for CPU-bound workloads
3. **Multiprocessing (Chosen):** True parallelism, bypasses GIL

**Decision:** Use `multiprocessing.Pool` for worker parallelism

**Consequences:**
- ✅ **Positive:** True parallelism (one worker per CPU core)
- ✅ **Positive:** Worker isolation (failures don't affect other workers)
- ❌ **Negative:** Process overhead (memory duplication)
- ❌ **Negative:** No shared state (requires Manager for coordination)

### 15.3 Implementation Approach Decisions

**Decision: Atomic Transactions Per Application**

**Context:**
- One application spans 10-15 tables (app_base, contact_base, child tables)
- Database constraints enforce FK relationships
- Need to prevent orphaned records (child without parent)

**Alternatives:**
1. **Table-by-Table Commits:** Fast, but allows orphans on failure
2. **Batch-Level Transactions:** Group multiple apps, but partial failures complex
3. **Application-Level Transactions (Chosen):** One transaction per app (all-or-nothing)

**Decision:** One atomic transaction per application (all tables + processing_log)

**Consequences:**
- ✅ **Positive:** Zero orphaned records (all-or-nothing guarantee)
- ✅ **Positive:** Resume-safe (processing_log tracks completion atomically)
- ✅ **Positive:** Deterministic debugging (known state on failure)
- ❌ **Negative:** 14% throughput reduction vs. table-by-table commits
- ✅ **Trade-off Justified:** Data integrity > throughput

---

**Decision: FK-Ordered Insertion**

**Context:**
- Database enforces FK constraints
- Child tables reference parent tables
- Inserting out-of-order causes FK violations

**Alternatives:**
1. **Disable FK Constraints:** Fast, but violates data integrity
2. **Dependency Analysis at Runtime:** Flexible, but complex and slow
3. **Contract-Defined Order (Chosen):** `table_insertion_order` in contract

**Decision:** Define FK dependency order in `table_insertion_order` field of contract

**Consequences:**
- ✅ **Positive:** Simple, predictable, auditable
- ✅ **Positive:** Contract documents FK dependencies explicitly
- ✅ **Positive:** MigrationEngine enforces order automatically
- ❌ **Negative:** Manual maintenance (must update on schema changes)

---

**Decision: NOLOCK Hints for Duplicate Detection**

**Context:**
- Duplicate contact detection queries block each other (RangeS-U locks)
- Concurrent workers serialize on duplicate checks (performance bottleneck)
- Read-committed isolation not required for duplicate detection

**Alternatives:**
1. **Read Committed (Default):** Safe, but serializes workers
2. **WITH (NOLOCK) (Chosen):** Dirty reads allowed, but prevents blocking
3. **Read Uncommitted Isolation Level:** Session-level change, affects all queries

**Decision:** Apply `WITH (NOLOCK)` hint to duplicate detection queries only

**Consequences:**
- ✅ **Positive:** 10x throughput improvement (workers don't block each other)
- ✅ **Positive:** Precise control (only specific queries affected)
- ❌ **Negative:** Potential for dirty reads (acceptable for duplicate checks)
- ✅ **Trade-off Justified:** Performance > strict read consistency for this use case

---

## 16. Architecture Governance

### 16.1 Architectural Consistency Maintenance

**Code Review Guidelines:**
1. **Contract-First Rule:** All transformations must be in contract, not code
2. **Schema Isolation Rule:** No hardcoded schema names (`[dbo]` forbidden)
3. **Interface Compliance:** New components must implement interfaces
4. **Layer Separation:** Infrastructure never depends on orchestration

**Peer Review Checklist:**
- [ ] Contract changes documented in commit message
- [ ] Tests updated for new functionality
- [ ] No hardcoded schema names or environment-specific logic
- [ ] Interfaces used for dependencies (not concrete classes)
- [ ] Exception handling follows domain exception hierarchy

### 16.2 Automated Architectural Compliance Checks

**Type Checking (mypy):**
```powershell
mypy xml_extractor/ --strict
# Ensures interface compliance, type safety
```

**Import Analysis:**
```python
# Verify domain layer has no infrastructure imports
import ast
import sys

domain_files = ['xml_extractor/models.py']
forbidden_imports = ['pyodbc', 'lxml', 'multiprocessing']

for file in domain_files:
    tree = ast.parse(open(file).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if any(forbidden in alias.name for forbidden in forbidden_imports):
                    print(f"ERROR: {file} imports forbidden module {alias.name}")
                    sys.exit(1)
```

**Contract Validation:**
```powershell
# Automated contract schema validation
python -m xml_extractor.validation.mapping_contract_validator config/mapping_contract.json
```

### 16.3 Documentation Practices

**Architecture Documentation:**
- **Architecture Guide:** `docs/architecture.md` (system design, data flow, FK ordering)
- **Bulk Insert Architecture:** `docs/bulk-insert-architecture.md` (performance optimizations)
- **Parallel Processing:** `docs/parallel-processing.md` (multi-process coordination)
- **This Blueprint:** `docs/Project_Architecture_Blueprint.md` (comprehensive reference)

**Code Documentation:**
```python
class DataMapper(DataMapperInterface):
    """
    Contract-driven XML-to-relational transformer.
    
    Applies field mappings, enum transformations, and calculated fields
    per MappingContract configuration.
    
    Architecture:
        - Application Layer: Implements business transformation logic
        - Dependencies: models.MappingContract, CalculatedFieldEngine
        - Interface: Implements DataMapperInterface for testability
    
    Usage:
        mapper = DataMapper('config/mapping_contract.json')
        mapped_data = mapper.apply_mapping_contract(xml_data, contract)
    """
```

**Decision Records:**
- `docs/decisions/bug-fixes.md` - Critical bugs resolved
- `docs/decisions/performance-findings.md` - Performance decisions
- `docs/decisions/*.md` - Architectural decision records

---

## 17. Blueprint for New Development

### 17.1 Development Workflow

**Adding a New Feature (Example: Add New Mapping Type)**

**Phase 1: Understanding & Design**
1. **Review:** Read `.github/skills/common-patterns/` for similar patterns
2. **Design:** Sketch how new mapping type fits into DataMapper
3. **Contract Design:** Define JSON schema for new mapping type

**Phase 2: Test-First Development**
1. **Write Test:**
   ```python
   # tests/unit/test_data_mapper.py
   def test_new_mapping_type():
       mapper = DataMapper()
       field_mapping = FieldMapping(mapping_type=['new_type'], ...)
       result = mapper._apply_new_mapping_type('input', field_mapping)
       assert result == 'expected_output'
   ```

2. **Run Test (should fail):**
   ```powershell
   pytest tests/unit/test_data_mapper.py::test_new_mapping_type -v
   ```

**Phase 3: Implementation**
1. **Implement Handler:**
   ```python
   # xml_extractor/mapping/data_mapper.py
   class DataMapper:
       def apply_mapping_contract(self, xml_data, contract):
           for field_mapping in contract.mappings:
               if 'new_type' in field_mapping.mapping_type:
                   value = self._apply_new_mapping_type(value, field_mapping)
       
       def _apply_new_mapping_type(self, value, field_mapping):
           # Implementation
   ```

2. **Run Test (should pass):**
   ```powershell
   pytest tests/unit/test_data_mapper.py::test_new_mapping_type -v
   ```

**Phase 4: Integration Testing**
1. **Write Integration Test:**
   ```python
   # tests/integration/test_new_mapping_type.py
   def test_new_mapping_type_end_to_end(test_database):
       # Complete pipeline test with new mapping type
   ```

2. **Run Integration Suite:**
   ```powershell
   pytest tests/integration/ -v
   ```

**Phase 5: Documentation & Review**
1. **Update Contract Schema:** Document new mapping type in `config/samples/`
2. **Update Common Patterns:** Add example to `.github/skills/common-patterns/`
3. **Commit:** `git commit -m "feat: add new_mapping_type support"`

### 17.2 Implementation Templates

**New Component Template:**

```python
"""
Module: xml_extractor/category/component_name.py

Purpose: [Brief description of component purpose]

Architecture:
    - Layer: [Domain/Application/Infrastructure/Orchestration]
    - Dependencies: [List key dependencies]
    - Interface: [Implements ComponentInterface]
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from xml_extractor.models import MappingContract
from xml_extractor.interfaces import ComponentInterface
from xml_extractor.exceptions import ComponentError


class ComponentName(ComponentInterface):
    """
    [Component description]
    
    Responsibilities:
        - [Responsibility 1]
        - [Responsibility 2]
    
    Usage:
        component = ComponentName(config)
        result = component.process(data)
    """
    
    def __init__(self, config: MappingContract):
        """Initialize component with configuration."""
        self.config = config
    
    def process(self, data: Dict) -> Dict:
        """
        [Process description]
        
        Args:
            data: Input data dictionary
        
        Returns:
            Processed data dictionary
        
        Raises:
            ComponentError: If processing fails
        """
        try:
            # Implementation
            result = self._internal_processing(data)
            return result
        except Exception as e:
            raise ComponentError(f"Processing failed: {e}")
    
    def _internal_processing(self, data: Dict) -> Dict:
        """Internal processing logic."""
        # Implementation
        pass
```

**New Test Template:**

```python
"""
Tests for ComponentName

Test Categories:
    - Unit: Isolated component testing
    - Integration: Component integration with dependencies
    - E2E: Complete pipeline testing
"""

import pytest
from xml_extractor.category.component_name import ComponentName
from xml_extractor.models import MappingContract


class TestComponentName:
    """Unit tests for ComponentName."""
    
    @pytest.fixture
    def component(self):
        """Fixture providing ComponentName instance."""
        config = MappingContract(...)
        return ComponentName(config)
    
    def test_process_valid_input(self, component):
        """Test processing with valid input."""
        data = {'key': 'value'}
        result = component.process(data)
        assert result == expected_result
    
    def test_process_invalid_input(self, component):
        """Test error handling with invalid input."""
        data = {'invalid': 'data'}
        with pytest.raises(ComponentError):
            component.process(data)


class TestComponentNameIntegration:
    """Integration tests for ComponentName."""
    
    @pytest.fixture
    def test_database(self):
        """Fixture providing test database."""
        # Setup test database
        yield db
        # Teardown
    
    def test_end_to_end_processing(self, test_database):
        """Test complete processing pipeline."""
        # End-to-end test
```

### 17.3 Common Pitfalls

**❌ Pitfall 1: Hardcoding Schema Names**
```python
# WRONG
query = f"SELECT * FROM [dbo].[app_base]"

# RIGHT
query = f"SELECT * FROM [{self.target_schema}].[app_base]"
```

**❌ Pitfall 2: Mapping Logic in Code (Not Contract)**
```python
# WRONG
if source == 'type_A':
    value = transform_a(value)

# RIGHT - Define in contract
"enum_mappings": {"type_A": "mapped_value"}
```

**❌ Pitfall 3: Table-by-Table Transactions**
```python
# WRONG - Can create orphans
for table_name, records in mapped_data.items():
    self.execute_bulk_insert(records, table_name)
    conn.commit()  # Partial commit!

# RIGHT - Atomic transaction
with self.transaction(conn):
    for table_name in self.table_insertion_order:
        self.execute_bulk_insert(mapped_data[table_name], table_name)
    # Single commit for all tables
```

**❌ Pitfall 4: Ignoring FK Ordering**
```python
# WRONG - May violate FK constraints
for table_name, records in mapped_data.items():
    self.execute_bulk_insert(records, table_name)

# RIGHT - Respect FK dependencies
for table_name in self.contract.table_insertion_order:
    self.execute_bulk_insert(mapped_data[table_name], table_name)
```

**❌ Pitfall 5: Not Using Interfaces**
```python
# WRONG - Tight coupling
def __init__(self):
    self.parser = XMLParser()  # Concrete class

# RIGHT - Dependency inversion
def __init__(self, parser: XMLParserInterface):
    self.parser = parser  # Interface
```

### 17.4 Performance Considerations

**Optimization Checklist:**
- [ ] Use `cursor.fast_executemany = True` for SQL Server bulk inserts
- [ ] Batch inserts (500-1000 records per `executemany()`)
- [ ] Use `WITH (NOLOCK)` for read-only queries that can tolerate dirty reads
- [ ] Reuse database connections (one per worker, not per operation)
- [ ] Stream parsing for large XML files (avoid loading entire file)
- [ ] Use multiprocessing for CPU-bound parallelism (not threading)

**Performance Anti-Patterns:**
```python
# ❌ Row-by-row inserts
for record in records:
    cursor.execute(sql, record)

# ✅ Bulk insert
cursor.fast_executemany = True
cursor.executemany(sql, records)
```

```python
# ❌ Loading entire XML into memory
xml_content = open('huge_file.xml').read()

# ✅ Streaming parser
for event, element in etree.iterparse('huge_file.xml'):
    process(element)
```

### 17.5 Testing Blind Spots

**Common Untested Scenarios:**
1. **Concurrent Workers:** Test with multiple workers to detect race conditions
2. **Database Failures:** Test transaction rollback on FK violations
3. **Malformed XML:** Test parser with edge cases (empty elements, special chars)
4. **Enum Mapping Failures:** Test behavior when enum value not in mapping
5. **Large Datasets:** Test with 10k+ records to detect memory leaks

**Test Coverage Gaps:**
```powershell
# Check test coverage
pytest tests/ --cov=xml_extractor --cov-report=html
# Open htmlcov/index.html to see coverage gaps
```

---

## Appendix: Key File Reference

### Core Domain Models
- [xml_extractor/models.py](../xml_extractor/models.py) - Domain models and data structures
- [xml_extractor/interfaces.py](../xml_extractor/interfaces.py) - Abstract interfaces
- [xml_extractor/exceptions.py](../xml_extractor/exceptions.py) - Exception hierarchy

### Infrastructure Components
- [xml_extractor/parsing/xml_parser.py](../xml_extractor/parsing/xml_parser.py) - lxml adapter
- [xml_extractor/database/migration_engine.py](../xml_extractor/database/migration_engine.py) - Bulk insert engine
- [xml_extractor/config/config_manager.py](../xml_extractor/config/config_manager.py) - Configuration loader

### Application Logic
- [xml_extractor/mapping/data_mapper.py](../xml_extractor/mapping/data_mapper.py) - Data transformation
- [xml_extractor/validation/](../xml_extractor/validation/) - Multi-stage validation
- [xml_extractor/processing/parallel_coordinator.py](../xml_extractor/processing/parallel_coordinator.py) - Multi-process orchestration

### Entry Points
- [production_processor.py](../production_processor.py) - Main production script
- [xml_extractor/cli.py](../xml_extractor/cli.py) - CLI interface

### Configuration
- [config/mapping_contract.json](../config/mapping_contract.json) - CC product line contract
- [config/mapping_contract_rl.json](../config/mapping_contract_rl.json) - RL product line contract

### Documentation
- [docs/architecture.md](architecture.md) - System architecture guide
- [docs/bulk-insert-architecture.md](bulk-insert-architecture.md) - Performance architecture
- [docs/testing-philosophy.md](testing-philosophy.md) - Testing approach
- [docs/operator-guide.md](operator-guide.md) - Operations manual

### Development Guidance
- [.github/skills/common-patterns/SKILL.md](../.github/skills/common-patterns/SKILL.md) - Reusable code patterns
- [.github/skills/system-constraints/SKILL.md](../.github/skills/system-constraints/SKILL.md) - Non-negotiable principles
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) - Development guidelines

---

## Keeping This Blueprint Updated

**Recommendation:** Regenerate this blueprint whenever:
1. Major architectural changes occur (new layers, patterns, or design decisions)
2. New product lines added (new mapping contracts)
3. Core component responsibilities change
4. Performance optimizations implemented that affect architecture

**Update Process:**
1. Run architecture analysis tools (import checker, type checker)
2. Review recent architectural decision records
3. Update relevant sections in this blueprint
4. Commit with message: `docs: update architecture blueprint - [reason]`

**Last Updated:** February 14, 2026  
**Next Review:** After next major feature release or architectural change
