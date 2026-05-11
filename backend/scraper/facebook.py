import asyncio
import re
import json
import os
import random
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urlencode
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
        # 1. Try saved cookies first
        if await self._load_saved_cookies():
            await self.page.goto("https://www.facebook.com/", timeout=60000)
            if "login" not in self.page.url:
                print("Loaded existing session from cookies")
                return True
        
        # 2. No credentials? Return False for limited scrape mode
        if not email or not password:
            print("No credentials provided. Proceeding with limited scrape...")
            return False
        
        # 3. Automated login with provided credentials
        print(f"Logging in with email: {email[:3]}***")
        
        try:
            await self.page.goto("https://www.facebook.com/login", timeout=60000)
            print(f"Login page loaded. URL: {self.page.url}")
        except Exception as e:
            print(f"Failed to load login page: {e}")
            return False
        
        # DEBUG: Screenshot
        try:
            await self.page.screenshot(path="/tmp/login_page.png")
            print("Screenshot saved to /tmp/login_page.png")
        except:
            pass
        
        # Check if we're on login page
        if "login" not in self.page.url:
            print(f"Unexpected redirect. Current URL: {self.page.url}")
            return False
        
        # Handle cookie consent popup if present
        try:
            cookie_buttons = [
                'button[data-testid="cookie-policy-manage-dialog-accept-button"]',
                'button[title="Allow essential and optional cookies"]',
                'div[role="button"]:has-text("Allow")',
                'button:has-text("Accept")',
            ]
            for btn in cookie_buttons:
                try:
                    consent = await self.page.query_selector(btn)
                    if consent:
                        await consent.click()
                        await asyncio.sleep(1)
                        print("Cookie consent accepted")
                        break
                except:
                    continue
        except:
            pass
        
        # Wait for and fill login form with multiple selector fallbacks
        email_selectors = [
            'input[name="email"]',
            'input[id="email"]',
            'input[type="text"]',
            'input[placeholder*="Email"]',
            'input[placeholder*="Phone"]',
        ]
        
        pass_selectors = [
            'input[name="pass"]',
            'input[id="pass"]',
            'input[type="password"]',
        ]
        
        login_btn_selectors = [
            'button[name="login"]',
            'button[type="submit"]',
            'button:has-text("Log in")',
            'button:has-text("Log In")',
        ]
        
        # Try to find email field
        email_field = None
        for selector in email_selectors:
            try:
                email_field = await self.page.wait_for_selector(selector, timeout=10000)
                if email_field:
                    print(f"Found email field: {selector}")
                    break
            except:
                continue
        
        if not email_field:
            print("Could not find email field. Facebook may be showing a challenge.")
            return False
        
        # Fill credentials
        try:
            await self.page.fill('input[name="email"]', email)
            await self.page.fill('input[name="pass"]', password)
        except Exception as e:
            print(f"Fill failed: {e}")
            return False
        
        # Click login with fallback
        for btn in login_btn_selectors:
            try:
                button = await self.page.query_selector(btn)
                if button:
                    await button.click()
                    print(f"Clicked login button: {btn}")
                    break
            except:
                continue
        
        # Wait for navigation with longer timeout
        try:
            await self.page.wait_for_load_state("networkidle", timeout=45000)
        except:
            print("Network idle timeout, continuing anyway...")
        
        # Wait a bit for redirects to settle
        await asyncio.sleep(3)
        
        current_url = self.page.url
        print(f"Post-login URL: {current_url}")
        
        # Check for 2FA/checkpoint
        if "twofactor" in current_url or "checkpoint" in current_url:
            print("2FA/Checkpoint detected. Saving partial session.")
            await self._save_cookies()
            return False
        
        # Check if login succeeded
        if "login" not in current_url:
            await self._save_cookies()
            print("Login successful, cookies saved")
            return True
        else:
            print(f"Login failed. Still on: {current_url}")
            return False
    
    async def scrape_marketplace(
        self,
        query: str,
        location: Optional[str] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None,
        condition: Optional[str] = None,
        limit: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        if not location:
            location = settings.DEFAULT_LOCATION

        base_url = f"https://www.facebook.com/marketplace/{location}/search"
        params = {"query": query}

        if min_price:
            params["minPrice"] = min_price
        if max_price:
            params["maxPrice"] = max_price
        if min_year:
            params["minYear"] = min_year
        if max_year:
            params["maxYear"] = max_year
        if condition:
            params["condition"] = condition

        full_url = f"{base_url}?{urlencode(params)}"
        print(f"Navigating to: {full_url}")

        await self.page.goto(full_url, timeout=settings.SCRAPE_TIMEOUT)

        # Check if we got redirected to login
        if "login" in self.page.url:
            print("Facebook requires login for this search. Returning empty results.")
            return []

        # Scroll and extract listings
        all_results = []
        previous_count = 0
        scroll_attempts = 0
        max_scrolls = 10

        while len(all_results) < limit and scroll_attempts < max_scrolls:
            # Extract visible listings
            listings = await self._extract_visible_listings()

            # Add new unique listings
            for listing in listings:
                if listing["facebook_id"] and not any(
                    r["facebook_id"] == listing["facebook_id"] for r in all_results
                ):
                    all_results.append(listing)

            print(f"Scraped {len(all_results)} / {limit} listings")

            # Check if we found new listings
            if len(all_results) == previous_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                previous_count = len(all_results)

            # Scroll down to load more
            await self.page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(random.uniform(1.5, 3.0))

        # Fetch details for top results (limit to avoid timeout)
        detailed_results = []
        for result in all_results[:limit]:
            try:
                details = await self._extract_listing_details(result["listing_url"])
                result.update(details)
                detailed_results.append(result)
                await asyncio.sleep(random.uniform(0.5, 1.5))
            except Exception as e:
                print(f"Failed to get details for {result['listing_url']}: {e}")
                detailed_results.append(result)

        return detailed_results

    async def _extract_visible_listings(self) -> List[Dict[str, Any]]:
        selector = 'a[href*="/marketplace/item/"]'
        cards = await self.page.query_selector_all(selector)
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
