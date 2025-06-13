from bs4 import BeautifulSoup
from typing import Dict, Optional, Union, List, Tuple
import re
import json
import math
from filing_data import FilingData
import column_parser
import boundary_parser as bp
import usaddress

def parse_xbrl_filing(file_content: str) -> FilingData:
    """
    Parse an XBRL-annotated SEC filing to extract key company information.
    First attempts to find direct <dei:tag> format, then falls back to ix:nonNumeric with name="dei:tag" format.
    
    Args:
        file_content (str): The content of the XBRL filing as a string
        
    Returns:
        FilingData: Object containing the parsed fields
    """
    # Initialize result object
    result = FilingData()
    
    # Define mapping of our keys to DEI tags
    dei_mapping = {
        'cik': 'EntityCentralIndexKey',
        'form': 'DocumentType',
        'date': 'DocumentPeriodEndDate',
        'company_name': 'EntityRegistrantName',
        'state_of_incorporation': 'EntityIncorporationStateCountryCode',
        'commission_file_number': 'EntityFileNumber',
        'irs_number': 'EntityTaxIdentificationNumber',
        'document_address': 'EntityAddressAddressLine1',
        'document_city': 'EntityAddressCityOrTown',
        'document_state': 'EntityAddressStateOrProvince',
        'document_zip': 'EntityAddressPostalZipCode',
        'trading_symbol': 'TradingSymbol',
        'exchange': 'SecurityExchangeName'
    }
    
    try:
        # Parse the document with lxml parser for better handling of malformed HTML
        soup = BeautifulSoup(file_content, 'html.parser')
        
        # Try both tag formats for each field
        for our_key, dei_tag in dei_mapping.items():
            value = None
            
            # Method 1: First try looking for direct dei: tags (usually at end of file)
            tag = soup.find(f'dei:{dei_tag.lower()}')
            if tag:
                value = tag.get_text(strip=True)
            
            # If not found, try inline XBRL formats
            if not value:
                # Method 2: Try to find tags using ix:nonNumeric or ix:nonFraction with name="dei:tag" format
                for tag_type in ['ix:nonnumeric', 'ix:nonfraction']:
                    tag = soup.find(tag_type, attrs={'name': f'dei:{dei_tag}'})
                    if tag:
                        value = tag.get_text(strip=True)
                        break
                
                # Method 3: As a last resort, try finding any tag with the dei: prefix in the name attribute
                if not value:
                    tag = soup.find(attrs={'name': re.compile(f'^dei:{dei_tag}$', re.I)})
                    if tag:
                        value = tag.get_text(strip=True)
            
            # Store the value if found
            if value:
                # Clean up the value - remove extra whitespace and normalize
                value = ' '.join(value.split())
                setattr(result, our_key, value)
    
    except Exception as e:
        print(f"Error parsing XBRL filing: {str(e)}")
        # Don't raise the exception - return partial results if any were found
    
    return result

def parse_html_filing(file_content: str) -> FilingData:
    """
    Parse an HTML-formatted SEC filing that lacks XBRL markup to extract key company information.
    Looks for specific labels in the text to identify relevant information.
    
    Args:
        file_content (str): The content of the HTML filing as a string
        
    Returns:
        FilingData: Object containing the parsed fields
    """
    # Initialize result object
    result = FilingData()
    
    try:
        # Parse the document with html parser
        soup = BeautifulSoup(file_content, 'html.parser')
        
        # Find the document section
        doc_section = soup.find('document')
        if not doc_section:
            return result
            
        # Find form type - it's usually in a centered div with font-weight:bold
        form_divs = doc_section.find_all('div', style=lambda s: s and 'text-align:center' in s and 'font-weight:bold' in s)
        for div in form_divs:
            if 'FORM' in div.text:
                form_text = div.text.strip()
                result.form = form_text.replace('FORM', '').strip()
                break
        
        # Find date - it's usually in a centered div with font-weight:bold before "Date of Report"
        date_divs = doc_section.find_all('div', style=lambda s: s and 'text-align:center' in s)
        for i, div in enumerate(date_divs):
            if 'Date of Report' in div.text:
                # Get the previous div which should contain the date
                if i > 0:
                    result.date = date_divs[i-1].text.strip()
                break
        
        # Find company name - it's usually in a large centered div
        company_divs = doc_section.find_all('div', style=lambda s: s and 'text-align:center' in s and 'font-size:21pt' in s)
        if company_divs:
            result.company_name = company_divs[0].text.strip()
            
        # Find the table containing state, commission number, and IRS number
        # Look for cells containing the labels
        label_cells = doc_section.find_all('td', string=lambda s: s and any(x in s.lower() for x in [
            'state or other jurisdiction',
            'commission file number',
            'i.r.s. employer'
        ]))
        
        for cell in label_cells:
            # Get the parent row
            label_row = cell.find_parent('tr')
            if not label_row:
                continue
                
            # Get the previous row which contains the values
            value_row = label_row.find_previous_sibling('tr')
            if not value_row:
                continue
                
            # Get all cells in both rows
            label_cells = label_row.find_all('td')
            value_cells = value_row.find_all('td')
            
            # Map the cells by their index
            for i, label_cell in enumerate(label_cells):
                label_text = label_cell.get_text().lower().strip()
                if i < len(value_cells):
                    value = value_cells[i].get_text().strip()
                    if 'state or other jurisdiction' in label_text:
                        result.state_of_incorporation = value
                    elif 'commission file number' in label_text:
                        result.commission_file_number = value
                    elif 'i.r.s. employer' in label_text:
                        result.irs_number = value
            
        # Find address - it's usually in centered divs with font-weight:bold
        address_divs = doc_section.find_all('div', style=lambda s: s and 'text-align:center' in s and 'font-weight:bold' in s)
        for i, div in enumerate(address_divs):
            text = div.text.strip()
            if 'Way' in text and not result.document_address:  # Looking for street address
                result.document_address = text
                # Next div might contain city, state, zip
                if i + 1 < len(address_divs):
                    location = address_divs[i + 1].text.strip()
                    parts = location.split(',')
                    if len(parts) >= 2:
                        result.document_city = parts[0].strip()
                        state_zip = parts[1].strip().split()
                        if len(state_zip) >= 2:
                            result.document_state = state_zip[0].strip()
                            result.document_zip = state_zip[1].strip()
                break
                    
        # Clean up any values - remove extra whitespace and normalize
        for field in result.__dataclass_fields__:
            value = getattr(result, field)
            if value:
                setattr(result, field, ' '.join(value.split()))
                
    except Exception as e:
        print(f"Error parsing HTML filing: {str(e)}")
        # Don't raise the exception - return partial results if any were found
    
    return result

