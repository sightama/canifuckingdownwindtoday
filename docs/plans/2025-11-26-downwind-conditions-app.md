# Can I Fucking Downwind Today - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a simple NiceGUI web app that tells advanced downwind foilers in Jupiter, FL whether today is a good day to go out, with snarky commentary and foil recommendations.

**Architecture:** Hybrid approach - fetch raw weather data from free APIs (NOAA, OpenWeatherMap), calculate 1-10 ratings with deterministic logic, use LLM API to generate snarky descriptions. Cache everything for 2-3 hours to minimize API costs and maximize speed.

**Tech Stack:** Python, NiceGUI, NOAA/OpenWeatherMap APIs, Google Gemini 2.5 Flash (free tier), pytest

---

## Progress Tracker

| Task | Description | Status | Notes |
|------|-------------|--------|-------|
| 1 | Project Setup & Dependencies | ✅ Complete | |
| 2 | Configuration Module | ✅ Complete | |
| 3 | Weather Data Models | ✅ Complete | |
| 4 | NOAA Weather Fetcher | ✅ Complete | |
| 5 | Weather Fetcher Orchestrator | ✅ Complete | |
| 6 | Scoring Calculator - Basic Structure | ✅ Complete | |
| 7 | SUP Foil Scoring Logic | ✅ Complete | Wind direction corrected |
| 8 | Parawing Scoring Logic | ✅ Complete | |
| 9 | Foil Recommendation Logic | ✅ Complete | |
| 10 | LLM Client Interface | ✅ Complete | |
| 11 | Cache Manager | ✅ Complete | |
| 12 | Main Application Orchestrator | ✅ Complete | |
| 13 | NiceGUI User Interface - Basic Structure | ✅ Complete | Combined with Task 14 |
| 14 | UI Styling - 90s Aesthetic | ✅ Complete | Combined with Task 13 |
| 15 | Environment Setup Documentation | ✅ Complete | |
| 16 | Integration Testing | ✅ Complete | Fixed NOAA two-step API mocking |
| 17 | Error Handling & Robustness | ✅ Complete | |
| 18 | Final Testing & Verification | ✅ Complete | 76% coverage |
| 19 | Deployment Preparation | ✅ Complete | |
| 20 | Create .env and Final Verification | ✅ Complete | NiceGUI sanitize fix applied |
| 21 | Pre-fetch ratings for instant toggle | ✅ Complete | Both SUP/Parawing loaded on page load |
| 22 | Responsive CSS for mobile scaling | ✅ Complete | clamp() and viewport units |
| 23 | Fix Gemini model name | ✅ Complete | Changed to gemini-1.5-flash |
| 24 | Fix LLM Service Unavailable | ✅ Complete | Model updated to gemini-2.0-flash |

**Last Updated:** 2025-12-01
**Tests:** 36 passing

### Wind Direction Correction (Applied in Task 7)

The original plan incorrectly specified East/ESE/SE as optimal wind directions. Jupiter FL's coast runs **North-South**, so for downwinding you want wind **parallel** to the coast.

**Corrected configuration in `app/config.py`:**
```python
OPTIMAL_WIND_DIRECTIONS = ["N", "S"]        # Parallel to coast - best
GOOD_WIND_DIRECTIONS = ["NE", "SE", "NW", "SW"]  # Diagonal - good
OK_WIND_DIRECTIONS = ["NNE", "SSE", "NNW", "SSW", "ENE", "ESE", "WNW", "WSW"]  # Acceptable
BAD_WIND_DIRECTIONS = ["E", "W"]            # Perpendicular to coast - bad
```

---

## Prerequisites

Before starting, ensure you have:
- Python 3.10+ installed
- Virtual environment created: `python -m venv .venv`
- Virtual environment activated: `source .venv/bin/activate` (or `.venv\Scripts\activate` on Windows)
- Git initialized and on a feature branch

---

## Task 1: Project Setup & Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore` (modify if exists)

**Step 1: Create requirements.txt**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/requirements.txt`:

```txt
nicegui>=2.0.0
google-generativeai>=0.8.0
requests>=2.32.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

**Step 2: Create .env.example**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/.env.example`:

```
GEMINI_API_KEY=your_api_key_here
CACHE_REFRESH_HOURS=2
```

**Step 3: Update .gitignore**

Ensure `.gitignore` contains:

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
*.log
```

**Step 4: Install dependencies**

Run:
```bash
pip install -r requirements.txt
```

Expected: All packages install successfully

**Step 5: Commit**

```bash
git add requirements.txt .env.example .gitignore
git commit -m "feat: add project dependencies and environment setup"
```

---

## Task 2: Configuration Module

**Files:**
- Create: `app/config.py`
- Create: `tests/test_config.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/test_config.py`:

```python
# ABOUTME: Tests for application configuration and location settings
# ABOUTME: Validates Jupiter FL coordinates and weather API configuration

from app.config import Config


def test_config_has_jupiter_coordinates():
    """Jupiter, FL coordinates should be defined"""
    assert Config.LOCATION_LAT == 26.9
    assert Config.LOCATION_LON == -80.1


def test_config_has_location_name():
    """Location name should be Jupiter FL"""
    assert Config.LOCATION_NAME == "Jupiter, FL"


def test_config_has_cache_refresh_hours():
    """Cache refresh interval should be configurable"""
    assert Config.CACHE_REFRESH_HOURS >= 1
    assert Config.CACHE_REFRESH_HOURS <= 24
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_config.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app'"

**Step 3: Create app directory and config module**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/__init__.py`:

```python
# ABOUTME: Main application package for Can I Fucking Downwind Today
# ABOUTME: Contains weather fetching, scoring, UI, and caching modules
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/config.py`:

```python
# ABOUTME: Application configuration including location coordinates and API settings
# ABOUTME: Centralized config to make future multi-location support easy

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # Location: Jupiter, FL (Juno Beach to Carlin Park downwind run)
    LOCATION_NAME = "Jupiter, FL"
    LOCATION_LAT = 26.9
    LOCATION_LON = -80.1

    # Jupiter-specific optimal conditions
    OPTIMAL_WIND_DIRECTIONS = ["E", "ESE", "SE"]  # East to Southeast
    OPTIMAL_WIND_MIN = 15  # knots
    OPTIMAL_WIND_MAX = 25  # knots
    OPTIMAL_WAVE_MIN = 2   # feet
    OPTIMAL_WAVE_MAX = 4   # feet

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Caching
    CACHE_REFRESH_HOURS = int(os.getenv("CACHE_REFRESH_HOURS", "2"))
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/test_config.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/__init__.py app/config.py tests/test_config.py
git commit -m "feat: add configuration module with Jupiter FL coordinates"
```

---

## Task 3: Weather Data Models

**Files:**
- Create: `app/weather/__init__.py`
- Create: `app/weather/models.py`
- Create: `tests/weather/test_models.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/weather/__init__.py`:

```python
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/weather/test_models.py`:

```python
# ABOUTME: Tests for weather data models and structures
# ABOUTME: Validates WeatherConditions data structure and defaults

from app.weather.models import WeatherConditions


def test_weather_conditions_creates_with_all_fields():
    """WeatherConditions should store all required fields"""
    conditions = WeatherConditions(
        wind_speed_kts=18.5,
        wind_direction="ESE",
        wave_height_ft=3.2,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    assert conditions.wind_speed_kts == 18.5
    assert conditions.wind_direction == "ESE"
    assert conditions.wave_height_ft == 3.2
    assert conditions.swell_direction == "S"
    assert conditions.timestamp == "2025-11-26T14:30:00"


def test_weather_conditions_has_string_representation():
    """WeatherConditions should have readable string representation"""
    conditions = WeatherConditions(
        wind_speed_kts=18.5,
        wind_direction="ESE",
        wave_height_ft=3.2,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    result = str(conditions)
    assert "18.5" in result
    assert "ESE" in result
    assert "3.2" in result
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/weather/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.weather'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/weather/__init__.py`:

