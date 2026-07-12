import math
import pymod
from .shape_renderer import ShapeRenderer


class RegularPolygonRenderer(ShapeRenderer):
    """Draws a regular polygon (equal sides) — triangle, pentagon, hexagon etc.

    Anchored from its center by default.

    Attributes:
        sides: Number of sides (3 = triangle, 6 = hexagon, ...).
        radius: Distance from center to each vertex, in world units.
    """

    def __init__(self, sides: int, radius: float, **kwargs):
        super().__init__(**kwargs)
        self.sides = max(3, sides)
        self.radius = radius

    def _local_bounds(self):
        d = self.radius * 2
        return (0.0, 0.0, d, d)

    def _world_points(self):
        pts = []
        for i in range(self.sides):
            # start pointing up, distribute evenly
            angle = math.radians(-90 + (360 / self.sides) * i)
            x = self.radius + math.cos(angle) * self.radius
            y = self.radius + math.sin(angle) * self.radius
            pts.append((x, y))
        return pts


class PolygonRenderer(ShapeRenderer):
    """Draws an irregular polygon from an explicit list of points.

    Points are in world units relative to the shape origin. Anchoring shifts them all together based on their collective bounding box.

    Attributes:
        points: List of (x, y) vertices defining the polygon outline.
    """

    def __init__(self, points: list[tuple[float, float]], **kwargs):
        super().__init__(**kwargs)
        self.points = points

    def _local_bounds(self):
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x, min_y = min(xs), min(ys)
        return (min_x, min_y, max(xs) - min_x, max(ys) - min_y)

    def _world_points(self):
        return list(self.points)