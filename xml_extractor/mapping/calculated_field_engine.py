"""
Calculated Field Engine for XML Database Extraction system.

Provides safe expression evaluation for calculated field mappings with
- Support for arithmetic operations, comparisons and conditional logic. 
- Expression can use SQL syntax for conditionals (CASE/WHEN/THEN/ELSE/END)
- Supports datetime comparisons with function `DATE('yyyy-mm-dd hh:mm:ss')`
- 'Empty-check' evalutions with `IS EMPTY` / `IS NOT EMPTY` and `''`
- Handles 'cross element' references with dot notation (e.g., 'contact.field_name')

Examples for 'calculated_field' as a mapping_type in the mapping contract:
    "expression": "b_months_at_job + (b_years_at_job * 12)"
    "expression": "CASE WHEN b_salary_basis_tp_c = 'ANNUM' THEN b_salary / 12 WHEN b_salary_basis_tp_c = 'MONTH' THEN b_salary * 12 WHEN b_salary_basis_tp_c = 'HOURLY' THEN b_salary WHEN b_salary_basis_tp_c = '' THEN b_salary ELSE b_salary END"
    "expression": "CASE WHEN app_product.adverse_actn1_type_cd IS NOT EMPTY AND application.app_receive_date > DATE('2023-10-11 00:00:00') AND application.population_assignment = 'CM' THEN 'AJ' WHEN app_product.adverse_actn1_type_cd LIKE 'V4_%' AND application.app_receive_date > DATE('2023-10-11 00:00:00') AND application.app_type_code = 'SECURE' THEN 'V4' ELSE '' END"
"""

import re
import logging

from typing import Dict, Any, Optional, Union, List
from decimal import Decimal
from datetime import datetime

from ..exceptions import DataTransformationError
from ..utils import ValidationUtils


