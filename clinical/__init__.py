"""
Clinical Decision Engine Package.

This package evaluates real-time inventory state events and OCR verified identities against
patient prescriptions and dose schedules to make automated clinical compliance decisions.
"""

from clinical.enums import DecisionOutcome, RuleSeverity, ScheduleWindowStatus
from clinical.exceptions import (
    ClinicalEngineError,
    PrescriptionError,
    InvalidScheduleError,
    RuleEvaluationError,
)
from clinical.models import Prescription, DoseSchedule, ComplianceDecision
from clinical.schedule import DoseScheduler
from clinical.rules import ClinicalRulesEngine
from clinical.history import ClinicalHistory
from clinical.manager import ClinicalDecisionManager

__version__ = "0.1.0"

__all__ = [
    "DecisionOutcome",
    "RuleSeverity",
    "ScheduleWindowStatus",
    "ClinicalEngineError",
    "PrescriptionError",
    "InvalidScheduleError",
    "RuleEvaluationError",
    "Prescription",
    "DoseSchedule",
    "ComplianceDecision",
    "DoseScheduler",
    "ClinicalRulesEngine",
    "ClinicalHistory",
    "ClinicalDecisionManager",
]
