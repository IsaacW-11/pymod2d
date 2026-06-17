from .core import Component
from .core import GameObject
from .core import Scene
from .core import SceneManager
from .core import Game

from .managers import TimeManager
from .managers import InputManager
from .managers import ScreenManager
from .managers import EventManager

from .utils import Timer
from .utils import Stopwatch

from .managers.screen_manager import ScaleFit
from .managers.screen_manager import GameScaleMode
from .managers.screen_manager import DisplayMode

from .managers.event_manager import Event

from .configs.screen_config import ScreenConfig
from .configs.input_config import InputConfig
from .configs.time_config import TimeConfig

class _ManagerProxy:
    def __init__(self, manager_name: str):
        self._name = manager_name

    def __getattr__(self, attr: str):
        return getattr(Game.get().__dict__[self._name], attr)

scenes: SceneManager = _ManagerProxy('scenes')
time: TimeManager = _ManagerProxy('time')
input: InputManager = _ManagerProxy('input')
screen: ScreenManager = _ManagerProxy('screen')
events: EventManager = _ManagerProxy('events')