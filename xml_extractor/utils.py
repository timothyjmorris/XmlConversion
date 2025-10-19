"""
Utility functions for common patterns across the XML extraction system.
"""

import re
from typing import Any, Optional


class StringUtils:
    """Utility methods for string validation and processing."""
    
    # Cached regex patterns for performance
    _regex_cache = {
        'numbers_only': re.compile(r'[^0-9]'),
        'numeric_extract': re.compile(r'\d+'),
        'whitespace': re.compile(r'\s+')
    }
    
    @staticmethod
    def safe_string_check(value: Any) -> bool:
        """
        Standardized string validation.
        
        Args:
            value: Value to check
            
        Returns:
            True if value is a non-empty string after stripping whitespace
        """
        return value is not None and str(value).strip() != ''
    
    @staticmethod
    def extract_numbers_only(value: Any) -> str:
        """
        Extract only numeric characters from value.
        
        Args:
            value: Input value
            
        Returns:
            String containing only numeric characters
        """
        if value is None:
            return ''
        return StringUtils._regex_cache['numbers_only'].sub('', str(value))
    
    @staticmethod
    def extract_numeric_value(text: str) -> Optional[int]:
        """
        Extract first numeric value from text like 'Up to $40' -> 40.
        
        Args:
            text: Input text
            
        Returns:
            First numeric value found, or None if no numbers found
        """
        if not text:
            return None
        
        match = StringUtils._regex_cache['numeric_extract'].search(str(text))
        if match:
            try:
                return int(match.group())
            except ValueError:
                return None
        return None
    
    @staticmethod
    def normalize_whitespace(value: Any) -> str:
        """
        Normalize whitespace in string values.
        
        Args:
            value: Input value
            
        Returns:
            String with normalized whitespace
        """
        if value is None:
            return ''
        return StringUtils._regex_cache['whitespace'].sub(' ', str(value).strip())


class ValidationUtils:
    """Utility methods for validation patterns."""
    
    @staticmethod
    def is_valid_identifier(value: Any, min_length: int = 1) -> bool:
        """
        Check if value is a valid identifier (non-empty after stripping).
        
        Args:
            value: Value to check
            min_length: Minimum required length
            
        Returns:
            True if value is a valid identifier
        """
        if not StringUtils.safe_string_check(value):
            return False
        return len(str(value).strip()) >= min_length
    
    @staticmethod
    def safe_int_conversion(value: Any, default: Optional[int] = None) -> Optional[int]:
        """
        Safely convert value to integer.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Integer value or default
        """
        if value is None:
            return default
        
        try:
            if isinstance(value, (int, float)):
                return int(value)
            return int(str(value).strip())
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_float_conversion(value: Any, default: Optional[float] = None) -> Optional[float]:
        """
        Safely convert value to float.
        
        Args:
            value: Value to convert
            default: Default value if conversion fails
            
        Returns:
            Float value or default
        """
        if value is None:
            return default
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value).strip())
        except (ValueError, TypeError):
            return default