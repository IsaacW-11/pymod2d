# pymod/managers/camera_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from ..components.camera import Camera
    from ..core.scene_manager import SceneManager


class CameraManager:
    """Manages all active Camera components and drives the render loop.

    Supports multiple simultaneous cameras, each rendering to its own viewport.

    Cameras are drawn in order of their `order` attribute, lowest first.
    If no cameras are registered, the scene draws once with no camera transform.
    Components draw at raw world position.

    Attributes:
        _cameras: All currently registered Camera components.
        _active: The camera currently being used for the in-progress render pass.
                 None outside of a render pass, or if no cameras are registered.
    """

    def __init__(self):
        self._cameras: list[Camera] = []
        self._active: Camera | None = None

    # REGISTRATION
    def register(self, camera: Camera) -> None:
        """Register a camera. Called automatically by Camera.on_attach.

        Args:
            camera: The Camera component to register.
        """
        if camera not in self._cameras:
            self._cameras.append(camera)

    def unregister(self, camera: Camera) -> None:
        """Unregister a camera. Called automatically by Camera.on_destroy.

        Args:
            camera: The Camera component to unregister.
        """
        if camera in self._cameras:
            self._cameras.remove(camera)

    # QUERIES
    @property
    def active(self) -> Camera | None:
        """The camera currently being used for rendering.

        Only meaningful during a render pass. Components read this in draw() to convert world coordinates to screen coordinates.
        None if no cameras exist, in which case components should draw at raw world position with no transform.
        """
        return self._active

    @property
    def has_cameras(self) -> bool:
        """Whether any cameras are currently registered."""
        return bool(self._cameras)

    @property
    def main(self) -> Camera | None:
        """The designated main camera, for use outside an active render pass.

        Returns whichever registered camera has is_main set to True.
        If none is explicitly marked, falls back to the lowest-order enabled camera.
        Returns None if no cameras are registered.
        """
        explicit = next((c for c in self._cameras if c.is_main and c.enabled), None)
        if explicit:
            return explicit
        enabled = [c for c in self._cameras if c.enabled]
        if not enabled:
            return None
        return min(enabled, key=lambda c: c.order)

    def get_cameras(self) -> list[Camera]:
        """Get all registered cameras.

        Returns:
            List of all registered Camera components.
        """
        return self._cameras.copy()

    def get_camera_at_point(self, screen_pos: tuple[int, int]) -> Camera | None:
        """Find which camera's viewport contains a given screen point.

        Useful for resolving clicks when multiple viewports are on screen.
        Clicking a minimap should resolve through the minimap camera, not the main camera.
        Checked in reverse draw order, so the topmost camera wins if viewports overlap.

        Args:
            screen_pos: Position in render-surface coordinates.

        Returns:
            The matching Camera, or None if the point is in no viewport.
        """
        from ..core.game import Game
        surface_size = Game.get().screen.render_size

        for camera in sorted(self._cameras, key=lambda c: -c.order):
            if not camera.enabled:
                continue
            rect = camera.get_viewport_rect(surface_size)
            if rect.collidepoint(screen_pos):
                return camera
        return None

    def screen_to_world(self, screen_pos: tuple[int, int]) -> tuple[float, float] | None:
        """Convert a screen position to a world position using whichever camera's viewport contains that point.

        Args:
            screen_pos: Position in render-surface coordinates.

        Returns:
            World position, or None if the point is in no camera's viewport.
        """
        camera = self.get_camera_at_point(screen_pos)
        if camera is None:
            return None
        return camera.screen_to_world(screen_pos)

    # INTERNAL
    def _update(self) -> None:
        """Internal method called every frame by Game to update camera logic."""
        for camera in self._cameras:
            if camera.enabled:
                camera._update()

    def _render(self, scene_manager: SceneManager, render_surface: pygame.Surface) -> None:
        """Internal method called every frame by Game to render through all cameras.

        If no cameras are registered, draws once with no transform applied.
        Otherwise draws the scene once per enabled camera, clipped to that camera's viewport, lowest order first.
        Scene._draw reads self.active internally to apply layer filtering per camera.

        Args:
            scene_manager: The game's SceneManager.
            render_surface: The surface to draw onto.
        """
        if not self._cameras:
            self._active = None
            scene_manager._draw()
            return

        enabled_cameras = sorted(
            (c for c in self._cameras if c.enabled),
            key=lambda c: c.order
        )

        for camera in enabled_cameras:
            self._active = camera
            viewport_rect = camera.get_viewport_rect(render_surface.get_size())
            render_surface.set_clip(viewport_rect)

            if camera.clear_color is not None:
                render_surface.fill(camera.clear_color, viewport_rect)

            scene_manager._draw()

        render_surface.set_clip(None)
        self._active = None