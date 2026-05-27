from __future__ import annotations
from enum import Enum, auto

import pygame

class DisplayMode(Enum):
    """The display mode of the window.

    WINDOWED: Resizable window
    FULLSCREEN: Fullscreen window. Changes resolution.
    BORDERLESS: Borderless window matching the screen size. Also known as Windowed Fullscreen.
    """
    WINDOWED = auto()
    FULLSCREEN = auto()
    BORDERLESS = auto()

class GameScaleMode(Enum):
    """How the game world scales with the window.

    EXPAND: Bigger window shows more of the world. No scaling occurs.
            Camera viewport grows with window size.

    SCALE: Bigger window makes everything bigger.
           Camera viewport stays fixed, scaled up to fill window.

    MIXED: Scale up to a target resolution, then expand beyond it.
    """
    EXPAND = auto()
    SCALE = auto()
    MIXED = auto()

class ScaleFit(Enum):
    """How the game is fitted to the window in SCALE or MIXED modes.

    Only relevant when GameScaleMode is SCALE or MIXED.

    FIT: Maintain aspect ratio, add black bars where needed.
    STRETCH: Fill window completely, ignore aspect ratio.
    INTEGER: Scale by integer multiples only. Crisp pixel art.
    LETTERBOX: Maintain aspect ratio, black bars top and bottom only.
    PILLARBOX: Maintain aspect ratio, black bars left and right only.
    """
    FIT = auto()
    STRETCH = auto()
    INTEGER = auto()
    LETTERBOX = auto()
    PILLARBOX = auto()


