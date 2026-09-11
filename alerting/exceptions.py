"""
Alert Engine Subsystem Domain Exceptions.

Purpose:
    Defines exception classes for alert dispatch and formatting errors.
"""


class AlertEngineError(Exception):
    """Base exception class for all errors originating within the Alert Engine."""
    pass


class DispatchError(AlertEngineError):
    """Raised when an alert dispatcher fails to send a notification."""
    pass


__all__ = ["AlertEngineError", "DispatchError"]
