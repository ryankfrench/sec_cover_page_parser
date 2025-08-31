"""
Text Parser Package

Intelligent document parsing library for extracting structured information from
text, markdown, and HTML documents. Uses advanced NLP techniques including
spaCy and transformers for entity recognition and extraction.

Main classes:
- EnhancedTextCoverPageParser: Advanced text parser  

Example usage:
    from sec_cover_page_parser.text_parser import EnhancedTextCoverPageParser
    
    parser = EnhancedTextCoverPageParser()
    result = parser.parse_document(content)
    print(f"Company: {result.company_name}")
    print(f"Address: {result.address}")
"""

# Import main classes for easy access
from .txt_cover_page_parser import parse_txt_filing

# Version info
__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "Intelligent document parsing library for structured information extraction"

# Define what gets imported with "from text_parser import *"
__all__ = [
    "parse_txt_filing"
] 