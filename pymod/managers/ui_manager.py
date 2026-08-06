from __future__ import annotations
import os
import json

import pygame

import pymod

UI_LAYER = "ui"


class UIManager:
    """Manages UI layout, rendering, and input routing.

    UI elements are ordinary GameObjects on the reserved "ui" layer.
    They are drawn in screen space after the world render pass, ignoring the camera entirely.
    This means UI never moves, scales, or rotates with the camera.

    Each frame the manager recalculates every UIRect top-down through the parent hierarchy (so parents resolve before children),
    routes mouse input to the topmost element under the cursor, and draws everything.

    Layouts are loaded from JSON and can hot-reload.
    It lets you edit the file while the game runs fand the UI rebuilds instantly, so you can iterate on layout without restarting.

    Attributes:
        debug_draw: When True, overlays every element's rect, name, and anchor point for visual debugging.
        hot_reload: When True, watches loaded layout files and rebuilds the UI whenever they change on disk.
    """

    def __init__(self, hot_reload: bool = True):
        self.debug_draw: bool = False
        self.hot_reload: bool = hot_reload

        self._hovered = None
        self._pressed = None
        self._mouse_over_ui: bool = False

        # hot reload bookkeeping
        self._loaded_path: str | None = None
        self._loaded_scene = None
        self._loaded_actions: dict = {}
        self._last_mtime: float = 0.0

        self._focused = None

        self._debug_font: pygame.font.Font | None = None

    # INPUT ROUTING
    @property
    def mouse_over_ui(self) -> bool:
        """Whether the mouse is currently over any interactive UI element.

        Check this before acting on a click in game code, so clicking a button doesn't also click through to the world behind it.
        """
        return self._mouse_over_ui

    # LAYOUT LOADING
    def load_layout(self, path: str, scene, actions: dict = None) -> None:
        """Build a UI from a JSON layout file and add it to a scene.

        Args:
            path: Path to the JSON layout file.
            scene: The Scene to add the created UI GameObjects to.
            actions: Maps action names in the JSON to Python callables.
                     A button with "action": "start_game" calls actions["start_game"] when clicked.
        """
        from ..utils.ui_loader import build_layout

        self._loaded_path = path
        self._loaded_scene = scene
        self._loaded_actions = actions or {}
        self._last_mtime = os.path.getmtime(path) if os.path.exists(path) else 0.0

        build_layout(path, scene, self._loaded_actions)

    def reload_layout(self) -> None:
        """Rebuild the current layout from disk, discarding the old UI."""
        if not self._loaded_path or not self._loaded_scene:
            return

        from ..utils.ui_loader import build_layout

        # remove all existing UI objects from the scene
        for obj in list(self._loaded_scene._game_objects):
            if obj.layer == UI_LAYER:
                self._loaded_scene.remove_object(obj)

        build_layout(self._loaded_path, self._loaded_scene, self._loaded_actions)

    # INTERNAL — FRAME PASSES
    def _check_hot_reload(self) -> None:
        if not self.hot_reload or not self._loaded_path:
            return
        if not os.path.exists(self._loaded_path):
            return
        mtime = os.path.getmtime(self._loaded_path)
        if mtime > self._last_mtime:
            self._last_mtime = mtime
            self.reload_layout()

    def _forward_text_input(self):
        if self._focused is None:
            return
        if pymod.input.key_pressed("escape"):
            self._focused.focused = False
            self._focused = None
            return
        for ch in pymod.input.text_typed:
            if ch.isprintable():
                self._focused.type_char(ch)
        if pymod.input.key_pressed("backspace"):
            self._focused.backspace()

    def _update(self, scene) -> None:
        """Internal method called each frame by Game. Recalculates layout, routes input, and handles hot-reload."""
        self._check_hot_reload()

        ui_objects = [o for o in scene._game_objects if o.layer == UI_LAYER]
        if not ui_objects:
            self._mouse_over_ui = False
            return

        self._recalculate_layout(ui_objects)
        self._route_input(ui_objects)
        self._forward_text_input()

    def _recalculate_layout(self, ui_objects) -> None:
        """Recompute every UIRect top-down, parents before children, then run any layout groups which reposition their children."""
        from ..components.ui.ui_rect import UIRect
        from ..components.ui.layouts import LayoutGroup

        roots = [o for o in ui_objects if o.parent is None]

        def recurse(obj):
            rect_comp = obj.get_component(UIRect)
            if rect_comp is not None:
                rect_comp.recalculate()

            # a layout group repositions its children before they resolve
            for component in obj._components.values():
                if isinstance(component, LayoutGroup):
                    component.arrange()

            for child in obj.children:
                recurse(child)

        for root in roots:
            recurse(root)

    def _route_input(self, ui_objects) -> None:
        """Find the topmost interactive element under the mouse and give it
        hover/press state. Later objects draw on top, so search in reverse."""
        from ..components.ui.ui_rect import UIRect
        from ..components.ui.widgets import UIInteractive, UIDropdown, UITextInput

        mouse = pymod.input.mouse_position
        mouse = pymod.Game.get().screen.window_to_render_coordinates(mouse)

        found = None
        for obj in reversed(ui_objects):
            rect_comp = obj.get_component(UIRect)
            if rect_comp is None or not rect_comp.contains_point(*mouse):
                continue
            for component in obj._components.values():
                if isinstance(component, UIInteractive) and component.interactable:
                    found = component
                    break
            if found:
                break

        self._mouse_over_ui = found is not None

        # an expanded dropdown's option list extends below its own rect,
        # so it isn't caught by the normal hit test
        for obj in ui_objects:
            dd = obj.get_component(UIDropdown)
            if dd is not None and dd.open:
                rc = obj.get_component(UIRect)
                if rc is not None:
                    r = rc.rect
                    listbox = pygame.Rect(r.left, r.bottom, r.width,
                                          r.height * len(dd.options))
                    if listbox.collidepoint(*mouse):
                        self._mouse_over_ui = True

        # hover transitions
        if self._hovered is not found:
            if self._hovered is not None:
                self._hovered._on_hover_exit()
            if found is not None:
                found._on_hover_enter()
            self._hovered = found

        # focus: a click anywhere re-decides which text field owns the keyboard
        if pymod.input.mouse_pressed("left"):
            new_focus = found if isinstance(found, UITextInput) else None
            if self._focused is not new_focus:
                if self._focused is not None:
                    self._focused.focused = False
                self._focused = new_focus
                if new_focus is not None:
                    new_focus.focused = True

        # press / release
        if found is not None:
            if pymod.input.mouse_pressed("left"):
                self._pressed = found
                found._on_press()
            elif pymod.input.mouse_released("left"):
                if self._pressed is found:
                    found._on_release()
                    found._on_click()
                self._pressed = None
        elif pymod.input.mouse_released("left"):
            if self._pressed is not None:
                self._pressed._on_release()
            self._pressed = None



    def _draw(self, scene) -> None:
        """Internal method called by Game after the world render pass. Draws all UI in screen space, ignoring the camera."""

        ui_objects = [o for o in scene._game_objects if o.layer == UI_LAYER]
        if not ui_objects:
            return

        surface = pymod.Game.get().screen.render_surface

        # draw roots first, then descend — children draw over parents
        roots = [o for o in ui_objects if o.parent is None]

        def recurse(obj):
            if obj.visible:
                for component in obj._components.values():
                    if hasattr(component, "draw_ui"):
                        component.draw_ui(surface)

            from ..components.ui.widgets import UIScrollView
            from ..components.ui.ui_rect import UIRect
            sv = obj.get_component(UIScrollView)
            if sv is not None:
                rc = obj.get_component(UIRect)
                old_clip = surface.get_clip()
                surface.set_clip(rc.rect)
                for child in obj.children:
                    crc = child.get_component(UIRect)
                    if crc is not None:
                        crc._rect.y -= int(sv.scroll_offset)
                    recurse(child)
                    if crc is not None:
                        crc._rect.y += int(sv.scroll_offset)
                surface.set_clip(old_clip)
                return
            for child in obj.children:
                recurse(child)

        for root in roots:
            recurse(root)

        # overlay pass — tooltips and open dropdown lists must sit above
        # everything else regardless of hierarchy order
        def recurse_overlay(obj):
            if obj.visible:
                for component in obj._components.values():
                    if hasattr(component, "draw_ui_overlay"):
                        component.draw_ui_overlay(surface)
            for child in obj.children:
                recurse_overlay(child)

        for root in roots:
            recurse_overlay(root)

        if self.debug_draw:
            self._draw_debug(surface, ui_objects)

    def _draw_debug(self, surface, ui_objects) -> None:
        """Overlay every element's rect, name, and anchor point."""
        from ..components.ui.ui_rect import UIRect

        if self._debug_font is None:
            self._debug_font = pygame.font.Font(None, 16)

        for obj in ui_objects:
            rect_comp = obj.get_component(UIRect)
            if rect_comp is None:
                continue
            r = rect_comp.rect

            pygame.draw.rect(surface, (255, 0, 255), r, 1)

            # anchor point marker
            parent_rect = rect_comp.get_parent_rect()
            pygame.draw.circle(
                surface, (255, 255, 0),
                (int(r.x + r.width * rect_comp.pivot[0]),
                 int(r.y + r.height * rect_comp.pivot[1])),
                3,
            )

            label = self._debug_font.render(
                f"{obj.name} {r.width}x{r.height}", True, (255, 0, 255)
            )
            surface.blit(label, (r.x + 2, r.y + 2))