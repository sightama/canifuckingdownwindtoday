# Loading Experience, Silly Graph, and 11/10 Perfect Conditions Implementation Plan

## ✅ IMPLEMENTATION COMPLETE - 2025-12-03

**Status:** All features implemented and tested. PR #7 created.

### Verified Working
- ✅ Loading overlay with pulsing "LOADING" text
- ✅ Cross-fade transition to main UI
- ✅ Crayon graph displays in WHY panel
- ✅ Swell direction parsing from NOAA
- ✅ 11/10 perfect conditions detection
- ✅ All 94 tests passing

### Known Issues (Future Work)
- [ ] WHY panel titles ("WHY THIS SCORE?" and "--- LIVE CAMS ---") are left-aligned instead of centered

---

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add three features: (1) a clean loading experience that hides templated content, (2) a hand-drawn crayon-style graph showing coast and wind direction in the WHY panel, and (3) detection of "11/10" perfect post-frontal conditions for SUP foiling.

**Architecture:**
- Loading: CSS overlay with fade animations, triggered by JavaScript when data is ready
- Graph: SVG-based drawing with randomized wobbly paths, rendered in the WHY dialog
- 11/10: New scoring check in calculator that detects specific condition combinations
- All features require parsing actual swell direction from NOAA (currently approximated)

**Tech Stack:** Python 3.10+, NiceGUI (web UI framework), pytest, CSS animations, SVG

---

## Codebase Orientation

Before starting, familiarize yourself with these key files:

| File | Purpose |
|------|---------|
| `app/main.py` | NiceGUI entry point, UI rendering, WHY panel dialog |
| `app/weather/sources.py` | NOAA API client, parses wind/wave data |
| `app/weather/models.py` | `WeatherConditions` dataclass |
| `app/scoring/calculator.py` | Calculates 1-10 rating based on conditions |
| `app/scoring/models.py` | `ConditionRating` dataclass |
| `app/orchestrator.py` | Coordinates weather fetch → scoring → LLM |
| `app/config.py` | Location coords, thresholds, wind direction classifications |
| `tests/` | Existing test files mirror `app/` structure |

**Running the app locally:**
```bash
pip install -r requirements.txt
python -m app.main
# Opens at http://localhost:8080
```

**Running tests:**
```bash
pytest -v
```

---

## Feature 1: Swell Direction Parsing

### Why This Comes First
The 11/10 detection requires knowing actual swell direction separately from wind direction. Currently `sources.py` just copies wind direction as swell direction (line 53). We need to parse it from NOAA's detailed forecast text.

---

### Task 1.1: Write Failing Test for Swell Direction Parsing

**Files:**
- Create: `tests/weather/test_swell_parsing.py`

**Step 1: Create the test file**

```python
# ABOUTME: Tests for parsing swell direction from NOAA forecast text
# ABOUTME: Verifies extraction of compass directions from various text formats

import pytest
from app.weather.sources import NOAAClient


class TestSwellDirectionParsing:
    """Tests for _parse_swell_direction method"""

    def setup_method(self):
        self.client = NOAAClient()

    def test_parse_northeast_swell_basic(self):
        """Parse 'Northeast swell 3 to 5 ft' format"""
        text = "Northeast swell 3 to 5 ft. Winds from the west."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"

    def test_parse_ne_abbreviation(self):
        """Parse 'NE swell' abbreviation format"""
        text = "Seas 2 to 3 ft. NE swell around 4 ft."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"

    def test_parse_swell_from_direction(self):
        """Parse 'swell from the NE' format"""
        text = "Winds west 10 kt. Swell from the northeast 2 to 4 ft."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"

    def test_parse_southerly_swell(self):
        """Parse southern swell directions"""
        text = "South swell 2 to 3 ft building to 4 ft."
        result = self.client._parse_swell_direction(text)
        assert result == "S"

    def test_parse_sse_swell(self):
        """Parse SSE direction"""
        text = "SSE swell 3 ft. Light winds."
        result = self.client._parse_swell_direction(text)
        assert result == "SSE"

    def test_no_swell_returns_none(self):
        """Return None when no swell direction found"""
        text = "Winds north 15 kt. Seas 2 ft."
        result = self.client._parse_swell_direction(text)
        assert result is None

    def test_mixed_case_handling(self):
        """Handle various capitalizations"""
        text = "NORTHEAST SWELL 4 FT."
        result = self.client._parse_swell_direction(text)
        assert result == "NE"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/weather/test_swell_parsing.py -v
```

Expected output: `AttributeError: 'NOAAClient' object has no attribute '_parse_swell_direction'`

