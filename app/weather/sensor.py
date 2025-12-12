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
        self.wf_token = wf_token
        self.spot_id = spot_id or self.DEFAULT_SPOT_ID

    def fetch(self) -> Optional[SensorReading]:
        """
        Fetch current sensor reading from WeatherFlow.

        Returns:
            SensorReading on success, None on any error.
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

        except Exception as e:
            log.error(f"WeatherFlow API request failed: {e}")
            return None

    def _parse_response(self, data: dict) -> Optional[SensorReading]:
        """Parse WeatherFlow API response into SensorReading."""
        try:
            spot = data["spots"][0]
            station = spot["stations"][0]

            field_names = spot["data_names"]
            field_values = station["data_values"][0]
            obs = dict(zip(field_names, field_values))

            utc_str = obs.get("utc_timestamp", "")
            timestamp_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

            # Parse optional fields - may be None or missing
            water_temp = obs.get("wtemp")
            pressure = obs.get("pres")
            humidity = obs.get("humidity")
            wind_desc = obs.get("wind_desc")

            return SensorReading(
                wind_speed_kts=float(obs.get("avg", 0)),
                wind_gust_kts=float(obs.get("gust", 0)),
                wind_lull_kts=float(obs.get("lull", 0)),
                wind_direction=obs.get("dir_text", "N"),
                wind_degrees=int(obs.get("dir", 0)),
                air_temp_f=float(obs.get("atemp", 0)),
                timestamp_utc=timestamp_utc,
                spot_name=spot.get("name", "Unknown"),
                water_temp_f=float(water_temp) if water_temp else None,
                pressure_mb=float(pressure) if pressure else None,
                humidity_pct=float(humidity) if humidity else None,
                wind_description=wind_desc if wind_desc else None,
            )

        except (KeyError, IndexError, TypeError, ValueError) as e:
            log.error(f"WeatherFlow API response parsing failed: {e} - Response: {data}")
            return None
