# Implementation Plan

## Project Scope Note
**IMPORTANT**: This XML extraction project assumes that:
- Database tables already exist in the target SQL Server database
- Enum values and lookup data are already populated
- Database schema setup is handled separately by database administrators or setup scripts
- This project focuses solely on extracting XML data and inserting it into existing tables

- [x] 1. Set up Python project structure and core data classes for credit application processing
  - Create Python package structure for configuration, parsing, mapping, and database components
  - Define Python dataclasses for MappingContract, FieldMapping, RelationshipMapping, and ProcessingConfig
  - Set up requirements.txt with lxml, pyodbc, and other dependencies for Provenir XML processing
  - Create base classes and abstract interfaces for credit application system components
  - _Requirements: 1.1, 3.1_

- [ ] 2. Implement configuration management system for credit application XML
  - [x] 2.1 Create ConfigurationManager class implementing ConfigurationManagerInterface
    - Implement load_mapping_contract() to parse JSON mapping contract files for Provenir XML structure
    - Implement load_table_structure() to parse credit application SQL CREATE TABLE scripts and data-model.md
    - Implement load_sample_xml() to load Provenir sample XML documents from directory
    - Implement get_processing_config() to return ProcessingConfig with defaults for credit application processing
    - Add validation for mapping contract completeness including app_id and con_id validation
    - _Requirements: 3.1, 3.4_

  - [x] 2.2 Create credit application configuration files and validation
    - Update JSON mapping contract to reflect Provenir XML structure with app_id/con_id identifiers
    - Create enum mapping configurations for status, decision, and application source codes
    - Create bit conversion mappings for Y/N flags to database bit fields
    - Update sample SQL CREATE TABLE scripts to match credit application schema
    - Update data-model.md to document credit application table relationships
    - _Requirements: 2.2, 3.1_

- [ ] 3. Build high-performance XML parsing engine
  - [x] 3.1 Create XMLParser class implementing XMLParserInterface
    - Implement parse_xml_stream() using lxml.etree.iterparse() for memory-efficient processing
    - Implement validate_xml_structure() with comprehensive XML validation
    - Implement extract_elements() with recursive element extraction and XPath support
    - Implement extract_attributes() with type-aware attribute extraction
    - Add XML namespace handling with prefix resolution using lxml
    - Create detailed error logging with source record identification
    - _Requirements: 1.1, 1.3, 4.1, 4.4, 5.3_

- [x] 4. Develop data mapping and transformation engine
  - [x] 4.1 Create DataMapper class implementing DataMapperInterface
    - Implement apply_mapping_contract() to transform XML data using mapping contracts
    - Implement transform_data_types() with comprehensive type conversion and fallback handling
    - Implement handle_nested_elements() for parent-child relationship detection and foreign key generation
    - Build transformation rule engine for calculated fields
    - Create data validation and quality checking with detailed error reporting
    - **CORE MAPPING PRINCIPLES IMPLEMENTED**:
      - **Principle 1**: Do not add columns to INSERT statement if there isn't a valid value
      - **Principle 2**: Always use enum mapping from contract, never resolve to invalid values (e.g., enum columns cannot be 0)
      - **Implementation**: Enum columns with no valid mapping return None and are excluded from INSERT entirely
    - Implement fallback strategies for missing or invalid data
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 3.1, 3.5_

  - [x] 4.2 Create comprehensive data integrity validation system
    - Build end-to-end validation comparing source XML with extracted relational data
    - Implement referential integrity checking for generated foreign key relationships
    - Create constraint compliance validation for all target tables
    - Add data quality reporting with detailed error information
    - _Requirements: 5.1, 5.2, 5.5_

- [ ] 5. Build migration engine with performance optimization
  - [x] 5.1 Create MigrationEngine class implementing MigrationEngineInterface
    - Implement execute_bulk_insert() using pyodbc fast_executemany for high-performance bulk inserts
    - Implement create_target_tables() to validate that required tables exist (NOTE: Does not create tables - assumes they exist)
    - Implement validate_target_schema() using SQL Server system views (INFORMATION_SCHEMA)
    - Implement track_progress() with real-time progress reporting
    - Create pyodbc connection management for SQL Server Express LocalDB
    - Add T-SQL transaction management with explicit BEGIN/COMMIT/ROLLBACK
    - **IMPORTANT**: This project assumes database tables and enums already exist. Table creation and enum insertion should be handled separately by database setup scripts or administrators.
    - _Requirements: 3.4, 4.2, 4.3_

  - [ ] 5.2 Implement parallel processing coordination
    - Build multiprocessing.Pool for parallel XML processing across CPU cores
    - Create process-safe work queue distribution using multiprocessing.Queue
    - Implement shared memory progress tracking with multiprocessing.Manager
    - Add coordination between parallel processes and database operations
    - _Requirements: 4.3, 4.5_

