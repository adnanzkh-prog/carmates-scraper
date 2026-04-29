"""
CarMates API v3.1 - Production-Ready Multi-Source Scraping
With strict accuracy filtering, manual submission, and source reliability scoring
"""

import os
import re
import json
import logging
import time
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ─── ENVIRONMENT VARIABLES ──────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://carmates-scraper.pages.dev").strip()
PORT = int(os.getenv("PORT", "8080"))
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")

# ─── PYDANTIC MODELS ──────────────────────────────────────────────────
class CarListing(BaseModel):
    id: str
    title: str
    price: Optional[float] = None
    year: Optional[int] = None
    make: str
    model: str
    odometer: Optional[int] = None
    location: str
    source: str
    url: str
    images: List[str] = []
    scraped_at: str
    seller_name: Optional[str] = None
    condition: Optional[str] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    accuracy_score: int = 0  # 0-100 relevance score
    verified: bool = False   # Manually verified by user

class SearchResponse(BaseModel):
    query: str
    filters: dict
    results: List[CarListing]
    total: int
    search_time_ms: int
    cached: bool = False
    sources: List[str] = []

class ManualSubmission(BaseModel):
    url: str = Field(..., description="Facebook Marketplace or other listing URL")
    title: Optional[str] = None
    price: Optional[float] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    odometer: Optional[int] = None
    location: Optional[str] = None
    images: List[str] = []
    notes: Optional[str] = None

# ─── CONFIGURATION ────────────────────────────────────────────────────
FB_LOCATION_IDS = {
    "sydney": "110884905406898",
    "melbourne": "110568095311578",
    "brisbane": "108479165840750",
    "perth": "108363952520166",
    "adelaide": "108225355867673",
}

GUMTREE_LOCATIONS = {
    "sydney": "sydney",
    "melbourne": "melbourne",
    "brisbane": "brisbane",
    "perth": "perth",
    "adelaide": "adelaide",
}

