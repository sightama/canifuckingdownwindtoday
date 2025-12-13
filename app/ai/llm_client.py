# ABOUTME: LLM API client for generating condition descriptions
# ABOUTME: Supports Google Gemini 2.5 Flash-Lite with persona-based prompts

import google.generativeai as genai
import json
import re
import os
from datetime import datetime
from typing import Optional
from app.debug import debug_log
from app.ai.personas import PERSONAS


def _log_llm_response(response_text: str, mode: str, rating: int, log_type: str = "batch") -> None:
    """
    Log LLM responses to stdout for Cloud Run visibility.

    Args:
        response_text: The full LLM response
        mode: "sup" or "parawing"
        rating: The rating that was used
        log_type: "batch" for all responses, "failure" for parse failures
    """
    import sys
    timestamp = datetime.now().isoformat()
    separator = "=" * 40

    # Print to stdout so Cloud Run captures it
    print(f"\n[LLM-RAW] {separator}", flush=True)
    print(f"[LLM-RAW] Timestamp: {timestamp}", flush=True)
    print(f"[LLM-RAW] Mode: {mode} | Rating: {rating} | Type: {log_type}", flush=True)
    print(f"[LLM-RAW] Response length: {len(response_text)} chars", flush=True)
    print(f"[LLM-RAW] {separator}", flush=True)
    print(f"[LLM-RAW] {response_text}", flush=True)
    print(f"[LLM-RAW] {separator}\n", flush=True)
    sys.stdout.flush()


def _log_failed_batch_response(response_text: str, mode: str, rating: int) -> None:
    """Log failed batch parsing responses to file for debugging."""
    _log_llm_response(response_text, mode, rating, log_type="failure")


def parse_variations_response(response_text: str, mode: str = "unknown", rating: int = 0) -> dict[str, list[str]]:
    """
    Parse the mega-prompt response into a dict of persona variations.

    Expected format:
    ===PERSONA:persona_id===
    1. First response
    2. Second response
    ...

    Args:
        response_text: The LLM response to parse
        mode: The mode ("sup" or "parawing") for logging
        rating: The rating for logging

    Returns:
        {"persona_id": ["response1", "response2", ...], ...}
    """
    result: dict[str, list[str]] = {}

    # Try multiple parsing strategies

    # Strategy 1: Split on persona markers (flexible format)
    # Handles: ===PERSONA:id===, ===id===, **PERSONA:id**, etc.
    # PERSONA: prefix is optional since LLMs sometimes omit it
    # NOTE: Use {2,} to require at least 2 delimiters, avoiding conflict with
    # markdown italic (*word*) which uses single asterisks
    parts = re.split(r'[=\*#]{2,}\s*(?:PERSONA[:\s]+)?(\w+)\s*[=\*#]{2,}', response_text, flags=re.IGNORECASE)

    # parts[0] is empty or preamble, then alternating: persona_id, content, persona_id, content...
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            persona_id = parts[i].strip().lower()
            content = parts[i + 1].strip()

            # Extract numbered responses - handle various LLM formatting quirks
            lines = _extract_numbered_lines(content)

            if lines:
                result[persona_id] = lines

    # If strategy 1 failed, try looking for persona names as headers
    if not result:
        debug_log("Batch parsing strategy 1 failed, trying strategy 2", "LLM")
        # Look for persona names followed by content
        from app.ai.personas import PERSONAS
        persona_ids = [p['id'] for p in PERSONAS]

        for persona_id in persona_ids:
            # Find this persona's section
            # Include = in delimiters since LLMs often use ===ID=== format
            pattern = rf'(?:^|\n)[#\*=\s]*{re.escape(persona_id)}[#\*=:\s]*\n(.*?)(?=(?:\n[#\*=\s]*(?:{"|".join(persona_ids)})[#\*=:\s]*\n)|$)'
            match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                lines = _extract_numbered_lines(content)
                if lines:
                    result[persona_id] = lines

    if not result:
        debug_log(f"Batch parsing failed. Response preview: {response_text[:500]}", "LLM")
        # Log the full failed response to file
        _log_failed_batch_response(response_text, mode, rating)

    return result


def _extract_numbered_lines(content: str) -> list[str]:
    """Extract numbered list items from content, handling multi-line responses."""
    items = []
    current_item = None

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Check if this is a new numbered item (number is REQUIRED)
        match = re.match(r'^[\*]*\s*(\d+)[\.\)\:]\s*(.+)$', line)
        if match:
            # Save previous item if exists
            if current_item is not None:
                items.append(current_item)
            # Start new item
            current_item = match.group(2).strip()
        elif current_item is not None:
            # Continuation of previous item - append with space
            current_item += ' ' + line

    # Don't forget the last item
    if current_item is not None:
        items.append(current_item)

    # Clean up markdown and filter
    result = []
    for text in items:
        # Skip if it's just a header
        if text.lower().startswith('persona') or text.startswith('==='):
            continue
        # Remove markdown formatting
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italic
        # Skip very short responses (likely parsing errors)
        if len(text) >= 10:
            result.append(text)

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

Return a JSON object where each key is a persona ID and each value is an array of {num_variations} response strings.

Generate for these personas: {persona_ids}

PERSONA STYLES:
{persona_descriptions}
"""

        debug_log(f"Batch prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                )
            )
            debug_log(f"Batch response length: {len(response.text)} chars", "LLM")
            # Log raw response for debugging
            _log_llm_response(response.text, mode=mode, rating=rating, log_type="batch")

            # Parse JSON and lowercase keys for consistency
            data = json.loads(response.text)
            return {k.lower(): v for k, v in data.items()}
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

Return a JSON array of {num_variations} response strings.
"""

        debug_log(f"Single persona prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "array",
                        "items": {"type": "string"}
                    }
                )
            )
            debug_log(f"Single persona response length: {len(response.text)} chars", "LLM")

            return json.loads(response.text)
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

Return a JSON object where each key is a persona ID and each value is an array of {num_variations} response strings.

Generate for these personas: {persona_ids}

PERSONA STYLES:
{persona_descriptions}
"""

        debug_log(f"Offline prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema={
                        "type": "object",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                )
            )
            debug_log(f"Offline response length: {len(response.text)} chars", "LLM")

            # Parse JSON and lowercase keys for consistency
            data = json.loads(response.text)
            return {k.lower(): v for k, v in data.items()}
        except Exception as e:
            debug_log(f"Offline API error: {e}", "LLM")
            print(f"LLM offline API error: {e}")
            return {}
