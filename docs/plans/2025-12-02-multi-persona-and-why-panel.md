# Multi-Persona, WHY Panel, and UX Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add rotating aggressive personas, a WHY panel showing scoring context and live cams, debug mode, expanded KT foil recommendations, fresh snark on refresh, and EST timestamps.

**Architecture:** Personas are defined as prompt templates in a new module, randomly selected (no repeats) via localStorage. The WHY panel is a NiceGUI dialog overlay containing weather data and embedded video streams. Foil recommendations become condition-matched based on score ranges. Fresh snark is achieved by generating both modes on page load (not from cache).

**Tech Stack:** Python 3.10+, NiceGUI 2.0+, Google Gemini 2.0 Flash, pytest

---

## Progress

| Task | Description | Status |
|------|-------------|--------|
| 1 | Debug Mode Infrastructure | ✅ COMPLETE |
| 2 | Add Multiple Personas | ✅ COMPLETE |
| 3 | Integrate Personas into Orchestrator | ✅ COMPLETE |
| 4 | Add Fresh Snark on Page Refresh | ✅ COMPLETE |
| 5 | Add EST Timestamp | ✅ COMPLETE |
| 6 | Expand KT Foil Recommendations | ✅ COMPLETE |
| 7 | Add WHY Panel with Conditions Context | ✅ COMPLETE |
| 8 | Track Last Persona in Frontend | ✅ COMPLETE |
| 9 | Final Integration Testing | ✅ COMPLETE |

**Last Updated:** 2025-12-02

---

## Codebase Overview (Read This First)

### Project Structure
```
app/
├── main.py              # NiceGUI web UI - where the 90s-style frontend lives
├── config.py            # Environment config (GEMINI_API_KEY, location coords)
├── orchestrator.py      # Coordinates weather→scoring→LLM→cache flow
├── ai/
│   └── llm_client.py    # Gemini API client - generates snarky descriptions
├── weather/
│   ├── fetcher.py       # Fetches from NOAA
│   ├── sources.py       # NOAA API parsing
│   └── models.py        # WeatherConditions dataclass
├── scoring/
│   ├── calculator.py    # SUP/parawing scoring (1-10)
│   ├── foil_recommender.py  # CODE/KT equipment suggestions
│   └── models.py        # ConditionRating dataclass
└── cache/
    └── manager.py       # Time-based cache (2hr TTL)

tests/                   # Mirrors app/ structure exactly
```

### Key Data Flow
1. User visits page → `main.py:index()` runs
2. `orchestrator.get_sup_rating()` called → checks cache
3. If cache miss: `weather_fetcher` → `score_calculator` → `llm_client` → cache result
4. UI displays rating, description, foil recommendations

### Testing Patterns
- Tests live in `tests/` mirroring `app/` structure
- Use `WeatherConditions` dataclass for test fixtures
- Mock Gemini API with `unittest.mock.patch`
- Run tests: `pytest tests/ -v`