# ─── IN-MEMORY DATABASE (Replace with PostgreSQL later) ───────────────
class CarDatabase:
    def __init__(self):
        self._listings: Dict[str, CarListing] = {}
        self._manual_submissions: List[ManualSubmission] = []
        self._load_sample_data()
    
    def _load_sample_data(self):
        """Initialize with high-quality sample data"""
        samples = [
            CarListing(
                id="cs-001", title="2022 Toyota Camry Ascent Auto", price=28990, year=2022,
                make="Toyota", model="Camry", odometer=45000, location="Sydney, NSW",
                source="Carsales", url="https://www.carsales.com.au/cars/details/2022-toyota-camry-ascent",
                images=["https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=400"],
                scraped_at=datetime.utcnow().isoformat(), transmission="Automatic", fuel_type="Petrol",
                accuracy_score=95, verified=True
            ),
            CarListing(
                id="cs-002", title="2021 Mazda CX-5 Maxx Sport Auto FWD", price=32500, year=2021,
                make="Mazda", model="CX-5", odometer=32000, location="Melbourne, VIC",
                source="Carsales", url="https://www.carsales.com.au/cars/details/2021-mazda-cx-5-maxx-sport",
                images=["https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400"],
                scraped_at=datetime.utcnow().isoformat(), transmission="Automatic", fuel_type="Petrol",
                accuracy_score=92, verified=True
            ),
            CarListing(
                id="ebay-001", title="2022 Toyota RAV4 GX Auto 2WD", price=27800, year=2022,
                make="Toyota", model="RAV4", odometer=38000, location="Brisbane, QLD",
                source="eBay Australia", url="https://www.ebay.com.au/itm/123456789",
                images=["https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=400"],
                scraped_at=datetime.utcnow().isoformat(), transmission="Automatic", fuel_type="Petrol",
                accuracy_score=88, verified=False
            ),
            CarListing(
                id="fb-001", title="2020 Honda CR-V VTi Auto FWD - Excellent Condition", price=24500, year=2020,
                make="Honda", model="CR-V", odometer=62000, location="Perth, WA",
                source="Facebook Marketplace", url="https://www.facebook.com/marketplace/item/sample-crv",
                images=["https://images.unsplash.com/photo-1605816988064-baf6d7006279?w=400"],
                scraped_at=datetime.utcnow().isoformat(), seller_name="Sarah M.", condition="Used - Excellent",
                accuracy_score=75, verified=False
            ),
            CarListing(
                id="gt-001", title="2019 Hyundai i30 Active Auto", price=19500, year=2019,
                make="Hyundai", model="i30", odometer=78000, location="Adelaide, SA",
                source="Gumtree", url="https://www.gumtree.com.au/s-ad/adelaide/2019-hyundai-i30",
                images=["https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=400"],
                scraped_at=datetime.utcnow().isoformat(), transmission="Automatic", fuel_type="Petrol",
                accuracy_score=82, verified=True
            ),
            CarListing(
                id="cs-003", title="2023 BMW X5 xDrive30d Auto", price=89500, year=2023,
                make="BMW", model="X5", odometer=12000, location="Sydney, NSW",
                source="Carsales", url="https://www.carsales.com.au/cars/details/2023-bmw-x5-xdrive30d",
                images=["https://images.unsplash.com/photo-1555215695-3004980adade?w=400"],
                scraped_at=datetime.utcnow().isoformat(), transmission="Automatic", fuel_type="Diesel",
                accuracy_score=96, verified=True
            ),
            CarListing(
                id="fb-002", title="2021 Ford Ranger XLT Auto 4x4 Turbo Diesel", price=45500, year=2021,
                make="Ford", model="Ranger", odometer=55000, location="Brisbane, QLD",
                source="Facebook Marketplace", url="https://www.facebook.com/marketplace/item/sample-ranger",
                images=["https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=400"],
                scraped_at=datetime.utcnow().isoformat(), seller_name="Mike's Autos", condition="Used - Like New",
                accuracy_score=70, verified=False
            ),
            CarListing(
                id="ebay-002", title="2022 Kia Sportage S Auto 2WD", price=26500, year=2022,
                make="Kia", model="Sportage", odometer=42000, location="Melbourne, VIC",
                source="eBay Australia", url="https://www.ebay.com.au/itm/987654321",
                images=["https://images.unsplash.com/photo-1606220838315-056192d5e927?w=400"],
                scraped_at=datetime.utcnow().isoformat(), transmission="Automatic", fuel_type="Petrol",
                accuracy_score=85, verified=False
            ),
            CarListing(
                id="gt-002", title="2020 Mercedes-Benz C200 Auto", price=42900, year=2020,
                make="Mercedes", model="C200", odometer=38000, location="Sydney, NSW",
                source="Gumtree", url="https://www.gumtree.com.au/s-ad/sydney/2020-mercedes-c200",
                images=["https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=400"],
                scraped_at=datetime.utcnow().isoformat(), transmission="Automatic", fuel_type="Petrol",
                accuracy_score=90, verified=True
            ),
            CarListing(
                id="manual-001", title="2023 Audi Q5 40 TDI Auto quattro", price=67500, year=2023,
                make="Audi", model="Q5", odometer=8000, location="Perth, WA",
                source="Manual Submission", url="https://www.facebook.com/marketplace/item/manual-q5",
                images=["https://images.unsplash.com/photo-1603584173870-7f23fdae1b7a?w=400"],
                scraped_at=datetime.utcnow().isoformat(), seller_name="Premium Motors", condition="Used - Like New",
                accuracy_score=100, verified=True
            ),
        ]
        for s in samples:
            self._listings[s.id] = s
    
    def add_listing(self, listing: CarListing):
        self._listings[listing.id] = listing
    
    def get_all(self) -> List[CarListing]:
        return list(self._listings.values())
    
    def add_manual(self, submission: ManualSubmission) -> CarListing:
        """Convert manual submission to verified listing"""
        make, model = extract_make_model(submission.title or "")
        year = submission.year or extract_year(submission.title or "")
        
        listing = CarListing(
            id=f"manual-{hash(submission.url) & 0xFFFFFFFF}",
            title=submission.title or "Unknown",
            price=submission.price,
            year=year,
            make=submission.make or make,
            model=submission.model or model,
            odometer=submission.odometer,
            location=submission.location or "Australia",
            source="Manual Submission",
            url=submission.url,
            images=submission.images or [],
            scraped_at=datetime.utcnow().isoformat(),
            accuracy_score=100,  # Manual submissions are 100% accurate
            verified=True
        )
        self._listings[listing.id] = listing
        self._manual_submissions.append(submission)
        return listing
    
    def search(self, filters: dict) -> List[CarListing]:
        results = list(self._listings.values())
        
        q = filters.get("q", "").lower()
        make = filters.get("make", "").lower()
        model = filters.get("model", "").lower()
        location = filters.get("location", "").lower()
        min_p = filters.get("min_price", 0)
        max_p = filters.get("max_price", 999999)
        year_from = filters.get("year_from", 1900)
        year_to = filters.get("year_to", 2030)
        source_filter = filters.get("source", "all")
        
        # Apply filters
        if q:
            results = [r for r in results if q in r.title.lower()]
        if make:
            results = [r for r in results if r.make.lower() == make]
        if model:
            results = [r for r in results if model in r.model.lower()]
        if location:
            results = [r for r in results if location in r.location.lower()]
        if source_filter != "all":
            results = [r for r in results if r.source.lower().replace(" ", "-") == source_filter.lower()]
        
        results = [r for r in results if min_p <= (r.price or 0) <= max_p]
        results = [r for r in results if year_from <= (r.year or 0) <= year_to]
        
        # Sort by accuracy score (highest first)
        results.sort(key=lambda x: x.accuracy_score, reverse=True)
        
        return results[:filters.get("limit", 50)]

