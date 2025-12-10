# ABOUTME: End-to-end integration tests with mocked external APIs
# ABOUTME: Validates full flow from weather fetch to rating generation

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.orchestrator import AppOrchestrator
from app.weather.models import SensorReading


def create_noaa_mock_responses(wind_speed, wind_direction, seas_text):
    """Create mock responses for NOAA's two-step API (point lookup then forecast)"""
    point_response = Mock()
    point_response.json.return_value = {
        "properties": {
            "forecast": "https://api.weather.gov/gridpoints/MLB/33,57/forecast"
        }
    }
    point_response.status_code = 200
    point_response.raise_for_status = Mock()

    forecast_response = Mock()
    forecast_response.json.return_value = {
        "properties": {
            "periods": [{
                "windSpeed": wind_speed,
                "windDirection": wind_direction,
                "detailedForecast": seas_text
            }]
        }
    }
    forecast_response.status_code = 200
    forecast_response.raise_for_status = Mock()

    return [point_response, forecast_response]


def create_sensor_reading(wind_speed_kts: float, wind_direction: str) -> SensorReading:
    """Create mock SensorReading for testing"""
    return SensorReading(
        wind_speed_kts=wind_speed_kts,
        wind_gust_kts=wind_speed_kts + 3.0,
        wind_lull_kts=wind_speed_kts - 2.0,
        wind_direction=wind_direction,
        wind_degrees=0,
        air_temp_f=75.0,
        timestamp_utc=datetime.now(timezone.utc),
        spot_name="Jupiter-Juno Beach Pier"
    )


@pytest.mark.integration
def test_foil_recommendations_flow():
    """Test foil recommendation generation"""
    mock_responses = create_noaa_mock_responses("18 mph", "ESE", "Seas 3 ft")

    with patch('requests.get') as mock_get:
        mock_get.side_effect = mock_responses

        orchestrator = AppOrchestrator(api_key="test_key")
        recommendations = orchestrator.get_foil_recommendations()

        assert "code" in recommendations
        assert "kt" in recommendations
        assert "770R" in recommendations["code"] or "960R" in recommendations["code"] or "1250R" in recommendations["code"]


class TestUnifiedCacheIntegration:
    """Integration tests for the unified caching system"""

    def test_full_refresh_cycle(self):
        """Test complete refresh: weather fetch -> rating calc -> variation generation"""
        with patch('app.weather.sensor.SensorClient.fetch') as mock_sensor_fetch, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Mock sensor reading (18 knots from N)
            mock_sensor_fetch.return_value = create_sensor_reading(18.0, "N")

            # Mock LLM response with proper persona format
            mock_llm_response = MagicMock()
            mock_llm_response.text = """===PERSONA:drill_sergeant===
1. Listen up, maggot! 18 knots of offshore wind and 2.5-foot waves? This isn't a fucking daycare. Get your ass on that foil and stop whining.
2. Oh, what's the matter, recruit? Wind's blowing offshore and you need me to hold your hand? Pathetic. Real foilers don't need perfect conditions to show up.
3. I've seen better commitment from hungover civilians. 18 knots and clean seas, and you're checking the app like some kind of amateur. Disappointing.
===PERSONA:disappointed_dad===
1. Well, son, I see the wind's blowing offshore at 18 knots. I'm not saying you'll mess this up, but... you usually do.
2. Your brother wouldn't need to check an app for these conditions. He'd just know. But I guess we can't all be gifted.
3. I suppose 18 knots is decent. Though I remember when you said 15 was too much for you. I'm just... never mind.
===PERSONA:sarcastic_weatherman===
1. Well, well, well! Looks like Mother Nature decided to throw you foiling kooks a bone with 18 knots offshore! Don't blow it, Chad!
2. Exciting news, foil fans! We've got 18 knots of wind that you'll probably waste by staying on the beach scrolling Instagram. Stay classy!
3. Breaking: Local conditions actually decent for once! Wind at 18 knots, waves clean. Try not to screw it up. This is Chad Storm, over and out!
===PERSONA:jaded_local===
1. 18 knots offshore? Back in 2019, we'd have killed for these conditions and we didn't need some fucking app to tell us. You kooks don't even know.
2. Yeah, it's decent out there. Not that you'll appreciate it. Too busy taking selfies and crowding the lineup with your rental gear.
3. Offshore at 18? In the old days, the real locals would already be out there. Now it's just tourists checking apps. Pathetic.
===PERSONA:angry_coach===
1. EIGHTEEN KNOTS OFFSHORE AND YOU'RE READING THIS?! DROP AND GIVE ME TWENTY PADDLES, THEN GET YOUR ASS ON THE WATER! NOW!
2. This is PERFECT training conditions and you're wasting my time checking ratings?! I should bench you for the entire season! MOVE!
3. You call yourself a foiler?! 18 knots offshore is EXACTLY what we trained for! If you're not rigged in five minutes, you're doing punishment drills!
===PERSONA:passive_aggressive_ex===
1. Oh, 18 knots offshore? That's nice. I just think it's funny how you always said that was too windy for you, but sure, go have fun.
2. I'm so happy for you that conditions are good! Though I remember you saying you didn't really like foiling that much anyway. But that's great!
3. Wow, perfect wind and waves! I'm sure you'll have an amazing time. Not that you ever appreciated when I came to watch you. But whatever, enjoy!"""

            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            orchestrator = AppOrchestrator(api_key="test_key")

            # First call should trigger refresh
            data = orchestrator.get_cached_data()

            # Verify weather data was fetched and cached
            assert data['weather'] is not None
            assert 'wind_speed' in data['weather']
            assert 'wind_direction' in data['weather']
            assert data['weather']['wind_direction'] == 'N'

            # Verify ratings calculated for both modes
            assert 'sup' in data['ratings']
            assert 'parawing' in data['ratings']
            assert isinstance(data['ratings']['sup'], int)
            assert isinstance(data['ratings']['parawing'], int)

            # Verify variations generated for both modes
            assert 'sup' in data['variations']
            assert 'parawing' in data['variations']

            # Verify persona variations exist
            assert 'drill_sergeant' in data['variations']['sup']
            assert 'disappointed_dad' in data['variations']['sup']
            assert len(data['variations']['sup']['drill_sergeant']) == 3
            assert len(data['variations']['sup']['disappointed_dad']) == 3

            # Verify LLM was called twice (once for sup, once for parawing)
            assert mock_model.generate_content.call_count == 2

            # Second call should use cache (no new API calls)
            initial_sensor_call_count = mock_sensor_fetch.call_count
            initial_llm_call_count = mock_model.generate_content.call_count

            data2 = orchestrator.get_cached_data()

            # Verify no new API calls were made
            assert mock_sensor_fetch.call_count == initial_sensor_call_count
            assert mock_model.generate_content.call_count == initial_llm_call_count

            # Verify data is the same
            assert data2['weather']['wind_direction'] == 'N'
            assert data2['ratings'] == data['ratings']


