"""
HTML processing utilities for SEC filing parsers.

This module provides common HTML processing functionality that can be shared
across different parser types (HTML, XBRL, etc.).
"""

import re
from bs4 import BeautifulSoup
from typing import Optional
from .text_utils import clean_unicode_text


def extract_text_from_html(html_content: str, separator: str = ' ', strip: bool = True) -> str:
    """
    Extract clean text from HTML content using BeautifulSoup.
    
    Args:
        html_content: Raw HTML content
        separator: Separator to use between text elements
        strip: Whether to strip whitespace from the result
        
    Returns:
        Clean text extracted from HTML
    """
    if not html_content:
        return ''
    
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator=separator, strip=strip)


def remove_html_tags(html_content: str) -> str:
    """
    Remove HTML tags while preserving text content.
    
    Args:
        html_content: HTML content with tags to remove
        
    Returns:
        Text content with HTML tags removed
    """
    if not html_content:
        return ''
    
    # Use regex as a backup for simple tag removal
    cleaned = re.sub(r'<[^>]+>', '', html_content)
    return cleaned


def clean_html_text(text: str, strip_trailing_punctuation: bool = False) -> str:
    """
    Clean HTML text using BeautifulSoup and unidecode for robust Unicode handling.
    
    This is the main function that combines HTML processing with text normalization.
    It handles:
    1. HTML entities and tags via BeautifulSoup
    2. Unicode normalization via unidecode
    3. Whitespace normalization
    4. Optional punctuation stripping
    
    Args:
        text: Raw HTML text that may contain HTML entities and Unicode characters
        strip_trailing_punctuation: If True, removes trailing commas and periods
        
    Returns:
        Clean ASCII text suitable for data processing
    """
    if not text:
        return text
    
    # Use BeautifulSoup to properly handle HTML entities and tags
    # This converts &nbsp; to \xa0, &amp; to &, removes HTML tags, etc.
    cleaned = extract_text_from_html(text, separator=' ', strip=True)
    
    # Use our text utilities for Unicode normalization
    cleaned = clean_unicode_text(cleaned)
    
    # Strip leading/trailing whitespace and optionally punctuation
    if strip_trailing_punctuation:
        cleaned = cleaned.strip(' ,.')
    else:
        cleaned = cleaned.strip()
    
    return cleaned


def get_dei_value(soup: BeautifulSoup, dei_name: str, strip_trailing_punctuation: bool = False) -> Optional[str]:
    """
    Extract DEI (Document Entity Information) value from XBRL soup with continuation support.
    
    This function handles XBRL-specific extraction where content may be split across
    multiple elements using continuedat attributes.
    
    Args:
        soup: BeautifulSoup object of the XBRL document
        dei_name: The DEI name to search for (e.g., "dei:EntityRegistrantName")
        
    Returns:
        Clean text content or None if not found
    """
    # Try both case variations of the tag name
    tag = soup.find("ix:nonnumeric", attrs={"name": dei_name})
    if not tag:
        tag = soup.find("ix:nonNumeric", attrs={"name": dei_name})
    if not tag:
        return None
    
    # Start with the initial tag's text (preserve leading/trailing whitespace for now)
    full_text = tag.get_text()
    
    # Check if this tag has a continuedat attribute
    continuedat_id = tag.get('continuedat')
    
    # Follow the continuation chain
    while continuedat_id:
        # Find the continuation element by its id
        continuation_tag = soup.find("ix:continuation", attrs={"id": continuedat_id})
        if not continuation_tag:
            break
        
        # Append the continuation text (preserve whitespace)
        continuation_text = continuation_tag.get_text()
        if continuation_text:
            full_text += continuation_text
        
        # Check if this continuation has its own continuedat attribute
        continuedat_id = continuation_tag.get('continuedat')
    
    # Clean the text using our centralized cleaning function
    return clean_html_text(full_text, strip_trailing_punctuation=strip_trailing_punctuation) if full_text else None


def safe_strip(value, strip_punctuation: bool = False) -> str:
    """
    Safely strip a value, handling None/null values and HTML entities.
    
    Args:
        value: Value to clean (may be None)
        strip_punctuation: Whether to strip trailing punctuation
        
    Returns:
        Clean string (empty string if input was None)
    """
    if value is None:
        return ''
    # Convert to string, clean HTML entities and Unicode, then strip
    return clean_html_text(str(value), strip_trailing_punctuation=strip_punctuation)
