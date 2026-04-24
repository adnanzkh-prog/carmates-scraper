from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Listing:
    title: str
    price: Optional[int]
    description: str
    location: Optional[str]
    contact_numbers: List[str]
    posted_time: Optional[str]
    url: str
    source: str
