"""
Unit tests for inventory/formatter.py.
"""
import json
import unittest
from datetime import datetime, timezone
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState
from inventory.events import InventoryEvent
from inventory.formatter import InventoryFormatter


class TestInventoryFormatter(unittest.TestCase):
    """Test suite for InventoryFormatter representation module."""

    def setUp(self):
        """Create sample state and event fixtures for formatting tests."""
        self.now = datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc)
        self.metadata = InventoryMetadata(
            inspection_id="insp_fmt_01",
            image_name="fmt_strip.jpg",
            capture_time=self.now,
            camera_id="cam_01",
        )
        self.state = InventoryState(
            strip_id="strip_20260729_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=12,
            missing_count=3,
            occupancy_percentage=80.0,
            missing_slots=(11, 14, 15),
            average_confidence=0.9975,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )
        self.event = InventoryEvent(
            event_id="evt_fmt_01",
            timestamp=self.now,
            strip_id="strip_20260729_001",
            event_type=EventType.TABLET_REMOVED,
            delta_present=-1,
            delta_missing=1,
            removed_slots=(11,),
            added_slots=(),
            previous_state=None,
            current_state=self.state,
        )

    def test_to_dict_formatting(self):
        """Test formatting InventoryState to dictionary."""
        d = InventoryFormatter.to_dict(self.state)
        self.assertEqual(d["strip_id"], "strip_20260729_001")
        self.assertEqual(d["status"], "TABLET_MISSING")
        self.assertEqual(d["missing_slots"], [11, 14, 15])

    def test_to_json_formatting(self):
        """Test formatting InventoryState to valid JSON string."""
        json_str = InventoryFormatter.to_json(self.state, indent=2)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["strip_id"], "strip_20260729_001")
        self.assertEqual(parsed["present_count"], 12)

    def test_to_concise_status(self):
        """Test formatting short status string."""
        concise = InventoryFormatter.to_concise_status(self.state)
        self.assertIn("strip_20260729_001", concise)
        self.assertIn("12/15", concise)
        self.assertIn("80.0%", concise)
        self.assertIn("TABLET_MISSING", concise)

    def test_to_terminal_summary(self):
        """Test human-readable multiline terminal summary formatting."""
        summary = InventoryFormatter.to_terminal_summary(self.state)
        self.assertIn("MEDICINE STRIP INVENTORY SUMMARY", summary)
        self.assertIn("strip_20260729_001", summary)
        self.assertIn("Present          : 12", summary)
        self.assertIn("Missing          : 3", summary)
        self.assertIn("Missing Slots    : [11, 14, 15]", summary)

    def test_format_event_terminal(self):
        """Test formatting InventoryEvent to terminal representation."""
        evt_str = InventoryFormatter.format_event_terminal(self.event)
        self.assertIn("INVENTORY EVENT LOG", evt_str)
        self.assertIn("TABLET_REMOVED", evt_str)
        self.assertIn("Removed Slots    : [11]", evt_str)



if __name__ == "__main__":
    unittest.main()
