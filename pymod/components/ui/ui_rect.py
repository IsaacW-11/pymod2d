from __future__ import annotations
from enum import Enum, auto

import math
import pygame

import pymod


class UIAnchor(Enum):
    """Where a UI element attaches to its parent (or the screen if no parent).

    The nine point anchors pin the element to that point, and `offset` shifts it from there.
    STRETCH anchors make the element resize with its parent instead of staying a fixed size.
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

    STRETCH = auto()             # fill parent entirely
    STRETCH_HORIZONTAL = auto()  # full width, fixed height
    STRETCH_VERTICAL = auto()    # full height, fixed width


class UIRect(pymod.Component):
    """Defines a UI element's position and size in screen space.

    Every UI element needs one. It computes the element's screen rect each frame from its anchor, size, and offset, relative to its parent's rect (or the full screen if it has no UI parent).

    Attributes:
        anchor: Where this element attaches to its parent.
        size: (width, height) in pixels. Ignored on stretched axes.
        offset: (x, y) pixel shift from the anchor point.
        margin: (left, top, right, bottom) inset, used by STRETCH anchors to leave a gap from the parent's edges.
        pivot: (px, py) from 0-1, which point of this element sits on the anchor. (0.5, 0.5) centers it, (0, 0) uses its top-left.
    """

    def __init__(
        self,
        anchor: UIAnchor = UIAnchor.TOP_LEFT,
        size: tuple[float, float] = (100, 100),
        offset: tuple[float, float] = (0, 0),
        margin: tuple[float, float, float, float] = (0, 0, 0, 0),
        pivot: tuple[float, float] = (0.5, 0.5),
        rotation: float = 0.0
    ):
        super().__init__()
        self.anchor = anchor
        self.size = size
        self.offset = offset
        self.margin = margin
        self.pivot = pivot
        self.rotation = rotation  # degrees, clockwise
        self._rect = pygame.Rect(0, 0, 0, 0)
        self.layout_controlled: bool = False

    @property
    def rect(self) -> pygame.Rect:
        """This element's computed screen-space rect. Updated each frame."""
        return self._rect

    def get_parent_rect(self) -> pygame.Rect:
        """The rect this element anchors within — its parent's UIRect, or the full screen if it has no UI parent."""
        parent = self.owner.parent
        if parent is not None:
            parent_rect_component = parent.get_component(UIRect)
            if parent_rect_component is not None:
                return parent_rect_component.rect
        w, h = pymod.Game.get().screen.render_size
        return pygame.Rect(0, 0, w, h)

    def recalculate(self) -> None:
        """Recompute this element's screen rect from its anchor and parent.

        Called each frame by UIManager, top-down through the hierarchy so parents are computed before their children.
        """
        if self.layout_controlled:
            return

        p = self.get_parent_rect()
        ml, mt, mr, mb = self.margin
        ox, oy = self.offset
        w, h = self.size

        if self.anchor == UIAnchor.STRETCH:
            self._rect=pygame.Rect(p.left+ml,p.top+mt,p.width-ml-mr,p.height-mt-mb)
            return

        if self.anchor == UIAnchor.STRETCH_HORIZONTAL:
            self._rect=pygame.Rect(p.left+ml,p.centery-h*self.pivot[1]+oy,p.width-ml-mr,h)
            return

        if self.anchor == UIAnchor.STRETCH_VERTICAL:
            self._rect=pygame.Rect(p.centerx-w*self.pivot[0]+ox,p.top+mt,w,p.height-mt-mb)
            return

        anchor_points = {
            UIAnchor.TOP_LEFT:      (p.left,    p.top),
            UIAnchor.TOP_CENTER:    (p.centerx, p.top),
            UIAnchor.TOP_RIGHT:     (p.right,   p.top),
            UIAnchor.CENTER_LEFT:   (p.left,    p.centery),
            UIAnchor.CENTER:        (p.centerx, p.centery),
            UIAnchor.CENTER_RIGHT:  (p.right,   p.centery),
            UIAnchor.BOTTOM_LEFT:   (p.left,    p.bottom),
            UIAnchor.BOTTOM_CENTER: (p.centerx, p.bottom),
            UIAnchor.BOTTOM_RIGHT:  (p.right,   p.bottom),
        }
        ax, ay = anchor_points[self.anchor]

        self._rect=pygame.Rect(ax+ox-w*self.pivot[0],ay+oy-h*self.pivot[1],w,h)

    def contains_point(self, x: float, y: float) -> bool:
        """Whether a screen-space point is inside this element."""
        if self.rotation % 360 == 0:
            return self._rect.collidepoint(x, y)
        cx, cy = self._rect.centerx, self._rect.centery
        rad = math.radians(-self.rotation)  # inverse rotation
        dx, dy = x - cx, y - cy
        lx = dx * math.cos(rad) - dy * math.sin(rad) + cx
        ly = dx * math.sin(rad) + dy * math.cos(rad) + cy
        return self._rect.collidepoint(lx, ly)