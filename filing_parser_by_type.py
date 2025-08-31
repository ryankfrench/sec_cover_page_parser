import os
from bs4 import BeautifulSoup
from typing import Dict, Optional, Union, List, Tuple
import re
import json
import math

import requests
from models.filing_data import FilingData
import column_parser
import boundary_parser as bp
import usaddress
import text_parser.txt_cover_page_parser as txt_parser
import html_parser.html_cover_page_parser as html_parser
import xbrl_parser.xbrl_cover_page_parser as xbrl_parser
import test_filings.download_filing as download_filing
import subprocess

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

def parse_cover_page(cik: int, accession_number: str, user_agent: str = 'Your Name your_email@address.com') -> FilingData:
    # Format CIK and accession number
    accession = accession_number.replace('-', '')
    
    # Define base URL for SEC EDGAR
    base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}"
    
    # Define headers with User-Agent
    headers = {
        'User-Agent': user_agent
    }

    # Create formatted accession with dashes
    acc_with_dashes = f"{accession[0:10]}-{accession[10:12]}-{accession[12:]}"

    # Define file URLs
    filing_txt_url = f"{base_url}/{accession}/{acc_with_dashes}.txt"

    filing_txt_response = requests.get(filing_txt_url, headers=headers)
    filing_txt_response.raise_for_status()

    filing_name = download_filing.extract_filename(filing_txt_response.text)
    
    filing_data: Optional[FilingData] = None

    # Try to use the (usually richer) HTML/XBRL document first
    if filing_name is not None:
        try:
            filing_url = f"{base_url}/{accession}/{filing_name}"
            filing_response = requests.get(filing_url, headers=headers)
            filing_response.raise_for_status()

            filing_data = parse_cover_page_by_type(filing_name, filing_response.text)
            filing_data.file_name = filing_name
            filing_data.url = filing_url
        except Exception as e:
            # Log the problem and fall through to the .txt fallback
            print(f"Error parsing {filing_name}, will fall back to .txt: {e}")

    # Fallback: parse the raw .txt version only if needed
    if filing_data is None:
        filing_data = txt_parser.parse_txt_filing(filing_txt_response.text)
        filing_data.file_name = filing_name
        filing_data.url = filing_txt_url

    filing_data.accession_number = accession_number
    return filing_data
    
def parse_cover_page_by_type(filename: str, file_content: str) -> FilingData:
    if filename.endswith('.htm'):
        if xbrl_parser.has_xbrl(file_content):
            return xbrl_parser.parse_xbrl_filing(file_content)
        else:
            return html_parser.parse_coverpage(file_content)
    else:
        return txt_parser.parse_txt_filing(file_content)

def test_cover_page_parsing():
    cik = 1493040
    accession_number = "0001056520-11-000233"
    results = parse_cover_page(cik, accession_number, "Ryan French rfrench@chapman.edu")
    print(results)
        

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
        # Food concepts
        ("test_filings/703901/0000703901-98-000003/0000703901-98-000003.txt", "Food Concepts, Inc.", "33073", "13-3124057", "", "6601 Lyons Road, Suite C-12, Coconut Creek, Florida", "Nevada", "January 26, 1998"),
    ]
    
    print("\nTesting company names, ZIP codes, IRS numbers, file numbers, addresses, incorporation states, and dates:")
    print("-" * 250)
    print(f"{'File':<70} {'Name':<20} {'ZIP':<10} {'IRS':<15} {'File No':<15} {'Address':<40} {'Incorporation':<15} {'Date':<15} {'Name Match':<10} {'ZIP Match':<10} {'IRS Match':<10} {'File No Match':<10} {'Address Match':<10} {'Incorp Match':<10} {'Date Match':<10}")
    print("-" * 250)
    
    for file_path, expected_name, expected_zip, expected_irs, expected_file_no, expected_address, expected_incorporation, expected_date in test_files:
        try:
            with open(file_path, 'r') as file:
                content = file.read()

                filename = os.path.basename(file_path)
                data = parse_cover_page_by_type(filename, content)

                name_match = (data.company_name or '').lower() == (expected_name or '').lower()
                zip_match = (data.document_zip or '').lower() == (expected_zip or '').lower()
                irs_match = (data.irs_number or '').lower() == (expected_irs or '').lower()
                file_no_match = (data.commission_file_number or '').lower() == (expected_file_no or '').lower()
                address_match = (data.document_address or '').lower() == (expected_address or '').lower()
                incorp_match = (data.state_of_incorporation or '').lower() == (expected_incorporation or '').lower()
                date_match = (data.date or '').lower() == (expected_date or '').lower()
                
                print(f"{file_path:<70} {data.company_name or 'None':<20} {data.document_zip or 'None':<10} {data.irs_number or 'None':<15} {data.commission_file_number or 'None':<15} "
                        f"{data.document_address or 'None':<40} {data.state_of_incorporation or 'None':<15} {data.date or 'None':<15} {str(name_match):<10} {str(zip_match):<10} {str(irs_match):<10} "
                        f"{str(file_no_match):<10} {str(address_match):<10} {str(incorp_match):<10} {str(date_match):<10}")

        except Exception as e:
            print(f"\nError testing {file_path}: {str(e)}")

