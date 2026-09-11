from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PocketResult:
    index: int
    class_name: str        # "present" | "missing"
    confidence: float
    bbox: tuple            # (x1, y1, x2, y2) in pixel coords


@dataclass
class StageImages:
    input: Optional[object] = None
    strip_detection: Optional[object] = None
    rectified: Optional[object] = None
    pocket_detection: Optional[object] = None
    pocket_crops: List[object] = field(default_factory=list)


@dataclass
class InspectionResult:
    total: int = 0
    present: int = 0
    missing: int = 0
    avg_confidence: float = 0.0
    pockets: List[PocketResult] = field(default_factory=list)
    stages: Optional[StageImages] = None
    execution_report: List[str] = field(default_factory=list)


    @property
    def occupancy_pct(self) -> float:
        return round((self.present / self.total * 100), 2) if self.total > 0 else 0.0

    @property
    def missing_indices(self) -> List[int]:
        return [p.index for p in self.pockets if p.class_name == "missing"]

    @property
    def status(self) -> str:
        if self.total == 0:
            return "No Pockets Detected"
        elif self.missing == 0:
            return "Inventory Fully Verified"
        else:
            return f"Missing {self.missing} Pill(s)"

    def to_dict(self, include_images=False):
        d = {
            "total": self.total,
            "present": self.present,
            "missing": self.missing,
            "occupancy_pct": f"{self.occupancy_pct}%",
            "missing_indices": self.missing_indices,
            "status": self.status,
            "avg_confidence": round(self.avg_confidence, 4),
            "pockets": [{
                "index": p.index,
                "class": p.class_name,
                "confidence": round(p.confidence, 4),
                "bbox": p.bbox,
            } for p in self.pockets],
        }
        if not include_images:
            d.pop("pockets", None)
        return d