- [ ] 6. Add monitoring, logging, and audit capabilities
  - [ ] 6.1 Create PerformanceMonitor class implementing PerformanceMonitorInterface
    - Implement start_monitoring() and stop_monitoring() with ProcessingResult return
    - Implement record_metric() and get_current_metrics() for real-time metrics tracking
    - Build automatic performance adjustment based on system resources
    - Create progress reporting with estimated completion times
    - Add memory usage monitoring and automatic garbage collection optimization
    - _Requirements: 3.2, 4.5_

  - [ ] 6.2 Implement comprehensive audit logging and error handling
    - Create audit columns linking extracted records to source XML data
    - Build processing logs with transformation decisions and data quality issues
    - Implement timestamping for all extraction operations
    - Build checkpoint system for restart capability after failures
    - Implement dead letter queue for problematic records
    - Create detailed error reporting with source record identifiers
    - _Requirements: 3.5, 5.1, 5.2, 5.3_

- [ ] 7. Implement incremental processing and optimization
  - [ ] 7.1 Create incremental processing logic
    - Build change detection for modified XML data in subsequent runs
    - Implement delta processing to handle only new or updated records
    - Create state management for tracking processed records
    - Add configurable memory limits with automatic adjustment
    - _Requirements: 4.1, 4.5, 5.5_

- [ ] 8. Create command-line interface and orchestration system
  - [ ] 8.1 Build comprehensive CLI application
    - Enhance cli.py with click-based command-line interface for running extraction jobs
    - Implement configuration file loading and validation
    - Build help system and usage documentation
    - Create job queue management for multiple extraction tasks
    - Build execution status tracking and reporting
    - Implement graceful shutdown and cleanup procedures
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 8.2 Create main orchestration system
    - Build XMLExtractor main class that coordinates all components
    - Implement end-to-end extraction workflow using all interfaces
    - Add integration between ConfigurationManager, XMLParser, DataMapper, MigrationEngine, and PerformanceMonitor
    - Create comprehensive error handling and recovery across all components
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

- [ ] 9. Create comprehensive testing suite
  - [ ] 9.1 Write unit tests for core components
    - Create unit tests for ConfigurationManager class methods
    - Write unit tests for XMLParser class with sample XML documents
    - Build unit tests for DataMapper class with mapping contract validation
    - Create unit tests for MigrationEngine database operations
    - Write unit tests for PerformanceMonitor metrics tracking
    - Add tests for all custom exception classes
    - **Implement comprehensive validation framework with real sample XML data**
    - **Use sample-source-xml-contact-test.xml for testing ghost nodes and edge cases**
    - _Requirements: 1.1, 2.1, 2.4, 5.3_

  - [x] 9.2 Create end-to-end integration test with real database insertion
    - **COMPLETED**: Test successfully inserts XML data into real database tables
    - **NEXT**: Manual validation of database records (cleanup disabled for inspection)
    - **VALIDATION TARGET**: Check app_id = 443306 in all target tables

  - [x] 9.3 Complete mapping contract with missing XML paths and tables






    - **CRITICAL**: Add missing XML path mappings identified from manual database validation:
      - `app_base.app_type_enum` from `@app_type_code` (enum value 30 = "PRODB")
      - `app_base.decision_enum` from `app_product/@decision_tp_c` (enum value 50 = "APPRV")
      - `app_base.decision_date` from `app_product/@decision_date`
      - `app_operational_cc.backend_fico_grade` from `app_product/@backend_fico_grade`
      - `app_operational_cc.backend_risk_grade` from `app_product/@backend_risk_grade`
      - `app_operational_cc.regb_start_date` from `app_product/@regb_start_date` (not default_getutcdate_if_null)
      - `app_operational_cc.ssn_match_type_enum` from `application/@ssn_match_flag` (Y=152)
    - **Add missing table mappings**: `app_transactional_cc`, `app_solicited_cc`
    - **Add rmts_info mappings**: `app_pricing_cc.special_flag_5` from `rmts_info/@special_flag_5`
    - **Add contact detail mappings**: `contact_base.cell_phone`, `contact_base.home_phone`
    - **Implement "last valid PR contact" logic** for `app_prod_bcard` data:
      - `app_operational_cc.housing_monthly_payment` from last PR contact `app_prod_bcard/@residence_monthly_pymnt`
      - `app_pricing_cc.credit_line` from last PR contact `app_prod_bcard/@allocated_credit_line`
    - **Add missing contact_address and contact_employment mappings**
    - **Test needs to validate from database that the expected number of rows are present, and the expected values are present**
    - **Definition of Done**: run E2E test/`test_end_to_end_integration.py` must run and manually validated by user that data is present and mapped correctly.
    - _Requirements: 2.2, 4.1, Data Completeness_

  - [ ] 9.4 Create full round-trip integration test (XML → Database → XML)
    - Build test that extracts XML from database and maps back to original structure
    - Implement database-to-XML reverse mapping using complete mapping contracts
    - Verify data integrity through complete round-trip transformation
    - Test with real production XML data from database source tables
    - Validate that extracted and re-mapped data matches original XML structure
    - **This is the ultimate litmus test to prove the complete plumbing works**
    - _Requirements: 1.1, 2.1, 4.1, 5.1, Data Integrity Validation_

