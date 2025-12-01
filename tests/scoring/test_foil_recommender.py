# ABOUTME: Tests for foil setup recommendation logic
# ABOUTME: Validates CODE and KT foil recommendations based on conditions

from app.scoring.foil_recommender import FoilRecommender
from app.weather.models import WeatherConditions


def test_small_conditions_recommend_large_wing():
    """Small conditions (8-14kt, 1-2ft) should recommend large wing"""
    conditions = WeatherConditions(
        wind_speed_kts=10.0,
        wind_direction="S",
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
        wind_direction="S",
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
        wind_direction="S",
        wave_height_ft=3.0,
        swell_direction="S",
        timestamp="2025-11-26T14:30:00"
    )

    recommender = FoilRecommender()
    kt_setup = recommender.recommend_kt(conditions)

    assert kt_setup is not None
    assert len(kt_setup) > 0
