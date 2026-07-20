from __future__ import annotations
import pygame
import pymod
from .collider import Collider


class BoxCollider(Collider):
    """An axis-aligned rectangular collider.

    If width or height is left as None, that dimension is auto-sized from the owner's SpriteRenderer.get_world_rect() at start, matching the
    sprite as closely as an AABB can. Explicit values override this.

    Attributes:
        width: Collider width in world units, or None to match the sprite.
        height: Collider height in world units, or None to match the sprite.
    """

    def __init__(self, width: float | None = None, height: float | None = None, **kwargs):
        super().__init__(**kwargs)
        self.width = width
        self.height = height

    def on_start(self) -> None:
        renderer = self._find_renderer()

        if renderer is not None:
            rect = renderer.get_world_rect()

            if self.width is None:
                self.width = rect.width
            if self.height is None:
                self.height = rect.height

            # auto-align the collider to overlay exactly where the renderer
            # draws, accounting for its anchor. Only if the user didn't
            # explicitly set an offset.
            if self.offset == (0.0, 0.0):
                self.offset = (rect.x - self.owner.x, rect.y - self.owner.y)
        else:
            if self.width is None:
                self.width = 32
            if self.height is None:
                self.height = 32

        super().on_start()


    def get_bounds(self) -> pygame.Rect:
        x = self.owner.x + self.offset[0]
        y = self.owner.y + self.offset[1]
        return pygame.Rect(x, y, self.width, self.height)

    def _debug_draw(self) -> None:
        camera = pymod.Game.get().camera.active
        bounds = self.get_bounds()
        topleft = camera.world_to_screen(bounds.x, bounds.y) if camera else (bounds.x, bounds.y)
        zoom = camera.zoom if camera else 1.0
        rect = pygame.Rect(topleft[0], topleft[1], bounds.width * zoom, bounds.height * zoom)
        pygame.draw.rect(pymod.Game.get().screen.render_surface, self.debug_color, rect, 1)