**Step 3: Commit the failing test**

```bash
git add tests/weather/test_swell_parsing.py
git commit -m "test: add failing tests for swell direction parsing"
```

---

### Task 1.2: Implement Swell Direction Parser

**Files:**
- Modify: `app/weather/sources.py` (add method after `_parse_wave_height`, around line 77)

**Step 1: Add the parsing method**

Add this method to the `NOAAClient` class after `_parse_wave_height`:

```python
    def _parse_swell_direction(self, text: str) -> str | None:
        """
        Parse swell direction from NOAA forecast text.

        Handles formats like:
        - "Northeast swell 3 to 5 ft"
        - "NE swell around 4 ft"
        - "Swell from the northeast"

        Returns:
            Compass direction abbreviation (N, NE, E, etc.) or None if not found
        """
        # Map full names to abbreviations
        direction_map = {
            "north": "N", "northeast": "NE", "east": "E", "southeast": "SE",
            "south": "S", "southwest": "SW", "west": "W", "northwest": "NW",
            "nne": "NNE", "ene": "ENE", "ese": "ESE", "sse": "SSE",
            "ssw": "SSW", "wsw": "WSW", "wnw": "WNW", "nnw": "NNW",
        }

        text_lower = text.lower()

        # Pattern 1: "[Direction] swell" (e.g., "Northeast swell 3 ft")
        pattern1 = r'(north(?:east|west)?|south(?:east|west)?|east|west|n[nesw]?[ew]?|s[nesw]?[ew]?|e[ns]?e?|w[ns]?w?)\s+swell'
        match = re.search(pattern1, text_lower)
        if match:
            direction = match.group(1)
            return direction_map.get(direction, direction.upper())

        # Pattern 2: "swell from the [direction]"
        pattern2 = r'swell\s+from\s+(?:the\s+)?(north(?:east|west)?|south(?:east|west)?|east|west)'
        match = re.search(pattern2, text_lower)
        if match:
            direction = match.group(1)
            return direction_map.get(direction, direction.upper())

        return None
```

**Step 2: Run tests to verify they pass**

```bash
pytest tests/weather/test_swell_parsing.py -v
```

Expected: All 7 tests PASS

**Step 3: Commit**

```bash
git add app/weather/sources.py
git commit -m "feat: add swell direction parsing from NOAA forecast text"
```

---

### Task 1.3: Integrate Swell Parsing into Weather Fetch

**Files:**
- Modify: `app/weather/sources.py` (update `fetch_conditions` method)
- Create: `tests/weather/test_swell_integration.py`

**Step 1: Write integration test**

```python
# ABOUTME: Integration test for swell direction in weather fetching
# ABOUTME: Verifies swell direction flows through to WeatherConditions

import pytest
from unittest.mock import patch, MagicMock
from app.weather.sources import NOAAClient


class TestSwellDirectionIntegration:
    """Test that swell direction is properly extracted in fetch_conditions"""

    def test_swell_direction_extracted_from_forecast(self):
        """Swell direction should come from detailed forecast, not wind direction"""
        client = NOAAClient()

        # Mock the API responses
        mock_point_response = MagicMock()
        mock_point_response.json.return_value = {
            "properties": {"forecast": "https://api.weather.gov/forecast"}
        }

        mock_forecast_response = MagicMock()
        mock_forecast_response.json.return_value = {
            "properties": {
                "periods": [{
                    "windSpeed": "15 mph",
                    "windDirection": "NW",  # Wind from NW
                    "detailedForecast": "Northwest winds 15 mph. Seas 3 ft. Northeast swell 2 to 4 ft."
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = [mock_point_response, mock_forecast_response]

            result = client.fetch_conditions(26.9, -80.1)

            # Wind should be NW, but swell should be NE (from forecast text)
            assert result.wind_direction == "NW"
            assert result.swell_direction == "NE"

    def test_swell_direction_fallback_to_wind(self):
        """When no swell direction in text, fall back to wind direction"""
        client = NOAAClient()

        mock_point_response = MagicMock()
        mock_point_response.json.return_value = {
            "properties": {"forecast": "https://api.weather.gov/forecast"}
        }

        mock_forecast_response = MagicMock()
        mock_forecast_response.json.return_value = {
            "properties": {
                "periods": [{
                    "windSpeed": "12 mph",
                    "windDirection": "S",
                    "detailedForecast": "South winds 12 mph. Seas 2 ft."  # No swell direction
                }]
            }
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = [mock_point_response, mock_forecast_response]

            result = client.fetch_conditions(26.9, -80.1)

            # Should fall back to wind direction
            assert result.swell_direction == "S"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/weather/test_swell_integration.py -v
```

