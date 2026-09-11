"""
In-Process EventBus Publisher/Subscriber Pattern Implementation.

Purpose:
    Provides an in-process pub/sub event bus enabling decoupled communication
    between event producers (Inventory, OCR, Clinical) and event consumers (Alerting, Hardware, Dashboard).

Responsibilities:
    - `EventSubscriber(ABC)` interface (`on_event(event_type: str, payload: object)`).
    - `EventBus`: Thread-safe pub/sub engine with `subscribe`, `unsubscribe`, and `publish`.

Dependencies:
    - Standard library `abc`, `logging`, `typing`, `collections`.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Set, Optional
from collections import defaultdict


logger = logging.getLogger(__name__)


class EventSubscriber(ABC):
    """Abstract interface for event subscribers."""

    @abstractmethod
    def on_event(self, event_type: str, payload: Any) -> None:
        """Callback invoked when a subscribed event is published."""
        pass


class EventBus:
    """In-process thread-safe event bus publisher/subscriber provider."""

    _instance: Optional["EventBus"] = None

    def __init__(self):
        self._subscribers: Dict[str, Set[EventSubscriber]] = defaultdict(set)

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Singleton accessor for shared global EventBus."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event_type: str, subscriber: EventSubscriber) -> None:
        """Register a subscriber to receive events of a specific event_type."""
        if not isinstance(subscriber, EventSubscriber):
            raise ValueError("Subscriber must implement EventSubscriber interface.")
        self._subscribers[event_type].add(subscriber)
        logger.debug("Subscribed %s to event channel '%s'", subscriber, event_type)

    def unsubscribe(self, event_type: str, subscriber: EventSubscriber) -> None:
        """Remove a registered subscriber from an event channel."""
        if event_type in self._subscribers and subscriber in self._subscribers[event_type]:
            self._subscribers[event_type].remove(subscriber)
            logger.debug("Unsubscribed %s from event channel '%s'", subscriber, event_type)

    def publish(self, event_type: str, payload: Any) -> None:
        """Publish an event payload to all registered subscribers of event_type."""
        subscribers = list(self._subscribers.get(event_type, set()))
        logger.info("Publishing event '%s' to %d subscriber(s)", event_type, len(subscribers))
        for sub in subscribers:
            try:
                sub.on_event(event_type, payload)
            except Exception as err:
                logger.error("Error in subscriber %s processing event '%s': %s", sub, event_type, err)

    def clear_subscribers(self) -> None:
        """Reset all subscriber channels (used in testing)."""
        self._subscribers.clear()


__all__ = ["EventSubscriber", "EventBus"]
