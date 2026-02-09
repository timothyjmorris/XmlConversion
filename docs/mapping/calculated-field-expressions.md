# Calculated Field Expression Reference

**Last Updated**: 2026-02-09

This document provides a comprehensive guide to writing `calculated_field` expressions in mapping contracts. The Calculated Field Engine provides SQL-like expression evaluation for complex data transformations.

## Overview

Calculated field expressions enable dynamic value computation using:
- **Arithmetic operations**: Addition, subtraction, multiplication, division
- **Conditional logic**: CASE/WHEN/THEN/ELSE/END statements
- **Comparisons**: Equality, inequality, greater than, less than
- **Logical operators**: AND, OR, NOT
- **String operations**: LIKE pattern matching
- **Date operations**: Date parsing and arithmetic
- **Null handling**: IS EMPTY, IS NOT EMPTY, IS NULL, IS NOT NULL

All expressions are evaluated in a **safe sandbox environment** that prevents code injection while supporting cross-element references to access data from any part of the XML structure.

---

## Expression Language Features

### 1. Arithmetic Operations

**Supported Operators**: `+`, `-`, `*`, `/`, `//` (floor division), `%` (modulo), `**` (power)

**Operator Precedence**: Standard mathematical precedence (multiplication/division before addition/subtraction)

**Examples**:
```json
{
  "expression": "b_months_at_job + (b_years_at_job * 12)",
  "description": "Total months at job (years converted to months)"
}

{
  "expression": "loan_amount - down_payment",
  "description": "Amount financed"
}

{
  "expression": "selling_price * 0.065",
  "description": "Sales tax (6.5%)"
}

{
  "expression": "monthly_income / 12",
  "description": "Annual income"
}
```

**Nullable Behavior**: If ANY referenced field is `NULL` or empty, the entire arithmetic expression returns `None` (column excluded from INSERT). This preserves NULL semantics.

---

### 2. Conditional Logic (CASE Statements)

**Syntax**: `CASE WHEN condition THEN value WHEN condition THEN value ... ELSE default END`

**Features**:
- Multiple WHEN clauses evaluated in order
- Optional ELSE clause (if omitted and no WHEN matches, returns `None`)
- Supports nested expressions in conditions and values
- Case-insensitive keywords

**Examples**:

**Simple mapping**:
```json
{
  "expression": "CASE WHEN b_salary_basis_tp_c = 'ANNUM' THEN b_salary / 12 WHEN b_salary_basis_tp_c = 'MONTH' THEN b_salary WHEN b_salary_basis_tp_c = 'HOURLY' THEN b_salary * 160 ELSE 0 END",
  "description": "Convert salary to monthly income based on basis type"
}
```

**String-based conditional**:
```json
{
  "expression": "CASE WHEN application.app_type_code = 'SECURE' THEN 'V4' WHEN application.app_type_code = 'UNSECURE' THEN 'AJ' ELSE '' END",
  "description": "Map app type to score identifier"
}
```

**Multi-condition logic**:
```json
{
  "expression": "CASE WHEN app_product.adverse_actn1_type_cd IS NOT EMPTY AND application.app_receive_date > DATE('2023-10-11 00:00:00') AND application.population_assignment = 'CM' THEN 'AJ' WHEN app_product.adverse_actn1_type_cd LIKE 'V4_%' AND application.app_receive_date > DATE('2023-10-11 00:00:00') THEN 'V4' ELSE '' END",
  "description": "Complex score identifier determination with date checks"
}
```

**Empty string default** (common pattern):
```json
{
  "expression": "CASE WHEN field IS NOT EMPTY THEN field ELSE '' END",
  "description": "Ensure non-null string output"
}
```

---

### 3. Comparison Operators

**Supported Operators**:
- `=` : Equality
- `!=` : Inequality  
- `<` : Less than
- `>` : Greater than
- `<=` : Less than or equal
- `>=` : Greater than or equal

**Type Coercion**:
- String-to-numeric comparison attempted automatically
- Date-to-string comparison via DATE() function
- Lexicographic string comparison as fallback

**Examples**:
```json
{
  "expression": "CASE WHEN credit_score >= 700 THEN 'A' WHEN credit_score >= 650 THEN 'B' ELSE 'C' END",
  "description": "Credit tier based on score"
}

{
  "expression": "CASE WHEN loan_amount > 50000 THEN 'HIGH' ELSE 'STANDARD' END",
  "description": "Loan size category"
}
```

---

### 4. Logical Operators

**Supported**: `AND`, `OR`, `NOT`

**Evaluation**:
- `AND`: All conditions must be true
- `OR`: At least one condition must be true
- `NOT`: Not currently implemented as prefix operator (use `!=` instead)

