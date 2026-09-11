"""
Alert Engine Subsystem Enumerations.

Purpose:
    Defines string-inherited enumerations for alert notification channels and severity levels.

Responsibilities:
    - `AlertChannel`: (LOG, PUSH_NOTIFICATION, SMS, ALARM_BUZZER, CAREGIVER_ALERT).
    - `AlertSeverity`: (INFO, WARNING, CRITICAL).

Dependencies:
    - Standard library `enum.Enum`.
"""

from enum import Enum


class AlertChannel(str, Enum):
    """Notification dispatch channels."""
    LOG = "LOG"
    PUSH_NOTIFICATION = "PUSH_NOTIFICATION"
    SMS = "SMS"
    ALARM_BUZZER = "ALARM_BUZZER"
    CAREGIVER_ALERT = "CAREGIVER_ALERT"


class AlertSeverity(str, Enum):
    """Notification severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


__all__ = ["AlertChannel", "AlertSeverity"]
