"""
Inventory Subsystem Domain Exceptions.

Purpose:
    Defines custom exception classes for domain validation, persistence, and state errors.

Responsibilities:
    - Provide clear, typed exception handling across the inventory module.
    - Enable upstream callers to catch domain-specific errors via base `InventoryError`.

Dependencies:
    - Standard library `Exception`.
"""


class InventoryError(Exception):
    """Base exception class for all errors originating within the inventory subsystem."""
    pass


class ValidationError(InventoryError):
    """Raised when an inventory state fails technical or mathematical validation constraints."""
    pass


class InvalidStateError(InventoryError):
    """Raised when an inventory state object violates internal structural contracts."""
    pass


class PersistenceError(InventoryError):
    """Raised when storage read, write, or deserialization operations fail."""
    pass


class ItemNotFoundError(InventoryError):
    """Raised when a requested strip ID or snapshot entry cannot be located."""
    pass


__all__ = [
    "InventoryError",
    "ValidationError",
    "InvalidStateError",
    "PersistenceError",
    "ItemNotFoundError",
]
