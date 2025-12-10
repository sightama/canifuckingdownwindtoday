# ABOUTME: Tests for scoring calculation logic
# ABOUTME: Validates SUP and parawing rating algorithms with various conditions

from app.scoring.calculator import ScoreCalculator
from app.weather.models import WeatherConditions


def test_perfect_sup_conditions_get_high_score():
    """
    Perfect SUP conditions: 18kt S wind (parallel to coast), 3ft waves
    Should score 8-10
    """
    conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",  # Optimal - parallel to coast
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 8 <= score <= 10


def test_good_diagonal_wind_direction_scores_well():
    """
    Good conditions: 18kt SE wind (diagonal to coast), 3ft waves
    Should score 7-9
    """
    conditions = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="SE",  # Good - diagonal
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 7 <= score <= 9


def test_marginal_sup_conditions_get_medium_score():
    """Marginal SUP conditions (12kt, 1.5ft) should score 5-7"""
    conditions = WeatherConditions(
        wind_speed_kts=12.0,
        wind_direction="N",  # Optimal direction
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
        wind_direction="S",  # Even with optimal direction, low wind hurts
        wave_height_ft=1.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 3 <= score <= 5


def test_terrible_sup_conditions_get_very_low_score():
    """
    Terrible SUP conditions: 5kt E wind (perpendicular to coast), flat
    Should score 1-2
    """
    conditions = WeatherConditions(
        wind_speed_kts=5.0,
        wind_direction="E",  # Bad - perpendicular to coast
        wave_height_ft=0.5,
        swell_direction="N",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_sup_score(conditions)

    assert 1 <= score <= 2


def test_wrong_wind_direction_lowers_score():
    """
    E/W wind (perpendicular to coast) should significantly lower score
    compared to N/S wind (parallel to coast)
    """
    good_direction = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",  # Optimal - parallel to coast
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    bad_direction = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="E",  # Bad - perpendicular to coast
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    good_score = calculator.calculate_sup_score(good_direction)
    bad_score = calculator.calculate_sup_score(bad_direction)

    assert good_score > bad_score + 3


def test_north_wind_is_as_good_as_south_wind():
    """N and S winds should score similarly (both parallel to coast)"""
    north_wind = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="N",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    south_wind = WeatherConditions(
        wind_speed_kts=18.0,
        wind_direction="S",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    north_score = calculator.calculate_sup_score(north_wind)
    south_score = calculator.calculate_sup_score(south_wind)

    # Should be within 1 point of each other
    assert abs(north_score - south_score) <= 1


# Parawing scoring tests

def test_parawing_requires_more_wind_than_sup():
    """Parawing needs consistent 15kt+ wind"""
    # Conditions that are okay for SUP but bad for parawing
    conditions = WeatherConditions(
        wind_speed_kts=12.0,
        wind_direction="S",  # Optimal direction
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
        wind_direction="S",  # Optimal direction
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
        wind_direction="S",  # Optimal direction
        wave_height_ft=3.0,  # Good waves
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    calculator = ScoreCalculator()
    score = calculator.calculate_parawing_score(conditions)

    assert score <= 4


# Wind-only scoring tests

from app.weather.models import SensorReading
from datetime import datetime, timezone


class TestWindOnlyScoring:
    """Tests for scoring with wind data only (no waves)"""

    def test_calculate_score_wind_only_good_conditions(self):
        """Good wind with no wave data scores reasonably"""
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

        score = calculator.calculate_sup_score_from_sensor(reading)

        # Good wind (18 kts) + good direction (N) should score well
        assert 6 <= score <= 9

    def test_calculate_score_wind_only_light_wind(self):
        """Light wind scores poorly even without wave penalty"""
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

        assert score <= 4

    def test_calculate_score_wind_only_bad_direction(self):
        """Bad wind direction penalizes score"""
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

        assert score <= 6

    def test_parawing_score_wind_only(self):
        """Parawing scoring works with wind-only data"""
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

        assert score >= 7

    def test_parawing_score_tanks_below_15kts(self):
        """Parawing score tanks when wind is below 15 kts"""
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

        assert score <= 4

    def test_calculate_score_with_optional_wave_data(self):
        """When wave data is provided, it affects the score"""
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

        score_no_waves = calculator.calculate_sup_score_from_sensor(reading)
        score_with_waves = calculator.calculate_sup_score_from_sensor(
            reading,
            wave_height_ft=3.0,
            swell_direction="NE"
        )

        assert score_with_waves >= score_no_waves
