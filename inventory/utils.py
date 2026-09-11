"""
Inventory Subsystem General Utility Helpers.

Purpose:
    Provides shared helper functions for datetime parsing, formatting, and string utilities.

Responsibilities:
    - Parse ISO 8601 strings and datetime instances safely.
    - Format datetime objects into standardized ISO 8601 strings.
    - Prevent private helper imports across domain module boundaries.

Dependencies:
    - Standard library `datetime`.
"""

from datetime import datetime, timezone
from typing import Any


def parse_datetime(val: Any) -> datetime:
    """
    Parse a string ISO 8601 timestamp or return an existing datetime object.

    Args:
        val: ISO string or datetime instance.

    Returns:
        datetime object.

    Raises:
        ValueError: If val is invalid or unsupported type.
    """
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        s = val.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    raise ValueError(f"Invalid timestamp type or value: {val}")


def format_datetime(dt: datetime) -> str:
    """
    Format a datetime instance into a standardized ISO 8601 string.

    Args:
        dt: datetime instance.

    Returns:
        ISO 8601 string.
    """
    return dt.isoformat()


__all__ = ["parse_datetime", "format_datetime"]
