# ABOUTME: Core scoring calculation logic for SUP and parawing modes
# ABOUTME: Converts weather conditions into 1-10 ratings using location-specific rules

import logging
from app.weather.models import WeatherConditions
from app.config import Config

log = logging.getLogger(__name__)

# Perfect conditions thresholds (11/10 day)
PERFECT_WIND_DIRECTIONS = {"NNW", "NW", "SSE", "SE"}
PERFECT_WIND_SPEED_MIN = 14.0
PERFECT_WIND_SPEED_MAX = 20.0
PERFECT_SWELL_DIRECTION = "NE"
PERFECT_WAVE_HEIGHT_MIN = 2.0
PERFECT_WAVE_HEIGHT_MAX = 4.0


class ScoreCalculator:
    """Calculates 1-10 ratings for downwind conditions"""

    def _is_perfect_conditions(self, conditions: WeatherConditions) -> bool:
        """
        Check if conditions meet the criteria for 11/10 perfect post-frontal day.

        Perfect conditions require:
        - Wind direction: NNW, NW, SSE, or SE
        - Wind speed: 14-20 kts
        - Swell direction: NE
        - Wave height: 2-4 ft

        Args:
            conditions: Current weather conditions

        Returns:
            True if all perfect condition criteria are met
        """
        return (
            conditions.wind_direction in PERFECT_WIND_DIRECTIONS
            and PERFECT_WIND_SPEED_MIN <= conditions.wind_speed_kts <= PERFECT_WIND_SPEED_MAX
            and conditions.swell_direction == PERFECT_SWELL_DIRECTION
            and PERFECT_WAVE_HEIGHT_MIN <= conditions.wave_height_ft <= PERFECT_WAVE_HEIGHT_MAX
        )

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
        base_score = max(1, min(10, int(round(score))))

        # Check for perfect post-frontal conditions (11/10 day)
        if self._is_perfect_conditions(conditions):
            log.info(f"Perfect conditions detected! Base score: {base_score}, elevated to 11/10")
            return 11

        return base_score

    def calculate_parawing_score(self, conditions: WeatherConditions) -> int:
        """
        Calculate parawing (trashbagger) score (1-10) based on conditions

        Parawing requires more consistent wind than SUP foil.
        Below 15kt is essentially un-rideable.

        Args:
            conditions: Current weather conditions

        Returns:
            Score from 1-10
        """
        # Start with SUP score as baseline
        score = float(self.calculate_sup_score(conditions))

        # Apply stricter wind requirements for parawing
        wind = conditions.wind_speed_kts
        if wind < 15:
            # Tank the score for insufficient wind
            score = min(score, 4)
            score -= (15 - wind) * 0.5  # Penalize heavily for low wind
        elif wind >= 18:
            # Bonus for strong consistent wind
            score += 1

        # Parawing is slightly more forgiving on wave height
        # (can ride smaller bumps with strong wind)
        if wind >= 18 and conditions.wave_height_ft >= 1.5:
            score += 0.5

        # Clamp to 1-10
        return max(1, min(10, int(round(score))))
