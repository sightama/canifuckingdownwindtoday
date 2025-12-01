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
