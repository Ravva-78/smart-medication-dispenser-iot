"""
Unit tests for clinical/models.py and clinical/enums.py domain contracts.
"""
import unittest
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
from clinical.enums import DecisionOutcome, RuleSeverity, ScheduleWindowStatus
from clinical.exceptions import ClinicalEngineError, PrescriptionError, InvalidScheduleError
from clinical.models import Prescription, DoseSchedule, ComplianceDecision


class TestClinicalDomainContracts(unittest.TestCase):
    """Test suite for Clinical Decision Engine domain dataclasses and enums."""

    def setUp(self):
        """Create sample Prescription, DoseSchedule, and ComplianceDecision fixtures."""
        self.now = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone.utc)

        self.prescription = Prescription(
            prescription_id="rx_1001",
            patient_id="patient_402",
            medicine_name="Paracetamol",
            strength="500mg",
            dosage_form="Tablet",
            doses_per_day=2,
            instructions="Take 1 tablet after meals",
        )

        self.schedule = DoseSchedule(
            schedule_id="sched_2001",
            prescription_id="rx_1001",
            scheduled_time=self.now,
            grace_period_minutes=30,
        )

        self.decision = ComplianceDecision(
            decision_id="dec_3001",
            timestamp=self.now,
            patient_id="patient_402",
            strip_id="strip_20260729_001",
            prescription_id="rx_1001",
            outcome=DecisionOutcome.CORRECT_DOSE,
            reason="Tablet Paracetamol 500mg removed within scheduled time window",
            actionable=True,
            schema_version="1.0",
        )

    def test_prescription_immutability_and_serialization(self):
        """Test Prescription frozen immutability and dictionary roundtrip."""
        self.assertEqual(self.prescription.prescription_id, "rx_1001")
        self.assertEqual(self.prescription.medicine_name, "Paracetamol")

        with self.assertRaises(FrozenInstanceError):
            self.prescription.medicine_name = "Ibuprofen"

        d = self.prescription.to_dict()
        self.assertEqual(d["medicine_name"], "Paracetamol")
        self.assertEqual(d["strength"], "500mg")

        reconstructed = Prescription.from_dict(d)
        self.assertEqual(reconstructed, self.prescription)

    def test_compliance_decision_serialization_roundtrip(self):
        """Test ComplianceDecision dictionary roundtrip serialization."""
        d = self.decision.to_dict()
        self.assertEqual(d["decision_id"], "dec_3001")
        self.assertEqual(d["outcome"], "CORRECT_DOSE")
        self.assertTrue(d["actionable"])
        self.assertEqual(d["schema_version"], "1.0")

        reconstructed = ComplianceDecision.from_dict(d)
        self.assertEqual(reconstructed, self.decision)

    def test_clinical_exceptions(self):
        """Test clinical domain exception hierarchy."""
        self.assertTrue(issubclass(PrescriptionError, ClinicalEngineError))
        self.assertTrue(issubclass(InvalidScheduleError, ClinicalEngineError))


if __name__ == "__main__":
    unittest.main()
