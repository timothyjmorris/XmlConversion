"""
Unit tests to diagnose why calculated_field CASE/LIKE expressions fail.

This tests the CalculatedFieldEngine's ability to evaluate SQL-style CASE/LIKE
expressions that are used in the check_requested_by_user field mapping.
"""

import pytest
from pathlib import Path
from xml_extractor.mapping.calculated_field_engine import CalculatedFieldEngine


class TestCalculatedFieldCaseLike:
    """Diagnostic tests for CASE/LIKE expression evaluation."""

    @pytest.fixture
    def engine(self):
        """Create CalculatedFieldEngine instance."""
        return CalculatedFieldEngine()

    def test_simple_case_exact_match(self, engine):
        """Test CASE with exact equality (should work)."""
        expression = "CASE WHEN chk_requested_by = 'WENDY' THEN 'WENDY.DOTSON@MERRICKBANK.COM' END"
        context = {"chk_requested_by": "WENDY"}
        
        result = engine.evaluate_expression(expression, context, "test_field")
        
        assert result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected email, got {result}"

    def test_simple_case_like_pattern(self, engine):
        """Test CASE with LIKE pattern - THIS IS THE FAILING CASE."""
        expression = "CASE WHEN chk_requested_by LIKE '%WENDY%' THEN 'WENDY.DOTSON@MERRICKBANK.COM' END"
        context = {"chk_requested_by": "WENDY"}
        
        result = engine.evaluate_expression(expression, context, "test_field")
        
        # This will likely fail - LIKE is SQL-specific, not Python
        assert result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected email, got {result}"

    def test_case_like_with_surrounding_text(self, engine):
        """Test LIKE with text before/after match."""
        expression = "CASE WHEN chk_requested_by LIKE '%WENDY%' THEN 'WENDY.DOTSON@MERRICKBANK.COM' END"
        context = {"chk_requested_by": "THE WENDY PERSON"}
        
        result = engine.evaluate_expression(expression, context, "test_field")
        
        assert result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected email for partial match, got {result}"

    def test_real_rl_contract_expression(self, engine):
        """Test the actual expression from RL contract check_requested_by_user."""
        # This is the EXACT expression from the contract
        expression = (
            "CASE "
            "WHEN chk_requested_by LIKE '%WENDY%' OR chk_requested_by LIKE '%DOTSON%' THEN 'WENDY.DOTSON@MERRICKBANK.COM' "
            "WHEN chk_requested_by LIKE '%POTEZ%' THEN 'ALYSSA.RAPOTEZ@MERRICKBANK.COM' "
            "WHEN chk_requested_by LIKE '%ANGIE%' THEN 'ANGIE.HAYS@MERRICKBANK.COM' "
            "WHEN chk_requested_by LIKE '%ASHLEY%' OR chk_requested_by LIKE '%HAASE%' THEN 'ASHLEY.HAASE@MERRICKBANK.COM' "
            "END"
        )
        
        # Test with "WENDY"
        context = {"chk_requested_by": "WENDY"}
        result = engine.evaluate_expression(expression, context, "check_requested_by_user")
        assert result == "WENDY.DOTSON@MERRICKBANK.COM", f"Expected WENDY email, got {result}"
        
        # Test with "ASHLEY"
        context = {"chk_requested_by": "ASHLEY"}
        result = engine.evaluate_expression(expression, context, "check_requested_by_user")
        assert result == "ASHLEY.HAASE@MERRICKBANK.COM", f"Expected ASHLEY email, got {result}"

    def test_case_with_python_in_operator(self, engine):
        """Test if we can use Python 'in' operator instead of SQL LIKE."""
        expression = "CASE WHEN 'WENDY' in chk_requested_by THEN 'WENDY.DOTSON@MERRICKBANK.COM' END"
        context = {"chk_requested_by": "WENDY"}
        
        result = engine.evaluate_expression(expression, context, "test_field")
        
        # This might work if engine supports Python expressions
        print(f"Result with 'in' operator: {result}")

    def test_diagnose_expression_type(self, engine):
        """Understand what the engine actually does with expressions."""
        expression = "CASE WHEN chk_requested_by LIKE '%WENDY%' THEN 'EMAIL' END"
        context = {"chk_requested_by": "WENDY"}
        
        # Add debug logging
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        result = engine.evaluate_expression(expression, context, "test_field")
        
        print(f"\nExpression: {expression}")
        print(f"Context: {context}")
        print(f"Result: {result}")
        print(f"Result type: {type(result)}")
