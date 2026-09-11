"""
Unit tests for inventory/validator.py.
"""
import unittest
from datetime import datetime, timezone
from inventory.enums import InventoryStatus
from inventory.models import InventoryMetadata, InventoryState
from inventory.exceptions import ValidationError
from inventory.validator import InventoryValidator


class TestInventoryValidator(unittest.TestCase):
    """Test suite for technical and mathematical correctness validation of InventoryState."""

    def setUp(self):
        """Create a valid baseline InventoryState fixture for validation testing."""
        self.now = datetime(2026, 7, 29, 0, 0, 0, tzinfo=timezone.utc)
        self.metadata = InventoryMetadata(
            inspection_id="insp_val_01",
            image_name="valid_strip.jpg",
            capture_time=self.now,
            camera_id="cam_01",
        )
        self.valid_state = InventoryState(
            strip_id="strip_20260729_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=12,
            missing_count=3,
            occupancy_percentage=80.0,
            missing_slots=(11, 14, 15),
            average_confidence=0.9950,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )

    def test_valid_state_passes_validation(self):
        """Test that a physically and mathematically correct state passes validation cleanly."""
        self.assertTrue(InventoryValidator.validate(self.valid_state))

    def test_zero_total_slots_fails_validation(self):
        """Test that total_slots <= 0 raises ValidationError."""
        invalid_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=0,
            present_count=0,
            missing_count=0,
            occupancy_percentage=0.0,
            missing_slots=(),
            average_confidence=0.95,
            status=InventoryStatus.INVALID,
            metadata=self.metadata,
        )
        with self.assertRaises(ValidationError) as ctx:
            InventoryValidator.validate(invalid_state)
        self.assertIn("must be strictly positive", str(ctx.exception))

    def test_negative_counts_fail_validation(self):
        """Test that negative present_count or missing_count raises ValidationError."""
        invalid_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=-1,
            missing_count=16,
            occupancy_percentage=0.0,
            missing_slots=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16),
            average_confidence=0.95,
            status=InventoryStatus.INVALID,
            metadata=self.metadata,
        )
        with self.assertRaises(ValidationError) as ctx:
            InventoryValidator.validate(invalid_state)
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_count_sum_mismatch_fails_validation(self):
        """Test that present_count + missing_count != total_slots raises ValidationError."""
        invalid_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=10,
            missing_count=3,
            occupancy_percentage=66.67,
            missing_slots=(13, 14, 15),
            average_confidence=0.95,
            status=InventoryStatus.INVALID,
            metadata=self.metadata,
        )
        with self.assertRaises(ValidationError) as ctx:
            InventoryValidator.validate(invalid_state)
        self.assertIn("must equal total_slots", str(ctx.exception))

    def test_unsorted_missing_slots_fails_validation(self):
        """Test that unsorted missing_slots tuple raises ValidationError."""
        invalid_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=12,
            missing_count=3,
            occupancy_percentage=80.0,
            missing_slots=(15, 11, 14),  # Unsorted
            average_confidence=0.95,
            status=InventoryStatus.INVALID,
            metadata=self.metadata,
        )
        with self.assertRaises(ValidationError) as ctx:
            InventoryValidator.validate(invalid_state)
        self.assertIn("must be sorted in ascending order", str(ctx.exception))

    def test_duplicate_missing_slots_fail_validation(self):
        """Test that duplicate indices in missing_slots raise ValidationError."""
        invalid_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=13,
            missing_count=2,
            occupancy_percentage=86.67,
            missing_slots=(14, 14),
            average_confidence=0.95,
            status=InventoryStatus.INVALID,
            metadata=self.metadata,
        )
        with self.assertRaises(ValidationError) as ctx:
            InventoryValidator.validate(invalid_state)
        self.assertIn("Duplicate", str(ctx.exception))

    def test_out_of_bounds_missing_slots_fail_validation(self):
        """Test that slot indices out of range [1, total_slots] raise ValidationError."""
        invalid_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=15,
            present_count=14,
            missing_count=1,
            occupancy_percentage=93.33,
            missing_slots=(16,),
            average_confidence=0.95,
            status=InventoryStatus.INVALID,
            metadata=self.metadata,
        )
        with self.assertRaises(ValidationError) as ctx:
            InventoryValidator.validate(invalid_state)
        self.assertIn("out of range", str(ctx.exception))

    def test_confidence_boundary_values(self):
        """Test confidence boundaries at exactly 0.0 and 1.0."""
        zero_conf_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=10,
            present_count=10,
            missing_count=0,
            occupancy_percentage=100.0,
            missing_slots=(),
            average_confidence=0.0,
            status=InventoryStatus.LOW_CONFIDENCE,
            metadata=self.metadata,
        )
        self.assertTrue(InventoryValidator.validate(zero_conf_state))

        perfect_conf_state = InventoryState(
            strip_id="strip_001",
            inspection_time=self.now,
            total_slots=10,
            present_count=10,
            missing_count=0,
            occupancy_percentage=100.0,
            missing_slots=(),
            average_confidence=1.0,
            status=InventoryStatus.NORMAL,
            metadata=self.metadata,
        )
        self.assertTrue(InventoryValidator.validate(perfect_conf_state))

    def test_large_strip_dataset(self):
        """Test validation on a large 100-pocket strip dataset."""
        large_state = InventoryState(
            strip_id="strip_large_100",
            inspection_time=self.now,
            total_slots=100,
            present_count=97,
            missing_count=3,
            occupancy_percentage=97.0,
            missing_slots=(12, 45, 88),
            average_confidence=0.992,
            status=InventoryStatus.TABLET_MISSING,
            metadata=self.metadata,
        )
        self.assertTrue(InventoryValidator.validate(large_state))


if __name__ == "__main__":
    unittest.main()
