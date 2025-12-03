# ABOUTME: Tests for 11/10 perfect post-frontal conditions detection
# ABOUTME: Verifies the specific combination that triggers an 11/10 rating

import pytest
from app.weather.models import WeatherConditions
from app.scoring.calculator import ScoreCalculator


class TestPerfectConditions:
    """Tests for 11/10 'perfect post-frontal' detection"""

    def setup_method(self):
        self.calculator = ScoreCalculator()

    def test_112825_perfect_conditions(self):
        """
        Test case named after Nov 28, 2025 - a perfect post-frontal day.
        NW wind + NE swell + good wave height + right wind speed = 11/10
        """
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-11-28T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11

    def test_perfect_with_nnw_wind(self):
        """NNW wind direction also triggers 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=15.0,
            wind_direction="NNW",
            wave_height_ft=2.5,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11

    def test_perfect_with_sse_wind(self):
        """SSE wind direction also triggers 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=18.0,
            wind_direction="SSE",
            wave_height_ft=3.5,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11

    def test_perfect_with_se_wind(self):
        """SE wind direction also triggers 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=17.0,
            wind_direction="SE",
            wave_height_ft=2.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11

    def test_not_perfect_wrong_wind_direction(self):
        """West wind (offshore) does NOT trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="W",  # Not in allowed list
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score <= 10

    def test_not_perfect_wrong_swell_direction(self):
        """Without NE swell, no 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="S",  # Not NE
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score <= 10

    def test_not_perfect_wind_too_light(self):
        """Wind under 14 kts doesn't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=12.0,  # Below 14
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score <= 10

    def test_not_perfect_wind_too_strong(self):
        """Wind over 20 kts doesn't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=22.0,  # Above 20
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score <= 10

    def test_not_perfect_waves_too_small(self):
        """Waves under 2ft don't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=1.5,  # Below 2
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score <= 10

    def test_not_perfect_waves_too_big(self):
        """Waves over 4ft don't trigger 11/10"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=5.0,  # Above 4
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score <= 10

    def test_parawing_mode_never_gets_11(self):
        """11/10 only applies to SUP mode, not parawing"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_parawing_score(conditions)

        assert score <= 10

    def test_boundary_wind_speed_14_triggers(self):
        """Exactly 14 kts should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=14.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11

    def test_boundary_wind_speed_20_triggers(self):
        """Exactly 20 kts should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=20.0,
            wind_direction="NW",
            wave_height_ft=3.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11

    def test_boundary_wave_height_2_triggers(self):
        """Exactly 2ft waves should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=2.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11

    def test_boundary_wave_height_4_triggers(self):
        """Exactly 4ft waves should trigger"""
        conditions = WeatherConditions(
            wind_speed_kts=16.0,
            wind_direction="NW",
            wave_height_ft=4.0,
            swell_direction="NE",
            timestamp="2025-01-01T10:00:00"
        )

        score = self.calculator.calculate_sup_score(conditions)

        assert score == 11
