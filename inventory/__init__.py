"""
Inventory Subsystem Package.

This package provides a production-grade, event-driven inventory tracking model for
medicine blister strips. It acts as the single source of truth for strip state.
"""

from inventory.enums import InventoryStatus, EventType, DecisionOutcome
from inventory.models import InventoryMetadata, InventoryState, InventorySnapshot
from inventory.exceptions import (
    InventoryError,
    ValidationError,
    InvalidStateError,
    PersistenceError,
    ItemNotFoundError,
)
from inventory.validator import InventoryValidator
from inventory.events import InventoryEvent
from inventory.comparator import InventoryComparator
from inventory.history import InventoryHistory
from inventory.formatter import InventoryFormatter
from inventory.persistence import AbstractPersistenceManager, JSONPersistenceManager
from inventory.decision import DecisionEngine
from inventory.manager import InventoryManager, StripIdentityProvider, DefaultStripIdentityProvider, generate_strip_id

__version__ = "0.1.0"

__all__ = [
    "InventoryStatus",
    "EventType",
    "DecisionOutcome",
    "InventoryMetadata",
    "InventoryState",
    "InventorySnapshot",
    "InventoryError",
    "ValidationError",
    "InvalidStateError",
    "PersistenceError",
    "ItemNotFoundError",
    "InventoryValidator",
    "InventoryEvent",
    "InventoryComparator",
    "InventoryHistory",
    "InventoryFormatter",
    "AbstractPersistenceManager",
    "JSONPersistenceManager",
    "DecisionEngine",
    "InventoryManager",
    "StripIdentityProvider",
    "DefaultStripIdentityProvider",
    "generate_strip_id",
]
