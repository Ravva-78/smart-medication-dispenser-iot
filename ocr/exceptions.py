"""
OCR Verification Subsystem Domain Exceptions.

Purpose:
    Defines exception classes for OCR extraction, image pre-processing, and matching failures.

Responsibilities:
    - Establish base `OCRError` for domain error handling.
    - Provide specific exceptions for low confidence and invalid payloads.

Dependencies:
    - Standard library `Exception`.
"""


class OCRError(Exception):
    """Base exception class for all errors originating within the OCR subsystem."""
    pass


class InvalidOCRDataError(OCRError):
    """Raised when raw or structured OCR payload fails validation or schema parsing."""
    pass


class LowConfidenceOCRError(OCRError):
    """Raised when extracted text confidence falls below minimum threshold."""
    pass


class OCRBackendError(OCRError):
    """Raised when underlying OCR engine (Tesseract/Paddle/EasyOCR) encounters runtime failure."""
    pass


__all__ = [
    "OCRError",
    "InvalidOCRDataError",
    "LowConfidenceOCRError",
    "OCRBackendError",
]