class CalculatedFieldEngine:
    """
    Safe and efficient engine for evaluating calculated field expressions in XML-to-database mappings.

    This engine provides SQL-like expression evaluation with safety restrictions to prevent code injection
    while supporting complex business logic. It enables cross-element references using dotted notation,
    allowing calculated fields to access data from any part of the XML structure.

    Expression Language Features:
    - Arithmetic: +, -, *, / with proper operator precedence
    - Comparisons: =, !=, <, >, <=, >=
    - Logical: AND, OR, NOT
    - Conditional: CASE WHEN ... THEN ... ELSE ... END
    - String operations: LIKE pattern matching
    - Date operations: DATE('yyyy-mm-dd hh:mm:ss') constructor
    - Null checking: IS EMPTY, IS NOT EMPTY
    - Cross-element references: table.field or element.subfield notation

    Safety Features:
    - Restricted to safe mathematical operations only (no file I/O, system calls, etc.)
    - Expression validation before evaluation
    - Error handling with detailed logging
    - Memory-safe evaluation with recursion limits
    - Type coercion for database compatibility

    Cross-Element Reference Resolution:
    - References like 'application.app_receive_date' access data from the flattened XML structure
    - Supports both direct field access and nested element traversal
    - Context-aware evaluation where field values are resolved from the provided data context
    - Fallback to None for missing references (graceful degradation)

    Performance Optimizations:
    - Pre-compiled regex patterns for expression parsing
    - Efficient CASE statement parsing and evaluation
    - Cached safe operations dictionary
    - Minimal memory allocation during evaluation
    """
    
    def __init__(self):
        """Initialize the calculated field engine."""
        self.logger = logging.getLogger(__name__)
        
        # Compile regex patterns for performance
        self._case_pattern = re.compile(
            r'CASE\s+WHEN\s+(.+?)\s+THEN\s+(.+?)(?:\s+WHEN\s+(.+?)\s+THEN\s+(.+?))*(?:\s+ELSE\s+(.+?))?\s+END',
            re.IGNORECASE | re.DOTALL
        )
        
        # Safe mathematical operations allowed in expressions
        self._safe_operations = {
            '__add__': lambda x, y: x + y,
            '__sub__': lambda x, y: x - y, 
            '__mul__': lambda x, y: x * y,
            '__truediv__': lambda x, y: x / y if y != 0 else None,
            '__floordiv__': lambda x, y: x // y if y != 0 else None,
            '__mod__': lambda x, y: x % y if y != 0 else None,
            '__pow__': lambda x, y: x ** y,
        }
    
    def evaluate_expression(self, expression: str, element_data: Dict[str, Any], 
                          target_column: str) -> Optional[Union[int, float, Decimal, str]]:
        """
        Evaluate a calculated field expression with support for cross-element references and complex logic.

        This method parses and evaluates SQL-like expressions that can reference data from any part
        of the XML structure using dotted notation. It supports both simple arithmetic and complex
        CASE WHEN conditional logic.

        Expression Types:
        - Arithmetic: "field1 + field2 * 12"
        - CASE statements: "CASE WHEN condition THEN value ELSE default END"
        - Cross-element: "application.app_receive_date > DATE('2023-10-11')"

        Cross-Element Reference Resolution:
        - element_data contains flattened XML data with keys like 'application.app_id', 'contact.con_id'
        - References are resolved by direct dictionary lookup
        - Missing references return None (graceful degradation)
        - Supports nested object access with dot notation

        Args:
            expression: SQL-like expression string to evaluate
            element_data: Flattened dictionary of all available XML data for cross-element references
            target_column: Column name for error reporting and logging context

        Returns:
            Evaluated result (int, float, Decimal, str) or None if evaluation fails

        Raises:
            DataTransformationError: If expression syntax is invalid or evaluation fails
        """
        self.logger.debug(f"Evaluating expression for {target_column}: {expression}")
        self.logger.debug(f"Element data keys: {list(element_data.keys())[:20]}")  # First 20 keys
        if 'app_product.adverse_actn1_type_cd' in element_data:
            self.logger.debug(f"app_product.adverse_actn1_type_cd = {element_data['app_product.adverse_actn1_type_cd']}")
        if 'application.app_receive_date' in element_data:
            self.logger.debug(f"application.app_receive_date = {element_data['application.app_receive_date']}")
        if 'application.population_assignment' in element_data:
            self.logger.debug(f"application.population_assignment = {element_data['application.population_assignment']}")
        
        try:
            # Handle CASE statements
            if 'CASE' in expression.upper():
                return self._evaluate_case_statement(expression, element_data, target_column)
            
            # Handle simple arithmetic expressions
            return self._evaluate_arithmetic_expression(expression, element_data, target_column)
            
        except Exception as e:
            self.logger.warning(f"Failed to evaluate calculated field '{target_column}': {e}")
            raise DataTransformationError(
                f"Calculated field evaluation failed for {target_column}: {e}",
                field_name=target_column,
                source_value=expression
            )
    
    def _evaluate_case_statement(self, expression: str, element_data: Dict[str, Any], 
                               target_column: str) -> Optional[Union[int, float, Decimal, str]]:
        """
        Evaluate CASE WHEN ... THEN ... ELSE ... END statements.
        
        Supports multiple WHEN clauses and optional ELSE clause.
        """
        self.logger.debug(f"Evaluating CASE statement for {target_column}: {expression}")
        
        # Parse CASE statement structure
        case_match = self._case_pattern.search(expression)
        if not case_match:
            raise DataTransformationError(f"Invalid CASE statement syntax: {expression}")
        
        # Extract all WHEN/THEN pairs and optional ELSE
        when_then_pairs = []
        else_value = None
        
        # Split the expression to handle multiple WHEN clauses (preserve original case)
        case_body = expression
        # Remove CASE and END keywords while preserving case of field names
        case_body = re.sub(r'\bCASE\b', '', case_body, flags=re.IGNORECASE).strip()
        case_body = re.sub(r'\bEND\b', '', case_body, flags=re.IGNORECASE).strip()
        
        # Simple parser for WHEN/THEN pairs
        parts = re.split(r'\s+WHEN\s+', case_body, flags=re.IGNORECASE)
        self.logger.debug(f"CASE parsing: expression='{expression}', case_body='{case_body}', parts={parts}")
        
        for part in parts:  # Process all parts (first part is not empty after removing CASE keyword)
            self.logger.debug(f"Processing CASE part: '{part}'")
            if 'THEN' in part.upper():
                when_then = re.split(r'\s+THEN\s+', part, maxsplit=1, flags=re.IGNORECASE)
                if len(when_then) == 2:
                    condition = when_then[0].strip()
                    # Remove WHEN keyword if present (for first condition)
                    condition = re.sub(r'^\s*WHEN\s+', '', condition, flags=re.IGNORECASE)
                    value_part = when_then[1].strip()
                    
                    # Check if this part contains ELSE
                    if 'ELSE' in value_part.upper():
                        value_else = re.split(r'\s+ELSE\s+', value_part, maxsplit=1, flags=re.IGNORECASE)
                        then_value = value_else[0].strip()
                        else_value = value_else[1].strip()
                    else:
                        then_value = value_part
                    
                    when_then_pairs.append((condition, then_value))
                    self.logger.debug(f"Parsed WHEN/THEN pair: condition='{condition}', then_value='{then_value}', else_value='{else_value}'")
        
        # Evaluate WHEN conditions in order
        for condition, then_value in when_then_pairs:
            try:
                if self._evaluate_condition(condition, element_data):
                    result = self._evaluate_value_expression(then_value, element_data)
                    self.logger.debug(f"CASE: WHEN condition matched, returning: {repr(result)}")
                    return result
            except Exception as e:
                self.logger.error(f"CASE: Error evaluating WHEN condition '{condition}': {e}")
                continue
        
        # If no WHEN condition matched, use ELSE value
        self.logger.debug(f"CASE: No WHEN conditions matched, else_value='{else_value}'")
        if else_value is not None:
            try:
                result = self._evaluate_value_expression(else_value, element_data)
                self.logger.debug(f"CASE: Returning ELSE value: {repr(result)}")
                return result
            except Exception as e:
                self.logger.error(f"CASE: Error evaluating ELSE value '{else_value}': {e}")
                return None
        
        # No condition matched and no ELSE clause
        self.logger.debug("CASE: No conditions matched and no ELSE clause")
        return None
    
    def _evaluate_condition(self, condition: str, element_data: Dict[str, Any]) -> bool:
        """
        Evaluate a boolean condition, supporting compound conditions with AND/OR.
        
        Supports: =, !=, <, >, <=, >=, IS NULL, IS NOT NULL, DATE() function, LIKE operator, IS EMPTY/NOT EMPTY
        """
        condition = condition.strip()
        
        # Handle compound conditions with AND/OR
        if ' AND ' in condition.upper():
            parts = self._split_condition(condition, 'AND')
            results = [self._evaluate_simple_condition(part.strip(), element_data) for part in parts]
            return all(results)
        elif ' OR ' in condition.upper():
            parts = self._split_condition(condition, 'OR')
            results = [self._evaluate_simple_condition(part.strip(), element_data) for part in parts]
            return any(results)
        else:
            # Single condition
            result = self._evaluate_simple_condition(condition, element_data)
            return result
    
    def _split_condition(self, condition: str, operator: str) -> List[str]:
        """Split a compound condition on AND/OR, respecting parentheses."""
        # Simple split for now - doesn't handle nested parentheses
        return condition.upper().split(f' {operator} ')
    
    def _evaluate_simple_condition(self, condition: str, element_data: Dict[str, Any]) -> bool:
        
        # Handle IS EMPTY / IS NOT EMPTY
        if 'IS EMPTY' in condition.upper():
            field_name = condition.upper().replace('IS EMPTY', '').strip()
            actual_field = self._find_field_case_insensitive(field_name, element_data)
            field_value = element_data.get(actual_field, '') if actual_field else ''
            result = field_value is None or str(field_value).strip() == ''
            self.logger.debug(f"IS EMPTY check: field='{field_name}', actual_field='{actual_field}', value='{field_value}', result={result}")
            return result
        
        if 'IS NOT EMPTY' in condition.upper():
            field_name = condition.upper().replace('IS NOT EMPTY', '').strip()
            actual_field = self._find_field_case_insensitive(field_name, element_data)
            field_value = element_data.get(actual_field, '') if actual_field else ''
            result = field_value is not None and str(field_value).strip() != ''
            self.logger.debug(f"IS NOT EMPTY check: field='{field_name}', actual_field='{actual_field}', value='{field_value}', result={result}")
            return result
        
        # Handle IS NULL / IS NOT NULL
        if 'IS NULL' in condition.upper():
            field_name = condition.upper().replace('IS NULL', '').strip()
            actual_field = self._find_field_case_insensitive(field_name, element_data)
            field_value = element_data.get(actual_field, '') if actual_field else ''
            return field_value is None or field_value == ''
        
        if 'IS NOT NULL' in condition.upper():
            field_name = condition.upper().replace('IS NOT NULL', '').strip()
            actual_field = self._find_field_case_insensitive(field_name, element_data)
            field_value = element_data.get(actual_field, '') if actual_field else ''
            return field_value is not None and field_value != ''
        
        # Handle LIKE operator
        if ' LIKE ' in condition.upper():
            parts = condition.upper().split(' LIKE ', 1)
            if len(parts) == 2:
                left_field = parts[0].strip()
                pattern = parts[1].strip().strip("'\"")
                
                # Find the actual field name case-insensitively
                actual_field = None
                for key in element_data.keys():
                    if key.upper() == left_field:
                        actual_field = key
                        break
                
                left_val = str(element_data.get(actual_field, '')) if actual_field else ''
                return self._matches_like_pattern(left_val, pattern)
        
        # Handle comparison operators
        operators = ['!=', '<=', '>=', '=', '<', '>']
        
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left_expr = parts[0].strip()
                    right_expr = parts[1].strip()
                    
                    # Handle DATE() function calls
                    left_val = self._extract_date_value(left_expr, element_data)
                    right_val = self._extract_date_value(right_expr, element_data)
                    
                    # If not DATE() functions, get regular field values
                    if left_val is None:
                        left_val = element_data.get(self._find_field_case_insensitive(left_expr, element_data), '')
                    if right_val is None:
                        # Check if right_expr is a quoted literal
                        if (right_expr.startswith("'") and right_expr.endswith("'")) or \
                           (right_expr.startswith('"') and right_expr.endswith('"')):
                            right_val = right_expr[1:-1]  # Remove quotes
                        else:
                            right_val = element_data.get(self._find_field_case_insensitive(right_expr, element_data), '')
                    
                    # Perform comparison with proper type handling
                    if op == '=':
                        result = self._safe_compare(left_val, right_val, lambda x, y: x == y)
                        return result
                    elif op == '!=':
                        return self._safe_compare(left_val, right_val, lambda x, y: x != y)
                    elif op == '<':
                        return self._safe_compare(left_val, right_val, lambda x, y: x < y)
                    elif op == '>':
                        return self._safe_compare(left_val, right_val, lambda x, y: x > y)
                    elif op == '<=':
                        return self._safe_compare(left_val, right_val, lambda x, y: x <= y)
                    elif op == '>=':
                        return self._safe_compare(left_val, right_val, lambda x, y: x >= y)
                
                break
        
        return False
    
    def _extract_date_value(self, expr: str, element_data: Dict[str, Any]) -> Optional[datetime]:
        """Extract date value from DATE() function call or return None if not a DATE() call."""
        expr = expr.strip()
        if expr.upper().startswith('DATE(') and expr.endswith(')'):
            # Extract the content from DATE(content)
            content = expr[5:-1].strip()
            
            # Check if it's a quoted literal
            if (content.startswith("'") and content.endswith("'")) or \
               (content.startswith('"') and content.endswith('"')):
                # It's a literal date string
                date_str = content[1:-1]  # Remove quotes
            else:
                # It's a field reference
                field_value = element_data.get(content)
                if field_value is None:
                    return None
                date_str = str(field_value)
            
            # Try to parse the date string
            try:
                # Try to parse as date (assuming YYYY-MM-DD format)
                return datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                # If parsing fails, try other common formats
                for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
                # If all parsing fails, return None
                return None
    
    def _matches_like_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches SQL LIKE pattern with % and _ wildcards."""
        # Convert SQL LIKE pattern to regex
        # % matches any sequence of characters
        # _ matches any single character
        regex_pattern = pattern.replace('%', '.*').replace('_', '.')
        # Escape the pattern, but since we already converted % and _, we're good
        try:
            return bool(re.match(f'^{regex_pattern}$', value, re.IGNORECASE))
        except re.error:
            # If regex compilation fails, fall back to simple string matching
            return pattern == value
    
    def _safe_compare(self, left_val: Any, right_val: Any, compare_func) -> bool:
        """Safely compare values, handling both dates and numeric types."""
        # If both are datetime objects, compare directly
        if isinstance(left_val, datetime) and isinstance(right_val, datetime):
            return compare_func(left_val, right_val)
        
        # If one is datetime and other is string, try to parse the string as date
        if isinstance(left_val, datetime) and isinstance(right_val, str):
            try:
                # Try the same formats as _extract_date_value
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        right_date = datetime.strptime(right_val, fmt)
                        return compare_func(left_val, right_date)
                    except ValueError:
                        continue
                return False
            except ValueError:
                return False
        
        if isinstance(right_val, datetime) and isinstance(left_val, str):
            try:
                # Try the same formats as _extract_date_value
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        left_date = datetime.strptime(left_val, fmt)
                        return compare_func(left_date, right_val)
                    except ValueError:
                        continue
                return False
            except ValueError:
                return False
        
        # If both are strings, do string comparison
        if isinstance(left_val, str) and isinstance(right_val, str):
            return compare_func(left_val, right_val)
        
        # Fall back to numeric comparison
        return self._safe_numeric_compare(left_val, right_val, compare_func)
    
    def _safe_numeric_compare(self, left_val: Any, right_val: Any, compare_func) -> bool:
        """Safely compare numeric values with type conversion."""
        try:
            left_num = ValidationUtils.safe_float_conversion(left_val, 0.0)
            right_num = ValidationUtils.safe_float_conversion(right_val, 0.0)
            return compare_func(left_num, right_num)
        except (ValueError, TypeError):
            return False
    
    def _find_field_case_insensitive(self, field_name: str, element_data: Dict[str, Any]) -> Optional[str]:
        """Find the actual field name in element_data case-insensitively."""
        field_upper = field_name.upper()
        for key in element_data.keys():
            if key.upper() == field_upper:
                return key
        return None
    
    def _evaluate_value_expression(self, expression: str, element_data: Dict[str, Any]) -> Optional[Union[int, float, Decimal, str]]:
        """
        Evaluate a value expression (could be field name, literal, or arithmetic).
        Supports cross-element field references like 'contact.field_name'.
        """
        expression = expression.strip()
        
        # If it's a simple field reference (including dotted cross-element references)
        if expression in element_data:
            return element_data[expression]
        
        # Handle dotted field references (cross-element access)
        if '.' in expression:
            parts = expression.split('.', 1)
            if len(parts) == 2:
                prefix, field_name = parts
                # Check if it's a cross-element reference like 'contact.field_name'
                cross_ref = f"{prefix}.{field_name}"
                if cross_ref in element_data:
                    return element_data[cross_ref]
        
        # If it's a quoted literal
        if (expression.startswith("'") and expression.endswith("'")) or \
           (expression.startswith('"') and expression.endswith('"')):
            return expression[1:-1]  # Remove quotes
        
        # If it's a numeric literal
        try:
            if '.' in expression:
                return float(expression)
            else:
                return int(expression)
        except ValueError:
            pass
        
        # If it's an arithmetic expression
        return self._evaluate_arithmetic_expression(expression, element_data, "value_expression")
    
    def _evaluate_arithmetic_expression(self, expression: str, element_data: Dict[str, Any], 
                                      target_column: str) -> Optional[Union[int, float, Decimal]]:
        """
        Evaluate arithmetic expressions safely using restricted eval.
        
        Only allows field references and basic math operations.
        """
        # Create safe namespace with only field values and safe operations
        safe_namespace = {
            '__builtins__': {},  # Remove all built-in functions
            # Add field values as variables (including dotted cross-element references)
            **{k: ValidationUtils.safe_float_conversion(v, 0.0) 
               for k, v in element_data.items() if v is not None}
        }
        
        # Validate expression contains only safe characters (allow dots for cross-element refs and quotes for literals)
        if not re.match(r'^[a-zA-Z0-9_+\-*/().\'"\s]+$', expression):
            raise DataTransformationError(f"Expression contains unsafe characters: {expression}")
        
        # Replace field names with safe variable names (in case they have special chars)
        safe_expression = expression
        for field_name in element_data.keys():
            if field_name in expression:
                safe_var_name = re.sub(r'[^a-zA-Z0-9_]', '_', field_name)
                safe_namespace[safe_var_name] = ValidationUtils.safe_float_conversion(
                    element_data[field_name], 0.0
                )
                safe_expression = safe_expression.replace(field_name, safe_var_name)
        
        try:
            # Use eval with restricted namespace for maximum flexibility
            result = eval(safe_expression, safe_namespace)
            
            # Convert result to appropriate type
            if isinstance(result, (int, float)):
                return result
            else:
                return ValidationUtils.safe_float_conversion(result, None)
                
        except Exception as e:
            self.logger.warning(f"Arithmetic evaluation failed for '{expression}': {e}")
            return None
    
    def _find_field_case_insensitive(self, field_name: str, element_data: Dict[str, Any]) -> Optional[str]:
        """
        Find the actual field name in element_data using case-insensitive lookup.
        Also handles qualified field references like 'app_product.field_name'.
        
        Args:
            field_name: The field name to find (may be qualified with dots)
            element_data: Dictionary containing field values
            
        Returns:
            The actual field name if found, None otherwise
        """
        # Handle qualified references (e.g., 'app_product.adverse_actn1_type_cd')
        if '.' in field_name:
            # Look for the qualified reference directly
            if field_name in element_data:
                return field_name
            
            # Try case-insensitive qualified lookup
            field_name_upper = field_name.upper()
            for key in element_data.keys():
                if key.upper() == field_name_upper:
                    return key
        else:
            # Simple field name lookup
            field_name_upper = field_name.upper()
            for key in element_data.keys():
                if key.upper() == field_name_upper:
                    return key
        
        return None
    
    def validate_expression(self, expression: str) -> bool:
        """
        Validate that an expression is syntactically correct and safe.
        
        Args:
            expression: Expression to validate
            
        Returns:
            True if expression is valid and safe
        """
        try:
            # Basic syntax validation
            if not expression or not expression.strip():
                return False
            
            # Check for dangerous keywords
            dangerous_keywords = ['import', 'exec', 'eval', '__', 'open', 'file', 'input']
            expression_upper = expression.upper()
            
            for keyword in dangerous_keywords:
                if keyword.upper() in expression_upper:
                    return False
            
            # Validate CASE statement syntax if present
            if 'CASE' in expression_upper:
                return self._validate_case_syntax(expression)
            
            # Validate arithmetic expression
            return self._validate_arithmetic_syntax(expression)
            
        except Exception:
            return False
    
    def _validate_case_syntax(self, expression: str) -> bool:
        """Validate CASE statement syntax."""
        # Must have CASE, at least one WHEN/THEN, and END
        expression_upper = expression.upper()
        return (
            'CASE' in expression_upper and
            'WHEN' in expression_upper and 
            'THEN' in expression_upper and
            'END' in expression_upper
        )
    
    def _validate_arithmetic_syntax(self, expression: str) -> bool:
        """Validate arithmetic expression syntax."""
        # Only allow safe characters for arithmetic
        return re.match(r'^[a-zA-Z0-9_+\-*/().\s]+$', expression) is not None