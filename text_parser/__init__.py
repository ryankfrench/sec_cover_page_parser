"""
Text Parser Package

Intelligent document parsing library for extracting structured information from
text, markdown, and HTML documents. Uses advanced NLP techniques including
spaCy and transformers for entity recognition and extraction.

Main classes:
- UnifiedDocumentParser: Single interface for all document types
- MarkdownCoverPageParser: Specialized markdown parser
- EnhancedTextCoverPageParser: Advanced text parser  
- HTMLCoverPageParser: DOM-aware HTML parser
- BaseIntelligentParser: Base class with NLP capabilities

Example usage:
    from text_parser import UnifiedDocumentParser
    
    parser = UnifiedDocumentParser()
    result = parser.parse_document(content)
    print(f"Company: {result.company_name}")
    print(f"Address: {result.address}")
"""

# Import main classes for easy access
from .unified_document_parser import (
    UnifiedDocumentParser,
    DocumentFormat,
    ParsedDocument
)

from .base_intelligent_parser import (
    BaseIntelligentParser,
    ParsedInformation,
    ExtractedEntity
)

from .markdown_cover_page_parser import MarkdownCoverPageParser
from .enhanced_txt_cover_page_parser import EnhancedTextCoverPageParser  
from .html_cover_page_parser import HTMLCoverPageParser

# Version info
__version__ = "1.0.0"
__author__ = "AI Assistant"
__description__ = "Intelligent document parsing library for structured information extraction"

# Define what gets imported with "from text_parser import *"
__all__ = [
    "UnifiedDocumentParser",
    "DocumentFormat", 
    "ParsedDocument",
    "BaseIntelligentParser",
    "ParsedInformation",
    "ExtractedEntity",
    "MarkdownCoverPageParser",
    "EnhancedTextCoverPageParser",
    "HTMLCoverPageParser"
] 