# ABOUTME: Generates a hand-drawn style SVG graph showing coast and wind direction
# ABOUTME: Creates wobbly lines that look like a child drew them with crayons

import random
import math
from typing import Literal


LineStyle = Literal["wobbly", "sketchy", "chunky"]


class CrayonGraph:
    """
    Generates a silly hand-drawn SVG showing Florida coast and wind direction.

    The coast runs roughly NNW to SSE (340° to 160°).
    Wind arrow points in the direction wind is going (not coming from).
    """

    # SVG dimensions
    WIDTH = 300
    HEIGHT = 250

    # Coast line runs from top-left-ish to bottom-right-ish
    # Representing NNW to SSE orientation
    COAST_START = (80, 30)
    COAST_END = (220, 220)

    # Wind arrow directions (degrees, 0 = right/east, 90 = down/south)
    DIRECTION_ANGLES = {
        "N": 270,
        "NE": 315,
        "E": 0,
        "SE": 45,
        "S": 90,
        "SW": 135,
        "W": 180,
        "NW": 225,
        "NNW": 247,
        "NNE": 292,
        "ENE": 337,
        "ESE": 22,
        "SSE": 67,
        "SSW": 112,
        "WSW": 157,
        "WNW": 202,
    }

    def __init__(self, line_style: LineStyle = "wobbly"):
        self.line_style = line_style
        # Use fixed seed for consistent look during same session
        # but re-seed each render for slight variation
        self._wobble_amount = 8

    def render(self, wind_direction: str) -> str:
        """
        Render the SVG graph.

        Args:
            wind_direction: Compass direction (N, NE, E, SE, S, SW, W, NW)

        Returns:
            SVG string
        """
        random.seed()  # Re-randomize for each render

        elements = []

        # Coast line (blue)
        coast_path = self._make_wobbly_line(
            self.COAST_START,
            self.COAST_END,
            color="blue",
            stroke_width=4
        )
        elements.append(coast_path)

        # Wind line with arrow (red)
        wind_elements = self._make_wind_arrow(wind_direction)
        elements.extend(wind_elements)

        # Labels
        coast_label = self._make_label("coast", (30, 80), pointer_to=(70, 60))
        wind_label = self._make_label("wind", (200, 180), pointer_to=(160, 140))
        elements.append(coast_label)
        elements.append(wind_label)

        # Assemble SVG
        svg = f'''<svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg" style="background: transparent;">
    {chr(10).join(elements)}
</svg>'''

        return svg

    def _make_wobbly_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str = "blue",
        stroke_width: int = 3
    ) -> str:
        """Generate a wobbly path that looks hand-drawn."""
        x1, y1 = start
        x2, y2 = end

        # Generate intermediate points with wobble
        num_points = 8
        points = []

        for i in range(num_points + 1):
            t = i / num_points
            # Linear interpolation
            x = x1 + (x2 - x1) * t
            y = y1 + (y2 - y1) * t

            # Add wobble (except at endpoints)
            if 0 < i < num_points:
                x += random.uniform(-self._wobble_amount, self._wobble_amount)
                y += random.uniform(-self._wobble_amount, self._wobble_amount)

            points.append((x, y))

        # Create SVG path
        path_d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
        for px, py in points[1:]:
            path_d += f" L {px:.1f} {py:.1f}"

        return f'<path d="{path_d}" stroke="{color}" stroke-width="{stroke_width}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'

    def _make_wind_arrow(self, direction: str) -> list[str]:
        """Generate wind line with arrow head."""
        elements = []

        # Arrow starts near center of graph
        center_x, center_y = 150, 120

        # Get angle for this direction
        angle_deg = self.DIRECTION_ANGLES.get(direction.upper(), 0)
        angle_rad = math.radians(angle_deg)

        # Arrow length
        length = 70

        # Calculate end point
        end_x = center_x + length * math.cos(angle_rad)
        end_y = center_y + length * math.sin(angle_rad)

        # Main arrow line
        arrow_line = self._make_wobbly_line(
            (center_x, center_y),
            (end_x, end_y),
            color="red",
            stroke_width=4
        )
        elements.append(arrow_line)

        # Arrow head (two short lines)
        head_size = 15
        head_angle1 = angle_rad + math.radians(150)
        head_angle2 = angle_rad - math.radians(150)

        head1_end = (
            end_x + head_size * math.cos(head_angle1) + random.uniform(-3, 3),
            end_y + head_size * math.sin(head_angle1) + random.uniform(-3, 3)
        )
        head2_end = (
            end_x + head_size * math.cos(head_angle2) + random.uniform(-3, 3),
            end_y + head_size * math.sin(head_angle2) + random.uniform(-3, 3)
        )

        # Wobbly arrow head lines
        head1 = self._make_wobbly_line((end_x, end_y), head1_end, color="red", stroke_width=3)
        head2 = self._make_wobbly_line((end_x, end_y), head2_end, color="red", stroke_width=3)

        elements.append(head1)
        elements.append(head2)

        return elements

    def _make_label(
        self,
        text: str,
        position: tuple[float, float],
        pointer_to: tuple[float, float]
    ) -> str:
        """Create a hand-written style label with pointer line."""
        x, y = position
        px, py = pointer_to

        # Wobbly pointer line
        pointer = self._make_wobbly_line(
            (x + 20, y - 5),  # Start near text
            pointer_to,
            color="#333",
            stroke_width=2
        )

        # Text (using a casual font)
        text_elem = f'<text x="{x}" y="{y}" font-family="Comic Sans MS, cursive, sans-serif" font-size="16" fill="#333">{text}</text>'

        return f'<g>{pointer}{text_elem}</g>'
