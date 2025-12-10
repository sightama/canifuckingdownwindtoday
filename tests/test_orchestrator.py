# ABOUTME: Tests for main application orchestrator
# ABOUTME: Validates end-to-end flow from weather fetch to rating generation

from unittest.mock import Mock, patch
from app.orchestrator import AppOrchestrator
from app.weather.models import WeatherConditions
from app.scoring.models import ConditionRating


def test_orchestrator_fetches_and_caches_rating():
    """Orchestrator should fetch weather, calculate rating, generate description, and cache"""
    mock_conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher, \
         patch('app.orchestrator.ScoreCalculator') as mock_calculator, \
         patch('app.orchestrator.LLMClient') as mock_llm, \
         patch('app.orchestrator.FoilRecommender') as mock_recommender:

        mock_fetcher.return_value.fetch_current_conditions.return_value = mock_conditions
        mock_calculator.return_value.calculate_sup_score.return_value = 8
        mock_llm.return_value.generate_description.return_value = "Fuck yeah, send it!"
        mock_recommender.return_value.recommend_code.return_value = "960r + 135r + short fuse"
        mock_recommender.return_value.recommend_kt.return_value = "Ginxu 950 + Stab M"

        orchestrator = AppOrchestrator(api_key="test_key")
        rating = orchestrator.get_sup_rating()

        assert isinstance(rating, ConditionRating)
        assert rating.score == 8
        assert rating.mode == "sup"
        assert "send it" in rating.description.lower()


def test_orchestrator_uses_cached_rating():
    """Orchestrator should return cached rating without fetching weather"""
    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher:
        orchestrator = AppOrchestrator(api_key="test_key")

        # Pre-cache a rating
        cached_rating = ConditionRating(score=7, mode="sup", description="Cached")
        orchestrator.cache.set_rating("sup", cached_rating)

        result = orchestrator.get_sup_rating()

        # Should return cached rating without calling weather API
        assert result == cached_rating
        mock_fetcher.return_value.fetch_current_conditions.assert_not_called()


def test_orchestrator_uses_persona():
    """Orchestrator should pass persona to LLM client"""
    mock_conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher, \
         patch('app.orchestrator.ScoreCalculator') as mock_calculator, \
         patch('app.orchestrator.LLMClient') as mock_llm, \
         patch('app.orchestrator.FoilRecommender'):

        mock_fetcher.return_value.fetch_current_conditions.return_value = mock_conditions
        mock_calculator.return_value.calculate_sup_score.return_value = 7

        orchestrator = AppOrchestrator(api_key="test_key")

        rating = orchestrator.get_sup_rating()

        # Verify persona was passed to LLM
        call_kwargs = mock_llm.return_value.generate_description.call_args[1]
        assert 'persona' in call_kwargs
        assert call_kwargs['persona'] is not None
        assert 'id' in call_kwargs['persona']


def test_orchestrator_get_fresh_rating_bypasses_cache():
    """get_fresh_rating should bypass cache and generate new"""
    mock_conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher, \
         patch('app.orchestrator.ScoreCalculator') as mock_calculator, \
         patch('app.orchestrator.LLMClient') as mock_llm, \
         patch('app.orchestrator.FoilRecommender'):

        mock_fetcher.return_value.fetch_current_conditions.return_value = mock_conditions
        mock_calculator.return_value.calculate_sup_score.return_value = 7
        mock_llm.return_value.generate_description.return_value = "Fresh snark"

        orchestrator = AppOrchestrator(api_key="test_key")

        # First call with normal method (caches it)
        orchestrator.get_sup_rating()
        first_call_count = mock_llm.return_value.generate_description.call_count

        # Second call with get_fresh should still call LLM
        orchestrator.get_fresh_rating("sup")

        assert mock_llm.return_value.generate_description.call_count > first_call_count


def test_orchestrator_get_weather_context_returns_formatted_conditions():
    """get_weather_context should return formatted weather data"""
    mock_conditions = WeatherConditions(
        wind_speed_kts=18.5,
        wind_direction="SSE",
        wave_height_ft=3.2,
        swell_direction="SE",
        timestamp="2025-11-26T14:30:00"
    )

    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher:
        mock_fetcher.return_value.fetch_current_conditions.return_value = mock_conditions

        orchestrator = AppOrchestrator(api_key="test_key")
        context = orchestrator.get_weather_context()

        assert context is not None
        assert context["wind_speed"] == "18.5 kts"
        assert context["wind_direction"] == "SSE"
        assert context["wave_height"] == "3.2 ft"
        assert context["swell_direction"] == "SE"
        assert context["timestamp"] == "2025-11-26T14:30:00"


def test_orchestrator_get_weather_context_returns_none_when_unavailable():
    """get_weather_context should return None when weather unavailable"""
    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher:
        mock_fetcher.return_value.fetch_current_conditions.return_value = None

        orchestrator = AppOrchestrator(api_key="test_key")
        context = orchestrator.get_weather_context()

        assert context is None


