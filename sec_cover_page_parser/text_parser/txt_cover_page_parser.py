"""
This module provides functions for parsing cover page information from SEC filings in text format.
It extracts key company information such as company name, filing date, state of incorporation,
IRS number, commission file number, and address details.

The parser handles various formatting styles and attempts to normalize the extracted data.
It uses a combination of pattern matching and boundary detection to locate relevant information
in the document structure.

Key functions:
- parse_name_txt: Extracts company name
- parse_date_txt: Extracts filing date
- parse_incorporation_txt: Extracts state of incorporation
- parse_file_no_txt: Extracts commission file number
- parse_irs_no_txt: Extracts IRS employer identification number
- parse_address_txt: Extracts company address
- parse_zip_txt: Extracts ZIP code

The module is designed to be resilient to variations in document formatting and structure,
with fallback mechanisms when primary parsing methods fail.
"""

import math
import re
from typing import Optional

import usaddress
from ..models.filing_data import FilingData
from .. import boundary_parser as bp
from .. import column_parser
from ..utils.text_utils import normalize_whitespace, clean_field_value

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

    label_patterns = [
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

    return bp.find_value_by_label_patterns(text, label_patterns, value_pattern, line_search_limit=(4, 0))

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

                if column_value in label.content or label.content in column_value:
                    address_column = column_name
                    break

        # now that we have the label's column, let's try to determine how many lines above should be used. 
        block = ""
        for line in reversed(columns[:(len(columns) - (label.line_end - label.line_start + 1) - 1)]):
            if line[address_column].strip(' -\t\r\n') == '':
                continue
            new_block = line[address_column] + "\n" + block
            try:
                address = parse_us_address(normalize_whitespace(new_block))
                if all(key in address and address[key] for key in ['address1', 'city', 'state']):
                    break
                block = new_block
            except Exception as e:
                print(f"Error parsing address: {e}")
                address = parse_us_address(normalize_whitespace(block))
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
                address = parse_us_address(normalize_whitespace(new_block))
                block = new_block
            except:
                address = parse_us_address(normalize_whitespace(block))
                break

    return ", ".join(address[key] for key in ['address1', 'address2', 'city', 'state'] if key in address and address[key]) if address else None


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
        
        # Only keep the first 100 liens as it should contain all relative cover page infor
        doc_section = "\n".join(file_content.split("\n")[:100])
        doc_section = re.sub(r'^[-\s]+$', '', doc_section, flags=re.MULTILINE)
            
        # Extract information using helper methods
        result.company_name = parse_name_txt(doc_section)
        result.date = parse_date_txt(doc_section)
        result.state_of_incorporation = parse_incorporation_txt(doc_section)
        result.commission_file_number = parse_file_no_txt(doc_section)
        result.irs_number = parse_irs_no_txt(doc_section)
        # result.document_address = parse_address_txt(doc_section)
        result.document_address = parse_usaddress(doc_section)
        result.document_zip = parse_zip_txt(doc_section)
        
        # Clean up any values - remove extra whitespace and normalize
        for field in result.__dataclass_fields__:
            value = getattr(result, field)
            if value:
                setattr(result, field, clean_field_value(value))
                
    except Exception as e:
        print(f"Error parsing TXT filing: {str(e)}")
        # Don't raise the exception - return partial results if any were found
    
    return result
