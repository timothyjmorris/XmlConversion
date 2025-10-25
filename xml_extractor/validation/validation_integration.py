"""
Validation Integration and Orchestration Layer

This module provides the integration layer that connects validation components with the
main XML extraction pipeline. It orchestrates validation workflows, manages result aggregation,
and provides reporting capabilities for comprehensive data quality assessment.

Key Responsibilities:
- Orchestrates multi-stage validation workflows across the extraction pipeline
- Provides integration points with DataMapper, XMLParser, and MigrationEngine
- Manages validation result aggregation and reporting
- Supports both individual record and batch validation scenarios
- Enables configurable validation strategies based on processing requirements

Integration Architecture:
- ValidationOrchestrator: Coordinates validation execution and result management
- ValidationReporter: Generates detailed reports in multiple formats
- Connects with DataIntegrityValidator for core validation logic
- Integrates with PreProcessingValidator for early quality gates
- Provides hooks for custom validation extensions and reporting

The integration layer ensures validation is seamlessly woven into the extraction workflow,
providing comprehensive quality assurance without disrupting the processing pipeline.
"""

import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from ..interfaces import DataMapperInterface, XMLParserInterface
from ..models import MappingContract, ProcessingResult
from .data_integrity_validator import DataIntegrityValidator
from .validation_models import ValidationResult, ValidationConfig, ValidationError, ValidationSeverity


