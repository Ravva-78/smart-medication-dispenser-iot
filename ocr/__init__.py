"""
OCR Verification Subsystem Package.

This package extracts, parses, and verifies text from medicine packaging and foil backings,
constructing structured `MedicineIdentity` domain models.
"""

from ocr.enums import OCRStatus, ExtractionField
from ocr.exceptions import OCRError, InvalidOCRDataError, LowConfidenceOCRError, OCRBackendError
from ocr.models import MedicineIdentity, OCRRegion, OCRResult
from ocr.preprocessing import OCRImagePreprocessor
from ocr.backends import AbstractOCRBackend, MockOCRBackend, TesseractBackend, EasyOCRBackend
from ocr.cleaning import OCRTextCleaner
from ocr.parser import OCREntityParser
from ocr.verifier import OCRVerifier
from ocr.manager import OCRManager

__version__ = "0.1.0"

__all__ = [
    "OCRStatus",
    "ExtractionField",
    "OCRError",
    "InvalidOCRDataError",
    "LowConfidenceOCRError",
    "OCRBackendError",
    "MedicineIdentity",
    "OCRRegion",
    "OCRResult",
    "OCRImagePreprocessor",
    "AbstractOCRBackend",
    "MockOCRBackend",
    "TesseractBackend",
    "EasyOCRBackend",
    "OCRTextCleaner",
    "OCREntityParser",
    "OCRVerifier",
    "OCRManager",
]
