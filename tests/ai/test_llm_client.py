# ABOUTME: Tests for LLM client interface (Google Gemini API)
# ABOUTME: Uses mocked responses to avoid real API calls and costs in tests

import json
from unittest.mock import Mock, patch, MagicMock
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


def test_llm_client_accepts_persona():
    """LLMClient should use persona in prompt when provided"""
    mock_response = Mock()
    mock_response.text = "Test response"

    with patch('google.generativeai.GenerativeModel') as mock_gemini:
        mock_model = Mock()
        mock_gemini.return_value = mock_model
        mock_model.generate_content.return_value = mock_response

        client = LLMClient(api_key="test_key")
        from app.ai.personas import PERSONAS

        result = client.generate_description(
            wind_speed=18.0,
            wind_direction="S",
            wave_height=3.0,
            swell_direction="S",
            rating=7,
            mode="sup",
            persona=PERSONAS[0]  # Pass persona
        )

        # Verify persona prompt was included in the call
        call_args = mock_model.generate_content.call_args[0][0]
        assert PERSONAS[0]["prompt_style"] in call_args or PERSONAS[0]["name"] in call_args


def test_uses_gemini_2_5_flash_lite_model():
    """Verify we're using the correct model"""
    with patch('app.ai.llm_client.genai') as mock_genai:
        mock_genai.GenerativeModel.return_value = MagicMock()

        client = LLMClient(api_key="test-key")

        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.5-flash-lite")


class TestBatchVariationGeneration:
    """Tests for generating all persona variations in one API call"""

    def test_generate_all_variations_returns_dict_structure(self):
        """Batch generation returns variations keyed by persona"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            # Mock returns JSON string (what structured output produces)
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "drill_sergeant": [
                    "First drill sergeant response for testing.",
                    "Second drill sergeant response here.",
                    "Third one with some variety."
                ],
                "disappointed_dad": [
                    "First disappointed dad response.",
                    "Second disappointed dad here.",
                    "Third dad response."
                ]
            })

            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_all_variations(
                wind_speed=15.0,
                wind_direction="N",
                wave_height=2.5,
                swell_direction="NE",
                rating=7,
                mode="sup"
            )

            assert "drill_sergeant" in result
            assert "disappointed_dad" in result
            assert len(result["drill_sergeant"]) == 3
            assert len(result["disappointed_dad"]) == 3
            assert "First drill sergeant" in result["drill_sergeant"][0]

    def test_generate_all_variations_handles_api_error(self):
        """Returns empty dict on API failure"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_all_variations(
                wind_speed=15.0,
                wind_direction="N",
                wave_height=2.5,
                swell_direction="NE",
                rating=7,
                mode="sup"
            )

            assert result == {}

    def test_generate_all_variations_handles_invalid_json(self):
        """Returns empty dict if JSON parsing somehow fails"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            # This shouldn't happen with structured output, but test the error path
            mock_response = MagicMock()
            mock_response.text = "not valid json {"

            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_all_variations(
                wind_speed=15.0,
                wind_direction="N",
                wave_height=2.5,
                swell_direction="NE",
                rating=7,
                mode="sup"
            )

            # Should return empty dict on parse failure, not crash
            assert result == {}


class TestOfflineVariations:
    """Tests for generating offline persona responses"""

    def test_generate_offline_variations_returns_dict(self):
        """Offline generation returns variations keyed by persona"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            # Mock returns JSON string (what structured output produces)
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "drill_sergeant": [
                    "The sensor's AWOL, just like your commitment to this sport, maggot!",
                    "Can't get a reading? Maybe the sensor got tired of watching you fail."
                ],
                "disappointed_dad": [
                    "Even the sensor doesn't want to watch you foil today. Can't say I blame it.",
                    "The sensor's taking a break. Wish I could take a break from your excuses."
                ]
            })

            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_offline_variations()

            assert "drill_sergeant" in result
            assert "disappointed_dad" in result
            assert len(result["drill_sergeant"]) == 2
            assert "sensor" in result["drill_sergeant"][0].lower()

    def test_generate_offline_variations_handles_error(self):
        """Returns empty dict on API failure"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_offline_variations()

            assert result == {}


class TestSinglePersonaVariations:
    """Tests for generating variations for a single persona"""

    def test_generate_single_persona_variations_returns_list(self):
        """Single persona generation returns list of variations"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            # Mock returns JSON array (what structured output produces)
            mock_response = MagicMock()
            mock_response.text = json.dumps([
                "First drill sergeant response for testing.",
                "Second drill sergeant response here.",
                "Third one with some variety.",
                "Fourth response to fill it out."
            ])

            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_single_persona_variations(
                wind_speed=15.0,
                wind_direction="N",
                wave_height=0,
                swell_direction="N",
                rating=7,
                mode="sup",
                persona_id="drill_sergeant"
            )

            assert isinstance(result, list)
            assert len(result) == 4
            assert "First drill sergeant" in result[0]

    def test_generate_single_persona_variations_handles_error(self):
        """Returns empty list on API failure"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_single_persona_variations(
                wind_speed=15.0,
                wind_direction="N",
                wave_height=0,
                swell_direction="N",
                rating=7,
                mode="sup",
                persona_id="drill_sergeant"
            )

            assert result == []
