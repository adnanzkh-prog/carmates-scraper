"""
CarMates API v4.0 — Real Data Only
Removes all sample data. Uses eBay Browse API, Carsales scraping, Apify Facebook.
"""

import os
import re
import json
import logging
import time
import asyncio
import base64
from datetime import datetime
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

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://carmates-scraper.pages.dev").strip()
PORT = int(os.getenv("PORT", "8080"))
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")

# eBay Browse API credentials (NEW API — Finding API is dead)
EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")
EBAY_DEV_ID = os.getenv("EBAY_DEV_ID", "")

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

class SearchResponse(BaseModel):
    query: str
    filters: dict
    results: List[CarListing]
    total: int
    search_time_ms: int
    sources: List[str] = []
    is_real_data: bool = True

# ─── REAL EBAY BROWSE API (Finding API is dead since Feb 2025) ──────
class eBayAPI:
    def __init__(self):
        self.access_token = None
        self.token_expires = 0
    
    async def get_token(self) -> str:
        """Get OAuth token for Browse API"""
        if self.access_token and time.time() < self.token_expires - 300:
            return self.access_token
        
        if not EBAY_APP_ID or not EBAY_CERT_ID:
            return ""
        
        credentials = base64.b64encode(f"{EBAY_APP_ID}:{EBAY_CERT_ID}".encode()).decode()
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.ebay.com/identity/v1/oauth2/token",
                headers={
                    "Authorization": f"Basic {credentials}",
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                data="grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope"
            )
            
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data["access_token"]
                self.token_expires = time.time() + data["expires_in"]
                return self.access_token
            else:
                logger.error(f"eBay auth failed: {resp.status_code}")
                return ""
    
    async def search(self, query: str, limit: int = 10) -> List[CarListing]:
        """Search eBay Australia using Browse API"""
        token = await self.get_token()
        if not token:
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    "https://api.ebay.com/buy/browse/v1/item_summary/search",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-EBAY-C-MARKETPLACE-ID": "EBAY_AU"
                    },
                    params={
                        "q": f"{query} car",
                        "limit": limit,
                        "filter": "buyingOptions:{FIXED_PRICE|AUCTION}"
                    }
                )
                
                if resp.status_code != 200:
                    logger.error(f"eBay Browse API error: {resp.status_code}")
                    return []
                
                data = resp.json()
                items = data.get("itemSummaries", [])
                
                results = []
                for item in items:
                    try:
                        title = item.get("title", "Unknown")
                        make, model = extract_make_model(title)
                        year = extract_year(title)
                        
                        price_data = item.get("price", {})
                        price = float(price_data.get("value", 0)) if price_data else None
                        
                        # Get image
                        images = []
                        img = item.get("image", {})
                        if img and "imageUrl" in img:
                            images.append(img["imageUrl"])
                        
                        # Additional images
                        for add_img in item.get("additionalImages", [])[:2]:
                            if isinstance(add_img, dict) and "imageUrl" in add_img:
                                images.append(add_img["imageUrl"])
                        
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
                            condition=item.get("condition", "Unknown"),
                            accuracy_score=85 if price and year else 60
                        )
                        results.append(listing)
                    except Exception as e:
                        logger.debug(f"eBay parse error: {e}")
                        continue
                
                logger.info(f"eBay: {len(results)} real listings")
                return results
                
        except Exception as e:
            logger.error(f"eBay search error: {e}")
            return []

ebay_api = eBayAPI()

