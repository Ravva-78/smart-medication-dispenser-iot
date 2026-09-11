"""
Core Shared Infrastructure Package.

This package provides foundational shared services across all system bounded contexts:
deterministic clock abstractions, standardized ID generators, observability trace contexts,
centralized logging factories, and global application configuration.
"""

from core.clock import AbstractClock, SystemClock, MockClock, Clock
from core.ids import IDGenerator
from core.tracing import TraceContext
from core.config import AppConfig
from core.logging import configure_logging, get_logger

__version__ = "0.1.0"

__all__ = [
    "AbstractClock",
    "SystemClock",
    "MockClock",
    "Clock",
    "IDGenerator",
    "TraceContext",
    "AppConfig",
    "configure_logging",
    "get_logger",
]