```python
# ABOUTME: Weather data fetching and parsing module
# ABOUTME: Handles API calls to NOAA, OpenWeatherMap and data normalization
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/weather/models.py`:

```python
# ABOUTME: Data models for weather conditions and forecasts
# ABOUTME: Provides structured representation of wind, waves, and swell data

from dataclasses import dataclass


@dataclass
class WeatherConditions:
    """Raw weather conditions from APIs"""
    wind_speed_kts: float
    wind_direction: str
    wave_height_ft: float
    swell_direction: str
    timestamp: str

    def __str__(self) -> str:
        return (
            f"Wind: {self.wind_speed_kts}kts {self.wind_direction}, "
            f"Waves: {self.wave_height_ft}ft, "
            f"Swell: {self.swell_direction}"
        )
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/weather/test_models.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/weather/__init__.py app/weather/models.py tests/weather/__init__.py tests/weather/test_models.py
git commit -m "feat: add weather data models"
```

---

## Task 4: NOAA Weather Fetcher

**Files:**
- Create: `app/weather/sources.py`
- Create: `tests/weather/test_sources.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/weather/test_sources.py`:

```python
# ABOUTME: Tests for weather API source clients (NOAA, OpenWeatherMap)
# ABOUTME: Uses mocked responses to avoid real API calls in tests

from unittest.mock import Mock, patch
from app.weather.sources import NOAAClient
from app.weather.models import WeatherConditions


def test_noaa_client_fetches_conditions():
    """NOAAClient should fetch and parse NOAA data"""
    mock_response = {
        "properties": {
            "periods": [
                {
                    "windSpeed": "15 to 20 mph",
                    "windDirection": "ESE",
                    "detailedForecast": "Seas 2 to 3 ft"
                }
            ]
        }
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200

        client = NOAAClient()
        result = client.fetch_conditions(26.9, -80.1)

        assert isinstance(result, WeatherConditions)
        assert result.wind_speed_kts > 0
        assert result.wind_direction == "ESE"
        assert result.wave_height_ft > 0


def test_noaa_client_converts_mph_to_knots():
    """NOAAClient should convert wind speed from mph to knots"""
    mock_response = {
        "properties": {
            "periods": [
                {
                    "windSpeed": "17 mph",
                    "windDirection": "E",
                    "detailedForecast": "Seas 2 ft"
                }
            ]
        }
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200

        client = NOAAClient()
        result = client.fetch_conditions(26.9, -80.1)

        # 17 mph ≈ 14.8 knots
        assert 14 <= result.wind_speed_kts <= 15
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/weather/test_sources.py -v
```

Expected: FAIL with "ImportError: cannot import name 'NOAAClient'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/weather/sources.py`:

```python
# ABOUTME: API client implementations for weather data sources
# ABOUTME: Handles NOAA and OpenWeatherMap API calls with proper error handling

import requests
import re
from datetime import datetime
from app.weather.models import WeatherConditions


class NOAAClient:
    """Client for fetching weather data from NOAA API"""

    BASE_URL = "https://api.weather.gov"

    def fetch_conditions(self, lat: float, lon: float) -> WeatherConditions:
        """
        Fetch current conditions from NOAA for given coordinates

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            WeatherConditions with parsed data
        """
        # Get grid point for coordinates
        point_url = f"{self.BASE_URL}/points/{lat},{lon}"
        point_response = requests.get(point_url)
        point_response.raise_for_status()
        point_data = point_response.json()

        # Get forecast
        forecast_url = point_data["properties"]["forecast"]
        forecast_response = requests.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()

        # Parse first period (current conditions)
        period = forecast_data["properties"]["periods"][0]

        # Extract wind speed (convert mph to knots: 1 mph = 0.868976 knots)
        wind_speed_str = period["windSpeed"]
        wind_speed_mph = self._parse_wind_speed(wind_speed_str)
        wind_speed_kts = wind_speed_mph * 0.868976

        # Extract wave height from detailed forecast
        wave_height_ft = self._parse_wave_height(period.get("detailedForecast", ""))

        return WeatherConditions(
            wind_speed_kts=wind_speed_kts,
            wind_direction=period["windDirection"],
            wave_height_ft=wave_height_ft,
            swell_direction=period["windDirection"],  # Approximate for now
            timestamp=datetime.now().isoformat()
        )

    def _parse_wind_speed(self, wind_str: str) -> float:
        """Parse wind speed from NOAA format like '15 to 20 mph' or '17 mph'"""
        # Extract numbers
        numbers = re.findall(r'\d+', wind_str)
        if len(numbers) >= 2:
            # Take average of range
            return (float(numbers[0]) + float(numbers[1])) / 2
        elif len(numbers) == 1:
            return float(numbers[0])
        return 0.0

    def _parse_wave_height(self, text: str) -> float:
        """Parse wave height from text like 'Seas 2 to 3 ft'"""
        match = re.search(r'[Ss]eas?\s+(\d+)(?:\s+to\s+(\d+))?\s*ft', text)
        if match:
            if match.group(2):
                # Average of range
                return (float(match.group(1)) + float(match.group(2))) / 2
            return float(match.group(1))
        return 0.0
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/weather/test_sources.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/weather/sources.py tests/weather/test_sources.py
git commit -m "feat: add NOAA weather API client"
```

---

## Task 5: Weather Fetcher Orchestrator

**Files:**
- Create: `app/weather/fetcher.py`
- Create: `tests/weather/test_fetcher.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/weather/test_fetcher.py`:

```python
# ABOUTME: Tests for weather fetcher orchestration logic
# ABOUTME: Validates combining multiple API sources and fallback behavior

from unittest.mock import Mock, patch
from app.weather.fetcher import WeatherFetcher
from app.weather.models import WeatherConditions


def test_weather_fetcher_uses_noaa_as_primary():
    """WeatherFetcher should try NOAA first"""
    mock_conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="ESE",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    with patch('app.weather.fetcher.NOAAClient') as mock_noaa:
        mock_noaa.return_value.fetch_conditions.return_value = mock_conditions

        fetcher = WeatherFetcher()
        result = fetcher.fetch_current_conditions(26.9, -80.1)

        assert result == mock_conditions
        mock_noaa.return_value.fetch_conditions.assert_called_once_with(26.9, -80.1)


def test_weather_fetcher_handles_noaa_failure():
    """WeatherFetcher should handle NOAA API failures gracefully"""
    with patch('app.weather.fetcher.NOAAClient') as mock_noaa:
        mock_noaa.return_value.fetch_conditions.side_effect = Exception("NOAA API down")

        fetcher = WeatherFetcher()
        result = fetcher.fetch_current_conditions(26.9, -80.1)

        # Should return None on failure (we'll add fallback sources later)
        assert result is None
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/weather/test_fetcher.py -v
```

Expected: FAIL with "ImportError: cannot import name 'WeatherFetcher'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/weather/fetcher.py`:

```python
# ABOUTME: Orchestrates weather data fetching from multiple sources
# ABOUTME: Handles primary/fallback API logic and error recovery

from typing import Optional
from app.weather.sources import NOAAClient
from app.weather.models import WeatherConditions


class WeatherFetcher:
    """Orchestrates weather data fetching from multiple sources"""

    def __init__(self):
        self.noaa_client = NOAAClient()

    def fetch_current_conditions(self, lat: float, lon: float) -> Optional[WeatherConditions]:
        """
        Fetch current weather conditions for given coordinates

        Tries NOAA first, falls back to other sources if needed

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            WeatherConditions or None if all sources fail
        """
        try:
            return self.noaa_client.fetch_conditions(lat, lon)
        except Exception as e:
            print(f"NOAA fetch failed: {e}")
            # TODO: Add fallback sources (OpenWeatherMap, etc.)
            return None
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/weather/test_fetcher.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/weather/fetcher.py tests/weather/test_fetcher.py
git commit -m "feat: add weather fetcher orchestrator"
```

---

## Task 6: Scoring Calculator - Basic Structure

**Files:**
- Create: `app/scoring/__init__.py`
- Create: `app/scoring/models.py`
- Create: `tests/scoring/test_models.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/scoring/__init__.py`:

```python
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/scoring/test_models.py`:

```python
# ABOUTME: Tests for scoring models and rating structures
# ABOUTME: Validates ConditionRating data structure and rating ranges

from app.scoring.models import ConditionRating


def test_condition_rating_stores_all_fields():
    """ConditionRating should store rating, mode, and description"""
    rating = ConditionRating(
        score=7,
        mode="sup",
        description="Decent conditions, get out there!"
    )

    assert rating.score == 7
    assert rating.mode == "sup"
    assert rating.description == "Decent conditions, get out there!"


def test_condition_rating_validates_score_range():
    """ConditionRating score should be 1-10"""
    # Valid scores
    rating = ConditionRating(score=1, mode="sup", description="test")
    assert rating.score == 1

    rating = ConditionRating(score=10, mode="sup", description="test")
    assert rating.score == 10

    # Invalid scores should raise
    try:
        ConditionRating(score=0, mode="sup", description="test")
        assert False, "Should raise ValueError for score < 1"
    except ValueError:
        pass

    try:
        ConditionRating(score=11, mode="sup", description="test")
        assert False, "Should raise ValueError for score > 10"
    except ValueError:
        pass
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/scoring/test_models.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.scoring'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/scoring/__init__.py`:

```python
# ABOUTME: Scoring and rating calculation module
# ABOUTME: Converts weather conditions into 1-10 ratings for SUP and parawing
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/scoring/models.py`:

```python
# ABOUTME: Data models for condition ratings and recommendations
# ABOUTME: Provides structured representation of scores and foil setups

from dataclasses import dataclass


@dataclass
class ConditionRating:
    """Rating for current conditions"""
    score: int  # 1-10
    mode: str   # "sup" or "parawing"
    description: str  # Snarky description from LLM

    def __post_init__(self):
        if not 1 <= self.score <= 10:
            raise ValueError(f"Score must be 1-10, got {self.score}")
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/scoring/test_models.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/scoring/__init__.py app/scoring/models.py tests/scoring/__init__.py tests/scoring/test_models.py
git commit -m "feat: add scoring models with validation"
```

---

## Task 7: SUP Foil Scoring Logic

**Files:**
- Create: `app/scoring/calculator.py`
- Create: `tests/scoring/test_calculator.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/scoring/test_calculator.py`:

```python
# ABOUTME: Tests for scoring calculation logic
# ABOUTME: Validates SUP and parawing rating algorithms with various conditions

from app.scoring.calculator import ScoreCalculator
from app.weather.models import WeatherConditions


def test_perfect_sup_conditions_get_high_score():
    """Perfect SUP conditions (18kt ESE, 3ft waves) should score 8-10"""
    conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="ESE",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 8 <= score <= 10


def test_marginal_sup_conditions_get_medium_score():
    """Marginal SUP conditions (12kt, 1.5ft) should score 5-7"""
    conditions = WeatherConditions(
        wind_speed_kts=12.0,
        wind_direction="E",
        wave_height_ft=1.5,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 5 <= score <= 7


def test_small_sup_conditions_get_low_score():
    """Small SUP conditions (8kt, 1ft) should score 3-5"""
    conditions = WeatherConditions(
        wind_speed_kts=8.0,
        wind_direction="ESE",
        wave_height_ft=1.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 3 <= score <= 5


def test_terrible_sup_conditions_get_very_low_score():
    """Terrible SUP conditions (5kt, flat) should score 1-2"""
    conditions = WeatherConditions(
        wind_speed_kts=5.0,
        wind_direction="W",  # Wrong direction
        wave_height_ft=0.5,
        swell_direction="N",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 1 <= score <= 2


def test_wrong_wind_direction_lowers_score():
    """Wrong wind direction should significantly lower score"""
    good_direction = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="ESE",  # Optimal
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    bad_direction = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="W",  # Bad
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    good_score = calculator.calculate_sup_score(good_direction)
    bad_score = calculator.calculate_sup_score(bad_direction)

    assert good_score > bad_score + 3
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/scoring/test_calculator.py -v
```

Expected: FAIL with "ImportError: cannot import name 'ScoreCalculator'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/scoring/calculator.py`:

```python
# ABOUTME: Core scoring calculation logic for SUP and parawing modes
# ABOUTME: Converts weather conditions into 1-10 ratings using location-specific rules

from app.weather.models import WeatherConditions
from app.config import Config


class ScoreCalculator:
    """Calculates 1-10 ratings for downwind conditions"""

    def calculate_sup_score(self, conditions: WeatherConditions) -> int:
        """
        Calculate SUP foil score (1-10) based on conditions

        Scoring factors:
        - Wind speed (optimal: 15-25kt)
        - Wind direction (optimal: E, ESE, SE)
        - Wave height (optimal: 2-4ft)

        Args:
            conditions: Current weather conditions

        Returns:
            Score from 1-10
        """
        score = 5.0  # Start neutral

        # Wind speed scoring
        wind = conditions.wind_speed_kts
        if Config.OPTIMAL_WIND_MIN <= wind <= Config.OPTIMAL_WIND_MAX:
            score += 3  # Perfect wind
        elif 12 <= wind < Config.OPTIMAL_WIND_MIN:
            score += 1.5  # Marginal
        elif 8 <= wind < 12:
            score += 0.5  # Small but rideable
        elif wind < 8:
            score -= 2  # Too light
        elif wind > Config.OPTIMAL_WIND_MAX:
            score -= 1  # Too strong

        # Wind direction scoring
        if conditions.wind_direction in Config.OPTIMAL_WIND_DIRECTIONS:
            score += 2  # Perfect direction
        elif conditions.wind_direction in ["ENE", "SSE"]:
            score += 0.5  # Okay direction
        else:
            score -= 2  # Wrong direction

        # Wave height scoring
        waves = conditions.wave_height_ft
        if Config.OPTIMAL_WAVE_MIN <= waves <= Config.OPTIMAL_WAVE_MAX:
            score += 2  # Perfect waves
        elif 1.5 <= waves < Config.OPTIMAL_WAVE_MIN:
            score += 0.5  # Small but rideable
        elif 1 <= waves < 1.5:
            score -= 0.5  # Very small
        elif waves < 1:
            score -= 1.5  # Too flat
        elif waves > Config.OPTIMAL_WAVE_MAX:
            score -= 1  # Too big

        # Clamp to 1-10
        return max(1, min(10, int(round(score))))
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/scoring/test_calculator.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/scoring/calculator.py tests/scoring/test_calculator.py
git commit -m "feat: add SUP foil scoring logic"
```