**Examples**:
```json
{
  "expression": "CASE WHEN age >= 18 AND income > 30000 THEN 'ELIGIBLE' ELSE 'NOT_ELIGIBLE' END",
  "description": "Eligibility check with multiple criteria"
}

{
  "expression": "CASE WHEN state = 'CA' OR state = 'NY' OR state = 'TX' THEN 'HIGH_VOLUME' ELSE 'STANDARD' END",
  "description": "State-based categorization"
}
```

---

### 5. NULL and Empty Checks

**Supported Checks**:
- `IS NULL` : Value is null or empty string
- `IS NOT NULL` : Value is not null and not empty string
- `IS EMPTY` : Value is null, empty string, or whitespace only
- `IS NOT EMPTY` : Value has meaningful content (not null/empty/whitespace)

**Difference**: `IS EMPTY` checks for whitespace-only strings, `IS NULL` treats whitespace as non-null.

**Examples**:
```json
{
  "expression": "CASE WHEN middle_name IS NOT EMPTY THEN middle_name ELSE '' END",
  "description": "Use middle name if present, empty string otherwise"
}

{
  "expression": "CASE WHEN co_borrower_name IS NOT NULL THEN 1 ELSE 0 END",
  "description": "Flag for co-borrower presence"
}

{
  "expression": "CASE WHEN notes IS EMPTY THEN 'N/A' ELSE notes END",
  "description": "Default value for empty notes"
}
```

---

### 6. String Operations

**LIKE Pattern Matching**:
- `%` : Matches any sequence of characters (including zero)
- `_` : Matches exactly one character
- Case-insensitive matching

**Examples**:
```json
{
  "expression": "CASE WHEN app_product.adverse_actn1_type_cd LIKE 'V4_%' THEN 'V4_SERIES' ELSE 'OTHER' END",
  "description": "Pattern-based categorization"
}

{
  "expression": "CASE WHEN email LIKE '%@merrickbank.com' THEN 'INTERNAL' ELSE 'EXTERNAL' END",
  "description": "Email domain check"
}

{
  "expression": "CASE WHEN product_code LIKE 'RL%' THEN 'RECLENDING' WHEN product_code LIKE 'CC%' THEN 'CREDIT_CARD' ELSE 'UNKNOWN' END",
  "description": "Product line from code prefix"
}
```

**String Literals**: Use single or double quotes
```json
{
  "expression": "CASE WHEN status = 'APPROVED' THEN 'Y' ELSE 'N' END"
}
```

---

### 7. Date Functions

#### DATE() - Date Parsing

**Syntax**: `DATE('yyyy-mm-dd')` or `DATE(field_name)`

**Supported Formats**:
- `YYYY-MM-DD` (primary format)
- `MM/DD/YYYY`
- `DD/MM/YYYY`
- `YYYY-MM-DD HH:MM:SS`
- `YYYY-MM-DD HH:MM:SS.ffffff`

**Usage**:
- Literal dates: `DATE('2023-10-11')`
- Field references: `DATE(application.app_receive_date)`
- Comparison: `field > DATE('2023-01-01')`

**Examples**:
```json
{
  "expression": "CASE WHEN application.app_receive_date > DATE('2023-10-11 00:00:00') THEN 'NEW_PROCESS' ELSE 'LEGACY_PROCESS' END",
  "description": "Process version based on receive date"
}

{
  "expression": "CASE WHEN funding_date >= DATE('2024-01-01') THEN 'CURRENT_YEAR' ELSE 'PRIOR_YEAR' END",
  "description": "Fiscal year categorization"
}
```

#### DATEADD() - Date Arithmetic

**Syntax**: `DATEADD(day, number, date_field)`

**Parameters**:
- `unit`: Must be `day` (only unit currently supported)
- `number`: Integer, field reference, or expression (NULL/empty defaults to 0)
- `date_field`: Field reference or DATE() function

**Returns**: Date in `YYYY-MM-DD` format

**NULL Handling**: If `number` is NULL or empty, defaults to 0 (returns original date)

**Examples**:
```json
{
  "expression": "DATEADD(day, 30, IL_application.app_entry_date)",
  "description": "Add 30 days to entry date"
}

{
  "expression": "CASE WHEN IL_app_decision_info.regb_closed_days_num > 0 AND IL_application.app_entry_date IS NOT EMPTY THEN DATEADD(day, IL_app_decision_info.regb_closed_days_num, IL_application.app_entry_date) WHEN IL_app_decision_info.regb_closed_days_num > 0 AND IL_application.app_receive_date IS NOT EMPTY THEN DATEADD(day, IL_app_decision_info.regb_closed_days_num, IL_application.app_receive_date) END",
  "description": "Calculate regb end date by adding days to entry or receive date"
}

{
  "expression": "DATEADD(day, 60, DATE('2024-01-01'))",
  "description": "Add 60 days to literal date (returns 2024-03-01)"
}
```

