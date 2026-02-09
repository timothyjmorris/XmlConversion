"""
Unit tests for validating that all expression keywords used in mapping contracts are supported.

This test prevents runtime errors by ensuring all functions and operators used in 
calculated_field expressions are implemented in the CalculatedFieldEngine.
"""

import json
import re
import pytest
from pathlib import Path


class TestExpressionKeywordValidation:
    """Validate all expression keywords in mapping contracts are supported."""
    
    # Supported keywords and functions in CalculatedFieldEngine
    SUPPORTED_KEYWORDS = {
        # SQL keywords
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
        'AND', 'OR', 'NOT',
        'IS', 'NULL', 'EMPTY',
        'LIKE',
        
        # Functions
        'DATE',      # DATE('yyyy-mm-dd') for date parsing
        'DATEADD',   # DATEADD(day, number, date_field) for date arithmetic
    }
    
    # Unsupported keywords that should trigger warnings
    KNOWN_UNSUPPORTED = {
        'ADDDAYS',   # Replaced by DATEADD
        'DATEDIFF',  # Not yet implemented
        'DATEPART',  # Not yet implemented  
        'SUBSTRING', # Not yet implemented
        'CONCAT',    # Not yet implemented
        'IN',        # Not yet implemented
        'COALESCE',  # Not yet implemented
        'ISNULL',    # Not yet implemented (use IS NULL instead)
    }
    
    @pytest.fixture
    def mapping_contracts(self):
        """Load both CC and RL mapping contracts."""
        config_dir = Path(__file__).parent.parent.parent / 'config'
        contracts = {}
        
        cc_path = config_dir / 'mapping_contract.json'
        rl_path = config_dir / 'mapping_contract_rl.json'
        
        if cc_path.exists():
            with open(cc_path, 'r', encoding='utf-8') as f:
                contracts['CC'] = json.load(f)
        
        if rl_path.exists():
            with open(rl_path, 'r', encoding='utf-8') as f:
                contracts['RL'] = json.load(f)
        
        return contracts
    
    def extract_function_calls(self, expression: str) -> set:
        """Extract all function calls from an expression.
        
        Returns: Set of function names (uppercase)
        
        Examples:
            'DATE("2023-01-01")' -> {'DATE'}
            'DATEADD(day, 30, app_date)' -> {'DATEADD'}
            'CASE WHEN x > 0 THEN y END' -> {'CASE'}
        """
        # Pattern to match function calls: WORD(
        pattern = r'\b([A-Z_]+)\s*\('
        matches = re.findall(pattern, expression.upper())
        return set(matches)
    
    def extract_keywords(self, expression: str) -> set:
        """Extract SQL keywords from an expression.
        
        Returns: Set of keywords (uppercase)
        
        Examples:
            'CASE WHEN x > 0 THEN y ELSE z END' -> {'CASE', 'WHEN', 'THEN', 'ELSE', 'END'}
            'field IS NOT EMPTY' -> {'IS', 'NOT', 'EMPTY'}
        """
        # Split by common delimiters and operators
        words = re.findall(r'\b[A-Z_]+\b', expression.upper())
        
        # Filter to known SQL keywords
        keywords = set()
        for word in words:
            if word in self.SUPPORTED_KEYWORDS or word in self.KNOWN_UNSUPPORTED:
                keywords.add(word)
        
        return keywords
    
    def test_all_expressions_use_supported_keywords(self, mapping_contracts):
        """Verify all calculated_field expressions use only supported keywords and functions."""
        unsupported_usage = []
        
        for contract_name, contract_data in mapping_contracts.items():
            mappings = contract_data.get('mappings', [])
            
            for mapping in mappings:
                # Only check calculated_field mappings
                if 'calculated_field' not in mapping.get('mapping_type', []):
                    continue
                
                expression = mapping.get('expression', '')
                if not expression:
                    continue
                
                target_column = mapping.get('target_column', 'unknown')
                target_table = mapping.get('target_table', 'unknown')
                
                # Extract functions and keywords
                functions = self.extract_function_calls(expression)
                keywords = self.extract_keywords(expression)
                
                # Check for unsupported items
                all_used = functions | keywords
                unsupported = all_used - self.SUPPORTED_KEYWORDS
                
                # Report any unsupported usage
                for item in unsupported:
                    unsupported_usage.append({
                        'contract': contract_name,
                        'table': target_table,
                        'column': target_column,
                        'unsupported_keyword': item,
                        'expression': expression[:100]  # First 100 chars
                    })
        
        # Assert no unsupported keywords found
        if unsupported_usage:
            error_msg = "\n\nUnsupported keywords/functions found in expressions:\n"
            for item in unsupported_usage:
                error_msg += f"\n{item['contract']} - {item['table']}.{item['column']}"
                error_msg += f"\n  Unsupported: {item['unsupported_keyword']}"
                error_msg += f"\n  Expression: {item['expression']}...\n"
            
            pytest.fail(error_msg)
    
    def test_dateadd_replaces_adddays(self, mapping_contracts):
        """Verify ADDDAYS has been replaced with DATEADD everywhere."""
        adddays_usage = []
        
        for contract_name, contract_data in mapping_contracts.items():
            mappings = contract_data.get('mappings', [])
            
            for mapping in mappings:
                expression = mapping.get('expression', '')
                if not expression:
                    continue
                
                # Check for ADDDAYS usage (case-insensitive)
                if re.search(r'\bADDDAYS\s*\(', expression, re.IGNORECASE):
                    target_column = mapping.get('target_column', 'unknown')
                    target_table = mapping.get('target_table', 'unknown')
                    adddays_usage.append({
                        'contract': contract_name,
                        'table': target_table,
                        'column': target_column,
                        'expression': expression[:100]
                    })
        
        # Assert ADDDAYS is not used
        if adddays_usage:
            error_msg = "\n\nADDDAYS() found in expressions (should use DATEADD()):\n"
            for item in adddays_usage:
                error_msg += f"\n{item['contract']} - {item['table']}.{item['column']}"
                error_msg += f"\n  Expression: {item['expression']}...\n"
            
            pytest.fail(error_msg)
    
    def test_mapping_contracts_exist(self, mapping_contracts):
        """Verify at least one mapping contract was loaded."""
        assert len(mapping_contracts) > 0, "No mapping contracts found"
        assert 'CC' in mapping_contracts or 'RL' in mapping_contracts, \
            "Expected CC or RL mapping contract"
    
    def test_expression_count(self, mapping_contracts):
        """Report number of calculated_field expressions in each contract."""
        for contract_name, contract_data in mapping_contracts.items():
            mappings = contract_data.get('mappings', [])
            calc_fields = [m for m in mappings if 'calculated_field' in m.get('mapping_type', [])]
            
            # This is informational, not a failure
            print(f"\n{contract_name}: {len(calc_fields)} calculated_field expressions")
            
            # Count unique functions used
            functions_used = set()
            for mapping in calc_fields:
                expr = mapping.get('expression', '')
                functions_used.update(self.extract_function_calls(expr))
            
            print(f"  Functions used: {sorted(functions_used)}")
