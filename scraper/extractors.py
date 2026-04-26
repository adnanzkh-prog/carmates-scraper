# scraper/extractors.py
from typing import Optional, List
import logging

def extract_price(soup) -> Optional[float]:
    """Multiple fallback selectors for price extraction"""
    selectors = [
        '[data-testid="price"]',
        '.price-value',
        '.listing-price',
        '[class*="price"]',  # Partial match
        'meta[itemprop="price"]'  # Structured data
    ]
    
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            # Try content attribute first (for meta tags)
            text = element.get('content') or element.get_text(strip=True)
            # Clean and parse
            price_str = text.replace('$', '').replace(',', '').strip()
            try:
                return float(price_str)
            except ValueError:
                continue
    
    # Fallback: JSON-LD structured data
    ld_json = soup.find('script', type='application/ld+json')
    if ld_json:
        try:
            data = json.loads(ld_json.string)
            if 'offers' in data:
                return float(data['offers']['price'])
        except:
            pass
    
    logging.warning(f"Could not extract price from page")
    return None
