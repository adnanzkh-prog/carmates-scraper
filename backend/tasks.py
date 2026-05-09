from celery_app import celery_app
from scraper.facebook import FacebookMarketplaceScraper
from database import SessionLocal
from models import CarListing
import asyncio
import logging
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

async def do_scrape(scrape_request):
    async with FacebookMarketplaceScraper() as scraper:
        await scraper.login(
            email=scrape_request.get("email"),
            password=scrape_request.get("password")
        )
        results = await scraper.scrape_marketplace(
            query=scrape_request["query"],
            location=scrape_request.get("location"),
            min_price=scrape_request.get("min_price"),
            max_price=scrape_request.get("max_price"),
            min_year=scrape_request.get("min_year"),
            max_year=scrape_request.get("max_year"),
            condition=scrape_request.get("condition"),
            limit=scrape_request.get("limit", 50),
        )
        return results

@celery_app.task(bind=True)
def scrape_marketplace_task(self, scrape_request: dict):
    # Run async function in sync context
    listings = async_to_sync(do_scrape)(scrape_request)

    db = SessionLocal()
    try:
        for item in listings:
            existing = db.query(CarListing).filter(CarListing.facebook_id == item.get("facebook_id")).first()
            if existing:
                for key, value in item.items():
                    if value is not None and hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                new_listing = CarListing(**item)
                db.add(new_listing)
        db.commit()
        logger.info(f"Celery task stored {len(listings)} listings")
    except Exception as e:
        db.rollback()
        logger.error(f"Task failed: {e}")
        raise
    finally:
        db.close()
    return {"stored": len(listings)}