db = CarDatabase()

# ─── ACCURACY & FILTERING ENGINE ──────────────────────────────────────
class AccuracyEngine:
    """
    Solves client's pain point: Facebook returns garbage listings.
    This engine scores every listing 0-100 based on data quality.
    """
    
    RED_FLAGS = [
        'wanted', 'buying', 'looking for', 'parts', 'wrecking', 
        'damaged', 'repairable', 'write off', 'statutory write-off',
        'project', 'no rego', 'no registration', 'unregistered',
        'swap', 'trade', 'exchange', 'px welcome', 'part exchange'
    ]
    
    @staticmethod
    def calculate_score(listing: CarListing, query: str, filters: dict) -> int:
        score = 0
        query_lower = query.lower()
        title_lower = listing.title.lower()
        
        # ── BASE SCORE (40 points) ──
        # Title contains all query words (exact match)
        query_words = query_lower.split() if query else []
        if query_words and all(word in title_lower for word in query_words):
            score += 40
        elif query and any(word in title_lower for word in query_words):
            score += 20
        
        # ── MAKE/MODEL PRECISION (25 points) ──
        if filters.get('make') and listing.make.lower() == filters['make'].lower():
            score += 15
        if filters.get('model') and filters['model'].lower() in listing.model.lower():
            score += 10
        
        # ── DATA COMPLETENESS (20 points) ──
        if listing.price and 500 <= listing.price <= 500000:
            score += 5
        if listing.year and 1990 <= listing.year <= 2026:
            score += 5
        if listing.odometer and 0 < listing.odometer < 500000:
            score += 5
        if listing.images and len(listing.images) >= 2:
            score += 5
        
        # ── SOURCE RELIABILITY (15 points) ──
        reliability = {
            "Manual Submission": 15,
            "Carsales": 12,
            "eBay Australia": 10,
            "Gumtree": 8,
            "Facebook Marketplace": 5
        }
        score += reliability.get(listing.source, 0)
        
        # ── VERIFICATION BONUS (10 points) ──
        if listing.verified:
            score += 10
        
        # ── PENALTIES ──
        # Red flags in title
        for flag in AccuracyEngine.RED_FLAGS:
            if flag in title_lower:
                score -= 30
                break
        
        # Suspicious price
        if listing.price:
            if listing.price < 1000:  # Too cheap = scam
                score -= 20
            if listing.price > 200000 and listing.year and listing.year < 2020:
                score -= 15  # Overpriced old car
        
        # Vague location
        if listing.location.lower() in ['australia', '']:
            score -= 10
        
        # No images
        if not listing.images:
            score -= 15
        
        return max(0, min(100, score))
    
    @staticmethod
    def is_accurate(listing: CarListing, query: str, filters: dict) -> bool:
        """
        Hard filter - removes listings that are definitely wrong
        """
        title_lower = listing.title.lower()
        
        # Must have title
        if not listing.title or listing.title == 'Unknown':
            return False
        
        # Price sanity check
        if listing.price is not None:
            if listing.price < 500:  # Engagement bait
                return False
            if listing.price > 500000:  # Placeholder
                return False
        
        # No red flags
        for flag in AccuracyEngine.RED_FLAGS:
            if flag in title_lower:
                return False
        
        # Must have images (real sellers post photos)
        if not listing.images or len(listing.images) == 0:
            return False
        
        # Location must be specific
        if listing.location.lower() in ['australia', '']:
            return False
        
        # If query specifies make, title should mention it
        if filters.get('make'):
            if filters['make'].lower() not in title_lower:
                # Exception: if make is in the structured field
                if listing.make.lower() != filters['make'].lower():
                    return False
        
        return True

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────
def extract_year(title: str) -> Optional[int]:
    match = re.search(r'\b(19|20)\d{2}\b', title or '')
    if match:
        year = int(match.group())
        if 1900 <= year <= 2030:
            return year
    return None

