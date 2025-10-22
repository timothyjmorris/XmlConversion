# Schema Configuration Guide

## Overview

The XML Database Extraction system now supports configurable database schema prefixes, allowing you to easily switch between different environments (production, sandbox, test) without modifying code or mapping contracts.

## Configuration Methods

### Method 1: Environment Variable (Recommended)

Set the schema prefix using an environment variable:

```bash
# Windows Command Prompt
set XML_EXTRACTOR_DB_SCHEMA_PREFIX=sandbox

# Windows PowerShell
$env:XML_EXTRACTOR_DB_SCHEMA_PREFIX = "sandbox"

# Linux/Mac
export XML_EXTRACTOR_DB_SCHEMA_PREFIX=sandbox
```

### Method 2: Programmatic Configuration

```python
import os
os.environ['XML_EXTRACTOR_DB_SCHEMA_PREFIX'] = 'sandbox'

# Then use your normal processing code
from xml_extractor.processing.parallel_coordinator import ParallelCoordinator
coordinator = ParallelCoordinator(connection_string, mapping_contract_path)
```

## Examples

### Production Environment (No Schema Prefix)
```bash
# No environment variable set
python production_processor.py --server "prod-server" --database "XmlConversionDB"
```
**Result**: Tables accessed as `[app_base]`, `[contact_base]`, etc.

### Sandbox Environment
```bash
set XML_EXTRACTOR_DB_SCHEMA_PREFIX=sandbox
python production_processor.py --server "test-server" --database "XmlConversionDB"
```
**Result**: Tables accessed as `[sandbox].[app_base]`, `[sandbox].[contact_base]`, etc.

### Development Environment
```bash
set XML_EXTRACTOR_DB_SCHEMA_PREFIX=dev
python production_processor.py --server "localhost\\SQLEXPRESS" --database "XmlConversionDB"
```
**Result**: Tables accessed as `[dev].[app_base]`, `[dev].[contact_base]`, etc.

## How It Works

1. **Centralized Configuration**: The schema prefix is managed by the `ConfigManager` class
2. **Automatic SQL Generation**: The `MigrationEngine` automatically applies the schema prefix to all SQL operations
3. **No Code Changes Required**: Your existing scripts and mapping contracts work unchanged
4. **Environment-Specific**: Each environment can have its own schema prefix

## SQL Operations Affected

All database operations automatically use the configured schema:

- **INSERT statements**: `INSERT INTO [sandbox].[app_base] (...)`
- **DELETE statements**: `DELETE FROM [sandbox].[app_base] WHERE ...`
- **IDENTITY_INSERT**: `SET IDENTITY_INSERT [sandbox].[app_base] ON`
- **Schema validation**: Checks tables in the specified schema

## Verification

You can verify the configuration is working by checking the logs:

```
INFO - MigrationEngine initialized with batch_size=1000
INFO - Using schema prefix: sandbox
DEBUG - Enabled IDENTITY_INSERT for [sandbox].[app_base]
INFO - Successfully inserted 25 records into app_base
```

## Best Practices

1. **Use Environment Variables**: Set the schema prefix via environment variables for easy deployment
2. **Document Your Schemas**: Clearly document which schema each environment uses
3. **Test Schema Switching**: Verify your application works with different schema prefixes
4. **Database Permissions**: Ensure your database user has access to the target schema

## Troubleshooting

### Schema Not Found Error
```
Invalid object name 'sandbox.app_base'
```
**Solution**: Ensure the schema exists and your database user has access to it.

### Permission Denied
```
The SELECT permission was denied on the object 'app_base', database 'XmlConversionDB', schema 'sandbox'
```
**Solution**: Grant appropriate permissions to your database user for the target schema.

### Environment Variable Not Working
**Solution**: Restart your application after setting the environment variable, or set it programmatically before importing the XML extractor modules.