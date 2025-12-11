# ABOUTME: LLM API client for generating condition descriptions
# ABOUTME: Supports Google Gemini 2.5 Flash-Lite with persona-based prompts

import google.generativeai as genai
import re
from typing import Optional
from app.debug import debug_log
from app.ai.personas import PERSONAS


def parse_variations_response(response_text: str) -> dict[str, list[str]]:
    """
    Parse the mega-prompt response into a dict of persona variations.

    Expected format:
    ===PERSONA:persona_id===
    1. First response
    2. Second response
    ...

    Returns:
        {"persona_id": ["response1", "response2", ...], ...}
    """
    result: dict[str, list[str]] = {}

    # Split on persona markers
    parts = re.split(r'===PERSONA:(\w+)===', response_text)

    # parts[0] is empty or preamble, then alternating: persona_id, content, persona_id, content...
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            persona_id = parts[i].strip()
            content = parts[i + 1].strip()

            # Extract numbered responses - handle various LLM formatting quirks
            lines = []
            for line in content.split('\n'):
                line = line.strip()
                # Match various formats: "1. text", "**1.** text", "1) text", "1: text"
                match = re.match(r'^[\*]*(\d+)[\.\)\:][\*]*\s*(.+)$', line)
                if match:
                    text = match.group(2).strip()
                    # Remove markdown formatting from the text
                    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
                    text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italic
                    if text:
                        lines.append(text)

            if lines:
                result[persona_id] = lines

    return result


class LLMClient:
    """Client for generating snarky descriptions via LLM API"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash-lite")

    def generate_description(
        self,
        wind_speed: float,
        wind_direction: str,
        wave_height: float,
        swell_direction: str,
        rating: int,
        mode: str,
        persona: Optional[dict] = None
    ) -> str:
        """
        Generate snarky description of conditions

        Args:
            wind_speed: Wind speed in knots
            wind_direction: Wind direction (N, S, E, W, etc.)
            wave_height: Wave height in feet
            swell_direction: Swell direction
            rating: 1-10 rating
            mode: "sup" or "parawing"
            persona: Optional persona dict with prompt_style

        Returns:
            1-2 paragraph snarky description
        """
        mode_name = "SUP foil" if mode == "sup" else "parawing"

        # Use persona prompt style if provided, otherwise default
        if persona:
            persona_instruction = persona["prompt_style"]
            debug_log(f"Using persona: {persona['name']}", "LLM")
        else:
            persona_instruction = "You are an extremely passive-aggressive asshole"

        prompt = f"""{persona_instruction}

You are giving a {mode_name} downwind rating to some dipshit checking if they should go out in Jupiter, FL.

CONDITIONS: {wind_speed}kts {wind_direction}, {wave_height}ft waves, {swell_direction} swell. Rating: {rating}/10.

Write 2-3 sentences MAX. Be viciously aggressive in your character's style. Question their skills and life choices. Use profanity including "cunt" and "fuck". You're giving THEM this rating - roast them directly."""

        debug_log(f"Prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(prompt)
            debug_log(f"Response length: {len(response.text)} chars", "LLM")
            return response.text
        except Exception as e:
            debug_log(f"API error: {e}", "LLM")
            print(f"LLM API error: {e}")
            return f"LLM service unavailable. Conditions: {wind_speed}kts {wind_direction}, {wave_height}ft waves. Rating: {rating}/10. Figure it out yourself."

    def generate_all_variations(
        self,
        wind_speed: float,
        wind_direction: str,
        wave_height: float,
        swell_direction: str,
        rating: int,
        mode: str,
        num_variations: int = 8
    ) -> dict[str, list[str]]:
        """
        Generate variations for ALL personas in a single API call.

        Args:
            wind_speed: Wind speed in knots
            wind_direction: Wind direction (N, S, E, W, etc.)
            wave_height: Wave height in feet
            swell_direction: Swell direction
            rating: 1-10 rating
            mode: "sup" or "parawing"
            num_variations: Number of variations per persona (default 8)

        Returns:
            Dict mapping persona_id to list of response strings.
            Empty dict on error.
        """
        mode_name = "SUP foil" if mode == "sup" else "parawing"

        # Build persona descriptions for prompt
        persona_descriptions = "\n".join([
            f"- {p['id']}: {p['prompt_style'].split('.')[0]}."
            for p in PERSONAS
        ])

        persona_ids = ", ".join([p['id'] for p in PERSONAS])

        prompt = f"""Generate responses for a foiling conditions rating site.
Conditions: {wind_speed}kts {wind_direction}, {wave_height}ft waves, {swell_direction} swell.
Rating: {rating}/10 for {mode_name} foiling in Jupiter, FL.

