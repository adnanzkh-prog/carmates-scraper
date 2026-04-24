import json, re, asyncio
from playwright.async_api import async_playwright
from models import Listing

async def scrape_facebook(query="cars", max_results=20):

    listings = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # load cookies
        try:
            cookies = json.load(open("cookies.json"))
            await context.add_cookies(cookies)
        except:
            pass

        page = await context.new_page()

        await page.goto(f"https://www.facebook.com/marketplace/search/?query={query}")
        await page.wait_for_timeout(4000)

        # scroll
        for _ in range(5):
            await page.mouse.wheel(0, 3000)
            await page.wait_for_timeout(1500)

        cards = await page.query_selector_all('[role="article"]')

        for c in cards[:max_results]:
            try:
                text = await c.inner_text()
                link = await c.query_selector("a")
                url = await link.get_attribute("href") if link else ""

                price = extract_price(text)
                contacts = extract_contacts(text)

                listings.append(Listing(
                    title=text.split("\n")[0],
                    price=price,
                    description=text,
                    location=None,
                    contact_numbers=contacts,
                    posted_time=None,
                    url=url,
                    source="facebook"
                ))
            except:
                continue

        await browser.close()

    return listings


def extract_price(text):
    match = re.search(r'\$([\d,]+)', text)
    return int(match.group(1).replace(",", "")) if match else None


def extract_contacts(text):
    return re.findall(r'04\d{8}', text)
