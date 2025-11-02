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
        Extract ALL numeric characters from text (aggressive mode), converting to integer.
        Used for explicit extract_numeric mapping type.
        
        Examples:
            'Up to $40' -> 40
            '(555) 555-5555' -> 5555555555
            '664-50-2346' -> 66450234
        
        Args:
            text: Input text
            
        Returns:
            Integer from all numeric characters found, or None if no numbers found
        """
        if not text:
            return None
        
        # Extract all numeric digits from the string
        digits_only = StringUtils.extract_numbers_only(text)
        
        if digits_only:
            try:
                return int(digits_only)
            except ValueError:
                return None
        return None
    
    @staticmethod
    def extract_numeric_value_preserving_decimals(text: str) -> Optional[float]:
        """
        Extract numeric value from text while preserving decimal structure.
        Used for auto-extraction when no mapping_type is specified.
        
        This extracts the FIRST numeric sequence, preserving the decimal point.
        Examples:
            '36.50' -> 36.50
            'Price: $36.50' -> 36.50
            'Up to $40' -> 40.0
        
        Args:
            text: Input text
            
        Returns:
            Float from first numeric sequence found, or None if no numbers found
        """
        if not text:
            return None
        
        # Match the first sequence of digits with optional decimal point
        # Allows: 123, 123.45, .45
        match = StringUtils._regex_cache['numeric_extract'].search(str(text))
        if match:
            try:
                # Get the first digit sequence
                first_num = match.group()
                # Now look for a decimal point that might follow immediately
                start_pos = match.end()
                remaining = str(text)[start_pos:]
                if remaining.startswith('.'):
                    # Check if there are more digits after the decimal
                    after_decimal = remaining[1:]
                    if after_decimal and after_decimal[0].isdigit():
                        # Extract the decimal number
                        decimal_match = re.match(r'\.(\d+)', remaining)
                        if decimal_match:
                            full_number = first_num + '.' + decimal_match.group(1)
                            return float(full_number)
                # No decimal part found, return as float
                return float(first_num)
            except (ValueError, AttributeError):
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