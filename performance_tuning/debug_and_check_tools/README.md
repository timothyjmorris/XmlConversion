# Debug and Check Tools

One-time diagnostic scripts for troubleshooting, validation, and data inspection. These tools are used for specific debugging scenarios and are not part of the regular performance testing workflow.

## Organization

### Check Scripts (Database State)
Scripts that inspect database state and report findings:
- `check_app_base_status.py` - Verify app_base table status and record count
- `check_mock_xml_status.py` - Check mock XML data status
- `check_processing_log.py` - Inspect processing_log table
- `check_processing_log_fk.py` - Verify foreign key relationships in processing_log
- `check_processing_log_schema.py` - Inspect processing_log table schema
- `check_processing_log_status.py` - Check processing_log status and record count
- `check_xml_range.py` - Check XML record range and distribution

### Clear Scripts (Database Cleanup)
Scripts for cleaning up test data:
- `clear_processing_log.py` - Clear processing_log table

### Debug Scripts (Investigation)
Scripts for detailed debugging and investigation:
- `debug_extraction_query.py` - Debug XML extraction queries
- `debug_mock_insert.py` - Debug mock data insertion

### Test Scripts (Validation)
Scripts for step-by-step testing and validation:
- `test_conditions_step_by_step.py` - Test conditions in detail
- `test_exact_query.py` - Test exact query results
- `test_extraction_query.py` - Test extraction query
- `test_mock_xml_generation.py` - Test mock XML generation
- `test_mock_xml_insert.py` - Test mock XML insertion
- `test_offset_difference.py` - Test offset differences
- `test_production_processor_output.py` - Test production_processor output
- `test_simple_queries.py` - Test simple database queries

### Diagnostic Scripts (Analysis)
Scripts for analysis and diagnostics:
- `diagnostic_population_assignment_enum.py` - Diagnose population assignment enum

## When to Use

**Troubleshooting specific issue:**
1. Identify the problem area (data loading, extraction, insertion, etc.)
2. Pick relevant check/test script
3. Run to understand the issue
4. Clean up with clear_* scripts if needed

**Validating data integrity:**
- Use check_* scripts to verify database state
- Use test_extraction_query.py to validate extraction logic
- Use test_mock_xml_* scripts to validate data generation

**Debugging production processor:**
- Use test_production_processor_output.py
- Use debug_extraction_query.py if extraction issues
- Use diagnostic_* scripts for specific component issues

## Usage Pattern

```bash
# 1. Check current state
python check_app_base_status.py
python check_processing_log_status.py

# 2. Run test/debug script
python test_exact_query.py

# 3. Clean up if needed
python clear_processing_log.py

# 4. Verify state again
python check_processing_log_status.py
```

## Notes

- These scripts are NOT part of regular performance testing
- Use only when troubleshooting specific issues
- Most are one-time use scripts for investigation
- See `../test_modules/` for regular performance testing
- See `../benchmarks/` for performance measurement

## Integration with Regular Workflow

Regular workflow uses:
- `../test_modules/establish_baseline.py` - Baseline measurement
- `../test_modules/batch_size_optimizer.py` - Batch size optimization
- `../test_modules/debug_connection_string.py` - Configuration verification

Debug scripts (here) are called only when troubleshooting issues with the above.

## Archiving/Cleanup

Some of these scripts are one-time use. Safe to delete after:
- Issue is resolved
- Data is validated
- Troubleshooting is complete

Keep scripts that are useful for your environment's regular maintenance:
- `check_*` scripts for periodic data inspection
- `clear_*` scripts for test data cleanup
