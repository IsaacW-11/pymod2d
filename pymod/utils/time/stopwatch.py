from __future__ import annotations

class Stopwatch:
    """A stopwatch that measures elapsed time.

    Args:
        scaled: Whether the stopwatch should respond to time_scale. Defaults to True.
    """

    def __init__(self, scaled: bool=True):
        self.scaled = scaled

        self._elapsed: float = 0.0
        self._running: bool = False

    # PROPERTIES
    @property
    def elapsed(self) -> float:
        """Total time elapsed in seconds."""
        return self._elapsed

    @property
    def running(self) -> bool:
        """Whether the stopwatch is currently running."""
        return self._running

    # STOPWATCH METHODS
    def start(self) -> Stopwatch:
        """Starts the stopwatch.

        Returns:
            The stopwatch. Used for chaining if needed.
        """
        self._running = True
        return self

    def stop(self) -> Stopwatch:
        """Stops the stopwatch without resetting.

        Returns:
            The stopwatch. Used for chaining if needed.
        """
        self._running = False
        return self

    def reset(self) -> Stopwatch:
        """Resets the stopwatch to zero.

        Returns:
            The stopwatch. Used for chaining if needed.
        """
        self._elapsed = 0.0
        self_running = False
        return self

    def restart(self) -> Stopwatch:
        """Resets and immediately restarts the stopwatch.

        Returns:
            The stopwatch. Used for chaining if needed.
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
            self._elapsed += unscaled_delta
        else:
            self._elapsed += delta

    def __repr__(self) -> str:
        return f"Stopwatch(elapsed={self._elapsed:.3f}s, running={self._running}, scaled={self.scaled})"