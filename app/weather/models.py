# ABOUTME: Data models for weather conditions and forecasts
# ABOUTME: Provides structured representation of wind, waves, and swell data

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


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
    # Optional fields - may not always be available from sensor
    water_temp_f: Optional[float] = None
    pressure_mb: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_description: Optional[str] = None  # e.g., "Light", "Moderate"

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
