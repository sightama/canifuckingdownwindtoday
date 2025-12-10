# ABOUTME: Unified cache manager for weather, ratings, and LLM variations
# ABOUTME: Single cache with configurable TTL, stores everything together

from datetime import datetime, timezone, timedelta
from typing import Any, Optional


class CacheManager:
    """
    Unified cache for weather data, ratings, and persona variations.

    Stores everything together with a single timestamp to ensure consistency.
    Default TTL is 15 minutes.
    """

    def __init__(self, cache_ttl_minutes: int = 15):
        self.cache_ttl_minutes = cache_ttl_minutes
        self._cache: Optional[dict[str, Any]] = None

    def set_cache(self, data: dict[str, Any]) -> None:
        """
        Store unified cache data.

        Expected structure:
        {
            "timestamp": datetime (UTC),
            "weather": {"wind_speed": float, "wind_direction": str, ...},
            "ratings": {"sup": int, "parawing": int},
            "variations": {"sup": {"persona_id": [str, ...]}, "parawing": {...}}
        }
        """
        self._cache = data

    def get_cache(self) -> Optional[dict[str, Any]]:
        """
        Get cached data if fresh, None if stale or empty.
        """
        if self.is_stale():
            return None
        return self._cache

    def is_stale(self) -> bool:
        """
        Check if cache is stale (empty or older than TTL).
        """
        if self._cache is None:
            return True

        timestamp = self._cache.get("timestamp")
        if timestamp is None:
            return True

        age = datetime.now(timezone.utc) - timestamp
        return age > timedelta(minutes=self.cache_ttl_minutes)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache = None