For EACH persona below, write {num_variations} unique 2-3 sentence responses.
Be viciously aggressive, use profanity including "fuck" and "cunt", roast the reader directly.
Each response should have a different angle or insult while staying in character.

Format your response EXACTLY as shown (this format is required for parsing):
===PERSONA:persona_id===
1. [response]
2. [response]
...
{num_variations}. [response]

Generate for these personas in this exact order: {persona_ids}

PERSONA STYLES:
{persona_descriptions}
"""

        debug_log(f"Batch prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(prompt)
            debug_log(f"Batch response length: {len(response.text)} chars", "LLM")
            return parse_variations_response(response.text)
        except Exception as e:
            debug_log(f"Batch API error: {e}", "LLM")
            print(f"LLM batch API error: {e}")
            return {}

    def generate_single_persona_variations(
        self,
        wind_speed: float,
        wind_direction: str,
        wave_height: float,
        swell_direction: str,
        rating: int,
        mode: str,
        persona_id: str,
        num_variations: int = 4
    ) -> list[str]:
        """
        Generate variations for a SINGLE persona (fast path for initial load).

        Args:
            wind_speed: Wind speed in knots
            wind_direction: Wind direction (N, S, E, W, etc.)
            wave_height: Wave height in feet
            swell_direction: Swell direction
            rating: 1-10 rating
            mode: "sup" or "parawing"
            persona_id: Single persona ID to generate for
            num_variations: Number of variations (default 4)

        Returns:
            List of response strings. Empty list on error.
        """
        mode_name = "SUP foil" if mode == "sup" else "parawing"

        # Find the persona
        persona = next((p for p in PERSONAS if p["id"] == persona_id), None)
        if not persona:
            debug_log(f"Unknown persona: {persona_id}", "LLM")
            return []

        prompt = f"""Generate responses for a foiling conditions rating site.
Conditions: {wind_speed}kts {wind_direction}, {wave_height}ft waves, {swell_direction} swell.
Rating: {rating}/10 for {mode_name} foiling in Jupiter, FL.

Write {num_variations} unique 2-3 sentence responses in this character:
{persona['prompt_style']}

Be viciously aggressive, use profanity including "fuck" and "cunt", roast the reader directly.
Each response should have a different angle or insult while staying in character.

Format as numbered list:
1. [response]
2. [response]
...
"""

        debug_log(f"Single persona prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(prompt)
            debug_log(f"Single persona response length: {len(response.text)} chars", "LLM")

            # Parse numbered list - handle various LLM formatting quirks
            lines = []
            for line in response.text.strip().split('\n'):
                line = line.strip()
                # Match various formats: "1. text", "**1.** text", "1) text", "1: text"
                match = re.match(r'^[\*]*(\d+)[\.\)\:][\*]*\s*(.+)$', line)
                if match:
                    text = match.group(2).strip()
                    # Remove markdown formatting from the text
                    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
                    text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italic
                    if text:
                        lines.append(text)

            return lines
        except Exception as e:
            debug_log(f"Single persona API error: {e}", "LLM")
            print(f"LLM single persona API error: {e}")
            return []

    def generate_offline_variations(self, num_variations: int = 4) -> dict[str, list[str]]:
        """
        Generate variations for when the sensor is offline.

        Each persona comments on the outage in their unique style.

        Args:
            num_variations: Number of variations per persona (default 4)

        Returns:
            Dict mapping persona_id to list of offline response strings.
            Empty dict on error.
        """
        persona_descriptions = "\n".join([
            f"- {p['id']}: {p['prompt_style'].split('.')[0]}."
            for p in PERSONAS
        ])

        persona_ids = ", ".join([p['id'] for p in PERSONAS])

        prompt = f"""The wind sensor at Jupiter-Juno Beach Pier is OFFLINE or returning stale data.
We cannot provide a foiling conditions rating.

For EACH persona below, write {num_variations} unique 1-2 sentence responses about the sensor being offline.
Stay in character. Be witty. Reference the sensor outage. You can still use profanity and roast the user.
Don't provide any actual wind information - just comment on the fact that we can't give them a rating.

Format your response EXACTLY as shown (this format is required for parsing):
===PERSONA:persona_id===
1. [response]
2. [response]
...
{num_variations}. [response]

Generate for these personas in this exact order: {persona_ids}

PERSONA STYLES:
{persona_descriptions}
"""

        debug_log(f"Offline prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(prompt)
            debug_log(f"Offline response length: {len(response.text)} chars", "LLM")
            return parse_variations_response(response.text)
        except Exception as e:
            debug_log(f"Offline API error: {e}", "LLM")
            print(f"LLM offline API error: {e}")
            return {}
