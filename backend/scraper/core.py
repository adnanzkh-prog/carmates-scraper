# scraper/core.py
import random
import time
import logging
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential

class ScraperConfig:
    REQUESTS_PER_SECOND = 1  # Respect target servers
    DELAY_RANGE = (1, 3)     # Random delay between requests
    MAX_RETRIES = 5
    PROXY_POOL = []          # Populate with rotating proxies

def rate_limited(func):
    """Decorator to enforce rate limiting"""
    last_call = [0]
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        elapsed = time.time() - last_call[0]
        delay = random.uniform(*ScraperConfig.DELAY_RANGE)
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        last_call[0] = time.time()
        return await func(*args, **kwargs)
    
    return wrapper

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=lambda e: isinstance(e, (TimeoutError, ConnectionError))
)
@rate_limited
async def fetch_page(page, url: str):
    """Fetch with automatic retries and rate limiting"""
    try:
        response = await page.goto(url, wait_until='networkidle', timeout=30000)
        if response.status >= 400:
            raise ConnectionError(f"HTTP {response.status}")
        return await page.content()
    except Exception as e:
        logging.error(f"Failed to fetch {url}: {e}")
        raise
