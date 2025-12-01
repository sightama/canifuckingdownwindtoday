# ABOUTME: Core scoring calculation logic for SUP and parawing modes
# ABOUTME: Converts weather conditions into 1-10 ratings using location-specific rules

from app.weather.models import WeatherConditions
from app.config import Config


class ScoreCalculator:
    """Calculates 1-10 ratings for downwind conditions"""

    def calculate_sup_score(self, conditions: WeatherConditions) -> int:
        """
        Calculate SUP foil score (1-10) based on conditions

        Scoring factors:
        - Wind speed (optimal: 15-25kt)
        - Wind direction (optimal: N/S parallel to coast, bad: E/W perpendicular)
        - Wave height (optimal: 2-4ft)

        Args:
            conditions: Current weather conditions

        Returns:
            Score from 1-10
        """
        score = 5.0  # Start neutral

        # Wind speed scoring (dominant factor for downwind foiling)
        wind = conditions.wind_speed_kts
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
        # Jupiter FL coast runs N-S, so N/S wind is best, E/W is worst
        if conditions.wind_direction in Config.OPTIMAL_WIND_DIRECTIONS:
            score += 1.5  # Perfect direction (N, S - parallel to coast)
        elif conditions.wind_direction in Config.GOOD_WIND_DIRECTIONS:
            score += 0.5  # Good direction (NE, SE, NW, SW - diagonal)
        elif conditions.wind_direction in Config.OK_WIND_DIRECTIONS:
            score += 0  # OK direction (more E/W leaning diagonals)
        elif conditions.wind_direction in Config.BAD_WIND_DIRECTIONS:
            score -= 2  # Bad direction (E, W - perpendicular to coast)
        else:
            score -= 1  # Unknown direction, slight penalty

        # Wave height scoring
        waves = conditions.wave_height_ft
        if Config.OPTIMAL_WAVE_MIN <= waves <= Config.OPTIMAL_WAVE_MAX:
            score += 1  # Perfect waves
        elif 1.5 <= waves < Config.OPTIMAL_WAVE_MIN:
            score += 0.5  # Small but rideable
        elif 1 <= waves < 1.5:
            score -= 0.5  # Very small
        elif waves < 1:
            score -= 1  # Too flat
        elif waves > Config.OPTIMAL_WAVE_MAX:
            score -= 1  # Too big

        # Clamp to 1-10
        return max(1, min(10, int(round(score))))