class TestSensorIntegration:
    """Integration tests for sensor-based data flow"""

    def test_full_sensor_to_rating_flow(self):
        """Test complete flow: sensor fetch -> rating calc -> variation generation"""
        with patch('app.weather.sensor.requests') as mock_requests, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Mock WeatherFlow API response
            mock_wf_response = MagicMock()
            mock_wf_response.status_code = 200
            mock_wf_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Jupiter-Juno Beach Pier",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "2025-12-10 12:51:16",
                            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            18.0, 14.0, 22.0, 0, "N", 75.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_wf_response

            # Mock LLM response
            mock_llm_response = MagicMock()
            mock_llm_response.text = """===PERSONA:drill_sergeant===
1. Test response for integration.
===PERSONA:disappointed_dad===
1. Dad response here."""
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            # Run the flow
            orchestrator = AppOrchestrator(api_key="test-key")

            result = orchestrator.get_cached_data()

            # Verify result structure
            assert result["is_offline"] is False
            assert result["ratings"]["sup"] >= 1
            assert result["ratings"]["parawing"] >= 1
            assert result["weather"]["wind_speed"] == 18.0
            assert result["weather"]["wind_direction"] == "N"

    def test_offline_flow_when_sensor_returns_stale_data(self):
        """Test offline state when sensor data is stale"""
        with patch('app.weather.sensor.requests') as mock_requests, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Mock stale sensor data (10 min old)
            old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)

            mock_wf_response = MagicMock()
            mock_wf_response.status_code = 200
            mock_wf_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "2025-12-10 12:51:16",
                            old_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            15.0, 12.0, 18.0, 0, "N", 75.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_wf_response

            # Mock offline variations
            mock_llm_response = MagicMock()
            mock_llm_response.text = """===PERSONA:drill_sergeant===
1. Sensor's dead, maggot!"""
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            orchestrator = AppOrchestrator(api_key="test-key")

            result = orchestrator.get_cached_data()

            assert result["is_offline"] is True
            assert result["last_known_reading"] is not None
            # Verify variations structure exists (but is empty in offline mode)
            assert "variations" in result
            assert "sup" in result["variations"]
            assert "parawing" in result["variations"]
            # In offline mode, variations dict is empty in the response
            # (offline variations are cached separately and accessed via get_random_variation)
            assert result["variations"]["sup"] == {}
            assert result["variations"]["parawing"] == {}

    def test_cache_prevents_redundant_llm_calls(self):
        """LLM is not called when rating hasn't changed"""
        with patch('app.weather.sensor.requests') as mock_requests, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Setup sensor response
            mock_wf_response = MagicMock()
            mock_wf_response.status_code = 200
            mock_wf_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "ts", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            18.0, 14.0, 22.0, 0, "N", 75.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_wf_response

            mock_llm_response = MagicMock()
            mock_llm_response.text = "===PERSONA:drill_sergeant===\n1. Test."
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            orchestrator = AppOrchestrator(api_key="test-key")

            # First call - should generate variations
            orchestrator.get_cached_data()
            first_llm_count = mock_model.generate_content.call_count
            initial_sensor_call_count = mock_requests.get.call_count

            # Second call with same rating - should NOT regenerate
            # (sensor cache is fresh, variations cache is fresh, rating same)
            orchestrator.get_cached_data()
            second_llm_count = mock_model.generate_content.call_count

            # LLM should not have been called again
            assert second_llm_count == first_llm_count
            # Sensor should not have been called again
            assert mock_requests.get.call_count == initial_sensor_call_count
