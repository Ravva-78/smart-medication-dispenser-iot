"""
Inventory Subsystem Chronological History & Event Tracker.

Purpose:
    Maintains an ordered, chronological log of InventorySnapshot and InventoryEvent entries for a medicine strip.

Responsibilities:
    - Append state transition events and historical snapshots.
    - Retrieve latest state, latest snapshot, or complete history.
    - Filter transition events by `EventType`.
    - Support dictionary/JSON serialization for persistence storage.

Dependencies:
    - Standard library `typing`, `uuid`.
    - `inventory.models.InventoryState`, `inventory.models.InventorySnapshot`.
    - `inventory.enums.EventType`.
    - `inventory.events.InventoryEvent`.
"""

import logging
from typing import List, Optional, Dict, Any
from inventory.enums import EventType
from inventory.models import InventoryState, InventorySnapshot
from inventory.events import InventoryEvent

logger = logging.getLogger(__name__)


class InventoryHistory:
    """Chronological event and snapshot history tracker for a medicine strip."""

    def __init__(self, strip_id: str):
        """
        Initialize InventoryHistory tracker.

        Args:
            strip_id: Medicine strip identifier.
        """
        self.strip_id = strip_id
        self._snapshots: List[InventorySnapshot] = []
        self._events: List[InventoryEvent] = []

    def record_event(self, event: InventoryEvent) -> InventorySnapshot:
        """
        Record a transition event and create an associated InventorySnapshot entry.

        Args:
            event: InventoryEvent instance to record.

        Returns:
            Newly recorded InventorySnapshot instance.
        """
        snapshot_id = f"snap_{len(self._snapshots) + 1:04d}"
        snapshot = InventorySnapshot(
            snapshot_id=snapshot_id,
            timestamp=event.timestamp,
            event_type=event.event_type,
            event_id=event.event_id,
            state=event.current_state,
        )

        self._events.append(event)
        self._snapshots.append(snapshot)
        logger.debug("Recorded event %s (%s) for strip %s", event.event_id, event.event_type.value, self.strip_id)
        return snapshot

    def get_latest_state(self) -> Optional[InventoryState]:
        """Return latest recorded InventoryState or None if empty."""
        return self._snapshots[-1].state if self._snapshots else None

    def get_latest_event(self) -> Optional[InventoryEvent]:
        """Return latest recorded InventoryEvent or None if empty."""
        return self._events[-1] if self._events else None

    def get_latest_snapshot(self) -> Optional[InventorySnapshot]:
        """Return latest recorded InventorySnapshot or None if empty."""
        return self._snapshots[-1] if self._snapshots else None

    def get_snapshots(self) -> List[InventorySnapshot]:
        """Return copy of all recorded InventorySnapshot entries."""
        return list(self._snapshots)

    def get_events(self) -> List[InventoryEvent]:
        """Return copy of all recorded InventoryEvent entries."""
        return list(self._events)

    def get_events_by_type(self, event_type: EventType) -> List[InventoryEvent]:
        """Filter recorded events by EventType."""
        return [e for e in self._events if e.event_type == event_type]

    def clear(self) -> None:
        """Clear all historical entries."""
        self._snapshots.clear()
        self._events.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete history log to dictionary."""
        return {
            "strip_id": self.strip_id,
            "snapshots": [s.to_dict() for s in self._snapshots],
            "events": [e.to_dict() for e in self._events],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryHistory":
        """Deserialize dictionary payload into InventoryHistory instance."""
        history = cls(strip_id=data["strip_id"])
        if "events" in data and data["events"]:
            for event_dict in data["events"]:
                event = InventoryEvent.from_dict(event_dict)
                history.record_event(event)
        elif "snapshots" in data and data["snapshots"]:
            for snap_dict in data["snapshots"]:
                snap = InventorySnapshot.from_dict(snap_dict)
                history._snapshots.append(snap)
        return history


__all__ = ["InventoryHistory"]
