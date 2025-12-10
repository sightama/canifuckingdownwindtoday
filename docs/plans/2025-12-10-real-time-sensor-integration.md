# Real-Time Sensor Data Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace inaccurate NOAA forecast data with real-time wind sensor data from the Jupiter-Juno Beach Pier WeatherFlow station, prioritizing accuracy over availability.

**Architecture:** WeatherFlow API provides real-time sensor readings (wind speed, direction, gust, lull). Split cache stores sensor data (2-3 min TTL) separately from LLM variations (15 min TTL, regenerates only when rating changes). If sensor data is stale (>5 min old) or unavailable, display "Sensor Offline" with witty persona responses instead of falling back to inaccurate forecasts.

**Tech Stack:** Python 3.11+, NiceGUI, WeatherFlow API, Google Generative AI SDK, pytest, GCP Secret Manager

---

## Implementation Status

| Task | Status | Commit |
|------|--------|--------|
| Task 1: Add WF_TOKEN to GCP Secret Manager | ⬜ TODO | |
| Task 2: Create SensorReading Model | ⬜ TODO | |
| Task 3: Create WeatherFlow SensorClient | ⬜ TODO | |
| Task 4: Update Config for Sensor Settings | ⬜ TODO | |
| Task 5: Update Scoring for Wind-Only | ⬜ TODO | |
| Task 6: Split Cache for Sensor + Variations | ⬜ TODO | |
| Task 7: Add Offline LLM Variations | ⬜ TODO | |
| Task 8: Update Orchestrator for Sensor Flow | ⬜ TODO | |
| Task 9: Update UI for Offline State | ⬜ TODO | |
| Task 10: Delete NOAA Code | ⬜ TODO | |
| Task 11: Integration Tests | ⬜ TODO | |
| Task 12: Deploy and Verify | ⬜ TODO | |

---

## Background: Why We're Doing This

**Problem:** NOAA forecast showed 5.2 kts North when actual sensor data (iKitesurf) showed 12 kts East. Users depend on accurate real-time wind for foiling decisions.

**Solution:** Use WeatherFlow API (the same data source iKitesurf uses) for the Jupiter-Juno Beach Pier station (Spot ID 453).

**Key Design Decisions:**
1. **Accuracy over availability** - Show "Sensor Offline" rather than wrong data
2. **Wind-only scoring** - No wave/swell data from sensor; design for future extension
3. **5-minute staleness threshold** - If sensor hasn't reported, something's wrong
4. **Split cache** - Sensor data (2-3 min), LLM variations (15 min, regenerate on rating change)
5. **Witty offline responses** - Personas comment on the outage

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/weather/sensor.py` | NEW: WeatherFlow API client |
| `app/weather/models.py` | Add SensorReading dataclass |
| `app/weather/sources.py` | DELETE: NOAA client (no longer needed) |
| `app/weather/fetcher.py` | DELETE: Was just NOAA pass-through |
| `app/cache/manager.py` | Split cache logic |
| `app/orchestrator.py` | New sensor flow, staleness checks |
| `app/scoring/calculator.py` | Wind-only scoring with optional wave |
| `app/ai/llm_client.py` | Offline variation generation |
| `app/main.py` | Offline state UI |
| `app/config.py` | WF_TOKEN, staleness threshold |

---

## Task 1: Add WF_TOKEN to GCP Secret Manager

**Goal:** Store the WeatherFlow API token securely using the same pattern as existing secrets.

**Files:**
- No code files modified (GCP configuration only)

### Step 1.1: Check existing secret patterns

First, look at how GEMINI_API_KEY is configured:

```bash
# See current secrets
gcloud secrets list

# See how the Cloud Run service is configured
gcloud run services describe canifuckingdownwindtoday --format="yaml" | grep -A 20 "env:"
```

### Step 1.2: Create the secret in GCP Secret Manager

```bash
# Create the secret (replace with actual token from scripts/ikitesurf_wind.py)
echo -n "c3095a0bc292a205fe1dcfe9d9f7fa60" | gcloud secrets create wf-token --data-file=-
```

### Step 1.3: Grant Cloud Run access to the secret

```bash
# Get the service account used by Cloud Run
gcloud run services describe canifuckingdownwindtoday --format="value(spec.template.spec.serviceAccountName)"

# Grant access (replace SERVICE_ACCOUNT with actual value)
gcloud secrets add-iam-policy-binding wf-token \
  --member="serviceAccount:SERVICE_ACCOUNT" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 1.4: Verify the secret is accessible

```bash
gcloud secrets versions access latest --secret=wf-token
```

Expected: The token value is printed.

### Step 1.5: Document the token refresh process

Add a comment to `app/config.py` (will be done in Task 4):

```python
# WF_TOKEN: WeatherFlow API token from iKitesurf login
# Expires: ~January 2027 (13-month lease)
# To refresh: Login to https://wx.ikitesurf.com/spot/453,
# open DevTools > Storage > Cookies > wfToken, update in GCP Secret Manager
```

### Step 1.6: Commit (documentation only for now)

No code changes yet - this task is GCP configuration.

---

## Task 2: Create SensorReading Model

**Goal:** Define the data structure for real-time sensor readings, separate from the old WeatherConditions model.

**Files:**
- Modify: `app/weather/models.py`
- Test: `tests/weather/test_models.py`

### Step 2.1: Write failing test for SensorReading

Add to `tests/weather/test_models.py`:

```python
from datetime import datetime, timezone
from app.weather.models import SensorReading


class TestSensorReading:
    """Tests for SensorReading dataclass"""

    def test_sensor_reading_creation(self):
        """SensorReading stores all expected fields"""
        reading = SensorReading(
            wind_speed_kts=12.5,
            wind_gust_kts=15.2,
            wind_lull_kts=9.8,
            wind_direction="NNE",
            wind_degrees=28,
            air_temp_f=75.5,
            timestamp_utc=datetime(2025, 12, 10, 17, 51, 16, tzinfo=timezone.utc),
            spot_name="Jupiter-Juno Beach Pier"
        )

        assert reading.wind_speed_kts == 12.5
        assert reading.wind_gust_kts == 15.2
        assert reading.wind_lull_kts == 9.8
        assert reading.wind_direction == "NNE"
        assert reading.wind_degrees == 28
        assert reading.air_temp_f == 75.5
        assert reading.spot_name == "Jupiter-Juno Beach Pier"

    def test_sensor_reading_str(self):
        """SensorReading has readable string representation"""
        reading = SensorReading(
            wind_speed_kts=12.5,
            wind_gust_kts=15.2,
            wind_lull_kts=9.8,
            wind_direction="NNE",
            wind_degrees=28,
            air_temp_f=75.5,
            timestamp_utc=datetime(2025, 12, 10, 17, 51, 16, tzinfo=timezone.utc),
            spot_name="Jupiter-Juno Beach Pier"
        )

        result = str(reading)

        assert "12.5" in result
        assert "NNE" in result

    def test_sensor_reading_is_stale_when_old(self):
        """is_stale returns True when reading is older than threshold"""
        from datetime import timedelta

        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        reading = SensorReading(
            wind_speed_kts=12.5,
            wind_gust_kts=15.2,
            wind_lull_kts=9.8,
            wind_direction="NNE",
            wind_degrees=28,
            air_temp_f=75.5,
            timestamp_utc=old_time,
            spot_name="Jupiter-Juno Beach Pier"
        )

        assert reading.is_stale(threshold_seconds=300) is True

    def test_sensor_reading_is_fresh_when_recent(self):
        """is_stale returns False when reading is recent"""
        from datetime import timedelta

        recent_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        reading = SensorReading(
            wind_speed_kts=12.5,
            wind_gust_kts=15.2,
            wind_lull_kts=9.8,
            wind_direction="NNE",
            wind_degrees=28,
            air_temp_f=75.5,
            timestamp_utc=recent_time,
            spot_name="Jupiter-Juno Beach Pier"
        )

        assert reading.is_stale(threshold_seconds=300) is False
```

### Step 2.2: Run test to verify it fails

```bash
pytest tests/weather/test_models.py::TestSensorReading -v
```

Expected: FAIL - `SensorReading` not defined

### Step 2.3: Implement SensorReading

Add to `app/weather/models.py` (keep existing WeatherConditions for now):

```python
from datetime import datetime, timezone


@dataclass
class SensorReading:
    """Real-time sensor data from WeatherFlow station"""
    wind_speed_kts: float
    wind_gust_kts: float
    wind_lull_kts: float
    wind_direction: str      # Compass: "N", "NNE", "NE", etc.
    wind_degrees: int        # 0-360
    air_temp_f: float
    timestamp_utc: datetime
    spot_name: str

    def __str__(self) -> str:
        return (
            f"Wind: {self.wind_speed_kts:.1f}kts {self.wind_direction} "
            f"(gusts {self.wind_gust_kts:.1f}, lulls {self.wind_lull_kts:.1f}) "
            f"@ {self.spot_name}"
        )

    def is_stale(self, threshold_seconds: int = 300) -> bool:
        """
        Check if this reading is stale.

        Args:
            threshold_seconds: Max age in seconds (default 300 = 5 minutes)

        Returns:
            True if reading is older than threshold
        """
        age = datetime.now(timezone.utc) - self.timestamp_utc
        return age.total_seconds() > threshold_seconds
```

