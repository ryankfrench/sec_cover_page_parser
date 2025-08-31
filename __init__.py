"""
SEC Cover Page Parser

A package for parsing SEC filing cover pages from XBRL documents, HTML, and text formats.
"""

# Import version from setup.py
try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

# Import main functionality for easy access
from xbrl_parser.xbrl_cover_page_parser import parse_coverpage, has_xbrl, DocumentEntityInformation
from text_parser import UnifiedDocumentParser, DocumentFormat
from models.filing_data import FilingData
from models.address import Address, AddressType

__author__ = "Ryan French"
__email__ = "rfrench@chapman.edu"

__all__ = [
    'parse_coverpage',
    'has_xbrl', 
    'DocumentEntityInformation',
    'UnifiedDocumentParser',
    'DocumentFormat',
    'FilingData',
    'Address',
    'AddressType'
]
