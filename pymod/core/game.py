from __future__ import annotations
from typing import TYPE_CHECKING

import pygame
from .scene_manager import SceneManager
from pymod.utils.exceptions import ExistingGameInstance, MissingGameInstance

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

    def __init__(self, title: str="Untitled Project", width: int=1920, height: int=1080, fps: int=60):
        """Initializes game instance.

        Args:
            title: The title of the game. Defaults to 'Untitled Project'.
            width: Width of game window. Defaults to 1920.
            height: Height of game window. Defaults to 1080.
            fps: Frame per second cap of game. Defaults to 60. Can be changed later on.

        Raises:
            ExistingGameInstance: The game instance already exists.
        """
        if Game._instance is not None:
            raise ExistingGameInstance("Only one Game Instance can exist at a time.")
        Game._instance = self

        self.title: str = title
        self.width: int = width
        self.height: int = height
        self.fps: int = fps

        self.running: bool = False

        pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(self.title)
        self._clock: pygame.time.Clock = pygame.time.Clock()

        # managers
        self.scenes: SceneManager = SceneManager()

    def run(self, start_scene: Scene):
        """Starts the game loop.

        Args:
            start_scene: The scene to start the game from.
        """
        self.scenes.push(start_scene)

        self.running = True
        while self.running:
            self._clock.tick(self.fps)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            self.scenes._update()

            self.screen.fill((0, 0, 0))
            self.scenes._draw()
            pygame.display.flip()

        self._shutdown()

    def quit(self):
        """Allows the game to be stopped cleanly from anywhere in the codebase."""
        self.running = False

    def _shutdown(self):
        """Internal cleanup method automatically called when the loop ends."""
        self.scenes.clear()

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