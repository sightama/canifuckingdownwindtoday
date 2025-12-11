# Fast Initial Load Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce initial page load time from ~15-30 seconds to ~2-3 seconds by generating only the minimum required LLM content upfront and loading the rest in the background.

**Architecture:** Two-phase loading strategy:
1. **Fast path**: Generate variations for 1 persona + 1 mode (SUP) only, show page immediately
2. **Background path**: Async-fetch remaining personas and parawing mode after page is visible

**Tech Stack:** Python 3.9+, NiceGUI (async), Google Gemini 2.5 Flash-Lite API

---

## Background Context

### The Problem

The current implementation calls `generate_all_variations()` which generates **48 responses per API call** (6 personas × 8 variations). This happens **twice** (SUP + Parawing mode) **sequentially** during page load, blocking for 15-30+ seconds.

### The Solution

1. On load: Generate variations for **1 persona only** for **SUP mode only** (single small API call)
2. Show page immediately with that content
3. Background: Fetch remaining 5 personas + all parawing variations asynchronously

### Files Overview

| File | Purpose |
|------|---------|
| `app/ai/llm_client.py` | LLM API interface - add single-persona generation method |
| `app/orchestrator.py` | App orchestrator - add fast initial load + background refresh methods |
| `app/main.py` | NiceGUI frontend - wire up two-phase loading |
| `tests/ai/test_llm_client.py` | LLM client tests |
| `tests/test_orchestrator.py` | Orchestrator tests |

---

## Task 1: Add Single-Persona Variation Generation to LLMClient

**Files:**
- Modify: `app/ai/llm_client.py` (add new method after line 176)
- Test: `tests/ai/test_llm_client.py`

### Step 1.1: Write the failing test

Add to `tests/ai/test_llm_client.py`:

```python
class TestSinglePersonaVariations:
    """Tests for generating variations for a single persona"""

    def test_generate_single_persona_variations_returns_list(self):
        """Single persona generation returns list of variations"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            mock_response = MagicMock()
            mock_response.text = """1. First drill sergeant response for testing.
2. Second drill sergeant response here.
3. Third one with some variety.
4. Fourth response to fill it out."""

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
```

### Step 1.2: Run test to verify it fails

```bash
pytest tests/ai/test_llm_client.py::TestSinglePersonaVariations -v
```

**Expected:** FAIL with `AttributeError: 'LLMClient' object has no attribute 'generate_single_persona_variations'`

### Step 1.3: Write minimal implementation

Add to `app/ai/llm_client.py` after line 176 (after `generate_all_variations` method):

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

