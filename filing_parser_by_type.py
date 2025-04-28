from bs4 import BeautifulSoup
from typing import Dict, Optional, Union, List
import re
import json

def parse_xbrl_filing(file_content: str) -> Dict[str, Optional[str]]:
    """
    Parse an XBRL-annotated SEC filing to extract key company information.
    First attempts to find direct <dei:tag> format, then falls back to ix:nonNumeric with name="dei:tag" format.
    
    Args:
        file_content (str): The content of the XBRL filing as a string
        
    Returns:
        Dict[str, Optional[str]]: Dictionary containing the parsed fields with the following keys:
            - cik: Central Index Key
            - form: Document Type
            - date: Document Period End Date
            - company_name: Entity Registrant Name
            - state_of_incorporation: Entity Incorporation State/Country Code
            - commission_file_number: Entity File Number
            - irs_number: Entity Tax Identification Number
            - document_address: Entity Address Line 1
            - document_city: Entity Address City
            - document_state: Entity Address State
            - document_zip: Entity Address Zip Code
            - trading_symbol: Trading Symbol
            - exchange: Security Exchange Name
    """
    # Initialize result dictionary with None values
    result = {
        'cik': None,
        'form': None,
        'date': None,
        'company_name': None,
        'state_of_incorporation': None,
        'commission_file_number': None,
        'irs_number': None,
        'document_address': None,
        'document_city': None,
        'document_state': None,
        'document_zip': None,
        'trading_symbol': None,
        'exchange': None
    }
    
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
                result[our_key] = value
    
    except Exception as e:
        print(f"Error parsing XBRL filing: {str(e)}")
        # Don't raise the exception - return partial results if any were found
    
    return result

def parse_html_filing(file_content: str) -> Dict[str, Optional[str]]:
    """
    Parse an HTML-formatted SEC filing that lacks XBRL markup to extract key company information.
    Looks for specific labels in the text to identify relevant information.
    
    Args:
        file_content (str): The content of the HTML filing as a string
        
    Returns:
        Dict[str, Optional[str]]: Dictionary containing the parsed fields with the following keys:
            - cik: Central Index Key
            - form: Document Type
            - date: Document Period End Date
            - company_name: Entity Registrant Name
            - state_of_incorporation: Entity Incorporation State/Country Code
            - commission_file_number: Entity File Number
            - irs_number: Entity Tax Identification Number
            - document_address: Entity Address Line 1
            - document_city: Entity Address City
            - document_state: Entity Address State
            - document_zip: Entity Address Zip Code
            - trading_symbol: Trading Symbol
            - exchange: Security Exchange Name
    """
    # Initialize result dictionary with None values
    result = {
        'cik': None,
        'form': None,
        'date': None,
        'company_name': None,
        'state_of_incorporation': None,
        'commission_file_number': None,
        'irs_number': None,
        'document_address': None,
        'document_city': None,
        'document_state': None,
        'document_zip': None,
        'trading_symbol': None,
        'exchange': None
    }
    
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
                result['form'] = form_text.replace('FORM', '').strip()
                break
        
        # Find date - it's usually in a centered div with font-weight:bold before "Date of Report"
        date_divs = doc_section.find_all('div', style=lambda s: s and 'text-align:center' in s)
        for i, div in enumerate(date_divs):
            if 'Date of Report' in div.text:
                # Get the previous div which should contain the date
                if i > 0:
                    result['date'] = date_divs[i-1].text.strip()
                break
        
        # Find company name - it's usually in a large centered div
        company_divs = doc_section.find_all('div', style=lambda s: s and 'text-align:center' in s and 'font-size:21pt' in s)
        if company_divs:
            result['company_name'] = company_divs[0].text.strip()
            
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
                        result['state_of_incorporation'] = value
                    elif 'commission file number' in label_text:
                        result['commission_file_number'] = value
                    elif 'i.r.s. employer' in label_text:
                        result['irs_number'] = value
            
        # Find address - it's usually in centered divs with font-weight:bold
        address_divs = doc_section.find_all('div', style=lambda s: s and 'text-align:center' in s and 'font-weight:bold' in s)
        for i, div in enumerate(address_divs):
            text = div.text.strip()
            if 'Way' in text and not result['document_address']:  # Looking for street address
                result['document_address'] = text
                # Next div might contain city, state, zip
                if i + 1 < len(address_divs):
                    location = address_divs[i + 1].text.strip()
                    parts = location.split(',')
                    if len(parts) >= 2:
                        result['document_city'] = parts[0].strip()
                        state_zip = parts[1].strip().split()
                        if len(state_zip) >= 2:
                            result['document_state'] = state_zip[0].strip()
                            result['document_zip'] = state_zip[1].strip()
                break
                    
        # Clean up any values - remove extra whitespace and normalize
        for key in result:
            if result[key]:
                result[key] = ' '.join(result[key].split())
                
    except Exception as e:
        print(f"Error parsing HTML filing: {str(e)}")
        # Don't raise the exception - return partial results if any were found
    
    return result

