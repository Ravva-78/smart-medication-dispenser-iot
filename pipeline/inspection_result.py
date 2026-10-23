from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PocketResult:
    index: int
    class_name: str        # "present" | "missing"
    confidence: float
    bbox: tuple            # (x1, y1, x2, y2) in pixel coords
    row: int = 0           # 1-based grid position as seen in the image (0 = unknown)
    col: int = 0


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
    layout_rows: int = 0
    layout_cols: int = 0
    layout_ok: Optional[bool] = None   # None = layout not checked
    layout_error: str = ""
    expected_total: int = 0            # 0 = no expected layout configured
    uncertain_cells: List[str] = field(default_factory=list)  # pockets below the confidence floor
    error: str = ""                    # non-empty = inspection could not run properly
    layout_uncertain: bool = False     # detected pockets do not form a clean rows x cols grid

    @property
    def min_confidence(self) -> float:
        return min((p.confidence for p in self.pockets), default=0.0)

    @property
    def verification(self) -> str:
        """FAILED | NO_POCKETS | CONFIG_MISMATCH | REVIEW_REQUIRED | VERIFIED (counts are trustworthy only for VERIFIED)."""
        if self.error:
            return "FAILED"
        if self.total == 0:
            return "NO_POCKETS"
        if self.layout_ok is False:
            return "CONFIG_MISMATCH"
        if self.uncertain_cells or self.layout_uncertain:
            return "REVIEW_REQUIRED"
        return "VERIFIED"

    @property
    def missing_cells(self) -> List[str]:
        return [f"r{p.row}c{p.col}" for p in self.pockets if p.class_name == "missing"]

    @property
    def occupancy_pct(self) -> float:
        return round((self.present / self.total * 100), 2) if self.total > 0 else 0.0

    @property
    def missing_indices(self) -> List[int]:
        return [p.index for p in self.pockets if p.class_name == "missing"]

    @property
    def status(self) -> str:
        v = self.verification
        if v == "FAILED":
            return f"INSPECTION FAILED: {self.error}"
        elif v == "NO_POCKETS":
            return "No Pockets Detected"
        elif v == "CONFIG_MISMATCH":
            return f"CONFIG MISMATCH: {self.layout_error}"
        elif v == "REVIEW_REQUIRED":
            why = []
            if self.layout_uncertain:
                why.append(f"grid detection uncertain ({self.total} pockets do not form a clean "
                           f"{self.layout_rows}x{self.layout_cols} grid; confirm the layout)")
            if self.uncertain_cells:
                why.append(f"low-confidence pocket(s) {', '.join(self.uncertain_cells)} "
                           f"(lowest confidence {self.min_confidence:.2f})")
            return f"REVIEW REQUIRED: {'; '.join(why)}; counts are not verified"
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
            "missing_cells": self.missing_cells,
            "layout_ok": self.layout_ok,
            "layout_error": self.layout_error,
            "layout_rows": self.layout_rows,
            "layout_cols": self.layout_cols,
            "layout_uncertain": self.layout_uncertain,
            "expected_total": self.expected_total,
            "verification": self.verification,
            "uncertain_cells": self.uncertain_cells,
            "min_confidence": round(self.min_confidence, 4),
            "error": self.error,
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

