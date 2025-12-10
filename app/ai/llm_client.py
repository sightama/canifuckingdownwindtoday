# ABOUTME: LLM API client for generating condition descriptions
# ABOUTME: Supports Google Gemini 2.0 Flash with persona-based prompts

import google.generativeai as genai
from typing import Optional
from app.debug import debug_log


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
