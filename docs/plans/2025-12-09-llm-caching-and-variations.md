# LLM Caching & Persona Variations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix LLM quota issues by switching to Gemini 2.5 Flash-Lite, pre-generate 8-10 variations per persona in a single API call, cache everything together with 15-minute TTL, and fix weather staleness bugs.

**Architecture:** Single unified cache holds weather + ratings + all persona variations together. One LLM API call generates ~96 variations (6 personas × 8 variations × 2 modes). Cache refreshes on user request if stale (>15 min). All UI code reads from this single cache - no more independent weather fetches.

**Tech Stack:** Python 3.11+, NiceGUI, Google Generative AI SDK (`google-generativeai`), pytest

---

## Implementation Status (Updated 2025-12-10)

| Task | Status | Commit |
|------|--------|--------|
| Task 1: Switch to Gemini 2.5 Flash-Lite | ✅ DONE | `a410437`, `b9bbbb7` |
| Task 2: Create Unified Cache Structure | ✅ DONE | `9dcac5e` |
| Task 3: Add Batch Variation Generation | ✅ DONE | `4b68eb0` |
| Task 4: Unified Refresh in Orchestrator | ✅ DONE | `a242ef2` |
| Task 5: Update main.py | ✅ DONE | `a73ea39` |
| Task 6: Clean Up Old Code | ✅ DONE | `89ee4f2` |
| Task 7: Integration Testing | ✅ DONE | `e0bc753` |
| Task 8: Deploy and Verify | ✅ DONE | `733723f`, PR #8 merged |

**Final Status: ALL TASKS COMPLETE**
- 99 tests passing
- Deployed to Cloud Run via PR #8 merge
- Verified working in production (2025-12-10 ~10:10 PM EST)
- LLM persona variations displaying correctly
- Using gemini-2.5-flash-lite model (no quota issues)

---

## Background: The Problems We're Fixing

1. **LLM quota exceeded**: Free tier limit hit on `gemini-2.0-flash`. Switching to `gemini-2.5-flash-lite`.
2. **Weather staleness**: Three independent weather fetches caused mismatched data (showed 7kts when actually 22kts).
3. **No variation**: Same persona response on every page load. Now pre-generating 8-10 variations.

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/ai/llm_client.py` | LLM API calls, model configuration |
| `app/ai/personas.py` | Persona definitions (6 personas) |
| `app/cache/manager.py` | Cache storage and TTL logic |
| `app/orchestrator.py` | Coordinates weather, scoring, LLM |
| `app/main.py` | NiceGUI UI, page rendering |
| `app/config.py` | Environment variables, settings |

---

## Task 1: Switch to Gemini 2.5 Flash-Lite

**Files:**
- Modify: `app/ai/llm_client.py:14`
- Test: `tests/ai/test_llm_client.py`

### Step 1.1: Update the existing model test

The current tests mock the API. We need a test that verifies the model name.

Open `tests/ai/test_llm_client.py` and add this test:

```python
def test_uses_gemini_2_5_flash_lite_model():
    """Verify we're using the correct model"""
    with patch('app.ai.llm_client.genai') as mock_genai:
        mock_genai.GenerativeModel.return_value = MagicMock()

        client = LLMClient(api_key="test-key")

        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.5-flash-lite")
```

### Step 1.2: Run the test to verify it fails

```bash
pytest tests/ai/test_llm_client.py::test_uses_gemini_2_5_flash_lite_model -v
```

Expected: FAIL - currently using `gemini-2.0-flash`

### Step 1.3: Update the model in llm_client.py

In `app/ai/llm_client.py`, change line 14:

```python
# Before:
self.model = genai.GenerativeModel("gemini-2.0-flash")

# After:
self.model = genai.GenerativeModel("gemini-2.5-flash-lite")
```

### Step 1.4: Run the test to verify it passes

```bash
pytest tests/ai/test_llm_client.py::test_uses_gemini_2_5_flash_lite_model -v
```

Expected: PASS

### Step 1.5: Run all LLM client tests

```bash
pytest tests/ai/test_llm_client.py -v
```

Expected: All tests PASS

### Step 1.6: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "feat: switch to gemini-2.5-flash-lite model"
```

