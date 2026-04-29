# backend/scrapers/test_facebook_stealth.py
"""
Test scraper for Facebook Marketplace
Run this locally to develop anti-detection techniques
"""

import asyncio
import random
import json
from playwright.async_api import async_playwright

class StealthFacebookScraper:
    """
    Experimental scraper using advanced anti-detection.
    NOT for production - use Apify for that.
    """
    
    def __init__(self):
        self.proxy_pool = [
            # Add residential proxies here
            # "http://user:pass@proxy1.com:8080",
        ]
    
    async def scrape(self, search_url: str, max_listings: int = 5):
        async with async_playwright() as p:
            # Launch with stealth settings
            browser = await p.chromium.launch(
                headless=True,  # Set False to see browser
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                ]
            )
            
            # Create context with realistic fingerprint
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
                locale='en-AU',
                timezone_id='Australia/Sydney',
                geolocation={'latitude': -33.8688, 'longitude': 151.2093},  # Sydney
                permissions=['geolocation'],
                color_scheme='light',
                # Add real browser headers
                extra_http_headers={
                    'Accept-Language': 'en-AU,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Inject stealth scripts to hide automation
            await context.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-AU', 'en', 'en-US']
                });
                
                // Hide Chrome runtime
                window.chrome = { runtime: {} };
                
                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            page = await context.new_page()
            
            # Human-like navigation
            await page.goto('https://www.facebook.com', wait_until='networkidle')
            await asyncio.sleep(random.uniform(2, 4))
            
            # Navigate to Marketplace
            await page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(3, 6))
            
            # Scroll like human
            for _ in range(3):
                await page.mouse.wheel(0, random.randint(300, 800))
                await asyncio.sleep(random.uniform(1, 3))
            
            # Extract listings
            listings = await page.query_selector_all('[role="article"]')
            results = []
            
            for listing in listings[:max_listings]:
                try:
                    title_el = await listing.query_selector('span[dir="auto"]')
                    title = await title_el.inner_text() if title_el else 'Unknown'
                    
                    # Click to get details (human-like)
                    await listing.click()
                    await asyncio.sleep(random.uniform(2, 4))
                    
                    # Get URL from address bar
                    url = page.url
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'source': 'facebook-test'
                    })
                    
                    # Go back
                    await page.go_back()
                    await asyncio.sleep(random.uniform(1, 2))
                    
                except Exception as e:
                    print(f"Parse error: {e}")
            
            await browser.close()
            return results

# Run test
async def main():
    scraper = StealthFacebookScraper()
    results = await scraper.scrape(
        "https://www.facebook.com/marketplace/sydney/search/?query=toyota&category_id=807311116002614",
        max_listings=3
    )
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
