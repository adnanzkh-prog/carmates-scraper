# backend/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="CarMates API", version="1.0.0")

# CORS — restrict to your Vercel domain in production
origins = [
    "http://localhost:3000",
    os.getenv("FRONTEND_URL", "https://carmates-frontend.vercel.app")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "carmates-api"}

@app.get("/search")
async def search_cars(q: str = "", make: str = "", model: str = "", 
                      min_price: int = 0, max_price: int = 999999,
                      year_from: int = 1900, year_to: int = 2026,
                      location: str = ""):
    """
    Search cars with filters
    """
    # Your scraping logic here
    # Return structured data
    return {
        "query": q,
        "filters": {
            "make": make,
            "model": model,
            "price_range": [min_price, max_price],
            "year_range": [year_from, year_to],
            "location": location
        },
        "results": [],
        "total": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
