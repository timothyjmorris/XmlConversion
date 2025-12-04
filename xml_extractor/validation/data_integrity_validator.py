"""
Data Integrity Validation Engine (Future Enhancement - Not Yet Deployed)

⚠️ STATUS: Fully implemented but not integrated into production pipeline.

This module provides comprehensive post-extraction validation capabilities including end-to-end
data consistency checks, referential integrity validation, constraint compliance, and quality metrics.
Currently used only in unit tests via validation harness.

DEPLOYMENT STATUS:
- Implementation: Complete (894 lines, 8 comprehensive tests)
- Production Use: Not deployed
- Test Use: Tests in tests/harness/test_validation_harness.py
- Integration: Database constraints currently serve as final validation gate

FUTURE USE CASE:
To deploy comprehensive validation, call validate_extraction_results() after DataMapper completes:

    validator = DataIntegrityValidator()
    result = validator.validate_extraction_results(xml_data, tables, contract)
    if not result.validation_passed and result.has_critical_errors:
        skip_record()  # Prevent insertion of corrupted data

See VALIDATION_MODULE_ANALYSIS.md for deployment roadmap and cost/benefit analysis.
"""

import logging
import time
import uuid

from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from ..models import MappingContract
from ..exceptions import ValidationError
from .validation_models import (
    ValidationResult, 
    ValidationError, 
    IntegrityCheckResult, 
    ValidationConfig,
    ValidationSeverity, 
    ValidationType
)