Format as numbered list:
1. [response]
2. [response]
...
"""

        debug_log(f"Single persona prompt length: {len(prompt)} chars", "LLM")

        try:
            response = self.model.generate_content(prompt)
            debug_log(f"Single persona response length: {len(response.text)} chars", "LLM")

            # Parse numbered list
            lines = []
            for line in response.text.strip().split('\n'):
                line = line.strip()
                import re
                match = re.match(r'^\d+\.\s*(.+)$', line)
                if match:
                    lines.append(match.group(1).strip())

            return lines
        except Exception as e:
            debug_log(f"Single persona API error: {e}", "LLM")
            print(f"LLM single persona API error: {e}")
            return []
```

### Step 1.4: Run test to verify it passes

```bash
pytest tests/ai/test_llm_client.py::TestSinglePersonaVariations -v
```

**Expected:** PASS (2 tests)

### Step 1.5: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "feat: add single-persona variation generation for fast initial load

Add generate_single_persona_variations() method to LLMClient that generates
variations for one persona only. This enables fast initial page load by
fetching minimal content upfront.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Add Fast Initial Load Method to Orchestrator

**Files:**
- Modify: `app/orchestrator.py` (add new method)
- Test: `tests/test_orchestrator.py`

### Step 2.1: Write the failing test

Add to `tests/test_orchestrator.py`:

```python
class TestFastInitialLoad:
    """Tests for fast initial page load"""

    def test_get_initial_data_returns_minimal_structure(self):
        """Fast initial load returns data for display with single persona"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = mock_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            mock_llm.generate_single_persona_variations.return_value = [
                "Test response 1",
                "Test response 2"
            ]
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            result = orchestrator.get_initial_data(persona_id="drill_sergeant")

            assert result["is_offline"] is False
            assert result["ratings"]["sup"] is not None
            assert "drill_sergeant" in result["variations"]["sup"]
            assert len(result["variations"]["sup"]["drill_sergeant"]) == 2

    def test_get_initial_data_only_generates_one_api_call(self):
        """Fast path makes exactly one LLM API call"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = mock_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            mock_llm.generate_single_persona_variations.return_value = ["Test"]
            mock_llm.generate_all_variations.return_value = {}
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            orchestrator.get_initial_data(persona_id="drill_sergeant")

            # Should call single persona method exactly once
            assert mock_llm.generate_single_persona_variations.call_count == 1
            # Should NOT call batch method
            assert mock_llm.generate_all_variations.call_count == 0
```

### Step 2.2: Run test to verify it fails

```bash
pytest tests/test_orchestrator.py::TestFastInitialLoad -v
```

**Expected:** FAIL with `AttributeError: 'AppOrchestrator' object has no attribute 'get_initial_data'`

### Step 2.3: Write minimal implementation

Add to `app/orchestrator.py` after `get_cached_data` method (around line 67):

```python
    def get_initial_data(self, persona_id: str) -> dict:
        """
        Fast path for initial page load.

        Fetches sensor data and generates variations for ONE persona in ONE mode.
        Use refresh_remaining_variations() afterward to populate full cache.

        Args:
            persona_id: The persona to generate variations for

        Returns:
            Same structure as get_cached_data() but with minimal variations
        """
        # Refresh sensor if needed
        if self.cache.is_sensor_stale():
            self._refresh_sensor()

        # Check offline state
        if self.cache.is_offline():
            return self._build_offline_response()

        # Get current ratings
        sensor_data = self.cache.get_sensor()
        if not sensor_data or not sensor_data.get("reading"):
            return self._build_offline_response()

        reading = sensor_data["reading"]
        ratings = sensor_data.get("ratings", {})

        # Generate variations for single persona, SUP mode only
        sup_variations = self.llm_client.generate_single_persona_variations(
            wind_speed=reading.wind_speed_kts,
            wind_direction=reading.wind_direction,
            wave_height=0,
            swell_direction="N",
            rating=ratings.get("sup", 5),
            mode="sup",
            persona_id=persona_id
        )

        debug_log(f"Initial load: {len(sup_variations)} variations for {persona_id}", "ORCHESTRATOR")

        return {
            "is_offline": False,
            "timestamp": sensor_data.get("fetched_at"),
            "last_known_reading": reading,
            "weather": self._reading_to_weather_dict(reading),
            "ratings": ratings,
            "variations": {
                "sup": {persona_id: sup_variations},
                "parawing": {}
            },
            "initial_persona_id": persona_id
        }
```

### Step 2.4: Run test to verify it passes

```bash
pytest tests/test_orchestrator.py::TestFastInitialLoad -v
```

**Expected:** PASS (2 tests)

### Step 2.5: Commit

```bash
git add app/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add fast initial load method to orchestrator

Add get_initial_data() that fetches sensor data and generates variations
for a single persona/mode. This reduces initial API calls from 2 large
requests to 1 small request.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Add Background Refresh Method to Orchestrator

**Files:**
- Modify: `app/orchestrator.py`
- Test: `tests/test_orchestrator.py`

### Step 3.1: Write the failing test

Add to `tests/test_orchestrator.py` in `TestFastInitialLoad` class:

```python
    def test_refresh_remaining_variations_fills_cache(self):
        """Background refresh generates all remaining variations"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc),
                spot_name="Test"
            )

            mock_cache = MagicMock()
            mock_cache.is_offline.return_value = False
            mock_cache.get_sensor.return_value = {
                "reading": mock_reading,
                "ratings": {"sup": 7, "parawing": 8},
                "fetched_at": datetime.now(timezone.utc)
            }
            mock_cache.get_ratings.return_value = {"sup": 7, "parawing": 8}
            MockCache.return_value = mock_cache

            mock_llm = MagicMock()
            mock_llm.generate_all_variations.return_value = {
                "drill_sergeant": ["response1"],
                "disappointed_dad": ["response2"]
            }
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.cache = mock_cache
            orchestrator.llm_client = mock_llm

            orchestrator.refresh_remaining_variations(
                initial_persona_id="drill_sergeant",
                initial_mode="sup"
            )

            # Should call generate_all_variations for both modes
            assert mock_llm.generate_all_variations.call_count == 2

            # Should update cache
            mock_cache.set_variations.assert_called()
