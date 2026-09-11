"""
OCR Verification Subsystem High-Level Orchestrator Facade.

Purpose:
    Acts as the primary entry point and facade for executing OCR extraction,
    text cleaning, medical entity parsing, and prescription verification.

Responsibilities:
    - Preprocess input image using `OCRImagePreprocessor`.
    - Delegate text extraction to pluggable `AbstractOCRBackend` (defaults to `MockOCRBackend`).
    - Clean raw extracted text via `OCRTextCleaner`.
    - Parse medical entities into `MedicineIdentity` via `OCREntityParser`.
    - Verify identity against expected prescription requirements via `OCRVerifier`.

Dependencies:
    - Standard library `logging`, `typing`.
    - `numpy`.
    - `ocr.enums.OCRStatus`.
    - `ocr.models.OCRResult`, `ocr.models.MedicineIdentity`.
    - `ocr.preprocessing.OCRImagePreprocessor`.
    - `ocr.backends.AbstractOCRBackend`, `ocr.backends.MockOCRBackend`.
    - `ocr.cleaning.OCRTextCleaner`.
    - `ocr.parser.OCREntityParser`.
    - `ocr.verifier.OCRVerifier`.
"""

import logging
from typing import Tuple, Optional
import numpy as np

from ocr.enums import OCRStatus
from ocr.models import OCRResult, MedicineIdentity
from ocr.preprocessing import OCRImagePreprocessor
from ocr.backends import AbstractOCRBackend, MockOCRBackend, EasyOCRBackend
from ocr.cleaning import OCRTextCleaner
from ocr.parser import OCREntityParser
from ocr.verifier import OCRVerifier

logger = logging.getLogger(__name__)


class OCRManager:
    """Orchestrator facade managing OCR pre-processing, engine extraction, parsing, and verification."""

    def __init__(
        self,
        backend: Optional[AbstractOCRBackend] = None,
        min_confidence: float = 0.70,
    ):
        """
        Initialize OCRManager facade.

        Args:
            backend: OCR engine implementation (defaults to EasyOCRBackend if available, else MockOCRBackend).
            min_confidence: Minimum required confidence score threshold.
        """
        if backend is not None:
            self.backend = backend
        else:
            try:
                easy = EasyOCRBackend()
                self.backend = easy if easy._available else MockOCRBackend()
            except Exception:
                self.backend = MockOCRBackend()
        self.min_confidence = min_confidence

    def process_image(self, image: np.ndarray, preprocess: bool = True) -> OCRResult:
        """
        Process an image array through pre-processing, OCR backend, cleaning, and entity parsing.

        Args:
            image: BGR or Grayscale numpy image array.
            preprocess: If True, executes CV preprocessing pipeline first.

        Returns:
            Fully populated OCRResult instance containing MedicineIdentity.
        """
        logger.debug("Processing image through OCRManager (backend=%s)", self.backend.get_backend_name())

        # 1. Image Pre-processing
        proc_image = OCRImagePreprocessor.preprocess(image) if preprocess else image

        # 2. Engine Extraction
        raw_result = self.backend.extract_text(proc_image)

        # 3. Text Cleaning & Normalization
        cleaned_text = OCRTextCleaner.clean(raw_result.raw_text)

        # 4. Medical Entity Parsing
        identity = OCREntityParser.parse(cleaned_text)

        # 5. Determine Overall Status
        if identity.confidence >= self.min_confidence:
            status = OCRStatus.VERIFIED
        elif identity.confidence > 0.0:
            status = OCRStatus.UNCERTAIN
        else:
            status = OCRStatus.FAILED

        # 6. Reconstruct Final OCRResult Payload
        final_result = OCRResult(
            raw_text=cleaned_text,
            extracted_regions=raw_result.extracted_regions,
            identity=identity,
            average_confidence=round(identity.confidence, 4),
            processing_time_ms=raw_result.processing_time_ms,
            status=status,
        )

        logger.info("OCR Processing completed for '%s' (status=%s)", identity.medicine_name, status.value)
        return final_result

    def verify_medicine(
        self,
        image: np.ndarray,
        expected_name: str,
        expected_strength: Optional[str] = None,
        preprocess: bool = True,
    ) -> Tuple[OCRResult, OCRStatus, str]:
        """
        Process image and verify extracted identity against expected prescription properties.

        Args:
            image: BGR or Grayscale numpy image array.
            expected_name: Expected medicine product name.
            expected_strength: Optional expected strength.
            preprocess: If True, executes CV preprocessing first.

        Returns:
            Tuple of (OCRResult, OCRStatus, detailed_reason_string).
        """
        result = self.process_image(image, preprocess=preprocess)

        if result.identity is None:
            return result, OCRStatus.FAILED, "No medicine identity extracted from image"

        status, reason = OCRVerifier.verify(
            extracted=result.identity,
            expected_name=expected_name,
            expected_strength=expected_strength,
            min_confidence=self.min_confidence,
        )

        return result, status, reason


__all__ = ["OCRManager"]