def parse_txt_filing(file_content: str) -> FilingData:
    """
    Parse a text-formatted SEC filing to extract key company information from the cover page.
    Ignores any content in <sec-header> sections if present.
    
    Args:
        file_content (str): The content of the SEC filing as a string
        
    Returns:
        FilingData: Object containing the parsed fields
    """
    # Initialize result object
    result = FilingData()
    
    try:
        # Remove any <sec-header> section if present
        if '<SEC-HEADER>' in file_content:
            header_start = file_content.find('<SEC-HEADER>')
            header_end = file_content.find('</SEC-HEADER>')
            if header_end != -1:
                file_content = file_content[:header_start] + file_content[header_end + len('</SEC-HEADER>'):]
        
        # Parse the document with BeautifulSoup
        soup = BeautifulSoup(file_content, 'html.parser')
        
        # Find the document section
        doc_section = soup.find('document')
        if not doc_section:
            return result
            
        # Extract information using helper methods
        result.company_name = parse_name_txt(doc_section)
        result.date = parse_date_txt(doc_section)
        result.state_of_incorporation = parse_incorporation_txt(doc_section)
        result.commission_file_number = parse_file_no_txt(doc_section)
        result.irs_number = parse_irs_no_txt(doc_section)
        result.document_address = parse_address_txt(doc_section)
        result.document_zip = parse_zip_txt(doc_section)
        
        # Clean up any values - remove extra whitespace and normalize
        for field in result.__dataclass_fields__:
            value = getattr(result, field)
            if value:
                setattr(result, field, ' '.join(value.split()))
                
    except Exception as e:
        print(f"Error parsing TXT filing: {str(e)}")
        # Don't raise the exception - return partial results if any were found
    
    return result

def parse_name_txt(doc_section) -> Optional[str]:
    """
    Parse the company name from the document section.
    The name is typically found in a centered div with specific formatting.
    """
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Define label word patterns and value pattern
    label_word_patterns = [
        r'exact',
        r'name',
        r'of',
        r'registrant',
        r'as',
        r'specified',
        #r'in(?:its|its\')?',
        r'in\s+(?:.*?)\s*charter'
        # r'.*?',
        # r'charter'
    ]
    value_pattern = r'(?=\S*[A-Za-z])\S+(?:\s\S+)*'
    
    return bp.find_value_by_label(text, label_word_patterns, value_pattern, line_search_limit=(4, 0))

def parse_date_txt(doc_section) -> Optional[str]:
    """
    Parse the report date from the document section.
    The date is typically found near "Date of Report" or "Date of earliest event reported".
    """
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Define label word patterns and value pattern
    label_word_patterns = [
        r'Date',
        r'of',
        r'Report'
    ]
    value_pattern = r'(?<!\(|\()\b(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER|January|February|March|April|May|June|July|August|September|October|November|December|Jan\.|Feb\.|Mar\.|Apr\.|May|Jun\.|Jul\.|Aug\.|Sep\.|Oct\.|Nov\.|Dec\.)\s+\d{1,2},\s+\d{4}\b(?!\)|\))'
    
    return bp.find_value_by_label(text, label_word_patterns, value_pattern, '','', line_search_limit=(3, 3))

