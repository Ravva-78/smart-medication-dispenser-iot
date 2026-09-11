"""
Unit tests for clinical/manager.py ClinicalDecisionManager facade.
"""
import unittest
from datetime import datetime, timezone
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState
from inventory.events import InventoryEvent
from ocr.models import MedicineIdentity
from clinical.enums import DecisionOutcome
from clinical.models import Prescription, DoseSchedule, ComplianceDecision
from clinical.manager import ClinicalDecisionManager


class TestClinicalDecisionManager(unittest.TestCase):
    """Test suite for ClinicalDecisionManager orchestrator facade."""

    def setUp(self):
        """Set up manager instance and sample fixtures."""
        self.now = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone.utc)
        self.manager = ClinicalDecisionManager()

        self.prescription = Prescription(
            prescription_id="rx_101",
            patient_id="patient_01",
            medicine_name="Paracetamol",
            strength="500mg",
        )
        self.schedule = DoseSchedule(
            schedule_id="sched_101",
            prescription_id="rx_101",
            scheduled_time=self.now,
            grace_period_minutes=30,
        )

        self.valid_identity = MedicineIdentity(
            medicine_name="Paracetamol",
            strength="500mg",
            expiry_date="2028-12-31",
            confidence=0.98,
        )

        metadata = InventoryMetadata(inspection_id="insp_1", image_name="img.jpg", capture_time=self.now, camera_id="cam1")
        state_prev = InventoryState(strip_id="strip_01", inspection_time=self.now, total_slots=10, present_count=10, missing_count=0, occupancy_percentage=100.0, missing_slots=(), average_confidence=0.99, status=InventoryStatus.NORMAL, metadata=metadata)
        state_curr = InventoryState(strip_id="strip_01", inspection_time=self.now, total_slots=10, present_count=9, missing_count=1, occupancy_percentage=90.0, missing_slots=(5,), average_confidence=0.99, status=InventoryStatus.TABLET_MISSING, metadata=metadata)

        self.removed_event = InventoryEvent(
            event_id="evt_01",
            timestamp=self.now,
            strip_id="strip_01",
            event_type=EventType.TABLET_REMOVED,
            delta_present=-1,
            delta_missing=1,
            removed_slots=(5,),
            added_slots=(),
            previous_state=state_prev,
            current_state=state_curr,
        )

    def test_evaluate_event_facade_flow(self):
        """Test evaluating an event through the ClinicalDecisionManager facade."""
        decision = self.manager.evaluate_event(
            event=self.removed_event,
            identity=self.valid_identity,
            prescription=self.prescription,
            schedule=self.schedule,
        )

        self.assertIsInstance(decision, ComplianceDecision)
        self.assertEqual(decision.patient_id, "patient_01")
        self.assertEqual(decision.outcome, DecisionOutcome.CORRECT_DOSE)
        self.assertTrue(decision.actionable)

        # Confirm decision was logged in internal history
        history = self.manager.get_decision_history(patient_id="patient_01")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0], decision)

        # Confirm metrics computation
        metrics = self.manager.get_patient_metrics("patient_01")
        self.assertEqual(metrics["adherence_percentage"], 100.0)


if __name__ == "__main__":
    unittest.main()
