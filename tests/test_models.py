"""
Unit tests for inventory/models.py.
"""
import unittest
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState, InventorySnapshot


class TestInventoryModels(unittest.TestCase):
    """Test suite for InventoryMetadata, InventoryState, and InventorySnapshot models."""

    def setUp(self):
        """Create sample instance data for testing."""
        self.now = datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc)

        self.metadata = InventoryMetadata(
            inspection_id="insp_12345",
            image_name="test_strip.jpg",
            capture_time=self.now,
            camera_id="cam_01",
            model_versions={"Model_A": "v1.0", "Model_B": "v1.0", "Model_C": "v1.0"},
            processing_time_ms=124.5,
            pipeline_version="0.1.0",
            software_version="0.1.0",
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

        self.snapshot = InventorySnapshot(
            snapshot_id="snap_001",
            timestamp=self.now,
            event_type=EventType.CREATED,
            event_id="evt_001",
            state=self.state,
        )

    def test_metadata_creation_and_immutability(self):
        """Test InventoryMetadata creation and frozen immutability."""
        self.assertEqual(self.metadata.inspection_id, "insp_12345")
        self.assertEqual(self.metadata.camera_id, "cam_01")
        self.assertIsInstance(self.metadata.capture_time, datetime)
        with self.assertRaises(FrozenInstanceError):
            self.metadata.camera_id = "cam_02"

    def test_state_creation_and_immutability(self):
        """Test InventoryState creation, missing_slots tuple immutability, and frozen state."""
        self.assertEqual(self.state.strip_id, "strip_20260729_001")
        self.assertEqual(self.state.present_count, 12)
        self.assertEqual(self.state.missing_count, 3)
        self.assertIsInstance(self.state.missing_slots, tuple)
        self.assertEqual(self.state.missing_slots, (11, 14, 15))
        self.assertEqual(self.state.status, InventoryStatus.TABLET_MISSING)

        with self.assertRaises(FrozenInstanceError):
            self.state.present_count = 10

    def test_snapshot_creation_and_immutability(self):
        """Test InventorySnapshot creation and frozen immutability."""
        self.assertEqual(self.snapshot.snapshot_id, "snap_001")
        self.assertEqual(self.snapshot.event_type, EventType.CREATED)
        self.assertEqual(self.snapshot.state.strip_id, "strip_20260729_001")
        with self.assertRaises(FrozenInstanceError):
            self.snapshot.event_type = EventType.UPDATED

    def test_metadata_serialization_roundtrip(self):
        """Test metadata to_dict() and from_dict() roundtrip."""
        d = self.metadata.to_dict()
        self.assertEqual(d["inspection_id"], "insp_12345")
        self.assertIsInstance(d["capture_time"], str)

        reconstructed = InventoryMetadata.from_dict(d)
        self.assertEqual(reconstructed, self.metadata)

    def test_state_serialization_roundtrip(self):
        """Test state to_dict() and from_dict() roundtrip."""
        d = self.state.to_dict()
        self.assertEqual(d["strip_id"], "strip_20260729_001")
        self.assertEqual(d["status"], "TABLET_MISSING")
        self.assertEqual(d["missing_slots"], [11, 14, 15])

        reconstructed = InventoryState.from_dict(d)
        self.assertEqual(reconstructed, self.state)
        self.assertIsInstance(reconstructed.missing_slots, tuple)

    def test_snapshot_serialization_roundtrip(self):
        """Test snapshot to_dict() and from_dict() roundtrip."""
        d = self.snapshot.to_dict()
        self.assertEqual(d["snapshot_id"], "snap_001")
        self.assertEqual(d["event_type"], "CREATED")

        reconstructed = InventorySnapshot.from_dict(d)
        self.assertEqual(reconstructed, self.snapshot)

    def test_dataclass_equality_semantics(self):
        """Test dataclass equality (==) and inequality (!=)."""
        state_copy = InventoryState(
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
        self.assertEqual(self.state, state_copy)

        different_state = InventoryState(
            strip_id="strip_20260729_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=11,  # 1 less present
            missing_count=4,
            occupancy_percentage=73.33,
            missing_slots=(10, 11, 14, 15),
            average_confidence=0.9975,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )
        self.assertNotEqual(self.state, different_state)

    def test_invalid_timestamp_deserialization(self):
        """Test that invalid timestamp types raise ValueError."""
        d = self.metadata.to_dict()
        d["capture_time"] = 1234567  # invalid integer
        with self.assertRaises(ValueError):
            InventoryMetadata.from_dict(d)


if __name__ == "__main__":
    unittest.main()
