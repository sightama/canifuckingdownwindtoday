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

    def test_parse_variations_response_extracts_all_personas(self):
        """Parser correctly splits response into persona dict"""
        response = """===PERSONA:drill_sergeant===
1. Response one.
2. Response two.
===PERSONA:angry_coach===
1. Coach response one.
2. Coach response two.
3. Coach response three."""

        from app.ai.llm_client import parse_variations_response
        result = parse_variations_response(response)

        assert len(result["drill_sergeant"]) == 2
        assert len(result["angry_coach"]) == 3
        assert "Response one" in result["drill_sergeant"][0]

    def test_parse_variations_handles_format_without_persona_prefix(self):
        """Parser handles LLM output with just ===ID=== format (no PERSONA: prefix)"""
        # This is the actual format Gemini sometimes outputs in production
        response = """===DRILL_SERGEANT===
1. What in the goddamn hell is this rating, maggot? You call that foiling?
2. You call that a rating, soldier? It's a goddamn insult to the ocean.
3. This ain't a floaty-boat cruise, you soft bastard.
===DISAPPOINTED_DAD===
1. Sigh. I'm not mad, just disappointed. Like always.
2. Your brother would have checked the conditions first.
===JADED_LOCAL===
1. Back in my day, we didn't need ratings. We just knew.
2. Another tourist asking about conditions. Great."""

        from app.ai.llm_client import parse_variations_response
        result = parse_variations_response(response)

        assert "drill_sergeant" in result
        assert "disappointed_dad" in result
        assert "jaded_local" in result
        assert len(result["drill_sergeant"]) == 3
        assert len(result["disappointed_dad"]) == 2
        assert len(result["jaded_local"]) == 2
        assert "maggot" in result["drill_sergeant"][0]

    def test_parse_variations_handles_multiline_responses(self):
        """Parser joins continuation lines to previous numbered item"""
        # LLMs sometimes wrap long responses across multiple lines
        response = """===PERSONA:drill_sergeant===
1. So, for all you armchair meteorologists and wannabe hydrofoil enthusiasts,
the conditions today in Jupiter are simply amazing and you should go out.
2. This is a shorter response on one line.
3. Another long response that the LLM decided to
wrap across multiple lines because it's verbose."""

        from app.ai.llm_client import parse_variations_response
        result = parse_variations_response(response)

        assert len(result["drill_sergeant"]) == 3
        # First response should include both lines joined
        assert "armchair meteorologists" in result["drill_sergeant"][0]
        assert "simply amazing" in result["drill_sergeant"][0]
        # Third response should be joined too
        assert "Another long response" in result["drill_sergeant"][2]
        assert "verbose" in result["drill_sergeant"][2]

    def test_parse_variations_preserves_markdown_italic_in_text(self):
        """Parser doesn't split on *word* markdown (regression test for cutoff bug)"""
        # This bug caused text to be cut off at markdown italic like *zero*
        # because the regex [=*#]+ matched single asterisks as persona delimiters
        response = """===PERSONA:broadcaster===
1. Well, folks, we have *zero* waves today! Plus, a North swell that's doing absolutely *nothing* helpful. Rating: 2/10.
2. The conditions are *terrible* and you should stay home."""

        from app.ai.llm_client import parse_variations_response
        result = parse_variations_response(response)

        assert "broadcaster" in result
        assert len(result["broadcaster"]) == 2
        # Text should NOT be cut off at *zero* - it should contain the full sentence
        assert "zero waves today" in result["broadcaster"][0]
        assert "North swell" in result["broadcaster"][0]
        assert "Rating: 2/10" in result["broadcaster"][0]
        # Markdown italic should be removed
        assert "*zero*" not in result["broadcaster"][0]
        assert "zero" in result["broadcaster"][0]
        # Second variation should also be complete
        assert "terrible" in result["broadcaster"][1]
        assert "stay home" in result["broadcaster"][1]


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

    def test_generate_single_persona_variations_handles_multiline(self):
        """Single persona generation joins continuation lines correctly"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            # LLM sometimes wraps long responses across multiple lines
            mock_response = MagicMock()
            mock_response.text = """1. Oh, you're going foiling? In
these conditions? You absolute moron, stay home.
2. This is a shorter response on one line.
3. Another long response that the LLM decided to
wrap across multiple lines because
it's verbose as hell."""

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

            assert len(result) == 3
            # First response should include BOTH lines joined
            assert "Oh, you're going foiling?" in result[0]
            assert "stay home" in result[0]  # This is from the continuation line
            # Third response should have all 3 lines joined
            assert "Another long response" in result[2]
            assert "verbose as hell" in result[2]
