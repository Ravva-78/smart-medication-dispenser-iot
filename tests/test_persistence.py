"""
Unit tests for inventory/persistence.py.
"""
import unittest
import shutil
from pathlib import Path
from datetime import datetime, timezone
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState
from inventory.events import InventoryEvent
from inventory.history import InventoryHistory
from inventory.exceptions import PersistenceError, ItemNotFoundError
from inventory.persistence import JSONPersistenceManager


class TestJSONPersistenceManager(unittest.TestCase):
    """Test suite for JSONPersistenceManager save/load operations."""

    def setUp(self):
        """Create temporary test directory and state fixtures."""
        self.test_dir = Path(__file__).parent / "temp_persistence_storage"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.manager = JSONPersistenceManager(storage_dir=self.test_dir)

        self.now = datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc)
        self.metadata = InventoryMetadata(
            inspection_id="insp_pers_01",
            image_name="pers_strip.jpg",
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

        self.history = InventoryHistory(strip_id="strip_20260729_001")
        self.event = InventoryEvent(
            event_id="evt_pers_01",
            timestamp=self.now,
            strip_id="strip_20260729_001",
            event_type=EventType.CREATED,
            delta_present=12,
            delta_missing=3,
            removed_slots=(11, 14, 15),
            added_slots=(),
            previous_state=None,
            current_state=self.state,
        )
        self.history.record_event(self.event)

    def tearDown(self):
        """Clean up temporary test directory."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_save_and_load_state(self):
        """Test saving and loading InventoryState to/from JSON."""
        filepath = self.manager.save(self.state)
        self.assertTrue(filepath.exists())
        self.assertTrue(self.manager.exists("strip_20260729_001"))

        loaded_state = self.manager.load("strip_20260729_001")
        self.assertEqual(loaded_state, self.state)
        self.assertEqual(loaded_state.strip_id, "strip_20260729_001")

    def test_save_and_load_with_history(self):
        """Test saving and loading state along with history log."""
        self.manager.save(self.state, self.history)
        loaded_history = self.manager.load_history("strip_20260729_001")
        self.assertIsNotNone(loaded_history)
        self.assertEqual(loaded_history.strip_id, "strip_20260729_001")
        self.assertEqual(len(loaded_history.get_events()), 1)

    def test_load_non_existent_item_raises_item_not_found(self):
        """Test loading a non-existent strip ID raises ItemNotFoundError."""
        with self.assertRaises(ItemNotFoundError):
            self.manager.load("strip_non_existent")

    def test_load_corrupted_json_raises_persistence_error(self):
        """Test loading corrupted JSON content raises PersistenceError."""
        file_path = self.test_dir / "strip_corrupted.json"
        with open(file_path, "w") as f:
            f.write("{ INVALID JSON PAYLOAD ...")

        with self.assertRaises(PersistenceError):
            self.manager.load("strip_corrupted")

    def test_delete_inventory_file(self):
        """Test deleting persisted inventory storage file."""
        self.manager.save(self.state)
        self.assertTrue(self.manager.exists("strip_20260729_001"))

        deleted = self.manager.delete("strip_20260729_001")
        self.assertTrue(deleted)
        self.assertFalse(self.manager.exists("strip_20260729_001"))


if __name__ == "__main__":
    unittest.main()
