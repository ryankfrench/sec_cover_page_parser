from bs4 import BeautifulSoup
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from ..models.filing_data import FilingData
from ..models.address import Address, AddressType
from ..models.company import Company
from ..utils.html_utils import get_dei_value, safe_strip, clean_html_text

# Functions moved to utils.html_utils module for centralized access


def group_dei_tags_by_context(soup: BeautifulSoup) -> Dict[str, List]:
    """
    Group all ix:nonnumeric DEI tags by their contextRef attribute.
    
    Args:
        soup: BeautifulSoup object of the XBRL document
        
    Returns:
        Dictionary with contextRef as key and list of DEI tags as value
    """
    context_groups = defaultdict(list)
    
    # Find all ix:nonNumeric tags with DEI names (try both case variations)
    dei_tags = soup.find_all("ix:nonnumeric", attrs={"name": lambda x: x and x.startswith("dei:")})
    if not dei_tags:
        dei_tags = soup.find_all("ix:nonNumeric", attrs={"name": lambda x: x and x.startswith("dei:")})
    
    for tag in dei_tags:
        # BeautifulSoup may convert contextRef to lowercase contextref
        context_ref = tag.get('contextRef') or tag.get('contextref')
        if context_ref:
            context_groups[context_ref].append(tag)
    
    return dict(context_groups)


def get_dei_value_from_context_group(context_tags: List, dei_name: str, strip_trailing_punctuation: bool = False) -> Optional[str]:
    """
    Extract DEI value from a specific context group with continuation support.
    
    Args:
        context_tags: List of DEI tags for a specific context
        dei_name: The DEI name to search for (e.g., "dei:EntityRegistrantName")
        strip_trailing_punctuation: Whether to strip trailing punctuation
        
    Returns:
        Clean text content or None if not found
    """
    for tag in context_tags:
        if tag.get('name') == dei_name:
            # Start with the initial tag's text
            full_text = tag.get_text()
            
            # Check if this tag has a continuedat attribute
            continuedat_id = tag.get('continuedat')
            
            # Follow the continuation chain
            while continuedat_id:
                # Find the continuation element by its id
                continuation_tag = tag.find_parent().find("ix:continuation", attrs={"id": continuedat_id})
                if not continuation_tag:
                    break
                
                # Append the continuation text
                continuation_text = continuation_tag.get_text()
                if continuation_text:
                    full_text += continuation_text
                
                # Check if this continuation has its own continuedat attribute
                continuedat_id = continuation_tag.get('continuedat')
            
            # Clean the text using our centralized cleaning function
            return clean_html_text(full_text, strip_trailing_punctuation=strip_trailing_punctuation) if full_text else None
    
    return None


def get_dei_list_values_from_context_group(context_tags: List, dei_name: str) -> List[str]:
    """
    Find all DEI values for a given name from a specific context group.
    
    Args:
        context_tags: List of DEI tags for a specific context
        dei_name: The DEI name to search for
        
    Returns:
        List of DEI values found
    """
    values = []
    for tag in context_tags:
        if tag.get('name') == dei_name:
            text = tag.get_text(strip=True)
            if text:
                values.append(text)
    return values


def extract_filing_level_data(soup: BeautifulSoup) -> Dict[str, str]:
    """
    Extract filing-level data that's not company-specific.
    
    Args:
        soup: BeautifulSoup object of the XBRL document
        
    Returns:
        Dictionary with filing-level data
    """
    filing_data = {}
    
    # Get all context groups
    context_groups = group_dei_tags_by_context(soup)
    
    # Look for filing-level data - try each context until we find the data
    for context_ref, context_tags in context_groups.items():
        # Try to get document type and filing date from this context
        doc_type = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.DocumentType.value, strip_trailing_punctuation=True)
        filing_date = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.FilingDate.value, strip_trailing_punctuation=True)
        
        if doc_type and not filing_data.get('form'):
            filing_data['form'] = doc_type
        if filing_date and not filing_data.get('date'):
            filing_data['date'] = filing_date
            
        # If we found both pieces of filing-level data, we can break
        if filing_data.get('form') and filing_data.get('date'):
            break
    
    return filing_data