### Step 2.4: Run test to verify it passes

```bash
pytest tests/weather/test_models.py::TestSensorReading -v
```

Expected: All PASS

### Step 2.5: Run all model tests

```bash
pytest tests/weather/test_models.py -v
```

Expected: All PASS (including existing WeatherConditions tests)

### Step 2.6: Commit

```bash
git add app/weather/models.py tests/weather/test_models.py
git commit -m "feat: add SensorReading model for real-time wind data"
```

---

## Task 3: Create WeatherFlow SensorClient

**Goal:** Create API client to fetch real-time wind data from WeatherFlow.

**Files:**
- Create: `app/weather/sensor.py`
- Test: `tests/weather/test_sensor.py`

### Step 3.1: Create test file with failing tests

Create `tests/weather/test_sensor.py`:

```python
# ABOUTME: Tests for WeatherFlow sensor client
# ABOUTME: Validates API parsing and error handling

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.weather.sensor import SensorClient
from app.weather.models import SensorReading


class TestSensorClient:
    """Tests for WeatherFlow SensorClient"""

    def test_fetch_returns_sensor_reading_on_success(self):
        """Successful API call returns SensorReading"""
        with patch('app.weather.sensor.requests') as mock_requests:
            # Mock successful WeatherFlow response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Jupiter-Juno Beach Pier",
                    "station_code": "XJUP",
                    "city": "Juno Beach",
                    "state": "FL",
                    "lat": 26.89337,
                    "lon": -80.05564,
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "2025-12-10 12:51:16",
                            "2025-12-10 17:51:16",
                            12.5,  # avg
                            9.8,   # lull
                            15.2,  # gust
                            28,    # dir
                            "NNE", # dir_text
                            75.5,  # atemp
                            None,  # wtemp
                            1012.7 # pres
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert isinstance(result, SensorReading)
            assert result.wind_speed_kts == 12.5
            assert result.wind_gust_kts == 15.2
            assert result.wind_lull_kts == 9.8
            assert result.wind_direction == "NNE"
            assert result.wind_degrees == 28
            assert result.air_temp_f == 75.5
            assert result.spot_name == "Jupiter-Juno Beach Pier"

    def test_fetch_returns_none_on_http_error(self):
        """HTTP error returns None and logs error"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized: Invalid token"
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="bad-token")
            result = client.fetch()

            assert result is None

    def test_fetch_returns_none_on_api_error_status(self):
        """API error status returns None"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {"status_code": 1, "status_message": "Invalid spot"}
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result is None

    def test_fetch_returns_none_on_network_error(self):
        """Network error returns None"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_requests.get.side_effect = Exception("Connection refused")

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result is None

    def test_fetch_returns_none_on_malformed_response(self):
        """Malformed JSON structure returns None"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"unexpected": "structure"}
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result is None

    def test_parses_utc_timestamp_correctly(self):
        """UTC timestamp is parsed into timezone-aware datetime"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test Spot",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "2025-12-10 12:51:16",
                            "2025-12-10 17:51:16",  # UTC timestamp
                            10.0, 8.0, 12.0, 90, "E", 70.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="test-token")
            result = client.fetch()

            assert result.timestamp_utc.year == 2025
            assert result.timestamp_utc.month == 12
            assert result.timestamp_utc.day == 10
            assert result.timestamp_utc.hour == 17
            assert result.timestamp_utc.minute == 51
            assert result.timestamp_utc.tzinfo == timezone.utc

    def test_uses_correct_api_endpoint_and_params(self):
        """Verifies correct API URL and parameters"""
        with patch('app.weather.sensor.requests') as mock_requests:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test",
                    "data_names": ["timestamp", "utc_timestamp", "avg", "lull", "gust", "dir", "dir_text", "atemp", "wtemp", "pres"],
                    "stations": [{"data_values": [["", "2025-01-01 00:00:00", 10, 8, 12, 0, "N", 70, None, 1013]]}]
                }]
            }
            mock_requests.get.return_value = mock_response

            client = SensorClient(wf_token="my-token", spot_id="453")
            client.fetch()

            # Verify the call
            mock_requests.get.assert_called_once()
            call_args = mock_requests.get.call_args

            assert "api.weatherflow.com" in call_args[0][0]
            assert call_args[1]["params"]["wf_token"] == "my-token"
            assert call_args[1]["params"]["spot_list"] == "453"
            assert call_args[1]["params"]["units_wind"] == "kts"
```

### Step 3.2: Run test to verify it fails

```bash
pytest tests/weather/test_sensor.py -v
```

Expected: FAIL - module `app.weather.sensor` not found

### Step 3.3: Implement SensorClient

Create `app/weather/sensor.py`:

```python
# ABOUTME: WeatherFlow API client for real-time sensor data
# ABOUTME: Fetches wind data from Jupiter-Juno Beach Pier station

import logging
import requests
from datetime import datetime, timezone
from typing import Optional

from app.weather.models import SensorReading

log = logging.getLogger(__name__)


class SensorClient:
    """
    Client for fetching real-time wind data from WeatherFlow API.

    This is the same data source used by iKitesurf for the
    Jupiter-Juno Beach Pier station.
    """

    BASE_URL = "https://api.weatherflow.com/wxengine/rest/spot/getSpotDetailSetByList"
    DEFAULT_SPOT_ID = "453"  # Jupiter-Juno Beach Pier

    def __init__(self, wf_token: str, spot_id: str = None):
        """
        Initialize the sensor client.

        Args:
            wf_token: WeatherFlow session token (from iKitesurf login)
            spot_id: WeatherFlow spot ID (default: Jupiter-Juno Beach Pier)
        """
        self.wf_token = wf_token
        self.spot_id = spot_id or self.DEFAULT_SPOT_ID

    def fetch(self) -> Optional[SensorReading]:
        """
        Fetch current sensor reading from WeatherFlow.

        Returns:
            SensorReading on success, None on any error.
            All errors are logged for debugging (e.g., expired token).
        """
        params = {
            "units_wind": "kts",
            "units_temp": "f",
            "units_distance": "mi",
            "units_precip": "in",
            "include_spot_products": "true",
            "stormprint_only": "false",
            "wf_token": self.wf_token,
            "spot_types": "1,100,101",
            "spot_list": self.spot_id
        }

        headers = {
            "Accept": "*/*",
            "Origin": "https://wx.ikitesurf.com",
            "Referer": "https://wx.ikitesurf.com/",
            "User-Agent": "Mozilla/5.0 (compatible; CanIFuckingDownwindToday/1.0)"
        }

        try:
            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=10)

            if response.status_code != 200:
                log.error(f"WeatherFlow API HTTP error: {response.status_code} - {response.text}")
                return None

            data = response.json()

            if data.get("status", {}).get("status_code") != 0:
                log.error(f"WeatherFlow API error status: {data}")
                return None

            return self._parse_response(data)

        except requests.RequestException as e:
            log.error(f"WeatherFlow API request failed: {e}")
            return None
        except Exception as e:
            log.error(f"WeatherFlow API unexpected error: {e}")
            return None

    def _parse_response(self, data: dict) -> Optional[SensorReading]:
        """
        Parse WeatherFlow API response into SensorReading.

        Args:
            data: Raw API response JSON

        Returns:
            SensorReading on success, None if parsing fails
        """
        try:
            spot = data["spots"][0]
            station = spot["stations"][0]

            # Map field names to values
            field_names = spot["data_names"]
            field_values = station["data_values"][0]
            obs = dict(zip(field_names, field_values))

            # Parse UTC timestamp
            utc_str = obs.get("utc_timestamp", "")
            timestamp_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

            return SensorReading(
                wind_speed_kts=float(obs.get("avg", 0)),
                wind_gust_kts=float(obs.get("gust", 0)),
                wind_lull_kts=float(obs.get("lull", 0)),
                wind_direction=obs.get("dir_text", "N"),
                wind_degrees=int(obs.get("dir", 0)),
                air_temp_f=float(obs.get("atemp", 0)),
                timestamp_utc=timestamp_utc,
                spot_name=spot.get("name", "Unknown")
            )

        except (KeyError, IndexError, TypeError, ValueError) as e:
            log.error(f"WeatherFlow API response parsing failed: {e} - Response: {data}")
            return None
```

### Step 3.4: Run test to verify it passes

```bash
pytest tests/weather/test_sensor.py -v
```

Expected: All PASS

### Step 3.5: Commit

```bash
git add app/weather/sensor.py tests/weather/test_sensor.py
git commit -m "feat: add WeatherFlow SensorClient for real-time wind data"
```

---

## Task 4: Update Config for Sensor Settings

**Goal:** Add configuration for WeatherFlow token and staleness threshold.

