from __future__ import annotations
from collections.abc import Callable
from typing import TYPE_CHECKING

class Timer:
    """A countdown timer that fires a callback on completion.

    Timers are automatically updated using the TimeManager when registered via ``pymod.time.add_timer()``.
    They do not need manual update calls.

    Args:
        duration: The duration of the timer in seconds.
        on_complete: An optional callback that will be called when the timer completes.
        repeat: Whether the timer should repeat after completion. Defaults to False.
        scaled: Whether the timer should respond to time_scale. Defaults to True.
    """

    def __init__(self, duration: float, on_complete: Callable, repeat: bool=False, scaled: bool=True):
        self.duration: float = duration
        self.on_complete: Callable = on_complete
        self.repeat: bool = repeat
        self.scaled: bool = scaled

        self._elapsed: float = 0.0
        self._running: bool = False
        self._completed: bool = False

    # PROPERTIES
    @property
    def elapsed(self) -> float:
        """Time elapsed since timer started in seconds."""
        return self._elapsed

    @property
    def remaining(self) -> float:
        """Time remaining until timer completes in seconds."""
        return max(0.0, self.duration - self._elapsed)

    @property
    def progress(self) -> float:
        """Normalised progress from 0.0 to 1.0"""
        return min(1.0, self._elapsed / self.duration) if self.duration > 0 else 1.0

    @property
    def completed(self) -> bool:
        """Whether the timer has completed."""
        return self._completed

    @property
    def running(self) -> bool:
        """Whether the timer is currently running."""
        return self._running

    # TIMER METHODS
    def start(self) -> Timer:
        """Start the timer.

        Returns:
            The timer. Used for chaining if needed.
        """
        self._running = True
        self._completed = False
        return self

    def stop(self) -> Timer:
        """Stops the timer without resetting.

        Returns:
             The timer. Used for chaining if needed.
        """
        self._running = False
        return self

    def reset(self) -> Timer:
        """Resets the timer to zero.

        Returns:
            The timer. Used for chaining if needed.
        """
        self._elapsed = 0.0
        self._running = False
        self._completed = False
        return self

    def restart(self) -> Timer:
        """Resets the timer and immediately starts the timer again.

        Returns:
            The timer. Used for chaining if needed.
        """
        self.reset()
        self.start()
        return self

    # INTERNAL METHODS
    def _tick(self, unscaled_delta: float, delta: float):
        """Internal method called by TimeManager every frame.

        Args:
            unscaled_delta: Unscaled delta time from TimeManager.
            delta: Scaled delta time from TimeManager.
        """
        if not self._running:
            return

        if not self.scaled:
            self._elapsed = unscaled_delta
        else:
            self._elapsed += delta

        if self._elapsed >= self.duration:
            self._completed = True
            self._running = False

            if self.on_complete:
                self.on_complete()

            if self.repeat:
                self._elapsed = 0.0
                self._running = True
                self._completed = False

    def __repr__(self) -> str:
        return f"Timer(duration={self.duration}s, remaining={self.remaining:.3f}s, running={self.running}, scaled={self.scaled})"