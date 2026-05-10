from celery_app import celery_app
from scraper.facebook import FacebookMarketplaceScraper
from database import SessionLocal
from models import CarListing
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def scrape_marketplace_task(self, scrape_request: dict):
    async def _run():
        # Use async context manager — browser init is handled in __aenter__
        async with FacebookMarketplaceScraper() as scraper:
            # Extract credentials from task payload
            email = scrape_request.get("email")
            password = scrape_request.get("password")
            
            logger.info(f"Task received. Has email: {bool(email)}, Has password: {bool(password)}")
            
            # Attempt login (graceful if no credentials)
            login_result = await scraper.login(email=email, password=password)
            
            if login_result:
                logger.info("Login successful or cookies loaded")
            else:
                logger.warning("No login — proceeding with limited scrape")
            
            # Perform scrape (works with or without login)
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

    # Run async code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        listings = loop.run_until_complete(_run())
    except Exception as e:
        logger.error(f"Scrape error: {str(e)}")
        # Don't retry on auth failures
        if "login" in str(e).lower() or "credentials" in str(e).lower():
            raise  # Let Celery mark as FAILURE
        raise self.retry(exc=e, countdown=60)
    finally:
        loop.close()

    # Store results in database
    db = SessionLocal()
    stored = 0
    try:
        for item in listings:
            existing = db.query(CarListing).filter(
                CarListing.facebook_id == item.get("facebook_id")
            ).first()
            
            if existing:
                for key, value in item.items():
                    if value is not None and hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                new_listing = CarListing(**item)
                db.add(new_listing)
                stored += 1
                
        db.commit()
        logger.info(f"Stored {stored} new listings, updated {len(listings) - stored} existing")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()
        
    return {"stored": len(listings), "new": stored}