**Files:**
- Modify: `app/config.py`
- Test: `tests/test_config.py`

### Step 4.1: Write failing test for new config values

Add to `tests/test_config.py`:

```python
class TestSensorConfig:
    """Tests for sensor-related configuration"""

    def test_wf_token_from_environment(self):
        """WF_TOKEN is read from environment"""
        import os
        from importlib import reload

        # Set env var
        os.environ["WF_TOKEN"] = "test-token-123"

        # Reload config to pick up new env var
        import app.config
        reload(app.config)
        from app.config import Config

        assert Config.WF_TOKEN == "test-token-123"

        # Cleanup
        del os.environ["WF_TOKEN"]

    def test_sensor_stale_threshold_default(self):
        """SENSOR_STALE_THRESHOLD_SECONDS has sensible default"""
        from app.config import Config

        # Default is 300 seconds (5 minutes)
        assert Config.SENSOR_STALE_THRESHOLD_SECONDS == 300

    def test_sensor_cache_ttl_default(self):
        """SENSOR_CACHE_TTL_SECONDS has sensible default"""
        from app.config import Config

        # Default is 120 seconds (2 minutes)
        assert Config.SENSOR_CACHE_TTL_SECONDS == 120

    def test_wf_spot_id_default(self):
        """WF_SPOT_ID defaults to Jupiter-Juno Beach Pier"""
        from app.config import Config

        assert Config.WF_SPOT_ID == "453"
```

### Step 4.2: Run test to verify it fails

```bash
pytest tests/test_config.py::TestSensorConfig -v
```

Expected: FAIL - attributes don't exist

### Step 4.3: Add sensor config to Config class

Update `app/config.py`:

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
    # Coast runs N-S, so wind parallel to coast is best for downwinding
    OPTIMAL_WIND_DIRECTIONS = ["N", "S"]  # Parallel to coast - best
    GOOD_WIND_DIRECTIONS = ["NE", "SE", "NW", "SW"]  # Diagonal - good
    OK_WIND_DIRECTIONS = ["NNE", "SSE", "NNW", "SSW", "ENE", "ESE", "WNW", "WSW"]  # Acceptable
    BAD_WIND_DIRECTIONS = ["E", "W"]  # Perpendicular to coast - bad

    OPTIMAL_WIND_MIN = 15  # knots
    OPTIMAL_WIND_MAX = 25  # knots
    OPTIMAL_WAVE_MIN = 2   # feet
    OPTIMAL_WAVE_MAX = 4   # feet

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # WeatherFlow Sensor Config
    # Token expires ~January 2027 (13-month lease from iKitesurf login)
    # To refresh: Login to https://wx.ikitesurf.com/spot/453,
    # DevTools > Storage > Cookies > wfToken, update in GCP Secret Manager
    WF_TOKEN = os.getenv("WF_TOKEN", "")
    WF_SPOT_ID = os.getenv("WF_SPOT_ID", "453")  # Jupiter-Juno Beach Pier

    # Sensor staleness: if reading is older than this, consider offline
    SENSOR_STALE_THRESHOLD_SECONDS = int(os.getenv("SENSOR_STALE_THRESHOLD_SECONDS", "300"))  # 5 minutes

    # Sensor cache TTL: how often to fetch fresh data
    SENSOR_CACHE_TTL_SECONDS = int(os.getenv("SENSOR_CACHE_TTL_SECONDS", "120"))  # 2 minutes

    # LLM variations cache TTL: regenerate when rating changes or after this time
    VARIATIONS_CACHE_TTL_MINUTES = int(os.getenv("VARIATIONS_CACHE_TTL_MINUTES", "15"))

    # Caching (legacy - kept for reference)
    CACHE_REFRESH_HOURS = int(os.getenv("CACHE_REFRESH_HOURS", "2"))

    # Debug mode
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
```

### Step 4.4: Run test to verify it passes

```bash
pytest tests/test_config.py::TestSensorConfig -v
```

Expected: All PASS

### Step 4.5: Run all config tests

```bash
pytest tests/test_config.py -v
```

Expected: All PASS

### Step 4.6: Commit

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add sensor configuration for WeatherFlow integration"
```

---

## Task 5: Update Scoring for Wind-Only

**Goal:** Make wave/swell data optional in scoring algorithm. Score based on wind only when wave data is unavailable.

**Files:**
- Modify: `app/scoring/calculator.py`
- Test: `tests/scoring/test_calculator.py`

### Step 5.1: Write failing tests for wind-only scoring

Add to `tests/scoring/test_calculator.py`:

```python
class TestWindOnlyScoring:
    """Tests for scoring with wind data only (no waves)"""

    def test_calculate_score_wind_only_good_conditions(self):
        """Good wind with no wave data scores reasonably"""
        from app.weather.models import SensorReading
        from datetime import datetime, timezone

        calculator = ScoreCalculator()

        # Create sensor reading (no wave data)
        reading = SensorReading(
            wind_speed_kts=18.0,
            wind_gust_kts=22.0,
            wind_lull_kts=14.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        score = calculator.calculate_sup_score_from_sensor(reading)

        # Good wind (18 kts) + good direction (N) should score well
        assert 6 <= score <= 9

    def test_calculate_score_wind_only_light_wind(self):
        """Light wind scores poorly even without wave penalty"""
        from app.weather.models import SensorReading
        from datetime import datetime, timezone

        calculator = ScoreCalculator()

        reading = SensorReading(
            wind_speed_kts=6.0,
            wind_gust_kts=8.0,
            wind_lull_kts=4.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        score = calculator.calculate_sup_score_from_sensor(reading)

        # Light wind should score poorly
        assert score <= 4

    def test_calculate_score_wind_only_bad_direction(self):
        """Bad wind direction penalizes score"""
        from app.weather.models import SensorReading
        from datetime import datetime, timezone

        calculator = ScoreCalculator()

        reading = SensorReading(
            wind_speed_kts=18.0,
            wind_gust_kts=22.0,
            wind_lull_kts=14.0,
            wind_direction="E",  # Bad - perpendicular to coast
            wind_degrees=90,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        score = calculator.calculate_sup_score_from_sensor(reading)

        # Good wind but bad direction
        assert score <= 6

    def test_parawing_score_wind_only(self):
        """Parawing scoring works with wind-only data"""
        from app.weather.models import SensorReading
        from datetime import datetime, timezone

        calculator = ScoreCalculator()

        reading = SensorReading(
            wind_speed_kts=20.0,
            wind_gust_kts=24.0,
            wind_lull_kts=16.0,
            wind_direction="S",
            wind_degrees=180,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        score = calculator.calculate_parawing_score_from_sensor(reading)

        # Strong wind + good direction should score well for parawing
        assert score >= 7

    def test_parawing_score_tanks_below_15kts(self):
        """Parawing score tanks when wind is below 15 kts"""
        from app.weather.models import SensorReading
        from datetime import datetime, timezone

        calculator = ScoreCalculator()

        reading = SensorReading(
            wind_speed_kts=12.0,
            wind_gust_kts=15.0,
            wind_lull_kts=9.0,
            wind_direction="S",
            wind_degrees=180,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        score = calculator.calculate_parawing_score_from_sensor(reading)

        # Below 15 kts should tank parawing score
        assert score <= 4

    def test_calculate_score_with_optional_wave_data(self):
        """When wave data is provided, it affects the score"""
        from app.weather.models import SensorReading
        from datetime import datetime, timezone

        calculator = ScoreCalculator()

        reading = SensorReading(
            wind_speed_kts=18.0,
            wind_gust_kts=22.0,
            wind_lull_kts=14.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        # Score without wave data
        score_no_waves = calculator.calculate_sup_score_from_sensor(reading)

        # Score with good wave data
        score_with_waves = calculator.calculate_sup_score_from_sensor(
            reading,
            wave_height_ft=3.0,
            swell_direction="NE"
        )

        # Good waves should boost score
        assert score_with_waves >= score_no_waves
```

### Step 5.2: Run tests to verify they fail

```bash
pytest tests/scoring/test_calculator.py::TestWindOnlyScoring -v
```

Expected: FAIL - methods don't exist

### Step 5.3: Implement wind-only scoring methods

Add to `app/scoring/calculator.py`:

```python
from app.weather.models import SensorReading
from typing import Optional


class ScoreCalculator:
    # ... existing methods ...

    def calculate_sup_score_from_sensor(
        self,
        reading: SensorReading,
        wave_height_ft: Optional[float] = None,
        swell_direction: Optional[str] = None
    ) -> int:
        """
        Calculate SUP foil score from sensor reading.

        Wind is the primary factor. Wave data is optional and acts as a modifier.

        Args:
            reading: Real-time sensor reading
            wave_height_ft: Optional wave height (future extension)
            swell_direction: Optional swell direction (future extension)

        Returns:
            Score from 1-10
        """
        score = 5.0  # Start neutral

        # Wind speed scoring (dominant factor)
        wind = reading.wind_speed_kts
        if Config.OPTIMAL_WIND_MIN <= wind <= Config.OPTIMAL_WIND_MAX:
            score += 2  # Perfect wind (15-25kt)
        elif 12 <= wind < Config.OPTIMAL_WIND_MIN:
            score -= 0.5  # Marginal - barely rideable
        elif 8 <= wind < 12:
            score -= 1.5  # Small - challenging conditions
        elif wind < 8:
            score -= 3  # Too light - not really rideable
        elif wind > Config.OPTIMAL_WIND_MAX:
            score -= 1  # Too strong

        # Wind direction scoring
        if reading.wind_direction in Config.OPTIMAL_WIND_DIRECTIONS:
            score += 1.5  # Perfect direction (N, S)
        elif reading.wind_direction in Config.GOOD_WIND_DIRECTIONS:
            score += 0.5  # Good direction (NE, SE, NW, SW)
        elif reading.wind_direction in Config.OK_WIND_DIRECTIONS:
            score += 0  # OK direction
        elif reading.wind_direction in Config.BAD_WIND_DIRECTIONS:
            score -= 2  # Bad direction (E, W)
        else:
            score -= 1  # Unknown direction

        # Wave modifier (when available)
        if wave_height_ft is not None:
            if Config.OPTIMAL_WAVE_MIN <= wave_height_ft <= Config.OPTIMAL_WAVE_MAX:
                score += 1  # Perfect waves
            elif 1.5 <= wave_height_ft < Config.OPTIMAL_WAVE_MIN:
                score += 0.5  # Small but rideable
            elif 1 <= wave_height_ft < 1.5:
                score -= 0.5  # Very small
            elif wave_height_ft < 1:
                score -= 1  # Too flat
            elif wave_height_ft > Config.OPTIMAL_WAVE_MAX:
                score -= 1  # Too big

        return max(1, min(10, int(round(score))))

    def calculate_parawing_score_from_sensor(
        self,
        reading: SensorReading,
        wave_height_ft: Optional[float] = None,
        swell_direction: Optional[str] = None
    ) -> int:
        """
        Calculate parawing score from sensor reading.

        Parawing requires more consistent wind - below 15kt is essentially un-rideable.

        Args:
            reading: Real-time sensor reading
            wave_height_ft: Optional wave height (future extension)
            swell_direction: Optional swell direction (future extension)

        Returns:
            Score from 1-10
        """
        # Start with SUP score as baseline
        score = float(self.calculate_sup_score_from_sensor(reading, wave_height_ft, swell_direction))

        # Apply stricter wind requirements
        wind = reading.wind_speed_kts
        if wind < 15:
            # Tank the score for insufficient wind
            score = min(score, 4)
            score -= (15 - wind) * 0.5
        elif wind >= 18:
            # Bonus for strong consistent wind
            score += 1

        # Parawing is slightly more forgiving on wave height with strong wind
        if wind >= 18 and wave_height_ft is not None and wave_height_ft >= 1.5:
            score += 0.5

        return max(1, min(10, int(round(score))))
```

### Step 5.4: Run tests to verify they pass

```bash
pytest tests/scoring/test_calculator.py::TestWindOnlyScoring -v
```

Expected: All PASS

### Step 5.5: Run all scoring tests

```bash
pytest tests/scoring/test_calculator.py -v
```

Expected: All PASS (including existing WeatherConditions-based tests)

### Step 5.6: Commit

```bash
git add app/scoring/calculator.py tests/scoring/test_calculator.py
git commit -m "feat: add wind-only scoring with optional wave modifier"
```

---

## Task 6: Split Cache for Sensor + Variations

**Goal:** Implement split cache with different TTLs: sensor data (2 min), LLM variations (15 min, regenerate on rating change).

**Files:**
- Modify: `app/cache/manager.py`
- Test: `tests/cache/test_manager.py`

### Step 6.1: Write failing tests for split cache

Add to `tests/cache/test_manager.py`:

```python
from datetime import datetime, timezone, timedelta
from app.cache.manager import CacheManager
from app.weather.models import SensorReading


class TestSplitCache:
    """Tests for split cache with separate TTLs"""

    def test_sensor_cache_separate_from_variations(self):
        """Sensor and variations have independent staleness"""
        manager = CacheManager(
            sensor_ttl_seconds=120,
            variations_ttl_minutes=15
        )

        # Set sensor data
        reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )
        manager.set_sensor(reading, ratings={"sup": 7, "parawing": 8})

        # Set variations
        manager.set_variations(
            rating_snapshot={"sup": 7, "parawing": 8},
            variations={"sup": {"persona": ["test"]}, "parawing": {}}
        )

        assert manager.is_sensor_stale() is False
        assert manager.is_variations_stale() is False

    def test_sensor_stale_after_ttl(self):
        """Sensor cache becomes stale after TTL"""
        manager = CacheManager(sensor_ttl_seconds=120)

        # Set sensor data with old fetch time
        reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )

        # Manually set old fetch timestamp
        manager._sensor_cache = {
            "reading": reading,
            "ratings": {"sup": 7, "parawing": 8},
            "fetched_at": datetime.now(timezone.utc) - timedelta(seconds=180)
        }

        assert manager.is_sensor_stale() is True

    def test_variations_stale_when_rating_changes(self):
        """Variations become stale when rating differs from snapshot"""
        manager = CacheManager()

        # Set variations with rating snapshot
        manager.set_variations(
            rating_snapshot={"sup": 7, "parawing": 8},
            variations={"sup": {"persona": ["test"]}, "parawing": {}}
        )

        # Check staleness with different current rating
        assert manager.should_regenerate_variations(current_ratings={"sup": 8, "parawing": 8}) is True

    def test_variations_fresh_when_rating_same(self):
        """Variations stay fresh when rating matches snapshot"""
        manager = CacheManager()

        manager.set_variations(
            rating_snapshot={"sup": 7, "parawing": 8},
            variations={"sup": {"persona": ["test"]}, "parawing": {}}
        )

        assert manager.should_regenerate_variations(current_ratings={"sup": 7, "parawing": 8}) is False

    def test_get_sensor_returns_none_when_stale(self):
        """get_sensor returns None when sensor cache is stale"""
        manager = CacheManager(sensor_ttl_seconds=120)

        manager._sensor_cache = {
            "reading": None,
            "ratings": {"sup": 5, "parawing": 5},
            "fetched_at": datetime.now(timezone.utc) - timedelta(seconds=180)
        }

        assert manager.get_sensor() is None

    def test_offline_state_stored_separately(self):
        """Offline state is tracked in sensor cache"""
        manager = CacheManager()

        # Store offline state with last known reading
        last_reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc) - timedelta(minutes=10),
            spot_name="Test"
        )

        manager.set_offline(last_known_reading=last_reading)

        assert manager.is_offline() is True
        assert manager.get_last_known_reading() is not None
        assert manager.get_last_known_reading().wind_speed_kts == 15.0

    def test_clear_offline_when_fresh_data(self):
        """Setting fresh sensor data clears offline state"""
        manager = CacheManager()

        manager.set_offline(last_known_reading=None)
        assert manager.is_offline() is True

        # Set fresh reading
        reading = SensorReading(
            wind_speed_kts=15.0,
            wind_gust_kts=18.0,
            wind_lull_kts=12.0,
            wind_direction="N",
            wind_degrees=0,
            air_temp_f=75.0,
            timestamp_utc=datetime.now(timezone.utc),
            spot_name="Test"
        )
        manager.set_sensor(reading, ratings={"sup": 7, "parawing": 8})

        assert manager.is_offline() is False
```

### Step 6.2: Run tests to verify they fail

```bash
pytest tests/cache/test_manager.py::TestSplitCache -v
```

Expected: FAIL - new methods don't exist

### Step 6.3: Implement split cache

Replace `app/cache/manager.py`:

