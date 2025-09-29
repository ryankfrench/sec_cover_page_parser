from dataclasses import dataclass, field
from typing import Optional, List
from .address import Address


@dataclass
class Company:
    """Class to hold individual company information from SEC filings."""
    context_ref: Optional[str] = None
    company_name: Optional[str] = None
    cik: Optional[str] = None
    state_of_incorporation: Optional[str] = None
    commission_file_number: Optional[str] = None
    irs_number: Optional[str] = None
    addresses: List[Address] = field(default_factory=list)
    trading_symbols: List[str] = field(default_factory=list)
    exchanges: List[str] = field(default_factory=list)
    phone_area_code: Optional[str] = None
    phone_local_number: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert the Company object to a dictionary."""
        return {
            'context_ref': self.context_ref,
            'company_name': self.company_name,
            'cik': self.cik,
            'state_of_incorporation': self.state_of_incorporation,
            'commission_file_number': self.commission_file_number,
            'irs_number': self.irs_number,
            'addresses': [addr.to_dict() for addr in self.addresses],
            'trading_symbols': self.trading_symbols,
            'exchanges': self.exchanges,
            'phone_area_code': self.phone_area_code,
            'phone_local_number': self.phone_local_number
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Company':
        """Create a Company object from a dictionary."""
        addresses = [Address.from_dict(addr_data) for addr_data in data.get('addresses', [])]
        return cls(
            context_ref=data.get('context_ref'),
            company_name=data.get('company_name'),
            cik=data.get('cik'),
            state_of_incorporation=data.get('state_of_incorporation'),
            commission_file_number=data.get('commission_file_number'),
            irs_number=data.get('irs_number'),
            addresses=addresses,
            trading_symbols=data.get('trading_symbols', []),
            exchanges=data.get('exchanges', []),
            phone_area_code=data.get('phone_area_code'),
            phone_local_number=data.get('phone_local_number')
        )
    
    def add_address(self, address: Address):
        """Add an address to this company."""
        if address:
            self.addresses.append(address)
    
    def get_primary_address(self) -> Optional[Address]:
        """Get the first/primary address for this company."""
        return self.addresses[0] if self.addresses else None
