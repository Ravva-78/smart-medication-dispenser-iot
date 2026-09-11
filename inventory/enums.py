"""
Inventory Subsystem Enumerations.

Purpose:
    Defines strongly-typed enumerations for inventory status, state transition event types,
    and decision outcomes.

Responsibilities:
    - Eliminate free-form magic strings across the system.
    - Provide a single source of truth for status classification.
    - Support string serialization and JSON interoperability.

Dependencies:
    - Standard library enum.Enum.
"""

from enum import Enum


class InventoryStatus(str, Enum):
    """Enumeration of inventory status states."""
    NORMAL = "NORMAL"
    TABLET_MISSING = "TABLET_MISSING"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class EventType(str, Enum):
    """Enumeration of state transition event types."""
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    TABLET_REMOVED = "TABLET_REMOVED"
    TABLET_ADDED = "TABLET_ADDED"
    STRIP_REPLACED = "STRIP_REPLACED"
    INSPECTION = "INSPECTION"
    NO_CHANGE = "NO_CHANGE"
    UNKNOWN = "UNKNOWN"


class DecisionOutcome(str, Enum):
    """Enumeration of high-level dispensing and compliance decision outcomes."""
    PENDING = "PENDING"
    CORRECT_DOSE = "CORRECT_DOSE"
    DOSE_MISSED = "DOSE_MISSED"
    WRONG_MEDICINE = "WRONG_MEDICINE"
    DISPENSE_FAILURE = "DISPENSE_FAILURE"
    UNEXPECTED_REMOVAL = "UNEXPECTED_REMOVAL"


__all__ = [
    "InventoryStatus",
    "EventType",
    "DecisionOutcome",
]

