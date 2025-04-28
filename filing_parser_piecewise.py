import re
import json
import os # Import os to check file existence

class AddressExtractionMethod:
    XBRL_TAGS = "xbrl_tags"
    PRINCIPAL_OFFICE = "principal_office"
    TABLE_CELL = "table_cell"
    SEPARATE_LINES = "separate_lines"
    HEADER = "header"

def clean_html_text(text):
    """Clean HTML tags and normalize whitespace from text."""
    if not text:
        return None
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove any leading/trailing whitespace
    return text.strip()

def extract_xbrl_address(doc_text):
    """Extract address components from XBRL tags."""
    components = {
        "street": re.search(r'<ix:nonNumeric[^>]*name="dei:EntityAddressAddressLine1"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE),
        "city": re.search(r'<ix:nonNumeric[^>]*name="dei:EntityAddressCityOrTown"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE),
        "state": re.search(r'<ix:nonNumeric[^>]*name="dei:EntityAddressStateOrProvince"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE),
        "zip": re.search(r'<ix:nonNumeric[^>]*name="dei:EntityAddressPostalZipCode"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE)
    }
    return components if all(components.values()) else None

def extract_principal_office_address(doc_text):
    """Extract address from 'Address of principal executive offices' format."""
    # First try to find address in HTML format before the label
    addr_match = re.search(
        r'<[^>]*>([^<>]+?)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?Address of principal executive offices\)?',
        doc_text,
        re.IGNORECASE | re.MULTILINE
    )
    
    if addr_match:
        # Clean up the address text and split into components
        addr_text = addr_match.group(1).strip()
        # Remove any extra whitespace and normalize commas
        addr_text = re.sub(r'\s+', ' ', addr_text)
        addr_parts = [p.strip() for p in addr_text.split(',')]
        
        if len(addr_parts) >= 3:
            # Last part typically contains state and zip
            state_zip = addr_parts[-1].strip().split()
            if len(state_zip) >= 2:
                return {
                    "street": type('Match', (), {'group': lambda x: addr_parts[0]}),
                    "city": type('Match', (), {'group': lambda x: addr_parts[-2]}),
                    "state": type('Match', (), {'group': lambda x: state_zip[0]}),
                    "zip": type('Match', (), {'group': lambda x: state_zip[-1]})
                }
    
    # If HTML format fails, try the original comma-separated format
    addr_match = re.search(
        r'([^,\n]+),\s*([^,\n]+),\s*([A-Za-z]{2})\s+(\d{5}(?:-\d{4})?)\s*(?:\n|\s)*\(Address of principal executive offices\)',
        doc_text,
        re.IGNORECASE
    )
    if addr_match:
        return {
            "street": type('Match', (), {'group': lambda x: addr_match.group(1)}),
            "city": type('Match', (), {'group': lambda x: addr_match.group(2)}),
            "state": type('Match', (), {'group': lambda x: addr_match.group(3)}),
            "zip": type('Match', (), {'group': lambda x: addr_match.group(4)})
        }
    
    return None

def extract_table_cell_address(doc_text):
    """Extract address from table cell or paragraph format."""
    # Look for address in a paragraph or cell before the label
    addr_match = re.search(
        r'(?:<(?:P|TD)[^>]*>)\s*(?:<[^>]*>)*([^<>]+?)(?:</[^>]*>)*\s*(?:<[^>]*>)*\s*\(?Address of (?:principal )?executive offices\)?',
        doc_text,
        re.IGNORECASE | re.MULTILINE
    )
    
    if addr_match:
        # Clean up the address text and split into components
        addr_text = addr_match.group(1).strip()
        # Remove any extra whitespace and normalize commas
        addr_text = re.sub(r'\s+', ' ', addr_text)
        addr_parts = [p.strip() for p in addr_text.split(',')]
        
        if len(addr_parts) >= 3:
            # Last part typically contains state and zip
            state_zip = addr_parts[-1].strip().split()
            if len(state_zip) >= 2:
                return {
                    "street": type('Match', (), {'group': lambda x: addr_parts[0]}),
                    "city": type('Match', (), {'group': lambda x: addr_parts[-2]}),
                    "state": type('Match', (), {'group': lambda x: state_zip[0]}),
                    "zip": type('Match', (), {'group': lambda x: state_zip[-1]})
                }
    
    return None

def extract_separate_lines_address(doc_text):
    """Extract address from separate lines format."""
    addr_section = re.search(
        r'(?:<[^>]*>)*([^<>]+?)\s*(?:</[^>]*>)*\s*\(?Address of (?:principal )?executive offices\)?.*?(?:<[^>]*>)*\s*(\d{5}(?:-\d{4})?)\s*(?:</[^>]*>)*\s*\(?Zip Code\)?',
        doc_text[:5000],
        re.IGNORECASE | re.DOTALL
    )
    if addr_section:
        addr_text = addr_section.group(1).strip()
        addr_parts = [p.strip() for p in addr_text.split(',') if p.strip()]
        if len(addr_parts) >= 3:
            return {
                "street": type('Match', (), {'group': lambda x: addr_parts[0]}),
                "city": type('Match', (), {'group': lambda x: addr_parts[-2]}),
                "state": type('Match', (), {'group': lambda x: addr_parts[-1]}),
                "zip": type('Match', (), {'group': lambda x: addr_section.group(2)})
            }
    return None

def extract_header_address(header_text):
    """Extract address from SEC-HEADER section."""
    business_address_section = re.search(r"BUSINESS ADDRESS:.*?\n(.*?)(?:\n\s*\n|\Z)", header_text, re.DOTALL | re.IGNORECASE)
    if business_address_section:
        address_text = business_address_section.group(1)
        components = {
            "street": re.search(r"STREET 1:\s+(.*)", address_text, re.IGNORECASE),
            "city": re.search(r"CITY:\s+(.*)", address_text, re.IGNORECASE),
            "state": re.search(r"STATE:\s+([A-Z]{2})", address_text, re.IGNORECASE),
            "zip": re.search(r"ZIP:\s+(\d{5}(?:-\d{4})?)", address_text, re.IGNORECASE)
        }
        return components if all(components.values()) else None
    return None

def clean_address_components(components):
    """Clean HTML/XML tags from address components."""
    cleaned = {}
    for key, match in components.items():
        if match:
            value = match.group(1).strip()
            value = re.sub(r'<[^>]+>', '', value)
            if key == "state":
                value = value.upper()
            cleaned[key] = value
    return cleaned

def extract_company_name(doc_text):
    """Extract company name from document section."""
    # Try XBRL tag first
    company_name = re.search(r'<ix:nonNumeric[^>]*name="dei:EntityRegistrantName"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE)
    if not company_name:
        # Try HTML format with charter specification
        company_name = re.search(
            r'(?:<[^>]*>)*([^<>]+?)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?Exact name of registrant as specified in its charter\)?',
            doc_text,
            re.IGNORECASE | re.MULTILINE
        )
    if company_name:
        return clean_html_text(company_name.group(1)).replace('-', '').strip()
    return None

def extract_state_of_incorporation(doc_text):
    """Extract state of incorporation from document section."""
    # Try XBRL tag first
    state_inc = re.search(r'<ix:nonNumeric[^>]*name="dei:EntityIncorporationStateCountryCode"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE)
    if not state_inc:
        # Try HTML format with various labels
        patterns = [
            r'(?:<[^>]*>)*([^<>]+?)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?State or other jurisdiction of[^<>]*?incorporation\)?',
            r'(?:<[^>]*>)*\(?A[n]?\s+([^<>]+?)\s+Corporation\)?',
            r'(?:<[^>]*>)*([^<>]{2,})(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?State of Incorporation\)?'
        ]
        for pattern in patterns:
            match = re.search(pattern, doc_text, re.IGNORECASE | re.MULTILINE)
            if match:
                state_name = clean_html_text(match.group(1))
                if len(state_name) == 2:
                    return state_name.upper()
    elif state_inc:
        return clean_html_text(state_inc.group(1)).upper()
    return None

def extract_commission_file_number(doc_text):
    """Extract commission file number from document section."""
    # Try HTML format with various labels
    patterns = [
        r'(?:<[^>]*>)*([0-9-]+)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?Commission File Number\)?',
        r'File Number[^<>]*?(?:</[^>]*>)*\s*(?:<[^>]*>)*\s*([0-9-]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, doc_text, re.IGNORECASE | re.MULTILINE)
        if match:
            return clean_html_text(match.group(1))
    return None

def extract_irs_number(doc_text):
    """Extract IRS employer identification number from document section."""
    # Try HTML format with various labels
    patterns = [
        r'(?:<[^>]*>)*([0-9-]+)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?IRS Employer[^<>]*?Identification[^<>]*?\)?',
        r'(?:<[^>]*>)*([0-9-]+)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?EIN\)?'
    ]
    for pattern in patterns:
        match = re.search(pattern, doc_text, re.IGNORECASE | re.MULTILINE)
        if match:
            return clean_html_text(match.group(1))
    return None

def extract_trading_symbol(doc_text):
    """Extract trading symbol from document section."""
    # Try XBRL tag first
    trading_symbol = re.search(r'<ix:nonNumeric[^>]*name="dei:TradingSymbol"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE)
    if not trading_symbol:
        # Try HTML format with various labels
        patterns = [
            r'(?:<[^>]*>)*([A-Z]+)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?Trading Symbol\(?s\)?\)?',
            r'Trading Symbol\(?s\)?[^<>]*?(?:</[^>]*>)*\s*(?:<[^>]*>)*\s*([A-Z]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, doc_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return clean_html_text(match.group(1))
    elif trading_symbol:
        return clean_html_text(trading_symbol.group(1))
    return None

def extract_exchange(doc_text):
    """Extract exchange information from document section."""
    # Try XBRL tag first
    exchange = re.search(r'<ix:nonNumeric[^>]*name="dei:SecurityExchangeName"[^>]*>(.*?)</ix:nonNumeric>', doc_text, re.IGNORECASE)
    if not exchange:
        # Try HTML format with various labels
        patterns = [
            r'(?:<[^>]*>)*([^<>\n]+?Stock Exchange)(?:</[^>]*>)*?\s*(?:<[^>]*>)*?\s*\(?(?:exchange[^<>]*?on[^<>]*?which[^<>]*?registered|Name of each exchange)\)?',
            r'(?:exchange[^<>]*?on[^<>]*?which[^<>]*?registered|Name of each exchange)[^<>]*?(?:</[^>]*>)*\s*(?:<[^>]*>)*\s*([^<>\n]+?Stock Exchange)'
        ]
        for pattern in patterns:
            match = re.search(pattern, doc_text, re.IGNORECASE | re.MULTILINE)
            if match:
                return clean_html_text(match.group(1))
    elif exchange:
        return clean_html_text(exchange.group(1))
    return None

def extract_header_fields(header_text):
    """Extract various fields from the SEC-HEADER section."""
    fields = {}
    
    # Company Name
    name_match = re.search(r"COMPANY CONFORMED NAME:\s+(.*)", header_text, re.IGNORECASE)
    if name_match:
        fields["company_name"] = name_match.group(1).strip()
    
    # State of Incorporation
    inc_state_match = re.search(r"STATE OF INCORPORATION:\s+([A-Z]{2})", header_text, re.IGNORECASE)
    if inc_state_match:
        fields["state_of_incorporation"] = inc_state_match.group(1).strip().upper()
    
    # Date of Filing
    filing_date_match = re.search(r"FILED AS OF DATE:\s+(\d{8})", header_text, re.IGNORECASE)
    if filing_date_match:
        date_str = filing_date_match.group(1)
        fields["date_of_filing"] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    
    # Form Type
    form_type_match = re.search(r"(?:CONFORMED SUBMISSION TYPE|FORM TYPE):\s+([\w-]+)", header_text, re.IGNORECASE)
    if form_type_match:
        fields["form_type"] = form_type_match.group(1).strip()
    
    # Commission File Number
    sec_file_match = re.search(r"SEC FILE NUMBER:\s+([\d-]+)", header_text, re.IGNORECASE)
    if sec_file_match:
        fields["commission_file_number"] = sec_file_match.group(1).strip()
    
    # IRS Number
    irs_match = re.search(r"IRS NUMBER:\s+([\d-]+)", header_text, re.IGNORECASE)
    if irs_match:
        fields["irs_number"] = irs_match.group(1).strip()
    
    return fields

def extract_filing_info_with_document_address(filing_text):
    """
    Extracts key information from an SEC filing text, prioritizing information from the document
    section over the header section. Uses modern XBRL tags when available, with fallbacks to
    traditional text patterns.

    Args:
        filing_text: A string containing the SEC filing content.

    Returns:
        A dictionary containing the extracted information and tracking of extraction methods.
    """
    info = {
        "company_name": None,
        "header_address": None,
        "document_address": None,
        "full_address": None,
        "state": None,
        "zip": None,
        "state_of_incorporation": None,
        "date_of_filing": None,
        "form_type": None,
        "commission_file_number": None,
        "irs_number": None,
        "trading_symbol": None,
        "exchange": None,
        "address_extraction_method": None,
        "document_extracted_fields": []  # Track which fields were extracted from document
    }

    # Extract document section
    doc_section = re.search(r"</SEC-HEADER>(.*)", filing_text, re.DOTALL | re.IGNORECASE)
    if doc_section:
        doc_text = doc_section.group(1)
        
        # Extract document section fields and track successful extractions
        field_extractors = {
            "company_name": extract_company_name,
            "state_of_incorporation": extract_state_of_incorporation,
            "commission_file_number": extract_commission_file_number,
            "irs_number": extract_irs_number,
            "trading_symbol": extract_trading_symbol,
            "exchange": extract_exchange
        }
        
        for field, extractor in field_extractors.items():
            value = extractor(doc_text)
            if value:
                info[field] = value
                info["document_extracted_fields"].append(field)
        
        # Try each address extraction method in order of preference
        address_components = None
        for extraction_method, extractor in [
            (AddressExtractionMethod.XBRL_TAGS, lambda: extract_xbrl_address(doc_text)),
            (AddressExtractionMethod.PRINCIPAL_OFFICE, lambda: extract_principal_office_address(doc_text)),
            (AddressExtractionMethod.TABLE_CELL, lambda: extract_table_cell_address(doc_text)),
            (AddressExtractionMethod.SEPARATE_LINES, lambda: extract_separate_lines_address(doc_text))
        ]:
            address_components = extractor()
            if address_components:
                info["address_extraction_method"] = extraction_method
                break

        if address_components:
            cleaned = clean_address_components(address_components)
            address_parts = [cleaned[k] for k in ["street", "city", "state", "zip"] if k in cleaned]
            if address_parts:
                info["document_address"] = ", ".join(address_parts)
                info["state"] = cleaned.get("state")
                info["zip"] = cleaned.get("zip")
                info["full_address"] = info["document_address"]
                info["document_extracted_fields"].append("address")

    # Extract from header as fallback
    header_match = re.search(r"<SEC-HEADER>.*?</SEC-HEADER>", filing_text, re.DOTALL | re.IGNORECASE)
    if header_match:
        header_text = header_match.group(0)
        
        # Extract header fields
        header_fields = extract_header_fields(header_text)
        
        # Only use header fields if not already set from document section
        for field, value in header_fields.items():
            if not info.get(field):
                info[field] = value
        
        # Extract header address if needed
        if not info.get("full_address"):
            header_components = extract_header_address(header_text)
            if header_components:
                cleaned = clean_address_components(header_components)
                address_parts = [cleaned[k] for k in ["street", "city", "state", "zip"] if k in cleaned]
                if address_parts:
                    info["header_address"] = ", ".join(address_parts)
                    if not info.get("state"):
                        info["state"] = cleaned.get("state")
                    if not info.get("zip"):
                        info["zip"] = cleaned.get("zip")
                    if not info.get("full_address"):
                        info["full_address"] = info["header_address"]
                        info["address_extraction_method"] = AddressExtractionMethod.HEADER

    # Filter out None values before returning
    return {k: v for k, v in info.items() if v is not None}

# --- Main execution ---
def process_filing(file_path):
    """Process a single filing file and extract information."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(50000)  # Read first 50K chars
        
        if content:
            extracted_data = extract_filing_info_with_document_address(content)
            print(f"\nExtracted data from {file_path}:")
            print(f"Address extraction method: {extracted_data.get('address_extraction_method', 'None')}")
            print(json.dumps({k: v for k, v in extracted_data.items() if k != 'address_extraction_method'}, indent=2))
            return extracted_data
        else:
            error = {"error": "File empty or could not read header"}
            print(f"\nError processing {file_path}: {error['error']}")
            return error

    except Exception as e:
        error = {"error": str(e)}
        print(f"\nError processing {file_path}: {error['error']}")
        return error

def process_directory(directory):
    """Process all filing files in a directory and its subdirectories."""
    all_filings_data = {}
    
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".txt") and '-' in filename and not filename.endswith(".hdr.sgml"):
                file_path = os.path.join(root, filename)
                all_filings_data[file_path] = process_filing(file_path)
    
    return all_filings_data

def sample_filing(cik, accession_number):
    """Sample a single filing from a given CIK and accession number."""
    filings_dir = f"test_filings/{cik}"
    file_path = f"{filings_dir}/{accession_number}/{accession_number}.txt"
    return process_filing(file_path)

if __name__ == "__main__":
    cik = "320193"
    accession_number = "0000320193-19-000032"
    # filings_dir = f"test_filings/{cik}"
    # all_data = process_directory(filings_dir)
    # print("\n--- Summary of All Extracted Data ---")
    # print(json.dumps(all_data, indent=2)) 

    print(json.dumps(sample_filing(cik, accession_number), indent=2))