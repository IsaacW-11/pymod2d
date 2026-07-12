# pymod/managers/collision_manager.py
from __future__ import annotations
import math
from typing import TYPE_CHECKING

import pygame

from ..utils.spatial_grid import SpatialGrid

if TYPE_CHECKING:
    from ..components.colliders.collider import Collider
    from ..components.colliders.box_collider import BoxCollider
    from ..components.colliders.circle_collider import CircleCollider


class LayerMatrix:
    """Controls which layers are allowed to collide with each other.

    By default, every layer collides with every other layer.
    Disable specific pairings to stop, for example, enemies colliding with each other while still colliding with the player and the world.

    Pairings are symmetric — disabling (A, B) also disables (B, A).

    Example:
        matrix = pymod.Game.get().collision.layer_matrix
        matrix.set_collision("enemy", "enemy", False)   # enemies pass through each other
        matrix.set_collision("bullet", "player", False)  # player's own bullets don't hit them
    """

    def __init__(self):
        self._disabled: set[frozenset] = set()

    def set_collision(self, layer_a: str, layer_b: str, enabled: bool):
        """Enable or disable collisions between two layers.

        Args:
            layer_a: First layer name.
            layer_b: Second layer name.
            enabled: True to allow collisions, False to disable.
        """
        pair = frozenset((layer_a, layer_b))
        if enabled:
            self._disabled.discard(pair)
        else:
            self._disabled.add(pair)

    def can_collide(self, layer_a: str, layer_b: str) -> bool:
        """Whether two layers are allowed to collide.

        Args:
            layer_a: First layer name.
            layer_b: Second layer name.

        Returns:
            True unless this pairing has been explicitly disabled.
        """
        return frozenset((layer_a, layer_b)) not in self._disabled


