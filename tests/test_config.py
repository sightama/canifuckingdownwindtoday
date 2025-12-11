# ABOUTME: Tests for application configuration and location settings
# ABOUTME: Validates Jupiter FL coordinates and weather API configuration

from app.config import Config


def test_config_has_jupiter_coordinates():
    """Jupiter, FL coordinates should be defined"""
    assert Config.LOCATION_LAT == 26.9
    assert Config.LOCATION_LON == -80.1


def test_config_has_location_name():
    """Location name should be Jupiter FL"""
    assert Config.LOCATION_NAME == "Jupiter, FL"


def test_config_has_cache_refresh_hours():
    """Cache refresh interval should be configurable"""
    assert Config.CACHE_REFRESH_HOURS >= 1
    assert Config.CACHE_REFRESH_HOURS <= 24


def test_config_has_correct_wind_directions_for_jupiter():
    """
    Jupiter FL coast runs SSE to NNW, so optimal wind follows the coast.
    Best: NNW, SSE (true along-coast - pushes along the run)
    Good: N, S, NE, NNE, SE (mostly along-coast with diagonal component)
    OK: NW, SW, SSW (somewhat cross-shore)
    Bad: E, W, ENE, ESE, WNW, WSW (cross-shore)
    """
    # Best directions should be NNW and SSE (true along-coast)
    assert "NNW" in Config.OPTIMAL_WIND_DIRECTIONS
    assert "SSE" in Config.OPTIMAL_WIND_DIRECTIONS

    # Good directions should include N, S and east-leaning diagonals
    assert "N" in Config.GOOD_WIND_DIRECTIONS
    assert "S" in Config.GOOD_WIND_DIRECTIONS
    assert "NE" in Config.GOOD_WIND_DIRECTIONS
    assert "NNE" in Config.GOOD_WIND_DIRECTIONS
    assert "SE" in Config.GOOD_WIND_DIRECTIONS

    # OK directions (somewhat cross-shore)
    assert "NW" in Config.OK_WIND_DIRECTIONS
    assert "SW" in Config.OK_WIND_DIRECTIONS
    assert "SSW" in Config.OK_WIND_DIRECTIONS

    # Bad directions should NOT be in optimal or good
    assert "E" not in Config.OPTIMAL_WIND_DIRECTIONS
    assert "W" not in Config.OPTIMAL_WIND_DIRECTIONS
    assert "E" not in Config.GOOD_WIND_DIRECTIONS
    assert "W" not in Config.GOOD_WIND_DIRECTIONS

    # Bad directions should be explicitly listed
    assert "E" in Config.BAD_WIND_DIRECTIONS
    assert "W" in Config.BAD_WIND_DIRECTIONS


class TestSensorConfig:
    """Tests for sensor-related configuration"""

    def test_wf_token_from_environment(self):
        """WF_TOKEN is read from environment"""
        import os
        from importlib import reload

        # Set env var
        os.environ["WF_TOKEN"] = "test-token-123"

        # Reload config to pick up new env var
        import app.config
        reload(app.config)
        from app.config import Config

        assert Config.WF_TOKEN == "test-token-123"

        # Cleanup
        del os.environ["WF_TOKEN"]

    def test_sensor_stale_threshold_default(self):
        """SENSOR_STALE_THRESHOLD_SECONDS has sensible default"""
        from app.config import Config

        # Default is 300 seconds (5 minutes)
        assert Config.SENSOR_STALE_THRESHOLD_SECONDS == 300

    def test_sensor_cache_ttl_default(self):
        """SENSOR_CACHE_TTL_SECONDS has sensible default"""
        from app.config import Config

        # Default is 120 seconds (2 minutes)
        assert Config.SENSOR_CACHE_TTL_SECONDS == 120

    def test_wf_spot_id_default(self):
        """WF_SPOT_ID defaults to Jupiter-Juno Beach Pier"""
        from app.config import Config

        assert Config.WF_SPOT_ID == "453"