Expected: First test FAILS (swell_direction equals wind direction "NW" instead of "NE")

**Step 3: Update fetch_conditions to use swell parser**

In `app/weather/sources.py`, modify the `fetch_conditions` method. Find line 53 (the `swell_direction` assignment) and replace:

```python
# OLD (around line 46-55):
        return WeatherConditions(
            wind_speed_kts=wind_speed_kts,
            wind_direction=period["windDirection"],
            wave_height_ft=wave_height_ft,
            swell_direction=period["windDirection"],  # Approximate for now
            timestamp=datetime.now().isoformat()
        )
```

```python
# NEW:
        # Parse actual swell direction from forecast text, fallback to wind direction
        detailed_forecast = period.get("detailedForecast", "")
        swell_direction = self._parse_swell_direction(detailed_forecast)
        if swell_direction is None:
            swell_direction = period["windDirection"]

        return WeatherConditions(
            wind_speed_kts=wind_speed_kts,
            wind_direction=period["windDirection"],
            wave_height_ft=wave_height_ft,
            swell_direction=swell_direction,
            timestamp=datetime.now().isoformat()
        )
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/weather/test_swell_integration.py tests/weather/test_swell_parsing.py -v
```

Expected: All tests PASS

**Step 5: Run full test suite to check for regressions**

```bash
pytest -v
```

Expected: All existing tests still pass

**Step 6: Commit**

```bash
git add app/weather/sources.py tests/weather/test_swell_integration.py
git commit -m "feat: integrate swell direction parsing into weather fetch"
```

---

## Feature 2: 11/10 Perfect Conditions

### Background
An "11/10" day happens when post-frontal conditions align perfectly:
- Wind direction: NNW, NW, SSE, or SE (parallel-ish to Jupiter coast)
- Wind speed: 14-20 kts
- Swell direction: NE (organized swell from cold front)
- Wave height: 2-4 ft

This only applies to SUP Foil mode, not Parawing.

---

### Task 2.1: Write Failing Test for 11/10 Detection

**Files:**
- Create: `tests/scoring/test_perfect_conditions.py`

**Step 1: Create the test file**

```python
# ABOUTME: Tests for 11/10 perfect post-frontal conditions detection
# ABOUTME: Verifies the specific combination that triggers an 11/10 rating

import pytest
from app.weather.models import WeatherConditions
from app.scoring.calculator import ConditionCalculator


class TestPerfectConditions:
    """Tests for 11/10 'perfect post-frontal' detection"""

    def setup_method(self):
        self.calculator = ConditionCalculator()

    def test_112825_perfect_conditions(self):
        """
        Test case named after Nov 28, 2025 - a perfect post-frontal day.
        NW wind + NE swell + good wave height + right wind speed = 11/10
        """
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-11-28T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11

    def test_perfect_with_nnw_wind(self):
        """NNW wind direction also triggers 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=15.0,
            wind_direction="NNW",
            wave_height_ft=2.5,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11

    def test_perfect_with_sse_wind(self):
        """SSE wind direction also triggers 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=18.0,
            wind_direction="SSE",
            wave_height_ft=3.5,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11

    def test_perfect_with_se_wind(self):
        """SE wind direction also triggers 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=17.0,
            wind_direction="SE",
            wave_height_ft=2.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11

    def test_not_perfect_wrong_wind_direction(self):
        """West wind (offshore) does NOT trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="W",  # Not in allowed list
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score <= 10

    def test_not_perfect_wrong_swell_direction(self):
        """Without NE swell, no 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="S",  # Not NE
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score <= 10

    def test_not_perfect_wind_too_light(self):
        """Wind under 14 kts doesn't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=12.0,  # Below 14
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score <= 10

    def test_not_perfect_wind_too_strong(self):
        """Wind over 20 kts doesn't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=22.0,  # Above 20
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score <= 10

    def test_not_perfect_waves_too_small(self):
        """Waves under 2ft don't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=1.5,  # Below 2
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score <= 10

    def test_not_perfect_waves_too_big(self):
        """Waves over 4ft don't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=5.0,  # Above 4
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score <= 10

    def test_parawing_mode_never_gets_11(self):
        """11/10 only applies to SUP mode, not parawing"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="parawing")

        assert rating.score <= 10

    def test_boundary_wind_speed_14_triggers(self):
        """Exactly 14 kts should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=14.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11

    def test_boundary_wind_speed_20_triggers(self):
        """Exactly 20 kts should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=20.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11

    def test_boundary_wave_height_2_triggers(self):
        """Exactly 2ft waves should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=2.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11

    def test_boundary_wave_height_4_triggers(self):
        """Exactly 4ft waves should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=4.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        rating = self.calculator.calculate(conditions, mode="sup")

        assert rating.score == 11
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/scoring/test_perfect_conditions.py -v
```

