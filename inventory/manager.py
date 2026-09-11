"""
Inventory Subsystem High-Level Orchestrator Facade.

Purpose:
    Acts as the primary entry point and facade for converting vision pipeline InspectionResult objects
    into validated, persistent, event-driven InventoryState models.

Responsibilities:
    - Transform `InspectionResult` into `InventoryState`.
    - Auto-generate temporary strip IDs (`strip_YYYYMMDD_HHMMSS_XXXX`) if `strip_id` is omitted.
    - Evaluate business rules (assigning `LOW_CONFIDENCE`, `TABLET_MISSING`, or `NORMAL` status).
    - Validate technical correctness via `InventoryValidator`.
    - Compare state transitions via `InventoryComparator` to produce `InventoryEvent`.
    - Record state and events into `InventoryHistory`.
    - Persist JSON state if explicitly requested (`save=False` by default).
    - Expose formatted summary, dict, JSON, and storage retrieval interfaces.

Dependencies:
    - Standard library `datetime`, `uuid`, `logging`, `typing`.
    - `pipeline.inspection_result.InspectionResult`.
    - `inventory.enums.InventoryStatus`, `inventory.enums.EventType`.
    - `inventory.models.InventoryState`, `inventory.models.InventoryMetadata`.
    - `inventory.validator.InventoryValidator`.
    - `inventory.comparator.InventoryComparator`.
    - `inventory.history.InventoryHistory`.
    - `inventory.formatter.InventoryFormatter`.
    - `inventory.persistence.AbstractPersistenceManager`, `inventory.persistence.JSONPersistenceManager`.
    - `inventory.exceptions.ItemNotFoundError`.
"""

import uuid
import logging
from datetime import datetime, timezone
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from pipeline.inspection_result import InspectionResult
from inventory.enums import InventoryStatus, EventType
from inventory.models import InventoryState, InventoryMetadata
from inventory.validator import InventoryValidator
from inventory.comparator import InventoryComparator
from inventory.history import InventoryHistory
from inventory.formatter import InventoryFormatter
from inventory.persistence import AbstractPersistenceManager, JSONPersistenceManager
from inventory.exceptions import ItemNotFoundError

logger = logging.getLogger(__name__)


class StripIdentityProvider(ABC):
    """Abstract interface for pluggable strip identity providers (QR, Barcode, OCR, Auto-UUID)."""

    @abstractmethod
    def provide_id(self, result: Optional[InspectionResult] = None) -> str:
        """Provide or resolve a unique strip identifier."""
        pass


class DefaultStripIdentityProvider(StripIdentityProvider):
    """Default identity provider generating timestamped unique strip IDs."""

    def provide_id(self, result: Optional[InspectionResult] = None) -> str:
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        rand_hex = uuid.uuid4().hex[:6]
        return f"strip_{now_str}_{rand_hex}"


def generate_strip_id() -> str:
    """Generate a unique temporary strip identifier."""
    return DefaultStripIdentityProvider().provide_id()


