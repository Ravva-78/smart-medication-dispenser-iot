"""
Integration tests for end-to-end vision pipeline and inventory subsystem.
"""
import unittest
import shutil
from pathlib import Path
from pipeline.inspection_result import InspectionResult, PocketResult
from app.pipeline import Pipeline
from inventory.manager import InventoryManager, StripIdentityProvider
from inventory.enums import InventoryStatus, EventType
from inventory.persistence import JSONPersistenceManager


class CustomOCRStripIdentityProvider(StripIdentityProvider):
    """Sample custom identity provider representing OCR/Barcode strip lookup."""

    def __init__(self, fixed_id: str):
        self.fixed_id = fixed_id

    def provide_id(self, result=None) -> str:
        return self.fixed_id


class TestPipelineIntegration(unittest.TestCase):
    """Integration test suite for Vision Pipeline + Inventory Subsystem."""

    def setUp(self):
        """Set up test environment and image source paths."""
        self.test_dir = Path(__file__).parent / "temp_integration_storage"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.persistence = JSONPersistenceManager(storage_dir=self.test_dir)
        self.inventory_mgr = InventoryManager(persistence=self.persistence)

        self.root_dir = Path(__file__).parent.parent
        self.test_image_path = self.root_dir / "dataset" / "images" / "test" / "Screenshot 2026-07-22 181006.png"

        # Baseline Inspection Results for multi-step workflow integration
        self.full_inspection = InspectionResult(
            total=10,
            present=10,
            missing=0,
            avg_confidence=0.999,
            pockets=[PocketResult(index=i, class_name="present", confidence=0.999, bbox=(0,0,10,10)) for i in range(1, 11)]
        )

        self.one_missing_inspection = InspectionResult(
            total=10,
            present=9,
            missing=1,
            avg_confidence=0.998,
            pockets=[PocketResult(index=i, class_name="present" if i != 5 else "missing", confidence=0.998, bbox=(0,0,10,10)) for i in range(1, 11)]
        )

        self.two_missing_inspection = InspectionResult(
            total=10,
            present=8,
            missing=2,
            avg_confidence=0.997,
            pockets=[PocketResult(index=i, class_name="present" if i not in (5, 8) else "missing", confidence=0.997, bbox=(0,0,10,10)) for i in range(1, 11)]
        )

    def tearDown(self):
        """Clean up temporary integration storage."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_pipeline_to_inventory_integration_flow(self):
        """Test complete flow: Image -> Pipeline -> InspectionResult -> InventoryState -> InventoryEvent."""
        if not self.test_image_path.exists():
            self.skipTest(f"Test image not found at {self.test_image_path}")

        pipeline = Pipeline.from_defaults()

        # 1. Execute Vision Pipeline
        result = pipeline.run(str(self.test_image_path), debug=False)
        self.assertGreater(result.total, 0)

        # 2. Process via InventoryManager
        strip_id = "strip_test_integration_01"
        state, event = self.inventory_mgr.from_inspection(
            result=result,
            strip_id=strip_id,
            image_name=self.test_image_path.name,
            save=True,
        )

        # 3. Assert InventoryState Properties
        self.assertEqual(state.strip_id, strip_id)
        self.assertEqual(state.total_slots, result.total)
        self.assertEqual(state.present_count, result.present)
        self.assertEqual(state.missing_count, result.missing)
        self.assertEqual(state.missing_slots, tuple(sorted(result.missing_indices)))
        self.assertEqual(state.status, InventoryStatus.TABLET_MISSING if result.missing > 0 else InventoryStatus.NORMAL)

        # 4. Assert InventoryEvent Properties
        self.assertEqual(event.event_type, EventType.CREATED)
        self.assertEqual(event.strip_id, strip_id)
        self.assertEqual(event.schema_version, "1.0")

        # 5. Assert Persistence Save
        self.assertTrue(self.persistence.exists(strip_id))
        loaded_state = self.persistence.load(strip_id)
        self.assertEqual(loaded_state, state)

    def test_multi_step_dispense_workflow(self):
        """Test full strip -> remove 1 tablet -> remove 2nd tablet -> repeated frame."""
        strip_id = "strip_dispense_seq_01"

        # Frame 1: Full Strip
        state1, event1 = self.inventory_mgr.from_inspection(self.full_inspection, strip_id=strip_id, save=True)
        self.assertEqual(event1.event_type, EventType.CREATED)
        self.assertEqual(state1.present_count, 10)

        # Frame 2: Remove Tablet 5
        state2, event2 = self.inventory_mgr.from_inspection(self.one_missing_inspection, strip_id=strip_id, save=True)
        self.assertEqual(event2.event_type, EventType.TABLET_REMOVED)
        self.assertEqual(event2.removed_slots, (5,))
        self.assertEqual(state2.present_count, 9)

        # Frame 3: Repeated Frame (Same state)
        state3, event3 = self.inventory_mgr.from_inspection(self.one_missing_inspection, strip_id=strip_id, save=True)
        self.assertEqual(event3.event_type, EventType.NO_CHANGE)

        # Frame 4: Remove Tablet 8
        state4, event4 = self.inventory_mgr.from_inspection(self.two_missing_inspection, strip_id=strip_id, save=True)
        self.assertEqual(event4.event_type, EventType.TABLET_REMOVED)
        self.assertEqual(event4.removed_slots, (8,))
        self.assertEqual(state4.present_count, 8)

    def test_strip_replacement_scenario(self):
        """Test tablet removal followed by strip replacement event."""
        strip_id_old = "strip_old_01"
        strip_id_new = "strip_new_02"

        # Frame 1: Old strip with missing tablet
        state1, event1 = self.inventory_mgr.from_inspection(self.one_missing_inspection, strip_id=strip_id_old, save=True)
        self.assertEqual(event1.event_type, EventType.CREATED)

        # Frame 2: Replace with new full strip (different strip_id)
        state2, event2 = self.inventory_mgr.from_inspection(self.full_inspection, strip_id=strip_id_new, save=True)
        self.assertEqual(event2.event_type, EventType.CREATED)
        self.assertEqual(state2.strip_id, strip_id_new)

    def test_pluggable_identity_provider_integration(self):
        """Test InventoryManager with custom pluggable StripIdentityProvider."""
        custom_provider = CustomOCRStripIdentityProvider("PARACETAMOL_500MG_BATCH_99")
        custom_mgr = InventoryManager(persistence=self.persistence, identity_provider=custom_provider)

        state, event = custom_mgr.from_inspection(self.full_inspection, strip_id=None)
        self.assertEqual(state.strip_id, "PARACETAMOL_500MG_BATCH_99")


if __name__ == "__main__":
    unittest.main()
