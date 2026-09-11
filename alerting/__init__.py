"""
Alert Engine Subsystem Package.

This package maps ComplianceDecision events to notification channels (SMS, Push, Buzzer, Logs)
without evaluating medical rules.
"""

from alerting.enums import AlertChannel, AlertSeverity
from alerting.exceptions import AlertEngineError, DispatchError
from alerting.models import AlertMessage
from alerting.dispatchers import AbstractAlertDispatcher, MockAlertDispatcher, TerminalAlertDispatcher
from alerting.manager import AlertManager

__version__ = "0.1.0"

__all__ = [
    "AlertChannel",
    "AlertSeverity",
    "AlertEngineError",
    "DispatchError",
    "AlertMessage",
    "AbstractAlertDispatcher",
    "MockAlertDispatcher",
    "TerminalAlertDispatcher",
    "AlertManager",
]
