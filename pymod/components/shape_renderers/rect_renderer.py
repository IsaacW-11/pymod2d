import pymod
from .shape_renderer import ShapeRenderer, ShapeAnchor


class RectRenderer(ShapeRenderer):
    """Draws a rectangle. Anchored by default from its center.

    Attributes:
        rect_width: Width of the rectangle in world units.
        rect_height: Height of the rectangle in world units.
    """

    def __init__(self, rect_width: float, rect_height: float, **kwargs):
        super().__init__(**kwargs)
        self.rect_width = rect_width
        self.rect_height = rect_height

    def _local_bounds(self):
        return (0.0, 0.0, self.rect_width, self.rect_height)

    def _world_points(self):
        w, h = self.rect_width, self.rect_height
        return [(0, 0), (w, 0), (w, h), (0, h)]