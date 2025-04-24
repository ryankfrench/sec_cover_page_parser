import re
import json
import os # Import os to check file existence

def extract_filing_info(filing_text):
    """
    Extracts key information from an SEC filing text using regex patterns
    designed to handle variations in format based on content.

    Args:
        filing_text: A string containing the SEC filing content.

    Returns:
        A dictionary containing the extracted information.
    """
    info = {
        "company_name": None,
        "full_address": None,
        "state": None, # Business address state
        "zip": None, # Business address zip
        "state_of_incorporation": None,
        "date_of_filing": None,
        "form_type": None,
        "commission_file_number": None,
        "irs_number": None,
        "trading_symbol": None,  # Often not in the header
        "exchange": None, # SROS
    }

    # --- Company Name ---
    # Primary pattern (newer filings)
    name_match = re.search(r"COMPANY CONFORMED NAME:\s+(.*)", filing_text, re.IGNORECASE)
    if name_match:
        info["company_name"] = name_match.group(1).strip()
    else:
        # Fallback for older formats (looks for text after charter specification)
        name_match_alt = re.search(r"\(Exact name of registrant as specified in its charter\)\s*\n+\s*(.+?)\s*\n", filing_text, re.IGNORECASE | re.MULTILINE)
        if name_match_alt:
            info["company_name"] = name_match_alt.group(1).strip().replace('-', '') # Remove potential ----- lines

    # --- Business Address Components ---
    street, city, state, zip_code = None, None, None, None
    # Primary pattern (newer filings)
    business_address_section = re.search(r"BUSINESS ADDRESS:\s*\n(.*?)\n\n", filing_text, re.DOTALL | re.IGNORECASE)
    if business_address_section:
        address_text = business_address_section.group(1)
        street_match = re.search(r"STREET 1:\s+(.*)", address_text, re.IGNORECASE)
        if street_match: street = street_match.group(1).strip()
        city_match = re.search(r"CITY:\s+(.*)", address_text, re.IGNORECASE)
        if city_match: city = city_match.group(1).strip()
        state_match = re.search(r"STATE:\s+([A-Z]{2})", address_text, re.IGNORECASE)
        if state_match: state = state_match.group(1).strip().upper()
        zip_match = re.search(r"ZIP:\s+(\d{5}(?:-\d{4})?)", address_text, re.IGNORECASE)
        if zip_match: zip_code = zip_match.group(1).strip()
    else:
        # Fallback for address pattern directly under offices description (older filings)
        addr_match_alt = re.search(r"\(Address of principal executive offices\)\s*\n+\s*(.+?),\s*([^,]+?),\s*([A-Za-z]+)\s+(\d{5}(?:-\d{4})?)\s*\n", filing_text, re.MULTILINE | re.IGNORECASE)
        if addr_match_alt:
            street = addr_match_alt.group(1).strip()
            city = addr_match_alt.group(2).strip()
            # State might be full name here, need conversion logic if desired
            state = addr_match_alt.group(3).strip()
            zip_code = addr_match_alt.group(4).strip()
            # Attempt to get 2-letter state code if we got a full name
            if len(state) > 2:
                 # Basic check, might need a proper mapping
                 state_abbr_match = re.search(r"\(State or other jurisdiction of\s+incorporation.*?\)\s*([\w\s]+?)\s+\d+-", filing_text, re.IGNORECASE)
                 if state_abbr_match:
                     potential_state_abbr = state_abbr_match.group(1).strip()
                     if len(potential_state_abbr) == 2 and potential_state_abbr.isalpha():
                         state = potential_state_abbr.upper() # Use abbreviation if found
                     else:
                         state = state # Keep full name if abbr not found or invalid


    if state and len(state) == 2: info["state"] = state.upper()
    if zip_code: info["zip"] = zip_code

    # --- Construct Full Address ---
    address_parts = [part for part in [street, city, state, zip_code] if part]
    if address_parts:
        info["full_address"] = ", ".join(address_parts)

    # --- State of Incorporation ---
    # Primary pattern
    inc_state_match = re.search(r"STATE OF INCORPORATION:\s+([A-Z]{2})", filing_text, re.IGNORECASE)
    if inc_state_match:
        info["state_of_incorporation"] = inc_state_match.group(1).strip().upper()
    else:
        # Fallback for older format (looks for state near Commission File Number section)
        older_format_inc_state_match = re.search(r"\(State or other jurisdiction of\s+incorporation.*?\)\s*([\w\s]+?)\s+(\d+-\d+)\s+([\d-]+)", filing_text, re.IGNORECASE | re.DOTALL)
        if older_format_inc_state_match:
            potential_state = older_format_inc_state_match.group(1).strip()
            # Basic check if it looks like a state abbreviation
            if len(potential_state) == 2 and potential_state.isalpha():
                 info["state_of_incorporation"] = potential_state.upper()
            # Could add a lookup for full state names to abbreviations if needed here

    # --- Date of Filing ---
    # This format seems relatively consistent
    filing_date_match = re.search(r"FILED AS OF DATE:\s+(\d{8})", filing_text, re.IGNORECASE)
    if filing_date_match:
        date_str = filing_date_match.group(1)
        info["date_of_filing"] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}" # Format YYYY-MM-DD

    # --- Form Type ---
    # Using non-capturing group for alternative names
    form_type_match = re.search(r"(?:CONFORMED SUBMISSION TYPE|FORM TYPE):\s+([\w-]+)", filing_text, re.IGNORECASE)
    if form_type_match:
         info["form_type"] = form_type_match.group(1).strip()

    # --- Commission File Number ---
    # Primary: Look in FILING VALUES section
    sec_file_match = re.search(r"FILING VALUES:.*?\n\s*SEC FILE NUMBER:\s+([\d-]+)", filing_text, re.DOTALL | re.IGNORECASE)
    if sec_file_match:
        info["commission_file_number"] = sec_file_match.group(1).strip()
    else:
        # Fallback: Look in the older horizontal format near jurisdiction
        older_format_file_match = re.search(r"\(State or other jurisdiction of\s+incorporation.*?\)\s*([\w\s]+?)\s+(\d+-\d+)\s+([\d-]+)", filing_text, re.IGNORECASE | re.DOTALL)
        if older_format_file_match:
            info["commission_file_number"] = older_format_file_match.group(2).strip() # Middle number

    # --- IRS Number ---
    # Primary pattern
    irs_match = re.search(r"IRS NUMBER:\s+([\d-]+)", filing_text, re.IGNORECASE)
    if irs_match:
        info["irs_number"] = irs_match.group(1).strip()
    else:
        # Fallback: Look in the older horizontal format near jurisdiction
        older_format_irs_match = re.search(r"\(State or other jurisdiction of\s+incorporation.*?\)\s*([\w\s]+?)\s+(\d+-\d+)\s+([\d-]+)", filing_text, re.IGNORECASE | re.DOTALL)
        if older_format_irs_match:
            info["irs_number"] = older_format_irs_match.group(3).strip() # Last number

    # --- Exchange (SROS) ---
    # This seems less common but checking the specific field
    exchange_match = re.search(r"SROS:\s+(\w+)", filing_text, re.IGNORECASE)
    if exchange_match:
        info["exchange"] = exchange_match.group(1).strip().upper()

    # Trading symbol is not reliably found in these header sections

    # Filter out None values before returning for cleaner output
    return {k: v for k, v in info.items() if v is not None}

