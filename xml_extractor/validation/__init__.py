"""
Data integrity validation system for XML Database Extraction.

This module provides comprehensive validation capabilities including:
- End-to-end validation comparing source XML with extracted relational data
- Referential integrity checking for foreign key relationships
- Constraint compliance validation for target tables
- Data quality reporting with detailed error information
"""

from .data_integrity_validator import DataIntegrityValidator
from .validation_models import (
    ValidationResult, ValidationError, IntegrityCheckResult, 
    ValidationConfig, ValidationSeverity, ValidationType
)
from .validation_integration import ValidationOrchestrator, ValidationReporter
__all__ = [
    'DataIntegrityValidator',
    'ValidationResult', 
    'ValidationError',
    'IntegrityCheckResult',
    'ValidationConfig',
    'ValidationSeverity',
    'ValidationType',
    'ValidationOrchestrator',
    'ValidationReporter'
]