---

## Task 8: Parawing Scoring Logic

**Files:**
- Modify: `app/scoring/calculator.py`
- Modify: `tests/scoring/test_calculator.py`

**Step 1: Write the failing test**

Add to `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/scoring/test_calculator.py`:

```python
def test_parawing_requires_more_wind_than_sup():
    """Parawing needs consistent 15kt+ wind"""
    # Conditions that are okay for SUP but bad for parawing
    conditions = WeatherConditions(
        wind_speed_kts=12.0,
        wind_direction="ESE",
        wave_height_ft=2.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    sup_score = calculator.calculate_sup_score(conditions)
    parawing_score = calculator.calculate_parawing_score(conditions)

    # SUP should be rideable (5+), parawing should be poor (3 or less)
    assert sup_score >= 5
    assert parawing_score <= 3


def test_parawing_good_conditions_with_strong_wind():
    """Parawing with 18kt+ wind should score well"""
    conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="ESE",
        wave_height_ft=2.5,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_parawing_score(conditions)

    assert 7 <= score <= 10


def test_parawing_marginal_wind_tanks_score():
    """Parawing with <15kt wind should score poorly even with good waves"""
    conditions = WeatherConditions(
        wind_speed_kts=13.0,
        wind_direction="ESE",
        wave_height_ft=3.0,  # Good waves
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_parawing_score(conditions)

    assert score <= 4
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/scoring/test_calculator.py::test_parawing_requires_more_wind_than_sup -v
```

Expected: FAIL with "AttributeError: 'ScoreCalculator' object has no attribute 'calculate_parawing_score'"

**Step 3: Write minimal implementation**

Add to `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/scoring/calculator.py`:

```python
    def calculate_parawing_score(self, conditions: WeatherConditions) -> int:
        """
        Calculate parawing (trashbagger) score (1-10) based on conditions

        Parawing requires more consistent wind than SUP foil.
        Below 15kt is essentially un-rideable.

        Args:
            conditions: Current weather conditions

        Returns:
            Score from 1-10
        """
        # Start with SUP score as baseline
        score = float(self.calculate_sup_score(conditions))

        # Apply stricter wind requirements
        wind = conditions.wind_speed_kts
        if wind < 15:
            # Tank the score for insufficient wind
            score = min(score, 4)
            score -= (15 - wind) * 0.5  # Penalize heavily for low wind
        elif wind >= 18:
            # Bonus for strong consistent wind
            score += 1

        # Parawing is slightly more forgiving on wave height
        # (can ride smaller bumps with strong wind)
        if wind >= 18 and conditions.wave_height_ft >= 1.5:
            score += 0.5

        # Clamp to 1-10
        return max(1, min(10, int(round(score))))
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/scoring/test_calculator.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/scoring/calculator.py tests/scoring/test_calculator.py
git commit -m "feat: add parawing scoring logic with stricter wind requirements"
```

---

## Task 9: Foil Recommendation Logic

**Files:**
- Create: `app/scoring/foil_recommender.py`
- Create: `tests/scoring/test_foil_recommender.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/scoring/test_foil_recommender.py`:

```python
# ABOUTME: Tests for foil setup recommendation logic
# ABOUTME: Validates CODE and KT foil recommendations based on conditions

from app.scoring.foil_recommender import FoilRecommender
from app.weather.models import WeatherConditions


def test_small_conditions_recommend_large_wing():
    """Small conditions (8-14kt, 1-2ft) should recommend large wing"""
    conditions = WeatherConditions(
        wind_speed_kts=10.0,
        wind_direction="ESE",
        wave_height_ft=1.5,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    recommender = FoilRecommender()
    code_setup = recommender.recommend_code(conditions)

    assert "1250r" in code_setup
    assert "135r" in code_setup
    assert "short fuse" in code_setup


def test_normal_conditions_recommend_medium_wing():
    """Normal conditions (15+kt, 2-4ft) should recommend medium wing"""
    conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="ESE",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    recommender = FoilRecommender()
    code_setup = recommender.recommend_code(conditions)

    assert "960r" in code_setup
    assert "135r" in code_setup
    assert "short fuse" in code_setup


def test_kt_recommendations_exist():
    """KT recommendations should be provided"""
    conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="ESE",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    recommender = FoilRecommender()
    kt_setup = recommender.recommend_kt(conditions)

    assert kt_setup is not None
    assert len(kt_setup) > 0
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/scoring/test_foil_recommender.py -v
```

Expected: FAIL with "ImportError: cannot import name 'FoilRecommender'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/scoring/foil_recommender.py`:

```python
# ABOUTME: Foil setup recommendations based on current conditions
# ABOUTME: Provides CODE and KT brand equipment suggestions for wind/wave combos

from app.weather.models import WeatherConditions


class FoilRecommender:
    """Recommends foil setups based on conditions"""

    def recommend_code(self, conditions: WeatherConditions) -> str:
        """
        Recommend CODE foil setup based on conditions

        Args:
            conditions: Current weather conditions

        Returns:
            Setup string (e.g., "960r + 135r stab + short fuse")
        """
        # Small conditions: 8-14kt, 1-2ft bumps
        if conditions.wind_speed_kts < 15 and conditions.wave_height_ft < 2.5:
            return "1250r + 135r stab + short fuse"

        # Normal/good conditions: 15+kt, 2-4ft bumps
        return "960r + 135r stab + short fuse"

    def recommend_kt(self, conditions: WeatherConditions) -> str:
        """
        Recommend KT foil setup based on conditions

        Args:
            conditions: Current weather conditions

        Returns:
            Setup string
        """
        # Small conditions
        if conditions.wind_speed_kts < 15 and conditions.wave_height_ft < 2.5:
            return "Ginxu 1150 + Stabilizer M"

        # Normal/good conditions
        return "Ginxu 950 + Stabilizer M"
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/scoring/test_foil_recommender.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/scoring/foil_recommender.py tests/scoring/test_foil_recommender.py
git commit -m "feat: add foil recommendation logic for CODE and KT"
```

---

## Task 10: LLM Client Interface

**Files:**
- Create: `app/ai/__init__.py`
- Create: `app/ai/llm_client.py`
- Create: `tests/ai/test_llm_client.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/ai/__init__.py`:

```python
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/ai/test_llm_client.py`:

```python
# ABOUTME: Tests for LLM client interface (Google Gemini API)
# ABOUTME: Uses mocked responses to avoid real API calls and costs in tests

from unittest.mock import Mock, patch
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
            wind_direction="ESE",
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
            wind_direction="ESE",
            wave_height=3.0,
            swell_direction="S",
            rating=7,
            mode="sup"
        )

        # Should return fallback message on failure
        assert result is not None
        assert "error" in result.lower() or "unavailable" in result.lower()
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/ai/test_llm_client.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.ai'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/ai/__init__.py`:

```python
# ABOUTME: AI/LLM integration module for generating snarky descriptions
# ABOUTME: Handles Google Gemini API calls with proper error handling
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/ai/llm_client.py`:

