# Structured JSON Output for LLM Response Parsing

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace fragile regex-based LLM response parsing with Gemini's native structured JSON output.

**Architecture:** Use Gemini's `response_mime_type: "application/json"` with `response_schema` to constrain LLM output at generation time. This eliminates parsing failures entirely - the API guarantees valid JSON conforming to our schema. We convert all three generation methods (batch, single-persona, offline) for consistency.

**Tech Stack:** Google Generative AI SDK (`google.generativeai`), specifically `GenerationConfig` for structured output. No new dependencies.

---

## Background Context

### The Problem We're Solving

The current code asks the LLM to output text in a specific format:
```
===PERSONA:drill_sergeant===
1. First response
2. Second response
===PERSONA:disappointed_dad===
1. First response
...
```

Then it parses this with regex. This keeps breaking:
- Markdown `*italic*` was matching the `[=*#]+` regex as a persona delimiter
- Multi-line responses need special handling
- LLMs sometimes omit the `PERSONA:` prefix
- We have fallback parsing strategies because the primary one fails

### The Solution

Gemini supports **structured output** - you provide a JSON schema, and the API guarantees the response conforms to it. No parsing needed, just `json.loads()`.

### Files You'll Touch

| File | Action |
|------|--------|
| `app/ai/llm_client.py` | Modify - add structured output, delete parsing functions |
| `tests/ai/test_llm_client.py` | Modify - update tests for JSON responses, delete parsing tests |

### How to Run Tests

```bash
# Run all LLM client tests
pytest tests/ai/test_llm_client.py -v

# Run a specific test
pytest tests/ai/test_llm_client.py::TestBatchVariationGeneration::test_name -v

# Run with output visible
pytest tests/ai/test_llm_client.py -v -s
```

---

## Task 1: Add JSON Import

**Files:**
- Modify: `app/ai/llm_client.py:1-10`

**Why:** We'll need `json.loads()` to parse the structured output. Currently not imported.

**Step 1: Add the import**

Open `app/ai/llm_client.py` and add `json` to the imports at the top:

```python
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
```

**Step 2: Verify no syntax errors**

Run: `python -c "from app.ai.llm_client import LLMClient; print('OK')"`

Expected: `OK`

**Step 3: Commit**

```bash
git add app/ai/llm_client.py
git commit -m "chore: add json import to llm_client"
```

---

## Task 2: Convert generate_all_variations to Structured Output

This is the main batch generation method. We'll use TDD: write the test first, watch it fail, then implement.

**Files:**
- Modify: `tests/ai/test_llm_client.py` (update existing test)
- Modify: `app/ai/llm_client.py:212-280` (the `generate_all_variations` method)

### Step 1: Update the test to expect JSON response

The existing test mocks the LLM response as text. We need to change it to return JSON, since that's what structured output produces.

Open `tests/ai/test_llm_client.py` and find `TestBatchVariationGeneration`. Replace `test_generate_all_variations_returns_dict_structure`:

```python
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
```

Add the import at the top of the test file if not present:
```python
import json
```

### Step 2: Run the test to verify it fails

Run: `pytest tests/ai/test_llm_client.py::TestBatchVariationGeneration::test_generate_all_variations_returns_dict_structure -v`

Expected: FAIL - The current implementation tries to parse with regex, which won't work on JSON.

### Step 3: Implement structured output in generate_all_variations

Open `app/ai/llm_client.py` and replace the `generate_all_variations` method (lines ~212-280):

```python
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
```

### Step 4: Run the test to verify it passes

Run: `pytest tests/ai/test_llm_client.py::TestBatchVariationGeneration::test_generate_all_variations_returns_dict_structure -v`

Expected: PASS

### Step 5: Run all existing tests to check for regressions

Run: `pytest tests/ai/test_llm_client.py -v`

Some parsing tests will now fail - that's expected. We'll delete those in Task 5.

### Step 6: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "feat: convert generate_all_variations to structured JSON output"
```

---

## Task 3: Convert generate_single_persona_variations to Structured Output

**Files:**
- Modify: `tests/ai/test_llm_client.py` (update `TestSinglePersonaVariations`)
- Modify: `app/ai/llm_client.py:282-344` (the `generate_single_persona_variations` method)

### Step 1: Update the test to expect JSON array response

Open `tests/ai/test_llm_client.py` and find `TestSinglePersonaVariations`. Replace `test_generate_single_persona_variations_returns_list`:

```python
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
```

### Step 2: Run the test to verify it fails

Run: `pytest tests/ai/test_llm_client.py::TestSinglePersonaVariations::test_generate_single_persona_variations_returns_list -v`

Expected: FAIL

### Step 3: Implement structured output in generate_single_persona_variations

Replace the method in `app/ai/llm_client.py`:

```python
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
```

### Step 4: Run the test to verify it passes

Run: `pytest tests/ai/test_llm_client.py::TestSinglePersonaVariations::test_generate_single_persona_variations_returns_list -v`

Expected: PASS

### Step 5: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "feat: convert generate_single_persona_variations to structured JSON output"
```

---

## Task 4: Convert generate_offline_variations to Structured Output

**Files:**
- Modify: `tests/ai/test_llm_client.py` (update `TestOfflineVariations`)
- Modify: `app/ai/llm_client.py:346-395` (the `generate_offline_variations` method)

