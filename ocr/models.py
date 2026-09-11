"""
OCR Verification Subsystem Domain Models & Data Contracts.

Purpose:
    Defines immutable domain data models for extracted text regions, medicine identities, and OCR results.

Responsibilities:
    - `MedicineIdentity`: Structured medical product info (name, strength, dosage form, batch, expiry).
    - `OCRRegion`: Extracted bounding box text snippet with local confidence.
    - `OCRResult`: Full extraction payload with status classification and execution timings.

Dependencies:
    - Standard library `dataclasses`, `typing`.
    - `ocr.enums.OCRStatus`.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional
from ocr.enums import OCRStatus


@dataclass(frozen=True)
class MedicineIdentity:
    """Immutable domain model representing verified medical product identity."""
    medicine_name: str
    strength: str
    dosage_form: str = "Tablet"
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    manufacturer: Optional[str] = None
    confidence: float = 0.0

    def __post_init__(self):
        """Normalize floating point values."""
        object.__setattr__(self, "confidence", round(self.confidence, 4))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize MedicineIdentity to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MedicineIdentity":
        """Deserialize dictionary payload into a MedicineIdentity instance."""
        return cls(**data)


@dataclass(frozen=True)
class OCRRegion:
    """Extracted text bounding box snippet with local confidence score."""
    bbox: Tuple[int, int, int, int]
    text: str
    confidence: float

    def __post_init__(self):
        """Normalize floating point values."""
        object.__setattr__(self, "confidence", round(self.confidence, 4))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize OCRRegion to dictionary representation."""
        return {
            "bbox": list(self.bbox),
            "text": self.text,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OCRRegion":
        """Deserialize dictionary payload into an OCRRegion instance."""
        return cls(
            bbox=tuple(data["bbox"]),
            text=data["text"],
            confidence=float(data["confidence"]),
        )


@dataclass(frozen=True)
class OCRResult:
    """Immutable result payload of an OCR extraction run."""
    raw_text: str
    extracted_regions: Tuple[OCRRegion, ...]
    identity: Optional[MedicineIdentity]
    average_confidence: float
    processing_time_ms: float
    status: OCRStatus = OCRStatus.UNCERTAIN

    def __post_init__(self):
        """Normalize floating point values."""
        object.__setattr__(self, "average_confidence", round(self.average_confidence, 4))
        object.__setattr__(self, "processing_time_ms", round(self.processing_time_ms, 2))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize OCRResult to dictionary representation."""
        return {
            "raw_text": self.raw_text,
            "extracted_regions": [r.to_dict() for r in self.extracted_regions],
            "identity": self.identity.to_dict() if self.identity is not None else None,
            "average_confidence": self.average_confidence,
            "processing_time_ms": self.processing_time_ms,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OCRResult":
        """Deserialize dictionary payload into an OCRResult instance."""
        id_data = data.get("identity")
        identity = MedicineIdentity.from_dict(id_data) if id_data is not None else None
        regions = tuple(OCRRegion.from_dict(r) for r in data.get("extracted_regions", []))

        return cls(
            raw_text=data["raw_text"],
            extracted_regions=regions,
            identity=identity,
            average_confidence=float(data["average_confidence"]),
            processing_time_ms=float(data["processing_time_ms"]),
            status=OCRStatus(data["status"]),
        )


__all__ = ["MedicineIdentity", "OCRRegion", "OCRResult"]
