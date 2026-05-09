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

    # ✅ INDENTED — INSIDE THE CLASS
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
        ...
    # (rest of your methods)
