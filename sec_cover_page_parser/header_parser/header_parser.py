"""
SEC SGML Header Parser

This module provides functionality to parse SEC SGML header files (.hdr.sgml)
that contain structured filing information. Unlike HTML/XML, SGML allows for
optional closing tags and more flexible syntax.

The parser handles the hierarchical structure of SEC SGML headers and extracts
key filing information such as company data, filing values, and addresses.
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from ..models.filing_data import FilingData
from ..models.address import Address, AddressType
from ..models.company import Company


@dataclass
class SGMLNode:
    """Represents a node in the SGML document tree."""
    tag: str
    content: str
    children: List['SGMLNode']
    parent: Optional['SGMLNode'] = None
    
    def find_child(self, tag: str) -> Optional['SGMLNode']:
        """Find the first child with the given tag name."""
        for child in self.children:
            if child.tag.upper() == tag.upper():
                return child
        return None
    
    def find_all_children(self, tag: str) -> List['SGMLNode']:
        """Find all children with the given tag name."""
        return [child for child in self.children if child.tag.upper() == tag.upper()]
    
    def get_text_content(self) -> str:
        """Get the text content of this node, excluding child nodes."""
        return self.content.strip()


class SGMLParser:
    """
    A specialized SGML parser for SEC filing headers.
    
    This parser handles the specific quirks of SEC SGML format:
    - Optional closing tags
    - Hierarchical structure
    - Mixed content (text and nested tags)
    """
    
    def __init__(self):
        self.root = None
        self._tag_stack: List[SGMLNode] = []
    
    def parse(self, sgml_content: str) -> SGMLNode:
        """
        Parse SGML content and return the root node.
        
        Args:
            sgml_content: The SGML content as a string
            
        Returns:
            SGMLNode: The root node of the parsed document
        """
        # Clean up the content
        content = self._preprocess_content(sgml_content)
        
        # Tokenize the content
        tokens = self._tokenize(content)
        
        # Build the document tree
        self.root = self._build_tree(tokens)
        
        return self.root
    
    def _preprocess_content(self, content: str) -> str:
        """Preprocess the SGML content to normalize it."""
        # Remove any leading/trailing whitespace
        content = content.strip()
        
        # Normalize line endings
        content = re.sub(r'\r\n|\r', '\n', content)
        
        return content
    
    def _tokenize(self, content: str) -> List[Tuple[str, str]]:
        """
        Tokenize SGML content into (token_type, value) pairs.
        
        Returns:
            List of tuples where each tuple is (token_type, value)
            token_type can be 'open_tag', 'close_tag', or 'text'
        """
        tokens = []
        
        # Pattern to match SGML tags
        tag_pattern = r'<(/?)([A-Z0-9-]+)(?:\s+[^>]*)?>'
        
        last_end = 0
        
        for match in re.finditer(tag_pattern, content):
            # Add any text before this tag
            if match.start() > last_end:
                text = content[last_end:match.start()].strip()
                if text:
                    tokens.append(('text', text))
            
            # Add the tag
            is_closing = bool(match.group(1))
            tag_name = match.group(2)
            
            if is_closing:
                tokens.append(('close_tag', tag_name))
            else:
                tokens.append(('open_tag', tag_name))
            
            last_end = match.end()
        
        # Add any remaining text
        if last_end < len(content):
            text = content[last_end:].strip()
            if text:
                tokens.append(('text', text))
        
        return tokens
    
    def _build_tree(self, tokens: List[Tuple[str, str]]) -> SGMLNode:
        """Build the document tree from tokens."""
        root = None
        current_node = None
        node_stack = []
        
        # Define hierarchical relationships for SEC SGML
        # Child tags that should be nested under their parent
        nested_tags = {
            'SEC-HEADER': ['ACCEPTANCE-DATETIME', 'ACCESSION-NUMBER', 'TYPE', 'PUBLIC-DOCUMENT-COUNT', 
                          'PERIOD', 'ITEMS', 'FILING-DATE', 'DATE-OF-FILING-DATE-CHANGE', 'FILER'],
            'FILER': ['COMPANY-DATA', 'FILING-VALUES', 'BUSINESS-ADDRESS', 'MAIL-ADDRESS', 'FORMER-COMPANY'],
            'COMPANY-DATA': ['CONFORMED-NAME', 'CIK', 'ASSIGNED-SIC', 'ORGANIZATION-NAME', 'IRS-NUMBER', 
                           'STATE-OF-INCORPORATION', 'FISCAL-YEAR-END'],
            'FILING-VALUES': ['FORM-TYPE', 'ACT', 'FILE-NUMBER', 'FILM-NUMBER'],
            'BUSINESS-ADDRESS': ['STREET1', 'STREET2', 'CITY', 'STATE', 'ZIP', 'PHONE'],
            'MAIL-ADDRESS': ['STREET1', 'STREET2', 'CITY', 'STATE', 'ZIP'],
            'FORMER-COMPANY': ['FORMER-CONFORMED-NAME', 'DATE-CHANGED']
        }
        
        for token_type, value in tokens:
            if token_type == 'open_tag':
                # Create new node
                new_node = SGMLNode(tag=value, content='', children=[], parent=current_node)
                
                if current_node is None:
                    # This is the root node
                    root = new_node
                    current_node = new_node
                else:
                    # Check if this tag should be a child of current node or a sibling
                    current_tag = current_node.tag.upper()
                    new_tag = value.upper()
                    
                    # If current node can contain this tag, add as child
                    if current_tag in nested_tags and new_tag in nested_tags[current_tag]:
                        current_node.children.append(new_node)
                        new_node.parent = current_node
                        node_stack.append(current_node)
                        current_node = new_node
                    else:
                        # This should be a sibling - pop up until we find the right parent
                        while node_stack:
                            parent = node_stack[-1]
                            if parent.tag.upper() in nested_tags and new_tag in nested_tags[parent.tag.upper()]:
                                # Found the right parent
                                current_node = node_stack.pop()
                                current_node.children.append(new_node)
                                new_node.parent = current_node
                                node_stack.append(current_node)
                                current_node = new_node
                                break
                            else:
                                node_stack.pop()
                        else:
                            # No suitable parent found, add as sibling to current
                            if current_node.parent:
                                current_node.parent.children.append(new_node)
                                new_node.parent = current_node.parent
                                current_node = new_node
                            else:
                                # Add as child to current (fallback)
                                current_node.children.append(new_node)
                                new_node.parent = current_node
                                node_stack.append(current_node)
                                current_node = new_node
                
            elif token_type == 'close_tag':
                # Pop back to parent node if we have a matching open tag
                if node_stack and current_node and current_node.tag.upper() == value.upper():
                    current_node = node_stack.pop()
                
            elif token_type == 'text':
                # Add text content to current node
                if current_node is not None:
                    if current_node.content:
                        current_node.content += '\n' + value
                    else:
                        current_node.content = value
        
        return root or SGMLNode(tag='ROOT', content='', children=[])


class SECSGMLParser:
    """
    Specialized parser for SEC SGML header files.
    
    This class provides high-level methods to extract structured data
    from SEC filing headers in SGML format.
    """
    
    def __init__(self):
        self.parser = SGMLParser()
    
    def parse_header_file(self, sgml_content: str) -> FilingData:
        """
        Parse a SEC SGML header file and extract filing data.
        
        Args:
            sgml_content: The content of the .hdr.sgml file
            
        Returns:
            FilingData: Structured filing information
        """
        # Parse the SGML content
        root = self.parser.parse(sgml_content)
        
        # Initialize result
        result = FilingData()
        
        # Find the SEC-HEADER node (should be root or first child)
        sec_header = root if root.tag.upper() == 'SEC-HEADER' else root.find_child('SEC-HEADER')
        
        if not sec_header:
            return result
        
        # Extract basic filing information
        self._extract_basic_info(sec_header, result)
        
        # Find and process FILER section
        filer_node = sec_header.find_child('FILER')
        if filer_node:
            company = self._extract_filer_info(filer_node)
            if company:
                result.add_company(company)
                result.populate_legacy_fields()
        
        return result
    
    def _extract_basic_info(self, sec_header: SGMLNode, result: FilingData) -> None:
        """Extract basic filing information from SEC-HEADER."""
        # Accession number
        accession_node = sec_header.find_child('ACCESSION-NUMBER')
        if accession_node:
            result.accession_number = accession_node.get_text_content()
        
        # Form type
        type_node = sec_header.find_child('TYPE')
        if type_node:
            result.form = type_node.get_text_content()
        
        # Filing date (use PERIOD if available, otherwise FILING-DATE)
        period_node = sec_header.find_child('PERIOD')
        if period_node:
            result.date = self._format_date(period_node.get_text_content())
        else:
            filing_date_node = sec_header.find_child('FILING-DATE')
            if filing_date_node:
                result.date = self._format_date(filing_date_node.get_text_content())
    
    def _extract_filer_info(self, filer_node: SGMLNode) -> Optional[Company]:
        """Extract filer information from FILER section."""
        company = Company()
        
        # Company data
        company_data = filer_node.find_child('COMPANY-DATA')
        if company_data:
            self._extract_company_data(company_data, company)
        
        # Filing values
        filing_values = filer_node.find_child('FILING-VALUES')
        if filing_values:
            self._extract_filing_values(filing_values, company)
        
        # Business address
        business_address = filer_node.find_child('BUSINESS-ADDRESS')
        if business_address:
            address = self._extract_address(business_address, AddressType.BUSINESS)
            if address:
                company.add_address(address)
        
        # Mail address
        mail_address = filer_node.find_child('MAIL-ADDRESS')
        if mail_address:
            address = self._extract_address(mail_address, AddressType.MAILING)
            if address:
                company.add_address(address)
        
        return company if company.company_name else None
    
    def _extract_company_data(self, company_data: SGMLNode, company: Company) -> None:
        """Extract company information."""
        # Company name
        name_node = company_data.find_child('CONFORMED-NAME')
        if name_node:
            company.company_name = name_node.get_text_content()
        
        # CIK
        cik_node = company_data.find_child('CIK')
        if cik_node:
            company.cik = cik_node.get_text_content()
        
        # IRS number
        irs_node = company_data.find_child('IRS-NUMBER')
        if irs_node:
            company.irs_number = irs_node.get_text_content()
        
        # State of incorporation
        state_node = company_data.find_child('STATE-OF-INCORPORATION')
        if state_node:
            company.state_of_incorporation = state_node.get_text_content()
    
    def _extract_filing_values(self, filing_values: SGMLNode, company: Company) -> None:
        """Extract filing values information."""
        # Commission file number
        file_number_node = filing_values.find_child('FILE-NUMBER')
        if file_number_node:
            company.commission_file_number = file_number_node.get_text_content()
    
    def _extract_address(self, address_node: SGMLNode, address_type: AddressType) -> Optional[Address]:
        """Extract address information."""
        address = Address(address_type=address_type)
        
        # Street address
        street1_node = address_node.find_child('STREET1')
        if street1_node:
            address.address_line1 = street1_node.get_text_content()
        
        street2_node = address_node.find_child('STREET2')
        if street2_node:
            address.address_line2 = street2_node.get_text_content()
        
        # City
        city_node = address_node.find_child('CITY')
        if city_node:
            address.city = city_node.get_text_content()
        
        # State
        state_node = address_node.find_child('STATE')
        if state_node:
            address.state = state_node.get_text_content()
        
        # ZIP
        zip_node = address_node.find_child('ZIP')
        if zip_node:
            address.zip_code = zip_node.get_text_content()
        
        # Return address only if it has at least some content
        if any([address.address_line1, address.city, address.state, address.zip_code]):
            return address
        return None
    
    def _format_date(self, date_str: str) -> str:
        """Format date from YYYYMMDD to a more readable format."""
        if len(date_str) == 8 and date_str.isdigit():
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{month}/{day}/{year}"
        return date_str


def parse_sgml_header(sgml_content: str) -> FilingData:
    """
    Convenience function to parse SEC SGML header content.
    
    Args:
        sgml_content: The content of a .hdr.sgml file
        
    Returns:
        FilingData: Structured filing information
    """
    parser = SECSGMLParser()
    return parser.parse_header_file(sgml_content)


def parse_sgml_header_file(file_path: str) -> FilingData:
    """
    Parse a SEC SGML header file from disk.
    
    Args:
        file_path: Path to the .hdr.sgml file
        
    Returns:
        FilingData: Structured filing information
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return parse_sgml_header(content)