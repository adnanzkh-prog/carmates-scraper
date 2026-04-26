# scraper/api_first.py
import asyncio
from playwright.async_api import async_playwright
import json

async def intercept_api_data(url: str):
    """Intercept API responses instead of parsing DOM"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        )
        page = await context.new_page()
        
        api_data = []
        
        # Intercept network responses
        page.on('response', lambda response: handle_response(response, api_data))
        
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(2)  # Allow final API calls to complete
        
        await browser.close()
        return api_data

async def handle_response(response, api_data):
    """Capture API responses containing car listings"""
    if '/api/search' in response.url or '/api/listings' in response.url:
        try:
            json_data = await response.json()
            api_data.extend(json_data.get('results', []))
        except:
            pass