```python
# ABOUTME: Split cache manager for sensor data and LLM variations
# ABOUTME: Sensor data has short TTL (2 min), variations have longer TTL (15 min)

from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from app.weather.models import SensorReading


class CacheManager:
    """
    Split cache for sensor data and LLM variations.

    Sensor data: Short TTL (default 2 minutes), refreshed frequently
    Variations: Longer TTL (default 15 minutes), regenerated when rating changes
    """

    def __init__(
        self,
        sensor_ttl_seconds: int = 120,
        variations_ttl_minutes: int = 15
    ):
        self.sensor_ttl_seconds = sensor_ttl_seconds
        self.variations_ttl_minutes = variations_ttl_minutes

        # Sensor cache: stores reading, ratings, and fetch timestamp
        self._sensor_cache: Optional[dict] = None

        # Variations cache: stores variations and the rating they were generated for
        self._variations_cache: Optional[dict] = None

        # Offline state
        self._is_offline: bool = False
        self._last_known_reading: Optional[SensorReading] = None

    # ==================== Sensor Cache ====================

    def set_sensor(self, reading: SensorReading, ratings: dict[str, int]) -> None:
        """
        Store sensor reading and calculated ratings.

        Args:
            reading: Fresh sensor reading
            ratings: {"sup": int, "parawing": int}
        """
        self._sensor_cache = {
            "reading": reading,
            "ratings": ratings,
            "fetched_at": datetime.now(timezone.utc)
        }
        self._is_offline = False
        self._last_known_reading = reading

    def get_sensor(self) -> Optional[dict]:
        """
        Get sensor cache if fresh.

        Returns:
            {"reading": SensorReading, "ratings": dict, "fetched_at": datetime}
            or None if stale/empty
        """
        if self.is_sensor_stale():
            return None
        return self._sensor_cache

    def get_ratings(self) -> Optional[dict[str, int]]:
        """Get current ratings from sensor cache."""
        if self._sensor_cache:
            return self._sensor_cache.get("ratings")
        return None

    def is_sensor_stale(self) -> bool:
        """Check if sensor cache needs refresh."""
        if self._sensor_cache is None:
            return True

        fetched_at = self._sensor_cache.get("fetched_at")
        if fetched_at is None:
            return True

        age = datetime.now(timezone.utc) - fetched_at
        return age.total_seconds() > self.sensor_ttl_seconds

    # ==================== Variations Cache ====================

    def set_variations(
        self,
        rating_snapshot: dict[str, int],
        variations: dict[str, dict[str, list[str]]]
    ) -> None:
        """
        Store LLM variations with the rating they were generated for.

        Args:
            rating_snapshot: {"sup": int, "parawing": int} at generation time
            variations: {"sup": {"persona_id": [responses]}, "parawing": {...}}
        """
        self._variations_cache = {
            "rating_snapshot": rating_snapshot,
            "variations": variations,
            "generated_at": datetime.now(timezone.utc)
        }

    def get_variations(self, mode: str, persona_id: str) -> list[str]:
        """Get variations for a specific mode and persona."""
        if self._variations_cache is None:
            return []
        return (
            self._variations_cache
            .get("variations", {})
            .get(mode, {})
            .get(persona_id, [])
        )

    def get_all_variations(self) -> Optional[dict]:
        """Get full variations cache."""
        return self._variations_cache

    def is_variations_stale(self) -> bool:
        """Check if variations cache has expired (time-based only)."""
        if self._variations_cache is None:
            return True

        generated_at = self._variations_cache.get("generated_at")
        if generated_at is None:
            return True

        age = datetime.now(timezone.utc) - generated_at
        return age > timedelta(minutes=self.variations_ttl_minutes)

    def should_regenerate_variations(self, current_ratings: dict[str, int]) -> bool:
        """
        Check if variations should be regenerated.

        Regenerate if:
        1. Variations cache is empty/stale (time-based)
        2. Rating has changed since variations were generated

        Args:
            current_ratings: Current {"sup": int, "parawing": int}

        Returns:
            True if variations should be regenerated
        """
        if self._variations_cache is None:
            return True

        if self.is_variations_stale():
            return True

        # Check if rating changed
        snapshot = self._variations_cache.get("rating_snapshot", {})
        return snapshot != current_ratings

    # ==================== Offline State ====================

    def set_offline(self, last_known_reading: Optional[SensorReading] = None) -> None:
        """Mark sensor as offline, preserving last known reading."""
        self._is_offline = True
        if last_known_reading is not None:
            self._last_known_reading = last_known_reading

    def is_offline(self) -> bool:
        """Check if sensor is currently offline."""
        return self._is_offline

    def get_last_known_reading(self) -> Optional[SensorReading]:
        """Get the last known good reading (for offline display)."""
        return self._last_known_reading

    # ==================== Offline Variations ====================

    def set_offline_variations(self, variations: dict[str, dict[str, list[str]]]) -> None:
        """Store offline-specific persona variations."""
        self._offline_variations = variations

    def get_offline_variations(self, mode: str, persona_id: str) -> list[str]:
        """Get offline variations for a specific persona."""
        if not hasattr(self, '_offline_variations') or self._offline_variations is None:
            return []
        return self._offline_variations.get(mode, {}).get(persona_id, [])

    # ==================== Legacy Support ====================

    def set_cache(self, data: dict[str, Any]) -> None:
        """
        Legacy method for unified cache format.
        Converts to split cache internally.
        """
        if "weather" in data and "ratings" in data:
            # This is the old format - we can't fully support it
            # but we can store the ratings
            self._sensor_cache = {
                "reading": None,  # Old format doesn't have SensorReading
                "ratings": data.get("ratings", {}),
                "fetched_at": data.get("timestamp", datetime.now(timezone.utc))
            }

        if "variations" in data:
            self.set_variations(
                rating_snapshot=data.get("ratings", {}),
                variations=data.get("variations", {})
            )

    def get_cache(self) -> Optional[dict[str, Any]]:
        """
        Legacy method for unified cache format.
        Returns None if sensor is stale.
        """
        if self.is_sensor_stale():
            return None

        return {
            "timestamp": self._sensor_cache.get("fetched_at") if self._sensor_cache else None,
            "weather": self._build_weather_dict(),
            "ratings": self.get_ratings() or {},
            "variations": self._variations_cache.get("variations", {}) if self._variations_cache else {}
        }

    def _build_weather_dict(self) -> dict:
        """Build weather dict from sensor reading for legacy format."""
        if not self._sensor_cache or not self._sensor_cache.get("reading"):
            return {"wind_speed": 0, "wind_direction": "N", "wave_height": 0, "swell_direction": "N"}

        reading = self._sensor_cache["reading"]
        return {
            "wind_speed": reading.wind_speed_kts,
            "wind_direction": reading.wind_direction,
            "wave_height": 0,  # No wave data from sensor
            "swell_direction": "N"  # No swell data from sensor
        }

    def is_stale(self) -> bool:
        """Legacy method - checks sensor staleness."""
        return self.is_sensor_stale()

    def clear(self) -> None:
        """Clear all caches."""
        self._sensor_cache = None
        self._variations_cache = None
        self._is_offline = False
```

### Step 6.4: Run tests to verify they pass

```bash
pytest tests/cache/test_manager.py::TestSplitCache -v
```

Expected: All PASS

### Step 6.5: Run all cache tests

```bash
pytest tests/cache/test_manager.py -v
```

Expected: All PASS (legacy tests should still work via compatibility methods)

### Step 6.6: Commit

```bash
git add app/cache/manager.py tests/cache/test_manager.py
git commit -m "feat: split cache with separate TTLs for sensor and variations"
```

---

## Task 7: Add Offline LLM Variations

**Goal:** Generate witty persona responses for when the sensor is offline.

**Files:**
- Modify: `app/ai/llm_client.py`
- Test: `tests/ai/test_llm_client.py`

### Step 7.1: Write failing tests for offline variations

Add to `tests/ai/test_llm_client.py`:

```python
class TestOfflineVariations:
    """Tests for generating offline persona responses"""

    def test_generate_offline_variations_returns_dict(self):
        """Offline generation returns variations keyed by persona"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            mock_response = MagicMock()
            mock_response.text = """===PERSONA:drill_sergeant===
1. The sensor's AWOL, just like your commitment to this sport, maggot!
2. Can't get a reading? Maybe the sensor got tired of watching you fail.
===PERSONA:disappointed_dad===
1. Even the sensor doesn't want to watch you foil today. Can't say I blame it.
2. The sensor's taking a break. Wish I could take a break from your excuses."""

            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_response
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_offline_variations()

            assert "drill_sergeant" in result
            assert "disappointed_dad" in result
            assert len(result["drill_sergeant"]) == 2
            assert "sensor" in result["drill_sergeant"][0].lower()

    def test_generate_offline_variations_handles_error(self):
        """Returns empty dict on API failure"""
        with patch('app.ai.llm_client.genai') as mock_genai:
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("API Error")
            mock_genai.GenerativeModel.return_value = mock_model

            client = LLMClient(api_key="test-key")
            result = client.generate_offline_variations()

            assert result == {}
```

### Step 7.2: Run tests to verify they fail

```bash
pytest tests/ai/test_llm_client.py::TestOfflineVariations -v
```

Expected: FAIL - method doesn't exist

### Step 7.3: Implement offline variations

Add to `app/ai/llm_client.py`:

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
```

### Step 7.4: Run tests to verify they pass

```bash
pytest tests/ai/test_llm_client.py::TestOfflineVariations -v
```

Expected: All PASS

### Step 7.5: Run all LLM tests

```bash
pytest tests/ai/test_llm_client.py -v
```

Expected: All PASS

### Step 7.6: Commit

```bash
git add app/ai/llm_client.py tests/ai/test_llm_client.py
git commit -m "feat: add offline persona variation generation"
```

---

## Task 8: Update Orchestrator for Sensor Flow

**Goal:** Replace NOAA fetch with SensorClient, implement staleness detection, and handle offline state.

**Files:**
- Modify: `app/orchestrator.py`
- Test: `tests/test_orchestrator.py`

### Step 8.1: Write failing tests for new orchestrator flow

Add to `tests/test_orchestrator.py`:

```python
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from app.weather.models import SensorReading


