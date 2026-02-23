from dataclasses import dataclass
from typing import Optional
from enum import Enum

class AddressType(Enum):
    """Enumeration for address types."""
    BUSINESS = "business"
    MAILING = "mailing"

@dataclass
class Address:
    """Class to hold address information."""
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    address_line3: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    address_type: AddressType = AddressType.BUSINESS

    def to_dict(self) -> dict:
        """Convert the Address object to a dictionary."""
        return {
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'address_line3': self.address_line3,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'address_type': self.address_type.value
        }

    def __str__(self) -> str:
        """Return a formatted string representation of the address."""
        parts = []
        if self.address_line1:
            parts.append(self.address_line1)
        if self.address_line2:
            parts.append(self.address_line2)
        if self.address_line3:
            parts.append(self.address_line3)
        if self.city and self.state:
            parts.append(f"{self.city}, {self.state}")
        elif self.city:
            parts.append(self.city)
        elif self.state:
            parts.append(self.state)
        if self.zip_code:
            parts.append(self.zip_code)
        
        return " ".join(parts) if parts else ""

    @classmethod
    def from_dict(cls, data: dict) -> 'Address':
        """Create an Address object from a dictionary."""
        address_type = AddressType(data.get('address_type', 'Business'))
        return cls(
            address_line1=data.get('address_line1'),
            address_line2=data.get('address_line2'),
            address_line3=data.get('address_line3'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            address_type=address_type
        )
