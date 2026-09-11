"""
Unit tests for inventory/enums.py.
"""
import unittest
from enum import Enum
from inventory.enums import InventoryStatus, EventType, DecisionOutcome


class TestInventoryEnums(unittest.TestCase):
    """Test suite for InventoryStatus, EventType, and DecisionOutcome enums."""

    def test_inventory_status_enum_values(self):
        """Test InventoryStatus members and string values."""
        self.assertEqual(InventoryStatus.NORMAL.value, "NORMAL")
        self.assertEqual(InventoryStatus.TABLET_MISSING.value, "TABLET_MISSING")
        self.assertEqual(InventoryStatus.INVALID.value, "INVALID")
        self.assertEqual(InventoryStatus.UNKNOWN.value, "UNKNOWN")
        self.assertEqual(InventoryStatus.LOW_CONFIDENCE.value, "LOW_CONFIDENCE")
        self.assertTrue(issubclass(InventoryStatus, str))
        self.assertTrue(issubclass(InventoryStatus, Enum))

    def test_event_type_enum_values(self):
        """Test EventType members and string values."""
        expected_events = {
            "CREATED", "UPDATED", "TABLET_REMOVED", "TABLET_ADDED",
            "STRIP_REPLACED", "INSPECTION", "NO_CHANGE", "UNKNOWN"
        }
        actual_events = {e.value for e in EventType}
        self.assertEqual(actual_events, expected_events)
        self.assertTrue(issubclass(EventType, str))
        self.assertTrue(issubclass(EventType, Enum))

    def test_decision_outcome_enum_values(self):
        """Test DecisionOutcome members and string values."""
        expected_outcomes = {
            "PENDING", "CORRECT_DOSE", "DOSE_MISSED", "WRONG_MEDICINE",
            "DISPENSE_FAILURE", "UNEXPECTED_REMOVAL"
        }
        actual_outcomes = {d.value for d in DecisionOutcome}
        self.assertEqual(actual_outcomes, expected_outcomes)
        self.assertTrue(issubclass(DecisionOutcome, str))
        self.assertTrue(issubclass(DecisionOutcome, Enum))

    def test_enum_uniqueness(self):
        """Test that all enum values across all enums are unique within their class."""
        for enum_cls in [InventoryStatus, EventType, DecisionOutcome]:
            values = [item.value for item in enum_cls]
            self.assertEqual(len(values), len(set(values)), f"Duplicate value found in {enum_cls.__name__}")

    def test_string_conversion_and_lookup(self):
        """Test string conversion, formatting, and constructor lookup for enums."""
        self.assertEqual(InventoryStatus.NORMAL.value, "NORMAL")
        self.assertEqual(f"{InventoryStatus.NORMAL.value}", "NORMAL")
        self.assertEqual(InventoryStatus("NORMAL"), InventoryStatus.NORMAL)
        self.assertEqual(EventType.TABLET_REMOVED.value, "TABLET_REMOVED")
        self.assertEqual(EventType("TABLET_REMOVED"), EventType.TABLET_REMOVED)
        self.assertEqual(DecisionOutcome.CORRECT_DOSE.value, "CORRECT_DOSE")
        self.assertEqual(DecisionOutcome("CORRECT_DOSE"), DecisionOutcome.CORRECT_DOSE)


    def test_enum_iteration(self):
        """Test iteration over enum members."""
        status_list = list(InventoryStatus)
        self.assertEqual(len(status_list), 5)
        self.assertIn(InventoryStatus.NORMAL, status_list)


if __name__ == "__main__":
    unittest.main()
