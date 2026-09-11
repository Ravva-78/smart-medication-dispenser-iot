"""
Unit tests for clinical/history.py ClinicalHistory audit log & metrics module.
"""
import unittest
from datetime import datetime, timezone
from clinical.enums import DecisionOutcome
from clinical.models import ComplianceDecision
from clinical.history import ClinicalHistory


class TestClinicalHistory(unittest.TestCase):
    """Test suite for ClinicalHistory audit log tracker and adherence metrics calculator."""

    def setUp(self):
        """Create sample ComplianceDecision fixtures for history testing."""
        self.now = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone.utc)
        self.history = ClinicalHistory()

        self.decision1 = ComplianceDecision(
            decision_id="dec_01",
            timestamp=self.now,
            patient_id="patient_01",
            strip_id="strip_01",
            prescription_id="rx_101",
            outcome=DecisionOutcome.CORRECT_DOSE,
            reason="Correct dose taken",
            actionable=True,
        )

        self.decision2 = ComplianceDecision(
            decision_id="dec_02",
            timestamp=self.now,
            patient_id="patient_01",
            strip_id="strip_01",
            prescription_id="rx_101",
            outcome=DecisionOutcome.DOSE_MISSED,
            reason="Dose window elapsed",
            actionable=True,
        )

    def test_add_and_query_decisions(self):
        """Test logging decisions and querying by patient ID."""
        self.history.add_decision(self.decision1)
        self.history.add_decision(self.decision2)

        decisions = self.history.get_decisions(patient_id="patient_01")
        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0], self.decision1)

    def test_compute_patient_adherence_metrics(self):
        """Test calculating adherence percentage and clinical stats metrics."""
        self.history.add_decision(self.decision1)
        self.history.add_decision(self.decision2)

        metrics = self.history.get_metrics(patient_id="patient_01")
        self.assertEqual(metrics["total_decisions"], 2)
        self.assertEqual(metrics["correct_doses"], 1)
        self.assertEqual(metrics["missed_doses"], 1)
        self.assertEqual(metrics["adherence_percentage"], 50.0)


if __name__ == "__main__":
    unittest.main()
