"""
Unit tests for clinical/schedule.py DoseScheduler module.
"""
import unittest
from datetime import datetime, timedelta, timezone
from clinical.enums import ScheduleWindowStatus
from clinical.models import DoseSchedule
from clinical.schedule import DoseScheduler


class TestDoseScheduler(unittest.TestCase):
    """Test suite for DoseScheduler time window calculation and classification."""

    def setUp(self):
        """Create baseline DoseSchedule fixture for time window testing."""
        self.scheduled_time = datetime(2026, 7, 29, 20, 0, 0, tzinfo=timezone.utc)  # 8:00 PM UTC
        self.schedule = DoseSchedule(
            schedule_id="sched_101",
            prescription_id="rx_201",
            scheduled_time=self.scheduled_time,
            grace_period_minutes=30,  # Window: 7:30 PM to 8:30 PM
        )

    def test_on_time_window_classification(self):
        """Test that dose taken within 8:00 PM ± 30 mins evaluates to ON_TIME."""
        # Exactly on time (8:00 PM)
        status = DoseScheduler.evaluate_window(self.schedule, self.scheduled_time)
        self.assertEqual(status, ScheduleWindowStatus.ON_TIME)

        # 7:35 PM (within window)
        early_in_window = self.scheduled_time - timedelta(minutes=25)
        self.assertEqual(DoseScheduler.evaluate_window(self.schedule, early_in_window), ScheduleWindowStatus.ON_TIME)

        # 8:25 PM (within window)
        late_in_window = self.scheduled_time + timedelta(minutes=25)
        self.assertEqual(DoseScheduler.evaluate_window(self.schedule, late_in_window), ScheduleWindowStatus.ON_TIME)

    def test_early_window_classification(self):
        """Test that dose taken before 7:30 PM evaluates to EARLY."""
        # 7:15 PM (45 mins before scheduled time)
        early_time = self.scheduled_time - timedelta(minutes=45)
        status = DoseScheduler.evaluate_window(self.schedule, early_time)
        self.assertEqual(status, ScheduleWindowStatus.EARLY)

    def test_late_and_missed_window_classification(self):
        """Test that dose taken after 8:30 PM evaluates to LATE or MISSED."""
        # 8:45 PM (15 mins past grace period)
        late_time = self.scheduled_time + timedelta(minutes=45)
        status = DoseScheduler.evaluate_window(self.schedule, late_time)
        self.assertEqual(status, ScheduleWindowStatus.LATE)

        # 11:00 PM (3 hours past scheduled time)
        missed_time = self.scheduled_time + timedelta(hours=3)
        status = DoseScheduler.evaluate_window(self.schedule, missed_time, max_late_minutes=120)
        self.assertEqual(status, ScheduleWindowStatus.MISSED)

    def test_get_window_bounds(self):
        """Test retrieving start and end timestamps of schedule window."""
        start_t, end_t = DoseScheduler.get_window_bounds(self.schedule)
        self.assertEqual(start_t, self.scheduled_time - timedelta(minutes=30))
        self.assertEqual(end_t, self.scheduled_time + timedelta(minutes=30))


if __name__ == "__main__":
    unittest.main()
