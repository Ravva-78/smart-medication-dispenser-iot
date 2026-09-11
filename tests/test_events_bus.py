"""
Unit tests for events/bus.py in-process EventBus implementation.
"""
import unittest
from datetime import datetime, timezone
from events.bus import EventBus, EventSubscriber
from clinical.models import ComplianceDecision
from clinical.enums import DecisionOutcome


class SampleSubscriber(EventSubscriber):
    """Sample test event subscriber."""

    def __init__(self):
        self.received_events = []

    def on_event(self, event_type: str, payload: object) -> None:
        self.received_events.append((event_type, payload))


class TestEventBus(unittest.TestCase):
    """Test suite for in-process EventBus publisher/subscriber pattern."""

    def setUp(self):
        """Reset EventBus before each test."""
        self.bus = EventBus()
        self.bus.clear_subscribers()

        self.subscriber = SampleSubscriber()
        self.now = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)
        self.decision = ComplianceDecision(
            decision_id="dec_test_01",
            timestamp=self.now,
            patient_id="p_01",
            strip_id="s_01",
            prescription_id="rx_01",
            outcome=DecisionOutcome.CORRECT_DOSE,
            reason="Match",
            actionable=True,
        )

    def test_publish_and_subscribe_flow(self):
        """Test subscribing to event channel and receiving published events."""
        self.bus.subscribe("compliance_decision", self.subscriber)
        self.bus.publish("compliance_decision", self.decision)

        self.assertEqual(len(self.subscriber.received_events), 1)
        event_type, payload = self.subscriber.received_events[0]
        self.assertEqual(event_type, "compliance_decision")
        self.assertEqual(payload, self.decision)

    def test_unsubscribe(self):
        """Test unsubscribing stops receiving events."""
        self.bus.subscribe("compliance_decision", self.subscriber)
        self.bus.unsubscribe("compliance_decision", self.subscriber)
        self.bus.publish("compliance_decision", self.decision)

        self.assertEqual(len(self.subscriber.received_events), 0)


if __name__ == "__main__":
    unittest.main()
