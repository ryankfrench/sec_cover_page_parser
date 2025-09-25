"""
Text processing utilities for SEC filing parsers.

This module provides text normalization and cleaning functionality that can be
shared across different parser types.
"""

import re
from unidecode import unidecode
from typing import Optional


def clean_unicode_text(text: str) -> str:
    """
    Convert Unicode text to clean ASCII using unidecode.
    
    This function handles all Unicode characters robustly, converting them to
    their ASCII equivalents. Examples:
    - \xa0 (non-breaking space) → regular space
    - é → e, ñ → n, ü → u
    - © → (c), ™ → (tm), ® → (r)
    - — → --, – → -, " → ", ' → '
    
    Args:
        text: Text that may contain Unicode characters
        
    Returns:
        ASCII-only text with Unicode characters converted to equivalents
    """
    if not text:
        return text
    
    # Use unidecode to convert ALL Unicode to ASCII equivalents
    return unidecode(text)


def normalize_whitespace(text: str) -> str:
    """
    Normalize all whitespace in text to single spaces.
    
    This collapses multiple spaces, tabs, newlines, and other whitespace
    characters into single spaces.
    
    Args:
        text: Text with potentially irregular whitespace
        
    Returns:
        Text with normalized whitespace
    """
    if not text:
        return text
    
    # Normalize whitespace (multiple spaces, tabs, newlines → single space)
    return re.sub(r'\s+', ' ', text)


def normalize_text(text: str, strip_trailing_punctuation: bool = False) -> str:
    """
    Comprehensive text normalization combining Unicode cleaning and whitespace normalization.
    
    This is the main text cleaning function that:
    1. Converts Unicode to ASCII
    2. Normalizes whitespace
    3. Optionally strips trailing punctuation
    
    Args:
        text: Raw text to normalize
        strip_trailing_punctuation: If True, removes trailing commas and periods
        
    Returns:
        Clean, normalized ASCII text
    """
    if not text:
        return text
    
    # Convert Unicode to ASCII
    cleaned = clean_unicode_text(text)
    
    # Normalize whitespace
    cleaned = normalize_whitespace(cleaned)
    
    # Strip leading/trailing whitespace and optionally punctuation
    if strip_trailing_punctuation:
        cleaned = cleaned.strip(' ,.')
    else:
        cleaned = cleaned.strip()
    
    return cleaned


def clean_field_value(value, strip_punctuation: bool = False) -> str:
    """
    Clean a field value that might be None, with optional punctuation stripping.
    
    This is a utility function for cleaning individual field values extracted
    from documents.
    
    Args:
        value: Field value to clean (may be None)
        strip_punctuation: Whether to strip trailing punctuation
        
    Returns:
        Clean string (empty string if input was None)
    """
    if value is None:
        return ''
    
    return normalize_text(str(value), strip_trailing_punctuation=strip_punctuation)
