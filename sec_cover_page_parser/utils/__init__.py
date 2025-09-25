"""
Shared utilities for SEC filing parsers.

This module provides common functionality used across different parser types:
- HTML processing and cleaning
- Text normalization and Unicode handling
- Common data extraction utilities
"""

from .html_utils import clean_html_text, extract_text_from_html, remove_html_tags
from .text_utils import normalize_text, clean_unicode_text, normalize_whitespace

__all__ = [
    'clean_html_text',
    'extract_text_from_html', 
    'remove_html_tags',
    'normalize_text',
    'clean_unicode_text',
    'normalize_whitespace'
]