---

## Task 2: Create Unified Cache Structure

**Files:**
- Modify: `app/cache/manager.py`
- Test: `tests/cache/test_manager.py`

### Step 2.1: Read the current cache implementation

```bash
# Read these files first to understand current structure
cat app/cache/manager.py
cat tests/cache/test_manager.py
```

The current `CacheManager` stores `ConditionRating` objects with a 2-hour TTL. We need to replace this with a unified cache that stores weather + ratings + variations together.

### Step 2.2: Write failing test for unified cache structure

Add to `tests/cache/test_manager.py`:

```python
from datetime import datetime, timezone, timedelta
from app.cache.manager import CacheManager


class TestUnifiedCache:
    """Tests for the new unified cache structure"""

    def test_set_and_get_unified_cache(self):
        """Cache stores weather, ratings, and variations together"""
        manager = CacheManager(cache_ttl_minutes=15)

        cache_data = {
            "timestamp": datetime.now(timezone.utc),
            "weather": {
                "wind_speed": 15.2,
                "wind_direction": "N",
                "wave_height": 2.5,
                "swell_direction": "NE"
            },
            "ratings": {
                "sup": 7,
                "parawing": 8
            },
            "variations": {
                "sup": {
                    "drill_sergeant": ["Response 1", "Response 2"],
                    "disappointed_dad": ["Response 1", "Response 2"]
                },
                "parawing": {
                    "drill_sergeant": ["Response 1", "Response 2"],
                    "disappointed_dad": ["Response 1", "Response 2"]
                }
            }
        }

        manager.set_cache(cache_data)
        result = manager.get_cache()

        assert result is not None
        assert result["weather"]["wind_speed"] == 15.2
        assert result["ratings"]["sup"] == 7
        assert len(result["variations"]["sup"]["drill_sergeant"]) == 2

    def test_cache_returns_none_when_stale(self):
        """Cache returns None after TTL expires"""
        manager = CacheManager(cache_ttl_minutes=15)

        # Set cache with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        cache_data = {
            "timestamp": old_time,
            "weather": {"wind_speed": 10.0, "wind_direction": "S", "wave_height": 1.0, "swell_direction": "E"},
            "ratings": {"sup": 5, "parawing": 5},
            "variations": {"sup": {}, "parawing": {}}
        }

        manager.set_cache(cache_data)
        result = manager.get_cache()

        assert result is None

    def test_cache_returns_data_when_fresh(self):
        """Cache returns data within TTL"""
        manager = CacheManager(cache_ttl_minutes=15)

        # Set cache with recent timestamp
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        cache_data = {
            "timestamp": recent_time,
            "weather": {"wind_speed": 10.0, "wind_direction": "S", "wave_height": 1.0, "swell_direction": "E"},
            "ratings": {"sup": 5, "parawing": 5},
            "variations": {"sup": {}, "parawing": {}}
        }

        manager.set_cache(cache_data)
        result = manager.get_cache()

        assert result is not None
        assert result["weather"]["wind_speed"] == 10.0

    def test_is_cache_stale_when_empty(self):
        """Empty cache is considered stale"""
        manager = CacheManager(cache_ttl_minutes=15)

        assert manager.is_stale() is True

    def test_is_cache_stale_when_old(self):
        """Cache older than TTL is stale"""
        manager = CacheManager(cache_ttl_minutes=15)

        old_time = datetime.now(timezone.utc) - timedelta(minutes=20)
        cache_data = {
            "timestamp": old_time,
            "weather": {},
            "ratings": {},
            "variations": {}
        }
        manager.set_cache(cache_data)

        assert manager.is_stale() is True

    def test_is_cache_fresh_when_recent(self):
        """Cache within TTL is not stale"""
        manager = CacheManager(cache_ttl_minutes=15)

        recent_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        cache_data = {
            "timestamp": recent_time,
            "weather": {},
            "ratings": {},
            "variations": {}
        }
        manager.set_cache(cache_data)

        assert manager.is_stale() is False
```

### Step 2.3: Run tests to verify they fail

