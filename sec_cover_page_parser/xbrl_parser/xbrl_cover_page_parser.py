from bs4 import BeautifulSoup
from enum import Enum
from ..models.filing_data import FilingData
from ..models.address import Address, AddressType
from ..utils.html_utils import get_dei_value, safe_strip, clean_html_text

# Functions moved to utils.html_utils module for centralized access


def find_unique_values_with_indices(values):
    """
    Find unique values in a list and return them with their first occurrence indices.
    
    Args:
        values: List of values to process
        
    Returns:
        tuple: (unique_values, first_occurrence_indices)
            - unique_values: list of unique values found
            - first_occurrence_indices: list of indices where each unique value first appears
    """
    if not values:
        return [], []
    
    unique_values = []
    first_occurrence_indices = []
    seen_values = {}
    
    for i, value in enumerate(values):
        if value not in seen_values:
            seen_values[value] = i
            unique_values.append(value)
            first_occurrence_indices.append(i)
    
    return unique_values, first_occurrence_indices

def get_dei_list_values(soup, dei_name):
    """
    Find all DEI values for a given name and return unique values with their first occurrence indices.
    
    Args:
        soup: BeautifulSoup object of the HTML document
        dei_name: The DEI name to search for
        
    Returns:
        tuple: (unique_values, first_occurrence_indices)
            - unique_values: list of unique DEI values found
            - first_occurrence_indices: list of indices where each unique value first appears
    """
    tags = soup.find_all("ix:nonnumeric", attrs={"name": dei_name})
    
    if not tags:
        return []
    
    # Use the utility function to find unique values and indices
    return [tag.get_text(strip=True) for tag in tags]

def has_xbrl(html_doc: str):
    soup = BeautifulSoup(html_doc, 'html.parser')
    return get_dei_value(soup, DocumentEntityInformation.CompanyName.value) is not None

def find_name(soup):
    """Find the company name in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.CompanyName.value)

def find_address(soup):
    """Find the company address in the coverpage."""
    address1 = get_dei_value(soup, DocumentEntityInformation.AddressLine1.value)
    address2 = get_dei_value(soup, DocumentEntityInformation.AddressLine2.value)
    city = get_dei_value(soup, DocumentEntityInformation.City.value)
    state = get_dei_value(soup, DocumentEntityInformation.State.value)
    zip_code = find_zip(soup)
    
    return Address(
        address_line1=address1,
        address_line2=address2,
        city=city,
        state=state,
        zip_code=zip_code,
        address_type=AddressType.BUSINESS
    )

def find_zip(soup):
    """Find the ZIP code in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.ZipCode.value)

def find_incorporation(soup):
    """Find the state of incorporation in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.IncorporationState.value)

def find_irs_employer_number(soup):
    """Find the IRS employer identification number in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.IRSEmployerNumber.value)

def find_document_number(soup):
    """Find the document number in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.SECFileNumber.value)

def find_filing_date(soup):
    """Find the filing date in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.FilingDate.value)

def find_document_type(soup):
    """Find the document type (e.g., 10-K, 8-K)."""
    return get_dei_value(soup, DocumentEntityInformation.DocumentType.value)

def find_date(soup):
    """Find the filing date in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.FilingDate.value)

def find_trading_symbol(soup):
    """Find the trading symbol in the coverpage."""
    tickers = get_dei_list_values(soup, DocumentEntityInformation.TradingSymbol.value)
    return find_unique_values_with_indices(tickers)

def find_exchange(soup, indices = None):
    """Find the exchange in the coverpage."""
    exchanges = get_dei_list_values(soup, DocumentEntityInformation.Exchange.value)
    try:
        return exchanges[indices] if indices else exchanges
    except Exception as e:
        print(f"Error finding exchange: {e}")
        return exchanges

def parse_coverpage(html_doc: str):
    """Parse the coverpage of an XBRL document."""
    soup = BeautifulSoup(html_doc, 'html.parser')
        
    result = FilingData()
    result.company_name = find_name(soup)
    result.form = find_document_type(soup)
    result.document_address = find_address(soup)
    result.document_zip = find_zip(soup)
    result.state_of_incorporation = find_incorporation(soup)
    result.irs_number = find_irs_employer_number(soup)
    result.commission_file_number = find_document_number(soup)
    result.date = find_date(soup)

    # for trading symbols, we need to match them with their exchange
    result.trading_symbol, indices = find_trading_symbol(soup)
    result.exchange = find_exchange(soup, indices)
    
    return result

class DocumentEntityInformation(Enum):
    """Constants for XBRL document entity information tags."""
    DocumentType = "dei:DocumentType"
    FilingDate = "dei:DocumentPeriodEndDate"
    CompanyName = "dei:EntityRegistrantName"
    CIK = "dei:EntityCentralIndexKey"
    IncorporationState = "dei:EntityIncorporationStateCountryCode"
    AddressLine1 = "dei:EntityAddressAddressLine1"
    AddressLine2 = "dei:EntityAddressAddressLine2"
    City = "dei:EntityAddressCityOrTown"
    State = "dei:EntityAddressStateOrProvince"
    ZipCode = "dei:EntityAddressPostalZipCode"
    IRSEmployerNumber = "dei:EntityTaxIdentificationNumber"
    SECFileNumber = "dei:EntityFileNumber"
    TradingSymbol = "dei:TradingSymbol"
    Exchange = "dei:SecurityExchangeName"


# Test code has been moved to tests/test_xbrl_parser.py