```

### Step 3.2: Run test to verify it fails

```bash
pytest tests/test_orchestrator.py::TestFastInitialLoad::test_refresh_remaining_variations_fills_cache -v
```

**Expected:** FAIL with `AttributeError: 'AppOrchestrator' object has no attribute 'refresh_remaining_variations'`

### Step 3.3: Write minimal implementation

Add to `app/orchestrator.py` after `get_initial_data` method:

```python
    def refresh_remaining_variations(
        self,
        initial_persona_id: str,
        initial_mode: str = "sup"
    ) -> None:
        """
        Background task: Generate remaining variations not fetched during initial load.

        This populates the full cache with all personas and both modes.
        Call this AFTER get_initial_data() and after the page is visible.

        Args:
            initial_persona_id: Persona already fetched (will be merged, not refetched)
            initial_mode: Mode already fetched (default "sup")
        """
        if self.cache.is_offline():
            debug_log("Skipping background refresh - offline", "ORCHESTRATOR")
            return

        sensor_data = self.cache.get_sensor()
        if not sensor_data or not sensor_data.get("reading"):
            debug_log("Skipping background refresh - no sensor data", "ORCHESTRATOR")
            return

        reading = sensor_data["reading"]
        ratings = self.cache.get_ratings() or {"sup": 5, "parawing": 5}

        debug_log("Starting background variation refresh", "ORCHESTRATOR")

        # Generate full variations for both modes
        variations = {"sup": {}, "parawing": {}}

        for mode in ["sup", "parawing"]:
            mode_variations = self.llm_client.generate_all_variations(
                wind_speed=reading.wind_speed_kts,
                wind_direction=reading.wind_direction,
                wave_height=0,
                swell_direction="N",
                rating=ratings[mode],
                mode=mode
            )
            variations[mode] = mode_variations

        self.cache.set_variations(ratings, variations)
        debug_log(f"Background refresh complete: {sum(len(v) for v in variations['sup'].values())} SUP variations", "ORCHESTRATOR")
```

### Step 3.4: Run test to verify it passes

```bash
pytest tests/test_orchestrator.py::TestFastInitialLoad::test_refresh_remaining_variations_fills_cache -v
```

**Expected:** PASS

### Step 3.5: Commit

```bash
git add app/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add background refresh method for remaining variations

Add refresh_remaining_variations() to populate full cache after initial
page load. This runs in background after user sees content.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Update Main.py for Two-Phase Loading

**Files:**
- Modify: `app/main.py` (lines 279-406)
- Test: Manual testing (NiceGUI UI)

### Step 4.1: Understand current flow

Current flow in `app/main.py:279-406`:
1. `prefetch_all()` calls `orchestrator.get_cached_data()` (SLOW - 2 big API calls)
2. `update_display()` shows content
3. `show_content()` fades out loading overlay

New flow:
1. `fast_initial_load()` calls `orchestrator.get_initial_data(persona_id)` (FAST - 1 small API call)
2. `update_display()` shows content
3. `show_content()` fades out loading overlay
4. `background_refresh()` calls `orchestrator.refresh_remaining_variations()` (runs async after page visible)

### Step 4.2: Replace prefetch_all with fast_initial_load

Replace lines 279-305 in `app/main.py` with:

```python
        # Pre-fetch data
        cached_data = None
        current_persona_id = None
        cached_recommendations = None

        async def fast_initial_load():
            """Fast path: fetch sensor + 1 persona only, show page immediately"""
            nonlocal cached_data, current_persona_id, cached_recommendations
            try:
                from app.ai.personas import get_random_persona

                # Get last persona from localStorage via JS
                last_persona = await ui.run_javascript('getLastPersona()')
                exclude_id = last_persona if last_persona else None

                # Select a random persona (excluding last one)
                persona = get_random_persona(exclude_id=exclude_id)
                current_persona_id = persona["id"]

                # Store the new persona ID
                await ui.run_javascript(f"setLastPersona('{current_persona_id}')")

                # FAST PATH: Get initial data with single persona
                cached_data = orchestrator.get_initial_data(persona_id=current_persona_id)

                # Get foil recommendations
                if cached_data and cached_data.get('ratings', {}).get('sup', 0) > 0:
                    cached_recommendations = orchestrator.get_foil_recommendations(
                        score=cached_data['ratings']['sup']
                    )
                else:
                    cached_recommendations = orchestrator.get_foil_recommendations()

            except Exception as e:
                print(f"Fast initial load error: {e}")
                # Fallback to full load on error
                cached_data = orchestrator.get_cached_data()

        async def background_refresh():
            """Background: fetch remaining personas and parawing mode"""
            try:
                if current_persona_id and cached_data and not cached_data.get("is_offline"):
                    # Run in executor to not block UI
                    import asyncio
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: orchestrator.refresh_remaining_variations(
                            initial_persona_id=current_persona_id,
                            initial_mode="sup"
                        )
                    )
            except Exception as e:
                print(f"Background refresh error: {e}")
```

### Step 4.3: Update initial_load to use two-phase approach

Replace the `initial_load` function (around line 401-406) with:

```python
        # Update on toggle change (instant since data is cached)
        toggle.on_value_change(lambda: update_display())

        # Initial load: fast path then background refresh
        async def initial_load():
            await fast_initial_load()
            update_display()
            await show_content()
            # Start background refresh after page is visible
            ui.timer(0.5, background_refresh, once=True)

        ui.timer(0.1, initial_load, once=True)
```

### Step 4.4: Test manually

```bash
# Start the app
python -m app.main
```

**Expected behavior:**
1. Page shows "LOADING" briefly (~2-3 seconds instead of 15-30)
2. Content appears with rating and snarky text
3. No "Connection lost" message
4. Console shows background refresh completing after page is visible

### Step 4.5: Commit

```bash
git add app/main.py
git commit -m "feat: implement two-phase loading for fast initial page load

Replace single slow prefetch with:
1. fast_initial_load() - 1 persona, 1 mode, ~2-3 sec
2. background_refresh() - remaining variations after page visible

This eliminates the Connection lost message and dramatically improves
perceived load time.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Run Full Test Suite and Verify

### Step 5.1: Run all tests

```bash
pytest -v
```

**Expected:** All tests pass

### Step 5.2: Run integration test

```bash
pytest tests/integration/test_end_to_end.py -v
```

**Expected:** Integration tests pass

### Step 5.3: Manual smoke test

```bash
python -m app.main
```

1. Open browser to http://localhost:8080
2. Verify page loads in ~2-3 seconds
3. Verify no "Connection lost" message appears
4. Verify rating and snarky text displays correctly
5. Toggle to "Trashbaggers" - verify it works (may show fallback text initially if background hasn't finished)
6. Refresh page - verify fast load again

### Step 5.4: Final commit

```bash
git add -A
git commit -m "test: verify fast initial load implementation

All tests passing. Manual smoke test confirms:
- Page loads in ~2-3 seconds (down from 15-30)
- No Connection lost message
- Background refresh populates full cache

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `app/ai/llm_client.py` | Add `generate_single_persona_variations()` method |
| `app/orchestrator.py` | Add `get_initial_data()` and `refresh_remaining_variations()` methods |
| `app/main.py` | Replace `prefetch_all()` with two-phase `fast_initial_load()` + `background_refresh()` |
| `tests/ai/test_llm_client.py` | Add tests for single persona generation |
| `tests/test_orchestrator.py` | Add tests for fast initial load and background refresh |

## Rollback Plan

If issues arise, revert to previous behavior:
1. In `app/main.py`, change `fast_initial_load()` to call `orchestrator.get_cached_data()` instead
2. Remove the `background_refresh()` timer

The new methods in `llm_client.py` and `orchestrator.py` can remain as they don't affect existing functionality.