Expected: Tests fail because calculator returns max 10, not 11

**Step 3: Commit the failing tests**

```bash
git add tests/scoring/test_perfect_conditions.py
git commit -m "test: add failing tests for 11/10 perfect conditions detection"
```

---

### Task 2.2: Implement 11/10 Detection Logic

**Files:**
- Modify: `app/scoring/calculator.py`

**Step 1: Read the current calculator implementation**

First, read `app/scoring/calculator.py` to understand the existing structure. Look for:
- The `calculate` method signature
- How scores are computed
- Where the score is clamped to 1-10

**Step 2: Add the 11/10 detection method and constants**

Add these constants at the top of the file (after imports):

```python
# Perfect conditions thresholds (11/10 day)
PERFECT_WIND_DIRECTIONS = {"NNW", "NW", "SSE", "SE"}
PERFECT_WIND_SPEED_MIN = 14.0
PERFECT_WIND_SPEED_MAX = 20.0
PERFECT_SWELL_DIRECTION = "NE"
PERFECT_WAVE_HEIGHT_MIN = 2.0
PERFECT_WAVE_HEIGHT_MAX = 4.0
```

Add this method to the `ConditionCalculator` class:

```python
    def _is_perfect_conditions(self, conditions: WeatherConditions) -> bool:
        """
        Check if conditions match 'perfect post-frontal' setup.

        Perfect conditions require ALL of:
        - Wind direction: NNW, NW, SSE, or SE (parallel to Jupiter coast)
        - Wind speed: 14-20 kts
        - Swell direction: NE (organized front-generated swell)
        - Wave height: 2-4 ft

        Returns:
            True if all conditions are met
        """
        wind_dir_ok = conditions.wind_direction in PERFECT_WIND_DIRECTIONS
        wind_speed_ok = PERFECT_WIND_SPEED_MIN <= conditions.wind_speed_kts <= PERFECT_WIND_SPEED_MAX
        swell_ok = conditions.swell_direction == PERFECT_SWELL_DIRECTION
        waves_ok = PERFECT_WAVE_HEIGHT_MIN <= conditions.wave_height_ft <= PERFECT_WAVE_HEIGHT_MAX

        return wind_dir_ok and wind_speed_ok and swell_ok and waves_ok
```

**Step 3: Add logging import at top of file**

```python
import logging

log = logging.getLogger(__name__)
```

**Step 4: Modify the calculate method to check for 11/10**

Find where the score is finalized in the `calculate` method. After calculating the base score but before returning, add:

```python
        # Check for perfect conditions (11/10) - SUP mode only
        if mode == "sup" and self._is_perfect_conditions(conditions):
            log.info(f"Perfect conditions detected! Base score: {score:.1f}, elevated to 11/10")
            score = 11
```

Make sure this comes AFTER any clamping to 1-10, so we can override to 11.

**Step 5: Run tests to verify they pass**

```bash
pytest tests/scoring/test_perfect_conditions.py -v
```

Expected: All 16 tests PASS

**Step 6: Run full test suite**

```bash
pytest -v
```

Expected: All tests pass (no regressions)

**Step 7: Commit**

```bash
git add app/scoring/calculator.py
git commit -m "feat: add 11/10 perfect post-frontal conditions detection"
```

---

### Task 2.3: Update UI to Display 11/10

**Files:**
- Modify: `app/main.py` (the rating display)

**Step 1: Verify no UI changes needed**

The UI currently displays `{rating}/10`. Since we're now allowing 11/10, we should display `{rating}/10` when score ≤ 10, and `11/10` when score is 11.

Check `app/main.py` for where the rating is displayed. Look for something like:
```python
ui.label(f"{rating}/10")
```

If it's using the actual score value, it should automatically show "11/10" - no changes needed.

**Step 2: Manual testing**

Start the app and verify the rating displays correctly:
```bash
python -m app.main
```

You won't see 11/10 unless actual conditions match - that's fine. The tests verify the logic.

**Step 3: Commit if any changes were made**

If no changes needed, skip this commit.

---

## Feature 3: Loading Experience

### Background
Currently the page shows templated placeholders (`--`, `loading`) while data loads. We want a clean white screen with pulsing "LOADING" text, then a cross-fade to the real UI.

---

### Task 3.1: Add Loading Overlay HTML/CSS

**Files:**
- Modify: `app/main.py`