def parse_incorporation_txt(doc_section) -> Optional[str]:
    """
    Parse the state of incorporation from the document section.
    The state is typically found near "State or other jurisdiction of incorporation".
    """
    # State or Other Jurisdiction of Incorporation
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)

    label_word_patterns = [
        [
            r'state\b',
            r'or\b',
            r'other\b',
            r'jurisdiction\b',
            r'of\b',
            r'incorp(?:oration)?\b',
            r'or\b',
            r'org(?:anization)?\b'
        ],
        [
            r'state\b',
            r'or\b',
            r'other\b',
            r'jurisdiction\b',
            r'of\b',
            r'incorp(?:oration)?\b(?:\s*[,;]\s*[^)]*|\s+[^)]*)?'
        ],
        [
            r'state\b',
            r'of\b',
            r'incorp(?:oration)?\b(?:\s*[,;]\s*[^)]*|\s+[^)]*)?'
        ],
        [
            r'jurisdiction\b',
            r'of\b',
            r'incorp(?:oration)?\b(?:\s*[,;]\s*[^)]*|\s+[^)]*)?'
        ]
    ]
    
    # Define label word patterns and value pattern
    # label_word_patterns = [
    #     r'state\b',
    #     r'or\b',
    #     r'other\b',
    #     r'jurisdiction\b',
    #     r'of\b',
    #     r'incorporation\b(?:\s*[,;]\s*[^)]*|\s+[^)]*)?'
    # ]
    # label_word_patterns = [
    #     r'(\b(?:state|jurisdiction)\b)',
    #     r'(\b(?:incorp(?:oration)?|org(?:anization)?)\b)'
    # ]

    # label_word_patterns = [
    #     r'\b(?:state|jurisdiction|place|incorporation|organization|formation|incorp(?:oration)?)\b',
    #     r'(?:\s*(?:of|or|/|\\|and)\s*\b(?:state|jurisdiction|place|incorporation|organization|formation|incorp(?:oration)?)\b)?',
    #     r'(?:\s*(?:of|for|in))?',
    #     r'(?:\s*the)?',
    #     r'(?:\s*(?:company|entity))?'
    # ]

    # Pattern to match state names and abbreviations, excluding leading spaces
    # value_pattern = r'(?<!\s)\b[A-Za-z]{2,}(?:\s+[A-Za-z]{2,})*\b'
    value_pattern = r'(?=\S*[A-Za-z])\S+(?:\s\S+)*'

    for label_word_pattern in label_word_patterns:
        result = bp.find_value_by_label(text, label_word_pattern, value_pattern, line_search_limit=(4, 0))
        if result:
            return result
    return None

def parse_file_no_txt(doc_section) -> Optional[str]:
    """
    Parse the commission file number from the document section.
    The file number is typically found near "Commission File Number".
    """
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Define label word patterns and value pattern
    label_word_patterns = [
        r'Commission',
        r'File',
        r'(?:Number|No\.)'
    ]
    value_pattern = r'\b(?:\d{1,3})-\d{3,5}\b'
    
    return bp.find_value_by_label(text, label_word_patterns, value_pattern, line_search_limit=(10, 10))

def parse_irs_no_txt(doc_section) -> Optional[str]:
    """
    Parse the IRS number from the document section.
    The IRS number is typically found near "IRS Employer Identification No." or "I.R.S. Employer".
    """
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Define label word patterns and value pattern
    label_word_patterns = [
        r'(?:IRS|I\.R\.S\.)',
        r'Employer',
        r'Identification',
        r'(?:Number|No\.)'
    ]
    value_pattern = r'\b\d{2}-\d{7}\b'
    
    return bp.find_value_by_label(text, label_word_patterns, value_pattern, line_search_limit=(3, 3))

