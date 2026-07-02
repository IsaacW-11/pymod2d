# pymod/components/camera.py
from __future__ import annotations
import math
import random
from typing import Iterable

import pygame

import pymod
from pymod.utils.viewport import Viewport

class Camera(pymod.Component):
    """Renders the world from this object's position to a region of the screen.

    Attach to a dedicated GameObject.  That object's x, y position is the world point the camera looks at (its center).
    Move the GameObject directly, or use follow() to have the camera track a target automatically.

    Attributes:
        viewport: The screen region this camera draws to. A Viewport instance, normalized or pixel-based. Defaults to full screen.
        rotation: Rotation in degrees, clockwise, around the camera center.
        order: Draw order relative to other cameras. Lower draws first; higher draws on top.
        clear_color: RGB colour to fill this camera's viewport with before drawing, or None to skip clearing.
        bounds: Optional pygame.Rect in world space. The camera's visible area is clamped to stay within these bounds.
        render_layers: Set of layer names this camera will draw, or None to draw every layer (the default).
                       GameObjects not on one of these layers are skipped entirely by this camera.
        is_main: Marks this as the designated main camera. Used by CameraManager.main as a default camera reference outside
                 of an active render pass. Only one camera should be marked main at a time.
        min_zoom: The smallest zoom value allowed. Prevents zoom reaching zero or negative, which would break coordinate math.
        max_zoom: The largest zoom value allowed, or None for no maximum.
    """

    def __init__(
        self,
        viewport: Viewport = None,
        zoom: float = 1.0,
        rotation: float = 0.0,
        order: int = 0,
        clear_color: tuple[int, int, int] | None = (0, 0, 0),
        render_layers: Iterable[str] | None = None,
        is_main: bool = False,
        min_zoom: float = 0.05,
        max_zoom: float | None = None,
    ):
        """Initialise the camera.

        Args:
            viewport: Screen region for this camera. Defaults to full screen.
            zoom: Initial zoom level. Higher shows less world, more detail. Defaults to 1.0.
            rotation: Initial rotation in degrees. Defaults to 0.
            order: Draw order relative to other cameras. Defaults to 0.
            clear_color: Colour to clear this viewport with before drawing. Defaults to black. Pass None to skip clearing.
            render_layers: Layers this camera draws. None draws every layer.
            is_main: Whether this is the designated main camera.
            min_zoom: Minimum allowed zoom. Defaults to 0.05.
            max_zoom: Maximum allowed zoom, or None for no limit.
        """
        super().__init__()
        self.viewport: Viewport = viewport or Viewport.normalized()
        self.rotation: float = rotation
        self.order: int = order
        self.clear_color: tuple[int, int, int] | None = clear_color
        self.bounds: pygame.Rect | None = None
        self.render_layers: set[str] | None = set(render_layers) if render_layers else None
        self.is_main: bool = is_main

        self.min_zoom: float = min_zoom
        self.max_zoom: float | None = max_zoom
        self._zoom: float = zoom
        self.zoom = zoom  # run through the clamped setter

        self.target: pymod.GameObject | None = None
        self.follow_speed: float | None = None
        self.follow_deadzone: tuple[float, float] = (0.0, 0.0)
        self.follow_offset: tuple[float, float] = (0.0, 0.0)

        self._shake_intensity: float = 0.0
        self._shake_duration: float = 0.0
        self._shake_offset: tuple[float, float] = (0.0, 0.0)
        self._shake_max_duration: float = 0.0

        self._zoom_target: float | None = None
        self._zoom_speed: float = 0.0

    # ZOOM
    @property
    def zoom(self) -> float:
        """Current zoom level, clamped between min_zoom and max_zoom."""
        return self._zoom

    @zoom.setter
    def zoom(self, value: float):
        value = max(self.min_zoom, value)
        if self.max_zoom is not None:
            value = min(self.max_zoom, value)
        self._zoom = value

    def zoom_to(self, target_zoom: float, speed: float = 0.0):
        """Smoothly change zoom level over time.

        Args:
            target_zoom: The zoom level to transition to.
            speed: Catch-up rate per second. 0 or negative snaps instantly.
        """
        if speed <= 0:
            self.zoom = target_zoom
            self._zoom_target = None
        else:
            self._zoom_target = target_zoom
            self._zoom_speed = speed

    # FOLLOW
    def follow(
        self,
        target: pymod.GameObject,
        speed: float | None = None,
        deadzone: tuple[float, float] = (0.0, 0.0),
        offset: tuple[float, float] = (0.0, 0.0),
    ):
        """Start following a target GameObject.

        Args:
            target: The GameObject to follow.
            speed: Catch-up rate per second. None or 0 snaps instantly with no lag. A value around 5-10 feels natural.
            deadzone: (width, height) in world units. The camera only moves once the target exits this zone around the
                      camera's current center. (0, 0) means no deadzone.
            offset: (x, y) added to the target's position before following.
        """
        self.target = target
        self.follow_speed = speed
        self.follow_deadzone = deadzone
        self.follow_offset = offset

    def stop_follow(self):
        """Stop following the current target. Camera stays at its last position."""
        self.target = None

    # SHAKE
    def shake(self, intensity: float, duration: float):
        """Apply a temporary shake effect to this camera.

        Shake decays linearly over the duration. Calling this again
        while a shake is active replaces it.

        Args:
            intensity: Maximum offset in pixels at the start of the shake.
            duration: How long the shake lasts in seconds.
        """
        self._shake_intensity = intensity
        self._shake_duration = duration
        self._shake_max_duration = duration  # store original for decay ratio

    # BOUNDS
    def set_bounds(self, bounds: pygame.Rect):
        """Clamp this camera's visible area to stay within a world-space rect.

        Args:
            bounds: A pygame.Rect in world coordinates.
        """
        self.bounds = bounds

    def clear_bounds(self):
        """Remove any bounds clamping."""
        self.bounds = None

    # LAYER FILTERING
    def set_render_layers(self, layers: Iterable[str] | None):
        """Set which layers this camera renders.

        Args:
            layers: Layer names to render, or None to render every layer.
        """
        self.render_layers = set(layers) if layers is not None else None

    def add_render_layer(self, layer: str):
        """Add a single layer to this camera's render set.

        If the camera was previously rendering all layers, this switches it to an explicit allow-list containing
        only this layer plus any added afterward.

        Args:
            layer: The layer name to add.
        """
        if self.render_layers is None:
            self.render_layers = set()
        self.render_layers.add(layer)

    def remove_render_layer(self, layer: str):
        """Remove a single layer from this camera's render set.

        Args:
            layer: The layer name to remove.
        """
        if self.render_layers is not None:
            self.render_layers.discard(layer)

    def render_all_layers(self):
        """Reset this camera to render every layer with no filtering."""
        self.render_layers = None

    def is_layer_visible(self, layer: str) -> bool:
        """Check whether this camera renders objects on a given layer.

        Args:
            layer: The layer name to check.

        Returns:
            True if this camera will render objects on this layer.
        """
        if self.render_layers is None:
            return True
        return layer in self.render_layers

    # DIRECT POSITIONING
    def set_position(self, x: float, y: float) -> None:
        """Move the camera directly to a world position. Stops any follow.

        Args:
            x: World x coordinate.
            y: World y coordinate.
        """
        self.target = None
        self.owner.x = x
        self.owner.y = y

    def move(self, dx: float, dy: float) -> None:
        """Move the camera by a relative amount. Stops any follow.

        Args:
            dx: Change in x.
            dy: Change in y.
        """
        self.target = None
        self.owner.x += dx
        self.owner.y += dy

    # COORDINATE CONVERSION
    def world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        """Convert a world position to a screen position within this camera's viewport.

        Args:
            world_x: World x coordinate.
            world_y: World y coordinate.

        Returns:
            (screen_x, screen_y) in render-surface coordinates.
        """
        surface_size = pymod.Game.get().screen.render_size
        viewport_rect = self.viewport.to_rect(surface_size)

        dx = world_x - self.owner.x
        dy = world_y - self.owner.y

        if self.rotation != 0:
            rad = math.radians(-self.rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            dx, dy = dx * cos_r - dy * sin_r, dx * sin_r + dy * cos_r

        shake_x, shake_y = self._shake_offset
        screen_x = dx * self.zoom + viewport_rect.width / 2 + viewport_rect.x + shake_x
        screen_y = dy * self.zoom + viewport_rect.height / 2 + viewport_rect.y + shake_y
        return (screen_x, screen_y)

    def screen_to_world(self, screen_pos: tuple[float, float]) -> tuple[float, float]:
        """Convert a screen position within this camera's viewport to a world position.

        screen_pos should already be in render-surface coordinates.
        If working with raw mouse input, convert window to render coordinates via ScreenManager first.

        Args:
            screen_pos: (screen_x, screen_y) in render-surface coordinates.

        Returns:
            (world_x, world_y).
        """
        surface_size = pymod.Game.get().screen.render_size
        viewport_rect = self.viewport.to_rect(surface_size)

        sx = (screen_pos[0] - viewport_rect.x - viewport_rect.width / 2) / self.zoom
        sy = (screen_pos[1] - viewport_rect.y - viewport_rect.height / 2) / self.zoom

        if self.rotation != 0:
            rad = math.radians(self.rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            sx, sy = sx * cos_r - sy * sin_r, sx * sin_r + sy * cos_r

        return (sx + self.owner.x, sy + self.owner.y)

    def get_visible_world_rect(self) -> pygame.Rect:
        """Get the world-space rect currently visible through this camera.

        Useful for culling — skip drawing or updating objects outside this rect for better performance.
        Does not account for rotation.
        If rotation is non-zero this is an approximation based on the unrotated frame.

        Returns:
            A pygame.Rect in world coordinates.
        """
        surface_size = pymod.Game.get().screen.render_size
        viewport_rect = self.viewport.to_rect(surface_size)
        w = viewport_rect.width / self.zoom
        h = viewport_rect.height / self.zoom
        return pygame.Rect(self.owner.x - w / 2, self.owner.y - h / 2, w, h)

    def is_visible(self, world_rect: pygame.Rect) -> bool:
        """Check whether a world-space rect overlaps this camera's visible area.

        Args:
            world_rect: A pygame.Rect in world coordinates.

        Returns:
            True if any part of the rect is visible through this camera.
        """
        return self.get_visible_world_rect().colliderect(world_rect)

    def get_viewport_rect(self, surface_size: tuple[int, int]) -> pygame.Rect:
        """Get this camera's viewport resolved to a pixel rect.

        Args:
            surface_size: (width, height) of the render surface.

        Returns:
            A pygame.Rect in pixel coordinates.
        """
        return self.viewport.to_rect(surface_size)

    # ════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ════════════════════════════════════════════════════════════════════

    def on_start(self):
        pymod.Game.get().camera.register(self)

    def on_destroy(self):
        pymod.Game.get().camera.unregister(self)

    def _update(self):
        """Internal method called every frame by CameraManager."""
        dt = pymod.time.delta

        if self.target is not None:
            self._update_follow(dt)

        if self._zoom_target is not None:
            self._update_zoom_transition(dt)

        if self._shake_duration > 0:
            self._update_shake(dt)
        else:
            self._shake_offset = (0.0, 0.0)

        if self.bounds is not None:
            self._clamp_to_bounds()

    def _update_follow(self, dt: float):
        target_x = self.target.x + self.follow_offset[0]
        target_y = self.target.y + self.follow_offset[1]

        deadzone_w, deadzone_h = self.follow_deadzone
        dx = target_x - self.owner.x
        dy = target_y - self.owner.y

        desired_x = self.owner.x
        desired_y = self.owner.y

        if abs(dx) > deadzone_w / 2:
            desired_x = target_x - (deadzone_w / 2 if dx > 0 else -deadzone_w / 2)
        if abs(dy) > deadzone_h / 2:
            desired_y = target_y - (deadzone_h / 2 if dy > 0 else -deadzone_h / 2)

        if not self.follow_speed:
            self.owner.x = desired_x
            self.owner.y = desired_y
        else:
            t = min(1.0, self.follow_speed * dt)
            self.owner.x += (desired_x - self.owner.x) * t
            self.owner.y += (desired_y - self.owner.y) * t

    def _update_zoom_transition(self, dt: float):
        t = min(1.0, self._zoom_speed * dt)
        self.zoom += (self._zoom_target - self.zoom) * t
        if abs(self.zoom - self._zoom_target) < 0.001:
            self.zoom = self._zoom_target
            self._zoom_target = None

    def _update_shake(self, dt: float):
        self._shake_duration -= dt
        if self._shake_duration <= 0:
            self._shake_duration = 0
            self._shake_offset = (0.0, 0.0)
            return

        # decay from full intensity to zero as duration runs out
        decay = self._shake_duration / self._shake_max_duration
        current_intensity = self._shake_intensity * decay

        self._shake_offset = (
            random.uniform(-current_intensity, current_intensity),
            random.uniform(-current_intensity, current_intensity),
        )

    def _clamp_to_bounds(self):
        visible = self.get_visible_world_rect()
        half_w = visible.width / 2
        half_h = visible.height / 2

        min_x = self.bounds.left + half_w
        max_x = self.bounds.right - half_w
        min_y = self.bounds.top + half_h
        max_y = self.bounds.bottom - half_h

        if min_x <= max_x:
            self.owner.x = max(min_x, min(max_x, self.owner.x))
        if min_y <= max_y:
            self.owner.y = max(min_y, min(max_y, self.owner.y))