class TestSensorFlow:
    """Tests for sensor-based data flow"""

    def test_get_cached_data_fetches_from_sensor(self):
        """Orchestrator fetches data from SensorClient"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache:

            # Setup sensor
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

            # Setup cache as stale
            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.get_ratings.return_value = {"sup": 7, "parawing": 8}
            mock_cache.should_regenerate_variations.return_value = False
            MockCache.return_value = mock_cache

            # Setup LLM
            mock_llm = MagicMock()
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache

            orchestrator.get_cached_data()

            mock_sensor.fetch.assert_called_once()

    def test_detects_stale_sensor_reading(self):
        """Orchestrator marks offline when sensor timestamp is stale"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            # Setup sensor with stale reading
            old_reading = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc) - timedelta(minutes=10),
                spot_name="Test"
            )
            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = old_reading
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            MockCache.return_value = mock_cache

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache

            orchestrator.get_cached_data()

            # Should have called set_offline
            mock_cache.set_offline.assert_called()

    def test_handles_sensor_fetch_failure(self):
        """Orchestrator handles None from sensor fetch gracefully"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            mock_sensor = MagicMock()
            mock_sensor.fetch.return_value = None
            MockSensor.return_value = mock_sensor

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = True
            mock_cache.is_offline.return_value = False
            mock_cache.get_last_known_reading.return_value = None
            MockCache.return_value = mock_cache

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache

            orchestrator.get_cached_data()

            mock_cache.set_offline.assert_called()

    def test_regenerates_variations_when_rating_changes(self):
        """LLM variations regenerate when rating changes"""
        with patch('app.orchestrator.SensorClient') as MockSensor, \
             patch('app.orchestrator.LLMClient') as MockLLM, \
             patch('app.orchestrator.CacheManager') as MockCache, \
             patch('app.orchestrator.ScoreCalculator') as MockCalc:

            mock_reading = SensorReading(
                wind_speed_kts=20.0,
                wind_gust_kts=24.0,
                wind_lull_kts=16.0,
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
            mock_cache.get_ratings.return_value = {"sup": 8, "parawing": 9}
            mock_cache.should_regenerate_variations.return_value = True
            MockCache.return_value = mock_cache

            mock_calc = MagicMock()
            mock_calc.calculate_sup_score_from_sensor.return_value = 8
            mock_calc.calculate_parawing_score_from_sensor.return_value = 9
            MockCalc.return_value = mock_calc

            mock_llm = MagicMock()
            mock_llm.generate_all_variations.return_value = {"drill_sergeant": ["test"]}
            MockLLM.return_value = mock_llm

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.sensor_client = mock_sensor
            orchestrator.cache = mock_cache
            orchestrator.score_calculator = mock_calc
            orchestrator.llm_client = mock_llm

            orchestrator.get_cached_data()

            # Should have generated variations
            assert mock_llm.generate_all_variations.call_count >= 1

    def test_returns_offline_state_with_last_known(self):
        """When offline, returns last known reading info"""
        with patch('app.orchestrator.SensorClient'), \
             patch('app.orchestrator.LLMClient'), \
             patch('app.orchestrator.CacheManager') as MockCache:

            last_known = SensorReading(
                wind_speed_kts=15.0,
                wind_gust_kts=18.0,
                wind_lull_kts=12.0,
                wind_direction="N",
                wind_degrees=0,
                air_temp_f=75.0,
                timestamp_utc=datetime.now(timezone.utc) - timedelta(minutes=20),
                spot_name="Test"
            )

            mock_cache = MagicMock()
            mock_cache.is_sensor_stale.return_value = False
            mock_cache.is_offline.return_value = True
            mock_cache.get_last_known_reading.return_value = last_known
            mock_cache.get_offline_variations.return_value = ["Sensor's dead, like your dreams."]
            MockCache.return_value = mock_cache

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test")
            orchestrator.cache = mock_cache

            result = orchestrator.get_cached_data()

            assert result["is_offline"] is True
            assert result["last_known_reading"] is not None
```

### Step 8.2: Run tests to verify they fail

```bash
pytest tests/test_orchestrator.py::TestSensorFlow -v
```

Expected: FAIL - new implementation needed

### Step 8.3: Implement new orchestrator

Replace `app/orchestrator.py`:

```python
# ABOUTME: Main application orchestrator coordinating all components
# ABOUTME: Handles sensor fetch, scoring, LLM generation, caching, and offline state

import logging
import random
from datetime import datetime, timezone
from typing import Optional

from app.config import Config
from app.weather.sensor import SensorClient
from app.weather.models import SensorReading
from app.scoring.calculator import ScoreCalculator
from app.scoring.foil_recommender import FoilRecommender
from app.ai.llm_client import LLMClient
from app.cache.manager import CacheManager
from app.debug import debug_log

log = logging.getLogger(__name__)


class AppOrchestrator:
    """Orchestrates all app components to generate ratings"""

    def __init__(self, api_key: str):
        self.sensor_client = SensorClient(
            wf_token=Config.WF_TOKEN,
            spot_id=Config.WF_SPOT_ID
        )
        self.score_calculator = ScoreCalculator()
        self.foil_recommender = FoilRecommender()
        self.llm_client = LLMClient(api_key=api_key)
        self.cache = CacheManager(
            sensor_ttl_seconds=Config.SENSOR_CACHE_TTL_SECONDS,
            variations_ttl_minutes=Config.VARIATIONS_CACHE_TTL_MINUTES
        )

    def get_cached_data(self) -> dict:
        """
        Get current data, fetching from sensor if needed.

        Returns:
            {
                "is_offline": bool,
                "timestamp": datetime or None,
                "last_known_reading": SensorReading or None,
                "weather": {...} or None,
                "ratings": {"sup": int, "parawing": int} or None,
                "variations": {...}
            }
        """
        # Check if sensor cache needs refresh
        if self.cache.is_sensor_stale():
            self._refresh_sensor()

        # Check if we're offline
        if self.cache.is_offline():
            return self._build_offline_response()

        # Get current ratings
        current_ratings = self.cache.get_ratings()

        # Check if variations need refresh (rating changed or TTL expired)
        if current_ratings and self.cache.should_regenerate_variations(current_ratings):
            self._refresh_variations(current_ratings)

        return self._build_online_response()

    def _refresh_sensor(self) -> None:
        """Fetch fresh sensor data and calculate ratings."""
        debug_log("Refreshing sensor data", "ORCHESTRATOR")

        reading = self.sensor_client.fetch()

        if reading is None:
            log.warning("Sensor fetch returned None - marking offline")
            self.cache.set_offline(self.cache.get_last_known_reading())
            self._ensure_offline_variations()
            return

        # Check if reading itself is stale (sensor hasn't updated)
        if reading.is_stale(threshold_seconds=Config.SENSOR_STALE_THRESHOLD_SECONDS):
            log.warning(f"Sensor reading is stale: {reading.timestamp_utc}")
            self.cache.set_offline(reading)
            self._ensure_offline_variations()
            return

        # Calculate ratings
        sup_score = self.score_calculator.calculate_sup_score_from_sensor(reading)
        parawing_score = self.score_calculator.calculate_parawing_score_from_sensor(reading)

        ratings = {
            "sup": sup_score,
            "parawing": parawing_score
        }

        self.cache.set_sensor(reading, ratings)
        debug_log(f"Sensor cache updated: {reading.wind_speed_kts}kts {reading.wind_direction}", "ORCHESTRATOR")

    def _refresh_variations(self, ratings: dict[str, int]) -> None:
        """Generate fresh LLM variations for current ratings."""
        debug_log(f"Refreshing variations for ratings: {ratings}", "ORCHESTRATOR")

        sensor_data = self.cache.get_sensor()
        if not sensor_data or not sensor_data.get("reading"):
            return

        reading = sensor_data["reading"]
        variations = {"sup": {}, "parawing": {}}

        for mode in ["sup", "parawing"]:
            mode_variations = self.llm_client.generate_all_variations(
                wind_speed=reading.wind_speed_kts,
                wind_direction=reading.wind_direction,
                wave_height=0,  # No wave data from sensor
                swell_direction="N",
                rating=ratings[mode],
                mode=mode
            )
            variations[mode] = mode_variations

        self.cache.set_variations(ratings, variations)
        debug_log(f"Variations cached: {sum(len(v) for v in variations['sup'].values())} SUP responses", "ORCHESTRATOR")

    def _ensure_offline_variations(self) -> None:
        """Generate offline variations if not already cached."""
        existing = self.cache.get_offline_variations("sup", "drill_sergeant")
        if existing:
            return  # Already have offline variations

        debug_log("Generating offline variations", "ORCHESTRATOR")
        offline_variations = self.llm_client.generate_offline_variations()

        if offline_variations:
            self.cache.set_offline_variations({
                "sup": offline_variations,
                "parawing": offline_variations  # Same variations for both modes
            })

    def _build_offline_response(self) -> dict:
        """Build response dict for offline state."""
        last_known = self.cache.get_last_known_reading()

        return {
            "is_offline": True,
            "timestamp": last_known.timestamp_utc if last_known else None,
            "last_known_reading": last_known,
            "weather": self._reading_to_weather_dict(last_known) if last_known else None,
            "ratings": None,
            "variations": {
                "sup": {},
                "parawing": {}
            }
        }

    def _build_online_response(self) -> dict:
        """Build response dict for online state."""
        sensor_data = self.cache.get_sensor()
        reading = sensor_data.get("reading") if sensor_data else None
        ratings = sensor_data.get("ratings") if sensor_data else {}
        fetched_at = sensor_data.get("fetched_at") if sensor_data else None

        variations_cache = self.cache.get_all_variations()
        variations = variations_cache.get("variations", {}) if variations_cache else {}

        return {
            "is_offline": False,
            "timestamp": fetched_at,
            "last_known_reading": reading,
            "weather": self._reading_to_weather_dict(reading) if reading else None,
            "ratings": ratings,
            "variations": variations
        }

    def _reading_to_weather_dict(self, reading: SensorReading) -> dict:
        """Convert SensorReading to weather dict for display."""
        return {
            "wind_speed": reading.wind_speed_kts,
            "wind_direction": reading.wind_direction,
            "wind_gust": reading.wind_gust_kts,
            "wind_lull": reading.wind_lull_kts,
            "air_temp": reading.air_temp_f,
            "wave_height": 0,  # No wave data from sensor
            "swell_direction": "N"  # No swell data from sensor
        }

    def get_random_variation(self, mode: str, persona_id: str) -> str:
        """
        Get a random variation for the given mode and persona.

        Handles both online and offline states.

        Args:
            mode: "sup" or "parawing"
            persona_id: e.g., "drill_sergeant"

        Returns:
            Random response string, or fallback if none available.
        """
        # Check if offline
        if self.cache.is_offline():
            variations = self.cache.get_offline_variations(mode, persona_id)
            if variations:
                return random.choice(variations)
            return "Sensor's offline. Can't tell you shit about the conditions right now."

        # Get online variations
        variations = self.cache.get_variations(mode, persona_id)
        if variations:
            return random.choice(variations)

        # Fallback
        ratings = self.cache.get_ratings() or {}
        rating = ratings.get(mode, 0)
        sensor_data = self.cache.get_sensor()
        reading = sensor_data.get("reading") if sensor_data else None

        if reading:
            return (
                f"Conditions: {reading.wind_speed_kts:.1f}kts {reading.wind_direction}. "
                f"Rating: {rating}/10. Figure it out yourself."
            )
        return "No data available. Go look outside."

    def get_foil_recommendations(self, score: Optional[int] = None) -> dict:
        """Get foil recommendations for current conditions."""
        if score is None:
            ratings = self.cache.get_ratings()
            score = ratings.get("sup", 5) if ratings else 5

        return {
            "code": self.foil_recommender.recommend_code(score=score),
            "kt": self.foil_recommender.recommend_kt(score=score)
        }
```

### Step 8.4: Run tests to verify they pass

```bash
pytest tests/test_orchestrator.py::TestSensorFlow -v
```

Expected: All PASS

### Step 8.5: Run all orchestrator tests

```bash
pytest tests/test_orchestrator.py -v
```

Expected: Most pass; some legacy tests may need updating.

### Step 8.6: Update any failing legacy tests

If tests fail because they expect old methods/behavior, update them to work with the new sensor-based flow.

### Step 8.7: Commit

```bash
git add app/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: orchestrator uses SensorClient with offline handling"
```

---

## Task 9: Update UI for Offline State

**Goal:** Display "Sensor Offline" with last-known timestamp when sensor is unavailable.

**Files:**
- Modify: `app/main.py`
- Test: Manual testing

### Step 9.1: Update main.py to handle offline state

The key changes:
1. Check `cached_data["is_offline"]`
2. Display "SENSOR OFFLINE" instead of rating
3. Show last known reading timestamp
4. Display offline persona variation

Update the `update_display` function in `app/main.py`:

```python
def update_display():
    """Update display based on toggle selection using cached data"""
    try:
        mode = 'sup' if toggle.value == 'SUP Foil' else 'parawing'

        if cached_data:
            is_offline = cached_data.get("is_offline", False)

            if is_offline:
                # OFFLINE STATE
                rating_label.content = '<div class="rating" style="color: #999;">OFFLINE</div>'

                # Get offline variation
                description = orchestrator.get_random_variation(mode, current_persona_id)
                description_label.content = f'<div class="description">{description}</div>'

                # Show last known info
                last_known = cached_data.get("last_known_reading")
                if last_known:
                    from datetime import datetime
                    from zoneinfo import ZoneInfo

                    # Calculate how long ago
                    now = datetime.now(timezone.utc)
                    age = now - last_known.timestamp_utc
                    age_minutes = int(age.total_seconds() / 60)

                    if age_minutes < 60:
                        age_str = f"{age_minutes} min ago"
                    else:
                        age_str = f"{age_minutes // 60}h {age_minutes % 60}m ago"

                    timestamp_label.content = (
                        f'<div class="timestamp" style="color: #c00;">'
                        f'Sensor offline - Last reading: {last_known.wind_speed_kts:.0f}kts '
                        f'{last_known.wind_direction} ({age_str})'
                        f'</div>'
                    )
                else:
                    timestamp_label.content = '<div class="timestamp" style="color: #c00;">Sensor offline - No recent data</div>'

                # Hide recommendations when offline
                code_rec.content = '<div class="rec-item">CODE: --</div>'
                kt_rec.content = '<div class="rec-item">KT: --</div>'

            else:
                # ONLINE STATE
                if current_persona_id:
                    score = cached_data['ratings'][mode]
                    description = orchestrator.get_random_variation(mode, current_persona_id)

                    rating_label.content = f'<div class="rating">{score}/10</div>'
                    description_label.content = f'<div class="description">{description}</div>'
                else:
                    rating_label.content = '<div class="rating">N/A</div>'
                    description_label.content = '<div class="description">Weather data unavailable.</div>'

                # Update foil recommendations
                if cached_recommendations:
                    code_rec.content = f'<div class="rec-item">CODE: {cached_recommendations["code"]}</div>'
                    kt_rec.content = f'<div class="rec-item">KT: {cached_recommendations["kt"]}</div>'

                # Update timestamp
                from datetime import datetime
                from zoneinfo import ZoneInfo

                est_time = datetime.now(ZoneInfo("America/New_York"))
                timestamp_label.content = f'<div class="timestamp">Last updated: {est_time.strftime("%I:%M %p")} EST</div>'

        else:
            rating_label.content = '<div class="rating">N/A</div>'
            description_label.content = '<div class="description">Weather data unavailable. Try again later.</div>'

    except Exception as e:
        print(f"UI update error: {e}")
        rating_label.content = '<div class="rating">ERROR</div>'
        description_label.content = '<div class="description">Something broke. Try refreshing.</div>'
```

### Step 9.2: Update the WHY dialog for sensor data

The WHY dialog needs to show sensor-specific info:

```python
def show_why():
    """Populate and show the WHY dialog"""
    conditions_container.clear()

    if cached_data:
        is_offline = cached_data.get("is_offline", False)
        weather_raw = cached_data.get('weather', {})
        timestamp = cached_data.get('timestamp')

        with conditions_container:
            if is_offline:
                ui.label('--- SENSOR OFFLINE ---').style('font-size: 18px; font-weight: bold; color: #c00; margin-bottom: 8px;')

                last_known = cached_data.get("last_known_reading")
                if last_known:
                    ui.label(f"Last reading: {last_known.wind_speed_kts:.1f}kts {last_known.wind_direction}").style('font-size: 14px; color: #666;')
            else:
                # Render crayon graph
                graph = CrayonGraph()
                wind_dir = weather_raw.get('wind_direction', 'N')
                svg = graph.render(wind_direction=wind_dir)

                ui.html(svg, sanitize=False).style('width: 100%; display: flex; justify-content: center; margin: 20px 0;')

                ui.label('--- CONDITIONS ---').style('font-size: 18px; font-weight: bold; margin-bottom: 8px;')
                ui.label(f"Wind: {weather_raw.get('wind_speed', 0):.1f} kts {weather_raw.get('wind_direction', 'N')}").style('font-size: 16px;')

                # Show gust/lull if available
                if weather_raw.get('wind_gust'):
                    ui.label(f"Gusts: {weather_raw['wind_gust']:.1f} kts / Lulls: {weather_raw.get('wind_lull', 0):.1f} kts").style('font-size: 14px; color: #666;')

                if weather_raw.get('air_temp'):
                    ui.label(f"Air Temp: {weather_raw['air_temp']:.0f}°F").style('font-size: 14px; color: #666;')

                # Note about no wave data
                ui.label('Wave/swell data not available from sensor').style('font-size: 12px; color: #999; font-style: italic; margin-top: 8px;')

                if timestamp:
                    ui.label(f"Data from: {timestamp.strftime('%Y-%m-%d %H:%M UTC')}").style('font-size: 12px; color: #666; margin-top: 8px;')
    else:
        with conditions_container:
            ui.label('Weather data unavailable').style('font-size: 16px; color: #666;')

    why_dialog.open()
```

### Step 9.3: Test manually

```bash
python -m app.main
```

Test scenarios:
1. **Normal operation**: Should show rating and description
2. **Simulate offline**: Temporarily set WF_TOKEN to invalid value, should show "SENSOR OFFLINE"
3. **WHY dialog**: Should show sensor data or offline message

### Step 9.4: Commit

```bash
git add app/main.py
git commit -m "feat: UI handles sensor offline state with last-known display"
```

---

## Task 10: Delete NOAA Code

**Goal:** Remove NOAA integration code that's no longer used.

**Files:**
- Delete: `app/weather/sources.py`
- Delete: `app/weather/fetcher.py`
- Delete: `tests/weather/test_sources.py`
- Delete: `tests/weather/test_fetcher.py`
- Modify: Any imports referencing deleted files

### Step 10.1: Search for NOAA references

```bash
grep -r "NOAAClient\|WeatherFetcher\|from app.weather.sources\|from app.weather.fetcher" app/ tests/ --include="*.py"
```

Review output and note all files that need updating.

### Step 10.2: Remove imports from any remaining files

If any files still import from sources.py or fetcher.py, update them.

### Step 10.3: Delete the NOAA files

```bash
rm app/weather/sources.py
rm app/weather/fetcher.py
rm tests/weather/test_sources.py
rm tests/weather/test_fetcher.py
```

### Step 10.4: Run all tests to verify nothing broke

```bash
pytest -v
```

Expected: All tests pass. If tests fail due to missing imports, fix them.

### Step 10.5: Commit

```bash
git add -A
git commit -m "chore: remove NOAA integration code"
```

---

## Task 11: Integration Tests

**Goal:** Add integration tests for the full sensor flow.

**Files:**
- Modify: `tests/integration/test_end_to_end.py`

### Step 11.1: Write integration tests

Add to `tests/integration/test_end_to_end.py`:

```python
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch


class TestSensorIntegration:
    """Integration tests for sensor-based data flow"""

    def test_full_sensor_to_rating_flow(self):
        """Test complete flow: sensor fetch -> rating calc -> variation generation"""
        with patch('app.weather.sensor.requests') as mock_requests, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Mock WeatherFlow API response
            mock_wf_response = MagicMock()
            mock_wf_response.status_code = 200
            mock_wf_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Jupiter-Juno Beach Pier",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "2025-12-10 12:51:16",
                            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            18.0, 14.0, 22.0, 0, "N", 75.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_wf_response

            # Mock LLM response
            mock_llm_response = MagicMock()
            mock_llm_response.text = """===PERSONA:drill_sergeant===
