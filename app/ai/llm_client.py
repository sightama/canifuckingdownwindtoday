# ABOUTME: LLM API client for generating condition descriptions
# ABOUTME: Supports Google Gemini 2.5 Flash with fallback error handling

import google.generativeai as genai


class LLMClient:
    """Client for generating snarky descriptions via LLM API"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    def generate_description(
        self,
        wind_speed: float,
        wind_direction: str,
        wave_height: float,
        swell_direction: str,
        rating: int,
        mode: str
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

        Returns:
            1-2 paragraph snarky description
        """
        mode_name = "SUP foil" if mode == "sup" else "parawing"

        prompt = f"""You are a snarky, profanity-loving downwind foiling expert.
Write a 1-2 paragraph description of today's conditions for {mode_name} downwinding in Jupiter, FL.

CONDITIONS:
- Wind: {wind_speed}kts {wind_direction}
- Waves: {wave_height}ft
- Swell: {swell_direction}
- Rating: {rating}/10

Be a passive-aggressive asshole. Question the rider's skills. Use profanity liberally.
Be brutally honest about the conditions while roasting the rider."""

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"LLM API error: {e}")
            return f"LLM service unavailable. Conditions: {wind_speed}kts {wind_direction}, {wave_height}ft waves. Rating: {rating}/10. Figure it out yourself."
