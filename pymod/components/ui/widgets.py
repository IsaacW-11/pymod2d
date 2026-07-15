from __future__ import annotations

import pygame

import pymod
from .ui_rect import UIRect


class UIInteractive(pymod.Component):
    """Base for UI components that respond to mouse hover and clicks.

    The UIManager drives the state transitions. It calls the _on_* hooks when the mouse enters, leaves, presses, releases, or clicks this element.
    Widgets override the hooks they care about. `interactable` can be toggled to disable interaction without removing the component.

    Attributes:
        interactable: Whether this element responds to input at all.
        hovered: Whether the mouse is currently over this element.
        pressed: Whether the mouse button is currently held on this element.
    """

    def __init__(self):
        super().__init__()
        self.interactable: bool = True
        self.hovered: bool = False
        self.pressed: bool = False

    def _on_hover_enter(self) -> None:
        self.hovered = True
        self.on_hover_enter()

    def _on_hover_exit(self) -> None:
        self.hovered = False
        self.pressed = False
        self.on_hover_exit()

    def _on_press(self) -> None:
        self.pressed = True
        self.on_press()

    def _on_release(self) -> None:
        self.pressed = False
        self.on_release()

    def _on_click(self) -> None:
        self.on_click()

    # override these in widgets
    def on_hover_enter(self) -> None: ...
    def on_hover_exit(self) -> None: ...
    def on_press(self) -> None: ...
    def on_release(self) -> None: ...
    def on_click(self) -> None: ...

    def _rect(self) -> pygame.Rect:
        rc = self.owner.get_component(UIRect)
        return rc.rect if rc else pygame.Rect(0, 0, 0, 0)