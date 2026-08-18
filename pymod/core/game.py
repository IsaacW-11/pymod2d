from __future__ import annotations
from typing import TYPE_CHECKING

import pygame

from ..managers.ui_manager import UIManager
from ..managers.audio_manager import AudioManager
from ..managers.event_manager import EventManager
from ..managers.physics_manager import PhysicsManager
from ..managers.collision_manager import CollisionManager
from .scene_manager import SceneManager
from ..managers.screen_manager import ScreenManager
from ..managers.input_manager import InputManager
from ..managers.time_manager import TimeManager
from ..managers.asset_manager import AssetManager
from ..managers.camera_manager import CameraManager
from ..utils.exceptions import ExistingGameInstance, MissingGameInstance
from ..configs.screen_config import ScreenConfig
from ..configs.input_config import InputConfig
from ..configs.time_config import TimeConfig
from ..configs.asset_config import AssetConfig

if TYPE_CHECKING:
    from .scene import Scene

class Game:
    """Core game class for pymod.

    Only one game instance can exist at a time.
    Creates the game window, initializes all managers, and runs game loop.

    Attributes:
        width: The width of the game window.
        height: The height of the game window.
        fps: FPS cap of game window.
        screen: The pygame screen object.
        running: Whether the game is running.
    """

    _instance: Game | None = None

    # Fixed-timestep safety limits.
    #
    # Without these the accumulator loop below is unstable: running the fixed
    # steps itself costs real time, which lands in the next frame's delta. Once
    # the work per step exceeds fixed_delta^2 / frame_time the accumulator grows
    # every frame and the while loop never exits, so the window stops responding
    # and has to be killed. Unity exposes the same guard as "Maximum Allowed
    # Timestep".
    MAX_FIXED_STEPS: int = 5      # most fixed updates allowed in one frame
    MAX_FRAME_DELTA: float = 0.25 # never accept more than 250ms from one frame

    def __init__(self,
                 screen_config: ScreenConfig = None,
                 time_config: TimeConfig = None,
                 input_config: InputConfig = None,
                 asset_config: AssetConfig = None):
        """Initializes game instance.

        Args:
            screen_config: Config file for the ScreenManager.
            time_config: Config file for the TimeManager.
            input_config: Config file for the InputManager..

        Raises:
            ExistingGameInstance: The game instance already exists.
        """
        if Game._instance is not None:
            raise ExistingGameInstance("Only one Game Instance can exist at a time.")
        Game._instance = self

        self.screen_config: ScreenConfig = screen_config or ScreenConfig()
        self.time_config: TimeConfig = time_config or TimeConfig()
        self.input_config: InputConfig = input_config or InputConfig()
        self.asset_config: AssetConfig = asset_config or AssetConfig()

        self.title: str = self.screen_config.title
        self.width: int = self.screen_config.window_size[0]
        self.height: int = self.screen_config.window_size[1]
        self.fps: int = self.time_config.fps

        self.running: bool = False

        self._accumulator: float = 0.0

        pygame.init()
        pygame.display.set_caption(self.title)
        self._clock: pygame.time.Clock = pygame.time.Clock()

        # managers
        self.scenes: SceneManager = SceneManager()
        self.time: TimeManager = TimeManager(fps_history_size=self.time_config.fps_history_size)
        self.input: InputManager = InputManager(default_bindings=self.input_config.default_bindings)
        self.screen: ScreenManager = ScreenManager(title=self.screen_config.title,
                                                           window_size=self.screen_config.window_size,
                                                           display_mode=self.screen_config.display_mode,
                                                           game_scale_mode=self.screen_config.game_scale_mode,
                                                           scale_fit=self.screen_config.scale_fit,
                                                           base_resolution=self.screen_config.base_resolution,
                                                           target_resolution=self.screen_config.target_resolution,
                                                           vsync=self.screen_config.vsync)
        self.events: EventManager = EventManager()
        self.assets: AssetManager = AssetManager(self.asset_config.root, self.asset_config.auto_scan, self.asset_config.preload)
        self.camera: CameraManager = CameraManager()
        self.collision: CollisionManager = CollisionManager()
        self.physics: PhysicsManager = PhysicsManager()
        self.audio: AudioManager = AudioManager()
        self.ui: UIManager = UIManager()

    def run(self, start_scene: Scene):
        """Starts the game loop.

        Args:
            start_scene: The scene to start the game from.
        """
        self.scenes.push(start_scene)

        self.running = True
        self._accumulator = 0.0

        while self.running:
            dt = self._clock.tick(self.fps) / 1000

            # A single very long frame (alt-tab, a debugger breakpoint, a disk
            # stall) would otherwise inject a huge delta and immediately
            # overload the fixed-step loop below.
            if dt > self.MAX_FRAME_DELTA:
                dt = self.MAX_FRAME_DELTA

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                self.input._handle_event(event)
                self.screen._handle_event(event)

            self.time._update(dt)
            self.input._update()
            self.audio._update()
            self.scenes._update()
            self.camera._update()
            self.events._flush_queue() # all queued events fire after scenes update

            # fixed update — clamped so it can never spiral
            self._accumulator += self.time.delta

            steps = 0
            while (self._accumulator >= self.time.fixed_delta
                   and steps < self.MAX_FIXED_STEPS):
                self.scenes._fixed_update()
                self._accumulator -= self.time.fixed_delta
                steps += 1

            # Hitting the cap means this machine cannot sustain the fixed rate.
            # DISCARD the backlog instead of trying to catch up: keeping it
            # would leave the next frame already behind and the deficit would
            # compound until the loop never exits. The visible effect is that
            # simulation runs slightly slow on weak hardware, which is a far
            # better failure mode than a hard freeze.
            if steps >= self.MAX_FIXED_STEPS:
                self._accumulator = 0.0

            self.screen.render_surface.fill((0, 0, 0)) # clears previous frames display
            self.camera._render(self.scenes, self.screen.render_surface)

            current = self.scenes.current
            if current is not None:
                self.ui._update(current)
                self.ui._draw(current)

            self.screen._present()

            pygame.display.flip()

        self._shutdown()

    def quit(self):
        """Allows the game to be stopped cleanly from anywhere in the codebase."""
        self.running = False

    def _shutdown(self):
        """Internal cleanup method automatically called when the loop ends."""
        self.scenes.clear()
        self.audio._shutdown()

        pygame.quit()
        Game._instance = None

    @classmethod
    def get(cls) -> Game:
        """Get the current game instance from anywhere in the codebase.

        Returns:
            Game: The current game instance.

        Raises:
            MissingGameInstance: The game instance is missing.
        """
        if cls._instance is None:
            raise MissingGameInstance("No game instance has been created.")
        return cls._instance