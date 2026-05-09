import asyncio
import re
import json
import os
import random
from typing import List, Dict, Optional, Any
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import stealth_async
from config import settings

class FacebookMarketplaceScraper:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.current_retry = 0

async def __aenter__(self):
    self.playwright = await async_playwright().start()
    launch_options = {
        "headless": True,  # ← FORCE HEADLESS
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

    async def _load_saved_cookies(self) -> bool:
        if os.path.exists(settings.SESSION_COOKIE_FILE):
            with open(settings.SESSION_COOKIE_FILE, "r") as f:
                cookies = json.load(f)
            await self.page.context.add_cookies(cookies)
            return True
        return False

    async def _save_cookies(self):
        cookies = await self.page.context.cookies()
        with open(settings.SESSION_COOKIE_FILE, "w") as f:
            json.dump(cookies, f, indent=2)

    async def login(self, email: str = None, password: str = None):
        if await self._load_saved_cookies():
            await self.page.goto("https://www.facebook.com/", timeout=settings.SCRAPE_TIMEOUT)
            if "login" not in self.page.url:
                print("✅ Loaded existing session")
                return
        await self.page.goto("https://www.facebook.com/login", timeout=settings.SCRAPE_TIMEOUT)
        if email and password:
            await self.page.fill('input[name="email"]', email)
            await self.page.fill('input[name="pass"]', password)
            await self.page.click('button[name="login"]')
            await self.page.wait_for_load_state("networkidle")
            if "twofactor" in self.page.url or "checkpoint" in self.page.url:
                print("⚠️ 2FA required. Complete manually.")
                input("Press Enter after completing 2FA...")
        else:
            print("🔐 Please log in manually within 5 minutes.")
            for _ in range(60):
                await asyncio.sleep(5)
                if "login" not in self.page.url and "checkpoint" not in self.page.url:
                    break
        await self._save_cookies()
        print("✅ Login successful")

    async def scrape_marketplace(self, query: str, location: Optional[str] = None,
                                 min_price: Optional[float] = None, max_price: Optional[float] = None,
                                 min_year: Optional[int] = None, max_year: Optional[int] = None,
                                 condition: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        from urllib.parse import urlencode
        if not location:
            location = settings.DEFAULT_LOCATION
        base_url = f"https://www.facebook.com/marketplace/{location}/search"
        params = {"query": query}
        if min_price is not None:
            params["minPrice"] = min_price
        if max_price is not None:
            params["maxPrice"] = max_price
        if min_year:
            params["minYear"] = min_year
        if max_year:
            params["maxYear"] = max_year
        if condition:
            params["condition"] = condition
        full_url = f"{base_url}?{urlencode(params)}"
        print(f"🌐 Navigating to: {full_url}")
        try:
            await self.page.goto(full_url, timeout=settings.SCRAPE_TIMEOUT)
        except Exception as e:
            if self.current_retry < settings.MAX_RETRIES:
                self.current_retry += 1
                wait = 2 ** self.current_retry
                print(f"Retrying in {wait}s (attempt {self.current_retry})")
                await asyncio.sleep(wait)
                return await self.scrape_marketplace(query, location, min_price, max_price,
                                                     min_year, max_year, condition, limit)
            else:
                raise
        try:
            await self.page.wait_for_selector('[aria-label="Marketplace feed"]', timeout=10000)
        except:
            await self.page.wait_for_selector('div[role="feed"]', timeout=10000)
        listings_data = []
        last_height = 0
        scroll_attempts = 0
        while len(listings_data) < limit and scroll_attempts < settings.MAX_SCROLLS:
            new_listings = await self._extract_visible_listings()
            existing_ids = {l.get("facebook_id") for l in listings_data}
            for listing in new_listings:
                if listing.get("facebook_id") not in existing_ids:
                    listings_data.append(listing)
            print(f"📊 Scraped {len(listings_data)} / {limit} listings")
            if len(listings_data) >= limit:
                break
            scroll_distance = random.randint(300, 800)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_distance})")
            await asyncio.sleep(random.uniform(settings.SCROLL_DELAY - 0.5, settings.SCROLL_DELAY + 0.5))
            new_height = await self.page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_height = new_height
            load_more = await self.page.query_selector('div[aria-label="Load more"]')
            if load_more:
                await load_more.click()
                await asyncio.sleep(1)
        if limit <= 20:
            for i, listing in enumerate(listings_data):
                if listing.get("listing_url"):
                    detailed = await self._extract_listing_details(listing["listing_url"])
                    listings_data[i].update(detailed)
        return listings_data[:limit]

    async def _extract_visible_listings(self) -> List[Dict[str, Any]]:
        cards = await self.page.query_selector_all('a[href*="/marketplace/item/"]')
        results = []
        for card in cards:
            try:
                href = await card.get_attribute("href")
                if not href:
                    continue
                fb_id_match = re.search(r"/item/(\d+)", href)
                facebook_id = fb_id_match.group(1) if fb_id_match else None
                title_elem = await card.query_selector('span[dir="auto"]')
                title = await title_elem.inner_text() if title_elem else ""
                price_elem = await card.query_selector('span[dir="auto"]:has-text("$")')
                price_text = await price_elem.inner_text() if price_elem else ""
                price = self._parse_price(price_text)
                location_elem = await card.query_selector('div[dir="auto"]:nth-child(2)')
                location = await location_elem.inner_text() if location_elem else ""
                year = self._parse_year(title)
                odometer = self._parse_odometer(title)
                results.append({
                    "facebook_id": facebook_id,
                    "title": title.strip(),
                    "price": price,
                    "currency": settings.CURRENCY,
                    "year": year,
                    "odometer": odometer,
                    "odometer_unit": settings.ODOMETER_UNIT,
                    "location": location.strip(),
                    "listing_url": f"https://facebook.com{href}" if not href.startswith("http") else href,
                    "scrape_timestamp": datetime.utcnow(),
                })
            except Exception as e:
                print(f"Error parsing card: {e}")
                continue
        return results

    async def _extract_listing_details(self, url: str) -> Dict[str, Any]:
        detail_page = await self.browser.new_page()
        try:
            await detail_page.goto(url, timeout=10000)
            await detail_page.wait_for_load_state("networkidle")
            desc_elem = await detail_page.query_selector('div[data-ad-preview="message"]')
            description = await desc_elem.inner_text() if desc_elem else ""
            image_elems = await detail_page.query_selector_all('img[src*=".jpg"]')
            image_urls = [await img.get_attribute("src") for img in image_elems[:5]]
            condition_elem = await detail_page.query_selector('span:has-text("Condition")')
            condition = None
            if condition_elem:
                parent = await condition_elem.evaluate_handle("el => el.parentElement")
                condition = await parent.evaluate("el => el.innerText")
            return {
                "description": description,
                "image_urls": json.dumps(image_urls),
                "condition": condition,
            }
        except Exception as e:
            print(f"Failed to fetch details: {e}")
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
        match = re.search(r"\b(19|20)\d{2}\b", text)
        return int(match.group(0)) if match else None

    def _parse_odometer(self, text: str) -> Optional[int]:
        match = re.search(r"(\d{2,5}(?:,\d{3})?)\s*km", text.lower())
        if match:
            return int(match.group(1).replace(",", ""))
        match_k = re.search(r"(\d{1,3})k\s*km", text.lower())
        if match_k:
            return int(match_k.group(1)) * 1000
        return None