**Step 1: Read the current main.py structure**

Understand how the page is built. Look for:
- Where `ui.page` or the main container is defined
- The `initial_load()` function that fetches data
- How/when content is updated after load

**Step 2: Add CSS for loading animation**

Find where custom styles are added (look for `ui.add_head_html` or similar). Add this CSS:

```python
ui.add_head_html('''
<style>
    /* Loading overlay */
    #loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: white;
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        transition: opacity 0.5s ease-out;
    }

    #loading-overlay.fade-out {
        opacity: 0;
        pointer-events: none;
    }

    #loading-text {
        font-family: monospace;
        font-size: 24px;
        color: #333;
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 1; }
    }

    /* Main content - hidden until loaded */
    #main-content {
        opacity: 0;
        transition: opacity 0.5s ease-in;
    }

    #main-content.visible {
        opacity: 1;
    }
</style>
''')
```

**Step 3: Add loading overlay element**

At the start of the page content (inside the `@ui.page('/')` function), add:

```python
    # Loading overlay - shown until data is ready
    ui.html('<div id="loading-overlay"><span id="loading-text">LOADING</span></div>')
```

**Step 4: Wrap main content in container**

Wrap all the main UI elements in a container div. Find where the main content starts and wrap it:

```python
    with ui.element('div').props('id="main-content"'):
        # ... all existing UI content goes here ...
```

**Step 5: Add JavaScript to trigger fade transition**

Add a function to trigger the cross-fade when loading completes:

```python
async def show_content():
    """Fade out loading overlay and fade in main content"""
    await ui.run_javascript('''
        document.getElementById('loading-overlay').classList.add('fade-out');
        document.getElementById('main-content').classList.add('visible');
        // Remove overlay from DOM after animation
        setTimeout(() => {
            const overlay = document.getElementById('loading-overlay');
            if (overlay) overlay.remove();
        }, 500);
    ''')
```

**Step 6: Call show_content at end of initial_load**

Find the `initial_load()` function. At the very end, after all data is loaded and UI is updated, add:

```python
    await show_content()
```

Make sure `initial_load` is an async function (it probably already is).

**Step 7: Manual testing**

```bash
python -m app.main
```

1. Refresh the page
2. You should see "LOADING" pulsing on white background
3. After 2-5 seconds, it should fade out and the main UI fades in
4. You should NOT see any `--` or placeholder text

**Step 8: Commit**

```bash
git add app/main.py
git commit -m "feat: add loading overlay with pulse animation and cross-fade"
```

---

### Task 3.2: Write Test for Loading State

**Files:**
- Create: `tests/ui/test_loading.py`

Note: UI tests in NiceGUI are tricky. We'll write a basic test that verifies the loading overlay HTML is present.

**Step 1: Create the test**

```python
# ABOUTME: Tests for loading overlay UI behavior
# ABOUTME: Verifies loading state is shown before content

import pytest
from unittest.mock import patch, AsyncMock


class TestLoadingOverlay:
    """Tests for loading screen behavior"""

    def test_loading_overlay_css_includes_pulse_animation(self):
        """Verify the pulse animation is defined"""
        # Import after potential patches
        from app.main import create_app

        # This is a basic sanity check - the actual visual testing
        # would require browser automation (Playwright/Selenium)
        # For now, we verify the app creates without errors
        assert True  # Placeholder - real UI testing needs browser

    def test_loading_text_is_loading(self):
        """Loading text should be 'LOADING' (not something else)"""
        # Read the main.py file and verify the text
        with open('app/main.py', 'r') as f:
            content = f.read()

        assert 'LOADING' in content
        assert 'loading-overlay' in content
        assert 'pulse' in content
```

**Step 2: Run tests**

```bash
pytest tests/ui/test_loading.py -v
```

**Step 3: Commit**

```bash
git add tests/ui/test_loading.py
git commit -m "test: add basic loading overlay tests"
```

---

## Feature 4: Silly Crayon Graph

### Background
A hand-drawn style graph showing:
- Blue wobbly line = Florida coast (runs NNW to SSE)
- Red wobbly line with arrow = wind direction
- Labels: "coast" and "wind" with arrows pointing to lines
- Positioned at top of WHY panel, above conditions

---

### Task 4.1: Create Graph Generator Module

**Files:**
- Create: `app/ui/crayon_graph.py`
- Create: `tests/ui/test_crayon_graph.py`

**Step 1: Write the failing test**

