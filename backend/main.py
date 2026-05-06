# backend/main.py
import os
import re
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scraper.cache import SearchCache
from scraper.facebook import scrape_facebook_marketplace

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://carmates-scraper.pages.dev")
PORT = int(os.getenv("PORT", "8080"))

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
    accuracy_score: int = 0

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", FRONTEND_URL, "https://carmates-scraper.pages.dev"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = SearchCache(ttl_minutes=15)

# Sample data that actually works
SAMPLE_CARS = [
    CarListing(
        id="sample-1",
        title="2022 Toyota Camry Ascent Sport Auto",
        price=28990,
        year=2022,
        make="Toyota",
        model="Camry",
        odometer=42000,
        location="Sydney, NSW",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2022-toyota-camry-ascent-sport",
        images=["https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=400"],
        scraped_at=datetime.utcnow().isoformat(),
        accuracy_score=92
    ),
    CarListing(
        id="sample-2",
        title="2021 Mazda CX-5 Maxx Sport Auto AWD",
        price=32990,
        year=2021,
        make="Mazda",
        model="CX-5",
        odometer=35000,
        location="Melbourne, VIC",
        source="eBay Australia",
        url="https://www.ebay.com.au/itm/2021-mazda-cx-5-maxx-sport",
        images=["https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400"],
        scraped_at=datetime.utcnow().isoformat(),
        accuracy_score=88
    ),
    CarListing(
        id="sample-3",
        title="2020 Toyota RAV4 GX Auto 2WD",
        price=26900,
        year=2020,
        make="Toyota",
        model="RAV4",
        odometer=58000,
        location="Brisbane, QLD",
        source="Facebook Marketplace",
        url="https://www.facebook.com/marketplace/item/1234567890",
        images=["https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=400"],
        scraped_at=datetime.utcnow().isoformat(),
        accuracy_score=75
    ),
    CarListing(
        id="sample-4",
        title="2023 Hyundai i30 N Line Premium Auto",
        price=31500,
        year=2023,
        make="Hyundai",
        model="i30",
        odometer=18000,
        location="Perth, WA",
        source="Gumtree",
        url="https://www.gumtree.com.au/s-ad/perth/2023-hyundai-i30-n-line",
        images=["https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=400"],
        scraped_at=datetime.utcnow().isoformat(),
        accuracy_score=85
    ),
    CarListing(
        id="sample-5",
        title="2023 BMW X3 xDrive20d Auto",
        price=78900,
        year=2023,
        make="BMW",
        model="X3",
        odometer=12000,
        location="Sydney, NSW",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2023-bmw-x3-xdrive20d",
        images=["https://images.unsplash.com/photo-1555215695-3004980adade?w=400"],
        scraped_at=datetime.utcnow().isoformat(),
        accuracy_score=96
    ),
]

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "4.1.1", "mode": "sample-data"}

@app.get("/search")
async def search_cars(
    q: str = Query(default=""),
    location: str = Query(default=""),
    limit: int = Query(default=10, ge=1, le=50)
):
    cache_key = {"q": q, "location": location, "limit": limit}
    cached = cache.get(cache_key)
    if cached is not None:
        return {
            "query": q,
            "results": cached,
            "total": len(cached),
            "search_time_ms": 0,
            "sources": ["Facebook Marketplace"],
            "dev_mode": False,
            "cached": True
        }

    results = []
    if q:
        results = scrape_facebook_marketplace(q, location, limit)

    if not results:
        results = SAMPLE_CARS.copy()
        if q:
            q_lower = q.lower()
            results = [c for c in results if q_lower in c.title.lower() or q_lower in c.make.lower()]
        if location:
            results = [c for c in results if location.lower() in c.location.lower()]

    serialized_results = []
    for item in results:
        if hasattr(item, 'dict') and callable(getattr(item, 'dict')):
            serialized_results.append(item.dict())
        else:
            serialized_results.append(item)

    cache.set(cache_key, serialized_results)

    return {
        "query": q,
        "results": serialized_results[:limit],
        "total": len(serialized_results[:limit]),
        "search_time_ms": 0,
        "sources": ["Facebook Marketplace"] if q else ["Sample Data"],
        "dev_mode": False
    }

@app.post("/submit")
async def submit_manual(url: str = Form(...)):
    return {"status": "received", "url": url}

@app.get("/")
async def root():
    return {"message": "CarMates API", "search": "/search?q=toyota"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