---

### 8. Cross-Element References

Calculated fields can access data from **any part of the XML structure** using dotted notation. The DataMapper flattens the XML into a context dictionary before evaluation.

**Syntax**: `element_name.field_name`

**Common Patterns**:
- `application.app_receive_date`
- `app_product.adverse_actn1_type_cd`
- `IL_application.app_entry_date`
- `IL_app_decision_info.regb_closed_days_num`
- `contact.mother_maiden_name`

**Field Resolution**:
- Case-insensitive matching
- Direct dictionary lookup (flattened XML keys)
- Returns `None` if reference not found

**Examples**:
```json
{
  "expression": "CASE WHEN app_product.adverse_actn1_type_cd IS NOT EMPTY THEN app_product.adverse_actn1_type_cd ELSE application.default_action_code END",
  "description": "Use product-level action code, fall back to app-level"
}

{
  "expression": "application.app_id + 1000000",
  "description": "Offset application ID (cross-element arithmetic)"
}
```

---

## Expression Best Practices

### 1. Handle NULL Values Explicitly
Always consider what should happen when fields are NULL/empty:

```json
// ✅ GOOD: Explicit NULL handling
{
  "expression": "CASE WHEN field IS NOT EMPTY THEN field * 2 ELSE 0 END"
}

// ❌ BAD: Arithmetic with potential NULL (entire expression returns NULL)
{
  "expression": "field * 2"
}
```

### 2. Use IS EMPTY vs IS NULL Appropriately
- `IS EMPTY`: Checks for whitespace-only strings
- `IS NULL`: Treats whitespace as non-null

```json
// For user input fields (may contain whitespace)
{
  "expression": "CASE WHEN notes IS EMPTY THEN 'N/A' ELSE notes END"
}

// For system fields (strict NULL check)
{
  "expression": "CASE WHEN app_id IS NULL THEN 0 ELSE app_id END"
}
```

### 3. Order WHEN Clauses by Specificity
Most specific conditions first, catch-all last:

```json
{
  "expression": "CASE WHEN credit_score >= 750 THEN 'EXCELLENT' WHEN credit_score >= 700 THEN 'GOOD' WHEN credit_score >= 650 THEN 'FAIR' WHEN credit_score >= 600 THEN 'POOR' ELSE 'VERY_POOR' END"
}
```

### 4. Provide ELSE Clause for Robustness
Always include ELSE to avoid unexpected `None` results:

```json
// ✅ GOOD: ELSE provides default
{
  "expression": "CASE WHEN status = 'APPROVED' THEN 'Y' ELSE 'N' END"
}

// ❌ RISKY: No ELSE means NULL if no match
{
  "expression": "CASE WHEN status = 'APPROVED' THEN 'Y' END"
}
```

### 5. Keep Expressions Readable
For complex logic, use clear conditions and meaningful values:

```json
// ✅ GOOD: Clear logic
{
  "expression": "CASE WHEN application.app_receive_date > DATE('2023-10-11 00:00:00') AND application.population_assignment = 'CM' THEN 'AJ' ELSE '' END",
  "description": "Score identifier for Campaign Manager population after process change"
}

// ❌ BAD: Magic values without context
{
  "expression": "CASE WHEN f1 > DATE('2023-10-11') AND f2 = 'CM' THEN 'AJ' ELSE '' END"
}
```

---

## Common Patterns & Examples

### Pattern 1: Conditional Field Selection
Choose between multiple field sources:

```json
{
  "expression": "CASE WHEN primary_phone IS NOT EMPTY THEN primary_phone WHEN mobile_phone IS NOT EMPTY THEN mobile_phone WHEN work_phone IS NOT EMPTY THEN work_phone ELSE '' END",
  "description": "Best available phone number (priority order)"
}
```

### Pattern 2: Date-Based Branching
Different logic based on date ranges:

```json
{
  "expression": "CASE WHEN app_receive_date >= DATE('2024-01-01') THEN 'NEW_SCORING' WHEN app_receive_date >= DATE('2023-01-01') THEN 'LEGACY_SCORING' ELSE 'ARCHIVE' END",
  "description": "Scoring model version by receive date"
}
```

### Pattern 3: Multi-Criteria Eligibility
Complex AND/OR conditions:

```json
{
  "expression": "CASE WHEN (credit_score >= 680 AND dti_ratio <= 0.43) OR (credit_score >= 720 AND dti_ratio <= 0.50) THEN 'ELIGIBLE' ELSE 'NOT_ELIGIBLE' END",
  "description": "Tiered eligibility criteria"
}
```

### Pattern 4: Numeric Range Categorization
Bucket numeric values:

