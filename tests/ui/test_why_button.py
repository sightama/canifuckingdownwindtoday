# ABOUTME: Tests for WHY button styling and positioning
# ABOUTME: Verifies button text, styles, and placement in content flow


class TestWhyButton:
    """Tests for the EXPLAIN YOURSELF button"""

    def test_button_text_is_explain_yourself(self):
        """Button should say 'EXPLAIN YOURSELF' not 'WHY'"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        assert "EXPLAIN YOURSELF" in content
        # Old text should NOT be present as a button label
        assert "ui.button('WHY')" not in content

    def test_button_not_absolutely_positioned(self):
        """Button should NOT be in an absolutely positioned container"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # The old pattern had a div with absolute positioning
        # This pattern should no longer exist
        assert "position: absolute; top: 20px; right: 20px;" not in content

    def test_button_has_border_style(self):
        """Button should have black border (matching toggle style)"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # Should have border style like the toggle
        assert "border: 2px solid black" in content

    def test_button_appears_after_description(self):
        """Button should appear in content flow after description, before timestamp"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # Find positions of key elements
        description_pos = content.find('description_label = ')
        button_pos = content.find("EXPLAIN YOURSELF")
        timestamp_pos = content.find('timestamp_label = ')

        assert description_pos != -1, "Could not find description_label"
        assert button_pos != -1, "Could not find EXPLAIN YOURSELF button"
        assert timestamp_pos != -1, "Could not find timestamp_label"

        # Button should come after description and before timestamp
        assert description_pos < button_pos < timestamp_pos, \
            f"Button should be between description and timestamp. " \
            f"Found: description={description_pos}, button={button_pos}, timestamp={timestamp_pos}"

    def test_button_has_hover_behavior(self):
        """Button should invert colors on hover"""
        with open('app/main.py', 'r') as f:
            content = f.read()

        # Should have mouseover handler for hover effect
        assert "mouseover" in content or "hover" in content.lower()