def parse_address_txt(doc_section) -> Optional[str]:
    """
    Parse the company address from the document section.
    Uses multiple patterns to handle different address formats including rural addresses,
    PO boxes, and standard street addresses. Also handles addresses split across multiple lines.
    """
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Define label word patterns
    label_word_patterns = [
        r'Address',
        r'of',
        r'principal',
        r'executive',
        r'office(?:s)?(?:\s*[,;]\s*[^)]*|\s+[^)]*)?'
    ]
    
    # First try to find complete addresses on a single line
    address_patterns = [
        # Standard street address (covers most urban/suburban addresses, optional extra comma-segments like PO Box, Floor, Suite)
        r'\s*\d+(?:-\d+)?\s+(?:\d+(?:st|nd|rd|th)?\s+)?[A-Za-z0-9\.,\-\']*[A-Za-z][A-Za-z0-9\.,\-\']*(?:\s+[A-Za-z0-9\.,\-\']*[A-Za-z][A-Za-z0-9\.,\-\']*)*\s*(?:N\.?|S\.?|E\.?|W\.?|N\.W\.?|S\.W\.?|N\.E\.?|S\.E\.?)?\s*(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Road|Rd\.?|Way|Place|Pl\.?|Court|Ct\.?|Circle|Cir\.?|Terrace|Terr\.?|Plaza|Plz\.?|Parkway|Pkwy\.?|Highway|Hwy\.?|Square|Sq\.?|Loop|Trail|Trl\.?|Pike|Turnpike|Alley|Aly\.?)?(?:\s+(?:Suite|Ste\.?|Unit|Apt\.?|Building|Bldg\.?|Floor|Fl\.?))?\s*[#\-]?\s*[A-Za-z0-9\-]*\s*(?:,\s*(?:P\.?\s*O\.?\s*Box\s+\d+|[A-Za-z0-9#&/\s\.\'-]+))*\s*,\s*[A-Za-z][A-Za-z\s\.\'-]*(?:\s+[A-Za-z][A-Za-z\s\.\'-]*)*\s*,\s*(?:[A-Za-z]{4,}|[A-Z]{2})(?=\s+\d{5}(?:-\d{4})?\b|\s*$)',
        
        # PO Box addresses
        r'P\.?\s*O\.?\s*Box\s+\d+\s*,\s*[A-Za-z\s\.,\-\']+(?:,\s*[A-Za-z\s]+)?',
        
        # Rural route addresses
        r'(?:Rural|RR|R\.R\.)\s+(?:Route\s+)?\d+\s*,?\s*(?:Box\s+\d+\s*,?)?\s*[A-Za-z\s\.,\-\']+(?:,\s*[A-Za-z\s]+)?',
        
        # Highway addresses (inverted format)
        r'(?:Highway|Hwy\.?|State\s+Route|SR|County\s+Road|CR|Route|Rt\.?)\s+\d+\s+(?:North|South|East|West|N\.?|S\.?|E\.?|W\.?)?\s*,\s*[A-Za-z\s\.,\-\'0-9]+(?:,\s*[A-Za-z\s]+)?',
        
        # Mile marker addresses
        r'(?:Mile|MM)\s+(?:Marker\s+)?\d+\s*,\s*(?:Highway|Hwy\.?|Route|Rt\.?)\s*\d+\s*,\s*[A-Za-z\s\.,\-\']+(?:,\s*[A-Za-z\s]+)?',
        
        # Named buildings with no street numbers (e.g., "The White House, Pennsylvania Avenue")
        r'(?:The\s+)?[A-Z][A-Za-z\s\.,\-\']+(?:Building|Tower|Plaza|Center|Centre|Complex|House|Hall|Campus|Park|Office)\s*,\s*[A-Za-z0-9\s\.,\-\']+(?:,\s*[A-Za-z\s]+)+',
        
        # Looser pattern for any building number followed by multiple words and a comma
        r'\d+\s+[A-Za-z0-9\s\.,\-\']+\s*,\s*[A-Za-z\s\.,\-\']+(?:,\s*[A-Za-z\s]+)?'
    ]
    
    # Try each pattern in order until we find a match
    for pattern in address_patterns:
        address = bp.find_value_by_label(text, label_word_patterns, pattern, line_search_limit=(6, 4))
        if address:
            return address
        
    # If no complete address found, try to find split addresses (street address on one line, city/state/zip on next)
    street_patterns = [
        # Standard street number and name
        r'\s*\d+(?:-\d+)?\s+(?:\d+(?:st|nd|rd|th)?\s+)?[A-Za-z0-9\.,\-\']*[A-Za-z][A-Za-z0-9\.,\-\']*(?:\s+(?:[A-Za-z0-9\.,\-\']*[A-Za-z][A-Za-z0-9\.,\-\']*))*\s*(?:N\.?|S\.?|E\.?|W\.?|N\.W\.?|S\.W\.?|N\.E\.?|S\.E\.?)*\s*(?:Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Drive|Dr\.?|Lane|Ln\.?|Road|Rd\.?|Way|Place|Pl\.?|Court|Ct\.?|Circle|Cir\.?|Terrace|Terr\.?|Plaza|Plz\.?|Parkway|Pkwy\.?|Highway|Hwy\.?|Square|Sq\.?|Loop|Trail|Trl\.?|Pike|Turnpike|Alley|Aly\.?)?(?:\s+(?:Suite|Ste\.?|Unit|Apt\.?|Building|Bldg\.?|Floor|Fl\.?)\s*[#\-]?\s[A-Za-z0-9\-]+)?(?=\s{4,}|\s*$|,)',
        
        # PO Box
        r'P\.?\s*O\.?\s*Box\s+\d+',
        
        # Rural route
        r'(?:Rural|RR|R\.R\.)\s+(?:Route\s+)?\d+\s*(?:,?\s*Box\s+\d+\s*)?',
        
        # Highway format
        r'(?:Highway|Hwy\.?|State\s+Route|SR|County\s+Road|CR|Route|Rt\.?)\s+\d+\s+(?:North|South|East|West|N\.?|S\.?|E\.?|W\.?)?',
        
        # Named buildings
        r'(?:The\s+)?[A-Z][A-Za-z\s\.,\-\']+(?:Building|Tower|Plaza|Center|Centre|Complex|House|Hall|Campus|Park|Office)'
    ]

    # Try each pattern in order until we find a match
    for pattern in street_patterns:
        street_address = bp.find_value_by_label(text, label_word_patterns, pattern, line_search_limit=(5, 5))
        if street_address:
            # If there is a PO Box line within the proximity window, append it to the street
            po_box_pattern = r'P\.?\s*O\.?\s*Box\s+\d+'
            po_box_line = bp.find_value_by_label(text, label_word_patterns, po_box_pattern, line_search_limit=(5, 5))
            if po_box_line and po_box_line not in street_address:
                street_address = f"{street_address}, {po_box_line}"
            # Pattern for city, state, zip line
            state_regex = r'(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC|District\s+of\s+Columbia|ALABAMA|ALASKA|ARIZONA|ARKANSAS|CALIFORNIA|COLORADO|CONNECTICUT|DELAWARE|FLORIDA|GEORGIA|HAWAII|IDAHO|ILLINOIS|INDIANA|IOWA|KANSAS|KENTUCKY|LOUISIANA|MAINE|MARYLAND|MASSACHUSETTS|MICHIGAN|MINNESOTA|MISSISSIPPI|MISSOURI|MONTANA|NEBRASKA|NEVADA|NEW\s+HAMPSHIRE|NEW\s+JERSEY|NEW\s+MEXICO|NEW\s+YORK|NORTH\s+CAROLINA|NORTH\s+DAKOTA|OHIO|OKLAHOMA|OREGON|PENNSYLVANIA|RHODE\s+ISLAND|SOUTH\s+CAROLINA|SOUTH\s+DAKOTA|TENNESSEE|TEXAS|UTAH|VERMONT|VIRGINIA|WASHINGTON|WEST\s+VIRGINIA|WISCONSIN|WYOMING)'
            city_regex = r'[A-Za-z][A-Za-z\s\.\'-]*'
            city_state_pattern = fr'{city_regex}\s*,\s*(?:{state_regex})\b(?=\s|$)'
            # Looser city/state pattern without requiring ZIP
            city_state_pattern_loose = city_state_pattern

            city_state_address = bp.find_value_by_label(text, label_word_patterns, city_state_pattern, line_search_limit=(5, 5))
            if city_state_address:
                return f"{street_address}, {city_state_address}"
            else:
                city_state_address = bp.find_value_by_label(text, label_word_patterns, city_state_pattern_loose, line_search_limit=(5, 5))
                if city_state_address:
                    return f"{street_address}, {city_state_address}"
    
    return None