class CollisionManager:
    """Detects and resolves collisions between all registered colliders.

    Runs one pass per frame:
        1. Rebuild the spatial grid from every collider's current bounds.
        2. Get candidate pairs from the grid (broad phase).
        3. For each candidate, check filters then do the exact shape test.
        4. Track enter/stay/exit against the previous frame's contacts.
        5. Fire callbacks and emit events for each phase.
        6. Resolve solid (non-trigger) overlaps by pushing objects apart,
           respecting the static flag.

    Attributes:
        layer_matrix: Controls which layers may collide.
        _colliders: All registered colliders.
        _grid: The spatial hash grid used for broad-phase culling.
    """

    def __init__(self, cell_size: int = 128):
        self.layer_matrix = LayerMatrix()
        self._colliders: list[Collider] = []
        self._grid = SpatialGrid(cell_size)

    # REGISTRATION
    def register(self, collider: Collider):
        if collider not in self._colliders:
            self._colliders.append(collider)

    def unregister(self, collider: Collider):
        if collider in self._colliders:
            self._colliders.remove(collider)
        # notify anyone still in contact that this collider is gone
        for other in list(collider._contacts):
            other._contacts.discard(collider)
        collider._contacts.clear()

    # QUERIES
    def query_point(self, x: float, y: float) -> list[Collider]:
        """Get every collider overlapping a world-space point.

        Args:
            x: World x coordinate.
            y: World y coordinate.

        Returns:
            List of colliders containing the point.
        """
        hits = []
        for collider in self._colliders:
            if collider.enabled_collision and self._point_in_collider(x, y, collider):
                hits.append(collider)
        return hits

    def query_rect(self, rect: pygame.Rect) -> list[Collider]:
        """Get every collider whose bounds overlap a world-space rect.

        Args:
            rect: A pygame.Rect in world coordinates.

        Returns:
            List of colliders overlapping the rect.
        """
        return [c for c in self._colliders if c.enabled_collision and c.get_bounds().colliderect(rect)]

    # MAIN PASS
    def _update(self):
        """Internal method. Full collision pass, called each frame by Game."""
        self._grid.clear()
        for collider in self._colliders:
            if collider.enabled_collision:
                self._grid.insert(collider, collider.get_bounds())

        pairs = self._grid.get_potential_pairs()
        current_contacts: dict[Collider, set[Collider]] = {}

        for a, b in pairs:
            if not a.can_collide_with(b) or not b.can_collide_with(a):
                continue

            result = self._test(a, b)
            if result is None:
                continue

            normal, overlap = result
            current_contacts.setdefault(a, set()).add(b)
            current_contacts.setdefault(b, set()).add(a)

            is_trigger = a.trigger or b.trigger
            was_in_contact = b in a._contacts

            if was_in_contact:
                self._fire_stay(a, b, normal, overlap, is_trigger)
            else:
                self._fire_enter(a, b, normal, overlap, is_trigger)

            if not is_trigger:
                self._resolve(a, b, normal, overlap)

        # exit detection — anything in last frame's contacts but not this frame's
        for collider in self._colliders:
            still = current_contacts.get(collider, set())
            for other in collider._contacts - still:
                self._fire_exit(collider, other)

        # commit this frame's contacts
        for collider in self._colliders:
            collider._contacts = current_contacts.get(collider, set())

    # SHAPE TESTS  →  return (normal, overlap) or None
    def _test(self, a: Collider, b: Collider):
        """Dispatch to the correct shape-pair test.

        Returns (normal, overlap) or None if not overlapping.
        """
        from ..components.colliders.box_collider import BoxCollider

        a_box = isinstance(a, BoxCollider)
        b_box = isinstance(b, BoxCollider)

        if a_box and b_box:
            return self._box_box(a, b)

        if not a_box and not b_box:
            return self._circle_circle(a, b)

        if a_box and not b_box:
            res = self._box_circle(a, b)
            if res is None:
                return None
            (nx, ny), overlap = res
            return ((-nx, -ny), overlap)


        return self._box_circle(b, a)

    def _box_box(self, a: BoxCollider, b: BoxCollider):
        ra, rb = a.get_bounds(), b.get_bounds()
        if not ra.colliderect(rb):
            return None

        overlap_x = min(ra.right, rb.right) - max(ra.left, rb.left)
        overlap_y = min(ra.bottom, rb.bottom) - max(ra.top, rb.top)

        if overlap_x < overlap_y:
            nx = -1.0 if ra.centerx < rb.centerx else 1.0
            return ((nx, 0.0), overlap_x)
        else:
            ny = -1.0 if ra.centery < rb.centery else 1.0
            return ((0.0, ny), overlap_y)

    def _circle_circle(self, a: CircleCollider, b: CircleCollider):
        ax, ay = a.center
        bx, by = b.center
        dx, dy = ax - bx, ay - by
        dist_sq = dx * dx + dy * dy
        r = a.radius + b.radius
        if dist_sq >= r * r:
            return None

        dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0
        if dist == 0:
            return ((1.0, 0.0), r)
        overlap = r - dist
        return ((dx / dist, dy / dist), overlap)

    def _box_circle(self, box: BoxCollider, circle: CircleCollider):
        rect = box.get_bounds()
        cx, cy = circle.center

        closest_x = max(rect.left, min(cx, rect.right))
        closest_y = max(rect.top, min(cy, rect.bottom))
        dx, dy = cx - closest_x, cy - closest_y
        dist_sq = dx * dx + dy * dy

        if dist_sq >= circle.radius * circle.radius:
            return None

        dist = math.sqrt(dist_sq) if dist_sq > 0 else 0.0
        if dist == 0:
            left = cx - rect.left
            right = rect.right - cx
            top = cy - rect.top
            bottom = rect.bottom - cy
            m = min(left, right, top, bottom)
            if m == left:
                return ((-1.0, 0.0), circle.radius + left)
            if m == right:
                return ((1.0, 0.0), circle.radius + right)
            if m == top:
                return ((0.0, -1.0), circle.radius + top)
            return ((0.0, 1.0), circle.radius + bottom)

        overlap = circle.radius - dist
        return ((dx / dist, dy / dist), overlap)

    def _point_in_collider(self, x: float, y: float, collider: Collider) -> bool:
        from ..components.colliders.box_collider import BoxCollider
        if isinstance(collider, BoxCollider):
            return collider.get_bounds().collidepoint(x, y)
        cx, cy = collider.center
        dx, dy = x - cx, y - cy
        return dx * dx + dy * dy <= collider.radius * collider.radius

    # RESOLUTION
    def _resolve(self, a, b, normal, overlap) -> None:
        from ..components.rigidbody import Rigidbody

        SLOP = 0.5  # pixels of penetration left uncorrected to avoid jitter

        nx, ny = normal

        rb_a = a.owner.get_component(Rigidbody)
        rb_b = b.owner.get_component(Rigidbody)

        a_movable = rb_a is not None and not rb_a.kinematic and not a.static
        b_movable = rb_b is not None and not rb_b.kinematic and not b.static

        # positional correction — only the amount beyond the slop tolerance
        corrected = max(0.0, overlap - SLOP)

        if corrected > 0:
            if not a_movable and not b_movable:
                pass  # neither can move
            elif not a_movable:
                b.owner.x -= nx * corrected
                b.owner.y -= ny * corrected
            elif not b_movable:
                a.owner.x += nx * corrected
                a.owner.y += ny * corrected
            else:
                half = corrected / 2
                a.owner.x += nx * half
                a.owner.y += ny * half
                b.owner.x -= nx * half
                b.owner.y -= ny * half

        # velocity response — always applied, even within slop, so objects
        # don't keep accelerating into the surface
        if rb_a is not None:
            rb_a._apply_collision_response((nx, ny), rb_b)
        if rb_b is not None:
            rb_b._apply_collision_response((-nx, -ny), rb_a)

    # NOTIFICATION
    def _fire_enter(self, a, b, normal, overlap, is_trigger):
        if is_trigger:
            a.on_trigger_enter(b)
            b.on_trigger_enter(a)
        else:
            a.on_collision_enter(b, normal, overlap)
            b.on_collision_enter(a, (-normal[0], -normal[1]), overlap)
        self._emit(a, b, "enter", is_trigger, normal, overlap)

    def _fire_stay(self, a, b, normal, overlap, is_trigger):
        if is_trigger:
            a.on_trigger_stay(b)
            b.on_trigger_stay(a)
        else:
            a.on_collision_stay(b, normal, overlap)
            b.on_collision_stay(a, (-normal[0], -normal[1]), overlap)
        self._emit(a, b, "stay", is_trigger, normal, overlap)

    def _fire_exit(self, a, b) -> None:
        is_trigger = a.trigger or b.trigger
        if is_trigger:
            a.on_trigger_exit(b)
            b.on_trigger_exit(a)
        else:
            a.on_collision_exit(b)
            b.on_collision_exit(a)
        self._emit(a, b, "exit", is_trigger, (0.0, 0.0), 0.0)

    def _emit(self, a, b, phase, is_trigger, normal, overlap) -> None:
        import pymod
        pymod.Game.get().events.emit(pymod.CollisionEvent(
            a=a, b=b, phase=phase, is_trigger=is_trigger,
            normal=normal, overlap=overlap,
        ))