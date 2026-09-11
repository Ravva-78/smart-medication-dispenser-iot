"""
In-Process EventBus Package.

This package provides an decoupled publish/subscribe mechanism for system-wide events.
"""

from events.bus import EventSubscriber, EventBus

__version__ = "0.1.0"

__all__ = ["EventSubscriber", "EventBus"]
