from .core import Component
from .core import GameObject
from .core import Scene
from .core import SceneManager
from .core import Game

class _ManagerProxy:
    def __init__(self, manager_name: str):
        self._name = manager_name

    def __getattr__(self, attr: str):
        return getattr(Game.get().__dict__[self._name], attr)

scenes = _ManagerProxy('scenes')