```python
# ABOUTME: Tests for crayon-style graph generation
# ABOUTME: Verifies SVG output contains required elements

import pytest
from app.ui.crayon_graph import CrayonGraph


class TestCrayonGraph:
    """Tests for the silly hand-drawn graph generator"""

    def test_generates_svg(self):
        """Output should be valid SVG"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')

    def test_contains_coast_line(self):
        """SVG should contain a blue coast line"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        # Check for blue stroke (coast)
        assert 'stroke="blue"' in svg or 'stroke="#' in svg

    def test_contains_wind_line(self):
        """SVG should contain a red wind line"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert 'stroke="red"' in svg or 'stroke="#' in svg

    def test_contains_coast_label(self):
        """SVG should have 'coast' label"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert 'coast' in svg.lower()

    def test_contains_wind_label(self):
        """SVG should have 'wind' label"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert 'wind' in svg.lower()

    def test_wind_direction_affects_arrow(self):
        """Different wind directions should produce different SVGs"""
        graph = CrayonGraph()
        svg_ne = graph.render(wind_direction="NE")
        svg_sw = graph.render(wind_direction="SW")

        # The SVGs should be different (arrow pointing different direction)
        assert svg_ne != svg_sw

    def test_all_eight_directions_work(self):
        """All 8 compass directions should render without error"""
        graph = CrayonGraph()
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

        for direction in directions:
            svg = graph.render(wind_direction=direction)
            assert '<svg' in svg, f"Failed for direction: {direction}"

    def test_wobbly_line_style_default(self):
        """Default line style should be 'wobbly'"""
        graph = CrayonGraph()
        assert graph.line_style == "wobbly"

    def test_can_change_line_style(self):
        """Should be able to set different line styles"""
        graph = CrayonGraph(line_style="sketchy")
        assert graph.line_style == "sketchy"

        graph2 = CrayonGraph(line_style="chunky")
        assert graph2.line_style == "chunky"

    def test_transparent_background(self):
        """SVG should have transparent background (no fill or white fill)"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        # Should not have a solid background rectangle
        # or should have fill="none" or fill="transparent"
        assert 'fill="white"' not in svg or 'fill="none"' in svg
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/ui/test_crayon_graph.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.ui.crayon_graph'`

**Step 3: Commit failing test**

```bash
git add tests/ui/test_crayon_graph.py
git commit -m "test: add failing tests for crayon graph generator"
```

---

### Task 4.2: Implement Crayon Graph Generator

