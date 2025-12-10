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


class TestSplitCache:
    """Tests for split cache with separate TTLs"""

    def test_sensor_cache_separate_from_variations(self):
        """Sensor and variations have independent staleness"""
        from app.weather.models import SensorReading

        manager = CacheManager(
            sensor_ttl_seconds=120,
            variations_ttl_minutes=15
        )

        # Set sensor data
        reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )
        manager.set_sensor(reading, ratings={"sup": 7, "parawing": 8})

        # Set variations
        manager.set_variations(
            rating_snapshot={"sup": 7, "parawing": 8},
            variations={"sup": {"persona": ["test"]}, "parawing": {}}
        )

        assert manager.is_sensor_stale() is False
        assert manager.is_variations_stale() is False

    def test_sensor_stale_after_ttl(self):
        """Sensor cache becomes stale after TTL"""
        from app.weather.models import SensorReading

        manager = CacheManager(sensor_ttl_seconds=120)

        # Set sensor data with old fetch time
        reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        # Manually set old fetch timestamp
        manager._sensor_cache = {
            "reading": reading,
            "ratings": {"sup": 7, "parawing": 8},
            "fetched_at": datetime.now(timezone.utc) - timedelta(seconds=180)
        }

        assert manager.is_sensor_stale() is True

    def test_variations_stale_when_rating_changes(self):
        """Variations become stale when rating differs from snapshot"""
        manager = CacheManager()

        # Set variations with rating snapshot
        manager.set_variations(
            rating_snapshot={"sup": 7, "parawing": 8},
            variations={"sup": {"persona": ["test"]}, "parawing": {}}
        )

        # Check staleness with different current rating
        assert manager.should_regenerate_variations(current_ratings={"sup": 8, "parawing": 8}) is True

    def test_variations_fresh_when_rating_same(self):
        """Variations stay fresh when rating matches snapshot"""
        manager = CacheManager()

        manager.set_variations(
            rating_snapshot={"sup": 7, "parawing": 8},
            variations={"sup": {"persona": ["test"]}, "parawing": {}}
        )

        assert manager.should_regenerate_variations(current_ratings={"sup": 7, "parawing": 8}) is False

    def test_get_sensor_returns_none_when_stale(self):
        """get_sensor returns None when sensor cache is stale"""
        manager = CacheManager(sensor_ttl_seconds=120)

        manager._sensor_cache = {
            "reading": None,
            "ratings": {"sup": 5, "parawing": 5},
            "fetched_at": datetime.now(timezone.utc) - timedelta(seconds=180)
        }

        assert manager.get_sensor() is None

    def test_offline_state_stored_separately(self):
        """Offline state is tracked in sensor cache"""
        from app.weather.models import SensorReading

        manager = CacheManager()

        # Store offline state with last known reading
        last_reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc) - timedelta(minutes=10),
            spot_name="Test"
        )

        manager.set_offline(last_known_reading=last_reading)

        assert manager.is_offline() is True
        assert manager.get_last_known_reading() is not None
        assert manager.get_last_known_reading().wind_speed_kts == 15.0

    def test_clear_offline_when_fresh_data(self):
        """Setting fresh sensor data clears offline state"""
        from app.weather.models import SensorReading

        manager = CacheManager()

        manager.set_offline(last_known_reading=None)
        assert manager.is_offline() is True

        # Set fresh reading
        reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )
        manager.set_sensor(reading, ratings={"sup": 7, "parawing": 8})

        assert manager.is_offline() is False
