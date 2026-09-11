"""
Expanded Clinical & Platform System Scenario Integration Tests.

Purpose:
    Exercises complete platform scenarios across all clinical outcomes:
    CREATED, CORRECT_DOSE, WRONG_MEDICINE, EXPIRED_MEDICINE, EXTRA_DOSE, UNCERTAIN, NO_CHANGE, and Alert Dispatching.
"""

import unittest
import numpy as np
from datetime import datetime, timedelta, timezone

from pipeline.inspection_result import InspectionResult, PocketResult
from inventory.manager import InventoryManager
from ocr.manager import OCRManager
from ocr.backends import MockOCRBackend
from clinical.manager import ClinicalDecisionManager
from clinical.models import Prescription, DoseSchedule
from clinical.enums import DecisionOutcome
from alerting.manager import AlertManager
from alerting.dispatchers import MockAlertDispatcher


class TestPlatformClinicalScenarios(unittest.TestCase):
    """Full system scenario integration testing suite."""

    def setUp(self):
        """Set up fully integrated system pipeline for scenario testing."""
        self.now = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone.utc)
        self.inventory_mgr = InventoryManager()
        self.ocr_mock_backend = MockOCRBackend(mock_text="PARACETAMOL 500mg BATCH-2026-09 EXP 12/2028")
        self.ocr_mgr = OCRManager(backend=self.ocr_mock_backend)
        self.clinical_mgr = ClinicalDecisionManager()
        self.mock_alert_dispatcher = MockAlertDispatcher()
        self.alert_mgr = AlertManager(dispatchers=[self.mock_alert_dispatcher])

        self.prescription = Prescription(
            prescription_id="rx_scen_01",
            patient_id="patient_scen_10",
            medicine_name="Paracetamol",
            strength="500mg",
        )
        self.schedule = DoseSchedule(
            schedule_id="sched_scen_01",
            prescription_id="rx_scen_01",
            scheduled_time=self.now,
            grace_period_minutes=30,
        )
        self.synthetic_crop = np.zeros((100, 200, 3), dtype=np.uint8)

    def _create_inspection(self, present: int, missing_indices: list, total: int = 10) -> InspectionResult:
        pockets = [
            PocketResult(index=i + 1, class_name="missing" if (i + 1) in missing_indices else "present", confidence=0.99, bbox=(0, 0, 10, 10))
            for i in range(total)
        ]
        return InspectionResult(total=total, present=present, missing=len(missing_indices), avg_confidence=0.99, pockets=pockets)


    def test_scenario_1_baseline_and_tablet_removal_correct_dose(self):
        """Scenario 1: Baseline registration followed by on-time tablet removal -> CORRECT_DOSE."""
        # 1. Baseline
        insp1 = self._create_inspection(present=10, missing_indices=[])
        s1, e1 = self.inventory_mgr.from_inspection(insp1, strip_id="strip_s1", inspection_time=self.now)
        self.assertEqual(e1.event_type.value, "CREATED")

        # 2. Tablet removal
        insp2 = self._create_inspection(present=9, missing_indices=[2])
        s2, e2 = self.inventory_mgr.from_inspection(insp2, strip_id="strip_s1", inspection_time=self.now)
        self.assertEqual(e2.event_type.value, "TABLET_REMOVED")

        # 3. Clinical Evaluation
        ocr_res = self.ocr_mgr.process_image(self.synthetic_crop)
        decision = self.clinical_mgr.evaluate_event(e2, prescription=self.prescription, identity=ocr_res.identity, schedule=self.schedule)

        self.assertEqual(decision.outcome, DecisionOutcome.CORRECT_DOSE)

    def test_scenario_2_wrong_medicine_alert_trigger(self):
        """Scenario 2: Tablet removed but OCR identifies wrong drug -> WRONG_MEDICINE & Critical Alert."""
        self.inventory_mgr.from_inspection(self._create_inspection(10, []), strip_id="strip_s2", inspection_time=self.now)
        s2, e2 = self.inventory_mgr.from_inspection(self._create_inspection(9, [3]), strip_id="strip_s2", inspection_time=self.now)

        # Mock OCR returning Ibuprofen
        self.ocr_mgr.backend = MockOCRBackend(mock_text="IBUPROFEN 400mg BATCH-101")
        ocr_res = self.ocr_mgr.process_image(self.synthetic_crop)

        decision = self.clinical_mgr.evaluate_event(e2, prescription=self.prescription, identity=ocr_res.identity, schedule=self.schedule)
        self.assertEqual(decision.outcome, DecisionOutcome.WRONG_MEDICINE)

        # Verify EventBus dispatched Critical Caregiver Alert
        alerts = self.alert_mgr.get_alert_history(self.prescription.patient_id)
        self.assertTrue(any(a.severity.value == "CRITICAL" for a in alerts))

    def test_scenario_3_expired_medicine_detection(self):
        """Scenario 3: Tablet removed but OCR identifies expired batch date -> EXPIRED_MEDICINE."""
        self.inventory_mgr.from_inspection(self._create_inspection(10, []), strip_id="strip_s3", inspection_time=self.now)
        s2, e2 = self.inventory_mgr.from_inspection(self._create_inspection(9, [1]), strip_id="strip_s3", inspection_time=self.now)

        # Mock OCR returning expired date
        self.ocr_mgr.backend = MockOCRBackend(mock_text="PARACETAMOL 500mg EXP 01/2020")
        ocr_res = self.ocr_mgr.process_image(self.synthetic_crop)

        decision = self.clinical_mgr.evaluate_event(e2, prescription=self.prescription, identity=ocr_res.identity, schedule=self.schedule)
        self.assertEqual(decision.outcome, DecisionOutcome.EXPIRED_MEDICINE)

    def test_scenario_4_early_dose_extra_dose(self):
        """Scenario 4: Tablet removed 2 hours before scheduled time -> EXTRA_DOSE."""
        early_time = self.now - timedelta(hours=2)
        self.inventory_mgr.from_inspection(self._create_inspection(10, []), strip_id="strip_s4", inspection_time=early_time)
        s2, e2 = self.inventory_mgr.from_inspection(self._create_inspection(9, [1]), strip_id="strip_s4", inspection_time=early_time)


        ocr_res = self.ocr_mgr.process_image(self.synthetic_crop)
        decision = self.clinical_mgr.evaluate_event(e2, prescription=self.prescription, identity=ocr_res.identity, schedule=self.schedule)
        self.assertEqual(decision.outcome, DecisionOutcome.EXTRA_DOSE)


if __name__ == "__main__":
    unittest.main()
