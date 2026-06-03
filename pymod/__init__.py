from .core import Component
from .core import GameObject
from .core import Scene
from .core import SceneManager
from .core import Game

from .managers import TimeManager
from .managers import InputManager
from .managers import ScreenManager

from .utils import Timer
from .utils import Stopwatch

class _ManagerProxy:
    def __init__(self, manager_name: str):
        self._name = manager_name

    def __getattr__(self, attr: str):
        return getattr(Game.get().__dict__[self._name], attr)

scenes: SceneManager = _ManagerProxy('scenes')
time: TimeManager = _ManagerProxy('time')
input: InputManager = _ManagerProxy('input')
screen_manager: ScreenManager = _ManagerProxy('screen_manager')