```bash
pytest tests/cache/test_manager.py::TestUnifiedCache -v
```

Expected: FAIL - methods don't exist yet

### Step 2.4: Implement the unified cache

Replace the contents of `app/cache/manager.py`:

```python
# ABOUTME: Unified cache manager for weather, ratings, and LLM variations
# ABOUTME: Single cache with configurable TTL, stores everything together

from datetime import datetime, timezone, timedelta
from typing import Any, Optional


class CacheManager:
    """
    Unified cache for weather data, ratings, and persona variations.

    Stores everything together with a single timestamp to ensure consistency.
    Default TTL is 15 minutes.
    """

    def __init__(self, cache_ttl_minutes: int = 15):
        self.cache_ttl_minutes = cache_ttl_minutes
        self._cache: Optional[dict[str, Any]] = None

    def set_cache(self, data: dict[str, Any]) -> None:
        """
        Store unified cache data.

        Expected structure:
        {
            "timestamp": datetime (UTC),
            "weather": {"wind_speed": float, "wind_direction": str, ...},
            "ratings": {"sup": int, "parawing": int},
            "variations": {"sup": {"persona_id": [str, ...]}, "parawing": {...}}
        }
        """
        self._cache = data

    def get_cache(self) -> Optional[dict[str, Any]]:
        """
        Get cached data if fresh, None if stale or empty.
        """
        if self.is_stale():
            return None
        return self._cache

    def is_stale(self) -> bool:
        """
        Check if cache is stale (empty or older than TTL).
        """
        if self._cache is None:
            return True

        timestamp = self._cache.get("timestamp")
        if timestamp is None:
            return True

        age = datetime.now(timezone.utc) - timestamp
        return age > timedelta(minutes=self.cache_ttl_minutes)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache = None
```

### Step 2.5: Run tests to verify they pass

```bash
pytest tests/cache/test_manager.py::TestUnifiedCache -v
```

Expected: All PASS

### Step 2.6: Run all cache tests

```bash
pytest tests/cache/test_manager.py -v
```

Note: Old tests for `set_rating`/`get_rating` will fail. That's expected - we're replacing the old API. Check if any other code uses these methods before removing the old tests.

### Step 2.7: Search for usages of old cache methods

```bash
grep -r "set_rating\|get_rating" app/ --include="*.py"
grep -r "set_rating\|get_rating" tests/ --include="*.py"
```

Review the output. These call sites will be updated in Task 4.

### Step 2.8: Commit

```bash
git add app/cache/manager.py tests/cache/test_manager.py
git commit -m "feat: unified cache for weather, ratings, and variations"
```

---

## Task 3: Add Batch Variation Generation to LLM Client

**Files:**
- Modify: `app/ai/llm_client.py`
- Test: `tests/ai/test_llm_client.py`

### Step 3.1: Write failing test for batch generation

Add to `tests/ai/test_llm_client.py`:

```python
class TestBatchVariationGeneration:
    """Tests for generating all persona variations in one API call"""

    def test_generate_all_variations_returns_dict_structure(self):
        """Batch generation returns variations keyed by persona"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            # Mock the API response with our expected format
            mock_response = MagicMock()
            mock_response.text = """===PERSONA:drill_sergeant===
1. First drill sergeant response for testing.
2. Second drill sergeant response here.
3. Third one with some variety.
===PERSONA:disappointed_dad===
1. First disappointed dad response.
2. Second disappointed dad here.
3. Third dad response."""

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
        client_module = __import__('app.ai.llm_client', fromlist=['parse_variations_response'])
        # We'll test the parser function directly

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
```

### Step 3.2: Run tests to verify they fail

```bash
pytest tests/ai/test_llm_client.py::TestBatchVariationGeneration -v
```

Expected: FAIL - method doesn't exist

### Step 3.3: Implement batch generation and parser

Add to `app/ai/llm_client.py` (keep existing `generate_description` method for now):

