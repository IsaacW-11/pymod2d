from __future__ import annotations
from typing import TYPE_CHECKING

import warnings

if TYPE_CHECKING:
    from pymod import GameObject

class Scene:
    """Template class for Scene.

    All Scenes must inherit from this class.

    Attributes:
        _game_objects: List to store all attached game objects.
    """
    def __init__(self):
        self._game_objects: list[GameObject] = []

    def __len__(self) -> int:
        return len(self._game_objects)

    def on_enter(self):
        """Called every time scene is entered into the SceneManager stack.

        This function is where game_objects should be created and added to the Scene
        """
        pass

    def on_exit(self):
        """Called every time the scene is removed from the SceneManager stack.

        Can be used for custom cleanup logic. Note that the SceneManager does automatically remove all GameObjects, and this function is for custom logic.
        """
        pass

    def on_pause(self):
        """Called anytime the scene is paused.

        A scene is paused whenever another scene is entered in-front on the SceneManager stack. This means the Scene is no longer calling update and draw methods, but isn't unloaded from memory.
        """
        pass

    def on_resume(self):
        """Called anytime the scene is resumed.

        A scene is paused whenever another scene is removed in-front on the SceneManager stack and this Scene is now the highest. This means the Scene is now active, but it doesn't need to reload any game_objects.
        """
        pass

    def add_object(self, game_object: GameObject):
        """Method to add game_object to the Scene.

        Args:
            game_object: The GameObject to add.

        Returns:
            The Scene that called this function to allow for chaining.
        """
        game_object.scene = self

        self._game_objects.append(game_object)

        return self

    def remove_object(self, game_object: GameObject):
        """Method to remove game_object to the Scene.

        Args:
            game_object: The GameObject to remove.

        Returns:
            The Scene that called this function to allow for chaining.
        """
        if game_object in self._game_objects:
            self._game_objects.remove(game_object)
        else:
            warnings.warn(f"GameObject {type(game_object).__name__} not found in Scene", UserWarning, stacklevel=2)
        return self

    def _update(self):
        """Internal method to update all GameObjects"""
        for game_object in self._game_objects:
            game_object._update()

    def _draw(self):
        """Internal method to draw all GameObjects"""
        for game_object in self._game_objects:
            game_object._draw()