def extract_make_model(title: str) -> tuple[str, str]:
    makes = ['Toyota', 'Honda', 'Ford', 'BMW', 'Mercedes', 'Mercedes-Benz', 'Audi', 'Mazda',
             'Hyundai', 'Kia', 'Volkswagen', 'Nissan', 'Subaru', 'Mitsubishi', 'Holden',
             'Jeep', 'Land Rover', 'Lexus', 'Volvo', 'Porsche', 'Tesla', 'Isuzu', 'MG']
    title_lower = (title or '').lower()
    for make in makes:
        if make.lower() in title_lower:
            pattern = rf'{re.escape(make)}\s+([A-Za-z0-9\-]+)'
            match = re.search(pattern, title, re.IGNORECASE)
            return make, match.group(1) if match else 'Unknown'
    return 'Unknown', 'Unknown'

def extract_price(text: str) -> Optional[float]:
    if not text:
        return None
    cleaned = re.sub(r'[^\d.]', '', text.replace(',', ''))
    try:
        price = float(cleaned)
        return price if 500 <= price <= 5000000 else None
    except:
        return None

# ─── EBAY API SCRAPER ─────────────────────────────────────────────────
async def scrape_ebay(query: str, filters: dict) -> List[CarListing]:
    if not EBAY_APP_ID:
        return []
    
    try:
        params = {
            "OPERATION-NAME": "findItemsByKeywords",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": EBAY_APP_ID,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "true",
            "keywords": f"{query} car".strip(),
            "GLOBAL-ID": "EBAY-AU",
            "paginationInput.entriesPerPage": str(filters.get("limit", 20)),
        }
        
        min_p = filters.get("min_price", 0)
        max_p = filters.get("max_price", 999999)
        if min_p > 0:
            params["itemFilter(0).name"] = "MinPrice"
            params["itemFilter(0).value"] = str(min_p)
        if max_p < 999999:
            params["itemFilter(1).name"] = "MaxPrice"
            params["itemFilter(1).value"] = str(max_p)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://svcs.ebay.com/services/search/FindingService/v1",
                params=params
            )
            
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            items = (data.get("findItemsByKeywordsResponse", [{}])[0]
                        .get("searchResult", [{}])[0]
                        .get("item", []))
            
            results = []
            for item in items:
                try:
                    title = item.get("title", [""])[0]
                    make, model = extract_make_model(title)
                    year = extract_year(title)
                    
                    price_data = item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0]
                    price = float(price_data.get("__value__", 0)) if price_data else None
                    
                    listing = CarListing(
                        id=f"ebay-{item.get('itemId', [''])[0]}",
                        title=title,
                        price=price,
                        year=year,
                        make=make,
                        model=model,
                        odometer=None,
                        location=item.get("location", ["Australia"])[0],
                        source="eBay Australia",
                        url=item.get("viewItemURL", [""])[0],
                        images=[item.get("galleryURL", [""])[0]] if item.get("galleryURL") else [],
                        scraped_at=datetime.utcnow().isoformat(),
                        condition=item.get("condition", [{}])[0].get("conditionDisplayName", [""])[0] if item.get("condition") else None,
                    )
                    listing.accuracy_score = AccuracyEngine.calculate_score(listing, query, filters)
                    results.append(listing)
                except:
                    continue
            
            return results
    except Exception as e:
        logger.error(f"eBay error: {e}")
        return []

