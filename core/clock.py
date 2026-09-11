"""
Core System Clock Infrastructure.

Purpose:
    Provides an abstraction over system time generation to enable deterministic, time-frozen unit testing.

Responsibilities:
    - `AbstractClock(ABC)` interface (`now()`).
    - `SystemClock`: Returns real-time UTC timestamp (`datetime.now(timezone.utc)`).
    - `MockClock`: Returns a frozen or custom controllable timestamp.
    - `Clock`: Thread-safe static facade provider.

Dependencies:
    - Standard library `abc`, `datetime`, `timezone`.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional


class AbstractClock(ABC):
    """Abstract interface for clock providers."""

    @abstractmethod
    def now(self) -> datetime:
        """Return current datetime timestamp with UTC timezone."""
        pass


class SystemClock(AbstractClock):
    """Production clock returning system current UTC datetime."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class MockClock(AbstractClock):
    """Testing clock returning a fixed frozen timestamp."""

    def __init__(self, frozen_time: Optional[datetime] = None):
        self._frozen_time = frozen_time if frozen_time is not None else datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)

    def set_time(self, new_time: datetime) -> None:
        self._frozen_time = new_time

    def now(self) -> datetime:
        return self._frozen_time


class Clock:
    """Static clock provider facade."""

    _instance: AbstractClock = SystemClock()

    @classmethod
    def get_clock(cls) -> AbstractClock:
        return cls._instance

    @classmethod
    def set_clock(cls, clock_instance: AbstractClock) -> None:
        cls._instance = clock_instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = SystemClock()

    @classmethod
    def now(cls) -> datetime:
        return cls._instance.now()


__all__ = ["AbstractClock", "SystemClock", "MockClock", "Clock"]
