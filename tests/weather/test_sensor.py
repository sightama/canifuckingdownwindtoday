# ABOUTME: Tests for WeatherFlow sensor client
# ABOUTME: Validates API parsing and error handling

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.weather.sensor import SensorClient
from app.weather.models import SensorReading


class TestSensorClient:
    """Tests for WeatherFlow SensorClient"""

    def test_fetch_returns_sensor_reading_on_success(self):
        """Successful API call returns SensorReading"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
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
                            "2025-12-10 17:51:16",
                            12.5,  # avg
                            9.8,   # lull
                            15.2,  # gust
                            28,    # dir
                            "NNE", # dir_text
                            75.5,  # atemp
                            None,  # wtemp
                            1012.7 # pres
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert isinstance(result, SensorReading)
            assert result.wind_speed_kts == 12.5
            assert result.wind_gust_kts == 15.2
            assert result.wind_lull_kts == 9.8
            assert result.wind_direction == "NNE"
            assert result.wind_degrees == 28
            assert result.air_temp_f == 75.5
            assert result.spot_name == "Jupiter-Juno Beach Pier"

    def test_fetch_returns_none_on_http_error(self):
        """HTTP error returns None"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="bad-token")
            result = client.fetch()

            assert result is None

    def test_fetch_returns_none_on_api_error_status(self):
        """API error status returns None"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {"status_code": 1, "status_message": "Invalid spot"}
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result is None

    def test_fetch_returns_none_on_network_error(self):
        """Network error returns None"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_requests.get.side_effect = Exception("Connection refused")

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result is None

    def test_fetch_returns_none_on_malformed_response(self):
        """Malformed JSON structure returns None"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"unexpected": "structure"}
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result is None

    def test_parses_utc_timestamp_correctly(self):
        """UTC timestamp is parsed into timezone-aware datetime"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test Spot",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "2025-12-10 12:51:16",
                            "2025-12-10 17:51:16",
                            10.0, 8.0, 12.0, 90, "E", 70.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result.timestamp_utc.year == 2025
            assert result.timestamp_utc.month == 12
            assert result.timestamp_utc.day == 10
            assert result.timestamp_utc.hour == 17
            assert result.timestamp_utc.minute == 51
            assert result.timestamp_utc.tzinfo == timezone.utc

    def test_uses_correct_api_endpoint_and_params(self):
        """Verifies correct API URL and parameters"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test",
                    "data_names": ["timestamp", "utc_timestamp", "avg", "lull", "gust", "dir", "dir_text", "atemp", "wtemp", "pres"],
                    "stations": [{"data_values": [["", "2025-01-01 00:00:00", 10, 8, 12, 0, "N", 70, None, 1013]]}]
                }]
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="my-token", spot_id="453")
            client.fetch()

            mock_requests.get.assert_called_once()
            call_args = mock_requests.get.call_args

            assert "api.weatherflow.com" in call_args[0][0]
            assert call_args[1]["params"]["wf_token"] == "my-token"
            assert call_args[1]["params"]["spot_list"] == "453"
            assert call_args[1]["params"]["units_wind"] == "kts"