```python
# ABOUTME: LLM API client for generating condition descriptions
# ABOUTME: Supports Google Gemini 2.5 Flash with fallback error handling

import google.generativeai as genai
from typing import Optional


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
            wind_direction: Wind direction (E, ESE, etc.)
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
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/ai/test_llm_client.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/ai/__init__.py app/ai/llm_client.py tests/ai/__init__.py tests/ai/test_llm_client.py
git commit -m "feat: add LLM client for snarky description generation"
```

---

## Task 11: Cache Manager

**Files:**
- Create: `app/cache/__init__.py`
- Create: `app/cache/manager.py`
- Create: `tests/cache/test_manager.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/cache/__init__.py`:

```python
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/cache/test_manager.py`:

```python
# ABOUTME: Tests for cache management and refresh logic
# ABOUTME: Validates in-memory caching and expiration behavior

from datetime import datetime, timedelta
from app.cache.manager import CacheManager
from app.scoring.models import ConditionRating


def test_cache_stores_and_retrieves_rating():
    """CacheManager should store and retrieve ratings"""
    cache = CacheManager(refresh_hours=2)
    rating = ConditionRating(score=7, mode="sup", description="Test")

    cache.set_rating("sup", rating)
    result = cache.get_rating("sup")

    assert result == rating


def test_cache_returns_none_when_empty():
    """CacheManager should return None for missing keys"""
    cache = CacheManager(refresh_hours=2)
    result = cache.get_rating("sup")

    assert result is None


def test_cache_expires_after_refresh_period():
    """CacheManager should expire cache after refresh hours"""
    cache = CacheManager(refresh_hours=2)
    rating = ConditionRating(score=7, mode="sup", description="Test")

    cache.set_rating("sup", rating)

    # Manually expire the cache by setting old timestamp
    cache._cache["sup"]["timestamp"] = datetime.now() - timedelta(hours=3)

    result = cache.get_rating("sup")
    assert result is None  # Should be expired


def test_cache_not_expired_within_refresh_period():
    """CacheManager should return cached value within refresh period"""
    cache = CacheManager(refresh_hours=2)
    rating = ConditionRating(score=7, mode="sup", description="Test")

    cache.set_rating("sup", rating)

    # Set timestamp to 1 hour ago (within 2 hour window)
    cache._cache["sup"]["timestamp"] = datetime.now() - timedelta(hours=1)

    result = cache.get_rating("sup")
    assert result == rating  # Should still be valid
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/cache/test_manager.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.cache'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/cache/__init__.py`:

```python
# ABOUTME: Caching module for weather data and ratings
# ABOUTME: Provides in-memory cache with time-based expiration
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/cache/manager.py`:

```python
# ABOUTME: Cache management with time-based expiration
# ABOUTME: Stores ratings and weather data to minimize API calls

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.scoring.models import ConditionRating


class CacheManager:
    """Manages cached ratings with time-based expiration"""

    def __init__(self, refresh_hours: int = 2):
        self.refresh_hours = refresh_hours
        self._cache: Dict[str, Dict[str, Any]] = {}

    def set_rating(self, mode: str, rating: ConditionRating) -> None:
        """
        Store rating in cache

        Args:
            mode: "sup" or "parawing"
            rating: ConditionRating to cache
        """
        self._cache[mode] = {
            "rating": rating,
            "timestamp": datetime.now()
        }

    def get_rating(self, mode: str) -> Optional[ConditionRating]:
        """
        Retrieve rating from cache if not expired

        Args:
            mode: "sup" or "parawing"

        Returns:
            Cached ConditionRating or None if expired/missing
        """
        if mode not in self._cache:
            return None

        cached = self._cache[mode]
        age = datetime.now() - cached["timestamp"]

        if age > timedelta(hours=self.refresh_hours):
            # Expired
            del self._cache[mode]
            return None

        return cached["rating"]

    def is_expired(self, mode: str) -> bool:
        """Check if cache is expired for given mode"""
        return self.get_rating(mode) is None
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/cache/test_manager.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/cache/__init__.py app/cache/manager.py tests/cache/__init__.py tests/cache/test_manager.py
git commit -m "feat: add cache manager with time-based expiration"
```

---

## Task 12: Main Application Orchestrator

**Files:**
- Create: `app/orchestrator.py`
- Create: `tests/test_orchestrator.py`

**Step 1: Write the failing test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/test_orchestrator.py`:

```python
# ABOUTME: Tests for main application orchestrator
# ABOUTME: Validates end-to-end flow from weather fetch to rating generation

from unittest.mock import Mock, patch
from app.orchestrator import AppOrchestrator
from app.weather.models import WeatherConditions
from app.scoring.models import ConditionRating


def test_orchestrator_fetches_and_caches_rating():
    """Orchestrator should fetch weather, calculate rating, generate description, and cache"""
    mock_conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="ESE",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher, \
         patch('app.orchestrator.ScoreCalculator') as mock_calculator, \
         patch('app.orchestrator.LLMClient') as mock_llm, \
         patch('app.orchestrator.FoilRecommender') as mock_recommender:

        mock_fetcher.return_value.fetch_current_conditions.return_value = mock_conditions
        mock_calculator.return_value.calculate_sup_score.return_value = 8
        mock_llm.return_value.generate_description.return_value = "Fuck yeah, send it!"
        mock_recommender.return_value.recommend_code.return_value = "960r + 135r + short fuse"
        mock_recommender.return_value.recommend_kt.return_value = "Ginxu 950 + Stab M"

        orchestrator = AppOrchestrator(api_key="test_key")
        rating = orchestrator.get_sup_rating()

        assert isinstance(rating, ConditionRating)
        assert rating.score == 8
        assert rating.mode == "sup"
        assert "send it" in rating.description.lower()


def test_orchestrator_uses_cached_rating():
    """Orchestrator should return cached rating without fetching weather"""
    with patch('app.orchestrator.WeatherFetcher') as mock_fetcher:
        orchestrator = AppOrchestrator(api_key="test_key")

        # Pre-cache a rating
        cached_rating = ConditionRating(score=7, mode="sup", description="Cached")
        orchestrator.cache.set_rating("sup", cached_rating)

        result = orchestrator.get_sup_rating()

        # Should return cached rating without calling weather API
        assert result == cached_rating
        mock_fetcher.return_value.fetch_current_conditions.assert_not_called()
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_orchestrator.py -v
```

Expected: FAIL with "ImportError: cannot import name 'AppOrchestrator'"

**Step 3: Write minimal implementation**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/orchestrator.py`:

