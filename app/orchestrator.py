# ABOUTME: Main application orchestrator coordinating all components
# ABOUTME: Handles sensor fetch, scoring, LLM generation, caching, and offline state

import logging
import random
from datetime import datetime, timezone
from typing import Optional

from app.config import Config
from app.weather.sensor import SensorClient
from app.weather.models import SensorReading
from app.scoring.calculator import ScoreCalculator
from app.scoring.foil_recommender import FoilRecommender
from app.ai.llm_client import LLMClient
from app.cache.manager import CacheManager
from app.debug import debug_log

log = logging.getLogger(__name__)


class AppOrchestrator:
    """Orchestrates all app components to generate ratings"""

    def __init__(self, api_key: str):
        self.sensor_client = SensorClient(
            wf_token=Config.WF_TOKEN,
            spot_id=Config.WF_SPOT_ID
        )
        self.score_calculator = ScoreCalculator()
        self.foil_recommender = FoilRecommender()
        self.llm_client = LLMClient(api_key=api_key)
        self.cache = CacheManager(
            sensor_ttl_seconds=Config.SENSOR_CACHE_TTL_SECONDS,
            variations_ttl_minutes=Config.VARIATIONS_CACHE_TTL_MINUTES
        )

    def get_cached_data(self) -> dict:
        """
        Get current data, fetching from sensor if needed.

        Returns:
            {
                "is_offline": bool,
                "timestamp": datetime or None,
                "last_known_reading": SensorReading or None,
                "weather": {...} or None,
                "ratings": {"sup": int, "parawing": int} or None,
                "variations": {...}
            }
        """
        # Check if sensor cache needs refresh
        if self.cache.is_sensor_stale():
            self._refresh_sensor()

        # Check if we're offline
        if self.cache.is_offline():
            return self._build_offline_response()

        # Get current ratings
        current_ratings = self.cache.get_ratings()

        # Check if variations need refresh (rating changed or TTL expired)
        if current_ratings and self.cache.should_regenerate_variations(current_ratings):
            self._refresh_variations(current_ratings)

        return self._build_online_response()

    def get_initial_data(self, persona_id: str) -> dict:
        """
        Fast path for initial page load.

        Returns cached data if fresh, otherwise fetches sensor data and
        generates variations for ONE persona in BOTH modes.
        Use refresh_remaining_variations() afterward to populate full cache.

        Args:
            persona_id: The persona to generate variations for

        Returns:
            Same structure as get_cached_data() but with minimal variations
        """
        # Refresh sensor if needed
        if self.cache.is_sensor_stale():
            self._refresh_sensor()

        # Check offline state
        if self.cache.is_offline():
            return self._build_offline_response()

        # Get current ratings
        sensor_data = self.cache.get_sensor()
        if not sensor_data or not sensor_data.get("reading"):
            return self._build_offline_response()

        reading = sensor_data["reading"]
        ratings = sensor_data.get("ratings", {})

        # Check if we already have fresh variations for this persona
        if self.cache.has_fresh_variations(persona_id):
            debug_log(f"Using cached variations for {persona_id}", "ORCHESTRATOR")
            variations_cache = self.cache.get_all_variations()
            return {
                "is_offline": False,
                "timestamp": sensor_data.get("fetched_at"),
                "last_known_reading": reading,
                "weather": self._reading_to_weather_dict(reading),
                "ratings": ratings,
                "variations": variations_cache.get("variations", {}),
                "initial_persona_id": persona_id
            }

        # Generate variations for single persona in BOTH modes
        sup_variations = self.llm_client.generate_single_persona_variations(
            wind_speed=reading.wind_speed_kts,
            wind_direction=reading.wind_direction,
            wave_height=0,
            swell_direction="N",
            rating=ratings.get("sup", 5),
            mode="sup",
            persona_id=persona_id
        )

        parawing_variations = self.llm_client.generate_single_persona_variations(
            wind_speed=reading.wind_speed_kts,
            wind_direction=reading.wind_direction,
            wave_height=0,
            swell_direction="N",
            rating=ratings.get("parawing", 5),
            mode="parawing",
            persona_id=persona_id
        )

        debug_log(f"Initial load: {len(sup_variations)} SUP, {len(parawing_variations)} parawing for {persona_id}", "ORCHESTRATOR")

        # Store initial variations in cache (merge to preserve other personas)
        initial_variations = {
            "sup": {persona_id: sup_variations},
            "parawing": {persona_id: parawing_variations}
        }
        self.cache.set_variations(ratings, initial_variations, merge=True)

        return {
            "is_offline": False,
            "timestamp": sensor_data.get("fetched_at"),
            "last_known_reading": reading,
            "weather": self._reading_to_weather_dict(reading),
            "ratings": ratings,
            "variations": {
                "sup": {persona_id: sup_variations},
                "parawing": {persona_id: parawing_variations}
            },
            "initial_persona_id": persona_id
        }

    def refresh_remaining_variations(
        self,
        initial_persona_id: str,
        initial_mode: str = "sup"
    ) -> None:
        """
        Background task: Populate full variations cache after initial load.

        Generates variations for all personas and both modes (SUP + Parawing).
        Call this AFTER get_initial_data() and after the page is visible.

        Args:
            initial_persona_id: Persona fetched during initial load (for logging)
            initial_mode: Mode fetched during initial load (default "sup")
        """
        if self.cache.is_offline():
            debug_log("Skipping background refresh - offline", "ORCHESTRATOR")
            return

        # Check if cache already has complete variations
        if self.cache.has_complete_variations():
            debug_log("Skipping background refresh - cache is complete", "ORCHESTRATOR")
            return

        sensor_data = self.cache.get_sensor()
        if not sensor_data or not sensor_data.get("reading"):
            debug_log("Skipping background refresh - no sensor data", "ORCHESTRATOR")
            return

        reading = sensor_data["reading"]
        ratings = self.cache.get_ratings() or {"sup": 5, "parawing": 5}

        debug_log("Starting background variation refresh", "ORCHESTRATOR")

        # Generate full variations for both modes
        variations = {"sup": {}, "parawing": {}}

        for mode in ["sup", "parawing"]:
            mode_variations = self.llm_client.generate_all_variations(
                wind_speed=reading.wind_speed_kts,
                wind_direction=reading.wind_direction,
                wave_height=0,
                swell_direction="N",
                rating=ratings[mode],
                mode=mode
            )
            variations[mode] = mode_variations

        # Merge to preserve any good data from initial load (in case batch had parsing failures)
        self.cache.set_variations(ratings, variations, merge=True)
        debug_log(f"Background refresh complete: {sum(len(v) for v in variations['sup'].values())} SUP variations", "ORCHESTRATOR")

    def _refresh_sensor(self) -> None:
        """Fetch fresh sensor data and calculate ratings."""
        print("[SENSOR] Fetching sensor data...", flush=True)

        reading = self.sensor_client.fetch()

        if reading is None:
            print("[SENSOR] Fetch returned None - marking offline", flush=True)
            self.cache.set_offline(self.cache.get_last_known_reading())
            self._ensure_offline_variations()
            return

        print(f"[SENSOR] Got reading: {reading.wind_speed_kts}kts {reading.wind_direction}", flush=True)

        # Check if reading itself is stale (sensor hasn't updated)
        if reading.is_stale(threshold_seconds=Config.SENSOR_STALE_THRESHOLD_SECONDS):
            print(f"[SENSOR] Reading is stale: {reading.timestamp_utc}", flush=True)
            self.cache.set_offline(reading)
            self._ensure_offline_variations()
            return

        # Calculate ratings
        sup_score = self.score_calculator.calculate_sup_score_from_sensor(reading)
        parawing_score = self.score_calculator.calculate_parawing_score_from_sensor(reading)

        ratings = {
            "sup": sup_score,
            "parawing": parawing_score
        }

        self.cache.set_sensor(reading, ratings)
        print(f"[SENSOR] Cached: ratings={ratings}", flush=True)

    def _refresh_variations(self, ratings: dict[str, int]) -> None:
        """Generate fresh LLM variations for current ratings."""
        debug_log(f"Refreshing variations for ratings: {ratings}", "ORCHESTRATOR")

        sensor_data = self.cache.get_sensor()
        if not sensor_data or not sensor_data.get("reading"):
            return

        reading = sensor_data["reading"]
        variations = {"sup": {}, "parawing": {}}

        for mode in ["sup", "parawing"]:
            mode_variations = self.llm_client.generate_all_variations(
                wind_speed=reading.wind_speed_kts,
                wind_direction=reading.wind_direction,
                wave_height=0,  # No wave data from sensor
                swell_direction="N",
                rating=ratings[mode],
                mode=mode
            )
            variations[mode] = mode_variations

        self.cache.set_variations(ratings, variations)
        debug_log(f"Variations cached: {sum(len(v) for v in variations['sup'].values())} SUP responses", "ORCHESTRATOR")

    def _ensure_offline_variations(self) -> None:
        """Generate offline variations if not already cached."""
        existing = self.cache.get_offline_variations("sup", "drill_sergeant")
        if existing:
            return  # Already have offline variations

        debug_log("Generating offline variations", "ORCHESTRATOR")
        offline_variations = self.llm_client.generate_offline_variations()

        if offline_variations:
            self.cache.set_offline_variations({
                "sup": offline_variations,
                "parawing": offline_variations  # Same variations for both modes
            })

    def _build_offline_response(self) -> dict:
        """Build response dict for offline state."""
        last_known = self.cache.get_last_known_reading()

        return {
            "is_offline": True,
            "timestamp": last_known.timestamp_utc if last_known else None,
            "last_known_reading": last_known,
            "weather": self._reading_to_weather_dict(last_known) if last_known else None,
            "ratings": None,
            "variations": {
                "sup": {},
                "parawing": {}
            }
        }

    def _build_online_response(self) -> dict:
        """Build response dict for online state."""
        sensor_data = self.cache.get_sensor()
        reading = sensor_data.get("reading") if sensor_data else None
        ratings = sensor_data.get("ratings") if sensor_data else {}
        fetched_at = sensor_data.get("fetched_at") if sensor_data else None

        variations_cache = self.cache.get_all_variations()
        variations = variations_cache.get("variations", {}) if variations_cache else {}

        return {
            "is_offline": False,
            "timestamp": fetched_at,
            "last_known_reading": reading,
            "weather": self._reading_to_weather_dict(reading) if reading else None,
            "ratings": ratings,
            "variations": variations
        }

    def _reading_to_weather_dict(self, reading: SensorReading) -> dict:
        """Convert SensorReading to weather dict for display."""
        return {
            "wind_speed": reading.wind_speed_kts,
            "wind_direction": reading.wind_direction,
            "wind_degrees": reading.wind_degrees,
            "wind_gust": reading.wind_gust_kts,
            "wind_lull": reading.wind_lull_kts,
            "wind_description": reading.wind_description,
            "air_temp": reading.air_temp_f,
            "water_temp": reading.water_temp_f,
            "pressure": reading.pressure_mb,
            "humidity": reading.humidity_pct,
            "wave_height": 0,  # No wave data from sensor
            "swell_direction": "N"  # No swell data from sensor
        }

    def get_random_variation(self, mode: str, persona_id: str) -> str:
        """
        Get a random variation for the given mode and persona.

        Handles both online and offline states.

        Args:
            mode: "sup" or "parawing"
            persona_id: e.g., "drill_sergeant"

        Returns:
            Random response string, or fallback if none available.
        """
        # Check if offline
        if self.cache.is_offline():
            variations = self.cache.get_offline_variations(mode, persona_id)
            if variations:
                return random.choice(variations)
            return "Sensor's offline. Can't tell you shit about the conditions right now."

        # Get online variations
        variations = self.cache.get_variations(mode, persona_id)
        if variations:
            return random.choice(variations)

        # Fallback
        ratings = self.cache.get_ratings() or {}
        rating = ratings.get(mode, 0)
        sensor_data = self.cache.get_sensor()
        reading = sensor_data.get("reading") if sensor_data else None

        if reading:
            return (
                f"Conditions: {reading.wind_speed_kts:.1f}kts {reading.wind_direction}. "
                f"Rating: {rating}/10. Figure it out yourself."
            )
        return "No data available. Go look outside."

    def get_foil_recommendations(self, score: Optional[int] = None) -> dict:
        """Get foil recommendations for current conditions."""
        if score is None:
            ratings = self.cache.get_ratings()
            score = ratings.get("sup", 5) if ratings else 5

        return {
            "code": self.foil_recommender.recommend_code(score=score),
            "kt": self.foil_recommender.recommend_kt(score=score)
        }

    def warmup_cache(self) -> None:
        """
        Warm up cache on server startup.

        Fetches sensor data, calculates ratings, and generates all persona variations
        via batch API calls. Runs in background to avoid blocking startup.
        """
        import sys
        try:
            print("[WARMUP] Starting cache warmup...", flush=True)
            sys.stdout.flush()

            # Fetch fresh sensor data
            self._refresh_sensor()

            # Check if we went offline during sensor fetch
            if self.cache.is_offline():
                print("[WARMUP] Sensor offline - generating offline variations")
                self._ensure_offline_variations()
                return

            # Get current ratings
            sensor_data = self.cache.get_sensor()
            if not sensor_data or not sensor_data.get("reading"):
                print("[WARMUP] No sensor data available - skipping")
                return

            reading = sensor_data["reading"]
            ratings = sensor_data.get("ratings", {})

            if not ratings or "sup" not in ratings:
                print(f"[WARMUP] ERROR: Invalid ratings: {ratings}")
                return

            print(f"[WARMUP] Sensor OK: {reading.wind_speed_kts}kts {reading.wind_direction}, ratings={ratings}")

            # Generate all variations for both modes via batch calls
            variations = {"sup": {}, "parawing": {}}

            for mode in ["sup", "parawing"]:
                print(f"[WARMUP] Generating {mode} variations...")
                mode_variations = self.llm_client.generate_all_variations(
                    wind_speed=reading.wind_speed_kts,
                    wind_direction=reading.wind_direction,
                    wave_height=0,
                    swell_direction="N",
                    rating=ratings[mode],
                    mode=mode
                )

                if mode_variations:
                    variations[mode] = mode_variations
                    print(f"[WARMUP] Got {len(mode_variations)} personas for {mode}")
                else:
                    # Batch failed - fall back to individual calls
                    print(f"[WARMUP] Batch failed for {mode}, trying individual calls...")
                    from app.ai.personas import PERSONAS
                    for persona in PERSONAS:
                        persona_id = persona["id"]
                        persona_variations = self.llm_client.generate_single_persona_variations(
                            wind_speed=reading.wind_speed_kts,
                            wind_direction=reading.wind_direction,
                            wave_height=0,
                            swell_direction="N",
                            rating=ratings[mode],
                            mode=mode,
                            persona_id=persona_id
                        )
                        if persona_variations:
                            variations[mode][persona_id] = persona_variations

            self.cache.set_variations(ratings, variations)
            total = sum(len(v) for v in variations['sup'].values())
            print(f"[WARMUP] Complete! {total} SUP variations cached")

        except Exception as e:
            print(f"[WARMUP] ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

    def check_and_refresh_if_needed(self) -> None:
        """
        Check if ratings changed significantly and refresh variations if needed.

        Called periodically (every 5 minutes) to keep cache fresh.
        Regenerates all variations if rating changed by more than 2 points.
        """
        debug_log("Checking if cache refresh needed", "ORCHESTRATOR")

        # Fetch fresh sensor data
        old_ratings = self.cache.get_ratings()
        self._refresh_sensor()

        # Check if we went offline
        if self.cache.is_offline():
            debug_log("Sensor offline during refresh check", "ORCHESTRATOR")
            self._ensure_offline_variations()
            return

        # Get new ratings
        new_ratings = self.cache.get_ratings()
        if not new_ratings:
            debug_log("No ratings available for refresh check", "ORCHESTRATOR")
            return

        # Compare ratings to cached snapshot
        variations_cache = self.cache.get_all_variations()
        if not variations_cache:
            debug_log("No variations cache - triggering warmup", "ORCHESTRATOR")
            self.warmup_cache()
            return

        old_snapshot = variations_cache.get("rating_snapshot", {})

        # Check if rating changed significantly
        if self._ratings_changed_significantly(new_ratings, old_snapshot):
            debug_log(f"Rating changed significantly: {old_snapshot} -> {new_ratings}, regenerating variations", "ORCHESTRATOR")
            self._refresh_variations(new_ratings)
        else:
            debug_log(f"Rating unchanged or minor change: {old_snapshot} -> {new_ratings}", "ORCHESTRATOR")

    def _ratings_changed_significantly(self, new_ratings: dict, old_ratings: dict) -> bool:
        """
        Check if either SUP or parawing rating changed by more than 2 points.

        Args:
            new_ratings: Current ratings {"sup": int, "parawing": int}
            old_ratings: Previous ratings {"sup": int, "parawing": int}

        Returns:
            True if delta > 2 for either mode
        """
        sup_delta = abs(new_ratings.get("sup", 0) - old_ratings.get("sup", 0))
        parawing_delta = abs(new_ratings.get("parawing", 0) - old_ratings.get("parawing", 0))
        return sup_delta > 2 or parawing_delta > 2
