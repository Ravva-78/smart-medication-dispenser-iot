"""
Unit tests for inventory/exceptions.py.
"""
import unittest
from inventory.exceptions import (
    InventoryError,
    ValidationError,
    InvalidStateError,
    PersistenceError,
    ItemNotFoundError,
)


class TestInventoryExceptions(unittest.TestCase):
    """Test suite for inventory exception hierarchy."""

    def test_exception_inheritance(self):
        """Test that all domain exceptions inherit from InventoryError and Exception."""
        self.assertTrue(issubclass(InventoryError, Exception))
        self.assertTrue(issubclass(ValidationError, InventoryError))
        self.assertTrue(issubclass(InvalidStateError, InventoryError))
        self.assertTrue(issubclass(PersistenceError, InventoryError))
        self.assertTrue(issubclass(ItemNotFoundError, InventoryError))

    def test_exception_raising_and_catching(self):
        """Test catching child exceptions as base InventoryError."""
        try:
            raise ValidationError("Count mismatch: present + missing != total")
        except InventoryError as err:
            self.assertIn("Count mismatch", str(err))

        try:
            raise PersistenceError("Failed to write JSON file")
        except InventoryError as err:
            self.assertIn("Failed to write", str(err))

        try:
            raise ItemNotFoundError("Strip 'strip_999' not found")
        except InventoryError as err:
            self.assertIn("Strip 'strip_999'", str(err))


if __name__ == "__main__":
    unittest.main()