```python
# ABOUTME: Main application orchestrator coordinating all components
# ABOUTME: Handles weather fetch, scoring, LLM generation, caching, and foil recommendations

from typing import Optional
from app.config import Config
from app.weather.fetcher import WeatherFetcher
from app.scoring.calculator import ScoreCalculator
from app.scoring.foil_recommender import FoilRecommender
from app.scoring.models import ConditionRating
from app.ai.llm_client import LLMClient
from app.cache.manager import CacheManager


class AppOrchestrator:
    """Orchestrates all app components to generate ratings"""

    def __init__(self, api_key: str):
        self.weather_fetcher = WeatherFetcher()
        self.score_calculator = ScoreCalculator()
        self.foil_recommender = FoilRecommender()
        self.llm_client = LLMClient(api_key=api_key)
        self.cache = CacheManager(refresh_hours=Config.CACHE_REFRESH_HOURS)

    def get_sup_rating(self) -> Optional[ConditionRating]:
        """
        Get SUP foil rating (cached or fresh)

        Returns:
            ConditionRating or None if weather unavailable
        """
        # Check cache first
        cached = self.cache.get_rating("sup")
        if cached:
            return cached

        # Fetch fresh data
        return self._generate_rating("sup")

    def get_parawing_rating(self) -> Optional[ConditionRating]:
        """
        Get parawing rating (cached or fresh)

        Returns:
            ConditionRating or None if weather unavailable
        """
        # Check cache first
        cached = self.cache.get_rating("parawing")
        if cached:
            return cached

        # Fetch fresh data
        return self._generate_rating("parawing")

    def get_foil_recommendations(self) -> dict:
        """
        Get foil recommendations for current conditions

        Returns:
            Dict with CODE and KT recommendations
        """
        conditions = self.weather_fetcher.fetch_current_conditions(
            Config.LOCATION_LAT,
            Config.LOCATION_LON
        )

        if not conditions:
            return {"code": "Weather unavailable", "kt": "Weather unavailable"}

        return {
            "code": self.foil_recommender.recommend_code(conditions),
            "kt": self.foil_recommender.recommend_kt(conditions)
        }

    def _generate_rating(self, mode: str) -> Optional[ConditionRating]:
        """Generate fresh rating for given mode"""
        # Fetch weather
        conditions = self.weather_fetcher.fetch_current_conditions(
            Config.LOCATION_LAT,
            Config.LOCATION_LON
        )

        if not conditions:
            return None

        # Calculate score
        if mode == "sup":
            score = self.score_calculator.calculate_sup_score(conditions)
        else:
            score = self.score_calculator.calculate_parawing_score(conditions)

        # Generate snarky description
        description = self.llm_client.generate_description(
            wind_speed=conditions.wind_speed_kts,
            wind_direction=conditions.wind_direction,
            wave_height=conditions.wave_height_ft,
            swell_direction=conditions.swell_direction,
            rating=score,
            mode=mode
        )

        # Create rating
        rating = ConditionRating(score=score, mode=mode, description=description)

        # Cache it
        self.cache.set_rating(mode, rating)

        return rating
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/test_orchestrator.py -v
```

Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add main application orchestrator"
```

---

## Task 13: NiceGUI User Interface - Basic Structure

**Files:**
- Create: `app/main.py`

**Step 1: Create minimal working UI**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/main.py`:

```python
# ABOUTME: Main NiceGUI web application entry point
# ABOUTME: Provides simple 90s-style UI for downwind condition ratings

from nicegui import ui
from app.config import Config
from app.orchestrator import AppOrchestrator


# Initialize orchestrator
orchestrator = AppOrchestrator(api_key=Config.GEMINI_API_KEY)


@ui.page('/')
def index():
    """Main page"""
    # 90s aesthetic: white background, black text
    ui.colors(primary='#000000', secondary='#000000')

    with ui.column().classes('w-full items-center'):
        # Title
        ui.label('CAN I FUCKING DOWNWIND TODAY').classes('text-4xl font-bold mt-8')

        # Toggle between SUP and Parawing
        toggle = ui.toggle(['SUP Foil', 'Trashbaggers'], value='SUP Foil').classes('mt-8')

        # Rating display (will update based on toggle)
        rating_label = ui.label('').classes('text-8xl font-bold mt-8')
        description_label = ui.label('').classes('text-xl mt-4 max-w-2xl text-center')

        # Foil recommendations
        ui.label('--- FOIL RECOMMENDATIONS ---').classes('text-2xl mt-8')
        code_rec = ui.label('').classes('text-lg mt-2')
        kt_rec = ui.label('').classes('text-lg mt-1')

        # Last updated timestamp
        timestamp_label = ui.label('').classes('text-sm mt-8 text-gray-600')

        def update_display():
            """Update display based on toggle selection"""
            if toggle.value == 'SUP Foil':
                rating = orchestrator.get_sup_rating()
            else:
                rating = orchestrator.get_parawing_rating()

            if rating:
                rating_label.text = f'{rating.score}/10'
                description_label.text = rating.description
            else:
                rating_label.text = 'N/A'
                description_label.text = 'Weather data unavailable'

            # Update foil recommendations
            recommendations = orchestrator.get_foil_recommendations()
            code_rec.text = f"CODE: {recommendations['code']}"
            kt_rec.text = f"KT: {recommendations['kt']}"

            # Update timestamp
            from datetime import datetime
            timestamp_label.text = f"Last updated: {datetime.now().strftime('%I:%M %p')}"

        # Update on toggle change
        toggle.on_value_change(lambda: update_display())

        # Initial load
        update_display()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Can I Fucking Downwind Today', port=8080)
```

**Step 2: Run the app manually to test**

Run:
```bash
python app/main.py
```

Expected: App starts on http://localhost:8080, shows UI (may show errors if NOAA API fails, that's okay for now)

**Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add basic NiceGUI user interface"
```

---

## Task 14: UI Styling - 90s Aesthetic

**Files:**
- Modify: `app/main.py`

**Step 1: Add proper 90s styling**

Replace the content of `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/main.py`:

```python
# ABOUTME: Main NiceGUI web application entry point
# ABOUTME: Provides simple 90s-style UI for downwind condition ratings

from nicegui import ui
from app.config import Config
from app.orchestrator import AppOrchestrator


# Initialize orchestrator
orchestrator = AppOrchestrator(api_key=Config.GEMINI_API_KEY)


@ui.page('/')
def index():
    """Main page with 90s aesthetic"""

    # Apply 90s styling
    ui.add_head_html("""
    <style>
        body {
            background-color: #FFFFFF;
            color: #000000;
            font-family: Arial, sans-serif;
        }
        .title {
            font-size: 48px;
            font-weight: bold;
            margin-top: 30px;
            text-align: center;
        }
        .rating {
            font-size: 120px;
            font-weight: bold;
            margin-top: 30px;
            text-align: center;
        }
        .description {
            font-size: 18px;
            margin-top: 20px;
            max-width: 700px;
            text-align: center;
            line-height: 1.6;
        }
        .toggle-container {
            margin-top: 30px;
            text-align: center;
        }
        .recommendations {
            margin-top: 40px;
            text-align: center;
        }
        .rec-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        .rec-item {
            font-size: 16px;
            margin: 5px 0;
        }
        .timestamp {
            margin-top: 30px;
            font-size: 12px;
            color: #666666;
            text-align: center;
        }
    </style>
    """)

    with ui.column().classes('w-full items-center'):
        # Title
        ui.html('<div class="title">CAN I FUCKING DOWNWIND TODAY</div>')

        # Toggle between SUP and Parawing
        with ui.row().classes('toggle-container'):
            toggle = ui.toggle(
                ['SUP Foil', 'Trashbaggers'],
                value='SUP Foil'
            ).style('border: 2px solid #000000; padding: 5px;')

        # Rating display (will update based on toggle)
        rating_label = ui.html('<div class="rating">--/10</div>')
        description_label = ui.html('<div class="description">Loading conditions...</div>')

        # Foil recommendations
        with ui.column().classes('recommendations'):
            ui.html('<div class="rec-title">--- FOIL RECOMMENDATIONS ---</div>')
            code_rec = ui.html('<div class="rec-item">CODE: Loading...</div>')
            kt_rec = ui.html('<div class="rec-item">KT: Loading...</div>')

        # Last updated timestamp
        timestamp_label = ui.html('<div class="timestamp">Last updated: --</div>')

        def update_display():
            """Update display based on toggle selection"""
            mode = 'sup' if toggle.value == 'SUP Foil' else 'parawing'

            if mode == 'sup':
                rating = orchestrator.get_sup_rating()
            else:
                rating = orchestrator.get_parawing_rating()

            if rating:
                rating_label.content = f'<div class="rating">{rating.score}/10</div>'
                description_label.content = f'<div class="description">{rating.description}</div>'
            else:
                rating_label.content = '<div class="rating">N/A</div>'
                description_label.content = '<div class="description">Weather data unavailable. Try again later.</div>'

            # Update foil recommendations
            recommendations = orchestrator.get_foil_recommendations()
            code_rec.content = f'<div class="rec-item">CODE: {recommendations["code"]}</div>'
            kt_rec.content = f'<div class="rec-item">KT: {recommendations["kt"]}</div>'

            # Update timestamp
            from datetime import datetime
            timestamp_label.content = f'<div class="timestamp">Last updated: {datetime.now().strftime("%I:%M %p")}</div>'

        # Update on toggle change
        toggle.on_value_change(lambda: update_display())

        # Initial load
        ui.timer(0.1, update_display, once=True)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title='Can I Fucking Downwind Today', port=8080)
