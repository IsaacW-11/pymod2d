from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymod.utils.time.timer import Timer
    from pymod.utils.time.stopwatch import Stopwatch

class TimeManager:
    """Manages all time-related functionality.

    Attributes:
        _time_scale: Multiplier applied to delta time. 0 = paused, 0.5 = slow motion
        _delta: Raw delta time in seconds since last frame.
        _elapsed: Total elapsed time since game started in seconds.
        _scene_time: Time elapsed since current scene was entered in seconds.
        _frame_count: Total number of frames elapsed since game started.
        _fps_history: List of recent fps values. Used for average fps calculation.
        _fps_history_size: Number of frames to average fps over.
        _timers: List to store active timers. Used to update automatically.
        _stopwatches: List to store active stopwatches. Used to update automatically.
    """

    def __init__(self, fps_history_size=60):
        self._time_scale: float = 1.0
        self._delta: float = 0.0
        self._elapsed: float = 0.0
        self._scene_time: float = 0.0
        self._frame_count: int = 0
        self._fps_history: list[float] = []
        self._fps_history_size: int = fps_history_size
        self._timers: list[Timer] = []
        self._stopwatches: list[Stopwatch] = []

    # PROPERTIES
    @property
    def time_scale(self) -> float:
        """Current timescale."""
        return self._time_scale

    @property
    def delta(self) -> float:
        """Current delta time in seconds.

        Use for all gameplay logic.
        """
        return self._delta * self._time_scale

    @property
    def unscaled_delta(self) -> float:
        """Raw delta time in seconds, unaffected by time_scale.

        Use for UI or animations that should run the same even when game is in slow motion or paused.
        """
        return self._delta

    @property
    def fixed_delta(self) -> float:
        """Delta time capped at a value of 1/20th of a second, scaled by time_scale.

        Use for game physics to ensure frame stutters don't affect physics calculations.
        """
        return min(self._delta, 0.05) * self._time_scale

    @property
    def elapsed(self) -> float:
        """Total time elapsed since game started in seconds."""
        return self._elapsed

    @property
    def scene_time(self) -> float:
        """Time elapsed since scene was entered in seconds."""
        return self._scene_time

    @property
    def frame_count(self) -> int:
        """Total number of frame since game started."""
        return self._frame_count

    @property
    def fps(self) -> float:
        """Current frames per second."""
        return 1.0 / self._delta if self._delta > 0 else 0.0

    @property
    def average_fps(self) -> float:
        """Average frames per second over the past N frames."""
        if not self._fps_history:
            return 0.0
        return sum(self._fps_history) / len(self._fps_history)

    # SETTERS
    @time_scale.setter
    def time_scale(self, value: float):
        self._time_scale = max(0.0, value)

    # TIMERS
    def add_timer(self, timer: Timer) -> Timer:
        """Register a timer to be updated automatically every frame.

        Args:
            timer: Timer to register.

        Returns:
            The timer that was registered, for convenience.
        """
        self._timers.append(timer)
        return timer

    def remove_timer(self, timer: Timer):
        """Unregister a timer.

        Args:
            timer: Timer to unregister.
        """
        if timer in self._timers:
            self._timers.remove(timer)

    # STOPWATCHES
    def add_stopwatch(self, stopwatch: Stopwatch) -> Stopwatch:
        """Register a stopwatch to be updated automatically every frame.

        Args:
            stopwatch: Stopwatch to register.

        Returns:
            The stopwatch that was registered, for convenience.
        """
        self._stopwatches.append(stopwatch)
        return stopwatch

    def remove_stopwatch(self, stopwatch: Stopwatch):
        """Unregister a stopwatch.

        Args:
            stopwatch: Stopwatch to unregister.
        """
        if stopwatch in self._stopwatches:
            self._stopwatches.remove(stopwatch)

    # INTERNAL
    def _update(self, dt: float):
        """Internal method called every frame by game.

        Args:
            dt: The raw delta time from pygame clock.
        """
        self._delta = dt
        self._elapsed += dt
        self._scene_time += dt
        self._frame_count += 1

        current_fps = 1.0 / dt if dt > 0 else 0.0
        self._fps_history.append(current_fps)
        if len(self._fps_history) > self._fps_history_size:
            self._fps_history.pop(0)

        for stopwatch in self._stopwatches:
            stopwatch._tick(self.unscaled_delta, self.delta)

        for timer in self._timers[:]:
            timer._tick(self.delta)
            if timer._completed and not timer.repeat:
                self._timers.remove(timer)

    def _reset_scene_time(self):
        """Called by scene manager when new scene is entered."""
        self._scene_time = 0.0