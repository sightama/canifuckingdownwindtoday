# ABOUTME: Tests for main application orchestrator
# ABOUTME: Validates end-to-end flow from sensor fetch to rating generation

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from app.orchestrator import AppOrchestrator
from app.weather.models import SensorReading


class TestSensorFlow:
    """Tests for sensor-based data flow"""

    def test_get_cached_data_fetches_from_sensor(self):
        """Orchestrator fetches data from SensorClient"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            # Setup sensor
            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = mock_reading
            MockSensor.return_value = mock_sensor

            # Setup cache as stale
            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.get_ratings.return_value = {"sup": 7, "parawing": 8}
            mock_cache.should_regenerate_variations.return_value = False
            MockCache.return_value = mock_cache

            # Setup LLM
            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache

            orchestrator.get_cached_data()

            mock_sensor.fetch.assert_called_once()

    def test_detects_stale_sensor_reading(self):
        """Orchestrator marks offline when sensor timestamp is stale"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            # Setup sensor with stale reading
            old_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc) - timedelta(minutes=10),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = old_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            MockCache.return_value = mock_cache

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache

            orchestrator.get_cached_data()

            # Should have called set_offline
            mock_cache.set_offline.assert_called()

    def test_handles_sensor_fetch_failure(self):
        """Orchestrator handles None from sensor fetch gracefully"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = None
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.get_last_known_reading.return_value = None
            MockCache.return_value = mock_cache

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache

            orchestrator.get_cached_data()

            mock_cache.set_offline.assert_called()

    def test_get_cached_data_never_blocks_on_llm(self):
        """get_cached_data should never block on LLM regeneration - periodic refresh handles that"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache, \
             patch('app.orchestrator.ScoreCalculator') as MockCalc:

            mock_reading = SensorReading(
                wind_speed_kts=20.0,
                wind_gust_kts=24.0,
                wind_lull_kts=16.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = mock_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.get_ratings.return_value = {"sup": 8, "parawing": 9}
            # Even if cache says variations need regeneration...
            mock_cache.should_regenerate_variations.return_value = True
            MockCache.return_value = mock_cache

            mock_calc = MagicMock()
            mock_calc.calculate_sup_score_from_sensor.return_value = 8
            mock_calc.calculate_parawing_score_from_sensor.return_value = 9
            MockCalc.return_value = mock_calc

            mock_llm = MagicMock()
            mock_llm.generate_all_variations.return_value = {"drill_sergeant": ["test"]}
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache
            orchestrator.score_calculator = mock_calc
            orchestrator.llm_client = mock_llm

            orchestrator.get_cached_data()

            # Should NOT have called LLM - page loads must be instant
            assert mock_llm.generate_all_variations.call_count == 0

    def test_returns_offline_state_with_last_known(self):
        """When offline, returns last known reading info"""
        with patch('app.orchestrator.SensorClient'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            last_known = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc) - timedelta(minutes=20),
                spot_name="Test"
            )

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = False
            mock_cache.is_offline.return_value = True
            mock_cache.get_last_known_reading.return_value = last_known
            mock_cache.get_offline_variations.return_value = ["Sensor's dead, like your dreams."]
            MockCache.return_value = mock_cache

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.cache = mock_cache

            result = orchestrator.get_cached_data()

            assert result["is_offline"] is True
            assert result["last_known_reading"] is not None


