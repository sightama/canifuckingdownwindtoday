# ABOUTME: Foil setup recommendations based on current conditions
# ABOUTME: Provides CODE and KT brand equipment suggestions for wind/wave combos

from app.weather.models import WeatherConditions


class FoilRecommender:
    """Recommends foil setups based on conditions"""

    def recommend_code(self, conditions: WeatherConditions) -> str:
        """
        Recommend CODE foil setup based on conditions

        Args:
            conditions: Current weather conditions

        Returns:
            Setup string (e.g., "960r + 135r stab + short fuse")
        """
        # Small conditions: 8-14kt, 1-2ft bumps
        if conditions.wind_speed_kts < 15 and conditions.wave_height_ft < 2.5:
            return "1250r + 135r stab + short fuse"

        # Normal/good conditions: 15+kt, 2-4ft bumps
        return "960r + 135r stab + short fuse"

    def recommend_kt(self, conditions: WeatherConditions) -> str:
        """
        Recommend KT foil setup based on conditions

        Args:
            conditions: Current weather conditions

        Returns:
            Setup string
        """
        # Small conditions
        if conditions.wind_speed_kts < 15 and conditions.wave_height_ft < 2.5:
            return "Ginxu 1150 + Stabilizer M"

        # Normal/good conditions
        return "Ginxu 950 + Stabilizer M"
