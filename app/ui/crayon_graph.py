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
        "N": 270, "NE": 315, "E": 0, "SE": 45,
        "S": 90, "SW": 135, "W": 180, "NW": 225,
        "NNW": 247, "NNE": 292, "ENE": 337, "ESE": 22,
        "SSE": 67, "SSW": 112, "WSW": 157, "WNW": 202,
    }

    def __init__(self, line_style: LineStyle = "wobbly"):
        self.line_style = line_style
        # Use fixed seed for consistent look during same session
        # but re-seed each render for slight variation
        self._wobble_amount = 8

    def render(self, wind_direction: str) -> str:
        random.seed()

        drawing_elements = []
        label_elements = []

        drawing_elements.append(self._make_wobbly_line(
            self.COAST_START,
            self.COAST_END,
            color="blue",
            stroke_width=4
        ))
        
        wind_elements = self._make_wind_arrow(wind_direction)
        drawing_elements.extend(wind_elements)

        label_elements.append(self._make_label("coast", (20, 80), pointer_to=(70, 60)))
        label_elements.append(self._make_label("wind", (220, 180), pointer_to=(160, 140)))

        svg = f'''<svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg" style="background: transparent;">
        <g id="drawings">{chr(10).join(drawing_elements)}</g>
        <g id="labels">{chr(10).join(label_elements)}</g>
    </svg>'''

        return svg

    def _make_straight_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str = "blue",
        stroke_width: int = 3
    ) -> str:
        """Generate a straight line."""
        x1, y1 = start
        x2, y2 = end
        return f'<path d="M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="{stroke_width}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'

    def _make_wobbly_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str = "blue",
        stroke_width: int = 3
    ) -> str:
        """Generate a path that looks hand-drawn based on current line_style."""
        if self.line_style == "sketchy":
            return self._make_sketchy_line(start, end, color, stroke_width)
        elif self.line_style == "chunky":
            return self._make_chunky_line(start, end, color, stroke_width)
        else:  # wobbly (default)
            return self._make_wobbly_line_impl(start, end, color, stroke_width)

    def _make_wobbly_line_impl(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str = "blue",
        stroke_width: int = 3
    ) -> str:
        """Generate a wobbly path that looks hand-drawn."""
        x1, y1 = start
        x2, y2 = end

        # 1. Calculate vector length and direction
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        
        if length < 0.1:
             return ""

        # 2. Calculate Unit vectors
        ux = dx / length
        uy = dy / length
        
        # 3. Calculate Perpendicular vector (normal)
        # We will apply wobble along THIS vector, so it never goes backwards
        nx = -uy
        ny = ux

        num_points = 8
        points = []

        for i in range(num_points + 1):
            t = i / num_points
            
            # Base point on the straight line
            bx = x1 + dx * t
            by = y1 + dy * t
            
            # Add wobble only perpendicular to the line direction
            if 0 < i < num_points:
                offset = random.uniform(-self._wobble_amount, self._wobble_amount)
                px = bx + (nx * offset)
                py = by + (ny * offset)
            else:
                px, py = bx, by

            points.append((px, py))

        # Create SVG path
        path_d = f"M {points[0][0]:.1f} {points[0][1]:.1f}"
        for px, py in points[1:]:
            path_d += f" L {px:.1f} {py:.1f}"

        return f'<path d="{path_d}" stroke="{color}" stroke-width="{stroke_width}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'

    def _make_sketchy_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str,
        stroke_width: int
    ) -> str:
        """Multiple overlapping strokes like scribbling."""
        paths = []
        for i in range(3):
            offset = (i - 1) * 2
            adjusted_start = (start[0] + offset, start[1] + offset)
            adjusted_end = (end[0] + offset, end[1] - offset)
            path = self._make_wobbly_line_impl(
                adjusted_start,
                adjusted_end,
                color,
                stroke_width - 1
            )
            paths.append(path)
        return '\n'.join(paths)

    def _make_chunky_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: str,
        stroke_width: int
    ) -> str:
        """Thick irregular line like a fat crayon."""
        old_wobble = self._wobble_amount
        self._wobble_amount = 12
        path = self._make_wobbly_line_impl(start, end, color, stroke_width + 4)
        self._wobble_amount = old_wobble
        return path

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
            end_x + head_size * math.cos(head_angle1),
            end_y + head_size * math.sin(head_angle1)
        )
        head2_end = (
            end_x + head_size * math.cos(head_angle2),
            end_y + head_size * math.sin(head_angle2)
        )

        # Straight arrow head lines
        head1 = self._make_straight_line((end_x, end_y), head1_end, color="red", stroke_width=3)
        head2 = self._make_straight_line((end_x, end_y), head2_end, color="red", stroke_width=3)

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

        # Determine start position
        if text == 'coast':
            start_pos = (x + 20, y + 20)
        else:
            start_pos = (x + 20, y - 20)

        # Wobbly pointer line
        pointer = self._make_wobbly_line(
            start_pos,
            pointer_to,
            color="#333",
            stroke_width=2
        )

        # Arrow head
        dx = px - start_pos[0]
        dy = py - start_pos[1]
        angle_rad = math.atan2(dy, dx)

        head_size = 12
        head_angle1 = angle_rad + math.radians(150)
        head_angle2 = angle_rad - math.radians(150)

        head1_end = (
            px + head_size * math.cos(head_angle1),
            py + head_size * math.sin(head_angle1)
        )
        head2_end = (
            px + head_size * math.cos(head_angle2),
            py + head_size * math.sin(head_angle2)
        )

        head1 = self._make_straight_line(pointer_to, head1_end, color="#333", stroke_width=2)
        head2 = self._make_straight_line(pointer_to, head2_end, color="#333", stroke_width=2)

        # Text (using a casual font)
        text_elem = f'<text x="{x}" y="{y}" font-family="Comic Sans MS, cursive, sans-serif" font-size="16" fill="#3d3d3d" font-weight="600">{text}</text>'

        return f'<g>{pointer}{head1}{head2}{text_elem}</g>'