# ─── GUMTREE RSS SCRAPER ──────────────────────────────────────────────
async def scrape_gumtree(query: str, location: str, limit: int = 10) -> List[CarListing]:
    loc = GUMTREE_LOCATIONS.get(location.lower(), "sydney")
    search_term = query.replace(" ", "-") if query else "cars"
    rss_url = f"https://www.gumtree.com.au/rss/{loc}/cars-vans-utes/{search_term}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0"}
            resp = await client.get(rss_url, headers=headers)
            
            if resp.status_code != 200:
                return []
            
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            
            results = []
            for item in root.findall('.//item')[:limit]:
                try:
                    title = item.find('title').text if item.find('title') is not None else 'Unknown'
                    link = item.find('link').text if item.find('link') is not None else ''
                    desc = item.find('description').text if item.find('description') is not None else ''
                    
                    price = extract_price(desc)
                    year = extract_year(title)
                    make, model = extract_make_model(title)
                    odometer = extract_odometer(desc)
                    
                    images = []
                    enclosure = item.find('enclosure')
                    if enclosure is not None:
                        images.append(enclosure.get('url', ''))
                    
                    content = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                    if content is not None and content.text:
                        img_matches = re.findall(r'<img[^>]+src="([^"]+)"', content.text)
                        images.extend(img_matches[:3])
                    
                    listing = CarListing(
                        id=f"gt-{hash(link) & 0xFFFFFFFF}",
                        title=title,
                        price=price,
                        year=year,
                        make=make,
                        model=model,
                        odometer=odometer,
                        location=loc.title(),
                        source="Gumtree",
                        url=link,
                        images=images[:3] if images else [],
                        scraped_at=datetime.utcnow().isoformat(),
                    )
                    listing.accuracy_score = AccuracyEngine.calculate_score(listing, query, {})
                    results.append(listing)
                except:
                    continue
            
            return results
    except Exception as e:
        logger.error(f"Gumtree error: {e}")
        return []