def extract_filing_info_two_pass(filing_text):
    """
    Extracts key information from an SEC filing using a two-pass approach:
    1. Extracts data from the structured <SEC-HEADER>.
    2. Updates/overwrites with data found in the formatted body text.

    Args:
        filing_text: A string containing the full SEC filing content.

    Returns:
        A dictionary containing the extracted information.
    """
    info = {
        "company_name": None,
        "full_address": None,
        "state": None, # Business address state
        "zip": None, # Business address zip
        "state_of_incorporation": None,
        "date_of_filing": None,
        "form_type": None,
        "commission_file_number": None,
        "irs_number": None,
        "trading_symbol": None,
        "exchange": None, # SROS
    }

    # --- Pass 1: Extract from <SEC-HEADER> structure ---
    # Limit search to the header initially if possible, though patterns are specific
    header_match = re.search(r"<SEC-HEADER>(.*?)</SEC-HEADER>", filing_text, re.DOTALL | re.IGNORECASE)
    header_text = header_match.group(1) if header_match else filing_text # Fallback to whole text if no header tags

    # Company Name (from header)
    name_match_hdr = re.search(r"COMPANY CONFORMED NAME:\s+(.*)", header_text, re.IGNORECASE)
    if name_match_hdr:
        info["company_name"] = name_match_hdr.group(1).strip()

    # Business Address (from header structure)
    business_address_section_hdr = re.search(r"BUSINESS ADDRESS:\s*\n(.*?)(?:\n\s*\n|\Z)", header_text, re.DOTALL | re.IGNORECASE)
    if business_address_section_hdr:
        address_text_hdr = business_address_section_hdr.group(1)
        street_hdr = re.search(r"STREET 1:\s+(.*)", address_text_hdr, re.IGNORECASE)
        city_hdr = re.search(r"CITY:\s+(.*)", address_text_hdr, re.IGNORECASE)
        state_hdr = re.search(r"STATE:\s+([A-Z]{2})", address_text_hdr, re.IGNORECASE)
        zip_hdr = re.search(r"ZIP:\s+(\d{5}(?:-\d{4})?)", address_text_hdr, re.IGNORECASE)
        _street = street_hdr.group(1).strip() if street_hdr else None
        _city = city_hdr.group(1).strip() if city_hdr else None
        _state = state_hdr.group(1).strip().upper() if state_hdr else None
        _zip = zip_hdr.group(1).strip() if zip_hdr else None
        if _state: info["state"] = _state
        if _zip: info["zip"] = _zip
        _address_parts = [part for part in [_street, _city, _state, _zip] if part]
        if _address_parts:
            info["full_address"] = ", ".join(_address_parts)


    # State of Incorporation (from header)
    inc_state_match_hdr = re.search(r"STATE OF INCORPORATION:\s+([A-Z]{2})", header_text, re.IGNORECASE)
    if inc_state_match_hdr:
        info["state_of_incorporation"] = inc_state_match_hdr.group(1).strip().upper()

    # Date of Filing (usually reliable in header)
    filing_date_match = re.search(r"FILED AS OF DATE:\s+(\d{8})", header_text, re.IGNORECASE)
    if filing_date_match:
        date_str = filing_date_match.group(1)
        info["date_of_filing"] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    # Form Type (usually reliable in header)
    form_type_match = re.search(r"(?:CONFORMED SUBMISSION TYPE|FORM TYPE):\s+([\w-]+)", header_text, re.IGNORECASE)
    if form_type_match:
         info["form_type"] = form_type_match.group(1).strip()

    # Commission File Number (from header FILING VALUES)
    sec_file_match_hdr = re.search(r"FILING VALUES:.*?\n\s*SEC FILE NUMBER:\s+([\d-]+)", header_text, re.DOTALL | re.IGNORECASE)
    if sec_file_match_hdr:
        info["commission_file_number"] = sec_file_match_hdr.group(1).strip()

    # IRS Number (from header COMPANY DATA)
    irs_match_hdr = re.search(r"IRS NUMBER:\s+([\d-]+)", header_text, re.IGNORECASE)
    if irs_match_hdr:
        info["irs_number"] = irs_match_hdr.group(1).strip()

    # Exchange / SROS (from header)
    exchange_match_hdr = re.search(r"SROS:\s+(\w+)", header_text, re.IGNORECASE)
    if exchange_match_hdr:
        info["exchange"] = exchange_match_hdr.group(1).strip().upper()


    # --- Pass 2: Update/Overwrite from Formatted Body Text ---
    # Use the *full* filing text for this pass

    # Company Name (from body - overwrite if header name was generic or missing)
    # Look for the name specified after "Exact name of registrant..."
    name_match_body = re.search(r"\(Exact name of registrant as specified in its charter\)\s*\n+([^\n]+?)\s*\n", filing_text, re.IGNORECASE | re.MULTILINE)
    if name_match_body:
        body_name = name_match_body.group(1).strip().replace('-', '').strip() # Clean potential underlines
        # Overwrite header name only if it seems more specific or header missed it
        if not info["company_name"] or info["company_name"] == "COMPANY CONFORMED NAME:":
             info["company_name"] = body_name
        # Optional: Add logic here if you *always* prefer the body name

    # Address (from body - generally preferred)
    # Look for address lines following "(Address of principal executive offices)"
    addr_match_body = re.search(
        r"\(Address of principal executive offices\)\s*\n+" # Anchor text
        r"\s*([^\n]+?)\s*\n"              # Street Address (Group 1)
        r"(?:\s*([^\n]+?)\s*\n)?"         # Optional Second Street Line (Group 2) - Not explicitly used but captures pattern
        r"\s*([^,\n]+?),\s*([A-Za-z\s]+?)\s+(\d{5}(?:-\d{4})?)\s*\n", # City (Group 3), State (Group 4), Zip (Group 5)
        filing_text,
        re.IGNORECASE | re.MULTILINE
    )
    if addr_match_body:
        street_body = addr_match_body.group(1).strip()
        city_body = addr_match_body.group(3).strip()
        state_body = addr_match_body.group(4).strip()
        zip_body = addr_match_body.group(5).strip()

        # Attempt to get 2-letter state code if full name was captured
        if len(state_body) > 2:
             # Look for the state abbreviation in the horizontal section as a hint
             state_abbr_hint_match = re.search(r"\(State or other jurisdiction of\s+incorporation.*?\)\s*([\w\s]+?)\s+\d+-", filing_text, re.IGNORECASE)
             if state_abbr_hint_match:
                 potential_state_abbr = state_abbr_hint_match.group(1).strip()
                 # Crude check if hint matches start of full name and is 2 letters
                 if len(potential_state_abbr) == 2 and potential_state_abbr.isalpha() and state_body.upper().startswith(potential_state_abbr):
                     state_body_abbr = potential_state_abbr.upper()
                 else:
                    state_body_abbr = state_body # Keep original if hint invalid/mismatch
             else:
                 state_body_abbr = state_body # Keep original if no hint
        else:
            state_body_abbr = state_body.upper() # Assume it was already abbr

        # Update info dict - preferring body address info
        if state_body_abbr and len(state_body_abbr) == 2 : info["state"] = state_body_abbr
        if zip_body: info["zip"] = zip_body
        _address_parts_body = [part for part in [street_body, city_body, state_body_abbr if (state_body_abbr and len(state_body_abbr)==2) else state_body, zip_body] if part]
        if _address_parts_body:
            info["full_address"] = ", ".join(_address_parts_body)


    # State of Incorporation / Commission File / IRS Number (from body horizontal layout)
    # Update only if header data was missing for these specific fields
    horizontal_match_body = re.search(
        r"\(State or other jurisdiction of\s+incorporation.*?\)\s*" # Anchor text
        r"([\w\s]+?)\s+"              # State (Group 1)
        r"(\d+-\d+)\s+"               # Commission File Number (Group 2)
        r"([\d-]+)",                  # IRS Number (Group 3)
        filing_text,
        re.IGNORECASE | re.DOTALL
    )
    if horizontal_match_body:
        state_inc_body = horizontal_match_body.group(1).strip()
        comm_file_body = horizontal_match_body.group(2).strip()
        irs_num_body = horizontal_match_body.group(3).strip()

        # Update State of Inc if header missed it
        if not info["state_of_incorporation"]:
            # Try to get abbreviation if full name
            if len(state_inc_body) == 2 and state_inc_body.isalpha():
                 info["state_of_incorporation"] = state_inc_body.upper()
            # Else: could add state name to abbr mapping here if needed

        # Update Comm File Num if header missed it
        if not info["commission_file_number"]:
            info["commission_file_number"] = comm_file_body

        # Update IRS Num if header missed it
        if not info["irs_number"]:
            info["irs_number"] = irs_num_body


    # Filter out None values before returning for cleaner output
    return {k: v for k, v in info.items() if v is not None}

