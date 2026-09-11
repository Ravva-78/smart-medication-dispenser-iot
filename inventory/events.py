"""
Inventory Subsystem Event Data Model.

Purpose:
    Defines the immutable audit record representing a discrete inventory transition event.

Responsibilities:
    - Capture state transition events (`TABLET_REMOVED`, `STRIP_REPLACED`, `NO_CHANGE`, etc.).
    - Maintain full audit trail including previous state, current state, deltas, and slot lists.
    - Support bidirectional JSON/dict serialization.

Dependencies:
    - Standard library `dataclasses`, `datetime`, `typing`.
    - `inventory.models.InventoryState`, `inventory.models._parse_datetime`, `inventory.models._format_datetime`.
    - `inventory.enums.EventType`.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from inventory.enums import EventType
from inventory.models import InventoryState
from inventory.utils import parse_datetime, format_datetime


@dataclass(frozen=True)
class InventoryEvent:
    """Immutable audit record representing a state transition event."""
    event_id: str
    timestamp: datetime
    strip_id: str
    event_type: EventType
    delta_present: int
    delta_missing: int
    removed_slots: Tuple[int, ...]
    added_slots: Tuple[int, ...]
    previous_state: Optional[InventoryState]
    current_state: InventoryState
    schema_version: str = "1.0"

    @property
    def is_material_change(self) -> bool:
        """Return True if this event represents a physical change in strip state."""
        return self.event_type in (
            EventType.TABLET_REMOVED,
            EventType.TABLET_ADDED,
            EventType.STRIP_REPLACED,
            EventType.UPDATED,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize InventoryEvent to a dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": format_datetime(self.timestamp),
            "strip_id": self.strip_id,
            "event_type": self.event_type.value,
            "delta_present": self.delta_present,
            "delta_missing": self.delta_missing,
            "removed_slots": list(self.removed_slots),
            "added_slots": list(self.added_slots),
            "is_material_change": self.is_material_change,
            "schema_version": self.schema_version,
            "previous_state": self.previous_state.to_dict() if self.previous_state is not None else None,
            "current_state": self.current_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryEvent":
        """Deserialize dictionary payload into an InventoryEvent instance."""
        prev_data = data.get("previous_state")
        prev_state = InventoryState.from_dict(prev_data) if prev_data is not None else None
        curr_state = InventoryState.from_dict(data["current_state"])

        return cls(
            event_id=data["event_id"],
            timestamp=parse_datetime(data["timestamp"]),
            strip_id=data["strip_id"],
            event_type=EventType(data["event_type"]),
            delta_present=int(data["delta_present"]),
            delta_missing=int(data["delta_missing"]),
            removed_slots=tuple(int(x) for x in data["removed_slots"]),
            added_slots=tuple(int(x) for x in data["added_slots"]),
            previous_state=prev_state,
            current_state=curr_state,
            schema_version=data.get("schema_version", "1.0"),
        )




__all__ = ["InventoryEvent"]
