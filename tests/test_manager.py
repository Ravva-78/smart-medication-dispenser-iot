"""
Unit tests for inventory/manager.py.
"""
import unittest
import shutil
from pathlib import Path
from pipeline.inspection_result import InspectionResult, PocketResult
from inventory.enums import InventoryStatus, EventType
from inventory.exceptions import ValidationError, ItemNotFoundError
from inventory.persistence import JSONPersistenceManager
from inventory.manager import InventoryManager


class TestInventoryManager(unittest.TestCase):
    """Test suite for InventoryManager orchestrator facade."""

    def setUp(self):
        """Create temporary storage directory and InspectionResult fixtures."""
        self.test_dir = Path(__file__).parent / "temp_manager_storage"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.persistence = JSONPersistenceManager(storage_dir=self.test_dir)
        self.manager = InventoryManager(persistence=self.persistence)

        # Baseline InspectionResult (15 total, 12 present, 3 missing)
        self.inspection_missing = InspectionResult(
            total=15,
            present=12,
            missing=3,
            avg_confidence=0.9975,
            pockets=[
                PocketResult(index=i, class_name="present" if i not in (11, 14, 15) else "missing", confidence=0.998, bbox=(0,0,10,10))
                for i in range(1, 16)
            ]
        )

        # Full InspectionResult (15 total, 15 present)
        self.inspection_full = InspectionResult(
            total=15,
            present=15,
            missing=0,
            avg_confidence=0.998,
            pockets=[
                PocketResult(index=i, class_name="present", confidence=0.999, bbox=(0,0,10,10))
                for i in range(1, 16)
            ]
        )

        # Low Confidence InspectionResult
        self.inspection_low_conf = InspectionResult(
            total=10,
            present=10,
            missing=0,
            avg_confidence=0.450,  # < 0.60 threshold
            pockets=[
                PocketResult(index=i, class_name="present", confidence=0.45, bbox=(0,0,10,10))
                for i in range(1, 11)
            ]
        )

    def tearDown(self):
        """Clean up temporary test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_from_inspection_auto_generated_strip_id(self):
        """Test that passing strip_id=None generates a unique auto strip ID."""
        state, event = self.manager.from_inspection(self.inspection_full, strip_id=None)
        self.assertTrue(state.strip_id.startswith("strip_"))
        self.assertEqual(event.event_type, EventType.CREATED)
        self.assertEqual(state.status, InventoryStatus.NORMAL)

    def test_from_inspection_explicit_strip_id(self):
        """Test processing inspection with explicit strip_id."""
        state, event = self.manager.from_inspection(self.inspection_missing, strip_id="strip_20260729_001")
        self.assertEqual(state.strip_id, "strip_20260729_001")
        self.assertEqual(state.present_count, 12)
        self.assertEqual(state.missing_count, 3)
        self.assertEqual(state.missing_slots, (11, 14, 15))
        self.assertEqual(state.status, InventoryStatus.TABLET_MISSING)

    def test_low_confidence_business_status_assignment(self):
        """Test assigning LOW_CONFIDENCE status when avg_confidence < threshold."""
        state, event = self.manager.from_inspection(
            self.inspection_low_conf,
            strip_id="strip_low_conf",
            conf_threshold=0.60
        )
        self.assertEqual(state.status, InventoryStatus.LOW_CONFIDENCE)

    def test_optional_persistence_default_false(self):
        """Test that save defaults to False so JSON files are not written automatically."""
        state, event = self.manager.from_inspection(self.inspection_full, strip_id="strip_no_save", save=False)
        self.assertFalse(self.persistence.exists("strip_no_save"))

        # Explicit save=True
        state, event = self.manager.from_inspection(self.inspection_full, strip_id="strip_save_explicit", save=True)
        self.assertTrue(self.persistence.exists("strip_save_explicit"))

    def test_sequential_frame_transitions(self):
        """Test sequential transition flow across frames."""
        strip_id = "strip_stream_01"
        # Frame 1: Full
        state1, event1 = self.manager.from_inspection(self.inspection_full, strip_id=strip_id)
        self.assertEqual(event1.event_type, EventType.CREATED)

        # Frame 2: Identical Frame -> NO_CHANGE
        state2, event2 = self.manager.from_inspection(self.inspection_full, strip_id=strip_id)
        self.assertEqual(event2.event_type, EventType.NO_CHANGE)

        # Frame 3: 3 Tablets Removed -> TABLET_REMOVED
        state3, event3 = self.manager.from_inspection(self.inspection_missing, strip_id=strip_id)
        self.assertEqual(event3.event_type, EventType.TABLET_REMOVED)
        self.assertEqual(event3.delta_present, -3)

    def test_summary_and_formatters(self):
        """Test manager summary() and output methods."""
        self.manager.from_inspection(self.inspection_missing, strip_id="strip_fmt_01")
        summary_str = self.manager.summary("strip_fmt_01")
        self.assertIn("MEDICINE STRIP INVENTORY SUMMARY", summary_str)
        self.assertIn("strip_fmt_01", summary_str)

        d = self.manager.to_dict("strip_fmt_01")
        self.assertEqual(d["strip_id"], "strip_fmt_01")

        j = self.manager.to_json("strip_fmt_01")
        self.assertIn("strip_fmt_01", j)

    def test_unknown_strip_lookup_raises_item_not_found(self):
        """Test looking up unknown strip ID raises ItemNotFoundError."""
        with self.assertRaises(ItemNotFoundError):
            self.manager.summary("unknown_strip")


if __name__ == "__main__":
    unittest.main()
