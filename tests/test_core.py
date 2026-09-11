"""
Unit tests for core shared infrastructure package (clock, ids, logging, tracing, config).
"""
import unittest
from datetime import datetime, timezone
from core.clock import Clock, MockClock, SystemClock
from core.ids import IDGenerator
from core.tracing import TraceContext
from core.config import AppConfig


class TestCoreInfrastructure(unittest.TestCase):
    """Test suite for core shared utilities."""

    def test_clock_deterministic_mock(self):
        """Test MockClock returns fixed frozen timestamp for testing."""
        frozen_time = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)
        mock_clock = MockClock(frozen_time)
        Clock.set_clock(mock_clock)

        self.assertEqual(Clock.now(), frozen_time)

        # Reset to default SystemClock
        Clock.reset()
        self.assertIsInstance(Clock.get_clock(), SystemClock)

    def test_id_generator_formatting(self):
        """Test IDGenerator produces prefixed formatted hex strings."""
        event_id = IDGenerator.generate("evt")
        self.assertTrue(event_id.startswith("evt_"))

        decision_id = IDGenerator.generate("dec")
        self.assertTrue(decision_id.startswith("dec_"))

        trace_id = IDGenerator.generate("trace")
        self.assertTrue(trace_id.startswith("trace_"))

    def test_trace_context(self):
        """Test TraceContext correlation tracking payload."""
        ctx = TraceContext(
            trace_id="trace_1001",
            patient_id="patient_99",
            strip_id="strip_01",
        )
        self.assertEqual(ctx.trace_id, "trace_1001")
        d = ctx.to_dict()
        self.assertEqual(d["patient_id"], "patient_99")

    def test_app_config_defaults(self):
        """Test AppConfig default configuration settings."""
        config = AppConfig()
        self.assertEqual(config.app_name, "MedicineDispenser")
        self.assertEqual(config.env, "development")
        self.assertTrue(config.debug)


if __name__ == "__main__":
    unittest.main()