def identify_companies_by_registrant_name(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """
    Identify unique companies by their EntityRegistrantName and map them to their contextRefs.
    
    Args:
        soup: BeautifulSoup object of the XBRL document
        
    Returns:
        Dictionary mapping company names to lists of their associated contextRefs
    """
    context_groups = group_dei_tags_by_context(soup)
    company_contexts = {}
    
    # Find all EntityRegistrantName entries and their contexts
    for context_ref, context_tags in context_groups.items():
        company_name = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.CompanyName.value)
        if company_name:
            if company_name not in company_contexts:
                company_contexts[company_name] = []
            company_contexts[company_name].append(context_ref)
    
    return company_contexts


def parse_company_from_multiple_contexts(company_name: str, context_refs: List[str], all_context_groups: Dict[str, List]) -> Company:
    """
    Parse company information from multiple context groups that belong to the same company.
    
    Args:
        company_name: The name of the company
        context_refs: List of context references for this company
        all_context_groups: All context groups from the document
        
    Returns:
        Company object with parsed information from all relevant contexts
    """
    company = Company()
    company.company_name = company_name
    
    # Use the first context as the primary context
    primary_context_ref = context_refs[0]
    company.context_ref = primary_context_ref
    
    # Collect all tags for this company across all its contexts
    all_company_tags = []
    for context_ref in context_refs:
        if context_ref in all_context_groups:
            all_company_tags.extend(all_context_groups[context_ref])
    
    # Extract basic company information (prioritize primary context)
    primary_tags = all_context_groups.get(primary_context_ref, [])
    
    company.cik = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.CIK.value)
    company.state_of_incorporation = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.IncorporationState.value)
    company.commission_file_number = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.SECFileNumber.value, strip_trailing_punctuation=True)
    company.irs_number = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.IRSEmployerNumber.value, strip_trailing_punctuation=True)
    company.phone_area_code = get_dei_value_from_context_group(primary_tags, "dei:CityAreaCode")
    company.phone_local_number = get_dei_value_from_context_group(primary_tags, "dei:LocalPhoneNumber")
    
    # Extract address information from primary context
    address1 = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.AddressLine1.value, strip_trailing_punctuation=True)
    address2 = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.AddressLine2.value, strip_trailing_punctuation=True)
    city = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.City.value, strip_trailing_punctuation=True)
    state = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.State.value)
    zip_code = get_dei_value_from_context_group(primary_tags, DocumentEntityInformation.ZipCode.value, strip_trailing_punctuation=True)
    
    # Create primary address if we have any address information
    if any([address1, address2, city, state, zip_code]):
        address = Address(
            address_line1=address1,
            address_line2=address2,
            city=city,
            state=state,
            zip_code=zip_code,
            address_type=AddressType.BUSINESS
        )
        company.add_address(address)
    
    # Extract trading symbols and exchanges from all contexts for this company
    for context_ref in context_refs:
        if context_ref in all_context_groups:
            context_tags = all_context_groups[context_ref]
            symbols = get_dei_list_values_from_context_group(context_tags, DocumentEntityInformation.TradingSymbol.value)
            exchanges = get_dei_list_values_from_context_group(context_tags, DocumentEntityInformation.Exchange.value)
            
            # Add unique symbols and exchanges
            for symbol in symbols:
                if symbol not in company.trading_symbols:
                    company.trading_symbols.append(symbol)
            for exchange in exchanges:
                if exchange not in company.exchanges:
                    company.exchanges.append(exchange)
    
    return company