class TestUnifiedCache:
    """Tests for the unified caching system"""

    def test_get_cached_data_returns_fresh_cache(self):
        """Returns cached data when cache is fresh"""
        from datetime import datetime, timezone
        with patch('app.orchestrator.WeatherFetcher'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_cache = Mock()
            mock_cache.is_stale.return_value = False
            mock_cache.get_cache.return_value = {
                "timestamp": datetime.now(timezone.utc),
                "weather": {"wind_speed": 15.0, "wind_direction": "N", "wave_height": 2.0, "swell_direction": "NE"},
                "ratings": {"sup": 7, "parawing": 8},
                "variations": {"sup": {"drill_sergeant": ["test response"]}, "parawing": {}}
            }
            MockCache.return_value = mock_cache

            orchestrator = AppOrchestrator(api_key="test_key")
            orchestrator.cache = mock_cache

            result = orchestrator.get_cached_data()

            assert result["weather"]["wind_speed"] == 15.0
            assert result["ratings"]["sup"] == 7
            mock_cache.get_cache.assert_called_once()

    def test_get_cached_data_refreshes_when_stale(self):
        """Fetches fresh data when cache is stale"""
        from datetime import datetime, timezone
        with patch('app.orchestrator.WeatherFetcher') as MockFetcher, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache, \
             patch('app.orchestrator.ScoreCalculator') as MockCalc:

            # Setup cache as stale
            mock_cache = Mock()
            mock_cache.is_stale.return_value = True
            MockCache.return_value = mock_cache

            # Setup weather fetcher
            mock_weather = WeatherConditions(
                wind_speed_kts=20.0,
                wind_direction="S",
                wave_height_ft=3.0,
                swell_direction="SE",
                timestamp="2025-12-09T12:00:00"
            )
            mock_fetcher = Mock()
            mock_fetcher.fetch_current_conditions.return_value = mock_weather
            MockFetcher.return_value = mock_fetcher

            # Setup calculator
            mock_calc = Mock()
            mock_calc.calculate_sup_score.return_value = 8
            mock_calc.calculate_parawing_score.return_value = 7
            MockCalc.return_value = mock_calc

            # Setup LLM
            mock_llm = Mock()
            mock_llm.generate_all_variations.return_value = {
                "drill_sergeant": ["response 1", "response 2"]
            }
            MockLLM.return_value = mock_llm

            orchestrator = AppOrchestrator(api_key="test_key")
            orchestrator.cache = mock_cache
            orchestrator.weather_fetcher = mock_fetcher
            orchestrator.llm_client = mock_llm
            orchestrator.score_calculator = mock_calc

            result = orchestrator.get_cached_data()

            # Verify weather was fetched
            mock_fetcher.fetch_current_conditions.assert_called()
            # Verify LLM was called for both modes
            assert mock_llm.generate_all_variations.call_count == 2
            # Verify cache was updated
            mock_cache.set_cache.assert_called_once()

    def test_get_random_variation_returns_variation(self):
        """Returns a random variation for given persona and mode"""
        from datetime import datetime, timezone
        with patch('app.orchestrator.WeatherFetcher'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_cache = Mock()
            mock_cache.is_stale.return_value = False
            mock_cache.get_cache.return_value = {
                "timestamp": datetime.now(timezone.utc),
                "weather": {},
                "ratings": {"sup": 7, "parawing": 8},
                "variations": {
                    "sup": {
                        "drill_sergeant": ["response A", "response B", "response C"]
                    },
                    "parawing": {}
                }
            }
            MockCache.return_value = mock_cache

            orchestrator = AppOrchestrator(api_key="test_key")
            orchestrator.cache = mock_cache

            result = orchestrator.get_random_variation("sup", "drill_sergeant")

            assert result in ["response A", "response B", "response C"]

    def test_get_random_variation_returns_fallback_when_missing(self):
        """Returns fallback message when no variations cached"""
        from datetime import datetime, timezone
        with patch('app.orchestrator.WeatherFetcher'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_cache = Mock()
            mock_cache.is_stale.return_value = False
            mock_cache.get_cache.return_value = {
                "timestamp": datetime.now(timezone.utc),
                "weather": {"wind_speed": 10.0, "wind_direction": "N", "wave_height": 1.0, "swell_direction": "E"},
                "ratings": {"sup": 5, "parawing": 5},
                "variations": {"sup": {}, "parawing": {}}
            }
            MockCache.return_value = mock_cache

            orchestrator = AppOrchestrator(api_key="test_key")
            orchestrator.cache = mock_cache

            result = orchestrator.get_random_variation("sup", "drill_sergeant")

            assert "conditions" in result.lower() or "figure it out" in result.lower()
