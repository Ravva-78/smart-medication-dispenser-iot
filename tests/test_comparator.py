"""
Unit tests for inventory/comparator.py.
"""
import unittest
from datetime import datetime, timezone
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState
from inventory.comparator import InventoryComparator


class TestInventoryComparator(unittest.TestCase):
    """Test suite for InventoryComparator delta engine."""

    def setUp(self):
        """Create baseline state fixtures for state transition testing."""
        self.now = datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc)
        self.metadata = InventoryMetadata(
            inspection_id="insp_comp_01",
            image_name="comp_strip.jpg",
            capture_time=self.now,
            camera_id="cam_01",
        )

        # 1. Baseline Full Strip (15/15 present)
        self.full_state = InventoryState(
            strip_id="strip_001",
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

        # 2. 1 Tablet Removed (14/15 present, missing slot 11)
        self.one_removed_state = InventoryState(
            strip_id="strip_001",
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

        # 3. 2 Tablets Removed (13/15 present, missing slots 11, 14)
        self.two_removed_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=13,
            missing_count=2,
            occupancy_percentage=86.67,
            missing_slots=(11, 14),
            average_confidence=0.996,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )

        # 4. Replaced Strip (Different strip_id, 10 slots)
        self.replaced_state = InventoryState(
            strip_id="strip_002",
            inspection_time=self.now,
            total_slots=10,
            present_count=10,
            missing_count=0,
            occupancy_percentage=100.0,
            missing_slots=(),
            average_confidence=0.999,
            status=InventoryStatus.NORMAL,
            metadata=self.metadata,
        )

    def test_initial_creation_event(self):
        """Test that comparing None against a state emits CREATED event."""
        event = InventoryComparator.compare(None, self.full_state)
        self.assertEqual(event.event_type, EventType.CREATED)
        self.assertEqual(event.delta_present, 15)
        self.assertEqual(event.delta_missing, 0)
        self.assertIsNone(event.previous_state)
        self.assertEqual(event.current_state, self.full_state)

    def test_repeated_identical_frames_emits_no_change(self):
        """Test that identical successive states emit NO_CHANGE event."""
        event = InventoryComparator.compare(self.full_state, self.full_state)
        self.assertEqual(event.event_type, EventType.NO_CHANGE)
        self.assertEqual(event.delta_present, 0)
        self.assertEqual(event.delta_missing, 0)
        self.assertEqual(event.removed_slots, ())
        self.assertEqual(event.added_slots, ())

    def test_tablet_removed_event(self):
        """Test that tablet removal emits TABLET_REMOVED event with correct deltas and removed slots."""
        event = InventoryComparator.compare(self.full_state, self.one_removed_state)
        self.assertEqual(event.event_type, EventType.TABLET_REMOVED)
        self.assertEqual(event.delta_present, -1)
        self.assertEqual(event.delta_missing, 1)
        self.assertEqual(event.removed_slots, (11,))
        self.assertEqual(event.added_slots, ())

    def test_second_tablet_removed_event(self):
        """Test sequential removal of a second tablet."""
        event = InventoryComparator.compare(self.one_removed_state, self.two_removed_state)
        self.assertEqual(event.event_type, EventType.TABLET_REMOVED)
        self.assertEqual(event.delta_present, -1)
        self.assertEqual(event.delta_missing, 1)
        self.assertEqual(event.removed_slots, (14,))

    def test_tablet_added_event(self):
        """Test that replacing a tablet into a missing slot emits TABLET_ADDED event."""
        event = InventoryComparator.compare(self.two_removed_state, self.one_removed_state)
        self.assertEqual(event.event_type, EventType.TABLET_ADDED)
        self.assertEqual(event.delta_present, 1)
        self.assertEqual(event.delta_missing, -1)
        self.assertEqual(event.added_slots, (14,))
        self.assertEqual(event.removed_slots, ())

    def test_strip_replaced_event(self):
        """Test that changing strip_id or total_slots emits STRIP_REPLACED event."""
        event = InventoryComparator.compare(self.one_removed_state, self.replaced_state)
        self.assertEqual(event.event_type, EventType.STRIP_REPLACED)
        self.assertEqual(event.delta_present, -4)
        self.assertEqual(event.delta_missing, -1)

    def test_slot_moved_same_count_emits_updated(self):
        """Test that when present count is identical but missing slot indices shift, UPDATED is emitted."""
        shifted_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=14,
            missing_count=1,
            occupancy_percentage=93.33,
            missing_slots=(8,),  # Shifted from slot 11 to slot 8
            average_confidence=0.997,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )
        event = InventoryComparator.compare(self.one_removed_state, shifted_state)
        self.assertEqual(event.event_type, EventType.UPDATED)
        self.assertEqual(event.removed_slots, (8,))
        self.assertEqual(event.added_slots, (11,))
        self.assertTrue(event.is_material_change)

    def test_multi_tablet_removal(self):
        """Test multi-tablet removal transition (e.g. 15 -> 12 present)."""
        event = InventoryComparator.compare(self.full_state, self.two_removed_state)
        self.assertEqual(event.event_type, EventType.TABLET_REMOVED)
        self.assertEqual(event.delta_present, -2)
        self.assertEqual(event.delta_missing, 2)
        self.assertEqual(event.removed_slots, (11, 14))

    def test_slot_pattern_swap(self):
        """Test complex slot pattern swap (e.g. missing (3, 7) -> (5, 9))."""
        state_a = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=13,
            missing_count=2,
            occupancy_percentage=86.67,
            missing_slots=(3, 7),
            average_confidence=0.99,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )
        state_b = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=13,
            missing_count=2,
            occupancy_percentage=86.67,
            missing_slots=(5, 9),
            average_confidence=0.99,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )
        event = InventoryComparator.compare(state_a, state_b)
        self.assertEqual(event.event_type, EventType.UPDATED)
        self.assertEqual(event.removed_slots, (5, 9))
        self.assertEqual(event.added_slots, (3, 7))


if __name__ == "__main__":
    unittest.main()

