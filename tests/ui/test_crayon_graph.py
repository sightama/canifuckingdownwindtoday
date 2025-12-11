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

    def test_contains_title(self):
        """SVG should have a title"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        assert 'Coastline' in svg or 'Wind' in svg

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

    def test_no_pointer_arrows(self):
        """SVG should not have black pointer arrows"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        # Should NOT have black/gray pointer lines
        assert 'stroke="#333"' not in svg

    def test_has_land_texture(self):
        """SVG should have land texture (dots/circles) left of coast"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        # Should have some land representation (circles or dots)
        assert '<circle' in svg or 'land' in svg.lower()

    def test_has_ocean_texture(self):
        """SVG should have ocean texture right of coast"""
        graph = CrayonGraph()
        svg = graph.render(wind_direction="NE")

        # Should have ocean representation (waves or similar)
        assert 'ocean' in svg.lower() or 'wave' in svg.lower() or svg.count('<path') > 3

    def test_north_wind_points_south(self):
        """Wind from North should point arrow SOUTH (down)"""
        import re
        graph = CrayonGraph()
        svg = graph.render(wind_direction="N")

        # Extract the wind arrow end point from SVG
        # The arrow starts at (200, 100) - if pointing south, end_y > 100
        # Look for the red path that forms the arrow
        red_paths = re.findall(r'<path d="M ([0-9.]+) ([0-9.]+) L ([0-9.]+) ([0-9.]+)', svg)

        # Find a red path (wind arrow)
        wind_arrow_found = False
        for match in red_paths:
            start_x, start_y, end_x, end_y = map(float, match)
            # Arrow starts near (200, 100)
            if abs(start_x - 200) < 10 and abs(start_y - 100) < 10:
                # If pointing south, end_y should be GREATER than start_y
                assert float(end_y) > float(start_y), f"North wind should point south (down), but end_y={end_y} <= start_y={start_y}"
                wind_arrow_found = True
                break

        assert wind_arrow_found, "Could not find wind arrow in SVG"
