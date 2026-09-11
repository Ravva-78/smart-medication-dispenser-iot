"""
Clinical Decision Engine Enumerations.

Purpose:
    Defines string-inherited enumeration classes for clinical decision outcomes,
    rule severity levels, and schedule window statuses.

Responsibilities:
    - Categorize clinical decision outcomes (CORRECT_DOSE, DOSE_MISSED, WRONG_MEDICINE, EXTRA_DOSE, EXPIRED_MEDICINE).
    - Categorize safety rule severity levels (INFO, WARNING, CRITICAL).
    - Categorize schedule window status (ON_TIME, EARLY, LATE, MISSED).

Dependencies:
    - Standard library `enum.Enum`.
"""

from enum import Enum


class DecisionOutcome(str, Enum):
    """Classified clinical dose compliance outcomes."""
    CORRECT_DOSE = "CORRECT_DOSE"        # Right medicine + Right dosage + Removed on time
    DOSE_MISSED = "DOSE_MISSED"          # Scheduled dose window elapsed without tablet removal
    WRONG_MEDICINE = "WRONG_MEDICINE"    # Removed tablet contradicts prescribed drug
    EXTRA_DOSE = "EXTRA_DOSE"            # Tablet removed when no dose was scheduled
    EXPIRED_MEDICINE = "EXPIRED_MEDICINE"# Removed tablet is past expiry date
    PENDING = "PENDING"                  # Evaluation in progress


class RuleSeverity(str, Enum):
    """Clinical safety rule alert severity classification."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ScheduleWindowStatus(str, Enum):
    """Dose schedule window classification."""
    ON_TIME = "ON_TIME"                  # Dose taken within scheduled window (± grace period)
    EARLY = "EARLY"                      # Dose taken before scheduled window
    LATE = "LATE"                        # Dose taken after grace period
    MISSED = "MISSED"                    # Window elapsed completely


__all__ = ["DecisionOutcome", "RuleSeverity", "ScheduleWindowStatus"]
