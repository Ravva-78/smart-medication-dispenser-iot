"""
Clinical Decision Engine Dose Scheduler.

Purpose:
    Computes dose administration time windows and evaluates whether actual dose events occurred
    ON_TIME, EARLY, LATE, or MISSED relative to patient schedules.

Responsibilities:
    - Compute window start/end timestamps ($\text{scheduled\_time} \pm \text{grace\_period\_minutes}$).
    - Evaluate current execution time against scheduled window bounds.
    - Classify time window status (`ON_TIME`, `EARLY`, `LATE`, `MISSED`).

Dependencies:
    - Standard library `datetime`, `timedelta`, `logging`.
    - `clinical.models.DoseSchedule`.
    - `clinical.enums.ScheduleWindowStatus`.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple
from clinical.models import DoseSchedule
from clinical.enums import ScheduleWindowStatus

logger = logging.getLogger(__name__)


class DoseScheduler:
    """Calculator for dose schedule time windows and window classification."""

    @staticmethod
    def get_window_bounds(schedule: DoseSchedule) -> Tuple[datetime, datetime]:
        """
        Compute window start and end timestamps for a dose schedule.

        Args:
            schedule: DoseSchedule instance.

        Returns:
            Tuple of (start_datetime, end_datetime).
        """
        grace_td = timedelta(minutes=schedule.grace_period_minutes)
        window_start = schedule.scheduled_time - grace_td
        window_end = schedule.scheduled_time + grace_td
        return window_start, window_end

    @classmethod
    def evaluate_window(
        cls,
        schedule: DoseSchedule,
        current_time: datetime,
        max_late_minutes: int = 120,
    ) -> ScheduleWindowStatus:
        """
        Evaluate current execution timestamp against a DoseSchedule time window.

        Args:
            schedule: DoseSchedule instance.
            current_time: Actual timestamp of dose administration event or inspection.
            max_late_minutes: Maximum allowable late threshold before window is classified MISSED.

        Returns:
            ScheduleWindowStatus enum value.
        """
        window_start, window_end = cls.get_window_bounds(schedule)
        max_late_td = timedelta(minutes=max_late_minutes)

        if current_time < window_start:
            logger.info("Dose event is EARLY (time=%s < window_start=%s)", current_time.isoformat(), window_start.isoformat())
            return ScheduleWindowStatus.EARLY

        if window_start <= current_time <= window_end:
            logger.info("Dose event is ON_TIME (time=%s within window [%s, %s])", current_time.isoformat(), window_start.isoformat(), window_end.isoformat())
            return ScheduleWindowStatus.ON_TIME

        if window_end < current_time <= (window_end + max_late_td):
            logger.info("Dose event is LATE (time=%s > window_end=%s)", current_time.isoformat(), window_end.isoformat())
            return ScheduleWindowStatus.LATE

        logger.info("Dose event is MISSED (time=%s > max_late_threshold)", current_time.isoformat())
        return ScheduleWindowStatus.MISSED


__all__ = ["DoseScheduler"]