def parse_company_from_context(context_ref: str, context_tags: List) -> Company:
    """
    Parse company information from a specific context group.
    
    Args:
        context_ref: The context reference identifier
        context_tags: List of DEI tags for this context
        
    Returns:
        Company object with parsed information
    """
    company = Company(context_ref=context_ref)
    
    # Extract basic company information
    company.company_name = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.CompanyName.value)
    company.cik = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.CIK.value)
    company.state_of_incorporation = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.IncorporationState.value)
    company.commission_file_number = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.SECFileNumber.value, strip_trailing_punctuation=True)
    company.irs_number = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.IRSEmployerNumber.value, strip_trailing_punctuation=True)
    company.phone_area_code = get_dei_value_from_context_group(context_tags, "dei:CityAreaCode")
    company.phone_local_number = get_dei_value_from_context_group(context_tags, "dei:LocalPhoneNumber")
    
    # Extract address information
    address1 = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.AddressLine1.value, strip_trailing_punctuation=True)
    address2 = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.AddressLine2.value, strip_trailing_punctuation=True)
    city = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.City.value, strip_trailing_punctuation=True)
    state = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.State.value)
    zip_code = get_dei_value_from_context_group(context_tags, DocumentEntityInformation.ZipCode.value, strip_trailing_punctuation=True)
    
    # Create address if we have any address information
    if any([address1, address2, city, state, zip_code]):
        address = Address(
            address_line1=address1,
            address_line2=address2,
            city=city,
            state=state,
            zip_code=zip_code,
            address_type=AddressType.BUSINESS
        )
        company.add_address(address)
    
    # Extract trading symbols and exchanges
    company.trading_symbols = get_dei_list_values_from_context_group(context_tags, DocumentEntityInformation.TradingSymbol.value)
    company.exchanges = get_dei_list_values_from_context_group(context_tags, DocumentEntityInformation.Exchange.value)
    
    return company


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
    # Try both case variations of the tag name
    tags = soup.find_all("ix:nonnumeric", attrs={"name": dei_name})
    if not tags:
        tags = soup.find_all("ix:nonNumeric", attrs={"name": dei_name})
    
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
    address1 = get_dei_value(soup, DocumentEntityInformation.AddressLine1.value, strip_trailing_punctuation=True)
    address2 = get_dei_value(soup, DocumentEntityInformation.AddressLine2.value, strip_trailing_punctuation=True)
    city = get_dei_value(soup, DocumentEntityInformation.City.value, strip_trailing_punctuation=True)
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
    return get_dei_value(soup, DocumentEntityInformation.ZipCode.value, strip_trailing_punctuation=True)

def find_incorporation(soup):
    """Find the state of incorporation in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.IncorporationState.value)

def find_irs_employer_number(soup):
    """Find the IRS employer identification number in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.IRSEmployerNumber.value, strip_trailing_punctuation=True)

def find_document_number(soup):
    """Find the document number in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.SECFileNumber.value, strip_trailing_punctuation=True)

def find_filing_date(soup):
    """Find the filing date in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.FilingDate.value, strip_trailing_punctuation=True)

def find_document_type(soup):
    """Find the document type (e.g., 10-K, 8-K)."""
    return get_dei_value(soup, DocumentEntityInformation.DocumentType.value, strip_trailing_punctuation=True)

def find_date(soup):
    """Find the filing date in the coverpage."""
    return get_dei_value(soup, DocumentEntityInformation.FilingDate.value, strip_trailing_punctuation=True)

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
        # print(f"Error finding exchange: {e}") # this weas too verbose and probably should use logging instead
        return exchanges

def parse_coverpage(html_doc: str) -> FilingData:
    """Parse the coverpage of an XBRL document with support for multiple companies."""
    soup = BeautifulSoup(html_doc, 'html.parser')
    
    result = FilingData()
    
    # Extract filing-level data (form, date, etc.)
    filing_data = extract_filing_level_data(soup)
    result.form = filing_data.get('form')
    result.date = filing_data.get('date')
    
    # Identify companies by their EntityRegistrantName
    company_contexts = identify_companies_by_registrant_name(soup)
    
    if not company_contexts:
        # No companies found, return empty result
        return result
    
    # Get all context groups for reference
    all_context_groups = group_dei_tags_by_context(soup)
    
    if len(company_contexts) == 1:
        # Single company case - safe to assume all data refers to this company
        company_name = list(company_contexts.keys())[0]
        all_context_refs = list(all_context_groups.keys())
        company = parse_company_from_multiple_contexts(company_name, all_context_refs, all_context_groups)
        result.add_company(company)
    else:
        # Multiple companies case - use contextRef to segregate data
        for company_name, context_refs in company_contexts.items():
            company = parse_company_from_multiple_contexts(company_name, context_refs, all_context_groups)
            result.add_company(company)
    
    # Populate legacy fields for backward compatibility
    result.populate_legacy_fields()
    
    return result


# Legacy parsing functions for backward compatibility
def parse_coverpage_legacy(html_doc: str):
    """Legacy parse function that returns data in the old format."""
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
