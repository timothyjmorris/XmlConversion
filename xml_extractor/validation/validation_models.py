"""
Data models for the validation system.

This module defines the data structures used for validation results,
error reporting, and integrity checking.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationType(Enum):
    """Types of validation checks."""
    DATA_INTEGRITY = "data_integrity"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    CONSTRAINT_COMPLIANCE = "constraint_compliance"
    DATA_QUALITY = "data_quality"
    END_TO_END = "end_to_end"


@dataclass
class ValidationError:
    """
    Represents a validation error or issue.
    
    Attributes:
        error_type: Type of validation that failed
        severity: Severity level of the error
        message: Human-readable error message
        table_name: Name of the table where error occurred
        record_index: Index of the record with the error
        field_name: Name of the field with the error
        expected_value: Expected value (if applicable)
        actual_value: Actual value that caused the error
        source_record_id: Identifier from source XML
        additional_context: Additional context information
    """
    error_type: ValidationType
    severity: ValidationSeverity
    message: str
    table_name: Optional[str] = None
    record_index: Optional[int] = None
    field_name: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    source_record_id: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        """String representation of the validation error."""
        location = ""
        if self.table_name:
            location = f" in {self.table_name}"
            if self.record_index is not None:
                location += f"[{self.record_index}]"
            if self.field_name:
                location += f".{self.field_name}"
        
        return f"[{self.severity.value.upper()}] {self.error_type.value}{location}: {self.message}"


@dataclass
class IntegrityCheckResult:
    """
    Results from a specific integrity check.
    
    Attributes:
        check_name: Name of the integrity check
        passed: Whether the check passed
        errors_found: Number of errors found
        warnings_found: Number of warnings found
        records_checked: Number of records checked
        execution_time_ms: Time taken to execute the check
        details: Additional details about the check
    """
    check_name: str
    passed: bool
    errors_found: int = 0
    warnings_found: int = 0
    records_checked: int = 0
    execution_time_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """
    Complete validation results for a data extraction operation.
    
    Attributes:
        validation_id: Unique identifier for this validation run
        timestamp: When the validation was performed
        source_record_id: Identifier from source XML
        total_records_validated: Total number of records validated
        total_errors: Total number of errors found
        total_warnings: Total number of warnings found
        validation_passed: Overall validation status
        execution_time_ms: Total validation execution time
        errors: List of validation errors
        integrity_checks: Results from individual integrity checks
        data_quality_metrics: Data quality metrics
        summary: Summary of validation results
    """
    validation_id: str
    timestamp: datetime
    source_record_id: Optional[str] = None
    total_records_validated: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    validation_passed: bool = False
    execution_time_ms: float = 0.0
    errors: List[ValidationError] = field(default_factory=list)
    integrity_checks: List[IntegrityCheckResult] = field(default_factory=list)
    data_quality_metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    
    def add_error(self, error: ValidationError) -> None:
        """Add a validation error to the results."""
        self.errors.append(error)
        if error.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]:
            self.total_errors += 1
        elif error.severity == ValidationSeverity.WARNING:
            self.total_warnings += 1
    
    def add_integrity_check(self, check_result: IntegrityCheckResult) -> None:
        """Add an integrity check result."""
        self.integrity_checks.append(check_result)
        self.total_errors += check_result.errors_found
        self.total_warnings += check_result.warnings_found
    
    def get_errors_by_severity(self, severity: ValidationSeverity) -> List[ValidationError]:
        """Get errors filtered by severity level."""
        return [error for error in self.errors if error.severity == severity]
    
    def get_errors_by_type(self, error_type: ValidationType) -> List[ValidationError]:
        """Get errors filtered by validation type."""
        return [error for error in self.errors if error.error_type == error_type]
    
    def get_errors_by_table(self, table_name: str) -> List[ValidationError]:
        """Get errors filtered by table name."""
        return [error for error in self.errors if error.table_name == table_name]
    
    @property
    def critical_errors(self) -> List[ValidationError]:
        """Get all critical errors."""
        return self.get_errors_by_severity(ValidationSeverity.CRITICAL)
    
    @property
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return len(self.critical_errors) > 0
    
    def generate_summary(self) -> str:
        """Generate a summary of validation results."""
        summary_lines = [
            f"Validation Summary (ID: {self.validation_id})",
            f"Timestamp: {self.timestamp}",
            f"Records Validated: {self.total_records_validated}",
            f"Total Errors: {self.total_errors}",
            f"Total Warnings: {self.total_warnings}",
            f"Validation Passed: {'Yes' if self.validation_passed else 'No'}",
            f"Execution Time: {self.execution_time_ms:.2f}ms",
            ""
        ]
        
        if self.integrity_checks:
            summary_lines.append("Integrity Checks:")
            for check in self.integrity_checks:
                status = "PASSED" if check.passed else "FAILED"
                summary_lines.append(f"  - {check.check_name}: {status} ({check.errors_found} errors, {check.warnings_found} warnings)")
            summary_lines.append("")
        
        if self.data_quality_metrics:
            summary_lines.append("Data Quality Metrics:")
            for metric, value in self.data_quality_metrics.items():
                if isinstance(value, float):
                    summary_lines.append(f"  - {metric}: {value:.2f}%")
                else:
                    summary_lines.append(f"  - {metric}: {value}")
            summary_lines.append("")
        
        if self.errors:
            summary_lines.append(f"Top Errors ({min(5, len(self.errors))}):")
            for error in self.errors[:5]:
                summary_lines.append(f"  - {error}")
            if len(self.errors) > 5:
                summary_lines.append(f"  ... and {len(self.errors) - 5} more errors")
        
        self.summary = "\n".join(summary_lines)
        return self.summary


@dataclass
class ValidationConfig:
    """
    Configuration for validation operations.
    
    Attributes:
        enable_end_to_end_validation: Enable comparison of source XML with extracted data
        enable_referential_integrity: Enable foreign key relationship validation
        enable_constraint_compliance: Enable database constraint validation
        enable_data_quality_checks: Enable data quality metrics calculation
        max_errors_per_check: Maximum errors to collect per validation check
        validation_timeout_ms: Timeout for validation operations
        strict_mode: Whether to fail validation on any error
        generate_detailed_report: Whether to generate detailed validation reports
    """
    enable_end_to_end_validation: bool = True
    enable_referential_integrity: bool = True
    enable_constraint_compliance: bool = True
    enable_data_quality_checks: bool = True
    max_errors_per_check: int = 100
    validation_timeout_ms: int = 30000
    strict_mode: bool = False
    generate_detailed_report: bool = True