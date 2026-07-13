from .core import Component
from .core import GameObject
from .core import Scene
from .core import SceneManager
from .core import Game

from .managers import TimeManager
from .managers import InputManager
from .managers import ScreenManager
from .managers import EventManager
from .managers import AssetManager
from .managers import CameraManager
from .managers import CollisionManager
from .managers import PhysicsManager
from .managers import AudioManager

from .utils import Timer
from .utils import Stopwatch
from .utils import Viewport
from .utils import SpatialGrid

from .managers.screen_manager import ScaleFit
from .managers.screen_manager import GameScaleMode
from .managers.screen_manager import DisplayMode

from .managers.event_manager import Event

from .configs.screen_config import ScreenConfig
from .configs.input_config import InputConfig
from .configs.time_config import TimeConfig
from .configs.asset_config import AssetConfig

from . import prebuilt_components as Prebuilts

from .components import Anchor

from .events import CollisionEvent

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
assets: AssetManager = _ManagerProxy('assets')
camera: CameraManager = _ManagerProxy('camera')
collision: CollisionManager = _ManagerProxy('collision')
physics: PhysicsManager = _ManagerProxy('physics')
audio: AudioManager = _ManagerProxy('audio')