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
    # Coast runs SSE to NNW, so wind parallel to coast is best for downwinding
    OPTIMAL_WIND_DIRECTIONS = ["NNW", "SSE"]  # True along-coast - best
    GOOD_WIND_DIRECTIONS = ["N", "S", "NE", "NNE", "SE"]  # Mostly along-coast - good
    OK_WIND_DIRECTIONS = ["NW", "SW", "SSW"]  # Somewhat cross-shore - acceptable
    BAD_WIND_DIRECTIONS = ["E", "W", "ENE", "ESE", "WNW", "WSW"]  # Cross-shore - bad

    OPTIMAL_WIND_MIN = 17  # knots - sweet spot starts here
    OPTIMAL_WIND_MAX = 30  # knots - still good up to here
    OPTIMAL_WAVE_MIN = 2   # feet
    OPTIMAL_WAVE_MAX = 4   # feet

    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    # Caching
    CACHE_REFRESH_HOURS = int(os.getenv("CACHE_REFRESH_HOURS", "2"))

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

    # Debug mode
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
