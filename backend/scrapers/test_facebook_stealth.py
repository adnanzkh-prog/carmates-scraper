#!/usr/bin/env python3
"""
Facebook Marketplace Test Scraper
Run locally to test anti-detection before production deployment

Usage:
    python test_facebook.py "https://www.facebook.com/marketplace/sydney/search/?query=toyota"
"""

import asyncio
import sys
import json
import random
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Install playwright: pip install playwright")
    print("   Then run: playwright install chromium")
    sys.exit(1)


class TestFacebookScraper:
    """
    Test scraper for Facebook Marketplace development.
    This helps you understand Facebook's anti-bot detection before building production scraper.
    """
    
    def __init__(self, proxy=None):
        self.proxy = proxy
        self.results = []
        self.blocked = False
        self.block_reason = None
    
    async def scrape(self, search_url: str, max_listings: int = 5, headless: bool = True):
        """
        Scrape Facebook Marketplace with stealth techniques
        
        Args:
            search_url: Full Facebook Marketplace search URL
            max_listings: Number of listings to extract
            headless: False = visible browser (good for debugging)
        """
        print(f"🔍 Starting test scrape: {search_url}")
        print(f"   Proxy: {self.proxy or 'None (direct connection - high ban risk)'}")
        print(f"   Headless: {headless}")
        
        async with async_playwright() as p:
            # Browser launch options
            launch_args = {
                'headless': headless,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080',
                    '--disable-blink-features=AutomationControlled',
                ]
            }
            
            if self.proxy:
                launch_args['proxy'] = {'server': self.proxy}
            
            browser = await p.chromium.launch(**launch_args)
            
            # Create context with realistic fingerprint
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0',
                locale='en-AU',
                timezone_id='Australia/Sydney',
                geolocation={'latitude': -33.8688, 'longitude': 151.2093},
                permissions=['geolocation'],
                color_scheme='light',
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
            
            # Inject stealth scripts
            await context.add_init_script("""
                // Hide webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Fake plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin'}, 
                        {name: 'Native Client'},
                        {name: 'Widevine Content Decryption Module'}
                    ]
                });
                
                // Fake languages
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
                
                // Hide Playwright/Puppeteer traces
                delete navigator.__proto__.webdriver;
            """)
            
            page = await context.new_page()
            
            # Test 1: Navigate to Facebook homepage first (builds trust)
            print("\n📍 Step 1: Navigating to facebook.com...")
            await page.goto('https://www.facebook.com', wait_until='networkidle')
            await asyncio.sleep(random.uniform(2, 4))
            
            # Check if blocked immediately
            content = await page.content()
            if 'checkpoint' in content.lower() or 'suspended' in content.lower():
                self.blocked = True
                self.block_reason = "IP/Account blocked at homepage"
                print(f"❌ BLOCKED: {self.block_reason}")
                await browser.close()
                return self.results
            
            print("   ✅ Homepage loaded successfully")
            
            # Test 2: Navigate to Marketplace search
            print(f"\n📍 Step 2: Navigating to search URL...")
            await page.goto(search_url, wait_until='networkidle')
            await asyncio.sleep(random.uniform(3, 6))
            
            # Check for blocks
            current_url = page.url
            if 'login' in current_url:
                self.blocked = True
                self.block_reason = "Redirected to login (session required)"
                print(f"❌ BLOCKED: {self.block_reason}")
                await browser.close()
                return self.results
            
            if 'checkpoint' in current_url:
                self.blocked = True
                self.block_reason = "Security checkpoint triggered"
                print(f"❌ BLOCKED: {self.block_reason}")
                await browser.close()
                return self.results
            
            print(f"   ✅ Search page loaded: {current_url[:80]}...")
            
            # Test 3: Scroll to load listings (human-like)
            print(f"\n📍 Step 3: Scrolling to load listings...")
            for i in range(3):
                await page.mouse.wheel(0, random.randint(400, 900))
                await asyncio.sleep(random.uniform(1.5, 3))
                print(f"   Scroll {i+1}/3 complete")
            
            # Test 4: Extract listings
            print(f"\n📍 Step 4: Extracting up to {max_listings} listings...")
            
            # Try multiple selectors (Facebook changes these often)
            selectors = [
                '[role="article"]',
                'div[data-testid="marketplace_search_results"] > div',
                'a[href*="/marketplace/item/"]',
                '[data-testid="marketplace_feed_item"]'
            ]
            
            listings = []
            for selector in selectors:
                listings = await page.query_selector_all(selector)
                if len(listings) > 0:
                    print(f"   ✅ Found {len(listings)} listings with selector: {selector}")
                    break
            
            if not listings:
                print("   ⚠️ No listings found - selectors may need updating")
                # Save page HTML for debugging
                html = await page.content()
                with open('debug_facebook.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                print("   📝 Saved debug_facebook.html for analysis")
            
            # Extract data from listings
            for i, listing in enumerate(listings[:max_listings]):
                try:
                    print(f"\n   📦 Listing {i+1}/{max_listings}:")
                    
                    # Try to get title
                    title_selectors = ['span[dir="auto"]', 'span:not([class])', 'div[role="button"] span']
                    title = "Unknown"
                    for sel in title_selectors:
                        el = await listing.query_selector(sel)
                        if el:
                            text = await el.inner_text()
                            if text and len(text) > 5:
                                title = text
                                break
                    print(f"      Title: {title[:60]}...")
                    
                    # Try to get price
                    price_text = await listing.inner_text()
                    price = None
                    price_match = __import__('re').search(r'\$[\d,]+', price_text)
                    if price_match:
                        price_str = price_match.group().replace('$', '').replace(',', '')
                        price = float(price_str)
                        print(f"      Price: ${price:,.0f}")
                    
                    # Try to get URL
                    link_el = await listing.query_selector('a[href*="/marketplace/item/"]')
                    url = None
                    if link_el:
                        href = await link_el.get_attribute('href')
                        if href:
                            url = f"https://www.facebook.com{href}" if href.startswith('/') else href
                            print(f"      URL: {url[:80]}...")
                    
                    # Try to get image
                    img_el = await listing.query_selector('img')
                    image = None
                    if img_el:
                        image = await img_el.get_attribute('src')
                    
                    self.results.append({
                        'title': title,
                        'price': price,
                        'url': url,
                        'image': image,
                        'source': 'facebook-test',
                        'scraped_at': datetime.utcnow().isoformat()
                    })
                    
                except Exception as e:
                    print(f"      ⚠️ Error parsing: {e}")
                    continue
            
            # Save screenshot for debugging
            if not headless:
                await page.screenshot(path='facebook_screenshot.png')
                print("\n📸 Screenshot saved: facebook_screenshot.png")
            
            await browser.close()
            
        print(f"\n{'='*50}")
        print(f"✅ SCRAPE COMPLETE")
        print(f"   Total listings: {len(self.results)}")
        print(f"   Blocked: {self.blocked}")
        if self.block_reason:
            print(f"   Reason: {self.block_reason}")
        print(f"{'='*50}")
        
        return self.results
    
    def save_to_json(self, filename='test_results.json'):
        """Save results to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'scraped_at': datetime.utcnow().isoformat(),
                'blocked': self.blocked,
                'block_reason': self.block_reason,
                'results': self.results
            }, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {filename}")


async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Facebook Marketplace scraper')
    parser.add_argument('url', help='Facebook Marketplace search URL')
    parser.add_argument('--proxy', help='Proxy URL (http://user:pass@host:port)')
    parser.add_argument('--headless', action='store_true', help='Run headless (no visible browser)')
    parser.add_argument('--max', type=int, default=5, help='Max listings to scrape')
    parser.add_argument('--save-db', action='store_true', help='Save to database format')
    
    args = parser.parse_args()
    
    # Create scraper
    scraper = TestFacebookScraper(proxy=args.proxy)
    
    # Run scrape
    results = await scraper.scrape(
        search_url=args.url,
        max_listings=args.max,
        headless=args.headless
    )
    
    # Save results
    scraper.save_to_json()
    
    # Optionally save in database format for insertion
    if args.save_db and results:
        db_format = []
        for r in results:
            db_format.append({
                'id': f"fb-test-{hash(r['url']) & 0xFFFFFFFF}",
                'title': r['title'],
                'price': r['price'],
                'year': None,
                'make': 'Unknown',
                'model': 'Unknown',
                'odometer': None,
                'location': 'Australia',
                'source': 'Facebook Test',
                'url': r['url'],
                'images': [r['image']] if r['image'] else [],
                'scraped_at': r['scraped_at'],
                'accuracy_score': 50,  # Test data gets medium score
                'verified': False
            })
        
        with open('test_results_db_format.json', 'w') as f:
            json.dump(db_format, f, indent=2)
        print("💾 Database format saved to: test_results_db_format.json")


if __name__ == "__main__":
    asyncio.run(main())
