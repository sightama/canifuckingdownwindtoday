# ABOUTME: Core scoring calculation logic for SUP and parawing modes
# ABOUTME: Converts weather conditions into 1-10 ratings using location-specific rules

import logging
from typing import Optional
from app.weather.models import WeatherConditions, SensorReading
from app.config import Config

log = logging.getLogger(__name__)

# Perfect conditions thresholds (11/10 day)
# Coast runs SSE-NNW, so optimal wind is along-coast with good swell
PERFECT_WIND_DIRECTIONS = {"NNW", "SSE", "N", "S", "NE", "NNE", "SE"}
PERFECT_WIND_SPEED_MIN = 17.0
PERFECT_WIND_SPEED_MAX = 30.0
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

        Scoring philosophy: Wind is THE dominant factor. Direction only matters
        when wind is sufficient (>= 15 kts). Below that, you can't really
        do a proper downwinder regardless of direction.

        Target scores:
        - 8 kts optimal dir: 2/10
        - 12 kts optimal dir: 3-4/10
        - 15 kts optimal dir: 7/10
        - 17 kts optimal dir: 9-10/10
        - 17-30 kts optimal dir + good swell: 10-11/10

        Args:
            conditions: Current weather conditions

        Returns:
            Score from 1-10 (or 11 for perfect conditions)
        """
        score = 1.0  # Base score

        wind = conditions.wind_speed_kts

        # Wind speed scoring (dominant factor)
        if wind < 10:
            score += 1  # Too light - barely worth checking
        elif 10 <= wind < 12:
            score += 2  # Light - challenging
        elif 12 <= wind < 15:
            score += 3  # Marginal - doable but not great
        elif 15 <= wind < 17:
            score += 5  # Good - solid session
        elif 17 <= wind <= Config.OPTIMAL_WIND_MAX:
            score += 7  # Optimal - prime conditions
        else:  # > 30 kts
            score += 5  # Too strong - getting scary

        # Direction bonus - ONLY applies when wind is rideable (>= 15 kts)
        if wind >= 15:
            if conditions.wind_direction in Config.OPTIMAL_WIND_DIRECTIONS:
                score += 2  # Perfect direction (NNW, SSE - true along-coast)
            elif conditions.wind_direction in Config.GOOD_WIND_DIRECTIONS:
                score += 1  # Good direction (N, S, NE, NNE, SE)
            elif conditions.wind_direction in Config.OK_WIND_DIRECTIONS:
                score += 0  # OK direction (NW, SW, SSW)
            elif conditions.wind_direction in Config.BAD_WIND_DIRECTIONS:
                score -= 2  # Bad direction (E, W, cross-shore)
            else:
                score -= 1  # Unknown direction

        # Wave height scoring
        waves = conditions.wave_height_ft
        if Config.OPTIMAL_WAVE_MIN <= waves <= Config.OPTIMAL_WAVE_MAX:
            score += 1  # Perfect waves
        elif 1.5 <= waves < Config.OPTIMAL_WAVE_MIN:
            score += 0.5  # Small but rideable
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

    def calculate_sup_score_from_sensor(
        self,
        reading: SensorReading,
        wave_height_ft: Optional[float] = None,
        swell_direction: Optional[str] = None
    ) -> int:
        """
        Calculate SUP foil score from sensor reading.
        Wind is the primary factor. Wave data is optional.
        Direction bonus only applies when wind >= 15 kts.
        """
        score = 1.0  # Base score

        wind = reading.wind_speed_kts

        # Wind speed scoring (dominant factor)
        if wind < 10:
            score += 1  # Too light
        elif 10 <= wind < 12:
            score += 2  # Light - challenging
        elif 12 <= wind < 15:
            score += 3  # Marginal
        elif 15 <= wind < 17:
            score += 5  # Good
        elif 17 <= wind <= Config.OPTIMAL_WIND_MAX:
            score += 7  # Optimal
        else:  # > 30 kts
            score += 5  # Too strong

        # Direction bonus - ONLY applies when wind is rideable (>= 15 kts)
        if wind >= 15:
            if reading.wind_direction in Config.OPTIMAL_WIND_DIRECTIONS:
                score += 2  # Perfect (NNW, SSE)
            elif reading.wind_direction in Config.GOOD_WIND_DIRECTIONS:
                score += 1  # Good (N, S, NE, NNE, SE)
            elif reading.wind_direction in Config.OK_WIND_DIRECTIONS:
                score += 0  # OK (NW, SW, SSW)
            elif reading.wind_direction in Config.BAD_WIND_DIRECTIONS:
                score -= 2  # Bad (E, W, cross-shore)
            else:
                score -= 1  # Unknown

        # Wave modifier (when available)
        if wave_height_ft is not None:
            if Config.OPTIMAL_WAVE_MIN <= wave_height_ft <= Config.OPTIMAL_WAVE_MAX:
                score += 1
            elif 1.5 <= wave_height_ft < Config.OPTIMAL_WAVE_MIN:
                score += 0.5
            elif wave_height_ft > Config.OPTIMAL_WAVE_MAX:
                score -= 1

        return max(1, min(10, int(round(score))))

    def calculate_parawing_score_from_sensor(
        self,
        reading: SensorReading,
        wave_height_ft: Optional[float] = None,
        swell_direction: Optional[str] = None
    ) -> int:
        """
        Calculate parawing score from sensor reading.
        Parawing requires more wind - below 15kt is essentially un-rideable.
        """
        score = float(self.calculate_sup_score_from_sensor(reading, wave_height_ft, swell_direction))

        wind = reading.wind_speed_kts
        if wind < 15:
            score = min(score, 4)
            score -= (15 - wind) * 0.5
        elif wind >= 18:
            score += 1

        if wind >= 18 and wave_height_ft is not None and wave_height_ft >= 1.5:
            score += 0.5

        return max(1, min(10, int(round(score))))
