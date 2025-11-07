"""
Data Integrity Validation System for XML Database Extraction

STRUCTURE:
- Deployed modules: ElementFilter, PreProcessingValidator (active in production)
- Shared models: ValidationModels (used by deployed + future modules)
- Future enhancement: DataIntegrityValidator, ValidationOrchestrator, ValidationReporter (in future/ subfolder)

DEPLOYED MODULES (Production):
- ElementFilter: Filters XML elements per business rules (active in DataMapper)
- PreProcessingValidator: Validates XML before extraction (active in batch processors)

FUTURE MODULES (Not yet deployed):
See xml_extractor/validation/future/ subfolder for:
- DataIntegrityValidator: Comprehensive post-extraction validation
- ValidationOrchestrator: Validates and orchestrates workflows
- ValidationReporter: Generates validation reports

See VALIDATION_MODULE_ANALYSIS.md and POST_EXTRACTION_VALIDATION_COST_BENEFIT.md
for deployment status and decision framework.

NOTE: Modules are imported directly from their source to avoid circular imports.
Import from specific modules, not from this __init__.py.
"""

# Shared validation data structures (safe to import here)
from .validation_models import (
    ValidationResult, ValidationError, IntegrityCheckResult, 
    ValidationConfig, ValidationSeverity, ValidationType
)

__all__ = [
    # Shared models
    'ValidationResult', 
    'ValidationError',
    'IntegrityCheckResult',
    'ValidationConfig',
    'ValidationSeverity',
    'ValidationType',
]

