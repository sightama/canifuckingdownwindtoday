# ABOUTME: Tests for weather API source clients (NOAA, OpenWeatherMap)
# ABOUTME: Uses mocked responses to avoid real API calls in tests

from unittest.mock import Mock, patch
from app.weather.sources import NOAAClient
from app.weather.models import WeatherConditions


def test_noaa_client_fetches_conditions():
    """NOAAClient should fetch and parse NOAA data"""
    # First call returns point data with forecast URL
    mock_point_response = {
        "properties": {
            "forecast": "https://api.weather.gov/gridpoints/MLB/33,76/forecast"
        }
    }
    # Second call returns forecast data
    mock_forecast_response = {
        "properties": {
            "periods": [
                {
                    "windSpeed": "15 to 20 mph",
                    "windDirection": "ESE",
                    "detailedForecast": "Seas 2 to 3 ft"
                }
            ]
        }
    }

    with patch('requests.get') as mock_get:
        # Configure mock to return different responses for each call
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = [mock_point_response, mock_forecast_response]

        client = NOAAClient()
        result = client.fetch_conditions(26.9, -80.1)

        assert isinstance(result, WeatherConditions)
        assert result.wind_speed_kts > 0
        assert result.wind_direction == "ESE"
        assert result.wave_height_ft > 0


def test_noaa_client_converts_mph_to_knots():
    """NOAAClient should convert wind speed from mph to knots"""
    mock_point_response = {
        "properties": {
            "forecast": "https://api.weather.gov/gridpoints/MLB/33,76/forecast"
        }
    }
    mock_forecast_response = {
        "properties": {
            "periods": [
                {
                    "windSpeed": "17 mph",
                    "windDirection": "E",
                    "detailedForecast": "Seas 2 ft"
                }
            ]
        }
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.side_effect = [mock_point_response, mock_forecast_response]

        client = NOAAClient()
        result = client.fetch_conditions(26.9, -80.1)

        # 17 mph ≈ 14.8 knots
        assert 14 <= result.wind_speed_kts <= 15