### Environment Variables
- `GEMINI_API_KEY` - Required for LLM
- `DEBUG` - New (we're adding this)
- `PORT` - Cloud Run port (default 8080)

---

## Task 1: Add Debug Mode Infrastructure ✅ COMPLETE

**Goal:** Enable verbose logging when `DEBUG=true` environment variable is set.

**Files:**
- Modify: `app/config.py`
- Create: `app/debug.py`
- Test: `tests/test_debug.py`

### Step 1.1: Write failing test for debug config

Create `tests/test_debug.py`:

```python
# ABOUTME: Tests for debug mode configuration
# ABOUTME: Validates DEBUG env var enables verbose logging

import os
from unittest.mock import patch


def test_debug_mode_disabled_by_default():
    """Debug mode should be disabled when env var not set"""
    with patch.dict(os.environ, {}, clear=True):
        # Force reimport to pick up env change
        from importlib import reload
        from app import config
        reload(config)
        assert config.Config.DEBUG is False


def test_debug_mode_enabled_when_env_true():
    """Debug mode should be enabled when DEBUG=true"""
    with patch.dict(os.environ, {"DEBUG": "true"}):
        from importlib import reload
        from app import config
        reload(config)
        assert config.Config.DEBUG is True


def test_debug_mode_enabled_case_insensitive():
    """DEBUG=TRUE (uppercase) should also work"""
    with patch.dict(os.environ, {"DEBUG": "TRUE"}):
        from importlib import reload
        from app import config
        reload(config)
        assert config.Config.DEBUG is True
```

### Step 1.2: Run test to verify it fails

```bash
pytest tests/test_debug.py -v
```

Expected: FAIL with `AttributeError: type object 'Config' has no attribute 'DEBUG'`

### Step 1.3: Add DEBUG to Config

Modify `app/config.py`, add after line 34 (after CACHE_REFRESH_HOURS):

```python
    # Debug mode
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

### Step 1.4: Run test to verify it passes

```bash
pytest tests/test_debug.py -v
```

Expected: PASS

### Step 1.5: Write failing test for debug logger

Add to `tests/test_debug.py`:

```python
def test_debug_log_outputs_when_enabled():
    """debug_log should print when DEBUG=true"""
    with patch.dict(os.environ, {"DEBUG": "true"}):
        from importlib import reload
        from app import config
        reload(config)
        from app.debug import debug_log
        import io
        import sys

        captured = io.StringIO()
        sys.stdout = captured
        debug_log("test message")
        sys.stdout = sys.__stdout__

        assert "test message" in captured.getvalue()


def test_debug_log_silent_when_disabled():
    """debug_log should be silent when DEBUG=false"""
    with patch.dict(os.environ, {"DEBUG": "false"}):
        from importlib import reload
        from app import config
        reload(config)
        from app import debug
        reload(debug)
        import io
        import sys

        captured = io.StringIO()
        sys.stdout = captured
        debug.debug_log("test message")
        sys.stdout = sys.__stdout__

        assert captured.getvalue() == ""
```

### Step 1.6: Run test to verify it fails

```bash
pytest tests/test_debug.py::test_debug_log_outputs_when_enabled -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.debug'`

### Step 1.7: Create debug module

Create `app/debug.py`:

```python
# ABOUTME: Debug logging utilities
# ABOUTME: Provides conditional logging when DEBUG=true

from app.config import Config


def debug_log(message: str, category: str = "DEBUG") -> None:
    """
    Print debug message if DEBUG mode is enabled.

    Args:
        message: The message to log
        category: Category prefix (e.g., "CACHE", "LLM", "WEATHER")
    """
    if Config.DEBUG:
        print(f"[{category}] {message}")
```

### Step 1.8: Run all debug tests

```bash
pytest tests/test_debug.py -v
```

Expected: PASS (all tests)

### Step 1.9: Commit

```bash
git add app/config.py app/debug.py tests/test_debug.py
git commit -m "feat: add debug mode infrastructure with DEBUG env var"
```

---

## Task 2: Add Multiple Personas ✅ COMPLETE

**Goal:** Create 5-6 aggressive persona voices that rotate randomly (no repeats).

**Files:**
- Create: `app/ai/personas.py`
- Modify: `app/ai/llm_client.py`
- Test: `tests/ai/test_personas.py`

### Step 2.1: Write failing test for persona definitions

Create `tests/ai/test_personas.py`:

```python
# ABOUTME: Tests for persona rotation system
# ABOUTME: Validates persona definitions and random selection

from app.ai.personas import PERSONAS, get_random_persona


def test_personas_exist():
    """Should have 5-6 persona definitions"""
    assert len(PERSONAS) >= 5
    assert len(PERSONAS) <= 6


def test_each_persona_has_required_fields():
    """Each persona needs id, name, and prompt_style"""
    for persona in PERSONAS:
        assert "id" in persona
        assert "name" in persona
        assert "prompt_style" in persona
        assert len(persona["prompt_style"]) > 50  # Substantial prompt


def test_persona_ids_are_unique():
    """Persona IDs must be unique for tracking"""
    ids = [p["id"] for p in PERSONAS]
    assert len(ids) == len(set(ids))
```

### Step 2.2: Run test to verify it fails

```bash
pytest tests/ai/test_personas.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.ai.personas'`

### Step 2.3: Create personas module with definitions

Create `app/ai/personas.py`:

```python
# ABOUTME: Persona definitions for snarky condition descriptions
# ABOUTME: Provides rotating aggressive voices for variety

import random
from typing import Optional

PERSONAS = [
    {
        "id": "drill_sergeant",
        "name": "Sergeant Stoke",
        "prompt_style": """You are a drill sergeant who's disgusted that civilians are trying to foil.
Bark at them like recruits who showed up to PT hungover. Question their commitment, their gear choices,
their life decisions. Use military metaphors. Call them 'maggot' or 'recruit'. Be disappointed in them."""
    },
    {
        "id": "disappointed_dad",
        "name": "Disappointed Dad",
        "prompt_style": """You are a disappointed father who's seen his kid fail at everything.
Sigh heavily through your words. Say things like 'I'm not mad, I'm just disappointed.'
Compare them unfavorably to their siblings or neighbors. Wonder aloud where you went wrong raising them."""
    },
    {
        "id": "sarcastic_weatherman",
        "name": "Chad Storm",
        "prompt_style": """You are an obnoxiously sarcastic TV weatherman who thinks foilers are idiots.
Use weather puns aggressively. Act like you're doing them a huge favor by even acknowledging their hobby.
Throw in fake enthusiasm that's clearly mocking them. Sign off with a condescending catchphrase."""
    },
    {
        "id": "jaded_local",
        "name": "Local Larry",
        "prompt_style": """You are a jaded Jupiter local who's been foiling since before it was cool.
You've seen a thousand kooks come and go. Nothing impresses you. Everything was better 'back in the day.'
Gatekeep aggressively. Imply they don't deserve these conditions. Complain about crowds."""
    },
    {
        "id": "angry_coach",
        "name": "Coach Pain",
        "prompt_style": """You are an unhinged sports coach who takes foiling way too seriously.
Scream about fundamentals. Threaten to make them do drills. Question their dedication to the sport.
Act like missing a session is a personal betrayal. Assign them punishment paddles."""
    },
    {
        "id": "passive_aggressive_ex",
        "name": "Your Ex",
        "prompt_style": """You are their passive-aggressive ex who's 'totally fine' and 'not even mad.'
Make backhanded compliments. Bring up past failures. Say 'I just think it's funny how...'
Be supportive in a way that's clearly not supportive. Hope they have fun (they won't)."""
    }
]


def get_random_persona(exclude_id: Optional[str] = None) -> dict:
    """
    Get a random persona, optionally excluding one (to avoid repeats).

    Args:
        exclude_id: Persona ID to exclude from selection

    Returns:
        Persona dict with id, name, and prompt_style
    """
    available = PERSONAS if exclude_id is None else [p for p in PERSONAS if p["id"] != exclude_id]
    return random.choice(available)
```

### Step 2.4: Run test to verify it passes

```bash
pytest tests/ai/test_personas.py -v
```

Expected: PASS

### Step 2.5: Write failing test for persona selection with exclusion

Add to `tests/ai/test_personas.py`:

```python
def test_get_random_persona_returns_persona():
    """get_random_persona should return a valid persona"""
    persona = get_random_persona()
    assert persona in PERSONAS


def test_get_random_persona_excludes_specified():
    """get_random_persona should not return excluded persona"""
    # Run multiple times to be confident
    for _ in range(20):
        persona = get_random_persona(exclude_id="drill_sergeant")
        assert persona["id"] != "drill_sergeant"


def test_get_random_persona_with_none_exclude():
    """get_random_persona with None exclude should work"""
    persona = get_random_persona(exclude_id=None)
    assert persona in PERSONAS
```

### Step 2.6: Run tests

```bash
pytest tests/ai/test_personas.py -v
```

Expected: PASS (all tests)

### Step 2.7: Write failing test for LLM client persona integration

Add to `tests/ai/test_llm_client.py` (at the end):

```python
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
```

### Step 2.8: Run test to verify it fails

```bash
pytest tests/ai/test_llm_client.py::test_llm_client_accepts_persona -v
```

Expected: FAIL with `TypeError: generate_description() got an unexpected keyword argument 'persona'`

### Step 2.9: Modify LLMClient to accept persona

Replace `app/ai/llm_client.py` content:

```python
# ABOUTME: LLM API client for generating condition descriptions
# ABOUTME: Supports Google Gemini 2.0 Flash with persona-based prompts

import google.generativeai as genai
from typing import Optional
from app.debug import debug_log


class LLMClient:
    """Client for generating snarky descriptions via LLM API"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

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
```

### Step 2.10: Run test to verify it passes

```bash
pytest tests/ai/test_llm_client.py -v
```

Expected: PASS (all tests)

### Step 2.11: Commit

```bash
git add app/ai/personas.py app/ai/llm_client.py tests/ai/test_personas.py tests/ai/test_llm_client.py
git commit -m "feat: add persona system with 6 aggressive voices"
```

---

## Task 3: Integrate Personas into Orchestrator ✅ COMPLETE

**Goal:** Pass random persona (excluding last used) to LLM client.

**Files:**
- Modify: `app/orchestrator.py`
- Test: `tests/test_orchestrator.py`

### Step 3.1: Write failing test for persona in orchestrator

Add to `tests/test_orchestrator.py`:

```python
def test_orchestrator_uses_persona(mock_weather, mock_llm):
    """Orchestrator should pass persona to LLM client"""
    from unittest.mock import patch, Mock

    # Mock weather
    mock_conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    with patch.object(WeatherFetcher, 'fetch_current_conditions', return_value=mock_conditions):
        with patch.object(LLMClient, 'generate_description', return_value="Snarky response") as mock_gen:
            orchestrator = AppOrchestrator(api_key="test_key")
            orchestrator.cache.clear()  # Ensure no cache hit

            rating = orchestrator.get_sup_rating()

            # Verify persona was passed
            call_kwargs = mock_gen.call_args[1]
            assert 'persona' in call_kwargs
            assert call_kwargs['persona'] is not None
            assert 'id' in call_kwargs['persona']
```

Note: This test may need adjustment based on existing test structure. First, let's check the existing test file.

### Step 3.2: Read existing orchestrator tests

Read `tests/test_orchestrator.py` to understand current test patterns before adding.

### Step 3.3: Update orchestrator to use personas

Modify `app/orchestrator.py`. Add import at top:

```python
from app.ai.personas import get_random_persona
```

Then modify `_generate_rating` method to use persona. Replace line 93-101 (the try block for description) with:

```python
            # Get random persona
            persona = get_random_persona()

            # Generate snarky description with persona
            try:
                description = self.llm_client.generate_description(
                    wind_speed=conditions.wind_speed_kts,
                    wind_direction=conditions.wind_direction,
                    wave_height=conditions.wave_height_ft,
                    swell_direction=conditions.swell_direction,
                    rating=score,
                    mode=mode,
                    persona=persona
                )
            except Exception as e:
                print(f"LLM generation failed: {e}")
                description = self._create_fallback_description(conditions, score, mode)
```

### Step 3.4: Run existing tests to verify no regression

```bash
pytest tests/test_orchestrator.py -v
```

Expected: PASS (all existing tests)

### Step 3.5: Commit

```bash
git add app/orchestrator.py
git commit -m "feat: integrate persona system into orchestrator"
```

---

## Task 4: Add Fresh Snark on Page Refresh ✅ COMPLETE

**Goal:** Generate both SUP and parawing descriptions on every page load (not from cache), but cache them for toggling within the session.

**Files:**
- Modify: `app/orchestrator.py`
- Modify: `app/main.py`

### Step 4.1: Write failing test for force-refresh method

Add to `tests/test_orchestrator.py`:

```python
def test_orchestrator_get_fresh_rating_bypasses_cache():
    """get_fresh_rating should bypass cache and generate new"""
    from unittest.mock import patch, Mock

    mock_conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    with patch.object(WeatherFetcher, 'fetch_current_conditions', return_value=mock_conditions):
        with patch.object(LLMClient, 'generate_description', return_value="Fresh snark") as mock_gen:
            orchestrator = AppOrchestrator(api_key="test_key")

            # First call with normal method (caches it)
            orchestrator.get_sup_rating()
            first_call_count = mock_gen.call_count

            # Second call with get_fresh should still call LLM
            orchestrator.get_fresh_rating("sup")

            assert mock_gen.call_count > first_call_count
```

### Step 4.2: Run test to verify it fails

```bash
pytest tests/test_orchestrator.py::test_orchestrator_get_fresh_rating_bypasses_cache -v
```

Expected: FAIL with `AttributeError: 'AppOrchestrator' object has no attribute 'get_fresh_rating'`

### Step 4.3: Add get_fresh_rating method to orchestrator

Add to `app/orchestrator.py` after `get_parawing_rating` method:

```python
    def get_fresh_rating(self, mode: str) -> Optional[ConditionRating]:
        """
        Get fresh rating, bypassing cache. Used for page refresh.

        Args:
            mode: "sup" or "parawing"

        Returns:
            ConditionRating or None if weather unavailable
        """
        return self._generate_rating(mode)
```

### Step 4.4: Run test to verify it passes

```bash
pytest tests/test_orchestrator.py::test_orchestrator_get_fresh_rating_bypasses_cache -v
```

Expected: PASS

### Step 4.5: Update main.py to use fresh ratings on load

Modify `app/main.py`. Replace the `prefetch_all` function (lines 121-129) with:

```python
        def prefetch_all():
            """Fetch FRESH ratings on page load for both modes"""
            nonlocal cached_recommendations
            try:
                # Always generate fresh ratings on page load
                cached_ratings['sup'] = orchestrator.get_fresh_rating('sup')
                cached_ratings['parawing'] = orchestrator.get_fresh_rating('parawing')
                cached_recommendations = orchestrator.get_foil_recommendations()
            except Exception as e:
                print(f"Prefetch error: {e}")
```

### Step 4.6: Run full test suite

```bash
pytest tests/ -v
```

Expected: PASS (all tests)

### Step 4.7: Commit

```bash
git add app/orchestrator.py app/main.py
git commit -m "feat: generate fresh snarky descriptions on every page load"
```

---

## Task 5: Add EST Timestamp

**Goal:** Display "Last updated" in Eastern Standard Time (Florida).

**Files:**
- Modify: `app/main.py`

### Step 5.1: Update timestamp to EST

In `app/main.py`, modify the timestamp section in `update_display()`. Replace line 150-151:

```python
                from datetime import datetime
                timestamp_label.content = f'<div class="timestamp">Last updated: {datetime.now().strftime("%I:%M %p")}</div>'
```

With:

```python
                from datetime import datetime
                from zoneinfo import ZoneInfo

                est_time = datetime.now(ZoneInfo("America/New_York"))
                timestamp_label.content = f'<div class="timestamp">Last updated: {est_time.strftime("%I:%M %p")} EST</div>'
```

### Step 5.2: Test manually

```bash
python -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/New_York')).strftime('%I:%M %p EST'))"
```

Expected: Current time in EST format like "02:30 PM EST"

### Step 5.3: Commit

```bash
git add app/main.py
git commit -m "fix: display timestamp in EST (Florida timezone)"
```

---

## Task 6: Expand KT Foil Recommendations

**Goal:** Replace simple recommendations with condition-matched CODE/KT equivalents based on score.

**Files:**
- Modify: `app/scoring/foil_recommender.py`
- Modify: `tests/scoring/test_foil_recommender.py`

### Step 6.1: Write failing tests for new recommendation tiers

Replace `tests/scoring/test_foil_recommender.py` content:

```python
# ABOUTME: Tests for foil setup recommendation logic
# ABOUTME: Validates CODE and KT foil recommendations based on conditions and score

from app.scoring.foil_recommender import FoilRecommender
from app.weather.models import WeatherConditions


def make_conditions(wind: float, waves: float) -> WeatherConditions:
    """Helper to create test conditions"""
    return WeatherConditions(
        wind_speed_kts=wind,
        wind_direction="S",
        wave_height_ft=waves,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )


# --- CODE Foil Tests ---

def test_code_light_conditions():
    """Light wind (score 1-4) should recommend 1250R"""
    recommender = FoilRecommender()
    result = recommender.recommend_code(score=3)

    assert "1250R" in result
    assert "135R stab" in result.lower() or "135r stab" in result.lower()


def test_code_good_conditions():
    """Good wind (score 5-7) should recommend 960R"""
    recommender = FoilRecommender()
    result = recommender.recommend_code(score=6)

    assert "960R" in result
    assert "135R stab" in result.lower() or "135r stab" in result.lower()


def test_code_great_conditions():
    """Great conditions (score 8-10) should recommend 770R"""
    recommender = FoilRecommender()
    result = recommender.recommend_code(score=9)

    assert "770R" in result


# --- KT Atlas Tests ---

def test_kt_light_conditions():
    """Light wind (score 1-4) should recommend Atlas 1130"""
    recommender = FoilRecommender()
    result = recommender.recommend_kt(score=3)

    assert "Atlas 1130" in result
    assert "145" in result  # Paka'a stabilizer


def test_kt_good_conditions():
    """Good wind (score 5-7) should recommend Atlas 790 or 960"""
    recommender = FoilRecommender()
    result = recommender.recommend_kt(score=6)

    assert "Atlas 790" in result or "Atlas 960" in result
    assert "145" in result  # Paka'a stabilizer


def test_kt_great_conditions():
    """Great conditions (score 8-10) should recommend Atlas 680"""
    recommender = FoilRecommender()
    result = recommender.recommend_kt(score=9)

    assert "Atlas 680" in result
    assert "170" in result  # Larger stabilizer for big days


# --- Integration with conditions (backwards compat) ---

def test_recommend_code_accepts_conditions():
    """Should still work when passed conditions (for backwards compat)"""
    recommender = FoilRecommender()
    conditions = make_conditions(wind=10.0, waves=1.5)

    # When passed conditions, should calculate score internally
    result = recommender.recommend_code(conditions=conditions)
    assert result is not None
    assert len(result) > 0


def test_recommend_kt_accepts_conditions():
    """Should still work when passed conditions (for backwards compat)"""
    recommender = FoilRecommender()
    conditions = make_conditions(wind=18.0, waves=3.0)

    result = recommender.recommend_kt(conditions=conditions)
    assert result is not None
    assert len(result) > 0
```

### Step 6.2: Run tests to verify they fail

```bash
pytest tests/scoring/test_foil_recommender.py -v
```

Expected: FAIL (signature changed, new assertions)

### Step 6.3: Rewrite foil_recommender.py

Replace `app/scoring/foil_recommender.py` content:

```python
# ABOUTME: Foil setup recommendations based on conditions and score
# ABOUTME: Provides CODE and KT Atlas equipment suggestions matched to condition tiers

from typing import Optional
from app.weather.models import WeatherConditions


class FoilRecommender:
    """
    Recommends foil setups based on conditions.

    Score tiers:
    - 1-4: Light/marginal conditions
    - 5-7: Good/decent conditions
    - 8-10: Great conditions / big swell

    Note: Recommendations calibrated for 195lb/88kg rider.
    """

    # CODE Foil recommendations by tier
    CODE_SETUPS = {
        "light": "1250R + 135R stab + short fuse",
        "good": "960R + 135R stab + short fuse",
        "great": "770R + 135R stab + short fuse"
    }

    # KT Atlas equivalents (sized down 10-20% per KT recommendation)
    KT_SETUPS = {
        "light": "Atlas 1130 + 145 Paka'a + 56cm fuse",
        "good": "Atlas 790 or 960 + 145 Paka'a + 56cm fuse",
        "great": "Atlas 680 + 170 Paka'a + 56cm fuse"
    }

    def _score_to_tier(self, score: int) -> str:
        """Convert 1-10 score to condition tier"""
        if score <= 4:
            return "light"
        elif score <= 7:
            return "good"
        else:
            return "great"

    def _conditions_to_score(self, conditions: WeatherConditions) -> int:
        """Estimate score from conditions for backwards compatibility"""
        # Simple heuristic matching old behavior
        if conditions.wind_speed_kts < 15 and conditions.wave_height_ft < 2.5:
            return 3  # Light
        elif conditions.wind_speed_kts >= 20 and conditions.wave_height_ft >= 3:
            return 8  # Great
        else:
            return 6  # Good

    def recommend_code(
        self,
        score: Optional[int] = None,
        conditions: Optional[WeatherConditions] = None
    ) -> str:
        """
        Recommend CODE foil setup based on score or conditions.

        Args:
            score: 1-10 rating (preferred)
            conditions: WeatherConditions (for backwards compat)

        Returns:
            Setup string (e.g., "960R + 135R stab + short fuse")
        """
        if score is None and conditions is not None:
            score = self._conditions_to_score(conditions)
        elif score is None:
            raise ValueError("Must provide either score or conditions")

        tier = self._score_to_tier(score)
        return self.CODE_SETUPS[tier]

    def recommend_kt(
        self,
        score: Optional[int] = None,
        conditions: Optional[WeatherConditions] = None
    ) -> str:
        """
        Recommend KT Atlas setup based on score or conditions.

        Args:
            score: 1-10 rating (preferred)
            conditions: WeatherConditions (for backwards compat)

        Returns:
            Setup string (e.g., "Atlas 790 or 960 + 145 Paka'a + 56cm fuse")
        """
        if score is None and conditions is not None:
            score = self._conditions_to_score(conditions)
        elif score is None:
            raise ValueError("Must provide either score or conditions")

        tier = self._score_to_tier(score)
        return self.KT_SETUPS[tier]
```

### Step 6.4: Run tests to verify they pass

```bash
pytest tests/scoring/test_foil_recommender.py -v
```

Expected: PASS

### Step 6.5: Update orchestrator to pass score to recommender

Modify `app/orchestrator.py`. Replace `get_foil_recommendations` method:

```python
    def get_foil_recommendations(self, score: Optional[int] = None) -> dict:
        """
        Get foil recommendations for current conditions.

        Args:
            score: Optional score to use (if not provided, fetches weather)

        Returns:
            Dict with CODE and KT recommendations
        """
        if score is None:
            # Fetch conditions to calculate score
            conditions = self.weather_fetcher.fetch_current_conditions(
                Config.LOCATION_LAT,
                Config.LOCATION_LON
            )

            if not conditions:
                return {"code": "Weather unavailable", "kt": "Weather unavailable"}

            score = self.score_calculator.calculate_sup_score(conditions)

        return {
            "code": self.foil_recommender.recommend_code(score=score),
            "kt": self.foil_recommender.recommend_kt(score=score)
        }
```

Add `Optional` import at top of file if not already there:

```python
from typing import Optional
```

### Step 6.6: Run all tests

```bash
pytest tests/ -v
```

Expected: PASS

### Step 6.7: Commit

```bash
git add app/scoring/foil_recommender.py app/orchestrator.py tests/scoring/test_foil_recommender.py
git commit -m "feat: expand KT foil recommendations with CODE equivalents by condition tier"
```

---

## Task 7: Add WHY Panel with Conditions Context

**Goal:** Add clickable "WHY" text that opens overlay showing weather data.

**Files:**
- Modify: `app/main.py`
- Modify: `app/orchestrator.py`

### Step 7.1: Add method to get weather context for display

Add to `app/orchestrator.py`:

```python
    def get_weather_context(self) -> Optional[dict]:
        """
        Get current weather conditions formatted for display.

        Returns:
            Dict with wind_speed, wind_direction, wave_height, swell_direction, timestamp
            or None if weather unavailable
        """
        conditions = self.weather_fetcher.fetch_current_conditions(
            Config.LOCATION_LAT,
            Config.LOCATION_LON
        )

        if not conditions:
            return None

        return {
            "wind_speed": f"{conditions.wind_speed_kts:.1f} kts",
            "wind_direction": conditions.wind_direction,
            "wave_height": f"{conditions.wave_height_ft:.1f} ft",
            "swell_direction": conditions.swell_direction,
            "timestamp": conditions.timestamp
        }
```

### Step 7.2: Add WHY button and dialog to main.py

This is a larger change to `app/main.py`. Add after the title (around line 95), before the toggle:

```python
        # WHY button in top-right corner
        with ui.element('div').style('position: absolute; top: 20px; right: 20px;'):
            why_button = ui.label('WHY').style(
                'font-size: 14px; cursor: pointer; text-decoration: underline;'
            )

        # WHY dialog/overlay
        with ui.dialog() as why_dialog, ui.card().style('width: 90vw; max-width: 600px; max-height: 90vh; overflow-y: auto;'):
            ui.label('WHY THIS SCORE?').style('font-size: 24px; font-weight: bold; margin-bottom: 16px;')

            # Weather conditions section
            conditions_container = ui.column().style('width: 100%; margin-bottom: 24px;')

            ui.label('--- LIVE CAMS ---').style('font-size: 18px; font-weight: bold; margin: 16px 0;')

            # Video streams section
            with ui.column().style('width: 100%; gap: 16px;'):
                # Palm Beach Marriott cam
                ui.label('Palm Beach Marriott').style('font-size: 14px; font-weight: bold;')
                ui.html('''
                    <iframe src="https://video-monitoring.com/beachcams/palmbeachmarriott/stream.htm"
                            style="width: 100%; height: 200px; border: 1px solid #000;"
                            allow="autoplay" allowfullscreen></iframe>
                ''')

                # Jupiter Inlet cam (YouTube)
                ui.label('Jupiter Inlet').style('font-size: 14px; font-weight: bold;')
                ui.html('''
                    <iframe src="https://www.youtube.com/embed/4y7kDbwBuh0?autoplay=1&mute=1"
                            style="width: 100%; height: 200px; border: 1px solid #000;"
                            allow="autoplay; encrypted-media" allowfullscreen></iframe>
                ''')

                # Juno Beach cam (YouTube)
                ui.label('Juno Beach').style('font-size: 14px; font-weight: bold;')
                ui.html('''
                    <iframe src="https://www.youtube.com/embed/1FYgBpkM7SA?autoplay=1&mute=1"
                            style="width: 100%; height: 200px; border: 1px solid #000;"
                            allow="autoplay; encrypted-media" allowfullscreen></iframe>
                ''')

            ui.label('* Recommendations for 195lb/88kg rider').style(
                'font-size: 12px; color: #666; margin-top: 16px; font-style: italic;'
            )

        def show_why():
            """Populate and show the WHY dialog"""
            conditions_container.clear()

            weather = orchestrator.get_weather_context()
            if weather:
                with conditions_container:
                    ui.label('--- CONDITIONS ---').style('font-size: 18px; font-weight: bold; margin-bottom: 8px;')
                    ui.label(f"Wind: {weather['wind_speed']} {weather['wind_direction']}").style('font-size: 16px;')
                    ui.label(f"Waves: {weather['wave_height']}").style('font-size: 16px;')
                    ui.label(f"Swell: {weather['swell_direction']}").style('font-size: 16px;')
            else:
                with conditions_container:
                    ui.label('Weather data unavailable').style('font-size: 16px; color: #666;')

            why_dialog.open()

        why_button.on('click', show_why)
```

### Step 7.3: Test manually

```bash
cd c:\projects\canifuckingdownwindtoday
python -m app.main
```

Visit http://localhost:8080 and click "WHY" to verify the overlay opens.

### Step 7.4: Commit

```bash
git add app/main.py app/orchestrator.py
git commit -m "feat: add WHY panel showing conditions and live cams"
```

---

## Task 8: Track Last Persona in Frontend

**Goal:** Use localStorage to track last persona and pass exclusion to backend.

**Files:**
- Modify: `app/main.py`
- Modify: `app/orchestrator.py`

### Step 8.1: Modify orchestrator to accept exclude_persona

Update the `get_fresh_rating` method signature in `app/orchestrator.py`:

```python
    def get_fresh_rating(self, mode: str, exclude_persona_id: Optional[str] = None) -> Optional[ConditionRating]:
        """
        Get fresh rating, bypassing cache. Used for page refresh.

        Args:
            mode: "sup" or "parawing"
            exclude_persona_id: Persona ID to exclude (for no-repeat rotation)

        Returns:
            ConditionRating or None if weather unavailable
        """
        return self._generate_rating(mode, exclude_persona_id=exclude_persona_id)
```

Update `_generate_rating` to accept and use exclude:

```python
    def _generate_rating(self, mode: str, exclude_persona_id: Optional[str] = None) -> Optional[ConditionRating]:
        """Generate fresh rating for given mode"""
        try:
            # Fetch weather
            conditions = self.weather_fetcher.fetch_current_conditions(
                Config.LOCATION_LAT,
                Config.LOCATION_LON
            )

            if not conditions:
                return self._create_fallback_rating(mode, "Weather data unavailable")

            # Calculate score
            if mode == "sup":
                score = self.score_calculator.calculate_sup_score(conditions)
            else:
                score = self.score_calculator.calculate_parawing_score(conditions)

            # Get random persona (excluding last used if specified)
            persona = get_random_persona(exclude_id=exclude_persona_id)

            # Generate snarky description with persona
            try:
                description = self.llm_client.generate_description(
                    wind_speed=conditions.wind_speed_kts,
                    wind_direction=conditions.wind_direction,
                    wave_height=conditions.wave_height_ft,
                    swell_direction=conditions.swell_direction,
                    rating=score,
                    mode=mode,
                    persona=persona
                )
            except Exception as e:
                print(f"LLM generation failed: {e}")
                description = self._create_fallback_description(conditions, score, mode)

            # Create rating with persona info
            rating = ConditionRating(score=score, mode=mode, description=description)

            # Store persona ID for tracking (we'll add this to the return)
            rating.persona_id = persona["id"]

            # Cache it
            self.cache.set_rating(mode, rating)

            return rating

        except Exception as e:
            print(f"Error generating rating: {e}")
            return self._create_fallback_rating(mode, f"Error: {str(e)}")
```

### Step 8.2: Update ConditionRating model

Modify `app/scoring/models.py` to include optional persona_id:

```python
# ABOUTME: Data models for condition ratings and recommendations
# ABOUTME: Provides structured representation of scores and foil setups

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConditionRating:
    """Rating for current conditions"""
    score: int  # 1-10
    mode: str   # "sup" or "parawing"
    description: str  # Snarky description from LLM
    persona_id: Optional[str] = field(default=None)  # For tracking no-repeat rotation

    def __post_init__(self):
        if not 1 <= self.score <= 10:
            raise ValueError(f"Score must be 1-10, got {self.score}")
```

### Step 8.3: Add JavaScript to track persona in localStorage

In `app/main.py`, add to the head HTML (inside the `<style>` tag area, after the styles):

```python
    ui.add_head_html("""
    <script>
        function getLastPersona() {
            return localStorage.getItem('lastPersonaId') || '';
        }

        function setLastPersona(personaId) {
            localStorage.setItem('lastPersonaId', personaId);
        }
    </script>
    """)
```

### Step 8.4: Use JavaScript interop for persona tracking

This requires NiceGUI's JavaScript interop. Update `prefetch_all` in `app/main.py`:

```python
        async def prefetch_all():
            """Fetch FRESH ratings on page load for both modes"""
            nonlocal cached_recommendations
            try:
                # Get last persona from localStorage via JS
                last_persona = await ui.run_javascript('getLastPersona()')
                exclude_id = last_persona if last_persona else None

                # Always generate fresh ratings on page load
                cached_ratings['sup'] = orchestrator.get_fresh_rating('sup', exclude_persona_id=exclude_id)
                cached_ratings['parawing'] = orchestrator.get_fresh_rating('parawing', exclude_persona_id=exclude_id)

                # Store the new persona ID
                if cached_ratings['sup'] and cached_ratings['sup'].persona_id:
                    await ui.run_javascript(f"setLastPersona('{cached_ratings['sup'].persona_id}')")

                cached_recommendations = orchestrator.get_foil_recommendations()
            except Exception as e:
                print(f"Prefetch error: {e}")
```

Note: You'll need to make the timer callback async:

```python
        ui.timer(0.1, prefetch_all, once=True)
```

### Step 8.5: Run and test manually

```bash
python -m app.main
```

Refresh the page multiple times and verify different personas appear (check browser console for localStorage).

### Step 8.6: Commit

```bash
git add app/main.py app/orchestrator.py app/scoring/models.py
git commit -m "feat: track persona in localStorage for no-repeat rotation"
```

---

## Task 9: Final Integration Testing

**Goal:** Verify all features work together.

### Step 9.1: Run full test suite

```bash
pytest tests/ -v
```

Expected: All tests PASS

### Step 9.2: Manual testing checklist

Test each feature:

1. **Personas**: Refresh page 5+ times, verify different tones appear
2. **WHY Panel**: Click WHY, verify conditions display and videos autoplay
3. **Debug Mode**: Set `DEBUG=true`, verify console shows debug output
4. **KT Recommendations**: Check foil recommendations match condition tier
5. **Fresh Snark**: Refresh page, verify new snarky text each time
6. **EST Timestamp**: Verify "Last updated" shows EST timezone
7. **Video Streams**: Verify all 3 cams load in WHY panel

### Step 9.3: Final commit

```bash
git add -A
git status  # Verify no unexpected files
git commit -m "feat: complete multi-persona and WHY panel implementation"
```

---

## Summary of All Files Changed

**Created:**
- `app/debug.py` - Debug logging utilities
- `app/ai/personas.py` - Persona definitions
- `tests/test_debug.py` - Debug mode tests
- `tests/ai/test_personas.py` - Persona tests

**Modified:**
- `app/config.py` - Added DEBUG env var
- `app/ai/llm_client.py` - Added persona parameter
- `app/orchestrator.py` - Persona integration, fresh ratings, weather context
- `app/scoring/foil_recommender.py` - Score-based recommendations
- `app/scoring/models.py` - Added persona_id field
- `app/main.py` - WHY panel, EST timestamp, persona tracking, fresh snark
- `tests/scoring/test_foil_recommender.py` - New tier-based tests
- `tests/ai/test_llm_client.py` - Persona parameter test

---

## Quick Reference

**Run tests:**
```bash
pytest tests/ -v
```

**Run locally:**
```bash
python -m app.main
```

**Enable debug:**
```bash
DEBUG=true python -m app.main
```

**Test specific file:**
```bash
pytest tests/ai/test_personas.py -v
```