class ScreenManager:
    """Manages the game window, display modes, and game layer scaling.

       Separates game scaling from UI scaling. The ScreenManager is only
       responsible for the window and the game world layer. UI scaling is
       handled entirely by the UIManager.

       In EXPAND mode the render surface matches the window size — a bigger
       window simply exposes more of the world. The camera uses render_size
       to determine how much world is visible.

       In SCALE mode a fixed canvas is rendered at base_resolution and scaled
       to fit the window according to scale_fit. The camera always sees the
       same amount of world regardless of window size.

       In MIXED mode the canvas scales up to target_resolution, then expands
       beyond it like EXPAND mode.

       Attributes:
           _title: Window title.
           _display_mode: Current display mode.
           _game_scale_mode: How the game world scales with the window.
           _scale_fit: How the fixed canvas fits the window in SCALE/MIXED modes.
           _base_resolution: Fixed canvas resolution for SCALE/MIXED modes.
           _target_resolution: Resolution to scale up to before expanding in MIXED mode.
           _window_size: Current OS window size.
           _vsync: Whether vsync is enabled.
           _window_surface: Actual pygame display surface.
           _render_surface: Surface everything renders to.
           _scale_rect: Rect where render surface is drawn on window.
           _scale_factor: Current scale factor from render to window.
       """
    def __init__(self,
                 title: str = "Untitled Project",
                 window_size: tuple[int, int] = (1280, 720),
                 display_mode: DisplayMode = DisplayMode.WINDOWED,
                 game_scale_mode: GameScaleMode = GameScaleMode.EXPAND,
                 scale_fit: ScaleFit = ScaleFit.FIT,
                 base_resolution: tuple[int, int] = (1280, 720),
                 target_resolution: tuple[int, int] = (1920, 1080),
                 vsync: bool = False):

        self._title: str = title
        self._window_size: tuple[int, int] = window_size
        self._display_mode: DisplayMode = display_mode
        self._game_scale_mode: GameScaleMode = game_scale_mode
        self._scale_fit: ScaleFit = scale_fit
        self._base_resolution: tuple[int, int] = base_resolution
        self._target_resolution: tuple[int, int] = target_resolution
        self._vsync: bool = vsync

        self._window_surface: pygame.Surface = None
        self._render_surface: pygame.Surface = None
        self._scale_rect: pygame.Rect = pygame.Rect(0, 0, *window_size)
        self._scale_factor: float = 1.0

        self._apply_display_mode()

    # PROPERTIES
    @property
    def render_surface(self) -> pygame.Surface:
        """This returns the surface that all rendering should target.

        In EXPAND mode this is the window surface directly.
        In SCALE and MIXED modes this is the fixed canvas.
        Never render to the window_surface.
        """
        return self._render_surface

    @property
    def render_size(self) -> tuple[int, int]:
        """Current render dimensions in pixels.

        In EXPAND mode this changes when the window is resized.
        In SCALE mode this is always base_resolution.
        In MIXED mode this is base_resolution until the window exceeds
        target_resolution, then it grows with the window.
        """
        return self._render_surface.get_size()

    @property
    def render_width(self) -> int:
        """Current render width in pixels."""
        return self.render_size[0]

    @property
    def render_height(self) -> int:
        """Current render height in pixels."""
        return self.render_size[1]

    @property
    def window_size(self) -> tuple[int, int]:
        """Current window size in pixels."""
        return self._window_size

    @property
    def window_width(self) -> int:
        """Current window width in pixels."""
        return self._window_size[0]

    @property
    def window_height(self) -> int:
        """Current window height in pixels."""
        return self._window_size[1]

    @property
    def display_mode(self) -> DisplayMode:
        """Current display mode."""
        return self._display_mode

    @property
    def game_scale_mode(self) -> GameScaleMode:
        """Current game scale mode."""
        return self._game_scale_mode

    @property
    def scale_fit(self) -> ScaleFit:
        """Current scale fit.

        Only relevant for MIXED and SCALE modes.
        """
        return self._scale_fit

    @property
    def base_resolution(self) -> tuple[int, int]:
        """Base resolution for MIXED and SCALE modes."""
        return self._base_resolution

    @property
    def target_resolution(self) -> tuple[int, int]:
        """Target resolution for MIXED mode. Window expands once it reaches beyond this resolution."""
        return self._target_resolution

    @property
    def scale_factor(self) -> float:
        """Current scale factor from render surface to window

        Always 1.0 in EXPAND mode.
        """
        return self._scale_factor

    @property
    def scale_rect(self) -> pygame.Rect:
        """Rect where the render surface is drawn on the window.

        Use for coordinate conversion. Always covers full window in EXPAND mode.
        """
        return self._scale_rect

    @property
    def vsync(self) -> bool:
        """Whether vsync is enabled."""
        return self._vsync

    @property
    def title(self) -> str:
        """Current window title"""
        return self._title

    @property
    def is_fullscreen(self) -> bool:
        """Whether window is in FULLSCREEN or BORDERLESS mode."""
        return self._display_mode in (DisplayMode.FULLSCREEN, DisplayMode.BORDERLESS)

    @property
    def center(self) -> tuple[int, int]:
        """Center of the render surface."""
        w, h = self.render_size
        return (w // 2, h // 2)

    @property
    def aspect_ratio(self) -> float:
        """Aspect ratio of the render surface."""
        w, h = self.render_size
        return w / h if h > 0 else 1.0 # in case of division by zero

    # WINDOW SIZE AND RESOLUTION
    def set_window_size(self, width: int, height: int):
        """Set the window size.

        Only applies in WINDOWED display mode.

        Args:
            width: New window width in pixels.
            height: New window height in pixels.
        """
        if self._display_mode != DisplayMode.WINDOWED:
            return

        self._window_size = (width, height)
        self._window_surface = pygame.display.set_mode((width, height),
                                                       self._get_display_flags(),
                                                       vsync=1 if self._vsync else 0)
        self._recalculate_render_surface()

    def set_base_resolution(self, width: int, height: int):
        """Set the base resolution for SCALE and MIXED modes.

        No effect in EXPAND mode.

        Args:
            width: New base width in pixels.
            height: New base height in pixels.
        """
        self._base_resolution = (width, height)
        self._recalculate_render_surface()

    def set_target_resolution(self, width: int, height: int):
        """Set the base resolution for MIXED mode.

        No effect in EXPAND or SCALE modes.

        Args:
            width: New base width in pixels.
            height: New base height in pixels.
        """
        self._target_resolution = (width, height)
        self._recalculate_render_surface()

    def get_available_resolutions(self) -> list[tuple[int, int]]:
        """Get all available display resolutions for the current monitor.

        Returns:
            List of (width, height) tuples, with the largest first.
        """
        modes = pygame.display.list_modes()
        if modes == -1:
            return [self._window_size]
        return sorted(modes, reverse=True)

    def get_native_resolution(self) -> tuple[int, int]:
        """Get the native resolution of the primary monitor.

        Returns:
            Tuple of (width, height) in pixels.
        """
        info = pygame.display.Info()
        return (info.current_w, info.current_h)

    # DISPLAY MODE
    def set_display_mode(self, mode: DisplayMode):
        """Set the display mode.

        Args:
            mode: New display mode to switch to.
        """
        self._display_mode = mode
        self._apply_display_mode()

    def toggle_fullscreen(self):
        """Toggle between windowed and exclusive fullscreen."""
        if self._display_mode == DisplayMode.WINDOWED:
            self.set_display_mode(DisplayMode.FULLSCREEN)
        else:
            self.set_display_mode(DisplayMode.WINDOWED)

    def toggle_borderless(self):
        """Toggle between windowed and borderless fullscreen."""
        if self._display_mode == DisplayMode.WINDOWED:
            self.set_display_mode(DisplayMode.BORDERLESS)
        else:
            self.set_display_mode(DisplayMode.WINDOWED)

    # GAME SCALE MODE
    def set_game_scale_mode(self,
                            mode: GameScaleMode,
                            scale_fit: ScaleFit = None,
                            base_resolution: tuple[int, int] = None,
                            target_resolution: tuple[int, int] = None):
        """Set the game scale mode.

        Args:
            mode: The game scale mode to use.
            scale_fit: How to fit the canvas to the window. Only used in SCALE and MIXED modes. Defaults to current scale_fit.
            base_resolution: Base render resolution for SCALE and MIXED modes. Defaults to current base_resolution.
            target_resolution: Resolution to scale up to before expanding in MIXED mode. Defaults to current target_resolution.
        """
        self._game_scale_mode = mode
        if scale_fit is not None:
            self._scale_fit = scale_fit
        if base_resolution is not None:
            self._base_resolution = base_resolution
        if target_resolution is not None:
            self._target_resolution = target_resolution
        self._recalculate_render_surface()

    def set_scale_fit(self, fit: ScaleFit):
        """Set how the fixed canvas fits the window.

        Only relevant for MIXED and SCALE modes.

        Args:
            fit: The new scale fit mode to use.
        """
        self._scale_fit = fit
        self._recalculate_render_surface()

    # WINDOW PROPERTIES
    def set_title(self, title: str):
        """Set the title for the window"""
        self._title = title
        pygame.display.set_caption(title)

    def set_icon(self, image_path: str):
        """Set the icon for the window"""
        icon = pygame.image.load(image_path)
        pygame.display.set_icon(icon)

    def set_vsync(self, enabled: bool) -> None:
        """Enable or disable vsync.

        Args:
            enabled: Whether to enable vsync.
        """
        self._vsync = enabled
        self._apply_display_mode()

    def set_resizable(self, enabled: bool) -> None:
        """Allow or prevent the user from resizing the window.

        Args:
            enabled: Whether the window should be resizable.
        """
        flags = self._get_display_flags()
        if enabled:
            flags |= pygame.RESIZABLE
        else:
            flags &= ~pygame.RESIZABLE

        self._window_surface = pygame.display.set_mode(self._window_size, flags, vsync=1 if self._vsync else 0)

    # COORDINATE CONVERSION
    def window_to_render_coordinates(self, window_pos: tuple[int, int]) -> tuple[int, int]:
        """Convert a window-space position to render-space position.

        Use this to convert raw mouse coordinates to game coordinates.
        In EXPAND mode this returns the position unchanged since window
        and render space are identical.

        Args:
            window_pos: Position in window coordinates.

        Returns:
            Position in render coordinates.
        """
        if self._game_scale_mode == GameScaleMode.EXPAND:
            return window_pos
        if self._scale_rect.width == 0 or self._scale_rect.height == 0:
            return window_pos

        render_w, render_h = self.render_size
        render_x = (window_pos[0] - self._scale_rect.x) / self._scale_rect.width * render_w
        render_y = (window_pos[1] - self._scale_rect.y) / self._scale_rect.height * render_h
        return (int(render_x), int(render_y))

    def render_to_window_coordinate(self, render_pos: tuple[int, int]) -> tuple[int, int]:
        """Convert a render-space position to window-space position.

        In EXPAND mode this returns the position unchanged.

        Args:
            render_pos: Position in render coordinates.

        Returns:
            Position in window coordinates.
        """
        if self._game_scale_mode == GameScaleMode.EXPAND:
            return render_pos
        render_w, render_h = self.render_size
        window_x = render_pos[0] * self._scale_rect.width / render_w + self._scale_rect.x
        window_y = render_pos[1] * self._scale_rect.height / render_h + self._scale_rect.y
        return (int(window_x), int(window_y))

    # SCREENSHOT
    def screenshot(self, path: str = "screenshot.png") -> None:
        """Save a screenshot of the render surface.

        Args:
            path: File path to save the screenshot to.
        """
        pygame.image.save(self._render_surface, path)

    def screenshot_window(self, path: str = "screenshot.png") -> None:
        """Save a screenshot of the entire window including black bars.

        Args:
            path: File path to save the screenshot to.
        """
        pygame.image.save(self._window_surface, path)

    # INTERNAL METHODS
    def _apply_display_mode(self):
        """Internal method to apply current display mode settings."""
        flags = self._get_display_flags()
        vsync = 1 if self._vsync else 0

        if self._display_mode == DisplayMode.WINDOWED:
            self._window_surface = pygame.display.set_mode(self._window_size, flags, vsync=vsync)
        elif self._display_mode == DisplayMode.FULLSCREEN:
            self._window_surface = pygame.display.set_mode((0, 0), flags | pygame.FULLSCREEN, vsync=vsync)
            self._window_size = self._window_surface.get_size()
        elif self._display_mode == DisplayMode.BORDERLESS:
            self._window_surface = pygame.display.set_mode((0, 0), flags | pygame.NOFRAME, vsync=vsync)
            self._window_size = self._window_surface.get_size()

        pygame.display.set_caption(self._title)
        self._recalculate_render_surface()

    def _get_display_flags(self) -> int:
        """Pygame display flags."""
        flags = 0

        if self._display_mode == DisplayMode.WINDOWED:
            flags |= pygame.RESIZABLE

        return flags

    def _recalculate_render_surface(self):
        """Recalculate render surface and scale rect."""
        window_w, window_h = self._window_size

        if self._game_scale_mode == GameScaleMode.EXPAND:
            # render surface is always the window surface
            # no scaling needed, no fixed canvas
            self._render_surface = self._window_surface
            self._scale_rect = pygame.Rect(0, 0, window_w, window_h)
            self._scale_factor = 1.0
        elif self._game_scale_mode == GameScaleMode.SCALE:
            # fixed canvas scaled to window
            base_w, base_h = self._base_resolution
            if self._render_surface is None or self._render_surface is self._window_surface:
                self._render_surface = pygame.Surface(self._base_resolution)
            self._calculate_scale_rect(base_w, base_h, window_w, window_h)
        elif self._game_scale_mode == GameScaleMode.MIXED:
            target_w, target_h = self._target_resolution
            window_w, window_h = self._window_size

            if window_w <= target_w and window_h <= target_h:
                # below target — behave like SCALE mode
                base_w, base_h = self._base_resolution
                if self._render_surface is None or self._render_surface is self._window_surface:
                    self._render_surface = pygame.Surface(self._base_resolution)
                self._calculate_scale_rect(base_w, base_h, window_w, window_h)
            else:
                # above target — behave like EXPAND mode
                self._render_surface = self._window_surface
                self._scale_rect = pygame.Rect(0, 0, window_w, window_h)
                self._scale_factor = 1.0

    def _calculate_scale_rect(self, render_w: int, render_h: int, window_w: int, window_h: int):
        """Calculates scale rect."""
        if self._scale_fit == ScaleFit.STRETCH:
            self._scale_rect = pygame.Rect(0, 0, window_w, window_h)
            self._scale_factor = window_w / render_w
        elif self._scale_fit == ScaleFit.FIT:
            scale = min(window_w / render_w, window_h / render_h)
            scaled_w = int(render_w * scale)
            scaled_h = int(render_h * scale)
            x = (window_w - scaled_w) // 2
            y = (window_h - scaled_h) // 2
            self._scale_rect = pygame.Rect(x, y, scaled_w, scaled_h)
            self._scale_factor = scale
        elif self._scale_fit == ScaleFit.LETTERBOX:
            scale = window_w / render_w
            scaled_w = window_w
            scaled_h = int(render_h * scale)
            y = (window_h - scaled_h) // 2
            self._scale_rect = pygame.Rect(0, y, scaled_w, scaled_h)
            self._scale_factor = scale
        elif self._scale_fit == ScaleFit.PILLARBOX:
            scale = window_h / render_h
            scaled_w = int(render_w * scale)
            scaled_h = window_h
            x = (window_w - scaled_w) // 2
            self._scale_rect = pygame.Rect(x, 0, scaled_w, scaled_h)
            self._scale_factor = scale
        elif self._scale_fit == ScaleFit.INTEGER:
            scale = max(1, min(window_w // render_w, window_h // render_h))
            scaled_w = render_w * scale
            scaled_h = render_h * scale
            x = (window_w - scaled_w) // 2
            y = (window_h - scaled_h) // 2
            self._scale_rect = pygame.Rect(x, y, scaled_w, scaled_h)
            self._scale_factor = float(scale)

    def _handle_event(self, event: pygame.event.Event):
        """Internal method to handle window resize events."""
        if event.type == pygame.VIDEORESIZE:
            self._window_size = (event.w, event.h)
            self._recalculate_render_surface()

    def _present(self):
        """Internal method called by Game after all drawing is complete.

                Scales and presents the render surface to the window.
                In EXPAND mode nothing needs to be scaled, just flip.
                """
        if self._game_scale_mode == GameScaleMode.EXPAND:
            pygame.display.flip()
            return

        # in MIXED mode above target, also just flip
        if self._game_scale_mode == GameScaleMode.MIXED:
            window_w, window_h = self._window_size
            target_w, target_h = self._target_resolution
            if window_w > target_w or window_h > target_h:
                pygame.display.flip()
                return

        # SCALE mode or MIXED below target — scale fixed canvas to window
        self._window_surface.fill((0, 0, 0))
        render_size = self._render_surface.get_size()
        if self._scale_rect.size == render_size:
            self._window_surface.blit(self._render_surface, self._scale_rect)
        else:
            scaled = pygame.transform.scale(self._render_surface, self._scale_rect.size)
            self._window_surface.blit(scaled, self._scale_rect)

        pygame.display.flip()