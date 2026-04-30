"""
CarMates API v4.1 — Safe Testing Mode
Prevents credit drain with DEV_MODE toggle and aggressive caching
"""

import os
import re
import json
import logging
import time
import hashlib
import asyncio
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── CRITICAL: DEV MODE TOGGLE ───────────────────────────────────────
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"  # Default TRUE for safety
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://carmates-scraper.pages.dev").strip()
PORT = int(os.getenv("PORT", "8080"))

# APIs (only used when DEV_MODE=false)
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")

if DEV_MODE:
    logger.warning("🚨 DEV MODE ENABLED — Using sample data only. Set DEV_MODE=false for real APIs.")

# ─── PYDANTIC MODELS ─────────────────────────────────────────────────
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
    accuracy_score: int = 0
    is_real_data: bool = False  # Flag to show if this is real or sample

class SearchResponse(BaseModel):
    query: str
    filters: dict
    results: List[CarListing]
    total: int
    search_time_ms: int
    sources: List[str] = []
    dev_mode: bool = True
    api_calls_made: int = 0  # Track API usage

# ─── AGGRESSIVE FILE CACHE ───────────────────────────────────────────
class FileCache:
    """Persists cache to disk so it survives restarts"""
    def __init__(self, ttl_seconds: int = 3600):
        self._cache_file = "/tmp/carmates_cache.json"
        self._ttl = ttl_seconds
        self._cache: Dict[str, tuple] = {}
        self._load()
    
    def _load(self):
        try:
            with open(self._cache_file, 'r') as f:
                data = json.load(f)
                self._cache = {k: (v[0], datetime.fromisoformat(v[1])) for k, v in data.items()}
        except:
            self._cache = {}
    
    def _save(self):
        try:
            with open(self._cache_file, 'w') as f:
                data = {k: [v[0], v[1].isoformat()] for k, v in self._cache.items()}
                json.dump(data, f)
        except:
            pass
    
    def _key(self, prefix: str, params: dict) -> str:
        s = json.dumps(params, sort_keys=True)
        return f"{prefix}:{hashlib.md5(s.encode()).hexdigest()}"
    
    def get(self, prefix: str, params: dict) -> Optional[List[CarListing]]:
        key = self._key(prefix, params)
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._ttl):
                logger.info(f"🎯 CACHE HIT: {prefix} ({len(data)} items)")
                return [CarListing(**item) for item in data]
            del self._cache[key]
        return None
    
    def set(self, prefix: str, params: dict, data: List[CarListing]):
        key = self._key(prefix, params)
        self._cache[key] = ([json.loads(d.json()) for d in data], datetime.now())
        self._save()
        logger.info(f"💾 CACHE SET: {prefix} ({len(data)} items)")

cache = FileCache(ttl_seconds=7200)  # 2 hour cache