```

**Step 2: Test the styling**

Run:
```bash
python app/main.py
```

Expected: Clean 90s-style interface with proper spacing and fonts

**Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add 90s aesthetic styling to UI"
```

---

## Task 15: Environment Setup Documentation

**Files:**
- Create: `README.md`

**Step 1: Write comprehensive README**

Replace `/Users/lanekubicki/tmp/canifuckingdownwindtoday/README.md`:

```markdown
# Can I Fucking Downwind Today

A snarky web app that tells you whether today is a good day for downwind SUP foiling or parawing in Jupiter, FL.

## Features

- **1-10 Condition Rating**: Objective scoring based on wind speed, direction, wave height, and swell
- **Snarky AI Descriptions**: Profanity-laden commentary that roasts your skills while explaining conditions
- **SUP vs Parawing Toggle**: Different ratings for paddle downwinders vs parawing/lowkite
- **Foil Recommendations**: Dynamic equipment suggestions for CODE and KT foils based on conditions
- **90s Aesthetic**: Simple, fast, brutally minimal UI

## Setup

### Prerequisites

- Python 3.10+
- Google Gemini API key (free tier)

### Installation

1. Clone the repo:
```bash
git clone <repo-url>
cd canifuckingdownwindtoday
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Add your Google Gemini API key to `.env`:
```
GEMINI_API_KEY=your_actual_key_here
CACHE_REFRESH_HOURS=2
```

### Running the App

```bash
python app/main.py
```

Visit http://localhost:8080

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## Architecture

- **Weather Fetching**: NOAA API (primary) with fallback support
- **Scoring**: Deterministic algorithm based on Jupiter, FL conditions
- **AI Descriptions**: Google Gemini API generates snarky commentary
- **Caching**: 2-hour cache to minimize API calls and maximize speed
- **UI**: NiceGUI with 90s HTML aesthetic

## Project Structure

```
app/
├── main.py              # NiceGUI app entry point
├── config.py            # Configuration (location, API keys)
├── orchestrator.py      # Main app orchestrator
├── weather/
│   ├── fetcher.py       # Weather data orchestration
│   ├── sources.py       # API clients (NOAA, etc.)
│   └── models.py        # Weather data models
├── scoring/
│   ├── calculator.py    # Rating calculation logic
│   ├── foil_recommender.py  # Equipment recommendations
│   └── models.py        # Rating data models
├── ai/
│   └── llm_client.py    # Gemini API client
└── cache/
    └── manager.py       # Cache management

tests/
└── (mirrors app structure)
```

## Future Enhancements

- Seaweed detection (scraping local surf reports)
- Multi-location support
- Historical trends and forecasts
- User preferences
- API/embeddable widget

## License

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README"
```

---

## Task 16: Integration Testing

**Files:**
- Create: `tests/integration/test_end_to_end.py`

**Step 1: Write integration test**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/integration/__init__.py`:

```python
```

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/tests/integration/test_end_to_end.py`:

```python
# ABOUTME: End-to-end integration tests with mocked external APIs
# ABOUTME: Validates full flow from weather fetch to UI rendering

import pytest
from unittest.mock import Mock, patch
from app.orchestrator import AppOrchestrator


@pytest.mark.integration
def test_full_sup_rating_flow():
    """Test complete flow: fetch weather -> calculate score -> generate description"""
    mock_noaa_response = {
        "properties": {
            "periods": [{
                "windSpeed": "18 mph",
                "windDirection": "ESE",
                "detailedForecast": "Seas 2 to 3 ft"
            }]
        }
    }

    mock_llm_response = Mock()
    mock_llm_response.text = "Perfect conditions, now don't fuck it up."

    with patch('requests.get') as mock_get, \
         patch('google.generativeai.GenerativeModel') as mock_gemini:

        # Mock NOAA API
        mock_get.return_value.json.return_value = mock_noaa_response
        mock_get.return_value.status_code = 200

        # Mock Gemini API
        mock_gemini.return_value.generate_content.return_value = mock_llm_response

        # Run full flow
        orchestrator = AppOrchestrator(api_key="test_key")
        rating = orchestrator.get_sup_rating()

        # Verify result
        assert rating is not None
        assert 1 <= rating.score <= 10
        assert rating.mode == "sup"
        assert len(rating.description) > 0


@pytest.mark.integration
def test_full_parawing_rating_flow():
    """Test complete flow for parawing mode"""
    mock_noaa_response = {
        "properties": {
            "periods": [{
                "windSpeed": "20 mph",
                "windDirection": "E",
                "detailedForecast": "Seas 3 ft"
            }]
        }
    }

    mock_llm_response = Mock()
    mock_llm_response.text = "Trashbagger conditions are ON POINT."

    with patch('requests.get') as mock_get, \
         patch('google.generativeai.GenerativeModel') as mock_gemini:

        mock_get.return_value.json.return_value = mock_noaa_response
        mock_get.return_value.status_code = 200
        mock_gemini.return_value.generate_content.return_value = mock_llm_response

        orchestrator = AppOrchestrator(api_key="test_key")
        rating = orchestrator.get_parawing_rating()

        assert rating is not None
        assert 1 <= rating.score <= 10
        assert rating.mode == "parawing"