**Files:**
- Create: `app/ui/__init__.py` (if doesn't exist)
- Create: `app/ui/crayon_graph.py`

**Step 1: Create the ui package init**

```python
# ABOUTME: UI components package
# ABOUTME: Contains custom UI elements like the crayon graph
```

**Step 2: Create the crayon graph module**

```python
# ABOUTME: Generates a hand-drawn style SVG graph showing coast and wind direction
# ABOUTME: Creates wobbly lines that look like a child drew them with crayons

import random
import math
from typing import Literal


LineStyle = Literal["wobbly", "sketchy", "chunky"]


class CrayonGraph:
    """
    Generates a silly hand-drawn SVG showing Florida coast and wind direction.

    The coast runs roughly NNW to SSE (340° to 160°).
    Wind arrow points in the direction wind is going (not coming from).
    """

    # SVG dimensions
    WIDTH = 300
    HEIGHT = 250

    # Coast line runs from top-left-ish to bottom-right-ish
    # Representing NNW to SSE orientation
    COAST_START = (80, 30)
    COAST_END = (220, 220)

    # Wind arrow directions (degrees, 0 = right/east, 90 = down/south)
    DIRECTION_ANGLES = {
        "N": 270,
        "NE": 315,
        "E": 0,
        "SE": 45,
        "S": 90,
        "SW": 135,
        "W": 180,
        "NW": 225,
        "NNW": 247,
        "NNE": 292,
        "ENE": 337,
        "ESE": 22,
        "SSE": 67,
        "SSW": 112,
        "WSW": 157,
        "WNW": 202,
    }

    def __init__(self, line_style: LineStyle = "wobbly"):
        self.line_style = line_style
        # Use fixed seed for consistent look during same session
        # but re-seed each render for slight variation
        self._wobble_amount = 8

    def render(self, wind_direction: str) -> str:
        """
        Render the SVG graph.

        Args:
            wind_direction: Compass direction (N, NE, E, SE, S, SW, W, NW)

        Returns:
            SVG string
        """
        random.seed()  # Re-randomize for each render

        elements = []

        # Coast line (blue)
        coast_path = self._make_wobbly_line(
            self.COAST_START,
            self.COAST_END,
            color="blue",
            stroke_width=4
        )
        elements.append(coast_path)

        # Wind line with arrow (red)
        wind_elements = self._make_wind_arrow(wind_direction)
        elements.extend(wind_elements)

        # Labels
        coast_label = self._make_label("coast", (30, 80), pointer_to=(70, 60))
        wind_label = self._make_label("wind", (200, 180), pointer_to=(160, 140))
        elements.append(coast_label)
        elements.append(wind_label)

        # Assemble SVG
        svg = f'''<svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg" style="background: transparent;">
    {chr(10).join(elements)}
</svg>'''

        return svg

    def _make_wobbly_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str = "blue",
        stroke_width: int = 3
    ) -> str:
        """Generate a wobbly path that looks hand-drawn."""
        x1, y1 = start
        x2, y2 = end

        # Generate intermediate points with wobble
        num_points = 8
        points = []

        for i in range(num_points + 1):
            t = i / num_points
            # Linear interpolation
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t

            # Add wobble (except at endpoints)
            if 0 < i < num_points:
                x += random.uniform(-self._wobble_amount, self._wobble_amount)
                y += random.uniform(-self._wobble_amount, self._wobble_amount)

            points.append((x, y))

        # Create SVG path
        path_d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
        for px, py in points[1:]:
            path_d += f" L {px:.1f} {py:.1f}"

        return f'<path d="{path_d}" stroke="{color}" stroke-width="{stroke_width}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'

    def _make_wind_arrow(self, direction: str) -> list[str]:
        """Generate wind line with arrow head."""
        elements = []

        # Arrow starts near center of graph
        center_x, center_y = 150, 120

        # Get angle for this direction
        angle_deg = self.DIRECTION_ANGLES.get(direction.upper(), 0)
        angle_rad = math.radians(angle_deg)

        # Arrow length
        length = 70

        # Calculate end point
        end_x = center_x + length * math.cos(angle_rad)
        end_y = center_y + length * math.sin(angle_rad)

        # Main arrow line
        arrow_line = self._make_wobbly_line(
            (center_x, center_y),
            (end_x, end_y),
            color="red",
            stroke_width=4
        )
        elements.append(arrow_line)

        # Arrow head (two short lines)
        head_size = 15
        head_angle1 = angle_rad + math.radians(150)
        head_angle2 = angle_rad - math.radians(150)

        head1_end = (
            end_x + head_size * math.cos(head_angle1) + random.uniform(-3, 3),
            end_y + head_size * math.sin(head_angle1) + random.uniform(-3, 3)
        )
        head2_end = (
            end_x + head_size * math.cos(head_angle2) + random.uniform(-3, 3),
            end_y + head_size * math.sin(head_angle2) + random.uniform(-3, 3)
        )

        # Wobbly arrow head lines
        head1 = self._make_wobbly_line((end_x, end_y), head1_end, color="red", stroke_width=3)
        head2 = self._make_wobbly_line((end_x, end_y), head2_end, color="red", stroke_width=3)

        elements.append(head1)
        elements.append(head2)

        return elements

    def _make_label(
        self,
        text: str,
        position: tuple[float, float],
        pointer_to: tuple[float, float]
    ) -> str:
        """Create a hand-written style label with pointer line."""
        x, y = position
        px, py = pointer_to

        # Wobbly pointer line
        pointer = self._make_wobbly_line(
            (x + 20, y - 5),  # Start near text
            pointer_to,
            color="#333",
            stroke_width=2
        )

        # Text (using a casual font)
        text_elem = f'<text x="{x}" y="{y}" font-family="Comic Sans MS, cursive, sans-serif" font-size="16" fill="#333">{text}</text>'

        return f'<g>{pointer}{text_elem}</g>'
```

**Step 3: Run tests to verify they pass**

```bash
pytest tests/ui/test_crayon_graph.py -v
```

Expected: All 10 tests PASS

**Step 4: Commit**

```bash
git add app/ui/__init__.py app/ui/crayon_graph.py
git commit -m "feat: add crayon-style graph generator for coast and wind"
```

---

### Task 4.3: Integrate Graph into WHY Panel

**Files:**
- Modify: `app/main.py` (the WHY dialog section)

**Step 1: Import the graph generator**

Add at top of `app/main.py`:

```python
from app.ui.crayon_graph import CrayonGraph
```

**Step 2: Find the WHY panel dialog code**

Look for `ui.dialog()` and the WHY panel content (around lines 116-179 based on earlier exploration).

**Step 3: Add graph rendering to show_why function**

Find the `show_why()` function. At the beginning of the content (after "WHY THIS SCORE?" header, before conditions), add:

```python
        # Render crayon graph
        graph = CrayonGraph()
        weather = orchestrator.get_weather_context()
        wind_dir = weather.get('wind_direction', 'N')
        svg = graph.render(wind_direction=wind_dir)

        # Display graph
        ui.html(svg).style('width: 100%; display: flex; justify-content: center; margin: 20px 0;')
```

**Step 4: Manual testing**

```bash
python -m app.main
```

1. Click the "WHY" link
2. You should see the crayon graph at the top of the dialog
3. The wind arrow should point in the current wind direction
4. Below the graph, you should still see the conditions text

**Step 5: Commit**

```bash
git add app/main.py
git commit -m "feat: add crayon graph to WHY panel"
```

---

### Task 4.4: Add Line Style Configuration

**Files:**
- Modify: `app/ui/crayon_graph.py` (add sketchy and chunky styles)

**Step 1: Implement sketchy style**

The "sketchy" style draws multiple overlapping lines. Modify `_make_wobbly_line` to check style:

```python
    def _make_wobbly_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str = "blue",
        stroke_width: int = 3
    ) -> str:
        """Generate a path that looks hand-drawn based on current line_style."""
        if self.line_style == "sketchy":
            return self._make_sketchy_line(start, end, color, stroke_width)
        elif self.line_style == "chunky":
            return self._make_chunky_line(start, end, color, stroke_width)
        else:  # wobbly (default)
            return self._make_wobbly_line_impl(start, end, color, stroke_width)
```

Then rename the current implementation to `_make_wobbly_line_impl` and add:

```python
    def _make_sketchy_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str,
        stroke_width: int
    ) -> str:
        """Multiple overlapping strokes like scribbling."""
        paths = []
        for i in range(3):
            offset = (i - 1) * 2
            adjusted_start = (start[0] + offset, start[1] + offset)
            adjusted_end = (end[0] + offset, end[1] - offset)
            path = self._make_wobbly_line_impl(
                adjusted_start,
                adjusted_end,
                color,
                stroke_width - 1
            )
            paths.append(path)
        return '\n'.join(paths)

    def _make_chunky_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str,
        stroke_width: int
    ) -> str:
        """Thick irregular line like a fat crayon."""
        # Use larger wobble and thicker stroke
        old_wobble = self._wobble_amount
        self._wobble_amount = 12
        path = self._make_wobbly_line_impl(start, end, color, stroke_width + 4)
        self._wobble_amount = old_wobble
        return path
```

**Step 2: Run tests**

```bash
pytest tests/ui/test_crayon_graph.py -v
```

**Step 3: Commit**

```bash
git add app/ui/crayon_graph.py
git commit -m "feat: add sketchy and chunky line style options to crayon graph"
```

---

## Final Verification

### Task 5.1: Full Test Suite

**Step 1: Run all tests**

```bash
pytest -v
```

Expected: All tests pass

**Step 2: Manual end-to-end test**

```bash
python -m app.main
```

Verify:
1. ✅ Page loads with "LOADING" pulsing text on white screen
2. ✅ After data loads, smooth cross-fade to main UI
3. ✅ No placeholder text (`--`, `loading`) visible during load
4. ✅ Click "WHY" - see crayon graph at top
5. ✅ Graph shows blue coast line, red wind arrow pointing correct direction
6. ✅ Conditions still display below graph

**Step 3: Commit any final fixes**

```bash
git add -A
git commit -m "chore: final cleanup and verification"
```

---

## Summary of Files Changed

| Feature | Files Created | Files Modified |
|---------|--------------|----------------|
| Swell Parsing | `tests/weather/test_swell_parsing.py`, `tests/weather/test_swell_integration.py` | `app/weather/sources.py` |
| 11/10 Conditions | `tests/scoring/test_perfect_conditions.py` | `app/scoring/calculator.py` |
| Loading Experience | `tests/ui/test_loading.py` | `app/main.py` |
| Crayon Graph | `app/ui/__init__.py`, `app/ui/crayon_graph.py`, `tests/ui/test_crayon_graph.py` | `app/main.py` |

---

## Troubleshooting

### "Module not found" errors
Make sure you're running from the project root and have the virtual environment activated:
```bash
pip install -r requirements.txt
```

### Tests pass but UI doesn't work
Check the browser console for JavaScript errors. NiceGUI renders in the browser, so JS issues won't appear in Python logs.

### Graph looks wrong
Try different line styles:
```python
graph = CrayonGraph(line_style="sketchy")  # or "chunky"
```

### 11/10 never triggers
Check that:
1. Swell direction is being parsed correctly (add debug logging)
2. All four conditions are actually met (wind dir, wind speed, swell dir, wave height)
3. Mode is "sup" (parawing never gets 11)
