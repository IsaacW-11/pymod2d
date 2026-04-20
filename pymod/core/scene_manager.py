from __future__ import annotations
from typing import TYPE_CHECKING

from pymod.utils.exceptions import EmptySceneManagerStack

if TYPE_CHECKING:
    from .scene import Scene

class SceneManager:
    """Manages the Scene stack.

    Attributes:
        _stack: List to store all active scenes.
    """
    def __init__(self):
        self._stack: list[Scene] = []

    def __len__(self) -> int:
        return len(self._stack)

    @property
    def current(self):
        """Returns current active scene."""
        return self._stack[-1] if self._stack else None

    def push(self, scene: Scene):
        """Pushes a new scene to the stack.

        The current scene is paused and the new scene is entered.
        Use this for overlays such as pause menus and inventory screens.

        Args:
            scene: New scene to push to the stack.
        """
        if self._stack:
            self.current.on_pause()
        self._stack.append(scene)
        scene.on_enter()

    def pop(self):
        """Pops the current active scene off the stack.

        The current scene is exited and the previous scene is resumed.
        Use this to close overlays and return to the scene underneath.
        """
        if not self._stack:
            raise EmptySceneManagerStack("Unable to pop from empty scene manager")

        self.current.on_exit()
        self._stack.pop()
        if self._stack:
            self.current.on_resume()

    def swap(self, scene: Scene):
        """Swaps the current scene with a new scene.

        The current scene is exited and the new scene is entered.
        Use this for full scene transitions such as main menus or new levels.
        Swapping is the same thing as doing ``pop()`` followed by ``push(scene)``.
        Unlike push, there will be no scene to resume underneath.

        Args:
            scene: New scene to swap to.
        """
        if self._stack:
            self.current.on_exit()
            self._stack.pop()
        self._stack.append(scene)
        scene.on_enter()

    def clear(self):
        """Clears all scenes from the stack."""
        while self._stack:
            self.current.on_exit()
            self._stack.pop()

    def _update(self):
        """Internal method to update the current scene."""
        if self._stack:
            self.current._update()

    def _draw(self):
        """Internal method to draw the current scene."""
        if self._stack:
            self.current._draw()