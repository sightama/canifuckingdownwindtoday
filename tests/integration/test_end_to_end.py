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
def test_full_sup_rating_flow():
    """Test complete flow: fetch weather -> calculate score -> generate description"""
    mock_responses = create_noaa_mock_responses("18 mph", "ESE", "Seas 2 to 3 ft")

    mock_llm_response = Mock()
    mock_llm_response.text = "Perfect conditions, now don't fuck it up."

    with patch('requests.get') as mock_get, \
         patch('google.generativeai.GenerativeModel') as mock_gemini:

        # Mock NOAA API (returns different responses for each call)
        mock_get.side_effect = mock_responses

        # Mock Gemini API
        mock_gemini.return_value.generate_content.return_value = mock_llm_response

        # Run full flow
        orchestrator = AppOrchestrator(api_key="test_key")
        rating = orchestrator.get_sup_rating()

        # Verify result
        assert rating is not None
        assert 1 <= rating.score <= 10
        assert rating.mode == "sup"
        assert len(rating.description) > 0


@pytest.mark.integration
def test_full_parawing_rating_flow():
    """Test complete flow for parawing mode"""
    mock_responses = create_noaa_mock_responses("20 mph", "E", "Seas 3 ft")

    mock_llm_response = Mock()
    mock_llm_response.text = "Trashbagger conditions are ON POINT."

    with patch('requests.get') as mock_get, \
         patch('google.generativeai.GenerativeModel') as mock_gemini:

        mock_get.side_effect = mock_responses
        mock_gemini.return_value.generate_content.return_value = mock_llm_response

        orchestrator = AppOrchestrator(api_key="test_key")
        rating = orchestrator.get_parawing_rating()

        assert rating is not None
        assert 1 <= rating.score <= 10
        assert rating.mode == "parawing"


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
        assert "960r" in recommendations["code"] or "1250r" in recommendations["code"]
