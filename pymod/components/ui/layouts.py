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

    def __init__(self, spacing=8, padding=(8, 8, 8, 8), align="center"):
        super().__init__()
        self.spacing = spacing
        self.padding = padding if not isinstance(padding, (int, float)) else (padding,) * 4
        self.align = align  # cross-axis: "start" | "center" | "end"

    def arrange(self):
        raise NotImplementedError

    def _children(self):
        out = []
        for c in self.owner.children:
            rc = c.get_component(UIRect)
            if rc:
                rc.layout_controlled = True
                out.append((c, rc))
        return out


class VerticalLayout(LayoutGroup):
    """Stacks children top to bottom, centered horizontally."""

    def arrange(self):
        p = self.owner.get_component(UIRect)
        if not p:
            return
        pr = p.rect
        pl, pt, prg, pb = self.padding
        y = pr.top + pt
        for _, rc in self._children():
            w, h = rc.size
            rc._rect.width, rc._rect.height = w, h
            if self.align == "start":
                rc._rect.x = pr.left + pl
            elif self.align == "end":
                rc._rect.x = pr.right - prg - w
            else:
                rc._rect.x = pr.centerx - w // 2
            rc._rect.y = y
            y += h + self.spacing


class HorizontalLayout(LayoutGroup):
    """Lays children left to right, centered vertically."""

    def arrange(self):
        p = self.owner.get_component(UIRect)
        if not p:
            return
        pr = p.rect
        pl, pt, prg, pb = self.padding
        x = pr.left + pl
        for _, rc in self._children():
            w, h = rc.size
            rc._rect.width, rc._rect.height = w, h
            if self.align == "start":
                rc._rect.y = pr.top + pt
            elif self.align == "end":
                rc._rect.y = pr.bottom - pb - h
            else:
                rc._rect.y = pr.centery - h // 2
            rc._rect.x = x
            x += w + self.spacing


class GridLayout(LayoutGroup):
    """Arranges children in a grid of a fixed number of columns.

    Attributes:
        columns: Number of columns before wrapping to the next row.
    """

    def __init__(self, columns=2, spacing=8, padding=(8, 8, 8, 8), cell_size=None):
        super().__init__(spacing, padding)
        self.columns = max(1, columns)
        self.cell_size = cell_size

    def arrange(self):
        p = self.owner.get_component(UIRect)
        if not p:
            return
        pr = p.rect
        pl, pt, prg, pb = self.padding
        kids = self._children()
        if not kids:
            return
        cw, ch = self.cell_size if self.cell_size else kids[0][1].size
        for i, (_, rc) in enumerate(kids):
            col, row = i % self.columns, i // self.columns
            rc._rect.width, rc._rect.height = rc.size
            rc._rect.x = pr.left + pl + col * (cw + self.spacing)
            rc._rect.y = pr.top + pt + row * (ch + self.spacing)