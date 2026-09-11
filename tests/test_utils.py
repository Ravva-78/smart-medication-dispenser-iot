"""
Unit tests for inventory/utils.py.
"""
import unittest
from datetime import datetime, timezone
from inventory.utils import parse_datetime, format_datetime


class TestInventoryUtils(unittest.TestCase):
    """Test suite for datetime serialization and parsing utility functions."""

    def test_format_datetime(self):
        """Test formatting datetime instance to ISO 8601 string."""
        dt = datetime(2026, 7, 29, 12, 30, 45, tzinfo=timezone.utc)
        formatted = format_datetime(dt)
        self.assertEqual(formatted, "2026-07-29T12:30:45+00:00")

    def test_parse_datetime_from_string(self):
        """Test parsing ISO string representation into datetime object."""
        iso_str = "2026-07-29T12:30:45+00:00"
        dt = parse_datetime(iso_str)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.minute, 30)

        # Test ISO string ending in Z
        z_str = "2026-07-29T12:30:45Z"
        dt_z = parse_datetime(z_str)
        self.assertEqual(dt_z.year, 2026)

    def test_parse_datetime_pass_through(self):
        """Test that passing an existing datetime instance returns it directly."""
        dt = datetime(2026, 7, 29, 12, 30, 45, tzinfo=timezone.utc)
        self.assertEqual(parse_datetime(dt), dt)

    def test_parse_invalid_datetime_type(self):
        """Test that invalid types raise ValueError."""
        with self.assertRaises(ValueError):
            parse_datetime(123456789)


if __name__ == "__main__":
    unittest.main()
