# scraper/cache.py
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

class SearchCache:
    def __init__(self, ttl_minutes: int = 15):
        self.cache_dir = Path('.cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _get_key(self, filters: dict) -> str:
        """Generate cache key from filter params"""
        filter_str = json.dumps(filters, sort_keys=True)
        return hashlib.md5(filter_str.encode()).hexdigest()
    
    def get(self, filters: dict) -> list | None:
        key = self._get_key(filters)
        cache_file = self.cache_dir / f"{key}.json"
        
        if not cache_file.exists():
            return None
        
        # Check TTL
        modified = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - modified > self.ttl:
            cache_file.unlink()
            return None
        
        with open(cache_file) as f:
            return json.load(f)
    
    def set(self, filters: dict, data: list):
        key = self._get_key(filters)
        with open(self.cache_dir / f"{key}.json", 'w') as f:
            json.dump(data, f)