class ValidationOrchestrator:
    """
    Central coordinator for validation processes across the XML extraction pipeline.

    This orchestrator manages the execution of validation workflows, coordinates between
    different validation components, and provides unified result aggregation and reporting.
    It serves as the main integration point between validation logic and the extraction pipeline.

    Orchestration Responsibilities:
    - Coordinates pre-processing validation (structure, business rules)
    - Executes comprehensive data integrity validation post-extraction
    - Manages batch validation scenarios with result aggregation
    - Provides progress tracking and performance monitoring
    - Generates unified validation reports across multiple records

    Validation Workflow:
    1. Pre-Processing: Validates XML structure and business rules before extraction
    2. Post-Extraction: Validates data integrity, referential integrity, and constraints
    3. Result Aggregation: Combines results from multiple validation stages
    4. Report Generation: Creates comprehensive reports in multiple formats
    5. History Management: Tracks validation results over time for trend analysis

    Integration Points:
    - DataMapper: Receives extracted tables for integrity validation
    - XMLParser: Receives source XML data for end-to-end validation
    - MigrationEngine: Can validate data before/after database insertion
    - CLI Tools: Provides validation status and detailed error reporting
    - Batch Processors: Supports high-throughput validation scenarios

    Configuration Options:
    - Enables/disables specific validation types based on processing requirements
    - Configures error thresholds and reporting preferences
    - Supports custom validation extensions and result handlers
    - Provides performance tuning options for large-scale processing
    """
    
    def __init__(self, 
                 validator: Optional[DataIntegrityValidator] = None,
                 config: Optional[ValidationConfig] = None):
        """Initialize the validation orchestrator."""
        self.logger = logging.getLogger(__name__)
        self.validator = validator or DataIntegrityValidator(config)
        self.config = config or ValidationConfig()
        self._validation_history = []
        
    def validate_complete_extraction(self,
                                   source_xml_data: Dict[str, Any],
                                   extracted_tables: Dict[str, List[Dict[str, Any]]],
                                   mapping_contract: MappingContract,
                                   source_record_id: Optional[str] = None) -> ValidationResult:
        """
        Perform complete validation of an extraction operation.
        
        Args:
            source_xml_data: Original parsed XML data
            extracted_tables: Extracted relational data
            mapping_contract: Mapping contract used
            source_record_id: Optional source record identifier
            
        Returns:
            Comprehensive validation results
        """
        self.logger.info(f"Starting complete extraction validation for record {source_record_id}")
        
        try:
            # Perform comprehensive validation
            validation_result = self.validator.validate_extraction_results(
                source_xml_data=source_xml_data,
                extracted_tables=extracted_tables,
                mapping_contract=mapping_contract,
                source_record_id=source_record_id
            )
            
            # Store validation history
            self._validation_history.append(validation_result)
            
            # Log validation summary
            self._log_validation_summary(validation_result)
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"Validation orchestration failed: {e}")
            # Create error validation result
            error_result = ValidationResult(
                validation_id=f"error_{datetime.now().isoformat()}",
                timestamp=datetime.now(),
                source_record_id=source_record_id,
                validation_passed=False
            )
            error_result.add_error(ValidationError(
                error_type=ValidationSeverity.CRITICAL,
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation orchestration failed: {e}"
            ))
            return error_result
    
    def validate_batch_extraction(self,
                                batch_results: List[Dict[str, Any]],
                                mapping_contract: MappingContract) -> Dict[str, Any]:
        """
        Validate a batch of extraction results.
        
        Args:
            batch_results: List of extraction results to validate
            mapping_contract: Mapping contract used for extraction
            
        Returns:
            Batch validation summary
        """
        self.logger.info(f"Starting batch validation for {len(batch_results)} records")
        
        batch_summary = {
            'total_records': len(batch_results),
            'validation_results': [],
            'overall_passed': True,
            'total_errors': 0,
            'total_warnings': 0,
            'critical_failures': 0,
            'execution_time_ms': 0
        }
        
        start_time = datetime.now()
        
        try:
            for i, result in enumerate(batch_results):
                if 'source_xml_data' in result and 'extracted_tables' in result:
                    validation_result = self.validate_complete_extraction(
                        source_xml_data=result['source_xml_data'],
                        extracted_tables=result['extracted_tables'],
                        mapping_contract=mapping_contract,
                        source_record_id=result.get('source_record_id', f"batch_record_{i}")
                    )
                    
                    batch_summary['validation_results'].append(validation_result)
                    batch_summary['total_errors'] += validation_result.total_errors
                    batch_summary['total_warnings'] += validation_result.total_warnings
                    
                    if validation_result.has_critical_errors:
                        batch_summary['critical_failures'] += 1
                        batch_summary['overall_passed'] = False
                    elif not validation_result.validation_passed:
                        batch_summary['overall_passed'] = False
            
            # Calculate execution time
            end_time = datetime.now()
            batch_summary['execution_time_ms'] = (end_time - start_time).total_seconds() * 1000
            
            self.logger.info(
                f"Batch validation completed: {batch_summary['total_records']} records, "
                f"{'PASSED' if batch_summary['overall_passed'] else 'FAILED'}, "
                f"{batch_summary['total_errors']} errors, {batch_summary['total_warnings']} warnings"
            )
            
        except Exception as e:
            self.logger.error(f"Batch validation failed: {e}")
            batch_summary['overall_passed'] = False
            batch_summary['error'] = str(e)
        
        return batch_summary
    
    def generate_validation_report(self, 
                                 validation_results: List[ValidationResult],
                                 include_details: bool = True) -> str:
        """
        Generate a comprehensive validation report.
        
        Args:
            validation_results: List of validation results to include
            include_details: Whether to include detailed error information
            
        Returns:
            Formatted validation report
        """
        if not validation_results:
            return "No validation results to report."
        
        report_lines = [
            "=" * 80,
            "DATA INTEGRITY VALIDATION REPORT",
            "=" * 80,
            f"Generated: {datetime.now().isoformat()}",
            f"Total Validations: {len(validation_results)}",
            ""
        ]
        
        # Summary statistics
        total_records = sum(vr.total_records_validated for vr in validation_results)
        total_errors = sum(vr.total_errors for vr in validation_results)
        total_warnings = sum(vr.total_warnings for vr in validation_results)
        passed_validations = sum(1 for vr in validation_results if vr.validation_passed)
        critical_failures = sum(1 for vr in validation_results if vr.has_critical_errors)
        
        report_lines.extend([
            "SUMMARY STATISTICS",
            "-" * 40,
            f"Total Records Validated: {total_records:,}",
            f"Validations Passed: {passed_validations}/{len(validation_results)} ({passed_validations/len(validation_results)*100:.1f}%)",
            f"Critical Failures: {critical_failures}",
            f"Total Errors: {total_errors:,}",
            f"Total Warnings: {total_warnings:,}",
            ""
        ])
        
        # Data quality metrics (if available)
        if validation_results and validation_results[0].data_quality_metrics:
            avg_completeness = sum(vr.data_quality_metrics.get('completeness_percentage', 0) 
                                 for vr in validation_results) / len(validation_results)
            avg_validity = sum(vr.data_quality_metrics.get('validity_percentage', 0) 
                             for vr in validation_results) / len(validation_results)
            avg_accuracy = sum(vr.data_quality_metrics.get('accuracy_percentage', 0) 
                             for vr in validation_results) / len(validation_results)
            
            report_lines.extend([
                "DATA QUALITY METRICS",
                "-" * 40,
                f"Average Completeness: {avg_completeness:.2f}%",
                f"Average Validity: {avg_validity:.2f}%",
                f"Average Accuracy: {avg_accuracy:.2f}%",
                ""
            ])
        
        # Error analysis
        all_errors = []
        for vr in validation_results:
            all_errors.extend(vr.errors)
        
        if all_errors:
            # Group errors by type
            error_by_type = {}
            for error in all_errors:
                error_type = error.error_type.value
                if error_type not in error_by_type:
                    error_by_type[error_type] = []
                error_by_type[error_type].append(error)
            
            report_lines.extend([
                "ERROR ANALYSIS",
                "-" * 40
            ])
            
            for error_type, errors in error_by_type.items():
                critical_count = sum(1 for e in errors if e.severity == ValidationSeverity.CRITICAL)
                error_count = sum(1 for e in errors if e.severity == ValidationSeverity.ERROR)
                warning_count = sum(1 for e in errors if e.severity == ValidationSeverity.WARNING)
                
                report_lines.append(
                    f"{error_type.upper()}: {len(errors)} total "
                    f"(Critical: {critical_count}, Errors: {error_count}, Warnings: {warning_count})"
                )
            
            report_lines.append("")
        
        # Individual validation results (if details requested)
        if include_details and len(validation_results) <= 10:  # Limit details for large reports
            report_lines.extend([
                "INDIVIDUAL VALIDATION RESULTS",
                "-" * 40
            ])
            
            for i, vr in enumerate(validation_results[:10]):
                status = "PASSED" if vr.validation_passed else "FAILED"
                report_lines.extend([
                    f"Validation {i+1}: {status}",
                    f"  ID: {vr.validation_id}",
                    f"  Source Record: {vr.source_record_id or 'N/A'}",
                    f"  Records: {vr.total_records_validated}",
                    f"  Errors: {vr.total_errors}, Warnings: {vr.total_warnings}",
                    f"  Execution Time: {vr.execution_time_ms:.2f}ms",
                    ""
                ])
                
                # Show top errors for failed validations
                if not vr.validation_passed and vr.errors:
                    report_lines.append("  Top Errors:")
                    for error in vr.errors[:3]:
                        report_lines.append(f"    - {error}")
                    if len(vr.errors) > 3:
                        report_lines.append(f"    ... and {len(vr.errors) - 3} more errors")
                    report_lines.append("")
        
        report_lines.extend([
            "=" * 80,
            "END OF REPORT",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get statistics about validation operations."""
        if not self._validation_history:
            return {'message': 'No validation history available'}
        
        total_validations = len(self._validation_history)
        passed_validations = sum(1 for vr in self._validation_history if vr.validation_passed)
        total_records = sum(vr.total_records_validated for vr in self._validation_history)
        total_errors = sum(vr.total_errors for vr in self._validation_history)
        total_warnings = sum(vr.total_warnings for vr in self._validation_history)
        
        avg_execution_time = sum(vr.execution_time_ms for vr in self._validation_history) / total_validations
        
        return {
            'total_validations': total_validations,
            'passed_validations': passed_validations,
            'success_rate': (passed_validations / total_validations * 100) if total_validations > 0 else 0,
            'total_records_validated': total_records,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'average_execution_time_ms': avg_execution_time,
            'error_rate': (total_errors / total_records * 100) if total_records > 0 else 0
        }
    
    def clear_validation_history(self) -> None:
        """Clear validation history."""
        self._validation_history.clear()
        self.logger.info("Validation history cleared")
    
    def _log_validation_summary(self, validation_result: ValidationResult) -> None:
        """Log a summary of validation results."""
        status = "PASSED" if validation_result.validation_passed else "FAILED"
        self.logger.info(
            f"Validation {validation_result.validation_id} {status}: "
            f"{validation_result.total_records_validated} records, "
            f"{validation_result.total_errors} errors, "
            f"{validation_result.total_warnings} warnings, "
            f"{validation_result.execution_time_ms:.2f}ms"
        )
        
        # Log critical errors
        if validation_result.has_critical_errors:
            self.logger.error(f"Critical validation failures found:")
            for error in validation_result.critical_errors[:5]:  # Log first 5 critical errors
                self.logger.error(f"  - {error}")


class ValidationReporter:
    """
    Generates detailed validation reports and metrics.
    
    Provides various reporting formats and analysis capabilities
    for validation results.
    """
    
    def __init__(self):
        """Initialize the validation reporter."""
        self.logger = logging.getLogger(__name__)
    
    def generate_csv_report(self, validation_results: List[ValidationResult]) -> str:
        """Generate CSV format validation report."""
        if not validation_results:
            return "validation_id,timestamp,source_record_id,records_validated,errors,warnings,passed,execution_time_ms\n"
        
        csv_lines = ["validation_id,timestamp,source_record_id,records_validated,errors,warnings,passed,execution_time_ms"]
        
        for vr in validation_results:
            csv_lines.append(
                f"{vr.validation_id},{vr.timestamp.isoformat()},{vr.source_record_id or ''},"
                f"{vr.total_records_validated},{vr.total_errors},{vr.total_warnings},"
                f"{vr.validation_passed},{vr.execution_time_ms:.2f}"
            )
        
        return "\n".join(csv_lines)
    
    def generate_json_report(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Generate JSON format validation report."""
        return {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_validations': len(validation_results),
                'report_version': '1.0'
            },
            'summary': self._calculate_summary_stats(validation_results),
            'validations': [self._serialize_validation_result(vr) for vr in validation_results]
        }
    
    def _calculate_summary_stats(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """Calculate summary statistics for validation results."""
        if not validation_results:
            return {}
        
        total_records = sum(vr.total_records_validated for vr in validation_results)
        total_errors = sum(vr.total_errors for vr in validation_results)
        total_warnings = sum(vr.total_warnings for vr in validation_results)
        passed_count = sum(1 for vr in validation_results if vr.validation_passed)
        
        return {
            'total_validations': len(validation_results),
            'total_records_validated': total_records,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'validations_passed': passed_count,
            'success_rate_percentage': (passed_count / len(validation_results) * 100) if validation_results else 0,
            'error_rate_percentage': (total_errors / total_records * 100) if total_records > 0 else 0
        }
    
    def _serialize_validation_result(self, validation_result: ValidationResult) -> Dict[str, Any]:
        """Serialize a validation result to dictionary format."""
        return {
            'validation_id': validation_result.validation_id,
            'timestamp': validation_result.timestamp.isoformat(),
            'source_record_id': validation_result.source_record_id,
            'total_records_validated': validation_result.total_records_validated,
            'total_errors': validation_result.total_errors,
            'total_warnings': validation_result.total_warnings,
            'validation_passed': validation_result.validation_passed,
            'execution_time_ms': validation_result.execution_time_ms,
            'data_quality_metrics': validation_result.data_quality_metrics,
            'integrity_checks': [
                {
                    'check_name': check.check_name,
                    'passed': check.passed,
                    'errors_found': check.errors_found,
                    'warnings_found': check.warnings_found,
                    'records_checked': check.records_checked,
                    'execution_time_ms': check.execution_time_ms
                }
                for check in validation_result.integrity_checks
            ],
            'error_summary': {
                'critical_errors': len(validation_result.get_errors_by_severity(ValidationSeverity.CRITICAL)),
                'errors': len(validation_result.get_errors_by_severity(ValidationSeverity.ERROR)),
                'warnings': len(validation_result.get_errors_by_severity(ValidationSeverity.WARNING))
            }
        }