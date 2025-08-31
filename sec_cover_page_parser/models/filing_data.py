from dataclasses import dataclass
from typing import Optional
from .address import Address

@dataclass
class FilingData:
    """Class to hold parsed SEC filing information."""
    file_name: Optional[str] = None
    url: Optional[str] = None
    cik: Optional[str] = None
    accession_number: Optional[str] = None
    form: Optional[str] = None
    date: Optional[str] = None
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
            'cik': self.cik,
            'accession_number': self.accession_number,
            'form': self.form,
            'date': self.date,
            'company_name': self.company_name,
            'state_of_incorporation': self.state_of_incorporation,
            'commission_file_number': self.commission_file_number,
            'irs_number': self.irs_number,
            'document_zip': self.document_zip,
            'document_address': self.document_address.to_dict() if self.document_address else None,
            'trading_symbol': self.trading_symbol,
            'exchange': self.exchange
        } 