class TestFastInitialLoad:
    """Tests for fast initial page load"""

    def test_get_initial_data_returns_minimal_structure(self):
        """Fast initial load returns data for display with single persona"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = mock_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.has_fresh_variations.return_value = False  # No cache
            mock_cache.get_sensor.return_value = {
                "reading": mock_reading,
                "ratings": {"sup": 7, "parawing": 8},
                "fetched_at": datetime.now(timezone.utc)
            }
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            mock_llm.generate_single_persona_variations.return_value = [
                "Test response 1",
                "Test response 2"
            ]
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            result = orchestrator.get_initial_data(persona_id="drill_sergeant")

            assert result["is_offline"] is False
            assert result["ratings"]["sup"] is not None
            assert "drill_sergeant" in result["variations"]["sup"]
            assert len(result["variations"]["sup"]["drill_sergeant"]) == 2

    def test_get_initial_data_generates_two_api_calls_for_both_modes(self):
        """Fast path makes LLM calls for both SUP and parawing modes"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = mock_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.has_fresh_variations.return_value = False  # No cache
            mock_cache.get_sensor.return_value = {
                "reading": mock_reading,
                "ratings": {"sup": 7, "parawing": 8},
                "fetched_at": datetime.now(timezone.utc)
            }
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            mock_llm.generate_single_persona_variations.return_value = ["Test"]
            mock_llm.generate_all_variations.return_value = {}
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            orchestrator.get_initial_data(persona_id="drill_sergeant")

            # Should call single persona method twice (once for sup, once for parawing)
            assert mock_llm.generate_single_persona_variations.call_count == 2
            # Should NOT call batch method
            assert mock_llm.generate_all_variations.call_count == 0

    def test_refresh_remaining_variations_fills_cache(self):
        """Background refresh generates all remaining variations"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )

            mock_cache = MagicMock()
            mock_cache.is_offline.return_value = False
            mock_cache.has_complete_variations.return_value = False  # Cache not complete
            mock_cache.get_sensor.return_value = {
                "reading": mock_reading,
                "ratings": {"sup": 7, "parawing": 8},
                "fetched_at": datetime.now(timezone.utc)
            }
            mock_cache.get_ratings.return_value = {"sup": 7, "parawing": 8}
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            mock_llm.generate_all_variations.return_value = {
                "drill_sergeant": ["response1"],
                "disappointed_dad": ["response2"]
            }
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            orchestrator.refresh_remaining_variations(
                initial_persona_id="drill_sergeant",
                initial_mode="sup"
            )

            # Should call generate_all_variations for both modes
            assert mock_llm.generate_all_variations.call_count == 2

            # Should update cache
            mock_cache.set_variations.assert_called()

    def test_get_initial_data_uses_cache_when_fresh(self):
        """Fast path returns cached data without LLM call if cache is fresh"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = False  # Sensor is fresh
            mock_cache.is_offline.return_value = False
            mock_cache.get_sensor.return_value = {
                "reading": mock_reading,
                "ratings": {"sup": 7, "parawing": 8},
                "fetched_at": datetime.now(timezone.utc)
            }
            # Cache has fresh variations for this persona
            mock_cache.has_fresh_variations.return_value = True
            mock_cache.get_variations.return_value = ["Cached response 1", "Cached response 2"]
            mock_cache.get_all_variations.return_value = {
                "rating_snapshot": {"sup": 7, "parawing": 8},
                "variations": {
                    "sup": {"drill_sergeant": ["Cached response 1", "Cached response 2"]},
                    "parawing": {"drill_sergeant": ["Cached parawing 1"]}
                }
            }
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            result = orchestrator.get_initial_data(persona_id="drill_sergeant")

            # Should NOT call any LLM methods - data is cached
            assert mock_llm.generate_single_persona_variations.call_count == 0
            assert mock_llm.generate_all_variations.call_count == 0

            # Should return cached data
            assert result["is_offline"] is False
            assert "drill_sergeant" in result["variations"]["sup"]

    def test_get_initial_data_fetches_both_modes(self):
        """Initial load fetches variations for BOTH sup and parawing"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = mock_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.has_fresh_variations.return_value = False  # No cache
            mock_cache.get_sensor.return_value = {
                "reading": mock_reading,
                "ratings": {"sup": 7, "parawing": 8},
                "fetched_at": datetime.now(timezone.utc)
            }
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            mock_llm.generate_single_persona_variations.return_value = ["Test response"]
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            result = orchestrator.get_initial_data(persona_id="drill_sergeant")

            # Should call LLM for BOTH modes
            assert mock_llm.generate_single_persona_variations.call_count == 2

            # Result should have variations for both modes
            assert "drill_sergeant" in result["variations"]["sup"]
            assert "drill_sergeant" in result["variations"]["parawing"]

    def test_refresh_remaining_skips_when_cache_fresh(self):
        """Background refresh does nothing if variations cache is fresh and complete"""
        with patch('app.orchestrator.SensorClient'), \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_cache = MagicMock()
            mock_cache.is_offline.return_value = False
            mock_cache.is_variations_stale.return_value = False  # Cache is fresh
            mock_cache.has_complete_variations.return_value = True  # All variations present
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            orchestrator.refresh_remaining_variations(
                initial_persona_id="drill_sergeant",
                initial_mode="sup"
            )

            # Should NOT call any LLM methods
            assert mock_llm.generate_all_variations.call_count == 0
