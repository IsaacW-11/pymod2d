from __future__ import annotations

import pymod
from .ui_rect import UIRect


class LayoutGroup(pymod.Component):
    """Base for layout components that arrange their owner's children.

    Attach to a parent UI element; it repositions the children's UIRects each frame.
    The UIManager calls arrange() during layout recalculation, after the parent's own rect resolves but before the children's do.

    Attributes:
        spacing: Pixels between children.
        padding: Pixels of inset from the parent's edges.
    """

    def __init__(self, spacing: float = 8, padding: float = 8):
        super().__init__()
        self.spacing = spacing
        self.padding = padding

    def arrange(self) -> None:
        raise NotImplementedError

    def _child_rects(self):
        rects = []
        for child in self.owner.children:
            rc = child.get_component(UIRect)
            if rc is not None:
                rc.layout_controlled = True
                rects.append((child, rc))
        return rects


class VerticalLayout(LayoutGroup):
    """Stacks children top to bottom, centered horizontally."""

    def arrange(self):
        rc_parent = self.owner.get_component(UIRect)
        if rc_parent is None:
            return
        parent = rc_parent.rect
        y = parent.top + self.padding
        for child, rc in self._child_rects():
            w, h = rc.size
            rc._rect.width, rc._rect.height = w, h
            rc._rect.x = parent.centerx - w // 2
            rc._rect.y = y
            y += h + self.spacing


class HorizontalLayout(LayoutGroup):
    """Lays children left to right, centered vertically."""

    def arrange(self):
        rc_parent = self.owner.get_component(UIRect)
        if rc_parent is None:
            return
        parent = rc_parent.rect
        x = parent.left + self.padding
        for child, rc in self._child_rects():
            w, h = rc.size
            rc._rect.width, rc._rect.height = w, h
            rc._rect.x = x
            rc._rect.y = parent.centery - h // 2
            x += w + self.spacing


class GridLayout(LayoutGroup):
    """Arranges children in a grid of a fixed number of columns.

    Attributes:
        columns: Number of columns before wrapping to the next row.
    """

    def __init__(self, columns: int = 2, spacing: float = 8, padding: float = 8):
        super().__init__(spacing, padding)
        self.columns = max(1, columns)

    def arrange(self):
        rc_parent = self.owner.get_component(UIRect)
        if rc_parent is None:
            return
        parent = rc_parent.rect
        children = self._child_rects()
        if not children:
            return

        cell_w = children[0][1].size[0]
        cell_h = children[0][1].size[1]

        for i, (child, rc) in enumerate(children):
            col = i % self.columns
            row = i // self.columns
            rc._rect.width, rc._rect.height = rc.size
            rc._rect.x = parent.left + self.padding + col * (cell_w + self.spacing)
            rc._rect.y = parent.top + self.padding + row * (cell_h + self.spacing)