from __future__ import annotations
from typing import TYPE_CHECKING, TypeVar

from pymod.utils.exceptions import MissingComponentError

if TYPE_CHECKING:
    from .component import Component
    from .scene import Scene

T = TypeVar("T", bound="Component")

class GameObject:
    """Template class for GameObject.

    All GameObjects must inherit from this class.

    Attributes:
        _components: Dictionary to store all attached components.
        scene: Stores the scene that the GameObject belongs to.
    """

    def __init__(self):
        self._components: dict[type[Component], Component] = {}
        self.scene: Scene | None = None

    def __len__(self) -> int:
        return len(self._components)

    def __repr__(self) -> str:
        component_names = [component.__name__ for component in self._components.keys()]
        return f"{type(self).__name__}(components={component_names})"

    def add_component(self, component: Component) -> GameObject:
        """Method to add a component to the game object.

        Args:
            component: The component to add. Must be an instance of a Component class or subclass.

        Returns:
            The GameObject that called this function. This allows for chaining.
        """
        self._components[type(component)] = component
        component.owner = self
        component.on_attach()

        return self # allows chaining

    def remove_component(self, component_type: type[Component]) -> GameObject:
        """Method to remove a component from the game object.

        Args:
            component_type: The type of the Component subclass you want to remove.

        Returns:
            The GameObject that called this function. This allows for chaining.
        """
        component = self._components.pop(component_type, None)
        if component:
            component.on_destroy()

        return self # allows chaining

    def get_component(self, component_type: type[T]) -> T | None:
        """Method to get a reference to a component from the GameObject.

        Args:
            component_type: The type of the Component subclass you want to get.

        Returns:
            Returns the reference to the Component or None if the component is not found.
        """
        return self._components.get(component_type)

    def require_component(self, component_type: type[T]) -> T:
        """Method to require a component from the GameObject.

        This is almost identical to ``get_component()`` but instead of returning ``None`` when there is no component, it raises an ``Exception()``

        Args:
            component_type: The type of the Component subclass you want to get.

        Returns:
            Returns the reference to the Component

        Raises:
            MissingComponentError: If the component is not found.
        """
        component = self._components.get(component_type, None)
        if component is None:
            raise MissingComponentError(f"Component of type {component_type.__name__} not found")

        return component

    def has_component(self, component_type: type[Component]) -> bool:
        """Method to check if a component exists in the GameObject.

        Args:
            component_type: The type of the Component subclass you want to get.

        Returns:
            True if the component exists in the GameObject, False otherwise.
        """
        return component_type in self._components

    def _update(self):
        """Internal method to update all components attached to this GameObject."""
        for component in self._components.values():
            component._update()

    def _draw(self):
        """Internal method to draw all components attached to this GameObject."""
        for component in self._components.values():
            component._draw()