- [ ] 10. Code Quality and Refactoring Phase
  - [ ] 10.1 Analyze and refactor mapping logic for consistency
    - Audit DataMapper for duplicate transformation logic and consolidate
    - Review enum mapping, bit conversion, and default value handling for redundancy
    - Standardize error handling patterns across all transformation methods
    - Remove unused transformation paths and deprecated methods
    - _Requirements: Code Quality, Maintainability_

  - [ ] 10.2 Clean up bulk insert debug output and verify None handling
    - Remove debug print statements from bulk insert method
    - Verify that None values are correctly excluded from INSERT statements (already working)
    - Confirm mapping contract correctly handles empty/invalid values per principles
    - Remove temporary debug logging added during troubleshooting
    - _Requirements: 4.3, Code Quality_

  - [ ] 10.3 Clean up test files and consolidate testing approach
    - Remove temporary test files: test_minimal_insert.py, test_fixed_bulk_insert.py, etc.
    - Consolidate test_end_to_end_integration.py and test_live_end_to_end_integration.py
    - Standardize test database setup and cleanup procedures
    - Remove debug print statements and temporary logging
    - _Requirements: Code Quality, Testing Standards_

  - [ ] 10.4 Documentation and configuration cleanup
    - Update mapping contract documentation with new principles
    - Review and clean up unused configuration options
    - Standardize error messages and logging levels
    - Create comprehensive code documentation for mapping principles
    - _Requirements: Documentation, Maintainability_












    - Build complete pipeline test using sample-source-xml-contact-test.xml
    - Create test database setup with required tables (application, contact, contact_address, contact_employment)
    - Implement full workflow: PreProcessingValidator → XMLParser → DataMapper → MigrationEngine
    - Test "last valid element" approach with actual database insertion
    - Verify 2 valid contacts (1 PR, 1 AUTHU) are correctly inserted with proper addresses and employments
    - Add database query validation to confirm data integrity and foreign key relationships
    - Create test cleanup and teardown procedures
    - _Requirements: 4.2, 4.4, 5.1, 5.4, 5.5_

  - [ ] 9.3 Implement integration and performance tests
    - Create end-to-end integration tests with sample data subsets
    - Build performance tests to validate 1000+ records/minute target
    - Write memory usage tests for 5MB XML document processing
    - Create integration tests for parallel processing coordination
    - Build data integrity tests comparing source XML with extracted data
    - _Requirements: 4.2, 4.4, 5.1, 5.4, 5.5_

  - [ ] 9.4 Implement comprehensive validation and testing framework
    - Create PreProcessingValidator class for XML validation before processing
    - Build comprehensive test scenarios using sample-source-xml-contact-test.xml
    - Implement validation for all XML hierarchy rules (con_id, ac_role_tp_c, address_tp_c, employment_tp_c)
    - Create test cases for ghost nodes, invalid attributes, and graceful degradation
    - Build system validation framework to test all components before production
    - Implement batch validation capabilities for processing multiple XML records
    - Create validation documentation and usage examples
    - _Requirements: 1.1, 2.1, 2.4, 5.1, 5.3_

  - [ ]* 9.5 Create extended test coverage and edge cases
    - Write tests for error handling and recovery scenarios
    - Build stress tests for memory management with large XML documents
    - Create tests for concurrent processing and thread safety
    - Write schema compatibility tests for generated table structures
    - Build mapping contract compliance validation tests
    - _Requirements: 2.1, 3.4, 4.1, 4.3, 4.5_