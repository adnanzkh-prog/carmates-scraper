# services/enrichment.py
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Optional

@dataclass
class CarListing:
    title: str
    price: Optional[float]
    year: Optional[int]
    make: str
    model: str
    odometer: Optional[int]
    location: str
    source: str
    url: str
    images: list[str]
    scraped_at: datetime
    
    @property
    def price_per_km(self) -> Optional[float]:
        if self.price and self.odometer and self.odometer > 0:
            return round(self.price / self.odometer, 2)
        return None
    
    @property
    def age_years(self) -> Optional[int]:
        if self.year:
            return datetime.now().year - self.year
        return None

def normalize_make_model(title: str) -> tuple[str, str]:
    """Extract standardized make/model from title"""
    makes = ['Toyota', 'Honda', 'Ford', 'BMW', 'Mercedes', 'Audi', 'Mazda', 'Hyundai', 'Kia']
    title_lower = title.lower()
    
    for make in makes:
        if make.lower() in title_lower:
            # Extract model (word after make)
            pattern = rf'{make}\s+(\w+)'
            match = re.search(pattern, title, re.IGNORECASE)
            model = match.group(1) if match else 'Unknown'
            return make, model
    
    return 'Unknown', 'Unknown'

def deduplicate_listings(listings: list[CarListing]) -> list[CarListing]:
    """Remove duplicates across sources based on VIN or title+price+odo"""
    seen = set()
    unique = []
    
    for listing in listings:
        # Create fingerprint
        fingerprint = f"{listing.make}_{listing.model}_{listing.year}_{listing.odometer}"
        if fingerprint not in seen:
            seen.add(fingerprint)
            unique.append(listing)
    
    return unique