def test_html_parsing():
    path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    with open(path, "r") as file:
        html_doc = file.read()
        results = html_parser.parse_coverpage(html_doc)
        print(results)

def test_html_html2text():
    path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    import html2text, pathlib, sys

    html_doc = pathlib.Path(path).read_text(encoding="utf-8")
    h = html2text.HTML2Text()
    h.body_width   = 0          # keep original line lengths – no re-wrapping
    h.unicode_snob = True       # keep "–", "…" etc. as Unicode
    h.ignore_links = False      # include link targets as footnotes

    txt = h.handle(html_doc)

    pathlib.Path("coverpage_html2text.txt").write_text(txt, encoding="utf-8")

def test_html_markdownify():
    from markdownify import markdownify as md
    path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    import pathlib, sys

    html_doc = pathlib.Path(path).read_text(encoding="utf-8")
    txt = md(html_doc, heading_style="ATX")   # returns markdown / plain text

    pathlib.Path("coverpage_markdownify.txt").write_text(txt, encoding="utf-8")

def test_html_w3m():
    import shutil, subprocess, pathlib

    def html_to_text_w3m(html_str: str, width: int = 72) -> str:
        """Return lynx-style text without touching the filesystem."""
        if shutil.which("w3m") is None:
            raise RuntimeError("w3m is not installed or not on PATH")

        cmd = ["w3m", "-dump", "-cols", str(width), "-T", "text/html"]
        out = subprocess.run(
            cmd,
            input=html_str,   # HTML goes in here
            text=True,        # tells subprocess that "input" is a str, not bytes
            capture_output=True,
            check=True        # will raise if w3m returns non-zero
        )
        return out.stdout

    # usage --------------------------------------------------------------
    path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    with open(path, encoding="utf-8") as fp:
        html = fp.read()

    txt = html_to_text_w3m(html, width=70)
    pathlib.Path("coverpage_w3m.txt").write_text(txt, encoding="utf-8")

def test_html_lynx():
    import shutil, subprocess, pathlib

    def html_to_text_lynx(html_str: str, width: int = 72) -> str:
        cmd = ["lynx", "-stdin", "-dump", f"-width={width}", "-assume_charset=UTF-8"]
        return subprocess.check_output(cmd, input=html_str,
                                    text=True).strip()

    # usage --------------------------------------------------------------
    path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    with open(path, encoding="utf-8") as fp:
        html = fp.read()

    txt = html_to_text_lynx(html, width=70)
    pathlib.Path("coverpage_lynx.txt").write_text(txt, encoding="utf-8")

def test_html_elinks():
    import shutil, subprocess, pathlib

    def html_to_text_elinks(html, width=70):
        """Render HTML to plain-text using links/links2 without temporary files."""
        cmd = [
            "elinks",          # use ELinks, superior stdin support
            "-dump",
            "-dump-width", str(width),   # control wrapping width
            "-force-html",               # treat stdin as HTML
            "/dev/stdin"                 # read HTML from stdin
        ]
        return subprocess.check_output(cmd, input=html, text=True)

    # usage --------------------------------------------------------------
    path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    with open(path, encoding="utf-8") as fp:
        html = fp.read()

    txt = html_to_text_elinks(html, width=70)
    pathlib.Path("coverpage_elinks.txt").write_text(txt, encoding="utf-8")

def test_html_links2():
    import shutil, subprocess, pathlib, tempfile, os

    def html_to_text_links2(html: str, width: int = 72) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            tmp.write(html.encode("utf-8"))
            tmp_path = tmp.name          # links2 needs a regular path

        try:
            out = subprocess.check_output(
                ["links2", "-dump", "-width", str(width), tmp_path],
                text=True
            )
            return out
        finally:
            os.unlink(tmp_path)          # clean up

    # usage --------------------------------------------------------------
    path = "test_filings/1341439/0001564590-22-023099/orcl-8k_20220613.htm"
    with open(path, encoding="utf-8") as fp:
        html = fp.read()

    txt = html_to_text_links2(html, width=70)
    pathlib.Path("coverpage_links2.txt").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    # test_txt_sample()
    # test_txt_parsing()
    # test_html_parsing()
    # test_html_w3m()
    # test_html_markdownify()
    # test_html_html2text()
    # test_html_lynx()
    # test_html_elinks()
    # test_html_links2()
    test_cover_page_parsing()