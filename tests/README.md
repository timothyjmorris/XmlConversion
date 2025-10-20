# Test Suite Guide

## 🚀 **Quick Start - How to Run Tests**

```bash
# 🏃‍♂️ DEVELOPMENT: Quick feedback (< 30 seconds)
python tests/run_quick_tests.py

# 🔍 PRE-COMMIT: Thorough validation (< 3 minutes)  
python -m pytest tests/unit/ tests/integration/ -v

# 🎯 PRE-RELEASE: Full validation (< 10 minutes)
python tests/run_comprehensive_suite.py
```

## 📊 **What to Expect**

| Test Type | Speed | Pass Rate | When It Fails |
|-----------|-------|-----------|---------------|
| **Quick Tests** | < 30s | 100% required | Fix before continuing development |
| **Pre-Commit** | < 3min | 100% required | Fix before committing |
| **Full Suite** | < 10min | ≥90% acceptable | Review before release |

## 🗂️ **Test Categories**

### **Unit Tests** (`tests/unit/`) - Fast & Isolated
- **Purpose**: Test individual components with mock data
- **Speed**: < 5 seconds each
- **When**: After every code change
- **Files**: `test_config_manager_unit.py`, `test_validation_scenarios_unit.py`, `test_validation_system_unit.py`

### **Integration Tests** (`tests/integration/`) - Real Data
- **Purpose**: Test component interactions with real sample data
- **Speed**: 5-30 seconds each  
- **When**: Before commits
- **Files**: `test_config_integration.py`, `test_validation_real_sample.py`, `test_database_connection.py`

### **E2E Tests** (`tests/e2e/`) - Full Pipeline
- **Purpose**: Test complete workflows with production-like data
- **Speed**: 30+ seconds each
- **When**: Before releases
- **Files**: `test_pipeline_full_integration.py`, `test_production_batch_processing.py`

### **Contract Tests** (`tests/contracts/`) - Schema Validation
- **Purpose**: Validate configuration files and schemas
- **Speed**: < 5 seconds each
- **When**: After config changes
- **Files**: `test_mapping_contract_schema.py`

## 🎯 **Development Workflow**

### **1. During Development**
```bash
python tests/run_quick_tests.py
```
- Runs unit + contract tests
- Should complete in < 30 seconds
- Must pass 100% before continuing

### **2. Before Committing**
```bash
python -m pytest tests/unit/ tests/integration/ -v
```
- Runs unit + integration tests
- Should complete in < 3 minutes
- Must pass 100% before committing

### **3. Before Releasing**
```bash
python tests/run_comprehensive_suite.py
```
- Runs all test categories
- Should complete in < 10 minutes
- ≥90% pass rate acceptable (E2E can be flaky with production data)

## 🔧 **Troubleshooting**

### **If Quick Tests Fail**
- **Stop development** and fix the issue
- These are fast, isolated tests that should always pass
- Failures indicate core functionality is broken

### **If Integration Tests Fail**
- **Don't commit** until fixed
- Check database connectivity and sample data
- Verify component interactions are working

### **If E2E Tests Fail**
- **Investigate but may proceed** if < 10% failure rate
- E2E tests can be sensitive to data variations
- Review failures to ensure they're not critical

### **Common Issues**
- **Import errors**: Check module paths after file moves
- **Database connection**: Ensure test database is accessible
- **Sample data**: Verify test XML files exist and are valid

## 📈 **Test Results Interpretation**

### **Success Indicators**
- ✅ All quick tests pass
- ✅ Unit tests execute in < 60 seconds total
- ✅ Integration tests complete without database errors
- ✅ Contract tests validate all schemas

### **Warning Signs**
- ⚠️ Tests taking longer than expected
- ⚠️ Intermittent failures (flaky tests)
- ⚠️ Database connection timeouts
- ⚠️ Missing test data files

### **Critical Issues**
- 🚨 Unit tests failing (core functionality broken)
- 🚨 Contract tests failing (configuration invalid)
- 🚨 All integration tests failing (system integration broken)

## 🛠️ **Advanced Usage**

### **Run Specific Categories**
```bash
# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only  
python -m pytest tests/integration/ -v

# E2E tests only
python -m pytest tests/e2e/ -v

# Contract tests only
python -m pytest tests/contracts/ -v
```

### **Run Specific Test Files**
```bash
# Single test file
python -m pytest tests/unit/test_config_manager_unit.py -v

# Single test method
python -m pytest tests/unit/test_config_manager_unit.py::TestConfigManager::test_initialization -v
```

### **Test with Coverage**
```bash
python -m pytest tests/unit/ --cov=xml_extractor --cov-report=html
```

### **Parallel Execution** (if pytest-xdist installed)
```bash
python -m pytest tests/ -n auto
```

## 📋 **Test Organization Benefits**

### **✅ Clear Purpose**
- Each test category has a specific role
- Easy to know which tests to run when
- Predictable execution times

### **✅ Fast Feedback**
- Quick tests provide immediate feedback
- Comprehensive tests catch integration issues
- Full suite validates production readiness

### **✅ Maintainable**
- Logical organization makes tests easy to find
- Clear naming conventions
- Scalable structure for adding new tests

## 🎉 **Current Status**

- ✅ **Test Organization**: Complete and well-structured
- ✅ **Test Runners**: Working and optimized
- ✅ **Contract Tests**: 7/7 passing
- ⚠️ **Unit Tests**: Some failing due to discovered bugs (this is good!)
- ✅ **Integration Tests**: Ready for use
- ✅ **E2E Tests**: Ready for use

The failing unit tests are **working as intended** - they've discovered real bugs in the XML parser and validation logic that need to be fixed.