```python
# Add this import at the top
import re
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

            # Extract numbered responses
            lines = []
            for line in content.split('\n'):
                line = line.strip()
                # Match lines starting with number and period: "1. Response text"
                match = re.match(r'^\d+\.\s*(.+)$', line)
                if match:
                    lines.append(match.group(1).strip())

            if lines:
                result[persona_id] = lines

    return result


# Add this method to the LLMClient class:

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
```

### Step 3.4: Run tests to verify they pass

```bash
pytest tests/ai/test_llm_client.py::TestBatchVariationGeneration -v
```

Expected: All PASS

### Step 3.5: Run all LLM tests

```bash
pytest tests/ai/test_llm_client.py -v
```

Expected: All PASS

### Step 3.6: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "feat: batch variation generation for all personas in single API call"
```

---

## Task 4: Create Unified Refresh Entry Point in Orchestrator

**Files:**
- Modify: `app/orchestrator.py`
- Test: `tests/test_orchestrator.py`

### Step 4.1: Read current orchestrator implementation

```bash
cat app/orchestrator.py
```

Note the current methods: `get_sup_rating`, `get_parawing_rating`, `get_fresh_rating`, `get_weather_context`, `get_foil_recommendations`. We'll add a unified method that replaces the scattered refresh logic.

### Step 4.2: Write failing tests for unified cache

Add to `tests/test_orchestrator.py`:

```python
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


