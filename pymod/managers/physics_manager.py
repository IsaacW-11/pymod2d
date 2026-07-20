from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..components.rigidbody import Rigidbody


class PhysicsManager:
    """Holds global physics settings and the registry of active rigidbodies.

    The actual integration happens in each Rigidbody's fixed_update.
    This manager just owns shared state like gravity and provides a lookup so he CollisionManager can find the Rigidbody (if any) on a colliding
    object to apply velocity response.

    Attributes:
        gravity: Global gravity vector in world units/second^2, as (x, y).
                 Positive y is downward. Individual bodies scale this with their gravity_scale.
    """

    def __init__(self, gravity: tuple[float, float] = (0.0, 980.0)):
        self.gravity: tuple[float, float] = gravity
        self._bodies: list[Rigidbody] = []

    def register(self, body: Rigidbody):
        if body not in self._bodies:
            self._bodies.append(body)

    def unregister(self, body: Rigidbody):
        if body in self._bodies:
            self._bodies.remove(body)

    def set_gravity(self, x: float, y: float):
        """Set the global gravity vector.

        Args:
            x: Horizontal gravity.
            y: Vertical gravity. Positive is downward.
        """
        self.gravity = (x, y)