# ─── APIFY FACEBOOK SCRAPER ───────────────────────────────────────────
async def scrape_facebook_apify(query: str, location: str, limit: int = 10) -> List[CarListing]:
    if not APIFY_API_TOKEN:
        return []
    
    try:
        location_id = FB_LOCATION_IDS.get(location.lower(), "108479165840750")
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.apify.com/v2/acts/apify~facebook-marketplace-scraper/run-sync-get-dataset-items",
                headers={"Authorization": f"Bearer {APIFY_API_TOKEN}"},
                json={
                    "startUrls": [{
                        "url": f"https://www.facebook.com/marketplace/{location_id}/search/?query={query or 'cars'}&category_id=807311116002614"
                    }],
                    "maxItems": limit,
                    "proxyConfiguration": {"useApifyProxy": True}
                }
            )
            
            if resp.status_code != 200:
                return []
            
            items = resp.json()
            results = []
            
            for item in items:
                try:
                    title = item.get("marketplace_listing_title") or item.get("title", "Unknown")
                    if title == "Unknown":
                        continue
                    
                    make, model = extract_make_model(title)
                    year = extract_year(title)
                    
                    price = None
                    price_data = item.get("listing_price", {})
                    if isinstance(price_data, dict) and "amount" in price_data:
                        price = float(price_data["amount"])
                    
                    loc = "Australia"
                    loc_data = item.get("location", {})
                    if isinstance(loc_data, dict):
                        reverse_geo = loc_data.get("reverse_geocode", {})
                        if isinstance(reverse_geo, dict):
                            loc = reverse_geo.get("city", "Australia")
                    
                    images = []
                    primary = item.get("primary_listing_photo", {})
                    if isinstance(primary, dict) and "image" in primary:
                        img = primary["image"]
                        if isinstance(img, dict) and "uri" in img:
                            images.append(img["uri"])
                    
                    listing = CarListing(
                        id=f"fb-{item.get('id', hash(title) & 0xFFFFFFFF)}",
                        title=title,
                        price=price,
                        year=year,
                        make=make,
                        model=model,
                        odometer=None,
                        location=loc,
                        source="Facebook Marketplace",
                        url=item.get("listingUrl") or item.get("url") or f"https://facebook.com/marketplace/item/{item.get('id', '')}",
                        images=images[:3] if images else ["https://via.placeholder.com/400x300?text=No+Image"],
                        scraped_at=datetime.utcnow().isoformat(),
                        seller_name=item.get("marketplace_listing_seller", {}).get("name") if isinstance(item.get("marketplace_listing_seller"), dict) else None,
                        condition=item.get("condition", "Used"),
                    )
                    listing.accuracy_score = AccuracyEngine.calculate_score(listing, query, {})
                    results.append(listing)
                except:
                    continue
            
            return results
    except Exception as e:
        logger.error(f"Apify error: {e}")
        return []

# ─── FASTAPI APP ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 CarMates API v3.1 starting...")
    logger.info(f"Frontend: {FRONTEND_URL}")
    logger.info(f"eBay: {'✅' if EBAY_APP_ID else '❌'}")
    logger.info(f"Apify: {'✅' if APIFY_API_TOKEN else '❌'}")
    yield
    logger.info("🛑 Shutting down")

app = FastAPI(
    title="CarMates API",
    description="Multi-source car scraping with accuracy filtering and manual submission",
    version="3.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        FRONTEND_URL,
        "https://carmates-scraper.pages.dev",
        "https://carmates-scraper-8yapf3mjq-adnanzkh-progs-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "3.1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "sources": {
            "ebay": bool(EBAY_APP_ID),
            "apify_facebook": bool(APIFY_API_TOKEN),
            "gumtree": True,
            "manual_submission": True,
            "sample_data": True
        }
    }