def parse_zip_txt(doc_section) -> Optional[str]:
    """
    Parse the ZIP code from the document section.
    Looks for ZIP codes that are closest to either:
    1. "(zip code)" label
    2. "Address of principal executive offices" label
    """
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Define label word patterns and value pattern
    label_word_patterns = [
        r'zip',
        r'code'
    ]
    value_pattern = r'\b\d{5}(?:-\d{4})?\b'
    
    zip = bp.find_value_by_label(text, label_word_patterns, value_pattern, line_search_limit=(4, 0))
    if not zip:
        # Try again by searching in the address section.
        label_word_patterns = [
            r'Address',
            r'of',
            r'principal',
            r'executive',
            r'offices'
        ]
        zip = bp.find_value_by_label(text, label_word_patterns, value_pattern, line_search_limit=(4, 0))
    return zip

def approx_relative_euclidean_distance(L1, C1, L2, C2, line_height_factor=2.0):
    """
    Calculates approximate visual Euclidean distance between two points in a text document.
    
    This function computes the distance between two points (L1,C1) and (L2,C2) where:
    - L represents line numbers (vertical position)
    - C represents character positions (horizontal position)
    - The distance is calculated using a line height factor to account for the visual
      difference between horizontal and vertical spacing in text documents.
    
    Args:
        L1 (int): Line number of the first point
        C1 (int): Character position of the first point
        L2 (int): Line number of the second point
        C2 (int): Character position of the second point
        line_height_factor (float, optional): Multiplier to account for the visual
            difference between line height and character width. Defaults to 2.0.
    
    Returns:
        float: The calculated Euclidean distance between the two points, adjusted
            by the line height factor.
    """
    # Calculate differences directly
    delta_c = float(C2 - C1)
    delta_l = float(L2 - L1)

    # Apply the formula derived from Euclidean distance
    # distance = math.sqrt( delta_c^2 + (delta_l * factor)^2 )
    distance = math.sqrt( delta_c**2 + (delta_l * line_height_factor)**2 )
    return distance

