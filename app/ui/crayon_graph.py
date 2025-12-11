import random
import math
from typing import Literal


LineStyle = Literal["wobbly", "sketchy", "chunky"]


class CrayonGraph:
    """
    Generates a silly hand-drawn SVG showing Florida coast and wind direction.

    The coast runs roughly NNW to SSE (340° to 160°).
    Wind direction (e.g., "N") indicates where wind comes FROM.
    Arrow points where wind is GOING (e.g., "N" wind points south/down).
    """

    # SVG dimensions
    WIDTH = 300
    HEIGHT = 250

    # Coast line runs from top-left-ish to bottom-right-ish
    # Representing NNW to SSE orientation
    COAST_START = (80, 30)
    COAST_END = (220, 220)

    # Wind arrow directions (degrees, 0 = right/east, 90 = down/south)
    # Wind direction indicates where wind is COMING FROM, so arrow points opposite
    # (e.g., "N" wind comes from north, so arrow points south/down = 90 degrees)
    DIRECTION_ANGLES = {
        "N": 90, "NE": 135, "E": 180, "SE": 225,
        "S": 270, "SW": 315, "W": 0, "NW": 45,
        "NNW": 67, "NNE": 112, "ENE": 157, "ESE": 202,
        "SSE": 247, "SSW": 292, "WSW": 337, "WNW": 22,
    }

    def __init__(self, line_style: LineStyle = "wobbly"):
        self.line_style = line_style
        # Use fixed seed for consistent look during same session
        # but re-seed each render for slight variation
        self._wobble_amount = 8

    def render(self, wind_direction: str) -> str:
        random.seed()

        texture_elements = []
        drawing_elements = []
        label_elements = []

        # Land texture (left of coast) - crayon-like dots
        texture_elements.extend(self._make_land_texture())

        # Ocean texture (right of coast) - wavy lines
        texture_elements.extend(self._make_ocean_texture())

        # Coast line (blue)
        drawing_elements.append(self._make_wobbly_line(
            self.COAST_START,
            self.COAST_END,
            color="blue",
            stroke_width=4
        ))

        # Wind arrow (red)
        wind_elements = self._make_wind_arrow(wind_direction)
        drawing_elements.extend(wind_elements)

        # Small title at top
        label_elements.append(self._make_title("Coastline / Wind", (150, 18)))

        svg = f'''<svg width="{self.WIDTH}" height="{self.HEIGHT}" xmlns="http://www.w3.org/2000/svg" style="background: transparent;">
        <g id="textures">{chr(10).join(texture_elements)}</g>
        <g id="drawings">{chr(10).join(drawing_elements)}</g>
        <g id="labels">{chr(10).join(label_elements)}</g>
    </svg>'''

        return svg

    def _make_land_texture(self) -> list[str]:
        """Generate crayon-like dots representing land (left of coast)."""
        elements = []
        # Land is to the left/top-left of the coast line
        # Coast goes from (80, 30) to (220, 220)
        # Generate scattered dots in the land area
        land_dots = [
            (30, 60), (50, 90), (25, 120), (45, 150), (60, 180),
            (70, 100), (55, 130), (35, 160), (65, 200), (40, 80),
            (20, 100), (50, 170), (30, 190), (55, 60), (75, 140),
        ]

        for x, y in land_dots:
            # Add slight randomness to position for hand-drawn feel
            x += random.uniform(-3, 3)
            y += random.uniform(-3, 3)
            radius = random.uniform(2, 4)
            # Green/brown dots for land
            color = random.choice(["#5d8a4a", "#7cb05c", "#4a6b3a", "#8b7355"])
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{color}" opacity="0.7"/>'
            )

        return elements

    def _make_ocean_texture(self) -> list[str]:
        """Generate crayon-like waves representing ocean (right of coast)."""
        elements = []
        # Ocean is to the right/bottom-right of the coast line
        # Generate small wavy lines to represent water

        wave_positions = [
            (240, 60), (260, 90), (230, 120), (250, 150), (270, 180),
            (220, 80), (245, 110), (265, 140), (235, 170), (255, 200),
            (275, 100), (240, 190), (260, 50), (280, 130), (225, 145),
        ]

        for x, y in wave_positions:
            # Small wavy line (~15px wide)
            x += random.uniform(-5, 5)
            y += random.uniform(-5, 5)
            # Create a small wave shape
            wave_width = random.uniform(12, 18)
            wave_height = random.uniform(3, 5)
            # Simple sine-like wave using quadratic bezier
            path = f'M {x:.1f} {y:.1f} Q {x + wave_width/4:.1f} {y - wave_height:.1f} {x + wave_width/2:.1f} {y:.1f} Q {x + 3*wave_width/4:.1f} {y + wave_height:.1f} {x + wave_width:.1f} {y:.1f}'
            color = random.choice(["#4a90d9", "#5da5e8", "#3a7bc8", "#6bb5f0"])
            elements.append(
                f'<path d="{path}" stroke="{color}" stroke-width="2" fill="none" opacity="0.6"/>'
            )

        return elements

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

        # Arrow positioned over the water (right/ocean side of coast)
        center_x, center_y = 200, 100

        # Get angle for this direction
        angle_deg = self.DIRECTION_ANGLES.get(direction.upper(), 0)
        angle_rad = math.radians(angle_deg)

        # Arrow length
        length = 85

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

    def _make_label(self, text: str, color: str, position: tuple[float, float]) -> str:
        """Create a simple colored text label (no pointer arrow)."""
        x, y = position
        return f'<text x="{x}" y="{y}" font-family="Comic Sans MS, cursive, sans-serif" font-size="16" fill="{color}" font-weight="600">{text}</text>'

    def _make_title(self, text: str, position: tuple[float, float]) -> str:
        """Create a small centered title."""
        x, y = position
        return f'<text x="{x}" y="{y}" font-family="Comic Sans MS, cursive, sans-serif" font-size="12" fill="#666" text-anchor="middle">{text}</text>'