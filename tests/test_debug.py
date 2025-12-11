# ABOUTME: Tests for debug mode configuration
# ABOUTME: Validates DEBUG env var enables verbose logging

import os
from unittest.mock import patch


def test_debug_mode_disabled_by_default():
    """Debug mode should be disabled when env var not set"""
    # Need to mock dotenv.load_dotenv before reload to prevent .env override
    import dotenv
    original_load_dotenv = dotenv.load_dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: None
    try:
        with patch.dict(os.environ, {}, clear=True):
            # Force reimport to pick up env change
            from importlib import reload
            from app import config
            reload(config)
            assert config.Config.DEBUG is False
    finally:
        dotenv.load_dotenv = original_load_dotenv


def test_debug_mode_enabled_when_env_true():
    """Debug mode should be enabled when DEBUG=true"""
    with patch.dict(os.environ, {"DEBUG": "true"}):
        from importlib import reload
        from app import config
        reload(config)
        assert config.Config.DEBUG is True


def test_debug_mode_enabled_case_insensitive():
    """DEBUG=TRUE (uppercase) should also work"""
    with patch.dict(os.environ, {"DEBUG": "TRUE"}):
        from importlib import reload
        from app import config
        reload(config)
        assert config.Config.DEBUG is True


def test_debug_log_outputs_when_enabled():
    """debug_log should print when DEBUG=true"""
    with patch.dict(os.environ, {"DEBUG": "true"}):
        from importlib import reload
        from app import config
        reload(config)
        from app import debug
        reload(debug)
        import io
        import sys

        captured = io.StringIO()
        sys.stdout = captured
        debug.debug_log("test message")
        sys.stdout = sys.__stdout__

        assert "test message" in captured.getvalue()


def test_debug_log_silent_when_disabled():
    """debug_log should be silent when DEBUG=false"""
    with patch.dict(os.environ, {"DEBUG": "false"}):
        from importlib import reload
        from app import config
        reload(config)
        from app import debug
        reload(debug)
        import io
        import sys

        captured = io.StringIO()
        sys.stdout = captured
        debug.debug_log("test message")
        sys.stdout = sys.__stdout__

        assert captured.getvalue() == ""
