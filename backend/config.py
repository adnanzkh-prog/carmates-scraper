import os
import random
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:STtSzbdjQbFGsEoLnxzLhhCmWCFkURPV@postgres.railway.internal:5432/railway")
    PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "False").lower() == "true"
    SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", "60000"))
    MAX_SCROLLS = int(os.getenv("MAX_SCROLLS", "30"))
    SCROLL_DELAY = float(os.getenv("SCROLL_DELAY", "2.0"))
    SESSION_COOKIE_FILE = "facebook_cookies.json"
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    DEFAULT_LOCATION = "australia"
    CURRENCY = "AUD"
    ODOMETER_UNIT = "km"
    PROXY_LIST = os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else []
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    ]

settings = Settings()