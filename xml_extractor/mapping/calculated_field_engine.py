"""
Calculated Field Engine for XML Database Extraction system.

Provides safe expression evaluation for calculated field mappings with
support for arithmetic operations and conditional logic. 
Expression can use SQL syntax for conditionals (CASE/WHEN/THEN/ELSE/END)

Examples for 'calculated_field' as a mapping_type in the mapping contract:
    "expression": "b_months_at_job + (b_years_at_job * 12)"
    "expression": "CASE WHEN b_salary_basis_tp_c = 'ANNUM' THEN b_salary / 12 WHEN b_salary_basis_tp_c = 'MONTH' THEN b_salary * 12 WHEN b_salary_basis_tp_c = 'HOURLY' THEN b_salary WHEN b_salary_basis_tp_c = '' THEN b_salary ELSE b_salary END"
"""

import re
import logging
from typing import Dict, Any, Optional, Union
from decimal import Decimal

from ..exceptions import DataTransformationError
from ..utils import ValidationUtils


class CalculatedFieldEngine:
    """
    Engine for evaluating calculated field expressions safely and efficiently.
    
    Supports:
    - Arithmetic operations: +, -, *, /
    - Conditional logic: CASE WHEN ... THEN ... ELSE ... END
    - Field references from the same XML element
    - Type-safe evaluation with proper error handling
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
        Evaluate a calculated field expression using data from the current XML element.
        
        Args:
            expression: The expression to evaluate (arithmetic or CASE statement)
            element_data: Dictionary of field values from the current XML element
            target_column: Name of the target column (for error reporting)
            
        Returns:
            Calculated value or None if evaluation fails
            
        Raises:
            DataTransformationError: If expression evaluation fails
        """
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
        
        for part in parts:  # Process all parts (first part is not empty after removing CASE keyword)
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
        
        # Evaluate WHEN conditions in order
        for condition, then_value in when_then_pairs:
            if self._evaluate_condition(condition, element_data):
                return self._evaluate_value_expression(then_value, element_data)
        
        # If no WHEN condition matched, use ELSE value
        if else_value:
            return self._evaluate_value_expression(else_value, element_data)
        
        # No condition matched and no ELSE clause
        return None
    
    def _evaluate_condition(self, condition: str, element_data: Dict[str, Any]) -> bool:
        """
        Evaluate a boolean condition (e.g., "b_salary_basis_tp_c = 'ANNUM'").
        
        Supports: =, !=, <, >, <=, >=, IS NULL, IS NOT NULL
        """
        condition = condition.strip()
        
        # Handle IS NULL / IS NOT NULL
        if 'IS NULL' in condition.upper():
            field_name = condition.upper().replace('IS NULL', '').strip()
            field_value = element_data.get(field_name)
            return field_value is None or field_value == ''
        
        if 'IS NOT NULL' in condition.upper():
            field_name = condition.upper().replace('IS NOT NULL', '').strip()
            field_value = element_data.get(field_name)
            return field_value is not None and field_value != ''
        
        # Handle comparison operators
        operators = ['!=', '<=', '>=', '=', '<', '>']
        
        for op in operators:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left_field = parts[0].strip()
                    right_value = parts[1].strip().strip("'\"")  # Remove quotes
                    
                    left_val = element_data.get(left_field, '')
                    
                    # Convert values for comparison
                    left_val_str = str(left_val) if left_val is not None else ''
                    right_val_str = str(right_value)
                    
                    # Perform comparison
                    if op == '=':
                        return left_val_str == right_val_str
                    elif op == '!=':
                        return left_val_str != right_val_str
                    elif op == '<':
                        return self._safe_numeric_compare(left_val, right_value, lambda x, y: x < y)
                    elif op == '>':
                        return self._safe_numeric_compare(left_val, right_value, lambda x, y: x > y)
                    elif op == '<=':
                        return self._safe_numeric_compare(left_val, right_value, lambda x, y: x <= y)
                    elif op == '>=':
                        return self._safe_numeric_compare(left_val, right_value, lambda x, y: x >= y)
                
                break
        
        return False
    
    def _safe_numeric_compare(self, left_val: Any, right_val: Any, compare_func) -> bool:
        """Safely compare numeric values with type conversion."""
        try:
            left_num = ValidationUtils.safe_float_conversion(left_val, 0.0)
            right_num = ValidationUtils.safe_float_conversion(right_val, 0.0)
            return compare_func(left_num, right_num)
        except (ValueError, TypeError):
            return False
    
    def _evaluate_value_expression(self, expression: str, element_data: Dict[str, Any]) -> Optional[Union[int, float, Decimal, str]]:
        """
        Evaluate a value expression (could be field name, literal, or arithmetic).
        """
        expression = expression.strip()
        
        # If it's a simple field reference
        if expression in element_data:
            return element_data[expression]
        
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
            # Add field values as variables
            **{k: ValidationUtils.safe_float_conversion(v, 0.0) 
               for k, v in element_data.items() if v is not None}
        }
        
        # Validate expression contains only safe characters
        if not re.match(r'^[a-zA-Z0-9_+\-*/().\s]+$', expression):
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