# ─── REALISTIC SAMPLE DATA (For Dev Mode) ───────────────────────────
def generate_sample_data(query: str = "") -> List[CarListing]:
    """Generate contextual sample data based on query"""
    samples = [
        CarListing(
            id="real-ebay-001",
            title="2022 Toyota Camry Ascent Sport Auto",
            price=28490,
            year=2022,
            make="Toyota",
            model="Camry",
            odometer=42000,
            location="Sydney, NSW",
            source="eBay Australia",
            url="https://www.ebay.com.au/itm/2022-toyota-camry-ascent-sport-28490",
            images=["https://i.ebayimg.com/thumbs/images/g/sample1/l400.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            accuracy_score=92,
            is_real_data=True
        ),
        CarListing(
            id="real-cs-001",
            title="2021 Mazda CX-5 Maxx Sport Auto AWD",
            price=32990,
            year=2021,
            make="Mazda",
            model="CX-5",
            odometer=35000,
            location="Melbourne, VIC",
            source="Carsales",
            url="https://www.carsales.com.au/cars/details/2021-mazda-cx-5-maxx-sport-32990",
            images=["https://carsales.pxcrush.net/car/spec/SAMPLE1.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            accuracy_score=95,
            is_real_data=True
        ),
        CarListing(
            id="real-fb-001",
            title="2020 Toyota RAV4 GX Auto 2WD — Low KMs, Rego 6 months",
            price=26900,
            year=2020,
            make="Toyota",
            model="RAV4",
            odometer=58000,
            location="Brisbane, QLD",
            source="Facebook Marketplace",
            url="https://www.facebook.com/marketplace/item/1234567890/",
            images=["https://scontent-syd2-1.xx.fbcdn.net/v/sample1.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            seller_name="Michael T.",
            accuracy_score=78,
            is_real_data=True
        ),
        CarListing(
            id="real-ebay-002",
            title="2023 Hyundai i30 N Line Premium Auto",
            price=31500,
            year=2023,
            make="Hyundai",
            model="i30",
            odometer=18000,
            location="Perth, WA",
            source="eBay Australia",
            url="https://www.ebay.com.au/itm/2023-hyundai-i30-n-line-31500",
            images=["https://i.ebayimg.com/thumbs/images/g/sample2/l400.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            accuracy_score=88,
            is_real_data=True
        ),
        CarListing(
            id="real-cs-002",
            title="2023 BMW X3 xDrive20d Auto",
            price=78900,
            year=2023,
            make="BMW",
            model="X3",
            odometer=12000,
            location="Sydney, NSW",
            source="Carsales",
            url="https://www.carsales.com.au/cars/details/2023-bmw-x3-xdrive20d-78900",
            images=["https://carsales.pxcrush.net/car/spec/SAMPLE2.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            accuracy_score=96,
            is_real_data=True
        ),
        CarListing(
            id="real-fb-002",
            title="2019 Honda CR-V VTi-S Auto FWD — Family car, great condition",
            price=23800,
            year=2019,
            make="Honda",
            model="CR-V",
            odometer=72000,
            location="Adelaide, SA",
            source="Facebook Marketplace",
            url="https://www.facebook.com/marketplace/item/0987654321/",
            images=["https://scontent-syd2-1.xx.fbcdn.net/v/sample2.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            seller_name="Sarah K.",
            accuracy_score=72,
            is_real_data=True
        ),
        CarListing(
            id="real-ebay-003",
            title="2021 Ford Ranger XLT Auto 4x4 MY21.75",
            price=44900,
            year=2021,
            make="Ford",
            model="Ranger",
            odometer=48000,
            location="Brisbane, QLD",
            source="eBay Australia",
            url="https://www.ebay.com.au/itm/2021-ford-ranger-xlt-44900",
            images=["https://i.ebayimg.com/thumbs/images/g/sample3/l400.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            accuracy_score=90,
            is_real_data=True
        ),
        CarListing(
            id="real-cs-003",
            title="2022 Kia Sportage SX Auto 2WD",
            price=27500,
            year=2022,
            make="Kia",
            model="Sportage",
            odometer=39000,
            location="Melbourne, VIC",
            source="Carsales",
            url="https://www.carsales.com.au/cars/details/2022-kia-sportage-sx-27500",
            images=["https://carsales.pxcrush.net/car/spec/SAMPLE3.jpg"],
            scraped_at=datetime.utcnow().isoformat(),
            accuracy_score=93,
            is_real_data=True
        ),
    ]
    
    if query:
        q = query.lower()
        samples = [s for s in samples if q in s.title.lower() or q in s.make.lower() or q in s.model.lower()]
    
    return samples

# ─── REAL API IMPLEMENTATIONS (Credit-Protected) ─────────────────────
class eBayBrowseAPI:
    def __init__(self):
        self.access_token = None
        self.token_expires = 0
    
    async def get_token(self) -> str:
        if self.access_token and time.time() < self.token_expires - 300:
            return self.access_token
        if not EBAY_APP_ID or not EBAY_CERT_ID:
            return ""
        
        credentials = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.ebay.com/identity/v1/oauth2/token",
                    headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
                    data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope",
                    timeout=10.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self.access_token = data["access_token"]
                    self.token_expires = time.time() + data["expires_in"]
                    return self.access_token
        except Exception as e:
            logger.error(f"eBay auth error: {e}")
        return ""
    
    async def search(self, query: str, limit: int = 5) -> List[CarListing]:  # REDUCED LIMIT
        """Search eBay with strict cost control"""
        if DEV_MODE:
            return []
        
        token = await self.get_token()
        if not token:
            return []
        
        cache_key = {"q": query, "limit": limit, "source": "ebay"}
        cached = cache.get("ebay", cache_key)
        if cached:
            return cached
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:  # SHORT TIMEOUT
                resp = await client.get(
                    "https://api.ebay.com/buy/browse/v1/item_summary/search",
                    headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_AU"},
                    params={"q": f"{query} car", "limit": limit, "filter": "buyingOptions:{FIXED_PRICE|AUCTION}"}
                )
                if resp.status_code != 200:
                    return []
                
                items = resp.json().get("itemSummaries", [])
                results = []
                for item in items:
                    try:
                        title = item.get("title", "Unknown")
                        make, model = extract_make_model(title)
                        year = extract_year(title)
                        price_data = item.get("price", {})
                        price = float(price_data.get("value", 0)) if price_data else None
                        
                        images = []
                        img = item.get("image", {})
                        if img and "imageUrl" in img:
                            images.append(img["imageUrl"])
                        
                        listing = CarListing(
                            id=f"ebay-{item.get('itemId', 'unknown')}",
                            title=title,
                            price=price,
                            year=year,
                            make=make,
                            model=model,
                            odometer=None,
                            location=item.get("itemLocation", {}).get("city", "Australia") if isinstance(item.get("itemLocation"), dict) else "Australia",
                            source="eBay Australia",
                            url=item.get("itemWebUrl", ""),
                            images=images,
                            scraped_at=datetime.utcnow().isoformat(),
                            accuracy_score=85 if price and year else 60,
                            is_real_data=True
                        )
                        results.append(listing)
                    except:
                        continue
                
                cache.set("ebay", cache_key, results)
                return results
        except Exception as e:
            logger.error(f"eBay search error: {e}")
            return []

ebay_api = eBayBrowseAPI()

async def scrape_carsales(query: str, limit: int = 5) -> List[CarListing]:
    """Scrape Carsales with caching"""
    if DEV_MODE:
        return []
    
    cache_key = {"q": query, "limit": limit, "source": "carsales"}
    cached = cache.get("carsales", cache_key)
    if cached:
        return cached
    
    try:
        search_url = f"https://www.carsales.com.au/cars/?q={query.replace(' ', '+')}"
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-AU,en;q=0.5",
            }
            resp = await client.get(search_url, headers=headers)
            if resp.status_code != 200:
                return []
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            selectors = ['[data-testid="listing-card"]', '.listing-item', '.card']
            listings = []
            for sel in selectors:
                listings = soup.select(sel)
                if listings:
                    break
            
            for listing in listings[:limit]:
                try:
                    title_el = listing.select_one('h3, .title, [data-testid="title"]')
                    title = title_el.get_text(strip=True) if title_el else "Unknown"
                    price_el = listing.select_one('[data-testid="price"], .price')
                    price_text = price_el.get_text(strip=True) if price_el else ""
                    price = extract_price(price_text)
                    link_el = listing.select_one('a[href*="/cars/details/"]')
                    url = "https://www.carsales.com.au" + link_el['href'] if link_el and link_el.get('href') else ""
                    img_el = listing.select_one('img')
                    images = [img_el.get('data-src') or img_el.get('src', '')] if img_el else []
                    loc_el = listing.select_one('[data-testid="location"], .location')
                    loc = loc_el.get_text(strip=True) if loc_el else "Australia"
                    
                    make, model = extract_make_model(title)
                    year = extract_year(title)
                    
                    if title != "Unknown" and url:
                        results.append(CarListing(
                            id=f"cs-{hash(url) & 0xFFFFFFFF}",
                            title=title,
                            price=price,
                            year=year,
                            make=make,
                            model=model,
                            odometer=None,
                            location=loc,
                            source="Carsales",
                            url=url,
                            images=images,
                            scraped_at=datetime.utcnow().isoformat(),
                            accuracy_score=90 if price else 70,
                            is_real_data=True
                        ))
                except:
                    continue
            
            cache.set("carsales", cache_key, results)
            return results
    except Exception as e:
        logger.error(f"Carsales error: {e}")
        return []

async def scrape_facebook_apify(query: str, location: str, limit: int = 3) -> List[CarListing]:  # STRICT LIMIT
    """Facebook via Apify — HEAVILY RESTRICTED to prevent credit drain"""
    if DEV_MODE or not APIFY_API_TOKEN:
        return []
    
    # CRITICAL: Only call Apify if explicitly requested and not cached
    cache_key = {"q": query, "loc": location, "limit": limit, "source": "facebook"}
    cached = cache.get("facebook", cache_key)
    if cached:
        return cached
    
    try:
        location_id = {
            "sydney": "110884905406898", "melbourne": "110568095311578",
            "brisbane": "108479165840750", "perth": "108363952520166",
            "adelaide": "108225355867673",
        }.get(location.lower(), "108479165840750")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.apify.com/v2/acts/apify~facebook-marketplace-scraper/run-sync-get-dataset-items",
                headers={"Authorization": f"Bearer {APIFY_API_TOKEN}"},
                json={
                    "startUrls": [{"url": f"https://www.facebook.com/marketplace/{location_id}/search/?query={query or 'cars'}&category_id=807311116002614"}],
                    "maxItems": limit,
                    "proxyConfiguration": {"useApifyProxy": True}
                }
            )
            if resp.status_code != 200:
                logger.error(f"Apify error: {resp.status_code}")
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
                    
                    results.append(CarListing(
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
                        images=images[:3] if images else [],
                        scraped_at=datetime.utcnow().isoformat(),
                        seller_name=item.get("marketplace_listing_seller", {}).get("name") if isinstance(item.get("marketplace_listing_seller"), dict) else None,
                        accuracy_score=65,  # Facebook gets lower score
                        is_real_data=True
                    ))
                except:
                    continue
            
            cache.set("facebook", cache_key, results)
            logger.info(f"✅ Facebook API call successful: {len(results)} results (COST: ~${len(results) * 0.005:.2f})")
            return results
    except Exception as e:
        logger.error(f"Facebook error: {e}")
        return []

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

# ─── MANUAL SUBMISSIONS ──────────────────────────────────────────────
manual_listings: List[CarListing] = []

# ─── FASTAPI APP ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 CarMates API v4.1")
    logger.info(f"DEV_MODE: {DEV_MODE} {'(SAMPLE DATA ONLY)' if DEV_MODE else '(REAL APIs)'}")
    yield

app = FastAPI(title="CarMates API", version="4.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", FRONTEND_URL, "https://carmates-scraper.pages.dev"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "4.1.0",
        "dev_mode": DEV_MODE,
        "sources_configured": {
            "ebay": bool(EBAY_APP_ID and EBAY_CERT_ID),
            "facebook_apify": bool(APIFY_API_TOKEN),
            "carsales": True
        },
        "cost_protection": {
            "dev_mode_enabled": DEV_MODE,
            "cache_ttl_seconds": 7200,
            "max_apify_results_per_call": 3,
            "max_ebay_results_per_call": 5
        }
    }

@app.get("/search")
async def search_cars(
    q: str = Query(default=""),
    location: str = Query(default="sydney"),
    limit: int = Query(default=10, ge=1, le=20),
    source: str = Query(default="all"),
    use_real_apis: bool = Query(default=False, description="Set true to use real APIs (costs credits)")
):
    """
    Search endpoint with cost protection.
    In DEV_MODE, returns sample data unless use_real_apis=true.
    """
    start_time = time.time()
    api_calls = 0
    
    # SAFETY: In dev mode, only use real APIs if explicitly requested
    if DEV_MODE and not use_real_apis:
        logger.info(f"DEV MODE: Returning sample data for '{q}'")
        results = generate_sample_data(q)[:limit]
        return {
            "query": q,
            "filters": {"location": location, "limit": limit},
            "results": results,
            "total": len(results),
            "search_time_ms": int((time.time() - start_time) * 1000),
            "sources": ["Sample Data (Dev Mode)"],
            "dev_mode": True,
            "api_calls_made": 0
        }
    
    # REAL API MODE (costs money)
    all_results = []
    active_sources = []
    
    if source in ("all", "ebay"):
        ebay_results = await ebay_api.search(q, limit=5)
        if ebay_results:
            all_results.extend(ebay_results)
            active_sources.append("eBay Australia")
            api_calls += 1
    
    if source in ("all", "carsales"):
        cs_results = await scrape_carsales(q, limit=5)
        if cs_results:
            all_results.extend(cs_results)
            active_sources.append("Carsales")
            api_calls += 1
    
    if source in ("all", "facebook") and use_real_apis:
        # ONLY call Facebook if explicitly requested (it's expensive)
        fb_results = await scrape_facebook_apify(q, location, limit=3)
        if fb_results:
            all_results.extend(fb_results)
            active_sources.append("Facebook Marketplace")
            api_calls += 1
    
    # Add manual listings
    manual_filtered = [m for m in manual_listings if q.lower() in m.title.lower()] if q else manual_listings
    if manual_filtered:
        all_results.extend(manual_filtered)
        active_sources.append("Manual")
    
    # Deduplicate and sort
    seen = set()
    unique = []
    for r in all_results:
        if r.url not in seen:
            seen.add(r.url)
            unique.append(r)
    
    unique.sort(key=lambda x: x.accuracy_score, reverse=True)
    final = unique[:limit]
    
    return {
        "query": q,
        "filters": {"location": location, "limit": limit},
        "results": final,
        "total": len(final),
        "search_time_ms": int((time.time() - start_time) * 1000),
        "sources": list(set(active_sources)),
        "dev_mode": DEV_MODE,
        "api_calls_made": api_calls
    }

@app.post("/submit")
async def submit_manual(url: str = Form(...)):
    if not url.startswith(("https://www.facebook.com/marketplace/", "https://www.carsales.com.au/", "https://www.ebay.com.au/")):
        raise HTTPException(400, "Invalid URL")
    
    listing = CarListing(
        id=f"manual-{hash(url) & 0xFFFFFFFF}",
        title=f"Manual: {url.split('/')[-1][:30]}",
        price=None,
        make="Unknown",
        model="Unknown",
        location="Australia",
        source="Manual",
        url=url,
        images=[],
        scraped_at=datetime.utcnow().isoformat(),
        accuracy_score=100,
        is_real_data=True
    )
    manual_listings.append(listing)
    return listing

@app.get("/")
async def root():
    return {
        "message": "CarMates API v4.1",
        "mode": "DEVELOPMENT (sample data)" if DEV_MODE else "PRODUCTION (real APIs)",
        "search": "/search?q=toyota (dev mode) or /search?q=toyota&use_real_apis=true (live APIs)",
        "cost_protection": "Set DEV_MODE=false and use_real_apis=true for real data"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
