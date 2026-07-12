from __future__ import annotations

import pygame

import pymod

class Collider(pymod.Component):
    """Base class for all collider components.

    Handles registration with the CollisionManager, filtering, the static/trigger flags, and the enter/stay/exit callback hooks.
    Shape-specific subclasses (BoxCollider, CircleCollider) implement the actual overlap test and debug drawing.

    Colliders collide with everything by default.
    Narrow this with tags (include/exclude specific tags) and/or the CollisionManager's layer matrix, which is checked using the owner GameObject's layer.

    Notification happens three ways simultaneously, all driven by the same detection pass:
        - callback methods on this component (override on_collision_enter etc)
        - CollisionEvent emitted through the EventManager
        - direct queries (is_colliding, get_colliding) any time

    Attributes:
        offset: (x, y) offset of the collider from the owner's position, in world units.
        trigger: If True, detects overlaps but never resolves them (no push-apart).
        static: If True, this collider never moves during resolution.
                Walls, floors, and immovable geometry should be static.
        enabled_collision: Whether this collider participates in detection at all.
        include_tags: If set, only collide with colliders that have at least
                      one of these tags. None means no include filter.
        exclude_tags: Never collide with colliders that have any of these tags.
        debug_draw: If True, draw the collider outline for visualising it.
        debug_color: RGB colour used for the debug outline.
    """

    def __init__(
        self,
        offset: tuple[float, float] = (0.0, 0.0),
        trigger: bool = False,
        static: bool = False,
        include_tags: set[str] | None = None,
        exclude_tags: set[str] | None = None,
        debug_draw: bool = False,
        debug_color: tuple[int, int, int] = (0, 255, 0),
    ):
        super().__init__()
        self.offset = offset
        self.trigger = trigger
        self.static = static
        self.enabled_collision = True
        self.include_tags = include_tags
        self.exclude_tags = exclude_tags or set()
        self.debug_draw = debug_draw
        self.debug_color = debug_color

        # colliders currently overlapping this one, for enter/stay/exit tracking
        self._contacts: set[Collider] = set()

    # OVERRIDABLE CALLBACKS
    def on_collision_enter(self, other: Collider, normal: tuple[float, float], overlap: float) -> None:
        """Called the first frame a solid collision with `other` begins."""
        pass

    def on_collision_stay(self, other: Collider, normal: tuple[float, float], overlap: float) -> None:
        """Called every frame a solid collision with `other` continues."""
        pass

    def on_collision_exit(self, other: "Collider"):
        """Called the first frame a solid collision with `other` ends."""
        pass

    def on_trigger_enter(self, other: Collider):
        """Called the first frame a trigger overlap with `other` begins."""
        pass

    def on_trigger_stay(self, other: Collider):
        """Called every frame a trigger overlap with `other` continues."""
        pass

    def on_trigger_exit(self, other: Collider):
        """Called the first frame a trigger overlap with `other` ends."""
        pass

    # SHAPE INTERFACE — subclasses implement these
    def get_bounds(self) -> pygame.Rect:
        """Return the world-space axis-aligned bounding rect of this collider.

        Used for broad-phase grid insertion. Subclasses must implement.
        """
        raise NotImplementedError

    def _debug_draw(self) -> None:
        """Draw the collider outline. Subclasses must implement."""
        raise NotImplementedError

    # QUERIES
    def is_colliding(self) -> bool:
        """Whether this collider is currently overlapping anything."""
        return bool(self._contacts)

    def is_colliding_with(self, other: Collider) -> bool:
        """Whether this collider is currently overlapping a specific collider."""
        return other in self._contacts

    def get_colliding(self) -> list[Collider]:
        """Get all colliders currently overlapping this one."""
        return list(self._contacts)

    # FILTERING
    def can_collide_with(self, other: Collider) -> bool:
        """Whether this collider is permitted to collide with `other`.

        Checks the enabled flag, tag include/exclude filters, and the CollisionManager's layer matrix.
        Called both directions before a pair is tested.
        """
        if not self.enabled_collision or not other.enabled_collision:
            return False

        other_tags = other.owner.tags
        if self.include_tags is not None and self.include_tags.isdisjoint(other_tags):
            return False
        if self.exclude_tags and not self.exclude_tags.isdisjoint(other_tags):
            return False

        matrix = pymod.Game.get().collision.layer_matrix
        if not matrix.can_collide(self.owner.layer, other.owner.layer):
            return False

        return True

    # LIFECYCLE
    def on_start(self) -> None:
        pymod.Game.get().collision.register(self)

    def on_destroy(self) -> None:
        pymod.Game.get().collision.unregister(self)

    def draw(self) -> None:
        if self.debug_draw:
            self._debug_draw()

    # INTERNAL
    def _find_renderer(self):
        """Find any component on the owner that can report a world rect.

        Checks for a SpriteRenderer first, then any ShapeRenderer subclass.
        Returns None if the owner has no renderer.
        """
        from ..sprite_renderer import SpriteRenderer
        from ..shape_renderers.shape_renderer import ShapeRenderer

        renderer = self.owner.get_component(SpriteRenderer)
        if renderer is not None:
            return renderer

        for component in self.owner._components.values():
            if isinstance(component, ShapeRenderer):
                return component

        return None