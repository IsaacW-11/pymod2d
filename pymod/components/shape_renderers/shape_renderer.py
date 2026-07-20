from __future__ import annotations
import math
from enum import Enum, auto

import pygame

import pymod


class ShapeAnchor(Enum):
    """Which point of a shape aligns to the owner's world position.

    For rects, this is a point on the bounding box.
    For circles and regular polygons, CENTER aligns the geometric center to the owner position (usually what you want);
    TOP_LEFT aligns the bounding box corner.
    For irregular polygons the points are already absolute offsets from the owner, so anchoring shifts all of them together.
    """
    TOP_LEFT = auto()
    TOP_CENTER = auto()
    TOP_RIGHT = auto()
    CENTER_LEFT = auto()
    CENTER = auto()
    CENTER_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_CENTER = auto()
    BOTTOM_RIGHT = auto()


class ShapeRenderer(pymod.Component):
    """Base class for primitive shape renderers.

    Handles everything common to all shapes:
    applying the active camera's world-to-screen transform (including zoom), color, outline width, opacity, visibility, culling, and anchoring.
    Subclasses only implement _world_points, returning the shape's outline as a list of world-space points, which the base transforms and draws.

    Attributes:
        color: RGB fill or outline color.
        width: Outline thickness in pixels. 0 means filled (default).
        opacity: Alpha 0-255. Applied via a temporary surface so it works for any shape.
        anchor: Which point of the shape aligns to the owner's position.
        offset: Additional visual (x, y) world-space shift before drawing.
        rotation: Rotation in degrees, clockwise, about the anchor point.
        visible: Whether the shape draws at all.
        cull: Whether to skip drawing when off-screen.
    """

    def __init__(
        self,
        color: tuple[int, int, int] = (255, 255, 255),
        width: int = 0,
        opacity: int = 255,
        anchor: ShapeAnchor = ShapeAnchor.CENTER,
        offset: tuple[float, float] = (0.0, 0.0),
        rotation: float = 0.0,
        visible: bool = True,
        cull: bool = True,
    ):
        super().__init__()
        self.color = color
        self.width = width
        self.opacity = opacity
        self.anchor = anchor
        self.offset = offset
        self.rotation = rotation
        self.visible = visible
        self.cull = cull

    # SUBCLASS METHODS

    def _world_points(self) -> list[tuple[float, float]]:
        """Return the shape outline as world-space points, before anchor, offset, and rotation are applied.
        The base class handles those.

        For a filled polygon/rect these are the corners.
        For a circle, _draw is overridden instead since circles aren't polygonal.
        """
        raise NotImplementedError

    def _local_bounds(self) -> tuple[float, float, float, float]:
        """Return (min_x, min_y, width, height) of the raw shape in local space, used for anchor offset computation.
        Local space means relative to the shape's own origin before anchoring.
        """
        raise NotImplementedError

    def _anchor_shift(self) -> tuple[float, float]:
        """How much to shift the shape so the chosen anchor lands on the owner position."""
        min_x, min_y, w, h = self._local_bounds()
        table = {
            ShapeAnchor.TOP_LEFT:      (0,     0),
            ShapeAnchor.TOP_CENTER:    (w / 2, 0),
            ShapeAnchor.TOP_RIGHT:     (w,     0),
            ShapeAnchor.CENTER_LEFT:   (0,     h / 2),
            ShapeAnchor.CENTER:        (w / 2, h / 2),
            ShapeAnchor.CENTER_RIGHT:  (w,     h / 2),
            ShapeAnchor.BOTTOM_LEFT:   (0,     h),
            ShapeAnchor.BOTTOM_CENTER: (w / 2, h),
            ShapeAnchor.BOTTOM_RIGHT:  (w,     h),
        }
        ax, ay = table[self.anchor]
        # shift so the anchor point sits at the owner origin
        return (-(min_x + ax), -(min_y + ay))

    def _transform_point(self, px: float, py: float, shift: tuple[float, float]) -> tuple[float, float]:
        """Apply anchor shift, rotation, offset → world; then camera → screen."""
        # anchor shift
        px += shift[0]
        py += shift[1]

        # rotation about the anchor (which is now at local origin)
        if self.rotation != 0:
            rad = math.radians(self.rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            px, py = px * cos_r - py * sin_r, px * sin_r + py * cos_r

        # into world space
        world_x = self.owner.x + self.offset[0] + px
        world_y = self.owner.y + self.offset[1] + py

        # into screen space
        camera = pymod.Game.get().camera.active
        if camera is not None:
            return camera.world_to_screen(world_x, world_y)
        return (world_x, world_y)

    def _camera_zoom(self) -> float:
        camera = pymod.Game.get().camera.active
        return camera.zoom if camera is not None else 1.0

    def draw(self):
        if not self.visible:
            return

        points = self._world_points()
        if not points:
            return

        shift = self._anchor_shift()
        screen_points = [self._transform_point(px, py, shift) for px, py in points]

        if self.cull and not self._points_on_screen(screen_points):
            return

        surface = pymod.Game.get().screen.render_surface

        if self.opacity >= 255:
            self._draw_polygon(surface, screen_points)
        else:
            self._draw_with_opacity(surface, screen_points)

    def get_world_rect(self) -> pygame.Rect:
        """Get the shape's bounding rect in world space, accounting for anchor and offset.
        Ignores rotation and simply returns the unrotated bounds.

        Used by colliders to auto-size and auto-position themselves to match the shape.
        """
        min_x, min_y, w, h = self._local_bounds()
        shift = self._anchor_shift()
        world_x = self.owner.x + self.offset[0] + min_x + shift[0]
        world_y = self.owner.y + self.offset[1] + min_y + shift[1]
        return pygame.Rect(world_x, world_y, w, h)

    def _draw_polygon(self, surface, screen_points):
        if len(screen_points) < 3:
            # a line or single point — draw as lines
            if len(screen_points) == 2:
                pygame.draw.line(surface, self.color, screen_points[0], screen_points[1], max(1, self.width))
            return
        pygame.draw.polygon(surface, self.color, screen_points, self.width)

    def _draw_with_opacity(self, surface, screen_points):
        """Draw onto a temporary alpha surface so opacity works for any shape."""
        xs = [p[0] for p in screen_points]
        ys = [p[1] for p in screen_points]
        min_x, min_y = int(min(xs)), int(min(ys))
        max_x, max_y = int(max(xs)), int(max(ys))
        w, h = max(1, max_x - min_x), max(1, max_y - min_y)

        temp = pygame.Surface((w, h), pygame.SRCALPHA)
        local = [(px - min_x, py - min_y) for px, py in screen_points]
        if len(local) >= 3:
            pygame.draw.polygon(temp, (*self.color, self.opacity), local, self.width)
        temp.set_alpha(self.opacity)
        surface.blit(temp, (min_x, min_y))

    def _points_on_screen(self, screen_points) -> bool:
        surface_size = pymod.Game.get().screen.render_size
        camera = pymod.Game.get().camera.active
        if camera is not None:
            viewport = camera.get_viewport_rect(surface_size)
        else:
            viewport = pygame.Rect(0, 0, *surface_size)
        xs = [p[0] for p in screen_points]
        ys = [p[1] for p in screen_points]
        bounds = pygame.Rect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        return bounds.colliderect(viewport)