@app.get("/search", response_model=SearchResponse)
async def search_cars(
    q: str = Query(default="", description="Search query"),
    make: str = Query(default=""),
    model: str = Query(default=""),
    min_price: int = Query(default=0, ge=0),
    max_price: int = Query(default=999999, ge=0),
    year_from: int = Query(default=1900, ge=1900, le=2030),
    year_to: int = Query(default=2030, ge=1900, le=2030),
    location: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
    source: str = Query(default="all", description="all, facebook, ebay, gumtree, manual, sample"),
    min_accuracy: int = Query(default=0, ge=0, le=100, description="Minimum accuracy score (0-100)")
):
    """
    Search with strict accuracy filtering.
    Use min_accuracy=70 to filter out Facebook garbage listings.
    """
    start_time = time.time()
    filters = {
        "q": q, "make": make, "model": model,
        "min_price": min_price, "max_price": max_price,
        "year_from": year_from, "year_to": year_to,
        "location": location, "limit": limit, "source": source
    }
    
    all_results: List[CarListing] = []
    active_sources: List[str] = []
    
    # Parallel scraping
    tasks = []
    
    if source in ("all", "facebook") and APIFY_API_TOKEN:
        tasks.append(("facebook", scrape_facebook_apify(q or "cars", location or "brisbane", limit)))
    
    if source in ("all", "ebay") and EBAY_APP_ID:
        tasks.append(("ebay", scrape_ebay(q or "cars", filters)))
    
    if source in ("all", "gumtree"):
        tasks.append(("gumtree", scrape_gumtree(q or "cars", location or "sydney", limit)))
    
    if tasks:
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        for (name, _), result in zip(tasks, results):
            if isinstance(result, list):
                all_results.extend(result)
                if result:
                    active_sources.append(name)
    
    # Add database listings (includes manual submissions + sample data)
    db_results = db.search(filters)
    if db_results:
        all_results.extend(db_results)
        active_sources.extend([r.source for r in db_results if r.source not in active_sources])
    
    # ── ACCURACY FILTERING (SOLVES CLIENT PAIN POINT) ──
    
    # 1. Hard filter: remove definitely wrong listings
    all_results = [r for r in all_results if AccuracyEngine.is_accurate(r, q, filters)]
    
    # 2. Calculate/update accuracy scores
    for r in all_results:
        r.accuracy_score = AccuracyEngine.calculate_score(r, q, filters)
    
    # 3. Filter by minimum accuracy
    if min_accuracy > 0:
        all_results = [r for r in all_results if r.accuracy_score >= min_accuracy]
    
    # 4. Deduplicate by URL
    seen = set()
    unique = []
    for r in all_results:
        if r.url not in seen:
            seen.add(r.url)
            unique.append(r)
    all_results = unique
    
    # 5. Sort by accuracy score (highest first)
    all_results.sort(key=lambda x: (x.accuracy_score, x.verified), reverse=True)
    
    final = all_results[:limit]
    search_time = int((time.time() - start_time) * 1000)
    
    logger.info(f"Search '{q}': {len(final)} results from {active_sources} in {search_time}ms")
    
    return SearchResponse(
        query=q, filters=filters, results=final,
        total=len(final), search_time_ms=search_time,
        cached=False, sources=list(set(active_sources))
    )

# ─── MANUAL SUBMISSION ENDPOINT ───────────────────────────────────────
@app.post("/submit", response_model=CarListing)
async def submit_manual_listing(submission: ManualSubmission):
    """
    Manually add a Facebook Marketplace or other listing URL.
    This is 100% accurate because the user verified it.
    """
    # Validate URL
    if not submission.url.startswith(("https://www.facebook.com/marketplace/", "https://www.gumtree.com.au/", "https://www.carsales.com.au/")):
        raise HTTPException(400, "URL must be from Facebook Marketplace, Gumtree, or Carsales")
    
    # Create verified listing
    listing = db.add_manual(submission)
    logger.info(f"Manual submission added: {listing.id} - {listing.title}")
    
    return listing

@app.get("/submissions", response_model=List[ManualSubmission])
async def get_manual_submissions():
    """Get all manual submissions"""
    return db._manual_submissions

# ─── TEST SCRAPER ENDPOINT (For Development) ─────────────────────────
@app.post("/test-scrape")
async def test_scrape(url: str = Form(...)):
    """
    Test scraping a single URL without affecting production.
    Returns raw HTML and parsed data for debugging.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-AU,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
            }
            
            resp = await client.get(url, headers=headers)
            
            return {
                "url": url,
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "content_length": len(resp.text),
                "title_preview": resp.text[:500] if len(resp.text) > 500 else resp.text,
                "success": resp.status_code == 200
            }
    except Exception as e:
        return {"error": str(e), "url": url}

@app.get("/")
async def root():
    return {
        "message": "CarMates API v3.1",
        "docs": "/docs",
        "health": "/health",
        "search": "/search?q=toyota&location=sydney&min_accuracy=70",
        "submit": "POST /submit - Add manual listing",
        "test_scrape": "POST /test-scrape - Test single URL scraping",
        "sources": {
            "ebay": "Free API (5K/day)",
            "apify_facebook": "Paid ($0.005/result)",
            "gumtree": "Free RSS",
            "manual": "User-verified submissions"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
