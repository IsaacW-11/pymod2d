from __future__ import annotations
import pygame
import pymod
from .collider import Collider


class CircleCollider(Collider):
    """A circular collider.

    If radius is left as None, it is auto-sized to half the larger dimension of the owner's SpriteRenderer at start.

    Attributes:
        radius: Collider radius in world units, or None to match the sprite.
    """

    def __init__(self, radius: float | None = None, **kwargs):
        super().__init__(**kwargs)
        self.radius = radius

    def on_start(self) -> None:
        if self.radius is None:
            self._auto_size_from_sprite()
        super().on_start()

    def _auto_size_from_sprite(self) -> None:
        from ..sprite_renderer import SpriteRenderer
        renderer = self.owner.get_component(SpriteRenderer)
        if renderer is not None:
            rect = renderer.get_world_rect()
            self.radius = max(rect.width, rect.height) / 2
        else:
            self.radius = 16

    @property
    def center(self) -> tuple[float, float]:
        return (self.owner.x + self.offset[0], self.owner.y + self.offset[1])

    def get_bounds(self) -> pygame.Rect:
        cx, cy = self.center
        return pygame.Rect(cx - self.radius, cy - self.radius, self.radius * 2, self.radius * 2)

    def _debug_draw(self) -> None:
        camera = pymod.Game.get().camera.active
        cx, cy = self.center
        screen = camera.world_to_screen(cx, cy) if camera else (cx, cy)
        zoom = camera.zoom if camera else 1.0
        pygame.draw.circle(
            pymod.Game.get().screen.render_surface,
            self.debug_color,
            (int(screen[0]), int(screen[1])),
            int(self.radius * zoom),
            1,
        )