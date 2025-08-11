"""
XBRL Parser Package

This package contains modules for parsing XBRL documents and extracting
SEC filing information from cover pages.
"""

from .xbrl_cover_page_parser import (
    parse_coverpage,
    has_xbrl,
    DocumentEntityInformation
)

__all__ = [
    'parse_coverpage',
    'has_xbrl', 
    'DocumentEntityInformation'
] 