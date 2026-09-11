"""
Unit tests for inventory/history.py.
"""
import unittest
from datetime import datetime, timezone
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState, InventorySnapshot
from inventory.events import InventoryEvent
from inventory.history import InventoryHistory


class TestInventoryHistory(unittest.TestCase):
    """Test suite for InventoryHistory chronological log tracking."""

    def setUp(self):
        """Create baseline history fixtures."""
        self.history = InventoryHistory(strip_id="strip_20260729_001")
        self.now = datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc)
        self.metadata = InventoryMetadata(
            inspection_id="insp_hist_01",
            image_name="hist_strip.jpg",
            capture_time=self.now,
            camera_id="cam_01",
        )
        self.state1 = InventoryState(
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
        self.state2 = InventoryState(
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

        self.event1 = InventoryEvent(
            event_id="evt_01",
            timestamp=self.now,
            strip_id="strip_20260729_001",
            event_type=EventType.CREATED,
            delta_present=15,
            delta_missing=0,
            removed_slots=(),
            added_slots=(),
            previous_state=None,
            current_state=self.state1,
        )

        self.event2 = InventoryEvent(
            event_id="evt_02",
            timestamp=self.now,
            strip_id="strip_20260729_001",
            event_type=EventType.TABLET_REMOVED,
            delta_present=-1,
            delta_missing=1,
            removed_slots=(11,),
            added_slots=(),
            previous_state=self.state1,
            current_state=self.state2,
        )

    def test_empty_history(self):
        """Test behavior of newly created empty history."""
        self.assertIsNone(self.history.get_latest_state())
        self.assertIsNone(self.history.get_latest_event())
        self.assertEqual(len(self.history.get_snapshots()), 0)
        self.assertEqual(len(self.history.get_events()), 0)

    def test_record_event_and_snapshots(self):
        """Test recording events and snapshot ordering."""
        self.history.record_event(self.event1)
        self.assertEqual(self.history.get_latest_state(), self.state1)
        self.assertEqual(self.history.get_latest_event(), self.event1)

        self.history.record_event(self.event2)
        self.assertEqual(self.history.get_latest_state(), self.state2)
        self.assertEqual(self.history.get_latest_event(), self.event2)

        snapshots = self.history.get_snapshots()
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[0].event_type, EventType.CREATED)
        self.assertEqual(snapshots[1].event_type, EventType.TABLET_REMOVED)

    def test_get_events_by_type(self):
        """Test filtering history events by EventType."""
        self.history.record_event(self.event1)
        self.history.record_event(self.event2)

        removed_events = self.history.get_events_by_type(EventType.TABLET_REMOVED)
        self.assertEqual(len(removed_events), 1)
        self.assertEqual(removed_events[0].event_id, "evt_02")

    def test_history_serialization_roundtrip(self):
        """Test history to_dict() and from_dict() roundtrip."""
        self.history.record_event(self.event1)
        self.history.record_event(self.event2)

        d = self.history.to_dict()
        self.assertEqual(d["strip_id"], "strip_20260729_001")
        self.assertEqual(len(d["events"]), 2)

        reconstructed = InventoryHistory.from_dict(d)
        self.assertEqual(reconstructed.strip_id, "strip_20260729_001")
        self.assertEqual(len(reconstructed.get_events()), 2)
        self.assertEqual(reconstructed.get_latest_state(), self.state2)


if __name__ == "__main__":
    unittest.main()
