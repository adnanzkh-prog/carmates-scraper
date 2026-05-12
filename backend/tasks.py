from celery_app import celery_app
from scraper.facebook import FacebookMarketplaceScraper
from scraper.gumtree import GumtreeScraper
from database import SessionLocal
from models import CarListing
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def scrape_marketplace_task(self, scrape_request: dict):
    async def _run():
        all_results = []

        # Extract config from payload
        email = scrape_request.get("email")
        password = scrape_request.get("password")
        include_gumtree = scrape_request.get("include_gumtree", True)
        include_facebook = scrape_request.get("include_facebook", True)
        query = scrape_request["query"]
        location = scrape_request.get("location")

        logger.info(f"Task received. Query: {query}, Location: {location}")
        logger.info(f"Facebook: {include_facebook} (has_creds: {bool(email and password)})")
        logger.info(f"Gumtree: {include_gumtree}")

        # --- FACEBOOK SCRAPER ---
        if include_facebook:
            try:
                async with FacebookMarketplaceScraper() as scraper:
                    login_result = await scraper.login(email=email, password=password)

                    if login_result:
                        logger.info("[Facebook] Login successful or cookies loaded")
                    else:
                        logger.warning("[Facebook] No login — proceeding with limited scrape")

                    fb_results = await scraper.scrape_marketplace(
                        query=query,
                        location=location,
                        min_price=scrape_request.get("min_price"),
                        max_price=scrape_request.get("max_price"),
                        min_year=scrape_request.get("min_year"),
                        max_year=scrape_request.get("max_year"),
                        condition=scrape_request.get("condition"),
                        limit=scrape_request.get("limit", 20),
                    )

                    # Tag results with source
                    for r in fb_results:
                        r["source"] = "facebook"

                    all_results.extend(fb_results)
                    logger.info(f"[Facebook] Found {len(fb_results)} listings")

            except Exception as e:
                logger.error(f"[Facebook] Scrape failed: {e}")
                # Facebook failures are non-blocking — continue to Gumtree

        # --- GUMTREE SCRAPER ---
        if include_gumtree:
            try:
                async with GumtreeScraper() as scraper:
                    gt_results = await scraper.scrape_listings(
                        query=query,
                        location=location,
                        min_price=scrape_request.get("min_price"),
                        max_price=scrape_request.get("max_price"),
                        min_year=scrape_request.get("min_year"),
                        max_year=scrape_request.get("max_year"),
                        limit=scrape_request.get("limit", 20),
                    )

                    # Tag results with source
                    for r in gt_results:
                        r["source"] = "gumtree"

                    all_results.extend(gt_results)
                    logger.info(f"[Gumtree] Found {len(gt_results)} listings")

            except Exception as e:
                logger.error(f"[Gumtree] Scrape failed: {e}")

        return all_results

    # Run async code
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        listings = loop.run_until_complete(_run())
    except Exception as e:
        logger.error(f"Scrape error: {str(e)}")
        raise
    finally:
        loop.close()

    # Store results in database
    db = SessionLocal()
    stored = 0
    updated = 0
    try:
        for item in listings:
            # Use composite key: source + listing_id
            listing_id = item.get("facebook_id") or item.get("listing_id")
            source = item.get("source", "unknown")

            if not listing_id:
                # Generate fallback ID from URL
                listing_id = hash(item.get("listing_url", "")) % 100000000
                item["listing_id"] = str(listing_id)

            existing = db.query(CarListing).filter(
                CarListing.facebook_id == str(listing_id)
            ).first()

            if existing:
                for key, value in item.items():
                    if value is not None and hasattr(existing, key):
                        setattr(existing, key, value)
                updated += 1
            else:
                # Map fields to model
                new_item = {
                    "facebook_id": str(listing_id),
                    "title": item.get("title"),
                    "price": item.get("price"),
                    "currency": item.get("currency", "AUD"),
                    "year": item.get("year"),
                    "odometer": item.get("odometer"),
                    "odometer_unit": item.get("odometer_unit"),
                    "location": item.get("location"),
                    "listing_url": item.get("listing_url"),
                    "description": item.get("description"),
                    "image_urls": item.get("image_urls"),
                    "condition": item.get("condition"),
                    "source": source,
                }
                new_listing = CarListing(**{k: v for k, v in new_item.items() if v is not None})
                db.add(new_listing)
                stored += 1

        db.commit()
        logger.info(f"Stored {stored} new listings, updated {updated} existing. Total: {len(listings)}")

    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()

    return {
        "stored": stored,
        "updated": updated,
        "total": len(listings),
        "facebook_count": len([r for r in listings if r.get("source") == "facebook"]),
        "gumtree_count": len([r for r in listings if r.get("source") == "gumtree"]),
    }