def exponential_vertical_distance(L1, C1, L2, C2,
                                   line_height_factor=2.0,
                                   exp_base=2.0, # How quickly penalty ramps up (e.g., 2 = doubles each line > 1)
                                   exp_sensitivity=1.0): # Multiplies the exponent
    """
    Calculates visual distance with exponentially increasing weight for vertical distance.
    This seemed necessary for cases where the value is one or two lines above but off-center
    but the distance is the same as a value that is 8 lines above due to horizontal proximity.

    Args:
    L1, C1: Line (1-based) and Char (0-based) for point 1.
    L2, C2: Line (1-based) and Char (0-based) for point 2.
    line_height_factor: Initial linear weight for vertical distance (vs char_width=1).
    exp_base: Base for the exponential scaling of vertical distance (> 1).
    exp_sensitivity: Sensitivity factor (k) applied to the exponent.

    Returns:
    The calculated distance score.
    """
    if exp_base <= 1.0:
        print("Warning: exp_base should be greater than 1 for exponential increase.")
        # Fallback to linear or handle as error depending on need
        exp_base = 1.00001 # Avoid math errors, minimal exponential effect

    delta_c = float(C2 - C1)
    delta_l = float(L2 - L1)
    abs_delta_l = abs(delta_l)

    # Calculate squared horizontal component
    d_c_squared = delta_c**2

    # Calculate initial weighted squared vertical component
    d_l_weighted_squared = (delta_l * line_height_factor)**2

    # Calculate the exponent for vertical scaling
    # Starts applying exponentially after the first line difference
    exponent = exp_sensitivity * max(0, abs_delta_l - 1)

    # Calculate the exponential multiplier
    vertical_multiplier = exp_base**exponent

    # Calculate the final exponentially scaled squared vertical component
    d_l_exp_scaled_squared = d_l_weighted_squared * vertical_multiplier

    # Calculate final distance
    distance = math.sqrt(d_c_squared + d_l_exp_scaled_squared)

    return distance

def parse_us_address(raw: str) -> dict | None:
    try:
        tagged, address_type = usaddress.tag(raw, tag_mapping={
            'Recipient': 'recipient',
            'AddressNumber': 'address1',
            'AddressNumberPrefix': 'address1',
            'AddressNumberSuffix': 'address1',
            'StreetName': 'address1',
            'StreetNamePreDirectional': 'address1',
            'StreetNamePreModifier': 'address1',
            'StreetNamePreType': 'address1',
            'StreetNamePostDirectional': 'address1',
            'StreetNamePostModifier': 'address1',
            'StreetNamePostType': 'address1',
            'CornerOf': 'address1',
            'IntersectionSeparator': 'address1',
            'LandmarkName': 'address1',
            'USPSBoxGroupID': 'address1',
            'USPSBoxGroupType': 'address1',
            'USPSBoxID': 'address1',
            'USPSBoxType': 'address1',
            'BuildingName': 'address2',
            'OccupancyType': 'address2',
            'OccupancyIdentifier': 'address2',
            'SubaddressIdentifier': 'address2',
            'SubaddressType': 'address2',
            'PlaceName': 'city',
            'StateName': 'state',
            'ZipCode': 'zip_code',
        })
    # try:
    #     tagged, _ = usaddress.tag(raw)
    except usaddress.RepeatedLabelError:
        return None       # let the call-site fall back to regex
    wanted = {
        # "street": " ".join(tagged.get(k, '') for k in (
        #     "AddressNumber", "StreetNamePreType", "StreetName",
        #     "StreetNamePostType", "OccupancyType", "OccupancyIdentifier",
        #     "USPSBoxType", "USPSBoxID"
        # )).strip(),
        # "city":     tagged.get("PlaceName"),
        # "state":    tagged.get("StateName"),
        # "zipcode":  tagged.get("ZipCode"),
        "address1": tagged.get("address1"),
        "address2": tagged.get("address2"),
        "city":     tagged.get("city"),
        "state":    tagged.get("state"),
        "zipcode":  tagged.get("zip_code"),
    }
    if all(v is None or v == '' for v in wanted.values()):
        return None
    return wanted

def normalise_whitespace(text: str) -> str:
    """Collapse all runs of whitespace (NL, TAB, NBSP, etc.) into a single space."""
    return re.sub(r'\s+', ' ', text)

