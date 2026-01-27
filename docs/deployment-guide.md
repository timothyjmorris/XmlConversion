# XML Database Extractor - Deployment Guide

## 📦 Distribution Packages Created

✅ **SUCCESS**: The following distribution packages were created in the `dist/` folder:

- **`xml_database_extractor-1.0.0-py3-none-any.whl`** - Wheel package (preferred for installation)
- **`xml_database_extractor-1.0.0.tar.gz`** - Source distribution (backup/development)

## 🚀 Deploying to Different Machines

### Method 1: Direct Wheel Installation (Recommended)

**Copy the wheel file to your target machine and install:**

```powershell
# Copy the wheel file to target machine first
# Then install the wheel package
pip install xml_database_extractor-1.0.0-py3-none-any.whl

# Or install with development dependencies if needed
pip install xml_database_extractor-1.0.0-py3-none-any.whl[dev]
```

### Method 2: Source Distribution Installation

```powershell
# Copy the tar.gz file to target machine
# Then install from source
pip install xml_database_extractor-1.0.0.tar.gz
```

### Method 3: Combined Package Transfer

**Create a deployment bundle with dependencies:**

```powershell
# On development machine, download all dependencies
pip download xml_database_extractor-1.0.0-py3-none-any.whl -d deployment_bundle

# Copy entire deployment_bundle folder to target machine
# Then install offline
pip install --find-links deployment_bundle --no-index xml_database_extractor
```

## 📁 What's Included in the Package

The package includes **everything needed** for deployment:

✅ **Core Python Code**:
- `xml_extractor/` - Complete Python package
- `production_processor.py` - Main processing script

✅ **Configuration & Contracts**:
- `config/mapping_contract.json` - ETL transformation rules
- `config/database_config.json` - Database configuration template
- `config/samples/` - SQL scripts and XML samples

✅ **Documentation**:
- `docs/` - Complete documentation set
- `README.md` - Usage instructions

✅ **Testing Framework**:
- `tests/` - Complete test suite for validation
- `requirements.txt` - Dependency specifications

## 🖥️ Target Machine Setup

### 1. Prerequisites on Target Machine

```powershell
# Ensure Python 3.8+ is installed
python --version

# Install pip if not available
# Download get-pip.py and run: python get-pip.py
```

### 2. Install the Package

```powershell
# Install from wheel (fastest)
pip install xml_database_extractor-1.0.0-py3-none-any.whl

# Verify installation
xml-extractor  # Should display configuration info
```

### 3. Configure for Target Environment

```powershell
# Set environment variables for target database
$env:XML_EXTRACTOR_DB_SERVER = "target-sql-server"
$env:XML_EXTRACTOR_DB_DATABASE = "TargetDatabase"

# Test connectivity
python -c "from xml_extractor.config import get_config_manager; print(get_config_manager())"
```

### 4. Run Production Processing

```powershell
# The production_processor.py script is included in the package
# Find its location after installation
python -c "import xml_extractor; import os; print(os.path.dirname(xml_extractor.__file__))"

# Or run directly if in PATH
python production_processor.py --server "target-server" --database "TargetDB" --limit 100
```

## 🔧 Advanced Deployment Options

### Docker Deployment (If Needed)

```dockerfile
# Dockerfile example
FROM python:3.11-slim

# Copy wheel file
COPY xml_database_extractor-1.0.0-py3-none-any.whl /tmp/

# Install package
RUN pip install /tmp/xml_database_extractor-1.0.0-py3-none-any.whl

# Set working directory
WORKDIR /app

# Entry point
CMD ["python", "-m", "xml_extractor.cli"]
```

### Network Share Deployment

```powershell
# Copy to network location
Copy-Item "xml_database_extractor-1.0.0-py3-none-any.whl" "\\network-share\software\"

# Install from network share on target machines
pip install "\\network-share\software\xml_database_extractor-1.0.0-py3-none-any.whl"
```

## ✅ Verification Checklist

After installation on target machine, verify:

```powershell
# 1. Package installed correctly
pip list | findstr xml-database

# 2. CLI command works
xml-extractor

# 3. Python import works
python -c "import xml_extractor; print('✓ Import successful')"

# 4. Configuration loads
python -c "from xml_extractor.config import get_config_manager; get_config_manager()"

# 5. Dependencies installed
python -c "import lxml, pyodbc; print('✓ Dependencies OK')"
```

## 🚨 Common Deployment Issues & Solutions

### Issue: Missing Dependencies

```powershell
# Solution: Install with dependencies
pip install xml_database_extractor-1.0.0-py3-none-any.whl --upgrade --force-reinstall
```

### Issue: ODBC Driver Missing

```powershell
# Download and install ODBC Driver 17 for SQL Server from Microsoft
# Or set connection string to use available driver
```

### Issue: Permission Errors

```powershell
# Install for user only
pip install --user xml_database_extractor-1.0.0-py3-none-any.whl
```

### Issue: Python Path Issues

```powershell
# Use full Python path
"C:\Program Files\Python311\python.exe" -m pip install xml_database_extractor-1.0.0-py3-none-any.whl
```

## 📋 Production Deployment Checklist

- [ ] Copy `.whl` file to target machine
- [ ] Install package: `pip install xml_database_extractor-1.0.0-py3-none-any.whl`  
- [ ] Verify CLI works: `xml-extractor`
- [ ] Configure environment variables for target database
- [ ] Test connectivity with small batch: `--limit 10`
- [ ] Configure production settings in `config/` files
- [ ] Set up monitoring and logging
- [ ] Schedule production runs

## 🎯 Ready for Multi-Machine Deployment!

Your package is now **production-ready** and includes everything needed to deploy to different machines. The wheel format ensures fast, consistent installation across environments.