# ─── CARSALES DIRECT SCRAPING ────────────────────────────────────────
async def scrape_carsales(query: str, location: str = "", limit: int = 10) -> List[CarListing]:
    """
    Scrape Carsales.com.au search results directly.
    This parses their search page HTML — may break if they redesign.
    """
    try:
        search_url = f"https://www.carsales.com.au/cars/?q={query.replace(' ', '+')}"
        if location:
            search_url += f"&location={location.lower()}"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-AU,en;q=0.5",
            }
            
            resp = await client.get(search_url, headers=headers)
            
            if resp.status_code != 200:
                logger.warning(f"Carsales returned {resp.status_code}")
                return []
            
            # Parse HTML for listings
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            results = []
            
            # Try multiple selector patterns (Carsales changes these)
            selectors = [
                '[data-testid="listing-card"]',
                '.listing-item',
                '.card',
                '[data-webm-clickvalue*="srp-listing"]'
            ]
            
            listings = []
            for sel in selectors:
                listings = soup.select(sel)
                if listings:
                    break
            
            for listing in listings[:limit]:
                try:
                    # Extract title
                    title_el = listing.select_one('h3, .title, [data-testid="title"]')
                    title = title_el.get_text(strip=True) if title_el else "Unknown"
                    
                    # Extract price
                    price_el = listing.select_one('[data-testid="price"], .price, .listing-price')
                    price_text = price_el.get_text(strip=True) if price_el else ""
                    price = extract_price(price_text)
                    
                    # Extract URL
                    link_el = listing.select_one('a[href*="/cars/details/"]')
                    url = "https://www.carsales.com.au" + link_el['href'] if link_el and link_el.get('href') else ""
                    
                    # Extract image
                    img_el = listing.select_one('img')
                    images = []
                    if img_el:
                        img_src = img_el.get('data-src') or img_el.get('src', '')
                        if img_src and not img_src.startswith('data:'):
                            images.append(img_src)
                    
                    # Extract location
                    loc_el = listing.select_one('[data-testid="location"], .location')
                    loc = loc_el.get_text(strip=True) if loc_el else "Australia"
                    
                    # Extract odometer
                    odo_el = listing.select_one('[data-testid="odometer"], .odometer')
                    odo_text = odo_el.get_text(strip=True) if odo_el else ""
                    odometer = extract_odometer(odo_text)
                    
                    make, model = extract_make_model(title)
                    year = extract_year(title)
                    
                    if title != "Unknown" and url:
                        listing_obj = CarListing(
                            id=f"cs-{hash(url) & 0xFFFFFFFF}",
                            title=title,
                            price=price,
                            year=year,
                            make=make,
                            model=model,
                            odometer=odometer,
                            location=loc,
                            source="Carsales",
                            url=url,
                            images=images,
                            scraped_at=datetime.utcnow().isoformat(),
                            accuracy_score=90 if price and odometer else 75
                        )
                        results.append(listing_obj)
                        
                except Exception as e:
                    logger.debug(f"Carsales parse error: {e}")
                    continue
            
            logger.info(f"Carsales: {len(results)} real listings")
            return results
            
    except Exception as e:
        logger.error(f"Carsales error: {e}")
        return []

# ─── APIFY FACEBOOK ───────────────────────────────────────────────────
async def scrape_facebook_apify(query: str, location: str, limit: int = 10) -> List[CarListing]:
    if not APIFY_API_TOKEN:
        return []
    
    try:
        location_id = {
            "sydney": "110884905406898",
            "melbourne": "110568095311578",
            "brisbane": "108479165840750",
            "perth": "108363952520166",
            "adelaide": "108225355867673",
        }.get(location.lower(), "108479165840750")
        
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
                        images=images[:3] if images else [],
                        scraped_at=datetime.utcnow().isoformat(),
                        seller_name=item.get("marketplace_listing_seller", {}).get("name") if isinstance(item.get("marketplace_listing_seller"), dict) else None,
                        condition=item.get("condition", "Used"),
                        accuracy_score=50  # Facebook gets lower score due to noise
                    )
                    results.append(listing)
                except:
                    continue
            
            logger.info(f"Facebook: {len(results)} real listings")
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

def extract_odometer(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r'([\d,]+)\s*(km|kms)', text.lower())
    if match:
        try:
            return int(match.group(1).replace(',', ''))
        except:
            pass
    return None

# ─── MANUAL SUBMISSIONS DATABASE ──────────────────────────────────────
manual_listings: List[CarListing] = []

# ─── FASTAPI APP ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 CarMates API v4.0 — Real Data Only")
    logger.info(f"Frontend: {FRONTEND_URL}")
    logger.info(f"eBay Browse API: {'✅' if EBAY_APP_ID else '❌ (needs EBAY_APP_ID + EBAY_CERT_ID)'}")
    logger.info(f"Facebook (Apify): {'✅' if APIFY_API_TOKEN else '❌ (needs APIFY_API_TOKEN)'}")
    yield

app = FastAPI(title="CarMates API", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        FRONTEND_URL,
        "https://carmates-scraper.pages.dev",
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
        "version": "4.0.0",
        "real_data_only": True,
        "sources_configured": {
            "ebay_browse_api": bool(EBAY_APP_ID and EBAY_CERT_ID),
            "facebook_apify": bool(APIFY_API_TOKEN),
            "carsales_scraping": True
        },
        "note": "Sample data removed. Add EBAY_APP_ID + EBAY_CERT_ID for eBay. Add APIFY_API_TOKEN for Facebook."
    }

