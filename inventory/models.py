"""
Inventory Subsystem Domain Models.

Purpose:
    Defines immutable data classes representing medicine strip metadata, inventory state,
    and historical snapshot entries.

Responsibilities:
    - Act as the single source of truth for medicine strip state.
    - Provide immutable dataclass contracts (`frozen=True`) to prevent accidental mutation.
    - Ensure strongly-typed fields, datetime Objects, and clean dictionary serialization/deserialization.

Dependencies:
    - Standard library `dataclasses`, `datetime`, `typing`.
    - `inventory.enums.InventoryStatus`, `inventory.enums.EventType`.
    - `config.PIPELINE_VERSION`, `config.SOFTWARE_VERSION`.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List, Optional
from inventory.enums import InventoryStatus, EventType
from inventory.utils import parse_datetime, format_datetime

try:
    from config import PIPELINE_VERSION, SOFTWARE_VERSION
except ImportError:
    PIPELINE_VERSION = "0.1.0"
    SOFTWARE_VERSION = "0.1.0"



@dataclass(frozen=True)
class InventoryMetadata:
    """Immutable metadata accompanying an inventory inspection."""
    inspection_id: str
    image_name: str
    capture_time: datetime
    camera_id: str
    model_versions: Dict[str, str] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    pipeline_version: str = PIPELINE_VERSION
    software_version: str = SOFTWARE_VERSION

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to a dictionary."""
        d = asdict(self)
        d["capture_time"] = format_datetime(self.capture_time)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryMetadata":
        """Deserialize dictionary payload into an InventoryMetadata instance."""
        data_copy = dict(data)
        data_copy["capture_time"] = parse_datetime(data_copy["capture_time"])
        return cls(**data_copy)



@dataclass(frozen=True)
class InventoryState:
    """Immutable domain model representing the complete inventory state of a medicine strip."""
    strip_id: str
    inspection_time: datetime
    total_slots: int
    present_count: int
    missing_count: int
    occupancy_percentage: float
    missing_slots: Tuple[int, ...]
    average_confidence: float
    status: InventoryStatus
    metadata: InventoryMetadata

    def __post_init__(self):
        """Normalize floating point values."""
        object.__setattr__(self, "average_confidence", round(self.average_confidence, 4))
        object.__setattr__(self, "occupancy_percentage", round(self.occupancy_percentage, 2))


    def to_dict(self) -> Dict[str, Any]:
        """Serialize inventory state to a dictionary."""
        return {
            "strip_id": self.strip_id,
            "inspection_time": format_datetime(self.inspection_time),
            "total_slots": self.total_slots,
            "present_count": self.present_count,
            "missing_count": self.missing_count,
            "occupancy_percentage": self.occupancy_percentage,
            "missing_slots": list(self.missing_slots),
            "average_confidence": round(self.average_confidence, 4),
            "status": self.status.value,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventoryState":
        """Deserialize dictionary payload into an InventoryState instance."""
        return cls(
            strip_id=data["strip_id"],
            inspection_time=parse_datetime(data["inspection_time"]),
            total_slots=int(data["total_slots"]),
            present_count=int(data["present_count"]),
            missing_count=int(data["missing_count"]),
            occupancy_percentage=float(data["occupancy_percentage"]),
            missing_slots=tuple(int(x) for x in data["missing_slots"]),
            average_confidence=float(data["average_confidence"]),
            status=InventoryStatus(data["status"]),
            metadata=InventoryMetadata.from_dict(data["metadata"]),
        )


@dataclass(frozen=True)
class InventorySnapshot:
    """Immutable historical snapshot combining an inventory state and an event trigger."""
    snapshot_id: str
    timestamp: datetime
    event_type: EventType
    event_id: str
    state: InventoryState

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to a dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": format_datetime(self.timestamp),
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "state": self.state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InventorySnapshot":
        """Deserialize dictionary payload into an InventorySnapshot instance."""
        return cls(
            snapshot_id=data["snapshot_id"],
            timestamp=parse_datetime(data["timestamp"]),
            event_type=EventType(data["event_type"]),
            event_id=data["event_id"],
            state=InventoryState.from_dict(data["state"]),
        )



__all__ = [
    "InventoryMetadata",
    "InventoryState",
    "InventorySnapshot",
]
