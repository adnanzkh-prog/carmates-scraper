import os  # ← ADD THIS IF MISSING
from pydantic import BaseModel, Field

from fastapi import FastAPI, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional, List
import json
import pandas as pd
from io import BytesIO
from fastapi.responses import StreamingResponse

# FIXED: Changed from relative to absolute imports
from database import engine, get_db, Base
from models import CarListing
from scraper.facebook import FacebookMarketplaceScraper
from celery_app import celery_app
from tasks import scrape_marketplace_task

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI()

origins = [
    "https://carmates-scraper.pages.dev",
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    query: str
    location: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    condition: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    email: Optional[str] = None
    password: Optional[str] = None

class ScheduledJob(BaseModel):
    cron_expression: str
    request: ScrapeRequest
    enabled: bool = True

scheduled_jobs = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.websocket("/ws/progress")
async def websocket_progress(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/scrape")
async def start_scrape(request: ScrapeRequest):
    # Build the task payload with credentials
    task_payload = request.dict()
    
    # Fallback to env vars if user didn't provide credentials
    if not task_payload.get("email"):
        task_payload["email"] = os.getenv("FACEBOOK_EMAIL")
    if not task_payload.get("password"):
        task_payload["password"] = os.getenv("FACEBOOK_PASSWORD")
    
    task = scrape_marketplace_task.delay(task_payload)
    return {
        "task_id": task.id,
        "status": "queued",
        "has_credentials": bool(task_payload.get("email") and task_payload.get("password"))
    }

@app.get("/scrape/status/{task_id}")
def get_task_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "result": result.result if result.ready() else None}

@app.post("/scrape/sync")
async def scrape_sync(request: ScrapeRequest, db: Session = Depends(get_db)):
    async with FacebookMarketplaceScraper() as scraper:
        if request.email and request.password:
            await scraper.login(email=request.email, password=request.password)
        else:
            await scraper.login()
        results = await scraper.scrape_marketplace(
            query=request.query,
            location=request.location,
            min_price=request.min_price,
            max_price=request.max_price,
            min_year=request.min_year,
            max_year=request.max_year,
            condition=request.condition,
            limit=request.limit,
        )
        for item in results:
            existing = db.query(CarListing).filter(CarListing.facebook_id == item.get("facebook_id")).first()
            if existing:
                for key, value in item.items():
                    if value is not None and hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                new_listing = CarListing(**item)
                db.add(new_listing)
        db.commit()
        await manager.broadcast(json.dumps({"type": "scrape_done", "count": len(results)}))
    return {"stored": len(results)}

@app.get("/listings")
def get_listings(skip: int = 0, limit: int = 100, min_price: Optional[float] = None,
                max_price: Optional[float] = None, make: Optional[str] = None,
                search: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(CarListing)
    if min_price:
        query = query.filter(CarListing.price >= min_price)
    if max_price:
        query = query.filter(CarListing.price <= max_price)
    if make:
        query = query.filter(CarListing.make.ilike(f"%{make}%"))
    if search:
        query = query.filter(
            (CarListing.title.ilike(f"%{search}%")) | (CarListing.description.ilike(f"%{search}%"))
        )
    total = query.count()
    listings = query.offset(skip).limit(limit).all()
    return {"total": total, "listings": listings}

@app.get("/export/csv")
def export_csv(db: Session = Depends(get_db)):
    listings = db.query(CarListing).all()
    data = [{
        "facebook_id": l.facebook_id,
        "title": l.title,
        "price": l.price,
        "currency": l.currency,
        "year": l.year,
        "odometer": l.odometer,
        "odometer_unit": l.odometer_unit,
        "location": l.location,
        "listing_url": l.listing_url,
        "scrape_timestamp": l.scrape_timestamp
    } for l in listings]
    df = pd.DataFrame(data)
    stream = BytesIO()
    df.to_csv(stream, index=False)
    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=listings.csv"
    return response

@app.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):
    listings = db.query(CarListing).all()
    data = [{
        "facebook_id": l.facebook_id,
        "title": l.title,
        "price": l.price,
        "currency": l.currency,
        "year": l.year,
        "odometer": l.odometer,
        "odometer_unit": l.odometer_unit,
        "location": l.location,
        "listing_url": l.listing_url,
        "scrape_timestamp": l.scrape_timestamp
    } for l in listings]
    df = pd.DataFrame(data)
    stream = BytesIO()
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Listings")
    response = StreamingResponse(iter([stream.getvalue()]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = "attachment; filename=listings.xlsx"
    return response

@app.post("/scheduled_jobs")
def add_scheduled_job(job: ScheduledJob):
    scheduled_jobs.append(job.dict())
    return {"status": "added", "jobs": scheduled_jobs}

@app.get("/scheduled_jobs")
def list_scheduled_jobs():
    return {"jobs": scheduled_jobs}
