"""
Core Observability & Trace Correlation Context.

Purpose:
    Provides correlation tracking properties (`trace_id`, `patient_id`, `strip_id`, `inspection_id`)
    to allow reconstructing an entire patient/strip execution journey across bounded contexts.

Responsibilities:
    - Immutable dataclass `TraceContext`.
    - Dictionary serialization & deserialization.

Dependencies:
    - Standard library `dataclasses`, `typing`.
    - `core.ids.IDGenerator`.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
from core.ids import IDGenerator


@dataclass(frozen=True)
class TraceContext:
    """Immutable trace correlation context passed across bounded contexts."""
    trace_id: str
    patient_id: Optional[str] = None
    strip_id: Optional[str] = None
    inspection_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        patient_id: Optional[str] = None,
        strip_id: Optional[str] = None,
        inspection_id: Optional[str] = None,
    ) -> "TraceContext":
        """Factory method generating a new TraceContext with a unique trace_id."""
        return cls(
            trace_id=IDGenerator.generate("trace", 12),
            patient_id=patient_id,
            strip_id=strip_id,
            inspection_id=inspection_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize TraceContext to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceContext":
        """Deserialize dictionary payload into TraceContext instance."""
        return cls(**data)


__all__ = ["TraceContext"]