def parse_usaddress(doc_section):
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)

    label_word_patterns = [
        r'Address',
        r'of',
        r'principal',
        r'executive',
        r'offices(?:\s*[,;]\s*[^)]*|\s+[^)]*)?'
    ]
    label = bp.find_label(text, label_word_patterns)

    lines = text.splitlines()

    block = lines[(label.line_start - 6):(label.line_end + 6)]

    # Let's ignore columns for now because they could cause an issue with labels on the same line as the value.
    # columns = column_parser.parse_columns("\n".join(block))

    # # Find the label's column
    # for line_number, line in enumerate(columns):
    #     for column_name, column_value in line.items():
    #         if column_value == label.content:
    #             address_column = column_name
    #             column_line = line_number
    #             break

    # # now that we have the label location, let's only search in that column. 
    # block = ""
    # for line in columns:
    #     if address_column in line.keys():
    #         block += line[address_column] + "\n"

    raw_block = "\n".join(block)
    # now let's find the location of the label and city and state in the subset of the data.
    label = bp.find_label(raw_block, label_word_patterns)

    # let's find the position of the city, state. This will tell us if we should look above, below, or beside the label.
    # Pattern for city, state, zip line
    state_regex = r'(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC|District\s+of\s+Columbia|D.C.|ALABAMA|ALASKA|ARIZONA|ARKANSAS|CALIFORNIA|COLORADO|CONNECTICUT|DELAWARE|FLORIDA|GEORGIA|HAWAII|IDAHO|ILLINOIS|INDIANA|IOWA|KANSAS|KENTUCKY|LOUISIANA|MAINE|MARYLAND|MASSACHUSETTS|MICHIGAN|MINNESOTA|MISSISSIPPI|MISSOURI|MONTANA|NEBRASKA|NEVADA|NEW\s+HAMPSHIRE|NEW\s+JERSEY|NEW\s+MEXICO|NEW\s+YORK|NORTH\s+CAROLINA|NORTH\s+DAKOTA|OHIO|OKLAHOMA|OREGON|PENNSYLVANIA|RHODE\s+ISLAND|SOUTH\s+CAROLINA|SOUTH\s+DAKOTA|TENNESSEE|TEXAS|UTAH|VERMONT|VIRGINIA|WASHINGTON|WEST\s+VIRGINIA|WISCONSIN|WYOMING)'
    city_regex = r'[A-Za-z][A-Za-z\s\.\'-]*'
    city_state_pattern = fr'{city_regex}\s*,\s*(?:{state_regex})\b(?=\s|$)'
    city_state = bp.find_label(raw_block, [city_state_pattern])

    if city_state is None:
        return None
    

    address = None
    if city_state.line_start <= label.line_start and city_state.line_end >= label.line_end:
        # next to the label

        pass
    elif city_state.line_start < label.line_start:
        # we need to search above the label.
        block = block[(label.line_start - 6):(label.line_end + 1)]
        columns = column_parser.parse_columns("\n".join(block))

        # Find the label's column
        for line_number, line in enumerate(columns):
            for column_name, column_value in line.items():
                if column_value.strip() == '':
                    continue

                if column_value in label.content:
                    address_column = column_name
                    break

        # now that we have the label's column, let's try to determine how many lines above should be used. 
        block = ""
        for line in reversed(columns[:(len(columns) - (label.line_end - label.line_start + 1) - 1)]):
            if line[address_column].strip(' -\t\r\n') == '':
                continue
            new_block = line[address_column] + "\n" + block
            try:
                address = parse_us_address(normalise_whitespace(new_block))
                if all(key in address and address[key] for key in ['address1', 'city', 'state']):
                    break
                block = new_block
            except Exception as e:
                print(f"Error parsing address: {e}")
                address = parse_us_address(normalise_whitespace(block))
                break
    elif city_state.line_start > label.line_start:
        # we need to search below the label.
        block = lines[label.line_start:(label.line_end + 6)]
        columns = column_parser.parse_columns("\n".join(block))

        # Find the label's column
        for line_number, line in enumerate(columns):
            for column_name, column_value in line.items():
                if column_value in label.content:
                    address_column = column_name
                    break

        # now that we have the label's column, let's try to determine how many lines above should be used. 
        block = ""
        for line in columns[(label.line_end - label.line_start):len(columns)]:
            if line[address_column].strip(' -\t\r\n') == '':
                continue
            new_block = block + "\n" + line[address_column] 
            try:
                address = parse_us_address(normalise_whitespace(new_block))
                block = new_block
            except:
                address = parse_us_address(normalise_whitespace(block))
                break

    return ", ".join(address[key] for key in ['address1', 'address2', 'city', 'state'] if key in address and address[key]) if address else None

