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

    def __init__(self, x: float = 0.0, y: float = 0.0, layer: str = "default"):
        self._components: dict[type[Component], Component] = {}
        self.scene: Scene | None = None

        self.x: float = x
        self.y: float = y
        self.layer: str = layer
        self.tags: set[str] = set()
        self.active: bool = True  # whether update runs
        self.visible: bool = True  # whether draw runs

        self.parent: GameObject | None = None
        self.children: list[GameObject] = []
        self.local_x: float = 0.0  # position relative to parent
        self.local_y: float = 0.0

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

    def add_child(self, child: GameObject) -> GameObject:
        """Parent another GameObject to this one.

        The child's world position becomes relative to this object. Moving the parent moves all children with it.
        The child's current world position is preserved at the moment of parenting.

        Args:
            child: The GameObject to parent to this one.

        Returns:
            This GameObject, for chaining.
        """
        if child.parent is not None:
            child.parent.remove_child(child)

        child.parent = self
        child.local_x = child.x - self.x
        child.local_y = child.y - self.y
        self.children.append(child)
        return self

    def remove_child(self, child: GameObject) -> GameObject:
        """Unparent a child, preserving its current world position."""
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            child.local_x = 0.0
            child.local_y = 0.0
        return self

    def set_parent(self, parent: GameObject | None) -> GameObject:
        """Set this object's parent, or None to unparent."""
        if parent is None:
            if self.parent is not None:
                self.parent.remove_child(self)
        else:
            parent.add_child(self)
        return self

    def _sync_children(self) -> None:
        """Internal method to push this object's world position down to children.

        Called each frame after updates so children follow their parent.
        Recurses so nested hierarchies work.
        """
        for child in self.children:
            child.x = self.x + child.local_x
            child.y = self.y + child.local_y
            child._sync_children()

    def _update(self):
        """Internal method to update all components attached to this GameObject."""
        if not self.active:
            return
        for component in self._components.values():
            component._update()

    def _fixed_update(self):
        """Internal method to update all components attached to this GameObject. Used for physics based calculations."""
        if not self.active:
            return
        for component in self._components.values():
            component._fixed_update()

    def _draw(self):
        """Internal method to draw all components attached to this GameObject."""
        if not self.visible:
            return
        for component in self._components.values():
            component._draw()