# --- Main execution ---
# Define the directory containing the filings relative to the script location
filings_dir = "test_filings/320193" # Adjust if your structure is different

all_filings_data = {}

# Walk through the directory structure
for root, dirs, files in os.walk(filings_dir):
    for filename in files:
        # Process only .txt files that seem like the main filing doc
        if filename.endswith(".txt") and '-' in filename and not filename.endswith(".hdr.sgml"):
            file_path = os.path.join(root, filename)
            print(f"--- Processing: {file_path} ---")
            try:
                # Actual file reading
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read only the beginning of the file, headers are usually near the top
                    # Adjust max_read_chars if headers can be much further down
                    max_read_chars = 10000
                    content = f.read(max_read_chars)

                if content:
                    extracted_data = extract_filing_info(content)
                    all_filings_data[file_path] = extracted_data
                    print(json.dumps(extracted_data, indent=2))
                else:
                     all_filings_data[file_path] = {"error": "File empty or could not read header"}
                     print("  Error: File empty or could not read header section.")

            except FileNotFoundError:
                 print(f"  Error: File not found at {file_path}")
                 all_filings_data[file_path] = {"error": "File not found"}
            except Exception as e:
                print(f"  Error processing file {file_path}: {e}")
                all_filings_data[file_path] = {"error": str(e)}

print("\n--- All Extracted Data ---")
print(json.dumps(all_filings_data, indent=2))

# Optional: Save the results to a JSON file
# output_file = "extracted_sec_data.json"
# with open(output_file, "w") as outfile:
#     json.dump(all_filings_data, outfile, indent=2)
# print(f"\nResults saved to {output_file}")