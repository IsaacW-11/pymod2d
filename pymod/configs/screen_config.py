from dataclasses import dataclass

from pymod.managers.screen_manager import GameScaleMode, DisplayMode, ScaleFit

@dataclass
class ScreenConfig:
    title: str = "Untitled Project"
    window_size: tuple[int, int] = (1280, 720)
    display_mode: DisplayMode = DisplayMode.WINDOWED
    game_scale_mode: GameScaleMode = GameScaleMode.EXPAND
    scale_fit: ScaleFit = ScaleFit.FIT
    base_resolution: tuple[int, int] = (1280, 720)
    target_resolution: tuple[int, int] = (1920, 1080)
    vsync: bool = False