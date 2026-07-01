from __future__ import annotations
from enum import Enum, auto

import pygame

class ViewportMode(Enum):
    """How a Viewport's dimensions should be interpreted.

    NORMALIZED: x, y, width, height are 0.0-1.0 fractions of the surface. Scales proportionally when the window is resized.
    PIXELS: x, y, width, height are exact pixel values. Stays a constant size regardless of resolution.
    """
    NORMALIZED = auto()
    PIXELS = auto()

class Viewport:
    """Defines the screen region a Camera renders to.

    Can be defined as a normalized fraction of the screen (scales with resolution) or as a fixed pixel rect (constant size regardless of
    resolution). A main camera usually wants normalized full-screen coverage; a minimap usually wants a fixed pixel size in a corner.

    Attributes:
        x: Horizontal position. Fraction if NORMALIZED, pixels if PIXELS.
        y: Vertical position. Fraction if NORMALIZED, pixels if PIXELS.
        width: Width. Fraction if NORMALIZED, pixels if PIXELS.
        height: Height. Fraction if NORMALIZED, pixels if PIXELS.
        mode: Whether values are normalized fractions or fixed pixels.
    """

    def __init__(self, x: float, y: float, width: float, height: float, mode: ViewportMode):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.mode = mode

    @classmethod
    def normalized(cls, x: float = 0.0, y: float = 0.0, width: float = 1.0, height: float = 1.0) -> "Viewport":
        """Create a viewport defined as fractions (0.0-1.0) of the screen.

        Args:
            x: Horizontal position, 0.0-1.0.
            y: Vertical position, 0.0-1.0.
            width: Width, 0.0-1.0.
            height: Height, 0.0-1.0.

        Returns:
            A new Viewport in NORMALIZED mode.
        """
        return cls(x, y, width, height, ViewportMode.NORMALIZED)

    @classmethod
    def pixels(cls, x: float = 0, y: float = 0, width: float = 320, height: float = 180) -> "Viewport":
        """Create a viewport defined as a fixed pixel rect.

        Negative x or y anchors the viewport from the right or bottom edge of the screen instead of the left or top.

        Args:
            x: Horizontal pixel position. Negative anchors from the right edge.
            y: Vertical pixel position. Negative anchors from the bottom edge.
            width: Width in pixels.
            height: Height in pixels.

        Returns:
            A new Viewport in PIXELS mode.
        """
        return cls(x, y, width, height, ViewportMode.PIXELS)

    def to_rect(self, surface_size: tuple[int, int]) -> pygame.Rect:
        """Resolve this viewport to a pixel rect for a given surface size.

        Args:
            surface_size: (width, height) of the surface being rendered to.

        Returns:
            A pygame.Rect in pixel coordinates.
        """
        sw, sh = surface_size

        if self.mode == ViewportMode.NORMALIZED:
            return pygame.Rect(
                int(self.x * sw), int(self.y * sh),
                int(self.width * sw), int(self.height * sh)
            )

        x = self.x if self.x >= 0 else sw + self.x
        y = self.y if self.y >= 0 else sh + self.y
        return pygame.Rect(int(x), int(y), int(self.width), int(self.height))   