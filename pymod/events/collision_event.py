from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..components.colliders.collider import Collider


@dataclass
class CollisionEvent:
    """Emitted when two colliders begin, continue, or end overlapping.

    Attributes:
        a: The first collider.
        b: The second collider.
        phase: One of "enter", "stay", "exit".
        is_trigger: True if either collider is a trigger (no resolution occurred).
        normal: Unit vector pointing from b toward a along the collision, or (0, 0) for exit events.
        overlap: Penetration depth in pixels, or 0 for exit events.
    """
    a: Collider
    b: Collider
    phase: str
    is_trigger: bool
    normal: tuple[float, float] = (0.0, 0.0)
    overlap: float = 0.0