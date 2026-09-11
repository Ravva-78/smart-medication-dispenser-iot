"""
Inventory Subsystem State Transition Comparator Engine.

Purpose:
    Compares two InventoryState objects (previous vs current) to compute exact deltas,
    slot differences, and classify discrete state transition events.

Responsibilities:
    - Compare complete InventoryState objects (including `missing_slots` tuple).
    - Detect `CREATED`, `NO_CHANGE`, `TABLET_REMOVED`, `TABLET_ADDED`, `STRIP_REPLACED`, `UPDATED`.
    - Compute `delta_present`, `delta_missing`, `removed_slots`, and `added_slots`.
    - Construct an immutable `InventoryEvent` audit record.

Dependencies:
    - Standard library `uuid`, `datetime`.
    - `inventory.models.InventoryState`
    - `inventory.enums.EventType`
    - `inventory.events.InventoryEvent`
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from inventory.enums import EventType
from inventory.models import InventoryState
from inventory.events import InventoryEvent

logger = logging.getLogger(__name__)


class InventoryComparator:
    """Comparator engine for computing state transitions and emitting InventoryEvent objects."""

    @staticmethod
    def compare(
        prev_state: Optional[InventoryState],
        curr_state: InventoryState,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ) -> InventoryEvent:
        """
        Compare previous and current InventoryState to compute transition event.

        Args:
            prev_state: Previous InventoryState or None if initial creation.
            curr_state: Current valid InventoryState.
            event_id: Optional custom event identifier.
            timestamp: Optional custom event timestamp.

        Returns:
            Immutable InventoryEvent describing the transition.
        """
        if event_id is None:
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
        if timestamp is None:
            timestamp = curr_state.inspection_time

        # Case 1: Initial Strip Creation
        if prev_state is None:
            logger.info("Initial inventory created for strip: %s", curr_state.strip_id)
            return InventoryEvent(
                event_id=event_id,
                timestamp=timestamp,
                strip_id=curr_state.strip_id,
                event_type=EventType.CREATED,
                delta_present=curr_state.present_count,
                delta_missing=curr_state.missing_count,
                removed_slots=curr_state.missing_slots,
                added_slots=(),
                previous_state=None,
                current_state=curr_state,
            )

        # Case 2: Strip Replaced (different strip_id or total_slots)
        if prev_state.strip_id != curr_state.strip_id or prev_state.total_slots != curr_state.total_slots:
            logger.info(
                "Strip replaced: prev_id=%s (slots=%d) -> curr_id=%s (slots=%d)",
                prev_state.strip_id, prev_state.total_slots, curr_state.strip_id, curr_state.total_slots
            )
            return InventoryEvent(
                event_id=event_id,
                timestamp=timestamp,
                strip_id=curr_state.strip_id,
                event_type=EventType.STRIP_REPLACED,
                delta_present=curr_state.present_count - prev_state.present_count,
                delta_missing=curr_state.missing_count - prev_state.missing_count,
                removed_slots=curr_state.missing_slots,
                added_slots=(),
                previous_state=prev_state,
                current_state=curr_state,
            )

        # Case 3: Exact Same State (Repeated identical frame)
        if (
            prev_state.present_count == curr_state.present_count
            and prev_state.missing_count == curr_state.missing_count
            and prev_state.missing_slots == curr_state.missing_slots
        ):
            logger.debug("No inventory change detected for strip: %s", curr_state.strip_id)
            return InventoryEvent(
                event_id=event_id,
                timestamp=timestamp,
                strip_id=curr_state.strip_id,
                event_type=EventType.NO_CHANGE,
                delta_present=0,
                delta_missing=0,
                removed_slots=(),
                added_slots=(),
                previous_state=prev_state,
                current_state=curr_state,
            )

        # Calculate slot deltas
        prev_missing_set = set(prev_state.missing_slots)
        curr_missing_set = set(curr_state.missing_slots)

        # Removed slots: newly missing in current state
        newly_removed = tuple(sorted(curr_missing_set - prev_missing_set))
        # Added slots: were missing in prev state, now present in current state
        newly_added = tuple(sorted(prev_missing_set - curr_missing_set))

        delta_present = curr_state.present_count - prev_state.present_count
        delta_missing = curr_state.missing_count - prev_state.missing_count

        # Case 4: Tablet Removed
        if curr_state.present_count < prev_state.present_count:
            event_type = EventType.TABLET_REMOVED
            logger.info("Tablet(s) removed from strip %s: slots %s", curr_state.strip_id, newly_removed)

        # Case 5: Tablet Added / Replaced
        elif curr_state.present_count > prev_state.present_count:
            event_type = EventType.TABLET_ADDED
            logger.info("Tablet(s) added to strip %s: slots %s", curr_state.strip_id, newly_added)

        # Case 6: Shifted / Updated
        else:
            event_type = EventType.UPDATED
            logger.info("Slot configuration updated for strip %s", curr_state.strip_id)

        return InventoryEvent(
            event_id=event_id,
            timestamp=timestamp,
            strip_id=curr_state.strip_id,
            event_type=event_type,
            delta_present=delta_present,
            delta_missing=delta_missing,
            removed_slots=newly_removed,
            added_slots=newly_added,
            previous_state=prev_state,
            current_state=curr_state,
        )


__all__ = ["InventoryComparator"]
