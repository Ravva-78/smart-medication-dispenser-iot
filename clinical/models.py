"""
Clinical Decision Engine Domain Models & Data Contracts.

Purpose:
    Defines immutable domain dataclasses for Prescription, DoseSchedule, and ComplianceDecision.

Responsibilities:
    - `Prescription`: Patient prescription requirements (drug name, strength, dosage form, instructions).
    - `DoseSchedule`: Scheduled administration time window and grace period.
    - `ComplianceDecision`: Immutable audit record of final dose compliance outcome.

Dependencies:
    - Standard library `dataclasses`, `datetime`, `typing`.
    - `inventory.utils.parse_datetime`, `inventory.utils.format_datetime`.
    - `clinical.enums.DecisionOutcome`.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from inventory.utils import parse_datetime, format_datetime
from clinical.enums import DecisionOutcome


@dataclass(frozen=True)
class Prescription:
    """Immutable domain model representing a patient prescription."""
    prescription_id: str
    patient_id: str
    medicine_name: str
    strength: str
    dosage_form: str = "Tablet"
    doses_per_day: int = 1
    instructions: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize Prescription to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Prescription":
        """Deserialize dictionary payload into a Prescription instance."""
        return cls(**data)


@dataclass(frozen=True)
class DoseSchedule:
    """Immutable domain model representing a scheduled dose time window."""
    schedule_id: str
    prescription_id: str
    scheduled_time: datetime
    grace_period_minutes: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Serialize DoseSchedule to dictionary representation."""
        return {
            "schedule_id": self.schedule_id,
            "prescription_id": self.prescription_id,
            "scheduled_time": format_datetime(self.scheduled_time),
            "grace_period_minutes": self.grace_period_minutes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DoseSchedule":
        """Deserialize dictionary payload into a DoseSchedule instance."""
        return cls(
            schedule_id=data["schedule_id"],
            prescription_id=data["prescription_id"],
            scheduled_time=parse_datetime(data["scheduled_time"]),
            grace_period_minutes=int(data.get("grace_period_minutes", 30)),
        )


@dataclass(frozen=True)
class ComplianceDecision:
    """Immutable audit record representing the final clinical compliance decision."""
    decision_id: str
    timestamp: datetime
    patient_id: str
    strip_id: str
    prescription_id: Optional[str]
    outcome: DecisionOutcome
    reason: str
    actionable: bool
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ComplianceDecision to dictionary representation."""
        return {
            "decision_id": self.decision_id,
            "timestamp": format_datetime(self.timestamp),
            "patient_id": self.patient_id,
            "strip_id": self.strip_id,
            "prescription_id": self.prescription_id,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "actionable": self.actionable,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceDecision":
        """Deserialize dictionary payload into a ComplianceDecision instance."""
        return cls(
            decision_id=data["decision_id"],
            timestamp=parse_datetime(data["timestamp"]),
            patient_id=data["patient_id"],
            strip_id=data["strip_id"],
            prescription_id=data.get("prescription_id"),
            outcome=DecisionOutcome(data["outcome"]),
            reason=data["reason"],
            actionable=bool(data["actionable"]),
            schema_version=data.get("schema_version", "1.0"),
        )


__all__ = ["Prescription", "DoseSchedule", "ComplianceDecision"]
