"""
CarMates API - FastAPI Backend
Deployed on Railway: renewed-adventure-production-fef0.up.railway.app
"""

import os
import logging
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get environment variables
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://carmates-scraper.vercel.app").strip()
PORT = int(os.getenv("PORT", "8080"))

# Pydantic models
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

class SearchResponse(BaseModel):
    query: str
    filters: dict
    results: List[CarListing]
    total: int
    search_time_ms: int
    cached: bool = False

# Sample car database (replace with real scraper later)
SAMPLE_CARS = [
    CarListing(
        id="cs-001",
        title="2022 Toyota Camry Ascent Auto",
        price=28990,
        year=2022,
        make="Toyota",
        model="Camry",
        odometer=45000,
        location="Sydney, NSW",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2022-toyota-camry-ascent/SOME-ID",
        images=["https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="cs-002",
        title="2021 Mazda CX-5 Maxx Sport Auto FWD",
        price=32500,
        year=2021,
        make="Mazda",
        model="CX-5",
        odometer=32000,
        location="Melbourne, VIC",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2021-mazda-cx-5-maxx-sport/SOME-ID",
        images=["https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="cs-003",
        title="2023 Hyundai i30 N Line Auto",
        price=28999,
        year=2023,
        make="Hyundai",
        model="i30",
        odometer=15000,
        location="Brisbane, QLD",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2023-hyundai-i30-n-line/SOME-ID",
        images=["https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="gt-001",
        title="2020 Toyota RAV4 GX Auto 2WD",
        price=27900,
        year=2020,
        make="Toyota",
        model="RAV4",
        odometer=65000,
        location="Perth, WA",
        source="Gumtree",
        url="https://www.gumtree.com.au/s-ad/some-id",
        images=["https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="gt-002",
        title="2019 Honda CR-V VTi Auto FWD",
        price=24500,
        year=2019,
        make="Honda",
        model="CR-V",
        odometer=78000,
        location="Adelaide, SA",
        source="Gumtree",
        url="https://www.gumtree.com.au/s-ad/some-id",
        images=["https://images.unsplash.com/photo-1605816988064-baf6d7006279?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="cs-004",
        title="2023 BMW X5 xDrive30d Auto",
        price=89500,
        year=2023,
        make="BMW",
        model="X5",
        odometer=12000,
        location="Sydney, NSW",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2023-bmw-x5-xdrive30d/SOME-ID",
        images=["https://images.unsplash.com/photo-1555215695-3004980adade?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="cs-005",
        title="2021 Ford Ranger XLT Auto 4x4",
        price=45900,
        year=2021,
        make="Ford",
        model="Ranger",
        odometer=55000,
        location="Brisbane, QLD",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2021-ford-ranger-xlt/SOME-ID",
        images=["https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="gt-003",
        title="2022 Kia Sportage S Auto 2WD",
        price=26500,
        year=2022,
        make="Kia",
        model="Sportage",
        odometer=42000,
        location="Melbourne, VIC",
        source="Gumtree",
        url="https://www.gumtree.com.au/s-ad/some-id",
        images=["https://images.unsplash.com/photo-1606220838315-056192d5e927?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="cs-006",
        title="2020 Mercedes-Benz C200 Auto",
        price=42900,
        year=2020,
        make="Mercedes",
        model="C200",
        odometer=38000,
        location="Sydney, NSW",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2020-mercedes-benz-c200/SOME-ID",
        images=["https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
    CarListing(
        id="cs-007",
        title="2023 Audi Q5 40 TDI Auto quattro",
        price=67900,
        year=2023,
        make="Audi",
        model="Q5",
        odometer=8000,
        location="Perth, WA",
        source="Carsales",
        url="https://www.carsales.com.au/cars/details/2023-audi-q5-40-tdi/SOME-ID",
        images=["https://images.unsplash.com/photo-1603584173870-7f23fdae1b7a?w=400"],
        scraped_at=datetime.utcnow().isoformat()
    ),
]

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 CarMates API starting up...")
    logger.info(f"Frontend URL configured: {FRONTEND_URL}")
    yield
    logger.info("🛑 CarMates API shutting down...")

# Create FastAPI app
app = FastAPI(
    title="CarMates API",
    description="Car scraping API for Australian car listings",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
origins = [
    "https://localhost:3000",
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "ok",
        "service": "carmates-api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Search endpoint
@app.get("/search", response_model=SearchResponse)
async def search_cars(
    q: str = Query(default="", description="Search query (e.g., toyota camry)"),
    make: str = Query(default="", description="Car make"),
    model: str = Query(default="", description="Car model"),
    min_price: int = Query(default=0, ge=0, description="Minimum price"),
    max_price: int = Query(default=999999999, ge=0, description="Maximum price"),
    year_from: int = Query(default=1900, ge=1900, le=2030, description="Year from"),
    year_to: int = Query(default=2030, ge=1900, le=2030, description="Year to"),
    location: str = Query(default="", description="Location in Australia"),
    limit: int = Query(default=20, ge=1, le=100, description="Max results")
):
    """
    Search for cars across Australian listings.
    
    Returns structured car data with filters applied.
    """
    start_time = time.time()
    
    logger.info(f"Search request: q='{q}', make='{make}', location='{location}'")
    
    # Filter sample data
    filtered = SAMPLE_CARS.copy()
    
    # Apply text search
    if q:
        q_lower = q.lower()
        filtered = [r for r in filtered if q_lower in r.title.lower()]
    
    # Apply make filter
    if make:
        filtered = [r for r in filtered if r.make.lower() == make.lower()]
    
    # Apply model filter
    if model:
        filtered = [r for r in filtered if model.lower() in r.model.lower()]
    
    # Apply price filter
    filtered = [r for r in filtered if min_price <= (r.price or 0) <= max_price]
    
    # Apply year filter
    filtered = [r for r in filtered if year_from <= (r.year or 0) <= year_to]
    
    # Apply location filter
    if location:
        filtered = [r for r in filtered if location.lower() in r.location.lower()]
    
    # Limit results
    filtered = filtered[:limit]
    
    search_time = int((time.time() - start_time) * 1000)
    
    logger.info(f"Search completed: {len(filtered)} results in {search_time}ms")
    
    return SearchResponse(
        query=q,
        filters={
            "make": make,
            "model": model,
            "price_range": [min_price, max_price],
            "year_range": [year_from, year_to],
            "location": location,
            "limit": limit
        },
        results=filtered,
        total=len(filtered),
        search_time_ms=search_time,
        cached=False
    )

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "CarMates API",
        "docs": "/docs",
        "health": "/health",
        "search": "/search?q=toyota"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
