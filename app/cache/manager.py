# ABOUTME: Split cache manager for sensor data and LLM variations
# ABOUTME: Sensor data has short TTL (2 min), variations have longer TTL (15 min)

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from app.weather.models import SensorReading


class CacheManager:
    """
    Split cache for sensor data and LLM variations.

    Sensor data: Short TTL (default 2 minutes), refreshed frequently
    Variations: Longer TTL (default 15 minutes), regenerated when rating changes
    """

    def __init__(
        self,
        sensor_ttl_seconds: int = 120,
        variations_ttl_minutes: int = 15,
        cache_ttl_minutes: Optional[int] = None
    ):
        # Legacy parameter support
        if cache_ttl_minutes is not None:
            # Old unified cache mode - use same TTL for both
            self.sensor_ttl_seconds = cache_ttl_minutes * 60
            self.variations_ttl_minutes = cache_ttl_minutes
        else:
            self.sensor_ttl_seconds = sensor_ttl_seconds
            self.variations_ttl_minutes = variations_ttl_minutes

        # Sensor cache: stores reading, ratings, and fetch timestamp
        self._sensor_cache: Optional[dict] = None

        # Variations cache: stores variations and the rating they were generated for
        self._variations_cache: Optional[dict] = None

        # Offline state
        self._is_offline: bool = False
        self._last_known_reading: Optional[SensorReading] = None

    # ==================== Sensor Cache ====================

    def set_sensor(self, reading: SensorReading, ratings: dict[str, int]) -> None:
        """
        Store sensor reading and calculated ratings.

        Args:
            reading: Fresh sensor reading
            ratings: {"sup": int, "parawing": int}
        """
        self._sensor_cache = {
            "reading": reading,
            "ratings": ratings,
            "fetched_at": datetime.now(timezone.utc)
        }
        self._is_offline = False
        self._last_known_reading = reading

    def get_sensor(self) -> Optional[dict]:
        """
        Get sensor cache if fresh.

        Returns:
            {"reading": SensorReading, "ratings": dict, "fetched_at": datetime}
            or None if stale/empty
        """
        if self.is_sensor_stale():
            return None
        return self._sensor_cache

    def get_ratings(self) -> Optional[dict[str, int]]:
        """Get current ratings from sensor cache."""
        if self._sensor_cache:
            return self._sensor_cache.get("ratings")
        return None

    def is_sensor_stale(self) -> bool:
        """Check if sensor cache needs refresh."""
        if self._sensor_cache is None:
            return True

        fetched_at = self._sensor_cache.get("fetched_at")
        if fetched_at is None:
            return True

        age = datetime.now(timezone.utc) - fetched_at
        return age.total_seconds() > self.sensor_ttl_seconds

    # ==================== Variations Cache ====================

    def set_variations(
        self,
        rating_snapshot: dict[str, int],
        variations: dict[str, dict[str, list[str]]]
    ) -> None:
        """
        Store LLM variations with the rating they were generated for.

        Args:
            rating_snapshot: {"sup": int, "parawing": int} at generation time
            variations: {"sup": {"persona_id": [responses]}, "parawing": {...}}
        """
        self._variations_cache = {
            "rating_snapshot": rating_snapshot,
            "variations": variations,
            "generated_at": datetime.now(timezone.utc)
        }

    def get_variations(self, mode: str, persona_id: str) -> list[str]:
        """Get variations for a specific mode and persona."""
        if self._variations_cache is None:
            return []
        return (
            self._variations_cache
            .get("variations", {})
            .get(mode, {})
            .get(persona_id, [])
        )

    def get_all_variations(self) -> Optional[dict]:
        """Get full variations cache."""
        return self._variations_cache

    def is_variations_stale(self) -> bool:
        """Check if variations cache has expired (time-based only)."""
        if self._variations_cache is None:
            return True

        generated_at = self._variations_cache.get("generated_at")
        if generated_at is None:
            return True

        age = datetime.now(timezone.utc) - generated_at
        return age > timedelta(minutes=self.variations_ttl_minutes)

    def should_regenerate_variations(self, current_ratings: dict[str, int]) -> bool:
        """
        Check if variations should be regenerated.

        Regenerate if:
        1. Variations cache is empty/stale (time-based)
        2. Rating has changed since variations were generated

        Args:
            current_ratings: Current {"sup": int, "parawing": int}

        Returns:
            True if variations should be regenerated
        """
        if self._variations_cache is None:
            return True

        if self.is_variations_stale():
            return True

        # Check if rating changed
        snapshot = self._variations_cache.get("rating_snapshot", {})
        return snapshot != current_ratings

    # ==================== Offline State ====================

    def set_offline(self, last_known_reading: Optional[SensorReading] = None) -> None:
        """Mark sensor as offline, preserving last known reading."""
        self._is_offline = True
        if last_known_reading is not None:
            self._last_known_reading = last_known_reading

    def is_offline(self) -> bool:
        """Check if sensor is currently offline."""
        return self._is_offline

    def get_last_known_reading(self) -> Optional[SensorReading]:
        """Get the last known good reading (for offline display)."""
        return self._last_known_reading

    # ==================== Offline Variations ====================

    def set_offline_variations(self, variations: dict[str, dict[str, list[str]]]) -> None:
        """Store offline-specific persona variations."""
        self._offline_variations = variations

    def get_offline_variations(self, mode: str, persona_id: str) -> list[str]:
        """Get offline variations for a specific persona."""
        if not hasattr(self, '_offline_variations') or self._offline_variations is None:
            return []
        return self._offline_variations.get(mode, {}).get(persona_id, [])

    # ==================== Legacy Support ====================

    def set_cache(self, data: dict[str, Any]) -> None:
        """
        Legacy method for unified cache format.
        Converts to split cache internally.
        """
        if "weather" in data and "ratings" in data:
            # Store old format with weather dict preserved
            self._sensor_cache = {
                "reading": None,  # Old format doesn't have SensorReading
                "ratings": data.get("ratings", {}),
                "fetched_at": data.get("timestamp", datetime.now(timezone.utc)),
                "legacy_weather": data.get("weather", {})  # Preserve old weather dict
            }

        if "variations" in data:
            self.set_variations(
                rating_snapshot=data.get("ratings", {}),
                variations=data.get("variations", {})
            )

    def get_cache(self) -> Optional[dict[str, Any]]:
        """
        Legacy method for unified cache format.
        Returns None if sensor is stale.
        """
        if self.is_sensor_stale():
            return None

        return {
            "timestamp": self._sensor_cache.get("fetched_at") if self._sensor_cache else None,
            "weather": self._build_weather_dict(),
            "ratings": self.get_ratings() or {},
            "variations": self._variations_cache.get("variations", {}) if self._variations_cache else {}
        }

    def _build_weather_dict(self) -> dict:
        """Build weather dict from sensor reading for legacy format."""
        if not self._sensor_cache:
            return {"wind_speed": 0, "wind_direction": "N", "wave_height": 0, "swell_direction": "N"}

        # Check if we have legacy weather data (from old unified cache)
        if "legacy_weather" in self._sensor_cache:
            return self._sensor_cache["legacy_weather"]

        # Build from SensorReading
        reading = self._sensor_cache.get("reading")
        if not reading:
            return {"wind_speed": 0, "wind_direction": "N", "wave_height": 0, "swell_direction": "N"}

        return {
            "wind_speed": reading.wind_speed_kts,
            "wind_direction": reading.wind_direction,
            "wave_height": 0,  # No wave data from sensor
            "swell_direction": "N"  # No swell data from sensor
        }

    def is_stale(self) -> bool:
        """Legacy method - checks sensor staleness."""
        return self.is_sensor_stale()

    def clear(self) -> None:
        """Clear all caches."""
        self._sensor_cache = None
        self._variations_cache = None
        self._is_offline = False