class TestUnifiedCache:
    """Tests for the unified caching system"""

    def test_get_cached_data_returns_fresh_cache(self):
        """Returns cached data when cache is fresh"""
        with patch('app.orchestrator.WeatherFetcher'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_cache = MagicMock()
            mock_cache.is_stale.return_value = False
            mock_cache.get_cache.return_value = {
                "timestamp": datetime.now(timezone.utc),
                "weather": {"wind_speed": 15.0, "wind_direction": "N", "wave_height": 2.0, "swell_direction": "NE"},
                "ratings": {"sup": 7, "parawing": 8},
                "variations": {"sup": {"drill_sergeant": ["test response"]}, "parawing": {}}
            }
            MockCache.return_value = mock_cache

            from app.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            orchestrator.cache = mock_cache

            result = orchestrator.get_cached_data()

            assert result["weather"]["wind_speed"] == 15.0
            assert result["ratings"]["sup"] == 7
            mock_cache.get_cache.assert_called_once()

    def test_get_cached_data_refreshes_when_stale(self):
        """Fetches fresh data when cache is stale"""
        with patch('app.orchestrator.WeatherFetcher') as MockFetcher, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache, \
             patch('app.orchestrator.ConditionCalculator') as MockCalc:

            # Setup cache as stale
            mock_cache = MagicMock()
            mock_cache.is_stale.return_value = True
            MockCache.return_value = mock_cache

            # Setup weather fetcher
            mock_weather = MagicMock()
            mock_weather.wind_speed = 20.0
            mock_weather.wind_direction = "S"
            mock_weather.wave_height = 3.0
            mock_weather.swell_direction = "SE"
            mock_fetcher = MagicMock()
            mock_fetcher.fetch_current_conditions.return_value = mock_weather
            MockFetcher.return_value = mock_fetcher

            # Setup calculator
            mock_calc = MagicMock()
            mock_calc.calculate_score.return_value = 8
            MockCalc.return_value = mock_calc

            # Setup LLM
            mock_llm = MagicMock()
            mock_llm.generate_all_variations.return_value = {
                "drill_sergeant": ["response 1", "response 2"]
            }
            MockLLM.return_value = mock_llm

            from app.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            orchestrator.cache = mock_cache
            orchestrator.weather_fetcher = mock_fetcher
            orchestrator.llm_client = mock_llm
            orchestrator.calculator = mock_calc

            result = orchestrator.get_cached_data()

            # Verify weather was fetched
            mock_fetcher.fetch_current_conditions.assert_called()
            # Verify LLM was called for both modes
            assert mock_llm.generate_all_variations.call_count == 2
            # Verify cache was updated
            mock_cache.set_cache.assert_called_once()

    def test_get_random_variation_returns_variation(self):
        """Returns a random variation for given persona and mode"""
        with patch('app.orchestrator.WeatherFetcher'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_cache = MagicMock()
            mock_cache.is_stale.return_value = False
            mock_cache.get_cache.return_value = {
                "timestamp": datetime.now(timezone.utc),
                "weather": {},
                "ratings": {"sup": 7, "parawing": 8},
                "variations": {
                    "sup": {
                        "drill_sergeant": ["response A", "response B", "response C"]
                    },
                    "parawing": {}
                }
            }
            MockCache.return_value = mock_cache

            from app.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            orchestrator.cache = mock_cache

            result = orchestrator.get_random_variation("sup", "drill_sergeant")

            assert result in ["response A", "response B", "response C"]

    def test_get_random_variation_returns_fallback_when_missing(self):
        """Returns fallback message when no variations cached"""
        with patch('app.orchestrator.WeatherFetcher'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_cache = MagicMock()
            mock_cache.is_stale.return_value = False
            mock_cache.get_cache.return_value = {
                "timestamp": datetime.now(timezone.utc),
                "weather": {"wind_speed": 10.0, "wind_direction": "N", "wave_height": 1.0, "swell_direction": "E"},
                "ratings": {"sup": 5, "parawing": 5},
                "variations": {"sup": {}, "parawing": {}}
            }
            MockCache.return_value = mock_cache

            from app.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            orchestrator.cache = mock_cache

            result = orchestrator.get_random_variation("sup", "drill_sergeant")

            assert "conditions" in result.lower() or "figure it out" in result.lower()
```

### Step 4.3: Run tests to verify they fail

```bash
pytest tests/test_orchestrator.py::TestUnifiedCache -v
```

Expected: FAIL - methods don't exist

### Step 4.4: Implement unified cache methods in orchestrator

Read the current orchestrator first, then add these methods. The key is to keep backward compatibility while adding the new unified approach.

Add to `app/orchestrator.py`:

```python
# Add these imports at the top
from datetime import datetime, timezone
import random

# Add these methods to the Orchestrator class:

    def get_cached_data(self) -> dict:
        """
        Get all data from unified cache. Refreshes if stale.

        Returns:
            {
                "timestamp": datetime,
                "weather": {...},
                "ratings": {"sup": int, "parawing": int},
                "variations": {"sup": {...}, "parawing": {...}}
            }
        """
        if self.cache.is_stale():
            self._refresh_cache()

        cached = self.cache.get_cache()
        if cached is None:
            # This shouldn't happen after refresh, but handle gracefully
            self._refresh_cache()
            cached = self.cache.get_cache()

        return cached or self._empty_cache_data()

    def _refresh_cache(self) -> None:
        """
        Fetch fresh weather, calculate ratings, generate all variations.
        Stores everything in unified cache.
        """
        from app.config import Config

        # Fetch weather ONCE
        conditions = self.weather_fetcher.fetch_current_conditions(
            Config.LOCATION_LAT,
            Config.LOCATION_LON
        )

        if conditions is None:
            debug_log("Weather fetch failed, using empty cache", "ORCHESTRATOR")
            self.cache.set_cache(self._empty_cache_data())
            return

        weather_data = {
            "wind_speed": conditions.wind_speed,
            "wind_direction": conditions.wind_direction,
            "wave_height": conditions.wave_height,
            "swell_direction": conditions.swell_direction
        }

        # Calculate ratings for both modes
        sup_score = self.calculator.calculate_score(conditions, "sup")
        parawing_score = self.calculator.calculate_score(conditions, "parawing")

        ratings = {
            "sup": sup_score,
            "parawing": parawing_score
        }

        # Generate variations for both modes
        variations = {"sup": {}, "parawing": {}}

        for mode in ["sup", "parawing"]:
            mode_variations = self.llm_client.generate_all_variations(
                wind_speed=conditions.wind_speed,
                wind_direction=conditions.wind_direction,
                wave_height=conditions.wave_height,
                swell_direction=conditions.swell_direction,
                rating=ratings[mode],
                mode=mode
            )
            variations[mode] = mode_variations

        # Store everything together
        cache_data = {
            "timestamp": datetime.now(timezone.utc),
            "weather": weather_data,
            "ratings": ratings,
            "variations": variations
        }

        self.cache.set_cache(cache_data)
        debug_log(f"Cache refreshed with {sum(len(v) for v in variations['sup'].values())} SUP variations", "ORCHESTRATOR")

    def _empty_cache_data(self) -> dict:
        """Return empty cache structure for error cases."""
        return {
            "timestamp": datetime.now(timezone.utc),
            "weather": {"wind_speed": 0, "wind_direction": "N", "wave_height": 0, "swell_direction": "N"},
            "ratings": {"sup": 0, "parawing": 0},
            "variations": {"sup": {}, "parawing": {}}
        }

    def get_random_variation(self, mode: str, persona_id: str) -> str:
        """
        Get a random variation for the given mode and persona.

        Args:
            mode: "sup" or "parawing"
            persona_id: e.g., "drill_sergeant"

        Returns:
            Random response string, or fallback if none available.
        """
        cached = self.get_cached_data()

        variations = cached.get("variations", {}).get(mode, {}).get(persona_id, [])

        if variations:
            return random.choice(variations)

        # Fallback message
        weather = cached.get("weather", {})
        rating = cached.get("ratings", {}).get(mode, 0)
        return (
            f"Conditions: {weather.get('wind_speed', 0)}kts {weather.get('wind_direction', 'N')}, "
            f"{weather.get('wave_height', 0)}ft waves. Rating: {rating}/10. Figure it out yourself."
        )
```

### Step 4.5: Update CacheManager initialization

The orchestrator needs to use the new CacheManager. Check `app/orchestrator.py` `__init__` method and update it:

```python
# In __init__, change:
# self.cache = CacheManager(refresh_hours=Config.CACHE_REFRESH_HOURS)

# To:
self.cache = CacheManager(cache_ttl_minutes=15)
```

### Step 4.6: Run tests to verify they pass

```bash
pytest tests/test_orchestrator.py::TestUnifiedCache -v
```

Expected: All PASS

### Step 4.7: Run all orchestrator tests

```bash
pytest tests/test_orchestrator.py -v
```

Note: Some old tests may fail if they depend on old cache methods. Update them as needed.

### Step 4.8: Commit

```bash
git add app/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: unified cache refresh with all variations"
```

---

## Task 5: Update main.py to Use Unified Cache

**Files:**
- Modify: `app/main.py`
- Test: Manual testing (UI changes)

### Step 5.1: Read current main.py implementation

```bash
cat app/main.py
```

Identify:
1. Where `prefetch_all()` is called
2. Where ratings are displayed
3. Where persona responses are displayed
4. Where the WHY panel gets its data

### Step 5.2: Update the data fetching

Replace the scattered fetching with unified cache calls. Find the `prefetch_all` function and similar code, then update to use `orchestrator.get_cached_data()`.

Key changes:
1. Remove separate calls to `get_fresh_rating`, `get_weather_context`, `generate_description`
2. Call `get_cached_data()` once
3. Use `get_random_variation()` for persona responses

Example pattern:

```python
# Before (scattered calls):
cached_ratings['sup'] = orchestrator.get_fresh_rating('sup')
weather = orchestrator.get_weather_context()
description = orchestrator.llm_client.generate_description(...)

# After (unified):
cached_data = orchestrator.get_cached_data()
rating = cached_data['ratings']['sup']
weather = cached_data['weather']
description = orchestrator.get_random_variation('sup', current_persona_id)
```

### Step 5.3: Update persona response display

Find where the persona description is shown and update to use random variation:

```python
# Get the current persona ID (you'll need to track this)
persona_id = current_persona['id']
mode = current_mode  # 'sup' or 'parawing'

# Get random variation
description = orchestrator.get_random_variation(mode, persona_id)
```

### Step 5.4: Test manually

```bash
# Run the app locally
python -m app.main

# Or if using uvicorn:
uvicorn app.main:app --reload
```

Test:
1. Page loads without errors
2. Rating displays correctly
3. Persona description shows (random variation)
4. Refresh page - should show different variation (sometimes same, that's fine)
5. WHY panel shows correct weather data

### Step 5.5: Commit

```bash
git add app/main.py
git commit -m "feat: UI uses unified cache with random variations"
```

---

## Task 6: Clean Up Old Code

**Files:**
- Modify: `app/orchestrator.py` (remove old methods if unused)
- Modify: `app/cache/manager.py` (remove old methods if unused)
- Modify: `tests/` (update or remove old tests)

### Step 6.1: Search for usages of old methods

```bash
grep -r "get_fresh_rating\|get_sup_rating\|get_parawing_rating" app/ --include="*.py"
grep -r "set_rating\|get_rating" app/ --include="*.py"
grep -r "generate_description" app/ --include="*.py"
```

### Step 6.2: Remove or deprecate unused methods

If methods are no longer used:
- Remove them from the class
- Remove corresponding tests
- Update any remaining callers

Keep `generate_description` if it's still used as a fallback somewhere.

### Step 6.3: Run all tests

```bash
pytest -v
```

Fix any failures.

### Step 6.4: Commit

```bash
git add -A
git commit -m "chore: remove deprecated cache and rating methods"
```

---

## Task 7: Integration Testing

**Files:**
- Test: `tests/integration/test_end_to_end.py`

### Step 7.1: Write integration test for the full flow

Add to `tests/integration/test_end_to_end.py`:

```python
class TestUnifiedCacheIntegration:
    """Integration tests for the unified caching system"""

    def test_full_refresh_cycle(self):
        """Test complete refresh: weather fetch -> rating calc -> variation generation"""
        with patch('app.weather.fetcher.requests') as mock_requests, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Mock weather API response
            mock_weather_response = MagicMock()
            mock_weather_response.json.return_value = {
                # ... valid NOAA response structure
            }
            mock_requests.get.return_value = mock_weather_response

            # Mock LLM response
            mock_llm_response = MagicMock()
            mock_llm_response.text = """===PERSONA:drill_sergeant===
1. Test response one.
2. Test response two.
===PERSONA:disappointed_dad===
1. Dad response one.
2. Dad response two."""
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            from app.orchestrator import Orchestrator
            orchestrator = Orchestrator()

            # First call should trigger refresh
            data = orchestrator.get_cached_data()

            assert data['weather'] is not None
            assert 'sup' in data['ratings']
            assert 'parawing' in data['ratings']
            assert 'drill_sergeant' in data['variations']['sup']

            # Second call should use cache (no new API calls)
            initial_call_count = mock_model.generate_content.call_count
            data2 = orchestrator.get_cached_data()
            assert mock_model.generate_content.call_count == initial_call_count
```

### Step 7.2: Run integration tests

```bash
pytest tests/integration/ -v
```

### Step 7.3: Commit

```bash
git add tests/integration/test_end_to_end.py
git commit -m "test: integration tests for unified cache"
```

---

## Task 8: Deploy and Verify

### Step 8.1: Run full test suite

```bash
pytest -v
```

All tests must pass.

### Step 8.2: Build and deploy

```bash
# Build container
docker build -t canifuckingdownwindtoday .

# Deploy to Cloud Run (adjust command for your setup)
gcloud run deploy canifuckingdownwindtoday --source .
```

### Step 8.3: Verify in production

1. Visit the live site
2. Check that rating loads
3. Check that persona description appears
4. Refresh multiple times - should see variation
5. Check GCP logs for any errors:

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=canifuckingdownwindtoday AND severity>=WARNING" --limit=20
```

### Step 8.4: Final commit

```bash
git add -A
git commit -m "chore: deployment verification complete"
git push
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `app/ai/llm_client.py` | Switch model, add batch generation |
| `app/cache/manager.py` | New unified cache structure |
| `app/orchestrator.py` | Unified refresh, random variation selection |
| `app/main.py` | Use unified cache, show random variations |
| `tests/*` | Updated tests for new behavior |

## Rollback Plan

If issues occur in production:

1. Check the specific error in logs
2. If LLM fails: The fallback message still works
3. If cache fails: Clear cache by redeploying (fresh instance)
4. If critical: Revert to previous commit and redeploy

```bash
git revert HEAD
gcloud run deploy canifuckingdownwindtoday --source .
```