def parse_txt_filing(file_content: str) -> Dict[str, Optional[str]]:
    """
    Parse a text-formatted SEC filing to extract key company information from the cover page.
    Ignores any content in <sec-header> sections if present.
    
    Args:
        file_content (str): The content of the SEC filing as a string
        
    Returns:
        Dict[str, Optional[str]]: Dictionary containing the parsed fields with the following keys:
            - cik: Central Index Key
            - form: Document Type
            - date: Document Period End Date
            - company_name: Entity Registrant Name
            - state_of_incorporation: Entity Incorporation State/Country Code
            - commission_file_number: Entity File Number
            - irs_number: Entity Tax Identification Number
            - document_address: Entity Address Line 1
            - document_city: Entity Address City
            - document_state: Entity Address State
            - document_zip: Entity Address Zip Code
            - trading_symbol: Trading Symbol
            - exchange: Security Exchange Name
    """
    # Initialize result dictionary with None values
    result = {
        'cik': None,
        'form': None,
        'date': None,
        'company_name': None,
        'state_of_incorporation': None,
        'commission_file_number': None,
        'irs_number': None,
        'document_address': None,
        'document_city': None,
        'document_state': None,
        'document_zip': None,
        'trading_symbol': None,
        'exchange': None
    }
    
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
        result['company_name'] = parse_name_txt(doc_section)
        result['date'] = parse_date_txt(doc_section)
        result['state_of_incorporation'] = parse_incorporation_txt(doc_section)
        result['commission_file_number'] = parse_file_no_txt(doc_section)
        result['irs_number'] = parse_irs_no_txt(doc_section)
        result['document_address'] = parse_address_txt(doc_section)
        result['document_zip'] = parse_zip_txt(doc_section)
        
        # Clean up any values - remove extra whitespace and normalize
        for key in result:
            if result[key]:
                result[key] = ' '.join(result[key].split())
                
    except Exception as e:
        print(f"Error parsing TXT filing: {str(e)}")
        # Don't raise the exception - return partial results if any were found
    
    return result

def parse_name_txt(doc_section) -> Optional[str]:
    """
    Parse the company name from the document section.
    The name is typically found in a centered div with specific formatting.
    """
    # TODO: Implement name parsing logic
    return None

def parse_date_txt(doc_section) -> Optional[str]:
    """
    Parse the report date from the document section.
    The date is typically found near "Date of Report" or "Date of earliest event reported".
    """
    # TODO: Implement date parsing logic
    return None

def parse_incorporation_txt(doc_section) -> Optional[str]:
    """
    Parse the state of incorporation from the document section.
    The state is typically found near "State or other jurisdiction of incorporation".
    """
    # TODO: Implement incorporation state parsing logic
    return None

def parse_file_no_txt(doc_section) -> Optional[str]:
    """
    Parse the commission file number from the document section.
    The file number is typically found near "Commission File Number".
    """
    # TODO: Implement file number parsing logic
    return None

def parse_irs_no_txt(doc_section) -> Optional[str]:
    """
    Parse the IRS number from the document section.
    The IRS number is typically found near "IRS Employer Identification No." or "I.R.S. Employer".
    The number follows the pattern dd-ddddddd where d is a digit.
    """
    import re
    
    # Convert the document section to text
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Pattern to match IRS numbers: two digits, hyphen, seven digits
    irs_pattern = r'\b\d{2}-\d{7}\b'
    
    # First try to find lines containing IRS-related labels
    lines = text.split('\n')
    for line in lines:
        if re.search(r'IRS\s+Employer|I\.R\.S\.\s+Employer', line, re.I):
            match = re.search(irs_pattern, line)
            if match:
                return match.group()
    
    # If not found near labels, look for the pattern anywhere in the text
    match = re.search(irs_pattern, text)
    if match:
        return match.group()
    
    return None

def parse_address_txt(doc_section) -> Optional[str]:
    """
    Parse the company address from the document section.
    The address is typically found near "Address of principal executive offices".
    """
    # TODO: Implement address parsing logic
    return None

def find_pattern_positions(text: str, pattern: str, flags: int = 0) -> List[Dict[str, Union[str, int]]]:
    """
    Find all occurrences of a pattern in text and return their positions.
    
    Args:
        text: The text to search in
        pattern: The regex pattern to search for
        flags: Optional regex flags
        
    Returns:
        List of dictionaries containing the match and its position information
    """
    lines = text.split('\n')
    positions = []
    
    for i, line in enumerate(lines):
        for match in re.finditer(pattern, line, flags):
            char_pos = sum(len(l) + 1 for l in lines[:i]) + match.start()
            positions.append({
                'value': match.group(),
                'line': i,
                'char_pos': char_pos
            })
    
    return positions

