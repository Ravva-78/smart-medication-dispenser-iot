"""
OCR Verification Subsystem Enumerations.

Purpose:
    Defines string-inherited enumeration classes for OCR extraction status and entity fields.

Responsibilities:
    - Categorize OCR execution states (VERIFIED, UNCERTAIN, REJECTED, FAILED).
    - Categorize extracted text entity fields (NAME, STRENGTH, DOSAGE, BATCH, EXPIRY, MANUFACTURER).

Dependencies:
    - Standard library `enum.Enum`.
"""

from enum import Enum


class OCRStatus(str, Enum):
    """Execution status of OCR text verification."""
    VERIFIED = "VERIFIED"          # Text extracted and matched prescription/dictionary with high confidence
    UNCERTAIN = "UNCERTAIN"        # Text extracted but confidence is below optimal threshold
    REJECTED = "REJECTED"          # Extracted text contradicts expected prescription
    FAILED = "FAILED"              # Low image quality or text unreadable


class ExtractionField(str, Enum):
    """Categorized medical entity fields extracted by OCR engine."""
    NAME = "NAME"                  # Active drug name (e.g., Paracetamol)
    STRENGTH = "STRENGTH"          # Dosage strength (e.g., 500mg)
    DOSAGE_FORM = "DOSAGE_FORM"    # Form (e.g., Tablet, Capsule)
    BATCH_NUMBER = "BATCH_NUMBER"  # Manufacturing batch code (e.g., BATCH-10492)
    EXPIRY_DATE = "EXPIRY_DATE"    # Expiry date (e.g., 2028-12-31)
    MANUFACTURER = "MANUFACTURER"  # Pharma company name


__all__ = ["OCRStatus", "ExtractionField"]
