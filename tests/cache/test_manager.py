# ABOUTME: Tests for cache management and refresh logic
# ABOUTME: Validates in-memory caching and expiration behavior

from datetime import datetime, timedelta, timezone
from app.cache.manager import CacheManager


class TestUnifiedCache:
    """Tests for the new unified cache structure"""

    def test_set_and_get_unified_cache(self):
        """Cache stores weather, ratings, and variations together"""
        manager = CacheManager(cache_ttl_minutes=15)

        cache_data = {
            "timestamp": datetime.now(timezone.utc),
            "weather": {
                "wind_speed": 15.2,
                "wind_direction": "N",
                "wave_height": 2.5,
                "swell_direction": "NE"
            },
            "ratings": {
                "sup": 7,
                "parawing": 8
            },
            "variations": {
                "sup": {
                    "drill_sergeant": ["Response 1", "Response 2"],
                    "disappointed_dad": ["Response 1", "Response 2"]
                },
                "parawing": {
                    "drill_sergeant": ["Response 1", "Response 2"],
                    "disappointed_dad": ["Response 1", "Response 2"]
                }
            }
        }

        manager.set_cache(cache_data)
        result = manager.get_cache()

        assert result is not None
        assert result["weather"]["wind_speed"] == 15.2
        assert result["ratings"]["sup"] == 7
        assert len(result["variations"]["sup"]["drill_sergeant"]) == 2

    def test_cache_returns_none_when_stale(self):
        """Cache returns None after TTL expires"""
        manager = CacheManager(cache_ttl_minutes=15)

        # Set cache with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        cache_data = {
            "timestamp": old_time,
            "weather": {"wind_speed": 10.0, "wind_direction": "S", "wave_height": 1.0, "swell_direction": "E"},
            "ratings": {"sup": 5, "parawing": 5},
            "variations": {"sup": {}, "parawing": {}}
        }

        manager.set_cache(cache_data)
        result = manager.get_cache()

        assert result is None

    def test_cache_returns_data_when_fresh(self):
        """Cache returns data within TTL"""
        manager = CacheManager(cache_ttl_minutes=15)

        # Set cache with recent timestamp
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        cache_data = {
            "timestamp": recent_time,
            "weather": {"wind_speed": 10.0, "wind_direction": "S", "wave_height": 1.0, "swell_direction": "E"},
            "ratings": {"sup": 5, "parawing": 5},
            "variations": {"sup": {}, "parawing": {}}
        }

        manager.set_cache(cache_data)
        result = manager.get_cache()

        assert result is not None
        assert result["weather"]["wind_speed"] == 10.0

    def test_is_cache_stale_when_empty(self):
        """Empty cache is considered stale"""
        manager = CacheManager(cache_ttl_minutes=15)

        assert manager.is_stale() is True

    def test_is_cache_stale_when_old(self):
        """Cache older than TTL is stale"""
        manager = CacheManager(cache_ttl_minutes=15)

        old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        cache_data = {
            "timestamp": old_time,
            "weather": {},
            "ratings": {},
            "variations": {}
        }
        manager.set_cache(cache_data)

        assert manager.is_stale() is True

    def test_is_cache_fresh_when_recent(self):
        """Cache within TTL is not stale"""
        manager = CacheManager(cache_ttl_minutes=15)

        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        cache_data = {
            "timestamp": recent_time,
            "weather": {},
            "ratings": {},
            "variations": {}
        }
        manager.set_cache(cache_data)

        assert manager.is_stale() is False
