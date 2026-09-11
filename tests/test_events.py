"""
Unit tests for inventory/events.py.
"""
import unittest
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState
from inventory.events import InventoryEvent


class TestInventoryEvents(unittest.TestCase):
    """Test suite for InventoryEvent data model."""

    def setUp(self):
        """Create sample previous and current InventoryState fixtures."""
        self.now = datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc)
        self.metadata = InventoryMetadata(
            inspection_id="insp_evt_01",
            image_name="event_strip.jpg",
            capture_time=self.now,
            camera_id="cam_01",
        )
        self.prev_state = InventoryState(
            strip_id="strip_20260729_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=15,
            missing_count=0,
            occupancy_percentage=100.0,
            missing_slots=(),
            average_confidence=0.998,
            status=InventoryStatus.NORMAL,
            metadata=self.metadata,
        )
        self.curr_state = InventoryState(
            strip_id="strip_20260729_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=14,
            missing_count=1,
            occupancy_percentage=93.33,
            missing_slots=(11,),
            average_confidence=0.997,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )

        self.event = InventoryEvent(
            event_id="evt_1001",
            timestamp=self.now,
            strip_id="strip_20260729_001",
            event_type=EventType.TABLET_REMOVED,
            delta_present=-1,
            delta_missing=1,
            removed_slots=(11,),
            added_slots=(),
            previous_state=self.prev_state,
            current_state=self.curr_state,
        )

    def test_event_creation_and_immutability(self):
        """Test InventoryEvent creation and frozen immutability."""
        self.assertEqual(self.event.event_id, "evt_1001")
        self.assertEqual(self.event.event_type, EventType.TABLET_REMOVED)
        self.assertEqual(self.event.delta_present, -1)
        self.assertEqual(self.event.removed_slots, (11,))
        self.assertIsInstance(self.event.timestamp, datetime)

        with self.assertRaises(FrozenInstanceError):
            setattr(self.event, "delta_present", 0)

    def test_event_serialization_roundtrip(self):
        """Test to_dict() and from_dict() roundtrip serialization."""
        d = self.event.to_dict()
        self.assertEqual(d["event_id"], "evt_1001")
        self.assertEqual(d["event_type"], "TABLET_REMOVED")
        self.assertEqual(d["delta_present"], -1)
        self.assertEqual(d["removed_slots"], [11])

        reconstructed = InventoryEvent.from_dict(d)
        self.assertEqual(reconstructed, self.event)
        self.assertEqual(reconstructed.previous_state, self.prev_state)
        self.assertEqual(reconstructed.current_state, self.curr_state)

    def test_event_initial_creation_without_previous_state(self):
        """Test event creation when previous_state is None (initial strip creation)."""
        init_event = InventoryEvent(
            event_id="evt_0001",
            timestamp=self.now,
            strip_id="strip_20260729_001",
            event_type=EventType.CREATED,
            delta_present=15,
            delta_missing=0,
            removed_slots=(),
            added_slots=(),
            previous_state=None,
            current_state=self.prev_state,
        )
        d = init_event.to_dict()
        self.assertIsNone(d["previous_state"])

        reconstructed = InventoryEvent.from_dict(d)
        self.assertIsNone(reconstructed.previous_state)
        self.assertEqual(reconstructed.current_state, self.prev_state)


if __name__ == "__main__":
    unittest.main()
