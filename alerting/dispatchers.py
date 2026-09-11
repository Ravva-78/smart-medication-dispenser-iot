"""
Alert Engine Subsystem Dispatcher Interfaces & Implementations.

Purpose:
    Provides an abstract interface (`AbstractAlertDispatcher`) and concrete implementations
    (Mock, Terminal) for sending alert notifications across channels.

Responsibilities:
    - `AbstractAlertDispatcher(ABC)` contract (`dispatch(message: AlertMessage)`).
    - `MockAlertDispatcher`: Stores dispatched messages in memory for unit testing.
    - `TerminalAlertDispatcher`: Prints formatted alert banners to standard log output.

Dependencies:
    - Standard library `abc`, `logging`, `typing`.
    - `alerting.models.AlertMessage`.
"""

import logging
from abc import ABC, abstractmethod
from typing import List
from alerting.models import AlertMessage

logger = logging.getLogger(__name__)


class AbstractAlertDispatcher(ABC):
    """Abstract interface for pluggable notification dispatchers."""

    @abstractmethod
    def dispatch(self, message: AlertMessage) -> bool:
        """
        Dispatch an alert notification message.

        Args:
            message: AlertMessage instance.

        Returns:
            True if dispatch succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def get_dispatcher_name(self) -> str:
        """Return human-readable identifier name for dispatcher."""
        pass


class MockAlertDispatcher(AbstractAlertDispatcher):
    """Deterministic mock dispatcher for unit testing."""

    def __init__(self):
        self._sent_messages: List[AlertMessage] = []

    def get_dispatcher_name(self) -> str:
        return "MockAlertDispatcher"

    def dispatch(self, message: AlertMessage) -> bool:
        self._sent_messages.append(message)
        logger.debug("MockAlertDispatcher dispatched alert %s (%s)", message.alert_id, message.severity.value)
        return True

    def get_dispatched_messages(self) -> List[AlertMessage]:
        return list(self._sent_messages)

    def clear(self) -> None:
        self._sent_messages.clear()


class TerminalAlertDispatcher(AbstractAlertDispatcher):
    """Console alert dispatcher printing formatted terminal banners."""

    def get_dispatcher_name(self) -> str:
        return "TerminalAlertDispatcher"

    def dispatch(self, message: AlertMessage) -> bool:
        banner = f"\n[ALERT - {message.severity.value}] {message.title}\n{message.message} (Patient: {message.patient_id})\n"
        logger.warning(banner)
        return True


__all__ = ["AbstractAlertDispatcher", "MockAlertDispatcher", "TerminalAlertDispatcher"]
