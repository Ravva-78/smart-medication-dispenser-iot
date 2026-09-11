"""
Clinical Decision Engine Domain Exceptions.

Purpose:
    Defines custom exception classes for prescription, scheduling, and clinical decision processing errors.

Responsibilities:
    - Establish base `ClinicalEngineError` for domain exception handling.
    - Provide typed exceptions for prescription validation and schedule errors.

Dependencies:
    - Standard library `Exception`.
"""


class ClinicalEngineError(Exception):
    """Base exception class for all errors originating within the Clinical Decision Engine."""
    pass


class PrescriptionError(ClinicalEngineError):
    """Raised when a prescription payload is invalid, expired, or corrupted."""
    pass


class InvalidScheduleError(ClinicalEngineError):
    """Raised when a dose schedule window is invalid or corrupted."""
    pass


class RuleEvaluationError(ClinicalEngineError):
    """Raised when a clinical rule evaluation fails during execution."""
    pass


__all__ = [
    "ClinicalEngineError",
    "PrescriptionError",
    "InvalidScheduleError",
    "RuleEvaluationError",
]
