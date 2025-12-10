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

    def test_regenerates_variations_when_rating_changes(self):
        """LLM variations regenerate when rating changes"""
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

            # Should have generated variations
            assert mock_llm.generate_all_variations.call_count >= 1

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
