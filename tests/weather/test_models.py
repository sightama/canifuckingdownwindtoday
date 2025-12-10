# ABOUTME: Tests for weather data models and structures
# ABOUTME: Validates WeatherConditions and SensorReading data structures

from datetime import datetime, timezone, timedelta
from app.weather.models import WeatherConditions, SensorReading


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