def test_txt_parsing():
    """Test the parsing of company names, ZIP codes, IRS numbers, file numbers, addresses, incorporation states, and dates with various test files."""
    test_files = [
        # Apple filings
        ("test_filings/320193/0000912057-00-002128/0000912057-00-002128.txt", "Apple Computer, Inc.", "95014", "94-2404110", "0-10030", "1 Infinite Loop, Cupertino, California", "California", "January 19, 2000"),
        ("test_filings/320193/0000320193-96-000027/0000320193-96-000027.txt", "Apple Computer, Inc.", "95014", "94-2404110", "0-10030", "1 Infinite Loop, Cupertino, California", "California", "December 24, 1996"),
        # Sears filing
        ("test_filings/319256/0000891092-04-003383/e18506_8k.txt", "SEARS, ROEBUCK AND CO.", "60179", "36-1750680", "1-416", "3333 Beverly Road, Hoffman Estates, Illinois", "New York", "July 22, 2004"),
        # Amazon filing
        ("test_filings/1018724/0000891020-98-001352/0000891020-98-001352.txt", "AMAZON.COM, INC.", "98101", "91-1646860", "000-22513", "1516 SECOND AVENUE, SEATTLE, WASHINGTON", "DELAWARE", "AUGUST 12, 1998"),
        # Cisco filing
        ("test_filings/858877/0000891618-95-000727/0000891618-95-000727.txt", "CISCO SYSTEMS, INC.", "95134", "77-0059951", "0-18225", "170 West Tasman Drive, San Jose, California", "California", "SEPTEMBER 29, 1995"),
        # Oasis entertainment
        ("test_filings/1063262/0001104540-02-000064/0001104540-02-000064.txt", "OASIS ENTERTAINMENT'S FOURTH MOVIE PROJECT, INC.", "92629", "76-0528600", "000-28881", "24843 Del Prado, Suite 326, Dana Point, California", "Nevada", "February 14, 2002"),
    ]
    
    print("\nTesting company names, ZIP codes, IRS numbers, file numbers, addresses, incorporation states, and dates:")
    print("-" * 250)
    print(f"{'File':<70} {'Name':<20} {'ZIP':<10} {'IRS':<15} {'File No':<15} {'Address':<40} {'Incorporation':<15} {'Date':<15} {'Name Match':<10} {'ZIP Match':<10} {'IRS Match':<10} {'File No Match':<10} {'Address Match':<10} {'Incorp Match':<10} {'Date Match':<10}")
    print("-" * 250)
    
    for file_path, expected_name, expected_zip, expected_irs, expected_file_no, expected_address, expected_incorporation, expected_date in test_files:
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                if '<SEC-HEADER>' in content:
                    header_start = content.find('<SEC-HEADER>')
                    header_end = content.find('</SEC-HEADER>')
                    if header_end != -1:
                        content = content[:header_start] + content[header_end + len('</SEC-HEADER>'):]
                
                doc_section = "\n".join(content.split("\n")[:100])
                #doc_section = re.sub(r'^[-\s]+$\n?', '', content, flags=re.MULTILINE)
                doc_section = re.sub(r'^[-\s]+$', '', doc_section, flags=re.MULTILINE)
                # parsed_columns = column_parser.parse_columns(doc_section)

                # # now, let's flatten this document so columns are vertically stacked.
                # aggregated_columns = {}
                # for line_data in parsed_columns:
                #     for column_name, column_value in line_data.items():
                #         if column_name not in aggregated_columns:
                #             aggregated_columns[column_name] = []
                #         aggregated_columns[column_name].append(column_value)

                # flat_doc = "\n".join("\n".join(aggregated_columns[column_name]) for column_name in aggregated_columns)

                #print(flat_doc)

                if doc_section:
                    found_name = parse_name_txt(doc_section)
                    found_zip = parse_zip_txt(doc_section)
                    found_irs = parse_irs_no_txt(doc_section)
                    found_file_no = parse_file_no_txt(doc_section)
                    # found_address = parse_address_txt(doc_section)
                    found_address = parse_usaddress(doc_section)
                    found_incorporation = parse_incorporation_txt(doc_section)
                    found_date = parse_date_txt(doc_section)
                    
                    name_match = (found_name or '').lower() == (expected_name or '').lower()
                    zip_match = (found_zip or '').lower() == (expected_zip or '').lower()
                    irs_match = (found_irs or '').lower() == (expected_irs or '').lower()
                    file_no_match = (found_file_no or '').lower() == (expected_file_no or '').lower()
                    address_match = (found_address or '').lower() == (expected_address or '').lower()
                    incorp_match = (found_incorporation or '').lower() == (expected_incorporation or '').lower()
                    date_match = (found_date or '').lower() == (expected_date or '').lower()
                    
                    print(f"{file_path:<70} {found_name or 'None':<20} {found_zip or 'None':<10} {found_irs or 'None':<15} {found_file_no or 'None':<15} "
                          f"{found_address or 'None':<40} {found_incorporation or 'None':<15} {found_date or 'None':<15} {str(name_match):<10} {str(zip_match):<10} {str(irs_match):<10} "
                          f"{str(file_no_match):<10} {str(address_match):<10} {str(incorp_match):<10} {str(date_match):<10}")
        except Exception as e:
            print(f"\nError testing {file_path}: {str(e)}")

if __name__ == "__main__":
    test_txt_parsing()
    # test_txt_sample()
    