@app.get("/search", response_model=SearchResponse)
async def search_cars(
    q: str = Query(default=""),
    make: str = Query(default=""),
    model: str = Query(default=""),
    min_price: int = Query(default=0, ge=0),
    max_price: int = Query(default=999999, ge=0),
    year_from: int = Query(default=1900, ge=1900, le=2030),
    year_to: int = Query(default=2030, ge=1900, le=2030),
    location: str = Query(default=""),
    limit: int = Query(default=20, ge=1, le=50),
    source: str = Query(default="all"),
    min_accuracy: int = Query(default=0, ge=0, le=100)
):
    start_time = time.time()
    filters = {
        "q": q, "make": make, "model": model,
        "min_price": min_price, "max_price": max_price,
        "year_from": year_from, "year_to": year_to,
        "location": location, "limit": limit
    }
    
    all_results: List[CarListing] = []
    active_sources: List[str] = []
    
    # Parallel scraping from ALL configured sources
    tasks = []
    
    if source in ("all", "facebook") and APIFY_API_TOKEN:
        tasks.append(("facebook", scrape_facebook_apify(q or "cars", location or "sydney", limit)))
    
    if source in ("all", "ebay") and EBAY_APP_ID:
        tasks.append(("ebay", ebay_api.search(q or "cars", limit)))
    
    if source in ("all", "carsales"):
        tasks.append(("carsales", scrape_carsales(q or "cars", location, limit)))
    
    # Execute all in parallel with timeout
    if tasks:
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*[t[1] for t in tasks], return_exceptions=True),
                timeout=25.0
            )
            for (name, _), result in zip(tasks, results):
                if isinstance(result, list) and result:
                    all_results.extend(result)
                    active_sources.append(name)
        except asyncio.TimeoutError:
            logger.warning("Search timeout — returning partial results")
    
    # Add manual submissions
    if source in ("all", "manual"):
        manual_filtered = [m for m in manual_listings if q.lower() in m.title.lower()] if q else manual_listings
        if manual_filtered:
            all_results.extend(manual_filtered)
            active_sources.append("Manual")
    
    # Filter by accuracy
    if min_accuracy > 0:
        all_results = [r for r in all_results if r.accuracy_score >= min_accuracy]
    
    # Deduplicate
    seen = set()
    unique = []
    for r in all_results:
        if r.url not in seen:
            seen.add(r.url)
            unique.append(r)
    all_results = unique
    
    # Sort by accuracy
    all_results.sort(key=lambda x: x.accuracy_score, reverse=True)
    
    final = all_results[:limit]
    search_time = int((time.time() - start_time) * 1000)
    
    return SearchResponse(
        query=q, filters=filters, results=final,
        total=len(final), search_time_ms=search_time,
        sources=active_sources, is_real_data=True
    )

@app.post("/submit")
async def submit_manual(url: str = Form(...), notes: str = Form(default="")):
    """Manually add a listing URL"""
    if not url.startswith(("https://www.facebook.com/marketplace/", "https://www.carsales.com.au/", "https://www.gumtree.com.au/", "https://www.ebay.com.au/")):
        raise HTTPException(400, "URL must be from Facebook, Carsales, Gumtree, or eBay")
    
    listing = CarListing(
        id=f"manual-{hash(url) & 0xFFFFFFFF}",
        title=f"Manual: {url.split('/')[-1][:30]}",
        price=None,
        year=None,
        make="Unknown",
        model="Unknown",
        odometer=None,
        location="Australia",
        source="Manual",
        url=url,
        images=[],
        scraped_at=datetime.utcnow().isoformat(),
        accuracy_score=100,
        condition=notes or "Manual submission"
    )
    manual_listings.append(listing)
    return listing

@app.get("/")
async def root():
    return {
        "message": "CarMates API v4.0 — Real Data Only (No Mockups)",
        "search": "/search?q=toyota&location=sydney",
        "health": "/health",
        "submit": "POST /submit with url=",
        "setup_required": {
            "ebay": "Add EBAY_APP_ID + EBAY_CERT_ID to Railway env vars",
            "facebook": "Add APIFY_API_TOKEN to Railway env vars"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
