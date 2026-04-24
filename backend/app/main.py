from fastapi import FastAPI
from aggregator import aggregate
from filters import is_valid_listing_au
from scoring import score_listing_au
from alerts import detect_underpriced

app = FastAPI()


@app.get("/search")
async def search(q: str = "cars"):

    listings = await aggregate(q)

    listings = [l for l in listings if is_valid_listing_au(l)]

    listings = sorted(listings, key=lambda x: score_listing_au(x), reverse=True)

    return [l.__dict__ for l in listings]


@app.get("/deals")
async def deals(q: str = "cars"):

    listings = await aggregate(q)
    deals = detect_underpriced(listings)

    return [l.__dict__ for l in deals]


@app.get("/health")
def health():
    return {"status": "ok"}