class DataIntegrityValidator:
    """
    Core validation engine for comprehensive post-extraction checks (Not yet deployed to production).

    ⚠️ STATUS: Fully implemented but not called during production processing. Database constraints
    currently serve as the final validation gate instead.

    DEPLOYMENT: When activated, this validator will perform comprehensive checks after DataMapper
    completes extraction, catching data quality issues before database insertion:
    - End-to-End Consistency: Verifies source XML correctly transformed to target tables
    - Referential Integrity: Validates FK relationships between all related tables
    - Constraint Compliance: Enforces NOT NULL, data types, lengths, business rules
    - Data Quality Metrics: Calculates completeness, validity, accuracy percentages

    See VALIDATION_MODULE_ANALYSIS.md for deployment guidance.
    """

    # Error Handling Strategy:
    # - Categorizes issues by severity (CRITICAL/ERROR/WARNING/INFO)
    # - Provides detailed context including source values, expected values, and record identifiers
    # - Continues validation after non-critical errors to provide complete assessment
    # - Generates actionable error reports for debugging and data quality improvement
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize the data integrity validator with configuration settings.

        Args:
            config: ValidationConfig object controlling which validation types to enable,
                   error thresholds, timeouts, and reporting preferences. If None, uses
                   default configuration with all validation types enabled.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or ValidationConfig()

        
    def validate_extraction_results(
        self,
        source_xml_data: Dict[str, Any],
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        mapping_contract: MappingContract,
        source_record_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Execute comprehensive validation suite on completed extraction results.

        This method orchestrates all configured validation checks to ensure the extracted
        relational data accurately represents the source XML while conforming to database
        constraints and business rules.

        Validation Flow:
        1. End-to-End Consistency: Compares source XML fields with extracted database records
        2. Referential Integrity: Validates foreign key relationships between tables
        3. Constraint Compliance: Checks required fields, data types, and business rules
        4. Data Quality Metrics: Calculates completeness, validity, and accuracy statistics

        Args:
            source_xml_data: Flattened XML data dictionary from XMLParser (XPath-like keys)
            extracted_tables: Dictionary mapping table names to lists of record dictionaries
                            from DataMapper.apply_mapping_contract()
            mapping_contract: FieldMapping definitions used during extraction
            source_record_id: Optional application ID or other identifier for error reporting

        Returns:
            ValidationResult containing:
            - Overall pass/fail status
            - Categorized errors by severity and type
            - Data quality metrics and statistics
            - Integrity check results
            - Execution time and performance data

        Raises:
            No exceptions raised - validation errors are collected and returned in ValidationResult
        """
        start_time = time.time()
        validation_id = str(uuid.uuid4())
        
        result = ValidationResult(
            validation_id=validation_id,
            timestamp=datetime.now(),
            source_record_id=source_record_id
        )
        
        try:
            self.logger.info(f"Starting comprehensive validation {validation_id}")
            
            # Count total records for validation
            result.total_records_validated = sum(len(records) for records in extracted_tables.values())
            
            # Perform validation checks based on configuration
            if self.config.enable_end_to_end_validation:
                self._validate_end_to_end_consistency(
                    source_xml_data, extracted_tables, mapping_contract, result
                )
            
            if self.config.enable_referential_integrity:
                self._validate_referential_integrity(extracted_tables, result)
            
            if self.config.enable_constraint_compliance:
                self._validate_constraint_compliance(extracted_tables, mapping_contract, result)
            
            if self.config.enable_data_quality_checks:
                self._calculate_data_quality_metrics(
                    source_xml_data, extracted_tables, mapping_contract, result
                )
            
            # Determine overall validation status
            result.validation_passed = (
                result.total_errors == 0 if self.config.strict_mode 
                else not result.has_critical_errors
            )
            
            # Calculate execution time
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            # Generate summary
            result.generate_summary()
            
            self.logger.info(
                f"Validation {validation_id} completed: "
                f"{'PASSED' if result.validation_passed else 'FAILED'} "
                f"({result.total_errors} errors, {result.total_warnings} warnings)"
            )
            
        except Exception as e:
            self.logger.error(f"Validation {validation_id} failed with exception: {e}")
            result.add_error(ValidationError(
                error_type=ValidationType.DATA_INTEGRITY,
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation process failed: {e}"
            ))
            result.validation_passed = False
            result.execution_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _validate_end_to_end_consistency(
        self,
        source_xml_data: Dict[str, Any],
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        mapping_contract: MappingContract,
        result: ValidationResult
    ) -> None:
        """Validate consistency between source XML and extracted relational data."""
        check_start = time.time()
        check_result = IntegrityCheckResult(
            check_name="End-to-End Data Consistency",
            passed=True
        )
        
        try:
            self.logger.debug("Starting end-to-end consistency validation")
            
            # Extract key identifiers from source XML
            app_id = self._extract_app_id_from_xml(source_xml_data)
            contact_ids = self._extract_contact_ids_from_xml(source_xml_data)
            
            # Validate app_id consistency
            if app_id:
                self._validate_app_id_consistency(app_id, extracted_tables, result, check_result)
            else:
                result.add_error(ValidationError(
                    error_type=ValidationType.END_TO_END,
                    severity=ValidationSeverity.CRITICAL,
                    message="Missing app_id in source XML data"
                ))
                check_result.errors_found += 1
                check_result.passed = False
            
            # Validate contact_id consistency
            if contact_ids:
                self._validate_contact_ids_consistency(contact_ids, extracted_tables, result, check_result)
            else:
                result.add_error(ValidationError(
                    error_type=ValidationType.END_TO_END,
                    severity=ValidationSeverity.CRITICAL,
                    message="No valid contact IDs found in source XML data"
                ))
                check_result.errors_found += 1
                check_result.passed = False
            
            # Validate field-level data consistency
            self._validate_field_level_consistency(
                source_xml_data, extracted_tables, mapping_contract, result, check_result
            )
            
            # Count records checked
            check_result.records_checked = sum(len(records) for records in extracted_tables.values())
            
        except Exception as e:
            self.logger.error(f"End-to-end validation failed: {e}")
            result.add_error(ValidationError(
                error_type=ValidationType.END_TO_END,
                severity=ValidationSeverity.ERROR,
                message=f"End-to-end validation error: {e}"
            ))
            check_result.errors_found += 1
            check_result.passed = False
        
        check_result.execution_time_ms = (time.time() - check_start) * 1000
        result.add_integrity_check(check_result)
    
    def _validate_referential_integrity(
        self,
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        result: ValidationResult
    ) -> None:
        """Validate referential integrity of foreign key relationships."""
        check_start = time.time()
        check_result = IntegrityCheckResult(
            check_name="Referential Integrity",
            passed=True
        )
        
        try:
            self.logger.debug("Starting referential integrity validation")
            
            # Collect all primary keys
            app_ids = self._collect_primary_keys(extracted_tables, 'app_base', 'app_id')
            con_ids = self._collect_primary_keys(extracted_tables, 'app_contact_base', 'con_id')
            
            # Validate app_id foreign key references
            app_fk_tables = [
                'app_operational_cc', 'app_contact_base', 'app_contact_address', 'app_contact_employment'
            ]
            for table_name in app_fk_tables:
                if table_name in extracted_tables:
                    self._validate_foreign_key_references(
                        extracted_tables[table_name], 'app_id', app_ids,
                        table_name, 'app_base', result, check_result
                    )
            
            # Validate con_id foreign key references
            con_fk_tables = ['app_contact_address', 'app_contact_employment']
            for table_name in con_fk_tables:
                if table_name in extracted_tables:
                    self._validate_foreign_key_references(
                        extracted_tables[table_name], 'con_id', con_ids,
                        table_name, 'app_contact_base', result, check_result
                    )
            
            # Count records checked
            check_result.records_checked = sum(
                len(extracted_tables.get(table, [])) for table in app_fk_tables + con_fk_tables
            )
            
        except Exception as e:
            self.logger.error(f"Referential integrity validation failed: {e}")
            result.add_error(ValidationError(
                error_type=ValidationType.REFERENTIAL_INTEGRITY,
                severity=ValidationSeverity.ERROR,
                message=f"Referential integrity validation error: {e}"
            ))
            check_result.errors_found += 1
            check_result.passed = False
        
        check_result.execution_time_ms = (time.time() - check_start) * 1000
        result.add_integrity_check(check_result)
    
    def _validate_constraint_compliance(
        self,
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        mapping_contract: MappingContract,
        result: ValidationResult
    ) -> None:
        """Validate compliance with database constraints."""
        check_start = time.time()
        check_result = IntegrityCheckResult(
            check_name="Constraint Compliance",
            passed=True
        )
        
        try:
            self.logger.debug("Starting constraint compliance validation")
            
            for table_name, records in extracted_tables.items():
                for record_index, record in enumerate(records):
                    # Validate required fields (NOT NULL constraints)
                    self._validate_required_fields(
                        record, table_name, record_index, result, check_result
                    )
                    
                    # Validate data type constraints
                    self._validate_data_type_constraints(
                        record, table_name, record_index, mapping_contract, result, check_result
                    )
                    
                    # Validate field length constraints
                    self._validate_field_length_constraints(
                        record, table_name, record_index, mapping_contract, result, check_result
                    )
                    
                    # Validate business rule constraints
                    self._validate_business_rule_constraints(
                        record, table_name, record_index, result, check_result
                    )
            
            check_result.records_checked = sum(len(records) for records in extracted_tables.values())
            
        except Exception as e:
            self.logger.error(f"Constraint compliance validation failed: {e}")
            result.add_error(ValidationError(
                error_type=ValidationType.CONSTRAINT_COMPLIANCE,
                severity=ValidationSeverity.ERROR,
                message=f"Constraint compliance validation error: {e}"
            ))
            check_result.errors_found += 1
            check_result.passed = False
        
        check_result.execution_time_ms = (time.time() - check_start) * 1000
        result.add_integrity_check(check_result)
    
    def _calculate_data_quality_metrics(
        self,
        source_xml_data: Dict[str, Any],
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        mapping_contract: MappingContract,
        result: ValidationResult
    ) -> None:
        """Calculate comprehensive data quality metrics."""
        try:
            self.logger.debug("Calculating data quality metrics")
            
            total_fields = 0
            populated_fields = 0
            valid_fields = 0
            
            for table_name, records in extracted_tables.items():
                for record in records:
                    for field_name, field_value in record.items():
                        total_fields += 1
                        
                        # Check if field is populated
                        if field_value is not None and field_value != '':
                            populated_fields += 1
                            
                            # Check if field value is valid (basic validation)
                            if self._is_field_value_valid(field_value, field_name):
                                valid_fields += 1
            
            # Calculate quality metrics
            completeness = (populated_fields / total_fields * 100) if total_fields > 0 else 0
            validity = (valid_fields / populated_fields * 100) if populated_fields > 0 else 0
            accuracy = (valid_fields / total_fields * 100) if total_fields > 0 else 0
            
            result.data_quality_metrics = {
                'completeness_percentage': round(completeness, 2),
                'validity_percentage': round(validity, 2),
                'accuracy_percentage': round(accuracy, 2),
                'total_fields': total_fields,
                'populated_fields': populated_fields,
                'valid_fields': valid_fields,
                'tables_processed': len(extracted_tables),
                'total_records': sum(len(records) for records in extracted_tables.values())
            }
            
            # Add quality warnings if metrics are below thresholds
            if completeness < 80:
                result.add_error(ValidationError(
                    error_type=ValidationType.DATA_QUALITY,
                    severity=ValidationSeverity.WARNING,
                    message=f"Low data completeness: {completeness:.1f}% (threshold: 80%)"
                ))
            
            if validity < 90:
                result.add_error(ValidationError(
                    error_type=ValidationType.DATA_QUALITY,
                    severity=ValidationSeverity.WARNING,
                    message=f"Low data validity: {validity:.1f}% (threshold: 90%)"
                ))
            
        except Exception as e:
            self.logger.error(f"Data quality metrics calculation failed: {e}")
            result.add_error(ValidationError(
                error_type=ValidationType.DATA_QUALITY,
                severity=ValidationSeverity.ERROR,
                message=f"Data quality metrics calculation error: {e}"
            ))
    
    def _extract_app_id_from_xml(self, xml_data: Dict[str, Any]) -> Optional[str]:
        """Extract app_id from XML data structure."""
        try:
            # Navigate to /Provenir/Request/@ID
            if 'Provenir' in xml_data and 'Request' in xml_data['Provenir']:
                request = xml_data['Provenir']['Request']
                if isinstance(request, dict) and 'ID' in request:
                    return str(request['ID'])
                elif isinstance(request, list) and len(request) > 0 and 'ID' in request[0]:
                    return str(request[0]['ID'])
        except Exception as e:
            self.logger.warning(f"Failed to extract app_id from XML: {e}")
        return None
    
    def _extract_contact_ids_from_xml(self, xml_data: Dict[str, Any]) -> List[str]:
        """Extract all contact IDs from XML data structure."""
        contact_ids = []
        try:
            # Navigate to contact elements
            contacts = self._navigate_to_contacts_in_xml(xml_data)
            for contact in contacts:
                if isinstance(contact, dict) and 'con_id' in contact and contact['con_id']:
                    contact_ids.append(str(contact['con_id']))
        except Exception as e:
            self.logger.warning(f"Failed to extract contact IDs from XML: {e}")
        return contact_ids
    
    def _navigate_to_contacts_in_xml(self, xml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Navigate to contact elements in XML structure."""
        try:
            path = xml_data.get('Provenir', {}).get('Request', {}).get('CustData', {}).get('application', {}).get('contact', [])
            if isinstance(path, dict):
                return [path]
            elif isinstance(path, list):
                return path
        except Exception:
            pass
        return []
    
    def _validate_app_id_consistency(
        self,
        source_app_id: str,
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate app_id consistency between source and extracted data."""
        # Check app_base table
        if 'app_base' in extracted_tables:
            for record_index, record in enumerate(extracted_tables['app_base']):
                extracted_app_id = str(record.get('app_id', ''))
                if extracted_app_id != source_app_id:
                    result.add_error(ValidationError(
                        error_type=ValidationType.END_TO_END,
                        severity=ValidationSeverity.ERROR,
                        message=f"app_id mismatch: source='{source_app_id}', extracted='{extracted_app_id}'",
                        table_name='app_base',
                        record_index=record_index,
                        field_name='app_id',
                        expected_value=source_app_id,
                        actual_value=extracted_app_id
                    ))
                    check_result.errors_found += 1
                    check_result.passed = False
    
    def _validate_contact_ids_consistency(
        self,
        source_contact_ids: List[str],
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate contact_id consistency between source and extracted data."""
        if 'app_contact_base' in extracted_tables:
            extracted_contact_ids = set()
            for record_index, record in enumerate(extracted_tables['app_contact_base']):
                extracted_con_id = str(record.get('con_id', ''))
                extracted_contact_ids.add(extracted_con_id)
                
                if extracted_con_id not in source_contact_ids:
                    result.add_error(ValidationError(
                        error_type=ValidationType.END_TO_END,
                        severity=ValidationSeverity.ERROR,
                        message=f"Unexpected con_id in extracted data: '{extracted_con_id}'",
                        table_name='app_contact_base',
                        record_index=record_index,
                        field_name='con_id',
                        expected_value=source_contact_ids,
                        actual_value=extracted_con_id
                    ))
                    check_result.errors_found += 1
                    check_result.passed = False
            
            # Check for missing contact IDs
            for source_con_id in source_contact_ids:
                if source_con_id not in extracted_contact_ids:
                    result.add_error(ValidationError(
                        error_type=ValidationType.END_TO_END,
                        severity=ValidationSeverity.WARNING,
                        message=f"Missing con_id in extracted data: '{source_con_id}'",
                        table_name='app_contact_base',
                        field_name='con_id',
                        expected_value=source_con_id
                    ))
                    check_result.warnings_found += 1
    
    def _validate_field_level_consistency(
        self,
        source_xml_data: Dict[str, Any],
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        mapping_contract: MappingContract,
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate field-level consistency between source XML and extracted data."""
        # Sample a subset of fields for validation to avoid performance issues
        sample_mappings = mapping_contract.mappings[:20]  # Validate first 20 mappings
        
        for mapping in sample_mappings:
            try:
                # Extract value from source XML
                source_value = self._extract_value_from_xml_path(source_xml_data, mapping.xml_path, mapping.xml_attribute)
                
                # Find corresponding extracted value
                if mapping.target_table in extracted_tables:
                    for record_index, record in enumerate(extracted_tables[mapping.target_table]):
                        extracted_value = record.get(mapping.target_column)
                        
                        # Compare values (with type conversion consideration)
                        if not self._values_are_equivalent(source_value, extracted_value, mapping.data_type):
                            result.add_error(ValidationError(
                                error_type=ValidationType.END_TO_END,
                                severity=ValidationSeverity.WARNING,
                                message=f"Field value mismatch for {mapping.xml_path}",
                                table_name=mapping.target_table,
                                record_index=record_index,
                                field_name=mapping.target_column,
                                expected_value=source_value,
                                actual_value=extracted_value,
                                additional_context={'xml_path': mapping.xml_path}
                            ))
                            check_result.warnings_found += 1
                        
                        break  # Only check first record for each mapping
                        
            except Exception as e:
                self.logger.debug(f"Field-level validation failed for {mapping.xml_path}: {e}")
                continue
    
    def _collect_primary_keys(
        self,
        extracted_tables: Dict[str, List[Dict[str, Any]]],
        table_name: str,
        key_field: str
    ) -> Set[Any]:
        """Collect all primary key values from a table."""
        keys = set()
        if table_name in extracted_tables:
            for record in extracted_tables[table_name]:
                key_value = record.get(key_field)
                if key_value is not None:
                    keys.add(key_value)
        return keys
    
    def _validate_foreign_key_references(
        self,
        records: List[Dict[str, Any]],
        fk_field: str,
        valid_keys: Set[Any],
        child_table: str,
        parent_table: str,
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate foreign key references."""
        for record_index, record in enumerate(records):
            fk_value = record.get(fk_field)
            if fk_value is not None and fk_value not in valid_keys:
                result.add_error(ValidationError(
                    error_type=ValidationType.REFERENTIAL_INTEGRITY,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid foreign key reference: {fk_field}={fk_value} not found in {parent_table}",
                    table_name=child_table,
                    record_index=record_index,
                    field_name=fk_field,
                    actual_value=fk_value,
                    additional_context={'parent_table': parent_table, 'valid_keys_count': len(valid_keys)}
                ))
                check_result.errors_found += 1
                check_result.passed = False
    
    def _validate_required_fields(
        self,
        record: Dict[str, Any],
        table_name: str,
        record_index: int,
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate required fields (NOT NULL constraints)."""
        required_fields = self._get_required_fields_for_table(table_name)
        
        for field_name in required_fields:
            field_value = record.get(field_name)
            if field_value is None or field_value == '':
                result.add_error(ValidationError(
                    error_type=ValidationType.CONSTRAINT_COMPLIANCE,
                    severity=ValidationSeverity.ERROR,
                    message=f"Required field '{field_name}' is null or empty",
                    table_name=table_name,
                    record_index=record_index,
                    field_name=field_name,
                    actual_value=field_value
                ))
                check_result.errors_found += 1
                check_result.passed = False
    
    def _validate_data_type_constraints(
        self,
        record: Dict[str, Any],
        table_name: str,
        record_index: int,
        mapping_contract: MappingContract,
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate data type constraints."""
        for field_name, field_value in record.items():
            if field_value is not None:
                expected_type = self._get_expected_type_for_field(field_name, mapping_contract)
                if expected_type and not self._is_value_of_expected_type(field_value, expected_type):
                    result.add_error(ValidationError(
                        error_type=ValidationType.CONSTRAINT_COMPLIANCE,
                        severity=ValidationSeverity.WARNING,
                        message=f"Data type mismatch: expected {expected_type}, got {type(field_value).__name__}",
                        table_name=table_name,
                        record_index=record_index,
                        field_name=field_name,
                        expected_value=expected_type,
                        actual_value=type(field_value).__name__
                    ))
                    check_result.warnings_found += 1
    
    def _validate_field_length_constraints(
        self,
        record: Dict[str, Any],
        table_name: str,
        record_index: int,
        mapping_contract: MappingContract,
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate field length constraints."""
        for field_name, field_value in record.items():
            if isinstance(field_value, str):
                max_length = self._get_max_length_for_field(field_name, mapping_contract)
                if max_length and len(field_value) > max_length:
                    result.add_error(ValidationError(
                        error_type=ValidationType.CONSTRAINT_COMPLIANCE,
                        severity=ValidationSeverity.ERROR,
                        message=f"Field length exceeds maximum: {len(field_value)} > {max_length}",
                        table_name=table_name,
                        record_index=record_index,
                        field_name=field_name,
                        expected_value=max_length,
                        actual_value=len(field_value)
                    ))
                    check_result.errors_found += 1
                    check_result.passed = False
    
    def _validate_business_rule_constraints(
        self,
        record: Dict[str, Any],
        table_name: str,
        record_index: int,
        result: ValidationResult,
        check_result: IntegrityCheckResult
    ) -> None:
        """Validate business rule constraints."""
        # Validate SSN format if present
        if 'ssn' in record and record['ssn']:
            if not self._is_valid_ssn(record['ssn']):
                result.add_error(ValidationError(
                    error_type=ValidationType.CONSTRAINT_COMPLIANCE,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid SSN format: {record['ssn']}",
                    table_name=table_name,
                    record_index=record_index,
                    field_name='ssn',
                    actual_value=record['ssn']
                ))
                check_result.errors_found += 1
                check_result.passed = False
        
        # Validate date ranges
        if 'birth_date' in record and record['birth_date']:
            if not self._is_valid_birth_date(record['birth_date']):
                result.add_error(ValidationError(
                    error_type=ValidationType.CONSTRAINT_COMPLIANCE,
                    severity=ValidationSeverity.WARNING,
                    message=f"Suspicious birth date: {record['birth_date']}",
                    table_name=table_name,
                    record_index=record_index,
                    field_name='birth_date',
                    actual_value=record['birth_date']
                ))
                check_result.warnings_found += 1
    
    # Helper methods
    def _extract_value_from_xml_path(self, xml_data: Dict[str, Any], xml_path: str, xml_attribute: Optional[str] = None) -> Any:
        """Extract value from XML data using XPath-like navigation."""
        try:
            current_data = xml_data
            path_parts = xml_path.strip('/').split('/')
            
            for part in path_parts:
                if isinstance(current_data, dict) and part in current_data:
                    current_data = current_data[part]
                elif isinstance(current_data, list) and len(current_data) > 0:
                    for item in current_data:
                        if isinstance(item, dict) and part in item:
                            current_data = item[part]
                            break
                    else:
                        return None
                else:
                    return None
            
            if xml_attribute and isinstance(current_data, dict):
                return current_data.get(xml_attribute)
            
            return current_data
        except Exception:
            return None
    
    def _values_are_equivalent(self, source_value: Any, extracted_value: Any, data_type: str) -> bool:
        """Check if source and extracted values are equivalent considering data type conversions."""
        if source_value is None and extracted_value is None:
            return True
        if source_value is None or extracted_value is None:
            return False
        
        try:
            # Convert both values to strings for comparison
            source_str = str(source_value).strip()
            extracted_str = str(extracted_value).strip()
            
            # Handle numeric comparisons
            if data_type in ['int', 'smallint', 'bigint', 'tinyint']:
                return int(float(source_str)) == int(float(extracted_str))
            elif data_type.startswith('decimal') or data_type == 'float':
                return abs(float(source_str) - float(extracted_str)) < 0.01
            elif data_type == 'bit':
                return self._normalize_bit_value(source_str) == self._normalize_bit_value(extracted_str)
            else:
                return source_str.lower() == extracted_str.lower()
        except (ValueError, TypeError):
            return str(source_value) == str(extracted_value)
    
    def _normalize_bit_value(self, value: str) -> int:
        """Normalize a value to bit representation (0 or 1)."""
        value_upper = value.upper()
        if value_upper in ['1', 'TRUE', 'YES', 'Y', 'ON']:
            return 1
        else:
            return 0
    
    def _is_field_value_valid(self, field_value: Any, field_name: str) -> bool:
        """Check if a field value is valid (basic validation)."""
        if field_value is None:
            return False
        
        # Check for obviously invalid values
        str_value = str(field_value).strip()
        if not str_value:
            return False
        
        # Field-specific validation
        if 'email' in field_name.lower():
            return '@' in str_value and '.' in str_value
        elif 'phone' in field_name.lower():
            return len(str_value.replace('-', '').replace('(', '').replace(')', '').replace(' ', '')) >= 10
        elif field_name == 'ssn':
            return self._is_valid_ssn(str_value)
        
        return True
    
    def _get_required_fields_for_table(self, table_name: str) -> List[str]:
        """Get list of required fields for a table."""
        required_fields_map = {
            'app_base': ['app_id'],
            'app_contact_base': ['con_id', 'app_id'],
            'app_contact_address': ['con_id', 'app_id'],
            'app_contact_employment': ['con_id', 'app_id'],
            'app_operational_cc': ['app_id']
        }
        return required_fields_map.get(table_name, [])
    
    def _get_expected_type_for_field(self, field_name: str, mapping_contract: MappingContract) -> Optional[str]:
        """Get expected data type for a field from mapping contract."""
        for mapping in mapping_contract.mappings:
            if mapping.target_column == field_name:
                return mapping.data_type
        return None
    
    def _get_max_length_for_field(self, field_name: str, mapping_contract: MappingContract) -> Optional[int]:
        """Get maximum length for a field from mapping contract."""
        for mapping in mapping_contract.mappings:
            if mapping.target_column == field_name and mapping.data_type:
                if 'varchar(' in mapping.data_type or 'char(' in mapping.data_type:
                    try:
                        length_str = mapping.data_type.split('(')[1].split(')')[0]
                        return int(length_str)
                    except (IndexError, ValueError):
                        pass
        return None
    
    def _is_value_of_expected_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected data type."""
        if expected_type in ['int', 'smallint', 'bigint', 'tinyint']:
            return isinstance(value, int) or (isinstance(value, str) and value.isdigit())
        elif expected_type.startswith('decimal') or expected_type == 'float':
            return isinstance(value, (int, float)) or (isinstance(value, str) and self._is_numeric(value))
        elif expected_type == 'bit':
            return isinstance(value, (int, bool)) or value in [0, 1, '0', '1', 'True', 'False']
        elif expected_type in ['varchar', 'char', 'nvarchar', 'nchar']:
            return isinstance(value, str)
        elif expected_type in ['datetime', 'smalldatetime', 'date']:
            return isinstance(value, datetime) or self._is_date_string(value)
        return True
    
    def _is_numeric(self, value: str) -> bool:
        """Check if string represents a numeric value."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    def _is_date_string(self, value: Any) -> bool:
        """Check if value represents a date string."""
        if not isinstance(value, str):
            return False
        
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{2}/\d{2}/\d{4}',
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
        ]
        
        import re
        for pattern in date_patterns:
            if re.match(pattern, value.strip()):
                return True
        return False
    
    def _is_valid_ssn(self, ssn: str) -> bool:
        """Validate SSN format."""
        if not ssn or len(ssn) != 9:
            return False
        if not ssn.isdigit():
            return False
        # Check for invalid patterns
        invalid_ssns = ['000000000', '111111111', '222222222', '333333333', '444444444',
                       '555555555', '666666666', '777777777', '888888888', '999999999']
        return ssn not in invalid_ssns
    
    def _is_valid_birth_date(self, birth_date: Any) -> bool:
        """Validate birth date is reasonable."""
        try:
            if isinstance(birth_date, datetime):
                date_obj = birth_date
            else:
                # Try to parse string date
                date_obj = datetime.strptime(str(birth_date)[:10], '%Y-%m-%d')
            
            # Check if date is between 1900 and current year - 18
            current_year = datetime.now().year
            return 1900 <= date_obj.year <= (current_year - 18)
        except (ValueError, TypeError):
            return False