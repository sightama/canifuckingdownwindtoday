# ABOUTME: Tests for LLM client interface (Google Gemini API)
# ABOUTME: Uses mocked responses to avoid real API calls and costs in tests

from unittest.mock import Mock, patch
from app.ai.llm_client import LLMClient


def test_llm_client_generates_description():
    """LLMClient should generate snarky description from conditions"""
    mock_response = Mock()
    mock_response.text = "Conditions are decent but you're probably gonna fuck it up anyway."

    with patch('google.generativeai.GenerativeModel') as mock_gemini:
        mock_gemini.return_value.generate_content.return_value = mock_response

        client = LLMClient(api_key="test_key")
        result = client.generate_description(
            wind_speed=18.0,
            wind_direction="S",
            wave_height=3.0,
            swell_direction="S",
            rating=7,
            mode="sup"
        )

        assert isinstance(result, str)
        assert len(result) > 0


def test_llm_client_handles_api_failure():
    """LLMClient should handle API failures gracefully"""
    with patch('google.generativeai.GenerativeModel') as mock_gemini:
        mock_gemini.return_value.generate_content.side_effect = Exception("API error")

        client = LLMClient(api_key="test_key")
        result = client.generate_description(
            wind_speed=18.0,
            wind_direction="S",
            wave_height=3.0,
            swell_direction="S",
            rating=7,
            mode="sup"
        )

        # Should return fallback message on failure
        assert result is not None
        assert "error" in result.lower() or "unavailable" in result.lower()