class InventoryManager:
    """Orchestrator facade managing inventory states, state comparisons, history, and persistence."""

    def __init__(
        self,
        persistence: Optional[AbstractPersistenceManager] = None,
        identity_provider: Optional[StripIdentityProvider] = None,
        conf_threshold: float = 0.60,
    ):
        """
        Initialize InventoryManager.

        Args:
            persistence: Storage persistence implementation (defaults to JSONPersistenceManager).
            identity_provider: Pluggable strip ID provider (defaults to DefaultStripIdentityProvider).
            conf_threshold: Confidence threshold below which status becomes LOW_CONFIDENCE.
        """
        self.persistence = persistence if persistence is not None else JSONPersistenceManager()
        self.identity_provider = identity_provider if identity_provider is not None else DefaultStripIdentityProvider()
        self.conf_threshold = conf_threshold
        self._histories: Dict[str, InventoryHistory] = {}

    def _get_or_create_history(self, strip_id: str) -> InventoryHistory:
        """Get or initialize the InventoryHistory tracker for a strip ID."""
        if strip_id not in self._histories:
            # Check if history exists in storage
            stored_history = self.persistence.load_history(strip_id)
            if stored_history is not None:
                self._histories[strip_id] = stored_history
            else:
                self._histories[strip_id] = InventoryHistory(strip_id=strip_id)
        return self._histories[strip_id]

    def from_inspection(
        self,
        result: InspectionResult,
        strip_id: Optional[str] = None,
        image_name: str = "input.jpg",
        camera_id: str = "cam_01",
        save: bool = False,
        conf_threshold: Optional[float] = None,
        inspection_time: Optional[datetime] = None,
    ) -> Tuple[InventoryState, Any]:
        """
        Convert vision pipeline InspectionResult into validated InventoryState and InventoryEvent.

        Args:
            result: Vision pipeline InspectionResult instance.
            strip_id: Optional strip identifier. Resolved via identity_provider if None.
            image_name: Source image filename for metadata.
            camera_id: Source camera identifier.
            save: If True, saves record to persistence storage (defaults to False).
            conf_threshold: Custom confidence threshold for this call.
            inspection_time: Custom inspection timestamp.

        Returns:
            Tuple of (InventoryState, InventoryEvent).
        """
        if strip_id is None:
            strip_id = self.identity_provider.provide_id(result)


        if inspection_time is None:
            inspection_time = datetime.now(timezone.utc)

        if conf_threshold is None:
            conf_threshold = self.conf_threshold

        # 1. Determine Business InventoryStatus
        if result.avg_confidence < conf_threshold:
            status = InventoryStatus.LOW_CONFIDENCE
        elif result.missing > 0:
            status = InventoryStatus.TABLET_MISSING
        elif result.total > 0 and result.missing == 0:
            status = InventoryStatus.NORMAL
        else:
            status = InventoryStatus.UNKNOWN

        # 2. Extract missing slot indices sorted in ascending order
        missing_slots = tuple(sorted(result.missing_indices))

        # 3. Construct Metadata
        metadata = InventoryMetadata(
            inspection_id=f"insp_{uuid.uuid4().hex[:10]}",
            image_name=image_name,
            capture_time=inspection_time,
            camera_id=camera_id,
        )

        # 4. Construct InventoryState
        state = InventoryState(
            strip_id=strip_id,
            inspection_time=inspection_time,
            total_slots=result.total,
            present_count=result.present,
            missing_count=result.missing,
            occupancy_percentage=result.occupancy_pct,
            missing_slots=missing_slots,
            average_confidence=result.avg_confidence,
            status=status,
            metadata=metadata,
        )

        # 5. Technical Validation
        InventoryValidator.validate(state)

        # 6. Compare against previous state in history
        history = self._get_or_create_history(strip_id)
        prev_state = history.get_latest_state()
        event = InventoryComparator.compare(prev_state, state, timestamp=inspection_time)

        # 7. Record to History
        history.record_event(event)

        # 8. Optional Persistence Save
        if save:
            self.persistence.save(state, history)

        return state, event

    def summary(self, strip_id: str) -> str:
        """
        Return multiline terminal summary for a strip ID.

        Args:
            strip_id: Medicine strip identifier.

        Returns:
            Formatted multiline string.
        """
        history = self._get_or_create_history(strip_id)
        state = history.get_latest_state()
        if state is None:
            raise ItemNotFoundError(f"No inventory state recorded for strip: '{strip_id}'")
        return InventoryFormatter.to_terminal_summary(state)

    def to_dict(self, strip_id: str) -> Dict[str, Any]:
        """Return dictionary representation of latest state for strip ID."""
        history = self._get_or_create_history(strip_id)
        state = history.get_latest_state()
        if state is None:
            raise ItemNotFoundError(f"No inventory state recorded for strip: '{strip_id}'")
        return InventoryFormatter.to_dict(state)

    def to_json(self, strip_id: str, indent: int = 2) -> str:
        """Return indented JSON representation of latest state for strip ID."""
        history = self._get_or_create_history(strip_id)
        state = history.get_latest_state()
        if state is None:
            raise ItemNotFoundError(f"No inventory state recorded for strip: '{strip_id}'")
        return InventoryFormatter.to_json(state, indent=indent)

    def save(self, strip_id: str) -> Path:
        """Explicitly save current inventory state and history for strip ID to persistence storage."""
        history = self._get_or_create_history(strip_id)
        state = history.get_latest_state()
        if state is None:
            raise ItemNotFoundError(f"No inventory state recorded for strip: '{strip_id}'")
        return self.persistence.save(state, history)

    def load(self, strip_id: str) -> InventoryState:
        """Load InventoryState for strip ID from persistence storage."""
        state = self.persistence.load(strip_id)
        history = self.persistence.load_history(strip_id)
        if history is not None:
            self._histories[strip_id] = history
        return state


__all__ = ["InventoryManager", "generate_strip_id"]
