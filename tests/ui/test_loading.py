# ABOUTME: Tests for loading overlay UI behavior
# ABOUTME: Verifies loading state is shown before content

import pytest


class TestLoadingOverlay:
    """Tests for loading screen behavior"""

    def test_loading_overlay_css_includes_pulse_animation(self):
        """Verify the pulse animation is defined"""
        # Read the main.py file and verify the animation exists
        with open('app/main.py', 'r') as f:
            content = f.read()

        assert '@keyframes pulse' in content
        assert 'animation: pulse' in content

    def test_loading_text_is_loading(self):
        """Loading text should be 'LOADING' (not something else)"""
        # Read the main.py file and verify the text
        with open('app/main.py', 'r') as f:
            content = f.read()

        assert 'LOADING' in content

    def test_loading_overlay_element_exists(self):
        """Verify loading-overlay element is in the HTML"""
        # Read the main.py file and verify the overlay exists
        with open('app/main.py', 'r') as f:
            content = f.read()

        assert 'loading-overlay' in content
