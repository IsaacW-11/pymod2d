import pygame
import pymod
from .shape_renderer import ShapeRenderer


class CircleRenderer(ShapeRenderer):
    """Draws a circle. Anchored from its center by default.

    Circles override draw directly since they aren't polygonal, but still use the base's camera transform for the center point and zoom for the radius.

    Attributes:
        radius: Circle radius in world units.
    """

    def __init__(self, radius: float, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius

    def _local_bounds(self):
        d = self.radius * 2
        return (0.0, 0.0, d, d)

    def _world_points(self):
        # not used for drawing, but provides a bounding box for culling
        d = self.radius * 2
        return [(0, 0), (d, 0), (d, d), (0, d)]

    def draw(self) -> None:
        if not self.visible:
            return

        shift = self._anchor_shift()
        # the circle center in local space is at (radius, radius)
        center_screen = self._transform_point(self.radius, self.radius, shift)
        screen_radius = int(self.radius * self._camera_zoom())

        surface = pymod.Game.get().screen.render_surface
        center = (int(center_screen[0]), int(center_screen[1]))

        if self.cull:
            surface_size = pymod.Game.get().screen.render_size
            camera = pymod.Game.get().camera.active
            viewport = camera.get_viewport_rect(surface_size) if camera else pygame.Rect(0, 0, *surface_size)
            circle_rect = pygame.Rect(center[0] - screen_radius, center[1] - screen_radius,
                                      screen_radius * 2, screen_radius * 2)
            if not circle_rect.colliderect(viewport):
                return

        if self.opacity >= 255:
            pygame.draw.circle(surface, self.color, center, screen_radius, self.width)
        else:
            size = screen_radius * 2 + 2
            temp = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(temp, (*self.color, self.opacity),
                               (size // 2, size // 2), screen_radius, self.width)
            surface.blit(temp, (center[0] - size // 2, center[1] - size // 2))