# ABOUTME: Tests for crayon-style graph generation
# ABOUTME: Verifies SVG output contains required elements

import pytest
from app.ui.crayon_graph import CrayonGraph


class TestCrayonGraph:
    """Tests for the silly hand-drawn graph generator"""

    def test_generates_svg(self):
        """Output should be valid SVG"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert svg.startswith('<svg')
        assert svg.endswith('</svg>')

    def test_contains_coast_line(self):
        """SVG should contain a blue coast line"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        # Check for blue stroke (coast)
        assert 'stroke="blue"' in svg or 'stroke="#' in svg

    def test_contains_wind_line(self):
        """SVG should contain a red wind line"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert 'stroke="red"' in svg or 'stroke="#' in svg

    def test_contains_coast_label(self):
        """SVG should have 'coast' label"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert 'coast' in svg.lower()

    def test_contains_wind_label(self):
        """SVG should have 'wind' label"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert 'wind' in svg.lower()

    def test_wind_direction_affects_arrow(self):
        """Different wind directions should produce different SVGs"""
        graph = CrayonGraph()
        svg_ne = graph.render(wind_direction="NE")
        svg_sw = graph.render(wind_direction="SW")

        # The SVGs should be different (arrow pointing different direction)
        assert svg_ne != svg_sw

    def test_all_eight_directions_work(self):
        """All 8 compass directions should render without error"""
        graph = CrayonGraph()
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

        for direction in directions:
            svg = graph.render(wind_direction=direction)
            assert '<svg' in svg, f"Failed for direction: {direction}"

    def test_wobbly_line_style_default(self):
        """Default line style should be 'wobbly'"""
        graph = CrayonGraph()
        assert graph.line_style == "wobbly"

    def test_can_change_line_style(self):
        """Should be able to set different line styles"""
        graph = CrayonGraph(line_style="sketchy")
        assert graph.line_style == "sketchy"

        graph2 = CrayonGraph(line_style="chunky")
        assert graph2.line_style == "chunky"

    def test_transparent_background(self):
        """SVG should have transparent background (no fill or white fill)"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        # Should not have a solid background rectangle
        # or should have fill="none" or fill="transparent"
        assert 'fill="white"' not in svg or 'fill="none"' in svg
