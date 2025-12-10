# ABOUTME: End-to-end integration tests with mocked external APIs
# ABOUTME: Validates full flow from weather fetch to rating generation

import pytest
from unittest.mock import Mock, patch
from app.orchestrator import AppOrchestrator


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
