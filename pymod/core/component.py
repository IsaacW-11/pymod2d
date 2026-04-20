from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .game_object import GameObject

class Component:
    """Template class for a component.

    All components must inherit from this class.

    Attributes:
        owner: The GameObject that the component is attached to.
        enabled: Whether the component is enabled or not.
        _started: Internal attribute to keep track of whether the ``on_start()`` function has been called.
    """
    def __init__(self):
        self.owner: GameObject | None = None
        self.enabled: bool = True
        self._started: bool = False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(owner={type(self.owner).__name__})"

    def on_attach(self):
        """Called by GameObject.add() the moment the component is added.

        Used only for self setup. Do not reference external components
        """
        pass

    def on_start(self):
        """
        Called a singular time on the first frame after all components have been attached.

        Safe to reference external components.
        """
        pass

    def update(self):
        """Called once every frame."""
        pass

    def draw(self):
        """Called once every frame after update."""
        pass

    def on_enable(self):
        """Called whenever ``Component`` is re-enabled."""
        pass

    def on_disable(self):
        """Called whenever ``Component`` is disabled."""
        pass

    def on_destroy(self):
        """Called whenever the owner ``GameObject`` is destroyed."""
        pass

    def destroy(self):
        """Shortcut to remove ``self`` from ``GameObject``.

        Can be used as an alternative to ``self.owner.remove_component(type(self))``
        """
        self.owner.remove_component(type(self))

    def _update(self):
        """Method to decide whether ``on_start()`` should be called, or if only ``update()`` is called.

        This method should only be called internally, and should never be accessed by the public API.
        """
        if not self._started:
            self._started = True
            self.on_start()
        if self.enabled:
            self.update()

    def _draw(self):
        """Method to decide if component should be drawn or not.

        This method should only be called internally, and should never be accessed by the public API.
        """
        if self._started and self.enabled:
            self.draw()