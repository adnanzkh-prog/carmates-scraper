import hashlib
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from services.enrichment import normalize_make_model

LOCATION_MAP = {
    'sydney': 'sydney',
    'melbourne': 'melbourne',
    'brisbane': 'brisbane',
    'perth': 'perth',
    'adelaide': 'adelaide',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept-Language': 'en-AU,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
}


def _cleanup_text(text: Optional[str]) -> str:
    if not text:
        return ''
    return ' '.join(text.split()).strip()


def _parse_price(text: str) -> Optional[float]:
    match = re.search(r'\$\s?([0-9,]+(?:\.\d+)?)', text)
    if not match:
        return None

    try:
        return float(match.group(1).replace(',', ''))
    except ValueError:
        return None


def _parse_year(title: str) -> Optional[int]:
    match = re.search(r'\b(19|20)\d{2}\b', title)
    return int(match.group(0)) if match else None


def _parse_odometer(text: str) -> Optional[int]:
    match = re.search(r'([0-9,]+)\s*(km|kilometres|kilometers|mi|miles)', text, re.IGNORECASE)
    if not match:
        return None

    value = match.group(1).replace(',', '')
    try:
        return int(value)
    except ValueError:
        return None


def _build_search_urls(query: str, location: str) -> List[str]:
    encoded = quote_plus(query)
    location_path = LOCATION_MAP.get(location.lower(), location.lower())
    urls = [
        f'https://www.facebook.com/marketplace/{location_path}/search/?query={encoded}',
        f'https://www.facebook.com/marketplace/search/?query={encoded}',
        f'https://mbasic.facebook.com/marketplace/search/?query={encoded}',
    ]
    return urls


def _fetch_page(url: str) -> Optional[str]:
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20.0) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return None
            return response.text
    except httpx.RequestError:
        return None


def _extract_title(anchor, container) -> str:
    title = ''
    candidate = anchor.get_text(' ', strip=True)
    if candidate and len(candidate) > 5:
        title = candidate

    if not title and container is not None:
        title = container.get_text(' ', strip=True)

    if title and len(title) > 5:
        return title

    return 'Unknown'


def _parse_listings(html: str, default_location: str, limit: int) -> List[dict]:
    soup = BeautifulSoup(html, 'lxml')
    links = soup.select('a[href*="/marketplace/item/"]')
    found = []
    seen_urls = set()

    for link in links:
        if len(found) >= limit:
            break

        href = link.get('href')
        if not href:
            continue

        url = href if href.startswith('http') else f'https://www.facebook.com{href}'
        if url in seen_urls:
            continue
        seen_urls.add(url)

        container = link.find_parent('div') or link
        raw_text = _cleanup_text(container.get_text(' ', strip=True))
        title = _extract_title(link, container)
        price = _parse_price(raw_text)
        year = _parse_year(title)
        odometer = _parse_odometer(raw_text)
        make, model = normalize_make_model(title)
        image = None

        img = container.select_one('img')
        if img and img.get('src'):
            image = img['src']

        if title == 'Unknown' and not price:
            continue

        listing_id = hashlib.md5(url.encode('utf-8')).hexdigest()

        found.append({
            'id': listing_id,
            'title': title,
            'price': price,
            'year': year,
            'make': make,
            'model': model,
            'odometer': odometer,
            'location': f'{default_location.capitalize()}, Australia',
            'source': 'Facebook Marketplace',
            'url': url,
            'images': [image] if image else [],
            'scraped_at': datetime.utcnow().isoformat(),
            'accuracy_score': 85,
        })

    return found


def scrape_facebook_marketplace(query: str, location: str, limit: int = 20) -> List[dict]:
    if not query:
        return []

    for url in _build_search_urls(query, location):
        html = _fetch_page(url)
        if not html:
            continue

        listings = _parse_listings(html, location, limit)
        if listings:
            return listings[:limit]

    return []
