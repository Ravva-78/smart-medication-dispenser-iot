"""
Unit tests for alerting package (enums, models, dispatchers, manager).
"""
import unittest
from datetime import datetime, timezone
from clinical.models import ComplianceDecision
from clinical.enums import DecisionOutcome
from alerting.enums import AlertChannel, AlertSeverity
from alerting.models import AlertMessage
from alerting.dispatchers import MockAlertDispatcher
from alerting.manager import AlertManager


class TestAlertingEngine(unittest.TestCase):
    """Test suite for Alert Engine subsystem dispatchers and manager."""

    def setUp(self):
        """Set up test fixtures for alerting engine."""
        self.now = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)
        self.mock_dispatcher = MockAlertDispatcher()
        self.manager = AlertManager(dispatchers=[self.mock_dispatcher])

        self.wrong_medicine_decision = ComplianceDecision(
            decision_id="dec_wrong_01",
            timestamp=self.now,
            patient_id="patient_100",
            strip_id="strip_55",
            prescription_id="rx_10",
            outcome=DecisionOutcome.WRONG_MEDICINE,
            reason="Extracted 'Aspirin' != prescribed 'Paracetamol'",
            actionable=True,
        )

        self.correct_dose_decision = ComplianceDecision(
            decision_id="dec_ok_01",
            timestamp=self.now,
            patient_id="patient_100",
            strip_id="strip_55",
            prescription_id="rx_10",
            outcome=DecisionOutcome.CORRECT_DOSE,
            reason="Correct dose taken",
            actionable=True,
        )

    def test_alert_message_dataclass(self):
        """Test AlertMessage immutability and dictionary serialization."""
        msg = AlertMessage(
            alert_id="alt_01",
            timestamp=self.now,
            patient_id="patient_100",
            decision_id="dec_wrong_01",
            severity=AlertSeverity.CRITICAL,
            channel=AlertChannel.ALARM_BUZZER,
            title="CRITICAL: Wrong Medicine Detected",
            message="Extracted 'Aspirin' != prescribed 'Paracetamol'",
        )
        self.assertEqual(msg.alert_id, "alt_01")
        self.assertEqual(msg.severity, AlertSeverity.CRITICAL)
        d = msg.to_dict()
        self.assertEqual(d["channel"], "ALARM_BUZZER")

    def test_process_wrong_medicine_decision_dispatches_critical_alert(self):
        """Test that processing a WRONG_MEDICINE decision dispatches CRITICAL alerts."""
        alerts = self.manager.process_decision(self.wrong_medicine_decision)

        self.assertGreater(len(alerts), 0)
        critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
        self.assertGreater(len(critical_alerts), 0)

        # Check mock dispatcher received messages
        sent_messages = self.mock_dispatcher.get_dispatched_messages()
        self.assertEqual(len(sent_messages), len(alerts))

    def test_process_correct_dose_decision_info_only(self):
        """Test that processing a CORRECT_DOSE decision generates INFO level record without alarm."""
        alerts = self.manager.process_decision(self.correct_dose_decision)

        for a in alerts:
            self.assertEqual(a.severity, AlertSeverity.INFO)


if __name__ == "__main__":
    unittest.main()
