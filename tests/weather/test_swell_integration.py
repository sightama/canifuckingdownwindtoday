# ABOUTME: Integration test for swell direction in weather fetching
# ABOUTME: Verifies swell direction flows through to WeatherConditions

import pytest
from unittest.mock import patch, MagicMock
from app.weather.sources import NOAAClient


class TestSwellDirectionIntegration:
    """Test that swell direction is properly extracted in fetch_conditions"""

    def test_swell_direction_extracted_from_forecast(self):
        """Swell direction should come from detailed forecast, not wind direction"""
        client = NOAAClient()

        # Mock the API responses
        mock_point_response = MagicMock()
        mock_point_response.json.return_value = {
            "properties": {"forecast": "https://api.weather.gov/forecast"}
        }

        mock_forecast_response = MagicMock()
        mock_forecast_response.json.return_value = {
            "properties": {
                "periods": [{
                    "windSpeed": "15 mph",
                    "windDirection": "NW",  # Wind from NW
                    "detailedForecast": "Northwest winds 15 mph. Seas 3 ft. Northeast swell 2 to 4 ft."
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = [mock_point_response, mock_forecast_response]

            result = client.fetch_conditions(26.9, -80.1)

            # Wind should be NW, but swell should be NE (from forecast text)
            assert result.wind_direction == "NW"
            assert result.swell_direction == "NE"

    def test_swell_direction_fallback_to_wind(self):
        """When no swell direction in text, fall back to wind direction"""
        client = NOAAClient()

        mock_point_response = MagicMock()
        mock_point_response.json.return_value = {
            "properties": {"forecast": "https://api.weather.gov/forecast"}
        }

        mock_forecast_response = MagicMock()
        mock_forecast_response.json.return_value = {
            "properties": {
                "periods": [{
                    "windSpeed": "12 mph",
                    "windDirection": "S",
                    "detailedForecast": "South winds 12 mph. Seas 2 ft."  # No swell direction
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = [mock_point_response, mock_forecast_response]

            result = client.fetch_conditions(26.9, -80.1)

            # Should fall back to wind direction
            assert result.swell_direction == "S"
