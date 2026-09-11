"""
End-to-End Master System Pipeline Integration Test.

Purpose:
    Validates end-to-end integration across all bounded contexts:
    InspectionResult (Vision) -> InventoryManager (InventoryEvent) -> OCRManager (MedicineIdentity) -> ClinicalDecisionManager (ComplianceDecision).
"""

import unittest
import numpy as np
from datetime import datetime, timezone

from pipeline.inspection_result import InspectionResult, PocketResult
from inventory.manager import InventoryManager
from ocr.manager import OCRManager
from ocr.backends import MockOCRBackend
from clinical.manager import ClinicalDecisionManager
from clinical.models import Prescription, DoseSchedule
from clinical.enums import DecisionOutcome


class TestMasterSystemPipeline(unittest.TestCase):
    """End-to-End Master System Pipeline Integration Test Suite."""

    def setUp(self):
        """Set up fully integrated system pipeline components."""
        self.now = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone.utc)

        # 1. Initialize Subsystem Facades
        self.inventory_mgr = InventoryManager()
        self.ocr_mgr = OCRManager(backend=MockOCRBackend(mock_text="PARACETAMOL 500mg BATCH-2026 EXP 12/2028"))
        self.clinical_mgr = ClinicalDecisionManager()

        # 2. Patient Prescription & Schedule Fixtures
        self.prescription = Prescription(
            prescription_id="rx_master_01",
            patient_id="patient_master_99",
            medicine_name="Paracetamol",
            strength="500mg",
        )
        self.schedule = DoseSchedule(
            schedule_id="sched_master_01",
            prescription_id="rx_master_01",
            scheduled_time=self.now,
            grace_period_minutes=30,
        )

        # Synthetic image array simulating packaging crop from camera feed
        self.crop_image = np.zeros((100, 200, 3), dtype=np.uint8)

    def test_full_pipeline_correct_dose_flow(self):
        """Test complete pipeline execution resulting in CORRECT_DOSE compliance decision."""
        # Step A: Initial baseline inspection (10 tablets present)
        pockets_1 = [PocketResult(index=i, class_name="present", confidence=0.98, bbox=(0, 0, 10, 10)) for i in range(10)]
        insp_1 = InspectionResult(
            total=10,
            present=10,
            missing=0,
            avg_confidence=0.98,
            pockets=pockets_1,
        )
        state_1, event_1 = self.inventory_mgr.from_inspection(insp_1, strip_id="strip_e2e_100", inspection_time=self.now)
        self.assertIsNotNone(event_1)
        self.assertEqual(event_1.event_type.value, "CREATED")

        # Step B: Subsequent inspection (1 tablet removed from pocket #4)
        pockets_2 = [
            PocketResult(index=i, class_name="missing" if i == 4 else "present", confidence=0.99, bbox=(0, 0, 10, 10))
            for i in range(10)
        ]
        insp_2 = InspectionResult(
            total=10,
            present=9,
            missing=1,
            avg_confidence=0.99,
            pockets=pockets_2,
        )
        state_2, event_2 = self.inventory_mgr.from_inspection(insp_2, strip_id="strip_e2e_100", inspection_time=self.now)

        self.assertEqual(event_2.event_type.value, "TABLET_REMOVED")
        self.assertEqual(event_2.removed_slots, (4,))

        # Step C: OCR Verification of packaging crop
        ocr_result = self.ocr_mgr.process_image(self.crop_image, preprocess=True)
        self.assertIsNotNone(ocr_result.identity)
        self.assertEqual(ocr_result.identity.medicine_name, "Paracetamol")
        self.assertEqual(ocr_result.identity.strength, "500mg")

        # Step D: Clinical Decision Engine evaluation
        decision = self.clinical_mgr.evaluate_event(
            event=event_2,
            prescription=self.prescription,
            identity=ocr_result.identity,
            schedule=self.schedule,
        )

        # Assert Master Pipeline Execution Outcome
        self.assertEqual(decision.outcome, DecisionOutcome.CORRECT_DOSE)
        self.assertEqual(decision.patient_id, "patient_master_99")
        self.assertEqual(decision.strip_id, "strip_e2e_100")
        self.assertTrue(decision.actionable)
        self.assertIn("Correct dose taken", decision.reason)

        # Step E: Verify Adherence Statistics in Audit Metrics
        metrics = self.clinical_mgr.get_patient_metrics("patient_master_99")
        self.assertEqual(metrics["total_decisions"], 1)
        self.assertEqual(metrics["correct_doses"], 1)
        self.assertEqual(metrics["adherence_percentage"], 100.0)


if __name__ == "__main__":
    unittest.main()
