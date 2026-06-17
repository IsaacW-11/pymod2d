from __future__ import annotations
from typing import Any, Callable, TypeVar

T = TypeVar("T")

class Event:
    """Optional base class for events.

    Inherit from this to get cancellation support.
    Events do not have to inherit from this. Any object can be an event.
    """
    def __init__(self):
        self._cancelled: bool = False

    def cancel(self) -> None:
        """Cancel this event.

        Remaining listeners will not be called after cancellation.
        Only works if the event inherits from Event.
        """
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        """Whether this event has been cancelled."""
        return self._cancelled

class EventManager:
    """Global pub/sub event bus.

    Events are typed. You subscribe and emit using the event class itself.
    Any class can be used as an event, but inheriting from Event base class adds cancellation support.

    Attributes:
        _listeners: Maps event types to lists of tuples. This tuple contains (priority, callback, one_shot)
        _queue: Events queued for end-of-frame emission.
    """

    def __init__(self):
        self._listeners: dict[type, list[tuple[int, Callable, bool]]] = {}
        self._queue: list[Any] = []

    # SUBSCRIBE / UNSUBSCRIBE
    def subscribe(self, event_type: type, callback: Callable, priority: int = 0):
        """Subscribe to an event type.

        The callback is called every time this event is emitted.
        Lower priority number = runs first.

        Args:
            event_type: The event class to listen for.
            callback: Function to call when the event is emitted.
                      Must accept one argument — the event instance.
            priority: Execution order. Lower runs first. Defaults to 0.
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []

        self._listeners[event_type].append((priority, callback, False))
        self._listeners[event_type].sort(key=lambda x: x[0])

    def subscribe_once(self, event_type: type, callback: Callable, priority: int = 0):
        """Subscribe to an event type for one emission only.

        Automatically unsubscribes after the first time the event fires.

        Args:
            event_type: The event class to listen for.
            callback: Function to call when the event is emitted.
            priority: Execution order. Lower runs first. Defaults to 0.
        """
        if event_type not in self._listeners:
            self._listeners[event_type] = []

        self._listeners[event_type].append((priority, callback, True))
        self._listeners[event_type].sort(key=lambda x: x[0])

    def unsubscribe(self, event_type: type, callback: Callable):
        """Unsubscribe a callback from an event type.

        Always call this in on_destroy to avoid callbacks firing on destroyed objects.

        Args:
            event_type: The event class to stop listening for.
            callback: The callback to remove.
        """
        if event_type not in self._listeners:
            return
        self._listeners[event_type] = [
            (p, cb, once)
            for p, cb, once in self._listeners[event_type]
            if cb != callback
        ]

    def unsubscribe_all(self, callback: Callable):
        """Unsubscribe a callback from all event types.

        Useful in on_destroy to clean up all subscriptions at once without knowing which events were subscribed to.

        Args:
            callback: The callback to remove from all events.
        """
        for event_type in self._listeners:
            self._listeners[event_type] = [
                (p, cb, once)
                for p, cb, once in self._listeners[event_type]
                if cb != callback
            ]

    # EMIT
    def emit(self, event: Any):
        """Emit an event immediately.

        All subscribed listeners are called right now in priority order.
        If the event inherits from Event and is cancelled by a listener, remaining listeners are skipped.

        Args:
            event: The event instance to emit.
        """
        event_type = type(event)
        if event_type not in self._listeners:
            return

        to_remove = []
        for priority, callback, one_shot in self._listeners[event_type]:
            # check if cancelled
            if isinstance(event, Event) and event.cancelled:
                break

            callback(event)

            if one_shot:
                to_remove.append(callback)

        # remove one_shot listeners
        for callback in to_remove:
            self.unsubscribe(event_type, callback)

    def queue(self, event: Any):
        """Queue an event to be emitted at end of frame.

        Use this when you want to emit an event but don't want it to fire in the middle of the current update cycle.
        For example, queueing a scene change event from within an update call.

        Args:
            event: The event instance to queue.
        """
        self._queue.append(event)

    # UTILITY
    def has_listeners(self, event_type: type) -> bool:
        """Check if any listeners are subscribed to an event type.

        Args:
            event_type: The event class to check.

        Returns:
            True if there are any listeners.
        """
        return bool(self._listeners.get(event_type))

    def listener_count(self, event_type: type) -> int:
        """Get the number of listeners for an event type.

        Args:
            event_type: The event class to check.

        Returns:
            Number of subscribed listeners.
        """
        return len(self._listeners.get(event_type, []))

    def clear(self, event_type: type):
        """Clear all listeners for an event type, or all listeners entirely.

        Args:
            event_type: Event type to clear. If None, clears everything.
        """
        if event_type:
            self._listeners.pop(event_type, None)
        else:
            self._listeners.clear()

    # INTERNAL
    def _flush_queue(self):
        """Emit all queued events. Called by Game each frame."""
        events = self._queue[:]
        self._queue.clear()
        for event in events:
            self.emit(event)