def parse_zip_txt(doc_section) -> Optional[str]:
    """
    Parse the ZIP code from the document section.
    Looks for ZIP codes that are closest to either:
    1. "(zip code)" label
    2. "Address of principal executive offices" label
    
    Uses proximity-based matching to find the most relevant ZIP code.
    Explicitly avoids the SEC-HEADER section.
    """
    import re
    
    # Convert the document section to text
    text = doc_section.get_text() if hasattr(doc_section, 'get_text') else str(doc_section)
    
    # Remove SEC-HEADER section if present
    if '<SEC-HEADER>' in text:
        header_start = text.find('<SEC-HEADER>')
        header_end = text.find('</SEC-HEADER>')
        if header_end != -1:
            text = text[:header_start] + text[header_end + len('</SEC-HEADER>'):]
    
    # Find all ZIP codes and their positions
    zip_positions = find_pattern_positions(text, r'\b\d{5}(?:-\d{4})?\b')
    
    # Find all label positions
    label_positions = []
    
    # Look for "(zip code)" label
    zip_labels = find_pattern_positions(text, r'\(zip\s*code\)', re.I)
    for pos in zip_labels:
        pos['type'] = 'zip_label'
        label_positions.append(pos)
    
    # Look for "Address of principal executive offices" label
    addr_labels = find_pattern_positions(text, r'Address\s+of\s+principal\s+executive\s+offices', re.I)
    for pos in addr_labels:
        pos['type'] = 'address_label'
        label_positions.append(pos)
    
    if not zip_positions or not label_positions:
        return None
    
    # Calculate distances from each ZIP to each label
    best_distance = float('inf')
    best_zip = None
    
    for zip_pos in zip_positions:
        for label_pos in label_positions:
            # Calculate both line-based and character-based distances
            line_distance = abs(zip_pos['line'] - label_pos['line'])
            char_distance = abs(zip_pos['char_pos'] - label_pos['char_pos'])
            
            # Prioritize line distance but use char distance as tiebreaker
            distance = line_distance * 1000 + (char_distance / 1000)
            
            # Give slight preference to ZIP codes that appear after their labels
            if zip_pos['line'] < label_pos['line']:
                distance += 0.5
            
            # Give preference to zip_label over address_label
            if label_pos['type'] == 'address_label':
                distance += 0.25
            
            if distance < best_distance:
                best_distance = distance
                best_zip = zip_pos['value']
    
    return best_zip

def test_parsing():
    """Test the parsing of ZIP codes and IRS numbers with various test files."""
    test_files = [
        # Apple filings
        ("test_filings/320193/0000912057-00-002128/0000912057-00-002128.txt", "95014", "94-2404110"),
        ("test_filings/320193/0000320193-96-000027/0000320193-96-000027.txt", "95014", "94-2404110"),
        # Sears filing
        ("test_filings/319256/0000891092-04-003383/e18506_8k.txt", "60179", "36-1750680"),
        # Amazon filing
        ("test_filings/1018724/0000891020-98-001352/0000891020-98-001352.txt", "98101", "91-1646860"),
        # Cisco filing
        ("test_filings/858877/0000891618-95-000727/0000891618-95-000727.txt", "95134", "77-0059951")
    ]
    
    print("\nTesting ZIP codes and IRS numbers:")
    print("-" * 80)
    print(f"{'File':<60} {'ZIP':<10} {'IRS':<15} {'ZIP Match':<10} {'IRS Match':<10}")
    print("-" * 80)
    
    for file_path, expected_zip, expected_irs in test_files:
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                soup = BeautifulSoup(content, 'html.parser')
                doc_section = soup.find('document')
                
                if doc_section:
                    found_zip = parse_zip_txt(doc_section)
                    found_irs = parse_irs_no_txt(doc_section)
                    
                    zip_match = found_zip == expected_zip
                    irs_match = found_irs == expected_irs
                    
                    print(f"{file_path:<60} {found_zip or 'None':<10} {found_irs or 'None':<15} "
                          f"{str(zip_match):<10} {str(irs_match):<10}")
        except Exception as e:
            print(f"\nError testing {file_path}: {str(e)}")

if __name__ == "__main__":
    # Test file path
    cik = "320193"
    accession_number = "0000320193-19-000032"
    filings_dir = f"test_filings/{cik}/{accession_number}"

    with open(f"{filings_dir}/{accession_number}.txt", "r") as file:
        text = file.read()
    
    print("\n--- Testing XBRL parsing method ---")
    xbrl_data = parse_xbrl_filing(text)
    print(json.dumps(xbrl_data, indent=2))
    
    print("\n--- Testing HTML parsing method ---")
    html_data = parse_html_filing(text)
    print(json.dumps(html_data, indent=2))
    
    print("\n--- Testing TXT parsing method ---")
    txt_data = parse_txt_filing(text)
    print(json.dumps(txt_data, indent=2))
    
    print("\n--- Testing ZIP code and IRS number parsing ---")
    test_parsing() 