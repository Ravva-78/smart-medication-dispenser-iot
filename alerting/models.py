"""
Alert Engine Subsystem Domain Models & Data Contracts.

Purpose:
    Defines immutable domain dataclasses for AlertMessage payloads.

Responsibilities:
    - `AlertMessage`: Immutable payload representing a dispatched notification alert.

Dependencies:
    - Standard library `dataclasses`, `datetime`, `typing`.
    - `inventory.utils.parse_datetime`, `inventory.utils.format_datetime`.
    - `alerting.enums.AlertChannel`, `alerting.enums.AlertSeverity`.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from inventory.utils import parse_datetime, format_datetime
from alerting.enums import AlertChannel, AlertSeverity


@dataclass(frozen=True)
class AlertMessage:
    """Immutable domain payload representing a dispatched notification alert."""
    alert_id: str
    timestamp: datetime
    patient_id: str
    decision_id: str
    severity: AlertSeverity
    channel: AlertChannel
    title: str
    message: str
    recipient: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize AlertMessage to dictionary representation."""
        return {
            "alert_id": self.alert_id,
            "timestamp": format_datetime(self.timestamp),
            "patient_id": self.patient_id,
            "decision_id": self.decision_id,
            "severity": self.severity.value,
            "channel": self.channel.value,
            "title": self.title,
            "message": self.message,
            "recipient": self.recipient,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertMessage":
        """Deserialize dictionary payload into an AlertMessage instance."""
        return cls(
            alert_id=data["alert_id"],
            timestamp=parse_datetime(data["timestamp"]),
            patient_id=data["patient_id"],
            decision_id=data["decision_id"],
            severity=AlertSeverity(data["severity"]),
            channel=AlertChannel(data["channel"]),
            title=data["title"],
            message=data["message"],
            recipient=data.get("recipient"),
        )


__all__ = ["AlertMessage"]