### Step 1: Update the test to expect JSON response

Open `tests/ai/test_llm_client.py` and find `TestOfflineVariations`. Replace `test_generate_offline_variations_returns_dict`:

```python
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
```

### Step 2: Run the test to verify it fails

Run: `pytest tests/ai/test_llm_client.py::TestOfflineVariations::test_generate_offline_variations_returns_dict -v`

Expected: FAIL

### Step 3: Implement structured output in generate_offline_variations

Replace the method in `app/ai/llm_client.py`:

```python
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
```

### Step 4: Run the test to verify it passes

Run: `pytest tests/ai/test_llm_client.py::TestOfflineVariations::test_generate_offline_variations_returns_dict -v`

Expected: PASS

### Step 5: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "feat: convert generate_offline_variations to structured JSON output"
```

---

## Task 5: Delete Old Parsing Code and Tests

Now we remove the dead code. This is the satisfying part.

**Files:**
- Modify: `app/ai/llm_client.py` (delete `parse_variations_response` and `_extract_numbered_lines`)
- Modify: `tests/ai/test_llm_client.py` (delete parsing tests)

### Step 1: Delete parsing functions from llm_client.py

Open `app/ai/llm_client.py` and delete these two functions entirely:

1. `parse_variations_response` (lines ~43-107) - the function with all the regex parsing
2. `_extract_numbered_lines` (lines ~110-149) - the numbered list extractor

Also remove the now-unused `re` import from the top of the file (line 5).

The imports section should now look like:
```python
# ABOUTME: LLM API client for generating condition descriptions
# ABOUTME: Supports Google Gemini 2.5 Flash-Lite with persona-based prompts

import google.generativeai as genai
import json
import os
from datetime import datetime
from typing import Optional
from app.debug import debug_log
from app.ai.personas import PERSONAS
```

### Step 2: Delete parsing tests from test file

Open `tests/ai/test_llm_client.py` and delete these test methods from `TestBatchVariationGeneration`:

1. `test_parse_variations_response_extracts_all_personas`
2. `test_parse_variations_handles_format_without_persona_prefix`
3. `test_parse_variations_handles_multiline_responses`
4. `test_parse_variations_preserves_markdown_italic_in_text`

Also delete this test from `TestSinglePersonaVariations`:
1. `test_generate_single_persona_variations_handles_multiline`

These tests were testing the regex parsing logic that no longer exists.

### Step 3: Run all tests to verify nothing is broken

Run: `pytest tests/ai/test_llm_client.py -v`

Expected: All remaining tests PASS

### Step 4: Verify no references to deleted functions

Run: `python -c "from app.ai.llm_client import LLMClient; print('OK')"`

Expected: `OK`

If you get an import error about `parse_variations_response`, check that nothing else imports it. (The orchestrator doesn't - it only uses the `LLMClient` class methods.)

### Step 5: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "refactor: delete regex parsing code replaced by structured output"
```

---

## Task 6: Add JSON Parse Error Test

Even though structured output guarantees valid JSON, we should test that the error handling works if something unexpected happens.

**Files:**
- Modify: `tests/ai/test_llm_client.py`

### Step 1: Add test for JSON parse failure

Add this test to `TestBatchVariationGeneration`:

```python
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
```

### Step 2: Run the test

Run: `pytest tests/ai/test_llm_client.py::TestBatchVariationGeneration::test_generate_all_variations_handles_invalid_json -v`

Expected: PASS (the `except Exception` block catches `json.JSONDecodeError`)

### Step 3: Commit

```bash
git add tests/ai/test_llm_client.py
git commit -m "test: add JSON parse error handling test"
```

---

## Task 7: Run Full Test Suite and Final Verification

### Step 1: Run all LLM client tests

Run: `pytest tests/ai/test_llm_client.py -v`

Expected: All tests PASS

### Step 2: Run the full project test suite

Run: `pytest -v`

Expected: All tests PASS

### Step 3: Verify the implementation manually (optional)

If you have API access and want to test against real Gemini:

```python
# Quick manual test (run in Python REPL)
import os
from app.ai.llm_client import LLMClient

client = LLMClient(api_key=os.environ["GEMINI_API_KEY"])
result = client.generate_single_persona_variations(
    wind_speed=15.0,
    wind_direction="S",
    wave_height=0,
    swell_direction="N",
    rating=7,
    mode="sup",
    persona_id="drill_sergeant",
    num_variations=2
)
print(result)
# Should print a list of 2 strings
```

### Step 4: Final commit with all changes

If you made any fixups:
```bash
git add -A
git commit -m "chore: final cleanup for structured JSON output"
```

---

## Summary: What Changed

| Before | After |
|--------|-------|
| 85 lines of regex parsing code | 0 lines (deleted) |
| Fragile text format with fallback strategies | Guaranteed JSON via API schema |
| Parsing tests for edge cases | Simple structure tests |
| `parse_variations_response()` | `json.loads()` |
| `_extract_numbered_lines()` | (deleted) |

**Files modified:**
- `app/ai/llm_client.py` - Structured output in 3 methods, deleted 2 functions
- `tests/ai/test_llm_client.py` - Updated mocks to return JSON, deleted parsing tests

**Net lines of code:** Approximately -80 lines
