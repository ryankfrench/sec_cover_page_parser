from dataclasses import dataclass, field
from typing import Optional, List
from .address import Address
from .company import Company

@dataclass
class FilingData:
    """Class to hold parsed SEC filing information."""
    # Filing-level information (not company-specific)
    file_name: Optional[str] = None
    url: Optional[str] = None
    accession_number: Optional[str] = None
    form: Optional[str] = None
    date: Optional[str] = None
    
    # Company information (can be multiple companies)
    companies: List[Company] = field(default_factory=list)
    
    # Legacy fields for backward compatibility (populated from primary company)
    cik: Optional[str] = None
    company_name: Optional[str] = None
    state_of_incorporation: Optional[str] = None
    commission_file_number: Optional[str] = None
    irs_number: Optional[str] = None
    document_zip: Optional[str] = None
    document_address: Optional[Address] = None
    trading_symbol: Optional[str] = None
    exchange: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the FilingData object to a dictionary."""
        return {
            'file_name': self.file_name,
            'url': self.url,
            'accession_number': self.accession_number,
            'form': self.form,
            'date': self.date,
            'companies': [company.to_dict() for company in self.companies],
            # Legacy fields for backward compatibility
            'cik': self.cik,
            'company_name': self.company_name,
            'state_of_incorporation': self.state_of_incorporation,
            'commission_file_number': self.commission_file_number,
            'irs_number': self.irs_number,
            'document_zip': self.document_zip,
            'document_address': self.document_address.to_dict() if self.document_address else None,
            'trading_symbol': self.trading_symbol,
            'exchange': self.exchange
        }
    
    def add_company(self, company: Company):
        """Add a company to this filing."""
        if company:
            self.companies.append(company)
    
    def get_primary_company(self) -> Optional[Company]:
        """Get the first/primary company in this filing."""
        return self.companies[0] if self.companies else None
    
    def populate_legacy_fields(self):
        """Populate legacy fields from the primary company for backward compatibility."""
        primary_company = self.get_primary_company()
        if primary_company:
            self.cik = primary_company.cik
            self.company_name = primary_company.company_name
            self.state_of_incorporation = primary_company.state_of_incorporation
            self.commission_file_number = primary_company.commission_file_number
            self.irs_number = primary_company.irs_number
            self.document_address = primary_company.get_primary_address()
            self.document_zip = self.document_address.zip_code if self.document_address else None
            self.trading_symbol = primary_company.trading_symbols[0] if primary_company.trading_symbols else None
            self.exchange = primary_company.exchanges[0] if primary_company.exchanges else None 