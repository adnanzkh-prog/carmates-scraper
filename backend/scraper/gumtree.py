import asyncio
import re
import json
import random
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urlencode, quote
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import stealth_async
from config import settings


class GumtreeScraper:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        launch_options = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        }
        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}
        self.browser = await self.playwright.chromium.launch(**launch_options)
        context = await self.browser.new_context(
            viewport={"width": random.randint(1200, 1920), "height": random.randint(800, 1080)},
            user_agent=random.choice(settings.USER_AGENTS)
        )
        self.page = await context.new_page()
        await stealth_async(self.page)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _build_search_url(
        self,
        query: str,
        location: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        category: str = "cars-vans-utes"
    ) -> str:
        """Build Gumtree Australia search URL."""
        # Gumtree uses location slugs like "sydney", "melbourne", "brisbane"
        location_slug = location.lower().replace(" ", "-") if location else "australia"

        base_url = f"https://www.gumtree.com.au/s-{category}/{location_slug}/{quote(query)}"

        params = {}
        if min_price is not None:
            params["priceFrom"] = min_price
        if max_price is not None:
            params["priceTo"] = max_price
        if min_year is not None:
            params["yearFrom"] = min_year
        if max_year is not None:
            params["yearTo"] = max_year

        if params:
            return f"{base_url}?{urlencode(params)}"
        return base_url

    async def scrape_listings(
        self,
        query: str,
        location: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        limit: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Scrape Gumtree listings. No authentication required."""

        search_url = self._build_search_url(
            query=query,
            location=location,
            min_price=min_price,
            max_price=max_price,
            min_year=min_year,
            max_year=max_year
        )

        print(f"[Gumtree] Navigating to: {search_url}")

        await self.page.goto(search_url, timeout=60000)

        # Check for anti-bot / blocked page
        if "blocked" in self.page.url.lower() or "captcha" in self.page.url.lower():
            print("[Gumtree] Anti-bot protection detected. Returning empty results.")
            return []

        # Wait for listings to load
        try:
            await self.page.wait_for_selector('[data-testid="listing-card"], .user-ad-row, .search-results-page__result', timeout=15000)
        except:
            print("[Gumtree] No listings found or page structure changed.")
            return []

        all_results = []
        page_num = 1
        max_pages = 3

        while len(all_results) < limit and page_num <= max_pages:
            listings = await self._extract_page_listings()

            for listing in listings:
                if listing["listing_id"] and not any(
                    r["listing_id"] == listing["listing_id"] for r in all_results
                ):
                    all_results.append(listing)

            print(f"[Gumtree] Scraped {len(all_results)} / {limit} listings (page {page_num})")

            if len(all_results) >= limit:
                break

            # Try next page
            next_page = await self.page.query_selector('a[aria-label="Next"], a.pagination__next, [data-testid="pagination-next"]')
            if not next_page:
                print("[Gumtree] No more pages.")
                break

            try:
                await next_page.click()
                await asyncio.sleep(random.uniform(2, 4))
                page_num += 1
            except:
                break

        # Fetch details for top results
        detailed_results = []
        for result in all_results[:limit]:
            try:
                details = await self._extract_listing_details(result["listing_url"])
                result.update(details)
                detailed_results.append(result)
                await asyncio.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                print(f"[Gumtree] Failed to get details: {e}")
                detailed_results.append(result)

        return detailed_results

    async def _extract_page_listings(self) -> List[Dict[str, Any]]:
        """Extract listings from current page."""
        # Gumtree uses multiple selectors over time — try them all
        card_selectors = [
            '[data-testid="listing-card"]',
            '.user-ad-row',
            '.search-results-page__result',
            'a[href*="/s-ad/"]',
        ]

        cards = []
        for selector in card_selectors:
            cards = await self.page.query_selector_all(selector)
            if cards:
                print(f"[Gumtree] Found {len(cards)} cards with selector: {selector}")
                break

        results = []
        for card in cards:
            try:
                # Extract href
                href = await card.get_attribute("href")
                if not href:
                    # Try finding nested link
                    link = await card.query_selector('a[href*="/s-ad/"]')
                    if link:
                        href = await link.get_attribute("href")

                if not href or "/s-ad/" not in href:
                    continue

                # Extract listing ID from URL
                listing_id_match = re.search(r"/s-ad/[^/]+/[^/]+/(\d+)", href)
                listing_id = listing_id_match.group(1) if listing_id_match else None

                # Title
                title_elem = await card.query_selector('h3, .user-ad-title, [data-testid="listing-title"], .user-ad-row__title')
                title = await title_elem.inner_text() if title_elem else ""

                # Price
                price_elem = await card.query_selector('.user-ad-price, [data-testid="listing-price"], span:has-text("$")')
                price_text = await price_elem.inner_text() if price_elem else ""
                price = self._parse_price(price_text)

                # Location
                location_elem = await card.query_selector('.user-ad-row__location, [data-testid="listing-location"]')
                location = await location_elem.inner_text() if location_elem else ""

                # Image
                img_elem = await card.query_selector('img')
                image_url = await img_elem.get_attribute("src") if img_elem else None

                # Year from title
                year = self._parse_year(title)

                results.append({
                    "listing_id": listing_id,
                    "title": title.strip(),
                    "price": price,
                    "currency": "AUD",
                    "year": year,
                    "location": location.strip(),
                    "listing_url": f"https://www.gumtree.com.au{href}" if not href.startswith("http") else href,
                    "image_url": image_url,
                    "source": "gumtree",
                    "scrape_timestamp": datetime.utcnow(),
                })
            except Exception as e:
                print(f"[Gumtree] Error parsing card: {e}")
                continue

        return results

    async def _extract_listing_details(self, url: str) -> Dict[str, Any]:
        """Fetch detailed info from listing page."""
        detail_page = await self.browser.new_page()
        try:
            await detail_page.goto(url, timeout=15000)
            await detail_page.wait_for_load_state("networkidle")

            # Description
            desc_elem = await detail_page.query_selector('[data-testid="ad-description"], .vip-ad-description, .ad-description')
            description = await desc_elem.inner_text() if desc_elem else ""

            # Odometer from description
            odometer = self._parse_odometer(description + " " + await detail_page.title())

            # All images
            img_elems = await detail_page.query_selector_all('img[src*="gumtree"]')
            image_urls = [await img.get_attribute("src") for img in img_elems[:8]]

            # Seller info
            seller_elem = await detail_page.query_selector('[data-testid="seller-name"], .seller-name')
            seller_name = await seller_elem.inner_text() if seller_elem else None

            return {
                "description": description.strip(),
                "image_urls": json.dumps(image_urls),
                "odometer": odometer,
                "odometer_unit": "km" if odometer else None,
                "seller_name": seller_name,
            }
        except Exception as e:
            print(f"[Gumtree] Failed to fetch details: {e}")
            return {}
        finally:
            await detail_page.close()

    def _parse_price(self, text: str) -> Optional[float]:
        if not text:
            return None
        match = re.search(r"\$?([\d,]+(?:\.\d{2})?)", text)
        if match:
            return float(match.group(1).replace(",", ""))
        return None

    def _parse_year(self, text: str) -> Optional[int]:
        match = re.search(r"(19|20)\d{2}", text)
        return int(match.group(0)) if match else None

    def _parse_odometer(self, text: str) -> Optional[int]:
        match = re.search(r"(\d{2,6}(?:,\d{3})?)\s*(km|kms|kilometres|kilometers)", text.lower())
        if match:
            return int(match.group(1).replace(",", ""))
        match_k = re.search(r"(\d{1,3})k\s*(km|kms)", text.lower())
        if match_k:
            return int(match_k.group(1)) * 1000
        return None
