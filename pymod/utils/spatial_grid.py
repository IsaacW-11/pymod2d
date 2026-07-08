from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame


class SpatialGrid:
    """A uniform spatial hash grid for broad-phase collision culling.

    Buckets colliders into square cells so only colliders sharing a cell (or neighbouring cells, handled by inserting into every cell a bounds overlaps) need to be pairwise tested.
    Turns the naive O(n^2) all-pairs check into something close to O(n) for evenly distributed objects.

    Rebuilt every frame from current collider bounds. This is cheap compared to the pairwise tests it saves.

    Attributes:
        cell_size: Side length of each square cell in world pixels.
    """

    def __init__(self, cell_size: int = 128):
        self.cell_size: int = cell_size
        self._cells: dict[tuple[int, int], list] = {}

    def clear(self):
        """Empty the grid. Called at the start of each rebuild."""
        self._cells.clear()

    def _cell_coords(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, collider, bounds: "pygame.Rect"):
        """Insert a collider into every cell its bounds overlap.

        Args:
            collider: The collider to insert.
            bounds: The collider's world-space bounding rect.
        """
        min_cx, min_cy = self._cell_coords(bounds.left, bounds.top)
        max_cx, max_cy = self._cell_coords(bounds.right, bounds.bottom)
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                self._cells.setdefault((cx, cy), []).append(collider)

    def get_potential_pairs(self) -> set[tuple]:
        """Get every unique pair of colliders that share at least one cell.

        Returns:
            A set of (collider_a, collider_b) tuples, deduplicated so each pair appears once regardless of how many cells they share.
        """
        pairs: set[tuple] = set()
        for bucket in self._cells.values():
            count = len(bucket)
            if count < 2:
                continue
            for i in range(count):
                for j in range(i + 1, count):
                    a, b = bucket[i], bucket[j]
                    pair = (a, b) if id(a) < id(b) else (b, a)
                    pairs.add(pair)
        return pairs