1. Test response for integration.
===PERSONA:disappointed_dad===
1. Dad response here."""
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            # Run the flow
            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test-key")

            result = orchestrator.get_cached_data()

            # Verify result structure
            assert result["is_offline"] is False
            assert result["ratings"]["sup"] >= 1
            assert result["ratings"]["parawing"] >= 1
            assert result["weather"]["wind_speed"] == 18.0
            assert result["weather"]["wind_direction"] == "N"

    def test_offline_flow_when_sensor_returns_stale_data(self):
        """Test offline state when sensor data is stale"""
        with patch('app.weather.sensor.requests') as mock_requests, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Mock stale sensor data (10 min old)
            old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)

            mock_wf_response = MagicMock()
            mock_wf_response.status_code = 200
            mock_wf_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "2025-12-10 12:51:16",
                            old_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            15.0, 12.0, 18.0, 0, "N", 75.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_wf_response

            # Mock offline variations
            mock_llm_response = MagicMock()
            mock_llm_response.text = """===PERSONA:drill_sergeant===
1. Sensor's dead, maggot!"""
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test-key")

            result = orchestrator.get_cached_data()

            assert result["is_offline"] is True
            assert result["last_known_reading"] is not None

    def test_cache_prevents_redundant_llm_calls(self):
        """LLM is not called when rating hasn't changed"""
        with patch('app.weather.sensor.requests') as mock_requests, \
             patch('app.ai.llm_client.genai') as mock_genai:

            # Setup sensor response
            mock_wf_response = MagicMock()
            mock_wf_response.status_code = 200
            mock_wf_response.json.return_value = {
                "status": {"status_code": 0},
                "spots": [{
                    "name": "Test",
                    "data_names": [
                        "timestamp", "utc_timestamp", "avg", "lull", "gust",
                        "dir", "dir_text", "atemp", "wtemp", "pres"
                    ],
                    "stations": [{
                        "data_values": [[
                            "ts", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            18.0, 14.0, 22.0, 0, "N", 75.0, None, 1013.0
                        ]]
                    }]
                }]
            }
            mock_requests.get.return_value = mock_wf_response

            mock_llm_response = MagicMock()
            mock_llm_response.text = "===PERSONA:drill_sergeant===\n1. Test."
            mock_model = MagicMock()
            mock_model.generate_content.return_value = mock_llm_response
            mock_genai.GenerativeModel.return_value = mock_model

            from app.orchestrator import AppOrchestrator
            orchestrator = AppOrchestrator(api_key="test-key")

            # First call - should generate variations
            orchestrator.get_cached_data()
            first_llm_count = mock_model.generate_content.call_count

            # Second call with same rating - should NOT regenerate
            # (sensor cache is fresh, variations cache is fresh, rating same)
            orchestrator.get_cached_data()
            second_llm_count = mock_model.generate_content.call_count

            # LLM should not have been called again
            assert second_llm_count == first_llm_count
