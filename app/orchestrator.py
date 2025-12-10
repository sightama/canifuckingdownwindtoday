# ABOUTME: Main application orchestrator coordinating all components
# ABOUTME: Handles weather fetch, scoring, LLM generation, caching, and foil recommendations

from typing import Optional
from datetime import datetime, timezone
import random
from app.config import Config
from app.weather.fetcher import WeatherFetcher
from app.scoring.calculator import ScoreCalculator
from app.scoring.foil_recommender import FoilRecommender
from app.scoring.models import ConditionRating
from app.ai.llm_client import LLMClient
from app.ai.personas import get_random_persona
from app.cache.manager import CacheManager
from app.debug import debug_log


class AppOrchestrator:
    """Orchestrates all app components to generate ratings"""

    def __init__(self, api_key: str):
        self.weather_fetcher = WeatherFetcher()
        self.score_calculator = ScoreCalculator()
        self.foil_recommender = FoilRecommender()
        self.llm_client = LLMClient(api_key=api_key)
        self.cache = CacheManager(cache_ttl_minutes=15)

    def get_sup_rating(self) -> Optional[ConditionRating]:
        """
        Get SUP foil rating (cached or fresh)

        Returns:
            ConditionRating or None if weather unavailable
        """
        # Check cache first
        cached = self.cache.get_rating("sup")
        if cached:
            return cached

        # Fetch fresh data
        return self._generate_rating("sup")

    def get_parawing_rating(self) -> Optional[ConditionRating]:
        """
        Get parawing rating (cached or fresh)

        Returns:
            ConditionRating or None if weather unavailable
        """
        # Check cache first
        cached = self.cache.get_rating("parawing")
        if cached:
            return cached

        # Fetch fresh data
        return self._generate_rating("parawing")

    def get_fresh_rating(self, mode: str, exclude_persona_id: Optional[str] = None) -> Optional[ConditionRating]:
        """
        Get fresh rating, bypassing cache. Used for page refresh.

        Args:
            mode: "sup" or "parawing"
            exclude_persona_id: Persona ID to exclude (for no-repeat rotation)

        Returns:
            ConditionRating or None if weather unavailable
        """
        return self._generate_rating(mode, exclude_persona_id=exclude_persona_id)

    def get_foil_recommendations(self, score: Optional[int] = None) -> dict:
        """
        Get foil recommendations for current conditions.

        Args:
            score: Optional score to use (if not provided, fetches weather)

        Returns:
            Dict with CODE and KT recommendations
        """
        if score is None:
            # Fetch conditions to calculate score
            conditions = self.weather_fetcher.fetch_current_conditions(
                Config.LOCATION_LAT,
                Config.LOCATION_LON
            )

            if not conditions:
                return {"code": "Weather unavailable", "kt": "Weather unavailable"}

            score = self.score_calculator.calculate_sup_score(conditions)

        return {
            "code": self.foil_recommender.recommend_code(score=score),
            "kt": self.foil_recommender.recommend_kt(score=score)
        }

    def get_weather_context(self) -> Optional[dict]:
        """
        Get current weather conditions formatted for display.

        Returns:
            Dict with wind_speed, wind_direction, wave_height, swell_direction, timestamp
            or None if weather unavailable
        """
        conditions = self.weather_fetcher.fetch_current_conditions(
            Config.LOCATION_LAT,
            Config.LOCATION_LON
        )

        if not conditions:
            return None

        return {
            "wind_speed": f"{conditions.wind_speed_kts:.1f} kts",
            "wind_direction": conditions.wind_direction,
            "wave_height": f"{conditions.wave_height_ft:.1f} ft",
            "swell_direction": conditions.swell_direction,
            "timestamp": conditions.timestamp
        }

    def get_cached_data(self) -> dict:
        """
        Get all data from unified cache. Refreshes if stale.

        Returns:
            {
                "timestamp": datetime,
                "weather": {...},
                "ratings": {"sup": int, "parawing": int},
                "variations": {"sup": {...}, "parawing": {...}}
            }
        """
        if self.cache.is_stale():
            self._refresh_cache()

        cached = self.cache.get_cache()
        if cached is None:
            # This shouldn't happen after refresh, but handle gracefully
            self._refresh_cache()
            cached = self.cache.get_cache()

        return cached or self._empty_cache_data()

    def _refresh_cache(self) -> None:
        """
        Fetch fresh weather, calculate ratings, generate all variations.
        Stores everything in unified cache.
        """
        # Fetch weather ONCE
        conditions = self.weather_fetcher.fetch_current_conditions(
            Config.LOCATION_LAT,
            Config.LOCATION_LON
        )

        if conditions is None:
            debug_log("Weather fetch failed, using empty cache", "ORCHESTRATOR")
            self.cache.set_cache(self._empty_cache_data())
            return

        weather_data = {
            "wind_speed": conditions.wind_speed_kts,
            "wind_direction": conditions.wind_direction,
            "wave_height": conditions.wave_height_ft,
            "swell_direction": conditions.swell_direction
        }

        # Calculate ratings for both modes
        sup_score = self.score_calculator.calculate_sup_score(conditions)
        parawing_score = self.score_calculator.calculate_parawing_score(conditions)

        ratings = {
            "sup": sup_score,
            "parawing": parawing_score
        }

        # Generate variations for both modes
        variations = {"sup": {}, "parawing": {}}

        for mode in ["sup", "parawing"]:
            mode_variations = self.llm_client.generate_all_variations(
                wind_speed=conditions.wind_speed_kts,
                wind_direction=conditions.wind_direction,
                wave_height=conditions.wave_height_ft,
                swell_direction=conditions.swell_direction,
                rating=ratings[mode],
                mode=mode
            )
            variations[mode] = mode_variations

        # Store everything together
        cache_data = {
            "timestamp": datetime.now(timezone.utc),
            "weather": weather_data,
            "ratings": ratings,
            "variations": variations
        }

        self.cache.set_cache(cache_data)
        debug_log(f"Cache refreshed with {sum(len(v) for v in variations['sup'].values())} SUP variations", "ORCHESTRATOR")

    def _empty_cache_data(self) -> dict:
        """Return empty cache structure for error cases."""
        return {
            "timestamp": datetime.now(timezone.utc),
            "weather": {"wind_speed": 0, "wind_direction": "N", "wave_height": 0, "swell_direction": "N"},
            "ratings": {"sup": 0, "parawing": 0},
            "variations": {"sup": {}, "parawing": {}}
        }

    def get_random_variation(self, mode: str, persona_id: str) -> str:
        """
        Get a random variation for the given mode and persona.

        Args:
            mode: "sup" or "parawing"
            persona_id: e.g., "drill_sergeant"

        Returns:
            Random response string, or fallback if none available.
        """
        cached = self.get_cached_data()

        variations = cached.get("variations", {}).get(mode, {}).get(persona_id, [])

        if variations:
            return random.choice(variations)

        # Fallback message
        weather = cached.get("weather", {})
        rating = cached.get("ratings", {}).get(mode, 0)
        return (
            f"Conditions: {weather.get('wind_speed', 0)}kts {weather.get('wind_direction', 'N')}, "
            f"{weather.get('wave_height', 0)}ft waves. Rating: {rating}/10. Figure it out yourself."
        )

    def _generate_rating(self, mode: str, exclude_persona_id: Optional[str] = None) -> Optional[ConditionRating]:
        """Generate fresh rating for given mode"""
        try:
            # Fetch weather
            conditions = self.weather_fetcher.fetch_current_conditions(
                Config.LOCATION_LAT,
                Config.LOCATION_LON
            )

            if not conditions:
                return self._create_fallback_rating(mode, "Weather data unavailable")

            # Calculate score
            if mode == "sup":
                score = self.score_calculator.calculate_sup_score(conditions)
            else:
                score = self.score_calculator.calculate_parawing_score(conditions)

            # Get random persona (excluding last used if specified)
            persona = get_random_persona(exclude_id=exclude_persona_id)

            # Generate snarky description with persona
            try:
                description = self.llm_client.generate_description(
                    wind_speed=conditions.wind_speed_kts,
                    wind_direction=conditions.wind_direction,
                    wave_height=conditions.wave_height_ft,
                    swell_direction=conditions.swell_direction,
                    rating=score,
                    mode=mode,
                    persona=persona
                )
            except Exception as e:
                print(f"LLM generation failed: {e}")
                description = self._create_fallback_description(conditions, score, mode)

            # Create rating with persona info
            rating = ConditionRating(
                score=score,
                mode=mode,
                description=description,
                persona_id=persona["id"]
            )

            # Cache it
            self.cache.set_rating(mode, rating)

            return rating

        except Exception as e:
            print(f"Error generating rating: {e}")
            return self._create_fallback_rating(mode, f"Error: {str(e)}")

    def _create_fallback_rating(self, mode: str, error_msg: str) -> ConditionRating:
        """Create fallback rating when things go wrong"""
        return ConditionRating(
            score=5,
            mode=mode,
            description=f"Unable to fetch conditions. {error_msg}. Check back later or just fucking send it anyway."
        )

    def _create_fallback_description(self, conditions, score: int, mode: str) -> str:
        """Create fallback description when LLM fails"""
        mode_name = "SUP foil" if mode == "sup" else "parawing"
        return (
            f"Conditions: {conditions.wind_speed_kts:.1f}kts {conditions.wind_direction}, "
            f"{conditions.wave_height_ft:.1f}ft waves. Rating: {score}/10 for {mode_name}. "
            f"LLM service is down so you're not getting the full snarky experience. "
            f"Figure it out yourself, you're advanced right?"
        )
