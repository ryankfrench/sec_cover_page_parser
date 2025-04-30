from dataclasses import dataclass
from typing import Optional

@dataclass
class FilingData:
    """Class to hold parsed SEC filing information."""
    cik: Optional[str] = None
    form: Optional[str] = None
    date: Optional[str] = None
    company_name: Optional[str] = None
    state_of_incorporation: Optional[str] = None
    commission_file_number: Optional[str] = None
    irs_number: Optional[str] = None
    document_address: Optional[str] = None
    document_city: Optional[str] = None
    document_state: Optional[str] = None
    document_zip: Optional[str] = None
    trading_symbol: Optional[str] = None
    exchange: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert the FilingData object to a dictionary."""
        return {
            'cik': self.cik,
            'form': self.form,
            'date': self.date,
            'company_name': self.company_name,
            'state_of_incorporation': self.state_of_incorporation,
            'commission_file_number': self.commission_file_number,
            'irs_number': self.irs_number,
            'document_address': self.document_address,
            'document_city': self.document_city,
            'document_state': self.document_state,
            'document_zip': self.document_zip,
            'trading_symbol': self.trading_symbol,
            'exchange': self.exchange
        } 