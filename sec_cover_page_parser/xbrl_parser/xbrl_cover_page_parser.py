from bs4 import BeautifulSoup
from enum import Enum
from ..models.filing_data import FilingData
from ..models.address import Address, AddressType

def get_dei_value(soup, dei_name):
    tag = soup.find("ix:nonnumeric", attrs={"name": dei_name})
    return tag.get_text(strip=True) if tag else None

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
    return get_dei_value(soup, DocumentEntityInformation.TradingSymbol.value)

def find_exchange(soup):
    """Find the exchange in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.Exchange.value)

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
    result.trading_symbol = find_trading_symbol(soup)
    result.exchange = find_exchange(soup)
    
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
