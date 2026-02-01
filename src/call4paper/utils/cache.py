"""Cache management for CFP data."""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

from .config import Config


class CacheManager:
    """Manages caching of CFP data with TTL."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.ttl_hours = ttl_hours
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, identifier: str) -> str:
        """Generate cache key from identifier."""
        return hashlib.md5(identifier.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get full path for cache file."""
        return self.cache_dir / f"{key}.json"

    def get(self, identifier: str) -> Optional[dict]:
        """Retrieve cached data if valid.

        Args:
            identifier: Unique identifier for the cached data (e.g., URL or journal name)

        Returns:
            Cached data dict if valid, None otherwise
        """
        key = self._get_cache_key(identifier)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)

            # Check TTL
            cached_at = datetime.fromisoformat(cached.get("cached_at", ""))
            if datetime.now() - cached_at > timedelta(hours=self.ttl_hours):
                # Cache expired
                cache_path.unlink(missing_ok=True)
                return None

            return cached.get("data")
        except (json.JSONDecodeError, ValueError, KeyError):
            # Invalid cache file
            cache_path.unlink(missing_ok=True)
            return None

    def set(self, identifier: str, data: Any) -> None:
        """Store data in cache.

        Args:
            identifier: Unique identifier for the cached data
            data: Data to cache (must be JSON serializable)
        """
        key = self._get_cache_key(identifier)
        cache_path = self._get_cache_path(key)

        cache_entry = {
            "cached_at": datetime.now().isoformat(),
            "identifier": identifier,
            "data": data,
        }

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_entry, f, ensure_ascii=False, indent=2)

    def invalidate(self, identifier: str) -> bool:
        """Invalidate cached data.

        Args:
            identifier: Unique identifier to invalidate

        Returns:
            True if cache was invalidated, False if not found
        """
        key = self._get_cache_key(identifier)
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear_all(self) -> int:
        """Clear all cached data.

        Returns:
            Number of cache files removed
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count