```

### Step 11.2: Run integration tests

```bash
pytest tests/integration/test_end_to_end.py -v
```

Expected: All PASS

### Step 11.3: Run full test suite

```bash
pytest -v
```

Expected: All tests pass

### Step 11.4: Commit

```bash
git add tests/integration/test_end_to_end.py
git commit -m "test: integration tests for sensor flow"
```

---

## Task 12: Deploy and Verify

### Step 12.1: Run full test suite

```bash
pytest -v
```

All tests must pass.

### Step 12.2: Update Cloud Run with WF_TOKEN secret

```bash
# Update the Cloud Run service to include the new secret
gcloud run services update canifuckingdownwindtoday \
  --update-secrets=WF_TOKEN=wf-token:latest
```

### Step 12.3: Deploy to Cloud Run

```bash
gcloud run deploy canifuckingdownwindtoday --source .
```

### Step 12.4: Verify in production

1. Visit the live site
2. Check that rating loads (should see real-time sensor data)
3. Toggle between SUP and Parawing
4. Click WHY to see sensor details
5. Verify no "OFFLINE" message (unless sensor is actually down)

### Step 12.5: Check logs for errors

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=canifuckingdownwindtoday AND severity>=WARNING" --limit=20
```

Look for:
- WeatherFlow API errors (could indicate expired token)
- Any unexpected exceptions

### Step 12.6: Compare with iKitesurf

Open https://wx.ikitesurf.com/spot/453 and compare:
- Wind speed should match (within rounding)
- Wind direction should match
- Timestamp should be recent

### Step 12.7: Final commit

```bash
git add -A
git commit -m "docs: mark sensor integration tasks complete"
git push
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `app/weather/sensor.py` | NEW: WeatherFlow API client |
| `app/weather/models.py` | Add SensorReading dataclass |
| `app/weather/sources.py` | DELETED: NOAA client |
| `app/weather/fetcher.py` | DELETED: Was NOAA pass-through |
| `app/config.py` | Add WF_TOKEN, staleness settings |
| `app/cache/manager.py` | Split cache for sensor + variations |
| `app/scoring/calculator.py` | Wind-only scoring methods |
| `app/ai/llm_client.py` | Offline variation generation |
| `app/orchestrator.py` | New sensor-based flow |
| `app/main.py` | Offline state UI |
| `tests/*` | Updated for new behavior |

## Rollback Plan

If issues occur in production:

1. **Expired token**: Update token in GCP Secret Manager
   ```bash
   echo -n "NEW_TOKEN_HERE" | gcloud secrets versions add wf-token --data-file=-
   ```

2. **Sensor API down**: App will show "SENSOR OFFLINE" with last known reading - this is expected behavior

3. **Critical bug**: Revert and redeploy
   ```bash
   git revert HEAD
   gcloud run deploy canifuckingdownwindtoday --source .
   ```

## Token Refresh Reminder

The WeatherFlow token expires ~January 2027. Set a calendar reminder for December 2026 to:

1. Login to https://wx.ikitesurf.com/spot/453
2. Open DevTools > Storage > Cookies
3. Copy `wfToken` value
4. Update in GCP Secret Manager:
   ```bash
   echo -n "NEW_TOKEN" | gcloud secrets versions add wf-token --data-file=-
   ```
