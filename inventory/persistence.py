"""
Inventory Subsystem Storage & Persistence Layer.

Purpose:
    Provides an abstract storage interface and JSON file implementation for persisting InventoryState and InventoryHistory.

Responsibilities:
    - Define `AbstractPersistenceManager(ABC)` to decouple storage technology from the application layer.
    - Implement `JSONPersistenceManager` to save/load JSON inventory records atomically.
    - Handle missing files (`ItemNotFoundError`) and corrupted files (`PersistenceError`).

Dependencies:
    - Standard library `abc`, `json`, `pathlib`, `logging`.
    - `inventory.models.InventoryState`.
    - `inventory.history.InventoryHistory`.
    - `inventory.exceptions.PersistenceError`, `inventory.exceptions.ItemNotFoundError`.
    - `config.ROOT`.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

from inventory.models import InventoryState
from inventory.history import InventoryHistory
from inventory.exceptions import PersistenceError, ItemNotFoundError

try:
    from config import ROOT
    DEFAULT_STORAGE_DIR = ROOT / "output" / "inventory_data"
except ImportError:
    DEFAULT_STORAGE_DIR = Path("output/inventory_data")

logger = logging.getLogger(__name__)


class AbstractPersistenceManager(ABC):
    """Abstract base class establishing the contract for inventory storage implementations."""

    @abstractmethod
    def save(self, state: InventoryState, history: Optional[InventoryHistory] = None) -> Path:
        """Save an InventoryState and optional InventoryHistory to storage."""
        pass

    @abstractmethod
    def load(self, strip_id: str) -> InventoryState:
        """Load an InventoryState by strip ID from storage."""
        pass

    @abstractmethod
    def load_history(self, strip_id: str) -> Optional[InventoryHistory]:
        """Load an InventoryHistory by strip ID from storage."""
        pass

    @abstractmethod
    def exists(self, strip_id: str) -> bool:
        """Check if inventory data exists for a strip ID."""
        pass

    @abstractmethod
    def delete(self, strip_id: str) -> bool:
        """Delete inventory record for a strip ID from storage."""
        pass


class JSONPersistenceManager(AbstractPersistenceManager):
    """JSON file persistence manager implementing atomic storage operations."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize JSONPersistenceManager.

        Args:
            storage_dir: Path to directory where JSON storage files are saved.
        """
        self.storage_dir = Path(storage_dir) if storage_dir is not None else DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, strip_id: str) -> Path:
        """Return the target file path for a strip ID."""
        # Sanitize filename
        safe_id = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in strip_id)
        return self.storage_dir / f"{safe_id}.json"

    def save(self, state: InventoryState, history: Optional[InventoryHistory] = None) -> Path:
        """
        Save an InventoryState and optional InventoryHistory to JSON file.

        Args:
            state: InventoryState instance.
            history: Optional InventoryHistory tracker.

        Returns:
            Path to saved JSON file.

        Raises:
            PersistenceError: If write operation fails.
        """
        file_path = self._get_file_path(state.strip_id)
        payload: Dict[str, Any] = {
            "state": state.to_dict(),
            "history": history.to_dict() if history is not None else None,
        }

        try:
            temp_path = file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            temp_path.replace(file_path)
            logger.info("Saved inventory JSON for strip %s to: %s", state.strip_id, file_path)
            return file_path
        except Exception as err:
            logger.error("Failed to save inventory JSON for strip %s: %s", state.strip_id, err)
            raise PersistenceError(f"Failed to save inventory for strip {state.strip_id}: {err}") from err

    def load(self, strip_id: str) -> InventoryState:
        """
        Load an InventoryState by strip ID from JSON file.

        Args:
            strip_id: Medicine strip identifier.

        Returns:
            Deserialized InventoryState instance.

        Raises:
            ItemNotFoundError: If JSON file does not exist.
            PersistenceError: If JSON file is corrupted or cannot be read.
        """
        file_path = self._get_file_path(strip_id)
        if not file_path.exists():
            logger.warning("Inventory JSON not found for strip: %s at %s", strip_id, file_path)
            raise ItemNotFoundError(f"Inventory record for strip '{strip_id}' not found.")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return InventoryState.from_dict(payload["state"])
        except Exception as err:
            logger.error("Failed to load/parse inventory JSON for strip %s: %s", strip_id, err)
            raise PersistenceError(f"Corrupted or invalid JSON for strip '{strip_id}': {err}") from err

    def load_history(self, strip_id: str) -> Optional[InventoryHistory]:
        """
        Load an InventoryHistory by strip ID from JSON file.

        Args:
            strip_id: Medicine strip identifier.

        Returns:
            Deserialized InventoryHistory instance or None if not present in storage.
        """
        file_path = self._get_file_path(strip_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            hist_data = payload.get("history")
            if hist_data is not None:
                return InventoryHistory.from_dict(hist_data)
            return None
        except Exception as err:
            logger.error("Failed to load inventory history for strip %s: %s", strip_id, err)
            raise PersistenceError(f"Failed to load history for strip '{strip_id}': {err}") from err

    def exists(self, strip_id: str) -> bool:
        """Check if JSON record exists for strip ID."""
        return self._get_file_path(strip_id).exists()

    def delete(self, strip_id: str) -> bool:
        """Delete JSON record for strip ID."""
        file_path = self._get_file_path(strip_id)
        if file_path.exists():
            file_path.unlink()
            logger.info("Deleted inventory record for strip: %s", strip_id)
            return True
        return False


__all__ = ["AbstractPersistenceManager", "JSONPersistenceManager"]
