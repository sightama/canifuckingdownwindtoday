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