```json
{
  "expression": "CASE WHEN loan_amount <= 10000 THEN 'SMALL' WHEN loan_amount <= 25000 THEN 'MEDIUM' WHEN loan_amount <= 50000 THEN 'LARGE' ELSE 'JUMBO' END",
  "description": "Loan size category"
}
```

### Pattern 5: Pattern-Based Routing
Use LIKE for pattern matching:

```json
{
  "expression": "CASE WHEN officer_code LIKE '60%' THEN 'FUNDING_TEAM' WHEN officer_code LIKE '70%' THEN 'UNDERWRITING_TEAM' ELSE 'OTHER' END",
  "description": "Team assignment from officer code prefix"
}
```

### Pattern 6: NULL-Safe Arithmetic
Handle missing values in calculations:

```json
{
  "expression": "CASE WHEN monthly_debt IS NOT EMPTY AND monthly_income IS NOT EMPTY AND monthly_income > 0 THEN monthly_debt / monthly_income ELSE 0 END",
  "description": "Debt-to-income ratio (null-safe division)"
}
```

### Pattern 7: Date Offset Calculations
Add/subtract days from dates:

```json
{
  "expression": "CASE WHEN close_days > 0 AND app_entry_date IS NOT EMPTY THEN DATEADD(day, close_days, app_entry_date) ELSE NULL END",
  "description": "Calculate deadline by adding business days to entry date"
}
```

---

## Unsupported Features

The following SQL features are **NOT** supported (attempts to use will fail validation):

### Functions
- `IN` operator (use multiple `OR` conditions)
- `DATEDIFF()` (use comparison instead)
- `DATEPART()` / `YEAR()` / `MONTH()` / `DAY()`
- `SUBSTRING()` / `LEFT()` / `RIGHT()`
- `CONCAT()` (use multiple fields or manual concatenation)
- `COALESCE()` / `ISNULL()` (use CASE WHEN instead)
- `CAST()` / `CONVERT()` (data_type conversion is automatic)
- `ROUND()` / `FLOOR()` / `CEILING()`

### Advanced SQL
- Subqueries
- JOINs
- Aggregate functions (SUM, AVG, MAX, MIN, COUNT)
- Window functions
- Common Table Expressions (CTEs)

### Workarounds

**Instead of IN**:
```json
// ❌ NOT SUPPORTED
"expression": "CASE WHEN state IN ('CA', 'NY', 'TX') THEN 'HIGH' ELSE 'LOW' END"

// ✅ USE THIS
"expression": "CASE WHEN state = 'CA' OR state = 'NY' OR state = 'TX' THEN 'HIGH' ELSE 'LOW' END"
```

**Instead of COALESCE**:
```json
// ❌ NOT SUPPORTED
"expression": "COALESCE(field1, field2, field3, 'default')"

// ✅ USE THIS
"expression": "CASE WHEN field1 IS NOT EMPTY THEN field1 WHEN field2 IS NOT EMPTY THEN field2 WHEN field3 IS NOT EMPTY THEN field3 ELSE 'default' END"
```

---

## Validation & Testing

### Unit Test
The `test_expression_validation.py` test validates all expressions in contracts:
```powershell
pytest tests/unit/test_expression_validation.py -v
```

This test:
- Extracts all function calls and keywords from expressions
- Validates against `SUPPORTED_KEYWORDS` list
- Fails if unsupported keywords are found
- Prevents `ADDDAYS` usage (replaced by `DATEADD`)

### Integration Testing
Test calculated fields end-to-end:
```powershell
python tests/e2e/manual_test_pipeline_full_integration_rl.py 325725
```

---

## Safety & Security

### Sandboxed Evaluation
- No access to file I/O, system calls, or external modules
- Restricted `eval()` with `__builtins__` disabled
- Only safe mathematical operations permitted
- Expression validation before execution

### Character Restrictions
Expressions must match: `^[a-zA-Z0-9_+\-*/().'"\s]+$`

Disallowed:
- `import`, `exec`, `eval`, `__`
- `open`, `file`, `input`
- Arbitrary code execution

### Error Handling
- Invalid expressions raise `DataTransformationError`
- Missing field references return `None` (graceful degradation)
- Type conversion errors logged with field context
- Arithmetic errors (division by zero) return `None`

---

## Related Documentation

- [mapping-types-and-capabilities.md](mapping-types-and-capabilities.md) - Overview of all mapping types
- [calculated_field_engine.py](../../xml_extractor/mapping/calculated_field_engine.py) - Implementation
- [test_expression_validation.py](../../tests/unit/test_expression_validation.py) - Validation tests

---

## Changelog

**2026-02-09**:
- Added DATEADD() function for date arithmetic
- Replaced ADDDAYS() with DATEADD(day, number, date)
- Documented all supported expression keywords
- Added comprehensive examples and patterns
- Clarified NULL/EMPTY semantics
- Added unsupported features section
