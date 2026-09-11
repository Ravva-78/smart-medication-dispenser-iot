"""
Unit tests for clinical/rules.py ClinicalRulesEngine module.
"""
import unittest
from datetime import datetime, timezone, timedelta
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryMetadata, InventoryState
from inventory.events import InventoryEvent
from ocr.models import MedicineIdentity
from clinical.enums import DecisionOutcome
from clinical.models import Prescription, DoseSchedule
from clinical.rules import ClinicalRulesEngine


class TestClinicalRulesEngine(unittest.TestCase):
    """Test suite for ClinicalRulesEngine safety rule evaluators."""

    def setUp(self):
        """Create baseline fixtures for rules testing."""
        self.now = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone.utc)
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

        self.wrong_identity = MedicineIdentity(
            medicine_name="Ibuprofen",
            strength="400mg",
            confidence=0.95,
        )

        self.expired_identity = MedicineIdentity(
            medicine_name="Paracetamol",
            strength="500mg",
            expiry_date="2024-01-01",  # Expired in past
            confidence=0.95,
        )

        # Baseline InventoryState and InventoryEvent fixtures
        metadata = InventoryMetadata(inspection_id="insp_1", image_name="img.jpg", capture_time=self.now, camera_id="cam1")
        self.state_prev = InventoryState(strip_id="strip_01", inspection_time=self.now, total_slots=10, present_count=10, missing_count=0, occupancy_percentage=100.0, missing_slots=(), average_confidence=0.99, status=InventoryStatus.NORMAL, metadata=metadata)
        self.state_curr = InventoryState(strip_id="strip_01", inspection_time=self.now, total_slots=10, present_count=9, missing_count=1, occupancy_percentage=90.0, missing_slots=(5,), average_confidence=0.99, status=InventoryStatus.TABLET_MISSING, metadata=metadata)

        self.removed_event = InventoryEvent(
            event_id="evt_01",
            timestamp=self.now,
            strip_id="strip_01",
            event_type=EventType.TABLET_REMOVED,
            delta_present=-1,
            delta_missing=1,
            removed_slots=(5,),
            added_slots=(),
            previous_state=self.state_prev,
            current_state=self.state_curr,
        )

    def test_correct_dose_evaluation(self):
        """Test rule evaluation returning CORRECT_DOSE for matching drug, valid expiry, and on-time window."""
        outcome, reason, actionable = ClinicalRulesEngine.evaluate_compliance(
            event=self.removed_event,
            identity=self.valid_identity,
            prescription=self.prescription,
            schedule=self.schedule,
        )
        self.assertEqual(outcome, DecisionOutcome.CORRECT_DOSE)
        self.assertTrue(actionable)
        self.assertIn("Correct dose taken", reason)

    def test_late_tablet_removal_is_correct_dose(self):
        """A real tablet removal should count as taken even after the grace window elapsed."""
        late_schedule = DoseSchedule(
            schedule_id="sched_late",
            prescription_id="rx_101",
            scheduled_time=self.now - timedelta(minutes=45),
            grace_period_minutes=5,
        )

        outcome, reason, actionable = ClinicalRulesEngine.evaluate_compliance(
            event=self.removed_event,
            identity=self.valid_identity,
            prescription=self.prescription,
            schedule=late_schedule,
        )

        self.assertEqual(outcome, DecisionOutcome.CORRECT_DOSE)
        self.assertTrue(actionable)
        self.assertIn("Correct dose taken", reason)

    def test_unchanged_count_after_grace_is_missed(self):
        """If scan #2 has no tablet removed after grace, the dose is genuinely missed."""
        missed_schedule = DoseSchedule(
            schedule_id="sched_missed",
            prescription_id="rx_101",
            scheduled_time=self.now - timedelta(minutes=10),
            grace_period_minutes=5,
        )
        no_change_event = InventoryEvent(
            event_id="evt_no_change",
            timestamp=self.now,
            strip_id="strip_01",
            event_type=EventType.NO_CHANGE,
            delta_present=0,
            delta_missing=0,
            removed_slots=(),
            added_slots=(),
            previous_state=self.state_prev,
            current_state=self.state_prev,
        )

        outcome, reason, actionable = ClinicalRulesEngine.evaluate_compliance(
            event=no_change_event,
            identity=self.valid_identity,
            prescription=self.prescription,
            schedule=missed_schedule,
        )

        self.assertEqual(outcome, DecisionOutcome.DOSE_MISSED)
        self.assertTrue(actionable)
        self.assertIn("Medicine not taken", reason)

    def test_wrong_medicine_evaluation(self):
        """Test rule evaluation returning WRONG_MEDICINE when extracted drug contradicts prescription."""
        outcome, reason, actionable = ClinicalRulesEngine.evaluate_compliance(
            event=self.removed_event,
            identity=self.wrong_identity,
            prescription=self.prescription,
            schedule=self.schedule,
        )
        self.assertEqual(outcome, DecisionOutcome.WRONG_MEDICINE)
        self.assertTrue(actionable)
        self.assertIn("Medicine mismatch", reason)

    def test_expired_medicine_evaluation(self):
        """Test rule evaluation returning EXPIRED_MEDICINE when drug expiry is in the past."""
        outcome, reason, actionable = ClinicalRulesEngine.evaluate_compliance(
            event=self.removed_event,
            identity=self.expired_identity,
            prescription=self.prescription,
            schedule=self.schedule,
        )
        self.assertEqual(outcome, DecisionOutcome.EXPIRED_MEDICINE)
        self.assertTrue(actionable)
        self.assertIn("Expired medicine", reason)


if __name__ == "__main__":
    unittest.main()
