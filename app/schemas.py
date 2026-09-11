"""
FastAPI Request & Response Pydantic Schemas.

Purpose:
    Provides Pydantic request and response schemas for OpenAPI documentation and input validation.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class PrescriptionSchema(BaseModel):
    """Prescription request schema."""
    prescription_id: str = Field(..., examples=["rx_1001"])
    patient_id: str = Field(..., examples=["patient_402"])
    medicine_name: str = Field(..., examples=["Paracetamol"])
    strength: str = Field(..., examples=["500mg"])
    dosage_form: str = Field(default="Tablet", examples=["Tablet"])


class RawInspectionSchema(BaseModel):
    """Raw Vision inspection input schema."""
    inspection_id: str = Field(..., examples=["insp_01"])
    image_name: str = Field(default="frame.jpg", examples=["frame.jpg"])
    capture_time: str = Field(..., examples=["2026-07-29T12:00:00Z"])
    camera_id: str = Field(default="cam_01", examples=["cam_01"])
    total: int = Field(..., examples=[10])
    present: int = Field(..., examples=[9])
    missing: int = Field(..., examples=[1])
    missing_indices: List[int] = Field(default_factory=list, examples=[[4]])
    avg_confidence: float = Field(default=0.98, examples=[0.98])


class InspectRequestSchema(BaseModel):
    """Inspection and evaluation request payload schema."""
    strip_id: Optional[str] = Field(default=None, examples=["strip_20260729_001"])
    raw_inspection: RawInspectionSchema
    prescription: PrescriptionSchema


class StandardAPIResponseSchema(BaseModel):
    """Standardized API JSON response payload wrapper."""
    status_code: int = Field(..., examples=[200])
    success: bool = Field(..., examples=[True])
    code: str = Field(..., examples=["SUCCESS"])
    data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = Field(default=None)


__all__ = [
    "PrescriptionSchema",
    "RawInspectionSchema",
    "InspectRequestSchema",
    "StandardAPIResponseSchema",
]