@pytest.mark.integration
def test_foil_recommendations_flow():
    """Test foil recommendation generation"""
    mock_noaa_response = {
        "properties": {
            "periods": [{
                "windSpeed": "18 mph",
                "windDirection": "ESE",
                "detailedForecast": "Seas 3 ft"
            }]
        }
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = mock_noaa_response
        mock_get.return_value.status_code = 200

        orchestrator = AppOrchestrator(api_key="test_key")
        recommendations = orchestrator.get_foil_recommendations()

        assert "code" in recommendations
        assert "kt" in recommendations
        assert "960r" in recommendations["code"] or "1250r" in recommendations["code"]
```

**Step 2: Run integration tests**

Run:
```bash
pytest tests/integration/ -v -m integration
```

Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/integration/__init__.py tests/integration/test_end_to_end.py
git commit -m "test: add end-to-end integration tests"
```

---

## Task 17: Error Handling & Robustness

**Files:**
- Modify: `app/orchestrator.py`
- Modify: `app/main.py`

**Step 1: Add graceful error handling to orchestrator**

Add error handling to `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/orchestrator.py` `_generate_rating` method:

```python
    def _generate_rating(self, mode: str) -> Optional[ConditionRating]:
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

            # Generate snarky description
            try:
                description = self.llm_client.generate_description(
                    wind_speed=conditions.wind_speed_kts,
                    wind_direction=conditions.wind_direction,
                    wave_height=conditions.wave_height_ft,
                    swell_direction=conditions.swell_direction,
                    rating=score,
                    mode=mode
                )
            except Exception as e:
                print(f"LLM generation failed: {e}")
                description = self._create_fallback_description(conditions, score, mode)

            # Create rating
            rating = ConditionRating(score=score, mode=mode, description=description)

            # Cache it
            self.cache.set_rating(mode, rating)

            return rating

        except Exception as e:
            print(f"Error generating rating: {e}")
            return self._create_fallback_rating(mode, f"Error: {str(e)}")

    def _create_fallback_rating(self, mode: str, error_msg: str) -> ConditionRating:
        """Create fallback rating when things go wrong"""
        return ConditionRating(
            score=5,
            mode=mode,
            description=f"Unable to fetch conditions. {error_msg}. Check back later or just fucking send it anyway."
        )

    def _create_fallback_description(self, conditions, score: int, mode: str) -> str:
        """Create fallback description when LLM fails"""
        mode_name = "SUP foil" if mode == "sup" else "parawing"
        return (
            f"Conditions: {conditions.wind_speed_kts:.1f}kts {conditions.wind_direction}, "
            f"{conditions.wave_height_ft:.1f}ft waves. Rating: {score}/10 for {mode_name}. "
            f"LLM service is down so you're not getting the full snarky experience. "
            f"Figure it out yourself, you're advanced right?"
        )
```

**Step 2: Add error handling to UI**

Modify the `update_display` function in `/Users/lanekubicki/tmp/canifuckingdownwindtoday/app/main.py`:

```python
        def update_display():
            """Update display based on toggle selection"""
            try:
                mode = 'sup' if toggle.value == 'SUP Foil' else 'parawing'

                if mode == 'sup':
                    rating = orchestrator.get_sup_rating()
                else:
                    rating = orchestrator.get_parawing_rating()

                if rating:
                    rating_label.content = f'<div class="rating">{rating.score}/10</div>'
                    description_label.content = f'<div class="description">{rating.description}</div>'
                else:
                    rating_label.content = '<div class="rating">N/A</div>'
                    description_label.content = '<div class="description">Weather data unavailable. Try again later or just send it.</div>'

                # Update foil recommendations
                try:
                    recommendations = orchestrator.get_foil_recommendations()
                    code_rec.content = f'<div class="rec-item">CODE: {recommendations["code"]}</div>'
                    kt_rec.content = f'<div class="rec-item">KT: {recommendations["kt"]}</div>'
                except Exception as e:
                    code_rec.content = f'<div class="rec-item">CODE: Error loading</div>'
                    kt_rec.content = f'<div class="rec-item">KT: Error loading</div>'

                # Update timestamp
                from datetime import datetime
                timestamp_label.content = f'<div class="timestamp">Last updated: {datetime.now().strftime("%I:%M %p")}</div>'

            except Exception as e:
                print(f"UI update error: {e}")
                rating_label.content = '<div class="rating">ERROR</div>'
                description_label.content = f'<div class="description">Something broke. Try refreshing the page.</div>'
```

**Step 3: Commit**

```bash
git add app/orchestrator.py app/main.py
git commit -m "feat: add robust error handling to orchestrator and UI"
```

---

## Task 18: Final Testing & Verification

**Files:**
- None (running tests)

**Step 1: Run full test suite**

Run:
```bash
pytest tests/ -v
```

Expected: All tests PASS

**Step 2: Run with coverage**

Run:
```bash
pytest --cov=app --cov-report=term-missing tests/
```

Expected: High coverage (>80%)

**Step 3: Manual smoke test**

Run:
```bash
python app/main.py
```

Visit http://localhost:8080 and verify:
- Page loads
- Toggle switches between SUP and Parawing
- Rating displays (may show error if no API keys configured, that's okay)
- Foil recommendations display

**Step 4: Commit if any fixes needed**

```bash
# If you had to fix anything:
git add .
git commit -m "fix: address issues found in final testing"
```

---

## Task 19: Deployment Preparation

**Files:**
- Create: `Procfile`
- Create: `.dockerignore`
- Modify: `requirements.txt`

**Step 1: Add production requirements**

Add to `/Users/lanekubicki/tmp/canifuckingdownwindtoday/requirements.txt`:

```txt
gunicorn==21.2.0
```

**Step 2: Create Procfile for Heroku/Railway**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/Procfile`:

```
web: python app/main.py
```

**Step 3: Create .dockerignore**

Create `/Users/lanekubicki/tmp/canifuckingdownwindtoday/.dockerignore`:

```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.git/
.env
*.log
tests/
```

**Step 4: Update README with deployment instructions**

Add to `/Users/lanekubicki/tmp/canifuckingdownwindtoday/README.md` (before License section):

```markdown
## Deployment

### Heroku

```bash
heroku create canifuckingdownwindtoday
heroku config:set GEMINI_API_KEY=your_key_here
git push heroku main
```

### Railway

1. Connect your GitHub repo to Railway
2. Add environment variable: `GEMINI_API_KEY`
3. Deploy

### Fly.io

```bash
fly launch
fly secrets set GEMINI_API_KEY=your_key_here
fly deploy
```
```

**Step 5: Commit**

```bash
git add Procfile .dockerignore requirements.txt README.md
git commit -m "feat: add deployment configuration for Heroku, Railway, Fly.io"
```

---

## Task 20: Create .env and Final Verification

**Files:**
- Create: `.env` (local only, not committed)

**Step 1: Create .env with actual API key**

DIRECTOR: You need to create `.env` file manually with your actual Google Gemini API key:

```bash
cp .env.example .env
# Then edit .env and add your real API key
```

**Step 2: Run app with real API**

Run:
```bash
python app/main.py
```

Verify:
- App loads at http://localhost:8080
- Real weather data fetches
- Real ratings calculate
- Real LLM descriptions generate
- Toggle works
- Foil recommendations display

**Step 3: Final commit and done**

```bash
git status
# Ensure .env is NOT staged (should be in .gitignore)
# If everything looks good, you're done!
```

---

## Completion Checklist

- [ ] All tests passing (`pytest tests/ -v`)
- [ ] App runs locally (`python app/main.py`)
- [ ] Real API integration works (weather + Claude)
- [ ] Toggle switches between SUP and Parawing
- [ ] Foil recommendations display correctly
- [ ] 90s styling looks clean
- [ ] README is comprehensive
- [ ] Deployment configs in place
- [ ] `.env` configured but not committed

---

## Notes for Future Development

**V2 Features (Seaweed Detection):**
- Add new module: `app/seaweed/scraper.py`
- Scrape Surfline, local Jupiter surf reports
- Parse for keywords: "seaweed", "sargassum", "grass"
- If detected, reduce score by 3-5 points
- Add to scoring calculator as optional parameter

**Multi-Location Support:**
- Add location configs to `app/config.py`
- Add location dropdown to UI
- Pass location to orchestrator methods
- Use location-specific scoring rules

**Test Design Principles Applied:**
- Mock external APIs (NOAA, Claude) to avoid costs and flakiness
- Test one thing per test function
- Use descriptive test names that explain what's being tested
- Test edge cases (no wind, wrong direction, API failures)
- Integration tests verify full flow with mocked externals
- Never test mock behavior - test real logic with mocked dependencies
